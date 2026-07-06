package com.binance.chuyennd.ai_ml.wfo.framework.tasks;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoDataset;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Arrays;
import java.util.Calendar;
import java.util.Map;

/**
 * TASK-135b — Phân bố predReturn15M (biến của gate MOM15) để đặt lưới sweep THEO PHÂN VỊ,
 * thay vì giá trị cách đều tay (tránh phí điểm sweep ở vùng thưa dữ liệu).
 *
 * <p>Đo: percentile toàn cục + theo regime (bull/phẳng/crash) + histogram quanh vùng ngưỡng 0..0.06.
 * Mỗi ngưỡng candidate cho biết CẮT bao nhiêu % số mốc → biết bước ngưỡng nào tạo khác biệt thật.
 * KHÔNG backtest — chỉ quét mảng, chạy vài giây.
 */
public class Pred15DistProbe {
    private static final Logger LOG = LoggerFactory.getLogger(Pred15DistProbe.class);

    public static void main(String[] args) throws Exception {
        String dataDir = System.getenv().getOrDefault("WFO_DATA_DIR", "/home/ubuntu/claudedata/wfo_dataset_wf");
        WfoDataset ds = WfoDataset.load(dataDir);
        LOG.info("LOAD OK pred={}", ds.pred.size());

        // toàn bộ predReturn15M
        double[] all = new double[ds.pred.size()];
        int i = 0;
        for (AiPredictionData p : ds.pred.values()) all[i++] = p.predReturn15M;
        Arrays.sort(all);
        LOG.info("========== PHÂN BỐ predReturn15M TOÀN KỲ (n={}) ==========", all.length);
        double[] pcts = {1, 5, 10, 25, 40, 50, 60, 70, 75, 80, 85, 90, 95, 99};
        for (double p : pcts) LOG.info(String.format("  P%-4.0f = %.5f", p, pct(all, p)));
        LOG.info("  min=%.5f max=%.5f mean=%.5f", all[0], all[all.length-1], mean(all));

        // % số mốc BỊ CẮT (predReturn15M < thres) theo candidate — biết bước nào tạo khác biệt
        LOG.info("========== %% MỐC BỊ GATE CẮT theo ngưỡng (pred15 < thres) ==========");
        double[] cand = {0.005,0.010,0.012,0.015,0.018,0.020,0.022,0.025,0.028,0.030,0.035,0.040,0.045,0.050,0.060,0.070};
        LOG.info(String.format("%-8s %-10s %-12s", "thres", "%cắt", "%cắt-lũy-kế-Δ"));
        double prevCut = 0;
        for (double t : cand) {
            double cut = 100.0 * countBelow(all, t) / all.length;
            LOG.info(String.format("%-8.4f %-10.2f %+.2f", t, cut, cut - prevCut));
            prevCut = cut;
        }

        // phân bố theo regime (chia theo năm để thấy bull vs phẳng vs crash khác nhau)
        LOG.info("========== PHÂN BỐ theo NĂM (P25/P50/P75/P90) ==========");
        java.util.TreeMap<Integer, java.util.List<Double>> byYear = new java.util.TreeMap<>();
        Calendar cal = Calendar.getInstance();
        for (Map.Entry<Long, AiPredictionData> e : ds.pred.entrySet()) {
            cal.setTimeInMillis(e.getKey());
            byYear.computeIfAbsent(cal.get(Calendar.YEAR), k -> new java.util.ArrayList<>()).add((double) e.getValue().predReturn15M);
        }
        LOG.info(String.format("%-6s %-8s %-9s %-9s %-9s %-9s", "năm", "n", "P25", "P50", "P75", "P90"));
        for (Map.Entry<Integer, java.util.List<Double>> e : byYear.entrySet()) {
            double[] a = e.getValue().stream().mapToDouble(Double::doubleValue).sorted().toArray();
            LOG.info(String.format("%-6d %-8d %-9.5f %-9.5f %-9.5f %-9.5f",
                    e.getKey(), a.length, pct(a,25), pct(a,50), pct(a,75), pct(a,90)));
        }
        LOG.info("========== HET DIST ==========");
    }

    private static double pct(double[] sorted, double p) {
        if (sorted.length == 0) return 0;
        double idx = p / 100.0 * (sorted.length - 1);
        int lo = (int) Math.floor(idx), hi = (int) Math.ceil(idx);
        if (lo == hi) return sorted[lo];
        return sorted[lo] + (idx - lo) * (sorted[hi] - sorted[lo]);
    }
    private static int countBelow(double[] sorted, double t) {
        int lo = 0, hi = sorted.length;
        while (lo < hi) { int m = (lo + hi) >>> 1; if (sorted[m] < t) lo = m + 1; else hi = m; }
        return lo;
    }
    private static double mean(double[] a) { double s = 0; for (double v : a) s += v; return s / a.length; }
}
