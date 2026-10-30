package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.c3live.recon.Reconciler;
import com.binance.chuyennd.ops.KillSwitchEngine;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

import static org.junit.Assert.*;

/**
 * [V12 R4] c3_live production tren TAI KHOAN CHINH: (a) chu ky day du giua 44 LEGACY + bot LEGACY; (b) MERGED; (c) LEGACY-busy
 * (ke ca race); (h) khoi dong voi 44 LEGACY; R6 stop bi san ket thuc => dat lai / dong khan cap.
 */
public class C3MainAccountE2ETest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final String S = C3LiveFixtures.sym(0);

    static void assertNoGlobalBlock(MainAccountRig r) {
        Map<String, String> b = r.rec.blocks();
        assertFalse("khong duoc chan (A) UNKNOWN vi LEGACY: " + b, b.containsKey(Reconciler.BLOCK_UNKNOWN));
        assertFalse("khong duoc chan EQUITY/QTY vi LEGACY: " + b, b.containsKey(Reconciler.BLOCK_EQUITY));
        assertFalse(b.containsKey(Reconciler.BLOCK_STARTUP));
    }

    static void assertLegacyUntouched(MainAccountRig r) {
        for (Map.Entry<String, BigDecimal> e : r.legacyExpected.entrySet()) {
            // san = phan LEGACY (chi doi theo lenh cua chinh LEGACY) + phan c3 dang mo theo so
            BigDecimal legacyPart = r.mock.position(e.getKey()).subtract(r.scope.c3OpenQty(e.getKey()));
            assertEquals("vi the LEGACY " + e.getKey() + " chi doi theo lenh cua chinh LEGACY", 0, e.getValue().compareTo(legacyPart));
        }
        boolean lim = false;
        for (OrderInfo o : r.mock.openOrders(MainAccountRig.legacySym(0))) if ("web_lim_1".equals(o.getClientOrderId())) lim = true;
        assertTrue("lenh LEGACY van mo", lim);
        boolean sl = false;
        for (OrderInfo o : r.mock.openStops(MainAccountRig.legacySym(1))) if ("legacy_sl_1".equals(o.getClientOrderId())) sl = true;
        assertTrue("algo LEGACY van mo", sl);
        assertEquals(0, r.mock.calls("setDualSidePosition"));
        assertEquals(0, r.mock.calls("cancelOrder"));
    }

    // ------------------------------------------------------------------ (h) khoi dong
    @Test
    public void h_startupWith44LegacyCompletesAndAllowsEntries() throws Exception {
        MainAccountRig r = new MainAccountRig(tmp.getRoot());
        assertEquals(44, r.scope.legacyPositionCount());
        assertTrue(r.rec.blocks().toString(), r.rec.blocks().isEmpty());
        assertTrue("view pham vi c3: 0 vi the LEGACY", r.sgw.positions().isEmpty());
        assertTrue(r.sgw.openOrders(null).isEmpty());
        assertTrue(r.sgw.openStops(null).isEmpty());
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(S, 1.0f, false).outcome);
        assertTrue(r.scope.entryBlocked(MainAccountRig.legacySym(5), r.now.get()));
        // restart giua chung: van 44 LEGACY = foreign DA BIET, cum c3 giu nguyen, khong cum ma, mo duoc
        r.now.addAndGet(60_000L);
        r.boot();
        assertTrue(r.rec.blocks().toString(), r.rec.blocks().isEmpty());
        assertTrue(r.book.isHolding(S));
        assertEquals(44, r.scope.legacyPositionCount());
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(C3LiveFixtures.sym(1), 1.0f, false).outcome);
        assertFalse(r.alerts.toString(), r.alerts.toString().contains("vi the LA"));
        assertLegacyUntouched(r);
    }

    // ------------------------------------------------------------------ (a) chu ky day du
    @Test
    public void a_fullCycleAmidLegacyBotNeverTouchesLegacyNorBlocksGlobally() throws Exception {
        MainAccountRig r = new MainAccountRig(tmp.getRoot());
        Set<String> avoid = Collections.singleton(S);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(S, 1.0f, false).outcome);
        r.legacyBot(15, avoid);
        r.tick(S, "0.7");
        assertNoGlobalBlock(r);
        r.mock.setPrice(S, new BigDecimal("0.5"));
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(S, 0.5f, true).outcome);
        assertEquals(2, r.book.cluster(S).get().legCount);
        float avg = r.book.cluster(S).get().avgEntryF;
        r.legacyBot(15, avoid);
        r.tick(S, "0.6");
        assertFalse(r.book.cluster(S).get().trailArmed());
        String prev = null;
        int moves = 0;
        for (int i = 0; i <= 10; i++) {
            r.legacyBot(5, avoid);
            r.tick(S, String.format(Locale.ROOT, "%.4f", avg * (1.08 + 0.04 * i)));
            LiveBookC3.ClusterView cv = r.book.cluster(S).get();
            assertTrue(cv.trailArmed());
            assertEquals("dung 1 stop c3 tren san", 1, r.sgw.openStops(S).size());
            if (prev != null && !prev.equals(cv.stopClientAlgoId)) moves++;
            prev = cv.stopClientAlgoId;
            assertNoGlobalBlock(r);
            if (i == 5) {
                r.now.addAndGet(3_600_000L);
                r.rec.hourly();   // doi chieu qty c3 (khong so tmb gom LEGACY)
                assertNoGlobalBlock(r);
            }
        }
        assertTrue("trailing doi stop nhieu lan", moves >= 3);
        assertTrue("bot LEGACY that su giao dich", r.legacyOps >= 50);
        double stopPx = r.book.cluster(S).get().stopPrice;
        r.tick(S, String.format(Locale.ROOT, "%.4f", stopPx * 0.999));
        assertFalse("cum dong do stop", r.book.isHolding(S));
        assertEquals(0, r.mock.position(S).signum());
        List<String> l = Files.readAllLines(new File(tmp.getRoot(), "run/" + LiveBookC3.LEDGER_NAME).toPath());
        assertTrue(l.get(l.size() - 1), l.get(l.size() - 1).startsWith(S + ","));
        for (int k = 0; k < 3; k++) {
            r.legacyBot(10, avoid);
            r.tick(MainAccountRig.legacySym(3), "1");
        }
        r.now.addAndGet(20 * 60_000L);
        r.tick(MainAccountRig.legacySym(3), "1");
        r.rec.hourly();
        assertNoGlobalBlock(r);
        assertTrue(r.scope.merged().isEmpty());
        assertTrue("c3 chi ghi tren " + S + ": " + r.c3WritesOutside(avoid), r.c3WritesOutside(avoid).isEmpty());
        assertLegacyUntouched(r);
        assertTrue(r.ks.latchCodes().toString(), r.ks.latchCodes().isEmpty());
        assertFalse(r.alerts.toString(), r.alerts.toString().contains("FILL MUA KHONG thuoc so"));
        assertFalse(r.alerts.toString(), r.alerts.toString().contains("vi the LA"));
        assertTrue(r.stream.droppedCount() > 0);
    }

    private static MainAccountRig armed(File root) {
        MainAccountRig r = new MainAccountRig(root);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(S, 1.0f, false).outcome);
        r.tick(S, "1.10");
        r.tick(S, "1.12");
        assertTrue(r.book.cluster(S).get().trailArmed());
        assertNotNull(r.book.cluster(S).get().stopClientAlgoId);
        assertFalse(r.book.cluster(S).get().stopQtyMode);
        return r;
    }

    private static OrderInfo onlyStop(MainAccountRig r) {
        List<OrderInfo> st = r.mock.openStops(S);
        assertEquals(st.toString(), 1, st.size());
        return st.get(0);
    }

    // ------------------------------------------------------------------ (b) MERGED
    @Test
    public void b_legacyFillsOnC3SymbolIsMergedQtyStopNoCloseBlockedThenReleased() throws Exception {
        MainAccountRig r = armed(tmp.getRoot());
        BigDecimal c3Qty = r.scope.c3OpenQty(S);
        double stopPx = onlyStop(r).getStopPrice().doubleValue();
        int sellsBefore = countC3Sells(r);
        r.legacyTrade(S, Side.BUY, new BigDecimal("500"));
        assertTrue("MERGED ngay khi lenh khong-c3 khop", r.scope.isMerged(S));
        OrderInfo st = onlyStop(r);
        assertFalse("khong con stop closePosition", st.isClosePosition());
        assertTrue(st.isReduceOnly());
        assertEquals("stop qty = qty c3", 0, c3Qty.compareTo(st.getOrigQty()));
        assertEquals("gia nhu cu", stopPx, st.getStopPrice().doubleValue(), 1e-9);
        assertEquals("KHONG dong", sellsBefore, countC3Sells(r));
        assertEquals(0, c3Qty.add(new BigDecimal("500")).compareTo(r.mock.position(S)));
        assertTrue(r.alerts.toString(), r.alerts.toString().contains("KHAN") && r.alerts.toString().contains("MERGED"));
        assertTrue(r.journal.toString(), r.journal.toString().contains("MERGED"));
        assertEquals(C3LiveEntry.Outcome.LEGACY, r.buy(S, 0.4f, true).outcome);
        assertTrue(new File(tmp.getRoot(), "run/c3live_merged.txt").exists());
        // trailing doi stop khi MERGED: van qty reduceOnly = qty c3
        r.tick(S, "1.40");
        st = onlyStop(r);
        assertFalse(st.isClosePosition());
        assertEquals(0, c3Qty.compareTo(st.getOrigQty()));
        assertTrue(st.getStopPrice().doubleValue() > stopPx);
        // view: phan c3 (khong phai tong san)
        assertEquals(0, c3Qty.compareTo(r.sgw.positions().get(0).getPositionAmt()));
        r.rec.hourly();
        assertNoGlobalBlock(r);
        // LEGACY rut phan cua no => san = qty c3 (2 lan doc cach >= 3 s) => go MERGED
        r.legacyTrade(S, Side.SELL, new BigDecimal("500"));
        r.merged.poll();
        r.now.addAndGet(3_000L);
        r.merged.poll();
        assertFalse(r.scope.isMerged(S));
        assertTrue(r.alerts.toString(), r.alerts.toString().contains("het MERGED"));
        assertEquals(sellsBefore, countC3Sells(r));
        assertLegacyUntouched(r);
    }

    @Test
    public void b2_restOnlyDetectionThenStopFillClosesOnlyC3QtyLegacyKept() throws Exception {
        MainAccountRig r = armed(tmp.getRoot());
        BigDecimal c3Qty = r.scope.c3OpenQty(S);
        r.mock.wsSink = null;   // mat stream: LEGACY vao S, chi REST thay
        r.legacyTrade(S, Side.BUY, new BigDecimal("300"));
        final MainAccountRig rr = r;
        r.mock.wsSink = txt -> {
            String f = rr.stream.filter(txt);
            if (f != null) rr.acct.dispatch(com.binance.chuyennd.c3live.fill.UserStreamEvents.parse(f));
        };
        r.merged.suspect(S);
        r.merged.poll();
        assertFalse("1 lan doc chua du", r.scope.isMerged(S));
        r.now.addAndGet(3_000L);
        r.merged.poll();
        assertTrue("REST 2 lan cach >= 3 s => MERGED", r.scope.isMerged(S));
        assertFalse(onlyStop(r).isClosePosition());
        // stop qty kich: chi ban qty c3, LEGACY 300 con nguyen; cum c3 dong
        double sp = onlyStop(r).getStopPrice().doubleValue();
        r.tick(S, String.format(Locale.ROOT, "%.4f", sp * 0.999));
        assertFalse(r.book.isHolding(S));
        assertEquals(0, new BigDecimal("300").compareTo(r.mock.position(S)));
        r.merged.poll();
        assertFalse("c3 het vi the => go MERGED", r.scope.isMerged(S));
        assertFalse("phan con lai la LEGACY: an khoi view", r.scope.related(S));
        r.now.addAndGet(15 * 60_000L);
        r.tick(MainAccountRig.legacySym(2), "1");
        r.rec.hourly();
        assertNoGlobalBlock(r);
        assertTrue(r.scope.entryBlocked(S, r.now.get()));
        assertTrue(c3Qty.signum() > 0);
    }

    private static int countC3Sells(MainAccountRig r) {
        int n = 0;
        for (String l : r.mock.callLog()) if (l.startsWith("newMarketOrder:") && l.contains(":c3x-")) n++;
        return n;
    }

    // ------------------------------------------------------------------ (c) LEGACY-busy
    @Test
    public void c_legacyBusySymbolNeverEnteredIncludingRaceAfterCycleRefresh() throws Exception {
        MainAccountRig r = new MainAccountRig(tmp.getRoot());
        int before = r.mock.calls("newMarketOrder");
        // c1: symbol co vi the LEGACY
        assertEquals(C3LiveEntry.Outcome.LEGACY, r.buy(MainAccountRig.legacySym(7), 1.0f, false).outcome);
        assertEquals(before, r.mock.calls("newMarketOrder"));
        // c2: anh chup chu ky sach, LEGACY vao C05 SAU lam moi, TRUOC gui (chi REST thay) => kiem trong supplier TU CHOI
        String s5 = C3LiveFixtures.sym(5);
        assertFalse(r.scope.entryBlocked(s5, r.now.get()));
        r.mock.setPosition(s5, new BigDecimal("40"), BigDecimal.ONE);
        C3LiveEntry.Result res = r.buy(s5, 1.0f, false);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, res.outcome);
        assertEquals("0 lenh c3 toi san", before, r.mock.calls("newMarketOrder"));
        assertFalse(r.book.isHolding(s5));
        assertTrue(r.scope.entryBlocked(s5, r.now.get()));
        assertEquals(0, new BigDecimal("40").compareTo(r.mock.position(s5)));
        // c3: lenh LEGACY dang cho tren C06 sau lam moi => tu choi
        String s6 = C3LiveFixtures.sym(6);
        r.mock.addRestingOrder(s6, "web_lim_9", Side.BUY, new BigDecimal("5"));
        r.buy(s6, 1.0f, false);
        assertEquals(before, r.mock.calls("newMarketOrder"));
        assertFalse(r.book.isHolding(s6));
        // algo LEGACY tren C08 => tu choi
        String s8 = C3LiveFixtures.sym(8);
        r.mock.addRestingStop(s8, "legacy_sl_8", new BigDecimal("5"), new BigDecimal("0.5"));
        r.buy(s8, 1.0f, false);
        assertEquals(before, r.mock.calls("newMarketOrder"));
        // symbol sach van vao duoc
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(C3LiveFixtures.sym(9), 1.0f, false).outcome);
        assertEquals(before + 1, r.mock.calls("newMarketOrder"));
        assertTrue(r.book.isHolding(C3LiveFixtures.sym(9)));
        assertNoGlobalBlock(r);
        assertLegacyUntouched(r);
    }

    /** Mock: LEGACY khop tren CUNG symbol trong khe GIUA kiem truoc ghi va gui (khong the chan) => MERGED ngay. */
    static final class RacyMock extends MockExchangeGateway {
        volatile Runnable beforeNextC3Buy;

        @Override
        public OrderInfo newMarketOrder(String symbol, Side side, BigDecimal qty, String cid, boolean reduceOnly) {
            Runnable h = beforeNextC3Buy;
            if (h != null && cid != null && cid.startsWith("c3-")) {
                beforeNextC3Buy = null;
                h.run();
            }
            return super.newMarketOrder(symbol, side, qty, cid, reduceOnly);
        }
    }

    @Test
    public void c4_legacyFillsInGapBetweenCheckAndSendBecomesMergedNotClosed() throws Exception {
        RacyMock m = new RacyMock();
        MainAccountRig r = new MainAccountRig(tmp.getRoot(), m, 10_000d);
        String s = C3LiveFixtures.sym(11);
        final MainAccountRig rr = r;
        m.beforeNextC3Buy = () -> rr.legacyTrade(s, Side.BUY, new BigDecimal("70"));
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(s, 1.0f, false).outcome);
        assertTrue(r.book.isHolding(s));
        assertTrue(r.scope.isMerged(s));
        BigDecimal c3 = r.scope.c3OpenQty(s);
        assertEquals(0, c3.add(new BigDecimal("70")).compareTo(r.mock.position(s)));
        assertEquals(0, countC3Sells(r));
        assertEquals(C3LiveEntry.Outcome.LEGACY, r.buy(s, 0.4f, true).outcome);
        r.tick(s, "1");
        assertNoGlobalBlock(r);
    }

    // ------------------------------------------------------------------ R6 stop bi san ket thuc
    /** Mock ghi lai lan / Urgent khi gui (kiem R5/R6). */
    static final class LaneMock extends MockExchangeGateway {
        final List<String> lanes = new java.util.concurrent.CopyOnWriteArrayList<>();

        @Override
        public OrderInfo newMarketOrder(String symbol, Side side, BigDecimal qty, String cid, boolean reduceOnly) {
            lanes.add("MKT:" + cid + ":emerg=" + com.binance.chuyennd.c3live.rate.RateGuard.inEmergencyLane());
            return super.newMarketOrder(symbol, side, qty, cid, reduceOnly);
        }

        @Override
        public synchronized OrderInfo newStopMarket(String symbol, Side side, BigDecimal qty, BigDecimal stopPrice, String cid,
                                                    boolean reduceOnly) {
            lanes.add("STOP:" + cid + ":urgent=" + com.binance.chuyennd.c3live.rate.RateGuard.inUrgent());
            return super.newStopMarket(symbol, side, qty, stopPrice, cid, reduceOnly);
        }
    }

    @Test
    public void r6_stopExpiredByExchangeIsReplacedInUrgentAtOnce() throws Exception {
        LaneMock m = new LaneMock();
        MainAccountRig r = new MainAccountRig(tmp.getRoot(), m, 10_000d);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(S, 1.0f, false).outcome);
        r.tick(S, "1.10");
        String cid = r.book.cluster(S).get().stopClientAlgoId;
        assertNotNull(cid);
        assertTrue(m.lanes.toString(), m.lanes.get(m.lanes.size() - 1).endsWith("urgent=true"));
        long t0 = r.now.get();
        r.mock.exchangeEndStop(cid, "EXPIRED");
        assertNull("so bo stop chet", r.book.cluster(S).get().stopClientAlgoId);
        r.protector.check();
        String c2 = r.book.cluster(S).get().stopClientAlgoId;
        assertNotNull("dat lai ngay", c2);
        assertNotEquals(cid, c2);
        assertTrue(r.now.get() - t0 <= 61_000L);
        assertTrue(m.lanes.get(m.lanes.size() - 1), m.lanes.get(m.lanes.size() - 1).startsWith("STOP:" + c2) && m.lanes.get(m.lanes.size() - 1).endsWith("urgent=true"));
        assertTrue(r.book.isHolding(S));
    }

    @Test
    public void r6_stopNotReplaceableWithin61sFlattensC3QtyViaEmergencyLane() throws Exception {
        LaneMock m = new LaneMock();
        MainAccountRig r = new MainAccountRig(tmp.getRoot(), m, 10_000d);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(S, 1.0f, false).outcome);
        BigDecimal c3 = r.scope.c3OpenQty(S);
        r.tick(S, "1.10");
        String cid = r.book.cluster(S).get().stopClientAlgoId;
        r.mock.rejectAllStops = true;
        r.mock.exchangeEndStop(cid, "EXPIRED");
        r.protector.check();
        assertNull(r.book.cluster(S).get().stopClientAlgoId);
        r.now.addAndGet(30_000L);
        r.sync();
        r.protector.check();
        assertEquals(0, countC3Sells(r));
        r.now.addAndGet(32_000L);
        r.sync();
        r.protector.check();
        assertEquals("dong qty c3 sau 61 s", 1, countC3Sells(r));
        String last = null;
        for (String x : m.lanes) if (x.startsWith("MKT:c3x-")) last = x;
        assertNotNull(last);
        assertTrue(last, last.endsWith("emerg=true"));
        assertEquals(0, r.mock.position(S).signum());
        assertTrue(r.alerts.toString(), r.alerts.toString().contains("MAT STOP") || r.alerts.toString().contains("stop bi san ket thuc"));
        assertTrue(c3.signum() > 0);
        assertLegacyUntouched(r);
    }

    // ------------------------------------------------------------------ pham vi gateway
    @Test
    public void scopedGatewayRefusesOutOfScopeWrites() throws Exception {
        MainAccountRig r = new MainAccountRig(tmp.getRoot());
        String lg = MainAccountRig.legacySym(4);
        int w = r.mock.totalCalls();
        try {
            r.sgw.cancelStop(MainAccountRig.legacySym(1), "legacy_sl_1");
            fail();
        } catch (C3ScopedGateway.ScopeRefusal e) {
            assertTrue(e.isDefinitelyNotExecuted());
        }
        try {
            r.sgw.newMarketOrder(lg, Side.SELL, BigDecimal.ONE, "c3x-" + lg + "-1-1", true);
            fail("ban qua qty c3 (0) tren symbol LEGACY");
        } catch (C3ScopedGateway.ScopeRefusal e) {
            assertTrue(e.getMessage(), e.getMessage().contains("qty c3"));
        }
        try {
            r.sgw.newMarketOrder(lg, Side.BUY, BigDecimal.ONE, "web_x", false);
            fail();
        } catch (C3ScopedGateway.ScopeRefusal e) {
            assertTrue(e.getMessage().contains("cid"));
        }
        try {
            r.sgw.setDualSidePosition(false);
            fail();
        } catch (C3ScopedGateway.ScopeRefusal e) {
            assertTrue(e.getMessage().contains("CHI DOC"));
        }
        try {
            r.sgw.setLeverage(lg, 1);
            fail();
        } catch (C3ScopedGateway.ScopeRefusal e) {
            assertTrue(e.getMessage().contains("ngoai c3"));
        }
        try {
            r.sgw.newStopMarket(lg, Side.SELL, null, new BigDecimal("0.5"), "c3s-" + lg + "-1-1", true);
            fail("stop closePosition tren symbol co vi the LEGACY");
        } catch (C3ScopedGateway.ScopeRefusal e) {
            assertTrue(e.getMessage().contains("LEGACY"));
        }
        assertEquals("chi cac lan doc kiem truoc ghi, 0 lenh ghi toi san", 0, r.mock.calls("newMarketOrder") + r.mock.calls("cancelStop")
                + r.mock.calls("setLeverage") + r.mock.calls("newStopMarket") + r.mock.calls("setDualSidePosition"));
        assertTrue(r.mock.totalCalls() > w);
        assertEquals(1, r.sgw.setLeverage(C3LiveFixtures.sym(20), 1));
        assertNotNull(r.sgw.account());
        assertTrue("account view an LEGACY", r.sgw.account().getPositions().isEmpty());
        assertLegacyUntouched(r);
        assertEquals(0, new HashSet<>(r.c3WritesOutside(Collections.singleton(C3LiveFixtures.sym(20)))).size());
        assertEquals(KillSwitchEngine.Action.NONE, r.ks.requiredAction());
    }
}
