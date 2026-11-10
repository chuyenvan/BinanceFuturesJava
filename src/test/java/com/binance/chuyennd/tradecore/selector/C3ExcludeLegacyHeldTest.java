package com.binance.chuyennd.tradecore.selector;

import org.junit.After;
import org.junit.Test;

import java.io.File;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.function.Predicate;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/** [V12 R4u2] C3_EXCLUDE_LEGACY_HELD: ca hai gia tri. */
public class C3ExcludeLegacyHeldTest {

    @After
    public void reset() {
        LegacySymbols.excludeForTest = null;
    }

    private static Set<String> set(String... s) {
        return new HashSet<>(Arrays.asList(s));
    }

    @Test
    public void parseDefaultTrueOnlyFalseOr0Disables() {
        assertTrue(LegacySymbols.parseExclude(null));
        assertTrue(LegacySymbols.parseExclude(""));
        assertTrue(LegacySymbols.parseExclude("true"));
        assertTrue(LegacySymbols.parseExclude("1"));
        assertTrue(LegacySymbols.parseExclude("yes"));
        assertFalse(LegacySymbols.parseExclude("false"));
        assertFalse(LegacySymbols.parseExclude(" FALSE "));
        assertFalse(LegacySymbols.parseExclude("0"));
    }

    @Test
    public void blocksC3BothValues() {
        assertTrue(LegacySymbols.blocksC3(true, true));
        assertFalse(LegacySymbols.blocksC3(true, false));
        assertFalse(LegacySymbols.blocksC3(false, true));
        assertFalse(LegacySymbols.blocksC3(false, false));
    }

    @Test
    public void reconcileTrueSubtractsC3_FalseKeepsAllRealAsLegacy() throws Exception {
        File f = File.createTempFile("legacy_r4u2", ".csv");
        f.delete();
        f.deleteOnExit();
        Set<String> real = set("AUSDT", "BUSDT", "CUSDT");
        LegacySymbols.excludeForTest = true;
        LegacySymbols.resetForTest(f.getAbsolutePath());
        LegacySymbols.getInstance().reconcile(real, set("BUSDT"), set("CUSDT"));
        assertEquals(new TreeSet<>(set("AUSDT")), LegacySymbols.getInstance().all());
        LegacySymbols.excludeForTest = false;
        LegacySymbols.resetForTest(f.getAbsolutePath() + ".b");
        new File(f.getAbsolutePath() + ".b").deleteOnExit();
        LegacySymbols.getInstance().reconcile(real, set("BUSDT"), set("CUSDT"));
        assertEquals(new TreeSet<>(real), LegacySymbols.getInstance().all());
    }

    @Test
    public void bigDownLockedBothValues() {
        Set<String> real = set("LEGUSDT");              // vi the that tk chinh (LEGACY)
        Predicate<String> c3Held = s -> s.equals("C3HUSDT");
        Predicate<String> lkTrue = BigDownSelect.lockedFor(true, real, c3Held);
        Predicate<String> lkFalse = BigDownSelect.lockedFor(false, real, c3Held);
        assertTrue(lkTrue.test("LEGUSDT"));
        assertTrue(lkTrue.test("C3HUSDT"));
        assertFalse(lkFalse.test("LEGUSDT"));
        assertTrue(lkFalse.test("C3HUSDT"));
        Map<String, Float> mp = new HashMap<>();
        mp.put("LEGUSDT", 0.05f);
        mp.put("C3HUSDT", 0.06f);
        mp.put("AUSDT", 0.10f);
        mp.put("BUSDT", 0.20f);
        mp.put("CUSDT", 0.30f);
        assertEquals(Arrays.asList("AUSDT", "BUSDT"), BigDownSelect.select(mp, 2, lkTrue, s -> true));
        assertEquals(Arrays.asList("LEGUSDT", "AUSDT"), BigDownSelect.select(mp, 2, lkFalse, s -> true));
    }

    @Test
    public void excludeForTestOverrides() {
        LegacySymbols.excludeForTest = false;
        assertFalse(LegacySymbols.excludeLegacyHeld());
        LegacySymbols.excludeForTest = true;
        assertTrue(LegacySymbols.excludeLegacyHeld());
    }
}
