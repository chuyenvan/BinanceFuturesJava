package com.binance.chuyennd.c3live.api;

import java.math.BigDecimal;

/** [V12 3] 1 dong GET /fapi/v1/ticker/24hr (public): gia khop cuoi + quoteVolume 24h (luat chon symbol canary). */
public final class Ticker24h {
    private final String symbol;
    private final BigDecimal lastPrice;
    private final BigDecimal quoteVolume;
    private final long closeTimeMs;

    public Ticker24h(String symbol, BigDecimal lastPrice, BigDecimal quoteVolume, long closeTimeMs) {
        this.symbol = symbol;
        this.lastPrice = lastPrice;
        this.quoteVolume = quoteVolume;
        this.closeTimeMs = closeTimeMs;
    }

    public String getSymbol() { return symbol; }
    public BigDecimal getLastPrice() { return lastPrice; }
    public BigDecimal getQuoteVolume() { return quoteVolume; }
    public long getCloseTimeMs() { return closeTimeMs; }

    @Override
    public String toString() {
        return "Ticker24h{" + symbol + " last=" + lastPrice + " quoteVol=" + quoteVolume + "}";
    }
}
