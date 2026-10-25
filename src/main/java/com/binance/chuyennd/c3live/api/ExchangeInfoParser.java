package com.binance.chuyennd.c3live.api;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.IOException;
import java.io.InputStream;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.zip.GZIPInputStream;

/**
 * [V12] Parse JSON GET /fapi/v1/exchangeInfo -> {@link ExchangeInfo}. Dung chung cho Live/Dry/Mock va fixture.
 * Chiu duoc filters dang mang phang (chuan san) hoac mang long nhau (file pin cu).
 */
public final class ExchangeInfoParser {
    private ExchangeInfoParser() { }

    @SuppressWarnings("deprecation")
    public static ExchangeInfo parse(String json) {
        if (json == null) throw new IllegalArgumentException("exchangeInfo json null");
        JsonElement rootEl = new JsonParser().parse(json);
        if (!rootEl.isJsonObject()) throw new IllegalArgumentException("exchangeInfo khong phai object");
        JsonObject root = rootEl.getAsJsonObject();
        long serverTime = optLong(root, "serverTime", 0L);
        List<RateLimitSpec> rl = new ArrayList<>();
        if (root.has("rateLimits") && root.get("rateLimits").isJsonArray()) {
            for (JsonElement e : root.getAsJsonArray("rateLimits")) {
                if (!e.isJsonObject()) continue;
                JsonObject o = e.getAsJsonObject();
                rl.add(new RateLimitSpec(optStr(o, "rateLimitType"), optStr(o, "interval"),
                        (int) optLong(o, "intervalNum", 1L), (int) optLong(o, "limit", 0L)));
            }
        }
        List<SymbolMeta> syms = new ArrayList<>();
        if (root.has("symbols") && root.get("symbols").isJsonArray()) {
            for (JsonElement e : root.getAsJsonArray("symbols")) {
                if (e.isJsonObject()) syms.add(parseSymbol(e.getAsJsonObject()));
            }
        }
        return new ExchangeInfo(serverTime, rl, syms);
    }

    /** Doc file .json hoac .json.gz (fixture owner dump). */
    public static ExchangeInfo parseFile(Path p) throws IOException {
        byte[] raw;
        if (p.getFileName().toString().endsWith(".gz")) {
            try (InputStream in = new GZIPInputStream(Files.newInputStream(p))) {
                raw = in.readAllBytes();
            }
        } else {
            raw = Files.readAllBytes(p);
        }
        return parse(new String(raw, StandardCharsets.UTF_8));
    }

    static SymbolMeta parseSymbol(JsonObject o) {
        SymbolMeta.Builder b = SymbolMeta.builder(optStr(o, "symbol"))
                .pair(optStr(o, "pair")).status(optStr(o, "status")).contractType(optStr(o, "contractType"))
                .baseAsset(optStr(o, "baseAsset")).quoteAsset(optStr(o, "quoteAsset"))
                .marginAsset(optStr(o, "marginAsset")).underlyingType(optStr(o, "underlyingType"))
                .onboardDate(optLong(o, "onboardDate", 0L)).deliveryDate(optLong(o, "deliveryDate", 0L));
        List<String> sub = new ArrayList<>();
        if (o.has("underlyingSubType") && o.get("underlyingSubType").isJsonArray()) {
            for (JsonElement e : o.getAsJsonArray("underlyingSubType")) if (e.isJsonPrimitive()) sub.add(e.getAsString());
        }
        b.underlyingSubType(sub);
        List<JsonObject> filters = new ArrayList<>();
        if (o.has("filters") && o.get("filters").isJsonArray()) flatten(o.getAsJsonArray("filters"), filters);
        for (JsonObject f : filters) {
            String t = optStr(f, "filterType");
            if (t == null) continue;
            switch (t) {
                case "PRICE_FILTER":
                    b.tickSize(optDec(f, "tickSize")).minPrice(optDec(f, "minPrice")).maxPrice(optDec(f, "maxPrice"));
                    break;
                case "LOT_SIZE":
                    b.stepSize(optDec(f, "stepSize")).minQty(optDec(f, "minQty")).maxQty(optDec(f, "maxQty"));
                    break;
                case "MARKET_LOT_SIZE":
                    b.marketStepSize(optDec(f, "stepSize")).marketMinQty(optDec(f, "minQty")).marketMaxQty(optDec(f, "maxQty"));
                    break;
                case "MIN_NOTIONAL":
                    BigDecimal n = optDec(f, "notional");
                    if (n == null) n = optDec(f, "minNotional");
                    b.minNotional(n);
                    break;
                default:
                    break;
            }
        }
        return b.build();
    }

    private static void flatten(JsonArray arr, List<JsonObject> out) {
        for (JsonElement e : arr) {
            if (e.isJsonObject()) out.add(e.getAsJsonObject());
            else if (e.isJsonArray()) flatten(e.getAsJsonArray(), out);
        }
    }

    static String optStr(JsonObject o, String k) {
        JsonElement e = o.get(k);
        if (e == null || e.isJsonNull() || !e.isJsonPrimitive()) return null;
        return e.getAsString();
    }

    static long optLong(JsonObject o, String k, long def) {
        JsonElement e = o.get(k);
        if (e == null || e.isJsonNull() || !e.isJsonPrimitive()) return def;
        try {
            return e.getAsBigDecimal().longValueExact();
        } catch (RuntimeException ex) {
            return def;
        }
    }

    static BigDecimal optDec(JsonObject o, String k) {
        JsonElement e = o.get(k);
        if (e == null || e.isJsonNull() || !e.isJsonPrimitive()) return null;
        String s = e.getAsString().trim();
        if (s.isEmpty()) return null;
        try {
            return new BigDecimal(s).stripTrailingZeros();
        } catch (NumberFormatException ex) {
            return null;
        }
    }
}
