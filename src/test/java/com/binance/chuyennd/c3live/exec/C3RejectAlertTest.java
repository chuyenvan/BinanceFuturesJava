package com.binance.chuyennd.c3live.exec;

import com.binance.chuyennd.c3live.alert.C3AlertThrottle;
import com.binance.chuyennd.c3live.api.ClientSideRefusal;
import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import org.junit.Test;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/** [W3A muc 3 A-06] Telegram thua khi san tu choi lenh vao c3 (1 lan / symbol / 30'). */
public class C3RejectAlertTest {

    static final class Refusal extends GatewayException implements ClientSideRefusal {
        Refusal() {
            super(ErrorKind.FILTER, "pham vi c3 tu choi (gia lap w3a)", true);
        }
    }

    final AtomicLong now = new AtomicLong(1_000_000L);
    final List<String> alerts = new ArrayList<>();

    private int place(MockExchangeGateway gw, C3LiveOrderExecutor ex, LiveBookC3 book, String sym, int leg, GatewayException e) {
        gw.failNext("newMarketOrder", e);
        String cid = "c3-" + sym + "-" + (1000 + leg) + "-0";
        book.reserve(sym, cid, 0, 1, "X", 1.0, BigDecimal.TEN, 10.0, now.get());
        ex.submit(cid);
        return alerts.size();
    }

    private C3LiveOrderExecutor exec(MockExchangeGateway gw, LiveBookC3 book) {
        return new C3LiveOrderExecutor(gw, book, null, null, now::get, ms -> now.addAndGet(ms), 10_000L, 3, Runnable::run);
    }

    @Test
    public void throttle_1lanMoiSymbolMoiCuaSo() {
        C3AlertThrottle t = new C3AlertThrottle(30 * 60_000L);
        assertEquals(0L, t.tryAcquire("A", 0L));
        assertEquals(-1L, t.tryAcquire("A", 60_000L));
        assertEquals(-1L, t.tryAcquire("A", 29 * 60_000L));
        assertEquals(0L, t.tryAcquire("B", 60_000L));
        assertEquals(2L, t.tryAcquire("A", 30 * 60_000L));
        assertEquals(30 * 60_000L, C3AlertThrottle.windowFromMinutes(null, 30));
        assertEquals(5 * 60_000L, C3AlertThrottle.windowFromMinutes(" 5 ", 30));
        assertEquals(30 * 60_000L, C3AlertThrottle.windowFromMinutes("abc", 30));
        assertEquals(30 * 60_000L, C3AlertThrottle.windowFromMinutes("0", 30));
        assertTrue(C3AlertThrottle.enabled(null));
        assertFalse(C3AlertThrottle.enabled("FALSE"));
    }

    @Test
    public void rejectSan_guiThua_khongInMaAm() {
        MockExchangeGateway gw = new MockExchangeGateway();
        LiveBookC3 book = new LiveBookC3(null, 1.0);
        C3LiveOrderExecutor ex = exec(gw, book);
        ex.setRejectAlert(alerts::add, 30 * 60_000L);
        assertEquals(1, place(gw, ex, book, "AUSDT", 1,
                new GatewayException(ErrorKind.INSUFFICIENT_MARGIN, 400, -2019, "margin", true, 0L, null)));
        String m = alerts.get(0);
        assertTrue(m, m.startsWith("[C3-LIVE] REJECT") && m.contains("AUSDT") && m.contains("ma_san=2019"));
        assertFalse("khong khop regex REJECT_SINCE cua golive_monitor", m.contains("-2019") || m.contains("code=")
                || m.contains("-4164") || m.contains("[C3-LIVE-EXEC]") || m.contains("KHONG khop"));
        now.addAndGet(60_000L);
        assertEquals("cung symbol trong 30' => nen", 1, place(gw, ex, book, "AUSDT", 2,
                new GatewayException(ErrorKind.FILTER, 400, -4164, "notional", true, 0L, null)));
        assertEquals("symbol khac => gui", 2, place(gw, ex, book, "BUSDT", 3,
                new GatewayException(ErrorKind.FILTER, 400, -4164, "notional", true, 0L, null)));
        now.addAndGet(30 * 60_000L);
        assertEquals(3, place(gw, ex, book, "AUSDT", 4,
                new GatewayException(ErrorKind.FILTER, 400, -4164, "notional", true, 0L, null)));
        assertTrue(alerts.get(2), alerts.get(2).contains("1 lan tu choi khac bi nen"));
        assertEquals(3L, ex.rejectAlertsSent());
    }

    @Test
    public void macDinhTat_vaTuChoiPhiaClient_khongGui() {
        MockExchangeGateway gw = new MockExchangeGateway();
        LiveBookC3 book = new LiveBookC3(null, 1.0);
        C3LiveOrderExecutor off = exec(gw, book);
        assertEquals(0, place(gw, off, book, "AUSDT", 1,
                new GatewayException(ErrorKind.INSUFFICIENT_MARGIN, 400, -2019, "margin", true, 0L, null)));
        C3LiveOrderExecutor on = exec(gw, book);
        on.setRejectAlert(alerts::add, 30 * 60_000L);
        assertEquals(0, place(gw, on, book, "CUSDT", 2, new Refusal()));
        assertFalse(book.isHolding("CUSDT"));
    }
}
