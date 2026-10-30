package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.IncomeRecord;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.api.SymbolConfig;
import com.binance.chuyennd.c3live.api.Ticker24h;
import com.binance.chuyennd.c3live.api.TradeFill;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.exec.C3LiveCids;
import com.binance.chuyennd.c3live.rate.RateGuard;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Consumer;
import java.util.function.LongConsumer;
import java.util.function.LongSupplier;
import java.util.function.Supplier;

/**
 * [V12 R4 R1/R2/R5] Gateway PHAM VI cua c3_live production tren TAI KHOAN CHINH — moi lop c3 (executor, trailing, flattener,
 * reconciler, guard, equity, mode guard) di qua day.
 * <ul>
 *   <li>DOC: {@code positions()/account()} = view {@link C3Scope#view} (an symbol LEGACY, symbol MERGED = phan c3);
 *       {@code openOrders/openStops} = CHI cid c3. Doc toan tai khoan THO chi qua {@link #positionsAll}/{@link #openOrdersAll}/
 *       {@link #openStopsAll} (CHI DOC, de lam moi LEGACY-busy).</li>
 *   <li>GHI: cid bat buoc c3 ({@code c3-} mo, {@code c3x-} dong, {@code c3s-} stop/huy stop); KHONG BAO GIO cancel/close/modify
 *       thu ngoai pham vi. Lenh MO: kiem LAI ngay truoc gui (trong vong thu, nhu canary 3g/3h): symbol khong MERGED, vi the san
 *       &lt;= qty c3, 0 lenh/algo khong-c3. Lenh DONG: qty &lt;= qty c3. Stop closePosition: cam khi MERGED / san &gt; can tren
 *       c3. Stop qty: reduceOnly + qty &lt;= qty c3. dualSide: luon tu choi (cap tai khoan CHI DOC). leverage/marginType: chi
 *       symbol khong co vi the/lenh/algo ngoai c3.</li>
 *   <li>Rate (R5, chinh sach canary 3i): lenh ghi thuong ngu qua cua so burst TRUOC kiem; guard client tu choi (chua gui) =>
 *       cho &lt;= 61 s roi KIEM LAI va thu 1 lan; pham vi {@link RateGuard.Urgent} khong cho qua han; lan khan cap khong bi
 *       lop nay chan.</li>
 * </ul>
 */
public final class C3ScopedGateway implements ExchangeGateway {

    private static final Logger LOG = LoggerFactory.getLogger(C3ScopedGateway.class);
    public static final long GUARD_RETRY_MAX_WAIT_MS = 61_000L;

    /** Lop pham vi c3 tu choi (CHAC CHAN khong gui len san). */
    public static final class ScopeRefusal extends GatewayException implements com.binance.chuyennd.c3live.api.ClientSideRefusal {
        private static final long serialVersionUID = 1L;

        ScopeRefusal(String msg) {
            super(ErrorKind.OTHER, "C3 SCOPE: " + msg, true);
        }
    }

    private final ExchangeGateway d;
    private final C3Scope scope;
    private final LongSupplier clock;
    private final RateGuard.CanaryPolicy burst;
    private volatile LongConsumer guardSleep = ms -> {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
        }
    };
    /** nghi MERGED (vi the san &gt; c3 khi kiem truoc ghi) => MergedGuard doc xac nhan. */
    private volatile Consumer<String> suspect = s -> { };
    private final AtomicLong refused = new AtomicLong();
    private final AtomicLong writes = new AtomicLong();

    public C3ScopedGateway(ExchangeGateway delegate, C3Scope scope, LongSupplier clock, RateGuard.CanaryPolicy burst) {
        this.d = delegate;
        this.scope = scope;
        this.clock = clock == null ? System::currentTimeMillis : clock;
        this.burst = burst;
    }

    public void setGuardSleep(LongConsumer s) {
        if (s != null) this.guardSleep = s;
    }

    public void setSuspectSink(Consumer<String> s) {
        this.suspect = s == null ? x -> { } : s;
    }

    public ExchangeGateway delegate() {
        return d;
    }

    public C3Scope scope() {
        return scope;
    }

    public long refusedCalls() {
        return refused.get();
    }

    public long writeCalls() {
        return writes.get();
    }

    // ------------------------------------------------------------------ bao ve
    private ScopeRefusal refuse(String api, String sym, String why) {
        refused.incrementAndGet();
        LOG.warn("[C3-LIVE-SCOPE] TU CHOI {} {}: {}", api, sym, why);
        return new ScopeRefusal(api + " " + sym + ": " + why);
    }

    private static boolean guardRetryable(GatewayException e) {
        return !(e instanceof ScopeRefusal) && e.getKind() == ErrorKind.RATE_LIMIT && e.getHttpStatus() == 0
                && e.isDefinitelyNotExecuted() && !RateGuard.inEmergencyLane() && e.getRetryAfterMs() > 0L
                && e.getRetryAfterMs() <= GUARD_RETRY_MAX_WAIT_MS;
    }

    private RuntimeException readFail(String api, String sym, String what, RuntimeException e) {
        if (e instanceof GatewayException && !(e instanceof ScopeRefusal) && guardRetryable((GatewayException) e)) return e;
        return refuse(api, sym, what + " (" + e.getClass().getSimpleName() + ") — fail-closed");
    }

    private boolean pastUrgentDeadline(String api, String sym, long w) {
        long dl = RateGuard.urgentDeadlineMs();
        if (dl == Long.MAX_VALUE) return false;
        long now = clock.getAsLong();
        if (now + w <= dl) return false;
        LOG.warn("[C3-LIVE-SCOPE] {} {}: cho {} ms se qua han Urgent (con {} ms) => loi ngay", api, sym, w, dl - now);
        return true;
    }

    private void burstWait(String api, String sym) {
        RateGuard.CanaryPolicy p = burst;
        if (p == null || RateGuard.inEmergencyLane() || RateGuard.inUrgent()) return;
        long ms = RateGuard.burstDelayMs(clock.getAsLong(), p);
        if (ms <= 0) return;
        LOG.info("[C3-LIVE-SCOPE] {} {}: cua so burst LEGACY => ngu {} ms truoc kiem truoc ghi", api, sym, ms);
        guardSleep.accept(ms);
    }

    private void runPre(String api, String sym, Runnable pre) {
        for (int i = 0; ; i++) {
            try {
                pre.run();
                return;
            } catch (GatewayException e) {
                if (!guardRetryable(e) || i >= 2) throw e;
                long w = Math.min(GUARD_RETRY_MAX_WAIT_MS, e.getRetryAfterMs() + 1_000L);
                if (pastUrgentDeadline(api, sym, w)) throw e;
                LOG.warn("[C3-LIVE-SCOPE] {} {}: doc trong kiem truoc ghi bi guard tu choi => cho {} ms roi kiem lai", api, sym, w);
                guardSleep.accept(w);
            }
        }
    }

    /** Lenh ghi: burst -> kiem -> gui; guard client tu choi (chua gui) => cho, KIEM LAI, thu 1 lan. */
    private <T> T write(String api, String sym, Runnable pre, Supplier<T> f) {
        burstWait(api, sym);
        runPre(api, sym, pre);
        writes.incrementAndGet();
        int waits = 0;
        while (true) {
            try {
                return f.get();
            } catch (GatewayException e) {
                if (!guardRetryable(e) || waits >= 1) throw e;
                long w = Math.min(GUARD_RETRY_MAX_WAIT_MS, e.getRetryAfterMs() + 1_000L);
                if (pastUrgentDeadline(api, sym, w)) throw e;
                waits++;
                LOG.warn("[C3-LIVE-SCOPE] {} {}: guard client tu choi (chua gui) => cho {} ms, kiem lai, thu lai", api, sym, w);
                guardSleep.accept(w);
                runPre(api, sym, pre);
            }
        }
    }

    private BigDecimal rawAmt(String api, String sym) {
        List<PositionInfo> ps;
        try {
            ps = d.positions();
        } catch (RuntimeException e) {
            throw readFail(api, sym, "khong doc duoc vi the", e);
        }
        BigDecimal amt = BigDecimal.ZERO;
        for (PositionInfo p : ps) {
            if (sym.equals(p.getSymbol()) && p.getPositionAmt() != null) amt = amt.add(p.getPositionAmt());
        }
        scope.noteRawAmt(sym, amt);
        return amt;
    }

    private List<String> foreignOn(String api, String sym) {
        List<String> out = new ArrayList<>();
        try {
            for (OrderInfo o : d.openOrders(sym)) if (!C3Scope.isC3OrderCid(o.getClientOrderId())) out.add("lenh " + o.getClientOrderId());
            for (OrderInfo o : d.openStops(sym)) if (!C3Scope.isC3AlgoCid(o.getClientOrderId())) out.add("algo " + o.getClientOrderId());
        } catch (RuntimeException e) {
            throw readFail(api, sym, "khong doc duoc lenh/algo cua symbol", e);
        }
        return out;
    }

    /** [R2] kiem LAI ngay truoc gui lenh MO (chay lai moi lan thu). */
    private void preOpen(String sym) {
        String api = "newMarketOrder";
        if (scope.isMerged(sym)) throw refuse(api, sym, "symbol MERGED — chan mo moi (R2)");
        BigDecimal amt = rawAmt(api, sym);
        BigDecimal mine = scope.c3OpenQty(sym);
        if (amt.signum() < 0 || amt.compareTo(mine.add(C3Scope.EPS)) > 0) {
            scope.markBusy(sym, "kiem truoc mo: san " + amt.toPlainString() + " > c3 " + mine.toPlainString());
            if (scope.held(sym) && mine.signum() > 0) suspect.accept(sym);
            throw refuse(api, sym, "vi the san " + amt.toPlainString() + " > c3 " + mine.toPlainString() + " (LEGACY-busy, R2)");
        }
        List<String> f = foreignOn(api, sym);
        if (!f.isEmpty()) {
            scope.markBusy(sym, "kiem truoc mo: " + f);
            throw refuse(api, sym, "co lenh/algo khong-c3 " + f + " (LEGACY-busy, R2)");
        }
    }

    private void preClose(String sym, BigDecimal qty) {
        BigDecimal mine = scope.c3OpenQty(sym);
        if (qty.compareTo(mine.add(C3Scope.EPS)) > 0) {
            throw refuse("newMarketOrder", sym, "ban " + qty.toPlainString() + " > qty c3 " + mine.toPlainString()
                    + " (khong ban phan ngoai c3)");
        }
    }

    private void preStopClosePosition(String sym) {
        String api = "newStopMarket";
        if (scope.isMerged(sym)) throw refuse(api, sym, "symbol MERGED — cam stop closePosition (R2)");
        BigDecimal amt = rawAmt(api, sym);
        BigDecimal upper = scope.c3UpperQty(sym);
        if (amt.signum() < 0 || amt.compareTo(upper.add(C3Scope.EPS)) > 0) {
            suspect.accept(sym);
            throw refuse(api, sym, "vi the san " + amt.toPlainString() + " > c3 " + upper.toPlainString()
                    + " — stop closePosition se dong ca phan LEGACY (R2)");
        }
    }

    private void preStopQty(String sym, BigDecimal qty) {
        BigDecimal cap;
        if (scope.isMerged(sym)) {
            cap = scope.c3OpenQty(sym);
        } else {
            cap = scope.c3UpperQty(sym);
            Optional<LiveBookC3.ClusterView> c = scopeCluster(sym);
            if (c.isPresent() && c.get().confirmedQty.compareTo(cap) > 0) cap = c.get().confirmedQty;
        }
        if (qty.compareTo(cap.add(C3Scope.EPS)) > 0) {
            throw refuse("newStopMarket", sym, "stop qty " + qty.toPlainString() + " > qty c3 " + cap.toPlainString());
        }
    }

    private Optional<LiveBookC3.ClusterView> scopeCluster(String sym) {
        return bookRef == null ? Optional.<LiveBookC3.ClusterView>empty() : bookRef.cluster(sym);
    }

    private volatile LiveBookC3 bookRef;

    /** So c3 (de kiem qty stop khi khong MERGED). */
    public void setBook(LiveBookC3 b) {
        this.bookRef = b;
    }

    private void preConfig(String api, String sym) {
        BigDecimal amt = rawAmt(api, sym);
        BigDecimal mine = scope.c3OpenQty(sym);
        if (amt.subtract(mine).abs().compareTo(C3Scope.EPS) > 0) {
            throw refuse(api, sym, "symbol co vi the ngoai c3 (san " + amt.toPlainString() + ", c3 " + mine.toPlainString() + ") (R1)");
        }
        List<String> f = foreignOn(api, sym);
        if (!f.isEmpty()) throw refuse(api, sym, "co lenh/algo khong-c3 " + f + " (R1)");
    }

    private void requireCid(String api, String sym, String cid, boolean ok, String want) {
        if (!ok) throw refuse(api, sym, "cid '" + cid + "' khong phai cid c3 " + want + " (R1)");
    }

    // ------------------------------------------------------------------ ExchangeGateway: GHI
    @Override
    public OrderInfo newMarketOrder(String symbol, Side side, BigDecimal qty, String clientOrderId, boolean reduceOnly) {
        if (symbol == null) throw refuse("newMarketOrder", null, "symbol null");
        if (qty == null || qty.signum() <= 0) throw refuse("newMarketOrder", symbol, "qty <= 0");
        if (side == Side.SELL && !reduceOnly) throw refuse("newMarketOrder", symbol, "SELL khong reduceOnly (mo short) bi cam");
        if (side == Side.BUY && reduceOnly) throw refuse("newMarketOrder", symbol, "BUY reduceOnly bi cam (chi long)");
        if (side == Side.BUY) {
            requireCid("newMarketOrder", symbol, clientOrderId, clientOrderId != null
                    && clientOrderId.startsWith(C3LiveCids.ENTRY_PREFIX), C3LiveCids.ENTRY_PREFIX);
            return write("newMarketOrder:BUY", symbol, () -> preOpen(symbol),
                    () -> d.newMarketOrder(symbol, side, qty, clientOrderId, false));
        }
        requireCid("newMarketOrder", symbol, clientOrderId, clientOrderId != null
                && clientOrderId.startsWith(C3LiveCids.CLOSE_PREFIX), C3LiveCids.CLOSE_PREFIX);
        return write("newMarketOrder:SELL:RO", symbol, () -> preClose(symbol, qty),
                () -> d.newMarketOrder(symbol, side, qty, clientOrderId, true));
    }

    @Override
    public OrderInfo newStopMarket(String symbol, Side side, BigDecimal qty, BigDecimal stopPrice, String clientOrderId,
                                   boolean reduceOnly) {
        if (symbol == null) throw refuse("newStopMarket", null, "symbol null");
        requireCid("newStopMarket", symbol, clientOrderId, C3Scope.isC3AlgoCid(clientOrderId), C3LiveCids.STOP_PREFIX);
        if (side != Side.SELL) throw refuse("newStopMarket", symbol, "stop chi SELL (dong long)");
        if (qty != null && !reduceOnly) throw refuse("newStopMarket", symbol, "stop qty bat buoc reduceOnly");
        Runnable pre = qty == null ? () -> preStopClosePosition(symbol) : () -> preStopQty(symbol, qty);
        return write("newStopMarket" + (qty == null ? ":closePosition" : ":qtyRO"), symbol, pre,
                () -> d.newStopMarket(symbol, side, qty, stopPrice, clientOrderId, reduceOnly));
    }

    @Override
    public OrderInfo cancelOrder(String symbol, String clientOrderId) {
        requireCid("cancelOrder", symbol, clientOrderId, C3Scope.isC3OrderCid(clientOrderId), "c3-/c3x-");
        return write("cancelOrder", symbol, () -> { }, () -> d.cancelOrder(symbol, clientOrderId));
    }

    @Override
    public OrderInfo cancelStop(String symbol, String clientAlgoId) {
        requireCid("cancelStop", symbol, clientAlgoId, C3Scope.isC3AlgoCid(clientAlgoId), C3LiveCids.STOP_PREFIX);
        return write("cancelStop", symbol, () -> { }, () -> d.cancelStop(symbol, clientAlgoId));
    }

    @Override
    public void setDualSidePosition(boolean dualSidePosition) {
        throw refuse("setDualSidePosition", null, "cap tai khoan CHI DOC (R1) — khong bao gio doi (yeu cau " + dualSidePosition + ")");
    }

    @Override
    public int setLeverage(String symbol, int leverage) {
        if (symbol == null) throw refuse("setLeverage", null, "symbol null");
        return write("setLeverage", symbol, () -> preConfig("setLeverage", symbol), () -> d.setLeverage(symbol, leverage));
    }

    @Override
    public void setMarginType(String symbol, String marginType) {
        if (symbol == null) throw refuse("setMarginType", null, "symbol null");
        write("setMarginType", symbol, () -> preConfig("setMarginType", symbol), () -> {
            d.setMarginType(symbol, marginType);
            return Boolean.TRUE;
        });
    }

    // ------------------------------------------------------------------ ExchangeGateway: DOC (view)
    @Override
    public String name() {
        return "c3scope(" + d.name() + ")";
    }

    @Override
    public long serverTime() {
        return d.serverTime();
    }

    @Override
    public ExchangeInfo exchangeInfo() {
        return d.exchangeInfo();
    }

    @Override
    public Optional<OrderInfo> queryOrder(String symbol, String clientOrderId) {
        return d.queryOrder(symbol, clientOrderId);
    }

    @Override
    public Optional<OrderInfo> queryOrderById(String symbol, long orderId) {
        return d.queryOrderById(symbol, orderId);
    }

    @Override
    public List<TradeFill> userTrades(String symbol, long orderId) {
        return d.userTrades(symbol, orderId);
    }

    @Override
    public Optional<OrderInfo> queryStop(String symbol, String clientAlgoId) {
        return d.queryStop(symbol, clientAlgoId);
    }

    @Override
    public List<OrderInfo> openOrders(String symbolOrNull) {
        return C3Scope.c3Only(d.openOrders(symbolOrNull));
    }

    @Override
    public List<OrderInfo> openStops(String symbolOrNull) {
        return C3Scope.c3Only(d.openStops(symbolOrNull));
    }

    @Override
    public List<PositionInfo> positions() {
        return scope.view(d.positions());
    }

    @Override
    public AccountSnapshot account() {
        AccountSnapshot a = d.account();
        if (a == null) return null;
        List<PositionInfo> ps = a.getPositions() == null ? null : scope.view(a.getPositions());
        return new AccountSnapshot(a.getTotalMarginBalance(), a.getTotalWalletBalance(), a.getAvailableBalance(),
                a.getTotalUnrealizedProfit(), a.getAssets(), a.getTimeMs(), ps);
    }

    /** CHI DOC toan tai khoan (lam moi LEGACY-busy / phat hien MERGED). */
    public List<PositionInfo> positionsAll() {
        return d.positions();
    }

    /** CHI DOC toan tai khoan. */
    public List<OrderInfo> openOrdersAll() {
        return d.openOrders(null);
    }

    /** CHI DOC toan tai khoan. */
    public List<OrderInfo> openStopsAll() {
        return d.openStops(null);
    }

    /** CHI DOC tai khoan tho (availableBalance / tmb cho kiem an toan ky quy). */
    public AccountSnapshot accountRaw() {
        return d.account();
    }

    @Override
    public boolean multiAssetsMargin() {
        return d.multiAssetsMargin();
    }

    @Override
    public boolean dualSidePosition() {
        return d.dualSidePosition();
    }

    @Override
    public SymbolConfig symbolConfig(String symbol) {
        return d.symbolConfig(symbol);
    }

    @Override
    public List<SymbolConfig> symbolConfigs() {
        return d.symbolConfigs();
    }

    @Override
    public List<Ticker24h> tickers24h(String symbolOrNull) {
        return d.tickers24h(symbolOrNull);
    }

    @Override
    public List<IncomeRecord> income(String incomeType, long startTimeMs, int limit) {
        return d.income(incomeType, startTimeMs, limit);
    }

    @Override
    public String startUserStream() {
        return d.startUserStream();
    }

    @Override
    public void keepAliveUserStream(String listenKey) {
        d.keepAliveUserStream(listenKey);
    }

    @Override
    public void closeUserStream(String listenKey) {
        d.closeUserStream(listenKey);
    }
}
