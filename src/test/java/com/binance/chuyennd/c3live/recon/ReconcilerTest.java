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
            // [2e] nhu runtime: 1 guard huy stop c3s- dung chung
            acct.setStopGuard(rec.stopGuard());
            mgr.setStopGuard(rec.stopGuard());
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
        assertFalse("[2d MIN-18] 1 lan doc vang chua go chan", n.rec.allowsEntry("C00USDT"));
        now.addAndGet(FlatConfirm.DEFAULT_MIN_GAP_MS);
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

    // ------------------------------------------------------------------ [2c] MAJ-1 / [2d] MAJ-2b / MIN-18 / MIN-6

    static final long GAP = FlatConfirm.DEFAULT_MIN_GAP_MS;   // 30 s

    @Test
    public void entryBlockedBeforeStartupReconcile() {
        Node n = new Node(true);
        assertFalse("MAJ-1: truoc startup() phai CHAN", n.rec.allowsEntry("C00USDT"));
        assertTrue(n.rec.blocks().containsKey(Reconciler.BLOCK_STARTUP));
        assertTrue(n.rec.startup().ok);
        assertTrue(n.rec.allowsEntry("C00USDT"));
        assertTrue(n.rec.blocks().isEmpty());
    }

    /**
     * Hoi quy ProofFlat (A1_DELTA_2C): mat stream + positionRisk 200 nhung RONG (vi the THAT con, stop c3s- NEW) => KHONG
     * bao gio huy stop / xoa cum, du doc nhieu lan cach >= 30 s.
     */
    @Test
    public void proofFlatRegressionGlitchNeverCancelsStopOfRealPosition() {
        Node n = new Node(false);   // stream chet
        n.leg("C00USDT", 0, "1.0", "100");
        n.step("C00USDT", 1.12f);   // arm => stop c3s- NEW tren san
        assertTrue(n.rec.startup().ok);
        String sid = n.book.cluster("C00USDT").get().stopClientAlgoId;
        assertNotNull(sid);
        int c0 = gw.calls("cancelStop");
        gw.positionsGlitch = true;
        long[] steps = {10_000L, 10_000L, GAP, GAP, GAP, GAP};
        for (long d : steps) {
            now.addAndGet(d);
            Reconciler.Report r = n.rec.checkPositions();
            assertTrue(r.toString(), r.closedWhileDown.isEmpty());
            assertTrue("giu cum", n.book.isHolding("C00USDT"));
            assertEquals("giu stop", c0, gw.calls("cancelStop"));
            assertEquals(1, gw.openStops("C00USDT").size());
            assertEquals(sid, n.book.cluster("C00USDT").get().stopClientAlgoId);
            assertFalse(n.rec.allowsEntry("C00USDT"));
        }
        assertEquals("vi the THAT van con", 0, new BigDecimal("100").compareTo(gw.position("C00USDT")));
        gw.positionsGlitch = false;
        now.addAndGet(GAP);
        assertTrue(n.rec.checkPositions().flatPending.isEmpty());
        assertTrue(n.rec.flatPending().isEmpty());
        assertTrue(n.rec.allowsEntry("C00USDT"));
    }

    /** (a) thieu: phang THAT, khong stop, account phang — nhung chua du 3 lan doc cach >= 30 s => giu; lan 3 => phang. */
    @Test
    public void conditionA_needsThreeReadsThirtySecondsApart() {
        Node n = new Node(false);
        n.leg("C00USDT", 0, "1.0", "100");   // chua arm => khong stop
        assertTrue(n.rec.startup().ok);
        gw.setPosition("C00USDT", BigDecimal.ZERO, BigDecimal.ONE);   // phang that (ngoai bot), stream chet
        long[] steps = {0L, 10_000L, 10_000L, 10_000L};   // doc 1 tai t, roi +10 +20 +30 (chi +30 duoc tinh = lan 2)
        for (long d : steps) {
            now.addAndGet(d);
            assertTrue(n.rec.checkPositions().closedWhileDown.isEmpty());
            assertTrue(n.book.isHolding("C00USDT"));
        }
        now.addAndGet(GAP - 1);
        assertNull("chua du 30 s ke tu lan tinh truoc", n.rec.confirmPendingFlat());
        assertTrue(n.book.isHolding("C00USDT"));
        now.addAndGet(1);
        Reconciler.Report r = n.rec.confirmPendingFlat();   // lan 3
        assertNotNull(r);
        assertEquals("[C00USDT:" + FillAccounting.REASON_EXTERNAL + "]", r.closedWhileDown.toString());
        assertFalse(n.book.isHolding("C00USDT"));
    }

    /** (b) thieu: positionRisk rong nhung account().positions VAN co vi the (hoac khong co mang) => giu mai. */
    @Test
    public void conditionB_accountPositionsMustAlsoBeFlat() {
        Node n = new Node(false);
        n.leg("C00USDT", 0, "1.0", "100");   // khong stop => (c) thoa
        assertTrue(n.rec.startup().ok);
        gw.positionsGlitch = true;           // positionRisk rong, account REAL con vi the
        for (int i = 0; i < 5; i++) {
            n.rec.checkPositions();
            now.addAndGet(GAP);
        }
        assertTrue(n.book.isHolding("C00USDT"));
        gw.accountPositions = MockExchangeGateway.AccountPositions.NULL;   // san khong tra mang => khong doi chung duoc
        for (int i = 0; i < 3; i++) {
            n.rec.checkPositions();
            now.addAndGet(GAP);
        }
        assertTrue("account khong co positions => khong ket luan phang", n.book.isHolding("C00USDT"));
        assertTrue(n.rec.flatPending().contains("C00USDT"));
    }

    /** (c) thieu: phang that + account phang nhung VAN con stop c3s- NEW => giu cum + stop, Telegram WARN DUNG 1 lan. */
    @Test
    public void conditionC_openOwnStopBlocksFlatConclusionWithSingleAlert() {
        Node n = new Node(false);
        n.leg("C00USDT", 0, "1.0", "100");
        n.step("C00USDT", 1.12f);   // arm => stop NEW
        assertTrue(n.rec.startup().ok);
        String sid = n.book.cluster("C00USDT").get().stopClientAlgoId;
        gw.setPosition("C00USDT", BigDecimal.ZERO, BigDecimal.ONE);   // owner dong tay, stream chet
        int a0 = alerts.size();
        int c0 = gw.calls("cancelStop");
        for (int i = 0; i < 6; i++) {
            n.rec.checkPositions();
            now.addAndGet(GAP);
        }
        assertTrue(n.book.isHolding("C00USDT"));
        assertEquals(c0, gw.calls("cancelStop"));
        assertEquals(1, gw.openStops("C00USDT").size());
        long warn = alerts.subList(a0, alerts.size()).stream().filter(m -> m.contains("stop c3s- NEW")).count();
        assertEquals("Telegram WARN 1 lan", 1L, warn);
        // owner huy stop tay => (c) thoa => lan doc ke tiep ket luan phang
        gw.cancelStop("C00USDT", sid);
        Reconciler.Report r = n.rec.checkPositions();
        assertEquals(1, r.closedWhileDown.size());
        assertFalse(n.book.isHolding("C00USDT"));
    }

    @Test
    public void positionReappearsClearsSuspicion() {
        Node n = new Node(false);
        n.leg("C00USDT", 0, "1.0", "100");
        assertTrue(n.rec.startup().ok);
        gw.setPosition("C00USDT", BigDecimal.ZERO, BigDecimal.ONE);
        assertEquals(1, n.rec.checkPositions().flatPending.size());
        now.addAndGet(GAP);
        n.rec.checkPositions();   // lan 2
        gw.setPosition("C00USDT", new BigDecimal("100"), BigDecimal.ONE);   // vi the hien lai => xoa moc
        now.addAndGet(GAP);
        assertTrue(n.rec.checkPositions().flatPending.isEmpty());
        gw.setPosition("C00USDT", BigDecimal.ZERO, BigDecimal.ONE);
        now.addAndGet(GAP);
        n.rec.checkPositions();   // lai la lan 1
        now.addAndGet(GAP);
        n.rec.checkPositions();   // lan 2
        assertTrue("dem lai tu dau sau khi vi the hien lai", n.book.isHolding("C00USDT"));
    }

    @Test
    public void startupWithMissingPositionKeepsClusterUntilConfirmed() {
        Node n1 = new Node(true);
        n1.leg("C00USDT", 0, "1.0", "100");
        gw.wsSink = null;
        gw.setPosition("C00USDT", BigDecimal.ZERO, BigDecimal.ONE);   // positionRisk thieu symbol luc restart (khong stop)
        Node n2 = new Node(false);
        Reconciler.Report r = n2.rec.startup();
        assertTrue(r.ok);
        assertEquals("[C00USDT]", r.flatPending.toString());
        assertTrue(r.closedWhileDown.isEmpty());
        assertTrue(n2.book.isHolding("C00USDT"));
        assertTrue(n2.rec.allowsEntry("C01USDT"));
        assertFalse(n2.rec.allowsEntry("C00USDT"));
        now.addAndGet(GAP);
        assertTrue(n2.rec.confirmPendingFlat().closedWhileDown.isEmpty());   // lan 2
        now.addAndGet(GAP);
        Reconciler.Report r3 = n2.rec.confirmPendingFlat();                   // lan 3
        assertEquals(1, r3.closedWhileDown.size());
        assertFalse(n2.book.isHolding("C00USDT"));
    }

    /** MIN-18: 1 lan doc rong KHONG go chan UNKNOWN_POSITION; can >= 2 lan doc nhat quan cach >= 30 s. */
    @Test
    public void unknownBlockNotReleasedByOneEmptyRead() {
        Node n = new Node(true);
        gw.setPosition("C03USDT", new BigDecimal("7"), BigDecimal.ONE);
        n.rec.startup();
        assertTrue(n.rec.blocks().containsKey(Reconciler.BLOCK_UNKNOWN));
        gw.positionsGlitch = true;
        n.rec.checkPositions();
        assertFalse("1 lan doc rong: van chan", n.rec.allowsEntry("C00USDT"));
        now.addAndGet(10_000L);
        n.rec.checkPositions();
        assertFalse("2 lan nhung < 30 s: van chan", n.rec.allowsEntry("C00USDT"));
        gw.positionsGlitch = false;
        now.addAndGet(GAP);
        n.rec.checkPositions();   // vi the la hien lai => xoa moc
        assertFalse(n.rec.allowsEntry("C00USDT"));
        gw.setPosition("C03USDT", BigDecimal.ZERO, BigDecimal.ONE);   // het that
        n.rec.checkPositions();
        assertFalse("het lan 1: van chan", n.rec.allowsEntry("C00USDT"));
        now.addAndGet(GAP);
        n.rec.checkPositions();
        assertTrue("2 lan nhat quan cach >= 30 s: go chan", n.rec.allowsEntry("C00USDT"));
    }

    /** MIN-6: so mat tham chieu stop (ghi loi) nhung stop VAN tren san, cum da arm => restart NHAN lai stop, khong huy. */
    @Test
    public void startupAdoptsOwnStopForArmedClusterInsteadOfCancelling() {
        Node n1 = new Node(true);
        n1.leg("C00USDT", 0, "1.0", "100");
        n1.step("C00USDT", 1.12f);
        String a = n1.book.cluster("C00USDT").get().stopClientAlgoId;
        assertNotNull(a);
        n1.book.retireActiveStop("C00USDT", now.get());
        n1.book.removeOrphanStop("C00USDT", a, now.get());
        assertFalse(n1.book.referencedStopCids().contains(a));
        Node n2 = new Node(true);
        Reconciler.Report r = n2.rec.startup();
        assertTrue(r.toString(), r.orphanCancelled.isEmpty());
        assertEquals(a, n2.book.cluster("C00USDT").get().stopClientAlgoId);
        assertEquals(1, gw.openStops("C00USDT").size());
        int s0 = gw.calls("newStopMarket");
        n2.step("C00USDT", 1.12f);
        assertEquals("khong dat stop trung", s0, gw.calls("newStopMarket"));
    }

    // ------------------------------------------------------------------ [2e] MAJ-3 (ProofFlat2 ca D/E) + cum ma

    static final String XRP = "XRPUSDT";
    static final String XRP_STOP = "c3s-XRPUSDT-29883400-1";

    /**
     * Hoi quy ProofFlat2 ca D (A1_DELTA_2D): so MAT/rollback (rong) + vi the THAT XRP 100 con stop c3s- NEW => startup KHONG
     * huy stop; XRP vao UNKNOWN_POSITION (chan mo moi) + Telegram; quet hang gio sau do van giu.
     */
    @Test
    public void proofFlat2CaseD_startupKeepsOwnStopOfRealPositionMissingFromBook() {
        gw.setPrice(XRP, BigDecimal.ONE);
        gw.setPosition(XRP, new BigDecimal("100"), BigDecimal.ONE);
        gw.newStopMarket(XRP, Side.SELL, new BigDecimal("0.95"), XRP_STOP, true);
        Node n = new Node(true);
        int c0 = gw.calls("cancelStop");
        Reconciler.Report r = n.rec.startup();
        assertTrue(r.toString(), r.orphanCancelled.isEmpty());
        assertEquals(r.toString(), 1, r.orphanKept.size());
        assertTrue(r.orphanKept.get(0), r.orphanKept.get(0).contains("KEPT_POSITION"));
        assertEquals("KHONG goi huy", c0, gw.calls("cancelStop"));
        assertEquals(1, gw.openStops(XRP).size());
        assertTrue(r.unknownPositions.contains(XRP));
        assertTrue(n.rec.blocks().get(Reconciler.BLOCK_UNKNOWN).contains(XRP));
        assertFalse(n.rec.allowsEntry(XRP));
        assertFalse(n.rec.allowsEntry("C00USDT"));
        assertTrue(alerts.stream().anyMatch(m -> m.contains("GIU stop " + XRP)));
        now.addAndGet(3_600_000L);
        Reconciler.Report h = n.rec.hourly();
        assertTrue(h.toString(), h.orphanCancelled.isEmpty());
        assertEquals(1, gw.openStops(XRP).size());
        assertEquals(c0, gw.calls("cancelStop"));
        assertEquals(0, new BigDecimal("100").compareTo(gw.position(XRP)));
    }

    /** Hoi quy ProofFlat2 ca E: so giu C00, vi the la DOGE (tay) co stop c3s- => quet hang gio GIU stop DOGE. */
    @Test
    public void proofFlat2CaseE_hourlySweepKeepsOwnStopOfForeignPosition() {
        Node n = new Node(true);
        n.leg("C00USDT", 0, "1.0", "100");
        n.step("C00USDT", 1.12f);
        assertTrue(n.rec.startup().ok);
        String ocid = "c3s-DOGEUSDT-29883500-1";
        gw.setPrice("DOGEUSDT", new BigDecimal("0.10"));
        gw.setPosition("DOGEUSDT", new BigDecimal("50"), new BigDecimal("0.10"));
        gw.newStopMarket("DOGEUSDT", Side.SELL, new BigDecimal("0.09"), ocid, true);
        int c0 = gw.calls("cancelStop");
        now.addAndGet(3_600_000L);
        Reconciler.Report r = n.rec.hourly();
        assertTrue(r.toString(), r.orphanCancelled.isEmpty());
        assertTrue(r.toString(), r.orphanKept.contains("DOGEUSDT/" + ocid + ":KEPT_POSITION"));
        assertEquals(c0, gw.calls("cancelStop"));
        assertEquals(1, gw.openStops("DOGEUSDT").size());
        assertFalse(n.rec.allowsEntry("C01USDT"));
        assertTrue(n.rec.blocks().get(Reconciler.BLOCK_UNKNOWN).contains("DOGEUSDT"));
        assertTrue("cum C00 khong bi dong", n.book.isHolding("C00USDT"));
    }

    /** Stop c3s- mo coi, ca positionRisk lan account deu phang => huy (hanh vi don dep van con). */
    @Test
    public void orphanOwnStopCancelledWhenBothSourcesFlat() {
        gw.newStopMarket("C01USDT", Side.SELL, new BigDecimal("1"), "c3s-C01USDT-1-1", true);
        Node n = new Node(true);
        Reconciler.Report r = n.rec.startup();
        assertEquals("[C01USDT/c3s-C01USDT-1-1]", r.orphanCancelled.toString());
        assertTrue(r.orphanKept.isEmpty());
        assertTrue(gw.openStops("C01USDT").isEmpty());
        assertTrue(n.rec.allowsEntry("C00USDT"));
        assertTrue(n.rec.stopGuard().keptStops().isEmpty());
    }

    /** Doc account loi / account khong co mang positions => GIU stop + UNKNOWN; doc lai duoc va phang => huy + go chan. */
    @Test
    public void guardReadErrorKeepsStopThenRetriesAndReleases() {
        gw.newStopMarket("C01USDT", Side.SELL, new BigDecimal("1"), "c3s-C01USDT-1-1", true);
        gw.failNext("account", new GatewayException(ErrorKind.TIMEOUT_UNKNOWN_STATE, "timeout", false));
        Node n = new Node(true);
        Reconciler.Report r = n.rec.startup();
        assertTrue(r.toString(), r.orphanCancelled.isEmpty());
        assertTrue(r.orphanKept.get(0), r.orphanKept.get(0).endsWith(":KEPT_READ_ERROR"));
        assertEquals(1, gw.openStops("C01USDT").size());
        assertFalse(n.rec.allowsEntry("C00USDT"));
        // lan doc lai: account khong co mang positions => van giu
        gw.accountPositions = MockExchangeGateway.AccountPositions.NULL;
        now.addAndGet(GAP);
        assertNotNull(n.rec.confirmPendingFlat());
        assertEquals(1, gw.openStops("C01USDT").size());
        assertFalse(n.rec.allowsEntry("C00USDT"));
        // doc duoc + phang => huy, roi go chan sau 2 lan doc nhat quan
        gw.accountPositions = MockExchangeGateway.AccountPositions.REAL;
        now.addAndGet(GAP);
        Reconciler.Report r2 = n.rec.confirmPendingFlat();
        assertEquals("[C01USDT/c3s-C01USDT-1-1]", r2.orphanCancelled.toString());
        assertTrue(gw.openStops("C01USDT").isEmpty());
        assertFalse("chua go ngay", n.rec.allowsEntry("C00USDT"));
        now.addAndGet(GAP);
        n.rec.confirmPendingFlat();
        assertTrue(n.rec.allowsEntry("C00USDT"));
    }

    static final String PA0_C00 = "{\"e\":\"ACCOUNT_UPDATE\",\"E\":1,\"a\":{\"m\":\"ORDER\",\"B\":[],\"P\":[{\"s\":\"C00USDT\","
            + "\"pa\":\"0\",\"ep\":\"0\",\"ps\":\"BOTH\"}]}}";

    /**
     * [2f] Duong thuong: cum X (C00, co stop) chot, stream pa=0 nhung positionRisk/account VAN con vi the (REST tre) => xoa cum
     * theo stream, GIU stop, CHI chan X (lop B); symbol Y (C01) moi VAN vao duoc; khong UNKNOWN toan he. San phang => huy
     * stop; X duoc go sau 2 lan doc phang cach >= 30 s.
     */
    @Test
    public void streamFlatButRestLagBlocksOnlyThatSymbol() {
        Node n = new Node(true);
        n.leg("C00USDT", 0, "1.0", "100");
        n.step("C00USDT", 1.12f);
        assertTrue(n.rec.startup().ok);
        String sid = n.book.cluster("C00USDT").get().stopClientAlgoId;
        int c0 = gw.calls("cancelStop");
        gw.emitRaw(PA0_C00);
        assertFalse("stream la bang chung duong => xoa cum", n.book.isHolding("C00USDT"));
        assertEquals("GIU stop", c0, gw.calls("cancelStop"));
        assertEquals(1, gw.openStops("C00USDT").size());
        assertTrue(n.rec.stopGuard().keptStops().containsKey(sid));
        assertTrue("Y vao duoc", n.rec.allowsEntry("C01USDT"));
        assertFalse("X bi chan", n.rec.allowsEntry("C00USDT"));
        assertTrue(n.rec.blocks().toString(), n.rec.blocks().isEmpty());
        assertEquals("[C00USDT]", n.rec.symbolBlocks().toString());
        // REST van con => giu, van chi chan X
        now.addAndGet(GAP);
        assertNotNull(n.rec.confirmPendingFlat());
        assertEquals(1, gw.openStops("C00USDT").size());
        assertTrue(n.rec.allowsEntry("C01USDT"));
        assertFalse(n.rec.allowsEntry("C00USDT"));
        assertFalse(n.rec.blocks().containsKey(Reconciler.BLOCK_UNKNOWN));
        // san that su phang => huy stop; lan doc phang 1
        gw.setPosition("C00USDT", BigDecimal.ZERO, BigDecimal.ONE);
        now.addAndGet(GAP);
        Reconciler.Report r = n.rec.confirmPendingFlat();
        assertEquals("[C00USDT/" + sid + "]", r.orphanCancelled.toString());
        assertTrue(gw.openStops("C00USDT").isEmpty());
        assertFalse("1 lan doc phang: X van chan", n.rec.allowsEntry("C00USDT"));
        assertTrue(n.rec.allowsEntry("C01USDT"));
        now.addAndGet(GAP);
        n.rec.confirmPendingFlat();   // lan doc phang 2
        assertTrue("2 lan doc phang: go X", n.rec.allowsEntry("C00USDT"));
        assertTrue(n.rec.symbolBlocks().isEmpty());
    }

    /** [2f] Cum KHONG co stop (chua arm) chot qua stream, REST tre (doc hang gio/fallback) => van lop B, khong chan toan he. */
    @Test
    public void streamFlatRestLagWithoutStopIsSymbolBlockOnly() {
        Node n = new Node(true);
        n.leg("C00USDT", 0, "1.0", "100");
        assertTrue(n.rec.startup().ok);
        gw.emitRaw(PA0_C00);
        assertFalse(n.book.isHolding("C00USDT"));
        Reconciler.Report r = n.rec.checkPositions();
        assertTrue(r.toString(), r.unknownPositions.isEmpty());
        assertTrue(n.rec.allowsEntry("C01USDT"));
        assertFalse(n.rec.allowsEntry("C00USDT"));
        gw.setPosition("C00USDT", BigDecimal.ZERO, BigDecimal.ONE);
        now.addAndGet(GAP);
        n.rec.confirmPendingFlat();
        assertFalse(n.rec.allowsEntry("C00USDT"));
        now.addAndGet(GAP);
        n.rec.confirmPendingFlat();
        assertTrue(n.rec.allowsEntry("C00USDT"));
    }

    /**
     * [2f] Lop B leo thang: san VAN con vi the (account) qua cua so 10' sau khi so chot => coi la vi the la => UNKNOWN toan he.
     * Trong cua so: con stop giu => X khong duoc go du positionRisk rong.
     */
    @Test
    public void symbolBlockEscalatesToGlobalAfterWindow() {
        Node n = new Node(true);
        n.leg("C00USDT", 0, "1.0", "100");
        n.step("C00USDT", 1.12f);
        assertTrue(n.rec.startup().ok);
        gw.emitRaw(PA0_C00);
        gw.positionsGlitch = true;   // positionRisk rong nhung account VAN con vi the => guard giu
        for (int i = 0; i < 4; i++) {
            now.addAndGet(GAP);
            n.rec.confirmPendingFlat();
            assertFalse("i=" + i, n.rec.allowsEntry("C00USDT"));
            assertTrue("i=" + i, n.rec.allowsEntry("C01USDT"));
            assertEquals(1, gw.openStops("C00USDT").size());
        }
        now.addAndGet(OwnStopGuard.KNOWN_CLOSE_WINDOW_MS);
        n.rec.confirmPendingFlat();
        assertEquals(1, gw.openStops("C00USDT").size());
        assertFalse("qua cua so => toan he", n.rec.allowsEntry("C01USDT"));
        assertTrue(n.rec.blocks().get(Reconciler.BLOCK_UNKNOWN).contains("C00USDT"));
    }

    /** [2f] positionRisk (REST) con vi the qua cua so 10' sau khi so chot => leo thang UNKNOWN toan he. */
    @Test
    public void restPositionPersistingPastWindowEscalates() {
        Node n = new Node(true);
        n.leg("C00USDT", 0, "1.0", "100");
        assertTrue(n.rec.startup().ok);
        gw.emitRaw(PA0_C00);
        n.rec.checkPositions();
        assertTrue(n.rec.allowsEntry("C01USDT"));
        now.addAndGet(OwnStopGuard.KNOWN_CLOSE_WINDOW_MS);
        Reconciler.Report r = n.rec.checkPositions();
        assertEquals("[C00USDT]", r.unknownPositions.toString());
        assertFalse(n.rec.allowsEntry("C01USDT"));
        assertTrue(n.rec.symbolBlocks().isEmpty());
    }

    /**
     * [2g MIN-21] Doc vi the LOI khi giu stop cua cum VUA chot (< 10') => chi (B) symbol do (truoc 2g: A toan he); REST hoi
     * phuc + phang => huy stop, go sau 2 lan doc phang.
     */
    @Test
    public void readErrorOnJustClosedClusterIsSymbolOnly() {
        Node n = new Node(true);
        n.leg("C00USDT", 0, "1.0", "100");
        n.step("C00USDT", 1.12f);
        assertTrue(n.rec.startup().ok);
        gw.failNext("positions", new GatewayException(ErrorKind.TIMEOUT_UNKNOWN_STATE, "timeout", false));
        gw.emitRaw(PA0_C00);
        assertEquals(1, gw.openStops("C00USDT").size());
        assertTrue(n.rec.allowsEntry("C01USDT"));
        assertFalse(n.rec.allowsEntry("C00USDT"));
        assertTrue(n.rec.blocks().toString(), n.rec.blocks().isEmpty());
        assertTrue(n.rec.stopGuard().keptStops().toString(), n.rec.stopGuard().hasKept("C00USDT"));
        gw.setPosition("C00USDT", BigDecimal.ZERO, BigDecimal.ONE);
        now.addAndGet(GAP);
        n.rec.confirmPendingFlat();
        assertTrue(gw.openStops("C00USDT").isEmpty());
        assertFalse(n.rec.allowsEntry("C00USDT"));
        now.addAndGet(GAP);
        n.rec.confirmPendingFlat();
        assertTrue(n.rec.allowsEntry("C00USDT"));
    }

    /** [2g MIN-21] Lop B qua cua so 10': lan giu sau (ke ca do loi doc) => (A) toan he. */
    @Test
    public void readErrorAfterWindowIsGlobal() {
        Node n = new Node(true);
        n.leg("C00USDT", 0, "1.0", "100");
        n.step("C00USDT", 1.12f);
        assertTrue(n.rec.startup().ok);
        gw.emitRaw(PA0_C00);   // REST con 100 => B
        assertTrue(n.rec.allowsEntry("C01USDT"));
        now.addAndGet(OwnStopGuard.KNOWN_CLOSE_WINDOW_MS);
        gw.failNext("account", new GatewayException(ErrorKind.TIMEOUT_UNKNOWN_STATE, "timeout", false));
        n.rec.confirmPendingFlat();
        assertFalse(n.rec.allowsEntry("C01USDT"));
        assertTrue(n.rec.blocks().get(Reconciler.BLOCK_UNKNOWN).contains("C00USDT"));
        assertEquals(1, gw.openStops("C00USDT").size());
    }

    /**
     * [2g MIN-22] Go (B) can CA account().positions phang: stop giu da mat (huy ngoai) + positionRisk rong (glitch) nhung
     * account VAN con vi the => KHONG mo lai X; account phang => go sau 2 lan doc.
     */
    @Test
    public void symbolBlockReleaseNeedsAccountFlat() {
        Node n = new Node(true);
        n.leg("C00USDT", 0, "1.0", "100");
        n.step("C00USDT", 1.12f);
        assertTrue(n.rec.startup().ok);
        String sid = n.book.cluster("C00USDT").get().stopClientAlgoId;
        gw.emitRaw(PA0_C00);   // REST con 100 => B + giu stop
        assertFalse(n.rec.allowsEntry("C00USDT"));
        gw.cancelStop("C00USDT", sid);   // stop mat (san/owner)
        gw.positionsGlitch = true;       // positionRisk rong, account con 100
        for (int i = 0; i < 5; i++) {
            now.addAndGet(GAP);
            n.rec.confirmPendingFlat();
            assertFalse("i=" + i + " account con vi the => khong go X", n.rec.allowsEntry("C00USDT"));
            assertTrue(n.rec.allowsEntry("C01USDT"));
        }
        assertFalse(n.rec.stopGuard().hasKept("C00USDT"));
        gw.positionsGlitch = false;
        gw.setPosition("C00USDT", BigDecimal.ZERO, BigDecimal.ONE);
        now.addAndGet(GAP);
        n.rec.confirmPendingFlat();
        assertFalse(n.rec.allowsEntry("C00USDT"));
        now.addAndGet(GAP);
        n.rec.confirmPendingFlat();
        assertTrue(n.rec.allowsEntry("C00USDT"));
    }

    /** Gateway tre/loi nhu ProofCrash (A1 2ef): positionRisk + account dong bang trong {@code frozenUntil}; readErr => positions nem. */
    static final class LagGateway extends MockExchangeGateway {
        AtomicLong clk;
        long frozenUntil = Long.MIN_VALUE;
        List<com.binance.chuyennd.c3live.api.PositionInfo> fp;
        com.binance.chuyennd.c3live.api.AccountSnapshot fa;
        boolean readErr;

        @Override
        public synchronized List<com.binance.chuyennd.c3live.api.PositionInfo> positions() {
            if (readErr) throw new GatewayException(ErrorKind.OTHER, "503 gia lap", false);
            return clk.get() < frozenUntil ? fp : super.positions();
        }

        @Override
        public synchronized com.binance.chuyennd.c3live.api.AccountSnapshot account() {
            return clk.get() < frozenUntil ? fa : super.account();
        }

        void freeze(long ms) {
            fp = new ArrayList<>(super.positions());
            fa = super.account();
            frozenUntil = clk.get() + ms;
        }
    }

    /**
     * [2g MIN-21] Hoi quy ProofCrash R3 (A1_DELTA_2EF): 3 cum chot cung luc (stop kich, xu ly nhu stream pa=0), moi cum con 1 stop
     * c3s- cu chua huy, REST tre 60 s VA positionRisk LOI DOC dung luc chot => 24/24 leg symbol khac VAO DUOC, 3 symbol vua chot
     * bi chan rieng; ~2' sau (REST het tre) 24/24 + 3/3, het chan, stop cu da huy.
     */
    @Test
    public void proofCrashR3ReadErrorDuringCrashStillAdmitsOtherSymbols() {
        String[] cl = {"AUSDT", "BUSDT", "CUSDT"};
        LagGateway lg = new LagGateway();
        lg.clk = now;
        LiveBookC3 book = new LiveBookC3(null, 1.0);
        int k = 0;
        for (String s : cl) {
            lg.setPrice(s, new BigDecimal("1.00"));
            String cid = "c3-" + s + "-2988" + (k++) + "-0";
            assertTrue(book.reserve(s, cid, 0, 29_880L + k, "BIG_DOWN", 1.0, new BigDecimal("100"), 100.0, now.get()));
            book.markSending(cid, now.get());
            OrderInfo o = lg.newMarketOrder(s, Side.BUY, new BigDecimal("100"), cid, false);
            assertTrue(book.confirm(cid, o.getExecutedQty(), o.getAvgPrice().doubleValue(), o.getOrderId(), now.get()));
            book.setTrail(s, 0.08f, 1.05f, now.get());
            String sc = "c3s-" + s + "-1-1";
            lg.newStopMarket(s, Side.SELL, new BigDecimal("1.05"), sc, true);
            book.setStop(s, 1.05, sc, now.get());
        }
        FillAccounting acct = new FillAccounting(book, lg, OrderAuditLog.dry(), null, alerts::add, null, now::get, null);
        Reconciler rec = new Reconciler(lg, book, acct, () -> null, alerts::add, null, now::get, 0.01, 2, null, null);
        OwnStopGuard g = new OwnStopGuard(lg, book, null, alerts::add, () -> rec::onUnknownPosition, now::get);
        rec.setStopGuard(g);
        acct.setStopGuard(g);
        acct.setUnknownPositionSink(rec::onUnknownPosition);
        assertTrue(rec.startup().ok);
        for (String s : cl) lg.newStopMarket(s, Side.SELL, new BigDecimal("0.90"), "c3s-" + s + "-1-0", true);   // stop cu chua huy
        lg.freeze(60_000L);
        for (String s : cl) lg.triggerStops(s, new BigDecimal("1.04"));
        lg.readErr = true;
        now.addAndGet(1_000L);
        for (String s : cl) acct.closedOnExchange(s, FillAccounting.REASON_TRAILING, now.get());
        lg.readErr = false;
        now.addAndGet(5_000L);
        rec.confirmPendingFlat();
        rec.checkPositions();
        int ok = 0;
        for (int i = 0; i < 24; i++) if (rec.allowsEntry("Y" + i + "USDT")) ok++;
        assertEquals("24/24 leg symbol khac vao duoc", 24, ok);
        for (String s : cl) assertFalse(s, rec.allowsEntry(s));
        assertTrue(rec.blocks().toString(), rec.blocks().isEmpty());
        assertEquals("[AUSDT, BUSDT, CUSDT]", rec.symbolBlocks().toString());
        assertEquals(3, lg.openStops(null).size());
        for (int i = 0; i < 4; i++) {
            now.addAndGet(31_000L);
            rec.confirmPendingFlat();
            rec.checkPositions();
        }
        ok = 0;
        for (int i = 0; i < 24; i++) if (rec.allowsEntry("Y" + i + "USDT")) ok++;
        assertEquals(24, ok);
        for (String s : cl) assertTrue(s, rec.allowsEntry(s));
        assertTrue(rec.blocks().isEmpty());
        assertTrue(rec.symbolBlocks().isEmpty());
        assertEquals("stop cu da huy", 0, lg.openStops(null).size());
    }

    /** Gateway loi doc keo dai nhu ProofB (A1 2g). */
    static final class ErrGateway extends MockExchangeGateway {
        volatile boolean errPos;
        volatile boolean errAcct;

        @Override
        public synchronized List<com.binance.chuyennd.c3live.api.PositionInfo> positions() {
            if (errPos) throw new GatewayException(ErrorKind.OTHER, "503 gia lap", false);
            return super.positions();
        }

        @Override
        public synchronized com.binance.chuyennd.c3live.api.AccountSnapshot account() {
            if (errAcct) throw new GatewayException(ErrorKind.OTHER, "503 gia lap", false);
            return super.account();
        }
    }

    /**
     * [2h MIN-23] Hoi quy ProofB (A1_DELTA_2G): stream bao cum X dong (sai) trong khi san THAT con 100, doc loi keo dai tu luc
     * chot. 0–9': (B) chi chan X, symbol khac vao duoc; tu 10': (A) toan he (theo thoi gian, khong can doc thanh cong) + Telegram;
     * nhac lai sau 6 h; stop LUON giu. Het loi + san phang => go (A) theo luat cu.
     */
    private void proofB(boolean errPos, boolean errAcct) {
        ErrGateway eg = new ErrGateway();
        String s = "XUSDT";
        eg.setPrice(s, BigDecimal.ONE);
        LiveBookC3 book = new LiveBookC3(null, 1.0);
        assertTrue(book.reserve(s, "c3-XUSDT-1-0", 0, 1L, "BIG_DOWN", 1.0, new BigDecimal("100"), 100.0, now.get()));
        book.markSending("c3-XUSDT-1-0", now.get());
        OrderInfo o = eg.newMarketOrder(s, Side.BUY, new BigDecimal("100"), "c3-XUSDT-1-0", false);
        assertTrue(book.confirm("c3-XUSDT-1-0", o.getExecutedQty(), o.getAvgPrice().doubleValue(), o.getOrderId(), now.get()));
        book.setTrail(s, 0.08f, 1.05f, now.get());
        eg.newStopMarket(s, Side.SELL, new BigDecimal("0.95"), "c3s-XUSDT-1-1", true);
        book.setStop(s, 0.95, "c3s-XUSDT-1-1", now.get());
        List<String> al = new ArrayList<>();
        FillAccounting acct = new FillAccounting(book, eg, OrderAuditLog.dry(), null, al::add, null, now::get, null);
        Reconciler rec = new Reconciler(eg, book, acct, () -> null, al::add, null, now::get, 0.01, 2, null, null);
        OwnStopGuard g = new OwnStopGuard(eg, book, null, al::add, () -> rec::onUnknownPosition, now::get);
        rec.setStopGuard(g);
        acct.setStopGuard(g);
        acct.setUnknownPositionSink(rec::onUnknownPosition);
        assertTrue(rec.startup().ok);
        eg.errPos = errPos;
        eg.errAcct = errAcct;
        acct.closedOnExchange(s, FillAccounting.REASON_TRAILING, now.get());   // stream bao dong (sai)
        String tag = "errPos=" + errPos + " errAcct=" + errAcct;
        for (int m = 1; m <= 16; m++) {
            for (int k = 0; k < 2; k++) {
                now.addAndGet(30_000L);
                rec.confirmPendingFlat();
            }
            boolean a = rec.blocks().containsKey(Reconciler.BLOCK_UNKNOWN);
            if (m < 10) {
                assertTrue(tag + " t=" + m + "' Y vao duoc", rec.allowsEntry("YUSDT"));
                assertFalse(tag + " t=" + m, a);
                assertTrue(tag + " t=" + m + " B", rec.symbolBlocks().contains(s));
            } else {
                assertTrue(tag + " t=" + m + "' phai (A)", a);
                assertFalse(tag + " t=" + m, rec.allowsEntry("YUSDT"));
                assertFalse(rec.symbolBlocks().contains(s));
            }
            assertEquals(tag + " stop luon giu", 1, eg.openStops(s).size());
        }
        assertEquals(0, new BigDecimal("100").compareTo(eg.position(s)));
        long esc = al.stream().filter(x -> x.contains("leo thang UNKNOWN_POSITION")).count()
                + al.stream().filter(x -> x.contains("vi the LA") && x.contains(s)).count();
        assertTrue(tag + " Telegram khi len (A): " + al, esc >= 1);
        long r0 = al.stream().filter(x -> x.contains("NHAC (6h)")).count();
        now.addAndGet(FlatConfirm.GHOST_REMIND_MS);
        rec.confirmPendingFlat();
        assertEquals(tag + " nhac lai 6h", r0 + 1, al.stream().filter(x -> x.contains("NHAC (6h)")).count());
        rec.confirmPendingFlat();
        assertEquals(tag + " khong spam", r0 + 1, al.stream().filter(x -> x.contains("NHAC (6h)")).count());
        // het loi + san phang => go (A) theo luat cu (huy stop giu, 2 lan doc phang cach >= 30 s)
        eg.errPos = false;
        eg.errAcct = false;
        eg.setPosition(s, BigDecimal.ZERO, BigDecimal.ONE);
        for (int i = 0; i < 3; i++) {
            now.addAndGet(31_000L);
            rec.confirmPendingFlat();
        }
        assertTrue(tag + " " + rec.blocks(), rec.allowsEntry("YUSDT"));
        assertTrue(eg.openStops(s).isEmpty());
    }

    @Test
    public void proofBR6PositionRiskErrorEscalatesAfterWindow() {
        proofB(true, false);
    }

    @Test
    public void proofBR8BothReadErrorsEscalateAfterWindow() {
        proofB(true, true);
    }

    @Test
    public void proofBR5R7ReadOkOrAccountErrorEscalateAfterWindow() {
        proofB(false, false);
        proofB(false, true);
    }

    /** [2e] Lenh owner go cum ma: TU CHOI khi vi the != 0 (positionRisk hoac account) / symbol sai; OK khi ca hai phang. */
    @Test
    public void ghostClearRefusesWithPositionAndClearsWhenFlat() {
        Node n = new Node(false);
        n.leg("C00USDT", 0, "1.0", "100");
        n.step("C00USDT", 1.12f);
        assertTrue(n.rec.startup().ok);
        assertTrue(n.rec.ghostClear("c00usdt;rm").startsWith("REFUSED"));
        assertTrue(n.rec.ghostClear("C05USDT").startsWith("REFUSED"));
        String res = n.rec.ghostClear("C00USDT");
        assertTrue(res, res.startsWith("REFUSED") && res.contains("vi the != 0"));
        gw.positionsGlitch = true;   // positionRisk rong, account con
        res = n.rec.ghostClear("C00USDT");
        assertTrue(res, res.startsWith("REFUSED"));
        gw.positionsGlitch = false;
        gw.setPosition("C00USDT", BigDecimal.ZERO, BigDecimal.ONE);
        gw.accountPositions = MockExchangeGateway.AccountPositions.NULL;
        res = n.rec.ghostClear("C00USDT");
        assertTrue(res, res.startsWith("REFUSED"));
        assertTrue(n.book.isHolding("C00USDT"));
        assertEquals(1, gw.openStops("C00USDT").size());
        gw.accountPositions = MockExchangeGateway.AccountPositions.REAL;
        res = n.rec.ghostClear("C00USDT");
        assertTrue(res, res.startsWith("OK"));
        assertFalse(n.book.isHolding("C00USDT"));
        assertTrue(gw.openStops("C00USDT").isEmpty());
        assertTrue(n.rec.flatPending().isEmpty());
        assertTrue(alerts.stream().anyMatch(m -> m.contains("GO cum ma C00USDT")));
        assertTrue(n.rec.ghostClear("C00USDT").startsWith("REFUSED"));
    }

    /** [2e] Cum ma (phang + con stop c3s- NEW): Telegram lan dau + NHAC LAI moi 6 h toi khi go. */
    @Test
    public void ghostClusterReminderEverySixHours() {
        Node n = new Node(false);
        n.leg("C00USDT", 0, "1.0", "100");
        n.step("C00USDT", 1.12f);
        assertTrue(n.rec.startup().ok);
        gw.setPosition("C00USDT", BigDecimal.ZERO, BigDecimal.ONE);
        int a0 = alerts.size();
        for (int i = 0; i < 6; i++) {
            n.rec.checkPositions();
            now.addAndGet(GAP);
        }
        assertEquals(1L, alerts.subList(a0, alerts.size()).stream().filter(m -> m.contains("stop c3s- NEW")).count());
        assertTrue(alerts.stream().anyMatch(m -> m.contains("c3live_ghost_clear.sh C00USDT")));
        now.addAndGet(FlatConfirm.GHOST_REMIND_MS);
        n.rec.checkPositions();
        assertEquals(2L, alerts.subList(a0, alerts.size()).stream().filter(m -> m.contains("stop c3s- NEW")).count());
        now.addAndGet(GAP);
        n.rec.checkPositions();
        assertEquals("khong spam", 2L, alerts.subList(a0, alerts.size()).stream().filter(m -> m.contains("stop c3s- NEW")).count());
        assertTrue(n.rec.ghostClear("C00USDT").startsWith("OK"));
        now.addAndGet(FlatConfirm.GHOST_REMIND_MS);
        n.rec.checkPositions();
        assertEquals("da go => het nhac", 2L,
                alerts.subList(a0, alerts.size()).stream().filter(m -> m.contains("stop c3s- NEW")).count());
    }
}
