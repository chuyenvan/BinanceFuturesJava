package com.binance.chuyennd.ops;

import com.binance.chuyennd.object.sw.KlineObjectSimple;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
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
 * Dac ta hanh dong khi act (cho c3_live sau nay, CHUA cai trong v11d — {@link #ACT_IMPLEMENTED} = false):
 * C1–C5 => dung mo lenh moi + Telegram, van quan ly vi the dang mo; C6/A40 => dong het + dung, cho owner.
 */
public final class KillSwitchEngine {

    public enum Mode { OFF, LOG, ACT }

    /** v11d khong cai hanh dong nao cho act. */
    public static final boolean ACT_IMPLEMENTED = false;

    public static final long C1_LAG_SEC = 180L;
    /** missing/universe > 10 % (so nguyen: missing*10 > universe). */
    public static final int C1_MISSING_PCT = 10;
    public static final long C1_UNIVERSE_LOOKBACK_MIN = 60L;
    public static final long C1_NODATA_SEC = 240L;
    public static final double C2_SLIP = 0.025;
    public static final int C3_CONSEC = 5;
    public static final int C4_MAX_POS = 90;
    public static final long C5_NOTICK_SEC = 300L;
    public static final double C6_DD = -0.40;
    public static final String REF_SYMBOL = "BTCUSDT";
    public static final String[] CODES = {"C1", "C2", "C3", "C4", "C5", "C6"};
    static final long REPEAT_LOG_MS = 60_000L;
    static final long PEAK_WRITE_MIN_MS = 60_000L;
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

    /**
     * off|log|act theo profile. c3_shadow (va moi profile khac c3_live): chi off|log — act BI TU CHOI + WARN, chay log.
     * c3_live + act: hop le ve chinh sach, nhung v11d chua cai hanh dong => chay log + WARN. Gia tri la => off + WARN.
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

    /** null = N/A (khong co fill that hoac thieu gia tham chieu). */
    static Double c2Slip(Double fill, Double ref) {
        if (fill == null || ref == null || !(ref > 0d) || !(fill > 0d)) return null;
        return Math.abs(fill / ref - 1.0);
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
        return "C6".equals(code) ? "CLOSE_ALL+HALT" : "STOP_NEW_ENTRIES+TELEGRAM(van quan ly vi the)";
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

    /**
     * @param mode        mode HIEU LUC (LOG; ACT chi khi da cai). OFF => khong nen tao engine.
     * @param modeLabel   chuoi in trong log (vd "log", "log(act_tu_choi)")
     * @param peakFile    file luu dinh equity (null = khong luu)
     * @param paperEquity PAPER_EQUITY — san cua dinh (doc tre, lan dau co so giay)
     * @param uMax        tran U cho C4 (Configs.U_MAX) — doc tre
     */
    public KillSwitchEngine(Mode mode, String modeLabel, Sink sink, File peakFile, DoubleSupplier paperEquity,
                            Supplier<Float> uMax, long nowMs) {
        this.mode = mode;
        this.modeLabel = modeLabel;
        this.sink = sink;
        this.peakFile = peakFile;
        this.paperEquity = paperEquity;
        this.uMax = uMax;
        for (String c : CODES) st.put(c, new CodeState());
        this.lastTickStartMs = nowMs;
        this.lastMarketDataMs = nowMs;
        this.hour = hourKey(nowMs);
        loadPeak();
    }

    public Mode mode() {
        return mode;
    }

    private void loadPeak() {
        if (peakFile == null || !peakFile.exists()) return;
        try {
            String s = new String(Files.readAllBytes(peakFile.toPath()), StandardCharsets.UTF_8).trim();
            double v = Double.parseDouble(s);
            if (Double.isFinite(v) && v > 0d) {
                peak = v;
                peakWritten = v;
                sink.info("[KILLSW] nap dinh equity giay tu " + peakFile.getAbsolutePath() + " = " + fmt2(v));
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
            Files.write(tmp.toPath(), (Double.toString(peak) + "\n").getBytes(StandardCharsets.UTF_8));
            Files.move(tmp.toPath(), abs.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
            peakWritten = peak;
        } catch (Exception e) {
            if (nowMs - lastPeakWarnMs >= 3_600_000L) {
                lastPeakWarnMs = nowMs;
                sink.warn("[KILLSW] khong ghi duoc file dinh " + peakFile.getAbsolutePath() + ": " + e);
            }
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
        set("C3", c3(c3Consec), "api=" + api + " consec=" + c3Consec, nowMs);
    }

    /** C2 cho c3_live sau nay (KHONG noi o v11d). ref = close nen quyet dinh. */
    public synchronized void onFill(long nowMs, String symbol, Double fillPx, Double refPx) {
        roll(nowMs);
        lastSlip = c2Slip(fillPx, refPx);
        set("C2", c2(lastSlip), symbol + " slip=" + (lastSlip == null ? "NA" : fmt4(lastSlip)), nowMs);
    }

    /** So GIAY: so cum mo, margin, equity MTM (LEGACY khong nam trong so giay). */
    public synchronized void onPaper(long nowMs, int openPos, float margin, float equity) {
        roll(nowMs);
        lastOpen = openPos;
        lastMargin = margin;
        lastEquity = equity;
        if (!peakFloorApplied) {
            peakFloorApplied = true;
            double pe = paperEquity == null ? 0d : paperEquity.getAsDouble();
            if (pe > 0d && !(peak >= pe)) peak = pe;
        }
        if (Float.isFinite(equity) && (Double.isNaN(peak) || equity > peak)) peak = equity;
        lastDd = dd(equity, peak);
        float um = uMax == null ? 0f : uMax.get();
        float u = equity > 0f ? margin / equity : Float.NaN;
        set("C4", c4(openPos, margin, equity, um), "open=" + openPos + " U=" + fmt4(u) + " U_MAX=" + fmt4(um), nowMs);
        set("C6", c6(lastDd), "dd=" + fmt4(lastDd) + " eq=" + fmt2(equity) + " peak=" + fmt2(peak), nowMs);
        maybeWritePeak(nowMs);
    }

    /** Thread rieng goi moi ~15 s: lan gio, C1 no_data, C5. */
    public synchronized void periodic(long nowMs) {
        roll(nowMs);
        evalC1(nowMs);
        long noTick = (nowMs - lastTickStartMs) / 1000L;
        set("C5", c5(noTick), "no_tick_s=" + noTick, nowMs);
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
                sink.warn(line("WOULD_TRIGGER", code, s, nowMs, "START"));
            } else if (nowMs - s.lastLog >= REPEAT_LOG_MS) {
                s.lastLog = nowMs;
                sink.warn(line("WOULD_TRIGGER", code, s, nowMs, "CONT"));
            }
        } else if (s.active) {
            s.active = false;
            sink.info("[KILLSW] CLEAR code=" + code + " mode=" + modeLabel + " dur_s=" + (nowMs - s.since) / 1000L
                    + " detail=" + detail);
        }
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
                .append(" api=").append(lastApi).append(" consec=").append(c3Consec)
                .append(" open=").append(lastOpen)
                .append(" U=").append(fmt4(lastEquity > 0f ? lastMargin / lastEquity : Float.NaN))
                .append(" eq=").append(fmt2(lastEquity)).append(" peak=").append(fmt2(peak))
                .append(" dd=").append(fmt4(lastDd));
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

    private static String fmt2(double v) {
        return Double.isNaN(v) ? "-" : String.format(Locale.ROOT, "%.2f", v);
    }

    private static String fmt4(double v) {
        return Double.isNaN(v) ? "-" : String.format(Locale.ROOT, "%.4f", v);
    }
}
