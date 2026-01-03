package com.binance.chuyennd.aerospike;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.BatchPolicy;

// Import Object Java cũ
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;

// --- QUAN TRỌNG: Import Proto MỚI (Float + No Time) ---
import com.binance.chuyennd.proto.MinuteDataFinalProto.MinuteDataFinal;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.io.File;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

public class DataManagerAerospikeFloatSim {
    public static final Logger LOG = LoggerFactory.getLogger(DataManagerAerospikeFloatSim.class);
    // --- CẤU HÌNH ---
    // Đổi sang Set mới đã tối ưu
    private static final String AEROSPIKE_SET_NAME_TICKER = "kline_1m_opt";
    private static final String AEROSPIKE_SET_NAME_PRICE = "price_realtime";
    private static final String AEROSPIKE_SET_NAME_FUNDINGFEE = "funding_data";

    private static volatile AerospikeClient client;
    private static final BatchPolicy batchPolicy = new BatchPolicy();
    private static final int BATCH_CHUNK_SIZE = 2000;
    private static final WritePolicy writePolicy = new WritePolicy();

    // Cấu hình đa luồng
    public static int threadCount = 2;
    public static ExecutorService executor = Executors.newFixedThreadPool(threadCount);

    static {
        // 🔥 GIÁ TRỊ 0: Lưu trữ vĩnh viễn, không bao giờ tự động xóa
        writePolicy.expiration = 0;
        writePolicy.recordExistsAction = RecordExistsAction.UPDATE;
    }

    public static AerospikeClient getClient() {
        if (client == null) {
            synchronized (DataManagerAerospikeFloatSim.class) {
                if (client == null) {
                    client = new AerospikeClient(Configs.AEROSPIKE_HOST, Configs.AEROSPIKE_PORT);
                }
            }
        }
        return client;
    }

    public static void writeMinuteBatch(long timestamp, Map<String, KlineObjectOptimized> newTickers) {
        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_TICKER, fmt.format(new Date(timestamp)));

            // Gộp dữ liệu cũ (nếu có) để bảo toàn nến của các mã khác
            Map<String, KlineObjectOptimized> finalMap = getExistingTickersMap(key);
            finalMap.putAll(newTickers);

            byte[] compressed = Snappy.compress(MinuteDataFinal.newBuilder().putAllTickers(finalMap).build().toByteArray());
            getClient().put(writePolicy, key, new Bin("data", compressed));
        } catch (Exception e) {
            LOG.error("❌ Error writing batch at {}: {}", timestamp, e.getMessage());
        }
    }
    public static void writePriceRealtime(Map<String, Double> priceMap) {
        if (priceMap == null || priceMap.isEmpty()) return;
        try {
            long now = System.currentTimeMillis();
            for (Map.Entry<String, Double> entry : priceMap.entrySet()) {
                // Sử dụng UPPERCASE cho symbol để đồng bộ
                String symbol = entry.getKey().toUpperCase();
                Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_PRICE, symbol);

                // Ghi giá và timestamp cập nhật
                getClient().put(null, key,
                        new Bin("price", entry.getValue()),
                        new Bin("ts", now)
                );
            }
        } catch (Exception e) {
            LOG.error("❌ Error writing Price Realtime: {}", e.getMessage());
        }
    }

    // =========================================================================
    // LOGIC FUNDING (Tối ưu Snappy Compression để lưu 5 năm)
    // =========================================================================

    /**
     * Ghi Funding Map sử dụng Snappy để nén, phá bỏ giới hạn 2000 kỳ
     */
    public static void writeFundingMap(String symbol, Map<Long, Float> fundingRates) {
        try {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_FUNDINGFEE, symbol);

            // 1. Lấy dữ liệu cũ
            Map<Long, Double> existingMap = getFundingMap(symbol);

            // 2. Gộp dữ liệu (Dùng TreeMap để luôn sắp xếp theo thời gian)
            TreeMap<Long, Float> finalMap = new TreeMap<>();
            existingMap.forEach((k, v) -> finalMap.put(k, v.floatValue()));
            fundingRates.forEach(finalMap::put);

            // 3. Serialize Map thành byte[] và nén bằng Snappy để tránh lỗi "Record too big"
            // Chúng ta lưu Map dưới dạng Map đơn giản để Snappy xử lý hiệu quả
            byte[] rawBytes = Utils.gson.toJson(finalMap).getBytes("UTF-8");
            byte[] compressedBytes = Snappy.compress(rawBytes);

            // 4. Ghi vào bin "f_data" dạng blob thay vì CDT Map trực tiếp
            getClient().put(writePolicy, key, new Bin("f_data", compressedBytes));

            if (finalMap.size() % 100 == 0) {
                LOG.info("💾 Saved Funding {}: {} records (Compressed)", symbol, finalMap.size());
            }
        } catch (Exception e) {
            LOG.error("❌ Error writing Funding for {}: {}", symbol, e.getMessage());
        }
    }

    /**
     * Giải nén và đọc Map Funding
     */
    public static Map<Long, Double> getFundingMap(String symbol) {
        Map<Long, Double> results = new HashMap<>();
        try {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_FUNDINGFEE, symbol);
            Record record = getClient().get(null, key);
            if (record != null) {
                byte[] compressedData = (byte[]) record.getValue("f_data");
                if (compressedData != null) {
                    // Giải nén Snappy
                    String json = new String(Snappy.uncompress(compressedData), "UTF-8");
                    Map<String, Double> rawMap = Utils.gson.fromJson(json, Map.class);

                    // Convert Key từ String (JSON) về Long
                    rawMap.forEach((k, v) -> results.put(Long.parseLong(k), v));
                }
            }
        } catch (Exception e) {
            // Trường hợp dữ liệu cũ vẫn là CDT Map (f_map)
            try {
                Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_FUNDINGFEE, symbol);
                Record record = getClient().get(null, key);
                if (record != null && record.getMap("f_map") != null) {
                    record.getMap("f_map").forEach((k, v) -> results.put((Long) k, ((Number) v).doubleValue()));
                }
            } catch (Exception ignored) {}
        }
        return results;
    }
    public static void migrateHistoricalFunding(String folderPath) {
        File folder = new File(folderPath);
        if (!folder.exists() || !folder.isDirectory()) {
            LOG.error("❌ Thư mục funding không tồn tại: {}", folderPath);
            return;
        }

        File[] files = folder.listFiles();
        if (files == null) return;

        LOG.info("🚀 Bắt đầu Migrate Funding Fee từ {} tệp tin...", files.length);

        for (File file : files) {
            try {
                String symbol = file.getName(); // Tên file chính là symbol

                // Đọc đối tượng TreeMap từ file bằng Storage (giống logic FundingFeeManager)
                TreeMap<Long, com.binance.client.model.market.FundingRate> time2RateFunding =
                        (TreeMap<Long, com.binance.client.model.market.FundingRate>) com.binance.chuyennd.utils.Storage.readObjectFromFile(file.getAbsolutePath());

                if (time2RateFunding != null && !time2RateFunding.isEmpty()) {
                    Map<Long, Float> fundingMapForAS = new HashMap<>();

                    // Chuyển đổi từ Object FundingRate sang Double để lưu vào AS
                    time2RateFunding.forEach((time, fundingObj) -> {
                        if (fundingObj != null && fundingObj.getFundingRate() != null) {
                            // Ép kiểu về Float để giảm kích thước record ngay từ lúc migrate
                            fundingMapForAS.put(time, fundingObj.getFundingRate().floatValue());
                        }
                    });
                    // Ghi vào Aerospike (Hàm này đã có logic gộp và lưu vĩnh viễn)
                    writeFundingMap(symbol, fundingMapForAS);
                    LOG.info("✅ Migrated {}: {} records", symbol, fundingMapForAS.size());
                }
            } catch (Exception e) {
                LOG.error("❌ Lỗi migrate file {}: {}", file.getName(), e.getMessage());
            }
        }
        LOG.info("🏁 Hoàn tất Migration Funding Rate.");
    }

    // =========================================================================
    // LOGIC KIỂM TRA DỮ LIỆU (REPAIR)
    // =========================================================================

    public static boolean isSymbolMissingInPoints(String shortSymbol, long start, int limit) {
        SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
        long[] points = {start, start + (limit/2)*60000L, start + (limit-1)*60000L};
        for (long p : points) {
            if (p > System.currentTimeMillis()) continue;
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_TICKER, fmt.format(new Date(p)));
            Map<String, KlineObjectOptimized> map = getExistingTickersMap(key);
            if (map.isEmpty() || !map.containsKey(shortSymbol)) return true;
        }
        return false;
    }
    public static Map<String, KlineObjectOptimized> getExistingTickersMap(Key key) {
        Map<String, KlineObjectOptimized> map = new HashMap<>();
        try {
            Record record = getClient().get(null, key);
            if (record != null) {
                byte[] data = (byte[]) record.getValue("data");
                if (data != null) {
                    map.putAll(MinuteDataFinal.parseFrom(Snappy.uncompress(data)).getTickersMap());
                }
            }
        } catch (Exception e) {}
        return map;
    }


    /**
     * Đọc dữ liệu toàn bộ thị trường trong 1 ngày (1440 phút)
     */
    public static TreeMap<Long, Map<String, KlineObjectSimple>> readDataFromAerospike1M(long startTime) {
        TreeMap<Long, Map<String, KlineObjectSimple>> results = new TreeMap<>();
        int totalRecords = 1440;

        // Tạo Key và Timestamp
        long[] allTimestamps = new long[totalRecords];
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(startTime);
        cal.set(Calendar.HOUR_OF_DAY, 7);
        cal.set(Calendar.MINUTE, 0);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);

        for (int i = 0; i < totalRecords; i++) {
            allTimestamps[i] = cal.getTimeInMillis();
            cal.add(Calendar.MINUTE, 1);
        }

        List<Future<Map<Long, Map<String, KlineObjectSimple>>>> futures = new ArrayList<>();
        int chunkSize = (totalRecords + threadCount - 1) / threadCount;

        for (int i = 0; i < threadCount; i++) {
            final int startIdx = i * chunkSize;
            final int endIdx = Math.min(startIdx + chunkSize, totalRecords);
            if (startIdx >= endIdx) break;

            futures.add(executor.submit(() -> {
                // --- FIX THREAD SAFETY: Tạo SimpleDateFormat riêng cho từng luồng ---
                SimpleDateFormat localKeyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");

                Map<Long, Map<String, KlineObjectSimple>> chunkResult = new HashMap<>();
                try {
                    // Tạo Keys cho chunk này
                    Key[] chunkKeys = new Key[endIdx - startIdx];
                    long[] chunkTimestamps = Arrays.copyOfRange(allTimestamps, startIdx, endIdx);

                    for (int k = 0; k < chunkKeys.length; k++) {
                        String keyString = localKeyFormat.format(new Date(chunkTimestamps[k]));
                        chunkKeys[k] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_TICKER, keyString);
                    }

                    // Batch Read
                    Record[] records = getClient().get(batchPolicy, chunkKeys);

                    for (int j = 0; j < records.length; j++) {
                        Record record = records[j];
                        if (record == null) continue;

                        // Lấy timestamp từ mảng (Vì trong Data không còn lưu timestamp nữa)
                        long minuteTimestamp = chunkTimestamps[j];

                        byte[] snappyCompressedBytes = (byte[]) record.getValue("data");
                        if (snappyCompressedBytes != null) {
                            byte[] protoAsBytes = Snappy.uncompress(snappyCompressedBytes);

                            // --- DÙNG PROTO MỚI ---
                            MinuteDataFinal protoData = MinuteDataFinal.parseFrom(protoAsBytes);

                            // Convert và truyền timestamp vào
                            Map<String, KlineObjectSimple> javaMap = convertProtoMapToJavaMap(protoData.getTickersMap(), minuteTimestamp);
                            chunkResult.put(minuteTimestamp, javaMap);
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
                return chunkResult;
            }));
        }

        // Tổng hợp kết quả
        for (Future<Map<Long, Map<String, KlineObjectSimple>>> future : futures) {
            try {
                results.putAll(future.get());
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return results;
    }

    /**
     * Đọc dữ liệu lịch sử của 1 Symbol cụ thể
     */
    public static TreeMap<Long, KlineObjectSimple> readDataForPeriod(String symbol, long startTime, long endTime) {
        TreeMap<Long, KlineObjectSimple> results = new TreeMap<>();

        // Xử lý Symbol: Vì DB lưu "BTC" mà input là "BTCUSDT", ta cần cắt đuôi
        final String shortSymbol = symbol.endsWith("USDT") ? symbol.substring(0, symbol.length() - 4) : symbol;

        int minutesToRead = (int) ((endTime - startTime) / Utils.TIME_MINUTE) + 1;
        if (minutesToRead <= 0) return results;

        List<Long> allTimestamps = new ArrayList<>(minutesToRead);
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(startTime);
        for (int i = 0; i < minutesToRead; i++) {
            allTimestamps.add(cal.getTimeInMillis());
            cal.add(Calendar.MINUTE, 1);
        }

        try {
            // Chia nhỏ request (Chunking)
            for (int i = 0; i < allTimestamps.size(); i += BATCH_CHUNK_SIZE) {
                int endIndex = Math.min(i + BATCH_CHUNK_SIZE, allTimestamps.size());
                List<Long> timestampChunk = allTimestamps.subList(i, endIndex);

                // Tạo Keys (Dùng Local Formatter)
                SimpleDateFormat localKeyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");
                Key[] keyChunk = new Key[timestampChunk.size()];
                for (int k = 0; k < timestampChunk.size(); k++) {
                    String keyString = localKeyFormat.format(new Date(timestampChunk.get(k)));
                    keyChunk[k] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_TICKER, keyString);
                }

                Record[] records = getClient().get(batchPolicy, keyChunk);

                for (int j = 0; j < records.length; j++) {
                    Record record = records[j];
                    if (record == null) continue;

                    long minuteTimestamp = timestampChunk.get(j);
                    byte[] snappyCompressedBytes = (byte[]) record.getValue("data");

                    if (snappyCompressedBytes != null && snappyCompressedBytes.length > 0) {
                        byte[] protoAsBytes = Snappy.uncompress(snappyCompressedBytes);

                        // --- DÙNG PROTO MỚI ---
                        MinuteDataFinal protoData = MinuteDataFinal.parseFrom(protoAsBytes);
                        Map<String, KlineObjectOptimized> protoMap = protoData.getTickersMap();

                        // Tìm theo Short Symbol (ví dụ "BTC")
                        if (protoMap.containsKey(shortSymbol)) {
                            KlineObjectSimple javaKline = convertProtoToKline(protoMap.get(shortSymbol), minuteTimestamp);
                            results.put(minuteTimestamp, javaKline);
                        }
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return results;
    }

    // =========================================================================
    // LOGIC CONVERT MỚI (FLOAT -> DOUBLE, APPEND USDT, INJECT TIME)
    // =========================================================================

    public static Map<String, KlineObjectSimple> convertProtoMapToJavaMap(Map<String, KlineObjectOptimized> protoMap, long timestamp) {
        Map<String, KlineObjectSimple> javaMap = new HashMap<>(protoMap.size());

        for (Map.Entry<String, KlineObjectOptimized> entry : protoMap.entrySet()) {
            String shortSymbol = entry.getKey(); // Đang là "BTC"
            KlineObjectOptimized protoTicker = entry.getValue();

            // 1. Khôi phục tên đầy đủ: BTC -> BTCUSDT

            String fullSymbol = shortSymbol;

            // 2. Convert Object
            javaMap.put(fullSymbol, convertProtoToKline(protoTicker, timestamp));
        }
        return javaMap;
    }

    private static KlineObjectSimple convertProtoToKline(KlineObjectOptimized protoTicker, long timestamp) {
        KlineObjectSimple javaTicker = new KlineObjectSimple();

        // 1. INJECT TIMESTAMP TỪ BÊN NGOÀI VÀO (Vì trong DB không còn lưu nữa)
        // Ép kiểu về double theo đúng định nghĩa class cũ của bạn
        javaTicker.startTime = (double) timestamp;

        // 2. ÉP KIỂU FLOAT (DB) -> DOUBLE (JAVA)
        javaTicker.priceOpen = (double) protoTicker.getPriceOpen();
        javaTicker.maxPrice = (double) protoTicker.getMaxPrice();
        javaTicker.minPrice = (double) protoTicker.getMinPrice();
        javaTicker.priceClose = (double) protoTicker.getPriceClose();
        javaTicker.totalUsdt = (double) protoTicker.getTotalUsdt();

        return javaTicker;
    }

    public static void closeConnection() {
        if (client != null) {
            client.close();
        }
    }

    public static void main(String[] args) throws ParseException {
//        Long startTime = Utils.sdfFile.parse("20260102").getTime() + 7 * Utils.TIME_HOUR;
//        System.out.println(DataManagerAerospikeFloatSim.readDataFromAerospike1M(startTime).size());
        DataManagerAerospikeFloatSim.migrateHistoricalFunding("../storage/funding_fee/");
    }
}