package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.nio.file.Files;
import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.function.Predicate;

/**
 * [TS-MKT-EXT v1.1] Gia han time-stop 168h cua SO GIAY c3_shadow toi da +336h (X14) vao ngay UTC co co
 * "ca thi truong alt dang sap" — {@code docs/plan/V11_TS_MKT_EXT_LIVE.md}; luat sim
 * {@code SimulatorMarketLevelTicker1MStopLoss.java:1042-1058} (feat/ts-mkt-ext a8690d46).
 *
 * <p>🔒 PHAM VI: CHI {@link ShadowBookC3#tick} (vi the GIAY) goi {@link #deferTimeStop}. Duong vi the THAT
 * (LEGACY, {@code BinanceOrderTradingManager}) KHONG tham chieu lop nay. Them chot kep: symbol LEGACY ⇒ khong
 * bao gio hoan ({@link #decide}). Bat ⟺ {@code LIVE_TS_MKT_EXT=1} ∧ {@code LIVE_PROFILE=c3_shadow}; mac dinh TAT ⇒
 * {@link #deferTimeStop} tra {@code false} ngay ⇒ y het v11b.
 *
 * <p>Du lieu: {@code kline_1m_opt} ma chinh JVM live doc ({@code readDataFromAerospikeCustom}); tong ngay luu
 * {@code run/ts_ext_daily.csv} de restart khong phai doc lai. Lich: co(D) tinh sau 00:03 UTC, cho nen 23:59 toi
 * 00:20 UTC; trong luc chua co co hom nay (PENDING) thi GIU cum trong cua so (khong cat).
 */
public final class TsMktExt {

    private static final Logger LOG = LoggerFactory.getLogger(TsMktExt.class);

    public static final String KEY_ENABLE = "LIVE_TS_MKT_EXT";
    public static final String KEY_FILE = "LIVE_TS_EXT_FILE";
    public static final String DEFAULT_FILE = "run/ts_ext_daily.csv";
    /** Time-stop goc cua so giay (= sim LOSER_TIME_STOP_HOURS 168). */
    public static final int BASE_HOURS = LiveProfileC3.TIME_STOP_HOURS;
    /** X14: SIM_LOSER_TS_EXT_HOURS = 336 (dong bang). */
    public static final int EXT_HOURS = 336;
    public static final long HOUR = 3_600_000L;
    public static final long COMPUTE_AFTER_MS = 3 * 60_000L;
    public static final long FINAL_DEADLINE_MS = 20 * 60_000L;
    public static final long PENDING_MAX_MS = FINAL_DEADLINE_MS + 2 * 60_000L;
    public static final long START_GRACE_MS = 20 * 60_000L;
    public static final int SEED_CHUNK_MIN = 60;
    public static final long SEED_PAUSE_MS = 200L;

    public enum Flag { ON, OFF, PENDING }

    public enum Decision { NOT_DUE, DEFER, CUT }

    /** Doc phut tu store (live: Aerospike). */
    interface MinuteReader {
        TreeMap<Long, Map<String, KlineObjectSimple>> read(long startMs, int minutes);
    }

    private static final boolean ENABLED;
    static volatile Boolean enabledForTest = null;
    static volatile Predicate<String> legacyCheck = LegacySymbols::isLegacySymbol;
    private static volatile TsMktExt INSTANCE;

    static {
        String v = Cfg.get(KEY_ENABLE);
        ENABLED = decideEnabled(v, LiveProfileC3.on(), LiveProfileC3.isLive());
        if (v != null && !ENABLED) {
            LOG.warn("[TS-EXT] TAT: {}={} nhung profile on={} live={} (chi bat cho LIVE_PROFILE=c3_shadow)",
                    KEY_ENABLE, v, LiveProfileC3.on(), LiveProfileC3.isLive());
        }
    }

    /** Thuan tinh toan cua cong bat. c3_live (co the day lenh that) ⇒ KHONG bat. */
    static boolean decideEnabled(String v, boolean profileOn, boolean profileLive) {
        return v != null && "1".equals(v.trim()) && profileOn && !profileLive;
    }

    public static boolean enabled() {
        Boolean t = enabledForTest;
        return t != null ? t : ENABLED;
    }

    /**
     * Quyet dinh time-stop cua MOT cum chua arm (thuan tinh toan). Sim {@code :1044-1057}:
     * age ≤ 168h ⇒ chua toi; tat / LEGACY ⇒ cat nhu v11b; age > 504h ⇒ cat; co ON (hoac PENDING) ⇒ hoan.
     */
    public static Decision decide(boolean enabled, boolean legacy, long ageMs, Flag flag) {
        if (ageMs <= BASE_HOURS * HOUR) return Decision.NOT_DUE;
        if (!enabled || legacy) return Decision.CUT;
        if (ageMs > (long) (BASE_HOURS + EXT_HOURS) * HOUR) return Decision.CUT;
        return (flag == Flag.ON || flag == Flag.PENDING) ? Decision.DEFER : Decision.CUT;
    }

    /**
     * Cong DUY NHAT tu {@link ShadowBookC3#tick} (so GIAY), goi khi cum chua arm va age > 168h. true ⇒ KHONG cat
     * o nhip nay. Co TAT ⇒ false ngay (v11b).
     */
    public static boolean deferTimeStop(String symbol, long tsFirstLeg, long now) {
        if (!enabled()) return false;
        TsMktExt x = getInstance();
        boolean legacy = symbol != null && legacyCheck.test(symbol);   // [LEGACY-GUARD] vi the that: khong bao gio
        Flag f = x.flagFor(Math.floorDiv(now, AltEwIndex.DAY), now);
        Decision d = decide(true, legacy, now - tsFirstLeg, f);
        x.track(symbol, tsFirstLeg, now, d, f, legacy);
        return d == Decision.DEFER;
    }

    /** Cum vua arm trailing (khong con thuoc time-stop). */
    public static void onArmed(String symbol, long tsFirstLeg, long now) {
        if (!enabled()) return;
        TsMktExt x = INSTANCE;
        if (x != null) x.endDefer(symbol, tsFirstLeg, now, "ARMED");
    }

    /** Cum vua dong (bat ky ly do). */
    public static void onClosed(String symbol, long tsFirstLeg, String reason, long now) {
        if (!enabled()) return;
        TsMktExt x = INSTANCE;
        if (x != null) x.endDefer(symbol, tsFirstLeg, now, "CLOSED_" + reason);
    }

    /** Khoi dong (idempotent) khi bat — goi tu constructor ShadowBookC3. */
    public static void startIfEnabled() {
        if (enabled()) getInstance();
    }

    public static TsMktExt getInstance() {
        if (INSTANCE == null) {
            synchronized (TsMktExt.class) {
                if (INSTANCE == null) {
                    TsMktExt x = new TsMktExt(TsMktExt::aeroRead, new File(Cfg.getOr(KEY_FILE, DEFAULT_FILE)),
                            System.currentTimeMillis(), SEED_PAUSE_MS);
                    LOG.info("[TS-EXT] BAT {}=1 profile=c3_shadow baseH={} extH={} thr={} minN={} file={} days_loaded={}",
                            KEY_ENABLE, BASE_HOURS, EXT_HOURS, AltEwIndex.DD_THRESHOLD,
                            AltEwIndex.MIN_MINUTES_PER_DAY, x.file.getAbsolutePath(), x.days.size());
                    x.startScheduler();
                    INSTANCE = x;
                }
            }
        }
        return INSTANCE;
    }

    /** CHI cho unit test. */
    static void setInstanceForTest(TsMktExt x) {
        synchronized (TsMktExt.class) {
            INSTANCE = x;
        }
    }

    private static TreeMap<Long, Map<String, KlineObjectSimple>> aeroRead(long startMs, int minutes) {
        return DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(startMs, minutes);
    }

    // ===================================== instance =====================================
    private final MinuteReader reader;
    final File file;
    private final long startedAt;
    private final long pauseMs;
    final ConcurrentHashMap<Long, AltEwIndex.DayStat> days = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<Long, AltEwIndex.FlagResult> flags = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Long> deferring = new ConcurrentHashMap<>();
    private volatile long lastWarnAt = Long.MIN_VALUE;
    private volatile long lastStatusHour = Long.MIN_VALUE;
    private volatile long lastWaitLogDay = Long.MIN_VALUE;
    /** So lan doc store (de test restart). */
    int readCalls = 0;

    TsMktExt(MinuteReader reader, File file, long startedAt, long pauseMs) {
        this.reader = reader;
        this.file = file;
        this.startedAt = startedAt;
        this.pauseMs = pauseMs;
        load();
    }

    private void startScheduler() {
        ScheduledExecutorService ex = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "TS-EXT");
            t.setDaemon(true);
            return t;
        });
        ex.scheduleWithFixedDelay(() -> {
            try {
                refresh(System.currentTimeMillis());
            } catch (Throwable e) {
                LOG.error("[TS-EXT] loi refresh: {}", e.toString());
            }
        }, 0L, 60L, TimeUnit.SECONDS);
    }

    /** Co cua ngay UTC {@code day} tai {@code now}: co roi ⇒ ON/OFF (NA ⇒ OFF); chua co ⇒ PENDING trong han. */
    Flag flagFor(long day, long now) {
        AltEwIndex.FlagResult r = flags.get(day);
        if (r != null) return r.state == AltEwIndex.State.ON ? Flag.ON : Flag.OFF;
        long since = now - day * AltEwIndex.DAY;
        if ((since >= 0 && since < PENDING_MAX_MS) || now - startedAt < START_GRACE_MS) return Flag.PENDING;
        if (now - lastWarnAt > HOUR) {
            lastWarnAt = now;
            LOG.warn("[TS-EXT] chua co co ngay {} sau han (since={}m, start={}m) -> OFF", LocalDate.ofEpochDay(day),
                    since / 60_000L, (now - startedAt) / 60_000L);
        }
        return Flag.OFF;
    }

    /** CHI cho unit test: dat co mot ngay. */
    void setFlagForTest(long day, AltEwIndex.State s) {
        flags.put(day, new AltEwIndex.FlagResult(day, s, Double.NaN, Double.NaN, Double.NaN, -1L, 0, "test"));
    }

    AltEwIndex.FlagResult flagResult(long day) {
        return flags.get(day);
    }

    /** Mot vong lich (moi 60 s): chot co hom nay khi du dieu kien. */
    synchronized void refresh(long now) {
        long today = Math.floorDiv(now, AltEwIndex.DAY);
        statusIfDue(now, today);
        if (flags.containsKey(today)) return;
        long since = now - today * AltEwIndex.DAY;
        if (since < COMPUTE_AFTER_MS) return;
        boolean finalPass = since >= FINAL_DEADLINE_MS;
        long last = today - 1;
        if (!days.containsKey(last) && !finalPass && !lastMinutePresent(last)) {
            if (lastWaitLogDay != today) {
                lastWaitLogDay = today;
                LOG.info("[TS-EXT] cho nen 23:59 UTC ngay {} (since={}m)", LocalDate.ofEpochDay(last), since / 60_000L);
            }
            return;
        }
        int read = 0;
        for (long j = today - AltEwIndex.WINDOW_DAYS; j <= last; j++) {
            if (days.containsKey(j)) continue;
            AltEwIndex.DayStat s = computeDay(j);
            read++;
            days.put(j, s);
            // de doi chieu sau voi Vision (cung luat): tong EW + so phut cua ngay doc tu store
            LOG.info("[TS-EXT] day {} sum_ew={} n_min={} src=aero", LocalDate.ofEpochDay(j), Double.toString(s.sum), s.n);
            if (s.n >= AltEwIndex.MIN_MINUTES_PER_DAY) {
                persist(s);
            } else {
                LOG.warn("[TS-EXT] ngay {} chi co {} phut EW (< {}) - giu trong RAM, khong ghi file",
                        LocalDate.ofEpochDay(j), s.n, AltEwIndex.MIN_MINUTES_PER_DAY);
            }
        }
        AltEwIndex.FlagResult r = AltEwIndex.flagFor(today, days);
        flags.put(today, r);
        String src = read > 0 ? ("aero:" + read + "d") : "file";
        if (r.state == AltEwIndex.State.NA) {
            LOG.warn("[TS-EXT] flag day={} flag=NA(->OFF) reason={} src={} final={}", LocalDate.ofEpochDay(today),
                    r.reason, src, finalPass);
        } else {
            LOG.info("[TS-EXT] flag day={} flag={} dd={} altEwIdx={} P={} max30={} max30Day={} minN={} src={} final={}",
                    LocalDate.ofEpochDay(today), r.state, String.format("%.6f", r.dd), String.format("%.6f", 1.0 + r.dd),
                    String.format("%.6f", r.p), String.format("%.6f", r.maxP), LocalDate.ofEpochDay(r.maxDay), r.minN,
                    src, finalPass);
        }
        days.keySet().removeIf(k -> k < today - AltEwIndex.WINDOW_DAYS - 10);
        flags.keySet().removeIf(k -> k < today - 3);
    }

    private boolean lastMinutePresent(long day) {
        long ts = (day + 1) * AltEwIndex.DAY - AltEwIndex.MIN;
        readCalls++;
        TreeMap<Long, Map<String, KlineObjectSimple>> m = reader.read(ts, 1);
        return m != null && m.containsKey(ts) && m.get(ts) != null && !m.get(ts).isEmpty();
    }

    /** Tong EW ngay j tu store: nap them phut 23:59 ngay truoc (return phut 00:00), doc tung khoi 60 phut. */
    AltEwIndex.DayStat computeDay(long j) {
        AltEwIndex acc = new AltEwIndex();
        long t = j * AltEwIndex.DAY - AltEwIndex.MIN;
        int total = 1441;
        int done = 0;
        while (done < total) {
            int k = Math.min(SEED_CHUNK_MIN, total - done);
            readCalls++;
            TreeMap<Long, Map<String, KlineObjectSimple>> m = reader.read(t, k);
            if (m != null) {
                for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : m.entrySet()) {
                    acc.feed(e.getKey(), e.getValue());
                }
            }
            t += k * AltEwIndex.MIN;
            done += k;
            if (pauseMs > 0) {
                try {
                    Thread.sleep(pauseMs);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }
        AltEwIndex.DayStat s = acc.finish().get(j);
        return s != null ? s : new AltEwIndex.DayStat(j, 0d, 0);
    }

    private void load() {
        if (file == null || !file.exists()) return;
        int n = 0;
        try {
            for (String ln : Files.readAllLines(file.toPath())) {
                if (ln.isEmpty() || ln.startsWith("epoch_day") || ln.startsWith("#")) continue;
                String[] p = ln.split(",", -1);
                if (p.length < 4) continue;
                long d = Long.parseLong(p[0].trim());
                days.put(d, new AltEwIndex.DayStat(d, Double.parseDouble(p[2].trim()), Integer.parseInt(p[3].trim())));
                n++;
            }
            LOG.info("[TS-EXT] nap {} ngay tu {}", n, file.getAbsolutePath());
        } catch (Exception e) {
            LOG.error("[TS-EXT] khong nap duoc {}: {}", file.getAbsolutePath(), e.toString());
        }
    }

    private synchronized void persist(AltEwIndex.DayStat s) {
        if (file == null) return;
        try {
            File parent = file.getAbsoluteFile().getParentFile();
            if (parent != null && !parent.exists() && !parent.mkdirs()) {
                LOG.warn("[TS-EXT] khong tao duoc thu muc {}", parent);
            }
            boolean header = !file.exists();
            try (PrintWriter w = new PrintWriter(new FileWriter(file, true))) {
                if (header) w.println("epoch_day,date,sum_ew,n_min");
                w.println(s.day + "," + LocalDate.ofEpochDay(s.day) + "," + Double.toString(s.sum) + "," + s.n);
            }
        } catch (IOException e) {
            LOG.error("[TS-EXT] khong ghi duoc {}: {}", file.getAbsolutePath(), e.toString());
        }
    }

    private void track(String symbol, long anchor, long now, Decision d, Flag f, boolean legacy) {
        String key = symbol + "|" + anchor;
        long ageH = (now - anchor) / HOUR;
        if (d == Decision.DEFER) {
            if (deferring.putIfAbsent(key, now) == null) {
                LOG.info("[TS-EXT] defer-START {} age_h={} flag={} day={}", symbol, ageH, f,
                        LocalDate.ofEpochDay(Math.floorDiv(now, AltEwIndex.DAY)));
            }
        } else if (d == Decision.CUT) {
            Long st = deferring.remove(key);
            if (legacy) {
                LOG.warn("[TS-EXT] {} la LEGACY - khong keo dai (time-stop nhu v11b)", symbol);
            } else if (st != null) {
                String reason = (now - anchor) > (long) (BASE_HOURS + EXT_HOURS) * HOUR ? "MAX_504H" : "FLAG_" + f;
                LOG.info("[TS-EXT] defer-END {} age_h={} reason={} -> CUT time-stop (keo dai {}h)", symbol, ageH,
                        reason, (now - st) / HOUR);
            }
        }
    }

    private void endDefer(String symbol, long anchor, long now, String reason) {
        Long st = deferring.remove(symbol + "|" + anchor);
        if (st != null) {
            LOG.info("[TS-EXT] defer-END {} age_h={} reason={} (keo dai {}h)", symbol, (now - anchor) / HOUR, reason,
                    (now - st) / HOUR);
        }
    }

    private void statusIfDue(long now, long today) {
        long h = Math.floorDiv(now, HOUR);
        if (h == lastStatusHour) return;
        lastStatusHour = h;
        AltEwIndex.FlagResult r = flags.get(today);
        List<String> items = new ArrayList<>();
        for (Map.Entry<String, Long> e : deferring.entrySet()) {
            String[] p = e.getKey().split("\\|");
            long anchor = Long.parseLong(p[1]);
            items.add(p[0] + ":" + (now - anchor) / HOUR + "h");
        }
        LOG.info("[TS-EXT] status now={} flagToday={} dd={} deferring={} {}", Instant.ofEpochMilli(now),
                r == null ? "PENDING" : r.state, r == null ? "NaN" : String.format("%.6f", r.dd), items.size(), items);
    }
}
