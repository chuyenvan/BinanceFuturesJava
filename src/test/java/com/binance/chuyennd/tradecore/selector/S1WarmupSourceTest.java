package com.binance.chuyennd.tradecore.selector;

import org.junit.Test;

import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.Assert.assertEquals;

/** [L5] Cong cho nguon warm-up S1 (nguyen nhan "0 coin" tren 242). */
public class S1WarmupSourceTest {

    @Test
    public void thieuKeyConfigThiVeNamespaceThatCuaCum242() {
        // config.properties cua bot 242 KHONG co AEROSPIKE_NAMESPACE_242 -> Configs tra null.
        assertEquals("ticker", S1RankerLive.resolveNs242(null));
        assertEquals("ticker", S1RankerLive.resolveNs242(""));
        assertEquals("ticker", S1RankerLive.resolveNs242("   "));
        assertEquals(S1RankerLive.NS_242_DEFAULT, S1RankerLive.resolveNs242(null));
    }

    @Test
    public void coKeyThiTonTrongConfig() {
        assertEquals("ticker", S1RankerLive.resolveNs242("ticker"));
        assertEquals("ticker", S1RankerLive.resolveNs242("  ticker  "));
        assertEquals("test", S1RankerLive.resolveNs242("test"));
    }

    private static double[] arr(int n, int nonNan) {
        double[] a = new double[n];
        for (int i = 0; i < n; i++) a[i] = i < nonNan ? 1.0 + i : Double.NaN;
        return a;
    }

    @Test
    public void demCoinDuLichSu() {
        Map<String, double[]> m = new LinkedHashMap<>();
        m.put("A", arr(384, 384));
        m.put("B", arr(384, 336));
        m.put("C", arr(384, 335));
        m.put("D", arr(384, 0));
        m.put("E", null);
        assertEquals(2, S1RankerLive.countReady(m, 336));
        assertEquals(3, S1RankerLive.countReady(m, 335));
        assertEquals(0, S1RankerLive.countReady(m, 385));
        assertEquals(0, S1RankerLive.countReady(null, 1));
    }
}
