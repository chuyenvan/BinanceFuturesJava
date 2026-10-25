package com.binance.chuyennd.c3live.canary;

import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.SymbolMeta;
import com.binance.chuyennd.c3live.api.Ticker24h;
import com.binance.chuyennd.c3live.universe.SymbolUniverseLive;

import java.math.BigDecimal;
import java.math.MathContext;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.TreeMap;
import java.util.function.Predicate;

/**
 * [V12 3] LUAT chon symbol canary (prereg GCANARY §3 + MASTER MO-3), tinh luc chay, KHONG chon tay:
 * <ol>
 *   <li>{@link SymbolUniverseLive} buyable (TRADING, PERPETUAL, quote USDT, khong TradFi/INDEX/EXCLUDE/non-ASCII, deliveryDate &gt;
 *       now + 7 ngay);</li>
 *   <li>underlyingType = COIN; deliveryDate &gt; now + 30 ngay;</li>
 *   <li>MIN_NOTIONAL &lt;= 10 USDT; tickSize / lastPrice &lt;= 0,01 %;</li>
 *   <li>khong thuoc tap LEGACY cua tai khoan chinh;</li>
 *   <li>xep {@code quoteVolume} 24h giam dan, hoa theo ten (chu cai). Hang 1 = symbol chinh (K1–K8), hang 2 = symbol phu (chi K7b).</li>
 * </ol>
 */
public final class SymbolPicker {

    public static final BigDecimal MAX_MIN_NOTIONAL = new BigDecimal("10");
    public static final BigDecimal MAX_TICK_FRAC = new BigDecimal("0.0001");
    public static final long MIN_DELIVERY_AHEAD_MS = 30L * 86_400_000L;
    public static final int TOP_KEEP = 10;

    /** 1 symbol du dieu kien (du lieu tho in cho owner/MASTER). */
    public static final class Row {
        public final String symbol;
        public final BigDecimal quoteVolume;
        public final BigDecimal lastPrice;
        public final BigDecimal tickSize;
        public final BigDecimal minNotional;

        Row(String symbol, BigDecimal quoteVolume, BigDecimal lastPrice, BigDecimal tickSize, BigDecimal minNotional) {
            this.symbol = symbol;
            this.quoteVolume = quoteVolume;
            this.lastPrice = lastPrice;
            this.tickSize = tickSize;
            this.minNotional = minNotional;
        }

        public Map<String, Object> toMap(int rank) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("rank", rank);
            m.put("symbol", symbol);
            m.put("quoteVolume24h", quoteVolume.toPlainString());
            m.put("lastPrice", lastPrice.toPlainString());
            m.put("tickSize", tickSize.toPlainString());
            m.put("tickFrac", tickSize.divide(lastPrice, MathContext.DECIMAL64).toPlainString());
            m.put("minNotional", minNotional.toPlainString());
            return m;
        }
    }

    /** Ket qua chon. main/aux null = khong du 2 symbol. */
    public static final class Pick {
        public final String main;
        public final String aux;
        public final List<Row> top;
        public final int scanned;
        public final int eligible;
        public final Map<String, Integer> rejectCounts;

        Pick(String main, String aux, List<Row> top, int scanned, int eligible, Map<String, Integer> rejectCounts) {
            this.main = main;
            this.aux = aux;
            this.top = top;
            this.scanned = scanned;
            this.eligible = eligible;
            this.rejectCounts = rejectCounts;
        }

        public List<Map<String, Object>> topMaps() {
            List<Map<String, Object>> out = new ArrayList<>();
            for (int i = 0; i < top.size(); i++) out.add(top.get(i).toMap(i + 1));
            return out;
        }
    }

    private SymbolPicker() {
    }

    public static Pick pick(ExchangeInfo ei, List<Ticker24h> tickers, Predicate<String> legacy, long now) {
        SymbolUniverseLive u = universe(ei, now);
        Map<String, Ticker24h> tk = index(tickers);
        List<Row> ok = new ArrayList<>();
        Map<String, Integer> rej = new TreeMap<>();
        int scanned = 0;
        for (SymbolMeta m : ei.getSymbols().values()) {
            scanned++;
            Optional<String> why = whyNot(u, m, tk.get(m.getSymbol()), legacy, now);
            if (why.isPresent()) {
                String k = why.get().split(" ")[0];
                rej.merge(k, 1, Integer::sum);
                continue;
            }
            Ticker24h t = tk.get(m.getSymbol());
            ok.add(new Row(m.getSymbol(), t.getQuoteVolume(), t.getLastPrice(), m.getTickSize(), m.getMinNotional()));
        }
        ok.sort((a, b) -> {
            int c = b.quoteVolume.compareTo(a.quoteVolume);
            return c != 0 ? c : a.symbol.compareTo(b.symbol);
        });
        List<Row> top = new ArrayList<>(ok.subList(0, Math.min(TOP_KEEP, ok.size())));
        String main = ok.size() >= 1 ? ok.get(0).symbol : null;
        String aux = ok.size() >= 2 ? ok.get(1).symbol : null;
        return new Pick(main, aux, top, scanned, ok.size(), rej);
    }

    /** Kiem lai 1 symbol (vd symbol trong file trang thai) con du dieu kien luat (khong xet hang). */
    public static Optional<String> whyNot(String symbol, ExchangeInfo ei, List<Ticker24h> tickers, Predicate<String> legacy,
                                          long now) {
        return whyNot(symbol, ei, tickers, legacy, now, false);
    }

    /**
     * structuralOnly = true: chi dieu kien CAU TRUC (universe, COIN, delivery, MIN_NOTIONAL, LEGACY) — dung khi kiem lai symbol
     * trong phien (gia doi lam tick/gia vuot 0,01 % KHONG lam symbol "sai luat" giua chung).
     */
    public static Optional<String> whyNot(String symbol, ExchangeInfo ei, List<Ticker24h> tickers, Predicate<String> legacy,
                                          long now, boolean structuralOnly) {
        Optional<SymbolMeta> m = ei.symbol(symbol);
        if (!m.isPresent()) return Optional.of("NOT_LISTED");
        return whyNot(universe(ei, now), m.get(), index(tickers).get(symbol), legacy, now, structuralOnly);
    }

    private static Optional<String> whyNot(SymbolUniverseLive u, SymbolMeta m, Ticker24h t, Predicate<String> legacy, long now) {
        return whyNot(u, m, t, legacy, now, false);
    }

    private static Optional<String> whyNot(SymbolUniverseLive u, SymbolMeta m, Ticker24h t, Predicate<String> legacy, long now,
                                           boolean structuralOnly) {
        String s = m.getSymbol();
        Optional<String> b = u.whyNotBuyable(s, now);
        if (b.isPresent()) return Optional.of("UNIVERSE_" + b.get());
        if (!"COIN".equals(m.getUnderlyingType() == null ? "" : m.getUnderlyingType().trim().toUpperCase(Locale.ROOT))) {
            return Optional.of("UNDERLYING_NOT_COIN");
        }
        if (m.getDeliveryDate() <= now + MIN_DELIVERY_AHEAD_MS) return Optional.of("DELIVERY_LT_30D");
        if (m.getMinNotional() == null || m.getMinNotional().compareTo(MAX_MIN_NOTIONAL) > 0) return Optional.of("MIN_NOTIONAL_GT_10");
        if (structuralOnly) return legacy != null && legacy.test(s) ? Optional.of("LEGACY") : Optional.empty();
        if (t == null || t.getLastPrice() == null || t.getLastPrice().signum() <= 0 || t.getQuoteVolume() == null) {
            return Optional.of("NO_TICKER");
        }
        if (m.getTickSize() == null || m.getTickSize().signum() <= 0
                || m.getTickSize().divide(t.getLastPrice(), MathContext.DECIMAL64).compareTo(MAX_TICK_FRAC) > 0) {
            return Optional.of("TICK_GT_0.01PCT");
        }
        if (legacy != null && legacy.test(s)) return Optional.of("LEGACY");
        return Optional.empty();
    }

    private static SymbolUniverseLive universe(ExchangeInfo ei, long now) {
        SymbolUniverseLive u = new SymbolUniverseLive(SymbolUniverseLive.Config.defaults(), () -> ei, m -> { });
        u.apply(ei, now);
        return u;
    }

    private static Map<String, Ticker24h> index(List<Ticker24h> tickers) {
        Map<String, Ticker24h> m = new HashMap<>();
        if (tickers != null) for (Ticker24h t : tickers) if (t.getSymbol() != null) m.put(t.getSymbol(), t);
        return m;
    }
}
