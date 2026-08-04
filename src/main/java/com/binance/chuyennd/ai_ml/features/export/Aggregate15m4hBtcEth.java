package com.binance.chuyennd.ai_ml.features.export;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import com.google.gson.reflect.TypeToken;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.lang.reflect.Type;
import java.util.*;

/**
 * TASK-009 — aggregate nến 15m + 4h cho BTC/ETH TỪ {@code kline_1m_opt} (KHÔNG fetch Binance riêng → không skew).
 *
 * Biên khung theo UTC = floor(epochMs / frameMs) (epoch tuyệt đối nên tự khớp 00:00/00:15 và 00/04/08… UTC).
 * Quy tắc: open=1m đầu khung, high=max(maxPrice), low=min(minPrice), close=1m cuối khung, vol=Σ totalUsdt.
 * Khung THIẾU phút (<15 / <240) → skip + đếm (không tạo nến nửa vời).
 *
 * Lưu: set kline_15m_btceth / kline_4h_btceth, key=symbol, bin "data"=Snappy(gson(TreeMap&lt;startMs,float[o,h,l,c,v]&gt;)).
 * Ghi CẢ 226 (train) + 242 (live). Đọc-only kline_1m_opt — cluster chọn THẲNG theo arg (TASK-112 #9: mặc định 226, arg "242" → 242).
 */
public class Aggregate15m4hBtcEth {

    private static final Logger LOG = LoggerFactory.getLogger(Aggregate15m4hBtcEth.class);
    private static final String[] SYMBOLS = {"BTCUSDT", "ETHUSDT"};
    private static final long MS_15M = 15L * 60_000L, MS_4H = 240L * 60_000L;
    private static final int N_15M = 15, N_4H = 240;
    private static final String SET_15M = "kline_15m_btceth", SET_4H = "kline_4h_btceth";
    private static final String START_DATE = "20210101";
    private static final Type SERIES_TYPE = new TypeToken<TreeMap<Long, float[]>>() {}.getType();

    /** Accumulator 1 khung. */
    private static class Acc {
        long openEpoch = Long.MAX_VALUE, closeEpoch = Long.MIN_VALUE;
        float open, close, high = Float.NEGATIVE_INFINITY, low = Float.POSITIVE_INFINITY, vol = 0f;
        int count = 0;
        void add(long epoch, KlineObjectSimple k) {
            if (epoch < openEpoch) { openEpoch = epoch; open = k.priceOpen; }
            if (epoch > closeEpoch) { closeEpoch = epoch; close = k.priceClose; }
            high = Math.max(high, k.maxPrice); low = Math.min(low, k.minPrice);
            vol += k.totalUsdt; count++;
        }
        float[] ohlcv() { return new float[]{open, high, low, close, vol}; }
    }

    public static void main(String[] args) {
        try {
            // TASK-033 lấp-gap: arg "242" → đọc 1m@242 (LIVE, tươi) cho forward gap-fill (15m/4h@242 dừng 06-07,
            // mà 1m@226 cũng dừng 06-07 nên KHÔNG lấp được). Mặc định (không arg) → 226 cho backtest historical (TASK-009).
            // writeSeries vẫn ghi CẢ 226+242. ⚠️ Chỉ THÁNG có nến mới bị overwrite; tháng 242 thiếu 1m → KHÔNG đụng
            // (byMonth không chứa). Nhưng THÁNG BIÊN (242 có 1m một phần) sẽ ghi đè bằng series một-phần → MẤT phần cũ
            // của tháng đó. ⇒ chạy 242-mode CHỈ khi 1m@242 đủ sâu (xem runbook TASK-033: verify độ sâu 1m@242 trước).
            boolean read242 = args.length > 0 && "242".equalsIgnoreCase(args[0]);
            // TASK-112 #9: tool chọn cluster ĐỘNG theo arg runtime (không phải per-box) → gọi THẲNG
            // getClientOracle/242, KHÔNG đi qua getReadClient()/AEROSPIKE_READ_CLUSTER.
            com.aerospike.client.AerospikeClient readClient = read242
                    ? DataManagerAerospikeFloatSim.getClient242()
                    : DataManagerAerospikeFloatSim.getClientOracle();
            long start = Utils.sdfFile.parse(START_DATE).getTime() + 7 * Utils.TIME_HOUR;
            long end = System.currentTimeMillis();
            LOG.info("🧱 Aggregate 15m/4h BTC/ETH từ kline_1m_opt ({}) | {} → nay | ghi 226+242",
                    read242 ? "242 LIVE — forward gap-fill" : "226 backtest", START_DATE);

            // accumulators per symbol per interval
            Map<String, TreeMap<Long, Acc>> acc15 = new HashMap<>(), acc4 = new HashMap<>();
            for (String s : SYMBOLS) { acc15.put(s, new TreeMap<>()); acc4.put(s, new TreeMap<>()); }

            int days = 0;
            for (long day = start; day < end; day += 24L * Utils.TIME_HOUR) {
                TreeMap<Long, Map<String, KlineObjectSimple>> oneDay = DataManagerAerospikeFloatSim.readDataFromAerospike1M(day, readClient);
                for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : oneDay.entrySet()) {
                    long epoch = e.getKey();
                    Map<String, KlineObjectSimple> m = e.getValue();
                    for (String s : SYMBOLS) {
                        KlineObjectSimple k = m.get(s);
                        if (!Utils.isTickerAvailable(k)) continue;
                        acc15.get(s).computeIfAbsent(epoch / MS_15M * MS_15M, x -> new Acc()).add(epoch, k);
                        acc4.get(s).computeIfAbsent(epoch / MS_4H * MS_4H, x -> new Acc()).add(epoch, k);
                    }
                }
                if (++days % 200 == 0) LOG.info("   ... {} ngày, {}", days, Utils.normalizeDateYYYYMMDD(day));
            }

            for (String s : SYMBOLS) {
                writeSeries(s, SET_15M, finalize(acc15.get(s), N_15M, s, "15m"));
                writeSeries(s, SET_4H, finalize(acc4.get(s), N_4H, s, "4h"));
            }
            validate(acc15, acc4);
            LOG.info("✅ TASK-009 aggregate xong.");
        } catch (Exception e) {
            LOG.error("Aggregate15m4hBtcEth lỗi", e);
            System.exit(1);
        }
        // BẪY non-daemon thread: AerospikeClient để lại thread sống → JVM KHÔNG tự thoát sau khi main xong việc
        // (job treo dù log "✅ xong"). Ép thoát (giống TASK-015/recipe Kaggle). Đặt SAU try để chạy mọi đường thành công.
        System.exit(0);
    }

    /** Lọc khung đủ phút → TreeMap<startMs, ohlcv>. Khung thiếu → skip + đếm. */
    private static TreeMap<Long, float[]> finalize(TreeMap<Long, Acc> acc, int need, String sym, String tf) {
        TreeMap<Long, float[]> series = new TreeMap<>();
        int dropped = 0;
        for (Map.Entry<Long, Acc> e : acc.entrySet()) {
            if (e.getValue().count == need) series.put(e.getKey(), e.getValue().ohlcv());
            else dropped++;
        }
        LOG.info("📊 {} {}: {} nến đủ, {} khung thiếu phút (skip). range {} → {}",
                sym, tf, series.size(), dropped,
                series.isEmpty() ? "-" : Utils.normalizeDateYYYYMMDD(series.firstKey()),
                series.isEmpty() ? "-" : Utils.normalizeDateYYYYMMDD(series.lastKey()));
        return series;
    }

    private static final ThreadLocal<java.text.SimpleDateFormat> MONTH =
            ThreadLocal.withInitial(() -> new java.text.SimpleDateFormat("yyyyMM")); // GMT+7

    /** Ghi CHUNK theo THÁNG (1 record toàn series vượt giới hạn Aerospike). key = SYMBOL-YYYYMM. CẢ 226+242. */
    private static void writeSeries(String symbol, String set, TreeMap<Long, float[]> series) throws Exception {
        Map<String, TreeMap<Long, float[]>> byMonth = new LinkedHashMap<>();
        for (Map.Entry<Long, float[]> e : series.entrySet())
            byMonth.computeIfAbsent(MONTH.get().format(new Date(e.getKey())), k -> new TreeMap<>()).put(e.getKey(), e.getValue());
        WritePolicy w = new WritePolicy();
        w.expiration = 0; w.sendKey = true; w.recordExistsAction = RecordExistsAction.UPDATE;
        int recs = 0, maxBytes = 0;
        for (Map.Entry<String, TreeMap<Long, float[]>> e : byMonth.entrySet()) {
            byte[] comp = Snappy.compress(Utils.gson.toJson(e.getValue()).getBytes("UTF-8"));
            maxBytes = Math.max(maxBytes, comp.length);
            for (AerospikeClient c : new AerospikeClient[]{DataManagerAerospikeFloatSim.getClientOracle(), DataManagerAerospikeFloatSim.getClient242()}) {
                c.put(w, new Key(Configs.AEROSPIKE_NAMESPACE, set, symbol + "-" + e.getKey()), new Bin("data", comp));
            }
            recs++;
        }
        LOG.info("💾 {}/{}: {} record-tháng → 226+242 ({} nến, max {} bytes/tháng)", set, symbol, recs, series.size(), maxBytes);
    }

    private static float[] readStored(String set, String symbol, long fs) throws Exception {
        Record r = DataManagerAerospikeFloatSim.getClient242().get(null,
                new Key(Configs.AEROSPIKE_NAMESPACE, set, symbol + "-" + MONTH.get().format(new Date(fs))));
        if (r == null) return null;
        TreeMap<Long, float[]> m = Utils.gson.fromJson(new String(Snappy.uncompress((byte[]) r.getValue("data")), "UTF-8"), SERIES_TYPE);
        return m == null ? null : m.get(fs);
    }

    /** Validate recompute-compare: đọc lại series từ 242 + so accumulator gốc vài khung. */
    private static void validate(Map<String, TreeMap<Long, Acc>> acc15, Map<String, TreeMap<Long, Acc>> acc4) throws Exception {
        for (String s : SYMBOLS) {
            checkOne(s, SET_15M, N_15M, acc15.get(s));
            checkOne(s, SET_4H, N_4H, acc4.get(s));
        }
    }

    private static void checkOne(String symbol, String set, int need, TreeMap<Long, Acc> acc) throws Exception {
        // chọn 4 khung đủ: đầu, 1/3, 2/3, cuối
        List<Long> full = new ArrayList<>();
        for (Map.Entry<Long, Acc> e : acc.entrySet()) if (e.getValue().count == need) full.add(e.getKey());
        if (full.isEmpty()) { LOG.warn("⚠️ {}/{}: không có khung đủ để validate", set, symbol); return; }
        long[] picks = {full.get(0), full.get(full.size() / 3), full.get(full.size() * 2 / 3), full.get(full.size() - 1)};
        int ok = 0;
        for (long fs : picks) {
            float[] stored = readStored(set, symbol, fs);
            Acc a = acc.get(fs);
            float[] re = a.ohlcv();
            boolean match = stored != null && eq(stored[0], re[0]) && eq(stored[1], re[1]) && eq(stored[2], re[2]) && eq(stored[3], re[3]) && eq(stored[4], re[4]);
            if (match) ok++;
            else LOG.error("   🔴 {}/{} khung {}: stored={} vs acc={}", set, symbol, Utils.normalizeDateYYYYMMDD(fs), Arrays.toString(stored), Arrays.toString(re));
        }
        // recompute ĐỘC LẬP khung đầu: đọc lại raw 1m, tính O/H/L/C/V bằng đường khác → so stored
        long fs0 = picks[0];
        TreeMap<Long, Map<String, KlineObjectSimple>> raw = DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(fs0, need);
        Long minE = null, maxE = null; float hi = Float.NEGATIVE_INFINITY, lo = Float.POSITIVE_INFINITY, v = 0f, op = 0f, cl = 0f; int cnt = 0;
        for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : raw.entrySet()) {
            KlineObjectSimple k = e.getValue().get(symbol);
            if (!Utils.isTickerAvailable(k)) continue;
            long ep = e.getKey();
            if (minE == null || ep < minE) { minE = ep; op = k.priceOpen; }
            if (maxE == null || ep > maxE) { maxE = ep; cl = k.priceClose; }
            hi = Math.max(hi, k.maxPrice); lo = Math.min(lo, k.minPrice); v += k.totalUsdt; cnt++;
        }
        float[] st = readStored(set, symbol, fs0);
        boolean indep = cnt == need && st != null && eq(st[0], op) && eq(st[1], hi) && eq(st[2], lo) && eq(st[3], cl) && eq(st[4], v);
        LOG.info("🔎 VALIDATE {}/{}: {}/4 khung khớp (read-back=acc) | recompute-độc-lập khung {} (n={}): {}",
                set, symbol, ok, Utils.normalizeDateYYYYMMDD(fs0), cnt, indep ? "KHỚP ✅" : "LỆCH 🔴 stored=" + Arrays.toString(st) + " recompute=[" + op + "," + hi + "," + lo + "," + cl + "," + v + "]");
    }

    private static boolean eq(float a, float b) { return Math.abs(a - b) <= Math.max(1e-3f, Math.abs(b) * 1e-5f); }
}
