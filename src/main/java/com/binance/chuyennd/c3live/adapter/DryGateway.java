package com.binance.chuyennd.c3live.adapter;

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
import com.binance.chuyennd.c3live.log.OrderAuditLog;

import java.math.BigDecimal;
import java.math.MathContext;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;
import java.util.function.LongSupplier;
import java.util.function.Supplier;

/**
 * [V12 C12] Adapter {@code LIVE_ADAPTER=dry}: di het duong size/round/clientOrderId/kill-switch cua c3_live nhung KHONG
 * goi mang. Lenh MARKET khop ngay o gia ref (close nen 1m quyet dinh, do duong vao lenh dua vao qua {@code refPrice});
 * STOP_MARKET chi luu (khong bao gio kich hoat). Moi lenh/huy ghi 1 dong {@code [LIVE-DRY]} cung 12 cot
 * {@link OrderAuditLog} nhu {@code [C3-LIVE-ORDER]}. Tai khoan gia: multiAssets=true, one-way, CROSSED, leverage 1,
 * totalMarginBalance = von dry + PnL da chot + PnL chua chot (theo gia ref).
 * exchangeInfo lay tu {@code exchangeInfo} supplier (file dump; khong REST).
 */
public final class DryGateway implements ExchangeGateway {

    private final Supplier<ExchangeInfo> exchangeInfo;
    private final Function<String, BigDecimal> refPrice;
    private final BigDecimal equity;
    private final OrderAuditLog audit;
    private final LongSupplier clock;
    private final Map<String, OrderInfo> orders = new LinkedHashMap<>();
    private final Map<String, OrderInfo> stops = new LinkedHashMap<>();
    private final Map<String, BigDecimal> posQty = new LinkedHashMap<>();
    private final Map<String, BigDecimal> posCost = new LinkedHashMap<>();
    private BigDecimal realized = BigDecimal.ZERO;
    private long ids = 1;

    public DryGateway(Supplier<ExchangeInfo> exchangeInfo, Function<String, BigDecimal> refPrice, BigDecimal equity,
                      OrderAuditLog audit, LongSupplier clock) {
        this.exchangeInfo = exchangeInfo;
        this.refPrice = refPrice;
        this.equity = equity;
        this.audit = audit;
        this.clock = clock;
    }

    @Override public String name() { return "dry"; }

    @Override public long serverTime() { return clock.getAsLong(); }

    @Override
    public ExchangeInfo exchangeInfo() {
        ExchangeInfo ei = exchangeInfo == null ? null : exchangeInfo.get();
        if (ei == null) throw new GatewayException(ErrorKind.OTHER, "dry: chua co exchangeInfo (file dump)", true);
        return ei;
    }

    @Override
    public synchronized OrderInfo newMarketOrder(String symbol, Side side, BigDecimal qty, String cid, boolean reduceOnly) {
        long t = clock.getAsLong();
        BigDecimal px = refPrice == null ? null : refPrice.apply(symbol);
        if (px == null || px.signum() <= 0) {
            rec(t, cid, 0L, symbol, side, "MARKET", qty, null, "REJECTED", "-1", "dry:no_ref_price");
            throw new GatewayException(ErrorKind.FILTER, 400, -1013, "dry: khong co gia ref", true, 0L, null);
        }
        if (qty == null || qty.signum() <= 0) {
            rec(t, cid, 0L, symbol, side, "MARKET", qty, px, "REJECTED", "-1013", "dry:qty");
            throw new GatewayException(ErrorKind.FILTER, 400, -1013, "dry: qty", true, 0L, null);
        }
        BigDecimal cur = posQty.getOrDefault(symbol, BigDecimal.ZERO);
        if (reduceOnly && (side != Side.SELL || cur.compareTo(qty) < 0)) {
            rec(t, cid, 0L, symbol, side, "MARKET", qty, px, "REJECTED", "-2022", "dry:reduce_only");
            throw new GatewayException(ErrorKind.OTHER, 400, -2022, "dry: ReduceOnly rejected", true, 0L, null);
        }
        long id = ids++;
        OrderInfo o = OrderInfo.builder().kind(OrderKind.REGULAR).symbol(symbol).orderId(id).clientOrderId(cid)
                .side(side).type("MARKET").status(OrderStatus.FILLED).rawStatus("FILLED").origQty(qty).executedQty(qty)
                .avgPrice(px).reduceOnly(reduceOnly).updateTimeMs(t).build();
        orders.put(cid, o);
        BigDecimal cost = posCost.getOrDefault(symbol, BigDecimal.ZERO);
        if (side == Side.BUY) {
            posQty.put(symbol, cur.add(qty));
            posCost.put(symbol, cost.add(qty.multiply(px)));
        } else {
            BigDecimal avg = cur.signum() > 0 ? cost.divide(cur, MathContext.DECIMAL64) : px;
            realized = realized.add(px.subtract(avg).multiply(qty));
            BigDecimal rest = cur.subtract(qty);
            posQty.put(symbol, rest);
            posCost.put(symbol, rest.signum() > 0 ? avg.multiply(rest) : BigDecimal.ZERO);
        }
        rec(t, cid, id, symbol, side, "MARKET", qty, px, "FILLED", "", reduceOnly ? "new_reduce_only" : "new");
        return o;
    }

    @Override
    public synchronized OrderInfo newStopMarket(String symbol, Side side, BigDecimal qtyOrNull, BigDecimal stopPrice,
                                                String cid, boolean reduceOnly) {
        long t = clock.getAsLong();
        if (stops.containsKey(cid) && !stops.get(cid).getStatus().isFinal()) {
            throw new GatewayException(ErrorKind.OTHER, 400, -4116, "dry: clientAlgoId trung", true, 0L, null);
        }
        long id = ids++;
        OrderInfo o = OrderInfo.builder().kind(OrderKind.ALGO).symbol(symbol).orderId(id).clientOrderId(cid).side(side)
                .type("STOP_MARKET").status(OrderStatus.NEW).rawStatus("NEW").origQty(qtyOrNull).stopPrice(stopPrice)
                .reduceOnly(qtyOrNull != null && reduceOnly).closePosition(qtyOrNull == null).updateTimeMs(t).build();
        stops.put(cid, o);
        rec(t, cid, id, symbol, side, "STOP_MARKET", qtyOrNull, stopPrice, "NEW", "",
                qtyOrNull == null ? "new_stop_closePosition" : "new_stop");
        return o;
    }

    @Override
    public synchronized OrderInfo cancelOrder(String symbol, String cid) {
        long t = clock.getAsLong();
        OrderInfo o = orders.get(cid);
        if (o == null || o.getStatus().isFinal()) {
            rec(t, cid, 0L, symbol, null, null, null, null, "ERR", "-2011", "cancel");
            throw new GatewayException(ErrorKind.UNKNOWN_ORDER, 400, -2011, "dry: Unknown order", true, 0L, null);
        }
        OrderInfo c = o.toBuilder().status(OrderStatus.CANCELED).rawStatus("CANCELED").build();
        orders.put(cid, c);
        rec(t, cid, c.getOrderId(), symbol, null, c.getType(), null, null, "CANCELED", "", "cancel");
        return c;
    }

    @Override
    public synchronized OrderInfo cancelStop(String symbol, String cid) {
        long t = clock.getAsLong();
        OrderInfo o = stops.get(cid);
        if (o == null || o.getStatus().isFinal()) {
            rec(t, cid, 0L, symbol, null, "STOP_MARKET", null, null, "ERR", "-2011", "cancel_stop");
            throw new GatewayException(ErrorKind.UNKNOWN_ORDER, 400, -2011, "dry: Unknown algo order", true, 0L, null);
        }
        OrderInfo c = o.toBuilder().status(OrderStatus.CANCELED).rawStatus("CANCELED").build();
        stops.put(cid, c);
        rec(t, cid, c.getOrderId(), symbol, null, "STOP_MARKET", null, c.getStopPrice(), "CANCELED", "", "cancel_stop");
        return c;
    }

    @Override
    public synchronized Optional<OrderInfo> queryOrder(String symbol, String cid) {
        return Optional.ofNullable(orders.get(cid));
    }

    @Override
    public synchronized Optional<OrderInfo> queryStop(String symbol, String cid) {
        return Optional.ofNullable(stops.get(cid));
    }

    @Override
    public synchronized List<OrderInfo> openOrders(String symbolOrNull) {
        return open(orders, symbolOrNull);
    }

    @Override
    public synchronized List<OrderInfo> openStops(String symbolOrNull) {
        return open(stops, symbolOrNull);
    }

    private static List<OrderInfo> open(Map<String, OrderInfo> m, String sym) {
        List<OrderInfo> out = new ArrayList<>();
        for (OrderInfo o : m.values()) {
            if (o.getStatus().isFinal()) continue;
            if (sym == null || sym.equals(o.getSymbol())) out.add(o);
        }
        return out;
    }

    @Override
    public synchronized List<PositionInfo> positions() {
        List<PositionInfo> out = new ArrayList<>();
        long t = clock.getAsLong();
        for (Map.Entry<String, BigDecimal> e : posQty.entrySet()) {
            if (e.getValue().signum() == 0) continue;
            BigDecimal q = e.getValue();
            BigDecimal avg = posCost.get(e.getKey()).divide(q, MathContext.DECIMAL64);
            BigDecimal px = mark(e.getKey(), avg);
            out.add(new PositionInfo(e.getKey(), "BOTH", q, avg, px, px.subtract(avg).multiply(q), q.multiply(px), t));
        }
        return out;
    }

    @Override
    public synchronized AccountSnapshot account() {
        BigDecimal upl = BigDecimal.ZERO;
        for (Map.Entry<String, BigDecimal> e : posQty.entrySet()) {
            BigDecimal q = e.getValue();
            if (q.signum() == 0) continue;
            BigDecimal avg = posCost.get(e.getKey()).divide(q, MathContext.DECIMAL64);
            upl = upl.add(mark(e.getKey(), avg).subtract(avg).multiply(q));
        }
        BigDecimal wallet = equity.add(realized);
        BigDecimal margin = wallet.add(upl);
        return new AccountSnapshot(margin, wallet, margin, upl,
                Collections.singletonList(new AssetBalance("DRY", wallet, margin, margin, upl)), clock.getAsLong());
    }

    private BigDecimal mark(String sym, BigDecimal def) {
        BigDecimal p = refPrice == null ? null : refPrice.apply(sym);
        return p == null || p.signum() <= 0 ? def : p;
    }

    @Override public boolean multiAssetsMargin() { return true; }

    @Override public boolean dualSidePosition() { return false; }

    @Override public void setDualSidePosition(boolean dual) { }

    @Override public SymbolConfig symbolConfig(String symbol) { return new SymbolConfig(symbol, SymbolConfig.CROSSED, 1); }

    @Override public int setLeverage(String symbol, int leverage) { return leverage; }

    @Override public void setMarginType(String symbol, String marginType) { }

    @Override public String startUserStream() { return "dry"; }

    @Override public void keepAliveUserStream(String listenKey) { }

    @Override public void closeUserStream(String listenKey) { }

    private void rec(long t, String cid, long orderId, String sym, Side side, String type, BigDecimal qty, BigDecimal px,
                     String status, String err, String reason) {
        audit.record(OrderAuditLog.Entry.of(t).clientOrderId(cid).orderId(orderId).symbol(sym)
                .side(side == null ? null : side.name()).type(type).qty(qty).price(px).status(status).latencyMs(0L)
                .errCode(err).reason(reason));
    }
}
