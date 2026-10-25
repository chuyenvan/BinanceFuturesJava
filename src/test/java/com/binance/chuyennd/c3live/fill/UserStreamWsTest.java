package com.binance.chuyennd.c3live.fill;

import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import org.junit.Test;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.BooleanSupplier;

import static org.junit.Assert.*;

/**
 * [V12 C7] UserStream qua websocket THAT (okhttp) toi server gia JDK: listenKey tai khoan con, ORDER_TRADE_UPDATE =>
 * so (qty/avgPrice/phi/orderId), mat stream => WARN + fallback REST + ket noi lai co backoff + bu REST 1 lan,
 * listenKeyExpired => listenKey MOI.
 */
public class UserStreamWsTest {

    static String buyFill(String sym, String cid, String qty, String px, String fee) {
        return "{\"e\":\"ORDER_TRADE_UPDATE\",\"E\":1,\"T\":1,\"o\":{\"s\":\"" + sym + "\",\"c\":\"" + cid
                + "\",\"S\":\"BUY\",\"o\":\"MARKET\",\"ot\":\"MARKET\",\"x\":\"TRADE\",\"X\":\"FILLED\",\"i\":777,\"l\":\"" + qty
                + "\",\"L\":\"" + px + "\",\"z\":\"" + qty + "\",\"ap\":\"" + px + "\",\"n\":\"" + fee
                + "\",\"N\":\"USDT\",\"rp\":\"0\",\"R\":false,\"T\":1}}";
    }

    static boolean waitFor(BooleanSupplier c, long ms) throws InterruptedException {
        long end = System.currentTimeMillis() + ms;
        while (System.currentTimeMillis() < end) {
            if (c.getAsBoolean()) return true;
            Thread.sleep(20);
        }
        return c.getAsBoolean();
    }

    @Test
    public void streamFillsDropFallbackReconnectAndListenKeyExpiry() throws Exception {
        try (FakeWsServer srv = new FakeWsServer()) {
            MockExchangeGateway gw = new MockExchangeGateway();
            LiveBookC3 book = new LiveBookC3(null, 1.0);
            assertTrue(book.reserve("AUSDT", "c3-AUSDT-10-0", 0, 10, "BIG_DOWN", 2.0, new BigDecimal("50"), 100.0, 1L));
            book.markSending("c3-AUSDT-10-0", 1L);
            List<String> fills = Collections.synchronizedList(new ArrayList<>());
            List<String> alerts = Collections.synchronizedList(new ArrayList<>());
            FillAccounting acct = new FillAccounting(book, gw, new OrderAuditLog(OrderAuditLog.LIVE_TAG, s -> { }),
                    (s, b, f, r) -> fills.add(s + ":" + b + ":" + f + ":" + r), alerts::add, null, System::currentTimeMillis, null);
            AtomicInteger fallback = new AtomicInteger();
            UserStream us = new UserStream(gw, UserStream.okHttp(0), Collections.singletonList(
                    "ws://127.0.0.1:" + srv.port() + "/ws/{key}"), acct, fallback::incrementAndGet, alerts::add, null,
                    System::currentTimeMillis, 5_000L, 1_000L, 2_000L, 1_000L);
            us.start();
            try {
                assertTrue("ket noi", waitFor(us::isConnected, 5_000L));
                assertEquals("/ws/mockListenKey1", srv.paths.get(0));
                // fill qua stream => so xac nhan qty/gia/orderId, phi, C2 1 lan
                assertTrue(srv.send(buyFill("AUSDT", "c3-AUSDT-10-0", "50", "2.04", "0.051")));
                assertTrue(waitFor(() -> book.leg("c3-AUSDT-10-0").get().state == LiveBookC3.LegState.CONFIRMED, 3_000L));
                LiveBookC3.LegView lv = book.leg("c3-AUSDT-10-0").get();
                assertEquals(0, new BigDecimal("50").compareTo(lv.execQty));
                assertEquals(2.04, lv.avgPx, 1e-12);
                assertEquals(777L, lv.orderId);
                assertEquals(0.051, book.cluster("AUSDT").get().commission, 1e-12);
                assertTrue("onFill (C2) sau confirm", waitFor(() -> fills.size() == 1, 2_000L));
                assertEquals(Collections.singletonList("AUSDT:true:2.04:2.0"), new ArrayList<>(fills));
                // mat stream => fallback REST + ket noi lai + bu REST 1 lan
                int fb0 = fallback.get();
                srv.refuse = true;   // mat lau: ket noi lai bi tu choi
                srv.drop();
                assertTrue(waitFor(() -> !us.isConnected(), 3_000L));
                assertTrue("fallback REST khi mat", waitFor(() -> fallback.get() > fb0, 8_000L));
                assertTrue("Telegram mat stream", waitFor(() -> alerts.stream().anyMatch(a -> a.contains("mat user stream")), 3_000L));
                assertEquals("chua bu REST khi chua ket noi lai", 0, us.catchUpCount());
                srv.refuse = false;
                assertTrue("ket noi lai", waitFor(() -> us.isConnected() && srv.accepted >= 2, 10_000L));
                assertTrue("bu REST 1 lan sau khi ket noi lai", waitFor(() -> us.catchUpCount() == 1, 3_000L));
                assertEquals("cung listenKey khi chi mat ket noi", 1, gw.calls("startUserStream"));
                // listenKeyExpired => listenKey moi
                assertTrue(srv.send("{\"e\":\"listenKeyExpired\",\"E\":2,\"listenKey\":\"x\"}"));
                assertTrue(waitFor(() -> gw.calls("startUserStream") == 2 && us.isConnected() && srv.accepted >= 3, 8_000L));
                assertEquals("/ws/mockListenKey2", srv.paths.get(srv.paths.size() - 1));
            } finally {
                us.stop();
            }
        }
    }

    @Test
    public void connectFailureRotatesUrlAndBacksOff() {
        MockExchangeGateway gw = new MockExchangeGateway();
        LiveBookC3 book = new LiveBookC3(null, 1.0);
        AtomicLong clk = new AtomicLong(0L);
        FillAccounting acct = new FillAccounting(book, gw, new OrderAuditLog(OrderAuditLog.LIVE_TAG, s -> { }), null, null,
                null, clk::get, null);
        List<String> urls = new ArrayList<>();
        UserStream.Connector failing = (url, l) -> {
            urls.add(url);
            l.onClosed("failure ConnectException");
            return () -> { };
        };
        AtomicInteger fb = new AtomicInteger();
        UserStream us = new UserStream(gw, failing, UserStream.parseUrls("wss://a/x/{key},wss://b/y"), acct, fb::incrementAndGet,
                null, null, clk::get, 5_000L, 1_000L, 8_000L, 0L);
        for (int i = 0; i < 40; i++) {
            us.tick(clk.get());
            clk.addAndGet(1_000L);
        }
        assertTrue(urls.size() >= 3);
        assertEquals("wss://a/x/mockListenKey1", urls.get(0));
        assertEquals("doi URL khi ket noi that bai", "wss://b/y/mockListenKey1", urls.get(1));
        assertTrue("backoff 1,2,4,8,8.. s: it hon 1 lan/giay (" + urls.size() + ")", urls.size() <= 10);
        assertTrue("fallback REST chay khi mat", fb.get() >= 3);
        assertEquals(UserStream.State.DISCONNECTED, us.state());
    }
}
