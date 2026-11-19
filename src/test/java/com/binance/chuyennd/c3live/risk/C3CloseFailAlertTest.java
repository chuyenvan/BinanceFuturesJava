package com.binance.chuyennd.c3live.risk;

import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.ops.KillSwitchEngine;
import org.junit.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.*;

/** [W3A muc 3 A-06] canh bao khi lenh DONG c3 loi lan &gt;= 3 (thua, 1 lan / symbol / cua so); mac dinh tat. */
public class C3CloseFailAlertTest {

    @Test
    public void closeFail_tuLan3_thua() {
        List<String> alerts = new ArrayList<>();
        C3LiveFlattener f = new C3LiveFlattener(new MockExchangeGateway(), new LiveBookC3(null, 1.0),
                () -> KillSwitchEngine.Action.NONE, alerts::add, (a, ok) -> { }, () -> 0L, 5, 10_000L, 0L);
        f.closeFailAlert("AUSDT", 3, "REJECTED", 0L);
        assertTrue("mac dinh tat", alerts.isEmpty());
        f.setCloseFailAlert(30 * 60_000L);
        f.closeFailAlert("AUSDT", 1, "REJECTED", 0L);
        f.closeFailAlert("AUSDT", 2, "REJECTED", 1L);
        assertTrue(alerts.isEmpty());
        f.closeFailAlert("AUSDT", 3, "REJECTED", 2L);
        assertEquals(1, alerts.size());
        assertTrue(alerts.get(0), alerts.get(0).startsWith("[C3-LIVE] CLOSE-FAIL") && alerts.get(0).contains("lan 3"));
        f.closeFailAlert("AUSDT", 4, "REJECTED", 60_000L);
        assertEquals(1, alerts.size());
        f.closeFailAlert("AUSDT", 9, "TIMEOUT", 31 * 60_000L);
        assertEquals(2, alerts.size());
        assertTrue(alerts.get(1).contains("1 canh bao bi nen"));
    }
}
