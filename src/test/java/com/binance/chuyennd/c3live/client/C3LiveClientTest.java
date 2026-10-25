package com.binance.chuyennd.c3live.client;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.OrderKind;
import com.binance.chuyennd.c3live.api.OrderStatus;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.api.SymbolConfig;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.rate.RateGuard;
import com.sun.net.httpserver.HttpServer;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.slf4j.LoggerFactory;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.io.OutputStream;
import java.math.BigDecimal;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.Executors;
import java.util.function.Function;

import static org.junit.Assert.*;

/**
 * [V12 C2] C3LiveClient tren mock HTTP server (JDK HttpServer; repo khong co MockWebServer). Khong goi Binance that.
 * Key/secret o day la VECTOR CONG KHAI trong tai lieu Binance (khong phai key that).
 */
public class C3LiveClientTest {
    // Vector HMAC USDT-M docs (SIGNED endpoint example)
    static final String KEY = "dbefbc809e3e83c283a984c3a1459732ea7db1360ca80c5c2c8867408d28cc83";
    static final String SECRET = "2b5eb11e18796d12d88f13dc27dbbd02c2cc51ff7059765ed9821957d82bb4d9";

    static final class Req {
        final String method, path, rawQuery, apiKey;
        Req(String m, String p, String q, String k) { method = m; path = p; rawQuery = q == null ? "" : q; apiKey = k; }
        String param(String name) {
            for (String kv : rawQuery.split("&")) {
                int i = kv.indexOf('=');
                if (i > 0 && kv.substring(0, i).equals(name)) return java.net.URLDecoder.decode(kv.substring(i + 1), StandardCharsets.UTF_8);
            }
            return null;
        }
    }

    static final class Resp {
        final int status; final String body; final Map<String, String> headers = new HashMap<>(); long delayMs;
        Resp(int s, String b) { status = s; body = b; }
        Resp h(String k, String v) { headers.put(k, v); return this; }
        Resp delay(long d) { delayMs = d; return this; }
    }

    HttpServer srv;
    final List<Req> reqs = new CopyOnWriteArrayList<>();
    volatile Function<Req, Resp> handler = r -> new Resp(404, "{\"code\":-1,\"msg\":\"no route\"}");
    volatile long serverOffsetMs = 5_000L;
    final List<String> auditLines = new CopyOnWriteArrayList<>();
    ListAppender<ILoggingEvent> logs;

    @Before
    public void start() throws Exception {
        srv = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        srv.createContext("/", ex -> {
            Req r = new Req(ex.getRequestMethod(), ex.getRequestURI().getPath(), ex.getRequestURI().getRawQuery(),
                    ex.getRequestHeaders().getFirst("X-MBX-APIKEY"));
            reqs.add(r);
            Resp p;
            if (r.path.equals("/fapi/v1/time")) p = new Resp(200, "{\"serverTime\":" + (System.currentTimeMillis() + serverOffsetMs) + "}");
            else p = handler.apply(r);
            if (p.delayMs > 0) { try { Thread.sleep(p.delayMs); } catch (InterruptedException ignored) { } }
            byte[] b = p.body.getBytes(StandardCharsets.UTF_8);
            for (Map.Entry<String, String> h : p.headers.entrySet()) ex.getResponseHeaders().add(h.getKey(), h.getValue());
            ex.getResponseHeaders().add("Content-Type", "application/json");
            ex.sendResponseHeaders(p.status, b.length == 0 ? -1 : b.length);
            if (b.length > 0) try (OutputStream os = ex.getResponseBody()) { os.write(b); }
            ex.close();
        });
        srv.setExecutor(Executors.newCachedThreadPool());
        srv.start();
        logs = new ListAppender<>();
        logs.start();
        ((Logger) LoggerFactory.getLogger(org.slf4j.Logger.ROOT_LOGGER_NAME)).addAppender(logs);
    }

    @After
    public void stop() {
        srv.stop(0);
        ((Logger) LoggerFactory.getLogger(org.slf4j.Logger.ROOT_LOGGER_NAME)).detachAppender(logs);
        // Khong dong log/audit nao duoc chua key / secret / signature
        List<String> all = new ArrayList<>(auditLines);
        for (ILoggingEvent e : logs.list) all.add(e.getFormattedMessage());
        for (Req r : reqs) {
            String sig = r.param("signature");
            for (String line : all) {
                assertFalse("lo key trong log: " + line, line.contains(KEY));
                assertFalse("lo secret trong log", line.contains(SECRET));
                if (sig != null) assertFalse("lo signature trong log", line.contains(sig));
                assertFalse("lo query trong log", line.contains("timestamp="));
            }
        }
    }

    C3LiveClient client(RateGuard g, long reqTimeoutMs) {
        C3LiveClientConfig cfg = C3LiveClientConfig.builder().baseUrl("http://127.0.0.1:" + srv.getAddress().getPort())
                .requestTimeoutMs(reqTimeoutMs).connectTimeoutMs(1_000L).rateMaxWaitMs(0L).build();
        return new C3LiveClient(cfg, C3LiveKeys.ofForTest(KEY, SECRET), g, new OrderAuditLog(OrderAuditLog.LIVE_TAG, auditLines::add));
    }

    C3LiveClient client() { return client(RateGuard.defaults(), 3_000L); }

    /** Kiem chu ky DOC LAP (javax.crypto truc tiep, khong qua HmacSigner). */
    static boolean signatureOk(Req r) throws Exception {
        int i = r.rawQuery.lastIndexOf("&signature=");
        if (i < 0) return false;
        String payload = r.rawQuery.substring(0, i);
        String sig = r.rawQuery.substring(i + "&signature=".length());
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(SECRET.getBytes(StandardCharsets.US_ASCII), "HmacSHA256"));
        StringBuilder sb = new StringBuilder();
        for (byte x : mac.doFinal(payload.getBytes(StandardCharsets.UTF_8))) sb.append(String.format("%02x", x & 0xff));
        return sb.toString().equals(sig);
    }

    static String orderJson(String sym, String cid, String status) {
        return "{\"orderId\":123456,\"symbol\":\"" + sym + "\",\"status\":\"" + status + "\",\"clientOrderId\":\"" + cid
                + "\",\"price\":\"0\",\"avgPrice\":\"64010.5\",\"origQty\":\"0.003\",\"executedQty\":\"0.003\",\"type\":\"MARKET\","
                + "\"origType\":\"MARKET\",\"side\":\"BUY\",\"reduceOnly\":false,\"closePosition\":false,\"stopPrice\":\"0\","
                + "\"updateTime\":1761400000123}";
    }

    @Test
    public void hmacMatchesBinanceDocVectors() {
        assertEquals("c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71", HmacSigner.hmacSha256Hex(
                "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j".getBytes(StandardCharsets.US_ASCII),
                "symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559"));
        assertEquals("3c661234138461fcc7a7d8746c6558c9842d4e10870d2ecbedf7777cad694af9", HmacSigner.hmacSha256Hex(
                SECRET.getBytes(StandardCharsets.US_ASCII),
                "symbol=BTCUSDT&side=BUY&type=LIMIT&quantity=1&price=9000&timeInForce=GTC&recvWindow=5000&timestamp=1591702613943"));
    }

    @Test
    public void signedMarketOrderRoundTrip() throws Exception {
        handler = r -> new Resp(200, orderJson("BTCUSDT", r.param("newClientOrderId"), "FILLED"))
                .h("X-MBX-USED-WEIGHT-1M", "7").h("X-MBX-ORDER-COUNT-10S", "1").h("X-MBX-ORDER-COUNT-1M", "1");
        RateGuard g = RateGuard.defaults();
        C3LiveClient c = client(g, 3_000L);
        long before = System.currentTimeMillis();
        OrderInfo o = c.newMarketOrder("BTCUSDT", Side.BUY, new BigDecimal("0.003"), "c3-BTCUSDT-29356667-1", false);
        assertEquals(OrderStatus.FILLED, o.getStatus());
        assertEquals(OrderKind.REGULAR, o.getKind());
        assertEquals(123456L, o.getOrderId());
        assertEquals(0, new BigDecimal("64010.5").compareTo(o.getAvgPrice()));
        Req r = reqs.stream().filter(x -> x.path.equals("/fapi/v1/order")).findFirst().get();
        assertEquals("POST", r.method);
        assertEquals(KEY, r.apiKey);
        assertTrue("chu ky sai", signatureOk(r));
        assertTrue(r.rawQuery.endsWith("&signature=" + r.param("signature")));
        assertEquals("MARKET", r.param("type"));
        assertEquals("0.003", r.param("quantity"));
        assertEquals("RESULT", r.param("newOrderRespType"));
        assertNull("reduceOnly=false khong gui", r.param("reduceOnly"));
        assertEquals("5000", r.param("recvWindow"));
        long ts = Long.parseLong(r.param("timestamp"));
        assertTrue("timestamp phai theo gio server (+5s): " + (ts - before), Math.abs(ts - (before + 5_000L)) < 2_000L);
        assertEquals(1, reqs.stream().filter(x -> x.path.equals("/fapi/v1/time")).count());
        assertNull("/time khong gui api key", reqs.get(0).apiKey);
        assertEquals(7, g.lastServerWeight1m());
        assertEquals(1, auditLines.size());
        String line = auditLines.get(0);
        assertTrue(line, line.startsWith("[C3-LIVE-ORDER] ts="));
        assertTrue(line, line.contains(" cid=c3-BTCUSDT-29356667-1 oid=123456 sym=BTCUSDT side=BUY type=MARKET qty=0.003 px=64010.5 status=FILLED lat_ms="));
        assertTrue(line, line.endsWith(" err=- reason=new"));
    }

    @Test
    public void nonAsciiSymbolPercentEncodedAndSigned() throws Exception {
        String sym = "币安人生USDT";
        handler = r -> new Resp(200, orderJson(sym, r.param("newClientOrderId"), "FILLED"));
        OrderInfo o = client().newMarketOrder(sym, Side.BUY, new BigDecimal("10"), "c3-" + com.binance.chuyennd.c3live.api.ClientOrderIds.symbolToken(sym) + "-1-1", false);
        Req r = reqs.stream().filter(x -> x.path.equals("/fapi/v1/order")).findFirst().get();
        assertTrue(r.rawQuery, r.rawQuery.startsWith("symbol=%E5%B8%81%E5%AE%89%E4%BA%BA%E7%94%9FUSDT&"));
        assertEquals(sym, r.param("symbol"));
        assertTrue(signatureOk(r));
        assertEquals(sym, o.getSymbol());
    }

    @Test
    public void invalidClientOrderIdNeverSent() {
        try {
            client().newMarketOrder("BTCUSDT", Side.BUY, BigDecimal.ONE, "c3 bad id", false);
            fail();
        } catch (GatewayException e) {
            assertTrue(e.isDefinitelyNotExecuted());
        }
        assertEquals(0, reqs.size());
    }

    private GatewayException expectError(int status, String body, Map<String, String> headers, String path) {
        handler = r -> {
            Resp p = new Resp(status, body);
            if (headers != null) p.headers.putAll(headers);
            return p;
        };
        C3LiveClient c = client();
        try {
            if (path.equals("cancel")) c.cancelOrder("BTCUSDT", "c3-x-1");
            else c.newMarketOrder("BTCUSDT", Side.BUY, BigDecimal.ONE, "c3-x-1", false);
            fail("phai nem loi");
            return null;
        } catch (GatewayException e) {
            assertFalse(e.getMessage().contains(SECRET));
            assertFalse(e.getMessage().contains("signature"));
            return e;
        }
    }

    private static String err(int code, String msg) { return "{\"code\":" + code + ",\"msg\":\"" + msg + "\"}"; }

    @Test
    public void errorMapping() {
        Object[][] cases = {
                {401, -2015, ErrorKind.AUTH, true},
                {400, -1022, ErrorKind.AUTH, true},
                {400, -2019, ErrorKind.INSUFFICIENT_MARGIN, true},
                {400, -1013, ErrorKind.FILTER, true},
                {400, -4164, ErrorKind.FILTER, true},
                {400, -1111, ErrorKind.FILTER, true},
                {400, -4061, ErrorKind.OTHER, true},
                {400, -1021, ErrorKind.OTHER, true},
                {503, -1007, ErrorKind.TIMEOUT_UNKNOWN_STATE, false},
                {502, 0, ErrorKind.TIMEOUT_UNKNOWN_STATE, false},
        };
        for (Object[] k : cases) {
            reqs.clear();
            GatewayException e = expectError((Integer) k[0], err((Integer) k[1], "x"), null, "new");
            assertEquals("code " + k[1], k[2], e.getKind());
            assertEquals("code " + k[1], k[3], e.isDefinitelyNotExecuted());
            assertEquals((int) (Integer) k[1], e.getExchangeCode());
            assertEquals((int) (Integer) k[0], e.getHttpStatus());
        }
        GatewayException u = expectError(400, err(-2011, "Unknown order sent."), null, "cancel");
        assertEquals(ErrorKind.UNKNOWN_ORDER, u.getKind());
        GatewayException nj = expectError(503, "<html>Service Unavailable</html>", null, "new");
        assertEquals(ErrorKind.TIMEOUT_UNKNOWN_STATE, nj.getKind());
        // moi loi lenh deu co 1 dong audit err
        assertTrue(auditLines.stream().anyMatch(l -> l.contains(" err=INSUFFICIENT_MARGIN:-2019 ")));
    }

    @Test
    public void http429BlocksGuardAndHonoursRetryAfter() {
        RateGuard g = RateGuard.defaults();
        handler = r -> new Resp(429, err(-1003, "Too many requests")).h("Retry-After", "3");
        C3LiveClient c = client(g, 3_000L);
        long t = System.currentTimeMillis();
        try { c.newMarketOrder("BTCUSDT", Side.BUY, BigDecimal.ONE, "c3-a-1", false); fail(); }
        catch (GatewayException e) { assertEquals(ErrorKind.RATE_LIMIT, e.getKind()); assertTrue(e.getRetryAfterMs() >= 2_500L); }
        assertTrue(g.blockedUntilMs() >= t + 2_900L);
        int n = reqs.size();
        try { c.newMarketOrder("BTCUSDT", Side.BUY, BigDecimal.ONE, "c3-a-2", false); fail(); }
        catch (GatewayException e) { assertEquals(ErrorKind.RATE_LIMIT, e.getKind()); assertTrue(e.isDefinitelyNotExecuted()); }
        assertEquals("bi chan noi bo, khong goi san", n, reqs.size());
    }

    @Test
    public void http418BanBlocksAllCalls() {
        RateGuard g = RateGuard.defaults();
        handler = r -> new Resp(418, err(-1003, "Way too many requests; IP banned")).h("Retry-After", "120");
        C3LiveClient c = client(g, 3_000L);
        long t = System.currentTimeMillis();
        try { c.positions(); fail(); } catch (GatewayException e) { assertEquals(ErrorKind.RATE_LIMIT, e.getKind()); }
        assertTrue(g.blockedUntilMs() >= t + 119_000L);
        int n = reqs.size();
        try { c.account(); fail(); } catch (GatewayException e) { assertEquals(ErrorKind.RATE_LIMIT, e.getKind()); }
        assertEquals(n, reqs.size());
    }

    @Test
    public void timestampErrorForcesResync() {
        final int[] k = {0};
        handler = r -> (k[0]++ == 0) ? new Resp(400, err(-1021, "Timestamp outside recvWindow")) : new Resp(200, "{\"multiAssetsMargin\":true}");
        C3LiveClient c = client();
        try { c.multiAssetsMargin(); fail(); } catch (GatewayException e) { assertEquals(-1021, e.getExchangeCode()); }
        assertTrue(c.multiAssetsMargin());
        assertEquals(2, reqs.stream().filter(x -> x.path.equals("/fapi/v1/time")).count());
        assertEquals(2L, c.timeSyncCount());
    }

    @Test
    public void queryUnknownIsEmptyButUnknownStateThrows() {
        handler = r -> new Resp(400, err(-2013, "Order does not exist."));
        assertFalse(client().queryOrder("BTCUSDT", "c3-q-1").isPresent());
        handler = r -> new Resp(503, err(0, "Unknown error, please check your request or try again later."));
        try { client().queryOrder("BTCUSDT", "c3-q-1"); fail(); }
        catch (GatewayException e) { assertEquals(ErrorKind.TIMEOUT_UNKNOWN_STATE, e.getKind()); }
        handler = r -> new Resp(200, orderJson("BTCUSDT", "c3-q-1", "NEW"));
        Optional<OrderInfo> o = client().queryOrder("BTCUSDT", "c3-q-1");
        assertEquals(OrderStatus.NEW, o.get().getStatus());
        assertEquals("c3-q-1", reqs.get(reqs.size() - 1).param("origClientOrderId"));
    }

    @Test
    public void timeoutOnOrderIsUnknownState() {
        handler = r -> new Resp(200, orderJson("BTCUSDT", "c3-t-1", "FILLED")).delay(1_500L);
        C3LiveClient c = client(RateGuard.defaults(), 300L);
        try { c.newMarketOrder("BTCUSDT", Side.BUY, BigDecimal.ONE, "c3-t-1", false); fail(); }
        catch (GatewayException e) {
            assertEquals(ErrorKind.TIMEOUT_UNKNOWN_STATE, e.getKind());
            assertFalse("timeout lenh = trang thai chua biet", e.isDefinitelyNotExecuted());
        }
    }

    @Test
    public void stopMarketUsesAlgoApi() throws Exception {
        handler = r -> new Resp(200, "{\"algoId\":777,\"clientAlgoId\":\"" + r.param("clientAlgoId") + "\",\"algoType\":\"CONDITIONAL\","
                + "\"orderType\":\"STOP_MARKET\",\"symbol\":\"ETHUSDT\",\"side\":\"SELL\",\"quantity\":\"" + (r.param("quantity") == null ? "0" : r.param("quantity"))
                + "\",\"algoStatus\":\"NEW\",\"triggerPrice\":\"" + r.param("triggerPrice") + "\",\"reduceOnly\":" + ("true".equals(r.param("reduceOnly")))
                + ",\"closePosition\":" + ("true".equals(r.param("closePosition"))) + ",\"createTime\":1761400000000,\"updateTime\":1761400000001}");
        C3LiveClient c = client();
        OrderInfo s = c.newStopMarket("ETHUSDT", Side.SELL, new BigDecimal("0.25"), new BigDecimal("2412.37"), "c3-ETHUSDT-1-sl1", true);
        Req r = reqs.stream().filter(x -> x.path.equals("/fapi/v1/algoOrder")).findFirst().get();
        assertEquals("POST", r.method);
        assertTrue(signatureOk(r));
        assertEquals("CONDITIONAL", r.param("algoType"));
        assertEquals("STOP_MARKET", r.param("type"));
        assertEquals("2412.37", r.param("triggerPrice"));
        assertEquals("MARK_PRICE", r.param("workingType"));   // [V12 MASTER 10-25] mac dinh MARK_PRICE
        assertEquals("0.25", r.param("quantity"));
        assertEquals("true", r.param("reduceOnly"));
        assertNull(r.param("closePosition"));
        assertEquals(OrderKind.ALGO, s.getKind());
        assertEquals(777L, s.getOrderId());
        assertEquals("c3-ETHUSDT-1-sl1", s.getClientOrderId());
        assertEquals(0, new BigDecimal("2412.37").compareTo(s.getStopPrice()));
        assertTrue(s.isReduceOnly());
        reqs.clear();
        OrderInfo cp = c.newStopMarket("ETHUSDT", Side.SELL, new BigDecimal("2400"), "c3-ETHUSDT-1-sl2", true);
        Req r2 = reqs.stream().filter(x -> x.path.equals("/fapi/v1/algoOrder")).findFirst().get();
        assertEquals("true", r2.param("closePosition"));
        assertNull("closePosition cam gui kem reduceOnly", r2.param("reduceOnly"));
        assertNull(r2.param("quantity"));
        assertTrue(cp.isClosePosition());
        // huy theo clientAlgoId
        handler = x -> new Resp(200, "{\"algoId\":777,\"clientAlgoId\":\"c3-ETHUSDT-1-sl1\",\"code\":\"200\",\"msg\":\"success\"}");
        OrderInfo cx = c.cancelStop("ETHUSDT", "c3-ETHUSDT-1-sl1");
        assertEquals(OrderStatus.CANCELED, cx.getStatus());
        assertEquals("DELETE", reqs.get(reqs.size() - 1).method);
        assertEquals("c3-ETHUSDT-1-sl1", reqs.get(reqs.size() - 1).param("clientAlgoId"));
    }

    @Test
    public void accountModeAndConfigParsing() {
        handler = r -> {
            switch (r.path) {
                case "/fapi/v3/account":
                    return new Resp(200, "{\"totalWalletBalance\":\"9977.8871\",\"totalMarginBalance\":\"9977.8871\",\"availableBalance\":\"9977.8871\","
                            + "\"totalUnrealizedProfit\":\"0\",\"assets\":[{\"asset\":\"BFUSD\",\"walletBalance\":\"10000\",\"marginBalance\":\"10000\","
                            + "\"availableBalance\":\"10000\",\"unrealizedProfit\":\"0\"},{\"asset\":\"USDT\",\"walletBalance\":\"0\",\"marginBalance\":\"0\","
                            + "\"availableBalance\":\"0\",\"unrealizedProfit\":\"0\"}]}");
                case "/fapi/v1/positionSide/dual": return new Resp(200, "{\"dualSidePosition\":false}");
                case "/fapi/v1/symbolConfig":
                    return new Resp(200, "[{\"symbol\":\"BTCUSDT\",\"marginType\":\"CROSSED\",\"isAutoAddMargin\":\"false\",\"leverage\":1,\"maxNotionalValue\":\"1000000\"}]");
                case "/fapi/v1/leverage": return new Resp(200, "{\"leverage\":1,\"maxNotionalValue\":\"1000000\",\"symbol\":\"BTCUSDT\"}");
                case "/fapi/v1/marginType": return new Resp(400, err(-4046, "No need to change margin type."));
                case "/fapi/v3/positionRisk":
                    return new Resp(200, "[{\"symbol\":\"ETHUSDT\",\"positionSide\":\"BOTH\",\"positionAmt\":\"0.250\",\"entryPrice\":\"2500\","
                            + "\"markPrice\":\"2510\",\"unRealizedProfit\":\"2.5\",\"notional\":\"627.5\",\"updateTime\":1761400000000}]");
                case "/fapi/v1/listenKey": return new Resp(200, "{\"listenKey\":\"lk123\"}");
                default: return new Resp(404, err(-1, "x"));
            }
        };
        C3LiveClient c = client();
        AccountSnapshot a = c.account();
        assertEquals(0, new BigDecimal("9977.8871").compareTo(a.getTotalMarginBalance()));
        assertEquals(0, new BigDecimal("10000").compareTo(a.asset("BFUSD").get().getWalletBalance()));
        assertFalse(c.dualSidePosition());
        SymbolConfig sc = c.symbolConfig("BTCUSDT");
        assertTrue(sc.isCrossed());
        assertEquals(1, sc.getLeverage());
        assertEquals(1, c.setLeverage("BTCUSDT", 1));
        c.setMarginType("BTCUSDT", "CROSSED"); // -4046 = thanh cong
        assertEquals(0, new BigDecimal("0.25").compareTo(c.positions().get(0).getPositionAmt()));
        assertEquals("lk123", c.startUserStream());
        Req lk = reqs.stream().filter(x -> x.path.equals("/fapi/v1/listenKey")).findFirst().get();
        assertEquals(KEY, lk.apiKey);
        assertNull("listenKey khong ky", lk.param("signature"));
        assertTrue(auditLines.isEmpty());
    }

    // --------------------------------------------------------------- key file

    @Test
    public void keyFileChecks() throws Exception {
        java.nio.file.Path dir = java.nio.file.Files.createTempDirectory("c3k");
        java.nio.file.Files.setPosixFilePermissions(dir, java.nio.file.attribute.PosixFilePermissions.fromString("rwx------"));
        java.nio.file.Path f = dir.resolve("keys.env");
        java.nio.file.Files.write(f, ("# c3 live\nexport C3_LIVE_API_KEY=" + KEY + "\nC3_LIVE_API_SECRET='" + SECRET + "'\n").getBytes(StandardCharsets.UTF_8));
        String me = System.getProperty("user.name");
        java.nio.file.Files.setPosixFilePermissions(f, java.nio.file.attribute.PosixFilePermissions.fromString("rw-------"));
        C3LiveKeys k = C3LiveKeys.load(f, me);
        assertEquals(KEY, k.apiKey());
        assertFalse(k.toString().contains(KEY));
        List<String> msgs = new ArrayList<>();
        // quyen 644
        java.nio.file.Files.setPosixFilePermissions(f, java.nio.file.attribute.PosixFilePermissions.fromString("rw-r--r--"));
        msgs.add(expectKeyFail(f, me, "rw-r--r--"));
        // quyen 400 cung bi tu choi (yeu cau dung 600)
        java.nio.file.Files.setPosixFilePermissions(f, java.nio.file.attribute.PosixFilePermissions.fromString("r--------"));
        msgs.add(expectKeyFail(f, me, "600"));
        java.nio.file.Files.setPosixFilePermissions(f, java.nio.file.attribute.PosixFilePermissions.fromString("rw-------"));
        // sai owner
        if (!"root".equals(me)) msgs.add(expectKeyFail(f, "root", "owner"));
        // thieu file
        msgs.add(expectKeyFail(dir.resolve("none.env"), me, "khong ton tai"));
        // symlink
        java.nio.file.Path ln = dir.resolve("ln.env");
        java.nio.file.Files.createSymbolicLink(ln, f);
        msgs.add(expectKeyFail(ln, me, "symlink"));
        // thieu secret
        java.nio.file.Path g = dir.resolve("g.env");
        java.nio.file.Files.write(g, ("C3_LIVE_API_KEY=" + KEY + "\n").getBytes(StandardCharsets.UTF_8));
        java.nio.file.Files.setPosixFilePermissions(g, java.nio.file.attribute.PosixFilePermissions.fromString("rw-------"));
        msgs.add(expectKeyFail(g, me, "C3_LIVE_API_SECRET"));
        // thu muc cha group-writable
        java.nio.file.Files.setPosixFilePermissions(dir, java.nio.file.attribute.PosixFilePermissions.fromString("rwxrwx---"));
        msgs.add(expectKeyFail(f, me, "thu muc cha"));
        java.nio.file.Files.setPosixFilePermissions(dir, java.nio.file.attribute.PosixFilePermissions.fromString("rwx------"));
        // create(): khong tao client khi file sai
        try {
            C3LiveClient.create(C3LiveClientConfig.builder().keysFile(dir.resolve("none.env")).keysOwner(me).build(), RateGuard.defaults());
            fail();
        } catch (C3LiveKeyException e) { msgs.add(e.getMessage()); }
        for (String m : msgs) { assertFalse(m, m.contains(KEY)); assertFalse(m, m.contains(SECRET)); }
        for (java.nio.file.Path p : new java.nio.file.Path[]{ln, g, f}) java.nio.file.Files.deleteIfExists(p);
        java.nio.file.Files.deleteIfExists(dir);
    }

    private static String expectKeyFail(java.nio.file.Path f, String owner, String mustContain) {
        try {
            C3LiveKeys.load(f, owner);
            fail("phai tu choi: " + mustContain);
            return null;
        } catch (C3LiveKeyException e) {
            assertTrue(e.getMessage(), e.getMessage().contains(mustContain));
            return e.getMessage();
        }
    }

    @Test
    public void configFromEnvDefaults() {
        C3LiveClientConfig d = C3LiveClientConfig.fromEnv(k -> null);
        assertEquals("/root/.config/c3live/keys.env", d.keysFile().toString());
        assertEquals("root", d.keysOwner());
        assertEquals("https://fapi.binance.com", d.baseUrl());
        Map<String, String> env = new HashMap<>();
        env.put("LIVE_C3_KEYS_FILE", "/tmp/x.env");
        env.put("LIVE_C3_RECV_WINDOW_MS", "abc");
        env.put("LIVE_C3_STOP_WORKING_TYPE", "mark_price");
        C3LiveClientConfig e = C3LiveClientConfig.fromEnv(env::get);
        assertEquals("/tmp/x.env", e.keysFile().toString());
        assertEquals(5_000L, e.recvWindowMs());
        assertEquals("MARK_PRICE", e.stopWorkingType());
        assertFalse(e.toString().contains("SECRET"));
        assertTrue(Collections.disjoint(Collections.singleton(e.toString()), Collections.singleton(KEY)));
    }
}
