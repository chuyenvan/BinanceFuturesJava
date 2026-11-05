package com.binance.chuyennd.c3live.fill;

import com.binance.chuyennd.c3live.api.TradeFill;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/**
 * [V12 R4p Bug2 — E2E F1] User stream rot: leg xac nhan qua REST (executor) => phi khop vao PHAI duoc bu qua userTrades theo
 * tradeId; stream toi tre / noi lai voi cung tradeId => KHONG dem 2 lan; stream binh thuong => 0 call REST them.
 * [V12 R4p Bug4] MERGED: realized khoi phuc = VWAP c3 (KHONG dung rp san gop LEGACY+c3).
 */
public class R4pCostRecoveryTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    final AtomicLong now = new AtomicLong(1_792_900_000_000L);
    MockExchangeGateway gw;
    LiveBookC3 book;
    FillAccounting acct;
    C3LiveOrderExecutor ex;
    final List<String> api = new ArrayList<>();

    @Before
    public void setUp() {
        gw = new MockExchangeGateway();
        gw.feeRate = new BigDecimal("0.0005");
        book = new LiveBookC3(new File(tmp.getRoot(), "run/c3live_book.json"), 1.0);
        acct = new FillAccounting(book, gw, new OrderAuditLog(OrderAuditLog.LIVE_TAG, l -> { }), (s, b, f, r) -> { }, a -> { }, null, now::get,
                null);
        gw.wsSink = txt -> acct.dispatch(UserStreamEvents.parse(txt));
        ex = new C3LiveOrderExecutor(gw, book, (a, ok) -> api.add(a + ":" + ok), null, now::get, ms -> now.addAndGet(ms),
                10_000L, 3, Runnable::run);
        ex.setCostRecovery(acct);
    }

    private String reserve(String sym, String px, String qty) {
        String cid = "c3-" + sym + "-100-0";
        assertTrue(book.reserve(sym, cid, 0, 100, "BIG_DOWN", Double.parseDouble(px), new BigDecimal(qty), 1.0, now.get()));
        gw.setPrice(sym, new BigDecimal(px));
        return cid;
    }

    /** F1: stream rot => xac nhan REST; sau COST_WAIT bu phi 1 lan qua userTrades; stream noi lai phat lai cung tradeId => khong cong. */
    @Test
    public void f1StreamDownFeeBackfilledOnceNoDoubleCountOnLateStream() {
        gw.holdFillEvents = true;   // stream rot: su kien khop KHONG toi
        String cid = reserve("AUSDT", "2", "100");
        ex.submit(cid);
        assertEquals(LiveBookC3.LegState.CONFIRMED, book.leg(cid).get().state);
        assertEquals("truoc fix: phi mat o day", 0d, book.account().commission, 1e-12);
        assertEquals(1, ex.pendingCostCount());
        assertEquals("chua het COST_WAIT => 0 call", 0, ex.tickCosts(now.get()));
        assertEquals(0, gw.calls("userTrades"));
        now.addAndGet(C3LiveOrderExecutor.COST_WAIT_MS);
        assertEquals(1, ex.tickCosts(now.get()));
        assertEquals("phi = 100*2*0.0005", 0.1, book.account().commission, 1e-12);
        assertEquals(0.1, book.cluster("AUSDT").get().commission, 1e-12);
        assertEquals("khop mua: realized khong doi", 0d, book.account().realized, 1e-12);
        assertEquals(0, ex.pendingCostCount());
        now.addAndGet(60_000L);
        assertEquals(0, ex.tickCosts(now.get()));
        assertEquals("khong goi lai", 1, gw.calls("userTrades"));
        gw.flushEvents();   // stream noi lai, su kien cu toi tre (cung tradeId)
        assertEquals("KHONG dem 2 lan", 0.1, book.account().commission, 1e-12);
        assertEquals(0.1, book.cluster("AUSDT").get().commission, 1e-12);
    }

    /** Stream binh thuong: stream ghi phi; executor khong xep hang bu => 0 call userTrades. */
    @Test
    public void streamUpNoExtraRestCall() {
        String cid = reserve("AUSDT", "2", "100");
        ex.submit(cid);
        assertEquals(0.1, book.account().commission, 1e-12);
        now.addAndGet(C3LiveOrderExecutor.COST_WAIT_MS * 2);
        assertEquals(0, ex.tickCosts(now.get()));
        assertEquals(0, gw.calls("userTrades"));
        assertEquals(0.1, book.account().commission, 1e-12);
    }

    /** Stream toi TRE sau ACK nhung truoc COST_WAIT: stream ghi, tick thay qty stream du => bo, 0 call. */
    @Test
    public void streamLateBeforeWaitNoRestCall() {
        gw.holdFillEvents = true;
        String cid = reserve("AUSDT", "2", "100");
        ex.submit(cid);
        assertEquals(1, ex.pendingCostCount());
        gw.flushEvents();
        assertEquals(0.1, book.account().commission, 1e-12);
        now.addAndGet(C3LiveOrderExecutor.COST_WAIT_MS);
        assertEquals(0, ex.tickCosts(now.get()));
        assertEquals(0, gw.calls("userTrades"));
        assertEquals(0, ex.pendingCostCount());
        assertEquals(0.1, book.account().commission, 1e-12);
    }

    /** userTrades chua co khop (doc-sau-ghi tre) => thu lai; lan sau co => phi 1 lan. Het COST_MAX_TRIES => bo (khong treo). */
    @Test
    public void retryThenBookOnceAndGiveUpBounded() {
        gw.holdFillEvents = true;
        String cid = reserve("AUSDT", "2", "100");
        ex.submit(cid);
        gw.userTradesEmpty = true;
        now.addAndGet(C3LiveOrderExecutor.COST_WAIT_MS);
        assertEquals(1, ex.tickCosts(now.get()));
        assertEquals(0d, book.account().commission, 1e-12);
        assertEquals(1, ex.pendingCostCount());
        gw.userTradesEmpty = false;
        now.addAndGet(C3LiveOrderExecutor.COST_WAIT_MS);
        assertEquals(1, ex.tickCosts(now.get()));
        assertEquals(0.1, book.account().commission, 1e-12);
        assertEquals(0, ex.pendingCostCount());

        String cid2 = reserve("BUSDT", "4", "10");
        ex.submit(cid2);
        gw.userTradesEmpty = true;
        for (int i = 0; i < C3LiveOrderExecutor.COST_MAX_TRIES + 3; i++) {
            now.addAndGet(C3LiveOrderExecutor.COST_WAIT_MS);
            ex.tickCosts(now.get());
        }
        assertEquals(0, ex.pendingCostCount());
        assertEquals("1 + 1 + COST_MAX_TRIES", 2 + C3LiveOrderExecutor.COST_MAX_TRIES, gw.calls("userTrades"));
    }

    /** Duong REST ghi truoc, ghi lai cung tradeId qua bookEntryCosts => 0 (idempotent). */
    @Test
    public void bookEntryCostsIdempotentByTradeId() {
        gw.holdFillEvents = true;
        String cid = reserve("AUSDT", "2", "100");
        ex.submit(cid);
        long oid = book.leg(cid).get().orderId;
        List<TradeFill> f = gw.userTrades("AUSDT", oid);
        assertEquals(1, acct.bookEntryCosts("AUSDT", f));
        assertEquals(0, acct.bookEntryCosts("AUSDT", f));
        assertEquals(0.1, book.account().commission, 1e-12);
    }

    /**
     * [Bug4] MERGED: khop thoat khoi phuc co rp san (gop LEGACY+c3) = 0,8135 khac c3 => realized so = (gia - VWAP c3) x qty;
     * rp san KHONG vao so. Duong stream: C3StreamScope.c3Rp (xem C3MainAccountR4bTest.minor3_*).
     */
    @Test
    public void bug4MergedRecoveredExitUsesC3VwapNotExchangeRp() {
        String cid = reserve("EVAAUSDT", "2", "100");
        ex.submit(cid);
        double r0 = book.account().realized;
        TradeFill exit = new TradeFill("EVAAUSDT", 777L, new BigDecimal("40"), new BigDecimal("2.05"), now.get(), 555_001L,
                new BigDecimal("0.041"), "USDT", new BigDecimal("0.8135"));
        assertEquals(1, acct.bookRecoveredExit("EVAAUSDT", Collections.singletonList(exit), true));
        assertEquals("realized = (2.05-2)*40 = 2.0 (VWAP c3), khong phai rp san 0.8135", 2.0, book.account().realized - r0, 1e-9);
        assertEquals("ghi lai cung tradeId => 0", 0, acct.bookRecoveredExit("EVAAUSDT", Collections.singletonList(exit), true));
    }
}
