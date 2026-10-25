package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.junit.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

import static org.junit.Assert.*;

/**
 * [V12 C1] vi the C3 THAT (LiveBookC3.ownedSymbols) KHONG bao gio bi LegacySymbols coi la LEGACY:
 * LEGACY = real \ (paper U c3liveOwned). [V12 P0-U3] bo loc thanh vien ALT_EW: null = y nguyen.
 */
public class C3LiveLegacyAndAltEwFilterTest {

    private static Set<String> set(String... s) {
        return new HashSet<>(Arrays.asList(s));
    }

    @Test
    public void realC3PositionsAreNotLegacy() {
        Set<String> real = set("AUSDT", "BUSDT", "CUSDT", "DUSDT");
        Set<String> paper = set("AUSDT");
        Set<String> owned = set("BUSDT", "DUSDT");
        assertEquals(new TreeSet<>(set("CUSDT")), LegacySymbols.compute(real, paper, owned));
        // khong co owned => y nhu ham cu
        assertEquals(LegacySymbols.compute(real, paper), LegacySymbols.compute(real, paper, Collections.emptySet()));
        assertEquals(LegacySymbols.compute(real, paper), LegacySymbols.compute(real, paper, null));
        assertEquals(new TreeSet<>(set("BUSDT", "CUSDT", "DUSDT")), LegacySymbols.compute(real, paper, null));
    }

    @Test
    public void altEwMemberFilter() {
        Map<String, KlineObjectSimple> bars = new HashMap<>();
        bars.put("BTCUSDT", new KlineObjectSimple());
        bars.put("TSLAUSDT", new KlineObjectSimple());
        bars.put("DOGEUSDT", new KlineObjectSimple());
        try {
            MarketIndexFilter.set(null);
            assertSame(bars, TsMktExt.filterMembers(bars));
            MarketIndexFilter.set(s -> !"TSLAUSDT".equals(s));
            Map<String, KlineObjectSimple> f = TsMktExt.filterMembers(bars);
            assertEquals(set("BTCUSDT", "DOGEUSDT"), f.keySet());
            assertEquals(3, bars.size());
        } finally {
            MarketIndexFilter.set(null);
        }
    }
}
