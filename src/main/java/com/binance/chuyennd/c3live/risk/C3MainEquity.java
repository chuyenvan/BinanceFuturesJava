package com.binance.chuyennd.c3live.risk;

import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.IncomeRecord;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.scope.C3Scope;
import com.binance.chuyennd.c3live.scope.C3ScopedGateway;
import com.binance.chuyennd.ops.EquitySource;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.function.Consumer;
import java.util.function.LongSupplier;

/**
 * [V12 R4 R4] Von &amp; equity RIENG c3 tren TAI KHOAN CHINH (tmb gom 44 vi the LEGACY => KHONG dung cho size / DD).
 * <pre>
 * equity c3 = C3_CAPITAL + realized c3 (rp - phi, cac cum c3 da dong tu moc bat dau + cum dang mo)
 *           + funding c3 (income FUNDING_FEE theo symbol trong khoang c3 giu; symbol MERGED => phan theo qty c3)
 *           + unrealized c3 (qty c3 x (mark - gia vao c3)).
 * von size = min(C3_CAPITAL, equity c3, availableBalance + margin c3 dang dung)   (khong tu phinh theo lai)
 * </pre>
 * La {@link EquitySource} cho kill-switch A40 (va C6 qua OpsHooks.onBook): DD do tren equity c3 voi dinh RIENG.
 * availableBalance (toan tai khoan) chi dung de kiem an toan ky quy: &lt; 2 x margin c3 => canh bao (Telegram, thua 1 h).
 * Loi doc / so khong hop le => null (chan mo moi, A40 giu trang thai). Trang thai (moc bat dau, funding cong don, moc income)
 * persist {@code stateFile}; nhan adapter khac (dry vs live) => bat dau lai.
 */
public final class C3MainEquity implements EquitySource {

    private static final Logger LOG = LoggerFactory.getLogger(C3MainEquity.class);
    public static final String KEY_CAPITAL = "C3_CAPITAL";
    public static final double DEFAULT_CAPITAL = 10_000d;
    public static final long FUNDING_POLL_MS = 600_000L;
    public static final long MARGIN_WARN_EVERY_MS = 3_600_000L;
    public static final int INCOME_LIMIT = 1000;
    public static final long MAX_TTL_MS = 60_000L;
    static final Set<String> STABLE = new HashSet<>(Arrays.asList("USDT", "USDC", "BFUSD", "FDUSD"));

    private final C3ScopedGateway gw;
    private final LiveBookC3 book;
    private final C3Scope scope;
    private final double capital;
    private final File stateFile;
    private final String tag;
    private final long ttlMs;
    private final LongSupplier clock;
    private final C3LiveOrderExecutor.ApiObserver api;
    private final Consumer<String> alert;

    private long startMs;
    private double fundingCum;
    private long incomeLastMs;
    private final Set<String> incomeLastIds = new HashSet<>();
    private Double eqCached;
    private long eqAtMs = Long.MIN_VALUE / 2;
    private Double availCached;
    private long availAtMs = Long.MIN_VALUE / 2;
    private long lastFundingPollMs = Long.MIN_VALUE / 2;
    private long lastMarginWarnMs = Long.MIN_VALUE / 2;
    private long lastWarnMs = Long.MIN_VALUE / 2;
    private long ledgerLen = -1L;
    private long ledgerMtime = -1L;
    private double ledgerNet;
    private final Map<String, List<long[]>> closedIntervals = new HashMap<>();
    /** [W3B muc 2] single-flight REST positions (c3Equity) / account (available): toi da 1 REST moi loai cung luc. */
    private final Object posFlight = new Object();
    private final Object accFlight = new Object();

    /**
     * [W3B muc 2 / HANG-1119 muc 6] REST (positions / account / income, gom ngu RateGuard toi ~14 s) va callback
     * {@code api.onApiResult} / alert chay NGOAI khoa {@code this} (khoa chi giu khi doc/ghi cache + tinh). Single-flight
     * theo loai; cache/TTL va ket qua 1 thread y nhu cu. Env {@value #KEY_REST_UNLOCKED}: khong dat / khac 0|false = BAT;
     * "0"/"false" = hanh vi cu (ca loi goi trong khoa).
     */
    public static final String KEY_REST_UNLOCKED = "C3_EQ_REST_UNLOCKED";
    static volatile boolean restUnlocked = effectiveRestUnlocked(com.binance.chuyennd.tradecore.Cfg.get(KEY_REST_UNLOCKED),
            com.binance.chuyennd.tradecore.Cfg.get("KILLSW_EQ_POLL_UNLOCKED"));

    /**
     * [W3B v2] Cam to hop tat CA 2 co (C3_EQ_REST_UNLOCKED + KILLSW_EQ_POLL_UNLOCKED = 0|false) = chu trinh khoa
     * KS&lt;-&gt;EQ cua lan treo 19/11: khi do ep REST ngoai khoa + WARN.
     *
     * @param eqRaw env C3_EQ_REST_UNLOCKED
     * @param ksRaw env KILLSW_EQ_POLL_UNLOCKED
     * @return true = REST ngoai khoa
     */
    static boolean effectiveRestUnlocked(String eqRaw, String ksRaw) {
        boolean eq = restUnlockedFrom(eqRaw);
        if (!eq && !restUnlockedFrom(ksRaw)) {
            LOG.warn("[C3-LIVE-EQ] {}=false VA KILLSW_EQ_POLL_UNLOCKED=false = to hop DEADLOCK (treo 19/11) => BO QUA {}, giu REST"
                    + " ngoai khoa", KEY_REST_UNLOCKED, KEY_REST_UNLOCKED);
            return true;
        }
        return eq;
    }

    /**
     * @param raw gia tri env
     * @return true = REST ngoai khoa (mac dinh)
     */
    static boolean restUnlockedFrom(String raw) {
        if (raw == null) return true;
        String v = raw.trim();
        return !("0".equals(v) || "false".equalsIgnoreCase(v));
    }

    public C3MainEquity(C3ScopedGateway gw, LiveBookC3 book, C3Scope scope, double capital, File stateFile, String tag,
                        long ttlMs, LongSupplier clock, C3LiveOrderExecutor.ApiObserver api, Consumer<String> alert) {
        if (!(capital > 0d)) throw new IllegalArgumentException("C3_CAPITAL phai > 0");
        this.gw = gw;
        this.book = book;
        this.scope = scope;
        this.capital = capital;
        this.stateFile = stateFile;
        this.tag = tag == null ? "-" : tag;
        this.ttlMs = Math.max(0L, Math.min(MAX_TTL_MS, ttlMs));
        this.clock = clock == null ? System::currentTimeMillis : clock;
        this.api = api == null ? (a, ok) -> { } : api;
        this.alert = alert == null ? m -> { } : alert;
        loadState();
    }

    public double capitalConfig() {
        return capital;
    }

    public synchronized long startMs() {
        return startMs;
    }

    public synchronized double fundingCum() {
        return fundingCum;
    }

    /** EquitySource (A40): = equity c3 (KHONG phai tmb tai khoan). */
    @Override
    public Double totalMarginBalance() {
        return c3Equity();
    }

    /** equity c3 (cache &lt;= ttl). null = khong co so tin cay. */
    public Double c3Equity() {
        if (!restUnlocked) {
            synchronized (this) {   // hanh vi cu: REST + onApiResult trong khoa
                return c3EquityFlight();
            }
        }
        synchronized (this) {   // [W3B muc 2] cache con han => tra ngay (khong cho REST cua thread khac)
            long now = clock.getAsLong();
            if (eqCached != null && now - eqAtMs < ttlMs) return eqCached;
        }
        return c3EquityFlight();
    }

    /** [W3B muc 2] single-flight positions: kiem lai cache trong luot; REST ngoai khoa this; onApiResult ngoai moi khoa. */
    private Double c3EquityFlight() {
        Double res;
        RuntimeException err = null;
        synchronized (posFlight) {
            long now;
            synchronized (this) {
                now = clock.getAsLong();
                if (eqCached != null && now - eqAtMs < ttlMs) return eqCached;
            }
            Map<String, BigDecimal> mark = new HashMap<>();
            try {
                for (PositionInfo p : gw.positions()) {
                    if (p.getSymbol() != null && p.getMarkPrice() != null && p.getMarkPrice().signum() > 0) mark.put(p.getSymbol(), p.getMarkPrice());
                }
            } catch (RuntimeException e) {
                err = e;
            }
            synchronized (this) {
                res = err != null ? fail(now, "positions() loi: " + err) : computeEquity(now, mark);
            }
        }
        api.onApiResult("positions", err == null);
        return res;
    }

    /** Tinh equity c3 tu markPrice (goi trong khoa this). */
    private Double computeEquity(long now, Map<String, BigDecimal> mark) {
        double upl = 0d;
        double openNet = 0d;
        for (LiveBookC3.ClusterView c : book.clusters()) {
            openNet += c.realizedPnl - c.commission;
            BigDecimal open = c.confirmedQty.subtract(c.exitQty == null ? BigDecimal.ZERO : c.exitQty);
            if (open.signum() <= 0) continue;
            BigDecimal m = mark.get(c.symbol);
            if (m == null) return fail(now, "khong co markPrice cho " + c.symbol + " (qty c3 " + open.toPlainString() + ")");
            if (!(c.avgPrice > 0d)) return fail(now, "gia vao c3 khong hop le " + c.symbol);
            upl += open.doubleValue() * (m.doubleValue() - c.avgPrice);
        }
        double eq = capital + ledgerNet() + openNet + fundingCum + upl;
        if (!Double.isFinite(eq)) return fail(now, "equity c3 khong hop le " + eq);
        eqCached = eq;
        eqAtMs = now;
        return eq;
    }

    private Double fail(long now, String why) {
        eqCached = null;
        if (now - lastWarnMs >= 600_000L) {
            lastWarnMs = now;
            LOG.warn("[C3-LIVE-EQ] {} => khong co equity c3 (chan mo moi, A40 giu trang thai)", why);
        }
        return null;
    }

    /** Von tinh size = min(C3_CAPITAL, equity c3, availableBalance + margin c3); null neu khong co so. */
    public Double capital() {
        if (!restUnlocked) {
            synchronized (this) {   // hanh vi cu
                return capitalImpl();
            }
        }
        return capitalImpl();
    }

    private Double capitalImpl() {
        Double eq = c3Equity();
        if (eq == null) return null;
        Double avail = available();
        if (avail == null) return null;
        double cap;
        String warn = null;
        synchronized (this) {
            double margin = book.marginUsed();
            cap = Math.min(capital, eq);
            cap = Math.min(cap, avail + margin);
            long now = clock.getAsLong();
            if (margin > 0d && avail < 2d * margin && now - lastMarginWarnMs >= MARGIN_WARN_EVERY_MS) {
                lastMarginWarnMs = now;
                warn = "[C3-LIVE-EQ] CANH BAO ky quy tai khoan chinh: availableBalance=" + fmt(avail) + " < 2 x margin c3 "
                        + fmt(margin) + " (LEGACY + c3 dung chung ky quy cross) — kiem tai khoan";
            }
        }
        if (warn != null) {   // [W3B muc 2] alert ngoai khoa this
            LOG.warn("{}", warn);
            alert.accept(warn);
        }
        return cap;
    }

    private Double available() {
        synchronized (this) {
            long now = clock.getAsLong();
            if (availCached != null && now - availAtMs < ttlMs) return availCached;
        }
        Double res;
        RuntimeException err = null;
        synchronized (accFlight) {   // [W3B muc 2] single-flight account, REST ngoai khoa this
            long now;
            synchronized (this) {
                now = clock.getAsLong();
                if (availCached != null && now - availAtMs < ttlMs) return availCached;
            }
            AccountSnapshot a = null;
            try {
                a = gw.accountRaw();
            } catch (RuntimeException e) {
                err = e;
            }
            synchronized (this) {
                BigDecimal av = err != null || a == null ? null : a.getAvailableBalance();
                if (av == null) {
                    availCached = null;
                    res = null;
                } else {
                    availCached = av.doubleValue();
                    availAtMs = now;
                    res = availCached;
                }
            }
        }
        api.onApiResult("account", err == null);
        if (err != null) LOG.warn("[C3-LIVE-EQ] account() loi {} => khong co availableBalance (chan mo moi)", err.toString());
        return res;
    }

    // ------------------------------------------------------------------ funding c3 (income)
    /** Moi {@link #FUNDING_POLL_MS}: income FUNDING_FEE moi => cong phan c3. @return so dong da cong; -1 = loi doc. */
    public int pollFunding(long now) {
        if (!restUnlocked) {
            synchronized (this) {   // hanh vi cu
                return pollFundingImpl(now);
            }
        }
        return pollFundingImpl(now);
    }

    /** [W3B muc 2] kiem+dat moc 10' trong khoa (=> single-flight), REST income ngoai khoa, xu ly + luu trong khoa. */
    private int pollFundingImpl(long now) {
        long from;
        synchronized (this) {
            if (now - lastFundingPollMs < FUNDING_POLL_MS) return 0;
            lastFundingPollMs = now;
            from = Math.max(startMs, incomeLastMs);
        }
        List<IncomeRecord> rs;
        try {
            rs = gw.income("FUNDING_FEE", from, INCOME_LIMIT);
        } catch (UnsupportedOperationException e) {
            return 0;
        } catch (RuntimeException e) {
            api.onApiResult("income", false);
            LOG.warn("[C3-LIVE-EQ] doc income FUNDING_FEE loi {} => thu lai sau {} s", e.toString(), FUNDING_POLL_MS / 1000);
            return -1;
        }
        api.onApiResult("income", true);
        synchronized (this) {
            return applyIncome(rs, from);
        }
    }

    /** Cong funding c3 tu cac dong income (goi trong khoa this). */
    private int applyIncome(List<IncomeRecord> rs, long from) {
        List<IncomeRecord> sorted = new ArrayList<>(rs);
        sorted.sort(Comparator.comparingLong(IncomeRecord::getTimeMs));
        int n = 0;
        double add = 0d;
        for (IncomeRecord r : sorted) {
            if (r.getTimeMs() < from || r.getIncome() == null || r.getSymbol() == null) continue;
            if (r.getTimeMs() < startMs) continue;
            String id = r.getTranId() == null ? r.getSymbol() + "@" + r.getTimeMs() + "@" + r.getIncome() : r.getTranId();
            if (r.getTimeMs() == incomeLastMs && incomeLastIds.contains(id)) continue;
            if (r.getTimeMs() > incomeLastMs) {
                incomeLastMs = r.getTimeMs();
                incomeLastIds.clear();
            }
            incomeLastIds.add(id);
            if (r.getAsset() != null && !STABLE.contains(r.getAsset().toUpperCase(Locale.ROOT))) {
                LOG.warn("[C3-LIVE-EQ] funding {} bang tai san {} khong on dinh => bo qua", r.getSymbol(), r.getAsset());
                continue;
            }
            double ratio = heldRatio(r.getSymbol(), r.getTimeMs());
            if (ratio <= 0d) continue;
            add += r.getIncome().doubleValue() * ratio;
            n++;
        }
        if (n > 0) {
            fundingCum += add;
            eqCached = null;
            LOG.info("[C3-LIVE-EQ] funding c3 +{} ({} dong) => cong don {}", fmt(add), n, fmt(fundingCum));
        }
        saveState();
        return n;
    }

    /** Ty le funding cua symbol tai thoi diem t thuoc c3 (0 = c3 khong giu). */
    double heldRatio(String sym, long t) {
        Optional<LiveBookC3.ClusterView> c = book.cluster(sym);
        if (c.isPresent() && c.get().tsFirstLeg <= t) {
            if (scope != null && scope.isMerged(sym)) {
                BigDecimal raw = scope.lastRawAmt(sym);
                BigDecimal open = scope.c3OpenQty(sym);
                if (raw != null && raw.signum() > 0) return Math.min(1d, open.doubleValue() / raw.doubleValue());
            }
            return 1d;
        }
        ledgerNet();   // nap khoang giu da dong
        List<long[]> iv = closedIntervals.get(sym);
        if (iv != null) for (long[] x : iv) if (x[0] <= t && t <= x[1]) return 1d;
        return 0d;
    }

    // ------------------------------------------------------------------ ledger c3 (cum da dong)
    private double ledgerNet() {
        File f = ledgerFile();
        if (f == null || !f.exists()) {
            ledgerNet = 0d;
            closedIntervals.clear();
            return 0d;
        }
        long len = f.length();
        long mt = f.lastModified();
        if (len == ledgerLen && mt == ledgerMtime) return ledgerNet;
        double net = 0d;
        Map<String, List<long[]>> iv = new HashMap<>();
        try {
            List<String> lines = Files.readAllLines(f.toPath(), StandardCharsets.UTF_8);
            for (int i = 1; i < lines.size(); i++) {
                String[] t = lines.get(i).split(",", -1);
                if (t.length < 11) continue;
                long first = Long.parseLong(t[1].trim());
                long close = Long.parseLong(t[10].trim());
                if (close < startMs) continue;
                net += Double.parseDouble(t[7].trim()) - Double.parseDouble(t[8].trim());
                iv.computeIfAbsent(t[0].trim(), k -> new ArrayList<>()).add(new long[]{first, close});
            }
        } catch (Exception e) {
            LOG.error("[C3-LIVE-EQ] khong doc duoc ledger {}: {} => giu so cu", f.getPath(), e.toString());
            return ledgerNet;
        }
        ledgerNet = net;
        closedIntervals.clear();
        closedIntervals.putAll(iv);
        ledgerLen = len;
        ledgerMtime = mt;
        return net;
    }

    private File ledgerFile() {
        File bf = book.file();
        if (bf == null || bf.getAbsoluteFile().getParentFile() == null) return null;
        return new File(bf.getAbsoluteFile().getParentFile(), LiveBookC3.LEDGER_NAME);
    }

    // ------------------------------------------------------------------ persist
    private void loadState() {
        long now = clock.getAsLong();
        if (stateFile != null && stateFile.exists()) {
            try {
                JsonObject o = JsonParser.parseString(new String(Files.readAllBytes(stateFile.toPath()), StandardCharsets.UTF_8))
                        .getAsJsonObject();
                String t = o.has("adapter") ? o.get("adapter").getAsString() : null;
                if (tag.equals(t)) {
                    startMs = o.get("start_ms").getAsLong();
                    fundingCum = o.has("funding_cum") ? o.get("funding_cum").getAsDouble() : 0d;
                    incomeLastMs = o.has("income_last_ms") ? o.get("income_last_ms").getAsLong() : 0L;
                    if (o.has("income_last_ids")) for (JsonElement e : o.getAsJsonArray("income_last_ids")) incomeLastIds.add(e.getAsString());
                    LOG.warn("[C3-LIVE-EQ] nap trang thai equity c3 {}: bat dau={} funding={} capital={}", stateFile.getPath(), startMs,
                            fmt(fundingCum), fmt(capital));
                    return;
                }
                String m = "[C3-LIVE-EQ] file equity c3 " + stateFile.getPath() + " cua adapter=" + t + " != " + tag
                        + " => BAT DAU LAI moc equity c3 (realized/funding tinh tu bay gio)";
                LOG.warn("{}", m);
                alert.accept(m);
            } catch (Exception e) {
                String m = "[C3-LIVE-EQ] file equity c3 " + stateFile.getPath() + " hong (" + e.getClass().getSimpleName()
                        + ") => BAT DAU LAI moc equity c3";
                LOG.error("{}", m);
                alert.accept(m);
            }
        }
        startMs = now;
        fundingCum = 0d;
        incomeLastMs = now;
        incomeLastIds.clear();
        saveState();
    }

    private void saveState() {
        if (stateFile == null) return;
        try {
            JsonObject o = new JsonObject();
            o.addProperty("adapter", tag);
            o.addProperty("start_ms", startMs);
            o.addProperty("capital", capital);
            o.addProperty("funding_cum", fundingCum);
            o.addProperty("income_last_ms", incomeLastMs);
            JsonArray ids = new JsonArray();
            for (String s : incomeLastIds) ids.add(s);
            o.add("income_last_ids", ids);
            File abs = stateFile.getAbsoluteFile();
            if (abs.getParentFile() != null) abs.getParentFile().mkdirs();
            File tmp = new File(abs.getParentFile(), abs.getName() + ".tmp");
            Files.write(tmp.toPath(), o.toString().getBytes(StandardCharsets.UTF_8));
            Files.move(tmp.toPath(), abs.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (Exception e) {
            LOG.error("[C3-LIVE-EQ] khong ghi duoc file equity c3 {}: {}", stateFile.getPath(), e.toString());
        }
    }

    private static String fmt(double v) {
        return String.format(Locale.ROOT, "%.2f", v);
    }

    public synchronized String status() {
        return "capital=" + fmt(capital) + " eq=" + (eqCached == null ? "NA" : fmt(eqCached)) + " funding=" + fmt(fundingCum)
                + " ledgerNet=" + fmt(ledgerNet) + " start=" + startMs;
    }
}
