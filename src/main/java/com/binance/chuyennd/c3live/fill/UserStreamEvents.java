package com.binance.chuyennd.c3live.fill;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * [V12 C7] Bo phan tich su kien user-data stream USD-M (tai khoan con). Thuan (khong mang) de test bang JSON gia.
 * <ul>
 *   <li>{@code ORDER_TRADE_UPDATE} (o.s/c/S/o/ot/x/X/i/l/L/z/ap/n/N/rp/R/cp/sp/T)</li>
 *   <li>{@code ACCOUNT_UPDATE} (a.m ly do; a.B[] {a, wb, cw, bc}; a.P[] {s, pa, ep, up, ps})</li>
 *   <li>{@code ALGO_UPDATE} (lenh dieu kien Algo API: o.caid/aid/s/X/ai) — dinh dang CHUA XAC MINH, chi doc lenient</li>
 *   <li>{@code listenKeyExpired}</li>
 * </ul>
 * Chap nhan ca dang combined ({@code {"stream":..,"data":{..}}}). JSON hong / thieu truong => {@link Other} (khong nem).
 */
public final class UserStreamEvents {

    private UserStreamEvents() {
    }

    public abstract static class Event {
        public final String type;
        public final long eventTimeMs;

        Event(String type, long eventTimeMs) {
            this.type = type;
            this.eventTimeMs = eventTimeMs;
        }
    }

    public static final class OrderUpdate extends Event {
        public final String symbol;
        public final String clientOrderId;
        public final String side;
        public final String orderType;
        public final String origType;
        public final String execType;
        public final String status;
        public final long orderId;
        public final BigDecimal lastQty;
        public final BigDecimal lastPrice;
        public final BigDecimal cumQty;
        public final BigDecimal avgPrice;
        public final BigDecimal commission;
        public final String commissionAsset;
        public final BigDecimal realizedPnl;
        public final boolean reduceOnly;
        public final boolean closePosition;
        public final BigDecimal stopPrice;
        public final long tradeTimeMs;

        OrderUpdate(long e, JsonObject o) {
            super("ORDER_TRADE_UPDATE", e);
            this.symbol = str(o, "s");
            this.clientOrderId = str(o, "c");
            this.side = str(o, "S");
            this.orderType = str(o, "o");
            this.origType = str(o, "ot");
            this.execType = str(o, "x");
            this.status = str(o, "X");
            this.orderId = lng(o, "i");
            this.lastQty = dec(o, "l");
            this.lastPrice = dec(o, "L");
            this.cumQty = dec(o, "z");
            this.avgPrice = dec(o, "ap");
            this.commission = dec(o, "n");
            this.commissionAsset = str(o, "N");
            this.realizedPnl = dec(o, "rp");
            this.reduceOnly = bool(o, "R");
            this.closePosition = bool(o, "cp");
            this.stopPrice = dec(o, "sp");
            this.tradeTimeMs = lng(o, "T");
        }

        public boolean isBuy() {
            return "BUY".equalsIgnoreCase(side);
        }

        public boolean isTrade() {
            return "TRADE".equalsIgnoreCase(execType);
        }

        public boolean isFinal() {
            return "FILLED".equals(status) || "CANCELED".equals(status) || "EXPIRED".equals(status)
                    || "REJECTED".equals(status) || "EXPIRED_IN_MATCH".equals(status);
        }

        @Override
        public String toString() {
            return "ORDER " + symbol + " " + side + " c=" + clientOrderId + " x=" + execType + " X=" + status + " l=" + lastQty
                    + "@" + lastPrice + " z=" + cumQty + " ap=" + avgPrice + " n=" + commission + " " + commissionAsset
                    + " rp=" + realizedPnl + " ot=" + origType;
        }
    }

    public static final class Balance {
        public final String asset;
        public final BigDecimal walletBalance;
        public final BigDecimal crossWallet;
        public final BigDecimal balanceChange;

        Balance(JsonObject b) {
            this.asset = str(b, "a");
            this.walletBalance = dec(b, "wb");
            this.crossWallet = dec(b, "cw");
            this.balanceChange = dec(b, "bc");
        }
    }

    public static final class Position {
        public final String symbol;
        public final BigDecimal positionAmt;
        public final BigDecimal entryPrice;
        public final BigDecimal unrealizedPnl;
        public final String positionSide;

        Position(JsonObject p) {
            this.symbol = str(p, "s");
            this.positionAmt = dec(p, "pa");
            this.entryPrice = dec(p, "ep");
            this.unrealizedPnl = dec(p, "up");
            this.positionSide = str(p, "ps");
        }
    }

    public static final class AccountUpdate extends Event {
        public final String reason;
        public final List<Balance> balances;
        public final List<Position> positions;

        AccountUpdate(long e, JsonObject a) {
            super("ACCOUNT_UPDATE", e);
            this.reason = str(a, "m");
            List<Balance> bs = new ArrayList<>();
            if (a.has("B") && a.get("B").isJsonArray()) {
                for (JsonElement x : a.getAsJsonArray("B")) if (x.isJsonObject()) bs.add(new Balance(x.getAsJsonObject()));
            }
            List<Position> ps = new ArrayList<>();
            if (a.has("P") && a.get("P").isJsonArray()) {
                for (JsonElement x : a.getAsJsonArray("P")) if (x.isJsonObject()) ps.add(new Position(x.getAsJsonObject()));
            }
            this.balances = Collections.unmodifiableList(bs);
            this.positions = Collections.unmodifiableList(ps);
        }
    }

    public static final class AlgoUpdate extends Event {
        public final String clientAlgoId;
        public final long algoId;
        public final String symbol;
        public final String status;
        public final String actualOrderId;

        AlgoUpdate(long e, JsonObject o) {
            super("ALGO_UPDATE", e);
            this.clientAlgoId = str(o, "caid");
            this.algoId = lng(o, "aid");
            this.symbol = str(o, "s");
            this.status = str(o, "X");
            this.actualOrderId = str(o, "ai");
        }
    }

    public static final class ListenKeyExpired extends Event {
        ListenKeyExpired(long e) {
            super("listenKeyExpired", e);
        }
    }

    public static final class Other extends Event {
        public final String raw;

        Other(String type, long e, String raw) {
            super(type, e);
            this.raw = raw;
        }
    }

    /** Phan tich 1 thong diep. Khong bao gio nem; hong => Other("PARSE_ERROR"). */
    public static Event parse(String text) {
        try {
            JsonElement el = JsonParser.parseString(text);
            if (!el.isJsonObject()) return new Other("NOT_OBJECT", 0L, cut(text));
            JsonObject root = el.getAsJsonObject();
            if (root.has("data") && root.get("data").isJsonObject() && !root.has("e")) root = root.getAsJsonObject("data");
            String e = str(root, "e");
            long t = lng(root, "E");
            if ("ORDER_TRADE_UPDATE".equals(e) && root.has("o") && root.get("o").isJsonObject()) {
                return new OrderUpdate(t, root.getAsJsonObject("o"));
            }
            if ("ACCOUNT_UPDATE".equals(e) && root.has("a") && root.get("a").isJsonObject()) {
                return new AccountUpdate(t, root.getAsJsonObject("a"));
            }
            if ("ALGO_UPDATE".equals(e) && root.has("o") && root.get("o").isJsonObject()) {
                return new AlgoUpdate(t, root.getAsJsonObject("o"));
            }
            if ("listenKeyExpired".equals(e)) return new ListenKeyExpired(t);
            return new Other(e == null ? "UNKNOWN" : e, t, cut(text));
        } catch (RuntimeException ex) {
            return new Other("PARSE_ERROR", 0L, cut(text));
        }
    }

    private static String cut(String s) {
        if (s == null) return "";
        return s.length() > 300 ? s.substring(0, 300) : s;
    }

    static String str(JsonObject o, String k) {
        if (o == null || !o.has(k) || o.get(k).isJsonNull()) return null;
        JsonElement v = o.get(k);
        return v.isJsonPrimitive() ? v.getAsString() : v.toString();
    }

    static long lng(JsonObject o, String k) {
        try {
            String s = str(o, k);
            return s == null || s.isEmpty() ? 0L : Long.parseLong(s.trim());
        } catch (NumberFormatException e) {
            return 0L;
        }
    }

    static BigDecimal dec(JsonObject o, String k) {
        try {
            String s = str(o, k);
            return s == null || s.trim().isEmpty() ? BigDecimal.ZERO : new BigDecimal(s.trim());
        } catch (NumberFormatException e) {
            return BigDecimal.ZERO;
        }
    }

    static boolean bool(JsonObject o, String k) {
        String s = str(o, k);
        return s != null && "true".equalsIgnoreCase(s.trim());
    }

    /** Helper cho test/replay: so -> JsonArray. */
    static JsonArray arr() {
        return new JsonArray();
    }
}
