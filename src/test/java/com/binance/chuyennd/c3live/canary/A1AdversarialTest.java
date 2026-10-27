package com.binance.chuyennd.c3live.canary;

import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.rate.RateGuard;
import org.junit.Test;

import java.math.BigDecimal;

import static org.junit.Assert.*;

/** A1 3f: test doi khang (scratch, KHONG commit). */
public class A1AdversarialTest extends CanaryEngineTest {

    private CanaryEngine.Result k0() throws Exception {
        CanaryEngine e = engine(cfg());
        CanaryEngine.Result r = e.preflight();
        e.close();
        assertEquals(r.line(), CanaryEngine.DAT, r.verdict);
        return r;
    }

    private CanaryEngine.Result st(String k) throws Exception {
        CanaryEngine e = engine(cfg());
        CanaryEngine.Result r = e.step(k);
        e.close();
        return r;
    }

    @Test
    public void a1LegacySellOnMainWhileCanaryLong() throws Exception {
        k0();
        CanaryEngine.Result k1 = st("K1");
        assertEquals(k1.line(), CanaryEngine.DAT, k1.verdict);
        BigDecimal mine = mock.position(MAIN);
        mock.newMarketOrder(MAIN, Side.SELL, mine.divide(new BigDecimal("2")), "web_legacy_short", false);
        int mo = mock.calls("newMarketOrder");
        CanaryEngine.Result r = st("K2");
        System.out.println("A1-A K2: " + r.line());
        CanaryEngine e3 = engine(cfg());
        CanaryEngine.Result f = e3.flatten();
        e3.close();
        System.out.println("A1-A flatten: " + f.line() + " posAfter=" + mock.position(MAIN) + " canaryMarketAfterLegacy="
                + (mock.calls("newMarketOrder") - mo) + " red=" + CanaryState.load(dir).red);
        assertTrue("§ADD-4 C: LEGACY SELL cong don one-way => phai TRUOT-DO, khong dong", r.line().contains(CanaryEngine.TRUOT_DO));
    }

    @Test
    public void a1GuardRetryOpenAfterLegacyEntered() throws Exception {
        k0();
        final boolean[] armed = {true};
        ExchangeGateway px = (ExchangeGateway) java.lang.reflect.Proxy.newProxyInstance(ExchangeGateway.class.getClassLoader(),
                new Class<?>[]{ExchangeGateway.class}, (p, m, a) -> {
                    if (armed[0] && "newMarketOrder".equals(m.getName()) && a[3] != null && ((String) a[3]).startsWith("c3-")) {
                        armed[0] = false;
                        mock.newMarketOrder((String) a[0], Side.BUY, new BigDecimal("7"), "web_legacy_race", false);
                        throw new GatewayException(ErrorKind.RATE_LIMIT, 0, 0, "rate guard: IP nang (gia lap)", true, 20_000L, null);
                    }
                    try {
                        return m.invoke(mock, a);
                    } catch (java.lang.reflect.InvocationTargetException e) {
                        throw e.getCause();
                    }
                });
        RateGuard rg = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 2_000L, rgClock());
        CanaryEngine e = engineRaw(cfg(), px, rg);
        CanaryEngine.Result r = e.step("K1");
        e.close();
        long canaryBuys = mock.callLog().stream().filter(x -> x.startsWith("newMarketOrder:" + MAIN + ":c3-")).count();
        System.out.println("A1-B K1: " + r.line() + " canaryBuysSent=" + canaryBuys + " pos=" + mock.position(MAIN));
        assertEquals("lenh MO canary khong duoc gui len symbol LEGACY vua vao (retry sau 21 s khong kiem lai)", 0L, canaryBuys);
    }
}
