package com.binance.chuyennd.tradecore.selector;

import org.junit.Test;

import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * Unit test cho {@link S1FeatureLive} — lap lai DUNG cac phep thu V3(a) cua
 * {@code research/pipeline/feat_v2_build.py} tren chuoi tong hop, cong them
 * tie/NaN cua {@code rank(pct=True)} va ddof=1 cua {@code vol_7d}.
 */
public class S1FeatureLiveTest {

    private static double[] linear(int n) {
        double[] c = new double[n];
        for (int i = 0; i < n; i++) c[i] = 100d + i;
        return c;
    }

    /** unit ret_3d tren chuoi tuyen tinh (V3(a) dong 1 cua feat_v2_build.py). */
    @Test
    public void retMatchesPandasOnLinearSeries() {
        double[] c = linear(1000);
        assertEquals(1099d / 1027d - 1d, S1FeatureLive.ret(c, 999, 72), 1e-12);
        assertEquals(Double.NaN, S1FeatureLive.ret(c, 10, 72), 0d);
    }

    /** unit dd_7d = 0 khi gia tang deu (dinh = hien tai). */
    @Test
    public void dd7dZeroOnRisingSeries() {
        double[] c = linear(1000);
        assertEquals(0d, S1FeatureLive.dd7d(c, 999), 1e-12);
    }

    /** unit dd_7d sau buoc nhay -50%: -0.5 roi ve 0 khi dinh roi khoi cua so 168. */
    @Test
    public void dd7dStepDown() {
        double[] c = new double[1000];
        Arrays.fill(c, 0, 500, 100d);
        Arrays.fill(c, 500, 1000, 50d);
        assertEquals(-0.5d, S1FeatureLive.dd7d(c, 600), 1e-12);
        assertEquals(0d, S1FeatureLive.dd7d(c, 999), 1e-12);
    }

    /** min_periods=84: duoi nguong tra NaN, tu 84 quan sat tro len co gia tri. */
    @Test
    public void rollMaxRespectsMinPeriods() {
        double[] c = linear(1000);
        assertTrue(Double.isNaN(S1FeatureLive.rollMax(c, 82, 168, 84)));
        assertEquals(100d + 83, S1FeatureLive.rollMax(c, 83, 168, 84), 1e-12);
    }

    /** hrs_since_high_7d: dinh o cuoi -> 0; dinh o dau cua so -> 167/168; NaN neu >84 NaN. */
    @Test
    public void hrsSinceHigh() {
        double[] up = linear(400);
        assertEquals(0d, S1FeatureLive.hrsSinceHigh7d(up, 399), 1e-12);
        double[] down = new double[400];
        for (int i = 0; i < 400; i++) down[i] = 500d - i;
        assertEquals(167d / 168d, S1FeatureLive.hrsSinceHigh7d(down, 399), 1e-12);
        double[] holey = linear(400);
        for (int i = 300; i <= 399; i++) holey[i] = Double.NaN;   // 100 NaN > 84
        assertTrue(Double.isNaN(S1FeatureLive.hrsSinceHigh7d(holey, 399)));
        assertTrue(Double.isNaN(S1FeatureLive.hrsSinceHigh7d(up, 166)));
    }

    /** vol_7d = std MAU (ddof=1) cua ret 1h; chuoi nhan doi deu -> std = 0. */
    @Test
    public void vol7dDdof1() {
        double[] geo = new double[400];
        geo[0] = 100d;
        for (int i = 1; i < 400; i++) geo[i] = geo[i - 1] * 1.01d;
        assertEquals(0d, S1FeatureLive.vol7d(geo, 399), 1e-12);
        // chuoi so le: ret luan phien +1% / -1% => mean ~0, std ddof=1 ~ 0.01
        double[] alt = new double[400];
        alt[0] = 100d;
        for (int i = 1; i < 400; i++) alt[i] = alt[i - 1] * (i % 2 == 1 ? 1.01d : (1d / 1.01d));
        double v = S1FeatureLive.vol7d(alt, 399);
        assertTrue("vol_7d ~1% nhung duoc " + v, v > 0.0095d && v < 0.0105d);
        assertTrue(Double.isNaN(S1FeatureLive.vol7d(geo, 80)));  // n=80 < min_periods 84
    }

    /** rank(pct=True): NaN giu NaN, tie chia rank trung binh, mau so = so phan tu CO gia tri. */
    @Test
    public void rankPctAveragesTiesAndSkipsNaN() {
        double[] v = {1d, 3d, 3d, Double.NaN, 5d};
        double[] r = S1FeatureLive.rankPct(v);
        assertEquals(1d / 4d, r[0], 1e-12);
        assertEquals(2.5d / 4d, r[1], 1e-12);
        assertEquals(2.5d / 4d, r[2], 1e-12);
        assertTrue(Double.isNaN(r[3]));
        assertEquals(4d / 4d, r[4], 1e-12);
        assertTrue(Double.isNaN(S1FeatureLive.rankPct(new double[]{Double.NaN})[0]));
    }

    /** computeTick tra dung 9 gia tri, dung thu tu FEATURE_ORDER, rank tinh trong tick. */
    @Test
    public void computeTickShapeAndOrder() {
        Map<String, double[]> closes = new LinkedHashMap<>();
        double[] a = linear(400);
        double[] b = new double[400];
        for (int i = 0; i < 400; i++) b[i] = 500d - i;
        closes.put("AAAUSDT", a);
        closes.put("BBBUSDT", b);
        Map<String, Double> lsg = new LinkedHashMap<>();
        lsg.put("AAAUSDT", 1.5d);
        lsg.put("BBBUSDT", 0.5d);
        Map<String, Double> oid = new LinkedHashMap<>();
        oid.put("AAAUSDT", 10d);
        oid.put("BBBUSDT", 20d);
        Map<String, double[]> f = S1FeatureLive.computeTick(closes, 399, lsg, oid);
        assertEquals(9, S1FeatureLive.FEATURE_ORDER.length);
        assertEquals(9, f.get("AAAUSDT").length);
        // AAA di len => dd_7d = 0 (cao nhat) => rank pct = 1.0; BBB di xuong => 0.5
        assertEquals(1.0d, f.get("AAAUSDT")[S1FeatureLive.IDX_RK_DD_7D], 1e-12);
        assertEquals(0.5d, f.get("BBBUSDT")[S1FeatureLive.IDX_RK_DD_7D], 1e-12);
        assertEquals(1.5d, f.get("AAAUSDT")[S1FeatureLive.IDX_LS_GLOBAL], 1e-12);
        assertEquals(1.0d, f.get("BBBUSDT")[S1FeatureLive.IDX_RK_OI_DELTA24H], 1e-12);
        assertEquals(0d, f.get("AAAUSDT")[S1FeatureLive.IDX_HRS_SINCE_HIGH_7D], 1e-12);
    }
}
