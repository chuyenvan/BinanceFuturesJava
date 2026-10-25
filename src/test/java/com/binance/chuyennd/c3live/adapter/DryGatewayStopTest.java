package com.binance.chuyennd.c3live.adapter;

import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.OrderStatus;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.fill.UserStreamEvents;
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
import java.util.concurrent.ConcurrentHashMap;

import static org.junit.Assert.*;

/** [V12 C12 2b] Dry: stop SELL kich theo gia mark gia lap, su kien dang user stream, phi, persist qua restart. */
public class DryGatewayStopTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    @Test
    public void stopTriggersEmitsEventsAndPersists() {
        File state = new File(tmp.getRoot(), "run/c3live_dry_state.json");
        Map<String, BigDecimal> refs = new ConcurrentHashMap<>();
        refs.put("C00USDT", new BigDecimal("2"));
        List<String> audit = new ArrayList<>();
        List<String> ev = new ArrayList<>();
        DryGateway g = new DryGateway(() -> C3LiveFixtures.info(2), refs::get, new BigDecimal("10000"),
                new OrderAuditLog(OrderAuditLog.DRY_TAG, audit::add), () -> 1000L, state, 0.0005);
        g.setEventSink(ev::add);
        OrderInfo b = g.newMarketOrder("C00USDT", Side.BUY, new BigDecimal("100"), "c3-C00USDT-1-0", false);
        assertEquals(0, new BigDecimal("2").compareTo(b.getAvgPrice()));
        assertEquals(2, ev.size());
        UserStreamEvents.Event e0 = UserStreamEvents.parse(ev.get(0));
        assertTrue(e0 instanceof UserStreamEvents.OrderUpdate);
        assertEquals(0, new BigDecimal("0.1").compareTo(((UserStreamEvents.OrderUpdate) e0).commission));
        g.newStopMarket("C00USDT", Side.SELL, new BigDecimal("2.1"), "c3s-C00USDT-1-1", true);
        Map<String, Float> px = new HashMap<>();
        px.put("C00USDT", 2.2f);
        assertEquals(0, g.onPrices(px));
        // restart dry: vi the + stop mo con nguyen
        DryGateway g2 = new DryGateway(() -> C3LiveFixtures.info(2), refs::get, new BigDecimal("10000"),
                new OrderAuditLog(OrderAuditLog.DRY_TAG, audit::add), () -> 2000L, state, 0.0005);
        List<String> ev2 = new ArrayList<>();
        g2.setEventSink(ev2::add);
        assertEquals(1, g2.positions().size());
        assertEquals(1, g2.openStops("C00USDT").size());
        px.put("C00USDT", 2.05f);
        assertEquals(1, g2.onPrices(px));
        assertTrue(g2.positions().isEmpty());
        assertEquals(OrderStatus.FINISHED, g2.queryStop("C00USDT", "c3s-C00USDT-1-1").get().getStatus());
        UserStreamEvents.OrderUpdate sell = (UserStreamEvents.OrderUpdate) UserStreamEvents.parse(ev2.get(0));
        assertEquals("SELL", sell.side);
        assertEquals("c3s-C00USDT-1-1", sell.clientOrderId);
        assertEquals("STOP_MARKET", sell.origType);
        assertEquals(0, new BigDecimal("2.05").compareTo(sell.lastPrice));
        assertEquals(0, new BigDecimal("5.00").compareTo(sell.realizedPnl));
        UserStreamEvents.AccountUpdate au = (UserStreamEvents.AccountUpdate) UserStreamEvents.parse(ev2.get(1));
        assertEquals(0, au.positions.get(0).positionAmt.signum());
        // tmb = 10000 + 5 - phi (0.1 + 0.1025)
        assertEquals(10000 + 5 - 0.1 - 0.1025, g2.account().getTotalMarginBalance().doubleValue(), 1e-9);
        assertTrue(audit.stream().anyMatch(l -> l.contains("TRIGGERED")));
    }
}
