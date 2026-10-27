package com.binance.chuyennd.c3live.canary;

import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.api.SymbolConfig;
import com.binance.chuyennd.c3live.api.Ticker24h;
import com.binance.chuyennd.c3live.exec.C3LiveCids;
import com.binance.chuyennd.c3live.rate.RateGuard;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.BooleanSupplier;
import java.util.function.IntSupplier;
import java.util.function.LongSupplier;
import java.util.function.Supplier;

/**
 * [V12 3] Lop bao ve CUNG quanh gateway that cua canary (moi lop c3_live trong JVM canary di qua day):
 * <ul>
 *   <li>moi lenh ghi (mo/dong/stop/huy/dat cau hinh) CHI tren 2 symbol do luat chon; symbol khac => TU CHOI (khong goi san);</li>
 *   <li>lenh MO (BUY khong reduceOnly): notional = qty x gia moi doc (ticker) &lt;= {@link CanaryLimits#MAX_ORDER_NOTIONAL_USDT};
 *       tong notional dang mo + lenh &lt;= {@link CanaryLimits#MAX_OPEN_NOTIONAL_USDT}; cham tran lo => TU CHOI; khong doc duoc gia /
 *       vi the => TU CHOI; co vi the symbol khac => TU CHOI;</li>
 *   <li>khong mo short (SELL khong reduceOnly), khong BUY reduceOnly; stop chi SELL, stop qty bat buoc reduceOnly;</li>
 *   <li>leverage chi = 1, marginType chi CROSSED, dualSide chi false;</li>
 *   <li>moi call ghi {@link CanaryJournal} (khong key/chu ky), dem weight lon nhat, HTTP 429/418, so lan gui theo cid.</li>
 * </ul>
 * Tiem loi CHI phia client (khong gui request la len san): positionRisk / account loi (K7b), mat response sau khi gui
 * DUNG 1 lenh MO (MO-5, K1).
 */
public final class CanaryGateway implements ExchangeGateway {

    /** Loi do lop bao ve canary tu choi (chac chan KHONG gui len san). */
    public static final class GuardException extends GatewayException {
        private static final long serialVersionUID = 1L;

        GuardException(String msg) {
            super(ErrorKind.OTHER, "CANARY GUARD: " + msg, true);
        }
    }

    private final ExchangeGateway d;
    private final Set<String> allowed;
    private final CanaryJournal j;
    private final IntSupplier weight;
    private final BooleanSupplier lossCapHit;
    /** Goi (symbol, cid) truoc moi lenh ghi co cid (engine ghi phut cuoi dung cid cua symbol). */
    public volatile java.util.function.BiConsumer<String, String> cidListener;
    public volatile boolean failPositions;
    public volatile boolean failAccount;
    private volatile boolean timeoutAfterNextOpen;
    private final Map<String, Integer> sendsByCid = new ConcurrentHashMap<>();
    private final AtomicLong mutating = new AtomicLong();
    private final AtomicLong refused = new AtomicLong();
    private final AtomicInteger maxWeight = new AtomicInteger(-1);
    private final AtomicInteger rateLimited = new AtomicInteger();
    private final List<OrderInfo> stopResponses = Collections.synchronizedList(new ArrayList<>());
    /** [3f §ADD-4] so luong canary (ledger) cua symbol; null = khong kiem (test truc tiep gateway). */
    public volatile java.util.function.Function<String, BigDecimal> canaryQty;
    /** [3f] nhan khoi luong da khop cua lenh cid canary (response / queryOrder) => engine cap nhat ledger. */
    public volatile ExecListener execListener;
    /** [3f §ADD-4 I] ngu khi guard client tu choi call thuong (IP nang): cho sang phut sau roi thu lai 1 lan. */
    public volatile java.util.function.LongConsumer guardSleep = ms -> {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
        }
    };
    /** [3f] cho toi da truoc khi thu lai call bi guard client tu choi (het phut + 1 s). */
    public static final long GUARD_RETRY_MAX_WAIT_MS = 61_000L;
    static final BigDecimal QTY_EPS = new BigDecimal("0.000000001");

    /** [3f] khoi luong da khop cua 1 lenh cid canary. */
    public interface ExecListener {
        void onExec(String symbol, String cid, BigDecimal executedQty);
    }

    /** [3f] cid lenh thuong cua canary (mo c3- / dong c3x-). */
    public static boolean canaryOrderCid(String cid) {
        return cid != null && (cid.startsWith(C3LiveCids.ENTRY_PREFIX) || cid.startsWith(C3LiveCids.CLOSE_PREFIX));
    }

    /** [3f] cid algo (stop) cua canary (c3s-). */
    public static boolean canaryAlgoCid(String cid) {
        return cid != null && cid.startsWith(C3LiveCids.STOP_PREFIX);
    }

    public static boolean canaryAnyCid(String cid) {
        return canaryOrderCid(cid) || canaryAlgoCid(cid);
    }

    /** [3e] dong ho dem weight canary tu goi (engine gan = dong ho phien). */
    public volatile LongSupplier ownClock = System::currentTimeMillis;
    private long ownBucket = Long.MIN_VALUE;
    private int ownInBucket;
    private final AtomicInteger maxOwn = new AtomicInteger(0);

    public CanaryGateway(ExchangeGateway delegate, Set<String> allowedSymbols, CanaryJournal journal, IntSupplier usedWeight1m,
                         BooleanSupplier lossCapHit) {
        if (allowedSymbols == null || allowedSymbols.isEmpty() || allowedSymbols.size() > CanaryLimits.SYMBOLS) {
            throw new IllegalArgumentException("can 1.." + CanaryLimits.SYMBOLS + " symbol canary");
        }
        this.d = delegate;
        this.allowed = Collections.unmodifiableSet(new LinkedHashSet<>(allowedSymbols));
        this.j = journal;
        this.weight = usedWeight1m == null ? () -> -1 : usedWeight1m;
        this.lossCapHit = lossCapHit == null ? () -> false : lossCapHit;
    }

    public Set<String> allowed() {
        return allowed;
    }

    /** MO-5: lan MO ke tiep duoc gui that roi gia lap mat response (TIMEOUT_UNKNOWN_STATE). Chi 1 lan. */
    public void armTimeoutAfterNextOpen() {
        timeoutAfterNextOpen = true;
        j.ev("INJECT_ARMED", "what", "timeout_after_next_open");
    }

    public boolean timeoutArmed() {
        return timeoutAfterNextOpen;
    }

    public int sends(String cid) {
        return sendsByCid.getOrDefault(cid, 0);
    }

    public Map<String, Integer> sendsByCid() {
        return new LinkedHashMap<>(sendsByCid);
    }

    public long mutatingCalls() {
        return mutating.get();
    }

    public long refusedCalls() {
        return refused.get();
    }

    public int maxWeight1m() {
        return maxWeight.get();
    }

    public int rateLimitedCount() {
        return rateLimited.get();
    }

    /** [3e] Weight canary TU GOI lon nhat trong 1 phut co dinh (uoc tinh bao thu nhu W_* cua C3LiveClient; chi JVM nay). */
    public int maxOwnWeight1m() {
        return maxOwn.get();
    }

    /** [3e] Weight uoc tinh 1 call — khop hang W_* cua C3LiveClient (khong symbol => ban toan tai khoan). */
    static int estWeight(String api, String sym) {
        String a = api == null ? "" : api;
        if (a.startsWith("positions") || a.startsWith("account") || a.startsWith("symbolConfig")) return 5;
        if ("multiAssetsMargin".equals(a) || "dualSidePosition".equals(a)) return 30;
        if ("openOrders".equals(a) || "openStops".equals(a) || "tickers24h".equals(a)) return sym == null ? 40 : 1;
        if ("openOrdersAll".equals(a) || "openStopsAll".equals(a)) return 40;
        return 1;
    }

    private synchronized int addOwnWeight(int w) {
        long b = Math.floorDiv(ownClock.getAsLong(), 60_000L);
        if (b != ownBucket) {
            ownBucket = b;
            ownInBucket = 0;
        }
        ownInBucket += w;
        maxOwn.accumulateAndGet(ownInBucket, Math::max);
        return ownInBucket;
    }

    public List<OrderInfo> stopResponses() {
        synchronized (stopResponses) {
            return new ArrayList<>(stopResponses);
        }
    }

    // ------------------------------------------------------------------ bao ve
    private GuardException refuse(String api, String sym, String why) {
        refused.incrementAndGet();
        j.ev("GUARD_REFUSE", "api", api, "symbol", sym, "why", why);
        return new GuardException(api + " " + sym + ": " + why);
    }

    private void requireAllowed(String api, String sym) {
        if (sym == null || !allowed.contains(sym)) throw refuse(api, sym, "symbol ngoai canary " + allowed);
    }

    private BigDecimal freshPrice(String sym) {
        List<Ticker24h> t;
        try {
            t = tickers24h(sym);
        } catch (RuntimeException e) {
            throw refuse("newMarketOrder", sym, "khong doc duoc gia tham chieu (" + e.getClass().getSimpleName() + ")");
        }
        for (Ticker24h x : t) {
            if (sym.equals(x.getSymbol()) && x.getLastPrice() != null && x.getLastPrice().signum() > 0) return x.getLastPrice();
        }
        throw refuse("newMarketOrder", sym, "khong co gia tham chieu");
    }

    /** Gia vao cua vi the long (doc thang delegate). null = khong co vi the / khong doc duoc (stop van duoc dat: giam rui ro). */
    private BigDecimal entryPrice(String sym) {
        try {
            for (PositionInfo p : d.positions()) {
                if (sym.equals(p.getSymbol()) && p.getPositionAmt() != null && p.getPositionAmt().signum() > 0
                        && p.getEntryPrice() != null && p.getEntryPrice().signum() > 0) {
                    return p.getEntryPrice();
                }
            }
        } catch (RuntimeException e) {
            j.ev("GUARD_STOP_NOREAD", "symbol", sym, "err", e.getClass().getSimpleName());
        }
        return null;
    }

    private BigDecimal openNotional(String sym) {
        List<PositionInfo> ps;
        try {
            ps = d.positions();
        } catch (RuntimeException e) {
            throw readFail("newMarketOrder", sym, "khong doc duoc vi the", e);
        }
        BigDecimal sum = BigDecimal.ZERO;
        for (PositionInfo p : ps) {
            if (p.getPositionAmt() == null || p.getPositionAmt().signum() == 0) continue;
            if (!allowed.contains(p.getSymbol())) continue;   // [3f §ADD-4] LEGACY tren symbol khac: binh thuong, khong tinh, khong cham
            java.util.function.Function<String, BigDecimal> cq = canaryQty;
            if (cq != null && sym.equals(p.getSymbol())) {
                BigDecimal led = cq.apply(sym);
                if (led == null || p.getPositionAmt().compareTo(led.add(QTY_EPS)) > 0) {
                    throw refuse("newMarketOrder", sym, "vi the san " + p.getPositionAmt().toPlainString() + " > canary " + led
                            + " (vi the ngoai canary tren symbol canary, §ADD-4 C)");
                }
            }
            BigDecimal px = p.getMarkPrice() != null && p.getMarkPrice().signum() > 0 ? p.getMarkPrice() : p.getEntryPrice();
            BigDecimal n = p.getNotional() != null && p.getNotional().signum() != 0 ? p.getNotional().abs()
                    : p.getPositionAmt().abs().multiply(px == null ? BigDecimal.ZERO : px);
            sum = sum.add(n);
        }
        return sum;
    }

    /** [3f §ADD-4 A/C/F] lenh/algo KHONG mang cid canary tren symbol (doc thang delegate, khong qua view). */
    private List<String> foreignOn(String api, String sym) {
        List<String> out = new ArrayList<>();
        try {
            for (OrderInfo o : d.openOrders(sym)) if (!canaryOrderCid(o.getClientOrderId())) out.add("lenh " + o.getClientOrderId());
            for (OrderInfo o : d.openStops(sym)) if (!canaryAlgoCid(o.getClientOrderId())) out.add("algo " + o.getClientOrderId());
        } catch (RuntimeException e) {
            throw readFail(api, sym, "khong doc duoc lenh/algo cua symbol", e);
        }
        return out;
    }

    /** [3f §ADD-4 F] doi leverage/margin chi khi symbol khong co vi the va khong co lenh/algo ngoai canary. */
    private void requireScopeClean(String api, String sym) {
        BigDecimal amt = BigDecimal.ZERO;
        try {
            for (PositionInfo p : d.positions()) {
                if (sym.equals(p.getSymbol()) && p.getPositionAmt() != null) amt = amt.add(p.getPositionAmt());
            }
        } catch (RuntimeException e) {
            throw readFail(api, sym, "khong doc duoc vi the", e);
        }
        if (amt.signum() != 0) throw refuse(api, sym, "symbol dang co vi the " + amt.toPlainString() + " (§ADD-4 F)");
        List<String> f = foreignOn(api, sym);
        if (!f.isEmpty()) throw refuse(api, sym, "co lenh/algo ngoai canary " + f + " (§ADD-4 F)");
    }

    /**
     * [3h MINOR] chay kiem truoc ghi; doc trong kiem bi guard client tu choi (RATE_LIMIT, chua gui, IP nang) => cho sang phut sau roi
     * chay LAI toan bo kiem (toi da 2 lan cho). Loi khac / GuardException => nem ngay.
     */
    private void runPre(String api, String sym, String cid, Runnable pre) {
        for (int i = 0; ; i++) {
            try {
                pre.run();
                return;
            } catch (GatewayException e) {
                if (e instanceof GuardException || !guardRetryable(e) || i >= 2) throw e;
                long w = Math.min(GUARD_RETRY_MAX_WAIT_MS, e.getRetryAfterMs() + 1_000L);
                j.ev("GUARD_WAIT_RETRY", "api", api, "symbol", sym, "cid", cid, "waitMs", w, "why", "kiem truoc ghi: " + e.getMessage());
                guardSleep.accept(w);
            }
        }
    }

    /** Loi doc trong kiem truoc ghi: RATE_LIMIT guard client (thu lai duoc) => nem nguyen de runPre cho; khac => TU CHOI. */
    private RuntimeException readFail(String api, String sym, String what, RuntimeException e) {
        if (e instanceof GatewayException && !(e instanceof GuardException) && guardRetryable((GatewayException) e)) return e;
        return refuse(api, sym, what + " (" + e.getClass().getSimpleName() + ")");
    }

    /** [3g MAJOR-2] kiem truoc lenh MO (chay lai moi lan thu): tran lo, gia moi, notional, lenh/algo ngoai canary, tong mo, vi the <= ledger. */
    private void preOpen(String symbol, BigDecimal qty) {
        if (lossCapHit.getAsBoolean()) throw refuse("newMarketOrder", symbol, "da cham tran lo phien (hoac tran phien <= 0,10) — khong mo");
        BigDecimal px = freshPrice(symbol);
        BigDecimal notional = qty.multiply(px);
        if (notional.compareTo(CanaryLimits.MAX_ORDER_NOTIONAL_USDT) > 0) {
            throw refuse("newMarketOrder", symbol, "notional " + notional.toPlainString() + " > " + CanaryLimits.MAX_ORDER_NOTIONAL_USDT);
        }
        List<String> fo = foreignOn("newMarketOrder", symbol);
        if (!fo.isEmpty()) throw refuse("newMarketOrder", symbol, "co lenh/algo ngoai canary tren symbol " + fo + " (§ADD-4 C)");
        BigDecimal openNow = openNotional(symbol);   // + vi the san tren symbol <= ledger canary
        if (openNow.add(notional).compareTo(CanaryLimits.MAX_OPEN_NOTIONAL_USDT) > 0) {
            throw refuse("newMarketOrder", symbol, "tong mo " + openNow.add(notional).toPlainString() + " > "
                    + CanaryLimits.MAX_OPEN_NOTIONAL_USDT);
        }
    }

    /** [3g] lenh DONG (c3x- reduce-only): khong bao gio ban qua ledger canary. */
    private void preSell(String symbol, BigDecimal qty) {
        java.util.function.Function<String, BigDecimal> cq = canaryQty;
        if (cq == null) return;
        BigDecimal led = cq.apply(symbol);
        if (led == null || qty.compareTo(led.add(QTY_EPS)) > 0) {
            throw refuse("newMarketOrder", symbol, "ban " + qty.toPlainString() + " > canary " + led + " (khong ban phan ngoai canary)");
        }
    }

    /**
     * [3g MIN-7a] kiem truoc stop (chay lai moi lan thu): vi the san &lt;= ledger canary (stop closePosition / qty kich se dong ca phan
     * ngoai canary neu lan); stop khong xa hon -4,5 % so gia vao (§ADD-2). Khong doc duoc vi the => TU CHOI.
     */
    private void preStop(String symbol, BigDecimal stopPrice) {
        BigDecimal amt = BigDecimal.ZERO;
        BigDecimal entry = null;
        try {
            for (PositionInfo p : d.positions()) {
                if (!symbol.equals(p.getSymbol()) || p.getPositionAmt() == null) continue;
                amt = amt.add(p.getPositionAmt());
                if (p.getPositionAmt().signum() > 0 && p.getEntryPrice() != null && p.getEntryPrice().signum() > 0) entry = p.getEntryPrice();
            }
        } catch (RuntimeException e) {
            j.ev("GUARD_STOP_NOREAD", "symbol", symbol, "err", e.getClass().getSimpleName());
            throw readFail("newStopMarket", symbol, "khong doc duoc vi the => khong kiem duoc vi the <= canary (§3g MIN-7)", e);
        }
        java.util.function.Function<String, BigDecimal> cq = canaryQty;
        if (cq != null) {
            BigDecimal led = cq.apply(symbol);
            if (led == null || amt.compareTo(led.add(QTY_EPS)) > 0) {
                throw refuse("newStopMarket", symbol, "vi the san " + amt.toPlainString() + " > canary " + led
                        + " — stop se dong ca phan ngoai canary (§ADD-4 C, §3g MIN-7)");
            }
        }
        // [3c MAJ-C1] stop KHONG BAO GIO xa hon -4,5 % so gia vao (vi the doc tu san, khong qua tiem loi)
        if (entry != null && stopPrice != null) {
            BigDecimal floor = entry.multiply(BigDecimal.valueOf(1d - CanaryLimits.MAX_STOP_DIST - CanaryLimits.STOP_ROUND_TOL));
            if (stopPrice.compareTo(floor) < 0) {
                throw refuse("newStopMarket", symbol, "stop " + stopPrice.toPlainString() + " thap hon entry " + entry.toPlainString()
                        + " x (1 - " + CanaryLimits.MAX_STOP_DIST + ") — tran lo giua 2 JVM (§ADD-2)");
            }
        }
    }

    private void requireCid(String api, String sym, String cid, boolean ok, String want) {
        if (!ok) throw refuse(api, sym, "cid '" + cid + "' khong phai cid canary " + want + " (§ADD-4 A)");
    }

    private void notifyExec(String sym, String cid, OrderInfo o) {
        ExecListener l = execListener;
        if (l == null || o == null || !canaryOrderCid(cid) || o.getExecutedQty() == null) return;
        try {
            l.onExec(sym, cid, o.getExecutedQty());
        } catch (RuntimeException e) {
            j.ev("EXEC_LISTENER_ERROR", "symbol", sym, "cid", cid, "err", e.toString());
        }
    }

    private List<PositionInfo> scopePositions(List<PositionInfo> in) {
        List<PositionInfo> out = new ArrayList<>();
        if (in == null) return out;
        for (PositionInfo p : in) if (p.getSymbol() != null && allowed.contains(p.getSymbol())) out.add(p);
        return out;
    }

    private AccountSnapshot scopeAccount(AccountSnapshot a) {
        if (a == null) return null;
        List<PositionInfo> ps = a.getPositions() == null ? null : scopePositions(a.getPositions());
        return new AccountSnapshot(a.getTotalMarginBalance(), a.getTotalWalletBalance(), a.getAvailableBalance(),
                a.getTotalUnrealizedProfit(), a.getAssets(), a.getTimeMs(), ps);
    }

    /** [3f §ADD-4 I] guard CLIENT tu choi (chua gui) ngoai lan khan cap, cho <= 61 s => thu lai sang phut sau. */
    private static boolean guardRetryable(GatewayException e) {
        return e.getKind() == ErrorKind.RATE_LIMIT && e.getHttpStatus() == 0 && e.isDefinitelyNotExecuted()
                && !RateGuard.inEmergencyLane() && e.getRetryAfterMs() > 0L && e.getRetryAfterMs() <= GUARD_RETRY_MAX_WAIT_MS;
    }

    // ------------------------------------------------------------------ ghi nhat ky
    private <T> T call(String api, String sym, String cid, boolean mut, Supplier<T> f) {
        return call(api, sym, cid, mut, null, f);
    }

    /**
     * [3g MAJOR-2] {@code pre} = MOI kiem truoc khi ghi (pham vi, ledger, tran lo, gia, notional...): chay truoc lan gui dau (tu choi =>
     * khong gui, khong CALL_W) VA chay LAI truoc moi lan thu sau GUARD_WAIT_RETRY. Lenh ghi khong co {@code pre} KHONG bao gio duoc thu lai.
     */
    private <T> T call(String api, String sym, String cid, boolean mut, Runnable pre, Supplier<T> f) {
        if (pre != null) runPre(api, sym, cid, pre);
        long t0 = System.nanoTime();
        boolean sent = true;
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("api", api);
        if (sym != null) m.put("symbol", sym);
        if (cid != null) m.put("cid", cid);
        if (mut) {
            mutating.incrementAndGet();
            java.util.function.BiConsumer<String, String> l = cidListener;
            if (l != null && sym != null && cid != null) l.accept(sym, cid);
        }
        try {
            T r;
            try {
                r = f.get();
            } catch (GatewayException e) {
                if (!guardRetryable(e)) throw e;
                if (mut && pre == null) throw e;   // [3g MAJOR-2] khong gui lai lenh ghi tren kiem cu
                long w = Math.min(GUARD_RETRY_MAX_WAIT_MS, e.getRetryAfterMs() + 1_000L);
                j.ev("GUARD_WAIT_RETRY", "api", api, "symbol", sym, "waitMs", w, "why", e.getMessage());
                guardSleep.accept(w);
                if (pre != null) {
                    j.ev("GUARD_RECHECK", "api", api, "symbol", sym, "cid", cid);
                    runPre(api, sym, cid, pre);   // [3g MAJOR-2] kiem LAI sau khi cho (LEGACY co the vua vao symbol)
                }
                r = f.get();
            }
            m.put("ok", true);
            describe(m, r);
            return r;
        } catch (GatewayException e) {
            m.put("ok", false);
            m.put("errKind", e.getKind().name());
            m.put("errCode", e.getExchangeCode());
            m.put("http", e.getHttpStatus());
            m.put("msg", e.getMessage());
            if (e.getKind() == ErrorKind.RATE_LIMIT && e.getHttpStatus() == 0) sent = false;   // [3e] guard client: chua gui
            if (e instanceof GuardException) sent = false;   // [3g] lop canary tu choi khi kiem lai: chua gui
            if (e.getHttpStatus() == 429 || e.getHttpStatus() == 418) rateLimited.incrementAndGet();
            throw e;
        } catch (RuntimeException e) {
            m.put("ok", false);
            m.put("errKind", e.getClass().getSimpleName());
            throw e;
        } finally {
            m.put("latMs", (System.nanoTime() - t0) / 1_000_000L);
            m.put("wOwn", addOwnWeight(sent ? estWeight(api, sym) : 0));   // [3e] weight canary tu goi trong phut (uoc tinh)
            int w = weight.getAsInt();
            if (w >= 0) {
                m.put("w1m", w);
                maxWeight.accumulateAndGet(w, Math::max);
            }
            j.event(mut ? "CALL_W" : "CALL_R", m);
        }
    }

    private static void describe(Map<String, Object> m, Object r) {
        if (r instanceof OrderInfo) {
            OrderInfo o = (OrderInfo) r;
            m.put("status", o.getRawStatus() != null ? o.getRawStatus() : String.valueOf(o.getStatus()));
            m.put("orderId", o.getOrderId());
            if (o.getExecutedQty() != null) m.put("executedQty", o.getExecutedQty().toPlainString());
            if (o.getAvgPrice() != null) m.put("avgPrice", o.getAvgPrice().toPlainString());
            if (o.getStopPrice() != null) m.put("stopPrice", o.getStopPrice().toPlainString());
            if (o.getOrigQty() != null) m.put("origQty", o.getOrigQty().toPlainString());
            m.put("closePosition", o.isClosePosition());
        } else if (r instanceof Optional) {
            Optional<?> o = (Optional<?>) r;
            m.put("present", o.isPresent());
            if (o.isPresent()) describe(m, o.get());
        } else if (r instanceof List) {
            List<?> l = (List<?>) r;
            m.put("n", l.size());
            List<String> items = new ArrayList<>();
            for (Object x : l) {
                if (x instanceof OrderInfo) {
                    OrderInfo o = (OrderInfo) x;
                    items.add(o.getSymbol() + "/" + o.getClientOrderId() + "/" + o.getRawStatus() + "/"
                            + (o.getStopPrice() == null ? "-" : o.getStopPrice().toPlainString()) + (o.isClosePosition() ? "/cp" : ""));
                } else if (x instanceof PositionInfo) {
                    PositionInfo p = (PositionInfo) x;
                    if (p.getPositionAmt() != null && p.getPositionAmt().signum() != 0) {
                        items.add(p.getSymbol() + "/" + p.getPositionAmt().toPlainString() + "@" + p.getEntryPrice() + "/mark="
                                + p.getMarkPrice());
                    }
                }
                if (items.size() >= 20) break;
            }
            if (!items.isEmpty()) m.put("items", items);
        } else if (r instanceof AccountSnapshot) {
            AccountSnapshot a = (AccountSnapshot) r;
            m.put("tmb", a.getTotalMarginBalance() == null ? null : a.getTotalMarginBalance().toPlainString());
            m.put("twb", a.getTotalWalletBalance() == null ? null : a.getTotalWalletBalance().toPlainString());
            List<String> as = new ArrayList<>();
            if (a.getAssets() != null) {
                for (com.binance.chuyennd.c3live.api.AssetBalance b : a.getAssets()) {
                    if (b.getWalletBalance() != null && b.getWalletBalance().signum() != 0) {
                        as.add(b.getAsset() + "=" + b.getWalletBalance().toPlainString());
                    }
                }
            }
            m.put("assets", as);
            m.put("positionsArray", a.getPositions() == null ? "null" : String.valueOf(a.getPositions().size()));
        } else if (r instanceof SymbolConfig) {
            SymbolConfig c = (SymbolConfig) r;
            m.put("marginType", c.getMarginType());
            m.put("leverage", c.getLeverage());
        } else if (r != null && !(r instanceof ExchangeInfo)) {
            m.put("result", String.valueOf(r));
        }
    }

    // ------------------------------------------------------------------ ExchangeGateway
    @Override
    public String name() {
        return "canary(" + d.name() + ")";
    }

    @Override
    public long serverTime() {
        return call("serverTime", null, null, false, d::serverTime);
    }

    @Override
    public ExchangeInfo exchangeInfo() {
        return call("exchangeInfo", null, null, false, d::exchangeInfo);
    }

    @Override
    public OrderInfo newMarketOrder(String symbol, Side side, BigDecimal qty, String clientOrderId, boolean reduceOnly) {
        requireAllowed("newMarketOrder", symbol);
        if (qty == null || qty.signum() <= 0) throw refuse("newMarketOrder", symbol, "qty <= 0");
        boolean open = side == Side.BUY && !reduceOnly;
        if (side == Side.SELL && !reduceOnly) throw refuse("newMarketOrder", symbol, "SELL khong reduceOnly (mo short) bi cam");
        if (side == Side.BUY && reduceOnly) throw refuse("newMarketOrder", symbol, "BUY reduceOnly bi cam (chi long)");
        if (side == Side.BUY) {
            requireCid("newMarketOrder", symbol, clientOrderId, clientOrderId != null && clientOrderId.startsWith(C3LiveCids.ENTRY_PREFIX),
                    C3LiveCids.ENTRY_PREFIX);
        } else {
            requireCid("newMarketOrder", symbol, clientOrderId, clientOrderId != null && clientOrderId.startsWith(C3LiveCids.CLOSE_PREFIX),
                    C3LiveCids.CLOSE_PREFIX);
        }
        Runnable pre = open ? () -> preOpen(symbol, qty) : () -> preSell(symbol, qty);   // [3g MAJOR-2] kiem LAI moi lan thu
        String key = clientOrderId == null ? "?" : clientOrderId;
        OrderInfo o = call("newMarketOrder:" + side + (reduceOnly ? ":RO" : ""), symbol, clientOrderId, true, pre, () -> {
            try {
                OrderInfo r = d.newMarketOrder(symbol, side, qty, clientOrderId, reduceOnly);
                sendsByCid.merge(key, 1, Integer::sum);
                return r;
            } catch (GatewayException e) {
                if (!(e.getKind() == ErrorKind.RATE_LIMIT && e.getHttpStatus() == 0)) sendsByCid.merge(key, 1, Integer::sum);
                throw e;
            } catch (RuntimeException e) {
                sendsByCid.merge(key, 1, Integer::sum);
                throw e;
            }
        });
        notifyExec(symbol, clientOrderId, o);   // [3f] ledger canary (ca khi MO-5 tiem timeout ngay sau)
        if (open && timeoutAfterNextOpen) {
            timeoutAfterNextOpen = false;
            j.ev("INJECT_TIMEOUT", "symbol", symbol, "cid", clientOrderId, "realStatus", String.valueOf(o.getStatus()));
            throw new GatewayException(ErrorKind.TIMEOUT_UNKNOWN_STATE, 0, 0,
                    "canary: TIEM timeout phia client SAU khi san nhan lenh (MO-5)", false, 0L, null);
        }
        return o;
    }

    @Override
    public OrderInfo newStopMarket(String symbol, Side side, BigDecimal qty, BigDecimal stopPrice, String clientOrderId,
                                   boolean reduceOnly) {
        requireAllowed("newStopMarket", symbol);
        requireCid("newStopMarket", symbol, clientOrderId, canaryAlgoCid(clientOrderId), C3LiveCids.STOP_PREFIX);
        if (side != Side.SELL) throw refuse("newStopMarket", symbol, "stop chi SELL (dong long)");
        if (qty != null && !reduceOnly) throw refuse("newStopMarket", symbol, "stop qty bat buoc reduceOnly");
        OrderInfo o = call("newStopMarket" + (qty == null ? ":closePosition" : ":qtyRO"), symbol, clientOrderId, true,
                () -> preStop(symbol, stopPrice), () -> d.newStopMarket(symbol, side, qty, stopPrice, clientOrderId, reduceOnly));
        stopResponses.add(o);
        return o;
    }

    @Override
    public OrderInfo cancelOrder(String symbol, String clientOrderId) {
        requireAllowed("cancelOrder", symbol);
        requireCid("cancelOrder", symbol, clientOrderId, canaryOrderCid(clientOrderId), "c3-/c3x-");
        return call("cancelOrder", symbol, clientOrderId, true, () -> { }, () -> d.cancelOrder(symbol, clientOrderId));   // kiem tinh (cid)
    }

    @Override
    public OrderInfo cancelStop(String symbol, String clientAlgoId) {
        requireAllowed("cancelStop", symbol);
        requireCid("cancelStop", symbol, clientAlgoId, canaryAlgoCid(clientAlgoId), C3LiveCids.STOP_PREFIX);
        return call("cancelStop", symbol, clientAlgoId, true, () -> { }, () -> d.cancelStop(symbol, clientAlgoId));   // kiem tinh (cid)
    }

    @Override
    public Optional<OrderInfo> queryOrderById(String symbol, long orderId) {   // [3h] CHI DOC
        return call("queryOrderById", symbol, Long.toString(orderId), false, () -> d.queryOrderById(symbol, orderId));
    }

    @Override
    public Optional<OrderInfo> queryOrder(String symbol, String clientOrderId) {
        Optional<OrderInfo> r = call("queryOrder", symbol, clientOrderId, false, () -> d.queryOrder(symbol, clientOrderId));
        if (r.isPresent()) notifyExec(symbol, clientOrderId, r.get());
        return r;
    }

    @Override
    public Optional<OrderInfo> queryStop(String symbol, String clientAlgoId) {
        return call("queryStop", symbol, clientAlgoId, false, () -> d.queryStop(symbol, clientAlgoId));
    }

    @Override
    public List<OrderInfo> openOrders(String symbolOrNull) {
        // [3f §ADD-4 A] view cua lop c3_live: CHI 2 symbol canary (doc theo symbol, 1 weight/symbol)
        if (symbolOrNull != null) {
            if (!allowed.contains(symbolOrNull)) return new ArrayList<>();
            return call("openOrders", symbolOrNull, null, false, () -> d.openOrders(symbolOrNull));
        }
        List<OrderInfo> out = new ArrayList<>();
        for (String s : allowed) out.addAll(call("openOrders", s, null, false, () -> d.openOrders(s)));
        return out;
    }

    /** [3f §ADD-4 B/D] CHI DOC toan tai khoan (chon symbol, anh chup LEGACY, lenh canary ngoai pham vi). */
    public List<OrderInfo> openOrdersAll() {
        return call("openOrdersAll", null, null, false, () -> d.openOrders(null));
    }

    @Override
    public List<OrderInfo> openStops(String symbolOrNull) {
        if (symbolOrNull != null) {
            if (!allowed.contains(symbolOrNull)) return new ArrayList<>();
            return call("openStops", symbolOrNull, null, false, () -> d.openStops(symbolOrNull));
        }
        List<OrderInfo> out = new ArrayList<>();
        for (String s : allowed) out.addAll(call("openStops", s, null, false, () -> d.openStops(s)));
        return out;
    }

    /** [3f §ADD-4 B/D] CHI DOC toan tai khoan. */
    public List<OrderInfo> openStopsAll() {
        return call("openStopsAll", null, null, false, () -> d.openStops(null));
    }

    @Override
    public List<PositionInfo> positions() {
        if (failPositions) {
            j.ev("INJECT_READ_ERROR", "api", "positions");
            throw new GatewayException(ErrorKind.OTHER, 0, 0, "canary: TIEM loi doc positionRisk (phia client, K7b)", true, 0L, null);
        }
        return call("positions", null, null, false, () -> scopePositions(d.positions()));   // [3f] view 2 symbol canary
    }

    /** [3f §ADD-4 B/D] CHI DOC toan tai khoan (anh chup LEGACY, chon symbol). */
    public List<PositionInfo> positionsAll() {
        if (failPositions) {
            j.ev("INJECT_READ_ERROR", "api", "positionsAll");
            throw new GatewayException(ErrorKind.OTHER, 0, 0, "canary: TIEM loi doc positionRisk (phia client, K7b)", true, 0L, null);
        }
        return call("positionsAll", null, null, false, d::positions);
    }

    @Override
    public AccountSnapshot account() {
        if (failAccount) {
            j.ev("INJECT_READ_ERROR", "api", "account");
            throw new GatewayException(ErrorKind.OTHER, 0, 0, "canary: TIEM loi doc account (phia client, K7b)", true, 0L, null);
        }
        return call("account", null, null, false, () -> scopeAccount(d.account()));   // [3f] mang positions: 2 symbol canary
    }

    @Override
    public boolean multiAssetsMargin() {
        return call("multiAssetsMargin", null, null, false, d::multiAssetsMargin);
    }

    @Override
    public boolean dualSidePosition() {
        return call("dualSidePosition", null, null, false, d::dualSidePosition);
    }

    @Override
    public void setDualSidePosition(boolean dualSidePosition) {
        // [3f §ADD-4 E] cap tai khoan CHI DOC: khong bao gio goi doi (ke ca ve one-way) — lenh nay KHONG toi san
        throw refuse("setDualSidePosition", null, "§ADD-4 E: cap tai khoan CHI DOC — khong bao gio doi (yeu cau "
                + dualSidePosition + ")");
    }

    @Override
    public SymbolConfig symbolConfig(String symbol) {
        return call("symbolConfig", symbol, null, false, () -> d.symbolConfig(symbol));
    }

    @Override
    public List<SymbolConfig> symbolConfigs() {
        return call("symbolConfigs", null, null, false, d::symbolConfigs);
    }

    @Override
    public int setLeverage(String symbol, int leverage) {
        requireAllowed("setLeverage", symbol);
        if (leverage != CanaryLimits.LEVERAGE) throw refuse("setLeverage", symbol, "chi leverage " + CanaryLimits.LEVERAGE);
        return call("setLeverage", symbol, null, true, () -> requireScopeClean("setLeverage", symbol),
                () -> d.setLeverage(symbol, leverage));
    }

    @Override
    public void setMarginType(String symbol, String marginType) {
        requireAllowed("setMarginType", symbol);
        if (!SymbolConfig.CROSSED.equals(SymbolConfig.normalizeMarginType(marginType))) {
            throw refuse("setMarginType", symbol, "chi CROSSED");
        }
        call("setMarginType", symbol, null, true, () -> requireScopeClean("setMarginType", symbol), () -> {
            d.setMarginType(symbol, marginType);
            return Boolean.TRUE;
        });
    }

    @Override
    public List<Ticker24h> tickers24h(String symbolOrNull) {
        return call("tickers24h", symbolOrNull, null, false, () -> d.tickers24h(symbolOrNull));
    }

    @Override
    public String startUserStream() {
        String k = call("startUserStream", null, null, false, () -> new Redacted(d.startUserStream())).value;
        return k;
    }

    @Override
    public void keepAliveUserStream(String listenKey) {
        call("keepAliveUserStream", null, null, false, () -> {
            d.keepAliveUserStream(listenKey);
            return Boolean.TRUE;
        });
    }

    @Override
    public void closeUserStream(String listenKey) {
        call("closeUserStream", null, null, false, () -> {
            d.closeUserStream(listenKey);
            return Boolean.TRUE;
        });
    }

    /** Boc listenKey de nhat ky chi thay 4 ky tu dau. */
    private static final class Redacted {
        final String value;

        Redacted(String value) {
            this.value = value;
        }

        @Override
        public String toString() {
            return CanaryJournal.redact(value);
        }
    }
}
