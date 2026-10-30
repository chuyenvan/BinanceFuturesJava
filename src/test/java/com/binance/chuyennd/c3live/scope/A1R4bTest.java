package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;

import static org.junit.Assert.*;

/** A1 R4b: test doi khang (scratch, KHONG commit). */
public class A1R4bTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final String S = C3LiveFixtures.sym(0);

    private static MainAccountRig armed(File root) {
        MainAccountRig r = new MainAccountRig(root);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(S, 1.0f, false).outcome);
        r.tick(S, "1.10");
        r.tick(S, "1.12");
        assertTrue(r.book.cluster(S).get().trailArmed());
        return r;
    }

    /** Mat stream, LEGACY ban DUNG qty c3 => san = 0 khong co bang chung c3: KHONG duoc ghi nhu c3 da dong (phai giu/LOST_FOREIGN + chan symbol). */
    @Test
    public void a1r4b_legacySellsExactC3QtyDuringGapIsNotBookedAsC3Close() throws Exception {
        MainAccountRig r = armed(tmp.getRoot());
        BigDecimal c3Qty = r.scope.c3OpenQty(S);
        int sells0 = 0;
        for (String l : r.mock.callLog()) if (l.startsWith("newMarketOrder:") && l.contains(":c3x-")) sells0++;
        r.mock.wsSink = null;
        r.legacyTrade(S, Side.SELL, c3Qty);
        for (int i = 0; i < 10; i++) r.tick(MainAccountRig.legacySym(2), "1");
        r.rec.checkPositions();
        r.rec.hourly(); for (int k = 0; k < 150; k++) r.tick(MainAccountRig.legacySym(2), "1"); r.rec.checkPositions(); r.rec.hourly();
        int sells = -sells0;
        for (String l : r.mock.callLog()) if (l.startsWith("newMarketOrder:") && l.contains(":c3x-")) sells++;
        boolean blocked = r.scope.entryBlocked(S, r.now.get());
        String al = r.alerts.toString();
        System.out.println("A1R4b-D holding=" + r.book.isHolding(S) + " merged=" + r.scope.isMerged(S) + " entryBlocked=" + blocked
                + " san=" + r.mock.position(S) + " blocks=" + r.rec.blocks() + " allowsOther=" + r.rec.allowsEntry(C3LiveFixtures.sym(5)) + " c3Sells=" + sells + " alertsTail="
                + al.substring(Math.max(0, al.length() - 600)));
        assertEquals("c3 khong gui lenh nao", 0, sells);
        assertTrue("san=0 khong bang chung c3: giu cum (MERGED/LOST) hoac chan symbol + KHAN — khong duoc coi la c3 da dong",
                r.book.isHolding(S) || (blocked && al.contains("LOST")));
    }
}
