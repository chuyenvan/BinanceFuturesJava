package com.binance.chuyennd.tradecore;

/**
 * CONG ENTRY TANG 2 — MOT cho duy nhat quyet dinh "tin hieu 15m co du manh de vao lenh khong",
 * dung chung cho BACKTEST ({@code SimulatorMarketLevelTicker1MStopLoss.createOrder}) va LIVE
 * ({@code DetectEntrySignal2TradeNormal.createOrderBuyRequest}).
 *
 * <p><b>Vi sao co class nay</b> (L7, docs/L7_LEAN_GATE.md + docs/LEAN_GATE_AUDIT.md): cong nay
 * tung nam o HAI ban sao trong {@code AIRejectFilter} ({@code checkSignalDynamic} va
 * {@code dynThreshold}) va duoc goi tu hai duong khac nhau, da troi khoi nhau 3 tuan
 * (commit {@code 311bb29}) ma khong ai thay — lech 95.62% slot entry tren 48 thang,
 * 77/78 entry so giay 242 (docs/AUDIT_GATE_DYN_PARITY.md). Nay chi con MOT bieu thuc.
 *
 * <p><b>Cong thuc — GIU NGUYEN TUNG PHEP NHAN, khong duoc "rut gon"</b>:
 * <pre>
 *   thr(symbolPred) = thrBase * max(DYN_MIN, (symbolPred / SCORE_BASE) * DYN_MULT)
 *   PASS  &lt;=&gt;  !(predReturn15M &lt; thr)
 * </pre>
 * Dang rut gon {@code predReturn15M >= K * symbolPred} voi {@code K = thrBase*DYN_MULT/SCORE_BASE}
 * = 0.0686720 **DA BI BAC BO** o docs/LEAN_GATE_AUDIT.md muc 3:
 * <ol>
 *   <li>floor {@code DYN_MIN} CO bind that (1 slot / 140,244 moc 15m x top-8 tren 48 thang:
 *       2024-08-05 13:30 GMT+7, symId 261, symbolPred 0.024885) => khong phai dong nhat thuc;</li>
 *   <li>nhan {@code float} KHONG ket hop: {@code base*((sp/RMAX)*MULT)} lech
 *       {@code (base*MULT/RMAX)*sp} co the 1 ULP — do duoc ngay tren tick do (rank2
 *       delta = -0.0000000) — va gate so sanh {@code >=} nen 1 ULP du doi mot quyet dinh.</li>
 * </ol>
 * Ai doi thu tu phep nhan o day = doi hanh vi da duoc kiem 48 thang. DUNG DOI.
 *
 * <p><b>Ba he so la HANG SO, co chu dich</b>: chung tung la {@code Configs.AI_DYNAMIC_MIN} /
 * {@code PREDICT_SYMBOL_RATE_MAX_THRESHOLD} / {@code AI_DYNAMIC_MULTIPLIER} doc qua key
 * {@code SIM_AI_DYNAMIC_*} — nhung KHONG profile/env nao tung khai bao chung (do o
 * docs/LEAN_GATE_AUDIT.md muc 2.3), tuc chung la hang so tra hinh cau hinh. Nay chot cung o day:
 * gate chi con DUNG MOT knob la {@code Configs.MIN_MOMENTUM_15M} (key {@code SIM_MIN_MOMENTUM_15M},
 * da co san trong {@code conf/env.sh} cua 242 => deploy KHONG phai sua env).
 *
 * <p><b>KHONG lien quan {@code Configs.AI_DYNAMIC_MAX}</b>: bien do la TRAN UNG VIEN o TANG 1
 * cua selector ({@code maxThres = PREDICT_SYMBOL_RATE_MAX_THRESHOLD * AI_DYNAMIC_MAX}), va tang 1
 * bi bo hoan toan khi {@code SELECTOR_RANK_TOPK > 0}. No khong bao gio la tran cua nguong nay.
 */
public final class EntryGate {

    /** Can DUOI cua he so nhan nguong (cu: {@code Configs.AI_DYNAMIC_MIN}). */
    public static final float DYN_MIN = 0.26787f;
    /** Mau so chuan hoa score selector (cu: {@code Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD}). */
    public static final float SCORE_BASE = 0.15f;
    /** He so nhan (cu: {@code Configs.AI_DYNAMIC_MULTIPLIER}). */
    public static final float DYN_MULT = 1.28760f;

    private EntryGate() {
    }

    /**
     * Nguong 15m THAT SU ap cho mot ung vien.
     *
     * @param thrBase    nguong co so = {@code Configs.MIN_MOMENTUM_15M}
     * @param symbolPred score selector cua coin; {@code null} = khong di qua sleeve selector
     *                   (BIG_DOWN / DCA_LEVEL1 / leg market-signal) => nguong CO SO, y nhu cu
     */
    public static float threshold(float thrBase, Float symbolPred) {
        if (symbolPred == null) return thrBase;
        float scale = (symbolPred / SCORE_BASE) * DYN_MULT;
        return thrBase * Math.max(DYN_MIN, scale);
    }

    /** Nguong voi {@code thrBase} lay thang tu cau hinh dang chay. */
    public static float threshold(Float symbolPred) {
        return threshold(Configs.MIN_MOMENTUM_15M, symbolPred);
    }

    /**
     * Quyet dinh cong entry. Viet dang {@code !(x < thr)} chu KHONG phai {@code x >= thr}:
     * hai dang khac nhau khi {@code predReturn15M} la NaN, va dang {@code <} la dang goc da chay
     * 48 thang ({@code AIRejectFilter.evaluate}).
     */
    public static boolean pass(float predReturn15M, float thrBase, Float symbolPred) {
        return !(predReturn15M < threshold(thrBase, symbolPred));
    }
}
