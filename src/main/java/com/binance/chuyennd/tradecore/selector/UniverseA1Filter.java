package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Cfg;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * [UNIVERSE-A1 2026-10-30] Bo loc TradFi + INDEX cho universe GIAO DICH va MOI feature thi truong
 * (ALT_EW / calMarketData / gate input), dung CHUNG cho live va sim/replay (parity).
 *
 * <p>Dinh nghia lay NGUYEN VAN tu {@code docs/result/HO2026_TRADFI_AUDIT.md} §2 (TradFiClassifier):
 * TF ⇔ {@code contractType} chua TRADIFI/TRADFI HOAC {@code underlyingType} khong thuoc
 * {COIN, INDEX, PREMARKET}; INDEX ⇔ {@code underlyingType=INDEX} hoac symbol trong danh sach INDEX
 * tuong minh. Thieu {@code underlyingType} ⇒ KHONG coi la TF (giong TradFiClassifier: verified=false).
 *
 * <p>Co {@code UNIVERSE_A1} mac dinh 0 = TAT (khong doc file, khong cap phat). Bat = 1: doc exchangeInfo
 * tu {@code UNIVERSE_A1_EXCHANGE_INFO} (mac dinh = {@code EXCHANGE_INFO_PATH} / duong dan Kaggle cua
 * ClientSingleton); file thieu/hong ⇒ FAIL-FAST (khong chay nua voi universe khong xac dinh).
 *
 * <p>Khong goi API, khong ghi Aerospike, khong doi quyet dinh nao khac ngoai tap symbol duoc chap nhan.
 */
public final class UniverseA1Filter {

    private static final Logger LOG = LoggerFactory.getLogger(UniverseA1Filter.class);

    public static final String K_ENABLE = "UNIVERSE_A1";
    public static final String K_FILE = "UNIVERSE_A1_EXCHANGE_INFO";
    public static final String K_INDEX_LIST = "UNIVERSE_A1_INDEX_LIST";

    /** Cung mac dinh voi ClientSingleton.EXCHANGE_INFO_PATH (khong in noi dung file). */
    public static final String DEFAULT_FILE = System.getenv("EXCHANGE_INFO_PATH") != null
            ? System.getenv("EXCHANGE_INFO_PATH").trim()
            : "/kaggle/input/datasets/chuyendinh/java-run/exchange_info.data";
    /** INDEX theo dump exchangeInfo 10-27 (HO2026_TRADFI_AUDIT §2). */
    public static final String DEFAULT_INDEX_LIST = "ALLUSDT,BTCDOMUSDT,DEFIUSDT";
    /** underlyingType duoc coi la crypto (PREMARKET = PREDICTUSDT, crypto). */
    private static final Set<String> CRYPTO_UNDERLYING = Collections.unmodifiableSet(
            new HashSet<>(java.util.Arrays.asList("COIN", "INDEX", "PREMARKET")));

    private static volatile boolean initialized = false;
    private static volatile boolean active = false;
    private static volatile Set<String> excluded = Collections.emptySet();
    private static volatile String source = "off";
    private static volatile int nTradFi = 0;
    private static volatile int nIndex = 0;

    private UniverseA1Filter() {
    }

    /** Doc co + nap exchangeInfo MOT lan (thread-safe). Goi tu moi diem loc. */
    private static synchronized void init() {
        if (initialized) return;
        initialized = true;
        if (!parseOn(Cfg.get(K_ENABLE))) {
            active = false;
            source = "off";
            excluded = Collections.emptySet();
            return;
        }
        String file = Cfg.getOr(K_FILE, DEFAULT_FILE);
        String indexList = Cfg.getOr(K_INDEX_LIST, DEFAULT_INDEX_LIST);
        Path p = Paths.get(file);
        if (!Files.isRegularFile(p)) {
            throw new IllegalStateException("[UNIVERSE-A1] BAT nhung KHONG thay exchangeInfo: " + file
                    + " (dat UNIVERSE_A1_EXCHANGE_INFO; KHONG goi API)");
        }
        Map<String, Object> parsed;
        try {
            parsed = parse(p, indexList);
        } catch (Exception e) {
            throw new IllegalStateException("[UNIVERSE-A1] doc exchangeInfo loi: " + file + " (" + e + ")", e);
        }
        @SuppressWarnings("unchecked")
        Set<String> ex = (Set<String>) parsed.get("excluded");
        excluded = Collections.unmodifiableSet(ex);
        active = true;
        nTradFi = (Integer) parsed.get("tradfi");
        nIndex = (Integer) parsed.get("index");
        source = file;
        LOG.warn("[UNIVERSE-A1] BAT — loai {} symbol (TradFi={}, INDEX={}) tu {} (co {} = 1). "
                        + "Ap o universe + ALT_EW + calMarketData + gate input + replay.",
                ex.size(), nTradFi, nIndex, file, K_ENABLE);
    }

    public static boolean isActive() {
        if (!initialized) init();
        return active;
    }

    /** True neu symbol bi loai khoi universe giao dich VA market features. */
    public static boolean isExcluded(String symbol) {
        if (!initialized) init();                 // sau lan dau: chi doc volatile, khong lock
        if (!active || symbol == null || symbol.isEmpty()) return false;
        return excluded.contains(norm(symbol));
    }

    /** Tap symbol bi loai (ban sao; rong khi co tat). */
    public static Set<String> excludedSymbols() {
        if (!initialized) init();
        return new HashSet<>(excluded);
    }

    /** Loc MOT snapshot phut; co tat / khong co symbol bi loai ⇒ tra NGUYEN map goc (khong copy). */
    public static <V> Map<String, V> filter(Map<String, V> snap) {
        if (!initialized) init();
        if (!active || snap == null || snap.isEmpty()) return snap;
        boolean hit = false;
        for (String s : snap.keySet()) {
            if (excluded.contains(norm(s))) {
                hit = true;
                break;
            }
        }
        if (!hit) return snap;
        Map<String, V> out = new LinkedHashMap<>(Math.max(16, snap.size()));
        for (Map.Entry<String, V> e : snap.entrySet()) {
            if (!excluded.contains(norm(e.getKey()))) out.put(e.getKey(), e.getValue());
        }
        return out;
    }

    /** Loc tung phut cua mot ngay (BT replay); giu TreeMap de downstream on dinh thu tu. */
    public static TreeMap<Long, Map<String, KlineObjectSimple>> filterMinutes(
            TreeMap<Long, Map<String, KlineObjectSimple>> minutes) {
        if (!initialized) init();
        if (!active || minutes == null || minutes.isEmpty()) return minutes;
        TreeMap<Long, Map<String, KlineObjectSimple>> out = new TreeMap<>();
        for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : minutes.entrySet()) {
            out.put(e.getKey(), filter(e.getValue()));
        }
        return out;
    }

    /** So symbol bi loai theo tung nhom (chi de log/plan). */
    public static Map<String, Integer> stats() {
        if (!initialized) init();
        Map<String, Integer> m = new HashMap<>();
        m.put("excluded", excluded.size());
        m.put("tradfi", nTradFi);
        m.put("index", nIndex);
        return m;
    }

    // ------------------------------------------------------------------ test hooks

    /** CHI unit test: nap thang fixture, khong doc env/Cfg. */
    static synchronized void installForTest(Path exchangeInfo, String indexListCsv, boolean enable) {
        initialized = true;
        active = false;
        excluded = Collections.emptySet();
        source = "test";
        nTradFi = 0;
        nIndex = 0;
        if (!enable) return;
        Map<String, Object> parsed;
        try {
            parsed = parse(exchangeInfo, indexListCsv);
        } catch (Exception e) {
            throw new IllegalStateException("fixture loi: " + exchangeInfo, e);
        }
        @SuppressWarnings("unchecked")
        Set<String> ex = (Set<String>) parsed.get("excluded");
        excluded = Collections.unmodifiableSet(ex);
        nTradFi = (Integer) parsed.get("tradfi");
        nIndex = (Integer) parsed.get("index");
        active = true;
    }

    static synchronized void resetForTest() {
        initialized = false;
        active = false;
        excluded = Collections.emptySet();
        source = "off";
        nTradFi = 0;
        nIndex = 0;
    }

    /** Dinh nghia DUY NHAT: TradFi ⇔ contractType TRADIFI/TRADFI hoac underlyingType ngoai {COIN,INDEX,PREMARKET};
     *  INDEX ⇔ underlyingType=INDEX hoac symbol trong danh sach INDEX tuong minh. Thieu underlyingType ⇒ khong TF. */
    private static Map<String, Object> parse(Path p, String indexListCsv) throws Exception {
        Set<String> idx = new HashSet<>();
        for (String s : indexListCsv.split(",")) {
            String t = norm(s);
            if (!t.isEmpty()) idx.add(t);
        }
        Set<String> ex = new HashSet<>();
        int tf = 0;
        int ix = 0;
        String json = new String(Files.readAllBytes(p), StandardCharsets.UTF_8);
        JsonObject root = JsonParser.parseString(json).getAsJsonObject();
        JsonArray arr = root.getAsJsonArray("symbols");
        if (arr == null) throw new IllegalStateException("exchangeInfo khong co mang symbols");
        for (JsonElement e : arr) {
            JsonObject o = e.getAsJsonObject();
            String sym = norm(str(o, "symbol"));
            if (sym.isEmpty()) continue;
            String ct = str(o, "contractType").toUpperCase(Locale.ROOT);
            String ut = str(o, "underlyingType");
            boolean isIndex = idx.contains(sym) || "INDEX".equalsIgnoreCase(ut);
            boolean isTradFi = ct.contains("TRADIFI") || ct.contains("TRADFI")
                    || (!ut.isEmpty() && !CRYPTO_UNDERLYING.contains(ut.toUpperCase(Locale.ROOT)));
            if (isIndex) {
                ex.add(sym);
                ix++;
            } else if (isTradFi) {
                ex.add(sym);
                tf++;
            }
        }
        Map<String, Object> m = new HashMap<>();
        m.put("excluded", ex);
        m.put("tradfi", tf);
        m.put("index", ix);
        return m;
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
