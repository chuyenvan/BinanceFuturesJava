package com.binance.chuyennd.c3live.api;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * [V12 C4/U1] 1 symbol trong exchangeInfo (USDT-M). Filter da tach san: PRICE_FILTER, LOT_SIZE, MARKET_LOT_SIZE,
 * MIN_NOTIONAL (truong "notional"). Truong thieu = null.
 */
public final class SymbolMeta {
    private final String symbol;
    private final String pair;
    private final String status;
    private final String contractType;
    private final String baseAsset;
    private final String quoteAsset;
    private final String marginAsset;
    private final String underlyingType;
    private final List<String> underlyingSubType;
    private final long onboardDate;
    private final long deliveryDate;
    private final BigDecimal tickSize;
    private final BigDecimal minPrice;
    private final BigDecimal maxPrice;
    private final BigDecimal stepSize;
    private final BigDecimal minQty;
    private final BigDecimal maxQty;
    private final BigDecimal marketStepSize;
    private final BigDecimal marketMinQty;
    private final BigDecimal marketMaxQty;
    private final BigDecimal minNotional;

    private SymbolMeta(Builder b) {
        this.symbol = b.symbol;
        this.pair = b.pair;
        this.status = b.status;
        this.contractType = b.contractType;
        this.baseAsset = b.baseAsset;
        this.quoteAsset = b.quoteAsset;
        this.marginAsset = b.marginAsset;
        this.underlyingType = b.underlyingType;
        this.underlyingSubType = b.underlyingSubType == null ? Collections.emptyList()
                : Collections.unmodifiableList(new ArrayList<>(b.underlyingSubType));
        this.onboardDate = b.onboardDate;
        this.deliveryDate = b.deliveryDate;
        this.tickSize = b.tickSize;
        this.minPrice = b.minPrice;
        this.maxPrice = b.maxPrice;
        this.stepSize = b.stepSize;
        this.minQty = b.minQty;
        this.maxQty = b.maxQty;
        this.marketStepSize = b.marketStepSize;
        this.marketMinQty = b.marketMinQty;
        this.marketMaxQty = b.marketMaxQty;
        this.minNotional = b.minNotional;
    }

    public static Builder builder(String symbol) { return new Builder().symbol(symbol); }

    public String getSymbol() { return symbol; }
    public String getPair() { return pair; }
    /** TRADING, SETTLING, CLOSE, PENDING_TRADING, PRE_DELIVERING, DELIVERING, DELIVERED ... */
    public String getStatus() { return status; }
    /** PERPETUAL, CURRENT_QUARTER, NEXT_QUARTER, (TradFi: CHUA XAC MINH, vd TRADIFI_PERPETUAL) ... */
    public String getContractType() { return contractType; }
    public String getBaseAsset() { return baseAsset; }
    public String getQuoteAsset() { return quoteAsset; }
    public String getMarginAsset() { return marginAsset; }
    /** COIN, INDEX, ... (TradFi: CHUA XAC MINH). */
    public String getUnderlyingType() { return underlyingType; }
    public List<String> getUnderlyingSubType() { return underlyingSubType; }
    public long getOnboardDate() { return onboardDate; }
    /** Perpetual binh thuong = 4133404800000 (2100-12-25); khi co lich delist san dat ngay that. 0 = khong co. */
    public long getDeliveryDate() { return deliveryDate; }
    public BigDecimal getTickSize() { return tickSize; }
    public BigDecimal getMinPrice() { return minPrice; }
    public BigDecimal getMaxPrice() { return maxPrice; }
    /** LOT_SIZE.stepSize (lenh LIMIT / STOP). */
    public BigDecimal getStepSize() { return stepSize; }
    public BigDecimal getMinQty() { return minQty; }
    public BigDecimal getMaxQty() { return maxQty; }
    /** MARKET_LOT_SIZE.stepSize (lenh MARKET). */
    public BigDecimal getMarketStepSize() { return marketStepSize; }
    public BigDecimal getMarketMinQty() { return marketMinQty; }
    public BigDecimal getMarketMaxQty() { return marketMaxQty; }
    /** MIN_NOTIONAL.notional. */
    public BigDecimal getMinNotional() { return minNotional; }

    @Override
    public String toString() {
        return "SymbolMeta{" + symbol + " " + status + " " + contractType + " " + quoteAsset + " ut=" + underlyingType
                + " sub=" + underlyingSubType + " tick=" + tickSize + " step=" + stepSize + " mstep=" + marketStepSize
                + " minN=" + minNotional + " deliv=" + deliveryDate + "}";
    }

    public static final class Builder {
        private String symbol, pair, status, contractType, baseAsset, quoteAsset, marginAsset, underlyingType;
        private List<String> underlyingSubType;
        private long onboardDate, deliveryDate;
        private BigDecimal tickSize, minPrice, maxPrice, stepSize, minQty, maxQty, marketStepSize, marketMinQty,
                marketMaxQty, minNotional;

        public Builder symbol(String v) { symbol = v; return this; }
        public Builder pair(String v) { pair = v; return this; }
        public Builder status(String v) { status = v; return this; }
        public Builder contractType(String v) { contractType = v; return this; }
        public Builder baseAsset(String v) { baseAsset = v; return this; }
        public Builder quoteAsset(String v) { quoteAsset = v; return this; }
        public Builder marginAsset(String v) { marginAsset = v; return this; }
        public Builder underlyingType(String v) { underlyingType = v; return this; }
        public Builder underlyingSubType(List<String> v) { underlyingSubType = v; return this; }
        public Builder onboardDate(long v) { onboardDate = v; return this; }
        public Builder deliveryDate(long v) { deliveryDate = v; return this; }
        public Builder tickSize(BigDecimal v) { tickSize = v; return this; }
        public Builder minPrice(BigDecimal v) { minPrice = v; return this; }
        public Builder maxPrice(BigDecimal v) { maxPrice = v; return this; }
        public Builder stepSize(BigDecimal v) { stepSize = v; return this; }
        public Builder minQty(BigDecimal v) { minQty = v; return this; }
        public Builder maxQty(BigDecimal v) { maxQty = v; return this; }
        public Builder marketStepSize(BigDecimal v) { marketStepSize = v; return this; }
        public Builder marketMinQty(BigDecimal v) { marketMinQty = v; return this; }
        public Builder marketMaxQty(BigDecimal v) { marketMaxQty = v; return this; }
        public Builder minNotional(BigDecimal v) { minNotional = v; return this; }
        public SymbolMeta build() { return new SymbolMeta(this); }
    }
}
