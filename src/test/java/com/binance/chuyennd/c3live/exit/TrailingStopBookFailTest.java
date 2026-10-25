package com.binance.chuyennd.c3live.exit;

import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.filters.SymbolRules;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import org.junit.After;
import org.junit.Assume;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/**
 * [V12 2c MIN-6] So KHONG ghi duoc (dia day / thu muc chi doc) => trailing VAN dat stop tren san (san la nguon su that),
 * ghi ERROR + Telegram. Truoc 2c: KHONG gui => vi the da arm mat bao ve moi.
 */
public class TrailingStopBookFailTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final long T0 = 1_792_900_000_000L;
    static final String S = "C00USDT";
    File dir;

    @After
    public void restore() {
        if (dir != null) dir.setWritable(true);
    }

    @Test
    public void stopStillPlacedWhenBookCannotPersist() throws Exception {
        AtomicLong now = new AtomicLong(T0);
        MockExchangeGateway gw = new MockExchangeGateway();
        ExchangeInfo ei = C3LiveFixtures.info(4);
        gw.exchangeInfo = ei;
        dir = tmp.newFolder("run");
        LiveBookC3 book = new LiveBookC3(new File(dir, "c3live_book.json"), 1.0);
        String cid = "c3-" + S + "-1000-0";
        assertTrue(book.reserve(S, cid, 0, 1000, "BIG_DOWN", 1.0, new BigDecimal("100"), 100.0, now.get()));
        book.markSending(cid, now.get());
        gw.setPrice(S, BigDecimal.ONE);
        OrderInfo o = gw.newMarketOrder(S, Side.BUY, new BigDecimal("100"), cid, false);
        assertTrue(book.confirm(cid, o.getExecutedQty(), o.getAvgPrice().doubleValue(), o.getOrderId(), now.get()));
        book.setMeta(S, 0.5f, 0, now.get());
        assertTrue(book.healthy());
        // thu muc so thanh chi doc => persist loi
        Assume.assumeTrue("can bo quyen ghi thu muc (khong chay duoi root)", dir.setWritable(false) && !dir.canWrite());
        List<String> alerts = new ArrayList<>();
        TrailingStopManager m = TrailingStopManager.builder().gateway(gw).book(book).rules(() -> new SymbolRules(ei, T0))
                .closer((s, r) -> 0).defer((s, t, n) -> false).armHook((s, t, n) -> { }).clock(now::get)
                .alert(alerts::add).safeRetryMs(10_000L).build();
        Map<String, Float> px = new HashMap<>();
        px.put(S, 1.08f);
        gw.setPrice(S, new BigDecimal("1.08"));
        m.step(px);   // arm +8 %
        assertFalse("so da hong (ghi loi)", book.healthy());
        assertEquals("VAN dat stop tren san du so khong ghi duoc", 1, gw.calls("newStopMarket"));
        assertEquals(1, gw.openStops(S).size());
        assertNotNull("trang thai stop giu trong RAM", book.cluster(S).get().stopClientAlgoId);
        assertEquals(1, alerts.size());
        assertTrue(alerts.get(0).contains("SO KHONG GHI DUOC"));
        // doi stop van chay (khong khoang trong: dat moi roi huy cu)
        px.put(S, 1.30f);
        gw.setPrice(S, new BigDecimal("1.30"));
        m.step(px);
        assertEquals(2, gw.calls("newStopMarket"));
        assertEquals(1, gw.openStops(S).size());
    }
}
