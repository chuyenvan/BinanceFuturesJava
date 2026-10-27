package com.binance.chuyennd.c3live.risk;

import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.rate.RateGuard;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.ops.KillSwitchEngine;
import org.junit.Test;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.Assert.*;

/** [V12 C8/C6] FLATTEN / dong cum: reduce-only, idempotent qua timeout, huy stop, chia lo, Telegram; equity min(pilot,tmb). */
public class C3LiveFlattenerTest {

    static final class TimeoutOnceGw extends MockExchangeGateway {
        boolean timeoutAfterFill = true;
        int sells;

        @Override
        public synchronized OrderInfo newMarketOrder(String s, Side side, BigDecimal q, String cid, boolean ro) {
            OrderInfo o = super.newMarketOrder(s, side, q, cid, ro);
            if (side == Side.SELL) {
                sells++;
                assertTrue("lenh dong phai reduce-only", ro);
                if (timeoutAfterFill) {
                    timeoutAfterFill = false;
                    throw new GatewayException(ErrorKind.TIMEOUT_UNKNOWN_STATE, 0, 0, "timeout", false, 0L, null);
                }
            }
            return o;
        }
    }

    private static void open(MockExchangeGateway gw, LiveBookC3 b, String sym, long now) {
        gw.setPrice(sym, BigDecimal.ONE);
        String cid = "c3-" + sym + "-1-0";
        b.reserve(sym, cid, 0, 1, "X", 1.0, BigDecimal.TEN, 10.0, now);
        OrderInfo o = gw.newMarketOrder(sym, Side.BUY, BigDecimal.TEN, cid, false);
        b.confirm(cid, o.getExecutedQty(), 1.0, o.getOrderId(), now);
    }

    @Test
    public void closeTimeoutQueriesInsteadOfResendThenCancelsStop() {
        TimeoutOnceGw gw = new TimeoutOnceGw();
        AtomicLong now = new AtomicLong(1_000_000L);
        LiveBookC3 b = new LiveBookC3(null, 1.0);
        open(gw, b, "AUSDT", now.get());
        gw.newStopMarket("AUSDT", Side.SELL, new BigDecimal("0.9"), "c3s-AUSDT-1", true);
        b.setStop("AUSDT", 0.9, "c3s-AUSDT-1", now.get());
        AtomicReference<KillSwitchEngine.Action> act = new AtomicReference<>(KillSwitchEngine.Action.NONE);
        List<String> alerts = new ArrayList<>();
        C3LiveFlattener f = new C3LiveFlattener(gw, b, act::get, alerts::add, null, now::get, 5, 10_000L, 10_000L);
        assertEquals(1, f.closeCluster("AUSDT", "TIME_STOP"));
        // timeout sau khi khop: cum chua xoa, closeCid giu
        assertTrue(b.isClosing("AUSDT"));
        assertNotNull(b.cluster("AUSDT").get().closeCid);
        now.addAndGet(1_000L);
        assertEquals(0, f.closeCluster("AUSDT", "TIME_STOP"));   // tra san: da khop + vi the 0 => xong, KHONG gui lai
        assertEquals(1, gw.sells);
        assertFalse(b.isHolding("AUSDT"));
        assertEquals(0, gw.openStops("AUSDT").size());
        assertTrue(alerts.isEmpty());   // closeCluster le khong phai FLATTEN
    }

    @Test
    public void flattenPacingAndAlertsAndSkipsUnresolved() {
        MockExchangeGateway gw = new MockExchangeGateway();
        AtomicLong now = new AtomicLong(1_000_000L);
        LiveBookC3 b = new LiveBookC3(null, 1.0);
        for (int i = 0; i < 12; i++) open(gw, b, "S" + i + "USDT", now.get());
        b.reserve("PUSDT", "c3-PUSDT-1-0", 0, 1, "X", 1.0, BigDecimal.ONE, 1.0, now.get());   // leg treo
        AtomicReference<KillSwitchEngine.Action> act = new AtomicReference<>(KillSwitchEngine.Action.NO_NEW_ENTRY);
        List<String> alerts = new ArrayList<>();
        C3LiveFlattener f = new C3LiveFlattener(gw, b, act::get, alerts::add, null, now::get, 5, 10_000L, 10_000L);
        assertEquals(0, f.step());   // khong FLATTEN => khong lam gi
        act.set(KillSwitchEngine.Action.FLATTEN);
        assertEquals(5, f.step());
        now.addAndGet(5_000L);
        assertEquals(0, f.step());   // con trong cua so 10 s
        now.addAndGet(5_001L);
        assertEquals(5, f.step());
        now.addAndGet(10_001L);
        assertEquals(2, f.step());
        assertEquals(1, b.openCount());   // PUSDT con leg treo => cho
        b.cancel("c3-PUSDT-1-0", "test", now.get());
        f.step();
        assertEquals(0, b.openCount());
        assertEquals(1, alerts.stream().filter(m -> m.contains("FLATTEN: dong")).count());
        assertEquals(1, alerts.stream().filter(m -> m.contains("FLATTEN xong")).count());
        assertEquals(0, gw.positions().size());
    }

    @Test
    public void equityCapitalIsMinPilotTmbAndCached() {
        MockExchangeGateway gw = new MockExchangeGateway();
        AtomicLong now = new AtomicLong(0L);
        List<String> api = new ArrayList<>();
        C3LiveEquity e = new C3LiveEquity(gw, 10_000d, 60_000L, now::get, (a, ok) -> api.add(a + ":" + ok));
        gw.accountSnapshot = snap("12000");
        assertEquals(12_000d, e.totalMarginBalance(), 0);
        assertEquals(10_000d, e.capital(), 0);   // khong phinh theo lai
        gw.accountSnapshot = snap("9000");
        now.addAndGet(59_000L);
        assertEquals(10_000d, e.capital(), 0);   // cache <= 60 s
        now.addAndGet(1_000L);
        assertEquals(9_000d, e.capital(), 0);
        assertEquals(2, gw.calls("account"));
        gw.failNext("account", new GatewayException(ErrorKind.TIMEOUT_UNKNOWN_STATE, "t", false));
        now.addAndGet(60_000L);
        assertNull(e.capital());   // loi => null, khong dung so cu qua ttl
        assertTrue(api.contains("account:false"));
        // ttl > 60 s bi kep ve 60 s
        C3LiveEquity e2 = new C3LiveEquity(gw, 10_000d, 600_000L, now::get, null);
        gw.accountSnapshot = snap("8000");
        assertEquals(8_000d, e2.capital(), 0);
        gw.accountSnapshot = snap("7000");
        now.addAndGet(60_000L);
        assertEquals(7_000d, e2.capital(), 0);
    }

    /**
     * [2c MAJ-2 / 2d MAJ-2b] positionRisk thieu symbol => KHONG huy stop/xoa cum cho toi khi du (a) 3 lan doc cach >= 30 s
     * + (b) account phang + (c) 0 stop c3s- NEW.
     */
    @Test
    public void positionsMissingDoesNotFinalizeUntilConfirmed() {
        MockExchangeGateway gw = new MockExchangeGateway();
        AtomicLong now = new AtomicLong(1_000_000L);
        LiveBookC3 b = new LiveBookC3(null, 1.0);
        open(gw, b, "AUSDT", now.get());   // chua arm => khong stop
        C3LiveFlattener f = new C3LiveFlattener(gw, b, () -> KillSwitchEngine.Action.NONE, null, null, now::get, 5, 10_000L,
                10_000L);
        gw.setPosition("AUSDT", BigDecimal.ZERO, BigDecimal.ONE);   // phang that (vd owner dong tay)
        assertEquals(0, f.closeCluster("AUSDT", "TIME_STOP"));   // lan 1
        assertTrue("1 lan: giu cum", b.isHolding("AUSDT"));
        now.addAndGet(10_000L);
        assertEquals(0, f.closeCluster("AUSDT", "TIME_STOP"));   // < 30 s: khong tinh
        now.addAndGet(20_000L);
        assertEquals(0, f.closeCluster("AUSDT", "TIME_STOP"));   // lan 2
        assertTrue("2 lan: van giu", b.isHolding("AUSDT"));
        now.addAndGet(30_000L);
        assertEquals(0, f.closeCluster("AUSDT", "TIME_STOP"));   // lan 3 + account phang + 0 stop
        assertFalse("du 3 dieu kien: phang", b.isHolding("AUSDT"));
        assertEquals("khong gui lenh ban khi san noi phang", 0, gw.calls("newMarketOrder") - 1);
    }

    /** [2d MAJ-2b] con stop c3s- NEW => Flattener KHONG bao gio ket luan phang (du positionRisk + account deu phang). */
    @Test
    public void openOwnStopKeepsClusterInFlattener() {
        MockExchangeGateway gw = new MockExchangeGateway();
        AtomicLong now = new AtomicLong(1_000_000L);
        LiveBookC3 b = new LiveBookC3(null, 1.0);
        open(gw, b, "AUSDT", now.get());
        gw.newStopMarket("AUSDT", Side.SELL, new BigDecimal("0.9"), "c3s-AUSDT-1", true);
        b.setStop("AUSDT", 0.9, "c3s-AUSDT-1", now.get());
        List<String> alerts = new ArrayList<>();
        C3LiveFlattener f = new C3LiveFlattener(gw, b, () -> KillSwitchEngine.Action.NONE, alerts::add, null, now::get, 5,
                10_000L, 10_000L);
        gw.setPosition("AUSDT", BigDecimal.ZERO, BigDecimal.ONE);
        for (int i = 0; i < 6; i++) {
            assertEquals(0, f.closeCluster("AUSDT", "TIME_STOP"));
            now.addAndGet(30_000L);
        }
        assertTrue(b.isHolding("AUSDT"));
        assertEquals(1, gw.openStops("AUSDT").size());
        assertEquals(0, gw.calls("cancelStop"));
        assertEquals(1, alerts.stream().filter(m -> m.contains("stop c3s- NEW")).count());
    }

    private static AccountSnapshot snap(String tmb) {
        BigDecimal v = new BigDecimal(tmb);
        return new AccountSnapshot(v, v, v, BigDecimal.ZERO, Collections.emptyList(), 0L);
    }

    // ------------------------------------------------------------------ [3f]
    @Test
    public void killSwitchFlattenAndCloseClusterUseEmergencyLane() {
        MockExchangeGateway mock = new MockExchangeGateway();
        AtomicLong now = new AtomicLong(1_793_114_327_000L);   // giay :47 (nhu flatten 10-27)
        RateGuard rg = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 2_000L, new RateGuard.Clock() {
            @Override public long nowMs() { return now.get(); }
            @Override public void sleepMs(long ms) { now.addAndGet(ms); }
        });
        ExchangeGateway gw = (ExchangeGateway) java.lang.reflect.Proxy.newProxyInstance(ExchangeGateway.class.getClassLoader(),
                new Class<?>[]{ExchangeGateway.class}, (p, m, a) -> {
                    String n = m.getName();
                    if (!"name".equals(n) && !"toString".equals(n) && !"hashCode".equals(n) && !"equals".equals(n)) {
                        rg.acquire(n.startsWith("positions") || n.startsWith("account") ? 5 : 1, n.startsWith("newMarketOrder") ? 1 : 0);
                    }
                    try {
                        return m.invoke(mock, a);
                    } catch (java.lang.reflect.InvocationTargetException e) {
                        throw e.getCause();
                    }
                });
        LiveBookC3 b = new LiveBookC3(null, 1.0);
        open(mock, b, "AUSDT", now.get());
        open(mock, b, "BUSDT", now.get());
        rg.onHeaders(1494, null, null);   // IP chung LEGACY > ngan sach 1200
        try {
            gw.positions();
            fail("lan thuong phai bi chan");
        } catch (GatewayException e) {
            assertEquals(ErrorKind.RATE_LIMIT, e.getKind());
        }
        AtomicReference<KillSwitchEngine.Action> act = new AtomicReference<>(KillSwitchEngine.Action.FLATTEN);
        C3LiveFlattener f = new C3LiveFlattener(gw, b, act::get, m -> { }, null, now::get, 5, 10_000L, 10_000L);
        assertEquals(1, f.closeCluster("AUSDT", "TIME_STOP"));
        assertEquals(0, mock.position("AUSDT").signum());
        assertTrue(f.step() >= 1);
        assertEquals(0, mock.position("BUSDT").signum());
        assertTrue(rg.emergencyOverBudget() > 0);
        assertEquals("chi lan doi chung bi tu choi", 1L, rg.rejects());
    }

    @Test
    public void closeNeverSellsMoreThanC3Qty() {
        MockExchangeGateway gw = new MockExchangeGateway();
        AtomicLong now = new AtomicLong(1_000_000L);
        LiveBookC3 b = new LiveBookC3(null, 1.0);
        open(gw, b, "AUSDT", now.get());   // c3: 10
        gw.newMarketOrder("AUSDT", Side.BUY, new BigDecimal("7"), "web_legacy_1", false);   // LEGACY 7 cung symbol (one-way)
        C3LiveFlattener f = new C3LiveFlattener(gw, b, () -> KillSwitchEngine.Action.NONE, m -> { }, null, now::get, 5, 10_000L, 10_000L);
        assertEquals(1, f.closeCluster("AUSDT", "TIME_STOP"));
        assertEquals("chi ban phan c3", 0, new BigDecimal("7").compareTo(gw.position("AUSDT")));
    }

    // ------------------------------------------------------------------ [3g MIN-6]
    @Test
    public void mineZeroNeverClosesConfirmedQty() {
        MockExchangeGateway gw = new MockExchangeGateway();
        AtomicLong now = new AtomicLong(1_000_000L);
        LiveBookC3 b = new LiveBookC3(null, 1.0);
        open(gw, b, "AUSDT", now.get());                       // c3: 10
        b.addExitFill("AUSDT", BigDecimal.TEN, 1.0, now.get());  // so: da thoat het (phan c3 = 0) nhung san van 10
        C3LiveFlattener f = new C3LiveFlattener(gw, b, () -> KillSwitchEngine.Action.NONE, m -> { }, null, now::get, 5, 10_000L, 10_000L);
        f.closeCluster("AUSDT", "TIME_STOP");
        assertEquals("KHONG ban (phan c3 = 0)", 0, gw.calls("newMarketOrder") - 1);
        assertEquals(0, BigDecimal.TEN.compareTo(gw.position("AUSDT")));
    }
}
