package com.binance.chuyennd.c3live.adapter;

import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.OrderStatus;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
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

/** [V12 C12] DryGateway (khop o gia ref, [LIVE-DRY] 12 cot, khong mang) + GatewayFactory (key loi => khong crash). */
public class DryGatewayTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    @Test
    public void fillsAtRefAndAuditsDryLines() {
        Map<String, BigDecimal> refs = new HashMap<>();
        List<String> lines = new ArrayList<>();
        DryGateway g = new DryGateway(() -> C3LiveFixtures.info(2), refs::get, new BigDecimal("10000"),
                new OrderAuditLog(OrderAuditLog.DRY_TAG, lines::add), () -> 123L);
        assertEquals("dry", g.name());
        assertTrue(g.multiAssetsMargin());
        assertFalse(g.dualSidePosition());
        // khong co gia ref => tu choi chac chan khong khop
        try {
            g.newMarketOrder("C00USDT", Side.BUY, BigDecimal.TEN, "c3-C00USDT-1-0", false);
            fail();
        } catch (GatewayException e) {
            assertTrue(e.isDefinitelyNotExecuted());
        }
        refs.put("C00USDT", new BigDecimal("2"));
        OrderInfo o = g.newMarketOrder("C00USDT", Side.BUY, BigDecimal.TEN, "c3-C00USDT-1-1", false);
        assertEquals(OrderStatus.FILLED, o.getStatus());
        assertEquals(0, new BigDecimal("2").compareTo(o.getAvgPrice()));
        assertEquals(o, g.queryOrder("C00USDT", "c3-C00USDT-1-1").get());
        refs.put("C00USDT", new BigDecimal("3"));
        assertEquals(10_010d, g.account().getTotalMarginBalance().doubleValue(), 1e-9);
        // reduce-only vuot vi the => tu choi
        try {
            g.newMarketOrder("C00USDT", Side.SELL, new BigDecimal("11"), "c3x-C00USDT-2-1", true);
            fail();
        } catch (GatewayException e) {
            assertTrue(e.isDefinitelyNotExecuted());
        }
        g.newStopMarket("C00USDT", Side.SELL, new BigDecimal("1.5"), "c3s-C00USDT-1", true);
        assertTrue(g.openStops("C00USDT").get(0).isClosePosition());
        g.newMarketOrder("C00USDT", Side.SELL, BigDecimal.TEN, "c3x-C00USDT-2-2", true);
        assertEquals(0, g.positions().size());
        assertEquals(10_010d, g.account().getTotalMarginBalance().doubleValue(), 1e-9);
        g.cancelStop("C00USDT", "c3s-C00USDT-1");
        assertEquals(0, g.openStops(null).size());
        assertEquals(6, lines.size());
        for (String l : lines) {
            assertTrue(l, l.startsWith("[LIVE-DRY] "));
            assertEquals(l, 12, l.split(" ").length - 1);
        }
        assertTrue(lines.get(1).contains("status=FILLED"));
        assertTrue(lines.get(3).contains("reason=new_stop_closePosition"));
    }

    @Test
    public void factoryModesAndBadKeyDoesNotThrow() throws Exception {
        assertEquals(GatewayFactory.Mode.OFF, GatewayFactory.Mode.parse(null));
        assertEquals(GatewayFactory.Mode.OFF, GatewayFactory.Mode.parse("yes"));
        assertEquals(GatewayFactory.Mode.DRY, GatewayFactory.Mode.parse(" DRY "));
        assertEquals(GatewayFactory.Mode.LIVE, GatewayFactory.Mode.parse("live"));
        Map<String, String> env = new HashMap<>();
        env.put("LIVE_C3_KEYS_FILE", new File(tmp.getRoot(), "khong_co/keys.env").getPath());
        GatewayFactory.Result r = GatewayFactory.create(GatewayFactory.Mode.LIVE, env::get, s -> null, BigDecimal.ONE,
                () -> 0L, OrderAuditLog.live());
        assertNull(r.gateway);
        assertTrue(r.reason, r.reason.startsWith("khong tao duoc C3LiveClient"));
        // dry: exchangeInfo tu file (thieu file => exchangeInfo() nem, khong crash luc tao)
        File ei = new File(tmp.getRoot(), "ei.json");
        env.put(GatewayFactory.KEY_EXCHANGEINFO_FILE, ei.getPath());
        GatewayFactory.Result d = GatewayFactory.create(GatewayFactory.Mode.DRY, env::get, s -> null, BigDecimal.ONE,
                () -> 0L, OrderAuditLog.dry());
        assertNotNull(d.gateway);
        try {
            d.gateway.exchangeInfo();
            fail();
        } catch (GatewayException expected) {
            // ok
        }
        java.nio.file.Files.copy(getClass().getResourceAsStream("/c3live/exchangeInfo_fixture_manual.json"), ei.toPath());
        assertTrue(d.gateway.exchangeInfo().symbol("BTCUSDT").isPresent());
        assertNull(GatewayFactory.create(GatewayFactory.Mode.OFF, env::get, s -> null, BigDecimal.ONE, () -> 0L,
                OrderAuditLog.dry()).gateway);
    }
}
