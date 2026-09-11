package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.tradecore.Configs;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.assertEquals;

/**
 * L6 — GATE DYN TANG 2 phai chay o CA rank-mode (docs/L6_GATE_DYN_FIX.md).
 *
 * <p>Truoc L6, LIVE ({@code DetectEntrySignal2TradeNormal:656}, commit {@code 311bb29}) BO
 * {@code checkSignalDynamic} khi {@code SELECTOR_RANK_TOPK > 0} nen chay gate PHANG 0.008,
 * trong khi SIM luon chay gate DONG. Audit {@code docs/AUDIT_GATE_DYN_PARITY.md} do duoc lech
 * 95.62% slot tren 48 thang va 77/78 entry so giay 242. Nay ca hai di chung
 * {@link AIRejectFilter#entryGate}.
 *
 * <p>Moc so: {@code dyn_thr = MIN_MOMENTUM_15M * max(AI_DYNAMIC_MIN, symbolPred/RATE_MAX *
 * AI_DYNAMIC_MULTIPLIER)} = {@code 0.008 * max(0.26787, 0.30/0.15*1.28760)} = {@code 0.0206016}
 * — dung vung {@code symbolPred} that cua top-8 tren 242 (0.2519..0.3484).
 */
public class GateDynEntryTest {

    /** symbolPred dai dien top-8 rank-mode (242 do duoc 0.2519..0.3484). */
    private static final Float SP = 0.30f;
    private static final float DYN_THR = 0.0206016f;   // 0.008 * 2.5752

    private final float min0 = Configs.MIN_MOMENTUM_15M;
    private final float mult0 = Configs.AI_DYNAMIC_MULTIPLIER;
    private final float dmin0 = Configs.AI_DYNAMIC_MIN;
    private final float rmax0 = Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD;

    private AIRejectFilter f;

    @Before
    public void setUp() {
        // Dung dung cau hinh dang chay: profile x1_c3_full / 242 conf/env.sh deu 0.008.
        Configs.MIN_MOMENTUM_15M = 0.008f;
        Configs.AI_DYNAMIC_MULTIPLIER = 1.28760f;
        Configs.AI_DYNAMIC_MIN = 0.26787f;
        Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD = 0.15f;
        f = new AIRejectFilter();
    }

    @After
    public void restore() {
        Configs.MIN_MOMENTUM_15M = min0;
        Configs.AI_DYNAMIC_MULTIPLIER = mult0;
        Configs.AI_DYNAMIC_MIN = dmin0;
        Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD = rmax0;
    }

    private static AiPredictionData p(float pred15m) {
        return new AiPredictionData(1_700_000_000_000L, pred15m, 0.02f);
    }

    /** Cong thuc nguong khong doi — neo so truoc khi doc hai ca duoi. */
    @Test
    public void dynThresholdDung0206() {
        assertEquals(DYN_THR, AIRejectFilter.dynThreshold(p(0.012f), SP), 1e-7f);
    }

    /**
     * TRUNG TAM: rank-mode (TOPK=8, symbolPred=0.30). pred15m=0.012 QUA gate phang 0.008
     * nhung DUOI dyn_thr 0.0206 => phai REJECT. Truoc L6 day la PASS => 77/78 entry live thua.
     */
    @Test
    public void rankModePred012BiReject() {
        assertEquals(AIRejectFilter.FilterDecision.REJECT,
                f.entryGate(p(0.012f), SP, true).decision);
    }

    /** Cung rank-mode, pred15m=0.025 vuot dyn_thr 0.0206 => PASS (gate khong chan sach tron). */
    @Test
    public void rankModePred025Pass() {
        assertEquals(AIRejectFilter.FilterDecision.PASS,
                f.entryGate(p(0.025f), SP, true).decision);
    }

    /**
     * KHONG HOI QUY: leg KHONG phai PREDICT_SYMBOL_TRADE (BIG_DOWN / DCA_LEVEL1 / market-signal)
     * van chay gate PHANG nhu truoc — 0.012 >= 0.008 => PASS. L6 khong duoc dong cac leg do.
     */
    @Test
    public void legKhacPstGiuGatePhang() {
        assertEquals(AIRejectFilter.FilterDecision.PASS,
                f.entryGate(p(0.012f), SP, false).decision);
        assertEquals(AIRejectFilter.FilterDecision.REJECT,
                f.entryGate(p(0.007f), SP, false).decision);
    }

    /** symbolPred == null (thieu score selector) => duong CU giu nguyen: gate phang. */
    @Test
    public void symbolPredNullGiuGatePhang() {
        assertEquals(AIRejectFilter.FilterDecision.PASS,
                f.entryGate(p(0.012f), null, true).decision);
    }

    /**
     * entryGate phai TRUNG KHIT checkSignalDynamic o nhanh PST — chung minh LIVE va SIM
     * (Simulator.createOrder van goi thang checkSignalDynamic) ra CUNG quyet dinh.
     */
    @Test
    public void entryGateTrungKhitCheckSignalDynamic() {
        for (float pred : new float[]{0.0f, 0.005f, 0.008f, 0.012f, 0.0206f, 0.021f, 0.05f}) {
            assertEquals("pred15m=" + pred,
                    f.checkSignalDynamic(p(pred), SP).decision,
                    f.entryGate(p(pred), SP, true).decision);
        }
    }
}
