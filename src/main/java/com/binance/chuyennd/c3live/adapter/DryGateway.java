package com.binance.chuyennd.c3live.adapter;

import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.AssetBalance;
import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.IncomeRecord;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.OrderKind;
import com.binance.chuyennd.c3live.api.OrderStatus;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.api.SymbolConfig;
import com.binance.chuyennd.c3live.api.TradeFill;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.math.BigDecimal;
import java.math.MathContext;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;
import java.util.function.Function;
import java.util.function.LongSupplier;
import java.util.function.Supplier;

/**
 * [V12 C12] Adapter {@code LIVE_ADAPTER=dry}: di het duong size/round/clientOrderId/kill-switch cua c3_live nhung KHONG
 * goi mang. Lenh MARKET MUA khop ngay o gia ref (close nen 1m quyet dinh, do duong vao lenh dua vao qua {@code refPrice});
 * lenh BAN (dong) khop o gia mark gia lap ({@link #onPrices}, = price_realtime nhip exit) neu co, khong thi gia ref.
 * Moi lenh/huy ghi 1 dong {@code [LIVE-DRY]} cung 12 cot {@link OrderAuditLog} nhu {@code [C3-LIVE-ORDER]}. Tai khoan gia:
 * multiAssets=true, one-way, CROSSED, leverage 1, totalMarginBalance = von dry + PnL da chot - phi + PnL chua chot.
 * exchangeInfo lay tu {@code exchangeInfo} supplier (file dump; khong REST).
 *
 * <p>[2b] STOP_MARKET SELL duoc KICH khi gia mark gia lap &lt;= stopPrice ({@link #onPrices}): dong vi the (closePosition
 * = toan bo; qty+reduceOnly = min(qty, vi the)) o gia mark, stop => FINISHED. Moi fill phat su kien JSON cung dang user
 * stream ({@code ORDER_TRADE_UPDATE} + {@code ACCOUNT_UPDATE}) qua {@link #setEventSink} => ke toan C7 chay y nhu live.
 * Phi dry = {@code feeRate} x notional (USDT). Trang thai (vi the, stop mo, lenh, PnL) persist file JSON (neu co) =>
 * restart dry khong mat vi the gia lap.
 */
public final class DryGateway implements ExchangeGateway {

    private static final Logger LOG = LoggerFactory.getLogger(DryGateway.class);
    public static final double DEFAULT_FEE_RATE = 0.0005d;
    static final int MAX_ORDERS_KEPT = 5000;

    private final Supplier<ExchangeInfo> exchangeInfo;
    private final Function<String, BigDecimal> refPrice;
    private final BigDecimal equity;
    private final OrderAuditLog audit;
    private final LongSupplier clock;
    private final File stateFile;
    private final BigDecimal feeRate;
    private final Map<String, OrderInfo> orders = new LinkedHashMap<>();
    private final Map<String, OrderInfo> stops = new LinkedHashMap<>();
    private final Map<String, BigDecimal> posQty = new LinkedHashMap<>();
    private final Map<String, BigDecimal> posCost = new LinkedHashMap<>();
    private final Map<String, BigDecimal> marks = new ConcurrentHashMap<>();
    private BigDecimal realized = BigDecimal.ZERO;
    private BigDecimal fees = BigDecimal.ZERO;
    private long ids = 1;
    private volatile Consumer<String> eventSink = s -> { };

    public DryGateway(Supplier<ExchangeInfo> exchangeInfo, Function<String, BigDecimal> refPrice, BigDecimal equity,
                      OrderAuditLog audit, LongSupplier clock) {
        this(exchangeInfo, refPrice, equity, audit, clock, null, 0d);
    }

    /**
     * @param stateFile file persist trang thai dry (null = chi RAM)
     * @param feeRate   phi taker gia lap (0 = khong phi)
     */
    public DryGateway(Supplier<ExchangeInfo> exchangeInfo, Function<String, BigDecimal> refPrice, BigDecimal equity,
                      OrderAuditLog audit, LongSupplier clock, File stateFile, double feeRate) {
        this.exchangeInfo = exchangeInfo;
        this.refPrice = refPrice;
        this.equity = equity;
        this.audit = audit;
        this.clock = clock;
        this.stateFile = stateFile;
        this.feeRate = BigDecimal.valueOf(Math.max(0d, feeRate));
        load();
    }

    /** [2b] noi ke toan C7 (JSON cung dang user stream). */
    public void setEventSink(Consumer<String> sink) {
        this.eventSink = sink == null ? s -> { } : sink;
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
    public OrderInfo newMarketOrder(String symbol, Side side, BigDecimal qty, String cid, boolean reduceOnly) {
        List<String> ev = new ArrayList<>();
        OrderInfo o;
        synchronized (this) {
            o = market0(symbol, side, qty, cid, reduceOnly, side == Side.BUY ? ref(symbol) : markOrRef(symbol), "MARKET", ev);
            persist();
        }
        emit(ev);
        return o;
    }

    private OrderInfo market0(String symbol, Side side, BigDecimal qty, String cid, boolean reduceOnly, BigDecimal px,
                              String origType, List<String> ev) {
        long t = clock.getAsLong();
        if (px == null || px.signum() <= 0) {
            rec(t, cid, 0L, symbol, side, "MARKET", qty, null, "REJECTED", "-1", "dry:no_ref_price");
            throw new GatewayException(ErrorKind.FILTER, 400, -1013, "dry: khong co gia ref", true, 0L, null);
        }
        if (qty == null || qty.signum() <= 0) {
            rec(t, cid, 0L, symbol, side, "MARKET", qty, px, "REJECTED", "-1013", "dry:qty");
            throw new GatewayException(ErrorKind.FILTER, 400, -1013, "dry: qty", true, 0L, null);
        }
        if (orders.containsKey(cid)) {
            throw new GatewayException(ErrorKind.OTHER, 400, -4116, "dry: clientOrderId trung", true, 0L, null);
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
        trimOrders();
        BigDecimal cost = posCost.getOrDefault(symbol, BigDecimal.ZERO);
        BigDecimal rp = BigDecimal.ZERO;
        BigDecimal avgAfter;
        if (side == Side.BUY) {
            posQty.put(symbol, cur.add(qty));
            posCost.put(symbol, cost.add(qty.multiply(px)));
            avgAfter = posCost.get(symbol).divide(posQty.get(symbol), MathContext.DECIMAL64);
        } else {
            BigDecimal avg = cur.signum() > 0 ? cost.divide(cur, MathContext.DECIMAL64) : px;
            rp = px.subtract(avg).multiply(qty);
            realized = realized.add(rp);
            BigDecimal rest = cur.subtract(qty);
            posQty.put(symbol, rest);
            posCost.put(symbol, rest.signum() > 0 ? avg.multiply(rest) : BigDecimal.ZERO);
            avgAfter = rest.signum() > 0 ? avg : BigDecimal.ZERO;
        }
        BigDecimal fee = qty.multiply(px).multiply(feeRate);
        fees = fees.add(fee);
        rec(t, cid, id, symbol, side, "MARKET", qty, px, "FILLED", "", reduceOnly ? "new_reduce_only" : "new");
        ev.add(orderEvent(t, symbol, cid, side, origType, id, qty, px, fee, rp, reduceOnly));
        ev.add(accountEvent(t, symbol, posQty.get(symbol), avgAfter));
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
        persist();
        return o;
    }

    /**
     * [2b] Gia mark gia lap (price_realtime nhip exit) — cap nhat mark + KICH stop SELL co stopPrice >= gia. Tra so stop
     * da kich.
     */
    public int onPrices(Map<String, Float> prices) {
        if (prices == null || prices.isEmpty()) return 0;
        List<String> ev = new ArrayList<>();
        int n = 0;
        synchronized (this) {
            for (Map.Entry<String, Float> e : prices.entrySet()) {
                if (e.getKey() == null || e.getValue() == null || !(e.getValue() > 0f)) continue;
                marks.put(e.getKey(), new BigDecimal(Float.toString(e.getValue())));
            }
            List<OrderInfo> due = new ArrayList<>();
            for (OrderInfo s : stops.values()) {
                if (s.getStatus().isFinal() || s.getSide() != Side.SELL || s.getStopPrice() == null) continue;
                BigDecimal m = marks.get(s.getSymbol());
                if (m != null && m.compareTo(s.getStopPrice()) <= 0) due.add(s);
            }
            for (OrderInfo s : due) {
                n += trigger(s, ev);
            }
            if (n > 0) persist();
        }
        emit(ev);
        return n;
    }

    private int trigger(OrderInfo s, List<String> ev) {
        long t = clock.getAsLong();
        String sym = s.getSymbol();
        BigDecimal pos = posQty.getOrDefault(sym, BigDecimal.ZERO);
        BigDecimal q = s.isClosePosition() ? pos : (s.getOrigQty() == null ? pos : s.getOrigQty().min(pos));
        if (q.signum() <= 0) {
            stops.put(s.getClientOrderId(), s.toBuilder().status(OrderStatus.EXPIRED).rawStatus("EXPIRED").updateTimeMs(t).build());
            rec(t, s.getClientOrderId(), s.getOrderId(), sym, Side.SELL, "STOP_MARKET", null, s.getStopPrice(), "EXPIRED", "",
                    "stop_no_position");
            return 0;
        }
        BigDecimal px = marks.get(sym);
        stops.put(s.getClientOrderId(), s.toBuilder().status(OrderStatus.FINISHED).rawStatus("FINISHED").updateTimeMs(t).build());
        rec(t, s.getClientOrderId(), s.getOrderId(), sym, Side.SELL, "STOP_MARKET", q, s.getStopPrice(), "TRIGGERED", "",
                "stop_trigger mark=" + px.toPlainString());
        market0(sym, Side.SELL, q, s.getClientOrderId(), true, px, "STOP_MARKET", ev);
        return 1;
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
        persist();
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
        persist();
        return c;
    }

    @Override
    public synchronized Optional<OrderInfo> queryOrder(String symbol, String cid) {
        return Optional.ofNullable(orders.get(cid));
    }

    /** [3j R2(c)] dry: 1 lenh MARKET khop ngay => 1 khop (qty @ avgPrice cua lenh); khong co => list rong. */
    @Override
    public synchronized List<TradeFill> userTrades(String symbol, long orderId) {
        for (OrderInfo o : orders.values()) {
            if (o.getOrderId() != orderId) continue;
            if (!symbol.equals(o.getSymbol())) continue;
            if (o.getExecutedQty() == null || o.getExecutedQty().signum() <= 0) return new ArrayList<>();
            if (o.getAvgPrice() == null || o.getAvgPrice().signum() <= 0) return new ArrayList<>();
            List<TradeFill> out = new ArrayList<>();
            out.add(new TradeFill(o.getSymbol(), orderId, o.getExecutedQty(), o.getAvgPrice(), o.getUpdateTimeMs(), orderId,
                    o.getExecutedQty().multiply(o.getAvgPrice()).multiply(feeRate), "USDT", null));   // [V12 R4f] id = stream "t"
            return out;
        }
        return new ArrayList<>();
    }

    /** [V12 R4] dry: khong gia lap funding => income rong (equity c3 dry = von ao + PnL dry). */
    @Override
    public List<IncomeRecord> income(String incomeType, long startTimeMs, int limit) {
        return new ArrayList<>();
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
        BigDecimal wallet = equity.add(realized).subtract(fees);
        BigDecimal margin = wallet.add(upl);
        return new AccountSnapshot(margin, wallet, margin, upl,
                Collections.singletonList(new AssetBalance("DRY", wallet, margin, margin, upl)), clock.getAsLong(), positions());
    }

    private BigDecimal mark(String sym, BigDecimal def) {
        BigDecimal m = marks.get(sym);
        if (m != null && m.signum() > 0) return m;
        BigDecimal p = refPrice == null ? null : refPrice.apply(sym);
        return p == null || p.signum() <= 0 ? def : p;
    }

    private BigDecimal ref(String sym) {
        return refPrice == null ? null : refPrice.apply(sym);
    }

    private BigDecimal markOrRef(String sym) {
        BigDecimal m = marks.get(sym);
        return m != null && m.signum() > 0 ? m : ref(sym);
    }

    @Override public boolean multiAssetsMargin() { return true; }
    @Override public boolean dualSidePosition() { return false; }
    @Override public void setDualSidePosition(boolean dual) { }
    @Override public SymbolConfig symbolConfig(String symbol) { return new SymbolConfig(symbol, SymbolConfig.CROSSED, 1); }

    /** [2c MIN-5] dry: moi symbol trong exchangeInfo = CROSSED 1x (khong goi san). */
    @Override
    public List<SymbolConfig> symbolConfigs() {
        List<SymbolConfig> out = new ArrayList<>();
        ExchangeInfo ei = exchangeInfo();
        if (ei != null) for (String s : ei.getSymbols().keySet()) out.add(new SymbolConfig(s, SymbolConfig.CROSSED, 1));
        return out;
    }
    @Override public int setLeverage(String symbol, int leverage) { return leverage; }
    @Override public void setMarginType(String symbol, String marginType) { }
    @Override public String startUserStream() { return "dry"; }
    @Override public void keepAliveUserStream(String listenKey) { }
    @Override public void closeUserStream(String listenKey) { }

    // ------------------------------------------------------------------ su kien (dang user stream)
    private static String orderEvent(long t, String sym, String cid, Side side, String origType, long id, BigDecimal qty,
                                     BigDecimal px, BigDecimal fee, BigDecimal rp, boolean reduceOnly) {
        JsonObject o = new JsonObject();
        o.addProperty("s", sym);
        o.addProperty("c", cid);
        o.addProperty("S", side.name());
        o.addProperty("o", "MARKET");
        o.addProperty("ot", origType);
        o.addProperty("x", "TRADE");
        o.addProperty("X", "FILLED");
        o.addProperty("i", id);
        o.addProperty("t", id);   // [V12 R4f] dry: 1 khop / lenh => tradeId = orderId (= userTrades id)
        o.addProperty("q", qty.toPlainString());
        o.addProperty("l", qty.toPlainString());
        o.addProperty("L", px.toPlainString());
        o.addProperty("z", qty.toPlainString());
        o.addProperty("ap", px.toPlainString());
        o.addProperty("n", fee.toPlainString());
        o.addProperty("N", "USDT");
        o.addProperty("rp", rp.toPlainString());
        o.addProperty("R", reduceOnly);
        o.addProperty("T", t);
        JsonObject root = new JsonObject();
        root.addProperty("e", "ORDER_TRADE_UPDATE");
        root.addProperty("E", t);
        root.addProperty("T", t);
        root.add("o", o);
        return root.toString();
    }

    private static String accountEvent(long t, String sym, BigDecimal pa, BigDecimal ep) {
        JsonObject p = new JsonObject();
        p.addProperty("s", sym);
        p.addProperty("pa", (pa == null ? BigDecimal.ZERO : pa).toPlainString());
        p.addProperty("ep", (ep == null ? BigDecimal.ZERO : ep).toPlainString());
        p.addProperty("ps", "BOTH");
        JsonArray ps = new JsonArray();
        ps.add(p);
        JsonObject a = new JsonObject();
        a.addProperty("m", "ORDER");
        a.add("B", new JsonArray());
        a.add("P", ps);
        JsonObject root = new JsonObject();
        root.addProperty("e", "ACCOUNT_UPDATE");
        root.addProperty("E", t);
        root.addProperty("T", t);
        root.add("a", a);
        return root.toString();
    }

    private void emit(List<String> ev) {
        Consumer<String> s = eventSink;
        for (String e : ev) {
            try {
                s.accept(e);
            } catch (Throwable t) {
                LOG.warn("[LIVE-DRY] loi xu ly su kien dry: {}", t.toString());
            }
        }
    }

    private void rec(long t, String cid, long orderId, String sym, Side side, String type, BigDecimal qty, BigDecimal px,
                     String status, String err, String reason) {
        audit.record(OrderAuditLog.Entry.of(t).clientOrderId(cid).orderId(orderId).symbol(sym)
                .side(side == null ? null : side.name()).type(type).qty(qty).price(px).status(status).latencyMs(0L)
                .errCode(err).reason(reason));
    }

    private void trimOrders() {
        if (orders.size() <= MAX_ORDERS_KEPT) return;
        Iterator<Map.Entry<String, OrderInfo>> it = orders.entrySet().iterator();
        while (orders.size() > MAX_ORDERS_KEPT && it.hasNext()) {
            it.next();
            it.remove();
        }
    }

    // ------------------------------------------------------------------ persist (chi dry)
    private void persist() {
        if (stateFile == null) return;
        try {
            JsonObject root = new JsonObject();
            root.addProperty("version", 1);
            root.addProperty("ids", ids);
            root.addProperty("realized", realized.toPlainString());
            root.addProperty("fees", fees.toPlainString());
            JsonArray pos = new JsonArray();
            for (Map.Entry<String, BigDecimal> e : posQty.entrySet()) {
                if (e.getValue().signum() == 0) continue;
                JsonObject p = new JsonObject();
                p.addProperty("s", e.getKey());
                p.addProperty("q", e.getValue().toPlainString());
                p.addProperty("cost", posCost.getOrDefault(e.getKey(), BigDecimal.ZERO).toPlainString());
                pos.add(p);
            }
            root.add("positions", pos);
            root.add("stops", toJson(stops, true));
            root.add("orders", toJson(orders, false));
            File abs = stateFile.getAbsoluteFile();
            File dir = abs.getParentFile();
            if (dir != null && !dir.exists()) dir.mkdirs();
            File tmp = new File(abs.getPath() + ".tmp");
            Files.write(tmp.toPath(), root.toString().getBytes(StandardCharsets.UTF_8));
            Files.move(tmp.toPath(), abs.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (Exception e) {
            LOG.warn("[LIVE-DRY] khong ghi duoc trang thai dry {}: {}", stateFile.getPath(), e.toString());
        }
    }

    private static JsonArray toJson(Map<String, OrderInfo> m, boolean openOnly) {
        JsonArray a = new JsonArray();
        for (OrderInfo o : m.values()) {
            if (openOnly && o.getStatus().isFinal()) continue;
            JsonObject j = new JsonObject();
            j.addProperty("kind", o.getKind().name());
            j.addProperty("s", o.getSymbol());
            j.addProperty("id", o.getOrderId());
            j.addProperty("c", o.getClientOrderId());
            j.addProperty("side", o.getSide() == null ? "" : o.getSide().name());
            j.addProperty("type", o.getType());
            j.addProperty("status", o.getStatus().name());
            if (o.getOrigQty() != null) j.addProperty("q", o.getOrigQty().toPlainString());
            if (o.getExecutedQty() != null) j.addProperty("z", o.getExecutedQty().toPlainString());
            if (o.getAvgPrice() != null) j.addProperty("ap", o.getAvgPrice().toPlainString());
            if (o.getStopPrice() != null) j.addProperty("sp", o.getStopPrice().toPlainString());
            j.addProperty("ro", o.isReduceOnly());
            j.addProperty("cp", o.isClosePosition());
            j.addProperty("t", o.getUpdateTimeMs());
            a.add(j);
        }
        return a;
    }

    private void load() {
        if (stateFile == null || !stateFile.exists()) return;
        try {
            JsonObject root = JsonParser.parseString(new String(Files.readAllBytes(stateFile.toPath()),
                    StandardCharsets.UTF_8)).getAsJsonObject();
            ids = root.get("ids").getAsLong();
            realized = new BigDecimal(root.get("realized").getAsString());
            fees = root.has("fees") ? new BigDecimal(root.get("fees").getAsString()) : BigDecimal.ZERO;
            for (JsonElement e : root.getAsJsonArray("positions")) {
                JsonObject p = e.getAsJsonObject();
                posQty.put(p.get("s").getAsString(), new BigDecimal(p.get("q").getAsString()));
                posCost.put(p.get("s").getAsString(), new BigDecimal(p.get("cost").getAsString()));
            }
            for (JsonElement e : root.getAsJsonArray("stops")) {
                OrderInfo o = fromJson(e.getAsJsonObject());
                stops.put(o.getClientOrderId(), o);
            }
            for (JsonElement e : root.getAsJsonArray("orders")) {
                OrderInfo o = fromJson(e.getAsJsonObject());
                orders.put(o.getClientOrderId(), o);
            }
            LOG.warn("[LIVE-DRY] nap trang thai dry {}: {} vi the, {} stop mo, {} lenh", stateFile.getPath(), posQty.size(),
                    stops.size(), orders.size());
        } catch (Exception e) {
            LOG.error("[LIVE-DRY] trang thai dry {} hong ({}) => bat dau trong", stateFile.getPath(), e.toString());
            posQty.clear();
            posCost.clear();
            stops.clear();
            orders.clear();
        }
    }

    private static OrderInfo fromJson(JsonObject j) {
        OrderInfo.Builder b = OrderInfo.builder().kind(OrderKind.valueOf(j.get("kind").getAsString()))
                .symbol(j.get("s").getAsString()).orderId(j.get("id").getAsLong()).clientOrderId(j.get("c").getAsString())
                .type(j.get("type").getAsString()).status(OrderStatus.valueOf(j.get("status").getAsString()))
                .rawStatus(j.get("status").getAsString()).reduceOnly(j.get("ro").getAsBoolean())
                .closePosition(j.get("cp").getAsBoolean()).updateTimeMs(j.get("t").getAsLong());
        String side = j.get("side").getAsString();
        if (!side.isEmpty()) b.side(Side.valueOf(side));
        if (j.has("q")) b.origQty(new BigDecimal(j.get("q").getAsString()));
        if (j.has("z")) b.executedQty(new BigDecimal(j.get("z").getAsString()));
        if (j.has("ap")) b.avgPrice(new BigDecimal(j.get("ap").getAsString()));
        if (j.has("sp")) b.stopPrice(new BigDecimal(j.get("sp").getAsString()));
        return b.build();
    }
}
