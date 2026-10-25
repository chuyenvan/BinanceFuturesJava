package com.binance.chuyennd.c3live.mock;

import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.AssetBalance;
import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.OrderKind;
import com.binance.chuyennd.c3live.api.OrderStatus;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.api.SymbolConfig;

import java.math.BigDecimal;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Deque;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

/**
 * [V12 test] San gia lap trong bo nho (ban cai Mock cua ExchangeGateway). Dung cho test C5/C13 va vong 2.
 * - MARKET khop ngay tai {@link #setPrice} (mac dinh 1). - STOP luu NEW. - clientOrderId trung -> OTHER(-4116).
 * - Tiem loi: {@link #failNext(String, GatewayException)} theo ten method.
 * - "Dat lai khong an" (stuck): {@link #stickMarginType}, {@link #stickLeverage}, {@link #stickDualSide}.
 */
public class MockExchangeGateway implements ExchangeGateway {
    public volatile boolean multiAssets = true;
    public volatile boolean dualSide = false;
    public volatile boolean stickDualSide = false;
    public volatile boolean stickMarginType = false;
    public volatile boolean stickLeverage = false;
    public volatile ExchangeInfo exchangeInfo = new ExchangeInfo(0L, Collections.emptyList(), Collections.emptyList());
    public volatile AccountSnapshot accountSnapshot = new AccountSnapshot(new BigDecimal("10000"), new BigDecimal("10000"),
            new BigDecimal("10000"), BigDecimal.ZERO,
            Collections.singletonList(new AssetBalance("BFUSD", new BigDecimal("10000"), new BigDecimal("10000"),
                    new BigDecimal("10000"), BigDecimal.ZERO)), 0L);

    private final Map<String, SymbolConfig> symbolConfigs = new ConcurrentHashMap<>();
    private final Map<String, BigDecimal> prices = new ConcurrentHashMap<>();
    private final Map<String, BigDecimal> positionAmt = new ConcurrentHashMap<>();
    private final Map<String, OrderInfo> orders = new LinkedHashMap<>();
    private final Map<String, OrderInfo> stops = new LinkedHashMap<>();
    private final Map<String, Deque<GatewayException>> failures = new HashMap<>();
    private final Map<String, AtomicInteger> calls = new ConcurrentHashMap<>();
    private final AtomicLong ids = new AtomicLong(1000);
    public volatile long now = 1_700_000_000_000L;

    public void setSymbolConfig(String symbol, String marginType, int leverage) {
        symbolConfigs.put(symbol, new SymbolConfig(symbol, marginType, leverage));
    }

    public void setPrice(String symbol, BigDecimal p) { prices.put(symbol, p); }

    public synchronized void failNext(String method, GatewayException e) {
        failures.computeIfAbsent(method, k -> new ArrayDeque<>()).add(e);
    }

    public int calls(String method) {
        AtomicInteger a = calls.get(method);
        return a == null ? 0 : a.get();
    }

    public int totalCalls() {
        int s = 0;
        for (AtomicInteger a : calls.values()) s += a.get();
        return s;
    }

    private synchronized void enter(String method) {
        calls.computeIfAbsent(method, k -> new AtomicInteger()).incrementAndGet();
        Deque<GatewayException> d = failures.get(method);
        if (d != null && !d.isEmpty()) throw d.poll();
    }

    @Override public String name() { return "mock"; }
    @Override public long serverTime() { enter("serverTime"); return now; }
    @Override public ExchangeInfo exchangeInfo() { enter("exchangeInfo"); return exchangeInfo; }

    @Override
    public synchronized OrderInfo newMarketOrder(String symbol, Side side, BigDecimal qty, String cid, boolean reduceOnly) {
        enter("newMarketOrder");
        if (orders.containsKey(cid)) throw dup();
        BigDecimal px = prices.getOrDefault(symbol, BigDecimal.ONE);
        OrderInfo o = OrderInfo.builder().kind(OrderKind.REGULAR).symbol(symbol).orderId(ids.incrementAndGet())
                .clientOrderId(cid).side(side).type("MARKET").status(OrderStatus.FILLED).rawStatus("FILLED")
                .origQty(qty).executedQty(qty).avgPrice(px).reduceOnly(reduceOnly).updateTimeMs(now).build();
        orders.put(cid, o);
        BigDecimal signed = side == Side.BUY ? qty : qty.negate();
        positionAmt.merge(symbol, signed, BigDecimal::add);
        return o;
    }

    @Override
    public synchronized OrderInfo newStopMarket(String symbol, Side side, BigDecimal qty, BigDecimal stopPrice, String cid,
                                                boolean reduceOnly) {
        enter("newStopMarket");
        if (stops.containsKey(cid)) throw dup();
        OrderInfo o = OrderInfo.builder().kind(OrderKind.ALGO).symbol(symbol).orderId(ids.incrementAndGet())
                .clientOrderId(cid).side(side).type("STOP_MARKET").status(OrderStatus.NEW).rawStatus("NEW")
                .origQty(qty).stopPrice(stopPrice).reduceOnly(qty != null && reduceOnly).closePosition(qty == null)
                .updateTimeMs(now).build();
        stops.put(cid, o);
        return o;
    }

    @Override
    public synchronized OrderInfo cancelOrder(String symbol, String cid) {
        enter("cancelOrder");
        OrderInfo o = orders.get(cid);
        if (o == null || o.getStatus().isFinal()) throw unknown();
        OrderInfo c = o.toBuilder().status(OrderStatus.CANCELED).rawStatus("CANCELED").build();
        orders.put(cid, c);
        return c;
    }

    @Override
    public synchronized OrderInfo cancelStop(String symbol, String cid) {
        enter("cancelStop");
        OrderInfo o = stops.get(cid);
        if (o == null || o.getStatus().isFinal()) throw unknown();
        OrderInfo c = o.toBuilder().status(OrderStatus.CANCELED).rawStatus("CANCELED").build();
        stops.put(cid, c);
        return c;
    }

    @Override
    public synchronized Optional<OrderInfo> queryOrder(String symbol, String cid) {
        enter("queryOrder");
        return Optional.ofNullable(orders.get(cid));
    }

    @Override
    public synchronized Optional<OrderInfo> queryStop(String symbol, String cid) {
        enter("queryStop");
        return Optional.ofNullable(stops.get(cid));
    }

    @Override
    public synchronized List<OrderInfo> openOrders(String symbolOrNull) {
        enter("openOrders");
        return filterOpen(orders, symbolOrNull);
    }

    @Override
    public synchronized List<OrderInfo> openStops(String symbolOrNull) {
        enter("openStops");
        return filterOpen(stops, symbolOrNull);
    }

    private static List<OrderInfo> filterOpen(Map<String, OrderInfo> m, String sym) {
        List<OrderInfo> out = new ArrayList<>();
        for (OrderInfo o : m.values()) {
            if (o.getStatus().isFinal()) continue;
            if (sym == null || sym.equals(o.getSymbol())) out.add(o);
        }
        return out;
    }

    @Override
    public synchronized List<PositionInfo> positions() {
        enter("positions");
        List<PositionInfo> out = new ArrayList<>();
        for (Map.Entry<String, BigDecimal> e : positionAmt.entrySet()) {
            if (e.getValue().signum() == 0) continue;
            BigDecimal px = prices.getOrDefault(e.getKey(), BigDecimal.ONE);
            out.add(new PositionInfo(e.getKey(), "BOTH", e.getValue(), px, px, BigDecimal.ZERO, e.getValue().multiply(px), now));
        }
        return out;
    }

    @Override public AccountSnapshot account() { enter("account"); return accountSnapshot; }
    @Override public boolean multiAssetsMargin() { enter("multiAssetsMargin"); return multiAssets; }
    @Override public boolean dualSidePosition() { enter("dualSidePosition"); return dualSide; }

    @Override
    public void setDualSidePosition(boolean v) {
        enter("setDualSidePosition");
        if (!stickDualSide) dualSide = v;
    }

    @Override
    public SymbolConfig symbolConfig(String symbol) {
        enter("symbolConfig");
        return symbolConfigs.getOrDefault(symbol, new SymbolConfig(symbol, SymbolConfig.CROSSED, 1));
    }

    @Override
    public int setLeverage(String symbol, int leverage) {
        enter("setLeverage");
        SymbolConfig c = symbolConfig0(symbol);
        if (!stickLeverage) symbolConfigs.put(symbol, new SymbolConfig(symbol, c.getMarginType(), leverage));
        return stickLeverage ? c.getLeverage() : leverage;
    }

    @Override
    public void setMarginType(String symbol, String marginType) {
        enter("setMarginType");
        SymbolConfig c = symbolConfig0(symbol);
        if (!stickMarginType) symbolConfigs.put(symbol, new SymbolConfig(symbol, marginType, c.getLeverage()));
    }

    private SymbolConfig symbolConfig0(String symbol) {
        return symbolConfigs.getOrDefault(symbol, new SymbolConfig(symbol, SymbolConfig.CROSSED, 1));
    }

    @Override public String startUserStream() { enter("startUserStream"); return "mockListenKey"; }
    @Override public void keepAliveUserStream(String listenKey) { enter("keepAliveUserStream"); }
    @Override public void closeUserStream(String listenKey) { enter("closeUserStream"); }

    private static GatewayException dup() {
        return new GatewayException(ErrorKind.OTHER, 400, -4116, "ClientOrderId is duplicated (mock)", true, 0L, null);
    }

    private static GatewayException unknown() {
        return new GatewayException(ErrorKind.UNKNOWN_ORDER, 400, -2011, "Unknown order sent (mock)", true, 0L, null);
    }
}
