"""R4u2 C3_EXCLUDE_LEGACY_HELD: moi duong VAO LENH cua c3 (that + giay) loai LEGACY chi khi co BAT (mac dinh = r4t).
TAT (SUB): c3 chi loai coin c3 dang giu (nhu sim); LEGACY = TOAN BO vi the that tk chinh (khong tru so c3) de luat
dong cua LEGACY khong doi khi c3 cung giu symbol do."""
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("patch3")


def rep(path, old, new, n=1):
    s = open(path, "rb").read().decode("utf-8")
    c = s.count(old)
    assert c == n, (path, c, old[:90])
    open(path, "wb").write(s.replace(old, new).encode("utf-8"))


SEL = "src/main/java/com/binance/chuyennd/tradecore/selector/"
LS = SEL + "LegacySymbols.java"
rep(LS, """    public int size() {
        return legacy.size();
    }
""", """    // ===================== [V12 R4u2 C3_EXCLUDE_LEGACY_HELD 2026-11-10] =====================
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
            c = parseExclude(Cfg.get(KEY_EXCLUDE));
            excludeCached = c;
        }
        return c;
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
""")
rep(LS, """    public void reconcile(Set<String> realPositions, Set<String> paperPositions, Set<String> c3LiveOwned) {
        TreeSet<String> ex = new TreeSet<>();""", """    public void reconcile(Set<String> realPositions, Set<String> paperPositions, Set<String> c3LiveOwned) {
        if (!excludeLegacyHeld()) {
            // [V12 R4u2] TAT (SUB): vi the that (tk chinh) chi la LEGACY => KHONG tru so giay/so c3. Neu tru, coin ma
            //   c3 cung giu se roi khoi LEGACY va vi the THAT cua LEGACY bi ap luat dong C3 (arm/ratchet/time-stop).
            reconcile(realPositions, Collections.<String>emptySet());
            return;
        }
        TreeSet<String> ex = new TreeSet<>();""")

TS = SEL + "TsMktExt.java"
rep(TS, """    static volatile Predicate<String> legacyCheck = LegacySymbols::isLegacySymbol;""",
    """    static volatile Predicate<String> legacyCheck = LegacySymbols::blocksC3;   // [V12 R4u2] TAT => khong coi LEGACY""")

BD = SEL + "BigDownSelect.java"
rep(BD, """    /** "SYM=0.123456,SYM2=..." cho dong log [BIG_DOWN-SEL]. */""", """    /**
     * [V12 R4u2] tap "dang giu" cua leg market-signal c3: co BAT => vi the that tk chinh (LEGACY) HOP so c3 (r4u);
     * TAT => CHI so c3 (nhu sim isSymbolRunning).
     */
    public static Predicate<String> lockedFor(boolean excludeLegacy, java.util.Set<String> realPositions,
                                              Predicate<String> c3Held) {
        final java.util.Set<String> real = realPositions == null ? java.util.Collections.<String>emptySet() : realPositions;
        final Predicate<String> held = c3Held == null ? s -> false : c3Held;
        return s -> (excludeLegacy && real.contains(s)) || held.test(s);
    }

    /** "SYM=0.123456,SYM2=..." cho dong log [BIG_DOWN-SEL]. */""")

D = "src/main/java/com/binance/chuyennd/trading/DetectEntrySignal2TradeNormal.java"
rep(D, """                    com.binance.chuyennd.tradecore.selector.LegacySymbols::isLegacySymbol, heldPre, tickersF::get,""",
    """                    com.binance.chuyennd.tradecore.selector.LegacySymbols::blocksC3, heldPre, tickersF::get,   // [V12 R4u2]""")
rep(D, """                && com.binance.chuyennd.tradecore.selector.LiveProfileC3.on()
                && com.binance.chuyennd.tradecore.selector.LegacySymbols.isLegacySymbol(symbol)) {""",
    """                && com.binance.chuyennd.tradecore.selector.LiveProfileC3.on()
                && com.binance.chuyennd.tradecore.selector.LegacySymbols.blocksC3(symbol)) {   // [V12 R4u2]""")
rep(D, """            if (com.binance.chuyennd.tradecore.selector.LegacySymbols.isLegacySymbol(symbol)) {
                LOG.info("[SHADOW] skip-LEGACY {}", symbol);""",
    """            if (com.binance.chuyennd.tradecore.selector.LegacySymbols.blocksC3(symbol)) {   // [V12 R4u2]
                LOG.info("[SHADOW] skip-LEGACY {}", symbol);""")
rep(D, """                numberOrder, s -> symbolLocked.contains(s) || held.test(s), s -> tickers.get(s) != null);""",
    """                numberOrder, com.binance.chuyennd.tradecore.selector.BigDownSelect.lockedFor(
                        com.binance.chuyennd.tradecore.selector.LegacySymbols.excludeLegacyHeld(), symbolLocked, held),
                s -> tickers.get(s) != null);   // [V12 R4u2] TAT => chi so c3""")

B = "src/main/java/com/binance/chuyennd/trading/BinanceOrderTradingManager.java"
rep(B, """        if (com.binance.chuyennd.tradecore.selector.LegacySymbols.isLegacySymbol(order.symbol)) {
            LOG.info("[SHADOW] skip-LEGACY {}", order.symbol);""",
    """        if (com.binance.chuyennd.tradecore.selector.LegacySymbols.blocksC3(order.symbol)) {   // [V12 R4u2]
            LOG.info("[SHADOW] skip-LEGACY {}", order.symbol);""")

R = "src/main/java/com/binance/chuyennd/c3live/runtime/C3LiveRuntime.java"
rep(R, """                .legacy(s -> LegacySymbols.isLegacySymbol(s) || scope.entryBlocked(""",
    """                .legacy(s -> LegacySymbols.blocksC3(s) || scope.entryBlocked(   // [V12 R4u2] TAT => chi scope""")

P = SEL + "LiveProfileC3.java"
rep(P, """                    decideLegacyQueueBlock(true, System.getenv("LEGACY_QUEUE_LIVE_BLOCK")));   // = KEY_LEGACY_QUEUE_BLOCK (tranh forward ref)
        }
    }
""", """                    decideLegacyQueueBlock(true, System.getenv("LEGACY_QUEUE_LIVE_BLOCK")));   // = KEY_LEGACY_QUEUE_BLOCK (tranh forward ref)
        }
        if (ON) {   // [V12 R4u2] 1 dong luc khoi dong
            boolean ex = LegacySymbols.excludeLegacyHeld();
            LOG.warn("[C3-LEGACY] C3_EXCLUDE_LEGACY_HELD={} => {}", ex, ex
                    ? "c3 KHONG vao symbol LEGACY (tk chinh dung chung, nhu r4t)"
                    : "c3 CHI loai coin c3 dang giu (nhu sim); LEGACY = toan bo vi the that tk chinh (CHI dung voi C3_ACCOUNT=SUB)");
        }
    }
""")
log.info("PATCH3_OK")
