package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.rate.RateGuard;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.BiConsumer;
import java.util.function.Consumer;
import java.util.function.LongSupplier;

/**
 * [V12 R4 R1/R2/R3] Loc user-data stream cua TAI KHOAN CHINH truoc lop c3 ({@code FillAccounting}) — nhu
 * {@code CanaryEngine.scopeFilter} (3f) nhung theo so c3 thay vi 2 symbol co dinh:
 * <ul>
 *   <li>ORDER_TRADE_UPDATE: cid c3 => qua; lenh san tu dong vi the (autoclose/ADL/delist) tren symbol c3 dang giu => qua;
 *       khop cua stop c3 da kich (orderId = ai cua ALGO_UPDATE c3s-, hoac ot STOP_MARKET khi cum co stop va symbol khong co
 *       algo khong-c3) => qua. Con lai = LEGACY: BO (khong bao gio vao so c3, khong canh bao "fill la", khong chan (A));
 *       neu tren symbol c3 dang giu: KHOP => MERGED ngay (R2), chua khop => LEGACY-busy (chan DCA).</li>
 *   <li>ALGO_UPDATE: c3s- => qua (+ nho ai; X=CANCELED/EXPIRED => bao bo bao ve stop R6); khong-c3 => BO (+ busy neu symbol c3).</li>
 *   <li>ACCOUNT_UPDATE: BO mang so du "B" (funding/chuyen tien la cua CA tai khoan — funding c3 lay theo symbol qua income);
 *       mang "P" chi giu symbol c3 dang giu (am / &gt; can tren c3 => nghi MERGED, am thi bo); symbol khong giu => bo.</li>
 *   <li>ACCOUNT_CONFIG_UPDATE (leverage) / TRADE_LITE: chi symbol/cid c3.</li>
 * </ul>
 * Khong bao gio nem: JSON hong => tra nguyen van (UserStreamEvents tu bo qua).
 */
public final class C3StreamScope {

    private static final Logger LOG = LoggerFactory.getLogger(C3StreamScope.class);
    static final long LOG_EVERY_MS = 600_000L;

    private final C3Scope scope;
    private final LiveBookC3 book;
    private final LongSupplier clock;
    private volatile BiConsumer<String, String> foreignFill = (s, d) -> { };
    private volatile Consumer<String> suspect = s -> { };
    private volatile BiConsumer<String, Long> stopTerminal = (s, t) -> { };
    private final Map<String, Boolean> c3AlgoOrderIds = Collections.synchronizedMap(new LinkedHashMap<String, Boolean>() {
        private static final long serialVersionUID = 1L;

        @Override
        protected boolean removeEldestEntry(Map.Entry<String, Boolean> e) {
            return size() > 2000;
        }
    });
    private final Set<String> foreignAlgoSyms = ConcurrentHashMap.newKeySet();
    private final Map<String, Long> lastLog = new ConcurrentHashMap<>();
    private final AtomicLong passed = new AtomicLong();
    private final AtomicLong dropped = new AtomicLong();
    /** [V12 R4b MINOR-1] gateway (pham vi c3) de xac nhan khop stop c3 bang queryStop c3s- (actualOrderId). */
    private volatile ExchangeGateway gw;
    private volatile java.util.function.LongConsumer sleeper = ms -> {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
        }
    };
    static final int STOP_CONFIRM_TRIES = 3;
    static final long STOP_CONFIRM_GAP_MS = 300L;

    public void setGateway(ExchangeGateway g) {
        this.gw = g;
    }

    public void setSleeper(java.util.function.LongConsumer s) {
        if (s != null) this.sleeper = s;
    }

    public C3StreamScope(C3Scope scope, LiveBookC3 book, LongSupplier clock) {
        this.scope = scope;
        this.book = book;
        this.clock = clock == null ? System::currentTimeMillis : clock;
    }

    /** Lenh khong-c3 KHOP tren symbol c3 dang giu => MERGED (R2). */
    public void setForeignFillSink(BiConsumer<String, String> s) {
        this.foreignFill = s == null ? (a, b) -> { } : s;
    }

    /** Vi the stream &gt; can tren c3 / am tren symbol c3 => nghi MERGED (doc REST xac nhan). */
    public void setSuspectSink(Consumer<String> s) {
        this.suspect = s == null ? x -> { } : s;
    }

    /** Stop c3s- bi san ket thuc (CANCELED/EXPIRED) => R6 dat lai trong han. */
    public void setStopTerminalSink(BiConsumer<String, Long> s) {
        this.stopTerminal = s == null ? (a, b) -> { } : s;
    }

    public long passedCount() {
        return passed.get();
    }

    public long droppedCount() {
        return dropped.get();
    }

    /** @return text (co the da sua) de chuyen cho lop c3, hoac null = BO. */
    public String filter(String text) {
        JsonObject o;
        try {
            JsonElement el = JsonParser.parseString(text);
            if (!el.isJsonObject()) return pass(text);
            o = el.getAsJsonObject();
        } catch (RuntimeException e) {
            return pass(text);
        }
        String e = str(o, "e");
        if (e == null) return pass(text);
        long now = clock.getAsLong();
        try {
            switch (e) {
                case "ORDER_TRADE_UPDATE":
                    return order(text, o, obj(o, "o"), now);
                case "ALGO_UPDATE":
                    return algo(text, obj(o, "o"), now);
                case "TRADE_LITE": {
                    String c = str(o, "c");
                    if (C3Scope.isC3Cid(c)) return pass(text);
                    scope.touchLegacy(str(o, "s"), now);
                    return drop();
                }
                case "ACCOUNT_UPDATE":
                    return account(o);
                case "ACCOUNT_CONFIG_UPDATE": {
                    JsonObject ac = obj(o, "ac");
                    if (ac == null) return pass(text);
                    String s = str(ac, "s");
                    return s == null || scope.related(s) ? pass(text) : drop();
                }
                default:
                    return pass(text);
            }
        } catch (RuntimeException ex) {
            LOG.error("[C3-LIVE-SCOPE] loi loc su kien {}: {} => BO (fail-closed)", e, ex.toString());
            return drop();
        }
    }

    private String order(String text, JsonObject root, JsonObject x, long now) {
        if (x == null) return pass(text);
        String s = str(x, "s");
        String c = str(x, "c");
        if (C3Scope.isC3Cid(c)) return pass(c3Rp(text, root, x, s));
        boolean held = scope.held(s);
        if (held && C3Scope.isExchangeCloseCid(c)) return pass(c3Rp(text, root, x, s));
        if (held && isC3StopFill(s, str(x, "i"), str(x, "ot"))) return pass(c3Rp(text, root, x, s));
        scope.touchLegacy(s, now);
        if (held) {
            String xt = str(x, "x");
            String detail = "lenh khong-c3 " + c + " " + str(x, "S") + " X=" + str(x, "X") + " x=" + xt + " l=" + str(x, "l");
            if ("TRADE".equals(xt)) {
                LOG.error("[C3-LIVE-SCOPE] {} {} KHOP tren symbol c3 dang giu => MERGED", s, detail);
                foreignFill.accept(s, detail);
            } else {
                scope.markBusy(s, detail);
                logThrottled(s, "[C3-LIVE-SCOPE] " + s + " " + detail + " tren symbol c3 dang giu => LEGACY-busy (chan DCA)");
            }
        }
        return drop();
    }

    /**
     * [V12 R4b MINOR-1] Khop cid khong-c3 la khop cua stop c3 da kich CHI KHI: orderId = ai cua ALGO_UPDATE c3s-, hoac queryStop
     * c3s- (stop active/pending/cu cua cum) tra actualOrderId = orderId (lan khan cap, thu toi da 3 lan cach 300 ms). Con lai =
     * khop LEGACY (=> MERGED).
     */
    private boolean isC3StopFill(String s, String orderId, String ot) {
        if (orderId != null && c3AlgoOrderIds.containsKey(orderId)) return true;
        if (orderId == null || ot == null || !(ot.equalsIgnoreCase("STOP_MARKET") || ot.equalsIgnoreCase("STOP"))) return false;
        ExchangeGateway g = gw;
        Optional<LiveBookC3.ClusterView> c = book.cluster(s);
        if (g == null || !c.isPresent()) return false;
        java.util.Set<String> cids = new java.util.LinkedHashSet<>();
        if (c.get().stopClientAlgoId != null) cids.add(c.get().stopClientAlgoId);
        if (c.get().pendingStopCid != null) cids.add(c.get().pendingStopCid);
        cids.addAll(c.get().orphanStops);
        if (cids.isEmpty()) return false;
        for (int t = 0; t < STOP_CONFIRM_TRIES; t++) {
            if (t > 0) sleeper.accept(STOP_CONFIRM_GAP_MS);
            for (String cid : cids) {
                try (RateGuard.Lane lane = RateGuard.emergencyLane()) {
                    Optional<OrderInfo> q = g.queryStop(s, cid);
                    String ai = q.isPresent() ? q.get().getActualOrderId() : null;
                    if (ai != null && orderId.equals(ai.trim())) {
                        c3AlgoOrderIds.put(orderId, Boolean.TRUE);
                        LOG.info("[C3-LIVE-SCOPE] {} khop {} = stop c3 {} (xac nhan queryStop)", s, orderId, cid);
                        return true;
                    }
                } catch (RuntimeException e) {
                    LOG.warn("[C3-LIVE-SCOPE] {} queryStop {} loi {}", s, cid, e.toString());
                }
            }
        }
        return false;
    }

    /**
     * [V12 R4b MINOR-3] Symbol MERGED: rp cua san tinh tren gia vao LAN LEGACY => thay bang PnL c3 = (gia khop - gia vao so c3) x
     * qty (BAN), 0 (MUA). Khong MERGED => giu nguyen rp san.
     */
    private String c3Rp(String text, JsonObject root, JsonObject x, String s) {
        if (s == null || !scope.isMerged(s) || !"TRADE".equals(str(x, "x"))) return text;
        Optional<LiveBookC3.ClusterView> c = book.cluster(s);
        BigDecimal l = dec(x, "l");
        BigDecimal px = dec(x, "L");
        BigDecimal rp = BigDecimal.ZERO;
        if ("SELL".equals(str(x, "S")) && c.isPresent() && c.get().avgPrice > 0d && l != null && px != null) {
            rp = px.subtract(BigDecimal.valueOf(c.get().avgPrice)).multiply(l);
        }
        LOG.info("[C3-LIVE-SCOPE] {} MERGED: rp san {} => rp c3 {} (gia vao so c3)", s, str(x, "rp"), rp.toPlainString());
        x.addProperty("rp", rp.toPlainString());
        return root.toString();
    }

    private String algo(String text, JsonObject x, long now) {
        if (x == null) return pass(text);
        String s = str(x, "s");
        String caid = str(x, "caid");
        if (C3Scope.isC3AlgoCid(caid)) {
            String ai = str(x, "ai");
            if (ai != null && !ai.isEmpty() && !"0".equals(ai)) c3AlgoOrderIds.put(ai, Boolean.TRUE);
            String st = str(x, "X");
            if (s != null && ("CANCELED".equals(st) || "EXPIRED".equals(st))) stopTerminal.accept(s, now);
            return pass(text);
        }
        scope.touchLegacy(s, now);
        if (s != null && scope.held(s)) {
            foreignAlgoSyms.add(s);
            scope.markBusy(s, "algo khong-c3 " + caid + " X=" + str(x, "X"));
            logThrottled(s, "[C3-LIVE-SCOPE] " + s + " algo khong-c3 " + caid + " tren symbol c3 dang giu => LEGACY-busy");
        }
        return drop();
    }

    private String account(JsonObject o) {
        JsonObject a = obj(o, "a");
        if (a == null) return pass(o.toString());
        if (a.has("B")) a.add("B", new JsonArray());   // so du = CA tai khoan: khong vao so c3
        if (a.has("P") && a.get("P").isJsonArray()) {
            JsonArray keep = new JsonArray();
            for (JsonElement pe : a.getAsJsonArray("P")) {
                if (!pe.isJsonObject()) continue;
                JsonObject p = pe.getAsJsonObject();
                String s = str(p, "s");
                if (s == null || !scope.held(s)) continue;   // LEGACY / symbol khong giu: REST (lop B) lo, khong chan (A) qua stream
                BigDecimal pa = dec(p, "pa");
                if (pa == null) continue;
                scope.noteRawAmt(s, pa);
                if (pa.signum() < 0) {
                    suspect.accept(s);
                    continue;
                }
                if (pa.compareTo(scope.c3UpperQty(s).add(C3Scope.EPS)) > 0) suspect.accept(s);
                keep.add(p);
            }
            a.add("P", keep);
        }
        return pass(o.toString());
    }

    private String pass(String t) {
        passed.incrementAndGet();
        return t;
    }

    private String drop() {
        dropped.incrementAndGet();
        return null;
    }

    private void logThrottled(String sym, String m) {
        long now = clock.getAsLong();
        Long last = lastLog.get(sym);
        if (last != null && now - last < LOG_EVERY_MS) return;
        lastLog.put(sym, now);
        LOG.warn("{}", m);
    }

    private static JsonObject obj(JsonObject o, String k) {
        return o != null && o.has(k) && o.get(k).isJsonObject() ? o.getAsJsonObject(k) : null;
    }

    private static String str(JsonObject o, String k) {
        if (o == null || !o.has(k) || o.get(k).isJsonNull()) return null;
        JsonElement e = o.get(k);
        return e.isJsonPrimitive() ? e.getAsString() : null;
    }

    private static BigDecimal dec(JsonObject o, String k) {
        String s = str(o, k);
        if (s == null || s.trim().isEmpty()) return null;
        try {
            return new BigDecimal(s.trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
