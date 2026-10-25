package com.binance.chuyennd.c3live.log;

import org.junit.Test;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.*;

/** [V12 C14] 1 dong, 12 cot co dinh, gia tri rong "-", khong vo dong. */
public class OrderAuditLogTest {
    static final String[] COLS = {"ts", "cid", "oid", "sym", "side", "type", "qty", "px", "status", "lat_ms", "err", "reason"};

    static void assertFixedColumns(String tag, String line) {
        assertFalse(line.contains("\n"));
        String[] parts = line.split(" ");
        assertEquals(line, 13, parts.length);
        assertEquals(tag, parts[0]);
        for (int i = 0; i < COLS.length; i++) assertTrue(line, parts[i + 1].startsWith(COLS[i] + "="));
    }

    @Test
    public void fixedColumnsFull() {
        List<String> out = new ArrayList<>();
        OrderAuditLog a = new OrderAuditLog(OrderAuditLog.LIVE_TAG, out::add);
        String l = a.record(OrderAuditLog.Entry.of(1761400000000L).clientOrderId("c3-BTCUSDT-1-1").orderId(42).symbol("BTCUSDT")
                .side("BUY").type("MARKET").qty(new BigDecimal("0.0030")).price(new BigDecimal("1E+2")).status("FILLED")
                .latencyMs(37).reason("new"));
        assertEquals(1, out.size());
        assertEquals("[C3-LIVE-ORDER] ts=1761400000000 cid=c3-BTCUSDT-1-1 oid=42 sym=BTCUSDT side=BUY type=MARKET qty=0.0030 px=100 "
                + "status=FILLED lat_ms=37 err=- reason=new", l);
        assertFixedColumns(OrderAuditLog.LIVE_TAG, l);
    }

    @Test
    public void emptyAndHostileValuesStayOneLine() {
        String l = OrderAuditLog.format(OrderAuditLog.DRY_TAG, OrderAuditLog.Entry.of(0).symbol("币安 USDT")
                .errCode("FILTER:-4164").reason("Order's notional must be no smaller than 5\nnext=line\tx"));
        assertFixedColumns(OrderAuditLog.DRY_TAG, l);
        assertTrue(l, l.contains(" sym=币安_USDT "));
        assertTrue(l, l.contains(" ts=- cid=- oid=- "));
        assertTrue(l, l.contains(" lat_ms=- err=FILTER:-4164 reason=Order's_notional_must_be_no_smaller_than_5_next_line_x"));
        StringBuilder big = new StringBuilder();
        for (int i = 0; i < 500; i++) big.append('a');
        String l2 = OrderAuditLog.format(OrderAuditLog.LIVE_TAG, OrderAuditLog.Entry.of(1).reason(big.toString()));
        assertTrue(l2.length() < 300);
        assertFixedColumns(OrderAuditLog.LIVE_TAG, l2);
    }
}
