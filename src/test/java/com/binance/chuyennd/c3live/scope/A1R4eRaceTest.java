package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;
import java.io.File;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;
import static org.junit.Assert.*;

/**
 * A1 4e/4f MAJOR-L1: anh chup ClusterView (Reconciler.checkPositions chup TRUOC doc san) + stream giao khop truoc/sau
 * recoverC3Exit. Stop ACTIVE (khong retire). Realized/phi tong ke tu moc phai ghi DUNG 1 lan o ca 2 thu tu, va
 * KHONG doi sau restart (nap lai so) + su kien stream lap lai.
 */
public class A1R4eRaceTest {
    @Rule public TemporaryFolder tmp = new TemporaryFolder();
    static final String S = C3LiveFixtures.sym(0);

    private double[] run(File root, boolean streamFirst) throws Exception {
        MainAccountRig r = new MainAccountRig(root);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(S, 1.0f, false).outcome);
        r.tick(S, "1.10");
        r.tick(S, "1.12");
        LiveBookC3.ClusterView c0 = r.book.cluster(S).get();
        assertTrue(c0.trailArmed());
        double r0 = r.book.account().realized;
        Consumer<String> sink = r.mock.wsSink;
        List<String> buf = new ArrayList<>();
        r.mock.wsSink = buf::add;
        r.sync();
        r.mock.triggerStops(S, new BigDecimal("1.08"));
        r.mock.wsSink = sink;
        assertFalse(buf.isEmpty());
        String reason;
        if (streamFirst) {
            for (String e : buf) sink.accept(e);
            assertFalse(r.book.isHolding(S));
            reason = r.merged.recoverC3Exit(c0);
        } else {
            reason = r.merged.recoverC3Exit(c0);
            for (String e : buf) sink.accept(e);
        }
        double r1 = r.book.account().realized;
        double f1 = r.book.account().commission;
        for (String e : buf) sink.accept(e);   // stream lap lai
        double r2 = r.book.account().realized;
        LiveBookC3 b2 = new LiveBookC3(new File(root, "run/c3live_book.json"), 1.0);
        double r3 = b2.account().realized;
        System.out.println("A1R4F_RACE streamFirst=" + streamFirst + " r0=" + r0 + " r1=" + r1 + " r2(replay)=" + r2
                + " fee=" + f1 + " reload=" + r3 + " reason=" + reason + " holding=" + r.book.isHolding(S));
        assertEquals("lap stream khong doi realized", r1, r2, 1e-9);
        assertEquals("restart: realized nap lai giu nguyen", r2, r3, 1e-9);
        return new double[]{r1 - r0, f1};
    }

    @Test
    public void bothOrdersBookOnce() throws Exception {
        double[] a = run(tmp.newFolder("a"), true);
        double[] b = run(tmp.newFolder("b"), false);
        assertEquals("realized 2 thu tu bang nhau (khong 2 lan)", a[0], b[0], 1e-9);
        assertEquals("phi 2 thu tu bang nhau", a[1], b[1], 1e-9);
        assertTrue("realized > 0 va khong gap doi (1.84 chu khong 3.68)", a[0] > 0 && a[0] < 2.5);
    }
}
