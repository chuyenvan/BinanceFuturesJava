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
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;

// --- QUAN TRỌNG: Import Proto MỚI (Float + No Time) ---
import com.binance.chuyennd.proto.MinuteDataFinalProto.MinuteDataFinal;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

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
    public static final String AEROSPIKE_SET_NAME_TICKER = "kline_1m_opt";
    private static final String AEROSPIKE_SET_NAME_PRICE = "price_realtime";
    public static final String AEROSPIKE_SET_NAME_FUNDINGFEE = "funding_data";
    public static final String AEROSPIKE_SET_NAME_OPEN_INTEREST = "open_interest";
    public static final String AEROSPIKE_SET_NAME_MARKET_DATA = "market_data_object";


    // set name 226
//    public static final String AEROSPIKE_SET_NAME_FUNDING_PRED = "funding_pred_1m_20260606";
    public static final String AEROSPIKE_SET_NAME_FUNDING_PRED = "funding_pred_1m_v5";

    public static final String AEROSPIKE_SET_NAME_AI_PRED_MARKET = "ai_pred_market_full_basket_v2";
    // 1. CẤU HÌNH SET NAME VÀ KEY
    public static final String AEROSPIKE_SET_NAME_MAPPER = "symbol_mapper"; // Set name mới
    public static final String MAPPER_KEY_GLOBAL = "global_id_map";         // Key chứa Map
    private static final String MAPPER_BIN_NAME = "data";                    // Tên Bin chứa Map
    public static final String AEROSPIKE_SET_NAME_AI_PRED_1M = "ai_pred_1m";
    // 🔥 SET NAME MỚI CHO AI PREDICT
    public static final String AEROSPIKE_SET_NAME_DCA_PRED = "dca_pred_1m";
    private static volatile AerospikeClient client242;
    private static final BatchPolicy batchPolicy = new BatchPolicy();
    private static final int BATCH_CHUNK_SIZE = 2000;
    // 🔁 Retry cho batch read lỗi transient ("Batch max requests exceeded" khi nhiều tiến trình cùng đọc 226).
    private static final int BATCH_MAX_RETRY = 4;
    private static final long BATCH_RETRY_BACKOFF_MS = 500;
    private static final WritePolicy writePolicy = new WritePolicy();
    private static volatile AerospikeClient client226;

    // Cấu hình đa luồng
    public static int threadCount = 2;
    public static ExecutorService executor = Executors.newFixedThreadPool(threadCount);

    static {
        // 🔥 GIÁ TRỊ 0: Lưu trữ vĩnh viễn, không bao giờ tự động xóa
        writePolicy.sendKey = true; // Thêm dòng này
        writePolicy.expiration = 0;
        writePolicy.recordExistsAction = RecordExistsAction.UPDATE;
    }

    public static AerospikeClient getClient242() {
        if (client242 == null) {
            synchronized (DataManagerAerospikeFloatSim.class) {
                if (client242 == null) {
                    client242 = new AerospikeClient(Configs.AEROSPIKE_HOST_242, Configs.AEROSPIKE_PORT_242);
                }
            }
        }
        return client242;
    }

    public static AerospikeClient getClient226() {
        if (client226 == null) {
            synchronized (DataManagerAerospikeFloatSim.class) {
                if (client226 == null) {
                    client226 = new AerospikeClient(Configs.AEROSPIKE_HOST_226, Configs.AEROSPIKE_PORT_226);
                }
            }
        }
        return client226;
    }

    /**
     * Hàm lấy toàn bộ Mapper (String -> Short) từ Aerospike khi khởi động
     */
    public static Map<String, Short> loadSymbolMapper() {
        Map<String, Short> result = new ConcurrentHashMap<>();
        try {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_MAPPER, MAPPER_KEY_GLOBAL);
            Record record = getReadClient().get(null, key);   // kaggle/hpo => 226 (bản sao)

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
            getClient242().operate(writePolicy, key,
                    MapOperation.put(MapPolicy.Default, MAPPER_BIN_NAME, Value.get(symbol), Value.get(id))
            );

            // LOG.info("💾 Saved Mapping: {} -> {}", symbol, id);
        } catch (Exception e) {
            LOG.error("❌ Error saving symbol mapping {} -> {}: {}", symbol, id, e.getMessage());
        }
    }

    // 🔒 #4 (TASK-029): striped lock chống race lost-update cùng key phút.
    // Rest-Price-Loop (3s) + Rest-Kline-Loop (chốt phút) cùng gọi writeMinuteBatch(curMin,...) → read(getExistingTickersMap)
    // → putAll → put KHÔNG atomic → 2 luồng cùng phút có thể mất nến. Khóa theo HASH key-phút (cùng phút = cùng stripe
    // = tuần tự hoá read-modify-write; phút khác = stripe khác, gần như không chặn nhau). Bounded 64 stripe, không phình.
    private static final int MINUTE_WRITE_STRIPES = 64;
    private static final Object[] MINUTE_WRITE_LOCKS = buildMinuteWriteLocks();

    private static Object[] buildMinuteWriteLocks() {
        Object[] locks = new Object[MINUTE_WRITE_STRIPES];
        for (int i = 0; i < MINUTE_WRITE_STRIPES; i++) locks[i] = new Object();
        return locks;
    }

    public static void writeMinuteBatch(long timestamp, Map<String, KlineObjectOptimized> newTickers) {
        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            String keyString = fmt.format(new Date(timestamp));
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_TICKER, keyString);

            // Khóa theo stripe của key-phút: read-modify-write của cùng một phút được tuần tự hoá (atomic trong JVM ingest).
            Object lock = MINUTE_WRITE_LOCKS[(keyString.hashCode() & 0x7fffffff) % MINUTE_WRITE_STRIPES];
            synchronized (lock) {
                // Gộp dữ liệu cũ (nếu có) để bảo toàn nến của các mã khác
                Map<String, KlineObjectOptimized> finalMap = getExistingTickersMap(key);
                finalMap.putAll(newTickers);

                byte[] compressed = Snappy.compress(MinuteDataFinal.newBuilder().putAllTickers(finalMap).build().toByteArray());
                getClient242().put(writePolicy, key, new Bin("data", compressed));
            }
        } catch (Exception e) {
            LOG.error("❌ Error writing batch at {}: {}", timestamp, e.getMessage());
        }
    }

    public static void writePriceRealtime(Map<String, Float> priceMap) {
        if (priceMap == null || priceMap.isEmpty()) return;
        try {
            long now = System.currentTimeMillis();
            for (Map.Entry<String, Float> entry : priceMap.entrySet()) {
                // Sử dụng UPPERCASE cho symbol để đồng bộ
                String symbol = entry.getKey().toUpperCase();
                Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_PRICE, symbol);

                // Ghi giá và timestamp cập nhật
                getClient242().put(null, key,
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
     * @return Map chứa Symbol -> Giá (Float)
     */
    public static Map<String, Float> getAllPriceRealtimeLegacy(Set<String> expectedSymbols) {
        Map<String, Float> results = new HashMap<>();
        // 1. Tạo bản đồ: Digest -> Symbol để tra cứu nhanh
        Map<String, String> digestToSymbol = new HashMap<>();
        for (String s : expectedSymbols) {
            String upperS = s.toUpperCase();
            Key k = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_PRICE, upperS);
            // Digest là mảng byte định danh duy nhất của Key
            digestToSymbol.put(Base64.getEncoder().encodeToString(k.digest), upperS);
        }

        try {
            ScanPolicy scanPolicy = new ScanPolicy();
            scanPolicy.concurrentNodes = true;
            scanPolicy.includeBinData = true;

            getClient242().scanAll(scanPolicy, Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_PRICE, (key, record) -> {
                // Lấy Digest của bản ghi hiện tại
                String currentDigest = Base64.getEncoder().encodeToString(key.digest);
                String symbol = digestToSymbol.get(currentDigest);

                if (symbol != null) {
                    results.put(symbol, record.getFloat("price"));
                }
            }, "price");
        } catch (Exception e) {
            LOG.error("❌ Error Legacy Scan: {}", e.getMessage());
        }
        return results;
    }

    /**
     * Đọc giá realtime của MỘT symbol từ set {@code price_realtime}.
     * <p>price_realtime CHỈ được live ghi trên 242 (xem {@link #writePriceRealtime}), nên LUÔN
     * đọc 242 — KHÔNG dùng {@link #getReadClient()} (bản sao 226 không có set này).
     *
     * @param symbol symbol (vd "BTCUSDT"); tự upper-case cho khớp key lúc ghi.
     * @return giá ({@link Float}) hoặc {@code null} nếu chưa có record / bin price rỗng / lỗi đọc.
     */
    public static Float getPriceRealtime(String symbol) {
        if (symbol == null || symbol.isBlank()) return null;
        try {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_PRICE, symbol.toUpperCase());
            Record record = getClient242().get(null, key);
            if (record == null || record.getValue("price") == null) return null;
            return record.getFloat("price");
        } catch (Exception e) {
            LOG.error("❌ Error getPriceRealtime {}: {}", symbol, e.getMessage());
            return null;
        }
    }

    /**
     * Đọc mốc thời gian (ms-epoch) lần cập nhật giá gần nhất của symbol (bin {@code ts}) để tính
     * tuổi dữ liệu. Đọc 242 cùng lý do với {@link #getPriceRealtime}.
     *
     * @param symbol symbol (vd "BTCUSDT").
     * @return ms-epoch hoặc {@code null} nếu chưa có record / bin ts rỗng / lỗi đọc.
     */
    public static Long getPriceRealtimeTs(String symbol) {
        if (symbol == null || symbol.isBlank()) return null;
        try {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_PRICE, symbol.toUpperCase());
            Record record = getClient242().get(null, key);
            if (record == null || record.getValue("ts") == null) return null;
            return record.getLong("ts");
        } catch (Exception e) {
            LOG.error("❌ Error getPriceRealtimeTs {}: {}", symbol, e.getMessage());
            return null;
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

            // 1. Lấy dữ liệu cũ (getFundingMap xử lý cả f_data Snappy lẫn f_map legacy)
            Map<Long, Float> existingMap = getFundingMap(symbol);

            // 🛡️ GUARD CHỐNG MẤT LỊCH SỬ: nếu record TỒN TẠI & có f_data nhưng đọc ra RỖNG
            // => nghi lỗi đọc tạm thời (Aerospike timeout / parse hỏng). TUYỆT ĐỐI không ghi đè,
            // vì merge-với-rỗng + ghi đè = xoá sạch lịch sử (chính là lỗi đã từng làm mất data).
            try {
                Record raw = getClient242().get(null, key);
                boolean hasBlob = raw != null && raw.getValue("f_data") != null
                        && ((byte[]) raw.getValue("f_data")).length > 0;
                if (hasBlob && existingMap.isEmpty()) {
                    LOG.error("❌ ABORT writeFundingMap {} — record có f_data nhưng đọc ra RỖNG (nghi lỗi đọc). "
                            + "Không ghi đè để tránh mất lịch sử funding.", symbol);
                    return;
                }
            } catch (Exception ignore) {
                // Không kiểm tra được thì theo luồng cũ (vẫn append bên dưới).
            }

            // 2. Gộp dữ liệu (Dùng TreeMap để luôn sắp xếp theo thời gian)
            TreeMap<Long, Float> finalMap = new TreeMap<>();
            existingMap.forEach((k, v) -> finalMap.put(k, v.floatValue()));
            fundingRates.forEach(finalMap::put);

            // 3. Serialize Map thành byte[] và nén bằng Snappy để tránh lỗi "Record too big"
            // Chúng ta lưu Map dưới dạng Map đơn giản để Snappy xử lý hiệu quả
            byte[] rawBytes = Utils.gson.toJson(finalMap).getBytes("UTF-8");
            byte[] compressedBytes = Snappy.compress(rawBytes);

            // 4. Ghi vào bin "f_data" dạng blob thay vì CDT Map trực tiếp
            getClient242().put(writePolicy, key, new Bin("f_data", compressedBytes));

            if (finalMap.size() % 100 == 0) {
                LOG.info("💾 Saved Funding {}: {} records (Compressed)", symbol, finalMap.size());
            }
        } catch (Exception e) {
            LOG.error("❌ Error writing Funding for {}: {}", symbol, e.getMessage());
        }
    }

    /**
     * Ghi Open Interest theo symbol — set {@code open_interest} trên 242. BẮT CHƯỚC
     * {@link #writeFundingMap}: Snappy nén Map&lt;Long,Float&gt; (ts → sumOpenInterestValue, USD notional),
     * merge với lịch sử cũ + GUARD chống mất lịch sử (không ghi đè khi đọc cũ ra rỗng nghi lỗi đọc).
     *
     * @param symbol  symbol (vd "BTCUSDT").
     * @param oiByTs  map mốc-thời-gian (ms) → OI notional (USD); rỗng/null → bỏ qua.
     */
    public static void writeOpenInterestMap(String symbol, Map<Long, Float> oiByTs) {
        if (oiByTs == null || oiByTs.isEmpty()) return;
        try {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_OPEN_INTEREST, symbol);

            // 1. Lấy dữ liệu cũ.
            Map<Long, Float> existingMap = getOpenInterestMap(symbol);

            // 🛡️ GUARD CHỐNG MẤT LỊCH SỬ: record có blob nhưng đọc ra RỖNG → nghi lỗi đọc tạm thời,
            // TUYỆT ĐỐI không ghi đè (merge-với-rỗng + ghi đè = xoá sạch lịch sử).
            try {
                Record raw = getClient242().get(null, key);
                boolean hasBlob = raw != null && raw.getValue("oi_data") != null
                        && ((byte[]) raw.getValue("oi_data")).length > 0;
                if (hasBlob && existingMap.isEmpty()) {
                    LOG.error("❌ ABORT writeOpenInterestMap {} — record có oi_data nhưng đọc ra RỖNG "
                            + "(nghi lỗi đọc). Không ghi đè để tránh mất lịch sử OI.", symbol);
                    return;
                }
            } catch (Exception ignore) {
            }

            // 2. Gộp (TreeMap để luôn sắp theo thời gian).
            TreeMap<Long, Float> finalMap = new TreeMap<>();
            existingMap.forEach((k, v) -> finalMap.put(k, v.floatValue()));
            oiByTs.forEach(finalMap::put);

            // 3. Serialize + nén Snappy → bin "oi_data".
            byte[] rawBytes = Utils.gson.toJson(finalMap).getBytes("UTF-8");
            byte[] compressedBytes = Snappy.compress(rawBytes);
            getClient242().put(writePolicy, key, new Bin("oi_data", compressedBytes));
        } catch (Exception e) {
            LOG.error("❌ Error writing OpenInterest for {}: {}", symbol, e.getMessage());
        }
    }

    /**
     * Giải nén và đọc Map Open Interest của 1 symbol (ts → notional USD). Đọc 242 (nơi live ghi).
     *
     * @param symbol symbol (vd "BTCUSDT").
     * @return {@link TreeMap} ts→OI; rỗng nếu chưa có / lỗi đọc.
     */
    public static TreeMap<Long, Float> getOpenInterestMap(String symbol) {
        TreeMap<Long, Float> results = new TreeMap<>();
        try {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_OPEN_INTEREST, symbol);
            Record record = getClient242().get(null, key);
            if (record != null) {
                byte[] compressedData = (byte[]) record.getValue("oi_data");
                if (compressedData != null) {
                    String json = new String(Snappy.uncompress(compressedData), "UTF-8");
                    java.lang.reflect.Type mapType = new com.google.gson.reflect.TypeToken<Map<String, Float>>() {
                    }.getType();
                    Map<String, Float> rawMap = Utils.gson.fromJson(json, mapType);
                    rawMap.forEach((k, v) -> results.put(Long.parseLong(k), v));
                }
            }
        } catch (Exception e) {
            LOG.error("❌ Error reading OpenInterest for {}: {}", symbol, e.getMessage());
        }
        return results;
    }

    /**
     * Ghi 1 metric per-symbol vào Aerospike <b>226</b> (kho compute/train) — TASK-013 backfill OI/LS/taker.
     * GENERIC hoá {@link #writeOpenInterestMap} (set/bin tham số) để 5 set metrics (open_interest,
     * oi_ls_toptrader_acc/pos, oi_ls_global_acc, oi_taker_vol) dùng CHUNG một mối ghi: Snappy nén
     * {@code Map<Long,Float>} (ts 5m UTC → giá trị), merge lịch sử cũ + GUARD chống mất lịch sử (record có
     * blob nhưng đọc ra RỖNG → nghi lỗi đọc, KHÔNG ghi đè). Worker Kaggle chỉ tới 226 nên ghi 226; job
     * trên 226 đẩy tiếp 226→242 sau (kiến trúc A).
     *
     * @param setName tên set Aerospike (vd {@code "open_interest"}).
     * @param binName tên bin chứa blob Snappy (vd {@code "oi_data"} cho OI, {@code "m_data"} cho LS/taker).
     * @param symbol  symbol (vd "BTCUSDT"), dùng làm key.
     * @param byTs    map ts(ms, mốc 5m UTC) → giá trị; rỗng/null → bỏ qua (không đụng record cũ).
     */
    public static int writeMetricMap226(String setName, String binName, String symbol, Map<Long, Float> byTs) {
        return writeMetricMapTo(getClient226(), "226", setName, binName, symbol, byTs);
    }

    /**
     * Ghi 1 metric per-symbol vào Aerospike <b>242</b> (source) — TASK-013 ĐẨY 226→242 (kiến trúc A) sau
     * khi backfill xong trên 226. Cùng lõi merge-guard với {@link #writeMetricMap226}, chỉ khác client.
     *
     * @return số chunk-tháng GHI LỖI (0 = OK).
     */
    public static int writeMetricMap242(String setName, String binName, String symbol, Map<Long, Float> byTs) {
        return writeMetricMapTo(getClient242(), "242", setName, binName, symbol, byTs);
    }

    // ============================================================================================
    // BIẾN THỂ CHUNK-NGÀY (SYMBOL_yyyyMMdd) — cho dữ liệu cadence DÀY (per-phút). Chunk-tháng
    // (writeMetricMap226) vỡ "Record too big" với per-phút (~43k điểm/tháng); chunk-ngày ~1440 điểm
    // /ngày → an toàn. CHUẨN HÓA: mọi dữ liệu per-phút (hoặc dày hơn 5m) PHẢI dùng biến thể ngày này.
    // Xem docs/DATA_CHUNKING_STANDARD.md.
    // ============================================================================================

    /** TZ + tháng bắt đầu dùng CHUNG với chunk-tháng (GMT+7) để reader iterate nhất quán. */
    private static SimpleDateFormat dayFmt() {
        SimpleDateFormat f = new SimpleDateFormat("yyyyMMdd");
        f.setTimeZone(TimeZone.getTimeZone(OI_METRIC_TZ));
        return f;
    }

    /** Ghi metric per-symbol vào 226 theo chunk-NGÀY (SYMBOL_yyyyMMdd). Trả số chunk lỗi (0 = OK). */
    public static int writeMetricMapDay226(String setName, String binName, String symbol, Map<Long, Float> byTs) {
        if (byTs == null || byTs.isEmpty()) return 0;
        SimpleDateFormat f = dayFmt();
        Map<String, TreeMap<Long, Float>> byDay = new HashMap<>();
        for (Map.Entry<Long, Float> e : byTs.entrySet()) {
            byDay.computeIfAbsent(f.format(new Date(e.getKey())), k -> new TreeMap<>()).put(e.getKey(), e.getValue());
        }
        int failed = 0;
        for (Map.Entry<String, TreeMap<Long, Float>> de : byDay.entrySet()) {
            // tái dùng writeMonthChunk: monthStr=yyyyMMdd vẫn tạo key SYMBOL_yyyyMMdd đúng, logic merge/guard y hệt
            if (!writeMonthChunk(getClient226(), "226", setName, binName, symbol, de.getKey(), de.getValue())) failed++;
        }
        return failed;
    }

    /** Đọc metric per-symbol từ 226 theo chunk-NGÀY: gộp toàn bộ key ngày [202001-01..nay]. */
    public static TreeMap<Long, Float> getMetricMapDay226(String setName, String binName, String symbol) {
        TreeMap<Long, Float> results = new TreeMap<>();
        try {
            List<String> days = allDaysTillNow();
            Key[] keys = new Key[days.size()];
            for (int i = 0; i < days.size(); i++) {
                keys[i] = new Key(Configs.AEROSPIKE_NAMESPACE, setName, symbol + "_" + days.get(i));
            }
            for (int off = 0; off < keys.length; off += BATCH_CHUNK_SIZE) {
                Key[] sub = Arrays.copyOfRange(keys, off, Math.min(off + BATCH_CHUNK_SIZE, keys.length));
                Record[] recs = getClient226().get(batchPolicy, sub);
                if (recs == null) continue;
                for (Record record : recs) results.putAll(decodeMap(record, binName));
            }
        } catch (Exception e) {
            LOG.error("❌ Error getMetricMapDay set={} bin={} {}: {}", setName, binName, symbol, e.getMessage());
        }
        return results;
    }

    /** Danh sách "yyyyMMdd" từ OI_METRIC_MONTH_START đến hôm nay (GMT+7), tăng dần. */
    private static List<String> allDaysTillNow() {
        List<String> days = new ArrayList<>();
        try {
            SimpleDateFormat f = dayFmt();
            Calendar cal = Calendar.getInstance(TimeZone.getTimeZone(OI_METRIC_TZ));
            cal.setTime(monthFmt().parse(OI_METRIC_MONTH_START));
            Calendar end = Calendar.getInstance(TimeZone.getTimeZone(OI_METRIC_TZ));
            while (!cal.after(end)) {
                days.add(f.format(cal.getTime()));
                cal.add(Calendar.DAY_OF_MONTH, 1);
            }
        } catch (ParseException e) {
            LOG.error("❌ allDaysTillNow parse lỗi: {}", e.getMessage());
        }
        return days;
    }

    /**
     * LÕI dùng chung (một mối ghi) cho {@link #writeMetricMap226}/{@link #writeMetricMap242}: Snappy nén
     * {@code Map<Long,Float>} (ts 5m UTC → giá trị), merge lịch sử cũ trên ĐÚNG client + GUARD chống mất
     * lịch sử (record có blob nhưng đọc ra RỖNG → nghi lỗi đọc, KHÔNG ghi đè).
     *
     * @param client  client đích (226 hoặc 242) — ĐỌC cũ + GHI mới cùng 1 client để guard nhất quán.
     * @param tag     nhãn host cho log ("226"/"242").
     * @param setName tên set Aerospike (vd {@code "open_interest"}).
     * @param binName tên bin chứa blob Snappy ({@code "oi_data"} cho OI, {@code "m_data"} cho LS/taker).
     * @param symbol  symbol (vd "BTCUSDT"), dùng làm key.
     * @param byTs    map ts(ms, mốc 5m UTC) → giá trị; rỗng/null → bỏ qua (không đụng record cũ).
     */
    /**
     * TZ bucket cho khoá record-tháng metrics — GMT+7, ĐỒNG NHẤT với khoá tháng kline/15m/4h của repo
     * (chúng dùng {@code SimpleDateFormat} default-TZ = GMT+7) để reader iterate tháng nhất quán.
     */
    public static final String OI_METRIC_TZ = "GMT+7";
    /** Tháng sớm nhất cần quét khi đọc-toàn-bộ (BTC metrics ~2020-09; quét từ 202001 cho rộng). */
    private static final String OI_METRIC_MONTH_START = "202001";

    private static SimpleDateFormat monthFmt() {
        SimpleDateFormat f = new SimpleDateFormat("yyyyMM");
        f.setTimeZone(TimeZone.getTimeZone(OI_METRIC_TZ));
        return f;
    }

    /** Khoá record-tháng: {@code SYMBOL_yyyyMM} (chia nhỏ để KHÔNG vượt max record size Aerospike). */
    private static String monthKey(String symbol, String monthStr) {
        return symbol + "_" + monthStr;
    }

    /** Danh sách "yyyyMM" từ {@link #OI_METRIC_MONTH_START} đến tháng hiện tại (GMT+7), tăng dần. */
    private static List<String> allMonthsTillNow() {
        List<String> months = new ArrayList<>();
        try {
            SimpleDateFormat f = monthFmt();
            Calendar cal = Calendar.getInstance(TimeZone.getTimeZone(OI_METRIC_TZ));
            cal.setTime(f.parse(OI_METRIC_MONTH_START));
            Calendar end = Calendar.getInstance(TimeZone.getTimeZone(OI_METRIC_TZ));
            while (!cal.after(end)) {
                months.add(f.format(cal.getTime()));
                cal.add(Calendar.MONTH, 1);
            }
        } catch (ParseException e) {
            LOG.error("❌ allMonthsTillNow parse lỗi: {}", e.getMessage());
        }
        return months;
    }

    /**
     * LÕI ghi: TÁCH map theo THÁNG (GMT+7) → mỗi tháng 1 record nhỏ ({@code SYMBOL_yyyyMM}, ~8.9k điểm 5m
     * → vừa max record size, KHÁC funding 1-record/symbol vốn vỡ với data 5m × nhiều năm). Mỗi chunk
     * read-merge-GUARD-write riêng. Trả số chunk LỖI (0 = OK) để caller biết có nên mark DONE.
     */
    private static int writeMetricMapTo(AerospikeClient client, String tag, String setName, String binName,
                                        String symbol, Map<Long, Float> byTs) {
        if (byTs == null || byTs.isEmpty()) return 0;
        SimpleDateFormat f = monthFmt();
        Map<String, TreeMap<Long, Float>> byMonth = new HashMap<>();
        for (Map.Entry<Long, Float> e : byTs.entrySet()) {
            String mon = f.format(new Date(e.getKey()));
            byMonth.computeIfAbsent(mon, k -> new TreeMap<>()).put(e.getKey(), e.getValue());
        }
        int failed = 0;
        for (Map.Entry<String, TreeMap<Long, Float>> me : byMonth.entrySet()) {
            if (!writeMonthChunk(client, tag, setName, binName, symbol, me.getKey(), me.getValue())) failed++;
        }
        return failed;
    }

    /** Ghi 1 chunk-tháng (read key tháng → GUARD chống mất lịch sử → merge → Snappy → put). false nếu lỗi. */
    private static boolean writeMonthChunk(AerospikeClient client, String tag, String setName, String binName,
                                           String symbol, String monthStr, Map<Long, Float> chunkData) {
        if (chunkData == null || chunkData.isEmpty()) return true;
        try {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, setName, monthKey(symbol, monthStr));
            Record raw = client.get(null, key);
            TreeMap<Long, Float> existing = decodeMap(raw, binName);

            // 🛡️ GUARD CHỐNG MẤT LỊCH SỬ: record có blob nhưng đọc ra RỖNG → nghi lỗi đọc tạm thời,
            // TUYỆT ĐỐI không ghi đè (merge-với-rỗng + ghi đè = xoá lịch sử).
            boolean hasBlob = raw != null && raw.getValue(binName) != null
                    && ((byte[]) raw.getValue(binName)).length > 0;
            if (hasBlob && existing.isEmpty()) {
                LOG.error("❌ ABORT writeMonthChunk@{} set={} key={}_{} — record có blob nhưng đọc ra RỖNG "
                        + "(nghi lỗi đọc). Không ghi đè.", tag, setName, symbol, monthStr);
                return false;
            }

            TreeMap<Long, Float> finalMap = new TreeMap<>(existing);
            finalMap.putAll(chunkData);
            byte[] rawBytes = Utils.gson.toJson(finalMap).getBytes("UTF-8");
            byte[] compressed = Snappy.compress(rawBytes);
            client.put(writePolicy, key, new Bin(binName, compressed));
            return true;
        } catch (Exception e) {
            LOG.error("❌ Error writeMonthChunk@{} set={} {}_{}: {}", tag, setName, symbol, monthStr, e.getMessage());
            return false;
        }
    }

    /** Giải mã 1 Record (Snappy JSON Map) → TreeMap (rỗng nếu null/lỗi). */
    private static TreeMap<Long, Float> decodeMap(Record record, String binName) {
        TreeMap<Long, Float> results = new TreeMap<>();
        if (record == null) return results;
        try {
            byte[] compressed = (byte[]) record.getValue(binName);
            if (compressed != null) {
                String json = new String(Snappy.uncompress(compressed), "UTF-8");
                java.lang.reflect.Type mapType = new com.google.gson.reflect.TypeToken<Map<String, Float>>() {
                }.getType();
                Map<String, Float> rawMap = Utils.gson.fromJson(json, mapType);
                rawMap.forEach((k, v) -> results.put(Long.parseLong(k), v));
            }
        } catch (Exception e) {
            LOG.error("❌ Error decodeMap bin={}: {}", binName, e.getMessage());
        }
        return results;
    }

    /**
     * Giải nén + đọc 1 metric per-symbol từ Aerospike <b>226</b> (cặp đôi đọc của {@link #writeMetricMap226}).
     *
     * @param setName tên set Aerospike.
     * @param binName tên bin chứa blob Snappy.
     * @param symbol  symbol (vd "BTCUSDT").
     * @return {@link TreeMap} ts→giá trị; rỗng nếu chưa có / lỗi đọc.
     */
    public static TreeMap<Long, Float> getMetricMap226(String setName, String binName, String symbol) {
        return getMetricMapFrom(getClient226(), setName, binName, symbol);
    }

    /** Như {@link #getMetricMap226} nhưng đọc từ <b>242</b> (xác minh sau khi đẩy 226→242). */
    public static TreeMap<Long, Float> getMetricMap242(String setName, String binName, String symbol) {
        return getMetricMapFrom(getClient242(), setName, binName, symbol);
    }

    /**
     * LÕI đọc dùng chung cho {@link #getMetricMap226}/{@link #getMetricMap242}: gộp TOÀN BỘ chunk-tháng
     * ({@code SYMBOL_yyyyMM}) của 1 symbol thành 1 TreeMap. Batch-get mọi key tháng [202001..nay] (chunk
     * theo {@link #BATCH_CHUNK_SIZE}), bỏ qua tháng null.
     */
    private static TreeMap<Long, Float> getMetricMapFrom(AerospikeClient client, String setName, String binName, String symbol) {
        TreeMap<Long, Float> results = new TreeMap<>();
        try {
            List<String> months = allMonthsTillNow();
            Key[] keys = new Key[months.size()];
            for (int i = 0; i < months.size(); i++) {
                keys[i] = new Key(Configs.AEROSPIKE_NAMESPACE, setName, monthKey(symbol, months.get(i)));
            }
            for (int off = 0; off < keys.length; off += BATCH_CHUNK_SIZE) {
                Key[] sub = Arrays.copyOfRange(keys, off, Math.min(off + BATCH_CHUNK_SIZE, keys.length));
                Record[] recs = client.get(batchPolicy, sub);
                if (recs == null) continue;
                for (Record record : recs) {
                    results.putAll(decodeMap(record, binName));
                }
            }
        } catch (Exception e) {
            LOG.error("❌ Error getMetricMap set={} bin={} {}: {}", setName, binName, symbol, e.getMessage());
        }
        return results;
    }

    /**
     * Giải nén và đọc Map Funding
     */
    public static TreeMap<Long, Float> getFundingMap(String symbol) {
        TreeMap<Long, Float> results = new TreeMap<>();
        try {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_FUNDINGFEE, symbol);
            Record record = getReadClient().get(null, key);   // kaggle/hpo => 226 (bản sao)
            if (record != null) {
                byte[] compressedData = (byte[]) record.getValue("f_data");
                if (compressedData != null) {
                    // Giải nén Snappy
                    String json = new String(Snappy.uncompress(compressedData), "UTF-8");
                    // FIX: phải dùng TypeToken như getAllFundingMap. Nếu để Map.class raw, Gson parse value
                    // thành Double → forEach ép sang Float ném ClassCastException → rơi vào catch → trả RỖNG.
                    // Hệ quả cũ: lazy-load trong getNearestFundingFee rỗng (→0), và writeFundingMap merge
                    // thấy existing rỗng → chạy lại crawler theo từng đợt sẽ GHI ĐÈ mất lịch sử cũ.
                    java.lang.reflect.Type mapType = new com.google.gson.reflect.TypeToken<Map<String, Float>>() {
                    }.getType();
                    Map<String, Float> rawMap = Utils.gson.fromJson(json, mapType);

                    // Convert Key từ String (JSON) về Long
                    rawMap.forEach((k, v) -> results.put(Long.parseLong(k), v));
                }
            }
        } catch (Exception e) {
            // Trường hợp dữ liệu cũ vẫn là CDT Map (f_map)
            try {
                Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_FUNDINGFEE, symbol);
                Record record = getReadClient().get(null, key);   // kaggle/hpo => 226 (bản sao)
                if (record != null && record.getMap("f_map") != null) {
                    record.getMap("f_map").forEach((k, v) -> results.put((Long) k, ((Number) v).floatValue()));
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
    public static Map<String, TreeMap<Long, Float>> getAllFundingMap() {
        Map<String, TreeMap<Long, Float>> allResults = new HashMap<>();
        try {
            ScanPolicy scanPolicy = new ScanPolicy();
            scanPolicy.concurrentNodes = true; // Quét song song trên các node
            scanPolicy.includeBinData = true;

            // Chỉ định rõ bin "f_data" (nén Snappy) và "f_map" (dữ liệu cũ) để tối ưu
            getReadClient().scanAll(scanPolicy, Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_FUNDINGFEE, (key, record) -> {   // kaggle/hpo => 226
                String symbol = (key.userKey != null) ? key.userKey.toString() : null;
                if (symbol == null) return;

                TreeMap<Long, Float> symbolFunding = new TreeMap<>();
                try {
                    // Ưu tiên xử lý dữ liệu mới (Snappy Compressed)
                    byte[] compressedData = (byte[]) record.getValue("f_data");
                    if (compressedData != null) {
                        String json = new String(Snappy.uncompress(compressedData), "UTF-8");

                        // SỬA Ở ĐÂY: Dùng TypeToken để ép Gson parse đúng kiểu số
                        java.lang.reflect.Type mapType = new com.google.gson.reflect.TypeToken<Map<String, Float>>() {
                        }.getType();
                        Map<String, Float> rawMap = Utils.gson.fromJson(json, mapType);

                        rawMap.forEach((k, v) -> symbolFunding.put(Long.parseLong(k), v));
                    } else {
                        // Xử lý dữ liệu cũ (CDT Map) nếu không có f_data
                        Map<?, ?> fMap = record.getMap("f_map");
                        if (fMap != null) {
                            fMap.forEach((k, v) -> symbolFunding.put((Long) k, ((Number) v).floatValue()));
                        }
                    }

                    if (!symbolFunding.isEmpty()) {
                        allResults.put(symbol, symbolFunding);
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                    LOG.error("❌ Lỗi giải mã Funding cho {}: {}", symbol, e.getMessage());
                }
            }, "f_data", "f_map");

        } catch (Exception e) {
            LOG.error("❌ Error Scanning all Funding data: {}", e.getMessage());
        }
        return allResults;
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
            Record record = getClient242().get(null, key);
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
     * Đọc dữ liệu toàn bộ thị trường trong 1 ngày (1440 phút) — client theo config {@link #getReadClient()}.
     */
    public static TreeMap<Long, Map<String, KlineObjectSimple>> readDataFromAerospike1M(long startTime) {
        return readDataFromAerospike1M(startTime, getReadClient());
    }

    /**
     * Đọc dữ liệu toàn bộ thị trường trong 1 ngày (1440 phút) với client TƯỜNG MINH — cho tool tự biết
     * nó muốn đọc cluster nào theo arg runtime (TASK-112 #9: {@code Aggregate15m4hBtcEth} chọn 226/242
     * theo arg, KHÔNG đi qua config per-box).
     *
     * @param startTime mốc đầu ngày (ms)
     * @param client    client Aerospike đích ({@link #getClient226()} / {@link #getClient242()})
     * @return map phút → (symbol → kline); phút thiếu record bị bỏ qua
     */
    public static TreeMap<Long, Map<String, KlineObjectSimple>> readDataFromAerospike1M(long startTime, AerospikeClient client) {
        TreeMap<Long, Map<String, KlineObjectSimple>> results = new TreeMap<>();
        int totalRecords = 1440;

        // Tạo Key và Timestamp
        long[] allTimestamps = new long[totalRecords];
        Calendar cal = Calendar.getInstance(java.util.TimeZone.getTimeZone("GMT+7")); // HARDEN 2026-07-23: pin GMT+7 (khong phu thuoc TZ mac dinh node) - khop quy uoc key da ghi
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
                localKeyFormat.setTimeZone(java.util.TimeZone.getTimeZone("GMT+7")); // HARDEN 2026-07-23: pin GMT+7 doc key deterministic

                Map<Long, Map<String, KlineObjectSimple>> chunkResult = new HashMap<>();
                // Tạo Keys cho chunk này
                Key[] chunkKeys = new Key[endIdx - startIdx];
                long[] chunkTimestamps = Arrays.copyOfRange(allTimestamps, startIdx, endIdx);
                for (int k = 0; k < chunkKeys.length; k++) {
                    String keyString = localKeyFormat.format(new Date(chunkTimestamps[k]));
                    chunkKeys[k] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_TICKER, keyString);
                }

                // 🔁 RETRY batch read: lỗi Connection/EOFException khi đọc ticker 226 qua WAN là transient.
                // KHÔNG nuốt lỗi như trước (printStackTrace -> chunk rỗng -> FAIL-FAST "khong co ticker" OAN).
                // Hết BATCH_MAX_RETRY vẫn lỗi -> THROW để tầng trên báo đúng nguyên nhân.
                Record[] records = null;
                Exception lastError = null;
                int attempt = 0;
                while (attempt < BATCH_MAX_RETRY) {
                    attempt++;
                    try {
                        records = client.get(batchPolicy, chunkKeys);
                        if (records != null) break;
                        LOG.warn("⚠️ [AEROSPIKE] get() trả NULL chunk start={} (lần {}/{})",
                                Utils.normalizeDateYYYYMMDDHHmm(chunkTimestamps[0]), attempt, BATCH_MAX_RETRY);
                    } catch (Exception e) {
                        // Bắt AerospikeException (Connection/EOF) và mọi Exception khác của batch read.
                        lastError = e;
                        LOG.warn("⚠️ [AEROSPIKE-RETRY] {} | chunk[{}..{}] start={} keys={} lần {}/{}: {}",
                                e.getClass().getSimpleName(), startIdx, endIdx,
                                Utils.normalizeDateYYYYMMDDHHmm(chunkTimestamps[0]),
                                chunkKeys.length, attempt, BATCH_MAX_RETRY, e.getMessage());
                    }
                    if (attempt < BATCH_MAX_RETRY) {
                        try {
                            Thread.sleep(BATCH_RETRY_BACKOFF_MS * attempt); // backoff tuyến tính: 500,1000,1500...
                        } catch (InterruptedException ie) {
                            Thread.currentThread().interrupt();
                            break;
                        }
                    }
                }

                if (records == null) {
                    throw new RuntimeException(String.format(
                            "batch read failed after %d retries: chunk start=%s keys=%d cause=%s",
                            BATCH_MAX_RETRY, Utils.normalizeDateYYYYMMDDHHmm(chunkTimestamps[0]),
                            chunkKeys.length, lastError == null ? "get() trả NULL" : lastError.toString()), lastError);
                }

                try {
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
                    LOG.error("❌ [AEROSPIKE-PARSE] Lỗi giải nén/parse chunk start={}: {} {}",
                            Utils.normalizeDateYYYYMMDDHHmm(chunkTimestamps[0]), e.getClass().getSimpleName(), e.getMessage());
                    throw new RuntimeException("parse failed for chunk start="
                            + Utils.normalizeDateYYYYMMDDHHmm(chunkTimestamps[0]) + ": " + e.getMessage(), e);
                }
                return chunkResult;
            }));
        }

        // Tổng hợp kết quả — future.get() ném ExecutionException nếu chunk task THROW.
        // KHÔNG nuốt (trước đây printStackTrace) -> rethrow để FAIL-FAST báo đúng nguyên nhân batch read.
        for (Future<Map<Long, Map<String, KlineObjectSimple>>> future : futures) {
            try {
                results.putAll(future.get());
            } catch (Exception e) {
                Throwable cause = e.getCause() != null ? e.getCause() : e;
                LOG.error("❌ [AEROSPIKE-READ] readDataFromAerospike1M lỗi ngày {}: {}",
                        Utils.normalizeDateYYYYMMDDHHmm(startTime), cause.getMessage());
                throw new RuntimeException("readDataFromAerospike1M failed: " + cause.getMessage(), cause);
            }
        }
        return results;
    }

    public static TreeMap<Long, KlineObjectSimple[]> readDataFromAerospike1M_ShortKey(long startTime) {
        TreeMap<Long, KlineObjectSimple[]> results = new TreeMap<>();
        int totalRecords = 1440;

        // Tạo Key và Timestamp
        long[] allTimestamps = new long[totalRecords];
        Calendar cal = Calendar.getInstance(java.util.TimeZone.getTimeZone("GMT+7")); // HARDEN 2026-07-23: pin GMT+7 (khong phu thuoc TZ mac dinh node) - khop quy uoc key da ghi
        cal.setTimeInMillis(startTime);
        cal.set(Calendar.HOUR_OF_DAY, 7);
        cal.set(Calendar.MINUTE, 0);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);

        for (int i = 0; i < totalRecords; i++) {
            allTimestamps[i] = cal.getTimeInMillis();
            cal.add(Calendar.MINUTE, 1);
        }

        List<Future<Map<Long, KlineObjectSimple[]>>> futures = new ArrayList<>();
        int chunkSize = (totalRecords + threadCount - 1) / threadCount;

        for (int i = 0; i < threadCount; i++) {
            final int startIdx = i * chunkSize;
            final int endIdx = Math.min(startIdx + chunkSize, totalRecords);
            if (startIdx >= endIdx) break;

            futures.add(executor.submit(() -> {
                // --- FIX THREAD SAFETY: Tạo SimpleDateFormat riêng cho từng luồng ---
                SimpleDateFormat localKeyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");
                localKeyFormat.setTimeZone(java.util.TimeZone.getTimeZone("GMT+7")); // HARDEN 2026-07-23: pin GMT+7 doc key deterministic

                Map<Long, KlineObjectSimple[]> chunkResult = new HashMap<>();
                // Tạo Keys cho chunk này
                Key[] chunkKeys = new Key[endIdx - startIdx];
                long[] chunkTimestamps = Arrays.copyOfRange(allTimestamps, startIdx, endIdx);
                for (int k = 0; k < chunkKeys.length; k++) {
                    String keyString = localKeyFormat.format(new Date(chunkTimestamps[k]));
                    chunkKeys[k] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_TICKER, keyString);
                }

                // 🔁 RETRY batch read: lỗi Connection/EOFException khi đọc ticker 226 qua WAN là transient.
                // KHÔNG nuốt lỗi như trước (printStackTrace -> chunk rỗng -> FAIL-FAST "khong co ticker" OAN).
                // Hết BATCH_MAX_RETRY vẫn lỗi -> THROW để tầng trên báo đúng nguyên nhân.
                Record[] records = null;
                Exception lastError = null;
                int attempt = 0;
                while (attempt < BATCH_MAX_RETRY) {
                    attempt++;
                    try {
                        records = getReadClient().get(batchPolicy, chunkKeys);
                        if (records != null) break;
                        LOG.warn("⚠️ [AEROSPIKE] get() trả NULL chunk start={} (lần {}/{})",
                                Utils.normalizeDateYYYYMMDDHHmm(chunkTimestamps[0]), attempt, BATCH_MAX_RETRY);
                    } catch (Exception e) {
                        // Bắt AerospikeException (Connection/EOF) và mọi Exception khác của batch read.
                        lastError = e;
                        LOG.warn("⚠️ [AEROSPIKE-RETRY] {} | chunk[{}..{}] start={} keys={} lần {}/{}: {}",
                                e.getClass().getSimpleName(), startIdx, endIdx,
                                Utils.normalizeDateYYYYMMDDHHmm(chunkTimestamps[0]),
                                chunkKeys.length, attempt, BATCH_MAX_RETRY, e.getMessage());
                    }
                    if (attempt < BATCH_MAX_RETRY) {
                        try {
                            Thread.sleep(BATCH_RETRY_BACKOFF_MS * attempt); // backoff tuyến tính: 500,1000,1500...
                        } catch (InterruptedException ie) {
                            Thread.currentThread().interrupt();
                            break;
                        }
                    }
                }

                if (records == null) {
                    throw new RuntimeException(String.format(
                            "batch read failed after %d retries: chunk start=%s keys=%d cause=%s",
                            BATCH_MAX_RETRY, Utils.normalizeDateYYYYMMDDHHmm(chunkTimestamps[0]),
                            chunkKeys.length, lastError == null ? "get() trả NULL" : lastError.toString()), lastError);
                }

                try {
                    for (int j = 0; j < records.length; j++) {
                        Record record = records[j];
                        if (record == null) continue;

                        // Lấy timestamp từ mảng (Vì trong Data không còn lưu timestamp nữa)
                        long minuteTimestamp = chunkTimestamps[j];

                        byte[] snappyCompressedBytes = (byte[]) record.getValue("data");
                        if (snappyCompressedBytes != null) {
                            byte[] protoAsBytes = Snappy.uncompress(snappyCompressedBytes);
                            MinuteDataFinal protoData = MinuteDataFinal.parseFrom(protoAsBytes);

                            KlineObjectSimple[] klineArray = new KlineObjectSimple[1000];
                            for (Map.Entry<String, KlineObjectOptimized> entry : protoData.getTickersMap().entrySet()) {
                                String fullSymbol = entry.getKey().endsWith("USDT") ? entry.getKey() : entry.getKey() + "USDT";
                                // Ép sang Short ngay lập tức
                                short symbolId = SimpleSymbolMapper.getInstance().getId(fullSymbol);
                                klineArray[symbolId] = convertProtoToKline(entry.getValue(), minuteTimestamp);
                            }
                            chunkResult.put(minuteTimestamp, klineArray);
                        }
                    }
                } catch (Exception e) {
                    LOG.error("❌ [AEROSPIKE-PARSE] Lỗi giải nén/parse chunk start={}: {} {}",
                            Utils.normalizeDateYYYYMMDDHHmm(chunkTimestamps[0]), e.getClass().getSimpleName(), e.getMessage());
                    throw new RuntimeException("parse failed for chunk start="
                            + Utils.normalizeDateYYYYMMDDHHmm(chunkTimestamps[0]) + ": " + e.getMessage(), e);
                }
                return chunkResult;
            }));
        }

        // Tổng hợp kết quả — future.get() ném ExecutionException nếu chunk task THROW.
        // KHÔNG nuốt (trước đây printStackTrace) -> rethrow để FAIL-FAST báo đúng nguyên nhân batch read.
        for (Future<Map<Long, KlineObjectSimple[]>> future : futures) {
            try {
                results.putAll(future.get());
            } catch (Exception e) {
                Throwable cause = e.getCause() != null ? e.getCause() : e;
                LOG.error("❌ [AEROSPIKE-READ] readDataFromAerospike1M_ShortKey lỗi ngày {}: {}",
                        Utils.normalizeDateYYYYMMDDHHmm(startTime), cause.getMessage());
                throw new RuntimeException("readDataFromAerospike1M_ShortKey failed: " + cause.getMessage(), cause);
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
                localKeyFormat.setTimeZone(java.util.TimeZone.getTimeZone("GMT+7")); // HARDEN 2026-07-23: pin GMT+7 doc key deterministic
                Map<Long, Map<String, KlineObjectSimple>> chunkResult = new HashMap<>();

                // Tạo mảng Keys cho chunk này
                Key[] chunkKeys = new Key[endIdx - startIdx];
                long[] chunkTimestamps = Arrays.copyOfRange(allTimestamps, startIdx, endIdx);
                for (int k = 0; k < chunkKeys.length; k++) {
                    String keyString = localKeyFormat.format(new Date(chunkTimestamps[k]));
                    chunkKeys[k] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_TICKER, keyString);
                }

                // 🔁 RETRY: lỗi "Batch max requests exceeded" là transient (nhiều tiến trình cùng đọc 226).
                // Retry với backoff thay vì nuốt lỗi + trả chunk rỗng (gây MẤT DATA âm thầm).
                Record[] records = null;
                int attempt = 0;
                while (attempt < BATCH_MAX_RETRY) {
                    attempt++;
                    try {
                        records = getReadClient().get(batchPolicy, chunkKeys);
                        if (records != null) break;
                        LOG.warn("⚠️ [AEROSPIKE] get() trả NULL chunk bắt đầu {} (lần {}/{})",
                                Utils.normalizeDateYYYYMMDDHHmm(chunkTimestamps[0]), attempt, BATCH_MAX_RETRY);
                    } catch (Exception e) {
                        // Log CỤ THỂ: loại lỗi + mốc bắt đầu + số key + lần thử (yêu cầu: ghi ngoại lệ cụ thể)
                        LOG.warn("⚠️ [AEROSPIKE-RETRY] {} | chunk[{}..{}] start={} keys={} lần {}/{}: {}",
                                e.getClass().getSimpleName(),
                                startIdx, endIdx,
                                Utils.normalizeDateYYYYMMDDHHmm(chunkTimestamps[0]),
                                chunkKeys.length, attempt, BATCH_MAX_RETRY, e.getMessage());
                    }
                    try {
                        Thread.sleep(BATCH_RETRY_BACKOFF_MS * attempt); // backoff tuyến tính: 500,1000,1500...
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }

                if (records == null) {
                    // Sau hết retry vẫn fail -> MẤT DATA THẬT, log ERROR rõ ràng để validate phát hiện.
                    LOG.error("❌ [AEROSPIKE-FAIL] MẤT DATA chunk start={} keys={} sau {} lần retry",
                            Utils.normalizeDateYYYYMMDDHHmm(chunkTimestamps[0]), chunkKeys.length, BATCH_MAX_RETRY);
                    return chunkResult;
                }

                try {
                    for (int j = 0; j < records.length; j++) {
                        Record record = records[j];
                        if (record == null) continue;
                        long minuteTimestamp = chunkTimestamps[j];
                        byte[] snappyCompressedBytes = (byte[]) record.getValue("data");
                        if (snappyCompressedBytes != null) {
                            byte[] protoAsBytes = Snappy.uncompress(snappyCompressedBytes);
                            MinuteDataFinal protoData = MinuteDataFinal.parseFrom(protoAsBytes);
                            Map<String, KlineObjectSimple> javaMap = convertProtoMapToJavaMap(protoData.getTickersMap(), minuteTimestamp);
                            chunkResult.put(minuteTimestamp, javaMap);
                        }
                    }
                } catch (Exception e) {
                    LOG.error("❌ [AEROSPIKE-PARSE] Lỗi giải nén/parse chunk start={}: {} {}",
                            Utils.normalizeDateYYYYMMDDHHmm(chunkTimestamps[0]), e.getClass().getSimpleName(), e.getMessage());
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
                localKeyFormat.setTimeZone(java.util.TimeZone.getTimeZone("GMT+7")); // HARDEN 2026-07-23: pin GMT+7 doc key deterministic
                Map<Long, Map<String, KlineObjectSimple>> chunkResult = new HashMap<>();

                try {
                    Key[] chunkKeys = new Key[endIdx - startIdx];
                    long[] chunkTimestamps = Arrays.copyOfRange(allTimestamps, startIdx, endIdx);

                    for (int k = 0; k < chunkKeys.length; k++) {
                        String keyString = localKeyFormat.format(new Date(chunkTimestamps[k]));
                        chunkKeys[k] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_TICKER, keyString);
                    }

                    // Batch Read tối ưu
                    Record[] records = getReadClient() .get(batchPolicy, chunkKeys);

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
        // Ép kiểu về float theo đúng định nghĩa class cũ của bạn
        javaTicker.startTime = timestamp;

        // 2. ÉP KIỂU FLOAT (DB) -> DOUBLE (JAVA)
        javaTicker.priceOpen = (float) protoTicker.getPriceOpen();
        javaTicker.maxPrice = (float) protoTicker.getMaxPrice();
        javaTicker.minPrice = (float) protoTicker.getMinPrice();
        javaTicker.priceClose = (float) protoTicker.getPriceClose();
        javaTicker.totalUsdt = (float) protoTicker.getTotalUsdt();

        return javaTicker;
    }

    public static void closeConnection() {
        if (client242 != null) {
            client242.close();
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
            getClient242().put(writePolicy, key, new Bin("data", compressed));

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
     * Lấy DUY NHẤT 1 bản ghi AI Market Prediction tại 1 thời điểm cụ thể (Tránh Full Scan)
     */
    public static AiPredictionData getAiPredictionMarketAtTime(long timestamp) {
        try {
            // Định dạng Key phải giống hệt lúc bạn lưu vào Aerospike
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            String keyString = fmt.format(new Date(timestamp));

            // Lấy từ Set AEROSPIKE_SET_NAME_AI_PRED_MARKET (Set dùng cho HPO)
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_AI_PRED_MARKET, keyString);

            // Dùng client226 vì dữ liệu HPO lưu ở đây
            Record record = getClient226().get(null, key);

            if (record != null) {
                byte[] compressed = (byte[]) record.getValue("data");
                if (compressed != null) {
                    String json = new String(Snappy.uncompress(compressed), "UTF-8");
                    return Utils.gson.fromJson(json, AiPredictionData.class);
                }
            }
        } catch (Exception e) {
            // Dùng debug thay vì error để không spam log nếu data thiếu
            LOG.debug("Không tìm thấy data Market Pred tại: {}", timestamp);
        }
        return null;
    }

    /**
     * 2. LẤY DỮ LIỆU THEO PHÚT (READ SINGLE MINUTE)
     */
    public static AiPredictionData getAiPredictionAtTime(long timestamp) {
        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            String keyString = fmt.format(new Date(timestamp));
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_AI_PRED_1M, keyString);

            Record record = getClient242().get(null, key);
            if (record != null) {
                return parseAiRecord(record);
            }
        } catch (Exception e) {
            LOG.error("❌ Error getting AI Pred at {}: {}", timestamp, e.getMessage());
        }
        return null;
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

            getClient242().put(writePolicy, key, new Bin("data", compressed));

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

            Record record = getClient242().get(null, key);
            if (record != null) {
                byte[] compressed = (byte[]) record.getValue("data");
                if (compressed != null) {
                    byte[] rawBytes = Snappy.uncompress(compressed);
                    String json = new String(rawBytes, "UTF-8");
                    // Sử dụng TypeToken để parse về Map<Short, float[]>
                    return Utils.gson.fromJson(json, new com.google.gson.reflect.TypeToken<Map<Short, float[]>>() {
                    }.getType());
                }
            }
        } catch (Exception e) {
            LOG.error("❌ Error reading DCA Pred at {}: {}", timestamp, e.getMessage());
        }
        return null;
    }

    /**
     * 🔥 MỚI: Đọc dự báo DCA theo tháng (Batch Read đa luồng giống Ticker 1M)
     *
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
                localKeyFormat.setTimeZone(java.util.TimeZone.getTimeZone("GMT+7")); // HARDEN 2026-07-23: pin GMT+7 doc key deterministic
                Map<Long, Map<Short, float[]>> chunkResult = new HashMap<>();
                try {
                    Key[] chunkKeys = new Key[endIdx - startIdx];
                    long[] chunkTimestamps = Arrays.copyOfRange(allTimestamps, startIdx, endIdx);

                    for (int k = 0; k < chunkKeys.length; k++) {
                        String keyString = localKeyFormat.format(new Date(chunkTimestamps[k]));
                        chunkKeys[k] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_DCA_PRED, keyString);
                    }

                    // Batch Get
                    Record[] records = getClient242().get(batchPolicy, chunkKeys);

                    for (int j = 0; j < records.length; j++) {
                        Record record = records[j];
                        if (record != null) {
                            byte[] compressed = (byte[]) record.getValue("data");
                            if (compressed != null) {
                                byte[] rawBytes = Snappy.uncompress(compressed);
                                String json = new String(rawBytes, "UTF-8");
                                Map<Short, float[]> data = Utils.gson.fromJson(json, new com.google.gson.reflect.TypeToken<Map<Short, float[]>>() {
                                }.getType());
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
            boolean[] existsArray = getClient242().exists(batchPolicy, keys);

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
    // =========================================================================
    // LOGIC CHECK GIÁ & SO SÁNH (MỚI)
    // =========================================================================

    /**
     * Quét toàn bộ giá Realtime từ Aerospike (Set: AEROSPIKE_SET_NAME_PRICE).
     * Yêu cầu: Dữ liệu khi ghi phải bật 'writePolicy.sendKey = true' để lấy lại được Symbol từ Key.
     * @return Map<Symbol, Price>
     */


    /**
     * So sánh giá giữa Aerospike và Binance API
     */
    public static int checkAndComparePriceDiff() {
//        LOG.info("🚀 Bắt đầu kiểm tra lệch giá (Aerospike vs Binance API)...");

        // BƯỚC 1: Lấy giá từ Binance API trước (Để lấy danh sách Symbol chuẩn)
        long t1 = System.currentTimeMillis();
        // Map này lấy từ TickerFuturesHelper của bạn
        Map<String, Float> binPrices = com.binance.chuyennd.helper.TickerFuturesHelper.getSymbolPrice();
        long t2 = System.currentTimeMillis();
//        LOG.info("✅ Binance API: Loaded {} symbols in {}ms", binPrices.size(), (t2 - t1));

        if (binPrices.isEmpty()) {
            LOG.error("❌ Không lấy được giá từ Binance, hủy kiểm tra.");
            return 0;
        }

        // BƯỚC 2: Truyền danh sách key của Binance vào Scan Aerospike để map ngược
        Map<String, Float> asPrices = getAllPriceRealtimeLegacy(binPrices.keySet());
        long t3 = System.currentTimeMillis();
//        LOG.info("✅ Aerospike: Loaded {} symbols in {}ms", asPrices.size(), (t3 - t2));

        // BƯỚC 3: So sánh (Logic giữ nguyên)
        float totalDiffPercent = 0;
        int countChecked = 0;
        int countHighDiff = 0;
        float maxDiff = 0;
        String maxDiffSymbol = "";

//        LOG.info("⚠️ --- DANH SÁCH LỆCH GIÁ > 0.2% ---");

        for (Map.Entry<String, Float> entry : asPrices.entrySet()) {
            String symbol = entry.getKey();
            float asPrice = entry.getValue();

            if (binPrices.containsKey(symbol)) {
                float binPrice = binPrices.get(symbol);

                // Tính % lệch
                float diffAbs = Math.abs(asPrice - binPrice);
                float diffPercent = (diffAbs / binPrice) * 100f;

                totalDiffPercent += diffPercent;
                countChecked++;

                if (diffPercent > maxDiff) {
                    maxDiff = diffPercent;
                    maxDiffSymbol = symbol;
                }

                if (diffPercent > 0.2) {
//                    LOG.warn("🚨 [High Diff] {}: AS={}, Bin={}, Diff={}%",
//                            symbol,
//                            String.format("%.5f", asPrice),
//                            String.format("%.5f", binPrice),
//                            String.format("%.4f", diffPercent));
                    countHighDiff++;
                }
            }
        }

        float avgDiff = (countChecked > 0) ? (totalDiffPercent / countChecked) : 0;

        LOG.info("=========================================");
//        LOG.info("📊 TỔNG KẾT SO SÁNH GIÁ");
//        LOG.info("   - Tổng mã kiểm tra: {}", countChecked);
        LOG.info("   - So ma lech > 0.2%: {}/{}", countHighDiff, countChecked);
//        LOG.info("   - Lệch trung bình: {}%", String.format("%.5f", avgDiff));
//        LOG.info("   - Lệch lớn nhất: {} ({}%)", maxDiffSymbol, String.format("%.4f", maxDiff));
        LOG.info("=========================================");
        return countHighDiff;
    }

    public static void saveFundingPredictions1M(long timestamp, Map<Short, float[]> predictions) {
        if (predictions == null || predictions.isEmpty()) return;
        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            String keyString = fmt.format(new Date(timestamp));
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_FUNDING_PRED, keyString);

            // 🔥 THAY ĐỔI: Dùng Binary Codec thay cho JSON
            byte[] rawBytes = encodeFundingMapToBinary(predictions);
            byte[] compressed = Snappy.compress(rawBytes);

            getClient226().put(writePolicy, key, new Bin("data", compressed));
        } catch (Exception e) {
            LOG.error("❌ Error saving Funding Pred at {}: {}", timestamp, e.getMessage());
        }
    }

    /**
     * TASK-109 — Ghi selector prediction (4 cột P(win) per symbol) vào set TÙY BIẾN (mặc định set Java riêng,
     * tách khỏi set Python 039d để validate compare). Tái dùng codec float[] linh hoạt (float[4]).
     * Key = yyyyMMdd-HHmm (khớp định dạng funding). Ghi 226 (native, như funding pred).
     */
    public static void saveSelectorPredictions1M(long timestamp, Map<Short, float[]> predictions, String setName) {
        if (predictions == null || predictions.isEmpty()) return;
        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            String keyString = fmt.format(new Date(timestamp));
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, setName, keyString);
            byte[] compressed = Snappy.compress(encodeFundingMapToBinary(predictions));
            getClient226().put(writePolicy, key, new Bin("data", compressed));
        } catch (Exception e) {
            LOG.error("❌ Error saving Selector Pred at {}: {}", timestamp, e.getMessage());
        }
    }

    /**
     * Đọc dự báo Funding tại 1 thời điểm cụ thể
     */
    /**
     * Đọc funding pred 1 mốc. ⚠️ #12 (TASK-030): set {@code funding_pred} là 226-NATIVE (chỉ sinh trên 226 bởi
     * tooling/HPO) → CỐ Ý dùng {@code getClient226()}, KHÔNG phải hardcode lạc (getReadClient sẽ trỏ 242 ở live
     * → đọc rỗng + vỡ validator chạy ở dev). CHỈ dùng trong tool/validator/HPO; TUYỆT ĐỐI KHÔNG gọi từ path
     * quyết-định LIVE (live infer realtime, không đọc pred-set). Bảo vệ thêm: {@link Configs#assertLiveRuntime()}.
     *
     * @param timestamp mốc phút (ms)
     * @return map symbolId→pred (rỗng nếu thiếu record)
     */
    public static Map<Short, float[]> getFundingPredictionAtTime(long timestamp) {
        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            String keyString = fmt.format(new Date(timestamp));
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_FUNDING_PRED, keyString);

            Record record = getClient226().get(null, key);   // 226-native set (xem Javadoc #12) — KHÔNG đổi getReadClient
            if (record != null) {
                byte[] compressed = (byte[]) record.getValue("data");
                if (compressed != null) {
                    byte[] rawBytes = Snappy.uncompress(compressed);

                    // 🔥 THAY ĐỔI: Dùng Binary Codec thay cho JSON
                    return decodeFundingMapFromBinary(rawBytes);
                }
            }
        } catch (Exception e) {
            LOG.error("❌ Error reading Funding Pred at {}: {}", timestamp, e.getMessage());
        }
        return null;
    }

    /**
     * Kiểm tra nhanh danh sách timestamp đã có dữ liệu Funding chưa (Dùng cho Resume)
     */
    public static Set<Long> checkExistingFundingPredictions(List<Long> timestamps) {
        Set<Long> existing = new HashSet<>();
        if (timestamps == null || timestamps.isEmpty()) return existing;

        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            Key[] keys = new Key[timestamps.size()];

            for (int i = 0; i < timestamps.size(); i++) {
                String keyString = fmt.format(new Date(timestamps.get(i)));
                keys[i] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_FUNDING_PRED, keyString);
            }

            // Batch Exists: Chỉ kiểm tra metadata
            boolean[] existsArray = getClient226().exists(batchPolicy, keys);

            for (int i = 0; i < existsArray.length; i++) {
                if (existsArray[i]) {
                    existing.add(timestamps.get(i));
                }
            }
        } catch (Exception e) {
            LOG.error("❌ Error checking Funding existence: {}", e.getMessage());
        }
        return existing;
    }

    /**
     * Đọc dự báo Funding theo tháng (Batch Read đa luồng)
     */
    public static TreeMap<Long, Map<Short, float[]>> getFundingPredictionsForMonth(String monthStr) {
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
            LOG.info("📥 Reading Funding Pred Data for month {} ({} records)...", monthStr, totalMinutes);

            results = readFundingBatchCustom(startTime, totalMinutes);

        } catch (Exception e) {
            LOG.error("❌ Error reading Funding Month {}: {}", monthStr, e.getMessage());
        }
        return results;
    }

    /**
     * Helper: Đọc Batch Funding Data theo range thời gian
     */
    public static TreeMap<Long, Map<Short, float[]>> readFundingBatchCustom(long startTime, int totalMinutes) {
        TreeMap<Long, Map<Short, float[]>> results = new TreeMap<>();

        long[] allTimestamps = new long[totalMinutes];
        for (int i = 0; i < totalMinutes; i++) {
            allTimestamps[i] = startTime + (i * 60000L);
        }

        List<Future<Map<Long, Map<Short, float[]>>>> futures = new ArrayList<>();
        int chunkSize = (totalMinutes + threadCount - 1) / threadCount;

        for (int i = 0; i < threadCount; i++) {
            final int startIdx = i * chunkSize;
            final int endIdx = Math.min(startIdx + chunkSize, totalMinutes);
            if (startIdx >= endIdx) break;

            futures.add(executor.submit(() -> {
                SimpleDateFormat localKeyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");
                localKeyFormat.setTimeZone(java.util.TimeZone.getTimeZone("GMT+7")); // HARDEN 2026-07-23: pin GMT+7 doc key deterministic
                Map<Long, Map<Short, float[]>> chunkResult = new HashMap<>();
                try {
                    Key[] chunkKeys = new Key[endIdx - startIdx];
                    long[] chunkTimestamps = Arrays.copyOfRange(allTimestamps, startIdx, endIdx);

                    for (int k = 0; k < chunkKeys.length; k++) {
                        String keyString = localKeyFormat.format(new Date(chunkTimestamps[k]));
                        chunkKeys[k] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_FUNDING_PRED, keyString);
                    }

                    Record[] records = getClient226().get(batchPolicy, chunkKeys);

                    for (int j = 0; j < records.length; j++) {
                        Record record = records[j];
                        if (record != null) {
                            byte[] compressed = (byte[]) record.getValue("data");
                            if (compressed != null) {
                                byte[] rawBytes = Snappy.uncompress(compressed);
                                String json = new String(rawBytes, "UTF-8");
                                Map<Short, float[]> data = Utils.gson.fromJson(json, new com.google.gson.reflect.TypeToken<Map<Short, float[]>>() {
                                }.getType());
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

        for (Future<Map<Long, Map<Short, float[]>>> f : futures) {
            try {
                results.putAll(f.get());
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return results;
    }

    public static void main(String[] args) throws ParseException {
//        System.out.println(checkAndComparePriceDiff());
        Long startTime = Utils.sdfFile.parse("20210203").getTime() + 7 * Utils.TIME_HOUR;
        System.out.println(Utils.toJson(readFundingBatchCustom(startTime, 1440)));

    }


    /**
     * Ghi một Batch (Nhiều phút) kết quả Market AI Prediction vào Aerospike
     */
    public static void saveMarketAiPredictionsBatch(Map<Long, AiPredictionData> predictions) {
        saveMarketAiPredictionsBatchToSet(AEROSPIKE_SET_NAME_AI_PRED_MARKET, predictions);
    }

    /** Như saveMarketAiPredictionsBatch nhưng GHI VÀO SET tuỳ chọn (vd ai_pred_market_gate_v2).
     *  Format y hệt set gốc (key yyyyMMdd-HHmm, bin "data" = Snappy(JSON AiPredictionData), client226)
     *  để getAllMarketAiPredictionsFromAerospikeSet đọc lại + backtest dùng chung code đọc. */
    public static void saveMarketAiPredictionsBatchToSet(String setName, Map<Long, AiPredictionData> predictions) {
        if (predictions == null || predictions.isEmpty()) return;
        try {
            // GHI SONG SONG (parallelStream) như saveMarketDataBatch — ghi tuần tự từng record qua mạng
            // 226 quá chậm (~10 rec/s) làm WFO ghi 1.7M record mất hàng chục giờ. ThreadLocal fmt vì
            // SimpleDateFormat KHÔNG thread-safe.
            ThreadLocal<SimpleDateFormat> tlFmt = ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyyMMdd-HHmm"));
            predictions.entrySet().parallelStream().forEach(entry -> {
                try {
                    AiPredictionData data = entry.getValue();
                    String keyString = tlFmt.get().format(new Date(entry.getKey()));
                    Key key = new Key(Configs.AEROSPIKE_NAMESPACE, setName, keyString);
                    String json = Utils.gson.toJson(data);
                    byte[] compressed = Snappy.compress(json.getBytes("UTF-8"));
                    getClient226().put(writePolicy, key, new Bin("data", compressed));
                } catch (Exception e) {
                    LOG.error("❌ Error saving AI Pred at {} -> set {}: {}", entry.getKey(), setName, e.getMessage());
                }
            });
        } catch (Exception e) {
            LOG.error("❌ Error saving Market AI Pred Batch -> set {}: {}", setName, e.getMessage());
        }
    }

    /** Đọc full Market AI Pred từ SET tuỳ chọn (cho verify/backtest set mới). */
    public static TreeMap<Long, AiPredictionData> getAllMarketAiPredictionsFromAerospikeSet(String setName) {
        TreeMap<Long, AiPredictionData> results = new TreeMap<>();
        try {
            ScanPolicy scanPolicy = new ScanPolicy();
            scanPolicy.concurrentNodes = true;
            getClient226().scanAll(scanPolicy, Configs.AEROSPIKE_NAMESPACE, setName, (key, record) -> {
                try {
                    byte[] compressed = (byte[]) record.getValue("data");
                    if (compressed != null) {
                        String json = new String(Snappy.uncompress(compressed), "UTF-8");
                        AiPredictionData data = Utils.gson.fromJson(json, AiPredictionData.class);
                        if (data != null && data.timestamp > 0) results.put(data.timestamp, data);
                    }
                } catch (Exception ignored) { }
            }, "data");
        } catch (Exception e) {
            LOG.error("❌ Error reading Market AI Pred set {}: {}", setName, e.getMessage());
        }
        return results;
    }


    /**
     * HÀM ĐỌC FULL: Tải toàn bộ dữ liệu Market AI Prediction (Entry) từ Aerospike
     * Thay thế hoàn toàn cho việc đọc file Snappy Configs.FILE_AI_ENTRY_PREDICTIONS
     */
    public static TreeMap<Long, AiPredictionData> getAllMarketAiPredictionsFromAerospike() {
        TreeMap<Long, AiPredictionData> results = new TreeMap<>();
        try {
            LOG.info("📥 Đang tải FULL Market AI Predictions từ Aerospike (Set: {})...", AEROSPIKE_SET_NAME_AI_PRED_MARKET);

            ScanPolicy scanPolicy = new ScanPolicy();
            scanPolicy.concurrentNodes = true; // Quét song song đa luồng từ các node

            // Dùng client226 vì lúc save chúng ta đã lưu vào client226
            getClient226().scanAll(scanPolicy, Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_AI_PRED_MARKET, (key, record) -> {
                try {
                    byte[] compressed = (byte[]) record.getValue("data");
                    if (compressed != null) {
                        // Giải nén Snappy và parse JSON
                        String json = new String(Snappy.uncompress(compressed), "UTF-8");
                        AiPredictionData data = Utils.gson.fromJson(json, AiPredictionData.class);

                        // Object AiPredictionData đã chứa sẵn timestamp, ta lấy làm key luôn
                        if (data != null && data.timestamp > 0) {
                            results.put(data.timestamp, data);
                        }
                    }
                } catch (Exception e) {
                    // Bỏ qua các record lỗi cục bộ để không chết toàn bộ tiến trình
                }
            }, "data");

            LOG.info("✅ Đã tải xong {} records Market AI Predictions từ Aerospike.", results.size());
        } catch (Exception e) {
            LOG.error("❌ Lỗi khi Scan Market AI Predictions", e);
        }
        return results;
    }

    /**
     * Ghi một Batch Market Data vào Aerospike (Dùng cho ExportMarketData2File)
     */
    public static void saveMarketDataBatch(Map<Long, MarketDataObject> dataMap) {
        if (dataMap == null || dataMap.isEmpty()) return;
        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            dataMap.entrySet().parallelStream().forEach(entry -> {
                try {
                    long timestamp = entry.getKey();
                    MarketDataObject data = entry.getValue();

                    String keyString = fmt.format(new Date(timestamp));
                    Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_MARKET_DATA, keyString);
                    byte[] compressed = data.endCode();

                    getClient226().put(writePolicy, key,
                            new Bin("data", compressed),
                            new Bin("time", timestamp) // Lưu time để sau scanAll lấy lại làm Key
                    );
                } catch (Exception e) {
                    LOG.error("❌ Error saving Market Data at {}: {}", entry.getKey(), e.getMessage());
                }
            });
        } catch (Exception e) {
            LOG.error("❌ Error in saveMarketDataBatch", e);
        }
    }
    // =========================================================================
    // 🔥 MARKET DATA LEVEL (Thay thế market_level.snappy)
    // =========================================================================
// =========================================================================
    // 🔥 TỐI ƯU BINARY CHO MARKET DATA (Chỉ tốn 12 bytes)
    // =========================================================================


    /**
     * HÀM ĐỌC FULL: Tải toàn bộ dữ liệu thay thế cho đọc File (Dùng trong initData của Simulator)
     */
    public static TreeMap<Long, MarketDataObject> getAllMarketDataFromAerospike() {
        TreeMap<Long, MarketDataObject> results = new TreeMap<>();
        try {
            LOG.info("📥 Đang tải FULL Market Data từ Aerospike (Thay thế File)...");
            ScanPolicy scanPolicy = new ScanPolicy();
            scanPolicy.concurrentNodes = true; // Quét song song đa luồng từ các node AS

            getClient226().scanAll(scanPolicy, Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_MARKET_DATA, (key, record) -> {
                try {
                    Long timestamp = record.getLong("time");
                    byte[] compressed = (byte[]) record.getValue("data");

                    if (timestamp != null && compressed != null) {
                        MarketDataObject data = MarketDataObject.decodeMarketDataFromBinary(compressed);
                        results.put(timestamp, data);
                    }
                } catch (Exception e) {
                    // Bỏ qua các record bị lỗi format nếu có
                }
            }, "data", "time");

            LOG.info("✅ Đã tải xong {} records Market Data từ Aerospike.", results.size());
        } catch (Exception e) {
            LOG.error("❌ Lỗi khi Scan Market Data", e);
        }
        return results;
    }
    /**
     * HÀM ĐỌC 1 BẢN GHI: Lấy dữ liệu Market AI Prediction (Entry) tại 1 thời điểm cụ thể
     * @param timestamp Thời gian (milliseconds) cần lấy dữ liệu
     * @return AiPredictionData hoặc null nếu không tồn tại
     */
    /**
     * HÀM ĐỌC 1 BẢN GHI: Lấy dữ liệu Market Data tại 1 thời điểm cụ thể
     * * @param timestamp Thời gian (milliseconds) cần lấy dữ liệu
     *
     * @return MarketDataObject hoặc null nếu không tồn tại
     */
    public static MarketDataObject getMarketDataAtTime(long timestamp) {
        try {
            // Khởi tạo key chuẩn xác theo format đã lưu
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            String keyString = fmt.format(new Date(timestamp));
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_MARKET_DATA, keyString);

            // Dùng client226 vì set market_data đang lưu ở đây
            Record record = getClient226().get(null, key);

            if (record != null) {
                // Lấy dữ liệu từ bin "data" (bỏ qua bin "time" vì ta đã có sẵn timestamp rồi)
                byte[] compressed = (byte[]) record.getValue("data");

                if (compressed != null) {
                    // Giải nén Snappy và parse JSON theo đúng logic của hàm getAll
                    return MarketDataObject.decodeMarketDataFromBinary(compressed);
                }
            }
        } catch (Exception e) {
            LOG.error("❌ Error reading Market Data at {}: {}", timestamp, e.getMessage());
        }
        return null; // Trả về null nếu không tìm thấy hoặc có lỗi
    }

    public static long getLastTimestampFromSet(String setName) {
        final long[] maxTime = {0L};
        try {
            ScanPolicy scanPolicy = new ScanPolicy();
            scanPolicy.concurrentNodes = true;
            // 🔥 ĐIỂM QUAN TRỌNG NHẤT: Bỏ qua Data, chỉ kéo Metadata (Key) về
            scanPolicy.includeBinData = false;

            getClient226().scanAll(scanPolicy, Configs.AEROSPIKE_NAMESPACE, setName, (key, record) -> {
                if (key.userKey != null) {
                    try {
                        String keyStr = key.userKey.toString();
                        // Format chuẩn mà chúng ta đã lưu
                        SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
                        long time = fmt.parse(keyStr).getTime();

                        // Dùng synchronized vì scanAll chạy đa luồng
                        synchronized (maxTime) {
                            if (time > maxTime[0]) {
                                maxTime[0] = time;
                            }
                        }
                    } catch (Exception e) {
                        // Bỏ qua lỗi parse của các key không hợp lệ
                    }
                }
            });
        } catch (Exception e) {
            LOG.error("❌ Error scanning metadata for set: " + setName, e);
        }
        return maxTime[0];
    }


    /**
     * Mã hóa Map thành mảng Byte nguyên thủy
     */
    public static byte[] encodeFundingMapToBinary(Map<Short, float[]> map) {
        if (map == null) return new byte[0];

        // Tính toán kích thước bộ đệm (RAM) cần thiết
        int size = 4; // 4 bytes lưu số lượng phần tử của Map
        for (float[] arr : map.values()) {
            size += 2; // 2 bytes lưu Key (Short)
            size += 4; // 4 bytes lưu độ dài mảng (Int)
            size += arr.length * 4; // 4 bytes cho mỗi giá trị Float
        }

        java.nio.ByteBuffer buffer = java.nio.ByteBuffer.allocate(size);
        buffer.putInt(map.size()); // Ghi số lượng Entry

        for (Map.Entry<Short, float[]> entry : map.entrySet()) {
            buffer.putShort(entry.getKey()); // Ghi ID (Symbol)
            float[] arr = entry.getValue();
            buffer.putInt(arr.length);       // Ghi số phần tử mảng
            for (float v : arr) {
                buffer.putFloat(v);          // Ghi từng giá trị float
            }
        }
        return buffer.array();
    }

    /**
     * Giải mã từ mảng Byte nguyên thủy về lại Map
     */
    public static Map<Short, float[]> decodeFundingMapFromBinary(byte[] data) {
        if (data == null || data.length == 0) return new HashMap<>();

        java.nio.ByteBuffer buffer = java.nio.ByteBuffer.wrap(data);
        int mapSize = buffer.getInt(); // Đọc số lượng Entry

        // Cấp phát Map với dung lượng chuẩn để tránh tốn RAM resize
        Map<Short, float[]> map = new HashMap<>(mapSize);

        for (int i = 0; i < mapSize; i++) {
            short key = buffer.getShort();     // Đọc ID
            int arrLen = buffer.getInt();      // Đọc độ dài mảng
            float[] arr = new float[arrLen];
            for (int j = 0; j < arrLen; j++) {
                arr[j] = buffer.getFloat();    // Đọc từng float
            }
            map.put(key, arr);
        }
        return map;
    }

    public static void setThreadCount(int i) {
        threadCount = i;
    }

    /**
     * HÀM ĐỌC 1 BẢN GHI: Lấy dữ liệu Market AI Prediction (Entry) tại 1 thời điểm cụ thể
     *
     * @param timestamp Thời gian (milliseconds) cần lấy dữ liệu
     * @return AiPredictionData hoặc null nếu không tồn tại
     */
    public static AiPredictionData getMarketAiPredictionAtTime(long timestamp) {
        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            String keyString = fmt.format(new Date(timestamp));
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_AI_PRED_MARKET, keyString);

            // Dùng client226 vì set ai_pred_market đang lưu ở đây
            Record record = getClient226().get(null, key);

            if (record != null) {
                byte[] compressed = (byte[]) record.getValue("data");
                if (compressed != null) {
                    // Giải nén Snappy và parse JSON
                    byte[] uncompressed = Snappy.uncompress(compressed);
                    String json = new String(uncompressed, "UTF-8");
                    return Utils.gson.fromJson(json, AiPredictionData.class);
                }
            }
        } catch (Exception e) {
            LOG.error("❌ Error reading Market AI Pred at {}: {}", timestamp, e.getMessage());
        }
        return null;
    }

    /**
     * TỐI ƯU RAM HPO: Đọc Map Funding chuyển thành mảng long nguyên thủy (Bitwise Packing)
     * Đóng gói (Short symbolId + Float pred[0]) vào 1 biến long.
     */
    public static long[] decodeFundingMapToPrimitiveArray(byte[] data) {
        if (data == null || data.length == 0) return new long[0];

        java.nio.ByteBuffer buffer = java.nio.ByteBuffer.wrap(data);
        int mapSize = buffer.getInt(); // Đọc số lượng Entry

        long[] result = new long[mapSize];

        for (int i = 0; i < mapSize; i++) {
            short symbolId = buffer.getShort();     // Đọc ID
            int arrLen = buffer.getInt();           // Đọc độ dài mảng float

            float firstPred = 0f;
            if (arrLen > 0) {
                firstPred = buffer.getFloat();      // Chỉ lấy giá trị pred[0]
            }

            // Bỏ qua các phần tử float còn lại (nếu có) để nhảy đến record tiếp theo
            for (int j = 1; j < arrLen; j++) {
                buffer.getFloat();
            }

            // ĐÓNG GÓI: 16 bit đầu là symbolId, 32 bit cuối là bit của float
            long encoded = ((long) symbolId << 32) | (Float.floatToRawIntBits(firstPred) & 0xFFFFFFFFL);
            result[i] = encoded;
        }
        return result;
    }

    /**
     * SELECTOR: decode map nhị phân lấy ĐÚNG 1 cột horizon (selector ghi 4 float/coin:
     * idx 0=4h, 1=12h, 2=24h, 3=72h). Đóng gói (symbolId&lt;&lt;32 | floatBits(score)).
     * ⚠️ ĐẢO DẤU NGỮ NGHĨA: funding cũ "điểm THẤP = ưu tiên vào lệnh" (engine sort tăng dần + cắt khi
     * vượt maxThres). Selector P(win) thì "CAO = tốt" (ngược). Để engine tái dùng nguyên logic + ngưỡng
     * mà KHÔNG sửa, ta đóng gói score = (1 - P(win)): P(win) cao → score thấp → engine ưu tiên. Khi đó
     * ngưỡng maxThres của engine mang nghĩa "score tối đa" = (1 - P(win) tối thiểu).
     * Coin có arrLen &lt;= horizonIdx (thiếu cột) bị BỎ QUA (không cho vào kết quả).
     */
    public static long[] decodeSelectorMapToPrimitiveArray(byte[] data, int horizonIdx) {
        if (data == null || data.length == 0) return new long[0];

        java.nio.ByteBuffer buffer = java.nio.ByteBuffer.wrap(data);
        int mapSize = buffer.getInt();

        long[] tmp = new long[mapSize];
        int n = 0;
        for (int i = 0; i < mapSize; i++) {
            short symbolId = buffer.getShort();
            int arrLen = buffer.getInt();
            float pred = Float.NaN;
            for (int j = 0; j < arrLen; j++) {
                float v = buffer.getFloat();
                if (j == horizonIdx) pred = v;
            }
            if (!Float.isNaN(pred)) {
                float score = 1.0f - pred;   // ĐẢO DẤU: P(win) cao → score thấp (khớp "thấp=ưu tiên" của engine)
                tmp[n++] = ((long) symbolId << 32) | (Float.floatToRawIntBits(score) & 0xFFFFFFFFL);
            }
        }
        return n == mapSize ? tmp : java.util.Arrays.copyOf(tmp, n);
    }

    /**
     * SELECTOR: scan toàn bộ set selector trên 226, lấy 1 cột horizon -&gt; TreeMap mốc -&gt; long[]
     * (cùng format funding để engine dùng chung). READ-ONLY trên 226.
     *
     * @param setName    set selector (vd funding_selector_pred_1m_v2)
     * @param horizonIdx 0=4h, 1=12h, 2=24h, 3=72h
     */
    public static TreeMap<Long, long[]> getAllSelectorPredictionsPrimitiveFromAerospike(String setName, int horizonIdx) {
        LOG.info("📥 Đang tải FULL Selector Pred (set={}, horizonIdx={}) bằng ScanAll...", setName, horizonIdx);
        java.util.concurrent.ConcurrentSkipListMap<Long, long[]> concurrentResults = new java.util.concurrent.ConcurrentSkipListMap<>();
        try {
            ScanPolicy scanPolicy = new ScanPolicy();
            scanPolicy.concurrentNodes = true;
            getClient226().scanAll(scanPolicy, Configs.AEROSPIKE_NAMESPACE, setName, (key, record) -> {
                try {
                    byte[] compressed = (byte[]) record.getValue("data");
                    if (compressed != null && key.userKey != null) {
                        long timestamp = tlKeyFormat.get().parse(key.userKey.toString()).getTime();
                        byte[] rawBytes = org.xerial.snappy.Snappy.uncompress(compressed);
                        long[] primitives = decodeSelectorMapToPrimitiveArray(rawBytes, horizonIdx);
                        concurrentResults.put(timestamp, primitives);
                    }
                } catch (Exception e) {
                    LOG.warn("Bỏ qua record selector lỗi: {}", e.getMessage());
                }
            }, "data");
            LOG.info("✅ Đã Scan xong {} records Selector Pred (set={}).", concurrentResults.size(), setName);
        } catch (Exception e) {
            LOG.error("❌ Lỗi khi Scan Selector Pred set={}", setName, e);
        }
        return new TreeMap<>(concurrentResults);
    }

    /**
     * DÀNH RIÊNG CHO HPO: Đọc Funding Data và nén thành mảng long[] nguyên thủy
     */
    public static TreeMap<Long, long[]> getFundingPredictionsPrimitiveByRange(long startTime, int totalMinutes) {
        LOG.info("📥 [HPO OPTIMIZED] Đang tải AI Symbol Predictions (Set: {} from: {} records: {})...",
                AEROSPIKE_SET_NAME_FUNDING_PRED, Utils.normalizeDateYYYYMMDDHHmm(startTime), totalMinutes);

        TreeMap<Long, long[]> results = new TreeMap<>();
        long[] allTimestamps = new long[totalMinutes];
        for (int i = 0; i < totalMinutes; i++) allTimestamps[i] = startTime + (i * 60000L);

        List<java.util.concurrent.Future<Map<Long, long[]>>> futures = new ArrayList<>();
        int chunkSize = (totalMinutes + threadCount - 1) / threadCount;
        int SUB_BATCH_SIZE = 5000;

        for (int i = 0; i < threadCount; i++) {
            final int startIdx = i * chunkSize;
            final int endIdx = Math.min(startIdx + chunkSize, totalMinutes);
            if (startIdx >= endIdx) break;

            futures.add(executor.submit(() -> {
                SimpleDateFormat localKeyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");
                localKeyFormat.setTimeZone(java.util.TimeZone.getTimeZone("GMT+7")); // HARDEN 2026-07-23: pin GMT+7 doc key deterministic
                Map<Long, long[]> chunkResult = new HashMap<>();
                long[] chunkTimestamps = Arrays.copyOfRange(allTimestamps, startIdx, endIdx);

                for (int j = 0; j < chunkTimestamps.length; j += SUB_BATCH_SIZE) {
                    int limit = Math.min(j + SUB_BATCH_SIZE, chunkTimestamps.length);
                    Key[] subKeys = new Key[limit - j];
                    for (int k = 0; k < subKeys.length; k++) {
                        subKeys[k] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_FUNDING_PRED,
                                localKeyFormat.format(new java.util.Date(chunkTimestamps[j + k])));
                    }

                    try {
                        Record[] records = getClient226().get(batchPolicy, subKeys);
                        if (records != null) {
                            for (int r = 0; r < records.length; r++) {
                                if (records[r] != null) {
                                    byte[] compressed = (byte[]) records[r].getValue("data");
                                    if (compressed != null) {
                                        byte[] rawBytes = org.xerial.snappy.Snappy.uncompress(compressed);
                                        // Gọi hàm decode ra long[] mà bạn đã viết
                                        chunkResult.put(chunkTimestamps[j + r], decodeFundingMapToPrimitiveArray(rawBytes));
                                    }
                                }
                            }
                        }
                    } catch (Exception e) {
                    }
                }
                return chunkResult;
            }));
        }

        for (java.util.concurrent.Future<Map<Long, long[]>> f : futures) {
            try {
                results.putAll(f.get());
            } catch (Exception e) {
            }
        }
        LOG.info("✅ Đã load xong {} records Funding Pred (Primitive Optimized).", results.size());
        return results;
    }
    // =========================================================================
    // 🔥🔥 KAGGLE EXPORT BATCH READERS (READ BY RANGE) 🔥🔥
    // =========================================================================

    /**
     * DÀNH CHO KAGGLE EXPORT: Đọc Market Data theo Range thời gian (Multi-thread, Sub-batching)
     * Set: AEROSPIKE_SET_NAME_MARKET_DATA
     */
    public static TreeMap<Long, MarketDataObject> getMarketDataByRange(long startTime, int totalMinutes) {
        LOG.info("📥 [KAGGLE EXPORT] Đang tải Market Data (Set: {} from: {} records: {})...",
                AEROSPIKE_SET_NAME_MARKET_DATA, Utils.normalizeDateYYYYMMDDHHmm(startTime), totalMinutes);

        TreeMap<Long, MarketDataObject> results = new TreeMap<>();
        long[] allTimestamps = new long[totalMinutes];
        for (int i = 0; i < totalMinutes; i++) allTimestamps[i] = startTime + (i * 60000L);

        List<java.util.concurrent.Future<Map<Long, MarketDataObject>>> futures = new ArrayList<>();
        int chunkSize = (totalMinutes + threadCount - 1) / threadCount;
        int SUB_BATCH_SIZE = 5000;

        for (int i = 0; i < threadCount; i++) {
            final int startIdx = i * chunkSize;
            final int endIdx = Math.min(startIdx + chunkSize, totalMinutes);
            if (startIdx >= endIdx) break;

            futures.add(executor.submit(() -> {
                SimpleDateFormat localKeyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");
                localKeyFormat.setTimeZone(java.util.TimeZone.getTimeZone("GMT+7")); // HARDEN 2026-07-23: pin GMT+7 doc key deterministic
                Map<Long, MarketDataObject> chunkResult = new HashMap<>();
                long[] chunkTimestamps = Arrays.copyOfRange(allTimestamps, startIdx, endIdx);

                for (int j = 0; j < chunkTimestamps.length; j += SUB_BATCH_SIZE) {
                    int limit = Math.min(j + SUB_BATCH_SIZE, chunkTimestamps.length);
                    Key[] subKeys = new Key[limit - j];
                    for (int k = 0; k < subKeys.length; k++) {
                        subKeys[k] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_MARKET_DATA,
                                localKeyFormat.format(new java.util.Date(chunkTimestamps[j + k])));
                    }

                    try {
                        Record[] records = getClient226().get(batchPolicy, subKeys);
                        if (records != null) {
                            for (int r = 0; r < records.length; r++) {
                                if (records[r] != null) {
                                    byte[] compressed = (byte[]) records[r].getValue("data");
                                    if (compressed != null) {
                                        // Sử dụng hàm giải nén có sẵn của MarketDataObject
                                        MarketDataObject data = MarketDataObject.decodeMarketDataFromBinary(compressed);
                                        if (data != null) {
                                            chunkResult.put(chunkTimestamps[j + r], data);
                                        }
                                    }
                                }
                            }
                        }
                    } catch (Exception e) {
                        LOG.error("Lỗi khi đọc batch Market Data", e);
                    }
                }
                return chunkResult;
            }));
        }

        for (java.util.concurrent.Future<Map<Long, MarketDataObject>> f : futures) {
            try {
                results.putAll(f.get());
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        LOG.info("✅ Đã load xong {} records Market Data.", results.size());
        return results;
    }

    /**
     * DÀNH CHO KAGGLE EXPORT: Đọc Market AI Prediction (Entry) theo Range thời gian (Multi-thread, Sub-batching)
     * Set: AEROSPIKE_SET_NAME_AI_PRED_MARKET
     */
    public static TreeMap<Long, AiPredictionData> getMarketAiPredictionsByRange(long startTime, int totalMinutes) {
        LOG.info("📥 [KAGGLE EXPORT] Đang tải AiPredictionData (Set: {} from: {} records: {})...",
                AEROSPIKE_SET_NAME_AI_PRED_MARKET, Utils.normalizeDateYYYYMMDDHHmm(startTime), totalMinutes);

        TreeMap<Long, AiPredictionData> results = new TreeMap<>();
        long[] allTimestamps = new long[totalMinutes];
        for (int i = 0; i < totalMinutes; i++) allTimestamps[i] = startTime + (i * 60000L);

        List<java.util.concurrent.Future<Map<Long, AiPredictionData>>> futures = new ArrayList<>();
        int chunkSize = (totalMinutes + threadCount - 1) / threadCount;
        int SUB_BATCH_SIZE = 5000;

        for (int i = 0; i < threadCount; i++) {
            final int startIdx = i * chunkSize;
            final int endIdx = Math.min(startIdx + chunkSize, totalMinutes);
            if (startIdx >= endIdx) break;

            futures.add(executor.submit(() -> {
                SimpleDateFormat localKeyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");
                localKeyFormat.setTimeZone(java.util.TimeZone.getTimeZone("GMT+7")); // HARDEN 2026-07-23: pin GMT+7 doc key deterministic
                Map<Long, AiPredictionData> chunkResult = new HashMap<>();
                long[] chunkTimestamps = Arrays.copyOfRange(allTimestamps, startIdx, endIdx);

                for (int j = 0; j < chunkTimestamps.length; j += SUB_BATCH_SIZE) {
                    int limit = Math.min(j + SUB_BATCH_SIZE, chunkTimestamps.length);
                    Key[] subKeys = new Key[limit - j];
                    for (int k = 0; k < subKeys.length; k++) {
                        subKeys[k] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_AI_PRED_MARKET,
                                localKeyFormat.format(new java.util.Date(chunkTimestamps[j + k])));
                    }

                    try {
                        Record[] records = getClient226().get(batchPolicy, subKeys);
                        if (records != null) {
                            for (int r = 0; r < records.length; r++) {
                                if (records[r] != null) {
                                    byte[] compressed = (byte[]) records[r].getValue("data");
                                    if (compressed != null) {
                                        // Giải nén Snappy và Parse Json -> AiPredictionData
                                        byte[] uncompressed = org.xerial.snappy.Snappy.uncompress(compressed);
                                        String json = new String(uncompressed, "UTF-8");
                                        AiPredictionData data = Utils.gson.fromJson(json, AiPredictionData.class);
                                        if (data != null) {
                                            chunkResult.put(chunkTimestamps[j + r], data);
                                        }
                                    }
                                }
                            }
                        }
                    } catch (Exception e) {
                        LOG.error("Lỗi khi đọc batch AI Prediction", e);
                    }
                }
                return chunkResult;
            }));
        }

        for (java.util.concurrent.Future<Map<Long, AiPredictionData>> f : futures) {
            try {
                results.putAll(f.get());
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        LOG.info("✅ Đã load xong {} records AiPredictionData.", results.size());
        return results;
    }

    // Dùng ThreadLocal để format ngày tháng an toàn trong môi trường đa luồng của ScanAll
    private static final ThreadLocal<SimpleDateFormat> tlKeyFormat = ThreadLocal.withInitial(() -> {
        SimpleDateFormat f = new SimpleDateFormat("yyyyMMdd-HHmm");
        f.setTimeZone(java.util.TimeZone.getTimeZone("GMT+7")); // 🕐 Lớp 1: pin GMT+7
        return f;
    });

    /**
     * 🔥 TỐI ƯU RAM/SPEED: Dùng ScanAll để load 5 năm dữ liệu thay vì Batch Get
     */
    public static TreeMap<Long, long[]> getAllFundingPredictionsPrimitiveFromAerospike() {
        LOG.info("📥 Đang tải FULL Funding Pred từ Aerospike bằng ScanAll (Siêu tốc)...");
        // Dùng ConcurrentSkipListMap để hứng dữ liệu an toàn từ nhiều luồng, tự động sort key
        java.util.concurrent.ConcurrentSkipListMap<Long, long[]> concurrentResults = new java.util.concurrent.ConcurrentSkipListMap<>();

        try {
            ScanPolicy scanPolicy = new ScanPolicy();
            scanPolicy.concurrentNodes = true; // Quét song song đa luồng

            getClient226().scanAll(scanPolicy, Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_FUNDING_PRED, (key, record) -> {
                try {
                    byte[] compressed = (byte[]) record.getValue("data");
                    if (compressed != null && key.userKey != null) {
                        // Parse timestamp từ key (Ví dụ: "20210101-0700")
                        long timestamp = tlKeyFormat.get().parse(key.userKey.toString()).getTime();

                        // Giải nén & Decode ra primitive array
                        byte[] rawBytes = org.xerial.snappy.Snappy.uncompress(compressed);
                        long[] primitives = decodeFundingMapToPrimitiveArray(rawBytes);

                        concurrentResults.put(timestamp, primitives);
                    }
                } catch (Exception e) {
                    // Bỏ qua record lỗi
                }
            }, "data");

            LOG.info("✅ Đã Scan xong {} records Funding Pred.", concurrentResults.size());
        } catch (Exception e) {
            LOG.error("❌ Lỗi khi Scan Funding Pred", e);
        }

        // Trả về TreeMap thông thường để dùng O(1) ở Simulator
        return new TreeMap<>(concurrentResults);
    }

    /**
     * Client ĐỌC dữ liệu-nguồn-trên-242 (ticker, symbol_mapper, funding_data). TASK-112: chọn cluster
     * TƯỜNG MINH theo config per-box {@code AEROSPIKE_READ_CLUSTER} (226=box backtest/Oracle đọc bản sao,
     * 242=live đọc gốc) — không còn flag runtime mode cũ (kaggle/HPO). Thiếu key / giá trị lạ →
     * fail-fast NGAY tại đây (lazy — box thuần file như Kaggle không cần khai key này).
     * CHỈ áp cho ĐỌC — mọi đường GHI giữ nguyên 242.
     * (market_data/ai_pred_market/funding_pred dùng getClient226() trực tiếp vì vốn nằm trên 226.)
     *
     * @return client Aerospike theo {@code AEROSPIKE_READ_CLUSTER}
     * @throws IllegalStateException nếu config thiếu hoặc khác 226/242
     */
    public static AerospikeClient getReadClient() {
        String cluster = Configs.AEROSPIKE_READ_CLUSTER;
        if ("226".equals(cluster)) {
            return getClient226();
        }
        if ("242".equals(cluster)) {
            return getClient242();
        }
        throw new IllegalStateException("Thieu/sai AEROSPIKE_READ_CLUSTER trong config.properties (hien tai: " + cluster
                + ") — them dong: AEROSPIKE_READ_CLUSTER=226 (box backtest/Oracle) hoac AEROSPIKE_READ_CLUSTER=242 (live).");
    }

    /**
     * Đọc funding pred (giải mã long-packed: symbolId&lt;&lt;32 | floatBits của pred[0]) cho DANH SÁCH
     * timestamp cụ thể từ SET chỉ định — phục vụ so sánh set (v5 vs v6) / sampling thưa. Tái dùng
     * decodeFundingMapToPrimitiveArray (cùng bit-layout cho mọi set len=1). Đọc trên 226. READ-ONLY.
     *
     * @param setName    tên set (vd funding_pred_1m_v5 / funding_pred_1m_20260606)
     * @param timestamps các mốc phút cần đọc (ms)
     * @return TreeMap mốc -&gt; long[] đã đóng gói; phút thiếu record bị bỏ qua
     */
    public static TreeMap<Long, long[]> getFundingPredsForTimestamps(String setName, long[] timestamps) {
        TreeMap<Long, long[]> results = new TreeMap<>();
        if (timestamps == null || timestamps.length == 0) return results;
        SimpleDateFormat keyFmt = new SimpleDateFormat("yyyyMMdd-HHmm");
        Key[] keys = new Key[timestamps.length];
        for (int i = 0; i < timestamps.length; i++) {
            keys[i] = new Key(Configs.AEROSPIKE_NAMESPACE, setName, keyFmt.format(new java.util.Date(timestamps[i])));
        }
        // ⚠️ #12 (TASK-030): set funding_pred là 226-NATIVE → CỐ Ý getClient226() (KHÔNG getReadClient: ở live trỏ 242
        // → rỗng, ở dev validator KHÔNG bật kaggle-mode cũng trỏ 242 → vỡ). Chỉ tool/validator/HPO gọi; KHÔNG từ live.
        Record[] records = getClient226().get(batchPolicy, keys);
        if (records == null) return results;
        for (int i = 0; i < records.length; i++) {
            if (records[i] == null) continue;
            byte[] data = (byte[]) records[i].getValue("data");
            if (data == null) continue;
            try {
                // "data" lưu dạng Snappy(compress(binary)) — phải GIẢI NÉN trước khi decode (mirror scanAll).
                byte[] raw = org.xerial.snappy.Snappy.uncompress(data);
                long[] arr = decodeFundingMapToPrimitiveArray(raw);
                if (arr.length > 0) results.put(timestamps[i], arr);
            } catch (Exception e) {
                // record lỗi/format lạ -> bỏ qua (giống scanAll), không làm gãy cả batch
            }
        }
        return results;
    }
}