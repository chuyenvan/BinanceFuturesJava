package com.binance.chuyennd.ai_ml.wfo.framework.tasks;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoDataset;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Calendar;
import java.util.Map;
import java.util.TreeMap;

/**
 * TASK-134 — MỔ w13 (OOS 2025Q2 ZERO_TRADES ở cả vế A lẫn D, bất kể seed).
 *
 * <p>KHÔNG chạy sim. Chỉ đọc dataset offline + tái hiện CHÍNH XÁC 2 cổng sinh entry của
 * {@code SimulatorMarketLevelTicker1MStopLoss}:
 * <ul>
 *   <li>Cổng 1 (market-level): cần {@code predict!=null && marketData!=null} rồi
 *       {@code getMarketStatus1M(...) != null}. Với OFF_FLAT_HARD=true chỉ còn nhánh BIG_DOWN sống:
 *       {@code rateDownAvg < MS_DOWN_BIG_AVG}. Đếm theo tháng số tick levelChange!=null.</li>
 *   <li>Cổng 2 (PREDICT_SYMBOL_TRADE): cần funding pred phủ (time2SymbolPred có key ts).</li>
 * </ul>
 * Đếm theo THÁNG 2025 để so tháng OOS w13 (04,05,06) với tháng IS có trade → tìm vì sao ZERO.
 * Số MS_DOWN_BIG_AVG lấy từ range gene [-0.055,-0.020]: quét NGƯỠNG để xem độ nhạy.
 */
public class W13Diagnose {
    private static final Logger LOG = LoggerFactory.getLogger(W13Diagnose.class);

    public static void main(String[] args) throws Exception {
        String dataDir = System.getenv().getOrDefault("WFO_DATA_DIR", "/home/ubuntu/claudedata/wfo_dataset_wf");
        WfoDataset ds = WfoDataset.load(dataDir);
        LOG.info("LOAD OK: market={} pred={} funding={}", ds.market.size(), ds.pred.size(), ds.funding.size());
        LOG.info("OFF_FLAT_HARD={} MS_DOWN_BIG_AVG default={} (gene range -0.055..-0.020)",
                Configs.OFF_FLAT_HARD, Configs.MS_DOWN_BIG_AVG);

        // Ngưỡng quét: cận gene, giữa, default, cận kia
        float[] thresholds = {-0.020f, -0.03157f, -0.045f, -0.055f};

        // Đếm theo tháng cho 2025 (bao IS cuối + OOS w13 = 2025-04,05,06)
        // key = YYYYMM
        TreeMap<Integer, long[]> monthStats = new TreeMap<>();
        // [0]=tickMarket [1]=tickPred [2]=tickBoth [3]=bigDownAtDefault [4]=fundingCovered
        // + phân bố rateDownAvg: [5]=min(scaled 1e6) dùng riêng mảng khác
        TreeMap<Integer, Float> monthMinDown = new TreeMap<>();
        TreeMap<Integer, Float> monthSumDown = new TreeMap<>();
        // đếm bigDown theo từng threshold: map month -> int[thresholds.length]
        TreeMap<Integer, int[]> monthBigDownByThres = new TreeMap<>();

        long y2025Start = Utils.sdfFile.parse("20250101").getTime() + 7 * Utils.TIME_HOUR;
        long y2025End = Utils.sdfFile.parse("20250701").getTime() + 7 * Utils.TIME_HOUR;

        Calendar cal = Calendar.getInstance();
        for (Map.Entry<Long, MarketDataObject> e : ds.market.subMap(y2025Start, true, y2025End, false).entrySet()) {
            long ts = e.getKey();
            MarketDataObject md = e.getValue();
            cal.setTimeInMillis(ts);
            int ym = cal.get(Calendar.YEAR) * 100 + (cal.get(Calendar.MONTH) + 1);

            long[] st = monthStats.computeIfAbsent(ym, k -> new long[6]);
            int[] bd = monthBigDownByThres.computeIfAbsent(ym, k -> new int[thresholds.length]);
            st[0]++; // tickMarket

            AiPredictionData pr = ds.pred.get(ts);
            boolean hasPred = pr != null;
            if (hasPred) st[1]++;
            if (hasPred && md != null) st[2]++;

            // nhánh BIG_DOWN sống (OFF_FLAT_HARD): rateDownAvg < thres
            for (int i = 0; i < thresholds.length; i++) {
                if (md.rateDownAvg < thresholds[i]) bd[i]++;
            }
            if (md.rateDownAvg < Configs.MS_DOWN_BIG_AVG) st[3]++;

            // funding coverage
            if (ds.funding.containsKey(ts)) st[4]++;

            monthMinDown.merge(ym, md.rateDownAvg, Math::min);
            monthSumDown.merge(ym, md.rateDownAvg, Float::sum);
        }

        LOG.info("========== THỐNG KÊ THEO THÁNG 2025 (w13 OOS = 2025-04,05,06) ==========");
        LOG.info(String.format("%-7s %9s %9s %9s %11s %10s %9s %10s",
                "thang", "tickMkt", "tickPred", "both", "bigDown@def", "funding", "minDown", "avgDown"));
        for (Map.Entry<Integer, long[]> e : monthStats.entrySet()) {
            int ym = e.getKey();
            long[] st = e.getValue();
            float avg = st[0] > 0 ? monthSumDown.get(ym) / st[0] : 0f;
            LOG.info(String.format("%-7d %9d %9d %9d %11d %10d %9.5f %10.5f",
                    ym, st[0], st[1], st[2], st[3], st[4], monthMinDown.get(ym), avg));
        }

        LOG.info("========== SỐ TICK BIG_DOWN THEO NGƯỠNG (quét gene range) ==========");
        StringBuilder hdr = new StringBuilder(String.format("%-7s", "thang"));
        for (float t : thresholds) hdr.append(String.format("%12s", String.format("<%.4f", t)));
        LOG.info(hdr.toString());
        for (Map.Entry<Integer, int[]> e : monthBigDownByThres.entrySet()) {
            StringBuilder sb = new StringBuilder(String.format("%-7d", e.getKey()));
            for (int c : e.getValue()) sb.append(String.format("%12d", c));
            LOG.info(sb.toString());
        }
        LOG.info("========== KẾT THÚC — đọc: bigDown≈0 ở tháng OOS => market-signal chết => ZERO_TRADES ==========");
    }
}
