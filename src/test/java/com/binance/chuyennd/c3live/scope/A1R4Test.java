package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.recon.Reconciler;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.util.List;
import java.util.Locale;
import java.util.Map;

import static org.junit.Assert.*;

/** A1 R4: test doi khang (scratch, KHONG commit). */
public class A1R4Test {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final String S = C3LiveFixtures.sym(0);

    private static MainAccountRig armed(File root) {
        MainAccountRig r = new MainAccountRig(root);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(S, 1.0f, false).outcome);
        r.tick(S, "1.10");
        r.tick(S, "1.12");
        assertTrue(r.book.cluster(S).get().trailArmed());
        assertNotNull(r.book.cluster(S).get().stopClientAlgoId);
        return r;
    }

    private static int c3Sells(MainAccountRig r) {
        int n = 0;
        for (String l : r.mock.callLog()) if (l.startsWith("newMarketOrder:") && l.contains(":c3x-")) n++;
        return n;
    }

    /** LEGACY ban vao long c3 khi mat stream, roi JVM restart: spec R2 "san != ledger c3" => MERGED, khong ghi de so. */
    @Test
    public void a1r4_legacySellDuringGapThenRestartIsNotAbsorbedIntoC3Book() throws Exception {
        MainAccountRig r = armed(tmp.getRoot());
        BigDecimal c3Qty = r.scope.c3OpenQty(S);
        BigDecimal half = c3Qty.divide(new BigDecimal("2"));
        r.mock.wsSink = null;
        r.legacyTrade(S, Side.SELL, half);
        r.now.addAndGet(60_000L);
        r.boot();
        System.out.println("A1R4-A merged=" + r.scope.isMerged(S) + " c3Open=" + r.scope.c3OpenQty(S) + " (truoc " + c3Qty + ") san="
                + r.mock.position(S) + " blocks=" + r.rec.blocks());
        assertTrue("LEGACY ban cong don vao c3 khi restart: phai MERGED hoac giu so c3, khong 'san thang'",
                r.scope.isMerged(S) || c3Qty.compareTo(r.scope.c3OpenQty(S)) == 0);
    }

    /** Dang chay, mat stream: LEGACY ban vao long c3 => trong <= 1 chu ky LEGACY (60 s + 3 s) phai MERGED; khong chan (A). */
    @Test
    public void a1r4_legacySellDuringGapDetectedWithinRefreshNoGlobalBlock() throws Exception {
        MainAccountRig r = armed(tmp.getRoot());
        BigDecimal c3Qty = r.scope.c3OpenQty(S);
        r.mock.wsSink = null;
        r.legacyTrade(S, Side.SELL, c3Qty.divide(new BigDecimal("2")));
        for (int i = 0; i < 8; i++) r.tick(MainAccountRig.legacySym(2), "1");
        r.rec.hourly();
        System.out.println("A1R4-B merged=" + r.scope.isMerged(S) + " c3Open=" + r.scope.c3OpenQty(S) + " san=" + r.mock.position(S)
                + " blocks=" + r.rec.blocks());
        assertTrue("san < ledger c3 khong co bang chung c3 => MERGED trong chu ky LEGACY", r.scope.isMerged(S));
        Map<String, String> b = r.rec.blocks();
        assertFalse("LEGACY khong duoc gay chan (A): " + b, b.containsKey(Reconciler.BLOCK_EQUITY) || b.containsKey(Reconciler.BLOCK_UNKNOWN));
    }

    /** c3 vua chot S (< 15'), mat stream, LEGACY mo S: khong duoc thanh chan (A) toan he (R3). */
    @Test
    public void a1r4_legacyOpensOnJustClosedSymbolDuringGapNoGlobalBlock() throws Exception {
        MainAccountRig r = armed(tmp.getRoot());
        double sp = r.mock.openStops(S).get(0).getStopPrice().doubleValue();
        r.tick(S, String.format(Locale.ROOT, "%.4f", sp * 0.999));
        assertFalse("cum c3 da dong", r.book.isHolding(S));
        r.mock.wsSink = null;
        r.legacyTrade(S, Side.BUY, new BigDecimal("50"));
        for (int i = 0; i < 8; i++) r.tick(MainAccountRig.legacySym(2), "1");
        r.rec.hourly();
        r.rec.checkPositions();
        boolean allows = r.rec.allowsEntry(C3LiveFixtures.sym(5));
        System.out.println("A1R4-C related=" + r.scope.related(S) + " blocks=" + r.rec.blocks() + " allowsOther=" + allows
                + " c3SellsSince=" + c3Sells(r));
        Map<String, String> b = r.rec.blocks();
        assertFalse("LEGACY tren symbol c3 vua chot khong duoc gay chan (A): " + b, b.containsKey(Reconciler.BLOCK_UNKNOWN));
        assertTrue(allows);
        assertEquals("LEGACY 50 nguyen ven", 0, new BigDecimal("50").compareTo(r.mock.position(S)));
    }
}
