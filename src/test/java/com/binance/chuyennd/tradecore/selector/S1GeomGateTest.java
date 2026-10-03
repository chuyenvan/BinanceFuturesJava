package com.binance.chuyennd.tradecore.selector;

import org.junit.Test;

import java.lang.reflect.Field;
import java.util.*;

import static org.junit.Assert.*;

/**
 * [GEOM-LIVE] Cong {@code LIVE_S1_GEOM_ENABLED} cua {@link S1RankerLive}: OFF => provider KHONG duoc tao, ma tran
 * input y het vong lap cu (bit-for-bit); ON => 18 cot KEEP9 roi GEOM9, symbol thieu GEOM -> NaN.
 */
public class S1GeomGateTest {

    @Test
    public void keyParsing() {
        assertFalse(S1RankerLive.geomEnabled(null));
        assertFalse(S1RankerLive.geomEnabled(""));
        assertFalse(S1RankerLive.geomEnabled("false"));
        assertFalse(S1RankerLive.geomEnabled("1"));
        assertFalse(S1RankerLive.geomEnabled("yes"));
        assertTrue(S1RankerLive.geomEnabled("true"));
        assertTrue(S1RankerLive.geomEnabled(" TRUE "));
    }

    private static Map<String, double[]> keep9(Random r, String... syms) {
        Map<String, double[]> m = new LinkedHashMap<>();
        for (String s : syms) {
            double[] v = new double[S1FeatureLive.FEATURE_ORDER.length];
            for (int j = 0; j < v.length; j++) v[j] = (j == 3 && s.startsWith("N")) ? Double.NaN : r.nextGaussian();
            m.put(s, v);
        }
        return m;
    }

    /** OFF: assemble(.., null) == DUNG vong lap cu cua scoreAll (ban sao nguyen van truoc patch). */
    @Test
    public void offMatrixIdenticalToLegacyLoop() {
        Map<String, double[]> feat = keep9(new Random(42), "AUSDT", "NUSDT", "BUSDT");
        String[] syms = feat.keySet().toArray(new String[0]);
        float[][] legacy = new float[syms.length][S1FeatureLive.FEATURE_ORDER.length];
        for (int i = 0; i < syms.length; i++) {
            double[] v = feat.get(syms[i]);
            for (int j = 0; j < v.length; j++) legacy[i][j] = (float) v[j];
        }
        float[][] x = S1RankerLive.assemble(syms, feat, null);
        assertEquals(legacy.length, x.length);
        for (int i = 0; i < x.length; i++) {
            assertEquals(9, x[i].length);
            for (int j = 0; j < 9; j++) {
                assertEquals(Float.floatToRawIntBits(legacy[i][j]), Float.floatToRawIntBits(x[i][j]));
            }
        }
    }

    /** ON: 18 cot, 9 dau = OFF, 9 sau = GEOM theo FEATURE_ORDER, symbol thieu GEOM -> NaN. */
    @Test
    public void onMatrixKeep9ThenGeom9() {
        Map<String, double[]> feat = keep9(new Random(7), "AUSDT", "BUSDT");
        Map<String, double[]> geom = new HashMap<>();
        double[] g = new double[9];
        for (int j = 0; j < 9; j++) g[j] = 0.1 * (j + 1);
        geom.put("AUSDT", g);
        String[] syms = {"AUSDT", "BUSDT"};
        float[][] off = S1RankerLive.assemble(syms, feat, null);
        float[][] on = S1RankerLive.assemble(syms, feat, geom);
        for (int i = 0; i < 2; i++) {
            assertEquals(18, on[i].length);
            for (int j = 0; j < 9; j++) assertEquals(off[i][j], on[i][j], 0f);
        }
        for (int j = 0; j < 9; j++) {
            assertEquals((float) g[j], on[0][9 + j], 0f);
            assertTrue(Float.isNaN(on[1][9 + j]));
        }
    }

    /**
     * OFF (env test KHONG dat LIVE_S1_GEOM_ENABLED): instance THAT cua S1RankerLive khong tao provider GEOM
     * (=> khong co doc Aerospike them nao) va co geomOn = false.
     */
    @Test
    public void offInstanceHasNoProvider() throws Exception {
        assumeOff();
        S1RankerLive r = S1RankerLive.getInstance();
        Field fg = S1RankerLive.class.getDeclaredField("geom");
        Field fo = S1RankerLive.class.getDeclaredField("geomOn");
        fg.setAccessible(true);
        fo.setAccessible(true);
        assertNull(fg.get(r));
        assertFalse((Boolean) fo.get(r));
    }

    private static void assumeOff() {
        org.junit.Assume.assumeFalse(S1RankerLive.geomEnabled(System.getenv("LIVE_S1_GEOM_ENABLED")));
        org.junit.Assume.assumeTrue(System.getenv("TRADING_PROFILE") == null);
    }
}
