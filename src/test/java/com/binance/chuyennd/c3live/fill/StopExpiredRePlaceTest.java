package com.binance.chuyennd.c3live.fill;

import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.exit.TrailingStopManager;
import com.binance.chuyennd.c3live.filters.SymbolRules;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.ops.KillSwitchEngine;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;


import static org.junit.Assert.*;

/**
 * [3k R1] DUONG PRODUCTION: stop c3s- bi san ket thuc (ALGO_UPDATE X=EXPIRED) khi vi the CON mo.
 * Yeu cau: bo stop khoi so NGAY (FillAccounting) de TrailingStopManager dat lai o nhip exit ke tiep (<= 10 s);
 * KHONG doi Reconciler hang gio (truoc 3k: stopClientAlgoId con => syncStop khong dat lai => vi the tran khong stop toi 1 h).
 */
public class StopExpiredRePlaceTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final long T0 = 1_792_900_000_000L;
    static final String S = "C00USDT";

    final AtomicLongBox now = new AtomicLongBox(T0);
    MockExchangeGateway gw;
    LiveBookC3 book;
    FillAccounting acct;
    ExchangeInfo ei;
    List<String> alerts;
    List<String> closed;
    TrailingStopManager trail;

    static final class AtomicLongBox {
        long v;
        AtomicLongBox(long v) { this.v = v; }
        long get() { return v; }
        void set(long x) { v = x; }
        long add(long d) { v += d; return v; }
    }

    @Before
    public void setUp() {
        gw = new MockExchangeGateway();
        gw.now = T0;
        ei = C3LiveFixtures.info(4);
        gw.exchangeInfo = ei;
        File run = new File(tmp.getRoot(), "run");
        assertTrue(run.exists() || run.mkdirs());
        book = new LiveBookC3(new File(run, "c3live_book.json"), 1.0);
        alerts = new ArrayList<>();
        closed = new ArrayList<>();
        acct = new FillAccounting(book, gw, new OrderAuditLog(OrderAuditLog.LIVE_TAG, l -> { }),
                (s, b, f, r) -> { }, alerts::add, null, now::get, (s, t, r, n) -> closed.add(s + ":" + r));
        gw.wsSink = txt -> acct.dispatch(UserStreamEvents.parse(txt));
        gw.feeRate = new BigDecimal("0.0005");
        trail = TrailingStopManager.builder().gateway(gw).book(book).rules(() -> new SymbolRules(ei, T0))
                .closer((s, r) -> 1).defer((s, t, n) -> false).armHook((s, t, n) -> { })
                .action(() -> KillSwitchEngine.Action.NONE).clock(now::get).safeRetryMs(10_000L).build();
    }

    private void open(String px, String qty) {
        assertTrue("book khong healthy: " + book.unhealthyReason(), book.healthy());
        String cid = "c3-" + S + "-100-0";
        assertTrue(book.reserve(S, cid, 0, 100, "BIG_DOWN", Double.parseDouble(px), new BigDecimal(qty),
                Double.parseDouble(px) * Double.parseDouble(qty), now.get()));
        book.markSending(cid, now.get());
        gw.setPrice(S, new BigDecimal(px));
        OrderInfo o = gw.newMarketOrder(S, Side.BUY, new BigDecimal(qty), cid, false);
        // FillAccounting (wsSink) da xac nhan qua stream; neu chua (khong co sink) thi xac nhan tay
        if (!book.leg(cid).map(l -> l.state == LiveBookC3.LegState.CONFIRMED).orElse(false)) {
            assertTrue(book.confirm(cid, o.getExecutedQty(), o.getAvgPrice().doubleValue(), o.getOrderId(), now.get()));
        }
        book.setMeta(S, 0.5f, 0, now.get());
    }

    private Map<String, Float> px(float v) {
        Map<String, Float> m = new HashMap<>();
        m.put(S, v);
        return m;
    }

    /** Mo cum + arm trailing de dat stop closePosition tren san; tra ve cid stop. */
    private String armAndPlace() {
        open("1.0", "100");
        trail.step(px(1.08f));
        List<OrderInfo> st = gw.openStops(S);
        assertEquals(1, st.size());
        assertTrue(st.get(0).isClosePosition());
        assertEquals(book.cluster(S).get().stopClientAlgoId, st.get(0).getClientOrderId());
        return st.get(0).getClientOrderId();
    }

    @Test
    public void expiredWhilePositionOpenRetiresAndTrailingReplaces() {
        String old = armAndPlace();
        gw.exchangeEndStop(old, "EXPIRED");
        // FillAccounting bo stop khoi so ngay, KHONG dua vao orphanStops (stop da chet tren san)
        LiveBookC3.ClusterView c = book.cluster(S).get();
        assertNull("stop active phai duoc go", c.stopClientAlgoId);
        assertTrue("stop da chet khong nam trong orphanStops", c.orphanStops.isEmpty());
        assertTrue("phai bao Telegram: " + alerts, alerts.stream().anyMatch(m -> m.contains("STOP MAT") && m.contains(old)));
        // nhip exit ke tiep (<= 10 s) dat lai stop
        trail.step(px(1.08f));
        List<OrderInfo> st = gw.openStops(S);
        assertEquals(1, st.size());
        assertNotEquals("stop moi, khong phai cid cu", old, st.get(0).getClientOrderId());
        assertTrue(st.get(0).isClosePosition());
        assertEquals(book.cluster(S).get().stopClientAlgoId, st.get(0).getClientOrderId());
    }

    @Test
    public void expiredAfterPositionClosedDoesNotPlaceNewStop() {
        String old = armAndPlace();
        book.addExitFill(S, new BigDecimal("100"), 1.05d, now.get());   // so: da dong du vi the
        gw.exchangeEndStop(old, "EXPIRED");
        assertTrue("vi the da phang => khong coi la mat stop: " + alerts, alerts.isEmpty());
        assertEquals("stop van o nguyen trang thai so (cho closedOnExchange)", old, book.cluster(S).get().stopClientAlgoId);
        trail.step(px(1.08f));
        assertEquals("khong dat stop moi khi da phang", 1, gw.calls("newStopMarket"));
        assertEquals(old, book.cluster(S).get().stopClientAlgoId);
    }

    @Test
    public void canceledPendingStopIsCleared() {
        open("1.0", "100");
        book.setPendingStop(S, "c3s-" + S + "-999-0", 0.96d, false, now.get());
        gw.newStopMarket(S, Side.SELL, null, new BigDecimal("0.96"), "c3s-" + S + "-999-0", true);
        gw.exchangeEndStop("c3s-" + S + "-999-0", "CANCELED");
        assertNull(book.cluster(S).get().pendingStopCid);
        assertTrue(alerts.stream().anyMatch(m -> m.contains("PENDING")));
    }
}
