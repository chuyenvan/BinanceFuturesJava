package com.binance.chuyennd.c3live.canary;

import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.rate.RateGuard;
import org.junit.Test;

import java.math.BigDecimal;

import static org.junit.Assert.*;

/** A1 3g: test doi khang (scratch, KHONG commit). */
public class A1G3Test extends CanaryEngineTest {

    private CanaryEngine.Result k(String s) throws Exception {
        CanaryEngine e = engine(cfg());
        CanaryEngine.Result r = "K0".equals(s) ? e.preflight() : "FLATTEN".equals(s) ? e.flatten() : e.step(s);
        e.close();
        return r;
    }

    @Test
    public void a1g3UnreadableScopeMustKeepCanaryStop() throws Exception {
        assertEquals(CanaryEngine.DAT, k("K0").verdict);
        assertEquals(CanaryEngine.DAT, k("K1").verdict);
        assertFalse("K1 co stop", mock.openStops(MAIN).isEmpty());
        final boolean[] fail = {false};
        ExchangeGateway raw = (ExchangeGateway) java.lang.reflect.Proxy.newProxyInstance(ExchangeGateway.class.getClassLoader(),
                new Class<?>[]{ExchangeGateway.class}, (p, m, a) -> {
                    if (fail[0] && "positions".equals(m.getName())) {
                        throw new GatewayException(ErrorKind.OTHER, 500, 0, "positionRisk loi (gia lap)", true, 0L, null);
                    }
                    try {
                        return m.invoke(mock, a);
                    } catch (java.lang.reflect.InvocationTargetException ex) {
                        throw ex.getCause();
                    }
                });
        RateGuard rg = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 2_000L, rgClock());
        CanaryEngine e = engineRaw(cfg(), raw, rg);
        fail[0] = true;
        CanaryEngine.Result f = e.flatten();
        e.close();
        System.out.println("A1G3-C flatten: " + f.line() + " pos=" + mock.position(MAIN) + " stops=" + mock.openStops(MAIN).size());
        assertTrue("vi the canary con => stop bao ve phai CON (doc loi khong phai bang chung lan LEGACY)",
                mock.position(MAIN).signum() == 0 || !mock.openStops(MAIN).isEmpty());
    }

    @Test
    public void a1g3StopFiredBetweenJvmsThenLegacyBuyIsNotSoldByCanary() throws Exception {
        assertEquals(CanaryEngine.DAT, k("K0").verdict);
        assertEquals(CanaryEngine.DAT, k("K1").verdict);
        mock.setPrice(MAIN, new BigDecimal("0.95"));
        mock.triggerStops(MAIN, new BigDecimal("0.95"));   // khong JVM nao song: stop canary kich, khong ai nghe stream
        assertEquals("stop da dong vi the canary", 0, mock.position(MAIN).signum());
        mock.newMarketOrder(MAIN, Side.BUY, new BigDecimal("7"), "web_legacy_after", false);   // LEGACY vao truoc JVM ke
        int sells0 = (int) mock.callLog().stream().filter(x -> x.startsWith("newMarketOrder:" + MAIN + ":c3x-")).count();
        CanaryEngine.Result r = k("K2");
        CanaryEngine.Result f = k("FLATTEN");
        int sells = (int) mock.callLog().stream().filter(x -> x.startsWith("newMarketOrder:" + MAIN + ":c3x-")).count() - sells0;
        System.out.println("A1G3-D K2: " + r.line() + " | flatten: " + f.line() + " pos=" + mock.position(MAIN) + " canarySells=" + sells
                + " ledger=" + CanaryState.load(dir).canaryQty);
        assertEquals("LEGACY 7 nguyen ven", 0, new BigDecimal("7").compareTo(mock.position(MAIN)));
        assertEquals("canary khong ban phan LEGACY", 0, sells);
    }
}
