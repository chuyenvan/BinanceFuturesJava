package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.tradecore.Cfg;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.EntryGate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;

/**
 * [NSEL 2026-10-08] docs/prereg/PREREG_NSEL.md §2 — tang THEM cua gate 2 tang (CHI SIM).
 *
 * <p>Instance THU HAI cua gate rolling tren ti so r: {@link GateRatioBuffer} RIENG, pct + days RIENG
 * ({@code SIM_NSEL_ADD_ROLLING_PCT}, {@code SIM_NSEL_ADD_ROLLING_DAYS}), warm-up 7 ngay nhu LOI. Quan the buffer
 * THEM = r cua MOI ung vien PREDICT hang &lt;= {@code NSEL_ADD_TOPK} khi so KHONG day (ke ca ung vien da qua LOI).
 * THEM KHONG nap va KHONG tieu buffer LOI ({@link GateRollingRatio}).
 *
 * <p>Key mac dinh OFF ({@code NSEL_ADD_ENABLED=false}) ⇒ {@link #isOn()} = false ⇒ sim khong goi lop nay ⇒
 * byte-identical. Live: KHONG ho tro trong vong nay ⇒ {@link #failIfLive()} nem loi neu profile live khai key NSEL.
 */
public final class NselGate {
    private static final Logger LOG = LoggerFactory.getLogger(NselGate.class);

    public static final int TIER_REJECT = -1;
    public static final int TIER_CORE = 0;
    public static final int TIER_ADD = 1;
    public static final int TIER_CORE_ADD = 2;

    private static boolean inited = false;
    private static boolean on = false;
    private static float pct = 0f;
    private static int days = 90;
    private static int coreK = -1;
    private static int addK = 32;
    private static float f1Min = Float.NaN;

    private static final GateRatioBuffer addBuffer = new GateRatioBuffer();

    // counter (chi tang khi on)
    static long corePass = 0;
    static long addSeen = 0;      // ung vien THEM duoc xet (LOI fail / hang > K_LOI, so khong day)
    static long addFailQ = 0;     // THEM fail q_add
    static long addRejF1 = 0;     // THEM qua q_add nhung bi F1 chan
    static long addPass = 0;      // THEM PASS gate (truoc budget/conc/grid)
    static long addBookFull = 0;  // LOI fail + so day => khong xet THEM, khong nap

    private NselGate() {
    }

    /**
     * Doc cau hinh + fail-fast (idempotent). Goi SAU {@link GateRollingRatio#init()} (can biet LOI co o mode ratio).
     *
     * @throws IllegalStateException cau hinh xung dot (xem {@link #validate})
     */
    public static synchronized void init() {
        if (inited) return;
        inited = true;
        String p = Cfg.get("SIM_NSEL_ADD_ROLLING_PCT");
        Float pctCfg = (p == null || p.trim().isEmpty()) ? null : Float.parseFloat(p.trim());
        validate(Configs.NSEL_ADD_ENABLED, Configs.NSEL_CORE_ADD, Configs.DCA_SIGNAL_GATE,
                Configs.NSEL_ADD_F1_MIN_BARRET, Configs.SELECTOR_RANK_TOPK, Configs.NSEL_ADD_TOPK,
                Configs.NSEL_CORE_ADD_MAX_PER_CLUSTER, GateRollingRatio.isOn(), LiveGateRollingRatio.isOn(),
                Cfg.get("GATE_BUFFER_TOPK"), pctCfg);
        if (!Configs.NSEL_ADD_ENABLED) {
            on = false;
            return;
        }
        String d = Cfg.get("SIM_NSEL_ADD_ROLLING_DAYS");
        int daysCfg = (d != null && !d.trim().isEmpty()) ? Integer.parseInt(d.trim()) : 90;
        configure(pctCfg, daysCfg, Configs.SELECTOR_RANK_TOPK, Configs.NSEL_ADD_TOPK, Configs.NSEL_ADD_F1_MIN_BARRET);
        LOG.warn("*** [NSEL] BAT tang THEM: K_LOI={} K_THEM={} pct_add={} days_add={} F1={} CORE_ADD={} max/cum={} ***",
                coreK, addK, String.format("%.8f", pct), days, f1Min, Configs.NSEL_CORE_ADD,
                Configs.NSEL_CORE_ADD_MAX_PER_CLUSTER);
    }

    /**
     * Fail-fast thuan (khong doc config) — unit test goi truc tiep.
     *
     * @param gateBufferTopkRaw gia tri tho cua key da bo GATE_BUFFER_TOPK (null = khong khai)
     * @param addPct            SIM_NSEL_ADD_ROLLING_PCT (null = khong khai)
     */
    static void validate(boolean addEnabled, boolean coreAdd, boolean dcaSignalGate, float f1, int coreTopK,
                         int addTopK, int coreAddMax, boolean coreRatioOn, boolean liveRatioOn,
                         String gateBufferTopkRaw, Float addPct) {
        if (gateBufferTopkRaw != null) {
            throw new IllegalStateException("[NSEL] key GATE_BUFFER_TOPK da BO (thay bang NSEL_ADD_*) — xoa khoi profile");
        }
        if (coreAdd && !addEnabled) {
            throw new IllegalStateException("[NSEL] SIM_NSEL_CORE_ADD=true can NSEL_ADD_ENABLED=true");
        }
        if (coreAdd && dcaSignalGate) {
            throw new IllegalStateException("[NSEL] SIM_NSEL_CORE_ADD xung dot SIM_DCA_SIGNAL_GATE (chung nhanh coin dang giu)");
        }
        if (coreAdd && coreAddMax < 1) {
            throw new IllegalStateException("[NSEL] NSEL_CORE_ADD_MAX_PER_CLUSTER phai >= 1");
        }
        if (!Float.isNaN(f1) && !addEnabled) {
            throw new IllegalStateException("[NSEL] NSEL_ADD_F1_MIN_BARRET chi ap tang THEM — can NSEL_ADD_ENABLED=true");
        }
        if (!addEnabled) return;
        if (liveRatioOn) {
            throw new IllegalStateException("[NSEL] tang THEM chi ho tro SIM — LIVE_GATE_ROLLING_* dang bat");
        }
        if (!coreRatioOn) {
            throw new IllegalStateException("[NSEL] NSEL_ADD_ENABLED can SIM_GATE_ROLLING_MODE=ratio (LOI o mode ratio)");
        }
        if (coreTopK <= 0) {
            throw new IllegalStateException("[NSEL] NSEL_ADD_ENABLED can SELECTOR_RANK_TOPK > 0 (rank-mode)");
        }
        if (addTopK < coreTopK) {
            throw new IllegalStateException("[NSEL] NSEL_ADD_TOPK=" + addTopK + " < SELECTOR_RANK_TOPK=" + coreTopK);
        }
        if (addPct == null || !(addPct > 0f && addPct < 1f)) {
            throw new IllegalStateException("[NSEL] NSEL_ADD_ENABLED can SIM_NSEL_ADD_ROLLING_PCT trong (0,1), co: " + addPct);
        }
    }

    /**
     * LIVE chua ho tro NSEL (vong nay chi sim). Goi o init live: profile live khai bat ky key NSEL nao (NSEL_ADD_ENABLED,
     * SIM_NSEL_CORE_ADD, NSEL_ADD_F1_MIN_BARRET, LIVE_NSEL_*) hoac key da bo GATE_BUFFER_TOPK ⇒ nem loi, khong am
     * tham lech parity sim↔live.
     */
    public static void failIfLive() {
        Iterable<String> keys;
        Map<String, String> prof = Cfg.all();
        keys = (prof != null) ? prof.keySet() : System.getenv().keySet();
        failIfLive(Configs.NSEL_ADD_ENABLED, Configs.NSEL_CORE_ADD, Configs.NSEL_ADD_F1_MIN_BARRET, keys,
                Cfg.get("GATE_BUFFER_TOPK"));
    }

    static void failIfLive(boolean addEnabled, boolean coreAdd, float f1, Iterable<String> keys, String gateBufferTopkRaw) {
        if (gateBufferTopkRaw != null) {
            throw new IllegalStateException("[NSEL] key GATE_BUFFER_TOPK da BO — xoa khoi profile live");
        }
        if (addEnabled || coreAdd || !Float.isNaN(f1)) {
            throw new IllegalStateException("[NSEL] LIVE chua ho tro NSEL (NSEL_ADD_ENABLED/SIM_NSEL_CORE_ADD/F1) — tat key");
        }
        if (keys != null) {
            for (String k : keys) {
                if (k != null && k.startsWith("LIVE_NSEL")) {
                    throw new IllegalStateException("[NSEL] LIVE chua ho tro NSEL — key " + k + " khong duoc khai");
                }
            }
        }
    }

    private static void configure(float pctValue, int daysValue, int coreTopK, int addTopK, float f1) {
        on = true;
        pct = pctValue;
        days = daysValue;
        coreK = coreTopK;
        addK = addTopK;
        f1Min = f1;
        addBuffer.reset();
        corePass = addSeen = addFailQ = addRejF1 = addPass = addBookFull = 0;
    }

    /** Chi cho unit test: bat tang THEM voi tham so cu the, reset state. */
    static void configureForTest(float pctValue, int daysValue, int coreTopK, int addTopK, float f1) {
        inited = true;
        configure(pctValue, daysValue, coreTopK, addTopK, f1);
    }

    /** Chi cho unit test: tat. */
    static void disableForTest() {
        inited = true;
        on = false;
    }

    public static boolean isOn() {
        return on;
    }

    /** K cua tang LOI (= SELECTOR_RANK_TOPK luc init; unit test dat rieng vi SELECTOR_RANK_TOPK la final). */
    public static int coreTopK() {
        return coreK;
    }

    /** So ung vien selector can xet moi tick: OFF ⇒ dung K cu (caller giu selectCands cu). */
    public static int selectorTopK() {
        return on ? Math.max(coreK, addK) : coreK;
    }

    /**
     * F1 (chi tang THEM): PASS ⇔ bar_ret nen quyet dinh &gt; nguong. NaN = tat ⇒ luon PASS. bar_ret tinh float32
     * {@code (close-open)/open} — cung bieu thuc voi penalty ({@code <= -0.01f} la "sap") ⇒ F1=-0.01 loai DUNG tap
     * nen bi phat.
     */
    public static boolean f1Pass(float barRet) {
        if (Float.isNaN(f1Min)) return true;
        return barRet > f1Min;
    }

    /** Ti so r cua ung vien (cung bieu thuc LOI) — package-private cho test. */
    static float addThreshold(long ts, float p15, float sp) {
        return addBuffer.addAndQuery(ts, GateRollingRatio.ratio(p15, sp), pct, days, Configs.MIN_MOMENTUM_15M);
    }

    /**
     * Quyet dinh tang sau khi LOI da chay (hoac khong chay vi hang &gt; K_LOI).
     * <ol>
     *   <li>Nap r vao buffer THEM neu sp != null, hang &lt;= K_THEM, va KHONG (skipFull bat ∧ so day) — ke ca khi LOI pass.</li>
     *   <li>LOI pass ⇒ TIER_CORE (THEM khong xet).</li>
     *   <li>Nguoc lai: so day ⇒ REJECT; p15 &lt; thr(q_add) ⇒ REJECT; F1 fail ⇒ REJECT; con lai TIER_ADD.</li>
     * </ol>
     */
    static int decide(long ts, float p15, Float sp, boolean bookFull, int selRank, boolean corePassed, float barRet) {
        boolean full = Configs.GATE_QUOTA_SKIP_WHEN_FULL && bookFull;
        boolean feed = sp != null && selRank <= addK && !full;
        float qAdd = feed ? addThreshold(ts, p15, sp) : Float.NaN;
        if (corePassed) {
            corePass++;
            return TIER_CORE;
        }
        if (!feed) {
            if (full) addBookFull++;
            return TIER_REJECT;
        }
        addSeen++;
        if (p15 < EntryGate.threshold(qAdd, sp)) {
            addFailQ++;
            return TIER_REJECT;
        }
        if (!f1Pass(barRet)) {
            addRejF1++;
            return TIER_REJECT;
        }
        addPass++;
        return TIER_ADD;
    }

    static int addBufferSize() {
        return addBuffer.size();
    }

    public static long addPassCount() {
        return addPass;
    }

    /** Mot dong cho log [NSEL] cuoi run (phan gate; phan chan/CORE_ADD do simulator ghep). */
    public static String stats() {
        return String.format("on=%s K_LOI=%d K_THEM=%d pct_add=%.8f days_add=%d F1=%s core_pass=%d add_seen=%d "
                        + "add_fail_q=%d add_rej_f1=%d add_pass=%d add_bookfull=%d addBuf_n=%d addBuf_query=%d addBuf_beforeFirst=%d",
                on, coreK, addK, pct, days, f1Min, corePass, addSeen, addFailQ, addRejF1, addPass, addBookFull,
                addBuffer.size(), addBuffer.nQuery(), addBuffer.nBeforeFirst());
    }
}
