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
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

/**
 * [UNIVERSE-A1 2026-10-30 / fixA] Bo loc TradFi + INDEX cho universe GIAO DICH va MOI feature thi truong
 * (ALT_EW / calMarketData / gate input), dung CHUNG cho live va sim/replay (parity).
 *
 * <p><b>Mot diem loc duy nhat (live)</b>: {@code DetectEntrySignal2TradeNormal} loc ngay sau
 * {@code tickerWindow.read(...)}; moi tap phia sau (symbol2FinalTicker, calRateChangeAvg, cascadeUniverse,
 * predictAllCandidates/funding-OI, getTopSymbol) deu sinh tu tap do. KHONG loc trong ingestor (JVM collectData
 * ghi du lieu dung chung, loc o do se lam hong du lieu cua nguoi khac).
 *
 * <p><b>Dinh nghia</b> (nguyen van {@code docs/result/HO2026_TRADFI_AUDIT.md} §2, TradFiClassifier):
 * TF ⇔ {@code contractType} chua TRADIFI/TRADFI HOAC {@code underlyingType} ngoai {COIN, INDEX, PREMARKET};
 * INDEX ⇔ {@code underlyingType=INDEX} hoac symbol trong danh sach INDEX tuong minh. Thieu
 * {@code underlyingType} ⇒ KHONG coi la TF (giong TradFiClassifier: verified=false).
 *
 * <p><b>Nguon</b>: raw {@code /fapi/v1/exchangeInfo} JSON (co {@code contractType}, {@code underlyingType},
 * {@code onboardDate}, {@code serverTime}). KHONG dung file dump SDK {@code EXCHANGE_INFO_PATH} (thieu truong
 * ⇒ khong phan loai duoc). Khi BAT: assert so TF ≥ {@link #MIN_TRADFI}, khong dat ⇒ fail-fast.
 *
 * <p><b>Point-in-time</b>: {@link #isExcluded(String, long)} — symbol TF/INDEX chi bi loai tai {@code t} khi
 * {@code t >= onboardDate} cua hop dong mang nhan do (MDTUSDT: crypto den 2026-10-13, TF Medtronic tu
 * 2026-10-21). Dung chung live + replay.
 *
 * <p><b>Fail-fast</b>: {@link #initEager()} duoc goi trong {@code main}/{@code start} (ngoai try/catch nuot loi).
 * {@code initialized=true} chi sau khi parse thanh cong; loi duoc giu lai va nem lai o MOI lan goi sau.
 * File doi mtime ⇒ reload (stat toi da 1 lan/phut); reload loi cung fail-fast.
 *
 * <p>Khong goi API, khong ghi Aerospike, khong doi quyet dinh nao khac ngoai tap symbol duoc chap nhan.
 */
public final class UniverseA1Filter {

    private static final Logger LOG = LoggerFactory.getLogger(UniverseA1Filter.class);

    public static final String K_ENABLE = "UNIVERSE_A1";
    public static final String K_FILE = "UNIVERSE_A1_EXCHANGE_INFO";
    public static final String K_INDEX_LIST = "UNIVERSE_A1_INDEX_LIST";

    /** So TF toi thieu cua mot raw exchangeInfo hop le (snapshot 10-27: 229 TRADIFI). */
    public static final int MIN_TRADFI = 200;

    /** INDEX theo raw exchangeInfo 10-27 (HO2026_TRADFI_AUDIT §2). */
    public static final String DEFAULT_INDEX_LIST = "ALLUSDT,BTCDOMUSDT,DEFIUSDT";

    /** underlyingType duoc coi la crypto (PREMARKET = PREDICTUSDT, crypto). */
    private static final Set<String> CRYPTO_UNDERLYING = Collections.unmodifiableSet(
            new HashSet<>(java.util.Arrays.asList("COIN", "INDEX", "PREMARKET")));

    private static final Object LOCK = new Object();

    private static volatile boolean initialized = false;
    private static volatile RuntimeException initError = null;
    private static volatile boolean active = false;
    private static volatile Set<String> excluded = Collections.emptySet();   // TF/INDEX
    private static volatile Map<String, Long> onboard = Collections.emptyMap(); // symbol -> onboardDate ms (0 = khong ro)
    private static volatile Set<String> known = Collections.emptySet();      // moi symbol co trong snapshot
    private static volatile long snapshotTs = 0L;
    private static volatile String source = "off";
    private static volatile int nTradFi = 0;
    private static volatile int nIndex = 0;
    private static volatile String filePath = "";
    private static volatile long fileMtime = 0L;
    private static volatile long lastStatMs = 0L;
    private static final Set<String> warnedUnknown = ConcurrentHashMap.newKeySet();

    /** Cau hinh test (null = doc Cfg/env). */
    private static volatile TestCfg testCfg = null;

    private UniverseA1Filter() {
    }

    /**
     * Bat buoc goi som (main/start, NGOAI try/catch nuot loi). Co TAT ⇒ no-op re; co BAT ma file
     * thieu/hong/khong dat assert ⇒ nem IllegalStateException ngay va moi lan goi sau.
     */
    public static void initEager() {
        ensureInit();
    }

    private static void ensureInit() {
        if (initError != null) throw initError;
        if (initialized) {
            maybeReload();
            return;
        }
        synchronized (LOCK) {
            if (initialized) {
                maybeReload();
                return;
            }
            if (initError != null) throw initError;
            try {
                load();
            } catch (RuntimeException e) {
                initError = e;    // giu loi, nem lai o moi lan goi
                throw e;
            }
        }
    }

    /** Doc cau hinh + nap file; chi set initialized=true khi thanh cong. */
    private static void load() {
        TestCfg tc = testCfg;
        boolean on;
        Path p = null;
        String idx;
        boolean enforceMin;
        if (tc != null) {
            on = tc.enable;
            p = tc.file;
            idx = tc.indexList;
            enforceMin = tc.enforceMin;
        } else {
            on = parseOn(Cfg.get(K_ENABLE));
            idx = Cfg.getOr(K_INDEX_LIST, DEFAULT_INDEX_LIST);
            enforceMin = true;
            if (on) {
                String file = Cfg.getOr(K_FILE, "");
                if (file.isEmpty()) {
                    throw new IllegalStateException("[UNIVERSE-A1] BAT nhung thieu " + K_FILE
                            + " — phai tro toi raw /fapi/v1/exchangeInfo JSON (co contractType/underlyingType/onboardDate);"
                            + " KHONG dung dump SDK EXCHANGE_INFO_PATH (thieu truong)");
                }
                p = Paths.get(file);
            }
        }
        if (!on) {
            active = false;
            source = "off";
            excluded = Collections.emptySet();
            onboard = Collections.emptyMap();
            known = Collections.emptySet();
            nTradFi = 0;
            nIndex = 0;
            initialized = true;   // TAT la trang thai hop le
            return;
        }
        if (p == null) throw new IllegalStateException("[UNIVERSE-A1] BAT nhung khong co duong dan exchangeInfo");
        if (!Files.isRegularFile(p)) {
            throw new IllegalStateException("[UNIVERSE-A1] BAT nhung KHONG thay exchangeInfo: " + p
                    + " (dat " + K_FILE + "; KHONG goi API)");
        }
        Parsed r = parse(p, idx);
        if (enforceMin && r.nTradFi < MIN_TRADFI) {
            throw new IllegalStateException("[UNIVERSE-A1] chi thay " + r.nTradFi + " TF (< " + MIN_TRADFI
                    + ") trong " + p + " — khong phai raw /fapi/v1/exchangeInfo (hoac snapshot thieu truong)."
                    + " Dung file SDK dump (EXCHANGE_INFO_PATH) la SAI.");
        }
        apply(p, r);
        initialized = true;
        LOG.warn("[UNIVERSE-A1] BAT — loai {} symbol (TradFi={}, INDEX={}) tu {} sha256={} serverTime={} (co {} = 1)."
                        + " Ap o universe + ALT_EW + calMarketData + gate input + replay.",
                r.excluded.size(), r.nTradFi, r.nIndex, p, r.sha256, r.snapshotTs, K_ENABLE);
    }

    private static void apply(Path p, Parsed r) {
        excluded = Collections.unmodifiableSet(r.excluded);
        onboard = Collections.unmodifiableMap(r.onboard);
        known = Collections.unmodifiableSet(r.known);
        snapshotTs = r.snapshotTs;
        nTradFi = r.nTradFi;
        nIndex = r.nIndex;
        source = p.toString();
        filePath = p.toString();
        try {
            fileMtime = Files.getLastModifiedTime(p).toMillis();
        } catch (IOException e) {
            fileMtime = 0L;
        }
        lastStatMs = System.currentTimeMillis();
        active = true;
    }

    /** Reload theo mtime, toi da 1 stat/phut. Loi doc file ⇒ nem (fail-fast). */
    private static void maybeReload() {
        if (!active || filePath.isEmpty()) return;
        long now = System.currentTimeMillis();
        if (now - lastStatMs < 60_000L) return;
        lastStatMs = now;
        long m;
        try {
            m = Files.getLastModifiedTime(Paths.get(filePath)).toMillis();
        } catch (IOException e) {
            throw new IllegalStateException("[UNIVERSE-A1] khong stat duoc exchangeInfo " + filePath, e);
        }
        if (m == fileMtime) return;
        synchronized (LOCK) {
            if (m == fileMtime) return;
            Parsed r;
            try {
                r = parse(Paths.get(filePath), Cfg.getOr(K_INDEX_LIST, DEFAULT_INDEX_LIST));
            } catch (RuntimeException e) {
                initError = e;
                throw e;
            }
            if (r.nTradFi < MIN_TRADFI) {
                IllegalStateException e = new IllegalStateException("[UNIVERSE-A1] reload: chi thay "
                        + r.nTradFi + " TF (< " + MIN_TRADFI + ") trong " + filePath + " — tu choi reload");
                initError = e;
                throw e;
            }
            apply(Paths.get(filePath), r);
            warnedUnknown.clear();
            LOG.warn("[UNIVERSE-A1] RELOAD exchangeInfo {} sha256={} (TradFi={}, INDEX={}, serverTime={})",
                    filePath, r.sha256, r.nTradFi, r.nIndex, r.snapshotTs);
        }
    }

    public static boolean isActive() {
        ensureInit();
        return active;
    }

    /** Point-in-time: symbol co bi loai tai thoi diem {@code tMs} khong. */
    public static boolean isExcluded(String symbol, long tMs) {
        ensureInit();
        if (!active) return false;
        String s = norm(symbol);
        if (s.isEmpty()) return false;
        Long ob = onboard.get(s);
        if (ob != null) return tMs >= ob;                 // ob=0 => luon loai
        // Khong co trong snapshot: tai thoi diem SAU snapshot ma van co du lieu ⇒ niem yet sau snapshot
        // (khong phan loai duoc) => fail-closed + canh bao 1 lan/symbol.
        if (tMs > snapshotTs) {
            if (warnedUnknown.add(s)) {
                LOG.warn("[UNIVERSE-A1] symbol {} khong co trong snapshot (serverTime={}) nhung xuat hien sau moc do"
                        + " — LOAI (fail-closed). Can refresh exchangeInfo.", s, snapshotTs);
            }
            return true;
        }
        return false;
    }

    /** True neu symbol bi loai o thoi diem hien tai. */
    public static boolean isExcluded(String symbol) {
        return isExcluded(symbol, System.currentTimeMillis());
    }

    /** Tap symbol bi loai (ban sao, theo snapshot; rong khi co tat). */
    public static Set<String> excludedSymbols() {
        ensureInit();
        return new HashSet<>(excluded);
    }

    /** onboardDate (ms) cua symbol trong snapshot; -1 neu khong co. */
    public static long onboardDate(String symbol) {
        ensureInit();
        Long v = onboard.get(norm(symbol));
        return v == null ? -1L : v;
    }

    public static long snapshotTs() {
        ensureInit();
        return snapshotTs;
    }

    /** Loc MOT snapshot phut tai thoi diem {@code tMs}; co tat / khong dinh ⇒ tra NGUYEN map goc. */
    public static <V> Map<String, V> filter(Map<String, V> snap, long tMs) {
        ensureInit();
        if (!active || snap == null || snap.isEmpty()) return snap;
        boolean hit = false;
        for (String s : snap.keySet()) {
            if (isExcludedRaw(s, tMs)) {
                hit = true;
                break;
            }
        }
        if (!hit) return snap;
        Map<String, V> out = new LinkedHashMap<>(Math.max(16, snap.size()));
        for (Map.Entry<String, V> e : snap.entrySet()) {
            if (!isExcludedRaw(e.getKey(), tMs)) out.put(e.getKey(), e.getValue());
        }
        return out;
    }

    public static <V> Map<String, V> filter(Map<String, V> snap) {
        return filter(snap, System.currentTimeMillis());
    }

    /** isExcluded khong goi lai ensureInit (filter da goi) — tranh lap stat. */
    private static boolean isExcludedRaw(String symbol, long tMs) {
        String s = norm(symbol);
        if (s.isEmpty()) return false;
        Long ob = onboard.get(s);
        if (ob != null) return tMs >= ob;
        if (tMs > snapshotTs) {
            if (warnedUnknown.add(s)) {
                LOG.warn("[UNIVERSE-A1] symbol {} khong co trong snapshot (serverTime={}) nhung xuat hien sau moc do"
                        + " — LOAI (fail-closed). Can refresh exchangeInfo.", s, snapshotTs);
            }
            return true;
        }
        return false;
    }

    /** Loc tung phut cua mot ngay (BT replay); giu TreeMap de downstream on dinh thu tu. */
    public static TreeMap<Long, Map<String, KlineObjectSimple>> filterMinutes(
            TreeMap<Long, Map<String, KlineObjectSimple>> minutes) {
        ensureInit();
        if (!active || minutes == null || minutes.isEmpty()) return minutes;
        TreeMap<Long, Map<String, KlineObjectSimple>> out = new TreeMap<>();
        for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : minutes.entrySet()) {
            out.put(e.getKey(), filter(e.getValue(), e.getKey()));
        }
        return out;
    }

    /** So symbol bi loai theo tung nhom (chi de log/plan). */
    public static Map<String, Integer> stats() {
        ensureInit();
        Map<String, Integer> m = new HashMap<>();
        m.put("excluded", excluded.size());
        m.put("tradfi", nTradFi);
        m.put("index", nIndex);
        return m;
    }

    public static String source() {
        ensureInit();
        return source;
    }

    // ------------------------------------------------------------------ test hooks

    /**
     * CHI unit test: nap thang fixture. {@code enforceMin} = ap assert >= MIN_TRADFI nhu production.
     * Loi ⇒ nem va KHONG set initialized (giong production).
     */
    static synchronized void installForTest(Path exchangeInfo, String indexListCsv, boolean enable, boolean enforceMin) {
        testCfg = null;
        initialized = false;
        initError = null;
        active = false;
        excluded = Collections.emptySet();
        onboard = Collections.emptyMap();
        known = Collections.emptySet();
        source = "test";
        nTradFi = 0;
        nIndex = 0;
        if (!enable) {
            initialized = true;
            return;
        }
        Parsed r = parse(exchangeInfo, indexListCsv);
        if (enforceMin && r.nTradFi < MIN_TRADFI) {
            throw new IllegalStateException("fixture: " + r.nTradFi + " TF < " + MIN_TRADFI);
        }
        apply(exchangeInfo, r);
        initialized = true;
    }

    static void installForTest(Path exchangeInfo, String indexListCsv, boolean enable) {
        installForTest(exchangeInfo, indexListCsv, enable, false);
    }

    /** CHI unit test: cau hinh cho {@link #initEager()} (di qua dung duong load/initError cua production). */
    static synchronized void setConfigForTest(boolean enable, Path exchangeInfo, String indexListCsv, boolean enforceMin) {
        resetForTest();
        testCfg = new TestCfg(enable, exchangeInfo, indexListCsv, enforceMin);
    }

    static synchronized void resetForTest() {
        initialized = false;
        initError = null;
        active = false;
        excluded = Collections.emptySet();
        onboard = Collections.emptyMap();
        known = Collections.emptySet();
        snapshotTs = 0L;
        source = "off";
        nTradFi = 0;
        nIndex = 0;
        filePath = "";
        fileMtime = 0L;
        lastStatMs = 0L;
        testCfg = null;
        warnedUnknown.clear();
    }

    /** CHI unit test: cho phep stat lai ngay (reload theo mtime). */
    static void resetStatForTest() {
        lastStatMs = 0L;
    }

    // ------------------------------------------------------------------ parse

    private static final class TestCfg {
        final boolean enable;
        final Path file;
        final String indexList;
        final boolean enforceMin;

        TestCfg(boolean enable, Path file, String indexList, boolean enforceMin) {
            this.enable = enable;
            this.file = file;
            this.indexList = indexList;
            this.enforceMin = enforceMin;
        }
    }

    private static final class Parsed {
        Set<String> excluded = new HashSet<>();
        Map<String, Long> onboard = new HashMap<>();
        Set<String> known = new HashSet<>();
        int nTradFi = 0;
        int nIndex = 0;
        long snapshotTs = 0L;
        String sha256 = "";
    }

    /** Dinh nghia DUY NHAT: xem javadoc lop. */
    private static Parsed parse(Path p, String indexListCsv) {
        Set<String> idx = new HashSet<>();
        for (String s : indexListCsv.split(",")) {
            String t = norm(s);
            if (!t.isEmpty()) idx.add(t);
        }
        byte[] raw;
        try {
            raw = Files.readAllBytes(p);
        } catch (IOException e) {
            throw new IllegalStateException("[UNIVERSE-A1] doc exchangeInfo loi: " + p, e);
        }
        Parsed r = new Parsed();
        r.sha256 = sha256(raw);
        JsonObject root;
        try {
            root = JsonParser.parseString(new String(raw, StandardCharsets.UTF_8)).getAsJsonObject();
        } catch (RuntimeException e) {
            throw new IllegalStateException("[UNIVERSE-A1] exchangeInfo khong phai JSON hop le: " + p, e);
        }
        JsonArray arr = root.getAsJsonArray("symbols");
        if (arr == null) throw new IllegalStateException("[UNIVERSE-A1] exchangeInfo khong co mang symbols: " + p);
        JsonElement st = root.get("serverTime");
        if (st != null && !st.isJsonNull()) {
            try {
                r.snapshotTs = st.getAsLong();
            } catch (RuntimeException ignore) {
                r.snapshotTs = 0L;
            }
        }
        if (r.snapshotTs <= 0L) {
            try {
                r.snapshotTs = Files.getLastModifiedTime(p).toMillis();
            } catch (IOException e) {
                r.snapshotTs = System.currentTimeMillis();
            }
        }
        for (JsonElement e : arr) {
            if (!e.isJsonObject()) continue;
            JsonObject o = e.getAsJsonObject();
            String sym = norm(str(o, "symbol"));
            if (sym.isEmpty()) continue;
            r.known.add(sym);
            long ob = 0L;
            JsonElement od = o.get("onboardDate");
            if (od != null && !od.isJsonNull()) {
                try {
                    ob = od.getAsLong();
                } catch (RuntimeException ignore) {
                    ob = 0L;
                }
            }
            String ct = str(o, "contractType").toUpperCase(Locale.ROOT);
            String ut = str(o, "underlyingType");
            boolean isIndex = idx.contains(sym) || "INDEX".equalsIgnoreCase(ut);
            boolean isTradFi = ct.contains("TRADIFI") || ct.contains("TRADFI")
                    || (!ut.isEmpty() && !CRYPTO_UNDERLYING.contains(ut.toUpperCase(Locale.ROOT)));
            if (isIndex) {
                r.excluded.add(sym);
                r.onboard.put(sym, ob);
                r.nIndex++;
            } else if (isTradFi) {
                r.excluded.add(sym);
                r.onboard.put(sym, ob);
                r.nTradFi++;
            }
        }
        // Symbol co onboardDate SAU serverTime cua chinh snapshot: khong the co trong file; neu co thi
        // van giu trong tap loai (fail-closed), chi log de dieu tra.
        List<String> weird = new ArrayList<>();
        for (Map.Entry<String, Long> en : r.onboard.entrySet()) {
            if (en.getValue() != null && en.getValue() > r.snapshotTs) weird.add(en.getKey());
        }
        if (!weird.isEmpty()) {
            LOG.warn("[UNIVERSE-A1] {} symbol co onboardDate > serverTime snapshot ({}) — giu trong tap loai: {}",
                    weird.size(), r.snapshotTs, weird.subList(0, Math.min(5, weird.size())));
        }
        return r;
    }

    private static String sha256(byte[] b) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] d = md.digest(b);
            StringBuilder sb = new StringBuilder(d.length * 2);
            for (byte x : d) sb.append(String.format("%02x", x));
            return sb.toString();
        } catch (Exception e) {
            return "NA";
        }
    }

    private static String norm(String s) {
        if (s == null) return "";
        String t = s.trim().toUpperCase(Locale.ROOT);
        if (t.isEmpty()) return "";
        if (!t.endsWith("USDT")) t = t + "USDT";
        return t;
    }

    private static String str(JsonObject o, String k) {
        JsonElement e = o.get(k);
        return e == null || e.isJsonNull() ? "" : e.getAsString().trim();
    }

    private static boolean parseOn(String v) {
        if (v == null) return false;
        String s = v.trim().toLowerCase(Locale.ROOT);
        return s.equals("1") || s.equals("true") || s.equals("on") || s.equals("yes");
    }
}
