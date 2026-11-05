package com.binance.chuyennd.ops;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayDeque;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.function.Consumer;
import java.util.function.DoubleSupplier;
import java.util.function.Supplier;

/**
 * [V11D OPS 2026-10-21] Kill-switch A40 + C1–C6 (owner duyet 10-21, docs/result/KILLSW_MENU.md muc 4) — v11d CHI co
 * che do {@code log}: moi dieu kien dat => {@code [KILLSW] WOULD_TRIGGER code=Cx ...} + dem theo gio, KHONG doi bat
 * ky quyet dinh nao (engine chi DOC so lieu duoc hook dua vao, khong giu tham chieu ghi nao toi state giao dich).
 *
 * <p>Detector (thuan, unit test o bien nguong):
 * <ul>
 *   <li>C1 du lieu: tuoi nen BTC moi nhat trong cua so ticker {@code > 180 s} (tinh tu luc nen DONG = start+60 s),
 *       HOAC {@code > 10 %} symbol "dang song" (nen cuoi trong 60' gan nhat) thieu nen phut hien tai, HOAC khong co
 *       du lieu thi truong nao duoc dua vao {@code > 240 s} (vd tick bo vong vi thieu BTC).</li>
 *   <li>C2 truot gia: {@code |fill/ref - 1| > 2,5 %}. So GIAY khong co fill that (gia vao = close nen quyet dinh) =>
 *       <b>N/A</b> tren c3_shadow; ham {@link #onFill} de danh cho c3_live (chua noi day).</li>
 *   <li>C3 API: {@code >= 5} loi lien tiep. Tren c3_shadow khong co API dat lenh => do tren lenh REST dong bo vi the
 *       ({@code getAllPositionInfos} moi phut: null/rong = loi).</li>
 *   <li>C4 phoi nhiem: vi the GIAY mo {@code > 90} HOAC {@code U = margin/equity >= U_MAX} (tran margin). LEGACY
 *       (vi the that cu) KHONG tinh.</li>
 *   <li>C5 song: khong co tick quyet dinh {@code > 300 s} (chi phat hien duoc khi JVM con chay; JVM chet/treo =>
 *       watchdog).</li>
 *   <li>C6/A40: DD MTM cua so GIAY (equity = PAPER_EQUITY + realized + MTM cum mo; dinh = max(PAPER_EQUITY, dinh da
 *       luu, equity da thay)) {@code <= -40 %}. LEGACY KHONG tinh.</li>
 * </ul>
 *
 * <p>[V12 SAFE 2026-10-25] (docs/plan/GOLIVE_SCENARIO.md C8, quyet dinh owner Q1b/Q1c 10-25):
 * <ul>
 *   <li><b>C2 co dau</b> sau co {@code LIVE_KILLSW_C2_SIGNED=1} (mac dinh 0 = cong thuc |.| v1.1 y nguyen): truot
 *       BAT LOI (mua: {@code fill/ref - 1}, ban: {@code 1 - fill/ref}); {@code > c2Warn} (1,7 %) => WARN
 *       {@code [KILLSW] C2_WARN}; {@code > c2Slip} (2,5 %) xay ra {@code >= c2Count} (3) lan trong {@code c2WindowMs}
 *       (24h) => C2 dat. Moc su kien luu file latch (song qua restart). Nguong = tham so config.</li>
 *   <li><b>ACT that</b> ({@link #ACT_IMPLEMENTED} = true, CHI profile {@code c3_live}; c3_shadow van tu choi => log):
 *       C1–C5 dat => latch {@link Action#NO_NEW_ENTRY}; C6 hoac A40 dat => latch {@link Action#FLATTEN} (bao gom chan
 *       mo moi). Latch persist {@code LIVE_KILLSW_LATCH_FILE} (mac dinh {@code run/killsw_latch.json}), CHI xoa bang
 *       script owner {@code ops/killsw_reset.sh} (ghi file yeu cau {@code LIVE_KILLSW_RESET_FILE}; engine la nguoi ghi
 *       DUY NHAT file latch). Hanh dong do caller thuc hien qua {@link #allowNewEntry(String)} /
 *       {@link #requiredAction()} (vong 2 noi o {@code createOrderBuyRequest} + cua gui lenh + vong dong reduce-only).</li>
 *   <li><b>A40</b> tren equity THAT tai khoan con qua {@link EquitySource} (vong 2 cai = totalMarginBalance, Q1b):
 *       dinh = max(dinh luu file, equity da thay); {@code equity/dinh - 1 <= -40 %} => FLATTEN. Chi co khi gan
 *       EquitySource ({@link #attachEquitySource}) — khong gan => dong HOURLY/log y nhu v1.1.</li>
 * </ul>
 * <p>[V12 vong 2b MASTER 10-25 — giai quyet lech GOLIVE §5.2] mode ACT + {@code Params.c4Capacity} (OpsConfig bat o
 * c3_live): C4 (vi the &gt; 90 hoac U &gt;= U_MAX) la dieu kien CONG SUAT — KHONG latch, chi chan MO CUM MOI
 * ({@link #allowNewEntry}); DCA cum dang co van qua ({@link #allowDca}; van chiu throttle U_MAX cua sizing); tu go co tre khi
 * vi the &lt;= 85 VA U &lt;= U_MAX - 0,05. C3 tu go sau 30' sach + &gt;= 3 call API thanh cong lien tiep (nhu C1/C5).
 * Giu latch cho owner: C2, C6, A40 (va STATE).
 *
 * Mode LOG (c3_shadow): KHONG doc/ghi file latch, {@link #allowNewEntry} luon true, {@link #requiredAction} luon NONE,
 * van ban log giu nguyen v1.1 (C2 co dau chi khi co bat).
 */
public final class KillSwitchEngine {

    public enum Mode { OFF, LOG, ACT }

    /** Hanh dong caller phai thuc hien (chi khac NONE o mode ACT). Thu tu = muc nghiem trong. */
    public enum Action { NONE, NO_NEW_ENTRY, FLATTEN }

    /** [V12] act da cai (latch NO_NEW_ENTRY / FLATTEN). Van chi hop le o profile c3_live. */
    public static final boolean ACT_IMPLEMENTED = true;

    public static final long C1_LAG_SEC = 180L;
    /** missing/universe > 10 % (so nguyen: missing*10 > universe). */
    public static final int C1_MISSING_PCT = 10;
    public static final long C1_UNIVERSE_LOOKBACK_MIN = 60L;
    public static final long C1_NODATA_SEC = 240L;
    public static final double C2_SLIP = 0.025;
    public static final int C3_CONSEC = 5;
    /**
     * [V12 R4p Bug3] C3 con DAT do 429 lenh toi khi het cua so nay tinh tu 429 lenh cuoi (khong co lenh OK xen giua); sau do
     * tu go van can >= autoReleaseMs sach + c3ReleaseOkConsec call OK nhu cu.
     */
    public static final long C3_ORDER429_HOLD_MS = 5 * 60_000L;
    public static final int C4_MAX_POS = 90;
    public static final long C5_NOTICK_SEC = 300L;
    public static final double C6_DD = -0.40;
    /** [V12] A40: DD equity that tai khoan con (owner 10-10: DD chap nhan 40 %). */
    public static final double A40_DD = -0.40;
    public static final String REF_SYMBOL = "BTCUSDT";
    public static final String[] CODES = {"C1", "C2", "C3", "C4", "C5", "C6"};
    public static final String CODE_A40 = "A40";
    /** Ma latch khi file latch hong/khong doc duoc o mode ACT (fail-closed). */
    public static final String CODE_STATE = "STATE";
    static final long REPEAT_LOG_MS = 60_000L;
    static final long PEAK_WRITE_MIN_MS = 60_000L;
    static final long BLOCK_LOG_MS = 60_000L;
    static final long EQ_WARN_MS = 600_000L;
    private static final long MIN_MS = 60_000L;
    private static final DateTimeFormatter HOUR_FMT =
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH'+07'").withZone(ZoneId.of("Asia/Ho_Chi_Minh"));

    /** Dau ra log (SLF4J o runtime, list o unit test). */
    public interface Sink {
        void info(String msg);

        void warn(String msg);
    }

    /** Ket qua phan giai {@code LIVE_KILLSW_MODE} theo profile. */
    public static final class Resolved {
        public final Mode requested;
        public final Mode effective;
        /** null = khong co canh bao. */
        public final String warn;

        Resolved(Mode requested, Mode effective, String warn) {
            this.requested = requested;
            this.effective = effective;
            this.warn = warn;
        }
    }

    /** [V12] tham so moi (mac dinh = hanh vi v1.1: C2 |.|, khong latch file, khong A40). */
    public static final class Params {
        /** {@code LIVE_KILLSW_C2_SIGNED}: false = cong thuc |fill/ref-1| > 2,5 % cua v1.1. */
        public boolean c2Signed = false;
        public double c2Warn = 0.017;
        public double c2Slip = 0.025;
        public int c2Count = 3;
        public long c2WindowMs = 24L * 3_600_000L;
        /** File latch (chi dung o mode ACT). */
        public File latchFile = null;
        /** File yeu cau reset cua owner (chi dung o mode ACT). */
        public File resetFile = null;
        /** [V12 MASTER 10-25] ACT: ma trong {@link #autoReleaseCodes} tu go latch sau bay nhieu ms LIEN TUC sach (0 = tat). */
        public long autoReleaseMs = 0L;
        /** Ma duoc tu go (C1 du lieu cu, C5 khong tick). C2/C3/C4/C6/A40/STATE giu latch toi khi owner reset. */
        public java.util.Set<String> autoReleaseCodes = new java.util.HashSet<>(java.util.Arrays.asList("C1", "C5"));
        /** [V12 2b MASTER 10-25] ACT: C4 = dieu kien CONG SUAT (khong latch; chan mo cum moi; DCA van chay; tu go co tre). */
        public boolean c4Capacity = false;
        /** Go C4 cong suat khi so vi the <= gia tri nay ... */
        public int c4ReleasePos = 85;
        /** ... VA U <= U_MAX - gia tri nay. */
        public double c4ReleaseUGap = 0.05;
        /** [V12 2b MASTER 10-25] C3 tu go can them >= bay nhieu call API thanh cong LIEN TIEP. */
        public int c3ReleaseOkConsec = 3;
        /**
         * [V12 2c CRIT-1] c3_live: C6 do DD cua totalMarginBalance THAT so voi dinh RIENG (file rieng, mac dinh
         * {@code run/c3live_killsw_peak}): KHONG san PAPER_EQUITY, KHONG doc/ghi file dinh so giay cua c3_shadow; dinh
         * khoi tao = tmb hop le dau tien; equity &lt;= 0 / NaN => giu trang thai C6 cu (khong danh gia); owner
         * {@code reset_peak=1} dat lai CA dinh nay (xoa file). Mac dinh false = hanh vi v1.1 (so giay).
         */
        public boolean c6OwnPeak = false;
        /**
         * [V12 2d MIN-19] c3_live: nhan adapter (dry|live|...) ghi kem dinh C6 (file dinh) va acct_peak (file latch). Nap
         * dinh co nhan KHAC (hoac khong nhan) => BO QUA + WARN (dinh dry khong duoc dung cho tien that). null = khong nhan
         * (c3_shadow / v1.1: dinh dang file y nguyen).
         */
        public String peakTag = null;
    }

    /**
     * off|log|act theo profile. c3_shadow (va moi profile khac c3_live): chi off|log — act BI TU CHOI + WARN, chay log.
     * c3_live + act: hop le (v1.2 da cai hanh dong). Gia tri la => off + WARN.
     */
    public static Resolved resolve(String raw, String profile) {
        String v = raw == null ? "" : raw.trim().toLowerCase(Locale.ROOT);
        String p = profile == null ? "" : profile.trim().toLowerCase(Locale.ROOT);
        if (v.isEmpty() || "off".equals(v)) return new Resolved(Mode.OFF, Mode.OFF, null);
        if ("log".equals(v)) return new Resolved(Mode.LOG, Mode.LOG, null);
        if ("act".equals(v)) {
            if (!"c3_live".equals(p)) {
                return new Resolved(Mode.ACT, Mode.LOG, "[KILLSW] LIVE_KILLSW_MODE=act BI TU CHOI o profile '"
                        + (p.isEmpty() ? "-" : p) + "' (chi off|log; act chi hop le o c3_live) => chay mode=log");
            }
            if (!ACT_IMPLEMENTED) {
                return new Resolved(Mode.ACT, Mode.LOG, "[KILLSW] LIVE_KILLSW_MODE=act o c3_live: hanh dong CHUA cai trong"
                        + " v11d => chay mode=log (KHONG co bao ve tu dong)");
            }
            return new Resolved(Mode.ACT, Mode.ACT, null);
        }
        return new Resolved(Mode.OFF, Mode.OFF, "[KILLSW] LIVE_KILLSW_MODE='" + raw + "' khong hop le (off|log|act) => off");
    }

    // ------------------------------------------------------------------ detector thuan
    static boolean c1Lag(long lagSec) {
        return lagSec > C1_LAG_SEC;
    }

    static boolean c1Missing(long universe, long missing) {
        return universe > 0 && missing * 100L > C1_MISSING_PCT * universe;
    }

    static boolean c1NoData(long sinceMarketDataSec) {
        return sinceMarketDataSec > C1_NODATA_SEC;
    }

    /** null = N/A (khong co fill that hoac thieu gia tham chieu). Cong thuc v1.1 (tri tuyet doi). */
    static Double c2Slip(Double fill, Double ref) {
        if (fill == null || ref == null || !(ref > 0d) || !(fill > 0d)) return null;
        return Math.abs(fill / ref - 1.0);
    }

    /**
     * [V12] truot BAT LOI co dau: mua {@code fill/ref - 1}, ban {@code 1 - fill/ref} (duong = bat loi).
     * null = N/A. Gia khong huu han => N/A.
     */
    static Double c2Adverse(boolean isBuy, Double fill, Double ref) {
        if (fill == null || ref == null || !(ref > 0d) || !(fill > 0d)) return null;
        if (!Double.isFinite(fill) || !Double.isFinite(ref)) return null;
        return isBuy ? fill / ref - 1.0 : 1.0 - fill / ref;
    }

    static boolean c2(Double slip) {
        return slip != null && slip > C2_SLIP;
    }

    static boolean c3(int consecErrors) {
        return consecErrors >= C3_CONSEC;
    }

    static boolean c4(int openPos, float margin, float equity, float uMax) {
        if (openPos > C4_MAX_POS) return true;
        return equity > 0f && uMax > 0f && margin / equity >= uMax;
    }

    static boolean c5(long noTickSec) {
        return noTickSec > C5_NOTICK_SEC;
    }

    static double dd(double equity, double peak) {
        return peak > 0d ? equity / peak - 1.0 : 0.0;
    }

    static boolean c6(double dd) {
        return dd <= C6_DD + 1e-12;
    }

    static boolean a40(double dd) {
        return dd <= A40_DD + 1e-12;
    }

    /** Tuoi (s) cua nen phut {@code refMinuteStartMs} tinh tu luc nen DONG. */
    static long lagSec(long nowMs, long refMinuteStartMs) {
        return (nowMs - refMinuteStartMs - MIN_MS) / 1000L;
    }

    /**
     * {refMinuteStartMs, universe, missing} tren cua so ticker (CHI DOC map). universe = symbol co nen cuoi trong
     * {@link #C1_UNIVERSE_LOOKBACK_MIN} phut truoc phut cua BTC; missing = trong do nen cuoi cu hon phut BTC.
     * Thieu BTC => {-1, 0, 0}. So theo PHUT (floor) vi startTime live lech ms.
     */
    static long[] c1Scan(Map<String, List<KlineObjectSimple>> w, String refSymbol) {
        if (w == null) return new long[]{-1L, 0L, 0L};
        Long ref = lastStart(w.get(refSymbol));
        if (ref == null) return new long[]{-1L, 0L, 0L};
        long refMin = Math.floorDiv(ref, MIN_MS);
        long uni = 0, miss = 0;
        for (Map.Entry<String, List<KlineObjectSimple>> e : w.entrySet()) {
            Long s = lastStart(e.getValue());
            if (s == null) continue;
            long m = Math.floorDiv(s, MIN_MS);
            if (m < refMin - C1_UNIVERSE_LOOKBACK_MIN) continue;
            uni++;
            if (m < refMin) miss++;
        }
        return new long[]{refMin * MIN_MS, uni, miss};
    }

    private static Long lastStart(List<KlineObjectSimple> l) {
        if (l == null || l.isEmpty()) return null;
        KlineObjectSimple k = l.get(l.size() - 1);
        return k == null ? null : k.startTime;
    }

    static String hourKey(long nowMs) {
        return HOUR_FMT.format(Instant.ofEpochMilli(nowMs));
    }

    static String action(String code) {
        return "C6".equals(code) || CODE_A40.equals(code) ? "CLOSE_ALL+HALT" : "STOP_NEW_ENTRIES+TELEGRAM(van quan ly vi the)";
    }

    /** [V12] hanh dong latch cua 1 ma: C6/A40 => FLATTEN, con lai => NO_NEW_ENTRY. */
    static Action latchActionOf(String code) {
        return "C6".equals(code) || CODE_A40.equals(code) ? Action.FLATTEN : Action.NO_NEW_ENTRY;
    }

    // ------------------------------------------------------------------ state
    static final class CodeState {
        boolean active;
        long since;
        long lastLog;
        long metHour;
        long edgesHour;
        long metTotal;
        long edgesTotal;
        String detail = "-";
    }

    private final Mode mode;
    private final String modeLabel;
    private final Sink sink;
    private final File peakFile;
    private final DoubleSupplier paperEquity;
    private final Supplier<Float> uMax;
    private final Params prm;
    private final Map<String, CodeState> st = new LinkedHashMap<>();
    private long lastTickStartMs;
    private long lastMarketDataMs;
    private boolean c1Data;
    private String c1DataDetail = "-";
    private long lastLagSec = Long.MIN_VALUE;
    private long lastUni = -1, lastMiss = -1;
    private int c3Consec;
    private String lastApi = "-";
    private int lastOpen = -1;
    private float lastMargin = Float.NaN, lastEquity = Float.NaN;
    private double peak = Double.NaN;
    private boolean peakFloorApplied;
    private double lastDd = Double.NaN;
    private double peakWritten = Double.NaN;
    private long lastPeakWriteMs = Long.MIN_VALUE / 2;
    private long lastPeakWarnMs = Long.MIN_VALUE / 2;
    private Double lastSlip;
    private String hour;
    // [V12] ACT / latch / C2 co dau / A40
    private Action latch = Action.NONE;
    private final Set<String> latchCodes = new LinkedHashSet<>();
    private long latchSinceMs;
    private String latchDetail = "-";
    private final ArrayDeque<Long> c2Events = new ArrayDeque<>();
    private EquitySource equitySource;
    private double acctPeak = Double.NaN;
    private double acctPeakWritten = Double.NaN;
    private double lastAcctEq = Double.NaN;
    private double lastAcctDd = Double.NaN;
    private long lastAcctPeakWriteMs = Long.MIN_VALUE / 2;
    private long lastEqWarnMs = Long.MIN_VALUE / 2;
    private long nEqUnavailable;
    private long lastResetAtMs;
    private long lastBlockLogMs = Long.MIN_VALUE / 2;
    private long nBlocked;
    private long lastStateWarnMs = Long.MIN_VALUE / 2;
    private Consumer<String> alert;
    /** [V12] moc bat dau sach lien tuc cua tung ma (cho auto-release C1/C5). */
    private final Map<String, Long> cleanSince = new LinkedHashMap<>();
    /** [V12 2b] C4 cong suat (ACT + c4Capacity): dang chan mo cum moi. */
    private boolean c4Cap;
    private long c4CapSinceMs;
    private long nCapBlocked;
    private long lastCapLogMs = Long.MIN_VALUE / 2;
    /** [V12 2b] so call API thanh cong lien tiep (dieu kien tu go C3). */
    private int apiOkConsec;
    /** [V12 R4p Bug3] 429 LIEN TIEP rieng duong DAT LENH; call doc OK KHONG reset, lenh OK reset. */
    private int order429Consec;
    private long lastOrder429Ms = Long.MIN_VALUE / 2;

    /**
     * @param mode        mode HIEU LUC (LOG; ACT chi khi da cai). OFF => khong nen tao engine.
     * @param modeLabel   chuoi in trong log (vd "log", "log(act_tu_choi)")
     * @param peakFile    file luu dinh equity (null = khong luu)
     * @param paperEquity PAPER_EQUITY — san cua dinh (doc tre, lan dau co so giay)
     * @param uMax        tran U cho C4 (Configs.U_MAX) — doc tre
     */
    public KillSwitchEngine(Mode mode, String modeLabel, Sink sink, File peakFile, DoubleSupplier paperEquity,
                            Supplier<Float> uMax, long nowMs) {
        this(mode, modeLabel, sink, peakFile, paperEquity, uMax, nowMs, null);
    }

    /** [V12] nhu tren + tham so C2 co dau / file latch. {@code prm == null} => mac dinh (= v1.1). */
    public KillSwitchEngine(Mode mode, String modeLabel, Sink sink, File peakFile, DoubleSupplier paperEquity,
                            Supplier<Float> uMax, long nowMs, Params prm) {
        this.mode = mode;
        this.modeLabel = modeLabel;
        this.sink = sink;
        this.peakFile = peakFile;
        this.paperEquity = paperEquity;
        this.uMax = uMax;
        this.prm = prm == null ? new Params() : prm;
        for (String c : CODES) st.put(c, new CodeState());
        this.lastTickStartMs = nowMs;
        this.lastMarketDataMs = nowMs;
        this.hour = hourKey(nowMs);
        loadPeak();
        if (mode == Mode.ACT) {
            loadLatch(nowMs);
            checkResetRequest(nowMs);
        }
    }

    public Mode mode() {
        return mode;
    }

    private void loadPeak() {
        if (peakFile == null || !peakFile.exists()) return;
        try {
            String s = new String(Files.readAllBytes(peakFile.toPath()), StandardCharsets.UTF_8).trim();
            if (prm.peakTag != null) {   // [2d MIN-19] "<dinh> adapter=<nhan>"
                String[] tok = s.split("\\s+");
                String tag = null;
                for (String x : tok) if (x.startsWith("adapter=")) tag = x.substring("adapter=".length());
                if (!prm.peakTag.equals(tag)) {
                    sink.warn("[KILLSW] file dinh " + peakFile.getAbsolutePath() + " cua adapter=" + (tag == null ? "(khong nhan)" : tag)
                            + " != adapter hien tai " + prm.peakTag + " => BO QUA (dinh lay lai tu tmb that dau tien)");
                    return;
                }
                s = tok[0];
            }
            double v = Double.parseDouble(s);
            if (Double.isFinite(v) && v > 0d) {
                peak = v;
                peakWritten = v;
                sink.info("[KILLSW] nap dinh equity " + (prm.c6OwnPeak ? "c3_live (tmb that, C6)" : "giay") + " tu "
                        + peakFile.getAbsolutePath() + " = " + fmt2(v));
            } else {
                sink.warn("[KILLSW] file dinh " + peakFile.getAbsolutePath() + " gia tri khong hop le => bo qua");
            }
        } catch (Exception e) {
            sink.warn("[KILLSW] khong doc duoc file dinh " + peakFile.getAbsolutePath() + ": " + e + " => bo qua");
        }
    }

    private void maybeWritePeak(long nowMs) {
        if (peakFile == null || !(peak > 0d)) return;
        if (!Double.isNaN(peakWritten) && peak <= peakWritten * (1 + 1e-9)) return;
        if (nowMs - lastPeakWriteMs < PEAK_WRITE_MIN_MS) return;
        lastPeakWriteMs = nowMs;
        try {
            File abs = peakFile.getAbsoluteFile();
            File tmp = new File(abs.getParentFile(), abs.getName() + ".tmp");
            Files.write(tmp.toPath(), (Double.toString(peak) + (prm.peakTag != null ? " adapter=" + prm.peakTag : "") + "\n")
                    .getBytes(StandardCharsets.UTF_8));
            Files.move(tmp.toPath(), abs.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
            peakWritten = peak;
        } catch (Exception e) {
            if (nowMs - lastPeakWarnMs >= 3_600_000L) {
                lastPeakWarnMs = nowMs;
                sink.warn("[KILLSW] khong ghi duoc file dinh " + peakFile.getAbsolutePath() + ": " + e);
            }
        }
    }

    // ------------------------------------------------------------------ [V12] API cho vong 2 (c3_live)

    /**
     * [V12] Cong mo lenh MOI (vong 2 goi o {@code createOrderBuyRequest} TRUOC push VA o cua gui lenh, ca entry lan
     * DCA). Mode khac ACT => luon true (c3_shadow/sim khong doi). ACT: false khi da latch (NO_NEW_ENTRY/FLATTEN).
     * Lenh reduce-only (dong/SL) KHONG di qua cong nay.
     */
    public synchronized boolean allowNewEntry(String symbol) {
        if (mode != Mode.ACT) return true;
        if (latch == Action.NONE && !c4Cap) return true;
        if (latch == Action.NONE) {   // [V12 2b] C4 cong suat: chi chan MO CUM MOI
            nCapBlocked++;
            long nowC = System.currentTimeMillis();
            if (nowC - lastCapLogMs >= BLOCK_LOG_MS) {
                lastCapLogMs = nowC;
                sink.warn("[KILLSW] C4_CAPACITY chan MO CUM MOI symbol=" + symbol + " (DCA van chay) n_blocked=" + nCapBlocked);
            }
            return false;
        }
        nBlocked++;
        long now = System.currentTimeMillis();
        if (now - lastBlockLogMs >= BLOCK_LOG_MS) {
            lastBlockLogMs = now;
            sink.warn("[KILLSW] BLOCK_NEW_ENTRY symbol=" + symbol + " latch=" + latch + " codes=" + latchCodes
                    + " n_blocked=" + nBlocked);
        }
        return false;
    }

    /**
     * [V12] Hanh dong bat buoc hien tai: NONE / NO_NEW_ENTRY (chi chan mo moi, van quan ly vi the) / FLATTEN (dong het
     * reduce-only chia lo + dung). Mode khac ACT => luon NONE.
     */
    public synchronized Action requiredAction() {
        return mode == Mode.ACT ? latch : Action.NONE;
    }

    /**
     * [V12 2b] Cong DCA cua cum DANG CO: chi latch (NO_NEW_ENTRY/FLATTEN) chan; C4 cong suat KHONG chan (sizing van throttle
     * U_MAX nhu sim). Mode khac ACT => luon true.
     */
    public synchronized boolean allowDca(String symbol) {
        if (mode != Mode.ACT) return true;
        if (latch == Action.NONE) return true;
        nBlocked++;
        long now = System.currentTimeMillis();
        if (now - lastBlockLogMs >= BLOCK_LOG_MS) {
            lastBlockLogMs = now;
            sink.warn("[KILLSW] BLOCK_DCA symbol=" + symbol + " latch=" + latch + " codes=" + latchCodes + " n_blocked=" + nBlocked);
        }
        return false;
    }

    /** [V12 2b] C4 cong suat dang chan mo cum moi (chi ACT + c4Capacity). */
    public synchronized boolean capacityBlocked() {
        return c4Cap;
    }

    /** [V12] cac ma da gay latch (copy). */
    public synchronized Set<String> latchCodes() {
        return new LinkedHashSet<>(latchCodes);
    }

    /** [V12] noi Telegram (vong 2). Goi khi latch moi / nang muc / reset / C2_WARN. Khong bao gio nem ra ngoai. */
    public synchronized void setAlert(Consumer<String> alert) {
        this.alert = alert;
        if (alert != null && !earlyAlerts.isEmpty()) {
            List<String> q = new java.util.ArrayList<>(earlyAlerts);
            earlyAlerts.clear();
            for (String m : q) fireAlert(m);
        }
    }

    /** [2e] canh bao phat sinh truoc setAlert (chi c3_live). */
    private final List<String> earlyAlerts = new java.util.ArrayList<>();

    /**
     * [V12] Gan nguon equity THAT (A40). Sau khi gan, dong HOURLY co them A40 va {@link #periodic} poll equity.
     * Chi gan 1 lan (lan sau bo qua).
     */
    public synchronized void attachEquitySource(EquitySource src) {
        if (src == null || equitySource != null) return;
        equitySource = src;
        st.put(CODE_A40, new CodeState());
        sink.info("[KILLSW] gan EquitySource (A40 DD<=" + A40_DD + " tren equity that) dinh_luu=" + fmt2(acctPeak));
    }

    /** [V12] Dua 1 diem equity that (vong 2 co the day thay vi de periodic poll). */
    public synchronized void onAccountEquity(long nowMs, Double equity) {
        roll(nowMs);
        if (!st.containsKey(CODE_A40)) st.put(CODE_A40, new CodeState());
        if (equity == null || !Double.isFinite(equity) || !(equity > 0d)) {
            nEqUnavailable++;
            if (nowMs - lastEqWarnMs >= EQ_WARN_MS) {
                lastEqWarnMs = nowMs;
                sink.warn("[KILLSW] A40 equity khong co/khong hop le (" + equity + ") n=" + nEqUnavailable
                        + " => giu trang thai A40 cu (bao loi API qua onApiResult de C3 bat)");
            }
            return;
        }
        lastAcctEq = equity;
        if (Double.isNaN(acctPeak) || equity > acctPeak) acctPeak = equity;
        lastAcctDd = dd(equity, acctPeak);
        set(CODE_A40, a40(lastAcctDd), "dd=" + fmt4(lastAcctDd) + " eq=" + fmt2(equity) + " peak=" + fmt2(acctPeak), nowMs);
        if (mode == Mode.ACT && prm.latchFile != null && acctPeak > 0d
                && (Double.isNaN(acctPeakWritten) || acctPeak > acctPeakWritten * (1 + 1e-9))
                && nowMs - lastAcctPeakWriteMs >= PEAK_WRITE_MIN_MS) {
            lastAcctPeakWriteMs = nowMs;
            persistLatch(nowMs);
        }
    }

    // ------------------------------------------------------------------ su kien (hook)
    public synchronized void onTickStart(long nowMs) {
        roll(nowMs);
        lastTickStartMs = nowMs;
        set("C5", false, "-", nowMs);
    }

    public synchronized void onMarketData(long nowMs, Map<String, List<KlineObjectSimple>> window) {
        roll(nowMs);
        long[] r = c1Scan(window, REF_SYMBOL);
        if (r[0] < 0) {
            // thieu BTC trong cua so: khong cap nhat lastMarketDataMs => C1 no_data sau 240 s
            return;
        }
        lastMarketDataMs = nowMs;
        lastLagSec = lagSec(nowMs, r[0]);
        lastUni = r[1];
        lastMiss = r[2];
        boolean lag = c1Lag(lastLagSec);
        boolean miss = c1Missing(r[1], r[2]);
        c1Data = lag || miss;
        c1DataDetail = (lag ? "LAG " : "") + (miss ? "MISSING " : "") + "lag_s=" + lastLagSec + " miss=" + r[2] + "/" + r[1];
        evalC1(nowMs);
    }

    public synchronized void onApiResult(long nowMs, String api, boolean ok) {
        roll(nowMs);
        lastApi = api;
        c3Consec = ok ? 0 : c3Consec + 1;
        apiOkConsec = ok ? apiOkConsec + 1 : 0;
        set("C3", c3Met(nowMs), c3Detail(api), nowMs);
    }

    /**
     * [V12 R4p Bug3] Ket qua 1 lan DAT LENH. {@code rateLimited} (san 429/418) => +1; lenh duoc san nhan (ok) => 0; loi khac
     * (mang/5xx/nghiep vu) khong doi. Dat {@link #C3_CONSEC} lien tiep => C3 (cung nguong) du cac call doc xen giua thanh cong.
     */
    public synchronized void onOrderResult(long nowMs, String api, boolean ok, boolean rateLimited) {
        roll(nowMs);
        if (rateLimited) {
            order429Consec++;
            lastOrder429Ms = nowMs;
        } else if (ok) {
            if (order429Consec == 0) return;
            order429Consec = 0;
        } else {
            return;
        }
        set("C3", c3Met(nowMs), c3Detail(api), nowMs);
    }

    static boolean c3Order429(int consec429, long sinceLastMs) {
        return consec429 >= C3_CONSEC && sinceLastMs <= C3_ORDER429_HOLD_MS;
    }

    private boolean c3Met(long nowMs) {
        return c3(c3Consec) || c3Order429(order429Consec, nowMs - lastOrder429Ms);
    }

    private String c3Detail(String api) {
        return "api=" + api + " consec=" + c3Consec + " order429=" + order429Consec;
    }

    /**
     * C2 cho c3_live. ref = close nen 1m quyet dinh. Co {@code LIVE_KILLSW_C2_SIGNED=0} (mac dinh): cong thuc v1.1
     * |fill/ref-1| > 2,5 % (y nguyen). Co = 1: coi la lenh MUA, xem {@link #onFill(long, String, boolean, Double, Double)}.
     */
    public synchronized void onFill(long nowMs, String symbol, Double fillPx, Double refPx) {
        if (prm.c2Signed) {
            onFillSigned(nowMs, symbol, true, fillPx, refPx);
            return;
        }
        roll(nowMs);
        lastSlip = c2Slip(fillPx, refPx);
        set("C2", c2(lastSlip), symbol + " slip=" + (lastSlip == null ? "NA" : fmt4(lastSlip)), nowMs);
    }

    /** [V12] C2 co chieu lenh. Co SIGNED=0 => cong thuc v1.1 (bo qua chieu). */
    public synchronized void onFill(long nowMs, String symbol, boolean isBuy, Double fillPx, Double refPx) {
        if (!prm.c2Signed) {
            onFill(nowMs, symbol, fillPx, refPx);
            return;
        }
        onFillSigned(nowMs, symbol, isBuy, fillPx, refPx);
    }

    private void onFillSigned(long nowMs, String symbol, boolean isBuy, Double fillPx, Double refPx) {
        roll(nowMs);
        Double adv = c2Adverse(isBuy, fillPx, refPx);
        lastSlip = adv;
        pruneC2(nowMs);
        String side = isBuy ? "BUY" : "SELL";
        if (adv != null && adv > prm.c2Warn) {
            String m = "[KILLSW] C2_WARN symbol=" + symbol + " side=" + side + " adverse=" + fmt4(adv)
                    + " warn>" + fmt4(prm.c2Warn) + " slip>" + fmt4(prm.c2Slip) + " mode=" + modeLabel;
            sink.warn(m);
            fireAlert(m);
        }
        if (adv != null && adv > prm.c2Slip) {
            c2Events.addLast(nowMs);
            if (mode == Mode.ACT) persistLatch(nowMs);
        }
        boolean met = c2Events.size() >= prm.c2Count;
        set("C2", met, symbol + " " + side + " adverse=" + (adv == null ? "NA" : fmt4(adv)) + " n_slip_win="
                + c2Events.size() + "/" + prm.c2Count + " win_h=" + prm.c2WindowMs / 3_600_000L, nowMs);
    }

    private void pruneC2(long nowMs) {
        while (!c2Events.isEmpty() && c2Events.peekFirst() <= nowMs - prm.c2WindowMs) c2Events.pollFirst();
    }

    /** So GIAY: so cum mo, margin, equity MTM (LEGACY khong nam trong so giay). */
    public synchronized void onPaper(long nowMs, int openPos, float margin, float equity) {
        roll(nowMs);
        lastOpen = openPos;
        lastMargin = margin;
        lastEquity = equity;
        if (prm.c6OwnPeak) {   // [V12 2c CRIT-1] c3_live: dinh rieng tu tmb that, khong san PAPER_EQUITY
            onBookOwnPeak(nowMs, openPos, margin, equity);
            return;
        }
        if (!peakFloorApplied) {
            peakFloorApplied = true;
            double pe = paperEquity == null ? 0d : paperEquity.getAsDouble();
            if (pe > 0d && !(peak >= pe)) peak = pe;
        }
        if (Float.isFinite(equity) && (Double.isNaN(peak) || equity > peak)) peak = equity;
        lastDd = dd(equity, peak);
        float um = uMax == null ? 0f : uMax.get();
        float u = equity > 0f ? margin / equity : Float.NaN;
        boolean c4met = c4(openPos, margin, equity, um);
        set("C4", c4met, "open=" + openPos + " U=" + fmt4(u) + " U_MAX=" + fmt4(um), nowMs);
        if (mode == Mode.ACT && prm.c4Capacity) updateCapacity(c4met, openPos, u, um, nowMs);
        set("C6", c6(lastDd), "dd=" + fmt4(lastDd) + " eq=" + fmt2(equity) + " peak=" + fmt2(peak), nowMs);
        maybeWritePeak(nowMs);
    }

    /** [V12 2c CRIT-1] c3_live: C4 nhu tren; C6 tren tmb that so voi dinh rieng (equity khong hop le => giu C6 cu). */
    private void onBookOwnPeak(long nowMs, int openPos, float margin, float equity) {
        float um = uMax == null ? 0f : uMax.get();
        float u = equity > 0f ? margin / equity : Float.NaN;
        boolean c4met = c4(openPos, margin, equity, um);
        set("C4", c4met, "open=" + openPos + " U=" + fmt4(u) + " U_MAX=" + fmt4(um), nowMs);
        if (mode == Mode.ACT && prm.c4Capacity) updateCapacity(c4met, openPos, u, um, nowMs);
        if (!(Float.isFinite(equity) && equity > 0f)) {
            if (nowMs - lastPeakWarnMs >= EQ_WARN_MS) {
                lastPeakWarnMs = nowMs;
                sink.warn("[KILLSW] C6 c3_live: equity khong hop le (" + equity + ") => giu trang thai C6 cu");
            }
            return;
        }
        if (Double.isNaN(peak) || equity > peak) peak = equity;
        lastDd = dd(equity, peak);
        set("C6", c6(lastDd), "dd=" + fmt4(lastDd) + " eq=" + fmt2(equity) + " peak=" + fmt2(peak) + " (c3_live tmb)", nowMs);
        maybeWritePeak(nowMs);
    }

    /** Thread rieng goi moi ~15 s: lan gio, C1 no_data, C5. [V12] + C2 het cua so, A40 poll, reset owner (ACT). */
    public synchronized void periodic(long nowMs) {
        roll(nowMs);
        // reset owner TRUOC khi danh gia => ma con dat se latch lai ngay trong cung luot
        if (mode == Mode.ACT) checkResetRequest(nowMs);
        evalC1(nowMs);
        long noTick = (nowMs - lastTickStartMs) / 1000L;
        set("C5", c5(noTick), "no_tick_s=" + noTick, nowMs);
        if (prm.c2Signed) {
            int before = c2Events.size();
            pruneC2(nowMs);
            if (c2Events.size() != before || st.get("C2").active) {
                set("C2", c2Events.size() >= prm.c2Count, "n_slip_win=" + c2Events.size() + "/" + prm.c2Count
                        + " (periodic)", nowMs);
            }
        }
        if (equitySource != null) {
            Double eq;
            try {
                eq = equitySource.totalMarginBalance();
            } catch (Throwable e) {
                eq = null;
            }
            onAccountEquity(nowMs, eq);
        }
        // [V12 R4p Bug3] het cua so 429 lenh ma khong co call nao => van ha C3 (bat dau dem sach cho auto-release)
        CodeState c3s = st.get("C3");
        if (c3s != null && c3s.active && !c3Met(nowMs)) set("C3", false, c3Detail(lastApi) + " (het cua so 429 lenh)", nowMs);
        if (mode == Mode.ACT) {
            if (latch != Action.NONE && prm.latchFile != null && !prm.latchFile.exists()) {
                if (nowMs - lastStateWarnMs >= REPEAT_LOG_MS) {
                    lastStateWarnMs = nowMs;
                    sink.warn("[KILLSW] file latch " + prm.latchFile.getPath() + " BI XOA khi dang latch " + latch
                            + " => ghi lai (chi script owner ops/killsw_reset.sh duoc mo latch)");
                }
                persistLatch(nowMs);
            }
        }
        if (mode == Mode.ACT && prm.autoReleaseMs > 0L) maybeAutoRelease(nowMs);
    }

    /**
     * [V12 MASTER 10-25] c3_live (ACT): C1/C5 tu go latch khi ma do SACH LIEN TUC >= autoReleaseMs (30') + Telegram.
     * Ma khac (C2, C3, C4, C6, A40, STATE) giu latch toi khi owner chay ops/killsw_reset.sh.
     */
    private void maybeAutoRelease(long nowMs) {
        if (latch == Action.NONE || latchCodes.isEmpty()) return;
        java.util.List<String> rel = new java.util.ArrayList<>();
        for (String code : latchCodes) {
            if (!prm.autoReleaseCodes.contains(code)) continue;
            CodeState s = st.get(code);
            if (s == null || s.active) continue;
            Long cs = cleanSince.get(code);
            if (cs == null) {
                cleanSince.put(code, nowMs);   // vd latch nap tu file sau restart: bat dau dem tu day
                continue;
            }
            if (nowMs - cs < prm.autoReleaseMs) continue;
            // [V12 2b MASTER 10-25] C3 (loi API lien tiep) can them >= c3ReleaseOkConsec call API thanh cong lien tiep
            if ("C3".equals(code) && apiOkConsec < prm.c3ReleaseOkConsec) continue;
            rel.add(code);
        }
        if (rel.isEmpty()) return;
        Action prev = latch;
        latchCodes.removeAll(rel);
        Action a = Action.NONE;
        for (String c : latchCodes) {
            Action x = CODE_STATE.equals(c) ? Action.NO_NEW_ENTRY : latchActionOf(c);
            if (x.ordinal() > a.ordinal()) a = x;
        }
        latch = a;
        if (latch == Action.NONE) {
            latchSinceMs = 0L;
            latchDetail = "-";
        }
        persistLatch(nowMs);
        String m = "[KILLSW] AUTO_RELEASE codes=" + rel + " sach lien tuc >= " + (prm.autoReleaseMs / 60_000L)
                + "' => latch " + prev + " -> " + latch
                + (latchCodes.isEmpty() ? "" : " (con " + latchCodes + ": chi owner mo bang ops/killsw_reset.sh)");
        sink.warn(m);
        fireAlert(m);
    }

    /**
     * [V12 2b MASTER 10-25] C4 cong suat: dat => chan mo cum moi (Telegram 1 lan); het dat => CHI go khi vi the <= c4ReleasePos
     * VA U <= U_MAX - c4ReleaseUGap (tre, tranh bat/tat lien tuc quanh tran).
     */
    private void updateCapacity(boolean met, int openPos, float u, float um, long nowMs) {
        if (met) {
            if (!c4Cap) {
                c4Cap = true;
                c4CapSinceMs = nowMs;
                String m = "[KILLSW] C4_CAPACITY ON open=" + openPos + " U=" + fmt4(u) + " U_MAX=" + fmt4(um)
                        + " => CHAN MO CUM MOI (DCA cum dang co van chay, throttle U_MAX); tu go khi open<=" + prm.c4ReleasePos
                        + " va U<=U_MAX-" + prm.c4ReleaseUGap;
                sink.warn(m);
                fireAlert(m);
            }
            return;
        }
        if (!c4Cap) return;
        boolean rel = openPos <= prm.c4ReleasePos && Float.isFinite(u) && u <= um - prm.c4ReleaseUGap;
        if (rel) {
            c4Cap = false;
            String m = "[KILLSW] C4_CAPACITY OFF open=" + openPos + " U=" + fmt4(u) + " (sau " + (nowMs - c4CapSinceMs) / 60_000L
                    + "') => mo cum moi tro lai";
            sink.warn(m);
            fireAlert(m);
        }
    }

    private void evalC1(long nowMs) {
        long since = (nowMs - lastMarketDataMs) / 1000L;
        boolean noData = c1NoData(since);
        set("C1", c1Data || noData, (noData ? "NO_DATA since_s=" + since + " " : "") + c1DataDetail, nowMs);
    }

    private void set(String code, boolean met, String detail, long nowMs) {
        CodeState s = st.get(code);
        s.detail = detail;
        if (met) {
            s.metHour++;
            s.metTotal++;
            if (!s.active) {
                s.active = true;
                s.since = nowMs;
                s.edgesHour++;
                s.edgesTotal++;
                s.lastLog = nowMs;
                sink.warn(line(what(), code, s, nowMs, "START"));
            } else if (nowMs - s.lastLog >= REPEAT_LOG_MS) {
                s.lastLog = nowMs;
                sink.warn(line(what(), code, s, nowMs, "CONT"));
            }
            cleanSince.remove(code);
            if (mode == Mode.ACT && !(prm.c4Capacity && "C4".equals(code))) latchFor(code, detail, nowMs);
        } else if (s.active) {
            s.active = false;
            cleanSince.put(code, nowMs);
            sink.info("[KILLSW] CLEAR code=" + code + " mode=" + modeLabel + " dur_s=" + (nowMs - s.since) / 1000L
                    + " detail=" + detail);
        }
    }

    private String what() {
        return mode == Mode.ACT ? "TRIGGER" : "WOULD_TRIGGER";
    }

    /** [V12] ACT: latch theo ma (moi lan dat, khong chi canh len => sau reset ma van dat thi latch lai ngay). */
    private void latchFor(String code, String detail, long nowMs) {
        Action a = latchActionOf(code);
        boolean newCode = latchCodes.add(code);
        if (a.ordinal() > latch.ordinal()) {
            Action prev = latch;
            if (prev == Action.NONE) latchSinceMs = nowMs;
            latch = a;
            latchDetail = code + ": " + detail;
            persistLatch(nowMs);
            String m = "[KILLSW] LATCH action=" + a + " (truoc " + prev + ") code=" + code + " codes=" + latchCodes
                    + " detail=" + detail + " | " + (a == Action.FLATTEN
                    ? "DONG HET reduce-only chia lo + dung; " : "dung mo moi, van quan ly vi the; ")
                    + "chi owner mo lai bang ops/killsw_reset.sh";
            sink.warn(m);
            fireAlert(m);
        } else if (newCode) {
            persistLatch(nowMs);
            sink.warn("[KILLSW] LATCH them code=" + code + " (giu " + latch + ") codes=" + latchCodes + " detail=" + detail);
        }
    }

    private void fireAlert(String m) {
        Consumer<String> a = alert;
        if (a == null) {
            // [2e] c3_live (peakTag != null): canh bao luc nap file (truoc setAlert) giu lai, gui khi setAlert. c3_shadow: nhu cu.
            if (prm.peakTag != null && earlyAlerts.size() < 8) earlyAlerts.add(m);
            return;
        }
        try {
            a.accept(m);
        } catch (Throwable ignore) {
            // alert khong duoc lam hong engine
        }
    }

    // ------------------------------------------------------------------ [V12] persist latch (chi mode ACT)

    /** Engine la nguoi ghi DUY NHAT file latch (atomic tmp + move). */
    private void persistLatch(long nowMs) {
        if (mode != Mode.ACT || prm.latchFile == null) return;
        JsonObject o = new JsonObject();
        o.addProperty("version", 1);
        o.addProperty("latch", latch.name());
        JsonArray codes = new JsonArray();
        for (String c : latchCodes) codes.add(c);
        o.add("codes", codes);
        o.addProperty("since_ms", latch == Action.NONE ? 0L : latchSinceMs);
        o.addProperty("detail", latchDetail);
        JsonArray ev = new JsonArray();
        for (Long t : c2Events) ev.add(t);
        o.add("c2_events_ms", ev);
        if (acctPeak > 0d) o.addProperty("acct_peak", acctPeak);
        if (acctPeak > 0d && prm.peakTag != null) o.addProperty("acct_peak_adapter", prm.peakTag);
        if (prm.peakTag != null) o.addProperty("adapter", prm.peakTag);   // [2e] nhan adapter cua ca file latch
        o.addProperty("last_reset_at_ms", lastResetAtMs);
        o.addProperty("updated_ms", nowMs);
        try {
            File abs = prm.latchFile.getAbsoluteFile();
            File dir = abs.getParentFile();
            if (dir != null && !dir.exists()) dir.mkdirs();
            File tmp = new File(dir, abs.getName() + ".tmp");
            Files.write(tmp.toPath(), (o.toString() + "\n").getBytes(StandardCharsets.UTF_8));
            Files.move(tmp.toPath(), abs.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
            if (acctPeak > 0d) acctPeakWritten = acctPeak;
        } catch (Exception e) {
            if (nowMs - lastStateWarnMs >= REPEAT_LOG_MS) {
                lastStateWarnMs = nowMs;
                sink.warn("[KILLSW] khong ghi duoc file latch " + prm.latchFile.getPath() + ": " + e
                        + " (latch van giu trong RAM)");
            }
        }
    }

    /** Nap latch luc khoi dong. File hong => FAIL-CLOSED: latch NO_NEW_ENTRY code=STATE (sao luu file hong). */
    private void loadLatch(long nowMs) {
        File f = prm.latchFile;
        if (f == null) {
            sink.warn("[KILLSW] mode=act KHONG co file latch => latch KHONG song qua restart");
            return;
        }
        if (!f.exists()) {
            sink.info("[KILLSW] chua co file latch " + f.getPath() + " => khong latch");
            return;
        }
        try {
            String s = new String(Files.readAllBytes(f.toPath()), StandardCharsets.UTF_8);
            JsonObject o = JsonParser.parseString(s).getAsJsonObject();
            Action a = Action.valueOf(o.get("latch").getAsString().trim());
            latch = a;
            latchCodes.clear();
            if (o.has("codes")) for (JsonElement e : o.getAsJsonArray("codes")) latchCodes.add(e.getAsString());
            latchSinceMs = o.has("since_ms") ? o.get("since_ms").getAsLong() : 0L;
            latchDetail = o.has("detail") ? o.get("detail").getAsString() : "-";
            c2Events.clear();
            if (o.has("c2_events_ms")) for (JsonElement e : o.getAsJsonArray("c2_events_ms")) c2Events.addLast(e.getAsLong());
            String apTag = o.has("acct_peak_adapter") ? o.get("acct_peak_adapter").getAsString() : null;
            if (o.has("acct_peak") && prm.peakTag != null && !prm.peakTag.equals(apTag)) {   // [2d MIN-19]
                sink.warn("[KILLSW] acct_peak trong " + f.getPath() + " cua adapter=" + (apTag == null ? "(khong nhan)" : apTag)
                        + " != adapter hien tai " + prm.peakTag + " => BO QUA (A40 lay lai dinh tu tmb that dau tien)");
            } else if (o.has("acct_peak")) {
                double p = o.get("acct_peak").getAsDouble();
                if (Double.isFinite(p) && p > 0d) {
                    acctPeak = p;
                    acctPeakWritten = p;
                }
            }
            lastResetAtMs = o.has("last_reset_at_ms") ? o.get("last_reset_at_ms").getAsLong() : 0L;
            // [2e] file latch cua adapter KHAC (vd dry -> live): KHONG tu bo latch / su kien C2 (huong an toan), chi WARN + Telegram
            // huong dan owner reset co chu dich bang ops/killsw_reset.sh
            if (prm.peakTag != null) {
                String lt = o.has("adapter") ? o.get("adapter").getAsString() : null;
                if (!prm.peakTag.equals(lt) && latch == Action.NONE && c2Events.isEmpty()) {
                    sink.info("[KILLSW] file latch " + f.getPath() + " cua adapter=" + (lt == null ? "(khong nhan)" : lt)
                            + " != " + prm.peakTag + " nhung khong co latch / su kien C2 => khong co gi de giu");
                } else if (!prm.peakTag.equals(lt)) {
                    String m = "[KILLSW] file latch " + f.getPath() + " cua adapter=" + (lt == null ? "(khong nhan)" : lt)
                            + " != adapter hien tai " + prm.peakTag + ": GIU nguyen latch=" + latch + " codes=" + latchCodes
                            + " c2_events=" + c2Events.size() + " (an toan). Neu chuyen adapter CO CHU DICH: owner chay"
                            + " DRY=0 RESET_PEAK=1 bash ops/killsw_reset.sh";
                    sink.warn(m);
                    fireAlert(m);
                }
            }
            if (prm.c4Capacity && latchCodes.remove("C4")) {   // [V12 2b] C4 la cong suat, khong latch (file cu)
                Action a0 = Action.NONE;
                for (String c : latchCodes) {
                    Action x = CODE_STATE.equals(c) ? Action.NO_NEW_ENTRY : latchActionOf(c);
                    if (x.ordinal() > a0.ordinal()) a0 = x;
                }
                latch = a0;
                if (latch == Action.NONE) {
                    latchSinceMs = 0L;
                    latchDetail = "-";
                }
                sink.warn("[KILLSW] file latch co C4 => bo (C4 la dieu kien cong suat, khong latch) => latch=" + latch);
            }
            if (latch != Action.NONE) {
                String m = "[KILLSW] NAP LATCH tu " + f.getPath() + ": " + latch + " codes=" + latchCodes + " since_ms="
                        + latchSinceMs + " detail=" + latchDetail + " => van chan (chi owner mo bang ops/killsw_reset.sh)";
                sink.warn(m);
                fireAlert(m);
            } else {
                sink.info("[KILLSW] nap file latch " + f.getPath() + ": NONE c2_events=" + c2Events.size()
                        + " acct_peak=" + fmt2(acctPeak));
            }
        } catch (Exception e) {
            File bak = new File(f.getPath() + ".corrupt_" + nowMs);
            try {
                Files.copy(f.toPath(), bak.toPath(), StandardCopyOption.REPLACE_EXISTING);
            } catch (Exception ignore) {
                // giu file goc neu khong sao luu duoc
            }
            latch = Action.NO_NEW_ENTRY;
            latchCodes.clear();
            latchCodes.add(CODE_STATE);
            latchSinceMs = nowMs;
            latchDetail = "file latch hong: " + e;
            String m = "[KILLSW] FAIL-CLOSED file latch " + f.getPath() + " khong doc duoc (" + e + ") => latch NO_NEW_ENTRY"
                    + " code=STATE, sao luu " + bak.getName();
            sink.warn(m);
            fireAlert(m);
            persistLatch(nowMs);
        }
    }

    /**
     * Yeu cau reset cua owner ({@code ops/killsw_reset.sh} ghi {@code resetFile}): {"reset_at_ms":..,"reset_by":..,
     * "reset_peak":0|1}. Ap dung: latch NONE, xoa ma + su kien C2; reset_peak=1 => dinh equity that ve NaN (lay lai
     * tu equity hien tai). File yeu cau doi ten {@code .done_<ms>}. Ma con dat => latch lai o lan danh gia ke.
     */
    private void checkResetRequest(long nowMs) {
        File f = prm.resetFile;
        if (f == null || !f.exists()) return;
        long at = nowMs;
        String by = "-";
        boolean resetPeak = false;
        try {
            String s = new String(Files.readAllBytes(f.toPath()), StandardCharsets.UTF_8);
            JsonObject o = JsonParser.parseString(s).getAsJsonObject();
            if (o.has("reset_at_ms")) at = o.get("reset_at_ms").getAsLong();
            if (o.has("reset_by")) by = o.get("reset_by").getAsString();
            if (o.has("reset_peak")) resetPeak = o.get("reset_peak").getAsInt() == 1;
        } catch (Exception e) {
            sink.warn("[KILLSW] file reset " + f.getPath() + " khong hop le (" + e + ") => BO QUA, doi ten .bad");
            try {
                Files.move(f.toPath(), new File(f.getPath() + ".bad_" + nowMs).toPath(), StandardCopyOption.REPLACE_EXISTING);
            } catch (Exception ignore) {
                // de nguyen
            }
            return;
        }
        Action prev = latch;
        Set<String> prevCodes = new LinkedHashSet<>(latchCodes);
        latch = Action.NONE;
        latchCodes.clear();
        latchSinceMs = 0L;
        latchDetail = "-";
        c2Events.clear();
        if (resetPeak) {
            acctPeak = Double.NaN;
            acctPeakWritten = Double.NaN;
            if (prm.c6OwnPeak) {   // [V12 2c CRIT-1] dinh C6 rieng c3_live cung dat lai (lay lai tu tmb ke tiep)
                peak = Double.NaN;
                peakWritten = Double.NaN;
                lastDd = Double.NaN;
                if (peakFile != null) {
                    try {
                        Files.deleteIfExists(peakFile.toPath());
                    } catch (Exception e) {
                        sink.warn("[KILLSW] reset_peak: khong xoa duoc file dinh " + peakFile.getPath() + ": " + e
                                + " (dinh RAM da dat lai; file se ghi de khi co dinh moi)");
                    }
                }
            }
        }
        lastResetAtMs = at;
        for (Iterator<CodeState> it = st.values().iterator(); it.hasNext(); ) {
            CodeState s = it.next();
            s.active = false;   // ma con dat => canh len moi + latch lai
        }
        persistLatch(nowMs);
        try {
            Files.move(f.toPath(), new File(f.getPath() + ".done_" + nowMs).toPath(), StandardCopyOption.REPLACE_EXISTING);
        } catch (Exception e) {
            try {
                Files.deleteIfExists(f.toPath());
            } catch (Exception ignore) {
                // lan sau se ap dung lai (idempotent)
            }
        }
        String m = "[KILLSW] RESET boi owner (" + by + ", reset_at_ms=" + at + ", reset_peak=" + (resetPeak ? 1 : 0)
                + "): " + prev + " codes=" + prevCodes + " => NONE";
        sink.warn(m);
        fireAlert(m);
    }

    private String line(String what, String code, CodeState s, long nowMs, String edge) {
        return "[KILLSW] " + what + " code=" + code + " mode=" + modeLabel + " action=" + action(code)
                + " edge=" + edge + " n_hour=" + s.metHour + " dur_s=" + (nowMs - s.since) / 1000L + " detail=" + s.detail;
    }

    private void roll(long nowMs) {
        String h = hourKey(nowMs);
        if (h.equals(hour)) return;
        sink.info(hourlyLine(hour));
        for (CodeState s : st.values()) {
            s.metHour = 0;
            s.edgesHour = 0;
        }
        hour = h;
    }

    String hourlyLine(String hourKey) {
        StringBuilder b = new StringBuilder("[KILLSW] HOURLY hour=").append(hourKey).append(" mode=").append(modeLabel);
        for (Map.Entry<String, CodeState> e : st.entrySet()) {
            CodeState s = e.getValue();
            b.append(' ').append(e.getKey()).append('=');
            if ("C2".equals(e.getKey()) && s.metTotal == 0 && lastSlip == null) b.append("NA");
            else b.append(s.metHour).append('/').append(s.edgesHour);
        }
        b.append(" (met/edge) | lag_s=").append(lastLagSec == Long.MIN_VALUE ? "-" : String.valueOf(lastLagSec))
                .append(" miss=").append(lastMiss).append('/').append(lastUni)
                .append(" api=").append(lastApi).append(" consec=").append(c3Consec).append(" order429=").append(order429Consec)
                .append(" open=").append(lastOpen)
                .append(" U=").append(fmt4(lastEquity > 0f ? lastMargin / lastEquity : Float.NaN))
                .append(" eq=").append(fmt2(lastEquity)).append(" peak=").append(fmt2(peak))
                .append(" dd=").append(fmt4(lastDd));
        if (st.containsKey(CODE_A40)) {
            b.append(" acct_eq=").append(fmt2(lastAcctEq)).append(" acct_peak=").append(fmt2(acctPeak))
                    .append(" acct_dd=").append(fmt4(lastAcctDd));
        }
        if (mode == Mode.ACT) b.append(" latch=").append(latch).append(latchCodes.isEmpty() ? "" : latchCodes.toString());
        return b.toString();
    }

    // ------------------------------------------------------------------ doc cho test/health
    synchronized long metTotal(String code) {
        return st.get(code).metTotal;
    }

    synchronized long edgesTotal(String code) {
        return st.get(code).edgesTotal;
    }

    synchronized long metHour(String code) {
        return st.get(code).metHour;
    }

    synchronized boolean active(String code) {
        return st.get(code).active;
    }

    synchronized double peak() {
        return peak;
    }

    synchronized double acctPeak() {
        return acctPeak;
    }

    synchronized int c2EventCount() {
        return c2Events.size();
    }

    private static String fmt2(double v) {
        return Double.isNaN(v) ? "-" : String.format(Locale.ROOT, "%.2f", v);
    }

    private static String fmt4(double v) {
        return Double.isNaN(v) ? "-" : String.format(Locale.ROOT, "%.4f", v);
    }
}
