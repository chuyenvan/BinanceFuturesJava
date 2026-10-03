package com.binance.chuyennd.tradecore.selector;

import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * GEOM FEATURE LIVE — 9 feature hinh hoc intraday (HIGH/LOW 1h) cho S1 ranker vong S1_FEAT_GEOM
 * ({@code docs/result/RESULT_S1_FEAT_GEOM.md}). THUAN TINH TOAN (khong I/O, khong state).
 *
 * <p>CONG THUC KHOP TUNG DONG voi {@code research/analysis/s1_geom_feat.py::geom_mats} (pandas/numpy):
 * <ul>
 *   <li>{@code roll(M, n, f) = DataFrame(M).rolling(n, min_periods=n//2).f()} — bo qua NaN, cua so ket thuc
 *       tai hang hien tai; min_periods 12 (24h) / 84 (168h)</li>
 *   <li>{@code TR = fmax(H-L, fmax(|H-Cprev|, |L-Cprev|))} — {@code np.fmax}: 1 ve NaN thi lay ve con lai</li>
 *   <li>{@code pos24 = (C-l24)/(h24-l24)} neu {@code h24-l24 > 0}, nguoc lai NaN; {@code pos7d} tuong tu 168h</li>
 *   <li>{@code dist_high24 = C/h24 - 1}; {@code dist_low24 = C/l24 - 1}; {@code range7d = (h7-l7)/C}</li>
 *   <li>{@code atr_ratio = ATR24/ATR168} (TB TR) neu {@code ATR168 > 0}</li>
 *   <li>moi gia tri khong huu han -> NaN; {@code rk_*} = {@code rank(axis=1, pct=True)} tren MOI symbol co gia tri
 *       trong gio (xem {@link S1FeatureLive#rankPct})</li>
 * </ul>
 * LUOI: mang {@code h,l,c} la luoi GIO day du (buoc 1h, gio DONG ts_h), gap = NaN (khong ffill).
 */
public final class GeomFeatureLive {

    private GeomFeatureLive() {
    }

    /** Thu tu KHOA — trung {@code GEOM} cua s1_geom_feat.py / s1_geom_kernel.py (cot 10..18 cua model S1-GEOM). */
    public static final String[] FEATURE_ORDER = {
            "pos24", "pos7d", "dist_high24", "dist_low24", "atr_ratio", "range7d",
            "rk_pos24", "rk_dist_low24", "rk_atr_ratio"
    };
    public static final int W_24 = 24;
    public static final int W_7D = 168;
    /** {@code min_periods = n // 2}. */
    public static final int MINP_24 = W_24 / 2;
    public static final int MINP_7D = W_7D / 2;
    /** 168 TR, TR dau tien can close gio truoc => toi thieu 169 gio lich su de khop cua so day du. */
    public static final int NEED_HOURS = W_7D + 1;

    /** {@code np.fmax}: NaN chi khi CA HAI la NaN. */
    static double fmax(double a, double b) {
        if (Double.isNaN(a)) return b;
        if (Double.isNaN(b)) return a;
        return Math.max(a, b);
    }

    /** {@code rolling(w, min_periods=w/2).max()} tai i (cua so [max(0,i-w+1)..i], bo qua NaN). */
    public static double rollMax(double[] x, int i, int w) {
        int lo = Math.max(0, i - w + 1), n = 0;
        double m = Double.NEGATIVE_INFINITY;
        for (int j = lo; j <= i; j++) {
            double v = x[j];
            if (!Double.isNaN(v)) {
                n++;
                if (v > m) m = v;
            }
        }
        return n >= w / 2 ? m : Double.NaN;
    }

    /** {@code rolling(w, min_periods=w/2).min()}. */
    public static double rollMin(double[] x, int i, int w) {
        int lo = Math.max(0, i - w + 1), n = 0;
        double m = Double.POSITIVE_INFINITY;
        for (int j = lo; j <= i; j++) {
            double v = x[j];
            if (!Double.isNaN(v)) {
                n++;
                if (v < m) m = v;
            }
        }
        return n >= w / 2 ? m : Double.NaN;
    }

    /** True range gio j: {@code fmax(H-L, fmax(|H-Cprev|, |L-Cprev|))}; j=0 -> Cprev = NaN. */
    public static double trueRange(double[] h, double[] l, double[] c, int j) {
        double cp = j >= 1 ? c[j - 1] : Double.NaN;
        return fmax(h[j] - l[j], fmax(Math.abs(h[j] - cp), Math.abs(l[j] - cp)));
    }

    /** {@code TR.rolling(w, min_periods=w/2).mean()} tai i. */
    public static double rollMeanTr(double[] h, double[] l, double[] c, int i, int w) {
        int lo = Math.max(0, i - w + 1), n = 0;
        double s = 0d;
        for (int j = lo; j <= i; j++) {
            double v = trueRange(h, l, c, j);
            if (!Double.isNaN(v)) {
                n++;
                s += v;
            }
        }
        return n >= w / 2 ? s / n : Double.NaN;
    }

    private static double fin(double v) {
        return (Double.isNaN(v) || Double.isInfinite(v)) ? Double.NaN : v;
    }

    /**
     * 6 feature per-coin tai i: {@code [pos24, pos7d, dist_high24, dist_low24, atr_ratio, range7d]}.
     */
    public static double[] perCoin(double[] h, double[] l, double[] c, int i) {
        double h24 = rollMax(h, i, W_24), l24 = rollMin(l, i, W_24);
        double h7 = rollMax(h, i, W_7D), l7 = rollMin(l, i, W_7D);
        double a24 = rollMeanTr(h, l, c, i, W_24), a168 = rollMeanTr(h, l, c, i, W_7D);
        double c0 = c[i];
        double r24 = h24 - l24, r7 = h7 - l7;
        return new double[]{
                fin(r24 > 0 ? (c0 - l24) / r24 : Double.NaN),
                fin(r7 > 0 ? (c0 - l7) / r7 : Double.NaN),
                fin(c0 / h24 - 1d),
                fin(c0 / l24 - 1d),
                fin(a168 > 0 ? a24 / a168 : Double.NaN),
                fin(r7 / c0)};
    }

    /**
     * 9 feature cho MOT gio. Rank cross-sectional tren TOAN BO symbol trong {@code bars} (offline: moi symbol cua
     * store co gia tri trong gio do) — KHONG phai tap ung vien selector.
     *
     * @param bars {@code symbol -> {h[], l[], c[]}} cung do dai, cung luoi gio
     * @param i    vi tri gio "bay gio"
     * @return {@code symbol -> double[9]} theo {@link #FEATURE_ORDER}, symbol sap xep tang dan
     */
    public static Map<String, double[]> computeTick(Map<String, double[][]> bars, int i) {
        String[] syms = bars.keySet().toArray(new String[0]);
        Arrays.sort(syms);
        int n = syms.length;
        double[][] pc = new double[n][];
        double[] p24 = new double[n], dl = new double[n], ar = new double[n];
        for (int s = 0; s < n; s++) {
            double[][] b = bars.get(syms[s]);
            pc[s] = perCoin(b[0], b[1], b[2], i);
            p24[s] = pc[s][0];
            dl[s] = pc[s][3];
            ar[s] = pc[s][4];
        }
        double[] rP = S1FeatureLive.rankPct(p24), rD = S1FeatureLive.rankPct(dl), rA = S1FeatureLive.rankPct(ar);
        Map<String, double[]> out = new LinkedHashMap<>();
        for (int s = 0; s < n; s++) {
            double[] v = pc[s];
            out.put(syms[s], new double[]{v[0], v[1], v[2], v[3], v[4], v[5], rP[s], rD[s], rA[s]});
        }
        return out;
    }
}
