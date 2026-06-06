package com.binance.chuyennd.ai_ml.validation.predict.market;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.validation.EdgeAttributionReport;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * NHIỆM VỤ B — Cross-check SỐ cho field minPrice (gốc của MAE trong EdgeAttributionReport).
 *
 * Tự tính lại MAE ĐỘC LẬP từ ticker thô (đáy chạy thật trong [timeStart, timeUpdate]) rồi so 2 nguồn:
 *
 *   old(minPrice) = legMaePctOld = (o.minPrice - entry)/entry   (field trailing CŨ — nghi reset-lên)
 *   new(maeLow)   = legMaePct    = (o.maeLow  - entry)/entry    (field đáy-thật MỚI thêm — phải đúng)
 *   independent   = (min(kline.minPrice trong [start,update]) - entry)/entry (đọc lại từ Aerospike)
 *
 * Đọc ticker đúng API mà sim dùng: readDataFromAerospike1M_ShortKey(anchor) -> 1 NGÀY giao dịch
 * (07:00 GMT+7 +1440'), TreeMap<phút, KlineObjectSimple[]> index theo symbolId. Lấy arr[o.symbolId].
 *
 * KỲ VỌNG SAU FIX: new ≈ independent (~100% khớp) ⇒ MAE đã đúng; old << independent (nông hơn, nhất là
 * cụm giữ lâu/đã trail) ⇒ tái khẳng định minPrice từng hỏng. READ-ONLY. Đây là bước TỰ-VERIFY của NV3.
 */
public class VerifyMinPriceMae {

    private static final Logger LOG = LoggerFactory.getLogger(VerifyMinPriceMae.class);

    private static final String START_DATE = "20210101";
    private static final String END_DATE = "20260601";
    private static final int SAMPLE = 600;          // số leg lấy mẫu (rải đều theo thời gian)
    private static final double TOL = 0.001;         // dung sai |recorded - independent|
    private static final int CACHE_DAYS = 200;       // LRU số ngày ticker giữ trong RAM

    /** LRU cache: key = mốc 07:00 GMT+7 của ngày giao dịch -> snapshot 1440' của ngày đó. */
    private final LinkedHashMap<Long, TreeMap<Long, KlineObjectSimple[]>> dayCache =
            new LinkedHashMap<Long, TreeMap<Long, KlineObjectSimple[]>>(16, 0.75f, true) {
                @Override
                protected boolean removeEldestEntry(Map.Entry<Long, TreeMap<Long, KlineObjectSimple[]>> e) {
                    return size() > CACHE_DAYS;
                }
            };

    public static void main(String[] args) {
        try { new VerifyMinPriceMae().run(); } catch (Exception e) { LOG.error("VerifyMinPriceMae error", e); }
    }

    public void run() throws Exception {
        Configs.IS_HPO_MODE = false;
        Configs.IS_KAGGLE_MODE = false;
        Configs.TIME_RUN = START_DATE;
        Configs.BREAKER_MODE = "OFF";
        LOG.info("🔒 PRE-FLIGHT: slippage={} lookahead_block={} FILTER_MODE={}",
                Configs.SLIPPAGE_RATE, Configs.BLOCK_INTRABAR_LOOKAHEAD, Configs.FILTER_MODE);

        long startTime = Utils.sdfFile.parse(START_DATE).getTime() + 7 * Utils.TIME_HOUR;
        long endTime = Utils.sdfFile.parse(END_DATE).getTime() + (24 * Utils.TIME_HOUR) - Utils.TIME_MINUTE;

        SimpleSymbolMapper.getInstance().init();
        LOG.info("📥 Nạp data Aerospike...");
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        TreeMap<Long, AiPredictionData> predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        TreeMap<Long, long[]> time2FundingPre = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();

        BudgetManagerSimple.resetInstance();
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();

        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        sim.initDataReady(time2MarketData, predictionMap, time2FundingPre, new AIRejectFilter());
        LOG.info("🚀 Chạy baseline full {} -> {}...", START_DATE, END_DATE);
        sim.simulatorWithInitEntry(startTime, endTime);

        analyze(sim);
    }

    private void analyze(SimulatorMarketLevelTicker1MStopLoss sim) {
        // leg đầu PREDICT_SYMBOL_TRADE, sort theo timeStart để mẫu rải đều + cache ticker tuần tự
        List<OrderTargetInfoTest> legs = new ArrayList<>(
                EdgeAttributionReport.firstLegsOf(sim.allOrderDone.values(), MarketLevelChange.PREDICT_SYMBOL_TRADE));
        legs.sort(Comparator.comparingLong(o -> o.timeStart));
        if (legs.isEmpty()) { LOG.warn("⚠️ Không có leg PREDICT_SYMBOL_TRADE."); return; }

        // stride sample rải đều toàn timeline
        List<OrderTargetInfoTest> sample = new ArrayList<>();
        int stride = Math.max(1, legs.size() / SAMPLE);
        for (int i = 0; i < legs.size() && sample.size() < SAMPLE; i += stride) sample.add(legs.get(i));
        LOG.info("\n================ VERIFY minPrice/MAE — mẫu {}/{} leg ================", sample.size(), legs.size());

        int matchedNew = 0, matchedOld = 0, skipped = 0, n = 0;
        // {|Δnew|, new, independent, holdHours, old, |Δold|}
        List<double[]> diffs = new ArrayList<>();
        for (OrderTargetInfoTest o : sample) {
            Float ind = independentMae(o);
            if (ind == null || Float.isNaN(ind)) { skipped++; continue; }
            float recNew = EdgeAttributionReport.legMaePct(o);      // maeLow (mới)
            float recOld = EdgeAttributionReport.legMaePctOld(o);   // minPrice (cũ)
            double dNew = Math.abs(recNew - ind);
            double dOld = Math.abs(recOld - ind);
            double holdH = (o.timeUpdate - o.timeStart) / (double) Utils.TIME_HOUR;
            diffs.add(new double[]{dNew, recNew, ind, holdH, recOld, dOld});
            if (dNew < TOL) matchedNew++;
            if (dOld < TOL) matchedOld++;
            n++;
        }
        if (n == 0) { LOG.warn("⚠️ Không tính được independent MAE (thiếu ticker)."); return; }

        diffs.sort((a, b) -> Double.compare(b[0], a[0]));   // giảm dần theo |Δnew|
        double[] absNewSorted = diffs.stream().mapToDouble(x -> x[0]).sorted().toArray();
        double[] absOldSorted = diffs.stream().mapToDouble(x -> x[5]).sorted().toArray();
        LOG.info("n so sánh={} (bỏ qua thiếu data={})", n, skipped);
        LOG.info("KHỚP independent (<{}):  new(maeLow)={} = {}%   |   old(minPrice)={} = {}%",
                TOL, matchedNew, f1(100.0 * matchedNew / n), matchedOld, f1(100.0 * matchedOld / n));
        LOG.info("|new-independent|: median={} p90={} max={}",
                f4(perc(absNewSorted, 50)), f4(perc(absNewSorted, 90)), f4(absNewSorted[absNewSorted.length - 1]));
        LOG.info("|old-independent|: median={} p90={} max={}",
                f4(perc(absOldSorted, 50)), f4(perc(absOldSorted, 90)), f4(absOldSorted[absOldSorted.length - 1]));

        LOG.info("--- 10 ca old LỆCH NẶNG NHẤT so independent (old | new | indep | hold) ---");
        diffs.sort((a, b) -> Double.compare(b[5], a[5]));   // theo |Δold|
        for (int i = 0; i < Math.min(10, diffs.size()); i++) {
            double[] x = diffs.get(i);
            LOG.info("   old={}% new={}% indep={}% | |Δold|={} |Δnew|={} | hold={}h",
                    f2(x[4] * 100), f2(x[1] * 100), f2(x[2] * 100), f4(x[5]), f4(x[0]), f1(x[3]));
        }

        // tương quan lệch OLD với độ dài giữ: tách <24h vs >=24h
        double dShort = 0, dLong = 0; int nShort = 0, nLong = 0;
        for (double[] x : diffs) {
            if (x[3] < 24) { dShort += x[5]; nShort++; } else { dLong += x[5]; nLong++; }
        }
        LOG.info("--- Lệch OLD(minPrice) theo độ dài giữ ---");
        LOG.info("   giữ <24h:  n={} mean|Δold|={}", nShort, nShort > 0 ? f4(dShort / nShort) : "-");
        LOG.info("   giữ >=24h: n={} mean|Δold|={}", nLong, nLong > 0 ? f4(dLong / nLong) : "-");

        // PHÁN QUYẾT (tự-verify fix)
        double pctNew = 100.0 * matchedNew / n, pctOld = 100.0 * matchedOld / n;
        LOG.info("\n📌 PHÁN QUYẾT (tự-verify fix MAE):");
        if (pctNew >= 98 && perc(absNewSorted, 50) < TOL) {
            LOG.info("   ✅ new(maeLow) khớp independent {}% (median~0) => FIX ĐÚNG: maeLow = đáy THẬT.", f1(pctNew));
            LOG.info("      old(minPrice) chỉ khớp {}% => tái khẳng định minPrice từng hỏng (reset-lên trailing).", f1(pctOld));
            if (nLong > 0 && nShort > 0 && (dLong / nLong) > (dShort / nShort) * 1.5)
                LOG.info("      Lệch OLD nặng hơn ở cụm giữ >=24h — đúng cơ chế kẹt minPrice.");
        } else {
            LOG.info("   🔴 new(maeLow) CHƯA khớp independent ({}% khớp, median={}) => FIX SAI, soi lại NV1:", f1(pctNew), f4(perc(absNewSorted, 50)));
            LOG.info("      kiểm tra carry-forward maeLow ở mergeOrder + copy ở closeOrder/tail-flush + tracking updatePriceByKlineSimple.");
        }
    }

    /** Đáy chạy thật của symbol (index symbolId) trong [timeStart, timeUpdate] -> MAE độc lập. null nếu thiếu. */
    private Float independentMae(OrderTargetInfoTest o) {
        if (o.priceEntry == null || o.priceEntry <= 0) return null;
        short sid = o.symbolId;
        float low = Float.MAX_VALUE;
        boolean any = false;
        // duyệt từng NGÀY giao dịch (07:00 GMT+7) phủ [timeStart, timeUpdate]
        for (long anchor = tradingDayStart(o.timeStart); anchor <= o.timeUpdate; anchor += Utils.TIME_DAY) {
            TreeMap<Long, KlineObjectSimple[]> day = getDay(anchor);
            if (day == null) continue;
            for (KlineObjectSimple[] arr : day.subMap(o.timeStart, true, o.timeUpdate, true).values()) {
                if (arr == null || sid < 0 || sid >= arr.length) continue;
                KlineObjectSimple k = arr[sid];
                if (k != null && k.minPrice > 0) { low = Math.min(low, k.minPrice); any = true; }
            }
        }
        if (!any) return Float.NaN;
        return (low - o.priceEntry) / o.priceEntry;
    }

    /** Mốc 07:00 GMT+7 của NGÀY GIAO DỊCH chứa t (cửa sổ [start,start+1440') mà readDataFromAerospike1M_ShortKey trả). */
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

    private TreeMap<Long, KlineObjectSimple[]> getDay(long anchor) {
        if (!dayCache.containsKey(anchor)) {
            try { dayCache.put(anchor, DataManagerAerospikeFloatSim.readDataFromAerospike1M_ShortKey(anchor)); }
            catch (Exception e) { dayCache.put(anchor, null); }
        }
        return dayCache.get(anchor);
    }

    private static double perc(double[] sorted, double p) {
        if (sorted.length == 0) return Double.NaN;
        int i = (int) Math.round(p / 100.0 * (sorted.length - 1));
        return sorted[Math.max(0, Math.min(sorted.length - 1, i))];
    }
    private static String f4(double v) { return String.format(Locale.US, "%.4f", v); }
    private static String f2(double v) { return String.format(Locale.US, "%.2f", v); }
    private static String f1(double v) { return String.format(Locale.US, "%.1f", v); }
}
