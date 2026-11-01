package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.tradecore.Cfg;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.EntryGate;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.io.IOException;
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

    // [GATE_SEED_DUMP 2026-10-31] docs/prereg/PREREG_PARITY_V12_DRY_ADDENDUM3.md: ghi buffer (GRR1) tai moc + trace (ts,sp,p15,r).
    //   Key tat (mac dinh) => khong doc/ghi gi them => byte-identical.
    private static String dumpFile = null;
    private static long dumpAt = Long.MAX_VALUE;
    private static boolean dumped = false;
    private static String traceFile = null;
    private static long traceFrom = Long.MAX_VALUE;
    private static long traceTo = Long.MIN_VALUE;
    private static BufferedWriter traceW = null;
    private static long traceN = 0;

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
        initSeedDump();
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
        if (dumpFile != null || traceFile != null) seedHook(ts, sp, p15, r);
        float q = buffer.addAndQuery(ts, r, pct, days, Configs.MIN_MOMENTUM_15M);
        if (!warnedBeforeFirst && buffer.nBeforeFirst() > 0) {
            warnedBeforeFirst = true;
            LOG.warn("[GATE-RATIO] truy vấn TRƯỚC khi đủ 7 ngày dữ liệu (m={}) -> fallback base {}",
                    buffer.size(), Configs.MIN_MOMENTUM_15M);
        }
        return q;
    }

    /** [GATE_SEED_DUMP] doc key SIM_GATE_DUMP_FILE/AT (ms UTC) va SIM_GATE_TRACE_FILE/FROM/TO (ms UTC, [from,to)). */
    private static void initSeedDump() {
        String f = Cfg.get("SIM_GATE_DUMP_FILE");
        String a = Cfg.get("SIM_GATE_DUMP_AT");
        if (f != null && !f.trim().isEmpty() && a != null && !a.trim().isEmpty()) {
            dumpFile = f.trim();
            dumpAt = Long.parseLong(a.trim());
            LOG.warn("*** [GATE-SEED] dump buffer -> {} tai truy van dau tien ts >= {} (hoac cuoi run neu chua toi) ***", dumpFile, dumpAt);
            try {
                Runtime.getRuntime().addShutdownHook(new Thread(GateRollingRatio::finalDump, "GateSeedFinalDump"));
            } catch (Exception ignore) {
            }
        }
        String t = Cfg.get("SIM_GATE_TRACE_FILE");
        String tf = Cfg.get("SIM_GATE_TRACE_FROM");
        String tt = Cfg.get("SIM_GATE_TRACE_TO");
        if (t != null && !t.trim().isEmpty() && tf != null && tt != null) {
            traceFile = t.trim();
            traceFrom = Long.parseLong(tf.trim());
            traceTo = Long.parseLong(tt.trim());
            LOG.warn("*** [GATE-SEED] trace (ts,sp,p15,r) -> {} cho ts in [{}, {}) ***", traceFile, traceFrom, traceTo);
            try {
                Runtime.getRuntime().addShutdownHook(new Thread(GateRollingRatio::closeTrace, "GateSeedTraceFlush"));
            } catch (Exception ignore) {
            }
        }
    }

    /** [GATE_SEED_DUMP] goi TRUOC khi nap (ts, r): dump = moi record ts &lt; dumpAt va ts &gt;= dumpAt - days. */
    static synchronized void seedHook(long ts, float sp, float p15, float r) {
        if (dumpFile != null && !dumped && ts >= dumpAt) {
            doDump("moc");
        }
        if (traceFile != null && ts >= traceFrom && ts < traceTo) {
            try {
                if (traceW == null) {
                    traceW = new BufferedWriter(new FileWriter(traceFile, false));
                    traceW.write("ts,sp,p15,r\n");
                }
                traceW.write(ts + "," + Float.toString(sp) + "," + Float.toString(p15) + "," + Float.toString(r) + "\n");
                if (++traceN % 4096 == 0) traceW.flush();
            } catch (IOException e) {
                LOG.error("[GATE-SEED] LOI trace {}: {}", traceFile, e.getMessage());
            }
        }
    }

    /** [GATE_SEED_DUMP] ghi moi record ts in [dumpAt - days, dumpAt) (buffer sort ts tang). */
    static synchronized void doDump(String why) {
        if (dumpFile == null || dumped) return;
        dumped = true;
        long[] a = buffer.tsSnapshot();
        float[] b = buffer.rSnapshot();
        long cut = dumpAt - (long) days * 86_400_000L;
        int lo = 0;
        while (lo < a.length && a[lo] < cut) lo++;
        int hi = lo;
        while (hi < a.length && a[hi] < dumpAt) hi++;
        long[] a2 = java.util.Arrays.copyOfRange(a, lo, hi);
        float[] b2 = java.util.Arrays.copyOfRange(b, lo, hi);
        try {
            GateRatioPersist.writeFresh(dumpFile, a2, b2);
            LOG.warn("[GATE-SEED] DA GHI ({}) {} record ({}..{}) -> {}", why, a2.length,
                    a2.length > 0 ? a2[0] : -1, a2.length > 0 ? a2[a2.length - 1] : -1, dumpFile);
        } catch (IOException e) {
            LOG.error("[GATE-SEED] LOI ghi {}: {}", dumpFile, e.getMessage());
        }
    }

    /** [GATE_SEED_DUMP] shutdown hook: run ket thuc truoc moc => dump buffer cuoi run (ts &lt; dumpAt). */
    static void finalDump() {
        doDump("cuoi-run");
        closeTrace();
    }

    /** [GATE_SEED_DUMP] dong trace (shutdown hook / cuoi run / test). */
    static synchronized void closeTrace() {
        if (traceW != null) {
            try {
                traceW.flush();
                traceW.close();
                LOG.warn("[GATE-SEED] trace dong: {} dong -> {}", traceN, traceFile);
            } catch (IOException ignore) {
            }
            traceW = null;
        }
    }

    /** [GATE_SEED_DUMP] chi cho unit test. */
    static synchronized void configureSeedForTest(String dFile, long dAt, String tFile, long tFrom, long tTo) {
        closeTrace();
        dumpFile = dFile; dumpAt = dAt; dumped = false;
        traceFile = tFile; traceFrom = tFrom; traceTo = tTo; traceN = 0;
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
