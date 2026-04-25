package com.binance.chuyennd.websocket;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.SubscriptionClient;
import com.binance.client.SubscriptionOptions;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.CandlestickInterval;
import com.binance.client.model.event.CandlestickEvent;
import com.binance.connector.futures.client.impl.UMWebsocketClientImpl;
import org.apache.commons.lang.StringUtils;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.*;

public class TickerIngestor2Aerospike {
    public static final Logger LOG = LoggerFactory.getLogger(TickerIngestor2AerospikeNew.class);

    private final ConcurrentHashMap<Long, ConcurrentHashMap<String, KlineObjectOptimized>> timeBuffer = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Float> priceBuffer = new ConcurrentHashMap<>();
    private final Set<String> globalSubscribedSymbols = Collections.newSetFromMap(new ConcurrentHashMap<>());
    private final List<SubscriptionClient> klineClients = new CopyOnWriteArrayList<>();
    private final ExecutorService repairService = Executors.newSingleThreadExecutor();

    private static final int MAX_STREAM_PER_CONNECTION = 150;

    public void start() {

        LOG.info("🚀 TickerIngestor V3 Started - Filtering invalid symbols");
        // 2. Tạo kết nối Kline cho tất cả symbol trong Redis
        List<String> symbols = collectSymbolsFromRedis();
        List<List<String>> partitions = subListBySize(symbols, MAX_STREAM_PER_CONNECTION);
        for (List<String> batch : partitions) {
            createNewKlineConnection(batch);
        }
        // 3. Kết nối Websocket để lấy price real time và symbol mới
        new UMWebsocketClientImpl().allTickerStream(this::processAllTickerJson);

        startDataRepair(30 * 60);
        startIngestorLoops();
    }

    private void processAllTickerJson(String eventStr) {
        try {
            JSONArray tickers = new JSONArray(eventStr);
            List<String> newSymbols = new ArrayList<>();
            // Regex chỉ cho phép chữ cái A-Z và số
            String regex = "^[A-Z0-9]+$";

            for (int i = 0; i < tickers.length(); i++) {
                JSONObject obj = tickers.getJSONObject(i);
                String symbol = obj.getString("s").toUpperCase();

                if (symbol.endsWith("USDT") && symbol.matches(regex)) {
                    priceBuffer.put(symbol, obj.getFloat("c"));
                    if (!globalSubscribedSymbols.contains(symbol) && !Constants.diedSymbol.contains(symbol)) {
                        LOG.info("✨ New Valid Symbol: {}", symbol);
                        initNewSymbolConfig(symbol);
                        globalSubscribedSymbols.add(symbol);
                        newSymbols.add(symbol);
                    }
                }
            }
            if (!newSymbols.isEmpty()) handleNewSymbolsDynamic(newSymbols);
        } catch (Exception e) { LOG.error("Ticker Processing Error", e); }
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
                        if (DataManagerAerospikeFloatSim.isSymbolMissingInPoints(s.replace("USDT",""), batchStart, step)) {
                            missing.add(s);
                        }
                    }
                    if (!missing.isEmpty()) {
                        repairBatch500(missing, batchStart, step);
                        Thread.sleep(3000);
                    }
                }
            } catch (Exception e) { LOG.error("Repair Task Error", e); }
        });
    }

    private void repairBatch500(List<String> symbols, long batchStartTime, int limit) {
        for (String s : symbols) {
            try {
                // Thêm kiểm tra Null và Regex một lần nữa để bảo vệ API
                if (StringUtils.isBlank(s) || !s.matches("^[A-Z0-9]+$")) continue;

                List<KlineObjectSimple> candles = TickerFuturesHelper.getTickerSimpleWithStartTime(s, "1m", batchStartTime);
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
            } catch (Exception e) { LOG.error("Repair Error for symbol {}: {}", s, e.getMessage()); }
        }
    }

    private List<String> collectSymbolsFromRedis() {
        List<String> symbols = new ArrayList<>();
        Set<String> redisData = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
        // Regex lọc bỏ ký tự đặc biệt, tiếng Trung và khoảng trắng
        String regex = "^[A-Z0-9]+$";

        for (String s : redisData) {
            String upperS = s.toUpperCase();
            if (!Constants.diedSymbol.contains(upperS) &&
                    StringUtils.endsWithIgnoreCase(upperS, "USDT") &&
                    upperS.matches(regex)) {
                symbols.add(upperS);
            } else if (!upperS.matches(regex)) {
                LOG.warn("🚫 Loại bỏ symbol không hợp lệ khỏi hàng đợi: {}", upperS);
            }
        }
        return symbols;
    }

    private void createNewKlineConnection(List<String> symbols) {
        SubscriptionOptions opt = new SubscriptionOptions();
        opt.setAutoReconnect(true);
        SubscriptionClient sc = SubscriptionClient.create(opt);
        List<String> low = new ArrayList<>();
        for (String s : symbols) low.add(s.toLowerCase());
        sc.subscribeAllCandlestickEvent(low, CandlestickInterval.ONE_MINUTE, (e) -> {
            String fullSymbol = e.getSymbol().toUpperCase();
            String shortS = e.getSymbol().toUpperCase().replace("USDT", "");
            KlineObjectOptimized optP = KlineObjectOptimized.newBuilder()
                    .setPriceOpen(e.getOpen().floatValue()).setPriceClose(e.getClose().floatValue())
                    .setMaxPrice(e.getHigh().floatValue()).setMinPrice(e.getLow().floatValue())
                    .setTotalUsdt(e.getQuoteAssetVolume().floatValue()).build();
            timeBuffer.computeIfAbsent(e.getStartTime(), k -> new ConcurrentHashMap<>()).put(shortS, optP);
            // Backup Price
            priceBuffer.put(fullSymbol, e.getClose().floatValue());
        }, null);
        klineClients.add(sc);
        globalSubscribedSymbols.addAll(symbols);
    }

    private void startIngestorLoops() {
        // --- LUỒNG 1: GHI NẾN (KLINE) ---
        new Thread(() -> {
            Thread.currentThread().setName("Kline-Ingestor-Loop");
            while (true) {
                try {
                    long now = System.currentTimeMillis();
                    long curMin = Utils.getMinute(now);
                    long lastMin = curMin - 60000;

                    // 1. Ghi dữ liệu phút hiện tại (Real-time update)
                    if (timeBuffer.containsKey(curMin)) {
                        DataManagerAerospikeFloatSim.writeMinuteBatch(curMin, new HashMap<>(timeBuffer.get(curMin)));
                    }

                    // 2. Xử lý chốt dữ liệu phút trước (Quét đuôi 15s đầu)
                    long second = (now / 1000) % 60;
                    if (second <= 15) {
                        if (timeBuffer.containsKey(lastMin)) {
                            DataManagerAerospikeFloatSim.writeMinuteBatch(lastMin, new HashMap<>(timeBuffer.get(lastMin)));
                        }
                    } else {
                        // 3. LOG FINALIZED: Ghi lần cuối và xóa khỏi RAM sau giây 15
                        if (timeBuffer.containsKey(lastMin)) {
                            DataManagerAerospikeFloatSim.writeMinuteBatch(lastMin, new HashMap<>(timeBuffer.get(lastMin)));
                            int finalSize = timeBuffer.get(lastMin).size();
                            timeBuffer.remove(lastMin);

                            // Log xác nhận đã chốt xong dữ liệu phút trước
                            LOG.info("✅ [KLINE] Finalized Minute: {} | Total Symbols: {}",
                                    Utils.normalizeDateYYYYMMDDHHmm(lastMin), finalSize);
                        }
                    }
                    Thread.sleep(50);
                } catch (Exception e) {
                    LOG.error("❌ Kline Ingestor Error: {}", e.getMessage());
                }
            }
        }).start();

        // --- LUỒNG 2: GHI GIÁ (PRICE) ---
        new Thread(() -> {
            Thread.currentThread().setName("Price-Ingestor-Loop");
            try { Thread.sleep(25); } catch (Exception e) {} // Chạy so le 25ms với luồng nến
            while (true) {
                try {
                    if (!priceBuffer.isEmpty()) {
                        // Gọi DataManager xử lý ghi tập trung
                        DataManagerAerospikeFloatSim.writePriceRealtime(new HashMap<>(priceBuffer));
                    }
                    Thread.sleep(50);
                } catch (Exception e) {
                    LOG.error("❌ Price Ingestor Error: {}", e.getMessage());
                }
            }
        }).start();
    }
    private void handleNewSymbolsDynamic(List<String> symbols) {
        if (klineClients.isEmpty()) return;
        SubscriptionClient last = klineClients.get(klineClients.size() - 1);
        List<String> low = new ArrayList<>();
        for (String s : symbols) low.add(s.toLowerCase());
        last.subscribeAllCandlestickEvent(low, CandlestickInterval.ONE_MINUTE, (e) -> processKlineEvent(e), null);
        repairService.execute(() -> repairBatch500(symbols, Utils.getMinute(System.currentTimeMillis() - 30 * Utils.TIME_HOUR), 1800));
    }

    private void processKlineEvent(CandlestickEvent e) {
        String shortS = e.getSymbol().toUpperCase().replace("USDT", "");
        KlineObjectOptimized optP = KlineObjectOptimized.newBuilder()
                .setPriceOpen(e.getOpen().floatValue()).setPriceClose(e.getClose().floatValue())
                .setMaxPrice(e.getHigh().floatValue()).setMinPrice(e.getLow().floatValue())
                .setTotalUsdt(e.getQuoteAssetVolume().floatValue()).build();
        timeBuffer.computeIfAbsent(e.getStartTime(), k -> new ConcurrentHashMap<>()).put(shortS, optP);
    }

    private void initNewSymbolConfig(String symbol) {
        try {
            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS, symbol, symbol);
            ClientSingleton.getInstance().syncRequestClient.changeInitialLeverage(symbol, Configs.LEVERAGE_ORDER);
        } catch (Exception e) {}
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