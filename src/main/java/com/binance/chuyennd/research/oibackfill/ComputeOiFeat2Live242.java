package com.binance.chuyennd.research.oibackfill;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.TreeMap;

/**
 * CHẠY TRÊN ORACLE (không tính trên 242). Tính EXACT 5 OI feature (oiDelta24h, oiZ expanding,
 * lsGlobal, lsToptrader, takerBuy) — logic COPY CHÍNH XÁC {@code SelectorOiProvider.buildCoin} —
 * từ chuỗi OI CANONICAL = merge(Oracle-full 226 ∪ 242-recent forward), rồi PUSH chỉ đoạn ROLLING
 * gần đây (env {@code OI_FEAT_DAYS}, default 14) sang Aerospike-242 ({@link OiFeatLiveSets}, per-coin
 * Snappy map). Live chỉ lookup, không tính → không OOM, 242 chỉ nhận vài trăm MB (chừa margin ingress).
 *
 * <p>Vì sao merge 226+242: oiZ expanding cần TOÀN lịch sử (backfill trên Oracle/226 tới ~cutoff) +
 * điểm forward mới nhất (chỉ có trên 242). Oracle đọc được cả hai (Oracle→242:3222 open).
 *
 * <p>Env: {@code OI_FEAT_DAYS} (default 14) — số ngày rolling push. {@code OI_FEAT_DRY=1} — dry-run
 * (chỉ log range/sample, KHÔNG ghi 242) để verify nguồn trước khi bật ghi thật.
 *
 * <p>Chạy định kỳ (cron mỗi 15m) để giữ oi_feat_* trên 242 tươi. Idempotent (ghi đè theo ts).
 */
public class ComputeOiFeat2Live242 {

    private static final Logger LOG = LoggerFactory.getLogger(ComputeOiFeat2Live242.class);
    private static final long STALE_MS = 60L * 60_000L;   // 1h — khớp SelectorOiProvider
    private static final long DAY = 24L * 3600_000L;

    public static void main(String[] args) {
        int days = envInt("OI_FEAT_DAYS", 14);
        boolean dry = "1".equals(System.getenv("OI_FEAT_DRY"));
        long cutoff = System.currentTimeMillis() - days * DAY;
        Map<String, Short> syms = SimpleSymbolMapper.getInstance().getAllMappings();
        LOG.info("ComputeOiFeat2Live242 START | coins={} | rolling {} ngay (cutoff ts={}) | dry={}",
                syms.size(), days, cutoff, dry);

        int done = 0, pushed = 0, empty = 0;
        for (String coin : syms.keySet()) {
            try {
                TreeMap<Long, float[]> series = computeCoin(coin);
                TreeMap<Long, float[]> recent = new TreeMap<>(series.tailMap(cutoff, true));
                if (recent.isEmpty()) { empty++; continue; }

                // Tách 5 map. BỎ NaN (writeMetricMap242 serialize Gson -> NaN khong hop le JSON).
                // Lookup van dung: feature NaN tai ts nao -> khong luu -> lookup tra NaN dung cho do.
                // Data recent hau het non-NaN nen 5 set van cung tap ts (aligned) o vung lookup thuc te.
                TreeMap<Long, Float> mDelta = new TreeMap<>(), mZ = new TreeMap<>(),
                        mLsg = new TreeMap<>(), mLst = new TreeMap<>(), mTk = new TreeMap<>();
                for (Map.Entry<Long, float[]> e : recent.entrySet()) {
                    long t = e.getKey();
                    float[] v = e.getValue();
                    if (!Float.isNaN(v[0])) mDelta.put(t, v[0]);
                    if (!Float.isNaN(v[1])) mZ.put(t, v[1]);
                    if (!Float.isNaN(v[2])) mLsg.put(t, v[2]);
                    if (!Float.isNaN(v[3])) mLst.put(t, v[3]);
                    if (!Float.isNaN(v[4])) mTk.put(t, v[4]);
                }

                if (dry) {
                    if (done < 8) {
                        Map.Entry<Long, float[]> last = recent.lastEntry();
                        LOG.info("  [DRY {}] fullPts={} recentPts={} | lastTs={} oi5={}",
                                coin, series.size(), recent.size(), last.getKey(), fmt(last.getValue()));
                    }
                } else {
                    DataManagerAerospikeFloatSim.writeMetricMap242(OiFeatLiveSets.OI_DELTA24H, OiFeatLiveSets.BIN, coin, mDelta);
                    DataManagerAerospikeFloatSim.writeMetricMap242(OiFeatLiveSets.OI_Z, OiFeatLiveSets.BIN, coin, mZ);
                    DataManagerAerospikeFloatSim.writeMetricMap242(OiFeatLiveSets.LS_GLOBAL, OiFeatLiveSets.BIN, coin, mLsg);
                    DataManagerAerospikeFloatSim.writeMetricMap242(OiFeatLiveSets.LS_TOPTRADER, OiFeatLiveSets.BIN, coin, mLst);
                    DataManagerAerospikeFloatSim.writeMetricMap242(OiFeatLiveSets.TAKER_BUY, OiFeatLiveSets.BIN, coin, mTk);
                    pushed++;
                }
                done++;
                if (done % 100 == 0) LOG.info("  ... {} coin xu ly ({} push, {} empty)", done, pushed, empty);
            } catch (Exception e) {
                LOG.warn("coin {} loi: {}", coin, e.toString());
            }
        }
        LOG.info("ComputeOiFeat2Live242 DONE | processed={} pushed={} empty(no-oi)={}", done, pushed, empty);
        System.exit(0);
    }

    /** Merge Oracle-full (226/getClientOracle) ∪ 242-recent forward cho 1 metric raw. */
    private static TreeMap<Long, Float> mergedMetric(String set, String bin, String coin) {
        TreeMap<Long, Float> full = DataManagerAerospikeFloatSim.getMetricMap226(set, bin, coin);
        TreeMap<Long, Float> recent = DataManagerAerospikeFloatSim.getMetricMap242(set, bin, coin);
        TreeMap<Long, Float> out = (full == null) ? new TreeMap<>() : new TreeMap<>(full);
        if (recent != null) out.putAll(recent); // 242 forward moi hon -> ghi de overlap
        return out;
    }

    /** COPY CHÍNH XÁC SelectorOiProvider.buildCoin (expanding oiZ, oiDelta24h, ls/taker floor-stale). */
    private static TreeMap<Long, float[]> computeCoin(String coin) {
        TreeMap<Long, Float> oi = mergedMetric(OiMetricSets.OI.set, OiMetricSets.OI.bin, coin);
        TreeMap<Long, float[]> series = new TreeMap<>();
        if (oi.isEmpty()) return series;
        TreeMap<Long, Float> lsg = mergedMetric(OiMetricSets.LS_GLOBAL_ACC.set, OiMetricSets.LS_GLOBAL_ACC.bin, coin);
        TreeMap<Long, Float> lst = mergedMetric(OiMetricSets.LS_TOPTRADER_ACC.set, OiMetricSets.LS_TOPTRADER_ACC.bin, coin);
        TreeMap<Long, Float> tk = mergedMetric(OiMetricSets.TAKER_VOL.set, OiMetricSets.TAKER_VOL.bin, coin);

        double sum = 0, sumSq = 0;
        int n = 0;
        for (Map.Entry<Long, Float> en : oi.entrySet()) {
            long t = en.getKey();
            float oiVal = en.getValue();
            sum += oiVal;
            sumSq += (double) oiVal * oiVal;
            n++;
            float oiDelta = Float.NaN;
            Map.Entry<Long, Float> past = oi.floorEntry(t - DAY);
            if (past != null && (t - DAY - past.getKey()) <= STALE_MS && past.getValue() != 0f)
                oiDelta = oiVal / past.getValue() - 1f;
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
                    oiDelta, z,
                    lg == null ? Float.NaN : lg,
                    lt == null ? Float.NaN : lt,
                    takerBuy
            });
        }
        return series;
    }

    private static Float floorStale(TreeMap<Long, Float> m, long t) {
        if (m == null || m.isEmpty()) return null;
        Map.Entry<Long, Float> e = m.floorEntry(t);
        if (e == null || (t - e.getKey()) > STALE_MS) return null;
        return e.getValue();
    }

    private static String fmt(float[] v) {
        return String.format("[d=%.4f z=%.3f lsg=%.3f lst=%.3f tk=%.3f]", v[0], v[1], v[2], v[3], v[4]);
    }

    private static int envInt(String k, int d) {
        String v = System.getenv(k);
        try {
            return v == null ? d : Integer.parseInt(v.trim());
        } catch (Exception e) {
            return d;
        }
    }
}
