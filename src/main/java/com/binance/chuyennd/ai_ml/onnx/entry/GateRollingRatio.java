package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.tradecore.Cfg;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.EntryGate;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Date;
import java.util.Map;
import java.util.TreeMap;

/**
 * GATE ROLLING "ĐỀU LỆNH" (GDV2 — docs/prereg/PREREG_GDV2_EVEN.md) — nhánh SIM.
 *
 * <p>Khác {@code GateRollingThreshold} (GD92): thay vì phân vị cuộn trên **p15** rồi nhân hệ số per-coin,
 * class này tính phân vị cuộn trên **CHÍNH TỈ SỐ `r`**:
 * <pre>
 *   r = p15 / (max(DYN_MIN, sp/SCORE_BASE * DYN_MULT) * GATE_DYN_SCALE)
 * </pre>
 * r đã chuẩn hoá theo score selector ⇒ tỉ lệ pass gần hằng số theo thời gian (đều lệnh).
 * PASS &lt;=&gt; r &gt; q_t, với q_t = phân vị `pct` của buffer `r` CAUSAL (cửa sổ W ngày, tính mỗi giờ).
 *
 * <p><b>Vì `r` cần `symbolPred` chỉ có lúc chạy ⇒ buffer được dựng ONLINE</b> (khác GD92 precompute từ
 * predictionMap). Chỉ áp cho nhánh PREDICT_SYMBOL_TRADE (`sp != null`); BIG_DOWN / DCA_LEVEL1 giữ base 0.008.
 *
 * <p>Key (qua {@link Cfg}): {@code SIM_GATE_ROLLING_MODE=ratio} (bật), {@code SIM_GATE_ROLLING_PCT} (0..1),
 * {@code SIM_GATE_ROLLING_DAYS} (mặc định 90). Key vắng / pct ngoài (0,1) ⇒ {@code isOn()=false}
 * ⇒ byte-identical (parity G0).
 *
 * <p>Warm-up: trước khi buffer đủ 7 ngày dữ liệu ⇒ fallback {@code Configs.MIN_MOMENTUM_15M} (đếm nBeforeFirst).
 *
 * <p>Lõi quantile dùng CHUNG {@link GateRatioBuffer} với {@link LiveGateRollingRatio} ⇒ q_t và quyết định
 * pass bit-identical giữa sim và live.
 */
public final class GateRollingRatio {
    private static final Logger LOG = LoggerFactory.getLogger(GateRollingRatio.class);

    private static boolean inited = false;
    private static boolean on = false;
    private static float pct = 0f;
    private static int days = 90;

    private static final GateRatioBuffer buffer = new GateRatioBuffer();
    private static boolean warnedBeforeFirst = false;

    // bộ đếm ρ (PREDICT candidates) — LUÔN chạy (kể cả G0 parity), không đổi hành vi
    private static long predictSeen = 0;
    private static long predictPass = 0;
    private static final TreeMap<String, long[]> quarterCounts = new TreeMap<>(); // "YYYYQn" -> {seen, pass}
    // [GATE_QUOTA_SKIPFULL 2026-10-04] docs/prereg/PREREG_GATE_QUOTA_SKIPFULL.md: so ung vien PREDICT bi bo qua vi so day (chi in khi key bat)
    private static long predictSkipFull = 0;

    private GateRollingRatio() {
    }

    /** Đọc cấu hình một lần (idempotent). Gọi đầu run. */
    public static synchronized void init() {
        if (inited) return;
        inited = true;
        if (Configs.GATE_QUOTA_SKIP_WHEN_FULL) {
            LOG.warn("*** [GATE-QUOTA] SKIP_WHEN_FULL=ON: so day (managerBudget null) => khong nap r, khong tinh pass ***");
        }
        String mode = Cfg.get("SIM_GATE_ROLLING_MODE");
        if (!"ratio".equalsIgnoreCase(mode == null ? "" : mode.trim())) {
            on = false;
            return;
        }
        String p = Cfg.get("SIM_GATE_ROLLING_PCT");
        if (p == null || p.trim().isEmpty()) {
            LOG.warn("[GATE-RATIO] SIM_GATE_ROLLING_MODE=ratio nhưng thiếu SIM_GATE_ROLLING_PCT -> TAT");
            return;
        }
        pct = Float.parseFloat(p.trim());
        if (pct <= 0f || pct >= 1f) {
            LOG.warn("[GATE-RATIO] SIM_GATE_ROLLING_PCT={} ngoài (0,1) -> TAT", pct);
            on = false;
            return;
        }
        String d = Cfg.get("SIM_GATE_ROLLING_DAYS");
        if (d != null && !d.trim().isEmpty()) days = Integer.parseInt(d.trim());
        on = true;
        LOG.warn("*** [GATE-RATIO] BAT: mode=ratio pct={} window={}d | warm-up 7d | quantile tren TY SO r ***",
                String.format("%.8f", pct), days);
    }

    public static boolean isOn() {
        return on;
    }

    /** Đếm 1 candidate PREDICT đã qua điểm gate. LUÔN chạy (G0 parity cũng đếm để đo ρ). */
    public static synchronized void noteCandidate(long ts) {
        predictSeen++;
        long[] c = quarterCounts.computeIfAbsent(quarterOf(ts), k -> new long[2]);
        c[0]++;
    }

    /** [GATE_QUOTA_SKIPFULL 2026-10-04] docs/prereg/PREREG_GATE_QUOTA_SKIPFULL.md: dem 1 ung vien PREDICT bi bo qua vi so day (khong nap r, khong pass). */
    public static synchronized void noteSkipFull(long ts) {
        predictSkipFull++;
    }

    /** Đếm 1 candidate PREDICT PASS gate. LUÔN chạy. */
    public static synchronized void notePass(long ts) {
        predictPass++;
        long[] c = quarterCounts.get(quarterOf(ts));
        if (c != null) c[1]++;
    }

    /**
     * Nguồn thrBase cho nhánh PREDICT (sp != null) khi GDV2 bật.
     * Trả về q_t (phân vị cuộn của r, hoặc base nếu warm-up). Đồng thời nạp (ts, r) vào buffer causal.
     */
    public static float threshold(long ts, float p15, float sp) {
        float factor = Math.max(EntryGate.DYN_MIN, (sp / EntryGate.SCORE_BASE) * EntryGate.DYN_MULT);
        float gs = EntryGate.GATE_REGIME_ADAPTIVE ? EntryGate.CURRENT_REGIME_SCALE : EntryGate.GATE_DYN_SCALE;
        float r = p15 / (factor * gs);
        float q = buffer.addAndQuery(ts, r, pct, days, Configs.MIN_MOMENTUM_15M);
        if (!warnedBeforeFirst && buffer.nBeforeFirst() > 0) {
            warnedBeforeFirst = true;
            LOG.warn("[GATE-RATIO] truy vấn TRƯỚC khi đủ 7 ngày dữ liệu (m={}) -> fallback base {}",
                    buffer.size(), Configs.MIN_MOMENTUM_15M);
        }
        return q;
    }

    /**
     * [GKF-PHASE3 2026-10-07] docs/prereg/PREREG_GATE_K_FRONTIER.md §7 — như {@link #threshold} nhưng
     * KHÔNG nạp {@code (ts,r)} vào buffer (dùng cho hạng &gt; {@code Configs.GATE_BUFFER_TOPK}).
     * Dùng CÙNG q_t nền ⇒ quota/q_t KHÔNG đổi; chỉ cho hạng sâu vào lệnh nếu tự vượt q_t.
     */
    public static float thresholdCheckOnly(long ts, float p15, float sp) {
        float factor = Math.max(EntryGate.DYN_MIN, (sp / EntryGate.SCORE_BASE) * EntryGate.DYN_MULT);
        float gs = EntryGate.GATE_REGIME_ADAPTIVE ? EntryGate.CURRENT_REGIME_SCALE : EntryGate.GATE_DYN_SCALE;
        float r = p15 / (factor * gs);
        return buffer.queryOnly(ts, r, pct, days, Configs.MIN_MOMENTUM_15M);
    }

    /** Lõi: tính (nếu qua giờ mới) q cho giờ của ts, trả q, rồi nạp (ts, r) — package-private cho unit test. */
    static float addAndQuery(long ts, float r) {
        return buffer.addAndQuery(ts, r, pct, days, Configs.MIN_MOMENTUM_15M);
    }

    /** Chỉ dùng cho unit test: bật ratio với pct/days cụ thể và reset toàn bộ state. */
    static void configureForTest(float pctValue, int daysValue) {
        init();
        on = true;
        pct = pctValue;
        days = daysValue;
        buffer.reset();
        warnedBeforeFirst = false;
        predictSeen = predictPass = 0;
        predictSkipFull = 0;
        quarterCounts.clear();
    }

    static int bufferSizeForTest() {
        return buffer.size();
    }

    static long passForTest() {
        return predictPass;
    }

    static long seenForTest() {
        return predictSeen;
    }

    static long skipFullForTest() {
        return predictSkipFull;
    }

    /** "YYYYQn" theo GMT+7 (khớp printDone.csv dùng Utils.sdf* GMT+7). */
    public static String quarterOf(long ts) {
        String ym = Utils.sdfMonth.format(new Date(ts));       // "202109"
        int y = Integer.parseInt(ym.substring(0, 4));
        int mo = Integer.parseInt(ym.substring(4, 6));
        return y + "Q" + ((mo - 1) / 3 + 1);
    }

    /** Thống kê ρ + per-quarter cho log cuối run. */
    public static String stats() {
        StringBuilder sb = new StringBuilder();
        double rho = predictSeen > 0 ? (double) predictPass / (double) predictSeen : Double.NaN;
        sb.append(String.format("GATE-RATIO %s pct=%.8f days=%d seen=%d pass=%d rho=%.8f query=%d beforeFirst=%d",
                on ? "on" : "off", pct, days, predictSeen, predictPass, rho, buffer.nQuery(), buffer.nBeforeFirst()));
        for (Map.Entry<String, long[]> e : quarterCounts.entrySet()) {
            sb.append(String.format(" | %s:%d/%d", e.getKey(), e.getValue()[1], e.getValue()[0]));
        }
        if (Configs.GATE_QUOTA_SKIP_WHEN_FULL) sb.append(" | skipFull=").append(predictSkipFull);
        return sb.toString();
    }
}
