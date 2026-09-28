package com.binance.chuyennd.trading;

import com.binance.chuyennd.ai_ml.onnx.entry.OnnxInferenceManager;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.EntryGate;
import org.junit.Test;

import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.Set;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.assertFalse;

/**
 * [CASCADE 2026-09-28] docs/plan/PLAN_CASCADE_ENTRY.md — bang chung LOGIC cho GATE-FIRST:
 * (i)   {@code ENTRY_CASCADE<=0} => {@code cascadeUniverse} tra ve DUNG tap dau vao (cung object) => y nguyen;
 * (ii)  BAT => chi giu ung vien CO THE DAT cong entry (pred cache + pred thi truong), khong giu het;
 * (iii) BAT => KHONG BAO GIO sinh them symbol (ket qua ⊆ universe) va luon giu coin DANG GIU (DCA);
 * (iv)  coin CHUA co pred cache => GIU (khong bo vi thieu thong tin) — chong "cascade bo sot" o cold-start.
 * Chi goi ham THUAN (cascadeUniverse / cascadeGateFirst), khong cham mang/ONNX/live.
 */
public class EntryCascadeTest {

    static { Configs.MIN_MOMENTUM_15M = 0.008f; }   // co dinh nguong gate cho phep tinh tay

    private static OnnxInferenceManager.PredictionResult pred(float ret15M) {
        return new OnnxInferenceManager.PredictionResult(ret15M, 0f);
    }

    private static Set<String> set(String... s) { return new LinkedHashSet<>(Arrays.asList(s)); }

    // ---- (i) TAT => tra ve DUNG object dau vao (byte-identical) ----

    @Test
    public void tat_thiTraVeDungTapDauVao() {
        Configs.ENTRY_CASCADE = 0;
        Set<String> u = set("AUSDT", "BUSDT", "CUSDT");
        assertSame("TAT => phai tra ve CHINH object dau vao", u,
                DetectEntrySignal2TradeNormal.cascadeUniverse(u, null, pred(0.05f)));
        // du co levelChange (leg market-signal) => van y nguyen
        assertSame(u, DetectEntrySignal2TradeNormal.cascadeUniverse(u, MarketLevelChange.BIG_DOWN, pred(0.05f)));
        // du predictData == null => van y nguyen
        assertSame(u, DetectEntrySignal2TradeNormal.cascadeUniverse(u, null, null));
    }

    // ---- (ii) BAT: cong entry DONG (thi truong yeu) => bo het ung vien chua-cache... ----

    @Test
    public void bat_congDong_thiBoUngVienCoCacheFail() {
        Configs.ENTRY_CASCADE = 8;
        DetectEntrySignal2TradeNormal.LATEST_SEL_MAPPRED.clear();
        DetectEntrySignal2TradeNormal.LATEST_SEL_PNOPUMP.clear();
        Set<String> u = set("AUSDT", "BUSDT", "CUSDT");
        // pred market rat yeu: 0.0005 (< moi nguong) => khong coin nao DAT; nhung CHUA co cache => GIU
        Set<String> keep = DetectEntrySignal2TradeNormal.cascadeGateFirst(u, new HashSet<>(), 0.0005f, 8);
        assertEquals("chua co cache => giu het (khong bo vi thieu thong tin)", 3, keep.size());
        // nap cache: A pass duoc (pred nho -> thr nho), B/C khong the pass (pred lon -> thr > 0.005)
        DetectEntrySignal2TradeNormal.LATEST_SEL_MAPPRED.put("AUSDT", 0.02f);
        DetectEntrySignal2TradeNormal.LATEST_SEL_MAPPRED.put("BUSDT", 0.50f);
        DetectEntrySignal2TradeNormal.LATEST_SEL_MAPPRED.put("CUSDT", 0.90f);
        Set<String> keep2 = DetectEntrySignal2TradeNormal.cascadeGateFirst(u, new HashSet<>(), 0.005f, 8);
        assertTrue("A (pred nho) van co the DAT => phai giu", keep2.contains("AUSDT"));
        assertFalse("B (pred 0.50 -> thr cao) => bo", keep2.contains("BUSDT"));
        assertFalse("C (pred 0.90 -> thr cao) => bo", keep2.contains("CUSDT"));
        // cong entry MO (pred market lon) => giu top-k
        Set<String> keep3 = DetectEntrySignal2TradeNormal.cascadeGateFirst(u, new HashSet<>(), 0.20f, 8);
        assertEquals("cong mo => giu het", 3, keep3.size());
    }

    // ---- (iii) BAT: khong sinh them symbol + luon giu coin DANG GIU ----

    @Test
    public void bat_khongSinhThem_vaGiuHeld() {
        Configs.ENTRY_CASCADE = 2;
        DetectEntrySignal2TradeNormal.LATEST_SEL_MAPPRED.clear();
        DetectEntrySignal2TradeNormal.LATEST_SEL_PNOPUMP.clear();
        Set<String> u = set("AUSDT", "BUSDT", "CUSDT");
        Set<String> held = set("CUSDT");
        Set<String> keep = DetectEntrySignal2TradeNormal.cascadeGateFirst(u, held, 0.20f, 2);
        assertTrue("ket qua ⊆ universe", u.containsAll(keep));
        assertTrue("held luon duoc giu (DCA)", keep.contains("CUSDT"));
        assertTrue("topK=2 => khong qua 2 khi held da nam trong do", keep.size() <= 2);
        // held khong nam trong universe => khong duoc them vao (khong sinh symbol ngoai)
        Set<String> keep2 = DetectEntrySignal2TradeNormal.cascadeGateFirst(u, set("ZZZUSDT"), 0.20f, 2);
        assertFalse("held ngoai universe khong duoc them", keep2.contains("ZZZUSDT"));
        assertTrue(u.containsAll(keep2));
    }

    // ---- (iv) BAT: cap topK (khong chay ca universe) ----

    @Test
    public void bat_capTopK() {
        Configs.ENTRY_CASCADE = 8;
        DetectEntrySignal2TradeNormal.LATEST_SEL_MAPPRED.clear();
        DetectEntrySignal2TradeNormal.LATEST_SEL_PNOPUMP.clear();
        Set<String> u = new LinkedHashSet<>();
        for (int i = 0; i < 50; i++) u.add("SIM" + i + "USDT");
        Set<String> keep = DetectEntrySignal2TradeNormal.cascadeGateFirst(u, new HashSet<>(), 0.20f, 8);
        assertEquals("cong mo nhung cap topK=8", 8, keep.size());
        assertTrue(u.containsAll(keep));
    }

    /** Chieu don dieu cua cong: thr(pred) khong giam theo pred => pred cang lon cang kho DAT. */
    @Test
    public void congDonDieuTheoPred() {
        assertTrue(EntryGate.threshold(0.01f) <= EntryGate.threshold(0.50f));
    }
}
