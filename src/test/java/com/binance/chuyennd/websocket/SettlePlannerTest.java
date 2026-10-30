package com.binance.chuyennd.websocket;

import org.junit.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.junit.Assert.*;

/** [INGEST-QF] Kế hoạch kiểm lại: suspects (ô không phải WS final) + mẫu xoay vòng thay settle mọi symbol. */
public class SettlePlannerTest {
    static final long MIN = 60_000L;
    static final long CUR = 1_760_000_000_000L / MIN * MIN;   // phut dang mo

    static List<String> uni(int n) {
        List<String> u = new ArrayList<>();
        for (int i = 0; i < n; i++) u.add(String.format("S%03dUSDT", i));
        return u;
    }

    @Test
    public void limitCoversOldestMinute() {
        assertEquals(3, SettlePlanner.limitFor(CUR, CUR - MIN));          // M = phut vua dong
        assertEquals(3, SettlePlanner.limitFor(CUR, CUR - 1));            // lam tron
        assertEquals(12, SettlePlanner.limitFor(CUR, CUR - 10 * MIN));
        assertEquals(32, SettlePlanner.limitFor(CUR, CUR - 30 * MIN));    // startup 30'
        assertEquals(99, SettlePlanner.limitFor(CUR, CUR - 500 * MIN));   // tran weight 1
    }

    @Test
    public void steadyStateOnlySampleNoSuspects() {
        SettlePlanner p = new SettlePlanner(25, 30);
        SettlePlanner.Plan a = p.plan(CUR, uni(752));
        assertTrue(a.suspects.isEmpty());
        assertEquals(25, a.sample.size());
        // xoay vong: 752/25 => ~31 pass phu het, khong trung trong 1 vong
        Set<String> seen = new HashSet<>(a.sample);
        for (int i = 1; i < 30; i++) seen.addAll(p.plan(CUR + i * MIN, uni(752)).sample);
        assertEquals(750, seen.size());
        seen.addAll(p.plan(CUR + 30 * MIN, uni(752)).sample);
        assertEquals(752, seen.size());
    }

    @Test
    public void suspectsUntilFetchedOk() {
        SettlePlanner p = new SettlePlanner(5, 3);
        List<String> u = uni(10);
        p.markSuspects(Arrays.asList("S001USDT", "S002USDT"), CUR - MIN);
        p.markSuspect("S001USDT", CUR - 5 * MIN);                 // giu phut cu nhat
        p.markSuspect("S003USDT", CUR);                           // phut dang mo: chua kiem
        SettlePlanner.Plan a = p.plan(CUR, u);
        assertEquals(Arrays.asList("S001USDT", "S002USDT"), a.suspects);
        assertEquals(7, a.suspectLimit);
        assertFalse("mau khong trung suspects", a.sample.contains("S001USDT") || a.sample.contains("S002USDT"));
        p.onSuspectsSettled(a.suspects, Collections.singletonList("S002USDT"), CUR, a.suspectLimit);
        assertEquals(2, p.suspectCount());                        // S002 (loi) + S003 (chua dong)
        SettlePlanner.Plan b = p.plan(CUR + MIN, u);
        assertEquals(Arrays.asList("S002USDT", "S003USDT"), b.suspects);
    }

    @Test
    public void persistentFailureDroppedAfterMaxPasses() {
        SettlePlanner p = new SettlePlanner(0, 3);
        p.markSuspect("DEADUSDT", CUR - MIN);
        List<String> u = Collections.singletonList("DEADUSDT");
        for (int i = 0; i < 3; i++) {
            SettlePlanner.Plan a = p.plan(CUR + i * MIN, u);
            assertEquals(1, a.suspects.size());
            p.onSuspectsSettled(a.suspects, a.suspects, CUR + i * MIN, a.suspectLimit);
        }
        assertEquals(0, p.suspectCount());
    }

    @Test
    public void symbolLeavingUniverseIsForgotten() {
        SettlePlanner p = new SettlePlanner(0, 30);
        p.markSuspect("GONEUSDT", CUR - MIN);
        assertTrue(p.plan(CUR, uni(3)).suspects.isEmpty());
        assertEquals(0, p.suspectCount());
    }
}
