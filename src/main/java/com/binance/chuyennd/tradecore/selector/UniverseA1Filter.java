package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Cfg;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

/**
 * [V12 R4d] Universe A1 (= backtest GOLIVE_QUARTERLY_2026_A1 / HO2026_NOTF A1): loai TradFi + INDEX o MOI tang phia tin hieu
 * (S1/ung vien, breadth calMarketData, ALT_EW, gate input, funding/OI) — live VA replay dung CUNG ham. Port tu ban nhap
 * OpenClaw {@code v1.1/universe-a1} 3d26f36a (chua audit), co sua — xem {@code docs/c3live/ROUND4D.md}.
 *
 * <ul>
 *   <li>Phan loai: {@link UniverseA1Classifier} (DUY NHAT, chung voi R7 c3_live).</li>
 *   <li>Nguon: raw {@code /fapi/v1/exchangeInfo} JSON ({@code UNIVERSE_A1_EXCHANGE_INFO}); bat buoc {@code serverTime} va
 *       nguong R4b ({@link UniverseA1Classifier#sourceProblem}: &gt;= 50 hop dong TradFi). KHONG goi API.</li>
 *   <li>Point-in-time: TF/INDEX bi loai tai {@code t} khi {@code t >= onboardDate} cua hop dong mang nhan do (MDTUSDT la
 *       crypto truoc 2026-10-21). Symbol KHONG co trong snapshot ma xuat hien sau {@code serverTime} ⇒ loai (fail-closed,
 *       giong R7: khong niem yet trong snapshot ⇒ khong mua). Symbol crypto CO trong snapshot ⇒ khong bao gio bi loai.</li>
 *   <li>Fail-fast: co bat ma file thieu / JSON hong / thieu serverTime / duoi nguong ⇒ {@link #initEager()} nem, loi duoc
 *       giu va nem lai o MOI lan goi sau. Reload theo mtime (stat &lt;= 1 lan/phut): file moi hong ⇒ GIU snapshot cu + ERROR
 *       (khong lam chet vong giao dich giua chung); so TF giam &gt; 30 % ⇒ WARN, van nhan.</li>
 *   <li>Co TAT (mac dinh): moi ham tra NGUYEN dau vao (cung object) — hanh vi = khong co lop nay.</li>
 * </ul>
 */
public final class UniverseA1Filter {

    private static final Logger LOG = LoggerFactory.getLogger(UniverseA1Filter.class);

    public static final String K_ENABLE = "UNIVERSE_A1";
    public static final String K_FILE = "UNIVERSE_A1_EXCHANGE_INFO";
    static final long RELOAD_STAT_MS = 60_000L;

    /** Snapshot bat bien (doi nguyen khoi khi reload => khong ai thay trang thai lai). */
    static final class Snap {
        final Map<String, Long> excludedOnboard;   // TF/INDEX -> onboardDate ms (0 = khong ro => luon loai)
        final Set<String> known;                   // moi symbol co trong snapshot
        final long serverTime;
        final int nSymbols;
        final int nTradFi;
        final int nIndex;
        final int nTfContract;
        final int nUnclassified;
        final String sha256;
        final String path;
        final long mtime;
        final boolean enforce;
        final String problem;

        Snap(Map<String, Long> ex, Set<String> known, long serverTime, int nSymbols, int nTradFi, int nIndex, int nTfContract,
             int nUnclassified, String sha256, String path, long mtime, boolean enforce, String problem) {
            this.excludedOnboard = Collections.unmodifiableMap(ex);
            this.known = Collections.unmodifiableSet(known);
            this.serverTime = serverTime;
            this.nSymbols = nSymbols;
            this.nTradFi = nTradFi;
            this.nIndex = nIndex;
            this.nTfContract = nTfContract;
            this.nUnclassified = nUnclassified;
            this.sha256 = sha256;
            this.path = path;
            this.mtime = mtime;
            this.enforce = enforce;
            this.problem = problem;
        }
    }

    private static final Object LOCK = new Object();
    private static volatile boolean initialized = false;
    private static volatile RuntimeException initError = null;
    private static volatile Snap snap = null;   // null = co TAT
    private static volatile long lastStatMs = 0L;
    private static volatile long lastBadMtime = Long.MIN_VALUE;
    private static final Set<String> warnedUnknown = ConcurrentHashMap.newKeySet();
    private static volatile TestCfg testCfg = null;

    private UniverseA1Filter() {
    }

    /** Goi SOM (start/replay), NGOAI moi try/catch nuot loi. Co tat => no-op; co bat ma nguon hong => nem (va moi lan sau). */
    public static void initEager() {
        ensureInit();
    }

    private static Snap ensureInit() {
        RuntimeException err = initError;
        if (err != null) throw err;
        if (!initialized) {
            synchronized (LOCK) {
                if (initError != null) throw initError;
                if (!initialized) {
                    try {
                        snap = load();
                        initialized = true;
                    } catch (RuntimeException e) {
                        initError = e;
                        throw e;
                    }
                }
            }
        }
        Snap s = snap;
        if (s != null) maybeReload(s);
        return snap;
    }

    private static Snap load() {
        TestCfg tc = testCfg;
        boolean on;
        Path p = null;
        boolean enforce = true;
        if (tc != null) {
            on = tc.enable;
            p = tc.file;
            enforce = tc.enforceMin;
        } else {
            on = parseOn(Cfg.get(K_ENABLE));
            if (on) {
                String f = Cfg.getOr(K_FILE, "").trim();
                if (f.isEmpty()) {
                    throw new IllegalStateException("[UNIVERSE-A1] BAT nhung thieu " + K_FILE
                            + " (raw /fapi/v1/exchangeInfo JSON; KHONG goi API)");
                }
                p = Paths.get(f);
            }
        }
        if (!on) return null;
        if (p == null || !Files.isRegularFile(p)) {
            throw new IllegalStateException("[UNIVERSE-A1] BAT nhung KHONG thay exchangeInfo: " + p + " (" + K_FILE + ")");
        }
        Snap s = parse(p, enforce);
        if (enforce && s.problem != null) {
            throw new IllegalStateException("[UNIVERSE-A1] exchangeInfo KHONG hop le: " + s.problem + " (" + p + ")");
        }
        LOG.warn("[UNIVERSE-A1] BAT — loai {} symbol (TradFi={}, INDEX={}) / {} symbol tu {} sha256={} serverTime={}"
                        + " unclassified={} (co {}=1: S1/ung vien, breadth, ALT_EW, gate, funding/OI, replay)",
                s.excludedOnboard.size(), s.nTradFi, s.nIndex, s.nSymbols, p, s.sha256, s.serverTime, s.nUnclassified, K_ENABLE);
        return s;
    }

    /** Reload theo mtime; loi => GIU snapshot cu + ERROR 1 lan/mtime (khong nem giua vong giao dich). */
    private static void maybeReload(Snap cur0) {
        long now = System.currentTimeMillis();
        if (now - lastStatMs < RELOAD_STAT_MS) return;
        lastStatMs = now;
        long m;
        try {
            m = Files.getLastModifiedTime(Paths.get(cur0.path)).toMillis();
        } catch (IOException e) {
            if (lastBadMtime != -1L) {
                lastBadMtime = -1L;
                LOG.error("[UNIVERSE-A1] khong stat duoc {} ({}) => GIU snapshot cu sha256={}", cur0.path, e.toString(), cur0.sha256);
            }
            return;
        }
        if (m == cur0.mtime || m == lastBadMtime) return;
        synchronized (LOCK) {
            Snap cur = snap;
            if (cur == null || m == cur.mtime) return;
            try {
                Snap n = parse(Paths.get(cur.path), cur.enforce);
                if (cur.enforce && n.problem != null) throw new IllegalStateException(n.problem);
                if (UniverseA1Classifier.tradFiDropped(cur.nTfContract, n.nTfContract)) {
                    LOG.warn("[UNIVERSE-A1] CANH BAO: so hop dong TradFi giam {} -> {} (> {} %) — van nhan snapshot, kiem nguon",
                            cur.nTfContract, n.nTfContract, (int) (UniverseA1Classifier.TRADFI_DROP_WARN * 100));
                }
                snap = n;
                lastBadMtime = Long.MIN_VALUE;
                warnedUnknown.clear();
                LOG.warn("[UNIVERSE-A1] RELOAD {} sha256={} (TradFi={}, INDEX={}, symbol={}, serverTime={})",
                        cur.path, n.sha256, n.nTradFi, n.nIndex, n.nSymbols, n.serverTime);
            } catch (RuntimeException e) {
                lastBadMtime = m;
                LOG.error("[UNIVERSE-A1] reload {} LOI ({}) => GIU snapshot cu sha256={} serverTime={}", cur.path, e.getMessage(),
                        cur.sha256, cur.serverTime);
            }
        }
    }

    public static boolean isActive() {
        return ensureInit() != null;
    }

    /** Point-in-time: symbol co bi loai tai {@code tMs} khong (co tat => false). */
    public static boolean isExcluded(String symbol, long tMs) {
        Snap s = ensureInit();
        return s != null && excludedIn(s, symbol, tMs);
    }

    public static boolean isExcluded(String symbol) {
        return isExcluded(symbol, System.currentTimeMillis());
    }

    private static boolean excludedIn(Snap s, String symbol, long tMs) {
        if (symbol == null || symbol.isEmpty()) return false;
        Long ob = s.excludedOnboard.get(symbol);
        if (ob != null) return tMs >= ob;
        if (s.known.contains(symbol)) return false;   // crypto co trong snapshot
        if (tMs > s.serverTime) {                     // niem yet SAU snapshot: chua phan loai duoc => loai
            if (warnedUnknown.add(symbol)) {
                LOG.warn("[UNIVERSE-A1] {} khong co trong snapshot (serverTime={}) nhung co du lieu sau moc do => LOAI (fail-closed);"
                        + " can lam moi exchangeInfo", symbol, s.serverTime);
            }
            return true;
        }
        return false;
    }

    /** Loc 1 snapshot phut tai {@code tMs}; co tat / khong dinh symbol nao => tra NGUYEN map goc (cung object). */
    public static <V> Map<String, V> filter(Map<String, V> m, long tMs) {
        Snap s = ensureInit();
        if (s == null || m == null || m.isEmpty()) return m;
        boolean hit = false;
        for (String k : m.keySet()) {
            if (excludedIn(s, k, tMs)) {
                hit = true;
                break;
            }
        }
        if (!hit) return m;
        Map<String, V> out = new LinkedHashMap<>(Math.max(16, m.size() * 2));
        for (Map.Entry<String, V> e : m.entrySet()) {
            if (!excludedIn(s, e.getKey(), tMs)) out.put(e.getKey(), e.getValue());
        }
        return out;
    }

    public static <V> Map<String, V> filter(Map<String, V> m) {
        return filter(m, System.currentTimeMillis());
    }

    /** Loc tung phut (replay/seed), point-in-time theo key phut; co tat => tra NGUYEN map goc. */
    public static TreeMap<Long, Map<String, KlineObjectSimple>> filterMinutes(TreeMap<Long, Map<String, KlineObjectSimple>> minutes) {
        Snap s = ensureInit();
        if (s == null || minutes == null || minutes.isEmpty()) return minutes;
        TreeMap<Long, Map<String, KlineObjectSimple>> out = new TreeMap<>();
        for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : minutes.entrySet()) {
            out.put(e.getKey(), filter(e.getValue(), e.getKey()));
        }
        return out;
    }

    /** Tap TF/INDEX cua snapshot (ban sao; rong khi co tat). */
    public static Set<String> excludedSymbols() {
        Snap s = ensureInit();
        return s == null ? new HashSet<>() : new HashSet<>(s.excludedOnboard.keySet());
    }

    /** onboardDate cua symbol TF/INDEX (ms); -1 neu khong phai TF/INDEX hoac co tat. */
    public static long onboardDate(String symbol) {
        Snap s = ensureInit();
        Long v = s == null ? null : s.excludedOnboard.get(symbol);
        return v == null ? -1L : v;
    }

    public static long snapshotTs() {
        Snap s = ensureInit();
        return s == null ? 0L : s.serverTime;
    }

    public static Map<String, Integer> stats() {
        Snap s = ensureInit();
        Map<String, Integer> m = new HashMap<>();
        m.put("excluded", s == null ? 0 : s.excludedOnboard.size());
        m.put("tradfi", s == null ? 0 : s.nTradFi);
        m.put("index", s == null ? 0 : s.nIndex);
        m.put("symbols", s == null ? 0 : s.nSymbols);
        return m;
    }

    public static String source() {
        Snap s = ensureInit();
        return s == null ? "off" : s.path;
    }

    // ------------------------------------------------------------------ test hooks

    private static final class TestCfg {
        final boolean enable;
        final Path file;
        final boolean enforceMin;

        TestCfg(boolean enable, Path file, boolean enforceMin) {
            this.enable = enable;
            this.file = file;
            this.enforceMin = enforceMin;
        }
    }

    /** CHI unit test: cau hinh cho lan init ke tiep (di dung duong load/initError cua production). */
    static void setConfigForTest(boolean enable, Path exchangeInfo, boolean enforceMin) {
        synchronized (LOCK) {
            resetForTest();
            testCfg = new TestCfg(enable, exchangeInfo, enforceMin);
        }
    }

    /** CHI unit test: ve trang thai chua init, khong cau hinh test (=> doc Cfg/env: mac dinh TAT). */
    static void resetForTest() {
        synchronized (LOCK) {
            initialized = false;
            initError = null;
            snap = null;
            lastStatMs = 0L;
            lastBadMtime = Long.MIN_VALUE;
            testCfg = null;
            warnedUnknown.clear();
        }
    }

    /** CHI unit test: cho phep stat lai ngay (reload theo mtime). */
    static void resetStatForTest() {
        lastStatMs = 0L;
    }

    // ------------------------------------------------------------------ parse

    static Snap parse(Path p, boolean enforce) {
        byte[] raw;
        long mtime;
        try {
            mtime = Files.getLastModifiedTime(p).toMillis();
            raw = Files.readAllBytes(p);
        } catch (IOException e) {
            throw new IllegalStateException("[UNIVERSE-A1] doc exchangeInfo loi: " + p + " (" + e + ")");
        }
        JsonObject root;
        try {
            root = JsonParser.parseString(new String(raw, StandardCharsets.UTF_8)).getAsJsonObject();
        } catch (RuntimeException e) {
            throw new IllegalStateException("[UNIVERSE-A1] exchangeInfo khong phai JSON hop le: " + p + " (" + e + ")");
        }
        JsonArray arr = root.has("symbols") && root.get("symbols").isJsonArray() ? root.getAsJsonArray("symbols") : null;
        if (arr == null) throw new IllegalStateException("[UNIVERSE-A1] exchangeInfo khong co mang symbols: " + p);
        long serverTime = longOf(root.get("serverTime"));
        if (serverTime <= 0L) {
            throw new IllegalStateException("[UNIVERSE-A1] exchangeInfo thieu serverTime (khong phai raw /fapi/v1/exchangeInfo): " + p);
        }
        Map<String, Long> ex = new HashMap<>();
        Set<String> known = new HashSet<>();
        int n = 0, nCt = 0, nUt = 0, nTfC = 0, nTf = 0, nIdx = 0, nUnc = 0;
        for (JsonElement e : arr) {
            if (!e.isJsonObject()) continue;
            JsonObject o = e.getAsJsonObject();
            String sym = str(o, "symbol").toUpperCase(Locale.ROOT);
            if (sym.isEmpty()) continue;
            n++;
            String ct = str(o, "contractType");
            String ut = str(o, "underlyingType");
            if (!ct.isEmpty()) nCt++;
            if (!ut.isEmpty()) nUt++;
            if (UniverseA1Classifier.isTradFiContract(ct)) nTfC++;
            known.add(sym);
            UniverseA1Classifier.Kind k = UniverseA1Classifier.classify(ct, ut);
            if (k == UniverseA1Classifier.Kind.UNCLASSIFIED) nUnc++;
            if (!UniverseA1Classifier.excluded(k)) continue;
            long ob = longOf(o.get("onboardDate"));
            ex.put(sym, ob < 0L ? 0L : ob);
            if (k == UniverseA1Classifier.Kind.TRADFI) nTf++;
            else nIdx++;
        }
        String problem = UniverseA1Classifier.sourceProblem(n, nCt, nUt, nTfC);
        return new Snap(ex, known, serverTime, n, nTf, nIdx, nTfC, nUnc, sha256(raw), p.toString(), mtime, enforce, problem);
    }

    private static long longOf(JsonElement e) {
        if (e == null || e.isJsonNull()) return 0L;
        try {
            return e.getAsLong();
        } catch (RuntimeException ex) {
            return 0L;
        }
    }

    private static String sha256(byte[] b) {
        try {
            byte[] d = MessageDigest.getInstance("SHA-256").digest(b);
            StringBuilder sb = new StringBuilder(d.length * 2);
            for (byte x : d) sb.append(String.format("%02x", x));
            return sb.toString();
        } catch (Exception e) {
            return "NA";
        }
    }

    private static String str(JsonObject o, String k) {
        JsonElement e = o.get(k);
        return e == null || e.isJsonNull() ? "" : e.getAsString().trim();
    }

    static boolean parseOn(String v) {
        if (v == null) return false;
        String s = v.trim().toLowerCase(Locale.ROOT);
        return s.equals("1") || s.equals("true") || s.equals("on") || s.equals("yes");
    }
}
