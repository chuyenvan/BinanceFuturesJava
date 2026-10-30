package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.nio.file.Files;

import static org.junit.Assert.*;

/** [V12 R4j A1 MIN-1] doc bang chung (queryStop/queryOrder) loi => thu lai co gioi han TRUOC khi ket luan LOST_FOREIGN. */
public class MergedEvidenceRetryR4jTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();
    static final String S = C3LiveFixtures.sym(0);

    private static MainAccountRig stopFiredStreamLost(File root) {
        MainAccountRig r = new MainAccountRig(root);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(S, 1.0f, false).outcome);
        r.tick(S, "1.10");
        r.tick(S, "1.12");
        assertTrue(r.book.cluster(S).get().trailArmed());
        r.mock.wsSink = null;
        r.book.retireActiveStop(S, r.now.get());
        r.mock.triggerStops(S, new BigDecimal("1.08"));
        assertEquals(0, r.mock.position(S).signum());
        return r;
    }

    private static void step(MainAccountRig r) {
        r.now.addAndGet(35_000L);
        r.sync();
        r.rec.checkPositions();
    }

    private static String reason(File root) throws Exception {
        String last = null;
        for (String x : Files.readAllLines(new File(root, "run/" + LiveBookC3.LEDGER_NAME).toPath())) {
            if (x.startsWith(S + ",")) last = x;
        }
        assertNotNull(last);
        return last.split(",", -1)[9];
    }

    @Test
    public void transientEvidenceReadError_retriedThenTrailing() throws Exception {
        MainAccountRig r = stopFiredStreamLost(tmp.getRoot());
        r.mock.failQueryStop = true;
        int guard = 0;
        while (r.merged.tradesRetryAttempts(S) < 2 && guard++ < 10) {
            step(r);
            assertTrue("dang thu lai => GIU cum", r.book.isHolding(S));
        }
        assertEquals(2, r.merged.tradesRetryAttempts(S));
        r.mock.failQueryStop = false;
        step(r);
        assertFalse(r.book.isHolding(S));
        assertEquals("TRAILING_STOP", reason(tmp.getRoot()));
        assertFalse(r.alerts.toString(), r.alerts.stream().anyMatch(m -> m.contains("LOST_FOREIGN")));
    }

    @Test
    public void persistentEvidenceReadError_lostForeignAfterFiveTries() throws Exception {
        MainAccountRig r = stopFiredStreamLost(tmp.getRoot());
        r.mock.failQueryStop = true;
        int maxSeen = 0;
        for (int i = 0; i < 14 && r.book.isHolding(S); i++) {
            step(r);
            maxSeen = Math.max(maxSeen, r.merged.tradesRetryAttempts(S));
        }
        assertEquals(4, maxSeen);
        assertFalse(r.book.isHolding(S));
        assertTrue(r.alerts.toString(), r.alerts.stream().anyMatch(m -> m.contains("LOST_FOREIGN")));
    }
}
