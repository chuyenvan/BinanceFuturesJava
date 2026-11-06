package com.binance.chuyennd.websocket;

import org.junit.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.junit.Assert.*;

/** [QF4, ADDENDUM 3 + ADD-3b] Luật chọn tập "mất WS" ở pass +2 s (thuần). */
public class Qf4WsTest {
    static final long CLOSE = 1_760_000_040_000L / 60_000L * 60_000L + 60_000L;

    @Test
    public void ruleA_connectionDownOrReopenedAroundBoundary() {
        long since = CLOSE - 1_000L;
        assertTrue("dang dong", KlineWsClient.hadGapSince(false, CLOSE - 5_000L, CLOSE - 3_600_000L, since));
        assertTrue("EOF dung :00 (11-04 23:47:00)", KlineWsClient.hadGapSince(false, CLOSE, CLOSE - 3_600_000L, since));
        assertTrue("da mo lai sau ranh (+5 s)", KlineWsClient.hadGapSince(true, CLOSE, CLOSE + 5_000L, since));
        assertFalse("song lien tuc qua ranh", KlineWsClient.hadGapSince(true, CLOSE - 600_000L, CLOSE - 590_000L, since));
    }

    @Test
    public void ruleB_silenceThresholdFromMeasurement() {
        assertFalse("im lang lon nhat do duoc 788 ms", KlineWsClient.silentNow(125, CLOSE, CLOSE + 788));
        assertTrue(KlineWsClient.silentNow(125, CLOSE, CLOSE + 1_500));
        assertFalse("ket noi < 20 symbol (moi niem yet) khong xet", KlineWsClient.silentNow(19, CLOSE, CLOSE + 10_000));
    }

    @Test
    public void lostSetOnlyGapConnectionsUnlessGlobal() {
        List<String> missing = new ArrayList<>();
        for (int i = 0; i < 564; i++) missing.add("S" + i + "USDT");   // phut binh thuong o +2 s (75 % final toi o 3 s)
        int[] st = new int[2];
        assertTrue("khong ket noi ho => khong REST", KlinePassController.lostSet(missing, new HashSet<String>(), 600, st).isEmpty());
        Set<String> gap = new HashSet<>(Arrays.asList("S1USDT", "S2USDT", "XUSDT"));
        st = new int[2];
        Set<String> l = KlinePassController.lostSet(missing, gap, 600, st);
        assertEquals("chi symbol THIEU cua ket noi ho", new HashSet<>(Arrays.asList("S1USDT", "S2USDT")), l);
        assertEquals(0, st[1]);
        for (int i = 564; i < 601; i++) missing.add("S" + i + "USDT");
        st = new int[2];
        assertEquals("tong thieu > 600 => moi symbol thieu", 601, KlinePassController.lostSet(missing, gap, 600, st).size());
        assertEquals(1, st[1]);
    }
}
