package com.binance.client.model.trade;

import com.binance.client.constant.BinanceApiConstants;
import org.apache.commons.lang3.builder.ToStringBuilder;

import java.math.BigDecimal;

public class Leverage {

    private BigDecimal leverage;

    private Float maxNotionalValue;

    private String symbol;

    public BigDecimal getLeverage() {
        return leverage;
    }

    public void setLeverage(BigDecimal leverage) {
        this.leverage = leverage;
    }

    public Float getMaxNotionalValue() {
        return maxNotionalValue;
    }

    public void setMaxNotionalValue(Float maxNotionalValue) {
        this.maxNotionalValue = maxNotionalValue;
    }

    public String getSymbol() {
        return symbol;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    @Override
    public String toString() {
        return new ToStringBuilder(this, BinanceApiConstants.TO_STRING_BUILDER_STYLE).append("leverage", leverage)
                .append("maxNotionalValue", maxNotionalValue).append("symbol", symbol).toString();
    }
}
