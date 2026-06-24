package com.binance.chuyennd.ai_ml.onnx.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.research.oibackfill.OiMetricSets;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.TreeMap;

/**
 * TASK-109 bước 3b — OI per-coin provider cho selector inference Java (OI cách 1: nạp RAM + merge backward).
 *
 * Tái lập CHÍNH XÁC logic ExportFundingOiPerCoin.writeCoin (nguồn sinh oi_percoin Python merge ở train 039):
 *   - oiDelta24h = oi(t)/oi(t-24h) - 1   (floorEntry(t-DAY), stale ≤ 1h, denom ≠ 0; null→NaN)
 *   - oiZ        = (oi(t)-mean)/std EXPANDING (mean/std tích lũy toàn lịch sử ≤ t, no-leak; n<2 → NaN)
 *   - lsGlobal, lsToptrader = floorStale(t) stale ≤ 1h
 *   - takerBuy   = r/(1+r), r = floorStale taker ratio
 * Sau đó merge_asof BACKWARD tol 2h (khớp Python train) khi lookup(coin, t Tool1).
 *
 * Khác Python ở chỗ TÍNH (Java reproduce) thay vì đọc file .bin Python — Python chỉ còn là baseline validate.
 * Nạp 1 lần per-coin vào RAM (Oracle 23GB đủ). oiZ expanding tính trên TOÀN lịch sử OI nên build map đầy đủ
 * rồi mới lookup theo range.
 */
public class SelectorOiProvider {
    private static final Logger LOG = LoggerFactory.getLogger(SelectorOiProvider.class);
    private static final long STALE_MS = 60L * 60_000L;       // 1h — khớp writeCoin
    private static final long DAY = 24L * 3600_000L;
    private static final long MERGE_TOL_MS = 2L * 60L * 60_000L;  // 2h — khớp Python merge_asof tolerance

    /** Map coin -> (ts OI -> oi5[oiDelta24h, oiZ, lsGlobal, lsToptrader, takerBuy]). NaN cho ô thiếu. */
    private final Map<String, TreeMap<Long, float[]>> coin2Series = new java.util.HashMap<>();

    /** Build chuỗi OI feature cho 1 coin (gọi lazy hoặc preload). Trả map rỗng nếu coin không có OI. */
    public TreeMap<Long, float[]> buildCoin(String coin) {
        TreeMap<Long, float[]> cached = coin2Series.get(coin);
        if (cached != null) return cached;

        TreeMap<Long, Float> oi = DataManagerAerospikeFloatSim.getMetricMap226(OiMetricSets.OI.set, OiMetricSets.OI.bin, coin);
        TreeMap<Long, float[]> series = new TreeMap<>();
        if (oi == null || oi.isEmpty()) {
            coin2Series.put(coin, series);
            return series;
        }
        TreeMap<Long, Float> lsg = DataManagerAerospikeFloatSim.getMetricMap226(OiMetricSets.LS_GLOBAL_ACC.set, OiMetricSets.LS_GLOBAL_ACC.bin, coin);
        TreeMap<Long, Float> lst = DataManagerAerospikeFloatSim.getMetricMap226(OiMetricSets.LS_TOPTRADER_ACC.set, OiMetricSets.LS_TOPTRADER_ACC.bin, coin);
        TreeMap<Long, Float> tk = DataManagerAerospikeFloatSim.getMetricMap226(OiMetricSets.TAKER_VOL.set, OiMetricSets.TAKER_VOL.bin, coin);

        // EXPANDING oiZ: duyệt theo thứ tự thời gian tăng dần (TreeMap đã sort), tích lũy sum/sumSq.
        double sum = 0, sumSq = 0;
        int n = 0;
        for (Map.Entry<Long, Float> en : oi.entrySet()) {
            long t = en.getKey();
            float oiVal = en.getValue();
            sum += oiVal;
            sumSq += (double) oiVal * oiVal;
            n++;
            // oiDelta24h
            float oiDelta = Float.NaN;
            Map.Entry<Long, Float> past = oi.floorEntry(t - DAY);
            if (past != null && (t - DAY - past.getKey()) <= STALE_MS && past.getValue() != 0f)
                oiDelta = oiVal / past.getValue() - 1f;
            // oiZ expanding
            float z = Float.NaN;
            if (n >= 2) {
                double mean = sum / n;
                double var = (sumSq - (sum * sum) / n) / (n - 1);
                if (var > 0) z = (float) ((oiVal - mean) / Math.sqrt(var));
            }
            Float lg = floorStale(lsg, t);
            Float lt = floorStale(lst, t);
            Float r = floorStale(tk, t);
            float takerBuy = (r != null && r >= 0f) ? r / (1f + r) : Float.NaN;
            series.put(t, new float[]{
                    oiDelta,
                    z,
                    lg == null ? Float.NaN : lg,
                    lt == null ? Float.NaN : lt,
                    takerBuy
            });
        }
        coin2Series.put(coin, series);
        return series;
    }

    /**
     * Tra OI5 cho (coin, t Tool1): merge_asof BACKWARD tol 2h — record OI gần nhất ≤ t trong vòng 2h.
     * Trả float[5] (có thể chứa NaN từng phần); nếu không có OI ≤ t trong tol → cả 5 = NaN.
     */
    public float[] lookup(String coin, long t) {
        TreeMap<Long, float[]> series = buildCoin(coin);
        if (series.isEmpty()) return nan5();
        Map.Entry<Long, float[]> e = series.floorEntry(t);
        if (e == null || (t - e.getKey()) > MERGE_TOL_MS) return nan5();
        return e.getValue();
    }

    private static Float floorStale(TreeMap<Long, Float> m, long t) {
        if (m == null || m.isEmpty()) return null;
        Map.Entry<Long, Float> e = m.floorEntry(t);
        if (e == null || (t - e.getKey()) > STALE_MS) return null;
        return e.getValue();
    }

    private static float[] nan5() {
        return new float[]{Float.NaN, Float.NaN, Float.NaN, Float.NaN, Float.NaN};
    }

    public void clear() {
        coin2Series.clear();
    }
}
