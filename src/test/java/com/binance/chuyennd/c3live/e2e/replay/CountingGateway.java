package com.binance.chuyennd.c3live.e2e.replay;

import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.IncomeRecord;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.api.SymbolConfig;
import com.binance.chuyennd.c3live.api.Ticker24h;
import com.binance.chuyennd.c3live.api.TradeFill;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.TreeMap;
import java.util.function.LongSupplier;

/**
 * [E2E_REPLAY X9] Dem weight REST / so lenh cua LOP c3 (dat giua C3ScopedGateway va san tho). Weight = bang W_* cua
 * {@code C3LiveClient} (W_ORDER=1, W_QUERY=1, W_OPEN_SYM=1, W_OPEN_ALL=40, W_POSITION=5, W_ACCOUNT=5, W_MULTI=30, W_DUAL=30,
 * W_SYMCFG=5, W_SET=1, W_LISTEN=1, W_TICKER_SYM=1, W_TICKER_ALL=40, W_TRADES=5, W_INCOME=30, W_TIME=1, W_EXINFO=1).
 */
final class CountingGateway implements ExchangeGateway {

    final ExchangeGateway d;
    final LongSupplier clock;
    final TreeMap<Long, int[]> perMin = new TreeMap<>();      // phut -> [weight, orders]
    final TreeMap<Long, Integer> orders10s = new TreeMap<>();  // o 10 s -> so lenh
    final Map<String, Integer> byMethod = new TreeMap<>();

    CountingGateway(ExchangeGateway d, LongSupplier clock) {
        this.d = d;
        this.clock = clock;
    }

    private synchronized void rec(String m, int w, int o) {
        long t = clock.getAsLong();
        int[] a = perMin.computeIfAbsent(t / 60_000L * 60_000L, k -> new int[2]);
        a[0] += w;
        a[1] += o;
        if (o > 0) orders10s.merge(t / 10_000L * 10_000L, o, Integer::sum);
        byMethod.merge(m, 1, Integer::sum);
    }

    synchronized int maxWeightPerMin() {
        int m = 0;
        for (int[] a : perMin.values()) m = Math.max(m, a[0]);
        return m;
    }

    synchronized long maxWeightMinute() {
        int m = -1;
        long at = 0L;
        for (Map.Entry<Long, int[]> e : perMin.entrySet()) if (e.getValue()[0] > m) { m = e.getValue()[0]; at = e.getKey(); }
        return at;
    }

    synchronized int maxOrders10s() {
        int m = 0;
        for (int v : orders10s.values()) m = Math.max(m, v);
        return m;
    }

    @Override public String name() { return d.name(); }
    @Override public long serverTime() { rec("serverTime", 1, 0); return d.serverTime(); }
    @Override public ExchangeInfo exchangeInfo() { rec("exchangeInfo", 1, 0); return d.exchangeInfo(); }

    @Override
    public OrderInfo newMarketOrder(String symbol, Side side, BigDecimal qty, String cid, boolean reduceOnly) {
        rec("newMarketOrder", 1, 1);
        return d.newMarketOrder(symbol, side, qty, cid, reduceOnly);
    }

    @Override
    public OrderInfo newStopMarket(String symbol, Side side, BigDecimal qty, BigDecimal stopPrice, String cid, boolean reduceOnly) {
        rec("newStopMarket", 1, 1);
        return d.newStopMarket(symbol, side, qty, stopPrice, cid, reduceOnly);
    }

    @Override public OrderInfo cancelOrder(String s, String cid) { rec("cancelOrder", 1, 1); return d.cancelOrder(s, cid); }
    @Override public OrderInfo cancelStop(String s, String cid) { rec("cancelStop", 1, 1); return d.cancelStop(s, cid); }
    @Override public Optional<OrderInfo> queryOrder(String s, String cid) { rec("queryOrder", 1, 0); return d.queryOrder(s, cid); }
    @Override public Optional<OrderInfo> queryOrderById(String s, long id) { rec("queryOrderById", 1, 0); return d.queryOrderById(s, id); }
    @Override public List<TradeFill> userTrades(String s, long id) { rec("userTrades", 5, 0); return d.userTrades(s, id); }
    @Override public Optional<OrderInfo> queryStop(String s, String cid) { rec("queryStop", 1, 0); return d.queryStop(s, cid); }
    @Override public List<OrderInfo> openOrders(String s) { rec("openOrders", s == null ? 40 : 1, 0); return d.openOrders(s); }
    @Override public List<OrderInfo> openStops(String s) { rec("openStops", s == null ? 40 : 1, 0); return d.openStops(s); }
    @Override public List<PositionInfo> positions() { rec("positions", 5, 0); return d.positions(); }
    @Override public AccountSnapshot account() { rec("account", 5, 0); return d.account(); }
    @Override public boolean multiAssetsMargin() { rec("multiAssetsMargin", 30, 0); return d.multiAssetsMargin(); }
    @Override public boolean dualSidePosition() { rec("dualSidePosition", 30, 0); return d.dualSidePosition(); }
    @Override public void setDualSidePosition(boolean v) { rec("setDualSidePosition", 1, 0); d.setDualSidePosition(v); }
    @Override public SymbolConfig symbolConfig(String s) { rec("symbolConfig", 5, 0); return d.symbolConfig(s); }
    @Override public List<SymbolConfig> symbolConfigs() { rec("symbolConfigs", 5, 0); return d.symbolConfigs(); }
    @Override public int setLeverage(String s, int l) { rec("setLeverage", 1, 0); return d.setLeverage(s, l); }
    @Override public void setMarginType(String s, String t) { rec("setMarginType", 1, 0); d.setMarginType(s, t); }
    @Override public List<Ticker24h> tickers24h(String s) { rec("tickers24h", s == null ? 40 : 1, 0); return d.tickers24h(s); }
    @Override public String startUserStream() { rec("startUserStream", 1, 0); return d.startUserStream(); }
    @Override public void keepAliveUserStream(String k) { rec("keepAliveUserStream", 1, 0); d.keepAliveUserStream(k); }
    @Override public void closeUserStream(String k) { rec("closeUserStream", 1, 0); d.closeUserStream(k); }
    @Override public List<IncomeRecord> income(String t, long st, int l) { rec("income", 30, 0); return d.income(t, st, l); }
}
