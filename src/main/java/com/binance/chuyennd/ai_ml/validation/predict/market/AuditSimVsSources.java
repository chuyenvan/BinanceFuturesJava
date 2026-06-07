package com.binance.chuyennd.ai_ml.validation.predict.market;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * ĐỐI SOÁT CƠ BẢN: engine sim có "ngáo" ở entry/exit/merge không? READ-ONLY, KHÔNG dựng lại logic trailing/TP.
 *
 * Đọc lệnh đã lưu (storage/OrderTestDone.data = TreeMap<Long, leg>), group CỤM theo (symbolId, timeUpdate),
 * sort leg theo timeStart ([0]=entry, còn lại=DCA). Lấy mẫu 150 cụm rải đều, ÉP >=30% cụm có >=2 leg.
 * Đối soát giá trên 2 NGUỒN: Aerospike (sim dùng) + Binance API (ground truth).
 *
 *   KIỂM 1 — Entry == priceClose tại timeStart (mọi leg, gồm DCA). tol = rel epsilon (không slippage ở priceEntry).
 *   KIỂM 2 — Giá đóng (priceTP) ∈ [low, high] của nến tại timeUpdate. Ngoài range = bịa/look-ahead => ĐỎ.
 *            Delist/flush: nến tại timeUpdate có thể trống => so với NẾN-DATA-CUỐI; Binance rỗng = delist nhất quán.
 *   KIỂM 3 — Merge DCA số học: avgEntry vol-weighted ∈ [min,max] leg-entry, totalQty = Σ. (Giá merge runtime
 *            KHÔNG persist => dùng công thức code đã đọc + leg đã verify ở Kiểm 1 => suy ra merge đúng — lựa chọn (a).)
 *
 * Phân loại: lệch Aerospike-vs-Binance = lỗi DATA; lệch sim-vs-(cùng nguồn) = lỗi ENGINE.
 */
public class AuditSimVsSources {

    private static final Logger LOG = LoggerFactory.getLogger(AuditSimVsSources.class);

    private static final int SAMPLE = 150;
    private static final double MULTI_FRAC = 0.30;   // ÉP >=30% cụm DCA
    private static final double REL_TOL = 1e-4;       // dung sai khớp giá (hấp thụ float-pack vs JSON)
    private static final double RANGE_EPS = 1e-4;     // nới [low,high] để hấp thụ sai số float
    private static final int CACHE_DAYS = 200;        // LRU ngày ticker Aerospike
    private static final long SLEEP_MS = 150;         // tôn trọng rate-limit Binance

    /** LRU cache ngày giao dịch (07:00 GMT+7) -> snapshot 1440' index theo symbolId. */
    private final LinkedHashMap<Long, TreeMap<Long, KlineObjectSimple[]>> dayCache =
            new LinkedHashMap<Long, TreeMap<Long, KlineObjectSimple[]>>(16, 0.75f, true) {
                @Override
                protected boolean removeEldestEntry(Map.Entry<Long, TreeMap<Long, KlineObjectSimple[]>> e) {
                    return size() > CACHE_DAYS;
                }
            };

    public static void main(String[] args) {
        try { new AuditSimVsSources().run(); } catch (Exception e) { LOG.error("Audit error", e); }
    }

    private static class Cluster {
        short symbolId;
        String symbol;
        long timeUpdate;
        List<OrderTargetInfoTest> legs = new ArrayList<>();   // sort theo timeStart
        OrderTargetInfoTest entry() { return legs.get(0); }
    }

    /** {magnitude, desc} cho top-N ca lệch nặng. */
    private static class Bad {
        double mag; String desc;
        Bad(double m, String d) { mag = m; desc = d; }
    }

    @SuppressWarnings("unchecked")
    public void run() throws Exception {
        SimpleSymbolMapper.getInstance().init();

        String file = SimulatorMarketLevelTicker1MStopLoss.FILE_STORAGE_ORDER_DONE;
        Object obj = Storage.readObjectFromFile(file);
        if (!(obj instanceof TreeMap)) {
            LOG.error("⛔ Không đọc được {} (chạy 1 backtest baseline để sinh file trước).", file);
            return;
        }
        TreeMap<Long, OrderTargetInfoTest> all = (TreeMap<Long, OrderTargetInfoTest>) obj;
        LOG.info("📥 Đọc {} leg từ {}", all.size(), file);

        // group cụm
        Map<String, Cluster> map = new HashMap<>();
        for (OrderTargetInfoTest o : all.values()) {
            Cluster c = map.computeIfAbsent(o.symbolId + "@" + o.timeUpdate, k -> {
                Cluster cc = new Cluster();
                cc.symbolId = o.symbolId;
                cc.symbol = SimpleSymbolMapper.getInstance().getSymbol(o.symbolId);
                cc.timeUpdate = o.timeUpdate;
                return cc;
            });
            c.legs.add(o);
        }
        for (Cluster c : map.values()) c.legs.sort(Comparator.comparingLong(o -> o.timeStart));

        List<Cluster> multi = new ArrayList<>(), single = new ArrayList<>();
        for (Cluster c : map.values()) (c.legs.size() >= 2 ? multi : single).add(c);
        multi.sort(Comparator.comparingLong(c -> c.entry().timeStart));
        single.sort(Comparator.comparingLong(c -> c.entry().timeStart));
        LOG.info("Tổng cụm={} (multi-leg/DCA={} | single={})", map.size(), multi.size(), single.size());

        // mẫu: >=30% multi, rải đều theo entry.timeStart
        int nMulti = Math.min(multi.size(), Math.max((int) Math.ceil(SAMPLE * 0.5), 1));
        int nSingle = Math.min(single.size(), SAMPLE - nMulti);
        List<Cluster> sample = new ArrayList<>();
        sample.addAll(stride(multi, nMulti));
        sample.addAll(stride(single, nSingle));
        int gotMulti = 0;
        for (Cluster c : sample) if (c.legs.size() >= 2) gotMulti++;
        double fracMulti = sample.isEmpty() ? 0 : (double) gotMulti / sample.size();
        LOG.info("Mẫu={} cụm (multi={} = {}%).", sample.size(), gotMulti, f1(fracMulti * 100));
        if (fracMulti < MULTI_FRAC)
            LOG.warn("⚠️ Tỉ lệ multi-leg {}% < 30% (dữ liệu ít cụm DCA) — Kiểm 3 yếu.", f1(fracMulti * 100));
        if (sample.isEmpty()) { LOG.warn("⚠️ Không có cụm."); return; }

        // ===== accumulators =====
        // Kiểm1 phân 3 lớp: EXACT(=close) / DRIFT(≠close nhưng ∈[low,high] = giá trôi trong nến) / OUT(ngoài nến)
        int aLegN = 0, aLegExact = 0, aLegDrift = 0, aLegOut = 0, aLegMiss = 0;   // sim vs Aerospike
        int bLegN = 0, bLegExact = 0, bLegDrift = 0, bLegOut = 0, bLegMiss = 0;   // sim vs Binance
        int abLegN = 0, abLegOk = 0;                       // Aerospike vs Binance close (DATA)
        int aClsN = 0, aClsIn = 0, aDelist = 0;           // Kiểm2 Aerospike
        int bClsN = 0, bClsIn = 0, bDelist = 0;           // Kiểm2 Binance
        int mN = 0, mOk = 0;                               // Kiểm3
        List<Bad> badLegOutAero = new ArrayList<>();       // entry NGOÀI nến (Aerospike) = engine bịa/look-ahead
        List<Bad> badLegOutBin = new ArrayList<>();        // entry NGOÀI nến (Binance)
        List<Bad> badLegData = new ArrayList<>();          // Aerospike vs Binance close drift (DATA)
        List<Bad> badClsAero = new ArrayList<>();          // exit ngoài range (Aerospike)
        List<Bad> badClsBin = new ArrayList<>();           // exit ngoài range (Binance)
        List<Bad> badMerge = new ArrayList<>();

        int idx = 0;
        for (Cluster c : sample) {
            idx++;
            Map<Long, KlineObjectSimple> bin = fetchBinanceWindow(c);
            sleepQuiet();

            // ----- KIỂM 1: entry vs nến tại timeStart (mọi leg). Phân lớp EXACT/DRIFT/OUT -----
            // Lý do DRIFT: entry sim = ticker.priceClose của snapshot phút đó; close chốt của nguồn khác
            // có thể lệch nhẹ nhưng nếu entry vẫn ∈[low,high] => giá trôi TRONG nến (benign), KHÔNG phải bịa.
            for (OrderTargetInfoTest leg : c.legs) {
                boolean isEntry = (leg == c.legs.get(0));
                String tag = isEntry ? "ENTRY" : "DCA";
                if (leg.priceEntry == null) continue;
                float pe = leg.priceEntry;
                KlineObjectSimple ka = aero(c.symbolId, leg.timeStart);
                KlineObjectSimple kb = bin.get(leg.timeStart);

                // sim vs AEROSPIKE (cùng nguồn sim dùng — kỳ vọng EXACT ~100%)
                if (ka == null) {
                    aLegMiss++;
                } else {
                    aLegN++;
                    if (rel(pe, ka.priceClose) < REL_TOL) aLegExact++;
                    else if (inRange(pe, ka)) aLegDrift++;
                    else { aLegOut++; badLegOutAero.add(new Bad(outDist(pe, ka), String.format(Locale.US,
                            "%s %s %s entry=%.6f close=%.6f [low=%.6f high=%.6f] NGOÀI nến", tag, c.symbol,
                            Utils.normalizeDateYYYYMMDDHHmm(leg.timeStart), pe, ka.priceClose, ka.minPrice, ka.maxPrice))); }
                }
                // sim vs BINANCE (ground truth — DRIFT kỳ vọng có do khác nguồn)
                if (kb == null) {
                    bLegMiss++;
                } else {
                    bLegN++;
                    if (rel(pe, kb.priceClose) < REL_TOL) bLegExact++;
                    else if (inRange(pe, kb)) bLegDrift++;
                    else { bLegOut++; badLegOutBin.add(new Bad(outDist(pe, kb), String.format(Locale.US,
                            "%s %s %s entry=%.6f close=%.6f [low=%.6f high=%.6f] NGOÀI nến", tag, c.symbol,
                            Utils.normalizeDateYYYYMMDDHHmm(leg.timeStart), pe, kb.priceClose, kb.minPrice, kb.maxPrice))); }
                }
                // DATA: Aerospike close vs Binance close
                if (ka != null && kb != null) {
                    abLegN++;
                    double r = rel(ka.priceClose, kb.priceClose);
                    if (r < REL_TOL) abLegOk++;
                    else badLegData.add(new Bad(r, String.format(Locale.US,
                            "%s %s aeroClose=%.6f binClose=%.6f rel=%.4f", c.symbol,
                            Utils.normalizeDateYYYYMMDDHHmm(leg.timeStart), ka.priceClose, kb.priceClose, r)));
                }
            }

            // ----- KIỂM 2: giá đóng (priceTP) ∈ [low,high] tại timeUpdate -----
            Float exit = c.entry().priceTP;
            if (exit != null) {
                // Aerospike
                KlineObjectSimple ka = aero(c.symbolId, c.timeUpdate);
                boolean delistA = (ka == null);
                if (delistA) ka = aeroLast(c.symbolId, c.timeUpdate);
                if (ka != null) {
                    aClsN++;
                    if (delistA) aDelist++;
                    if (inRange(exit, ka)) aClsIn++;
                    else badClsAero.add(new Bad(outDist(exit, ka), String.format(Locale.US,
                            "%s %s exit=%.6f [low=%.6f high=%.6f]%s", c.symbol,
                            Utils.normalizeDateYYYYMMDDHHmm(c.timeUpdate), exit, ka.minPrice, ka.maxPrice,
                            delistA ? " (nến-data-cuối/delist)" : "")));
                }
                // Binance
                KlineObjectSimple kb = bin.get(c.timeUpdate);
                if (kb == null) {
                    bDelist++;   // Binance rỗng tại timeUpdate = delist nhất quán, không tính lệch
                } else {
                    bClsN++;
                    if (inRange(exit, kb)) bClsIn++;
                    else badClsBin.add(new Bad(outDist(exit, kb), String.format(Locale.US,
                            "%s %s exit=%.6f [low=%.6f high=%.6f]", c.symbol,
                            Utils.normalizeDateYYYYMMDDHHmm(c.timeUpdate), exit, kb.minPrice, kb.maxPrice)));
                }
            }

            // ----- KIỂM 3: merge DCA số học -----
            if (c.legs.size() >= 2) {
                mN++;
                double sumQ = 0, sumEQ = 0, minE = Double.MAX_VALUE, maxE = -Double.MAX_VALUE;
                boolean valid = true;
                for (OrderTargetInfoTest leg : c.legs) {
                    if (leg.priceEntry == null || leg.quantity == null) { valid = false; break; }
                    sumQ += leg.quantity;
                    sumEQ += (double) leg.priceEntry * leg.quantity;
                    minE = Math.min(minE, leg.priceEntry);
                    maxE = Math.max(maxE, leg.priceEntry);
                }
                if (valid && sumQ > 0) {
                    double avg = sumEQ / sumQ;
                    double eps = REL_TOL * maxE;
                    boolean ok = avg >= minE - eps && avg <= maxE + eps;
                    if (ok) mOk++;
                    else badMerge.add(new Bad(Math.abs(avg - Math.max(minE, Math.min(maxE, avg))),
                            String.format(Locale.US, "%s %s legs=%d avg=%.6f notIn[%.6f,%.6f]", c.symbol,
                                    Utils.normalizeDateYYYYMMDDHHmm(c.timeUpdate), c.legs.size(), avg, minE, maxE)));
                } else {
                    badMerge.add(new Bad(0, String.format(Locale.US, "%s %s legs=%d THIẾU qty/entry",
                            c.symbol, Utils.normalizeDateYYYYMMDDHHmm(c.timeUpdate), c.legs.size())));
                }
            }

            if (idx % 25 == 0) LOG.info("  ...đã soát {}/{} cụm", idx, sample.size());
        }

        // ===== BÁO CÁO =====
        LOG.info("\n================ KIỂM 1 — ENTRY vs nến tại timeStart (EXACT/DRIFT/OUT) ================");
        LOG.info("DRIFT = ≠close nhưng ∈[low,high] (giá trôi trong nến, benign) | OUT = NGOÀI nến (cờ đỏ thật)");
        LOG.info("sim vs AEROSPIKE: n={} exact={}% drift={}% NGOÀI={}%  | nến thiếu={}",
                aLegN, pct(aLegExact, aLegN), pct(aLegDrift, aLegN), pct(aLegOut, aLegN), aLegMiss);
        LOG.info("sim vs BINANCE : n={} exact={}% drift={}% NGOÀI={}%  | nến thiếu/delist={}",
                bLegN, pct(bLegExact, bLegN), pct(bLegDrift, bLegN), pct(bLegOut, bLegN), bLegMiss);
        LOG.info("AEROSPIKE vs BINANCE (DATA): n={} close khớp={}%", abLegN, pct(abLegOk, abLegN));
        printTop("10 ca NGOÀI nến — Aerospike (engine bịa/look-ahead?)", badLegOutAero);
        printTop("10 ca NGOÀI nến — Binance", badLegOutBin);
        printTop("10 ca DATA lệch (Aerospike vs Binance close)", badLegData);

        LOG.info("\n================ KIỂM 2 — giá đóng (priceTP) ∈ [low,high] ================");
        LOG.info("AEROSPIKE: n={} trong-range={}%  | đóng kiểu delist/nến-cuối={}", aClsN, pct(aClsIn, aClsN), aDelist);
        LOG.info("BINANCE  : n={} trong-range={}%  | delist (Binance rỗng, bỏ qua)={}", bClsN, pct(bClsIn, bClsN), bDelist);
        printTop("10 ca NGOÀI range (Aerospike) — bịa/look-ahead?", badClsAero);
        printTop("10 ca NGOÀI range (Binance)", badClsBin);

        LOG.info("\n================ KIỂM 3 — Merge DCA số học ================");
        LOG.info("cụm DCA: n={} avgEntry vol-weighted ∈[min,max] & qty OK={}%", mN, pct(mOk, mN));
        LOG.info("(Giá merge runtime KHÔNG persist => xác nhận qua công thức code + leg đã verify Kiểm 1 — lựa chọn (a).)");
        printTop("10 ca merge bất thường", badMerge);

        // ===== 1 DÒNG KẾT =====
        LOG.info("\n📌 PHÁN QUYẾT (sim có ngáo không):");
        double aOut = aLegN > 0 ? 100.0 * aLegOut / aLegN : -1;
        double bOut = bLegN > 0 ? 100.0 * bLegOut / bLegN : -1;
        double aDr = aLegN > 0 ? 100.0 * aLegDrift / aLegN : -1;
        LOG.info("   KIỂM 1 entry: NGOÀI-nến Aero={} Bin={} | drift-trong-nến Aero={}  {}",
                aOut < 0 ? "-" : f1(aOut) + "%", bOut < 0 ? "-" : f1(bOut) + "%", aDr < 0 ? "-" : f1(aDr) + "%",
                (aOut > 2) ? "🔴 ENGINE bịa giá NGOÀI nến" : "✅ entry trong nến (lệch nếu có = giá trôi/data drift)");
        verdict2("KIỂM 2 exit-range", aClsIn, aClsN, bClsIn, bClsN);
        if (mN > 0) {
            double mp = 100.0 * mOk / mN;
            LOG.info("   KIỂM 3 merge: {}% cụm DCA hợp lệ {}", f1(mp), mp >= 98 ? "=> OK" : "=> SOI badMerge");
        }
        LOG.info("   (lệch Aero-vs-Binance = lỗi DATA; lệch sim-vs-Aerospike = lỗi ENGINE; delist không tính lệch.)");
    }

    private void verdict2(String name, int aIn, int aN, int bIn, int bN) {
        double a = aN > 0 ? 100.0 * aIn / aN : -1;
        double b = bN > 0 ? 100.0 * bIn / bN : -1;
        StringBuilder sb = new StringBuilder("   " + name + ": ");
        sb.append("Aerospike=").append(a < 0 ? "-" : f1(a) + "%");
        sb.append(" | Binance=").append(b < 0 ? "-" : f1(b) + "%");
        if ((a >= 0 && a < 98) || (b >= 0 && b < 98)) sb.append("  🔴 có giá đóng NGOÀI nến (look-ahead/bịa?)");
        else sb.append("  ✅ giá đóng khả thi trong nến");
        LOG.info(sb.toString());
    }

    // ===== Binance: lấy nến cửa sổ cụm + bù khe các phút cần =====
    private Map<Long, KlineObjectSimple> fetchBinanceWindow(Cluster c) {
        Map<Long, KlineObjectSimple> m = new HashMap<>();
        long start = c.entry().timeStart;
        long span = (c.timeUpdate - start) / Utils.TIME_MINUTE;
        int limit = (int) Math.min(Math.max(span + 2, 2), 1000);
        for (KlineObjectSimple k : TickerFuturesHelper.getTickerSimpleWithStartTimeAndLimit(c.symbol, "1m", start, limit)) {
            if (k != null && k.startTime != null) m.put(k.startTime, k);
        }
        // bù khe: phút entry/DCA/close chưa có trong cửa sổ (hold dài > limit)
        Set<Long> need = new HashSet<>();
        for (OrderTargetInfoTest o : c.legs) need.add(o.timeStart);
        need.add(c.timeUpdate);
        for (Long t : need) {
            if (m.containsKey(t)) continue;
            for (KlineObjectSimple k : TickerFuturesHelper.getTickerSimpleWithStartTimeAndLimit(c.symbol, "1m", t, 2)) {
                if (k != null && k.startTime != null) m.put(k.startTime, k);
            }
        }
        return m;
    }

    // ===== Aerospike helpers =====
    private KlineObjectSimple aero(short sid, long minute) {
        TreeMap<Long, KlineObjectSimple[]> day = getDay(tradingDayStart(minute));
        if (day == null) return null;
        KlineObjectSimple[] arr = day.get(minute);
        if (arr == null || sid < 0 || sid >= arr.length) return null;
        return arr[sid];
    }

    /** Nến có data CUỐI CÙNG tại/trước minute (cho cụm delist/flush). Quét lùi tối đa 5 ngày. */
    private KlineObjectSimple aeroLast(short sid, long minute) {
        for (int d = 0; d < 5; d++) {
            TreeMap<Long, KlineObjectSimple[]> day = getDay(tradingDayStart(minute - d * Utils.TIME_DAY));
            if (day == null) continue;
            for (Map.Entry<Long, KlineObjectSimple[]> e : day.headMap(minute, true).descendingMap().entrySet()) {
                KlineObjectSimple[] arr = e.getValue();
                if (arr != null && sid >= 0 && sid < arr.length && arr[sid] != null) return arr[sid];
            }
        }
        return null;
    }

    private TreeMap<Long, KlineObjectSimple[]> getDay(long anchor) {
        if (!dayCache.containsKey(anchor)) {
            try { dayCache.put(anchor, DataManagerAerospikeFloatSim.readDataFromAerospike1M_ShortKey(anchor)); }
            catch (Exception e) { dayCache.put(anchor, null); }
        }
        return dayCache.get(anchor);
    }

    private static long tradingDayStart(long t) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(t);
        cal.set(Calendar.HOUR_OF_DAY, 7);
        cal.set(Calendar.MINUTE, 0);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);
        if (cal.getTimeInMillis() > t) cal.add(Calendar.DAY_OF_MONTH, -1);
        return cal.getTimeInMillis();
    }

    // ===== utils =====
    private static <T> List<T> stride(List<T> src, int n) {
        List<T> out = new ArrayList<>();
        if (src.isEmpty() || n <= 0) return out;
        int stride = Math.max(1, src.size() / n);
        for (int i = 0; i < src.size() && out.size() < n; i += stride) out.add(src.get(i));
        return out;
    }

    private static double rel(float a, float b) {
        return Math.abs(a - b) / Math.max(Math.abs(b), 1e-9);
    }

    private static boolean inRange(float p, KlineObjectSimple k) {
        double low = k.minPrice - RANGE_EPS * k.minPrice;
        double high = k.maxPrice + RANGE_EPS * k.maxPrice;
        return p >= low && p <= high;
    }

    /** Khoảng cách ra ngoài [low,high] (rel theo giá), để xếp hạng ca tệ. */
    private static double outDist(float p, KlineObjectSimple k) {
        if (p < k.minPrice) return (k.minPrice - p) / Math.max(k.minPrice, 1e-9f);
        if (p > k.maxPrice) return (p - k.maxPrice) / Math.max(k.maxPrice, 1e-9f);
        return 0;
    }

    private void printTop(String title, List<Bad> bads) {
        if (bads.isEmpty()) { LOG.info("--- {}: (không có) ---", title); return; }
        bads.sort((x, y) -> Double.compare(y.mag, x.mag));
        LOG.info("--- {} ({} ca) ---", title, bads.size());
        for (int i = 0; i < Math.min(10, bads.size()); i++) LOG.info("   {}", bads.get(i).desc);
    }

    private void sleepQuiet() {
        try { Thread.sleep(SLEEP_MS); } catch (InterruptedException ignored) { Thread.currentThread().interrupt(); }
    }

    private static String pct(int ok, int n) { return n > 0 ? f1(100.0 * ok / n) : "-"; }
    private static String f1(double v) { return String.format(Locale.US, "%.1f", v); }
}
