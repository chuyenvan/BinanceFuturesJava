package com.binance.chuyennd.c3live.book;

import com.binance.chuyennd.tradecore.selector.LiveDcaGridC3;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.List;

import static org.junit.Assert.*;

/** [V12 C1] LiveBookC3: giu cho margin, xac nhan/huy, persist + khoi phuc, fail-closed, grid state. */
public class LiveBookC3Test {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    private static final long T = 1_792_900_000_000L;

    @Test
    public void reserveConfirmCancelMargin() {
        LiveBookC3 b = new LiveBookC3(null, 1.0);
        assertTrue(b.reserve("AUSDT", "c3-AUSDT-1-0", 0, 1, "BIG_DOWN", 2.0, new BigDecimal("100"), 200.0, T));
        assertTrue(b.isHolding("AUSDT"));
        assertEquals(200.0, b.marginUsed(), 1e-9);
        assertEquals(200.0, b.pendingMargin(), 1e-9);
        // cid trung => tu choi (idempotent)
        assertFalse(b.reserve("AUSDT", "c3-AUSDT-1-0", 0, 1, "BIG_DOWN", 2.0, new BigDecimal("100"), 200.0, T));
        assertTrue(b.markSending("c3-AUSDT-1-0", T + 1));
        assertTrue(b.confirm("c3-AUSDT-1-0", new BigDecimal("100"), 2.1, 77L, T + 2));
        assertEquals(210.0, b.marginUsed(), 1e-9);
        assertEquals(0.0, b.pendingMargin(), 1e-9);
        assertFalse("confirm lan 2 khong doi gi", b.confirm("c3-AUSDT-1-0", new BigDecimal("1"), 9.0, 1L, T + 3));
        assertEquals(210.0, b.marginUsed(), 1e-9);
        // leg 2 huy => cum van con (leg 1 song)
        assertTrue(b.reserve("AUSDT", "c3-AUSDT-2-1", 1, 2, "DCA_LEVEL1", 1.0, new BigDecimal("50"), 50.0, T));
        assertEquals(260.0, b.marginUsed(), 1e-9);
        assertTrue(b.cancel("c3-AUSDT-2-1", "test", T + 4));
        assertEquals(210.0, b.marginUsed(), 1e-9);
        assertEquals(1, b.legCount("AUSDT"));
        // cum chi co leg huy => xoa cum
        assertTrue(b.reserve("BUSDT", "c3-BUSDT-1-0", 0, 1, "X", 1.0, new BigDecimal("10"), 10.0, T));
        assertTrue(b.cancel("c3-BUSDT-1-0", "x", T));
        assertFalse(b.isHolding("BUSDT"));
        // partial fill => margin theo qty khop
        assertTrue(b.reserve("CUSDT", "c3-CUSDT-1-0", 0, 1, "X", 1.0, new BigDecimal("100"), 100.0, T));
        assertTrue(b.confirm("c3-CUSDT-1-0", new BigDecimal("40"), 1.0, 5L, T));
        assertEquals(250.0, b.marginUsed(), 1e-9);
        // exec 0 => huy
        assertTrue(b.reserve("DUSDT", "c3-DUSDT-1-0", 0, 1, "X", 1.0, new BigDecimal("10"), 10.0, T));
        assertTrue(b.confirm("c3-DUSDT-1-0", BigDecimal.ZERO, 0.0, 5L, T));
        assertFalse(b.isHolding("DUSDT"));
    }

    @Test
    public void persistAndRestoreAllFields() throws Exception {
        File f = new File(tmp.getRoot(), "run/c3live_book.json");
        LiveBookC3 b = new LiveBookC3(f, 1.0);
        b.reserve("AUSDT", "c3-AUSDT-10-0", 0, 10, "BIG_DOWN", 2.0, new BigDecimal("100.5"), 201.0, T);
        b.markSending("c3-AUSDT-10-0", T + 5);
        b.confirm("c3-AUSDT-10-0", new BigDecimal("100.5"), 2.02, 99L, T + 6);
        b.reserve("AUSDT", "c3-AUSDT-20-1", 1, 20, "DCA_LEVEL1", 1.5, new BigDecimal("10"), 15.0, T + 7);
        b.markSending("c3-AUSDT-20-1", T + 8);
        b.markUnknown("c3-AUSDT-20-1", "send:TIMEOUT_UNKNOWN_STATE", T + 9);
        b.setStop("AUSDT", 1.9, "c3s-AUSDT-1", T + 10);
        b.updatePeak("AUSDT", 2.5, T + 11);
        b.reserve("BUSDT", "c3-BUSDT-10-0", 0, 10, "X", 3.0, new BigDecimal("1"), 3.0, T);
        b.markClosing("BUSDT", "c3x-BUSDT-5-1", "FLATTEN", T + 12);
        assertTrue(f.exists());
        assertFalse(new File(f.getPath() + ".tmp").exists());

        LiveBookC3 r = new LiveBookC3(f, 1.0);
        assertTrue(r.healthy());
        assertEquals(b.marginUsed(), r.marginUsed(), 1e-9);
        assertEquals(b.ownedSymbols(), r.ownedSymbols());
        LiveBookC3.ClusterView a = r.cluster("AUSDT").get();
        assertEquals(T, a.tsFirstLeg);
        assertEquals(2, a.legCount);
        assertEquals(2.5, a.peak, 0);
        assertTrue(a.armed);
        assertEquals(1.9, a.stopPrice, 0);
        assertEquals("c3s-AUSDT-1", a.stopClientAlgoId);
        assertEquals(new BigDecimal("100.5"), a.confirmedQty);
        assertTrue(a.hasUnresolved);
        LiveBookC3.LegView u = r.leg("c3-AUSDT-20-1").get();
        assertEquals(LiveBookC3.LegState.UNKNOWN, u.state);
        assertEquals(1, u.attempts);
        assertEquals(T + 8, u.lastSendMs);
        assertEquals("send:TIMEOUT_UNKNOWN_STATE", u.note);
        LiveBookC3.ClusterView c = r.cluster("BUSDT").get();
        assertEquals("FLATTEN", c.closeReason);
        assertEquals("c3x-BUSDT-5-1", c.closeCid);
        assertEquals(1, c.closeAttempts);
        assertEquals(T + 12, c.closeSentMs);
        // khoa xu ly persist: leg treo van khoa symbol sau restart
        assertTrue(r.hasUnresolved("AUSDT"));
        assertEquals(2, r.unresolvedLegs().size());   // AUSDT leg DCA UNKNOWN + BUSDT leg PENDING
    }

    @Test
    public void corruptFileFailsClosed() throws Exception {
        File f = new File(tmp.getRoot(), "book.json");
        Files.write(f.toPath(), "{not json".getBytes(StandardCharsets.UTF_8));
        LiveBookC3 b = new LiveBookC3(f, 1.0);
        assertFalse(b.healthy());
        assertFalse(b.reserve("AUSDT", "c3-AUSDT-1-0", 0, 1, "X", 1.0, BigDecimal.ONE, 1.0, T));
        File[] bak = tmp.getRoot().listFiles((d, n) -> n.startsWith("book.json.corrupt_"));
        assertNotNull(bak);
        assertEquals(1, bak.length);
    }

    @Test
    public void gridStatesOnlySettledClusters() {
        LiveBookC3 b = new LiveBookC3(null, 1.0);
        b.reserve("AUSDT", "a0", 0, 1, "X", 2.0, BigDecimal.TEN, 20.0, T);
        b.markSending("a0", T);
        b.confirm("a0", BigDecimal.TEN, 2.2, 1L, T);
        b.reserve("BUSDT", "b0", 0, 1, "X", 3.0, BigDecimal.TEN, 30.0, T);   // treo
        b.reserve("CUSDT", "c0", 0, 1, "X", 4.0, BigDecimal.TEN, 40.0, T);
        b.markSending("c0", T);
        b.confirm("c0", BigDecimal.TEN, 4.0, 2L, T);
        b.markClosing("CUSDT", null, "TIME_STOP", T);                        // dang dong
        List<LiveDcaGridC3.GridState> g = b.gridStates();
        assertEquals(1, g.size());
        assertEquals("AUSDT", g.get(0).symbol);
        assertEquals(2.2f, g.get(0).firstEntryPrice, 0f);
        assertEquals(1, g.get(0).legCount);
        // cum dang dong khong nhan leg moi
        assertFalse(b.reserve("CUSDT", "c1", 1, 2, "DCA_LEVEL1", 3.0, BigDecimal.ONE, 3.0, T));
    }
}
