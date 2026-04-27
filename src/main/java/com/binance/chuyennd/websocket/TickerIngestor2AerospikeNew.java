package com.binance.chuyennd.websocket;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.apache.commons.lang.StringUtils;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.*;

public class TickerIngestor2AerospikeNew {
    public static final Logger LOG = LoggerFactory.getLogger(TickerIngestor2AerospikeNew.class);

    private final ConcurrentHashMap<Long, ConcurrentHashMap<String, KlineObjectOptimized>> timeBuffer = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Float> priceBuffer = new ConcurrentHashMap<>();
    private final Set<String> globalSubscribedSymbols = Collections.newSetFromMap(new ConcurrentHashMap<>());

    private final ExecutorService restFetchService = Executors.newFixedThreadPool(15);
    private final ExecutorService repairService = Executors.newSingleThreadExecutor();

    public void start() {
        LOG.info("🚀 TickerIngestor V8.1 (HYBRID REALTIME - KHẮC PHỤC TRỄ 1 PHÚT) Started!");

        List<String> symbols = collectSymbolsFromRedis();
        globalSubscribedSymbols.addAll(symbols);

        startDataRepair(30 * 60);
        startIngestorLoops();
    }

    private void startIngestorLoops() {
        // --- LUỒNG 1: LẤY GIÁ & "HOẠT HÌNH" NẾN HIỆN TẠI (3s/lần) ---
        new Thread(() -> {
            Thread.currentThread().setName("Rest-Price-Loop");
            String endpoint = "https://fapi.binance.com/fapi/v1/ticker/price"; // Chỉ tốn 2 weight

            while (true) {
                try {
                    String response = HttpRequest.getContentFromUrl(endpoint, 5000);
                    List<String> newSymbolsToRepair = new ArrayList<>();
                    long curMin = Utils.getMinute(System.currentTimeMillis());

                    // Lấy hoặc tạo mới rổ chứa nến của phút HIỆN TẠI
                    ConcurrentHashMap<String, KlineObjectOptimized> currentMinuteCandles = timeBuffer.computeIfAbsent(curMin, k -> new ConcurrentHashMap<>());

                    if (StringUtils.isNotBlank(response) && response.trim().startsWith("[")) {
                        JSONArray tickers = new JSONArray(response);

                        for (int i = 0; i < tickers.length(); i++) {
                            JSONObject obj = tickers.getJSONObject(i);
                            String symbol = obj.getString("symbol").toUpperCase();

                            if (symbol.endsWith("USDT") && symbol.matches("^[A-Z0-9]+$") && !Constants.diedSymbol.contains(symbol)) {
                                float price = obj.getFloat("price");
                                priceBuffer.put(symbol, price);

                                // --- LOGIC NẶN NẾN REALTIME ---
                                String shortS = symbol.replace("USDT", "");
                                currentMinuteCandles.compute(shortS, (k, existingCandle) -> {
                                    if (existingCandle == null) {
                                        // Phút mới chưa có data -> Lấy giá hiện tại làm râu nến ban đầu
                                        return KlineObjectOptimized.newBuilder()
                                                .setPriceOpen(price).setPriceClose(price)
                                                .setMaxPrice(price).setMinPrice(price)
                                                .setTotalUsdt(0).build();
                                    } else {
                                        // Đã có data -> Cập nhật Close và nới râu High/Low theo giá Realtime
                                        return KlineObjectOptimized.newBuilder()
                                                .setPriceOpen(existingCandle.getPriceOpen())
                                                .setPriceClose(price)
                                                .setMaxPrice(Math.max(existingCandle.getMaxPrice(), price))
                                                .setMinPrice(Math.min(existingCandle.getMinPrice(), price))
                                                .setTotalUsdt(existingCandle.getTotalUsdt()).build();
                                    }
                                });

                                if (!globalSubscribedSymbols.contains(symbol)) {
                                    LOG.info("✨ Mã mới gia nhập cuộc chơi: {}", symbol);
                                    initNewSymbolConfig(symbol);
                                    globalSubscribedSymbols.add(symbol);
                                    newSymbolsToRepair.add(symbol);
                                }
                            }
                        }

                        // Ghi Giá Realtime cho Bot chạy
                        if (!priceBuffer.isEmpty()) {
                            DataManagerAerospikeFloatSim.writePriceRealtime(new HashMap<>(priceBuffer));
                        }

                        // 🔥 ĐIỂM SỬA QUAN TRỌNG: Ghi liên tục NẾN HIỆN TẠI xuống DB để Bot không bị trễ
                        if (!currentMinuteCandles.isEmpty()) {
                            DataManagerAerospikeFloatSim.writeMinuteBatch(curMin, new HashMap<>(currentMinuteCandles));
                        }

                        // Repair mã mới
                        if (!newSymbolsToRepair.isEmpty()) {
                            final List<String> repairList = new ArrayList<>(newSymbolsToRepair);
                            repairService.execute(() -> repairBatchOptimized(repairList, Utils.getMinute(System.currentTimeMillis() - 30 * Utils.TIME_HOUR), 1800));
                        }

                    } else if (StringUtils.isNotBlank(response) && response.trim().startsWith("{")) {
                        LOG.warn("⚠️ API Price báo lỗi (Limit): {}", response);
                    }

                    Thread.sleep(3000);

                } catch (Exception e) {
                    LOG.error("❌ Rest-Price-Loop Error: {}", e.getMessage());
                    Utils.sleep(3000L);
                }
            }
        }).start();

        // --- LUỒNG 2: CHỐT NẾN CHUẨN (ĐÚNG 1 LẦN KHI SANG PHÚT MỚI) ---
        new Thread(() -> {
            Thread.currentThread().setName("Rest-Kline-Loop");
            long lastProcessedMinute = 0;

            while (true) {
                try {
                    long now = System.currentTimeMillis();
                    long curMin = Utils.getMinute(now);
                    long second = (now / 1000) % 60;

                    // Chỉ kích hoạt lấy Klines vào đúng giây thứ 02 đến 10 của phút mới
                    if (second >= 2 && second <= 10 && curMin > lastProcessedMinute) {
                        List<String> currentSymbols = new ArrayList<>(globalSubscribedSymbols);
                        if (!currentSymbols.isEmpty()) {
                            List<List<String>> batches = subListBySize(currentSymbols, 15);
                            List<Future<?>> futures = new ArrayList<>();

                            for (List<String> batch : batches) {
                                futures.add(restFetchService.submit(() -> fetchKlinesForBatch(batch)));
                            }

                            for (Future<?> f : futures) {
                                f.get(20, TimeUnit.SECONDS);
                            }

                            flushKlinesToDatabase(curMin);
                            lastProcessedMinute = curMin;
                        }
                    }
                    Thread.sleep(1000);
                } catch (Exception e) {
                    LOG.error("❌ Rest-Kline-Loop Error: {}", e.getMessage());
                }
            }
        }).start();
    }

    //    private void fetchKlinesForBatch(List<String> symbols) {
//        for (String symbol : symbols) {
//            try {
//                // limit=2 sẽ lấy cây nến ĐÃ ĐÓNG của phút trước, VÀ cây nến VỪA MỞ của phút hiện tại
//                String url = "https://fapi.binance.com/fapi/v1/klines?symbol=" + symbol + "&interval=1m&limit=2";
//                String response = HttpRequest.getContentFromUrl(url, 5000);
//
//                if (StringUtils.isNotBlank(response) && response.trim().startsWith("[")) {
//                    JSONArray klines = new JSONArray(response);
//
//                    for (int i = 0; i < klines.length(); i++) {
//                        JSONArray k = klines.getJSONArray(i);
//
//                        long startTime = k.getLong(0);
//                        float open = k.getFloat(1);
//                        float high = k.getFloat(2);
//                        float low = k.getFloat(3);
//                        float close = k.getFloat(4);
//                        float volume = k.getFloat(7);
//
//                        String shortS = symbol.replace("USDT", "");
//                        KlineObjectOptimized optP = KlineObjectOptimized.newBuilder()
//                                .setPriceOpen(open).setPriceClose(close)
//                                .setMaxPrice(high).setMinPrice(low)
//                                .setTotalUsdt(volume).build();
//
//                        // Nạp đè dữ liệu CHUẨN TỪ SÀN vào RAM (thay thế cho cây nến ta tự nặn lúc đầu)
//                        timeBuffer.computeIfAbsent(startTime, key -> new ConcurrentHashMap<>()).put(shortS, optP);
//                    }
//                }
//                Thread.sleep(10);
//            } catch (Exception e) {
//                // Ignore
//            }
//        }
//    }
    private void fetchKlinesForBatch(List<String> symbols) {
        // Khởi tạo một ThreadPool riêng để gọi API Binance song song (Khoảng 30 luồng là mượt nhất)
        java.util.concurrent.ForkJoinPool customThreadPool = new java.util.concurrent.ForkJoinPool(30);

        try {
            customThreadPool.submit(() ->
                    symbols.parallelStream().forEach(symbol -> {
                        try {
                            String url = "https://fapi.binance.com/fapi/v1/klines?symbol=" + symbol + "&interval=1m&limit=2";
                            // Giảm timeout xuống 3000ms để luồng không bị kẹt nếu mạng lag
                            String response = HttpRequest.getContentFromUrl(url, 3000);

                            if (org.apache.commons.lang.StringUtils.isNotBlank(response) && response.trim().startsWith("[")) {
                                org.json.JSONArray klines = new org.json.JSONArray(response);

                                for (int i = 0; i < klines.length(); i++) {
                                    org.json.JSONArray k = klines.getJSONArray(i);

                                    long startTime = k.getLong(0);
                                    float open = k.getFloat(1);
                                    float high = k.getFloat(2);
                                    float low = k.getFloat(3);
                                    float close = k.getFloat(4);
                                    float volume = k.getFloat(7);

                                    String shortS = symbol.replace("USDT", "");
                                    com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized optP =
                                            com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized.newBuilder()
                                                    .setPriceOpen(open).setPriceClose(close)
                                                    .setMaxPrice(high).setMinPrice(low)
                                                    .setTotalUsdt(volume).build();

                                    // Nạp đè dữ liệu CHUẨN TỪ SÀN vào RAM
                                    // timeBuffer là ConcurrentHashMap nên rất an toàn khi dùng đa luồng
                                    timeBuffer.computeIfAbsent(startTime, key -> new java.util.concurrent.ConcurrentHashMap<>()).put(shortS, optP);
                                }
                            }
                            // 🔥 ĐÃ XÓA THREAD.SLEEP(10)
                        } catch (Exception e) {
                            // Ignore lỗi của từng đồng coin để không ảnh hưởng các coin khác
                        }
                    })
            ).get(); // Đợi tất cả 554 đồng coin tải xong
        } catch (Exception e) {
            LOG.error("Lỗi khi fetch kline đa luồng: ", e);
        } finally {
            customThreadPool.shutdown();
        }
    }

    private void flushKlinesToDatabase(long curMin) {
        long lastMin = curMin - 60000;

        try {
            // 1. Lưu cây nến hiện tại (Đã được cập nhật Open/Volume chuẩn)
            if (timeBuffer.containsKey(curMin)) {
                DataManagerAerospikeFloatSim.writeMinuteBatch(curMin, new HashMap<>(timeBuffer.get(curMin)));
            }

            // 2. Chốt lưu vĩnh viễn cây nến của phút trước
            if (timeBuffer.containsKey(lastMin)) {
                DataManagerAerospikeFloatSim.writeMinuteBatch(lastMin, new HashMap<>(timeBuffer.get(lastMin)));

                int finalSize = timeBuffer.get(lastMin).size();
                timeBuffer.remove(lastMin);
                LOG.info("✅ [KLINE V8.1] Chốt nến phút {} thành công. Total: {} symbols", Utils.normalizeDateYYYYMMDDHHmm(lastMin), finalSize);
            }

            // Dọn rác
            for (Long timeKey : new ArrayList<>(timeBuffer.keySet())) {
                if (timeKey < lastMin) timeBuffer.remove(timeKey);
            }
        } catch (Exception e) {
            LOG.error("❌ Flush Kline Error: {}", e.getMessage());
        }
    }

    private List<String> collectSymbolsFromRedis() {
        List<String> symbols = new ArrayList<>();
        Set<String> redisData = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
        String regex = "^[A-Z0-9]+$";

        for (String s : redisData) {
            String upperS = s.toUpperCase();
            if (!Constants.diedSymbol.contains(upperS) && StringUtils.endsWithIgnoreCase(upperS, "USDT") && upperS.matches(regex)) {
                symbols.add(upperS);
            }
        }
        return symbols;
    }

    private void startDataRepair(int totalMinutes) {
        repairService.execute(() -> {
            try {
                long now = System.currentTimeMillis();
                int step = 500;
                List<String> symbols = collectSymbolsFromRedis();

                for (int offset = totalMinutes; offset > 0; offset -= step) {
                    long batchStart = Utils.getMinute(now - (long) offset * Utils.TIME_MINUTE);
                    List<String> missing = new ArrayList<>();

                    for (String s : symbols) {
                        if (DataManagerAerospikeFloatSim.isSymbolMissingInPoints(s.replace("USDT", ""), batchStart, step)) {
                            missing.add(s);
                        }
                    }

                    if (!missing.isEmpty()) {
                        repairBatchOptimized(missing, batchStart, step);
                        Thread.sleep(5000);
                    }
                }
            } catch (Exception e) {
                LOG.error("Repair Task Error", e);
            }
        });
    }

    private void repairBatchOptimized(List<String> symbols, long batchStartTime, int limit) {
        for (String s : symbols) {
            try {
                if (StringUtils.isBlank(s) || !s.matches("^[A-Z0-9]+$")) continue;

                List<KlineObjectSimple> candles = TickerFuturesHelper.getTickerSimpleWithStartTimeAndLimit(s, "1m", batchStartTime, limit);
                if (candles == null || candles.isEmpty()) continue;

                String shortS = s.replace("USDT", "");
                for (KlineObjectSimple c : candles) {
                    if (c == null || c.startTime == null) continue;
                    long ts = c.startTime.longValue();

                    if (ts >= batchStartTime && ts < batchStartTime + (long) limit * Utils.TIME_MINUTE) {
                        Map<String, KlineObjectOptimized> map = new HashMap<>();
                        map.put(shortS, convertToProto(c));
                        DataManagerAerospikeFloatSim.writeMinuteBatch(ts, map);
                    }
                }

                Thread.sleep(300);

            } catch (Exception e) {
                // Ignore
            }
        }
    }

    private void initNewSymbolConfig(String symbol) {
        try {
            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS, symbol, symbol);
            ClientSingleton.getInstance().syncRequestClient.changeInitialLeverage(symbol, Configs.LEVERAGE_ORDER);
        } catch (Exception e) {
        }
    }

    private List<List<String>> subListBySize(List<String> list, int size) {
        List<List<String>> parts = new ArrayList<>();
        for (int i = 0; i < list.size(); i += size) parts.add(list.subList(i, Math.min(i + size, list.size())));
        return parts;
    }

    private KlineObjectOptimized convertToProto(KlineObjectSimple c) {
        return KlineObjectOptimized.newBuilder().setPriceOpen(c.priceOpen).setPriceClose(c.priceClose)
                .setMaxPrice(c.maxPrice).setMinPrice(c.minPrice).setTotalUsdt(c.totalUsdt).build();
    }
}