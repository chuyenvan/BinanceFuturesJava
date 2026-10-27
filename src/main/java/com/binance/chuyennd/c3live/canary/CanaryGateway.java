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
            throw refuse("newMarketOrder", sym, "khong doc duoc vi the (" + e.getClass().getSimpleName() + ")");
        }
        BigDecimal sum = BigDecimal.ZERO;
        for (PositionInfo p : ps) {
            if (p.getPositionAmt() == null || p.getPositionAmt().signum() == 0) continue;
            if (!allowed.contains(p.getSymbol())) throw refuse("newMarketOrder", sym, "tai khoan co vi the symbol khac " + p.getSymbol());
            BigDecimal px = p.getMarkPrice() != null && p.getMarkPrice().signum() > 0 ? p.getMarkPrice() : p.getEntryPrice();
            BigDecimal n = p.getNotional() != null && p.getNotional().signum() != 0 ? p.getNotional().abs()
                    : p.getPositionAmt().abs().multiply(px == null ? BigDecimal.ZERO : px);
            sum = sum.add(n);
        }
        return sum;
    }

    // ------------------------------------------------------------------ ghi nhat ky
    private <T> T call(String api, String sym, String cid, boolean mut, Supplier<T> f) {
        long t0 = System.nanoTime();
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
            T r = f.get();
            m.put("ok", true);
            describe(m, r);
            return r;
        } catch (GatewayException e) {
            m.put("ok", false);
            m.put("errKind", e.getKind().name());
            m.put("errCode", e.getExchangeCode());
            m.put("http", e.getHttpStatus());
            m.put("msg", e.getMessage());
            if (e.getHttpStatus() == 429 || e.getHttpStatus() == 418) rateLimited.incrementAndGet();
            throw e;
        } catch (RuntimeException e) {
            m.put("ok", false);
            m.put("errKind", e.getClass().getSimpleName());
            throw e;
        } finally {
            m.put("latMs", (System.nanoTime() - t0) / 1_000_000L);
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
        if (open) {
            if (lossCapHit.getAsBoolean()) throw refuse("newMarketOrder", symbol, "da cham tran lo " + CanaryLimits.LOSS_CAP_USDT + " USDT");
            BigDecimal px = freshPrice(symbol);
            BigDecimal notional = qty.multiply(px);
            if (notional.compareTo(CanaryLimits.MAX_ORDER_NOTIONAL_USDT) > 0) {
                throw refuse("newMarketOrder", symbol, "notional " + notional.toPlainString() + " > " + CanaryLimits.MAX_ORDER_NOTIONAL_USDT);
            }
            BigDecimal openNow = openNotional(symbol);
            if (openNow.add(notional).compareTo(CanaryLimits.MAX_OPEN_NOTIONAL_USDT) > 0) {
                throw refuse("newMarketOrder", symbol, "tong mo " + openNow.add(notional).toPlainString() + " > "
                        + CanaryLimits.MAX_OPEN_NOTIONAL_USDT);
            }
        }
        sendsByCid.merge(clientOrderId == null ? "?" : clientOrderId, 1, Integer::sum);
        OrderInfo o = call("newMarketOrder:" + side + (reduceOnly ? ":RO" : ""), symbol, clientOrderId, true,
                () -> d.newMarketOrder(symbol, side, qty, clientOrderId, reduceOnly));
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
        if (side != Side.SELL) throw refuse("newStopMarket", symbol, "stop chi SELL (dong long)");
        if (qty != null && !reduceOnly) throw refuse("newStopMarket", symbol, "stop qty bat buoc reduceOnly");
        // [3c MAJ-C1] stop KHONG BAO GIO xa hon -4,5 % so gia vao (vi the doc tu san, khong qua tiem loi)
        BigDecimal entry = entryPrice(symbol);
        if (entry != null && stopPrice != null) {
            BigDecimal floor = entry.multiply(BigDecimal.valueOf(1d - CanaryLimits.MAX_STOP_DIST - CanaryLimits.STOP_ROUND_TOL));
            if (stopPrice.compareTo(floor) < 0) {
                throw refuse("newStopMarket", symbol, "stop " + stopPrice.toPlainString() + " thap hon entry " + entry.toPlainString()
                        + " x (1 - " + CanaryLimits.MAX_STOP_DIST + ") — tran lo giua 2 JVM (§ADD-2)");
            }
        }
        OrderInfo o = call("newStopMarket" + (qty == null ? ":closePosition" : ":qtyRO"), symbol, clientOrderId, true,
                () -> d.newStopMarket(symbol, side, qty, stopPrice, clientOrderId, reduceOnly));
        stopResponses.add(o);
        return o;
    }

    @Override
    public OrderInfo cancelOrder(String symbol, String clientOrderId) {
        requireAllowed("cancelOrder", symbol);
        return call("cancelOrder", symbol, clientOrderId, true, () -> d.cancelOrder(symbol, clientOrderId));
    }

    @Override
    public OrderInfo cancelStop(String symbol, String clientAlgoId) {
        requireAllowed("cancelStop", symbol);
        return call("cancelStop", symbol, clientAlgoId, true, () -> d.cancelStop(symbol, clientAlgoId));
    }

    @Override
    public Optional<OrderInfo> queryOrder(String symbol, String clientOrderId) {
        return call("queryOrder", symbol, clientOrderId, false, () -> d.queryOrder(symbol, clientOrderId));
    }

    @Override
    public Optional<OrderInfo> queryStop(String symbol, String clientAlgoId) {
        return call("queryStop", symbol, clientAlgoId, false, () -> d.queryStop(symbol, clientAlgoId));
    }

    @Override
    public List<OrderInfo> openOrders(String symbolOrNull) {
        return call("openOrders", symbolOrNull, null, false, () -> d.openOrders(symbolOrNull));
    }

    @Override
    public List<OrderInfo> openStops(String symbolOrNull) {
        return call("openStops", symbolOrNull, null, false, () -> d.openStops(symbolOrNull));
    }

    @Override
    public List<PositionInfo> positions() {
        if (failPositions) {
            j.ev("INJECT_READ_ERROR", "api", "positions");
            throw new GatewayException(ErrorKind.OTHER, 0, 0, "canary: TIEM loi doc positionRisk (phia client, K7b)", true, 0L, null);
        }
        return call("positions", null, null, false, d::positions);
    }

    @Override
    public AccountSnapshot account() {
        if (failAccount) {
            j.ev("INJECT_READ_ERROR", "api", "account");
            throw new GatewayException(ErrorKind.OTHER, 0, 0, "canary: TIEM loi doc account (phia client, K7b)", true, 0L, null);
        }
        return call("account", null, null, false, d::account);
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
        if (dualSidePosition) throw refuse("setDualSidePosition", null, "chi cho phep one-way (false)");
        call("setDualSidePosition", null, null, true, () -> {
            d.setDualSidePosition(false);
            return Boolean.TRUE;
        });
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
        return call("setLeverage", symbol, null, true, () -> d.setLeverage(symbol, leverage));
    }

    @Override
    public void setMarginType(String symbol, String marginType) {
        requireAllowed("setMarginType", symbol);
        if (!SymbolConfig.CROSSED.equals(SymbolConfig.normalizeMarginType(marginType))) {
            throw refuse("setMarginType", symbol, "chi CROSSED");
        }
        call("setMarginType", symbol, null, true, () -> {
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
