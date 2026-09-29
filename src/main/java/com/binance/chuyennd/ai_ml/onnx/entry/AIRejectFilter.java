package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.EntryGate;

import java.util.concurrent.atomic.AtomicInteger;

/**
 * Loc tin hieu entry dua tren AI prediction.
 *
 * <p>2026-09-03: filter chi con MOT cong duy nhat = MOM15 (nguong dong theo score selector).
 * Nhanh RISK/DD4H bo 2026-08-08; cac co FILTER_MODE / gate-market-off / gate-rolling xoa 2026-09-03.
 *
 * <p><b>L7 (2026-09-11, docs/experiment/L7_LEAN_GATE.md)</b>: cong thuc nguong da chuyen han sang
 * {@link EntryGate} — MOT bieu thuc cho ca sim va live. Lop nay chi con lam vo boc:
 * doi bool cua {@link EntryGate#pass} thanh {@link FilterResult} + dem counter cho ablation.
 * Ba thu da XOA o ban nay:
 * <ul>
 *   <li>{@code checkSignalDynamic} — ban sao thu hai cua cung cong thuc;</li>
 *   <li>{@code checkSignal} — nhanh "gate phang" rieng; nay la truong hop {@code symbolPred == null}
 *       cua cung mot ham, khong con duong code rieng de troi;</li>
 *   <li>nhanh EARLY-HARD-GATE ({@code p15 < thrBase && symbolPred > RATE_MAX} => REJECT) —
 *       CHUNG MINH GIAI TICH la THUA (docs/audit/LEAN_GATE_AUDIT.md muc 3.4): no chi fire khi
 *       {@code symbolPred > 0.15}, luc do {@code thr = base*max(0.26787, sp/0.15*1.2876)
 *       > 1.2876*base > base > p15} nen {@code evaluate} cung tra REJECT. Dung voi MOI input,
 *       khong can du lieu. Bo no chi doi chuoi {@code reason} trong log va bo counter
 *       {@code earlyHardGateReject}; {@code mom15RejectCount} tang dung 1 lan o ca hai duong.</li>
 * </ul>
 */
public class AIRejectFilter {
    public enum FilterDecision {PASS, REJECT}

    public static class FilterResult {
        public FilterDecision decision;
        public String reason;

        public FilterResult(FilterDecision decision, String reason) {
            this.decision = decision;
            this.reason = reason;
        }
    }

    /** Dem so REJECT do gate MOM15 trong mot ablation run. Reset bang resetCounters() truoc moi run. */
    public static final AtomicInteger mom15RejectCount = new AtomicInteger(0);

    /** Reset counter truoc moi ablation run. */
    public static void resetCounters() {
        mom15RejectCount.set(0);
    }

    /**
     * CONG ENTRY TANG 2 — mot cho duy nhat quyet dinh gate cho ca SIM va LIVE.
     *
     * <p>Quy tac: {@code predictSymbolTrade} (= levelChange PREDICT_SYMBOL_TRADE) VA
     * {@code symbolPred != null} => nguong DONG; moi truong hop con lai (BIG_DOWN, DCA_LEVEL1,
     * leg market-signal, hoac thieu symbolPred) => nguong CO SO, hanh vi KHONG doi.
     *
     * @param predictSymbolTrade leg nay den tu sleeve selector PREDICT_SYMBOL_TRADE
     */
    public FilterResult entryGate(AiPredictionData prediction, Float symbolPred, boolean predictSymbolTrade) {
        Float sp = predictSymbolTrade ? symbolPred : null;
        // [GDV2-EVEN 2026-09-29] docs/prereg/PREREG_GDV2_EVEN.md — quantile cuon tren CHINH TY SO r.
        //   Bo dem rho (PREDICT) LUON chay (ke ca parity G0), khong doi hanh vi gate.
        if (predictSymbolTrade) {
            GateRollingRatio.noteCandidate(prediction.timestamp);
        }
        // [GD92-RECHECK 2026-09-15] phuc hoi nguong TRUOT theo phan vi (docs/PREREG_GD92_RECHECK.md).
        //   Ban cu f1c43a3^ bom o AIRejectFilter.thres15M = DUNG cho nguong CO SO nay.
        //   Key SIM_GATE_ROLLING_PCT khong khai bao -> isOn()=false -> bieu thuc y het HEAD
        //   -> byte-identical (cong parity GD_PARITY_C3).
        float thrBase;
        if (GateRollingRatio.isOn() && sp != null) {
            // GDV2: nguong cuon tren ty so r (chi nhanh PREDICT).
            thrBase = GateRollingRatio.threshold(prediction.timestamp, prediction.predReturn15M, sp);
        } else if (GateRollingThreshold.isOn()) {
            thrBase = GateRollingThreshold.threshold(prediction.timestamp);
        } else {
            thrBase = Configs.MIN_MOMENTUM_15M;
        }
        FilterResult res = evaluate(prediction.predReturn15M, EntryGate.threshold(thrBase, sp));
        if (predictSymbolTrade && res.decision == FilterDecision.PASS) {
            GateRollingRatio.notePass(prediction.timestamp);
        }
        return res;
    }

    /** Giu signature cu de khong vo caller (BackTestEngineCombined/MarketThresholds/BenchmarkSpeedTest) —
     *  {@code risk} chi con ghi vao HARD_RISK_LIMIT_4H (field da xoa) cho log/HPO doc, KHONG con dung de loc. */
    public void setConfig(float risk, float min15m) {
        // `risk` KHONG con duoc dung o dau ca (nhanh RISK/DD4H bo 2026-08-08, field xoa 2026-09-03);
        // giu tham so de khong phai sua 3 call-site HPO.
        Configs.MIN_MOMENTUM_15M = min15m;
    }

    /**
     * LOGIC DANH GIA LOI — chi con nhanh MOM15. Nhanh RISK (DD4H/predRisk4H) da bo han 2026-08-08:
     * predRisk4H khong con model dung sau (carry-forward tu gate cu), dung lam la chan live la rui ro gia.
     */
    private FilterResult evaluate(float pred15M, float thres15M) {
        if (pred15M < thres15M) {
            mom15RejectCount.incrementAndGet();
            return new FilterResult(FilterDecision.REJECT,
                    String.format("BAD MOMENTUM: 15M chua nay manh (%.2f%% < %.2f%%)", pred15M * 100, thres15M * 100));
        }
        return new FilterResult(FilterDecision.PASS,
                String.format("PERFECT: 15M(%.2f%%)", pred15M * 100));
    }

}
