package com.binance.chuyennd.trading;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.Assert.*;

/**
 * [W3A muc 1] AUDIT_LEGACY_DCA_1116 Q5(2).1 ? vong DCA luat cu cua LEGACY ({@code DcaProcessor.getDCAProduction})
 * KHONG chay khi profile c3 bat. Tai hien chuoi 17/11/2026 22:52:06 (12 dong {@code [SHADOW] add-leg leg=2}, moi leg
 * ~600-840 USDT, sinh tu tin hieu DCA_LEVEL1 cua LEGACY tren coin so giay dang giu): truoc va => 12 leg di vao
 * createOrderBuyRequest (=> C3LiveHook.onLeg + so giay add-leg); sau va => 0. Profile TAT => y nguyen (hoi quy).
 * Danh sach 12 symbol la DAI DIEN (lay tu 33 cum rank=-1 trong AUDIT_LEGACY_DCA_1116 Q3), khong phai ban sao log.
 */
public class LegacyDcaC3SkipTest {

    static final List<String> EVENT_1117_2252 = Arrays.asList("REUSDT", "BREVUSDT", "ZBTUSDT", "VELVETUSDT", "PEOPLEUSDT",
            "SAHARAUSDT", "ZORAUSDT", "PRLUSDT", "BANKUSDT", "TRUMPUSDT", "AVAAIUSDT", "XPINUSDT");

    /** Mo phong dung vong goi cua DetectEntrySignal2TradeNormal: moi symbol tra ve => 1 createOrderBuyRequest(DCA_LEVEL1). */
    private static int replay(boolean runs, AtomicInteger productionCalls, List<String> hookCalls) {
        List<String> syms = DetectEntrySignal2TradeNormal.legacyDcaSymbols(runs, () -> {
            productionCalls.incrementAndGet();
            return new ArrayList<>(EVENT_1117_2252);
        });
        int legs = 0;
        for (String s : syms) {
            hookCalls.add(s);   // createOrderBuyRequest -> C3LiveHook.onLeg -> nhanh giay add-leg
            legs++;
        }
        return legs;
    }

    @Test
    public void decide_profileTat_luonChay() {
        assertTrue(DetectEntrySignal2TradeNormal.decideLegacyDcaRuns(false, null));
        assertTrue(DetectEntrySignal2TradeNormal.decideLegacyDcaRuns(false, "true"));
        assertTrue(DetectEntrySignal2TradeNormal.decideLegacyDcaRuns(false, "false"));
    }

    @Test
    public void decide_profileBat_macDinhBoQua_chiFalseMoiChay() {
        assertFalse(DetectEntrySignal2TradeNormal.decideLegacyDcaRuns(true, null));
        assertFalse(DetectEntrySignal2TradeNormal.decideLegacyDcaRuns(true, ""));
        assertFalse(DetectEntrySignal2TradeNormal.decideLegacyDcaRuns(true, "true"));
        assertFalse(DetectEntrySignal2TradeNormal.decideLegacyDcaRuns(true, "0"));
        assertTrue(DetectEntrySignal2TradeNormal.decideLegacyDcaRuns(true, "false"));
        assertTrue(DetectEntrySignal2TradeNormal.decideLegacyDcaRuns(true, " FALSE "));
    }

    @Test
    public void event1117_truocVa_12addLeg_sauVa_0() {
        // TRUOC va (= jar 5e10325b: vong luon chay) => 12 leg DCA_LEVEL1 ngoai luoi
        AtomicInteger p0 = new AtomicInteger();
        List<String> h0 = new ArrayList<>();
        assertEquals(12, replay(true, p0, h0));
        assertEquals(1, p0.get());
        assertEquals(12, h0.size());
        // SAU va: profile c3 bat, env mac dinh => 0 leg, 0 goi hook, KHONG doc getDCAProduction
        boolean runs = DetectEntrySignal2TradeNormal.decideLegacyDcaRuns(true, null);
        AtomicInteger p1 = new AtomicInteger();
        List<String> h1 = new ArrayList<>();
        long before = DetectEntrySignal2TradeNormal.legacyDcaSkippedCount();
        assertEquals(0, replay(runs, p1, h1));
        assertEquals(0, p1.get());
        assertTrue(h1.isEmpty());
        assertEquals(before + 1, DetectEntrySignal2TradeNormal.legacyDcaSkippedCount());
        // Rollback env C3_SKIP_LEGACY_DCA=false => y nhu truoc va
        AtomicInteger p2 = new AtomicInteger();
        List<String> h2 = new ArrayList<>();
        assertEquals(12, replay(DetectEntrySignal2TradeNormal.decideLegacyDcaRuns(true, "false"), p2, h2));
        // Profile TAT (LEGACY thuan) => y nguyen (hoi quy)
        AtomicInteger p3 = new AtomicInteger();
        List<String> h3 = new ArrayList<>();
        assertEquals(12, replay(DetectEntrySignal2TradeNormal.decideLegacyDcaRuns(false, null), p3, h3));
        assertEquals(EVENT_1117_2252, h3);
    }

    @Test
    public void runsTrue_traVeDungObjectNguon() {
        List<String> src = new ArrayList<>(EVENT_1117_2252);
        assertSame(src, DetectEntrySignal2TradeNormal.legacyDcaSymbols(true, () -> src));
        assertNull("null cua nguon cu giu nguyen (khong doi hanh vi)", DetectEntrySignal2TradeNormal.legacyDcaSymbols(true, () -> null));
    }

    /** Ca 2 call-site getDCAProduction trong luong live deu qua chot; 2 call-site luoi paperDcaGrid giu nguyen. */
    @Test
    public void source_haiCallSiteDeuQuaChot_luoiGiuNguyen() throws Exception {
        String s = new String(Files.readAllBytes(Paths.get(
                "src/main/java/com/binance/chuyennd/trading/DetectEntrySignal2TradeNormal.java")), StandardCharsets.UTF_8);
        int n = 0;
        int i = -1;
        while ((i = s.indexOf("DcaProcessor.getDCAProduction(", i + 1)) >= 0) {
            n++;
            String before = s.substring(Math.max(0, i - 120), i);
            assertTrue("call-site " + n + " phai nam trong legacyDcaSymbols(legacyDcaRuns(), () -> ...)",
                    before.contains("legacyDcaSymbols(legacyDcaRuns(), () -> "));
        }
        assertEquals(2, n);
        assertEquals(1, count(s, "paperDcaGrid(\"level\""));
        assertEquals(1, count(s, "paperDcaGrid(\"dcaAlt\""));
    }

    private static int count(String s, String sub) {
        int c = 0;
        int i = -1;
        while ((i = s.indexOf(sub, i + 1)) >= 0) c++;
        return c;
    }
}
