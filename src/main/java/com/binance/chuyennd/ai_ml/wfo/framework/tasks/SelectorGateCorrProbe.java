package com.binance.chuyennd.ai_ml.wfo.framework.tasks;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoDataset;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * TASK-135 — Đo TƯƠNG QUAN giữa selector-score (per-coin) và predReturn15M (toàn cục, gate dùng).
 *
 * <p>Câu hỏi kiến trúc (Uni): gate MOM15 base trên market (predReturn15M — 1 giá trị/timestamp),
 * selector base trên cả market + riêng coin (score per-coin). Hai tín hiệu này TRÙNG hay TRỰC GIAO?
 *   - Tương quan CAO → gate market-level thừa (selector đã encode regime) → gộp 1 AI hợp lý.
 *   - Tương quan THẤP/TRỰC GIAO → gate bổ sung thông tin THẬT (chiều thời gian/regime mà selector thiếu)
 *     → giữ 2 AI có cơ sở.
 *
 * <p>KHÔNG train gì. Chỉ đọc dataset, ghép theo timestamp, tính Pearson + Spearman giữa:
 *   x = predReturn15M(t) [toàn cục, lặp cho mọi coin tại t]
 *   y = selectorScore(coin, t) [per-coin, = 1 - P(win) semantics; điểm THẤP = coin tốt]
 * trên toàn bộ cặp (coin,t). Cũng đo ở cấp AGG (mỗi t: score TB của coin đẹp nhất) để bớt nhiễu.
 */
public class SelectorGateCorrProbe {
    private static final Logger LOG = LoggerFactory.getLogger(SelectorGateCorrProbe.class);

    public static void main(String[] args) throws Exception {
        String dataDir = System.getenv().getOrDefault("WFO_DATA_DIR", "/home/ubuntu/claudedata/wfo_dataset_wf");
        WfoDataset ds = WfoDataset.load(dataDir);
        LOG.info("LOAD OK market={} pred={} funding={}", ds.market.size(), ds.pred.size(), ds.funding.size());

        // Ghép theo timestamp có CẢ pred lẫn funding. Lấy mẫu để không nổ RAM (bước nhảy).
        // Mỗi t: predReturn15M toàn cục (x), và với mỗi coin score (y).
        // Đo 2 cấp: (1) PAIR-level: mọi (coin,t); (2) BEST-level: mỗi t lấy score coin tốt nhất (min score).
        List<double[]> pairXY = new ArrayList<>();   // [x=pred15, y=score]
        List<double[]> bestXY = new ArrayList<>();    // [x=pred15, y=minScore@t]

        long stepSample = 0;
        int SAMPLE_EVERY = Integer.parseInt(System.getenv().getOrDefault("CORR_SAMPLE_EVERY", "5")); // lấy 1/5 timestamp

        for (Map.Entry<Long, long[]> e : ds.funding.entrySet()) {
            long t = e.getKey();
            if ((stepSample++ % SAMPLE_EVERY) != 0) continue;
            AiPredictionData pr = ds.pred.get(t);
            if (pr == null) continue;
            double x = pr.predReturn15M;
            long[] arr = e.getValue();
            if (arr == null || arr.length == 0) continue;
            double minScore = Double.MAX_VALUE;
            for (long enc : arr) {
                double score = Float.intBitsToFloat((int) enc);
                pairXY.add(new double[]{x, score});
                if (score < minScore) minScore = score;
            }
            bestXY.add(new double[]{x, minScore});
        }

        LOG.info("SAMPLE_EVERY={} | #cap PAIR={} #timestamp BEST={}", SAMPLE_EVERY, pairXY.size(), bestXY.size());
        report("PAIR (moi coin,t): pred15 vs selectorScore", pairXY);
        report("BEST (moi t: pred15 vs score coin tot nhat)", bestXY);
        LOG.info("========== HET CORR ==========");
    }

    private static void report(String label, List<double[]> xy) {
        if (xy.size() < 10) { LOG.info("{}: qua it mau ({})", label, xy.size()); return; }
        double[] x = new double[xy.size()], y = new double[xy.size()];
        for (int i = 0; i < xy.size(); i++) { x[i] = xy.get(i)[0]; y[i] = xy.get(i)[1]; }
        double pear = pearson(x, y);
        double spear = spearman(x, y);
        LOG.info("{}", label);
        LOG.info("  n={} Pearson={} Spearman={} | |r|<0.1=truc giao(gate bo sung thong tin), |r|>0.5=trung(gate thua)",
                xy.size(), String.format("%.4f", pear), String.format("%.4f", spear));
    }

    private static double pearson(double[] x, double[] y) {
        int n = x.length;
        double mx = 0, my = 0;
        for (int i = 0; i < n; i++) { mx += x[i]; my += y[i]; }
        mx /= n; my /= n;
        double sxy = 0, sxx = 0, syy = 0;
        for (int i = 0; i < n; i++) {
            double dx = x[i] - mx, dy = y[i] - my;
            sxy += dx * dy; sxx += dx * dx; syy += dy * dy;
        }
        return (sxx > 0 && syy > 0) ? sxy / Math.sqrt(sxx * syy) : 0;
    }

    private static double spearman(double[] x, double[] y) {
        return pearson(rank(x), rank(y));
    }

    private static double[] rank(double[] a) {
        int n = a.length;
        Integer[] idx = new Integer[n];
        for (int i = 0; i < n; i++) idx[i] = i;
        java.util.Arrays.sort(idx, (i, j) -> Double.compare(a[i], a[j]));
        double[] r = new double[n];
        for (int k = 0; k < n; k++) r[idx[k]] = k;
        return r;
    }
}
