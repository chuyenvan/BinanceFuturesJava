package com.binance.chuyennd.c3live.universe;

import com.binance.chuyennd.tradecore.selector.UniverseA1Classifier;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.SymbolMeta;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;
import java.util.function.Consumer;
import java.util.function.Function;
import java.util.function.Supplier;

/**
 * [V12 P0-U1/U2/U3/U4] Universe live cua c3_live tu exchangeInfo (thay regex ^[A-Z0-9]+$ + Constants.diedSymbol).
 * <pre>U(t) = { s : status=TRADING, contractType=PERPETUAL, quoteAsset=USDT, underlyingType != INDEX } \ TradFi \ UNIVERSE_EXCLUDE</pre>
 * [2c MASTER] buyable = TRADING + PERPETUAL + underlyingType != INDEX (+ USDT, khong TradFi, ASCII, delivery); chi so
 * tong hop (ALLUSDT, BTCDOMUSDT) loai ca khoi buyable lan market index. PREMARKET (vd PREDICTUSDT) = crypto: hien bi loai
 * vi status (PENDING_TRADING), tu vao khi chuyen TRADING + PERPETUAL.
 * <ul>
 *   <li>{@link #isAlive}: san con TRADING (moi loai) - dung cho QUAN LY/dong vi the, khong chan theo chinh sach.</li>
 *   <li>{@link #isTradable}: trong U (gom ca ten non-ASCII, xu ly UTF-8, khong regex ASCII).</li>
 *   <li>{@link #isBuyable}: trong U, ASCII (tru khi LIVE_C3_ALLOW_NONASCII=1), deliveryDate &gt;= now + 7 ngay (P0-U2),
 *       snapshot khong cu qua maxStale (fail-closed).</li>
 *   <li>{@link #marketIndexMembers}: tap cho ALT_EW / market level cua c3_live (da loai TradFi; non-ASCII theo co).</li>
 *   <li>Refresh 15 phut ({@link #refreshIfDue}); loi -> giu snapshot cu + WARN.</li>
 *   <li>Canh bao (alerter + WARN) khi symbol trong UNIVERSE_EXCLUDE khong co ":intentional" van TRADING (vd POWR, MDT).</li>
 * </ul>
 * Khong dung trong duong c3_shadow / sim (chi c3_live sau co).
 */
public final class SymbolUniverseLive {
    private static final Logger LOG = LoggerFactory.getLogger(SymbolUniverseLive.class);
    public static final long REFRESH_MS = 15L * 60_000L;
    public static final long DELIVERY_GUARD_MS = 7L * 86_400_000L;
    public static final long DEFAULT_MAX_STALE_MS = 60L * 60_000L;
    public static final String DEFAULT_EXCLUDE = "BTCDOMUSDT:intentional,USDCUSDT:intentional";
    /** [V12 R4b MINOR-6] nguon exchangeInfo tho phai co >= so hop dong TradFi nay (dump 10-25: 225); giam > 30 % => chi canh bao. */
    public static final int MIN_TRADFI_IN_SOURCE = UniverseA1Classifier.MIN_TRADFI;   // [V12 R4d] nguong CHUNG voi bo loc A1
    public static final double TRADFI_DROP_WARN = UniverseA1Classifier.TRADFI_DROP_WARN;

    /** Ly do khong tradable / khong buyable. */
    public enum Reason { NOT_LISTED, NOT_TRADING, NOT_USDT, TRADFI, NOT_PERPETUAL, EXCLUDED, NON_ASCII, DELIVERY_UNKNOWN, DELIVERY_SOON, STALE, NO_SNAPSHOT,
        /** [2c MASTER] underlyingType=INDEX (ALLUSDT, BTCDOMUSDT...): backtest crash-buy khong xac thuc cho chi so tong hop. */
        INDEX,
        /** [V12 R4 R7] universe chat: underlyingType thieu => chua phan loai => LOAI (fail-closed). */
        UNCLASSIFIED,
        /** [V12 R4 R7] universe chat: underlyingType khong thuoc {COIN, PREMARKET} => LOAI. [PREMARKET-a] PREMARKET mua duoc (= A1). */
        NOT_COIN }

    /** Cau hinh bat bien. */
    public static final class Config {
        final Map<String, Boolean> exclude;
        final boolean allowNonAscii;
        final TradFiClassifier classifier;
        final long maxStaleMs;
        /** [V12 R4 R7] universe chat: CHI underlyingType=COIN + kiem nguon exchangeInfo tho (fail-fast). Mac dinh tat. */
        final boolean strictCoin;

        public Config(Map<String, Boolean> exclude, boolean allowNonAscii, TradFiClassifier classifier, long maxStaleMs) {
            this(exclude, allowNonAscii, classifier, maxStaleMs, false);
        }

        public Config(Map<String, Boolean> exclude, boolean allowNonAscii, TradFiClassifier classifier, long maxStaleMs,
                      boolean strictCoin) {
            this.strictCoin = strictCoin;
            this.exclude = exclude == null ? Collections.emptyMap() : Collections.unmodifiableMap(new LinkedHashMap<>(exclude));
            this.allowNonAscii = allowNonAscii;
            this.classifier = classifier == null ? TradFiClassifier.defaults() : classifier;
            this.maxStaleMs = maxStaleMs <= 0 ? DEFAULT_MAX_STALE_MS : maxStaleMs;
        }

        /**
         * UNIVERSE_EXCLUDE ("SYM" hoac "SYM:intentional", phan cach ','; mac dinh BTCDOMUSDT, USDCUSDT intentional),
         * LIVE_C3_ALLOW_NONASCII (0|1, mac dinh 0), UNIVERSE_TRADFI_LIST, UNIVERSE_CRYPTO_UNDERLYING_TYPES,
         * UNIVERSE_TRADFI_SUBTYPES, UNIVERSE_MAX_STALE_MS.
         */
        public static Config fromEnv(Function<String, String> env) {
            String ex = env.apply("UNIVERSE_EXCLUDE");
            Map<String, Boolean> exclude = parseExclude(ex == null ? DEFAULT_EXCLUDE : ex);
            boolean nonAscii = "1".equals(trim(env.apply("LIVE_C3_ALLOW_NONASCII")));
            TradFiClassifier c = new TradFiClassifier(csv(env.apply("UNIVERSE_CRYPTO_UNDERLYING_TYPES")),
                    csv(env.apply("UNIVERSE_TRADFI_SUBTYPES")), csv(env.apply("UNIVERSE_TRADFI_LIST")));
            long stale = DEFAULT_MAX_STALE_MS;
            String s = trim(env.apply("UNIVERSE_MAX_STALE_MS"));
            if (s != null) {
                try { stale = Long.parseLong(s); } catch (NumberFormatException ignore) { stale = DEFAULT_MAX_STALE_MS; }
            }
            return new Config(exclude, nonAscii, c, stale);
        }

        public static Config defaults() { return fromEnv(k -> null); }

        /** [V12 R4 R7] ban sao BAT universe chat (production c3_live tai khoan chinh). */
        public Config strictCoin() {
            return new Config(exclude, allowNonAscii, classifier, maxStaleMs, true);
        }

        public boolean isStrictCoin() { return strictCoin; }

        /** [V12 R4d] ban sao voi bo phan loai khac (UNIVERSE_A1=1: {@link TradFiClassifier#universeA1()}). */
        public Config withClassifier(TradFiClassifier c) {
            return new Config(exclude, allowNonAscii, c, maxStaleMs, strictCoin);
        }

        public TradFiClassifier getClassifier() { return classifier; }

        public Map<String, Boolean> getExclude() { return exclude; }
        public boolean isAllowNonAscii() { return allowNonAscii; }

        static Map<String, Boolean> parseExclude(String s) {
            Map<String, Boolean> m = new LinkedHashMap<>();
            if (s == null) return m;
            for (String raw : s.split(",")) {
                String t = raw.trim();
                if (t.isEmpty()) continue;
                int c = t.indexOf(':');
                String sym = c < 0 ? t : t.substring(0, c).trim();
                boolean intentional = c >= 0 && "intentional".equalsIgnoreCase(t.substring(c + 1).trim());
                if (!sym.isEmpty()) m.put(sym, intentional);
            }
            return m;
        }

        private static Set<String> csv(String s) {
            Set<String> out = new HashSet<>();
            if (s == null) return out;
            for (String x : s.split(",")) if (!x.trim().isEmpty()) out.add(x.trim());
            return out;
        }

        private static String trim(String s) {
            if (s == null) return null;
            String t = s.trim();
            return t.isEmpty() ? null : t;
        }
    }

    /** Snapshot bat bien sau 1 lan nap. */
    private static final class Snapshot {
        final long loadedAtMs;
        final Map<String, SymbolMeta> metas;
        final Map<String, Reason> notTradable;
        final Map<String, TradFiClassifier.Verdict> verdicts;
        final Set<String> alive;
        final Set<String> tradable;

        Snapshot(long loadedAtMs, Map<String, SymbolMeta> metas, Map<String, Reason> notTradable,
                 Map<String, TradFiClassifier.Verdict> verdicts, Set<String> alive, Set<String> tradable) {
            this.loadedAtMs = loadedAtMs;
            this.metas = metas;
            this.notTradable = notTradable;
            this.verdicts = verdicts;
            this.alive = alive;
            this.tradable = tradable;
        }
    }

    private final Config cfg;
    private final Supplier<ExchangeInfo> source;
    private final Consumer<String> alerter;
    private volatile Snapshot snap;
    private volatile UniverseDiff lastDiff;
    private volatile long lastAttemptMs;
    private Set<String> lastAlertedExclude = Collections.emptySet();

    public SymbolUniverseLive(Config cfg, Supplier<ExchangeInfo> source, Consumer<String> alerter) {
        this.cfg = cfg == null ? Config.defaults() : cfg;
        this.source = source;
        this.alerter = alerter == null ? s -> { } : alerter;
    }

    /** Nap ngay tu source. Loi -> giu snapshot cu, WARN, tra null. */
    public synchronized UniverseDiff refresh(long nowMs) {
        lastAttemptMs = nowMs;
        ExchangeInfo ei;
        try {
            ei = source.get();
        } catch (RuntimeException e) {
            LOG.warn("[UNIVERSE] refresh exchangeInfo loi ({}), giu snapshot cu {}", e.toString(), snap == null ? "(chua co)" : snap.loadedAtMs);
            return null;
        }
        return apply(ei, nowMs);
    }

    /** Refresh neu da qua 15 phut tu lan thu truoc (thanh cong hoac khong). */
    public synchronized UniverseDiff refreshIfDue(long nowMs) {
        if (snap != null && nowMs - lastAttemptMs < REFRESH_MS) return null;
        return refresh(nowMs);
    }

    /** Ap 1 exchangeInfo (fixture / test / refresh). */
    public synchronized UniverseDiff apply(ExchangeInfo ei, long nowMs) {
        if (ei == null || ei.getSymbols().isEmpty()) {
            LOG.warn("[UNIVERSE] exchangeInfo rong - bo qua, giu snapshot cu");
            return null;
        }
        if (cfg.strictCoin) {   // [V12 R4 R7] nguon tho phai du truong phan loai (fail-fast)
            String bad = sourceProblem(ei);
            lastSourceError = bad;
            if (bad != null) {
                String m = "[C3-LIVE UNIVERSE] exchangeInfo KHONG hop le (R7 fail-fast): " + bad + " => TU CHOI snapshot moi (giu cu; qua "
                        + cfg.maxStaleMs / 60_000L + "' => STALE, khong mua)";
                LOG.error("{}", m);
                alerter.accept(m);
                return null;
            }
            int tf = tradfiCount(ei);
            if (lastTfCount > 0 && tf < lastTfCount * (1d - TRADFI_DROP_WARN)) {
                String m = "[C3-LIVE UNIVERSE] CANH BAO: so hop dong TradFi trong exchangeInfo giam " + lastTfCount + " -> " + tf
                        + " (> " + (int) (TRADFI_DROP_WARN * 100) + " %) — van nhan snapshot, kiem nguon";
                LOG.warn("{}", m);
                alerter.accept(m);
            }
            lastTfCount = tf;
        }
        lastAttemptMs = Math.max(lastAttemptMs, nowMs);
        Map<String, SymbolMeta> metas = new HashMap<>(ei.getSymbols());
        Map<String, Reason> notTradable = new HashMap<>();
        Map<String, TradFiClassifier.Verdict> verdicts = new HashMap<>();
        Set<String> alive = new HashSet<>();
        Set<String> tradable = new HashSet<>();
        Set<String> tradfi = new TreeSet<>();
        Set<String> excludeWarn = new TreeSet<>();
        Set<String> unverified = new TreeSet<>();
        for (SymbolMeta m : metas.values()) {
            String sym = m.getSymbol();
            TradFiClassifier.Verdict v = cfg.classifier.classify(m);
            verdicts.put(sym, v);
            boolean trading = "TRADING".equals(m.getStatus());
            if (trading) alive.add(sym);
            if (trading && cfg.exclude.containsKey(sym) && !cfg.exclude.get(sym)) excludeWarn.add(sym);
            Reason r = null;
            if (!trading) r = Reason.NOT_TRADING;
            else if (!"USDT".equals(m.getQuoteAsset())) r = Reason.NOT_USDT;
            else if (v.isTradFi()) r = Reason.TRADFI;
            else if (!"PERPETUAL".equals(m.getContractType())) r = Reason.NOT_PERPETUAL;
            else if ("INDEX".equalsIgnoreCase(trimOrEmpty(m.getUnderlyingType()))) r = Reason.INDEX;
            else if (cfg.strictCoin && trimOrEmpty(m.getUnderlyingType()).isEmpty()) r = Reason.UNCLASSIFIED;
            else if (cfg.strictCoin && !"COIN".equalsIgnoreCase(trimOrEmpty(m.getUnderlyingType()))
                    && !"PREMARKET".equalsIgnoreCase(trimOrEmpty(m.getUnderlyingType()))) r = Reason.NOT_COIN;   // [PREMARKET-a] R7 = A1
            else if (cfg.exclude.containsKey(sym)) r = Reason.EXCLUDED;
            if (r == null) {
                tradable.add(sym);
                if (!v.isVerified()) unverified.add(sym);
            } else {
                notTradable.put(sym, r);
                if (r == Reason.TRADFI) tradfi.add(sym);
            }
        }
        Snapshot prev = snap;
        Snapshot cur = new Snapshot(nowMs, Collections.unmodifiableMap(metas), Collections.unmodifiableMap(notTradable),
                Collections.unmodifiableMap(verdicts), Collections.unmodifiableSet(alive), Collections.unmodifiableSet(tradable));
        snap = cur;
        Set<String> added = new TreeSet<>(tradable);
        Set<String> removed = new TreeSet<>();
        Set<String> newTradfi = new TreeSet<>(tradfi);
        if (prev != null) {
            added.removeAll(prev.tradable);
            removed.addAll(prev.tradable);
            removed.removeAll(tradable);
            for (Map.Entry<String, Reason> e : prev.notTradable.entrySet()) if (e.getValue() == Reason.TRADFI) newTradfi.remove(e.getKey());
        }
        Set<String> nonAscii = new TreeSet<>();
        Set<String> deliverySoon = new TreeSet<>();
        int buyable = 0;
        for (String s : tradable) {
            if (!isAsciiSymbol(s)) nonAscii.add(s);
            long dd = metas.get(s).getDeliveryDate();
            if (dd > 0 && dd < nowMs + DELIVERY_GUARD_MS) deliverySoon.add(s);
            if (buyableReason(cur, s, nowMs) == null) buyable++;
        }
        UniverseDiff d = new UniverseDiff(nowMs, metas.size(), alive.size(), tradable.size(), buyable, added, removed, tradfi, newTradfi,
                excludeWarn, nonAscii, deliverySoon, unverified);
        lastDiff = d;
        LOG.info("{}", d.summary());
        if (!newTradfi.isEmpty()) {
            for (String s : newTradfi) LOG.info("[UNIVERSE] TradFi loai: {} ({})", s, verdicts.get(s));
        }
        if (!unverified.isEmpty()) {
            LOG.warn("[UNIVERSE] {} symbol thieu underlyingType - phan loai TradFi CHUA XAC MINH (vd {})", unverified.size(), unverified.iterator().next());
        }
        if (!nonAscii.isEmpty() && !cfg.allowNonAscii) {
            LOG.info("[UNIVERSE] {} symbol non-ASCII trong U nhung KHONG mua (LIVE_C3_ALLOW_NONASCII=0): {}", nonAscii.size(), nonAscii);
        }
        if (!excludeWarn.isEmpty()) {
            LOG.warn("[UNIVERSE] symbol trong UNIVERSE_EXCLUDE (khong intentional) van TRADING: {}", excludeWarn);
            if (!excludeWarn.equals(lastAlertedExclude)) {
                alerter.accept("[C3-LIVE UNIVERSE] UNIVERSE_EXCLUDE chan symbol van TRADING: " + excludeWarn
                        + " - xem lai danh sach (them :intentional neu co chu dich)");
                lastAlertedExclude = excludeWarn;
            }
        } else {
            lastAlertedExclude = Collections.emptySet();
        }
        return d;
    }

    private volatile String lastSourceError;
    private volatile int lastTfCount = -1;

    /** [V12 R4b] so hop dong TradFi (contractType chua TRADIFI/TRADFI) trong nguon. */
    public static int tradfiCount(ExchangeInfo ei) {
        int tf = 0;
        for (SymbolMeta m : ei.getSymbols().values()) {
            if (UniverseA1Classifier.isTradFiContract(m.getContractType())) tf++;
        }
        return tf;
    }

    /** [V12 R4 R7] loi nguon exchangeInfo lan nap gan nhat (null = hop le / khong kiem). */
    public String lastSourceError() { return lastSourceError; }

    /**
     * [V12 R4 R7] Nguon exchangeInfo THO phai du truong phan loai: co truong contractType, co truong underlyingType va
     * &gt;= {@link #MIN_TRADFI_IN_SOURCE} hop dong TradFi (contractType chua TRADIFI) — chung minh la exchangeInfo day du cua san
     * (khong phai ban da loc / parser mat truong). null = hop le.
     */
    public static String sourceProblem(ExchangeInfo ei) {
        int ct = 0;
        int ut = 0;
        int tf = 0;
        int n = 0;
        for (SymbolMeta m : ei.getSymbols().values()) {
            n++;
            String c = trimOrEmpty(m.getContractType());
            if (!c.isEmpty()) ct++;
            if (!trimOrEmpty(m.getUnderlyingType()).isEmpty()) ut++;
            if (UniverseA1Classifier.isTradFiContract(c)) tf++;
        }
        return UniverseA1Classifier.sourceProblem(n, ct, ut, tf);   // [V12 R4d] kiem nguon CHUNG voi bo loc A1
    }

    /** UTF-16 code unit ngoai [0x21, 0x7E] -> non-ASCII. Khong regex. */
    public static boolean isAsciiSymbol(String s) {
        if (s == null || s.isEmpty()) return false;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c < 0x21 || c > 0x7E) return false;
        }
        return true;
    }

    public boolean hasSnapshot() { return snap != null; }

    public long loadedAtMs() { Snapshot s = snap; return s == null ? 0L : s.loadedAtMs; }

    /** San con TRADING (moi loai hop dong, ke ca TradFi / EXCLUDE) - cho quan ly vi the. */
    public boolean isAlive(String symbol) {
        Snapshot s = snap;
        return s != null && s.alive.contains(symbol);
    }

    /** Trong universe U. */
    public boolean isTradable(String symbol) {
        Snapshot s = snap;
        return s != null && s.tradable.contains(symbol);
    }

    /** Duoc MO MOI tai nowMs. */
    public boolean isBuyable(String symbol, long nowMs) {
        Snapshot s = snap;
        return s != null && buyableReason(s, symbol, nowMs) == null;
    }

    /** Ly do khong mua duoc (empty = mua duoc). */
    public Optional<String> whyNotBuyable(String symbol, long nowMs) {
        Snapshot s = snap;
        if (s == null) return Optional.of(Reason.NO_SNAPSHOT.name());
        Reason r = buyableReason(s, symbol, nowMs);
        if (r == null) return Optional.empty();
        String extra = "";
        if (r == Reason.TRADFI) extra = " " + s.verdicts.get(symbol);
        if (r == Reason.DELIVERY_SOON) extra = " deliveryDate=" + s.metas.get(symbol).getDeliveryDate();
        if (r == Reason.STALE) extra = " snapshot=" + s.loadedAtMs;
        return Optional.of(r.name() + extra);
    }

    private Reason buyableReason(Snapshot s, String symbol, long nowMs) {
        if (nowMs - s.loadedAtMs > cfg.maxStaleMs) return Reason.STALE;
        SymbolMeta m = s.metas.get(symbol);
        if (m == null) return Reason.NOT_LISTED;
        Reason nt = s.notTradable.get(symbol);
        if (nt != null) return nt;
        if (!isAsciiSymbol(symbol) && !cfg.allowNonAscii) return Reason.NON_ASCII;
        long dd = m.getDeliveryDate();
        if (dd <= 0) return Reason.DELIVERY_UNKNOWN;
        if (dd < nowMs + DELIVERY_GUARD_MS) return Reason.DELIVERY_SOON;
        return null;
    }

    /** Thanh vien ALT_EW / market level c3_live: U (da loai TradFi, EXCLUDE), non-ASCII chi khi LIVE_C3_ALLOW_NONASCII=1. */
    public Set<String> marketIndexMembers() {
        Snapshot s = snap;
        if (s == null) return Collections.emptySet();
        Set<String> out = new TreeSet<>();
        for (String x : s.tradable) if (cfg.allowNonAscii || isAsciiSymbol(x)) out.add(x);
        return Collections.unmodifiableSet(out);
    }

    /** Toan bo U (gom non-ASCII). */
    public Set<String> tradableSymbols() {
        Snapshot s = snap;
        return s == null ? Collections.emptySet() : Collections.unmodifiableSet(new TreeSet<>(s.tradable));
    }

    /** Phan loai TradFi cua 1 symbol trong snapshot (bang chung). */
    public Optional<TradFiClassifier.Verdict> classification(String symbol) {
        Snapshot s = snap;
        return s == null ? Optional.empty() : Optional.ofNullable(s.verdicts.get(symbol));
    }

    /** Ly do khong nam trong U (empty = nam trong U). */
    public Optional<Reason> notTradableReason(String symbol) {
        Snapshot s = snap;
        if (s == null) return Optional.of(Reason.NO_SNAPSHOT);
        if (!s.metas.containsKey(symbol)) return Optional.of(Reason.NOT_LISTED);
        return Optional.ofNullable(s.notTradable.get(symbol));
    }

    /** Bao cao lan refresh gan nhat (null neu chua co). */
    public UniverseDiff diff() { return lastDiff; }

    public Config config() { return cfg; }

    static String upper(String s) { return s == null ? null : s.toUpperCase(Locale.ROOT); }

    private static String trimOrEmpty(String s) { return s == null ? "" : s.trim(); }
}
