package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.recon.Reconciler;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.util.List;

import static org.junit.Assert.*;

/**
 * [V12 R4e MINOR-1] Mat stream; stop c3s- MO COI (khong con la stop active) da kich va dong het vi the => KHONG phai
 * LOST_FOREIGN (khong KHAN gia, khong chan 24 h); realized c3 lay tu userTrades (khong thieu).
 */
public class C3MainAccountR4eTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final String S = C3LiveFixtures.sym(0);

    @Test
    public void triggeredOrphanStopIsC3EvidenceNotLostForeign() throws Exception {
        MainAccountRig r = new MainAccountRig(tmp.getRoot());
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(S, 1.0f, false).outcome);
        r.tick(S, "1.10");
        r.tick(S, "1.12");
        LiveBookC3.ClusterView c0 = r.book.cluster(S).get();
        assertTrue(c0.trailArmed());
        String stopCid = c0.stopClientAlgoId;
        assertNotNull(stopCid);
        BigDecimal qty = c0.confirmedQty;
        r.mock.wsSink = null;                                   // mat stream
        assertEquals(stopCid, r.book.retireActiveStop(S, r.now.get()));   // stop tren san gio la MO COI trong so
        assertNull(r.book.cluster(S).get().stopClientAlgoId);
        r.sync();
        r.mock.triggerStops(S, new BigDecimal("1.08"));        // stop mo coi kich => san = 0, khong su kien stream
        assertEquals(0, r.mock.position(S).signum());
        for (int i = 0; i < 6; i++) {
            r.now.addAndGet(35_000L);
            r.sync();
            r.rec.checkPositions();
        }
        assertFalse("cum da dong", r.book.isHolding(S));
        List<String> l = Files.readAllLines(new File(tmp.getRoot(), "run/" + LiveBookC3.LEDGER_NAME).toPath());
        String[] last = null;
        for (String x : l) if (x.startsWith(S + ",")) last = x.split(",", -1);
        assertNotNull(last);
        assertNotEquals(Reconciler.REASON_LOST_FOREIGN, last[9]);
        assertEquals("TRAILING_STOP", last[9]);
        assertEquals("exit qty tu userTrades", 0, new BigDecimal(last[5]).compareTo(qty));
        assertTrue("realized c3 > 0 (khop that ~1.09 > avg 1.0), khong bi thieu: " + last[7], Double.parseDouble(last[7]) > 1.0);
        assertFalse(r.scope.isLostBlocked(S, r.now.get()));
        assertFalse(r.alerts.toString(), r.alerts.stream().anyMatch(a -> a.contains("LOST_FOREIGN")));
        assertFalse(r.journal.stream().anyMatch(j -> j.contains("LOST_FOREIGN")));
    }
}
