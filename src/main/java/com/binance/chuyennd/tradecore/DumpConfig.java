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
        System.out.printf("derived.gate_formula=%s%n", "min_mom * clamp(score/rate_max*mult, min, max)");
        for (float sc : new float[]{0.05f, 0.15f, 0.30f, 0.50f, 0.70f}) {
            float raw = sc / rmax * mult;
            float cl = Math.max(lo, Math.min(raw, hi));
            System.out.printf("derived.gate_thr@score_%.2f=%.5f  (raw_scale=%.3f clamped=%.3f %s)%n",
                    sc, mm * cl, raw, cl, (raw > hi ? "<-- CHAM TRAN" : (raw < lo ? "<-- CHAM SAN" : "")));
        }
        System.out.printf("derived.cost_roundtrip=%.5f (fee %.5f x2 + slip %.5f x2)%n",
                2 * Configs.RATE_FEE + 2 * Configs.SLIPPAGE_RATE, Configs.RATE_FEE, Configs.SLIPPAGE_RATE);
        float arm = Configs.RATE_PROFIT_STOP_MARKET;
        System.out.printf("derived.arm_roi=%.4f | sl_locked_at_arm=%.4f (giveback %.2f, cap strong %.3f/weak %.3f)%n",
                arm, arm - Math.min(arm * Configs.TS_GIVEBACK_RATIO, Configs.TS_MAX_GAP),
                Configs.TS_GIVEBACK_RATIO, Configs.TS_MAX_GAP, Configs.TS_MAX_GAP_WEAK);
        System.out.printf("derived.ratchet_gate=%s%n", Configs.TS_GIVEBACK_MODE || Configs.TS_RATCHET_DECOUPLED
                ? "LIEN TUC (giveback/decoupled)" : "DEAD-ZONE x" + Configs.TS_PROFIT_MULTIPLIER);

        MessageDigest md = MessageDigest.getInstance("SHA-256");
        byte[] h = md.digest(sb.toString().getBytes("UTF-8"));
        StringBuilder hex = new StringBuilder();
        for (int i = 0; i < 8; i++) hex.append(String.format("%02x", h[i]));
        System.out.println("# CONFIG_HASH=" + hex);
    }
}
