package com.binance.chuyennd.c3live.client;

import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.AssetBalance;
import com.binance.chuyennd.c3live.api.ClientOrderIds;
import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.ExchangeInfoParser;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.OrderKind;
import com.binance.chuyennd.c3live.api.OrderStatus;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.api.SymbolConfig;
import com.binance.chuyennd.c3live.api.Ticker24h;
import com.binance.chuyennd.c3live.api.TradeFill;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.rate.RateGuard;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.math.BigDecimal;
import java.net.ConnectException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpConnectTimeoutException;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;

/**
 * [V12 C2] Client REST rieng cho TAI KHOAN CON c3_live (ban cai Live cua {@link ExchangeGateway}).
 * <ul>
 *   <li>Key doc tu file root-only ({@link C3LiveKeys}); KHONG dung PrivateConfig / ClientSingleton / BinanceFuturesClientSingleton.</li>
 *   <li>Ky HMAC-SHA256 tren query string da percent-encode UTF-8 (symbol non-ASCII an toan); moi tham so di trong query.</li>
 *   <li>java.net.http, connect/request timeout, recvWindow, dong bo gio server (dinh ky + khi -1021).</li>
 *   <li>Moi call qua {@link RateGuard} (chung 1 instance); header X-MBX-USED-WEIGHT-1M / ORDER-COUNT -> RateGuard.</li>
 *   <li>Moi loi -> {@link GatewayException}/{@link ErrorKind} qua {@link ErrorMapper}.</li>
 *   <li>Lenh moi / huy -> 1 dong [C3-LIVE-ORDER] ({@link OrderAuditLog}). Khong bao gio log key / secret / signature /
 *       query / listenKey.</li>
 * </ul>
 * Weight endpoint (CHUA XAC MINH lai voi tai lieu tai thoi diem code; dung so bao thu): xem hang W_*.
 */
public final class C3LiveClient implements ExchangeGateway {
    private static final Logger LOG = LoggerFactory.getLogger(C3LiveClient.class);
    static final String H_APIKEY = "X-MBX-APIKEY";

    static final int W_TIME = 1, W_EXINFO = 1, W_ORDER = 1, W_QUERY = 1, W_OPEN_SYM = 1, W_OPEN_ALL = 40,
            W_POSITION = 5, W_ACCOUNT = 5, W_MULTI = 30, W_DUAL = 30, W_SYMCFG = 5, W_SET = 1, W_LISTEN = 1,
            W_TICKER_SYM = 1, W_TICKER_ALL = 40, W_TRADES = 5;
    /** [3i] dang trong 1 call GHI cua luong nay: GET long ben trong (dong bo gio) KHONG ngu burst / cho => kiem truoc ghi -> gui lien nhau. */
    private static final ThreadLocal<int[]> IN_WRITE = ThreadLocal.withInitial(() -> new int[1]);

    private enum Sec { NONE, API_KEY, SIGNED }

    private final C3LiveClientConfig cfg;
    private final String apiKey;
    private final HmacSigner signer;
    private final HttpClient http;
    private final RateGuard rate;
    private final OrderAuditLog audit;
    private volatile long timeOffsetMs;
    private volatile long lastSyncLocalMs;
    private final AtomicLong timeSyncCount = new AtomicLong();

    /**
     * Cach DUY NHAT tao client cho production: nap key tu cfg.keysFile() (kiem 600 + owner). Loi -> C3LiveKeyException,
     * KHONG co client -> c3_live phai tu choi bat push.
     */
    public static C3LiveClient create(C3LiveClientConfig cfg, RateGuard rate) throws C3LiveKeyException {
        Objects.requireNonNull(cfg, "cfg");
        C3LiveKeys keys = C3LiveKeys.load(cfg.keysFile(), cfg.keysOwner());
        return new C3LiveClient(cfg, keys, rate, OrderAuditLog.live());
    }

    C3LiveClient(C3LiveClientConfig cfg, C3LiveKeys keys, RateGuard rate, OrderAuditLog audit) {
        this.cfg = Objects.requireNonNull(cfg, "cfg");
        Objects.requireNonNull(keys, "keys");
        this.apiKey = keys.apiKey();
        this.signer = new HmacSigner(keys.secret());
        this.rate = rate == null ? RateGuard.defaults() : rate;
        this.audit = audit == null ? OrderAuditLog.live() : audit;
        this.http = HttpClient.newBuilder().connectTimeout(Duration.ofMillis(cfg.connectTimeoutMs()))
                .followRedirects(HttpClient.Redirect.NEVER).build();
        LOG.info("[C3-LIVE] client san sang base={} recvWindow={} (key nap tu file, khong in)", cfg.baseUrl(), cfg.recvWindowMs());
    }

    public RateGuard rateGuard() { return rate; }
    public long timeOffsetMs() { return timeOffsetMs; }
    public long timeSyncCount() { return timeSyncCount.get(); }

    @Override
    public String name() { return "live"; }

    @Override
    public String toString() { return "C3LiveClient[" + cfg.baseUrl() + "]"; }

    // ------------------------------------------------------------------ time

    /** Dong bo offset = serverTime - trung diem RTT. */
    public synchronized long syncTime() {
        long t0 = System.currentTimeMillis();
        JsonElement j = call("GET", "/fapi/v1/time", new LinkedHashMap<>(), Sec.NONE, W_TIME, 0);
        long t1 = System.currentTimeMillis();
        long server = j.getAsJsonObject().get("serverTime").getAsLong();
        long off = server - (t0 + t1) / 2;
        timeOffsetMs = off;
        lastSyncLocalMs = t1;
        timeSyncCount.incrementAndGet();
        if (Math.abs(off) > 1_000L) LOG.warn("[C3-LIVE] lech gio server {} ms (rtt {} ms)", off, t1 - t0);
        return off;
    }

    private void maybeSyncTime() {
        long now = System.currentTimeMillis();
        if (lastSyncLocalMs == 0L || now - lastSyncLocalMs > cfg.timeSyncIntervalMs()) syncTime();
    }

    @Override
    public long serverTime() {
        JsonElement j = call("GET", "/fapi/v1/time", new LinkedHashMap<>(), Sec.NONE, W_TIME, 0);
        return j.getAsJsonObject().get("serverTime").getAsLong();
    }

    @Override
    public ExchangeInfo exchangeInfo() {
        JsonElement j = call("GET", "/fapi/v1/exchangeInfo", new LinkedHashMap<>(), Sec.NONE, W_EXINFO, 0);
        return ExchangeInfoParser.parse(j.toString());
    }

    // ------------------------------------------------------------------ orders

    @Override
    public OrderInfo newMarketOrder(String symbol, Side side, BigDecimal qty, String clientOrderId, boolean reduceOnly) {
        checkCid(clientOrderId);
        if (qty == null || qty.signum() <= 0) throw new GatewayException(ErrorKind.FILTER, "qty <= 0", true);
        Map<String, String> p = new LinkedHashMap<>();
        p.put("symbol", symbol);
        p.put("side", side.name());
        p.put("type", "MARKET");
        p.put("quantity", qty.toPlainString());
        if (reduceOnly) p.put("reduceOnly", "true");
        p.put("newClientOrderId", clientOrderId);
        p.put("newOrderRespType", "RESULT");
        long t0 = System.nanoTime();
        try {
            OrderInfo o = parseOrder(call("POST", "/fapi/v1/order", p, Sec.SIGNED, W_ORDER, 1).getAsJsonObject());
            auditOk("new", o, qty, o.getAvgPrice(), t0);
            return o;
        } catch (GatewayException e) {
            auditErr("new", symbol, side, "MARKET", clientOrderId, qty, null, t0, e);
            throw e;
        }
    }

    @Override
    public OrderInfo newStopMarket(String symbol, Side side, BigDecimal qty, BigDecimal stopPrice, String clientOrderId,
                                   boolean reduceOnly) {
        checkCid(clientOrderId);
        if (stopPrice == null || stopPrice.signum() <= 0) throw new GatewayException(ErrorKind.FILTER, "stopPrice <= 0", true);
        if (qty != null && qty.signum() <= 0) throw new GatewayException(ErrorKind.FILTER, "qty <= 0", true);
        Map<String, String> p = new LinkedHashMap<>();
        p.put("algoType", "CONDITIONAL");
        p.put("symbol", symbol);
        p.put("side", side.name());
        p.put("type", "STOP_MARKET");
        p.put("triggerPrice", stopPrice.toPlainString());
        p.put("workingType", cfg.stopWorkingType());
        if (qty == null) {
            p.put("closePosition", "true");
        } else {
            p.put("quantity", qty.toPlainString());
            if (reduceOnly) p.put("reduceOnly", "true");
        }
        p.put("clientAlgoId", clientOrderId);
        long t0 = System.nanoTime();
        try {
            OrderInfo o = parseAlgo(call("POST", "/fapi/v1/algoOrder", p, Sec.SIGNED, W_ORDER, 1).getAsJsonObject(), null);
            auditOk("new_stop", o, qty, stopPrice, t0);
            return o;
        } catch (GatewayException e) {
            auditErr("new_stop", symbol, side, "STOP_MARKET", clientOrderId, qty, stopPrice, t0, e);
            throw e;
        }
    }

    @Override
    public OrderInfo cancelOrder(String symbol, String clientOrderId) {
        Map<String, String> p = new LinkedHashMap<>();
        p.put("symbol", symbol);
        p.put("origClientOrderId", clientOrderId);
        long t0 = System.nanoTime();
        try {
            OrderInfo o = parseOrder(call("DELETE", "/fapi/v1/order", p, Sec.SIGNED, W_ORDER,
                    cfg.cancelCountsAsOrder() ? 1 : 0).getAsJsonObject());
            auditOk("cancel", o, o.getOrigQty(), o.getStopPrice(), t0);
            return o;
        } catch (GatewayException e) {
            auditErr("cancel", symbol, null, null, clientOrderId, null, null, t0, e);
            throw e;
        }
    }

    @Override
    public OrderInfo cancelStop(String symbol, String clientAlgoId) {
        Map<String, String> p = new LinkedHashMap<>();
        p.put("clientAlgoId", clientAlgoId);
        long t0 = System.nanoTime();
        try {
            OrderInfo o = parseAlgo(call("DELETE", "/fapi/v1/algoOrder", p, Sec.SIGNED, W_ORDER,
                    cfg.cancelCountsAsOrder() ? 1 : 0).getAsJsonObject(), OrderStatus.CANCELED);
            if (o.getSymbol() == null) o = o.toBuilder().symbol(symbol).build();
            auditOk("cancel_stop", o, o.getOrigQty(), o.getStopPrice(), t0);
            return o;
        } catch (GatewayException e) {
            auditErr("cancel_stop", symbol, null, "STOP_MARKET", clientAlgoId, null, null, t0, e);
            throw e;
        }
    }

    @Override
    public Optional<OrderInfo> queryOrderById(String symbol, long orderId) {   // [3h]
        Map<String, String> p = new LinkedHashMap<>();
        p.put("symbol", symbol);
        p.put("orderId", Long.toString(orderId));
        try {
            return Optional.of(parseOrder(call("GET", "/fapi/v1/order", p, Sec.SIGNED, W_QUERY, 0).getAsJsonObject()));
        } catch (GatewayException e) {
            if (e.getKind() == ErrorKind.UNKNOWN_ORDER) return Optional.empty();
            throw e;
        }
    }

    @Override
    public Optional<OrderInfo> queryOrder(String symbol, String clientOrderId) {
        Map<String, String> p = new LinkedHashMap<>();
        p.put("symbol", symbol);
        p.put("origClientOrderId", clientOrderId);
        try {
            return Optional.of(parseOrder(call("GET", "/fapi/v1/order", p, Sec.SIGNED, W_QUERY, 0).getAsJsonObject()));
        } catch (GatewayException e) {
            if (e.getKind() == ErrorKind.UNKNOWN_ORDER) return Optional.empty();
            throw e;
        }
    }

    /**
     * [3j R2(c)] GET /fapi/v1/userTrades?symbol=&amp;orderId= — cac khop THAT cua 1 lenh (CHI DOC, weight 5).
     * orderId khong co khop => list rong (san tra mang rong), khong nem.
     */
    @Override
    public List<TradeFill> userTrades(String symbol, long orderId) {
        Map<String, String> p = new LinkedHashMap<>();
        p.put("symbol", symbol);
        p.put("orderId", Long.toString(orderId));
        JsonElement j = call("GET", "/fapi/v1/userTrades", p, Sec.SIGNED, W_TRADES, 0);
        List<TradeFill> out = new ArrayList<>();
        for (JsonElement e : asArray(j)) {
            if (!e.isJsonObject()) continue;
            JsonObject o = e.getAsJsonObject();
            BigDecimal qty = dec(o, "qty");
            BigDecimal px = dec(o, "price");
            if (qty == null || px == null || qty.signum() <= 0 || px.signum() <= 0) continue;
            String sym = str(o, "symbol");
            out.add(new TradeFill(sym == null ? symbol : sym, lng(o, "orderId"), qty, px, lng(o, "time")));
        }
        return out;
    }

    @Override
    public Optional<OrderInfo> queryStop(String symbol, String clientAlgoId) {
        Map<String, String> p = new LinkedHashMap<>();
        p.put("clientAlgoId", clientAlgoId);
        try {
            return Optional.of(parseAlgo(call("GET", "/fapi/v1/algoOrder", p, Sec.SIGNED, W_QUERY, 0).getAsJsonObject(), null));
        } catch (GatewayException e) {
            if (e.getKind() == ErrorKind.UNKNOWN_ORDER) {   // [3e] ghi ma san (doc-sau-ghi tre vs khong ton tai)
                LOG.info("[C3-LIVE] queryStop {} {}: san bao khong co (http={} code={})", symbol, clientAlgoId, e.getHttpStatus(),
                        e.getExchangeCode());
                return Optional.empty();
            }
            throw e;
        }
    }

    @Override
    public List<OrderInfo> openOrders(String symbolOrNull) {
        Map<String, String> p = new LinkedHashMap<>();
        if (symbolOrNull != null) p.put("symbol", symbolOrNull);
        JsonElement j = call("GET", "/fapi/v1/openOrders", p, Sec.SIGNED, symbolOrNull == null ? W_OPEN_ALL : W_OPEN_SYM, 0);
        List<OrderInfo> out = new ArrayList<>();
        for (JsonElement e : asArray(j)) out.add(parseOrder(e.getAsJsonObject()));
        return out;
    }

    @Override
    public List<OrderInfo> openStops(String symbolOrNull) {
        Map<String, String> p = new LinkedHashMap<>();
        if (symbolOrNull != null) p.put("symbol", symbolOrNull);
        JsonElement j = call("GET", "/fapi/v1/openAlgoOrders", p, Sec.SIGNED, symbolOrNull == null ? W_OPEN_ALL : W_OPEN_SYM, 0);
        List<OrderInfo> out = new ArrayList<>();
        for (JsonElement e : asArray(j)) out.add(parseAlgo(e.getAsJsonObject(), null));
        return out;
    }

    // ------------------------------------------------------------------ account

    @Override
    public List<PositionInfo> positions() {
        JsonElement j = call("GET", "/fapi/v3/positionRisk", new LinkedHashMap<>(), Sec.SIGNED, W_POSITION, 0);
        List<PositionInfo> out = new ArrayList<>();
        for (JsonElement e : asArray(j)) {
            JsonObject o = e.getAsJsonObject();
            BigDecimal upnl = dec(o, "unRealizedProfit");
            if (upnl == null) upnl = dec(o, "unrealizedProfit");
            out.add(new PositionInfo(str(o, "symbol"), str(o, "positionSide"), dec(o, "positionAmt"), dec(o, "entryPrice"),
                    dec(o, "markPrice"), upnl, dec(o, "notional"), lng(o, "updateTime")));
        }
        return out;
    }

    @Override
    public AccountSnapshot account() {
        JsonObject o = call("GET", "/fapi/v3/account", new LinkedHashMap<>(), Sec.SIGNED, W_ACCOUNT, 0).getAsJsonObject();
        List<AssetBalance> assets = new ArrayList<>();
        if (o.has("assets") && o.get("assets").isJsonArray()) {
            for (JsonElement e : o.getAsJsonArray("assets")) {
                JsonObject a = e.getAsJsonObject();
                assets.add(new AssetBalance(str(a, "asset"), dec(a, "walletBalance"), dec(a, "marginBalance"),
                        dec(a, "availableBalance"), dec(a, "unrealizedProfit")));
            }
        }
        BigDecimal tmb = dec(o, "totalMarginBalance");
        if (tmb == null) throw new GatewayException(ErrorKind.OTHER, "account: thieu totalMarginBalance", true);
        // [2d MAJ-2b] positions cua v3/account = nguon doi chung thu 2 cho xac nhan "phang" (null neu san khong tra mang)
        List<PositionInfo> positions = null;
        if (o.has("positions") && o.get("positions").isJsonArray()) {
            positions = new ArrayList<>();
            for (JsonElement e : o.getAsJsonArray("positions")) {
                JsonObject p = e.getAsJsonObject();
                BigDecimal amt = dec(p, "positionAmt");
                String s = str(p, "symbol");
                if (s == null || amt == null) continue;
                positions.add(new PositionInfo(s, str(p, "positionSide"), amt, dec(p, "entryPrice"), dec(p, "markPrice"),
                        dec(p, "unrealizedProfit"), dec(p, "notional"), p.has("updateTime") ? lng(p, "updateTime") : 0L));
            }
        }
        return new AccountSnapshot(tmb, dec(o, "totalWalletBalance"), dec(o, "availableBalance"),
                dec(o, "totalUnrealizedProfit"), assets, System.currentTimeMillis() + timeOffsetMs, positions);
    }

    @Override
    public boolean multiAssetsMargin() {
        JsonObject o = call("GET", "/fapi/v1/multiAssetsMargin", new LinkedHashMap<>(), Sec.SIGNED, W_MULTI, 0).getAsJsonObject();
        return requireBool(o, "multiAssetsMargin");
    }

    @Override
    public boolean dualSidePosition() {
        JsonObject o = call("GET", "/fapi/v1/positionSide/dual", new LinkedHashMap<>(), Sec.SIGNED, W_DUAL, 0).getAsJsonObject();
        return requireBool(o, "dualSidePosition");
    }

    @Override
    public void setDualSidePosition(boolean dual) {
        Map<String, String> p = new LinkedHashMap<>();
        p.put("dualSidePosition", Boolean.toString(dual));
        try {
            call("POST", "/fapi/v1/positionSide/dual", p, Sec.SIGNED, W_SET, 0);
        } catch (GatewayException e) {
            if (e.getExchangeCode() != -4059) throw e; // No need to change position side
        }
    }

    @Override
    public SymbolConfig symbolConfig(String symbol) {
        Map<String, String> p = new LinkedHashMap<>();
        p.put("symbol", symbol);
        JsonElement j = call("GET", "/fapi/v1/symbolConfig", p, Sec.SIGNED, W_SYMCFG, 0);
        for (JsonElement e : asArray(j)) {
            JsonObject o = e.getAsJsonObject();
            if (symbol.equals(str(o, "symbol"))) {
                return new SymbolConfig(symbol, str(o, "marginType"), (int) lng(o, "leverage"));
            }
        }
        throw new GatewayException(ErrorKind.OTHER, "symbolConfig: khong co dong cho symbol", true);
    }

    /** [2c MIN-5] GET /fapi/v1/symbolConfig khong symbol => moi symbol (1 call). */
    @Override
    public List<SymbolConfig> symbolConfigs() {
        JsonElement j = call("GET", "/fapi/v1/symbolConfig", new LinkedHashMap<>(), Sec.SIGNED, W_SYMCFG, 0);
        List<SymbolConfig> out = new ArrayList<>();
        for (JsonElement e : asArray(j)) {
            JsonObject o = e.getAsJsonObject();
            String s = str(o, "symbol");
            if (s != null) out.add(new SymbolConfig(s, str(o, "marginType"), (int) lng(o, "leverage")));
        }
        return out;
    }

    @Override
    public int setLeverage(String symbol, int leverage) {
        Map<String, String> p = new LinkedHashMap<>();
        p.put("symbol", symbol);
        p.put("leverage", Integer.toString(leverage));
        JsonObject o = call("POST", "/fapi/v1/leverage", p, Sec.SIGNED, W_SET, 0).getAsJsonObject();
        return (int) lng(o, "leverage");
    }

    @Override
    public void setMarginType(String symbol, String marginType) {
        Map<String, String> p = new LinkedHashMap<>();
        p.put("symbol", symbol);
        p.put("marginType", SymbolConfig.normalizeMarginType(marginType));
        try {
            call("POST", "/fapi/v1/marginType", p, Sec.SIGNED, W_SET, 0);
        } catch (GatewayException e) {
            if (e.getExchangeCode() != -4046) throw e; // No need to change margin type
        }
    }

    /** [V12 3] GET /fapi/v1/ticker/24hr (public, khong ky). Chi cong cu canary dung. */
    @Override
    public List<Ticker24h> tickers24h(String symbolOrNull) {
        Map<String, String> p = new LinkedHashMap<>();
        if (symbolOrNull != null) p.put("symbol", symbolOrNull);
        JsonElement j = call("GET", "/fapi/v1/ticker/24hr", p, Sec.NONE, symbolOrNull == null ? W_TICKER_ALL : W_TICKER_SYM, 0);
        List<Ticker24h> out = new ArrayList<>();
        if (j != null && j.isJsonObject()) {
            out.add(parseTicker(j.getAsJsonObject()));
        } else {
            for (JsonElement e : asArray(j)) out.add(parseTicker(e.getAsJsonObject()));
        }
        return out;
    }

    static Ticker24h parseTicker(JsonObject o) {
        return new Ticker24h(str(o, "symbol"), dec(o, "lastPrice"), dec(o, "quoteVolume"), lng(o, "closeTime"));
    }

    @Override
    public String startUserStream() {
        JsonObject o = call("POST", "/fapi/v1/listenKey", new LinkedHashMap<>(), Sec.API_KEY, W_LISTEN, 0).getAsJsonObject();
        String k = str(o, "listenKey");
        if (k == null || k.isEmpty()) throw new GatewayException(ErrorKind.OTHER, "listenKey rong", true);
        return k;
    }

    @Override
    public void keepAliveUserStream(String listenKey) {
        call("PUT", "/fapi/v1/listenKey", new LinkedHashMap<>(), Sec.API_KEY, W_LISTEN, 0);
    }

    @Override
    public void closeUserStream(String listenKey) {
        call("DELETE", "/fapi/v1/listenKey", new LinkedHashMap<>(), Sec.API_KEY, W_LISTEN, 0);
    }

    // ------------------------------------------------------------------ transport

    private JsonElement call(String method, String path, Map<String, String> params, Sec sec, int weight, int orders) {
        boolean mutating = !"GET".equals(method);
        // [3i] GET = doc (chinh sach canary: ngu burst / cho sang phut moi); GET long trong lenh ghi (dong bo gio) = khong cho
        rate.acquire(weight, orders, cfg.rateMaxWaitMs(), !mutating && IN_WRITE.get()[0] == 0);
        if (sec == Sec.SIGNED) {
            if (mutating) {
                IN_WRITE.get()[0]++;
                try {
                    maybeSyncTime();
                } finally {
                    IN_WRITE.get()[0]--;
                }
            } else {
                maybeSyncTime();
            }
        }
        StringBuilder q = new StringBuilder();
        for (Map.Entry<String, String> e : params.entrySet()) {
            if (q.length() > 0) q.append('&');
            q.append(enc(e.getKey())).append('=').append(enc(e.getValue()));
        }
        if (sec == Sec.SIGNED) {
            if (q.length() > 0) q.append('&');
            q.append("recvWindow=").append(cfg.recvWindowMs());
            q.append("&timestamp=").append(System.currentTimeMillis() + timeOffsetMs);
            String sig = signer.sign(q.toString());
            q.append("&signature=").append(sig);
        }
        URI uri = URI.create(cfg.baseUrl() + path + (q.length() > 0 ? "?" + q : ""));
        HttpRequest.Builder rb = HttpRequest.newBuilder(uri).timeout(Duration.ofMillis(cfg.requestTimeoutMs()))
                .method(method, HttpRequest.BodyPublishers.noBody());
        if (sec != Sec.NONE) rb.header(H_APIKEY, apiKey);
        long t0 = System.nanoTime();
        HttpResponse<String> resp;
        try {
            resp = http.send(rb.build(), HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        } catch (HttpConnectTimeoutException e) {
            throw new GatewayException(ErrorKind.OTHER, 0, 0, method + " " + path + ": connect timeout", true, 0L, null);
        } catch (ConnectException e) {
            throw new GatewayException(ErrorKind.OTHER, 0, 0, method + " " + path + ": khong ket noi duoc", true, 0L, null);
        } catch (HttpTimeoutException e) {
            throw new GatewayException(ErrorKind.TIMEOUT_UNKNOWN_STATE, 0, 0, method + " " + path + ": timeout sau "
                    + cfg.requestTimeoutMs() + " ms", !mutating, 0L, null);
        } catch (IOException e) {
            throw new GatewayException(mutating ? ErrorKind.TIMEOUT_UNKNOWN_STATE : ErrorKind.OTHER, 0, 0,
                    method + " " + path + ": IO " + e.getClass().getSimpleName(), !mutating, 0L, null);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new GatewayException(mutating ? ErrorKind.TIMEOUT_UNKNOWN_STATE : ErrorKind.OTHER, 0, 0,
                    method + " " + path + ": interrupted", !mutating, 0L, null);
        }
        long latMs = (System.nanoTime() - t0) / 1_000_000L;
        rate.onHeaders(intHeader(resp, "X-MBX-USED-WEIGHT-1M"), intHeader(resp, "X-MBX-ORDER-COUNT-10S"),
                intHeader(resp, "X-MBX-ORDER-COUNT-1M"));
        int st = resp.statusCode();
        String body = resp.body() == null ? "" : resp.body();
        if (LOG.isDebugEnabled()) LOG.debug("[C3-LIVE] {} {} http={} lat={}ms", method, path, st, latMs);
        if (st >= 200 && st < 300) {
            rate.onSuccess();
            try {
                return parseJson(body);
            } catch (RuntimeException e) {
                throw new GatewayException(mutating ? ErrorKind.TIMEOUT_UNKNOWN_STATE : ErrorKind.OTHER, st, 0,
                        method + " " + path + ": body 2xx khong phai JSON", !mutating, 0L, null);
            }
        }
        int code = 0;
        String msg = "";
        try {
            JsonElement j = parseJson(body);
            if (j.isJsonObject()) {
                JsonObject o = j.getAsJsonObject();
                if (o.has("code") && o.get("code").isJsonPrimitive()) code = o.get("code").getAsInt();
                String m = str(o, "msg");
                if (m != null) msg = m;
            }
        } catch (RuntimeException ignore) {
            msg = "body khong phai JSON";
        }
        long retryAfterMs = 0L;
        if (st == 429 || st == 418) {
            Integer ra = intHeader(resp, "Retry-After");
            retryAfterMs = ra == null ? 0L : ra * 1000L;
            long until = rate.onRateLimited(st, retryAfterMs);
            retryAfterMs = Math.max(retryAfterMs, until - System.currentTimeMillis());
        }
        if (code == -1021) {
            lastSyncLocalMs = 0L; // buoc dong bo lai o call ky tiep theo
            LOG.warn("[C3-LIVE] -1021 timestamp ngoai recvWindow -> se dong bo gio server lai");
        }
        ErrorKind kind = ErrorMapper.kindFor(st, code);
        throw new GatewayException(kind, st, code, method + " " + path + ": " + shortMsg(msg), ErrorMapper.definitelyNotExecuted(kind),
                retryAfterMs, null);
    }

    @SuppressWarnings("deprecation")
    private static JsonElement parseJson(String body) {
        return new JsonParser().parse(body);
    }

    private static Integer intHeader(HttpResponse<?> r, String name) {
        Optional<String> v = r.headers().firstValue(name);
        if (!v.isPresent()) return null;
        try {
            return Integer.parseInt(v.get().trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static String enc(String s) {
        return URLEncoder.encode(s == null ? "" : s, StandardCharsets.UTF_8).replace("+", "%20");
    }

    private static String shortMsg(String m) {
        if (m == null) return "";
        String s = m.replace('\n', ' ').replace('\r', ' ');
        return s.length() > 200 ? s.substring(0, 200) : s;
    }

    private static void checkCid(String cid) {
        if (!ClientOrderIds.isValid(cid)) {
            throw new GatewayException(ErrorKind.OTHER, "clientOrderId khong hop le (luat san ^[.A-Z:/a-z0-9_-]{1,36}$)", true);
        }
    }

    // ------------------------------------------------------------------ audit

    private void auditOk(String reason, OrderInfo o, BigDecimal qty, BigDecimal px, long t0Nanos) {
        audit.record(OrderAuditLog.Entry.of(System.currentTimeMillis()).clientOrderId(o.getClientOrderId()).orderId(o.getOrderId())
                .symbol(o.getSymbol()).side(o.getSide() == null ? null : o.getSide().name()).type(o.getType())
                .qty(qty != null ? qty : o.getOrigQty()).price(px).status(o.getRawStatus() != null ? o.getRawStatus() : o.getStatus().name())
                .latencyMs((System.nanoTime() - t0Nanos) / 1_000_000L).reason(reason));
    }

    private void auditErr(String reason, String symbol, Side side, String type, String cid, BigDecimal qty, BigDecimal px,
                          long t0Nanos, GatewayException e) {
        audit.record(OrderAuditLog.Entry.of(System.currentTimeMillis()).clientOrderId(cid).symbol(symbol)
                .side(side == null ? null : side.name()).type(type).qty(qty).price(px).status("ERROR")
                .latencyMs((System.nanoTime() - t0Nanos) / 1_000_000L)
                .errCode(e.getKind().name() + ":" + e.getExchangeCode()).reason(reason + ":" + e.getMessage()));
    }

    // ------------------------------------------------------------------ parse

    static OrderInfo parseOrder(JsonObject o) {
        String type = str(o, "type");
        if (type == null) type = str(o, "origType");
        String rs = str(o, "status");
        long ut = lng(o, "updateTime");
        if (ut == 0L) ut = lng(o, "time");
        return OrderInfo.builder().kind(OrderKind.REGULAR).symbol(str(o, "symbol")).orderId(lng(o, "orderId"))
                .clientOrderId(str(o, "clientOrderId")).side(Side.parse(str(o, "side"))).type(type)
                .status(OrderStatus.parse(rs)).rawStatus(rs).origQty(dec(o, "origQty")).executedQty(dec(o, "executedQty"))
                .avgPrice(dec(o, "avgPrice")).stopPrice(dec(o, "stopPrice")).reduceOnly(bool(o, "reduceOnly"))
                .closePosition(bool(o, "closePosition")).updateTimeMs(ut).build();
    }

    static OrderInfo parseAlgo(JsonObject o, OrderStatus fallbackStatus) {
        String type = str(o, "orderType");
        if (type == null) type = str(o, "type");
        String rs = str(o, "algoStatus");
        OrderStatus st = rs == null && fallbackStatus != null ? fallbackStatus : OrderStatus.parse(rs);
        long ut = lng(o, "updateTime");
        if (ut == 0L) ut = lng(o, "createTime");
        return OrderInfo.builder().kind(OrderKind.ALGO).symbol(str(o, "symbol")).orderId(lng(o, "algoId"))
                .clientOrderId(str(o, "clientAlgoId")).side(Side.parse(str(o, "side"))).type(type).status(st)
                .rawStatus(rs != null ? rs : st.name()).origQty(dec(o, "quantity")).stopPrice(dec(o, "triggerPrice"))
                .reduceOnly(bool(o, "reduceOnly")).closePosition(bool(o, "closePosition")).updateTimeMs(ut)
                .actualOrderId(str(o, "actualOrderId")).build();
    }

    private static JsonArray asArray(JsonElement j) {
        if (j != null && j.isJsonArray()) return j.getAsJsonArray();
        throw new GatewayException(ErrorKind.OTHER, "response khong phai mang JSON", true);
    }

    static String str(JsonObject o, String k) {
        JsonElement e = o.get(k);
        return e == null || e.isJsonNull() || !e.isJsonPrimitive() ? null : e.getAsString();
    }

    static BigDecimal dec(JsonObject o, String k) {
        String s = str(o, k);
        if (s == null || s.trim().isEmpty()) return null;
        try {
            return new BigDecimal(s.trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    static long lng(JsonObject o, String k) {
        String s = str(o, k);
        if (s == null) return 0L;
        try {
            return new BigDecimal(s.trim()).longValue();
        } catch (NumberFormatException e) {
            return 0L;
        }
    }

    static boolean bool(JsonObject o, String k) {
        String s = str(o, k);
        return s != null && "true".equalsIgnoreCase(s.trim());
    }

    private static boolean requireBool(JsonObject o, String k) {
        String s = str(o, k);
        if (s == null) throw new GatewayException(ErrorKind.OTHER, "thieu truong " + k, true);
        return "true".equalsIgnoreCase(s.trim());
    }
}
