package com.binance.chuyennd.ai_ml.validation.predict.market;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * ĐỊNH LƯỢNG ΔPnL bị THỔI do exit (priceTP) > high nến timeUpdate. READ-ONLY, chỉ Aerospike.
 *
 * Cơ chế (NV0, đã đọc code): mọi ca OUT đến từ trailing-stop close — priceTP=priceSL (level set ở nến
 * TRƯỚC, KHÔNG kẹp), timeUpdate = nến TRIGGER thật (đầu tiên low<=priceSL). Khi nến trigger gap thủng SL
 * (high<priceSL), giá ghi cao hơn mức đạt được TRONG nến đó => loại (B) đóng-thật-giá-cũ => PnL THỔI,
 * phải KẸP GIÁ về high. "lag" (timeUpdate − nến gần nhất từng chạm exit) chỉ là độ-cũ của level, KHÔNG
 * phải lỗi mốc (sell-stop fill ở nến gap, không ở nến cũ). Vì vậy ΔPnL_kẹp tính cho TOÀN BỘ ca OUT.
 *
 *   ΔPnL_kẹp = totalQty·(priceTP − high_timeUpdate)   (cận DƯỚI mức thổi; kẹp về high là rộng rãi nhất)
 *
 * Cắt ΔPnL theo: bucket lag × NĂM × loại-close (status) + riêng ngày 20251011. fabrication = ca KHÔNG nến
 * nào trong kỳ giữ từng chạm exit (kỳ vọng ~0 — đã xác nhận giá luôn đạt-được đâu đó).
 */
public class ClassifyExitOutOfRange {

    private static final Logger LOG = LoggerFactory.getLogger(ClassifyExitOutOfRange.class);

    private static final double REL_TOL = 1e-4;
    private static final int CACHE_DAYS = 250;
    private static final int[] YEARS = {2021, 2022, 2023, 2024, 2025, 2026};
    private static final String CRASH_DAY = "20251011";

    // bucket lag (phút): ≤5 / 5-30 / 30-360 / 360-1440 / >1440
    private static final long[] LAG_EDGES = {5, 30, 360, 1440};
    private static final String[] LAG_LABELS = {"≤5′", "5-30′", "30′-6h", "6h-1d", ">1d"};

    private final LinkedHashMap<Long, TreeMap<Long, KlineObjectSimple[]>> dayCache =
            new LinkedHashMap<Long, TreeMap<Long, KlineObjectSimple[]>>(16, 0.75f, true) {
                @Override
                protected boolean removeEldestEntry(Map.Entry<Long, TreeMap<Long, KlineObjectSimple[]>> e) {
                    return size() > CACHE_DAYS;
                }
            };

    public static void main(String[] args) {
        try { new ClassifyExitOutOfRange().run(); } catch (Exception e) { LOG.error("Classify error", e); }
    }

    private static class Cluster {
        short symbolId;
        String symbol;
        long entryTime = Long.MAX_VALUE;
        long timeUpdate;
        float exit;            // priceTP
        float totalQty = 0f;
        int nLeg = 0;
        String closeType = "?";  // status (STOP_MARKET_DONE / STOP_LOSS_DONE / ...)
    }

    private static class Out {
        Cluster c;
        float high;
        double rel;            // (exit-high)/high
        double dPnl;           // totalQty*(exit-high)  >0 = bị thổi
        long lag;              // phút tới nến gần nhất từng chạm exit; -1 = fabrication
    }

    @SuppressWarnings("unchecked")
    public void run() throws Exception {
        SimpleSymbolMapper.getInstance().init();
        String file = SimulatorMarketLevelTicker1MStopLoss.FILE_STORAGE_ORDER_DONE;
        Object obj = Storage.readObjectFromFile(file);
        if (!(obj instanceof TreeMap)) {
            LOG.error("⛔ Không đọc được {} (chạy 1 backtest baseline để sinh file).", file);
            return;
        }
        TreeMap<Long, OrderTargetInfoTest> all = (TreeMap<Long, OrderTargetInfoTest>) obj;

        Map<String, Cluster> map = new HashMap<>();
        double totalPnlFile = 0;
        for (OrderTargetInfoTest o : all.values()) {
            totalPnlFile += o.calTp();
            Cluster c = map.computeIfAbsent(o.symbolId + "@" + o.timeUpdate, k -> {
                Cluster cc = new Cluster();
                cc.symbolId = o.symbolId;
                cc.symbol = SimpleSymbolMapper.getInstance().getSymbol(o.symbolId);
                cc.timeUpdate = o.timeUpdate;
                return cc;
            });
            c.entryTime = Math.min(c.entryTime, o.timeStart);
            if (o.priceTP != null) c.exit = o.priceTP;
            if (o.quantity != null) c.totalQty += o.quantity;
            if (o.status != null) c.closeType = o.status.name();
            c.nLeg++;
        }
        LOG.info("📥 {} leg / {} cụm. totalPnl(file)={} (tham chiếu OFF=70991).",
                all.size(), map.size(), f0(totalPnlFile));

        // ===== NV1: phát hiện OUT + đo lag + ΔPnL_kẹp =====
        List<Out> outs = new ArrayList<>();
        int nClusters = 0, nDelist = 0, nInRange = 0, nNoExit = 0;
        int binSmall = 0, binMid = 0, binBig = 0;
        Map<String, Integer> outByDay = new HashMap<>();

        for (Cluster c : map.values()) {
            if (c.exit <= 0) { nNoExit++; continue; }
            nClusters++;
            KlineObjectSimple k = aero(c.symbolId, c.timeUpdate);
            if (k == null) { nDelist++; continue; }
            double high = k.maxPrice;
            if (c.exit <= high * (1 + REL_TOL)) { nInRange++; continue; }
            Out o = new Out();
            o.c = c;
            o.high = (float) high;
            o.rel = (c.exit - high) / Math.max(high, 1e-9);
            o.dPnl = c.totalQty * (c.exit - high);
            outs.add(o);
            if (o.rel < 0.005) binSmall++;
            else if (o.rel <= 0.02) binMid++;
            else binBig++;
            outByDay.merge(Utils.normalizeDateYYYYMMDD(c.timeUpdate), 1, Integer::sum);
        }

        LOG.info("\n================ NV1 — EXIT NGOÀI nến (toàn bộ) ================");
        LOG.info("cụm có nến timeUpdate={} | OUT(exit>high)={} = {}% | in-range={} | delist/no-candle={} | no-exit={}",
                (nClusters - nDelist), outs.size(), pct(outs.size(), nClusters - nDelist), nInRange, nDelist, nNoExit);
        LOG.info("phân bố rel=(exit-high)/high: <0.5%%={} | 0.5-2%%={} | >2%%={}", binSmall, binMid, binBig);
        if (outs.isEmpty()) { LOG.info("✅ Không có ca OUT."); return; }

        // lag + fabrication (sort theo entryTime cho cache locality)
        outs.sort(Comparator.comparingLong(o -> o.c.entryTime));
        int fab = 0;
        for (Out o : outs) {
            long reach = nearestReach(o.c.symbolId, o.c.entryTime, o.c.timeUpdate, o.c.exit);
            o.lag = (reach < 0) ? -1 : (o.c.timeUpdate - reach) / Utils.TIME_MINUTE;
            if (reach < 0) fab++;
        }
        LOG.info("fabrication (KHÔNG nến nào trong kỳ giữ chạm exit) = {} (kỳ vọng ~0)", fab);

        // ===== bucket lag × ΔPnL =====
        int[] lagCnt = new int[5];
        double[] lagPnl = new double[5];
        for (Out o : outs) {
            int b = lagBucket(o.lag);
            lagCnt[b]++;
            lagPnl[b] += o.dPnl;
        }
        double totalClamp = 0;
        for (Out o : outs) totalClamp += o.dPnl;
        LOG.info("--- ΔPnL_kẹp theo bucket lag (count | ΣΔPnL) ---");
        for (int i = 0; i < 5; i++)
            LOG.info("   {} n={}  ΣΔPnL={}", LAG_LABELS[i], lagCnt[i], f0(lagPnl[i]));
        LOG.info("   TỔNG ΔPnL_kẹp = {} = {}% totalPnl(file)", f0(totalClamp),
                f2(100.0 * totalClamp / Math.max(Math.abs(totalPnlFile), 1e-9)));

        // ===== theo NĂM =====
        Map<Integer, double[]> byYear = new TreeMap<>();   // [count, dPnl]
        for (Out o : outs) {
            double[] v = byYear.computeIfAbsent(Utils.getYear(o.c.timeUpdate), y -> new double[2]);
            v[0]++; v[1] += o.dPnl;
        }
        LOG.info("--- ΔPnL_kẹp theo NĂM (count | ΣΔPnL) ---");
        for (int y : YEARS) {
            double[] v = byYear.get(y);
            LOG.info("   {} : n={}  ΣΔPnL={}", y, v == null ? 0 : (int) v[0], f0(v == null ? 0 : v[1]));
        }

        // ===== theo LOẠI CLOSE =====
        Map<String, double[]> byType = new TreeMap<>();
        for (Out o : outs) {
            double[] v = byType.computeIfAbsent(o.c.closeType, t -> new double[2]);
            v[0]++; v[1] += o.dPnl;
        }
        LOG.info("--- ΔPnL_kẹp theo LOẠI CLOSE (count | ΣΔPnL) ---");
        byType.forEach((t, v) -> LOG.info("   {} n={}  ΣΔPnL={}", t, (int) v[0], f0(v[1])));

        // ===== ngày sập 20251011 =====
        int crashN = 0; double crashPnl = 0;
        for (Out o : outs)
            if (CRASH_DAY.equals(Utils.normalizeDateYYYYMMDD(o.c.timeUpdate))) { crashN++; crashPnl += o.dPnl; }
        LOG.info("--- Ngày sập {} ---", CRASH_DAY);
        LOG.info("   n={} ({}% số ca OUT) | ΣΔPnL={} ({}% tổng ΔPnL_kẹp)", crashN,
                f1(100.0 * crashN / outs.size()), f0(crashPnl), f1(100.0 * crashPnl / Math.max(totalClamp, 1e-9)));

        LOG.info("--- Top ngày dồn OUT ---");
        outByDay.entrySet().stream().sorted((a, b) -> b.getValue() - a.getValue()).limit(10)
                .forEach(e -> LOG.info("   {} : {} ca", e.getKey(), e.getValue()));

        LOG.info("--- 10 ca THỔI NẶNG nhất (ΔPnL) ---");
        outs.stream().sorted((a, b) -> Double.compare(b.dPnl, a.dPnl)).limit(10)
                .forEach(o -> LOG.info("   {} {} {} rel={}% lag={}′ hold={}h legs={} exit={} high={} ΔPnL={}",
                        o.c.symbol, o.c.closeType, Utils.normalizeDateYYYYMMDDHHmm(o.c.timeUpdate),
                        f2(o.rel * 100), o.lag, f1((o.c.timeUpdate - o.c.entryTime) / (double) Utils.TIME_HOUR),
                        o.c.nLeg, f6(o.c.exit), f6(o.high), f0(o.dPnl)));

        // ===== 1 DÒNG KẾT =====
        LOG.info("\n📌 PHÁN QUYẾT NV1/NV2:");
        LOG.info("   Mọi OUT = trailing-stop loại (B) đóng-thật-giá-cũ (NV0). fabrication={} => fix GIÁ (kẹp priceTP≤high), KHÔNG sửa mốc.", fab);
        LOG.info("   ΔPnL dự kiến GIẢM = {} = {}% totalPnl, dồn năm: {}. Chờ duyệt rồi áp fix (NV3).",
                f0(totalClamp), f2(100.0 * totalClamp / Math.max(Math.abs(totalPnlFile), 1e-9)),
                topYear(byYear));
    }

    private static int lagBucket(long lag) {
        if (lag < 0) return 4;                 // fabrication xếp >1d (hiếm)
        for (int i = 0; i < LAG_EDGES.length; i++) if (lag <= LAG_EDGES[i]) return i;
        return 4;
    }

    private static String topYear(Map<Integer, double[]> byYear) {
        return byYear.entrySet().stream()
                .max(Comparator.comparingDouble(e -> e.getValue()[1]))
                .map(e -> e.getKey() + "(" + f0(e.getValue()[1]) + ")").orElse("-");
    }

    /** Phút GẦN NHẤT (lớn nhất ≤to) có nến high >= exit-tol. -1 nếu không có. Quét lùi theo ngày. */
    private long nearestReach(short sid, long from, long to, float exit) {
        double need = exit - Math.abs(exit) * REL_TOL;
        for (long anchor = tradingDayStart(to); anchor >= tradingDayStart(from); anchor -= Utils.TIME_DAY) {
            TreeMap<Long, KlineObjectSimple[]> day = getDay(anchor);
            if (day == null) continue;
            for (Map.Entry<Long, KlineObjectSimple[]> e : day.subMap(from, true, to, true).descendingMap().entrySet()) {
                KlineObjectSimple[] arr = e.getValue();
                if (arr == null || sid < 0 || sid >= arr.length) continue;
                KlineObjectSimple k = arr[sid];
                if (k != null && k.maxPrice >= need) return e.getKey();
            }
        }
        return -1;
    }

    private KlineObjectSimple aero(short sid, long minute) {
        TreeMap<Long, KlineObjectSimple[]> day = getDay(tradingDayStart(minute));
        if (day == null) return null;
        KlineObjectSimple[] arr = day.get(minute);
        if (arr == null || sid < 0 || sid >= arr.length) return null;
        return arr[sid];
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

    private static String pct(int a, int n) { return n > 0 ? f1(100.0 * a / n) : "-"; }
    private static String f6(double v) { return String.format(Locale.US, "%.6f", v); }
    private static String f2(double v) { return String.format(Locale.US, "%.2f", v); }
    private static String f1(double v) { return String.format(Locale.US, "%.1f", v); }
    private static String f0(double v) { return String.format(Locale.US, "%.0f", v); }
}
