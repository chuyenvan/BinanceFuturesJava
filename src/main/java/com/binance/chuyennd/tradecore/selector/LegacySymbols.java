package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.Collections;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.ConcurrentHashMap;

/**
 * SYMBOL DAC BIET "LEGACY" — vi the THAT co tu truoc, van dong THAT theo duong HEAD,
 * KHONG duoc so giay C3 dung toi. CHI co nghia khi {@link LiveProfileC3#on()}.
 *
 * <p>VI SAO CAN: tren 242 co 66 vi the that mo tu truoc. Khi bat {@code LIVE_PROFILE=c3_shadow}
 * tren CUNG mot JVM, hai duong cung ton tai:
 * <ul>
 *   <li>duong THAT: dong 66 vi the cu (SL/TP/reduce-only KHONG bi {@code SHADOW_NO_PUSH} chan),</li>
 *   <li>duong GIAY: {@link ShadowBookC3} chay C3 song song, khong lenh that.</li>
 * </ul>
 * Neu khong tach, co C3 (arm 0.07 / ratchet lien tuc / time-stop 168h) se ap len duong dong
 * vi the THAT => doi luat dong cua tien that. Lop nay danh dau tap symbol do de:
 * <ol>
 *   <li>duong dong that cua chung giu <b>byte-identical HEAD</b>
 *       ({@link LiveProfileC3#armRateFor}, {@link LiveProfileC3#ratchetDeadzoneMultFor},
 *        {@link LiveProfileC3#timeStopApplies}),</li>
 *   <li>so giay KHONG mo entry giay cho chung ({@code [SHADOW] skip-LEGACY}) va chung
 *       KHONG chiem slot top-K cua so giay.</li>
 * </ol>
 *
 * <p>Nguon su that: reconcile tu Binance moi tick trong
 * {@code BinanceOrderTradingManager.updatePositionInfo()} — LEGACY = (vi the that) \ (so giay).
 * Tu THU HEP khi vi the that dong. Ghi dia {@code run/legacy_symbols.csv} de song sot restart
 * (JVM tu restart moi 4h) truoc khi reconcile dau tien kip chay.
 *
 * <p>Co TAT (mac dinh moi noi khac): {@link #isLegacySymbol} tra {@code false} NGAY, khong doc
 * file, khong tao file => duong HEAD khong doi mot bit.
 */
public final class LegacySymbols {

    private static final Logger LOG = LoggerFactory.getLogger(LegacySymbols.class);

    /** Duong dan mac dinh, tuong doi so voi cwd cua JVM (giong pidfile {@code run/}). */
    public static final String DEFAULT_FILE = "run/legacy_symbols.csv";

    private static volatile LegacySymbols INSTANCE;

    private final Set<String> legacy = Collections.newSetFromMap(new ConcurrentHashMap<String, Boolean>());
    private final String path;

    private LegacySymbols(String path) {
        this.path = path;
        load();
    }

    public static LegacySymbols getInstance() {
        if (INSTANCE == null) {
            synchronized (LegacySymbols.class) {
                if (INSTANCE == null) INSTANCE = new LegacySymbols(Cfg.getOr("LIVE_LEGACY_FILE", DEFAULT_FILE));
            }
        }
        return INSTANCE;
    }

    /** CHI cho unit test. */
    static void resetForTest(String path) {
        synchronized (LegacySymbols.class) {
            INSTANCE = new LegacySymbols(path);
        }
    }

    /**
     * Cong DUY NHAT cho duong live hoi "symbol nay co phai vi the that cu khong".
     * Profile TAT -> {@code false} ngay lap tuc (khong cham dia) => HEAD khong doi.
     */
    public static boolean isLegacySymbol(String symbol) {
        if (!LiveProfileC3.on()) return false;
        return symbol != null && getInstance().legacy.contains(symbol);
    }

    // ===================== [V12 R4u2 C3_EXCLUDE_LEGACY_HELD 2026-11-10] =====================
    /** Key env/profile. Mac dinh true = hanh vi r4t (tk chinh dung chung c3 + LEGACY). */
    public static final String KEY_EXCLUDE = "C3_EXCLUDE_LEGACY_HELD";
    static volatile Boolean excludeForTest = null;
    private static volatile Boolean excludeCached = null;

    /** Chi "false"/"0" (khong phan biet hoa thuong, bo khoang trang) moi TAT; con lai (ke ca vang/rong) = BAT. */
    static boolean parseExclude(String v) {
        if (v == null) return true;
        String s = v.trim();
        return !("false".equalsIgnoreCase(s) || "0".equals(s));
    }

    /**
     * true (mac dinh): c3 KHONG vao lenh tren symbol LEGACY (tk chinh, one-way dung chung). false (chi khi
     * C3_ACCOUNT=SUB, LEGACY o tk chinh khac): c3 chi loai coin c3 dang giu — dung quy uoc sim isSymbolRunning.
     */
    public static boolean excludeLegacyHeld() {
        Boolean t = excludeForTest;
        if (t != null) return t;
        Boolean c = excludeCached;
        if (c == null) {
            synchronized (LegacySymbols.class) {
                c = excludeCached;
                if (c == null) {
                    boolean env = parseExclude(Cfg.get(KEY_EXCLUDE));
                    boolean live = com.binance.chuyennd.c3live.adapter.GatewayFactory.Mode.parse(
                            Cfg.get(com.binance.chuyennd.c3live.adapter.GatewayFactory.KEY_ADAPTER))
                            == com.binance.chuyennd.c3live.adapter.GatewayFactory.Mode.LIVE;
                    // [A1 r4u3 MIN-1, 2026-11-14] CUNG nguon voi client live (C3LiveRuntime: GatewayFactory.create(mode, Cfg::get, ..)
                    //   => C3LiveClientConfig.fromEnv(Cfg::get)); bo fallback System.getProperty (client khong doc).
                    String kf = Cfg.get(KEY_KEYS_FILE);
                    String why = forceReason(env, live, kf, LegacySymbols::canonical);
                    if (why != null) {
                        LOG.warn("[C3-EXCL-FORCE] C3_EXCLUDE_LEGACY_HELD=false bi EP ve true: {}", why);
                    }
                    c = env || why != null;
                    excludeCached = c;
                }
            }
        }
        return c;
    }

    // ===================== [V12 R4u3 C3-EXCL-FORCE 2026-11-10] =====================
    /** Env file key c3 (= C3LiveClientConfig.fromEnv). Vang => jar dung C3LiveKeys.DEFAULT_PATH = keys.env tk CHINH. */
    public static final String KEY_KEYS_FILE = "LIVE_C3_KEYS_FILE";
    /** Ten file key tk CON (ADD4). Chi file chinh tac co DUNG ten nay moi duoc coi la SUB. */
    public static final String SUB_KEYS_NAME = "keys_sub.env";

    /** Duong dan chinh tac (realpath, theo symlink); file chua co => tuyet doi + normalize. KHONG doc noi dung. */
    static String canonical(String p) {
        try {
            return java.nio.file.Paths.get(p).toRealPath().toString();
        } catch (Exception e) {
            try {
                return java.nio.file.Paths.get(p).toAbsolutePath().normalize().toString();
            } catch (Exception e2) {
                return p;
            }
        }
    }

    /**
     * Thuan: ly do EP {@code true} hoac null. Chi ep khi env=false VA adapter=live VA key KHONG phai tk con:
     * LIVE_C3_KEYS_FILE vang/rong, hoac ten file chinh tac != keys_sub.env (vd keys.env, symlink sang keys.env).
     * adapter khac live (dry/off) => giu dung env.
     */
    static String forceReason(boolean envExclude, boolean liveAdapter, String keysFileRaw,
                              java.util.function.Function<String, String> canon) {
        if (envExclude || !liveAdapter) return null;
        String f = keysFileRaw == null ? null : keysFileRaw.trim();
        if (f == null || f.isEmpty()) {
            return "adapter=live va LIVE_C3_KEYS_FILE vang => jar dung key mac dinh keys.env (tk CHINH)";
        }
        String c = canon == null ? f : canon.apply(f);
        java.nio.file.Path fn = c == null ? null : java.nio.file.Paths.get(c).getFileName();
        String name = fn == null ? null : fn.toString();
        if (!SUB_KEYS_NAME.equals(name)) {
            return "adapter=live va LIVE_C3_KEYS_FILE=" + f + " (chinh tac " + c + ") khong phai " + SUB_KEYS_NAME
                    + " => coi la tk CHINH";
        }
        return null;
    }

    /** Thuan: gia tri hieu luc cua C3_EXCLUDE_LEGACY_HELD. */
    static boolean effectiveExclude(String envRaw, boolean liveAdapter, String keysFileRaw,
                                    java.util.function.Function<String, String> canon) {
        boolean env = parseExclude(envRaw);
        return env || forceReason(env, liveAdapter, keysFileRaw, canon) != null;
    }

    /** Thuan: c3 bi chan vao symbol nay vi LEGACY? */
    static boolean blocksC3(boolean exclude, boolean isLegacy) {
        return exclude && isLegacy;
    }

    /** Cong cho MOI duong VAO LENH cua c3 (that + giay). Luat DONG cua LEGACY van doc {@link #isLegacySymbol}. */
    public static boolean blocksC3(String symbol) {
        return blocksC3(excludeLegacyHeld(), isLegacySymbol(symbol));
    }

    public int size() {
        return legacy.size();
    }

    public Set<String> all() {
        return new TreeSet<>(legacy);
    }

    public String path() {
        return path;
    }

    /**
     * LUAT LEGACY (thuan tinh toan, de test): symbol co vi the THAT ma so GIAY khong giu.
     * Tap nay tu thu hep khi vi the that dong (khong con trong {@code realPositions}).
     */
    static TreeSet<String> compute(Set<String> realPositions, Set<String> paperPositions) {
        TreeSet<String> out = new TreeSet<>();
        if (realPositions == null) return out;
        for (String s : realPositions) {
            if (s == null || s.isEmpty()) continue;
            if (paperPositions != null && paperPositions.contains(s)) continue;
            out.add(s);
        }
        return out;
    }

    /**
     * Reconcile moi tick tu vi the THAT doc ve tu Binance. Ghi dia khi tap doi.
     * Luon in {@code [LEGACY] managed N: ...} de verify.sh/health doc duoc.
     */
    /** [V12 C1] LEGACY = real \\ (paper U c3liveOwned): vi the C3 THAT (LiveBookC3) KHONG bao gio la LEGACY. */
    static TreeSet<String> compute(Set<String> realPositions, Set<String> paperPositions, Set<String> c3LiveOwned) {
        TreeSet<String> ex = new TreeSet<>();
        if (paperPositions != null) ex.addAll(paperPositions);
        if (c3LiveOwned != null) ex.addAll(c3LiveOwned);
        return compute(realPositions, ex);
    }

    /** [V12 C1] nhu {@link #reconcile(Set, Set)} nhung loai ca symbol c3_live dang so huu (so that). */
    public void reconcile(Set<String> realPositions, Set<String> paperPositions, Set<String> c3LiveOwned) {
        if (!excludeLegacyHeld()) {
            // [V12 R4u2] TAT (SUB): vi the that (tk chinh) chi la LEGACY => KHONG tru so giay/so c3. Neu tru, coin ma
            //   c3 cung giu se roi khoi LEGACY va vi the THAT cua LEGACY bi ap luat dong C3 (arm/ratchet/time-stop).
            reconcile(realPositions, Collections.<String>emptySet());
            return;
        }
        TreeSet<String> ex = new TreeSet<>();
        if (paperPositions != null) ex.addAll(paperPositions);
        if (c3LiveOwned != null) ex.addAll(c3LiveOwned);
        reconcile(realPositions, ex);
    }

    public void reconcile(Set<String> realPositions, Set<String> paperPositions) {
        TreeSet<String> now = compute(realPositions, paperPositions);
        boolean changed = !now.equals(new TreeSet<>(legacy));
        if (changed) {
            legacy.clear();
            legacy.addAll(now);
            save();
        }
        LOG.info("[LEGACY] managed {}: {}", now.size(), String.join(",", now));
    }

    /**
     * MO HINH thuan tinh toan cua vong chon top-K trong
     * {@code DetectEntrySignal2TradeNormal} sau patch L3: duyet pool theo thu tu, BO QUA symbol
     * legacy ma KHONG dem rank, lay {@code k} symbol dau tien con lai.
     * => legacy KHONG chiem slot cua so giay. Dung cho unit test cua luat do.
     */
    static java.util.List<String> paperCandidates(java.util.List<String> poolOrder,
                                                  Set<String> legacySet, int k) {
        java.util.List<String> out = new java.util.ArrayList<>();
        if (poolOrder == null) return out;
        for (String s : poolOrder) {
            if (legacySet != null && legacySet.contains(s)) continue;   // skip-LEGACY, khong dem rank
            if (out.size() >= k) break;
            out.add(s);
        }
        return out;
    }

    private void load() {
        File f = new File(path);
        if (!f.exists()) return;
        try {
            for (String ln : java.nio.file.Files.readAllLines(f.toPath())) {
                String s = ln.trim();
                if (s.isEmpty() || s.startsWith("#")) continue;
                legacy.add(s);
            }
            LOG.info("[LEGACY] nap lai {} symbol tu {}", legacy.size(), f.getAbsolutePath());
        } catch (Exception e) {
            LOG.error("[LEGACY] khong nap duoc {}: {}", f.getAbsolutePath(), e.getMessage());
        }
    }

    private synchronized void save() {
        try {
            File f = new File(path);
            File parent = f.getParentFile();
            if (parent != null && !parent.exists() && !parent.mkdirs()) {
                LOG.warn("[LEGACY] khong tao duoc thu muc {}", parent);
            }
            try (PrintWriter w = new PrintWriter(new FileWriter(f, false))) {
                w.println("# LEGACY symbols: vi the THAT cu, dong theo duong HEAD, so giay C3 KHONG cham.");
                w.println("# Tu sinh boi LegacySymbols.reconcile() — KHONG sua tay.");
                for (String s : new TreeSet<>(legacy)) w.println(s);
            }
        } catch (Exception e) {
            LOG.error("[LEGACY] khong ghi duoc {}: {}", path, e.getMessage());
        }
    }
}
