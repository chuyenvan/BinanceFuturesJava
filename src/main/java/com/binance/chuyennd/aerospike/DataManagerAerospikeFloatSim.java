package com.binance.chuyennd.aerospike;

import com.aerospike.client.*;
import com.aerospike.client.Record;
import com.aerospike.client.cdt.MapOperation;
import com.aerospike.client.cdt.MapPolicy;
import com.aerospike.client.policy.BatchPolicy;

// Import Object Java cũ
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.ScanPolicy;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
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
import java.util.concurrent.ConcurrentHashMap;
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

    // 1. CẤU HÌNH SET NAME VÀ KEY
    private static final String AEROSPIKE_SET_NAME_MAPPER = "symbol_mapper"; // Set name mới
    private static final String MAPPER_KEY_GLOBAL = "global_id_map";         // Key chứa Map
    private static final String MAPPER_BIN_NAME = "data";                    // Tên Bin chứa Map
    private static final String AEROSPIKE_SET_NAME_AI_PRED_1M = "ai_pred_1m";
    // 🔥 SET NAME MỚI CHO AI PREDICT
    private static final String AEROSPIKE_SET_NAME_DCA_PRED = "dca_pred_1m";
    private static volatile AerospikeClient client;
    private static final BatchPolicy batchPolicy = new BatchPolicy();
    private static final int BATCH_CHUNK_SIZE = 2000;
    private static final WritePolicy writePolicy = new WritePolicy();

    // Cấu hình đa luồng
    public static int threadCount = 2;
    public static ExecutorService executor = Executors.newFixedThreadPool(threadCount);

    static {
        // 🔥 GIÁ TRỊ 0: Lưu trữ vĩnh viễn, không bao giờ tự động xóa
        writePolicy.sendKey = true; // Thêm dòng này
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
    /**
     * Hàm lấy toàn bộ Mapper (String -> Short) từ Aerospike khi khởi động
     */
    public static Map<String, Short> loadSymbolMapper() {
        Map<String, Short> result = new ConcurrentHashMap<>();
        try {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_MAPPER, MAPPER_KEY_GLOBAL);
            Record record = getClient().get(null, key);

            if (record != null) {
                // Lấy dữ liệu Map từ Aerospike
                Map<String, Long> rawMap = (Map<String, Long>) record.getMap(MAPPER_BIN_NAME);

                if (rawMap != null) {
                    // Convert từ Long (Aerospike) sang Short (Java)
                    for (Map.Entry<String, Long> entry : rawMap.entrySet()) {
                        result.put(entry.getKey(), entry.getValue().shortValue());
                    }
                    LOG.info("✅ Loaded Symbol Mapper: {} symbols from Aerospike.", result.size());
                }
            }
        } catch (Exception e) {
            LOG.error("❌ Error loading Symbol Mapper: {}", e.getMessage());
        }
        return result;
    }

    /**
     * Hàm ghi 1 cặp Symbol - ID mới vào Aerospike (Append vào Map)
     * Dùng MapOperation để chỉ ghi thêm, không cần ghi đè toàn bộ record.
     */
    public static void saveSymbolMapping(String symbol, short id) {
        try {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_MAPPER, MAPPER_KEY_GLOBAL);

            // MapPolicy.Default: Tạo map nếu chưa tồn tại
            // MapOperation.put: Thêm key-value mới vào Map
            getClient().operate(writePolicy, key,
                    MapOperation.put(MapPolicy.Default, MAPPER_BIN_NAME, Value.get(symbol), Value.get(id))
            );

            // LOG.info("💾 Saved Mapping: {} -> {}", symbol, id);
        } catch (Exception e) {
            LOG.error("❌ Error saving symbol mapping {} -> {}: {}", symbol, id, e.getMessage());
        }
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

    /**
     * Lấy toàn bộ giá realtime của tất cả các mã đang có trong Aerospike
     *
     * @return Map chứa Symbol -> Giá (Double)
     */
    public static Map<String, Double> getAllPriceRealtimeLegacy(Set<String> expectedSymbols) {
        Map<String, Double> results = new HashMap<>();
        // 1. Tạo bản đồ: Digest -> Symbol để tra cứu nhanh
        Map<String, String> digestToSymbol = new HashMap<>();
        for (String s : expectedSymbols) {
            String upperS = s.toUpperCase();
            Key k = new Key(Configs.AEROSPIKE_NAMESPACE, "price_realtime", upperS);
            // Digest là mảng byte định danh duy nhất của Key
            digestToSymbol.put(Base64.getEncoder().encodeToString(k.digest), upperS);
        }

        try {
            ScanPolicy scanPolicy = new ScanPolicy();
            scanPolicy.concurrentNodes = true;
            scanPolicy.includeBinData = true;

            getClient().scanAll(scanPolicy, Configs.AEROSPIKE_NAMESPACE, "price_realtime", (key, record) -> {
                // Lấy Digest của bản ghi hiện tại
                String currentDigest = Base64.getEncoder().encodeToString(key.digest);
                String symbol = digestToSymbol.get(currentDigest);

                if (symbol != null) {
                    results.put(symbol, record.getDouble("price"));
                }
            }, "price");
        } catch (Exception e) {
            LOG.error("❌ Error Legacy Scan: {}", e.getMessage());
        }
        return results;
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
    public static TreeMap<Long, Double> getFundingMap(String symbol) {
        TreeMap<Long, Double> results = new TreeMap<>();
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
            } catch (Exception ignored) {
            }
        }
        return results;
    }

    /**
     * Quét toàn bộ dữ liệu Funding từ Aerospike
     *
     * @return Map<Symbol, TreeMap < Timestamp, Rate>>
     */
    public static Map<String, TreeMap<Long, Double>> getAllFundingMap() {
        Map<String, TreeMap<Long, Double>> allResults = new HashMap<>();
        try {
            ScanPolicy scanPolicy = new ScanPolicy();
            scanPolicy.concurrentNodes = true; // Quét song song trên các node
            scanPolicy.includeBinData = true;

            // Chỉ định rõ bin "f_data" (nén Snappy) và "f_map" (dữ liệu cũ) để tối ưu
            getClient().scanAll(scanPolicy, Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_FUNDINGFEE, (key, record) -> {
                String symbol = (key.userKey != null) ? key.userKey.toString() : null;
                if (symbol == null) return;

                TreeMap<Long, Double> symbolFunding = new TreeMap<>();
                try {
                    // Ưu tiên xử lý dữ liệu mới (Snappy Compressed)
                    byte[] compressedData = (byte[]) record.getValue("f_data");
                    if (compressedData != null) {
                        String json = new String(Snappy.uncompress(compressedData), "UTF-8");
                        Map<String, Double> rawMap = Utils.gson.fromJson(json, Map.class);
                        rawMap.forEach((k, v) -> symbolFunding.put(Long.parseLong(k), v));
                    } else {
                        // Xử lý dữ liệu cũ (CDT Map) nếu không có f_data
                        Map<?, ?> fMap = record.getMap("f_map");
                        if (fMap != null) {
                            fMap.forEach((k, v) -> symbolFunding.put((Long) k, ((Number) v).doubleValue()));
                        }
                    }

                    if (!symbolFunding.isEmpty()) {
                        allResults.put(symbol, symbolFunding);
                    }
                } catch (Exception e) {
                    LOG.error("❌ Lỗi giải mã Funding cho {}: {}", symbol, e.getMessage());
                }
            }, "f_data", "f_map");

        } catch (Exception e) {
            LOG.error("❌ Error Scanning all Funding data: {}", e.getMessage());
        }
        return allResults;
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
        long[] points = {start, start + (limit / 2) * 60000L, start + (limit - 1) * 60000L};
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
        } catch (Exception e) {
        }
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
     * Đọc dữ liệu từ Aerospike theo mốc thời gian và số lượng phút tùy chỉnh.
     * Không chuẩn hóa startTime (lấy chính xác mốc truyền vào).
     * * @param startTime Mốc thời gian bắt đầu (miliseconds)
     *
     * @param totalMinutes Số lượng phút (records) cần lấy
     * @return TreeMap<Long, Map < String, KlineObjectSimple>>
     */
    public static TreeMap<Long, Map<String, KlineObjectSimple>> readDataFromAerospikeCustom(long startTime, int totalMinutes) {
        TreeMap<Long, Map<String, KlineObjectSimple>> results = new TreeMap<>();

        // 1. Tạo danh sách Timestamps chính xác từ startTime
        long[] allTimestamps = new long[totalMinutes];
        for (int i = 0; i < totalMinutes; i++) {
            allTimestamps[i] = startTime + (i * Utils.TIME_MINUTE); // Nhảy từng phút từ mốc truyền vào
        }

        List<Future<Map<Long, Map<String, KlineObjectSimple>>>> futures = new ArrayList<>();
        int chunkSize = (totalMinutes + threadCount - 1) / threadCount;

        // 2. Chia đa luồng để thực hiện Batch Read
        for (int i = 0; i < threadCount; i++) {
            final int startIdx = i * chunkSize;
            final int endIdx = Math.min(startIdx + chunkSize, totalMinutes);
            if (startIdx >= endIdx) break;

            futures.add(executor.submit(() -> {
                // Đảm bảo thread-safety cho format ngày
                SimpleDateFormat localKeyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");
                Map<Long, Map<String, KlineObjectSimple>> chunkResult = new HashMap<>();

                try {
                    // Tạo mảng Keys cho chunk này
                    Key[] chunkKeys = new Key[endIdx - startIdx];
                    long[] chunkTimestamps = Arrays.copyOfRange(allTimestamps, startIdx, endIdx);

                    for (int k = 0; k < chunkKeys.length; k++) {
                        String keyString = localKeyFormat.format(new Date(chunkTimestamps[k]));
                        chunkKeys[k] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_TICKER, keyString);
                    }

                    // Batch Read từ Aerospike
                    Record[] records = getClient().get(batchPolicy, chunkKeys);

                    for (int j = 0; j < records.length; j++) {
                        Record record = records[j];
                        if (record == null) continue;

                        long minuteTimestamp = chunkTimestamps[j];
                        byte[] snappyCompressedBytes = (byte[]) record.getValue("data");

                        if (snappyCompressedBytes != null) {
                            // Giải nén và parse Proto
                            byte[] protoAsBytes = Snappy.uncompress(snappyCompressedBytes);
                            MinuteDataFinal protoData = MinuteDataFinal.parseFrom(protoAsBytes);

                            // Convert sang Object Java và inject lại timestamp
                            Map<String, KlineObjectSimple> javaMap = convertProtoMapToJavaMap(protoData.getTickersMap(), minuteTimestamp);
                            chunkResult.put(minuteTimestamp, javaMap);
                        }
                    }
                } catch (Exception e) {
                    LOG.error("❌ Lỗi trong luồng đọc Batch: {}", e.getMessage());
                }
                return chunkResult;
            }));
        }

        // 3. Tổng hợp kết quả từ các Future
        for (Future<Map<Long, Map<String, KlineObjectSimple>>> future : futures) {
            try {
                results.putAll(future.get());
            } catch (Exception e) {
                LOG.error("❌ Lỗi khi lấy kết quả từ Future: {}", e.getMessage());
            }
        }

        return results;
    }

    /**
     * Đọc dữ liệu nến 1m từ Aerospike và trả về Map theo Symbol.
     * Không chuẩn hóa startTime (lấy chính xác từ mốc truyền vào).
     * * @param startTime Mốc thời gian bắt đầu (ms)
     *
     * @param minutesToRead Số lượng phút muốn đọc (ví dụ: 1440 cho 1 ngày)
     * @return Map<Symbol, List < KlineObjectSimple>>
     */
    public static Map<String, List<KlineObjectSimple>> readDataForSymbols(long startTime, int minutesToRead) {
        // 1. Chuẩn bị danh sách Timestamps từ startTime chính xác
        long[] allTimestamps = new long[minutesToRead];
        for (int i = 0; i < minutesToRead; i++) {
            allTimestamps[i] = startTime + (i * 60000L);
        }
        LOG.info("Read ticker from Aerospike: startTime={} | minutes={}", Utils.normalizeDateYYYYMMDDHHmm(startTime), minutesToRead);
        // Kết quả trung gian (Thời gian -> Map các Symbol)
        TreeMap<Long, Map<String, KlineObjectSimple>> timeToTickers = new TreeMap<>();
        List<Future<Map<Long, Map<String, KlineObjectSimple>>>> futures = new ArrayList<>();
        int chunkSize = (minutesToRead + threadCount - 1) / threadCount;

        // 2. Chia đa luồng để đọc Batch từ Aerospike
        for (int i = 0; i < threadCount; i++) {
            final int startIdx = i * chunkSize;
            final int endIdx = Math.min(startIdx + chunkSize, minutesToRead);
            if (startIdx >= endIdx) break;

            futures.add(executor.submit(() -> {
                SimpleDateFormat localKeyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");
                Map<Long, Map<String, KlineObjectSimple>> chunkResult = new HashMap<>();

                try {
                    Key[] chunkKeys = new Key[endIdx - startIdx];
                    long[] chunkTimestamps = Arrays.copyOfRange(allTimestamps, startIdx, endIdx);

                    for (int k = 0; k < chunkKeys.length; k++) {
                        String keyString = localKeyFormat.format(new Date(chunkTimestamps[k]));
                        chunkKeys[k] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_TICKER, keyString);
                    }

                    // Batch Read tối ưu
                    Record[] records = getClient().get(batchPolicy, chunkKeys);

                    for (int j = 0; j < records.length; j++) {
                        Record record = records[j];
                        if (record == null) continue;

                        long minuteTimestamp = chunkTimestamps[j];
                        byte[] snappyCompressedBytes = (byte[]) record.getValue("data");

                        if (snappyCompressedBytes != null) {
                            byte[] protoAsBytes = Snappy.uncompress(snappyCompressedBytes);
                            MinuteDataFinal protoData = MinuteDataFinal.parseFrom(protoAsBytes);

                            // Sử dụng hàm convert hiện tại của bạn
                            Map<String, KlineObjectSimple> javaMap = convertProtoMapToJavaMap(protoData.getTickersMap(), minuteTimestamp);
                            chunkResult.put(minuteTimestamp, javaMap);
                        }
                    }
                } catch (Exception e) {
                    LOG.error("❌ Error in Batch Read Thread: {}", e.getMessage());
                }
                return chunkResult;
            }));
        }

        // 3. Tổng hợp kết quả từ các Thread
        for (Future<Map<Long, Map<String, KlineObjectSimple>>> future : futures) {
            try {
                timeToTickers.putAll(future.get());
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        // 4. CHUYỂN ĐỔI CẤU TRÚC: Time-Major -> Symbol-Major
        Map<String, List<KlineObjectSimple>> symbolToKlines = new HashMap<>();

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : timeToTickers.entrySet()) {
            Map<String, KlineObjectSimple> tickersAtTime = entry.getValue();

            for (Map.Entry<String, KlineObjectSimple> tickerEntry : tickersAtTime.entrySet()) {
                String symbolInDb = tickerEntry.getKey();

                // 🔥 Bổ sung lại "USDT" nếu symbol trong DB đang bị cắt đuôi (ví dụ "BTC" -> "BTCUSDT")
                String fullSymbol = symbolInDb.endsWith("USDT") ? symbolInDb : symbolInDb + "USDT";

                KlineObjectSimple kline = tickerEntry.getValue();
                symbolToKlines.computeIfAbsent(fullSymbol, k -> new ArrayList<>()).add(kline);
            }
        }

        return symbolToKlines;
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
            // 🔥 Bổ sung lại "USDT" nếu symbol trong DB đang bị cắt đuôi (ví dụ "BTC" -> "BTCUSDT")
            String fullSymbol = shortSymbol.endsWith("USDT") ? shortSymbol : shortSymbol + "USDT";
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

    public static void debugKeys() {
        try (AerospikeClient client = new AerospikeClient("103.157.218.242", 3222)) {
            ScanPolicy sp = new ScanPolicy();
            sp.maxRecords = 10;
            client.scanAll(sp, "ticker", "kline_1m_opt", (key, rec) -> {
                System.out.println("🔑 Key thực tế trong DB: " + key.userKey);
            });
        }
    }
// =========================================================================
    // 🔥🔥 AI PREDICTION DATA: GHI VÀ ĐỌC THEO PHÚT (GIỐNG TICKER 1M) 🔥🔥
    // =========================================================================

    /**
     * 1. GHI DỮ LIỆU (WRITE BY MINUTE)
     * Ghi 1 record cho mỗi phút. Key = yyyyMMdd-HHmm
     */
    public static void saveAiPrediction1M(AiPredictionData data) {
        if (data == null) return;
        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            String keyString = fmt.format(new Date(data.timestamp));
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_AI_PRED_1M, keyString);

            // Serialize JSON -> Bytes -> Snappy Compress
            String json = Utils.gson.toJson(data);
            byte[] rawBytes = json.getBytes("UTF-8");
            byte[] compressed = Snappy.compress(rawBytes);

            // Ghi vào bin "data"
            getClient().put(writePolicy, key, new Bin("data", compressed));

        } catch (Exception e) {
            LOG.error("❌ Error saving AI Pred 1M at {}: {}", data.timestamp, e.getMessage());
        }
    }

    /**
     * Helper: Ghi danh sách lớn (Batch Write) bằng đa luồng để tăng tốc độ
     */
    public static void saveListAiPrediction1M(TreeMap<Long, AiPredictionData> dataMap) {
        if (dataMap == null || dataMap.isEmpty()) return;
        LOG.info("🚀 Starting batch save for {} AI records...", dataMap.size());

        dataMap.values().parallelStream().forEach(data -> {
            saveAiPrediction1M(data);
        });

        LOG.info("✅ Done batch save AI records.");
    }

    /**
     * 2. LẤY DỮ LIỆU THEO PHÚT (READ SINGLE MINUTE)
     */
    public static AiPredictionData getAiPredictionAtTime(long timestamp) {
        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            String keyString = fmt.format(new Date(timestamp));
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_AI_PRED_1M, keyString);

            Record record = getClient().get(null, key);
            if (record != null) {
                return parseAiRecord(record);
            }
        } catch (Exception e) {
            LOG.error("❌ Error getting AI Pred at {}: {}", timestamp, e.getMessage());
        }
        return null;
    }

    /**
     * 3. LẤY DỮ LIỆU THEO THÁNG (READ MONTH - BATCH READ)
     * Logic giống hệt readDataFromAerospike1M của Ticker: Tạo key cho từng phút trong tháng -> Batch Read
     * @param monthStr format "yyyyMM" (Ví dụ: "202401")
     */
    public static TreeMap<Long, AiPredictionData> getAiPredictionsForMonth(String monthStr) {
        TreeMap<Long, AiPredictionData> results = new TreeMap<>();
        try {
            SimpleDateFormat sdfMonth = new SimpleDateFormat("yyyyMM");
            Date date = sdfMonth.parse(monthStr);
            Calendar cal = Calendar.getInstance();
            cal.setTime(date);

            // Xác định thời gian bắt đầu và kết thúc của tháng
            long startTime = cal.getTimeInMillis();
            cal.add(Calendar.MONTH, 1);
            long endTime = cal.getTimeInMillis();

            // Tính tổng số phút (records) trong tháng
            int totalMinutes = (int) ((endTime - startTime) / (60 * 1000));
            LOG.info("📥 Reading AI Data for month {} ({} records)...", monthStr, totalMinutes);

            // Tận dụng hàm đọc Batch tùy chỉnh
            results = readAiBatchCustom(startTime, totalMinutes);

        } catch (Exception e) {
            LOG.error("❌ Error reading AI Month {}: {}", monthStr, e.getMessage());
        }
        return results;
    }

    /**
     * Helper: Đọc Batch AI Data theo range thời gian (Đa luồng)
     */
    public static TreeMap<Long, AiPredictionData> readAiBatchCustom(long startTime, int totalMinutes) {
        TreeMap<Long, AiPredictionData> results = new TreeMap<>();

        // 1. Tạo danh sách Timestamps
        long[] allTimestamps = new long[totalMinutes];
        for (int i = 0; i < totalMinutes; i++) {
            allTimestamps[i] = startTime + (i * 60000L);
        }

        List<Future<Map<Long, AiPredictionData>>> futures = new ArrayList<>();
        int chunkSize = (totalMinutes + threadCount - 1) / threadCount;

        // 2. Chia đa luồng Batch Read
        for (int i = 0; i < threadCount; i++) {
            final int startIdx = i * chunkSize;
            final int endIdx = Math.min(startIdx + chunkSize, totalMinutes);
            if (startIdx >= endIdx) break;

            futures.add(executor.submit(() -> {
                SimpleDateFormat localKeyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");
                Map<Long, AiPredictionData> chunkResult = new HashMap<>();
                try {
                    Key[] chunkKeys = new Key[endIdx - startIdx];
                    long[] chunkTimestamps = Arrays.copyOfRange(allTimestamps, startIdx, endIdx);

                    for (int k = 0; k < chunkKeys.length; k++) {
                        String keyString = localKeyFormat.format(new Date(chunkTimestamps[k]));
                        chunkKeys[k] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_AI_PRED_1M, keyString);
                    }

                    // Batch Read
                    Record[] records = getClient().get(batchPolicy, chunkKeys);

                    for (int j = 0; j < records.length; j++) {
                        Record record = records[j];
                        if (record != null) {
                            AiPredictionData data = parseAiRecord(record);
                            if (data != null) {
                                chunkResult.put(data.timestamp, data);
                            }
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
                return chunkResult;
            }));
        }

        // 3. Tổng hợp kết quả
        for (Future<Map<Long, AiPredictionData>> future : futures) {
            try {
                results.putAll(future.get());
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return results;
    }

    private static AiPredictionData parseAiRecord(Record record) {
        try {
            byte[] compressedData = (byte[]) record.getValue("data");
            if (compressedData != null) {
                byte[] uncompressed = Snappy.uncompress(compressedData);
                String json = new String(uncompressed, "UTF-8");
                return Utils.gson.fromJson(json, AiPredictionData.class);
            }
        } catch (Exception e) {
        }
        return null;
    }

    // =========================================================================
    // 2. DCA PREDICTIONS (WRITE PER MINUTE)
    // =========================================================================

    /**
     * Ghi kết quả dự báo của TOÀN BỘ thị trường trong 1 phút vào 1 record.
     * Key: yyyyMMdd-HHmm
     * Value: JSON Compressed (Map<Short, float[]>)
     */
    public static void saveDcaPredictions1M(long timestamp, Map<Short, float[]> predictions) {
        if (predictions == null || predictions.isEmpty()) return;
        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            String keyString = fmt.format(new Date(timestamp));
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_DCA_PRED, keyString);

            // Serialize: Map -> JSON -> Bytes -> Snappy
            // Dùng JSON thay vì Proto vì Map<Short, float[]> linh hoạt, Gson xử lý nhanh
            String json = Utils.gson.toJson(predictions);
            byte[] rawBytes = json.getBytes("UTF-8");
            byte[] compressed = Snappy.compress(rawBytes);

            getClient().put(writePolicy, key, new Bin("data", compressed));

        } catch (Exception e) {
            LOG.error("❌ Error saving DCA Pred at {}: {}", timestamp, e.getMessage());
        }
    }
    /**
     * 🔥 MỚI: Đọc dự báo DCA tại 1 thời điểm cụ thể
     */
    public static Map<Short, float[]> getDcaPredictionAtTime(long timestamp) {
        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            String keyString = fmt.format(new Date(timestamp));
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_DCA_PRED, keyString);

            Record record = getClient().get(null, key);
            if (record != null) {
                byte[] compressed = (byte[]) record.getValue("data");
                if (compressed != null) {
                    byte[] rawBytes = Snappy.uncompress(compressed);
                    String json = new String(rawBytes, "UTF-8");
                    // Sử dụng TypeToken để parse về Map<Short, float[]>
                    return Utils.gson.fromJson(json, new com.google.gson.reflect.TypeToken<Map<Short, float[]>>(){}.getType());
                }
            }
        } catch (Exception e) {
            LOG.error("❌ Error reading DCA Pred at {}: {}", timestamp, e.getMessage());
        }
        return null;
    }

    /**
     * 🔥 MỚI: Đọc dự báo DCA theo tháng (Batch Read đa luồng giống Ticker 1M)
     * @param monthStr format "yyyyMM" (Ví dụ: "202401")
     */
    public static TreeMap<Long, Map<Short, float[]>> getDcaPredictionsForMonth(String monthStr) {
        TreeMap<Long, Map<Short, float[]>> results = new TreeMap<>();
        try {
            SimpleDateFormat sdfMonth = new SimpleDateFormat("yyyyMM");
            Date date = sdfMonth.parse(monthStr);
            Calendar cal = Calendar.getInstance();
            cal.setTime(date);

            long startTime = cal.getTimeInMillis();
            cal.add(Calendar.MONTH, 1);
            long endTime = cal.getTimeInMillis();

            int totalMinutes = (int) ((endTime - startTime) / (60 * 1000));
            LOG.info("📥 Reading DCA Data for month {} ({} records)...", monthStr, totalMinutes);

            results = readDcaBatchCustom(startTime, totalMinutes);

        } catch (Exception e) {
            LOG.error("❌ Error reading DCA Month {}: {}", monthStr, e.getMessage());
        }
        return results;
    }

    /**
     * Helper: Đọc Batch DCA Data theo range thời gian (Đa luồng)
     */
    public static TreeMap<Long, Map<Short, float[]>> readDcaBatchCustom(long startTime, int totalMinutes) {
        TreeMap<Long, Map<Short, float[]>> results = new TreeMap<>();

        // Tạo mảng timestamp
        long[] allTimestamps = new long[totalMinutes];
        for (int i = 0; i < totalMinutes; i++) {
            allTimestamps[i] = startTime + (i * 60000L);
        }

        List<Future<Map<Long, Map<Short, float[]>>>> futures = new ArrayList<>();
        int chunkSize = (totalMinutes + threadCount - 1) / threadCount;

        // Chia chunk cho các threads
        for (int i = 0; i < threadCount; i++) {
            final int startIdx = i * chunkSize;
            final int endIdx = Math.min(startIdx + chunkSize, totalMinutes);
            if (startIdx >= endIdx) break;

            futures.add(executor.submit(() -> {
                SimpleDateFormat localKeyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");
                Map<Long, Map<Short, float[]>> chunkResult = new HashMap<>();
                try {
                    Key[] chunkKeys = new Key[endIdx - startIdx];
                    long[] chunkTimestamps = Arrays.copyOfRange(allTimestamps, startIdx, endIdx);

                    for (int k = 0; k < chunkKeys.length; k++) {
                        String keyString = localKeyFormat.format(new Date(chunkTimestamps[k]));
                        chunkKeys[k] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_DCA_PRED, keyString);
                    }

                    // Batch Get
                    Record[] records = getClient().get(batchPolicy, chunkKeys);

                    for (int j = 0; j < records.length; j++) {
                        Record record = records[j];
                        if (record != null) {
                            byte[] compressed = (byte[]) record.getValue("data");
                            if (compressed != null) {
                                byte[] rawBytes = Snappy.uncompress(compressed);
                                String json = new String(rawBytes, "UTF-8");
                                Map<Short, float[]> data = Utils.gson.fromJson(json, new com.google.gson.reflect.TypeToken<Map<Short, float[]>>(){}.getType());
                                chunkResult.put(chunkTimestamps[j], data);
                            }
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
                return chunkResult;
            }));
        }

        // Gom kết quả
        for (Future<Map<Long, Map<Short, float[]>>> f : futures) {
            try {
                results.putAll(f.get());
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return results;
    }
    /**
     * 🔥 HÀM MỚI: Kiểm tra nhanh xem một list thời gian đã có dữ liệu AI chưa.
     * Trả về Set<Long> chứa các timestamp ĐÃ TỒN TẠI.
     */
    public static Set<Long> checkExistingDcaPredictions(List<Long> timestamps) {
        Set<Long> existing = new HashSet<>();
        if (timestamps == null || timestamps.isEmpty()) return existing;

        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            Key[] keys = new Key[timestamps.size()];

            for (int i = 0; i < timestamps.size(); i++) {
                String keyString = fmt.format(new Date(timestamps.get(i)));
                keys[i] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_DCA_PRED, keyString);
            }

            // Batch Exists: Cực nhanh, chỉ kiểm tra metadata không đọc dữ liệu
            boolean[] existsArray = getClient().exists(batchPolicy, keys);

            for (int i = 0; i < existsArray.length; i++) {
                if (existsArray[i]) {
                    existing.add(timestamps.get(i));
                }
            }
        } catch (Exception e) {
            LOG.error("❌ Error checking existence: {}", e.getMessage());
        }
        return existing;
    }
    public static void main(String[] args) throws ParseException {
        Long startTime = Utils.sdfFile.parse("20210103").getTime() + 7 * Utils.TIME_HOUR;
        TreeMap<Long, Map<Short, float[]>> time2Tickers = DataManagerAerospikeFloatSim.readDcaBatchCustom(startTime, 1440);
        for (Long timeKey : time2Tickers.keySet()) {

            LOG.info("Time: {} -> {} records", Utils.normalizeDateYYYYMMDDHHmm(timeKey), time2Tickers.get(timeKey).size());
        }
        LOG.info("{} {} {} {}",Utils.toJson(time2Tickers.firstEntry().getValue()), Utils.normalizeDateYYYYMMDDHHmm(time2Tickers.firstKey()),
                Utils.normalizeDateYYYYMMDDHHmm(time2Tickers.lastKey()), time2Tickers.size());
//        debugKeys();
//        Map<String, TreeMap<Long, Double>> symbol2FundingMap = DataManagerAerospikeFloatSim.getAllFundingMap();
//        for (String symbol : symbol2FundingMap.keySet()) {
//            LOG.info("{} -> {} records first: {} last: {}", symbol, symbol2FundingMap.get(symbol).size()
//                    , Utils.normalizeDateYYYYMMDDHHmm(symbol2FundingMap.get(symbol).firstKey())
//                    , Utils.normalizeDateYYYYMMDDHHmm(symbol2FundingMap.get(symbol).lastKey()));
//        }
//        TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(System.currentTimeMillis() - 1500 * Utils.TIME_MINUTE, 1500);
//        LOG.info("{} {} {} {}",time2Tickers.firstEntry().getValue().keySet(), Utils.normalizeDateYYYYMMDDHHmm(time2Tickers.firstKey()),
//                Utils.normalizeDateYYYYMMDDHHmm(time2Tickers.lastKey()), time2Tickers.size());
    }
}