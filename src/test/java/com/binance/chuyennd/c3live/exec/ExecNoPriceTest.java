package com.binance.chuyennd.c3live.exec;

import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import org.junit.Test;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/**
 * [3j R1/R2/R4] Duong PRODUCTION {@link C3LiveOrderExecutor} + {@link FillPriceResolver}: ACK MARKET {@code FILLED}
 * khong {@code avgPrice} (that 10-28) KHONG duoc lam mat qty khoi so.
 */
public class ExecNoPriceTest {

    private final MockExchangeGateway gw = new MockExchangeGateway();
    private final AtomicLong now = new AtomicLong(1_792_900_000_000L);
    private final List<String> prices = new ArrayList<>();

    private C3LiveOrderExecutor exec(LiveBookC3 book, FillPriceResolver resolver) {
        C3LiveOrderExecutor ex = new C3LiveOrderExecutor(gw, book, null, null, now::get, ms -> now.addAndGet(ms),
                10_000L, 3, Runnable::run);
        if (resolver != null) ex.setPriceResolver(resolver);
        ex.setPriceObserver((t, s, c, p, src) -> prices.add(t + ":" + s + ":" + c + ":" + p + ":" + src));
        return ex;
    }

    private LiveBookC3 book() {
        return new LiveBookC3(null, 1.0);
    }

    private void reserve(LiveBookC3 b, String sym, String cid, String qty) {
        assertTrue(b.reserve(sym, cid, 0, 1, "CANARY", 1310.00, new BigDecimal(qty), 19.66, now.get()));
    }

    /** T6: duong production, ACK khong avgPrice, khong stream, khong query, khong trades => so GIU qty voi gia TAM. */
    @Test
    public void t6ProductionAckWithoutPriceKeepsQtyWithProvisionalPrice() {
        gw.setPrice("ZECUSDT", new BigDecimal("1310.36"));
        gw.ackWithoutAvgPrice = true;
        gw.queryOrderWithoutAvgPrice = true;
        gw.userTradesEmpty = true;
        LiveBookC3 b = book();
        reserve(b, "ZECUSDT", "c3-ZECUSDT-1-0", "0.015");
        exec(b, null).place("c3-ZECUSDT-1-0");
        LiveBookC3.LegView lv = b.leg("c3-ZECUSDT-1-0").orElse(null);
        assertNotNull("leg KHONG duoc bi xoa (R1)", lv);
        assertEquals(LiveBookC3.LegState.CONFIRMED, lv.state);
        assertEquals(0, new BigDecimal("0.015").compareTo(lv.execQty));
        assertTrue("gia tam", lv.pxProvisional);
        assertEquals("gia tam = mark", 1310.36, lv.avgPx, 1e-9);
        assertEquals("qty tren so", 0, new BigDecimal("0.015").compareTo(b.cluster("ZECUSDT").get().confirmedQty));
        assertTrue("phai co su kien PX_PROVISIONAL: " + prices, prices.stream().anyMatch(x -> x.startsWith("PX_PROVISIONAL:")));
        assertEquals("khong duoc huy", 0, gw.calls("cancelOrder"));
    }

    /** T6b: ACK khong gia nhung queryOrder co gia => so ghi gia THAT (khong phai gia tam). */
    @Test
    public void t6bProductionAckWithoutPriceQueryOrderGivesRealPrice() {
        gw.setPrice("ZECUSDT", new BigDecimal("1310.36"));
        gw.ackWithoutAvgPrice = true;
        gw.queryOrderWithoutAvgPrice = false;
        LiveBookC3 b = book();
        reserve(b, "ZECUSDT", "c3-ZECUSDT-1-0", "0.015");
        exec(b, null).place("c3-ZECUSDT-1-0");
        LiveBookC3.LegView lv = b.leg("c3-ZECUSDT-1-0").orElseThrow(AssertionError::new);
        assertEquals(LiveBookC3.LegState.CONFIRMED, lv.state);
        assertFalse(lv.pxProvisional);
        assertEquals(1310.36, lv.avgPx, 1e-9);
        assertTrue("nguon QUERY: " + prices, prices.stream().anyMatch(x -> x.startsWith("PX_RESOLVED:") && x.endsWith(":QUERY")));
        assertTrue("khong duoc co gia tam", prices.stream().noneMatch(x -> x.startsWith("PX_PROVISIONAL:")));
    }

    /** T4 (R4): ACK FILLED executedQty=0 => KHONG huy; tra san thay FILLED qty => leg CONFIRMED. */
    @Test
    public void t4AckFilledExecZeroRequeryKeepsLeg() {
        gw.setPrice("ZECUSDT", new BigDecimal("1310.36"));
        gw.ackExecZero = true;
        LiveBookC3 b = book();
        reserve(b, "ZECUSDT", "c3-ZECUSDT-1-0", "0.015");
        exec(b, null).place("c3-ZECUSDT-1-0");
        LiveBookC3.LegView lv = b.leg("c3-ZECUSDT-1-0").orElse(null);
        assertNotNull("leg phai con (R4: executedQty=0 KHONG duoc huy)", lv);
        assertEquals(LiveBookC3.LegState.CONFIRMED, lv.state);
        assertEquals(0, new BigDecimal("0.015").compareTo(lv.execQty));
        assertTrue("phai tra san", gw.calls("queryOrder") >= 1);
        assertEquals("khong duoc gui lai", 1, gw.calls("newMarketOrder"));
        assertEquals("khong duoc huy giu cho", 0, gw.calls("cancelOrder"));
    }

    /** R4: san noi CANCELED + executedQty=0 => huy giu cho (truong hop DUY NHAT duoc huy). */
    @Test
    public void cancelWithExecZeroStillCancels() {
        gw.setPrice("XUSDT", new BigDecimal("1.0"));
        LiveBookC3 b = book();
        reserve(b, "XUSDT", "c3-XUSDT-1-0", "10");
        exec(b, null).apply("c3-XUSDT-1-0", OrderInfo.builder().symbol("XUSDT").clientOrderId("c3-XUSDT-1-0").orderId(5L)
                .status(com.binance.chuyennd.c3live.api.OrderStatus.CANCELED).executedQty(BigDecimal.ZERO)
                .origQty(BigDecimal.TEN).build());
        assertFalse("CANCELED + exec 0 => huy giu cho", b.leg("c3-XUSDT-1-0").isPresent());
    }

    /** R1 o tang so: confirm(execQty>0, avgPx=0) KHONG duoc huy/khong lam mat leg. */
    @Test
    public void bookConfirmKeepsQuantityWhenPriceMissing() {
        LiveBookC3 b = book();
        reserve(b, "ZECUSDT", "c3-ZECUSDT-1-0", "0.015");
        assertTrue(b.markSending("c3-ZECUSDT-1-0", now.get()));
        assertFalse("px<=0 khong duoc coi la khop", b.confirm("c3-ZECUSDT-1-0", new BigDecimal("0.015"), 0.0, 1L, now.get()));
        LiveBookC3.LegView lv = b.leg("c3-ZECUSDT-1-0").orElse(null);
        assertNotNull("leg phai con", lv);
        assertEquals(LiveBookC3.LegState.SENDING, lv.state);
        // roi ghi gia tam => qty vao so
        assertTrue(b.confirmProvisional("c3-ZECUSDT-1-0", new BigDecimal("0.015"), 1310.36, 1L, now.get()));
        assertTrue(b.leg("c3-ZECUSDT-1-0").get().pxProvisional);
        assertEquals(0, new BigDecimal("0.015").compareTo(b.leg("c3-ZECUSDT-1-0").get().execQty));
        // gia that den => bo co
        assertTrue(b.correctPrice("c3-ZECUSDT-1-0", 1310.40, now.get()));
        assertFalse(b.leg("c3-ZECUSDT-1-0").get().pxProvisional);
        assertEquals(1310.40, b.leg("c3-ZECUSDT-1-0").get().avgPx, 1e-12);
    }

    /** R2 thu tu: (a) stream truoc, (b) queryOrder, (c) userTrades, het thi NONE — trong ngan sach 3 s. */
    @Test
    public void resolverOrderStreamThenQueryThenTradesThenNone() {
        // (a) stream
        FillPriceResolver r = new FillPriceResolver(now::get, ms -> now.addAndGet(ms), (a, ok) -> { });
        r.observe("cid1", 11L, new BigDecimal("100.5"), new BigDecimal("100"));
        FillPriceResolver.Resolved a = r.resolve(gw, "ZECUSDT", "cid1", 11L);
        assertEquals(FillPriceResolver.Source.STREAM_AP, a.source);
        assertEquals(100.5, a.px, 1e-12);

        // (b) queryOrder
        gw.setPrice("ZECUSDT", new BigDecimal("100"));
        OrderInfo o = gw.newMarketOrder("ZECUSDT", com.binance.chuyennd.c3live.api.Side.BUY, BigDecimal.ONE, "cid2", false);
        FillPriceResolver r2 = new FillPriceResolver(now::get, ms -> now.addAndGet(ms), (a1, ok) -> { });
        FillPriceResolver.Resolved b = r2.resolve(gw, "ZECUSDT", "cid2", o.getOrderId());
        assertEquals(FillPriceResolver.Source.QUERY, b.source);
        assertEquals(100d, b.px, 1e-12);

        // (c) userTrades
        gw.queryOrderWithoutAvgPrice = true;
        FillPriceResolver r3 = new FillPriceResolver(now::get, ms -> now.addAndGet(ms), (a2, ok) -> { });
        FillPriceResolver.Resolved c = r3.resolve(gw, "ZECUSDT", "cid2", o.getOrderId());
        assertEquals(FillPriceResolver.Source.TRADES, c.source);
        assertEquals(100d, c.px, 1e-12);

        // khong nguon nao
        gw.userTradesEmpty = true;
        FillPriceResolver r4 = new FillPriceResolver(now::get, ms -> now.addAndGet(ms), (a3, ok) -> { });
        long t0 = now.get();
        FillPriceResolver.Resolved d = r4.resolve(gw, "ZECUSDT", "cid2", o.getOrderId());
        assertEquals(FillPriceResolver.Source.NONE, d.source);
        assertEquals(0d, d.px, 0d);
        assertTrue("tong ngan sach <= 3 s: " + (now.get() - t0), now.get() - t0 <= FillPriceResolver.DEFAULT_BUDGET_MS);
    }

    /** Gia binh quan gia quyen cua userTrades (2 khop). */
    @Test
    public void weightedAverageOfTrades() {
        List<com.binance.chuyennd.c3live.api.TradeFill> l = new ArrayList<>();
        l.add(new com.binance.chuyennd.c3live.api.TradeFill("X", 1L, new BigDecimal("1"), new BigDecimal("100"), 1L));
        l.add(new com.binance.chuyennd.c3live.api.TradeFill("X", 1L, new BigDecimal("3"), new BigDecimal("110"), 2L));
        assertEquals(107.5d, FillPriceResolver.weightedAvg(l), 1e-12);
    }
}
