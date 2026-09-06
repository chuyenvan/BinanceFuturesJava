package com.binance.chuyennd.tradecore.selector;

import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * S1 FEATURE LIVE — 9 feature cua selector S1 (`research/pipeline/s1_rank.py` KEEP), tinh
 * real-time tu chuoi close 1h + 2 gia tri OI da tinh san.
 *
 * <p>CONG THUC KHOP TUNG DONG voi `research/pipeline/feat_v2_build.py` (pandas):
 * <ul>
 *   <li>{@code ret(n) = P/P.shift(n) - 1}</li>
 *   <li>{@code dd_7d  = P/P.rolling(168, min_periods=84).max() - 1}</li>
 *   <li>{@code vol_7d = R1.rolling(168, min_periods=84).std()} voi {@code R1 = P/P.shift(1)-1}, ddof=1</li>
 *   <li>{@code hrs_since_high_7d}: cua so 168; NaN neu {@code nan_count > 84}; {@code (167-argmax)/168}</li>
 *   <li>{@code rk_*} = {@code rank(axis=1, pct=True)} — rank trung binh cho tie, mau so = so coin CO gia tri</li>
 * </ul>
 *
 * <p>LUOI THOI GIAN: mang {@code closes} la luoi GIO day du (buoc 3_600_000 ms), gap = NaN,
 * KHONG ffill gia (giong `P.reindex(hours)` trong pipeline). Chi so {@code i} la vi tri "bay gio".
 *
 * <p>Lop nay THUAN TINH TOAN (khong I/O, khong state) de unit-test duoc.
 */
public final class S1FeatureLive {

    private S1FeatureLive() {
    }

    /** Thu tu feature KHOA — phai trung `KEEP` cua s1_rank.py va thu tu input cua model S1. */
    public static final String[] FEATURE_ORDER = {
            "vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d",
            "ret_3d", "rk_ret_3d", "ret_14d", "ls_global", "rk_oi_delta24h"
    };

    public static final int IDX_VOL_7D = 0;
    public static final int IDX_DD_7D = 1;
    public static final int IDX_RK_DD_7D = 2;
    public static final int IDX_HRS_SINCE_HIGH_7D = 3;
    public static final int IDX_RET_3D = 4;
    public static final int IDX_RK_RET_3D = 5;
    public static final int IDX_RET_14D = 6;
    public static final int IDX_LS_GLOBAL = 7;
    public static final int IDX_RK_OI_DELTA24H = 8;

    public static final long HOUR_MS = 3_600_000L;
    /** Cua so 7 ngay = 168 gio (dd_7d, vol_7d, hrs_since_high_7d). */
    public static final int W_7D = 168;
    /** {@code min_periods = max(2, 168 // 2)} trong feat_v2_build.py. */
    public static final int MINP_7D = Math.max(2, W_7D / 2);
    public static final int W_RET_3D = 72;
    public static final int W_RET_14D = 336;
    /** Lookback dai nhat = ret_14d = 336 gio => warm-up BAT BUOC 14 ngay. */
    public static final int WARMUP_HOURS = W_RET_14D;

    // ---------------------------------------------------------------- per-coin

    /** {@code P/P.shift(n) - 1} tai vi tri i. */
    public static double ret(double[] c, int i, int n) {
        if (c == null || i < 0 || i >= c.length || i - n < 0) return Double.NaN;
        double a = c[i], b = c[i - n];
        if (Double.isNaN(a) || Double.isNaN(b) || b == 0d) return Double.NaN;
        return a / b - 1d;
    }

    /** {@code rolling(w, min_periods=minp).max()} — cua so [max(0,i-w+1) .. i], bo qua NaN. */
    public static double rollMax(double[] c, int i, int w, int minp) {
        if (c == null || i < 0 || i >= c.length) return Double.NaN;
        int lo = Math.max(0, i - w + 1);
        int n = 0;
        double m = Double.NEGATIVE_INFINITY;
        for (int j = lo; j <= i; j++) {
            double v = c[j];
            if (!Double.isNaN(v)) {
                n++;
                if (v > m) m = v;
            }
        }
        return n >= minp ? m : Double.NaN;
    }

    /** {@code dd_7d = P/rmax(168) - 1} (luon <= 0). */
    public static double dd7d(double[] c, int i) {
        double mx = rollMax(c, i, W_7D, MINP_7D);
        if (Double.isNaN(mx) || mx == 0d) return Double.NaN;
        double v = c[i];
        if (Double.isNaN(v)) return Double.NaN;
        return v / mx - 1d;
    }

    /**
     * {@code hrs_since_high_7d}: y NGUYEN vong lap python — chi tinh khi {@code i >= 167};
     * NaN neu so NaN trong cua so {@code > 84}; ket qua {@code (167 - nanargmax)/168}.
     * {@code nanargmax} lay vi tri XUAT HIEN DAU TIEN cua gia tri lon nhat.
     */
    public static double hrsSinceHigh7d(double[] c, int i) {
        if (c == null || i < W_7D - 1 || i >= c.length) return Double.NaN;
        int lo = i - W_7D + 1;
        int nan = 0;
        for (int j = lo; j <= i; j++) if (Double.isNaN(c[j])) nan++;
        if (nan > W_7D / 2) return Double.NaN;
        int k = -1;
        double best = Double.NEGATIVE_INFINITY;
        for (int j = 0; j < W_7D; j++) {
            double v = c[lo + j];
            if (!Double.isNaN(v) && v > best) {
                best = v;
                k = j;
            }
        }
        if (k < 0) return Double.NaN;
        return (W_7D - 1 - k) / (double) W_7D;
    }

    /** {@code R1[j] = P[j]/P[j-1] - 1}. */
    public static double ret1h(double[] c, int j) {
        if (c == null || j < 1 || j >= c.length) return Double.NaN;
        double a = c[j], b = c[j - 1];
        if (Double.isNaN(a) || Double.isNaN(b) || b == 0d) return Double.NaN;
        return a / b - 1d;
    }

    /**
     * {@code vol_7d = R1.rolling(168, min_periods=84).std()} — do lech chuan MAU (ddof=1),
     * bo qua NaN. Dung hai luot (mean roi sum-of-squares quanh mean) de tranh mat do chinh xac.
     */
    public static double vol7d(double[] c, int i) {
        if (c == null || i < 0 || i >= c.length) return Double.NaN;
        int lo = Math.max(0, i - W_7D + 1);
        int n = 0;
        double s = 0d;
        for (int j = lo; j <= i; j++) {
            double r = ret1h(c, j);
            if (!Double.isNaN(r)) {
                n++;
                s += r;
            }
        }
        if (n < MINP_7D || n < 2) return Double.NaN;
        double mean = s / n;
        double ss = 0d;
        for (int j = lo; j <= i; j++) {
            double r = ret1h(c, j);
            if (!Double.isNaN(r)) {
                double d = r - mean;
                ss += d * d;
            }
        }
        return Math.sqrt(ss / (n - 1));
    }

    // ------------------------------------------------------------ cross-section

    /**
     * {@code Series.rank(pct=True)} cua pandas (method='average'): NaN giu NaN; tie chia rank
     * trung binh; mau so = SO PHAN TU CO GIA TRI (khong tinh NaN).
     */
    public static double[] rankPct(double[] v) {
        int n = v.length;
        double[] out = new double[n];
        Arrays.fill(out, Double.NaN);
        int cnt = 0;
        for (double x : v) if (!Double.isNaN(x)) cnt++;
        if (cnt == 0) return out;
        Integer[] idx = new Integer[cnt];
        int p = 0;
        for (int j = 0; j < n; j++) if (!Double.isNaN(v[j])) idx[p++] = j;
        Arrays.sort(idx, (a, b) -> Double.compare(v[a], v[b]));
        int j = 0;
        while (j < cnt) {
            int k = j;
            while (k + 1 < cnt && v[idx[k + 1]] == v[idx[j]]) k++;
            // rank 1-based trung binh cho doan tie [j..k]
            double avg = ((j + 1) + (k + 1)) / 2.0;
            for (int q = j; q <= k; q++) out[idx[q]] = avg / cnt;
            j = k + 1;
        }
        return out;
    }

    /**
     * Tinh 9 feature cho MOT tick.
     *
     * @param closes   {@code symbol -> mang close 1h} (cung do dai, cung luoi gio)
     * @param i        vi tri "bay gio" trong moi mang
     * @param lsGlobal {@code symbol -> ls_global} (da tinh san, live: LiveOiFeatProvider.lookup()[2])
     * @param oiDelta  {@code symbol -> oi_delta24h} (live: lookup()[0]) — chi dung de xep rank
     * @return {@code symbol -> double[9]} theo {@link #FEATURE_ORDER}
     */
    public static Map<String, double[]> computeTick(Map<String, double[]> closes, int i,
                                                    Map<String, Double> lsGlobal,
                                                    Map<String, Double> oiDelta) {
        String[] syms = closes.keySet().toArray(new String[0]);
        Arrays.sort(syms);
        int n = syms.length;
        double[] vol = new double[n], dd = new double[n], hrs = new double[n];
        double[] r3 = new double[n], r14 = new double[n], lsg = new double[n], oid = new double[n];
        for (int s = 0; s < n; s++) {
            double[] c = closes.get(syms[s]);
            vol[s] = vol7d(c, i);
            dd[s] = dd7d(c, i);
            hrs[s] = hrsSinceHigh7d(c, i);
            r3[s] = ret(c, i, W_RET_3D);
            r14[s] = ret(c, i, W_RET_14D);
            Double a = lsGlobal == null ? null : lsGlobal.get(syms[s]);
            Double b = oiDelta == null ? null : oiDelta.get(syms[s]);
            lsg[s] = a == null ? Double.NaN : a;
            oid[s] = b == null ? Double.NaN : b;
        }
        double[] rkDd = rankPct(dd);
        double[] rkR3 = rankPct(r3);
        double[] rkOi = rankPct(oid);
        Map<String, double[]> out = new LinkedHashMap<>();
        for (int s = 0; s < n; s++) {
            out.put(syms[s], new double[]{vol[s], dd[s], rkDd[s], hrs[s], r3[s], rkR3[s], r14[s], lsg[s], rkOi[s]});
        }
        return out;
    }
}
