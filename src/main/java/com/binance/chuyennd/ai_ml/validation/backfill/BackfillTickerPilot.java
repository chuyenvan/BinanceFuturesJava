package com.binance.chuyennd.ai_ml.validation.backfill;

import com.aerospike.client.*;
import com.aerospike.client.Record;
import com.aerospike.client.cdt.MapOperation;
import com.aerospike.client.cdt.MapPolicy;
import com.aerospike.client.cdt.MapReturnType;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.proto.MinuteDataFinalProto.MinuteDataFinal;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * TASK-005 — backfill ticker coin die vào kline_1m_opt (pilot LUNA, fill 226→audit→242).
 *
 * ⚠️ GHI Aerospike namespace ticker. Đường ghi RIÊNG (helper DataManager hardcode getClient242) +
 *    cấp id THỦ CÔNG (KHÔNG gọi SimpleSymbolMapper.getId vì nó ghi mapper 242). Đọc INGEST_FORMAT.md.
 *
 * Format (đã rà): key=yyyyMMdd-HHmm (GMT+7), bin "data"=Snappy(MinuteDataFinal: map<shortSymbol→
 * KlineObjectOptimized{open,max,min,close,totalUsdt}>). Ticker map key = SHORT (LUNA); mapper key = FULL (LUNAUSDT).
 * READ-MODIFY-WRITE giữ coin khác.
 *
 * Mode:
 *  - inspect SYMBOL                : (read-only) mapper 226+242 (present/id/maxId), format key record mẫu, ticker SYMBOL đã có chưa.
 *  - write   SYMBOL 226|242 ID     : ghi ticker + mapper(SYMBOL→ID) vào cluster; audit before/after coin-khác-không-đổi trên mốc mẫu.
 *  - audit   SYMBOL 226|242        : (read-only) đọc lại mốc mẫu → SYMBOL đúng giá CSV + đếm coin khác + mapper.
 */
public class BackfillTickerPilot {

    private static final Logger LOG = LoggerFactory.getLogger(BackfillTickerPilot.class);
    private static final String NS = Configs.AEROSPIKE_NAMESPACE;
    private static final String SET_TICKER = DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_TICKER; // kline_1m_opt
    private static final String SET_MAPPER = "symbol_mapper";
    private static final String MAPPER_KEY = "global_id_map";
    private static final String BIN = "data";
    private static final String CSV_DIR = "luna_csv/";
    private static final int SAMPLE_N = 8;   // số mốc mẫu để audit coin-khác-không-đổi

    private static WritePolicy wp() {
        WritePolicy w = new WritePolicy();
        w.expiration = 0; w.sendKey = true; w.recordExistsAction = RecordExistsAction.UPDATE;
        return w;
    }

    private static AerospikeClient client(String cluster) {
        return "242".equals(cluster) ? DataManagerAerospikeFloatSim.getClient242()
                : DataManagerAerospikeFloatSim.getClient226();
    }

    public static void main(String[] args) {
        try {
            if (args.length < 1) { LOG.error("Dùng: diffmapper | inspect SYMBOL | write SYMBOL 226|242 ID | audit SYMBOL 226|242 | remove SYMBOL 226|242"); return; }
            String mode = args[0];
            if ("diffmapper".equals(mode)) { diffMapper(); return; }
            if (args.length < 2) { LOG.error("Mode {} cần SYMBOL.", mode); return; }
            String symbol = args[1].toUpperCase(Locale.US);
            switch (mode) {
                case "inspect": inspect(symbol); break;
                case "write":   write(symbol, args[2], Short.parseShort(args[3])); break;
                case "audit":   audit(symbol, args[2]); break;
                case "remove":  remove(symbol, args[2]); break;
                case "probe":   probe(symbol, args[2]); break;
                default: LOG.error("Mode lạ: {}", mode);
            }
        } catch (Exception e) {
            LOG.error("BackfillTickerPilot lỗi", e);
        }
    }

    // ===================== INSPECT (read-only) =====================
    private static void inspect(String symbol) throws Exception {
        List<long[]> bars = loadBars(symbol);   // [timeMs] only needed for sample key
        LOG.info("📥 CSV {} bars={} (đĩa)", symbol, bars.size());
        for (String cl : new String[]{"226", "242"}) {
            Map<String, Long> m = readMapper(cl);
            Long id = m.get(symbol);
            long maxId = m.values().stream().mapToLong(Long::longValue).max().orElse(0);
            LOG.info("🗺️ MAPPER[{}]: tổng={} | {} -> {} | maxId={} (nextId={})",
                    cl, m.size(), symbol, id, maxId, maxId + 1);
        }
        // format key record mẫu (giữa lifespan) trên 226
        if (!bars.isEmpty()) {
            long t = bars.get(bars.size() / 2)[0];
            String key = keyOf(t);
            Map<String, KlineObjectOptimized> rec = readRecord(client("226"), key);
            LOG.info("🔑 record mẫu key={} (226): {} symbol; mẫu keys={}; {} đã có={}",
                    key, rec == null ? "null" : rec.size(),
                    rec == null ? "[]" : new ArrayList<>(rec.keySet()).subList(0, Math.min(5, rec.size())),
                    symbol, rec != null && rec.containsKey(symbol));
        }
    }

    // ===================== WRITE (ghi cluster) =====================
    private static void write(String symbol, String cluster, short id) throws Exception {
        AerospikeClient c = client(cluster);
        String tkey = symbol;   // KEY ticker map = FULL symbol (record hiện dùng full, vd SUSHIUSDT — xác nhận qua inspect)
        List<Bar> bars = loadFullBars(symbol);
        if (bars.isEmpty()) { LOG.error("⛔ Không có bar {} trên đĩa.", symbol); return; }
        LOG.info("✍️ WRITE {} → cluster {} | id={} | bars={} | tickerKey={}", symbol, cluster, id, bars.size(), tkey);

        // mapper an toàn: nếu SYMBOL đã có id khác id truyền vào → DỪNG (tránh lệch 226/242)
        Map<String, Long> mp = readMapper(cluster);
        if (mp.containsKey(symbol) && mp.get(symbol) != id) {
            LOG.error("⛔ {} đã map id={} trên {} ≠ id truyền {} → DỪNG (id phải nhất quán).", symbol, mp.get(symbol), cluster, id);
            return;
        }
        for (Map.Entry<String, Long> e : mp.entrySet()) {
            if (e.getValue() == id && !e.getKey().equals(symbol)) {
                LOG.error("⛔ id={} đã thuộc {} trên {} → DỪNG (trùng id).", id, e.getKey(), cluster); return;
            }
        }

        // mốc mẫu (spread) + snapshot TRƯỚC
        List<String> sampleKeys = sampleKeys(bars);
        Map<String, Map<String, KlineObjectOptimized>> before = new LinkedHashMap<>();
        for (String k : sampleKeys) before.put(k, readRecord(c, k));

        // bulk read-modify-write
        WritePolicy w = wp();
        long written = 0, onPopulated = 0, createdNew = 0;
        for (Bar b : bars) {
            String key = keyOf(b.t);
            Map<String, KlineObjectOptimized> rec = readRecord(c, key);
            if (rec == null) { rec = new HashMap<>(); createdNew++; } else onPopulated++;
            rec.put(tkey, KlineObjectOptimized.newBuilder()
                    .setPriceOpen(b.open).setMaxPrice(b.high).setMinPrice(b.low)
                    .setPriceClose(b.close).setTotalUsdt(b.qv).build());
            byte[] comp = Snappy.compress(MinuteDataFinal.newBuilder().putAllTickers(rec).build().toByteArray());
            c.put(w, new Key(NS, SET_TICKER, key), new Bin(BIN, comp));
            if (++written % 100000 == 0) LOG.info("   ... {}/{}", written, bars.size());
        }
        LOG.info("✅ Ghi {} record (record có sẵn coin khác={}, tạo mới={}).", written, onPopulated, createdNew);

        // mapper SYMBOL→id (THỦ CÔNG, KHÔNG getId)
        c.operate(w, new Key(NS, SET_MAPPER, MAPPER_KEY),
                MapOperation.put(MapPolicy.Default, BIN, Value.get(symbol), Value.get((long) id)));
        LOG.info("🗺️ Mapper[{}] {} -> {} (ghi thủ công).", cluster, symbol, id);

        // audit AFTER: coin khác không đổi + SYMBOL có mặt
        int okSamples = 0, badSamples = 0;
        for (String k : sampleKeys) {
            Map<String, KlineObjectOptimized> aft = readRecord(c, k);
            Map<String, KlineObjectOptimized> bef = before.get(k);
            String verdict = compareNonTarget(bef, aft, tkey);
            boolean targetOk = aft != null && aft.containsKey(tkey);
            if (verdict == null && targetOk) okSamples++; else {
                badSamples++;
                LOG.error("   🔴 SAMPLE key={} FAIL: otherDiff={} targetPresent={}", k, verdict, targetOk);
            }
        }
        LOG.info("🔎 AUDIT WRITE[{}]: {} mốc OK / {} FAIL (coin khác bit-nguyên + {} có mặt).",
                cluster, okSamples, badSamples, tkey);
        if (badSamples == 0) LOG.info("✅ WRITE[{}] PASS — coin khác KHÔNG đổi, {} đã ghi.", cluster, symbol);
        else LOG.error("🔴 WRITE[{}] có {} mốc lỗi — KIỂM TRA.", cluster, badSamples);
    }

    // ===================== AUDIT (read-only) =====================
    private static void audit(String symbol, String cluster) throws Exception {
        AerospikeClient c = client(cluster);
        String tkey = symbol;   // ticker map key = FULL symbol
        List<Bar> bars = loadFullBars(symbol);
        Map<Long, Bar> t2b = new HashMap<>();
        for (Bar b : bars) t2b.put(b.t, b);
        List<String> sampleKeys = sampleKeys(bars);
        int present = 0, priceOk = 0;
        for (String k : sampleKeys) {
            Map<String, KlineObjectOptimized> rec = readRecord(c, k);
            boolean has = rec != null && rec.containsKey(tkey);
            if (has) present++;
            long t = parseKey(k);
            Bar b = t2b.get(t);
            if (has && b != null) {
                float close = rec.get(tkey).getPriceClose();
                boolean match = Math.abs(close - b.close) / Math.max(1e-9f, Math.abs(b.close)) < 1e-3;
                if (match) priceOk++;
                LOG.info("   key={} {}: close-cluster={} close-CSV={} {} | tổng symbol={}",
                        k, tkey, close, b.close, match ? "KHỚP" : "LỆCH", rec.size());
            } else {
                LOG.info("   key={} {}: VẮNG | record symbol={}", k, tkey, rec == null ? 0 : rec.size());
            }
        }
        Map<String, Long> mp = readMapper(cluster);
        LOG.info("🔎 AUDIT[{}] {}: present {}/{} mốc, price khớp {}/{} | mapper {} -> {}",
                cluster, symbol, present, sampleKeys.size(), priceOk, present, symbol, mp.get(symbol));
    }

    // ===================== DIFFMAPPER (read-only) — audit nguồn lệch 226 vs 242 =====================
    private static void diffMapper() {
        Map<String, Long> m226 = readMapper("226"), m242 = readMapper("242");
        LOG.info("🗺️ tổng: 226={} 242={}", m226.size(), m242.size());
        List<String> only242 = new ArrayList<>(), only226 = new ArrayList<>(), idMismatch = new ArrayList<>();
        long lo = Long.MAX_VALUE, hi = Long.MIN_VALUE;
        for (Map.Entry<String, Long> e : m242.entrySet()) {
            if (!m226.containsKey(e.getKey())) {
                only242.add(e.getKey() + "=" + e.getValue());
                lo = Math.min(lo, e.getValue()); hi = Math.max(hi, e.getValue());
            } else if (!m226.get(e.getKey()).equals(e.getValue())) {
                idMismatch.add(e.getKey() + ": 226=" + m226.get(e.getKey()) + " 242=" + e.getValue());
            }
        }
        for (Map.Entry<String, Long> e : m226.entrySet())
            if (!m242.containsKey(e.getKey())) only226.add(e.getKey() + "=" + e.getValue());
        LOG.info("🔴 CHỈ trên 242 (226 thiếu) [{}]: {}", only242.size(), only242);
        LOG.info("🔴 CHỈ trên 226 (242 thiếu) [{}]: {}", only226.size(), only226);
        LOG.info("🔴 CÙNG symbol KHÁC id [{}]: {}", idMismatch.size(), idMismatch);
        if (!only242.isEmpty())
            LOG.info("📊 id của nhóm 'chỉ-242': range [{}..{}] → {}", lo, hi,
                    lo >= 700 ? "VÙNG CAO (id mới gần đây, 226 chưa sync)" : "VÙNG THẤP/RẢI (lệch sâu)");
        LOG.info(idMismatch.isEmpty()
                ? "✅ KHÔNG có symbol nào lệch id giữa 2 cluster → an toàn cấp id mới từ max+1."
                : "⛔ CÓ symbol lệch id → CẢNH BÁO: cùng id nghĩa khác nhau giữa 2 node.");
    }

    // ===================== PROBE (read-only) — coin có data trên cluster từ mốc THÁNG nào =====================
    // Quét tháng 2021-01..2026-06, mỗi tháng lấy mẫu 2 mốc (ngày 10 & 20, 12:00 GMT+7), check SYMBOL có trong record.
    // → phân loại Đợt B: (a) KHÔNG present tháng nào = full backfill; (b) present từ tháng M = chỉ backfill tháng < M.
    private static void probe(String symbol, String cluster) throws Exception {
        AerospikeClient c = client(cluster);
        String firstPresent = null, lastPresent = null;
        List<String> present = new ArrayList<>();
        for (int y = 2021; y <= 2026; y++) {
            for (int m = 1; m <= 12; m++) {
                if (y == 2026 && m > 6) break;
                boolean has = false;
                for (int d : new int[]{10, 20}) {
                    String key = String.format("%04d%02d%02d-1200", y, m, d);
                    Map<String, KlineObjectOptimized> rec = readRecord(c, key);
                    if (rec != null && rec.containsKey(symbol)) { has = true; break; }
                }
                if (has) {
                    String ym = String.format("%04d-%02d", y, m);
                    present.add(ym);
                    if (firstPresent == null) firstPresent = ym;
                    lastPresent = ym;
                }
            }
        }
        if (firstPresent == null)
            LOG.info("🔍 PROBE[{}] {}: VẮNG mọi tháng 2021-01..2026-06 → (a) BACKFILL TOÀN BỘ an toàn.", cluster, symbol);
        else
            LOG.info("🔍 PROBE[{}] {}: CÓ data {} tháng, từ {} → {} ⇒ (b) chỉ backfill THÁNG < {} (KHÔNG đụng [{},nay]). present={}",
                    cluster, symbol, present.size(), firstPresent, lastPresent, firstPresent, firstPresent, present);
    }

    // ===================== REMOVE (rollback) — gỡ SYMBOL khỏi cluster =====================
    private static void remove(String symbol, String cluster) throws Exception {
        AerospikeClient c = client(cluster);
        List<Bar> bars = loadFullBars(symbol);
        if (bars.isEmpty()) { LOG.error("⛔ Không có bar {} trên đĩa (cần CSV để biết key cần gỡ).", symbol); return; }
        LOG.info("🗑️ REMOVE {} khỏi cluster {} | quét {} key phút...", symbol, cluster, bars.size());
        // snapshot mẫu TRƯỚC để audit coin khác không đổi
        List<String> sampleKeys = sampleKeys(bars);
        Map<String, Map<String, KlineObjectOptimized>> before = new LinkedHashMap<>();
        for (String k : sampleKeys) before.put(k, readRecord(c, k));

        WritePolicy w = wp();
        long removed = 0, notFound = 0;
        for (Bar b : bars) {
            String key = keyOf(b.t);
            Map<String, KlineObjectOptimized> rec = readRecord(c, key);
            if (rec == null || !rec.containsKey(symbol)) { notFound++; continue; }
            rec.remove(symbol);
            byte[] comp = Snappy.compress(MinuteDataFinal.newBuilder().putAllTickers(rec).build().toByteArray());
            c.put(w, new Key(NS, SET_TICKER, key), new Bin(BIN, comp));
            if (++removed % 100000 == 0) LOG.info("   ... gỡ {}", removed);
        }
        // mapper: removeByKey
        c.operate(w, new Key(NS, SET_MAPPER, MAPPER_KEY),
                MapOperation.removeByKey(BIN, Value.get(symbol), MapReturnType.NONE));
        LOG.info("✅ Gỡ {} record (không thấy {}). Mapper[{}] removeByKey {}.", removed, notFound, cluster, symbol);

        int ok = 0, bad = 0;
        for (String k : sampleKeys) {
            Map<String, KlineObjectOptimized> aft = readRecord(c, k), bef = before.get(k);
            // sau khi gỡ: SYMBOL phải VẮNG + coin khác bit-nguyên (so bef đã trừ SYMBOL)
            boolean gone = aft == null || !aft.containsKey(symbol);
            String diff = compareNonTarget(bef, aft, symbol);
            if (gone && diff == null) ok++; else { bad++; LOG.error("   🔴 key={} gone={} otherDiff={}", k, gone, diff); }
        }
        if (bad == 0) LOG.info("✅ REMOVE[{}] PASS — {} vắng, coin khác bit-nguyên.", cluster, symbol);
        else LOG.error("🔴 REMOVE[{}] {} mốc lỗi.", cluster, bad);
    }

    // ===================== helpers =====================
    private static String compareNonTarget(Map<String, KlineObjectOptimized> bef, Map<String, KlineObjectOptimized> aft, String target) {
        if (bef == null) bef = Collections.emptyMap();
        if (aft == null) return "after=null";
        for (Map.Entry<String, KlineObjectOptimized> e : bef.entrySet()) {
            if (e.getKey().equals(target)) continue;
            KlineObjectOptimized a = aft.get(e.getKey());
            if (a == null) return "mất " + e.getKey();
            KlineObjectOptimized b = e.getValue();
            if (a.getPriceOpen() != b.getPriceOpen() || a.getMaxPrice() != b.getMaxPrice()
                    || a.getMinPrice() != b.getMinPrice() || a.getPriceClose() != b.getPriceClose()
                    || a.getTotalUsdt() != b.getTotalUsdt()) return "đổi giá trị " + e.getKey();
        }
        int befNonTarget = bef.containsKey(target) ? bef.size() - 1 : bef.size();
        int aftNonTarget = aft.containsKey(target) ? aft.size() - 1 : aft.size();
        if (aftNonTarget != befNonTarget) return "đếm coin khác lệch " + befNonTarget + "->" + aftNonTarget;
        return null;
    }

    private static Map<String, KlineObjectOptimized> readRecord(AerospikeClient c, String key) throws Exception {
        Record r = c.get(null, new Key(NS, SET_TICKER, key));
        if (r == null) return null;
        byte[] data = (byte[]) r.getValue(BIN);
        if (data == null) return null;
        return new HashMap<>(MinuteDataFinal.parseFrom(Snappy.uncompress(data)).getTickersMap());
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Long> readMapper(String cluster) {
        Record r = client(cluster).get(null, new Key(NS, SET_MAPPER, MAPPER_KEY));
        if (r == null) return new HashMap<>();
        Map<String, Long> raw = (Map<String, Long>) r.getMap(BIN);
        return raw == null ? new HashMap<>() : new HashMap<>(raw);
    }

    private static List<String> sampleKeys(List<Bar> bars) {
        List<String> ks = new ArrayList<>();
        int n = bars.size();
        for (int i = 0; i < SAMPLE_N; i++) {
            int idx = (int) ((long) i * (n - 1) / (SAMPLE_N - 1));
            ks.add(keyOf(bars.get(idx).t));
        }
        return ks;
    }

    private static final ThreadLocal<SimpleDateFormat> FMT =
            ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyyMMdd-HHmm"));   // TZ = GMT+7 (TimeZoneGuard)

    private static String keyOf(long ms) { return FMT.get().format(new Date(ms)); }

    private static long parseKey(String key) {
        try { return FMT.get().parse(key).getTime(); } catch (Exception e) { return -1; }
    }

    private static class Bar { long t; float open, high, low, close, qv; }

    private static List<Bar> loadFullBars(String symbol) throws Exception {
        List<Bar> bars = new ArrayList<>();
        File dir = new File(CSV_DIR);
        File[] files = dir.listFiles((d, n) -> n.startsWith(symbol + "-1m-") && n.endsWith(".csv"));
        if (files == null) return bars;
        Arrays.sort(files);
        for (File f : files) {
            try (BufferedReader br = new BufferedReader(new FileReader(f))) {
                String line;
                while ((line = br.readLine()) != null) {
                    String[] c = line.split(",");
                    if (c.length < 8) continue;
                    long t;
                    try { t = Long.parseLong(c[0].trim()); } catch (NumberFormatException e) { continue; }
                    Bar b = new Bar();
                    b.t = t; b.open = pf(c[1]); b.high = pf(c[2]); b.low = pf(c[3]); b.close = pf(c[4]); b.qv = pf(c[7]);
                    bars.add(b);
                }
            }
        }
        bars.sort(Comparator.comparingLong(x -> x.t));
        return bars;
    }

    private static List<long[]> loadBars(String symbol) throws Exception {
        List<long[]> r = new ArrayList<>();
        for (Bar b : loadFullBars(symbol)) r.add(new long[]{b.t});
        return r;
    }

    private static float pf(String s) { return Float.parseFloat(s.trim()); }
}
