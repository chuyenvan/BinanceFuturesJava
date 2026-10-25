package com.binance.chuyennd.c3live.recon;

import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.exit.TrailingStopManager;
import com.binance.chuyennd.c3live.fill.FillAccounting;
import com.binance.chuyennd.c3live.fill.UserStreamEvents;
import com.binance.chuyennd.c3live.filters.SymbolRules;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/**
 * [V12 C9] Restart giua vi the (co/khong stop, leg DCA do, stop da khop luc bot chet) => khoi phuc tsFirstLeg/legCount/
 * peak/stop 100 %; san thang qty/gia; stop mo coi huy; vi the la => chan mo moi (khong tu dong); doi chieu equity hang gio.
 */
public class ReconcilerTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final long T0 = 1_792_900_000_000L;
    final AtomicLong now = new AtomicLong(T0);
    MockExchangeGateway gw;
    ExchangeInfo ei;
    File bookFile;
    List<String> alerts;

    @Before
    public void setUp() {
        gw = new MockExchangeGateway();
        ei = C3LiveFixtures.info(6);
        gw.exchangeInfo = ei;
        gw.dynamicAccount = true;
        bookFile = new File(tmp.getRoot(), "run/c3live_book.json");
        alerts = new ArrayList<>();
    }

    /** 1 "JVM" c3_live (so + ke toan + reconcile + trailing) tren cung file so. */
    final class Node {
        final LiveBookC3 book = new LiveBookC3(bookFile, 1.0);
        final FillAccounting acct = new FillAccounting(book, gw, new OrderAuditLog(OrderAuditLog.LIVE_TAG, s -> { }), null,
                alerts::add, null, now::get, null);
        final Reconciler rec = new Reconciler(gw, book, acct, () -> new SymbolRules(ei, T0), alerts::add, null, now::get, 0.01,
                2, new File(tmp.getRoot(), "run/c3live_reanchor.req"));
        final TrailingStopManager mgr = TrailingStopManager.builder().gateway(gw).book(book)
                .rules(() -> new SymbolRules(ei, T0)).closer((s, r) -> 0).defer((s, t, n) -> false)
                .armHook((s, t, n) -> { }).clock(now::get).safeRetryMs(0L).build();
        final C3LiveOrderExecutor ex = new C3LiveOrderExecutor(gw, book, null, null, now::get, ms -> now.addAndGet(ms), 0L, 3,
                Runnable::run);

        Node(boolean streamUp) {
            acct.setUnknownPositionSink(rec::onUnknownPosition);
            gw.wsSink = streamUp ? txt -> acct.dispatch(UserStreamEvents.parse(txt)) : null;
        }

        void leg(String sym, int legIdx, String px, String qty) {
            String cid = "c3-" + sym + "-" + (500 + legIdx) + "-" + legIdx;
            assertTrue(book.reserve(sym, cid, legIdx, 500 + legIdx, "X", Double.parseDouble(px), new BigDecimal(qty),
                    Double.parseDouble(px) * Double.parseDouble(qty), now.get()));
            gw.setPrice(sym, new BigDecimal(px));
            ex.submit(cid);
            book.setMeta(sym, 0.5f, 3, now.get());
        }

        void step(String sym, float px) {
            Map<String, Float> m = new HashMap<>();
            m.put(sym, px);
            gw.setPrice(sym, new BigDecimal(Float.toString(px)));
            mgr.step(m);
        }
    }

    private static void sameState(LiveBookC3.ClusterView a, LiveBookC3.ClusterView b) {
        assertEquals(a.tsFirstLeg, b.tsFirstLeg);
        assertEquals(a.legCount, b.legCount);
        assertEquals(0, a.confirmedQty.compareTo(b.confirmedQty));
        assertEquals(Float.floatToIntBits(a.avgEntryF), Float.floatToIntBits(b.avgEntryF));
        assertEquals(Float.floatToIntBits(a.peakRate), Float.floatToIntBits(b.peakRate));
        assertEquals(Float.floatToIntBits(a.priceSL), Float.floatToIntBits(b.priceSL));
        assertEquals(a.stopClientAlgoId, b.stopClientAlgoId);
        assertEquals(a.stopPrice, b.stopPrice, 0d);
        assertEquals(a.symbolPred, b.symbolPred);
        assertEquals(a.rank, b.rank);
        assertEquals(a.stopSeq, b.stopSeq);
        assertEquals(a.peak, b.peak, 0d);
    }

    @Test
    public void restartWithStopRestores100pct() {
        Node n1 = new Node(true);
        n1.leg("C00USDT", 0, "1.0", "100");
        n1.step("C00USDT", 1.12f);
        n1.step("C00USDT", 1.25f);
        LiveBookC3.ClusterView before = n1.book.cluster("C00USDT").get();
        assertNotNull(before.stopClientAlgoId);
        // --- restart
        Node n2 = new Node(true);
        assertEquals(0, n2.ex.resolveUnresolved(true));
        Reconciler.Report r = n2.rec.startup();
        assertTrue(r.toString(), r.ok && r.closedWhileDown.isEmpty() && r.overridden.isEmpty() && r.stopsDropped.isEmpty()
                && r.orphanCancelled.isEmpty() && r.unknownPositions.isEmpty());
        sameState(before, n2.book.cluster("C00USDT").get());
        assertTrue(n2.rec.allowsEntry("C01USDT"));
        int stops0 = gw.calls("newStopMarket");
        n2.step("C00USDT", 1.24f);
        assertEquals("khong dat stop trung sau restart", stops0, gw.calls("newStopMarket"));
        assertEquals(1, gw.openStops("C00USDT").size());
    }

    @Test
    public void restartArmedButStopMissingReplacesStop() {
        Node n1 = new Node(true);
        n1.leg("C00USDT", 0, "1.0", "100");
        n1.step("C00USDT", 1.12f);
        String sid = n1.book.cluster("C00USDT").get().stopClientAlgoId;
        gw.cancelStop("C00USDT", sid);   // stop bien mat (huy tay / san)
        Node n2 = new Node(true);
        Reconciler.Report r = n2.rec.startup();
        assertEquals(1, r.stopsDropped.size());
        assertNull(n2.book.cluster("C00USDT").get().stopClientAlgoId);
        assertTrue("van arm (priceSL persist)", n2.book.cluster("C00USDT").get().trailArmed());
        n2.mgr.step(new HashMap<>());   // ke ca khong co gia
        assertEquals(1, gw.openStops("C00USDT").size());
    }

    @Test
    public void restartWithPendingStopAlreadyOnExchangeNoDuplicate() {
        Node n1 = new Node(true);
        n1.leg("C00USDT", 0, "1.0", "100");
        // gia lap: da ghi pending + gui len san roi JVM chet truoc khi nhan response
        n1.book.setTrail("C00USDT", 0.12f, 1.09f, now.get());
        n1.book.setPendingStop("C00USDT", "c3s-C00USDT-1-1", 1.09, false, now.get());
        gw.newStopMarket("C00USDT", Side.SELL, new BigDecimal("1.09"), "c3s-C00USDT-1-1", true);
        Node n2 = new Node(true);
        Reconciler.Report r = n2.rec.startup();
        assertEquals(1, r.pendingPromoted.size());
        assertEquals("c3s-C00USDT-1-1", n2.book.cluster("C00USDT").get().stopClientAlgoId);
        int c0 = gw.calls("newStopMarket");
        n2.step("C00USDT", 1.11f);
        assertEquals(c0, gw.calls("newStopMarket"));
    }

    @Test
    public void restartWithDcaLegHalfwayResolvedFromExchange() {
        Node n1 = new Node(true);
        n1.leg("C00USDT", 0, "1.0", "100");
        n1.step("C00USDT", 1.12f);   // arm
        // DCA leg: ghi SENDING, san khop, JVM chet truoc khi ghi CONFIRMED
        String cid = "c3-C00USDT-900-1";
        assertTrue(n1.book.reserve("C00USDT", cid, 1, 900, "DCA_LEVEL1", 0.5, new BigDecimal("100"), 50.0, now.get()));
        n1.book.markSending(cid, now.get());
        gw.wsSink = null;   // stream chet cung JVM
        gw.setPrice("C00USDT", new BigDecimal("0.5"));
        gw.newMarketOrder("C00USDT", Side.BUY, new BigDecimal("100"), cid, false);
        now.addAndGet(20_000L);
        Node n2 = new Node(true);
        assertEquals(0, n2.ex.resolveUnresolved(true));
        Reconciler.Report r = n2.rec.startup();
        assertTrue(r.toString(), r.overridden.isEmpty());
        LiveBookC3.ClusterView c = n2.book.cluster("C00USDT").get();
        assertEquals(2, c.legCount);
        assertEquals(0, new BigDecimal("200").compareTo(c.confirmedQty));
        assertFalse("DCA reset arm nhu so giay", c.trailArmed());
        n2.mgr.step(new HashMap<>());
        n2.step("C00USDT", 0.6f);
        assertNull("stop cu bi huy sau DCA", n2.book.cluster("C00USDT").get().stopClientAlgoId);
        assertTrue(gw.openStops("C00USDT").isEmpty());
    }

    @Test
    public void stopFilledWhileBotDownClosesClusterOnRestart() throws Exception {
        Node n1 = new Node(true);
        n1.leg("C00USDT", 0, "1.0", "100");
        n1.step("C00USDT", 1.12f);
        gw.wsSink = null;   // bot chet
        gw.triggerStops("C00USDT", new BigDecimal("1.05"));
        assertEquals(0, gw.position("C00USDT").signum());
        Node n2 = new Node(true);
        Reconciler.Report r = n2.rec.startup();
        assertEquals("[C00USDT:" + FillAccounting.REASON_TRAILING + "]", r.closedWhileDown.toString());
        assertFalse(n2.book.isHolding("C00USDT"));
        List<String> ledger = Files.readAllLines(new File(tmp.getRoot(), "run/" + LiveBookC3.LEDGER_NAME).toPath());
        assertTrue(ledger.get(ledger.size() - 1).contains(FillAccounting.REASON_TRAILING));
    }

    @Test
    public void exchangeWinsQtyAndOrphanAndForeignStops() {
        Node n1 = new Node(true);
        n1.leg("C00USDT", 0, "1.0", "100");
        gw.setPosition("C00USDT", new BigDecimal("90"), new BigDecimal("1.01"));   // lech so
        gw.newStopMarket("C01USDT", Side.SELL, new BigDecimal("1"), "c3s-C01USDT-1-1", true);   // mo coi
        gw.newStopMarket("C02USDT", Side.SELL, new BigDecimal("1"), "manual-owner-1", true);    // khong phai cua bot
        Node n2 = new Node(true);
        Reconciler.Report r = n2.rec.startup();
        assertEquals(1, r.overridden.size());
        LiveBookC3.ClusterView c = n2.book.cluster("C00USDT").get();
        assertEquals(0, new BigDecimal("90").compareTo(c.confirmedQty));
        assertEquals(1.01, c.avgPrice, 1e-12);
        assertEquals(1, r.orphanCancelled.size());
        assertEquals(1, r.foreignStops.size());
        assertEquals(1, gw.openStops("C02USDT").size());
        assertTrue(gw.openStops("C01USDT").isEmpty());
        assertFalse(alerts.isEmpty());
    }

    @Test
    public void unknownPositionBlocksEntryUntilGone() {
        Node n = new Node(true);
        gw.setPosition("C03USDT", new BigDecimal("7"), BigDecimal.ONE);
        n.rec.startup();
        assertFalse(n.rec.allowsEntry("C00USDT"));
        assertTrue(n.rec.blocks().containsKey(Reconciler.BLOCK_UNKNOWN));
        assertEquals("KHONG tu dong vi the la", 0, gw.calls("newMarketOrder"));
        gw.setPosition("C03USDT", BigDecimal.ZERO, BigDecimal.ONE);
        n.rec.checkPositions();
        assertTrue(n.rec.allowsEntry("C00USDT"));
    }

    @Test
    public void startupReadFailureBlocksEntry() {
        Node n = new Node(true);
        gw.failNext("positions", new GatewayException(ErrorKind.TIMEOUT_UNKNOWN_STATE, "timeout", false));
        assertFalse(n.rec.startup().ok);
        assertFalse(n.rec.allowsEntry("C00USDT"));
        assertTrue(n.rec.startup().ok);
        assertTrue(n.rec.allowsEntry("C00USDT"));
    }

    @Test
    public void hourlyEquityMismatchBlocksAndReleasesAfterTwoMatches() throws Exception {
        Node n = new Node(true);
        n.leg("C00USDT", 0, "1.0", "1000");
        n.rec.startup();
        n.rec.hourly();   // dat moc
        assertTrue(n.book.account().anchored());
        gw.setPrice("C00USDT", new BigDecimal("1.1"));
        n.rec.hourly();
        assertTrue("lai chua chot tinh dung => khop", n.rec.allowsEntry("C00USDT"));
        gw.deposit(new BigDecimal("500"));   // owner chuyen tien khi KHONG co stream ghi nhan
        n.rec.hourly();
        assertFalse(n.rec.allowsEntry("C00USDT"));
        assertTrue(alerts.stream().anyMatch(a -> a.contains("LECH EQUITY")));
        gw.deposit(new BigDecimal("-500"));
        n.rec.hourly();
        assertFalse("can khop 2 lan lien tiep", n.rec.allowsEntry("C00USDT"));
        n.rec.hourly();
        assertTrue(n.rec.allowsEntry("C00USDT"));
        // yeu cau dat lai moc cua owner
        gw.deposit(new BigDecimal("300"));
        n.rec.hourly();
        assertFalse(n.rec.allowsEntry("C00USDT"));
        Files.write(new File(tmp.getRoot(), "run/c3live_reanchor.req").toPath(), "{}".getBytes());
        n.rec.hourly();
        assertTrue(n.rec.allowsEntry("C00USDT"));
    }

    @Test
    public void fallbackRestDetectsStopFillWhenStreamDown() {
        Node n = new Node(false);   // stream chet
        n.leg("C00USDT", 0, "1.0", "100");
        n.step("C00USDT", 1.12f);
        gw.triggerStops("C00USDT", new BigDecimal("1.05"));
        assertTrue(n.book.isHolding("C00USDT"));
        Reconciler.Report r = n.rec.checkPositions();
        assertEquals("[C00USDT:" + FillAccounting.REASON_TRAILING + "]", r.closedWhileDown.toString());
        assertFalse(n.book.isHolding("C00USDT"));
        OrderInfo dummy = null;
        assertNull(dummy);
    }
}
