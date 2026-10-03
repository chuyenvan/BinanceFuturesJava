package com.binance.chuyennd.tradecore.selector;

import org.junit.Test;

import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * Unit test {@link GeomFeatureLive} — lap lai DUNG {@code unit_tests()} cua research/analysis/s1_geom_feat.py,
 * cong min_periods (warm-up thieu -> NaN nhu pandas), np.fmax cua TR, rank pct va cac nhanh NaN.
 */
public class GeomFeatureLiveTest {

    private static final double E = 1e-12;

    private static double[] ramp(int n, double add) {
        double[] c = new double[n];
        for (int i = 0; i < n; i++) c[i] = 100d + i + add;
        return c;
    }

    private static double[] nan(int n) {
        double[] a = new double[n];
        Arrays.fill(a, Double.NaN);
        return a;
    }

    /** s1_geom_feat.unit_tests dong 1-4: H=L=C tang deu. */
    @Test
    public void rampHlcEqual() {
        int n = 400, i = n - 1;
        double[] c = ramp(n, 0);
        double[] f = GeomFeatureLive.perCoin(c, c, c, i);
        assertEquals(1d, f[0], E);                                   // pos24
        assertEquals(0d, f[2], E);                                   // dist_high24
        assertEquals(c[i] / c[n - 24] - 1d, f[3], E);                // dist_low24
        assertEquals((c[i] - c[n - 168]) / c[i], f[5], E);           // range7d
        assertEquals(1d, f[4], E);                                   // atr_ratio: TR = 1 moi gio
        assertEquals(1d, f[1], E);                                   // pos7d
    }

    /** s1_geom_feat.unit_tests dong 5-6: H = C+2, L = C-2, Cprev = C-1 -> TR = max(4, 3, 1) = 4 deu (comment python ghi 5 la sai, assert python chi kiem atr_ratio = 1). */
    @Test
    public void rampWithBand() {
        int n = 400, i = n - 1;
        double[] c = ramp(n, 0), h = ramp(n, 2), l = ramp(n, -2);
        double[] f = GeomFeatureLive.perCoin(h, l, c, i);
        assertEquals((c[i] - (c[n - 24] - 2)) / ((c[i] + 2) - (c[n - 24] - 2)), f[0], E);
        assertEquals(1d, f[4], E);
        assertEquals(4d, GeomFeatureLive.trueRange(h, l, c, i), E);
    }

    /** min_periods = n//2: 24h can >= 12 gio co gia tri, 168h can >= 84 (warm-up thieu -> NaN nhu pandas). */
    @Test
    public void minPeriodsWarmup() {
        int n = 200, i = n - 1;
        double[] c = nan(n), h = nan(n), l = nan(n);
        for (int k = n - 11; k < n; k++) c[k] = h[k] = l[k] = 50d + k;    // 11 gio
        double[] f = GeomFeatureLive.perCoin(h, l, c, i);
        for (double v : f) assertTrue(Double.isNaN(v));
        c[n - 12] = h[n - 12] = l[n - 12] = 50d + n - 12;                // 12 gio -> 24h co, 168h chua
        f = GeomFeatureLive.perCoin(h, l, c, i);
        assertEquals(1d, f[0], E);
        assertEquals(0d, f[2], E);
        assertTrue(Double.isNaN(f[1]));   // pos7d
        assertTrue(Double.isNaN(f[4]));   // atr_ratio (ATR168 chua du 84)
        assertTrue(Double.isNaN(f[5]));   // range7d
        for (int k = n - 84; k < n; k++) c[k] = h[k] = l[k] = 50d + k;    // 84 gio -> du 168h
        f = GeomFeatureLive.perCoin(h, l, c, i);
        assertEquals(1d, f[1], E);
        assertEquals((c[i] - c[n - 84]) / c[i], f[5], E);
    }

    /** np.fmax: close gio truoc NaN -> TR = H-L (khong NaN); ca gio NaN -> TR NaN (bi bo khoi mean). */
    @Test
    public void trueRangeFmax() {
        double[] h = {10, 12, Double.NaN, 15}, l = {8, 9, Double.NaN, 11}, c = {Double.NaN, 11, Double.NaN, 14};
        assertEquals(2d, GeomFeatureLive.trueRange(h, l, c, 0), E);   // j=0: Cprev NaN
        assertEquals(3d, GeomFeatureLive.trueRange(h, l, c, 1), E);   // Cprev = c[0] NaN -> H-L = 3
        assertTrue(Double.isNaN(GeomFeatureLive.trueRange(h, l, c, 2)));
        assertEquals(4d, GeomFeatureLive.trueRange(h, l, c, 3), E);   // Cprev = c[2] NaN -> H-L = 4
    }

    /** Nen phang (H=L=C) 24h: r24 = 0 -> pos24 NaN; ATR = 0 ca 168h -> atr_ratio NaN. */
    @Test
    public void flatGivesNaN() {
        int n = 200, i = n - 1;
        double[] c = new double[n];
        Arrays.fill(c, 7d);
        double[] f = GeomFeatureLive.perCoin(c, c, c, i);
        assertTrue(Double.isNaN(f[0]));
        assertTrue(Double.isNaN(f[1]));
        assertEquals(0d, f[2], E);
        assertEquals(0d, f[3], E);
        assertTrue(Double.isNaN(f[4]));
        assertEquals(0d, f[5], E);
    }

    /** TR co Cprev huu han: max(H-L, |H-Cp|, |L-Cp|). */
    @Test
    public void trueRangeGap() {
        double[] h = {10, 12}, l = {8, 9}, c = {13, 11};
        assertEquals(4d, GeomFeatureLive.trueRange(h, l, c, 1), E);   // max(3, 1, 4)
    }

    /**
     * Rank cross-sectional: tren MOI symbol co gia tri (NaN loai khoi mau so), tie = rank trung binh;
     * thu tu cot = FEATURE_ORDER; 6 cot per-coin khong doi khi them symbol.
     */
    @Test
    public void computeTickRanks() {
        int n = 200, i = n - 1;
        Map<String, double[][]> bars = new LinkedHashMap<>();
        double[] a = ramp(n, 0);                       // pos24 = 1
        double[] b = ramp(n, 0);
        double[] bl = ramp(n, -2), bh = ramp(n, 2);    // pos24 < 1
        double[] flat = new double[n];
        Arrays.fill(flat, 5d);                         // pos24 NaN
        bars.put("CCCUSDT", new double[][]{a, a, a});
        bars.put("AAAUSDT", new double[][]{bh, bl, b});
        bars.put("BBBUSDT", new double[][]{a.clone(), a.clone(), a.clone()});
        bars.put("DDDUSDT", new double[][]{flat, flat, flat});
        Map<String, double[]> out = GeomFeatureLive.computeTick(bars, i);
        assertEquals(Arrays.asList("AAAUSDT", "BBBUSDT", "CCCUSDT", "DDDUSDT"), Arrays.asList(out.keySet().toArray()));
        assertEquals(1d / 3d, out.get("AAAUSDT")[6], E);           // nho nhat trong 3 gia tri huu han
        assertEquals(2.5d / 3d, out.get("BBBUSDT")[6], E);         // tie B=C -> (2+3)/2 / 3
        assertEquals(2.5d / 3d, out.get("CCCUSDT")[6], E);
        assertTrue(Double.isNaN(out.get("DDDUSDT")[6]));
        double[] solo = GeomFeatureLive.perCoin(bh, bl, b, i);
        for (int j = 0; j < 6; j++) assertEquals(solo[j], out.get("AAAUSDT")[j], 0d);
        assertEquals(9, GeomFeatureLive.FEATURE_ORDER.length);
    }
}
