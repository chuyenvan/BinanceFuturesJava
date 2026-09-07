package com.binance.chuyennd.tradecore.selector;

import org.junit.Test;

import java.util.TreeMap;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

/** [L5] Cong: khong bao gio fallback pNoPump khi co C3 bat ma S1 chua co score. */
public class EntryPoolGateTest {

    private static TreeMap<Float, String> pool(String... syms) {
        TreeMap<Float, String> m = new TreeMap<>();
        for (int i = 0; i < syms.length; i++) m.put(0.1f * (i + 1), syms[i]);
        return m;
    }

    @Test
    public void profileOffGiuNguyenPoolPnoPump() {
        TreeMap<Float, String> pnp = pool("AAA", "BBB");
        assertSame(pnp, EntryPoolGate.choose(false, pnp, null));
        assertSame(pnp, EntryPoolGate.choose(false, pnp, pool("CCC")));
    }

    @Test
    public void profileOnCoScoreThiDungPoolS1() {
        TreeMap<Float, String> pnp = pool("AAA", "BBB");
        TreeMap<Float, String> s1 = pool("CCC");
        assertSame(s1, EntryPoolGate.choose(true, pnp, s1));
    }

    @Test
    public void profileOnChuaCoScoreThiPoolRONG_khongFallbackPnoPump() {
        TreeMap<Float, String> pnp = pool("AAA", "BBB");
        assertTrue(EntryPoolGate.choose(true, pnp, null).isEmpty());
        assertTrue(EntryPoolGate.choose(true, pnp, new TreeMap<Float, String>()).isEmpty());
        // va KHONG duoc la chinh pool pNoPump
        assertEquals(0, EntryPoolGate.choose(true, pnp, null).size());
    }

    @Test
    public void usable() {
        assertFalse(EntryPoolGate.usable(null));
        assertFalse(EntryPoolGate.usable(new TreeMap<Float, String>()));
        assertTrue(EntryPoolGate.usable(pool("AAA")));
    }
}
