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

    // [NUP-TIER2 2026-10-26] docs/prereg/PREREG_NUP.md §1.2. Mac dinh TAT => khong nhanh nao chay.
    private static boolean tier2On = false;
    private static float tier2Pct = 0.99985f;
    // q2 cache theo GIO: chi tinh 1 lan/gio trong threshold(), khong tinh lai moi candidate.
    private static float currentTier2Q = Float.NaN;
    private static final float[] t2q = new float[2];
    // [NUP3-SLEEVE 2026-10-26] true <=> q2 dang phuc vu so sleeve (khong phai TIER2 cua NUP).
    private static boolean sleeveQ2 = false;

    private static final GateRatioBuffer buffer = new GateRatioBuffer();

    // [R3-G3 MTF-OR 2026-11-10] docs/prereg/PREREG_R3_GATE_FAMILY.md (b901016e) §2 G3: khung 1' (p15 diem) + khung W'
    //   (mean causal p15 tren [t-(W-1)', t], can >= MINCOV phut), MOI khung 1 buffer r rieng, pct_w = float32(1 - c*(1 - pct)).
    //   PASS <=> qua khung 1 HOAC qua khung W. Key SIM_GATE_MTF_W vang => TAT => duong cu nguyen ven (byte-identical).
    private static boolean mtfOn = false;
    private static int mtfW = 15;
    private static int mtfMinCov = 12;
    private static float mtfC = 0.5f;
    private static float mtfPct = 0f;
    private static final GateRatioBuffer bufferW = new GateRatioBuffer();
    private static java.util.NavigableMap<Long, com.binance.chuyennd.ai_ml.onnx.AiPredictionData> p15Src = null;
    private static long mtfPass1 = 0, mtfPassW = 0, mtfPassBoth = 0, mtfNoCov = 0;

    // [R3B SMOOTH 2026-11-11] docs/prereg/PREREG_R3B_SMOOTH_ISO.md (3ea5df40): key SIM_GATE_P15_SMOOTH=W:minCov — nhanh PREDICT
    //   dung p~ = mean causal p15 [t-(W-1)', t] (>= minCov phut) thay p15 diem cho r/buffer/so nguong; thieu phu => REJECT, khong nap.
    //   DCA_LEVEL1 (sp=null) giu p15 diem. Key vang => TAT => byte-identical.
    private static boolean smoothOn = false;
    private static int smoothW = 60;
    private static int smoothMinCov = 48;
    private static long smoothNoCov = 0;
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
        initMtf();
        initSmooth();
        // [NUP-TIER2] doc key rieng; mac dinh TAT. Key chi co tac dung khi gate ratio ON.
        String t2 = Cfg.get("GATE_TIER2_ENABLED");
        tier2On = t2 != null && Boolean.parseBoolean(t2.trim());
        String t2p = Cfg.get("GATE_TIER2_PCT");
        if (t2p != null && !t2p.trim().isEmpty()) tier2Pct = Float.parseFloat(t2p.trim());
        if (tier2On) {
            if (tier2Pct <= 0f || tier2Pct >= 1f || tier2Pct >= pct) {
                LOG.warn("[GATE-TIER2] pct={} khong hop le (phai 0<pct<gate pct={}) -> TAT", tier2Pct, pct);
                tier2On = false;
            } else {
                LOG.warn("*** [GATE-TIER2] BAT: pct={} (gate chinh {}) | chi PREDICT, U<{}, crash>{} | size x{} ***",
                        String.format("%.8f", tier2Pct), String.format("%.8f", pct),
                        Configs.GATE_TIER2_U_MAX, Configs.GATE_TIER2_CRASH_RET, Configs.GATE_TIER2_SIZE_MULT);
            }
        }
        // [NUP3-SLEEVE 2026-10-26] docs/prereg/PREREG_NUP3.md §2: q2 = phan vi SLEEVE_PCT tren CUNG buffer r, tinh MOT
        //   lan/gio boi CUNG co che TIER2 (addAndQuery2: q1 y het addAndQuery, q2 chi doc ban sao scratch).
        //   KHONG bat Configs.GATE_TIER2_ENABLED => duong createOrder cua so nen khong co nhanh tier2. TAT => khong lam gi.
        if (Configs.SLEEVE_ENABLED) {
            if (tier2On) {
                throw new IllegalStateException("[NUP3-SLEEVE] GATE_TIER2_ENABLED va SLEEVE_ENABLED khong duoc bat cung luc");
            }
            if (!(Configs.SLEEVE_PCT > 0f && Configs.SLEEVE_PCT < pct)) {
                throw new IllegalStateException("[NUP3-SLEEVE] SLEEVE_PCT=" + Configs.SLEEVE_PCT
                        + " phai trong (0, gate pct=" + pct + ")");
            }
            tier2On = true;
            tier2Pct = Configs.SLEEVE_PCT;
            sleeveQ2 = true;
            LOG.warn("*** [NUP3-SLEEVE] q2 BAT: pct={} (gate chinh {}) | chi doc, khong nap r, khong quota ***",
                    String.format("%.8f", tier2Pct), String.format("%.8f", pct));
        }
    }

    /** [R3-G3] doc key MTF (chi khi gate ratio BAT). Sai cau hinh => fail-fast. */
    private static void initMtf() {
        String w = Cfg.get("SIM_GATE_MTF_W");
        if (w == null || w.trim().isEmpty()) {
            mtfOn = false;
            return;
        }
        mtfW = Integer.parseInt(w.trim());
        String c = Cfg.get("SIM_GATE_MTF_C");
        String mc = Cfg.get("SIM_GATE_MTF_MINCOV");
        if (c == null || c.trim().isEmpty() || mc == null || mc.trim().isEmpty()) {
            throw new IllegalStateException("[R3-G3] SIM_GATE_MTF_W dat nhung thieu SIM_GATE_MTF_C / SIM_GATE_MTF_MINCOV");
        }
        mtfC = Float.parseFloat(c.trim());
        mtfMinCov = Integer.parseInt(mc.trim());
        if (mtfW < 2 || mtfMinCov < 1 || mtfMinCov > mtfW || !(mtfC > 0f && mtfC <= 1f)) {
            throw new IllegalStateException("[R3-G3] tham so MTF sai W=" + mtfW + " minCov=" + mtfMinCov + " c=" + mtfC);
        }
        if (tier2On || Configs.SLEEVE_ENABLED) {
            throw new IllegalStateException("[R3-G3] MTF khong duoc bat cung TIER2/SLEEVE");
        }
        mtfPct = (float) (1.0 - (double) mtfC * (1.0 - (double) pct));
        mtfOn = true;
        LOG.warn("*** [R3-G3 MTF-OR] BAT: khung 1' + {}' (minCov {}), c={} => pct_w={} (gate pct {}) | buffer rieng moi khung ***",
                mtfW, mtfMinCov, mtfC, String.format("%.10f", mtfPct), String.format("%.10f", pct));
    }

    /** [R3B] doc SIM_GATE_P15_SMOOTH=W:minCov (chi khi gate ratio BAT). Khong duoc bat cung MTF. */
    private static void initSmooth() {
        String v = Cfg.get("SIM_GATE_P15_SMOOTH");
        if (v == null || v.trim().isEmpty()) {
            smoothOn = false;
            return;
        }
        String[] a = v.trim().split(":");
        if (a.length != 2) throw new IllegalStateException("[R3B] SIM_GATE_P15_SMOOTH phai dang W:minCov, nhan " + v);
        smoothW = Integer.parseInt(a[0].trim());
        smoothMinCov = Integer.parseInt(a[1].trim());
        if (smoothW < 2 || smoothMinCov < 1 || smoothMinCov > smoothW) {
            throw new IllegalStateException("[R3B] tham so smooth sai W=" + smoothW + " minCov=" + smoothMinCov);
        }
        if (mtfOn || tier2On || Configs.SLEEVE_ENABLED) {
            throw new IllegalStateException("[R3B] SMOOTH khong duoc bat cung MTF/TIER2/SLEEVE");
        }
        smoothOn = true;
        LOG.warn("*** [R3B SMOOTH] BAT: p15 PREDICT = mean causal {}' (minCov {}) | pct gate {} ***",
                smoothW, smoothMinCov, String.format("%.10f", pct));
    }

    /** [R3B] smooth bat (gate ratio BAT + SIM_GATE_P15_SMOOTH). */
    public static boolean smoothOn() {
        return on && smoothOn;
    }

    /** [R3B] p~ cho nhanh PREDICT (NaN neu thieu phu; dem noCov). */
    public static synchronized float smoothP15ForGate(long ts) {
        float v = smoothedP15(ts, smoothW, smoothMinCov);
        if (Float.isNaN(v)) smoothNoCov++;
        return v;
    }

    static void configureSmoothForTest(int w, int minCov) {
        smoothW = w;
        smoothMinCov = minCov;
        smoothOn = true;
        smoothNoCov = 0;
    }

    static void disableSmoothForTest() {
        smoothOn = false;
    }

    /** [R3-G3] MTF bat (gate ratio BAT + SIM_GATE_MTF_W). */
    public static boolean mtfOn() {
        return on && mtfOn;
    }

    /** [R3-G3] nguon p15 THEO PHUT cua sim (predictionMap) — bat buoc khi MTF bat. */
    public static void setP15Source(java.util.NavigableMap<Long, com.binance.chuyennd.ai_ml.onnx.AiPredictionData> src) {
        p15Src = src;
    }

    /** [R3-G3] mean causal p15 tren [ts-(W-1)', ts] (gom ts, theo thoi gian that); < minCov gia tri huu han => NaN. */
    static float smoothedP15(long ts) {
        return smoothedP15(ts, mtfW, mtfMinCov);
    }

    /** mean causal p15 tren [ts-(w-1)', ts]; < minCov gia tri huu han => NaN (dung chung G3/R3B). */
    static float smoothedP15(long ts, int w, int minCov) {
        if (p15Src == null) throw new IllegalStateException("[R3-G3/R3B] chua setP15Source");
        double s = 0.0;
        int n = 0;
        for (com.binance.chuyennd.ai_ml.onnx.AiPredictionData d
                : p15Src.subMap(ts - (long) (w - 1) * 60_000L, true, ts, true).values()) {
            if (d == null || !Float.isFinite(d.predReturn15M)) continue;
            s += (double) d.predReturn15M;
            n++;
        }
        return n >= minCov ? (float) (s / n) : Float.NaN;
    }

    /**
     * [R3-G3] quyet dinh MTF-OR cho 1 ung vien PREDICT: nap r1 (p15 diem) vao buffer khung 1 va rW (p15 mean) vao buffer khung W
     * (chi khi du phu), moi buffer q rieng voi pct_w, causal theo gio nhu {@link GateRatioBuffer#addAndQuery}.
     * PASS <=> !(p15 < q1*fac*gs) || !(pW < qW*fac*gs).
     */
    public static synchronized boolean mtfPass(long ts, float p15, float sp) {
        float factor = Math.max(EntryGate.DYN_MIN, (sp / EntryGate.SCORE_BASE) * EntryGate.DYN_MULT);
        float gs = EntryGate.GATE_REGIME_ADAPTIVE ? EntryGate.CURRENT_REGIME_SCALE : EntryGate.GATE_DYN_SCALE;
        if (!Float.isFinite(p15)) return false;
        float r1 = p15 / (factor * gs);
        float q1 = buffer.addAndQuery(ts, r1, mtfPct, days, Configs.MIN_MOMENTUM_15M);
        boolean pass1 = !(p15 < EntryGate.threshold(q1, sp));
        boolean passW = false;
        float pw = smoothedP15(ts);
        if (Float.isNaN(pw)) {
            mtfNoCov++;
        } else {
            float rw = pw / (factor * gs);
            float qw = bufferW.addAndQuery(ts, rw, mtfPct, days, Configs.MIN_MOMENTUM_15M);
            passW = !(pw < EntryGate.threshold(qw, sp));
        }
        if (pass1) mtfPass1++;
        if (passW) mtfPassW++;
        if (pass1 && passW) mtfPassBoth++;
        return pass1 || passW;
    }

    /** Chi dung cho unit test: bat MTF voi tham so cu the + reset buffer khung W va bo dem. */
    static void configureMtfForTest(int w, int minCov, float c) {
        mtfW = w;
        mtfMinCov = minCov;
        mtfC = c;
        mtfPct = (float) (1.0 - (double) c * (1.0 - (double) pct));
        mtfOn = true;
        bufferW.reset();
        mtfPass1 = mtfPassW = mtfPassBoth = mtfNoCov = 0;
    }

    static void disableMtfForTest() {
        mtfOn = false;
        p15Src = null;
    }

    static float mtfPctForTest() {
        return mtfPct;
    }

    /** [NUP3-SLEEVE] q2 sleeve san sang (gate ratio BAT + SLEEVE_ENABLED da bat q2 trong init()). */
    public static boolean sleeveQ2On() {
        return on && tier2On && sleeveQ2;
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
        float q;
        if (tier2On) {
            buffer.addAndQuery2(ts, r, pct, tier2Pct, days, Configs.MIN_MOMENTUM_15M, t2q);
            q = t2q[0];
            if (!Float.isNaN(t2q[1])) currentTier2Q = t2q[1];
        } else {
            q = buffer.addAndQuery(ts, r, pct, days, Configs.MIN_MOMENTUM_15M);
        }
        if (!warnedBeforeFirst && buffer.nBeforeFirst() > 0) {
            warnedBeforeFirst = true;
            LOG.warn("[GATE-RATIO] truy vấn TRƯỚC khi đủ 7 ngày dữ liệu (m={}) -> fallback base {}",
                    buffer.size(), Configs.MIN_MOMENTUM_15M);
        }
        return q;
    }

    /**
     * [NUP-TIER2] Ung vien da TRUOT gate chinh: kiem tra no co QUA phan vi {@code tier2Pct} tren
     * CUNG buffer r, CUNG cua so/gio hay khong. Chi doc buffer; KHONG nap mau, KHONG notePass,
     * KHONG doi bat ky bo dem/quota nao cua gate chinh.
     */
    public static boolean tier2Pass(long ts, float p15, float sp) {
        if (!on || !tier2On) return false;
        float scale = (sp / EntryGate.SCORE_BASE) * EntryGate.DYN_MULT;
        float gs = EntryGate.GATE_REGIME_ADAPTIVE ? EntryGate.CURRENT_REGIME_SCALE : EntryGate.GATE_DYN_SCALE;
        float factor = Math.max(EntryGate.DYN_MIN, scale);
        float q2 = currentTier2Q;
        if (Float.isNaN(q2)) return false;
        // Cung bieu thuc voi EntryGate.threshold(q2, sp): pass <=> !(p15 < q2*factor*gs).
        return !(p15 < q2 * factor * gs);
    }

    /** Unit test: bat/tat tier2 va dat pct (khong doc Cfg). */
    static void configureTier2ForTest(boolean enabled, float pctValue) {
        tier2On = enabled;
        tier2Pct = pctValue;
        currentTier2Q = Float.NaN;
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
        currentTier2Q = Float.NaN;
        warnedBeforeFirst = false;
        predictSeen = predictPass = 0;
        predictSkipFull = 0;
        quarterCounts.clear();
    }

    static int bufferSizeForTest() {
        return buffer.size();
    }

    static float tier2QForTest() {
        return currentTier2Q;
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
        if (smoothOn) {
            sb.append(String.format(" | SMOOTH W=%d minCov=%d noCov=%d", smoothW, smoothMinCov, smoothNoCov));
        }
        if (mtfOn) {
            sb.append(String.format(" | MTF W=%d minCov=%d c=%.4f pct_w=%.10f pass1=%d passW=%d both=%d noCov=%d bufW=%d",
                    mtfW, mtfMinCov, mtfC, mtfPct, mtfPass1, mtfPassW, mtfPassBoth, mtfNoCov, bufferW.size()));
        }
        return sb.toString();
    }
}
