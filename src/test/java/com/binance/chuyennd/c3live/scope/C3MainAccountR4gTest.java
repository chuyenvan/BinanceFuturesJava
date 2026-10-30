package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.api.TradeFill;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.exec.C3LiveCids;
import com.binance.chuyennd.c3live.fill.FillAccounting;
import com.binance.chuyennd.c3live.fill.UserStreamEvents;
import org.junit.Assume;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.lang.reflect.Modifier;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.Assert.*;

/**
 * [V12 R4g] MINOR-A: userTrades loi (mot phan) => GIU cum (flatPending), thu lai toi 5 lan cach 30 s; thanh cong giua chung
 * => realized/khop day du. MINOR-B: gia asset phi (BNB, Aerospike) lay NGOAI khoa FillAccounting, cache 60 s. K5 production:
 * stop closePosition bi san ket thuc SAU moc GUI lenh dong c3x- => khong "STOP MAT".
 */
public class C3MainAccountR4gTest {

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

    private static String[] ledger(File root) throws Exception {
        String[] last = null;
        for (String x : Files.readAllLines(new File(root, "run/" + LiveBookC3.LEDGER_NAME).toPath())) {
            if (x.startsWith(S + ",")) last = x.split(",", -1);
        }
        return last;
    }

    /** Nua qty dong bang c3x- (userTrades LOI), nua bang stop c3s- kich; stream mat. Tra orderId lenh dong. */
    private static long partialFlat(MainAccountRig r) {
        BigDecimal c3 = r.scope.c3OpenQty(S);
        r.mock.wsSink = null;
        String cid = C3LiveCids.close(S, Math.floorDiv(r.now.get(), 60_000L), 1);
        r.book.markClosing(S, cid, "TEST_PARTIAL", r.now.get());
        r.sync();
        OrderInfo o = r.mock.newMarketOrder(S, Side.SELL, c3.divide(new BigDecimal("2")), cid, true);
        r.mock.userTradesFail.add(o.getOrderId());
        r.book.retireActiveStop(S, r.now.get());
        r.mock.triggerStops(S, new BigDecimal("1.08"));
        assertEquals(0, r.mock.position(S).signum());
        return o.getOrderId();
    }

    private static void step(MainAccountRig r) {
        r.now.addAndGet(35_000L);
        r.sync();
        r.rec.checkPositions();
    }

    @Test
    public void transientUserTradesFailure_keepsClusterThenBooksFullRealized() throws Exception {
        MainAccountRig r = armed(tmp.getRoot());
        BigDecimal c3 = r.scope.c3OpenQty(S);
        long oid = partialFlat(r);
        int guard = 0;
        while (r.merged.tradesRetryAttempts(S) < 2 && guard++ < 10) {
            step(r);
            assertTrue("dang thu lai => GIU cum", r.book.isHolding(S));
        }
        assertEquals(2, r.merged.tradesRetryAttempts(S));
        assertTrue(r.rec.flatPending().contains(S));
        r.mock.userTradesFail.remove(oid);   // userTrades hoi phuc
        step(r);
        assertFalse("doc du khop => chot cum", r.book.isHolding(S));
        assertEquals(0, r.merged.tradesRetryAttempts(S));
        String[] l = ledger(tmp.getRoot());
        assertNotNull(l);
        assertEquals("exit qty DU (ca nua c3x- loi luc dau)", 0, new BigDecimal(l[5]).compareTo(c3));
        assertTrue("realized > 0", Double.parseDouble(l[7]) > 0d);
        assertFalse(r.alerts.toString(), r.alerts.stream().anyMatch(m -> m.contains("LOI mot phan") || m.contains("KHONG doc duoc khop")));
    }

    @Test
    public void persistentFailure_fiveAttemptsThenUrgentClose() throws Exception {
        MainAccountRig r = armed(tmp.getRoot());
        partialFlat(r);
        int maxSeen = 0;
        for (int i = 0; i < 12 && r.book.isHolding(S); i++) {
            step(r);
            maxSeen = Math.max(maxSeen, r.merged.tradesRetryAttempts(S));
        }
        assertEquals("giu cum qua 4 lan loi", C3MergedGuard.TRADES_MAX_TRY - 1, maxSeen);
        assertFalse(r.book.isHolding(S));
        assertTrue(r.alerts.toString(), r.alerts.stream().anyMatch(m -> m.contains("KHAN") && m.contains("LOI mot phan")
                && m.contains("SAU " + C3MergedGuard.TRADES_MAX_TRY)));
        assertEquals("khong ghi ket qua mot phan (nhu 4f)", 0, new BigDecimal(ledger(tmp.getRoot())[5]).signum());
    }

    @Test
    public void assetPriceFetchedOutsideLock_cached60s() throws Exception {
        MainAccountRig r = armed(tmp.getRoot());
        FillAccounting acct = r.acct;
        BigDecimal q = r.book.cluster(S).get().confirmedQty;
        BigDecimal part = q.divide(new BigDecimal("4"), 8, RoundingMode.DOWN);
        AtomicInteger calls = new AtomicInteger();
        AtomicInteger underLock = new AtomicInteger();
        acct.setAssetUsdPrice(a -> {
            calls.incrementAndGet();
            if (Thread.holdsLock(acct)) underLock.incrementAndGet();
            return 600d;
        });
        List<TradeFill> f1 = new ArrayList<>();
        f1.add(new TradeFill(S, 1L, part, new BigDecimal("1.10"), r.now.get(), 701L, new BigDecimal("0.00002"), "BNB", null));
        assertEquals(1, acct.bookRecoveredExit(S, f1, false));
        assertEquals(1, calls.get());
        r.now.addAndGet(30_000L);
        List<TradeFill> f2 = new ArrayList<>();
        f2.add(new TradeFill(S, 1L, part, new BigDecimal("1.10"), r.now.get(), 702L, new BigDecimal("0.00002"), "bnb", null));
        assertEquals(1, acct.bookRecoveredExit(S, f2, false));
        assertEquals("< 60 s: dung cache", 1, calls.get());
        r.now.addAndGet(31_000L);
        List<TradeFill> f3 = new ArrayList<>();
        f3.add(new TradeFill(S, 1L, part, new BigDecimal("1.10"), r.now.get(), 703L, new BigDecimal("0.00002"), "BNB", null));
        assertEquals(1, acct.bookRecoveredExit(S, f3, false));
        assertEquals(">= 60 s: doc lai", 2, calls.get());
        assertEquals("KHONG doc gia duoi khoa FillAccounting", 0, underLock.get());
        assertFalse(Modifier.isSynchronized(FillAccounting.class.getMethod("onOrderUpdate", UserStreamEvents.OrderUpdate.class)
                .getModifiers()));
        assertFalse(Modifier.isSynchronized(FillAccounting.class.getMethod("bookRecoveredExit", String.class, List.class,
                boolean.class).getModifiers()));
        r.acct.closedOnExchange(S, "TEST", r.now.get());
        double fee = Double.parseDouble(ledger(tmp.getRoot())[8]);
        assertEquals("phi BNB quy theo gia 600 (3 khop)", 3 * 0.00002 * 600d, fee, 1e-9);
    }

    private static String algo(String sid, long e, String x) {
        return "{\"e\":\"ALGO_UPDATE\",\"E\":" + e + ",\"o\":{\"caid\":\"" + sid + "\",\"s\":\"" + S + "\",\"X\":\"" + x + "\"}}";
    }

    @Test
    public void stopExpiredAfterCloseSent_noStopLostAlert() throws Exception {
        MainAccountRig r = armed(tmp.getRoot());
        LiveBookC3.ClusterView c = r.book.cluster(S).get();
        Assume.assumeFalse("stop closePosition", c.stopQtyMode);
        String sid = c.stopClientAlgoId;
        assertNotNull(sid);
        long sent = r.now.get();
        String cid = C3LiveCids.close(S, Math.floorDiv(sent, 60_000L), 1);
        r.book.markClosing(S, cid, "TEST_K5", sent);
        LiveBookC3.ClusterView closing = r.book.cluster(S).get();
        UserStreamEvents.AlgoUpdate early = (UserStreamEvents.AlgoUpdate) UserStreamEvents.parse(algo(sid, sent - 50, "EXPIRED"));
        UserStreamEvents.AlgoUpdate after = (UserStreamEvents.AlgoUpdate) UserStreamEvents.parse(algo(sid, sent + 4, "EXPIRED"));
        assertFalse("su kien TRUOC moc gui", FillAccounting.closingAfterSend(closing, early));
        assertTrue(FillAccounting.closingAfterSend(closing, after));
        assertFalse("chua dong", FillAccounting.closingAfterSend(c, after));
        int n0 = r.alerts.size();
        r.acct.dispatch(after);   // ALGO_UPDATE toi TRUOC su kien khop c3x- (so con qty)
        assertTrue(r.book.isHolding(S));
        assertNull("stop da chet tren san => bo khoi so", r.book.cluster(S).get().stopClientAlgoId);
        assertFalse(r.alerts.subList(n0, r.alerts.size()).toString(),
                r.alerts.subList(n0, r.alerts.size()).stream().anyMatch(m -> m.contains("STOP MAT")));
    }
}
