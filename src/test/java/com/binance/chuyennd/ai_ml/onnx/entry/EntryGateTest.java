package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.EntryGate;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * L7 — cong entry tang 2 la MOT ham dung chung sim + live
 * ({@link EntryGate} qua {@link AIRejectFilter#entryGate}).
 *
 * <p>Moc so: {@code thr = MIN_MOMENTUM_15M * max(DYN_MIN, symbolPred/SCORE_BASE * DYN_MULT)}
 * = {@code 0.008 * max(0.26787, 0.30/0.15*1.28760)} = {@code 0.0206016}.
 *
 * <p>Hai bien QUAN TRONG lay tu do that 48 thang (docs/LEAN_GATE_AUDIT.md muc 3.3):
 * {@code symbolPred = 0.031206} la diem chuyen floor/tuyen tinh, va
 * {@code symbolPred = 0.024885} la slot DUY NHAT trong 48 thang ma floor THUC SU thang
 * (2024-08-05 13:30 GMT+7, symId 261) — do la ly do gate KHONG duoc rut ve {@code K*symbolPred}.
 */
public class EntryGateTest {

    private static final float SP = 0.30f;
    private static final float DYN_THR = 0.0206016f;

    private final float mm0 = Configs.MIN_MOMENTUM_15M;
    private final int topk0 = Configs.SELECTOR_RANK_TOPK;
    private AIRejectFilter f;

    private static AiPredictionData p(float pred15m) {
        return new AiPredictionData(1_700_000_000_000L, pred15m, -0.05f);
    }

    @Before
    public void setUp() {
        Configs.MIN_MOMENTUM_15M = 0.008f;
        f = new AIRejectFilter();
        AIRejectFilter.resetCounters();
    }

    @After
    public void tearDown() {
        Configs.MIN_MOMENTUM_15M = mm0;
    }

    /** Gia tri nguong — chot bang so, khong suy tu code. */
    @Test
    public void nguongDung0206() {
        assertEquals(DYN_THR, EntryGate.threshold(0.008f, SP), 1e-7f);
        assertEquals(DYN_THR, EntryGate.threshold(SP), 1e-7f);
    }

    /** Ba he so la HANG SO cua EntryGate, khong con doc tu Configs. */
    @Test
    public void baHeSoLaHangSo() {
        assertEquals(0.26787f, EntryGate.DYN_MIN, 0f);
        assertEquals(0.15f, EntryGate.SCORE_BASE, 0f);
        assertEquals(1.28760f, EntryGate.DYN_MULT, 0f);
    }

    /** rank-mode (TOPK>0): pred15m=0.012 QUA gate phang 0.008 nhung DUOI nguong dong => REJECT. */
    @Test
    public void rankModePred012BiReject() {
        assertEquals(AIRejectFilter.FilterDecision.REJECT,
                f.entryGate(p(0.012f), SP, true).decision);
        assertFalse(EntryGate.pass(0.012f, 0.008f, SP));
    }

    /** Cung the, pred15m=0.025 vuot nguong dong => PASS. */
    @Test
    public void rankModePred025Pass() {
        assertEquals(AIRejectFilter.FilterDecision.PASS,
                f.entryGate(p(0.025f), SP, true).decision);
        assertTrue(EntryGate.pass(0.025f, 0.008f, SP));
    }

    /** Leg KHONG phai PREDICT_SYMBOL_TRADE => nguong CO SO, hanh vi cu khong doi. */
    @Test
    public void legKhacPstGiuNguongCoSo() {
        assertEquals(AIRejectFilter.FilterDecision.PASS,
                f.entryGate(p(0.012f), SP, false).decision);
        assertEquals(AIRejectFilter.FilterDecision.REJECT,
                f.entryGate(p(0.007f), SP, false).decision);
    }

    /** symbolPred == null (thieu score selector) => nguong CO SO. */
    @Test
    public void symbolPredNullGiuNguongCoSo() {
        assertEquals(AIRejectFilter.FilterDecision.PASS,
                f.entryGate(p(0.012f), null, true).decision);
        assertEquals(0.008f, EntryGate.threshold(0.008f, null), 0f);
    }

    /**
     * BIEN floor: dung tai diem chuyen {@code DYN_MIN*SCORE_BASE/DYN_MULT = 0.0312064},
     * duoi diem do floor thang.
     */
    @Test
    public void bienFloor0312() {
        float cut = EntryGate.DYN_MIN * EntryGate.SCORE_BASE / EntryGate.DYN_MULT;
        assertEquals(0.0312064f, cut, 1e-6f);
        // ngay TREN diem chuyen: ve tuyen tinh thang
        float above = 0.0313f;
        assertEquals(0.008f * (above / 0.15f * 1.28760f), EntryGate.threshold(0.008f, above), 1e-9f);
        // ngay DUOI diem chuyen: floor thang => nguong KHONG giam theo symbolPred nua
        float below = 0.0300f;
        assertEquals(0.008f * 0.26787f, EntryGate.threshold(0.008f, below), 1e-9f);
    }

    /**
     * Slot floor-bind DUY NHAT cua 48 thang (docs/LEAN_GATE_AUDIT.md muc 3.3). Test nay la LY DO
     * gate khong duoc rut ve {@code K*symbolPred}: hai dang cho HAI nguong khac nhau o day.
     */
    @Test
    public void slotFloorBindThucTe() {
        float sp = 0.024885f;
        float thr = EntryGate.threshold(0.008f, sp);
        assertEquals(0.008f * 0.26787f, thr, 1e-9f);
        float k = 0.008f * EntryGate.DYN_MULT / EntryGate.SCORE_BASE;
        assertTrue("dang rut gon PHAI long hon o slot nay", k * sp < thr);
    }

    /** Gate KHONG con phu thuoc SELECTOR_RANK_TOPK — sim va live cung mot duong. */
    @Test
    public void gateKhongPhuThuocTopk() {
        assertEquals(topk0, Configs.SELECTOR_RANK_TOPK);
        assertEquals(f.entryGate(p(0.012f), SP, true).decision,
                AIRejectFilter.FilterDecision.REJECT);
    }
}
