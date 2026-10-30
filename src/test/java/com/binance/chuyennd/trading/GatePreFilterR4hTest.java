package com.binance.chuyennd.trading;

import org.junit.Test;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;
import java.util.function.Predicate;

import static org.junit.Assert.*;

/** [V12 R4h] loc truoc gate theo quy uoc sim. */
public class GatePreFilterR4hTest {

    @Test
    public void decideOrder() {
        assertEquals(GatePreFilter.Action.DROP_UNIVERSE, GatePreFilter.decide(true, true, true, true));
        assertEquals("dang giu: dem hang, KHONG gate (khong nap r)", GatePreFilter.Action.SKIP_AFTER_RANK,
                GatePreFilter.decide(false, true, false, true));
        assertEquals(GatePreFilter.Action.SKIP_AFTER_RANK, GatePreFilter.decide(false, false, true, false));
        assertEquals("LEGACY: qua gate nap r, khong vao", GatePreFilter.Action.GATE_NO_ENTRY,
                GatePreFilter.decide(false, false, false, true));
        assertEquals(GatePreFilter.Action.GATE, GatePreFilter.decide(false, false, false, false));
    }

    @Test
    public void heldSourceByAdapter() {
        assertEquals(GatePreFilter.HeldSource.HEAD_REAL_POSITIONS, GatePreFilter.source(false, false, false));
        assertEquals(GatePreFilter.HeldSource.HEAD_REAL_POSITIONS, GatePreFilter.source(false, true, true));
        assertEquals("c3_live + live => so c3 that", GatePreFilter.HeldSource.C3_LIVE_BOOK, GatePreFilter.source(true, true, true));
        assertEquals("c3_live + dry => so giay twin", GatePreFilter.HeldSource.PAPER_TWIN, GatePreFilter.source(true, true, false));
        assertEquals("c3_shadow => so giay", GatePreFilter.HeldSource.PAPER_TWIN, GatePreFilter.source(true, false, false));
    }

    @Test
    public void headUsesRealPositions() {
        Set<String> pos = new HashSet<>(Collections.singletonList("AUSDT"));
        Predicate<String> h = GatePreFilter.heldPredicate(GatePreFilter.HeldSource.HEAD_REAL_POSITIONS, pos);
        assertTrue(h.test("AUSDT"));
        assertFalse(h.test("BUSDT"));
        pos.add("BUSDT");   // view song (keySet ConcurrentHashMap) — nhu dong cu symbol2Pos.containsKey
        assertTrue(h.test("BUSDT"));
        assertFalse(GatePreFilter.heldPredicate(GatePreFilter.HeldSource.HEAD_REAL_POSITIONS, null).test("AUSDT"));
    }
}
