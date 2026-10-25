package com.binance.chuyennd.c3live.api;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/** [V12] exchangeInfo da parse (bat bien). Thu tu symbol giu nguyen nhu san tra ve. */
public final class ExchangeInfo {
    private final long serverTime;
    private final List<RateLimitSpec> rateLimits;
    private final Map<String, SymbolMeta> symbols;

    public ExchangeInfo(long serverTime, List<RateLimitSpec> rateLimits, List<SymbolMeta> symbols) {
        this.serverTime = serverTime;
        this.rateLimits = rateLimits == null ? Collections.emptyList()
                : Collections.unmodifiableList(new ArrayList<>(rateLimits));
        Map<String, SymbolMeta> m = new LinkedHashMap<>();
        if (symbols != null) for (SymbolMeta s : symbols) if (s != null && s.getSymbol() != null) m.put(s.getSymbol(), s);
        this.symbols = Collections.unmodifiableMap(m);
    }

    public long getServerTime() { return serverTime; }
    public List<RateLimitSpec> getRateLimits() { return rateLimits; }
    public Map<String, SymbolMeta> getSymbols() { return symbols; }
    public Optional<SymbolMeta> symbol(String s) { return Optional.ofNullable(symbols.get(s)); }

    /** Tim gioi han dau tien khop type (REQUEST_WEIGHT/ORDERS) + cua so ms; empty neu khong co. */
    public Optional<RateLimitSpec> rateLimit(String type, long windowMs) {
        for (RateLimitSpec r : rateLimits) if (r.getRateLimitType().equals(type) && r.windowMs() == windowMs) return Optional.of(r);
        return Optional.empty();
    }

    @Override
    public String toString() { return "ExchangeInfo{serverTime=" + serverTime + " symbols=" + symbols.size() + " rateLimits=" + rateLimits + "}"; }
}
