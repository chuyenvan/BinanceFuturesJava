package com.binance.chuyennd.tradecore;

import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * DUMP CAU HINH HIEU DUNG (2026-09-03): in TOAN BO field public static cua Configs sau khi da ap env,
 * + cac GIA TRI DAN XUAT (derived) ma logic thuc su dung nhung khong ai nhin thay,
 * + hash SHA-256 cua toan bo cau hinh de moi run tai lap duoc.
 * Chay: java -cp <jar> com.binance.chuyennd.tradecore.DumpConfig
 */
public class DumpConfig {
    public static void main(String[] args) throws Exception {
        List<String> rows = new ArrayList<>();
        for (Field f : Configs.class.getDeclaredFields()) {
            if (!Modifier.isPublic(f.getModifiers()) || !Modifier.isStatic(f.getModifiers())) continue;
            if (f.getName().equals("properties") || f.getName().equals("LOG")) continue;
            f.setAccessible(true);
            Object v = f.get(null);
            String s;
            if (v == null) s = "null";
            else if (v instanceof float[]) s = java.util.Arrays.toString((float[]) v);
            else if (v instanceof int[]) s = java.util.Arrays.toString((int[]) v);
            else if (v instanceof double[]) s = java.util.Arrays.toString((double[]) v);
            else if (v instanceof long[]) s = java.util.Arrays.toString((long[]) v);
            else if (v instanceof Object[]) s = java.util.Arrays.deepToString((Object[]) v);
            else s = String.valueOf(v);
            if (s.length() > 60) s = s.substring(0, 60) + "...";
            rows.add(String.format("%s=%s|%s|%s", f.getName(), s,
                    Modifier.isFinal(f.getModifiers()) ? "final" : "MUTABLE", f.getType().getSimpleName()));
        }
        Collections.sort(rows);
        StringBuilder sb = new StringBuilder();
        System.out.println("# ===== CAU HINH HIEU DUNG (effective config) =====");
        for (String r : rows) { System.out.println(r); sb.append(r).append('\n'); }

        System.out.println("# ===== GIA TRI DAN XUAT (derived) — thu logic THUC SU dung =====");
        float mm = Configs.MIN_MOMENTUM_15M, rmax = Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD;
        float mult = Configs.AI_DYNAMIC_MULTIPLIER, lo = Configs.AI_DYNAMIC_MIN, hi = Configs.AI_DYNAMIC_MAX;
        // TANG 1 — PRE-FILTER UNG VIEN (SimulatorMarketLevelTicker1MStopLoss: vong `if (score > maxThres) break`).
        //   AI_DYNAMIC_MAX lam viec o DAY: no la TRAN UNG VIEN, khong phai tran clamp cua nguong.
        float candMax = rmax * hi;
        System.out.printf("derived.candidate_score_max=%.5f (= rate_max %.5f x AI_DYNAMIC_MAX %.5f)%n"
                + "derived.candidate_note=coin co score > tran nay KHONG BAO GIO la ung vien, du nguong bao nhieu%n",
                candMax, rmax, hi);
        // TANG 2 — NGUONG DONG (AIRejectFilter.checkSignalDynamic): CHI con can duoi AI_DYNAMIC_MIN.
        //   Co OFF_FLAT_HARD da go 2026-09-03 => tran clamp KHONG con ton tai trong code.
        boolean noCap = true;
        System.out.printf("derived.gate_formula=%s%n",
                "min_mom * max(AI_DYNAMIC_MIN, score/rate_max*mult)   [KHONG CO TRAN]");
        for (float sc : new float[]{0.05f, 0.15f, 0.2494f, 0.30f, candMax}) {
            float raw = sc / rmax * mult;
            float cl = noCap ? Math.max(lo, raw) : Math.max(lo, Math.min(raw, hi));
            String tag = (raw < lo) ? "<-- CHAM SAN"
                    : (!noCap && raw > hi) ? "<-- CHAM TRAN"
                    : (Math.abs(sc - candMax) < 1e-6f) ? "<-- TRAN UNG VIEN (nguong CAO NHAT co the)" : "";
            System.out.printf("derived.gate_thr@score_%.4f=%.5f  (raw_scale=%.3f dung=%.3f) %s%n",
                    sc, mm * cl, raw, cl, tag);
        }
        System.out.printf("derived.cost_roundtrip=%.5f (fee %.5f x2 + slip %.5f x2)%n",
                2 * Configs.RATE_FEE + 2 * Configs.SLIPPAGE_RATE, Configs.RATE_FEE, Configs.SLIPPAGE_RATE);
        float arm = Configs.RATE_PROFIT_STOP_MARKET;

        // Trailing: duong DUY NHAT la TradeUtils.calRateLossDynamicBuyPNoPump
        //   maxGap = (symbolPred > TS_PNOPUMP_WEAK_THR) ? TS_MAX_GAP_WEAK : TS_MAX_GAP
        //   gap    = min(peak * TS_GIVEBACK_RATIO, maxGap)      [co TS_GIVEBACK_FLOOR/TS_MIN_GAP da go]
        //   SL     = round((peak - gap)/0.005)*0.005
        float rat = Configs.TS_GIVEBACK_RATIO;
        float gStrong = Math.min(arm * rat, Configs.TS_MAX_GAP);
        float gWeak = Math.min(arm * rat, Configs.TS_MAX_GAP_WEAK);
        System.out.printf("derived.arm_roi=%.4f | sl_at_arm STRONG(score<=%.2f)=%.4f | WEAK(score>%.2f)=%.4f%n"
                + "derived.trail_path=calRateLossDynamicBuyPNoPump (duy nhat) | giveback_ratio=%.2f"
                + " cap_strong=%.3f cap_weak=%.3f%n"
                + "derived.ratchet_gate=LIEN TUC (dead-zone x TS_PROFIT_MULTIPLIER da go)%n",
                arm, Configs.tsPnoPumpWeakThr(), arm - gStrong,
                Configs.tsPnoPumpWeakThr(), arm - gWeak,
                rat, Configs.TS_MAX_GAP, Configs.TS_MAX_GAP_WEAK);
        System.out.printf("derived.pre_arm_stop=%s%n",
                Configs.LOSER_TIME_STOP_HOURS > 0
                        ? "KHONG co SL cung truoc khi arm - loi ra duy nhat la time-stop "
                          + Configs.LOSER_TIME_STOP_HOURS + "h"
                        : "KHONG co SL va KHONG co time-stop truoc khi arm (!)");
        // SIM dung TradeUtils.managerBudget: THROTTLE LIEN TUC theo F_BASE/U_MAX (FROZEN v1 2026-08-24,
        //   thay logic vach roi rac BUDGET_MARGIN_RATIO_*/BUDGET_DIVIDER_* = overfit, nay DA CHET trong engine).
        //   budget = equity * F_BASE * clamp(1 - U/U_MAX,0,1) / dcaGridTotalWeight(), roi * DCA_GRID_SCALE * tier.
        // CAPITAL_START/NUMBER_ORDER_BUDGET la duong BudgetManager (LIVE), KHONG phai duong sim.
        float cap = Configs.capitalStart();
        float ladder = Configs.dcaGridTotalWeight() > 0f ? Configs.dcaGridTotalWeight() : 1f;
        System.out.printf("derived.sim_budget_formula=equity * F_BASE(%.4f) * (1-U/U_MAX(%.3f)) / ladder(%.2f) * DCA_GRID_SCALE(%.3f)%n",
                Configs.F_BASE, Configs.U_MAX, ladder, Configs.DCA_GRID_SCALE);
        System.out.printf("derived.sim_budget_max_at_U0=%.2f (= %.1f%% equity) | margin_ceiling_U_MAX=%.2f%n",
                cap * Configs.F_BASE / ladder * Configs.DCA_GRID_SCALE,
                100f * Configs.F_BASE / ladder * Configs.DCA_GRID_SCALE, cap * Configs.U_MAX);
        System.out.printf("derived.live_path_base_budget=%.2f (CAPITAL_START %.0f / NUMBER_ORDER_BUDGET %d — duong BudgetManager, KHONG phai sim)%n",
                cap / Configs.number_order_budget, cap, Configs.number_order_budget);

        MessageDigest md = MessageDigest.getInstance("SHA-256");
        byte[] h = md.digest(sb.toString().getBytes("UTF-8"));
        StringBuilder hex = new StringBuilder();
        for (int i = 0; i < 8; i++) hex.append(String.format("%02x", h[i]));
        System.out.println("# CONFIG_HASH=" + hex);
        // Bat key khai bao trong profile ma khong ai doc (go sai ten key -> am tham roi ve default).
        Cfg.auditProfile();
    }
}
