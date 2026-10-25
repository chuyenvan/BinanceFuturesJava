package com.binance.chuyennd.tradecore.selector;

import org.junit.Test;

import static org.junit.Assert.assertTrue;

/**
 * [V12 SAFE C10 muc 4] dong [GATE] khi predictData == null: DetectEntrySignal2TradeNormal truyen nRej = nCand
 * (patch audD) => n_pass = 0 (truoc: nRej = 0 => in n_pass = n_cand du KHONG co ung vien nao duoc xet).
 */
public class GateLineNoPredTest {

    @Test
    public void noPredictionPrintsZeroPass() {
        String legacy = LiveBookU.gateLine(false, "1.5500", 24, "0.00800", "-", "-", 24, 24, 0, 0f);
        assertTrue(legacy, legacy.contains("n_pass=0"));
        String skip = LiveBookU.gateLine(true, "1.5500", 24, "0.00800", "-", "-", 24, 24, 0, 0f);
        assertTrue(skip, skip.contains("n_pass=0"));
        String before = LiveBookU.gateLine(true, "1.5500", 24, "0.00800", "-", "-", 24, 0, 0, 0f);
        assertTrue(before, before.contains("n_pass=24"));
    }
}
