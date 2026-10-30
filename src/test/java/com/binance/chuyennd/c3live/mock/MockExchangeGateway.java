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
import com.binance.chuyennd.c3live.api.TradeFill;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import java.math.BigDecimal;
import java.math.MathContext;
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
import java.util.function.Consumer;

/**
 * [V12 test] San gia lap trong bo nho (ban cai Mock cua ExchangeGateway). Dung cho test C5/C13 va vong 2.
 * - MARKET khop ngay tai {@link #setPrice} (mac dinh 1). - STOP luu NEW. - clientOrderId trung -> OTHER(-4116).
 * - Tiem loi: {@link #failNext(String, GatewayException)} theo ten method.
 * - "Dat lai khong an" (stuck): {@link #stickMarginType}, {@link #stickLeverage}, {@link #stickDualSide}.
 * [2b] - {@link #triggerStops}: kich STOP SELL co stopPrice >= gia (dong vi the, stop => FINISHED);
 *      {@link #forceClose} (thanh ly/ADL/delist); {@link #rejectSecondClosePosition} (-4130), {@link #rejectWouldTrigger}
 *      (-2021 khi stopPrice >= gia hien tai); moi fill phat su kien JSON dang user stream qua {@link #wsSink}
 *      (ORDER_TRADE_UPDATE + ACCOUNT_UPDATE); phi = {@link #feeRate} x notional (USDT).
 */
public class MockExchangeGateway implements ExchangeGateway {
    public volatile boolean multiAssets = true;
    public volatile boolean dualSide = false;
    public volatile boolean stickDualSide = false;
    public volatile boolean stickMarginType = false;
    public volatile boolean stickLeverage = false;
    public volatile boolean rejectSecondClosePosition = false;
    public volatile boolean rejectWouldTrigger = false;
    /** [V12 3c] tu choi MOI lenh dat stop (test stop bao ve khong dat duoc => dong ngay). */
    public volatile boolean rejectAllStops = false;
    public volatile BigDecimal feeRate = BigDecimal.ZERO;
    public volatile Consumer<String> wsSink = null;
    /**
     * [3j] ACK MARKET tra {@code avgPrice=null} nhu ACK that 10-28 (status FILLED, executedQty > 0, khong co gia);
     * lenh VAN duoc khop ben trong mock (queryOrder van thay gia that).
     */
    public volatile boolean ackWithoutAvgPrice = false;
    /** [3j] ACK FILLED nhung {@code executedQty=0} (R4: khong duoc huy giu cho). */
    public volatile boolean ackExecZero = false;
    /** [3j] queryOrder tra avgPrice=null (doc-sau-ghi chua co gia). */
    public volatile boolean queryOrderWithoutAvgPrice = false;
    /** [3j] userTrades luon rong. */
    public volatile boolean userTradesEmpty = false;
    /** [3j] giu su kien stream lai (phat sau bang {@link #flushEvents()}) — gia lap stream den TRE hon ACK. */
    public volatile boolean holdFillEvents = false;
    /** [3j] ACK tra DUNG OrderInfo nay (tai hien fixture that 10-28); null = ACK tu lenh mock. */
    public volatile OrderInfo ackTemplate = null;
    private final List<String> heldEvents = new ArrayList<>();
    private final Map<Long, List<TradeFill>> trades = new LinkedHashMap<>();
    public volatile ExchangeInfo exchangeInfo = new ExchangeInfo(0L, Collections.emptyList(), Collections.emptyList());
    public volatile AccountSnapshot accountSnapshot = new AccountSnapshot(new BigDecimal("10000"), new BigDecimal("10000"),
            new BigDecimal("10000"), BigDecimal.ZERO,
            Collections.singletonList(new AssetBalance("BFUSD", new BigDecimal("10000"), new BigDecimal("10000"),
                    new BigDecimal("10000"), BigDecimal.ZERO)), 0L);
    /** [2b] true => account() tinh tu von + PnL da chot - phi + PnL chua chot (thay accountSnapshot co dinh). */
    public volatile boolean dynamicAccount = false;
    public volatile BigDecimal startEquity = new BigDecimal("10000");
    private final Map<String, SymbolConfig> symbolConfigs = new ConcurrentHashMap<>();
    private final Map<String, BigDecimal> prices = new ConcurrentHashMap<>();
    private final Map<String, BigDecimal> positionAmt = new ConcurrentHashMap<>();
    private final Map<String, BigDecimal> positionCost = new ConcurrentHashMap<>();
    private final Map<String, OrderInfo> orders = new LinkedHashMap<>();
    private final Map<String, OrderInfo> stops = new LinkedHashMap<>();
    private final Map<String, Deque<GatewayException>> failures = new HashMap<>();
    private final Map<String, AtomicInteger> calls = new ConcurrentHashMap<>();
    private final AtomicLong ids = new AtomicLong(1000);
    private final List<String> callLog = Collections.synchronizedList(new ArrayList<>());
    private BigDecimal realized = BigDecimal.ZERO;
    private BigDecimal fees = BigDecimal.ZERO;
    public volatile long now = 1_700_000_000_000L;

    public void setSymbolConfig(String symbol, String marginType, int leverage) {
        symbolConfigs.put(symbol, new SymbolConfig(symbol, marginType, leverage));
    }

    public void setPrice(String symbol, BigDecimal p) { prices.put(symbol, p); }

    public BigDecimal price(String symbol) { return prices.get(symbol); }

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

    /** [2b] nhat ky goi "method:symbol:cid" theo thu tu (kiem thu tu dat-roi-huy stop). */
    public List<String> callLog() {
        synchronized (callLog) {
            return new ArrayList<>(callLog);
        }
    }

    public BigDecimal position(String symbol) {
        return positionAmt.getOrDefault(symbol, BigDecimal.ZERO);
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
    public OrderInfo newMarketOrder(String symbol, Side side, BigDecimal qty, String cid, boolean reduceOnly) {
        List<String> ev = new ArrayList<>();
        OrderInfo o;
        synchronized (this) {
            enter("newMarketOrder");
            callLog.add("newMarketOrder:" + symbol + ":" + cid);
            if (orders.containsKey(cid)) throw dup();
            BigDecimal px = prices.getOrDefault(symbol, BigDecimal.ONE);
            o = fill(symbol, side, qty, cid, reduceOnly, px, "MARKET", ev);
            if (ackTemplate != null) o = ackTemplate;
            if (ackWithoutAvgPrice) o = o.toBuilder().avgPrice(null).build();
            if (ackExecZero) o = o.toBuilder().executedQty(BigDecimal.ZERO).build();
        }
        emit(ev);
        return o;
    }

    /** [3k R1] Gia lap SU CO: SELL khong giam vi the (san/lenh dong khong an vi the). Chi test. */
    public volatile boolean keepPositionOnSell = false;
    /** [3k R1] Gia lap san TU ket thuc stop closePosition (ALGO_UPDATE X=EXPIRED) ngay sau fill SELL. Chi test. */
    public volatile boolean expireStopsOnSellFill = false;

    /** [3k R1] San TU ket thuc stop (mark EXPIRED + phat ALGO_UPDATE dung caid, KHONG qua API cua bot). */
    public synchronized void exchangeEndStop(String cid, String status) {
        OrderInfo o = stops.get(cid);
        if (o == null) return;
        stops.put(cid, o.toBuilder().status("CANCELED".equals(status) ? OrderStatus.CANCELED : OrderStatus.EXPIRED)
                .rawStatus(status).build());
        emitRaw(algoEvent(o, status, ""));
    }

    private OrderInfo fill(String symbol, Side side, BigDecimal qty, String cid, boolean reduceOnly, BigDecimal px,
                           String origType, List<String> ev) {
        OrderInfo o = OrderInfo.builder().kind(OrderKind.REGULAR).symbol(symbol).orderId(ids.incrementAndGet())
                .clientOrderId(cid).side(side).type("MARKET").status(OrderStatus.FILLED).rawStatus("FILLED")
                .origQty(qty).executedQty(qty).avgPrice(px).reduceOnly(reduceOnly).updateTimeMs(now).build();
        orders.put(cid, o);
        BigDecimal cur = positionAmt.getOrDefault(symbol, BigDecimal.ZERO);
        BigDecimal cost = positionCost.getOrDefault(symbol, BigDecimal.ZERO);
        BigDecimal rp = BigDecimal.ZERO;
        if (side == Side.BUY) {
            positionAmt.put(symbol, cur.add(qty));
            positionCost.put(symbol, cost.add(qty.multiply(px)));
        } else if (!keepPositionOnSell) {
            BigDecimal avg = cur.signum() > 0 ? cost.divide(cur, MathContext.DECIMAL64) : px;
            BigDecimal q = qty.min(cur.max(BigDecimal.ZERO));
            rp = px.subtract(avg).multiply(q);
            realized = realized.add(rp);
            BigDecimal rest = cur.subtract(qty);
            positionAmt.put(symbol, rest);
            positionCost.put(symbol, rest.signum() > 0 ? avg.multiply(rest) : BigDecimal.ZERO);
        }
        BigDecimal fee = qty.multiply(px).multiply(feeRate);
        fees = fees.add(fee);
        List<TradeFill> tr = trades.get(o.getOrderId());
        if (tr == null) {
            tr = new ArrayList<>();
            trades.put(o.getOrderId(), tr);
        }
        tr.add(new TradeFill(symbol, o.getOrderId(), qty, px, now));
        ev.add(orderEvent(symbol, cid, side, origType, o.getOrderId(), qty, px, fee, rp, reduceOnly));
        ev.add(accountEvent(symbol));
        if (side == Side.SELL && expireStopsOnSellFill) {
            for (OrderInfo st : new ArrayList<>(stops.values())) {
                if (st.getStatus().isFinal() || !symbol.equals(st.getSymbol()) || !st.isClosePosition()) continue;
                stops.put(st.getClientOrderId(), st.toBuilder().status(OrderStatus.EXPIRED).rawStatus("EXPIRED").build());
                ev.add(algoEvent(st, "EXPIRED", ""));
            }
        }
        return o;
    }

    @Override
    public synchronized OrderInfo newStopMarket(String symbol, Side side, BigDecimal qty, BigDecimal stopPrice, String cid,
                                                boolean reduceOnly) {
        enter("newStopMarket");
        callLog.add("newStopMarket:" + symbol + ":" + cid);
        if (stops.containsKey(cid)) throw dup();
        if (rejectAllStops) {
            throw new GatewayException(ErrorKind.OTHER, 400, -1000, "stop bi tu choi (mock rejectAllStops)", true, 0L, null);
        }
        if (qty == null && rejectSecondClosePosition) {
            for (OrderInfo s : stops.values()) {
                if (!s.getStatus().isFinal() && s.getSymbol().equals(symbol) && s.isClosePosition() && s.getSide() == side) {
                    throw new GatewayException(ErrorKind.OTHER, 400, -4130,
                            "An open stop or take profit order with GTE and closePosition in the direction is existing (mock)",
                            true, 0L, null);
                }
            }
        }
        if (rejectWouldTrigger && side == Side.SELL) {
            BigDecimal px = prices.get(symbol);
            if (px != null && stopPrice.compareTo(px) >= 0) {
                throw new GatewayException(ErrorKind.OTHER, 400, -2021, "Order would immediately trigger (mock)", true, 0L, null);
            }
        }
        OrderInfo o = OrderInfo.builder().kind(OrderKind.ALGO).symbol(symbol).orderId(ids.incrementAndGet())
                .clientOrderId(cid).side(side).type("STOP_MARKET").status(OrderStatus.NEW).rawStatus("NEW")
                .origQty(qty).stopPrice(stopPrice).reduceOnly(qty != null && reduceOnly).closePosition(qty == null)
                .updateTimeMs(now).build();
        stops.put(cid, o);
        return o;
    }

    /** [2b] Kich stop SELL cua symbol co stopPrice >= gia (dong vi the o gia), stop => FINISHED. Tra so stop kich. */
    public int triggerStops(String symbol, BigDecimal price) {
        List<String> ev = new ArrayList<>();
        int n = 0;
        synchronized (this) {
            prices.put(symbol, price);
            List<OrderInfo> due = new ArrayList<>();
            for (OrderInfo s : stops.values()) {
                if (s.getStatus().isFinal() || !s.getSymbol().equals(symbol) || s.getSide() != Side.SELL) continue;
                if (s.getStopPrice() != null && price.compareTo(s.getStopPrice()) <= 0) due.add(s);
            }
            for (OrderInfo s : due) {
                BigDecimal pos = positionAmt.getOrDefault(symbol, BigDecimal.ZERO);
                BigDecimal q = s.isClosePosition() ? pos : s.getOrigQty().min(pos);
                if (q.signum() <= 0) {
                    stops.put(s.getClientOrderId(), s.toBuilder().status(OrderStatus.EXPIRED).rawStatus("EXPIRED").build());
                    continue;
                }
                // [3g] nhu Algo Service: stop FINISHED mang actualOrderId (lenh thuong sinh ra) + ALGO_UPDATE (ai)
                String fcid = triggeredFillCidPrefix == null ? s.getClientOrderId() : triggeredFillCidPrefix + (ids.get() + 1);
                int at = ev.size();
                OrderInfo fo = fill(symbol, Side.SELL, q, fcid, true, price, "STOP_MARKET", ev);
                String ai = String.valueOf(fo.getOrderId());
                stops.put(s.getClientOrderId(), s.toBuilder().status(OrderStatus.FINISHED).rawStatus("FINISHED").actualOrderId(ai).build());
                String ae = algoEvent(s, "FINISHED", ai);
                if (algoUpdateAfterFill) ev.add(ae); else ev.add(at, ae);
                n++;
            }
        }
        emit(ev);
        return n;
    }

    /** [2b] San dong vi the (thanh ly "autoclose-", ADL "adl_autoclose", delist "settlement_autoclose-"). */
    public void forceClose(String symbol, String cidPrefix, BigDecimal price) {
        List<String> ev = new ArrayList<>();
        synchronized (this) {
            BigDecimal pos = positionAmt.getOrDefault(symbol, BigDecimal.ZERO);
            if (pos.signum() <= 0) return;
            prices.put(symbol, price);
            fill(symbol, Side.SELL, pos, cidPrefix + ids.incrementAndGet(), true, price, "MARKET", ev);
        }
        emit(ev);
    }

    /** [V12 R4] lich su income (FUNDING_FEE) gia lap cho equity c3. */
    public final List<com.binance.chuyennd.c3live.api.IncomeRecord> incomes =
            Collections.synchronizedList(new ArrayList<com.binance.chuyennd.c3live.api.IncomeRecord>());

    @Override
    public List<com.binance.chuyennd.c3live.api.IncomeRecord> income(String incomeType, long startTimeMs, int limit) {
        enter("income");
        List<com.binance.chuyennd.c3live.api.IncomeRecord> out = new ArrayList<>();
        synchronized (incomes) {
            for (com.binance.chuyennd.c3live.api.IncomeRecord r : incomes) {
                if (incomeType != null && !incomeType.equals(r.getIncomeType())) continue;
                if (r.getTimeMs() < startTimeMs) continue;
                out.add(r);
                if (out.size() >= limit) break;
            }
        }
        return out;
    }

    /** [2b] Phat su kien thu cong (vd FUNDING_FEE). */
    public void emitRaw(String json) {
        Consumer<String> s = wsSink;
        if (s != null) s.accept(json);
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
        callLog.add("cancelStop:" + symbol + ":" + cid);
        OrderInfo o = stops.get(cid);
        if (o == null || o.getStatus().isFinal()) throw unknown();
        OrderInfo c = o.toBuilder().status(OrderStatus.CANCELED).rawStatus("CANCELED").build();
        stops.put(cid, c);
        return c;
    }

    @Override
    public synchronized Optional<OrderInfo> queryOrderById(String symbol, long orderId) {   // [3h]
        enter("queryOrderById");
        for (OrderInfo o : orders.values()) if (o.getOrderId() == orderId && symbol.equals(o.getSymbol())) return Optional.of(o);
        return Optional.empty();
    }

    @Override
    public synchronized Optional<OrderInfo> queryOrder(String symbol, String cid) {
        enter("queryOrder");
        OrderInfo o = orders.get(cid);
        if (o != null && queryOrderWithoutAvgPrice) o = o.toBuilder().avgPrice(null).build();
        return Optional.ofNullable(o);
    }

    /** [3j R2(c)] khop that cua 1 lenh theo orderId (mock ghi trong fill). */
    @Override
    public synchronized List<TradeFill> userTrades(String symbol, long orderId) {
        enter("userTrades");
        if (userTradesEmpty) return new ArrayList<>();
        List<TradeFill> l = trades.get(orderId);
        if (l == null) return new ArrayList<>();
        List<TradeFill> out = new ArrayList<>();
        for (TradeFill t : l) if (symbol == null || symbol.equals(t.getSymbol())) out.add(t);
        return out;
    }

    /** [3e] gia lap doc-sau-ghi tre cua GET algoOrder: N lan queryStop dau tien moi cid tra KHONG CO (openStops van thay). */
    public volatile int queryStopLagCalls = 0;
    private final java.util.Map<String, Integer> queryStopMiss = new java.util.HashMap<>();

    @Override
    public synchronized Optional<OrderInfo> queryStop(String symbol, String cid) {
        enter("queryStop");
        OrderInfo o = stops.get(cid);
        if (o != null && queryStopLagCalls > 0) {
            int n = queryStopMiss.merge(cid, 1, Integer::sum);
            if (n <= queryStopLagCalls) return Optional.empty();
        }
        return Optional.ofNullable(o);
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
        if (positionsGlitch) return new ArrayList<>();   // [2d] 200 nhung rong
        List<PositionInfo> out = new ArrayList<>();
        for (Map.Entry<String, BigDecimal> e : positionAmt.entrySet()) {
            if (e.getValue().signum() == 0) continue;
            BigDecimal px = prices.getOrDefault(e.getKey(), BigDecimal.ONE);
            BigDecimal ep = avg(e.getKey(), px);
            out.add(new PositionInfo(e.getKey(), "BOTH", e.getValue(), ep, px, px.subtract(ep).multiply(e.getValue()),
                    e.getValue().multiply(px), now));
        }
        return out;
    }

    private BigDecimal avg(String sym, BigDecimal def) {
        BigDecimal q = positionAmt.getOrDefault(sym, BigDecimal.ZERO);
        BigDecimal c = positionCost.getOrDefault(sym, BigDecimal.ZERO);
        return q.signum() > 0 && c.signum() > 0 ? c.divide(q, MathContext.DECIMAL64) : def;
    }

    /** [3g] cid lenh thuong khi stop kich: null = cid cua stop (c3s-); khac => "<prefix><id>" (san that co the KHONG mang c3s-). */
    public volatile String triggeredFillCidPrefix = null;
    /** [3g] ALGO_UPDATE (FINISHED, ai) phat SAU su kien khop (mac dinh: truoc). */
    public volatile boolean algoUpdateAfterFill = false;

    private String algoEvent(OrderInfo s, String status, String ai) {
        JsonObject o = new JsonObject();
        o.addProperty("caid", s.getClientOrderId());
        o.addProperty("aid", s.getOrderId());
        o.addProperty("at", "CONDITIONAL");
        o.addProperty("o", "STOP_MARKET");
        o.addProperty("s", s.getSymbol());
        o.addProperty("S", "SELL");
        o.addProperty("X", status);
        o.addProperty("ai", ai);
        o.addProperty("cp", s.isClosePosition());
        JsonObject r = new JsonObject();
        r.addProperty("e", "ALGO_UPDATE");
        r.addProperty("T", now);
        r.addProperty("E", now);
        r.add("o", o);
        return r.toString();
    }

    /** [3f] lenh LEGACY dang cho (chua khop) — gia lap lenh tai khoan chinh ngoai canary. */
    public synchronized void addRestingOrder(String symbol, String cid, Side side, BigDecimal qty) {
        orders.put(cid, OrderInfo.builder().kind(OrderKind.REGULAR).symbol(symbol).orderId(ids.incrementAndGet()).clientOrderId(cid)
                .side(side).type("LIMIT").status(OrderStatus.NEW).rawStatus("NEW").origQty(qty).executedQty(BigDecimal.ZERO)
                .updateTimeMs(now).build());
    }

    /** [3f] algo LEGACY dang cho (stop qty reduce-only) — gia lap algo tai khoan chinh ngoai canary. */
    public synchronized void addRestingStop(String symbol, String cid, BigDecimal qty, BigDecimal stopPrice) {
        stops.put(cid, OrderInfo.builder().kind(OrderKind.ALGO).symbol(symbol).orderId(ids.incrementAndGet()).clientOrderId(cid)
                .side(Side.SELL).type("STOP_MARKET").status(OrderStatus.NEW).rawStatus("NEW").origQty(qty).stopPrice(stopPrice)
                .reduceOnly(true).closePosition(false).updateTimeMs(now).build());
    }

    /** [2b] dat vi the truc tiep (test "vi the la" / lech so). */
    public synchronized void setPosition(String symbol, BigDecimal qty, BigDecimal entry) {
        positionAmt.put(symbol, qty);
        positionCost.put(symbol, qty.signum() > 0 ? qty.multiply(entry) : BigDecimal.ZERO);
    }

    /** [2d] positions trong account(): null = san khong tra mang; EMPTY = tra mang rong (glitch); REAL = vi the that. */
    public enum AccountPositions { REAL, EMPTY, NULL }
    public volatile AccountPositions accountPositions = AccountPositions.REAL;
    /** [2d] positionRisk tra 200 nhung RONG (glitch) — giu vi the that ben trong. */
    public volatile boolean positionsGlitch = false;

    private List<PositionInfo> accountPositionList() {
        if (accountPositions == AccountPositions.NULL) return null;
        if (accountPositions == AccountPositions.EMPTY) return Collections.emptyList();
        List<PositionInfo> out = new ArrayList<>();
        for (Map.Entry<String, BigDecimal> e : positionAmt.entrySet()) {
            if (e.getValue().signum() == 0) continue;
            BigDecimal px = prices.getOrDefault(e.getKey(), BigDecimal.ONE);
            out.add(new PositionInfo(e.getKey(), "BOTH", e.getValue(), avg(e.getKey(), px), px, BigDecimal.ZERO,
                    e.getValue().multiply(px), now));
        }
        return out;
    }

    @Override
    public synchronized AccountSnapshot account() {
        enter("account");
        if (!dynamicAccount) {
            AccountSnapshot a = accountSnapshot;
            return new AccountSnapshot(a.getTotalMarginBalance(), a.getTotalWalletBalance(), a.getAvailableBalance(),
                    a.getTotalUnrealizedProfit(), a.getAssets(), a.getTimeMs(), accountPositionList());
        }
        BigDecimal upl = BigDecimal.ZERO;
        for (Map.Entry<String, BigDecimal> e : positionAmt.entrySet()) {
            if (e.getValue().signum() == 0) continue;
            BigDecimal px = prices.getOrDefault(e.getKey(), BigDecimal.ONE);
            upl = upl.add(px.subtract(avg(e.getKey(), px)).multiply(e.getValue()));
        }
        BigDecimal wallet = startEquity.add(realized).subtract(fees);
        BigDecimal m = wallet.add(upl);
        return new AccountSnapshot(m, wallet, m, upl,
                Collections.singletonList(new AssetBalance("BFUSD", wallet, m, m, upl)), now, accountPositionList());
    }

    /** [2b] cong them so du (vd owner chuyen tien) — chi khi dynamicAccount. */
    public synchronized void deposit(BigDecimal usd) {
        startEquity = startEquity.add(usd);
    }

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

    /** [2c MIN-5] moi symbol trong exchangeInfo + symbol da dat cau hinh. */
    @Override
    public synchronized List<SymbolConfig> symbolConfigs() {
        enter("symbolConfigs");
        Map<String, SymbolConfig> m = new java.util.TreeMap<>();
        for (String s : exchangeInfo.getSymbols().keySet()) m.put(s, symbolConfig0(s));
        for (Map.Entry<String, SymbolConfig> e : symbolConfigs.entrySet()) m.put(e.getKey(), e.getValue());
        return new ArrayList<>(m.values());
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

    /** [V12 3] quoteVolume 24h gia lap (luat chon symbol canary); thieu = 0. */
    public final Map<String, BigDecimal> quoteVolumes = new ConcurrentHashMap<>();

    @Override
    public List<com.binance.chuyennd.c3live.api.Ticker24h> tickers24h(String symbolOrNull) {
        enter("tickers24h");
        java.util.Set<String> syms = new java.util.TreeSet<>(prices.keySet());
        syms.addAll(exchangeInfo.getSymbols().keySet());
        List<com.binance.chuyennd.c3live.api.Ticker24h> out = new ArrayList<>();
        for (String s : syms) {
            if (symbolOrNull != null && !symbolOrNull.equals(s)) continue;
            out.add(new com.binance.chuyennd.c3live.api.Ticker24h(s, prices.getOrDefault(s, BigDecimal.ONE),
                    quoteVolumes.getOrDefault(s, BigDecimal.ZERO), now));
        }
        return out;
    }

    private final AtomicInteger listenKeys = new AtomicInteger();

    @Override public String startUserStream() { enter("startUserStream"); return "mockListenKey" + listenKeys.incrementAndGet(); }
    @Override public void keepAliveUserStream(String listenKey) { enter("keepAliveUserStream"); }
    @Override public void closeUserStream(String listenKey) { enter("closeUserStream"); }

    // ------------------------------------------------------------------ su kien dang user stream
    private String orderEvent(String sym, String cid, Side side, String origType, long id, BigDecimal qty, BigDecimal px,
                              BigDecimal fee, BigDecimal rp, boolean reduceOnly) {
        JsonObject o = new JsonObject();
        o.addProperty("s", sym);
        o.addProperty("c", cid);
        o.addProperty("S", side.name());
        o.addProperty("o", "MARKET");
        o.addProperty("ot", origType);
        o.addProperty("x", "TRADE");
        o.addProperty("X", "FILLED");
        o.addProperty("i", id);
        o.addProperty("l", qty.toPlainString());
        o.addProperty("L", px.toPlainString());
        o.addProperty("z", qty.toPlainString());
        o.addProperty("ap", px.toPlainString());
        o.addProperty("n", fee.toPlainString());
        o.addProperty("N", "USDT");
        o.addProperty("rp", rp.toPlainString());
        o.addProperty("R", reduceOnly);
        o.addProperty("T", now);
        JsonObject r = new JsonObject();
        r.addProperty("e", "ORDER_TRADE_UPDATE");
        r.addProperty("E", now);
        r.add("o", o);
        return r.toString();
    }

    private String accountEvent(String sym) {
        JsonObject p = new JsonObject();
        p.addProperty("s", sym);
        p.addProperty("pa", positionAmt.getOrDefault(sym, BigDecimal.ZERO).toPlainString());
        p.addProperty("ep", avg(sym, BigDecimal.ZERO).toPlainString());
        p.addProperty("ps", "BOTH");
        JsonArray ps = new JsonArray();
        ps.add(p);
        JsonObject a = new JsonObject();
        a.addProperty("m", "ORDER");
        a.add("B", new JsonArray());
        a.add("P", ps);
        JsonObject r = new JsonObject();
        r.addProperty("e", "ACCOUNT_UPDATE");
        r.addProperty("E", now);
        r.add("a", a);
        return r.toString();
    }

    private void emit(List<String> ev) {
        Consumer<String> s = wsSink;
        if (s == null) return;
        if (holdFillEvents) {
            synchronized (heldEvents) {
                heldEvents.addAll(ev);
            }
            return;
        }
        for (String e : ev) s.accept(e);
    }

    /** [3j] phat cac su kien stream dang bi giu (holdFillEvents) theo dung thu tu. */
    public void flushEvents() {
        List<String> q;
        synchronized (heldEvents) {
            q = new ArrayList<>(heldEvents);
            heldEvents.clear();
        }
        Consumer<String> s = wsSink;
        if (s == null) return;
        for (String e : q) s.accept(e);
    }

    /** [3j] so su kien stream dang bi giu. */
    public int heldEventCount() {
        synchronized (heldEvents) {
            return heldEvents.size();
        }
    }

    private static GatewayException dup() {
        return new GatewayException(ErrorKind.OTHER, 400, -4116, "ClientOrderId is duplicated (mock)", true, 0L, null);
    }

    private static GatewayException unknown() {
        return new GatewayException(ErrorKind.UNKNOWN_ORDER, 400, -2011, "Unknown order sent (mock)", true, 0L, null);
    }
}
