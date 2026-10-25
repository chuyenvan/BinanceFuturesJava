package com.binance.chuyennd.c3live.api;

import java.math.BigDecimal;

/** [V12] Vi the 1 symbol (one-way: positionSide = BOTH). positionAmt > 0 = long. */
public final class PositionInfo {
    private final String symbol;
    private final String positionSide;
    private final BigDecimal positionAmt;
    private final BigDecimal entryPrice;
    private final BigDecimal markPrice;
    private final BigDecimal unrealizedProfit;
    private final BigDecimal notional;
    private final long updateTimeMs;

    public PositionInfo(String symbol, String positionSide, BigDecimal positionAmt, BigDecimal entryPrice,
                        BigDecimal markPrice, BigDecimal unrealizedProfit, BigDecimal notional, long updateTimeMs) {
        this.symbol = symbol;
        this.positionSide = positionSide;
        this.positionAmt = positionAmt == null ? BigDecimal.ZERO : positionAmt;
        this.entryPrice = entryPrice;
        this.markPrice = markPrice;
        this.unrealizedProfit = unrealizedProfit;
        this.notional = notional;
        this.updateTimeMs = updateTimeMs;
    }

    public String getSymbol() { return symbol; }
    public String getPositionSide() { return positionSide; }
    public BigDecimal getPositionAmt() { return positionAmt; }
    public BigDecimal getEntryPrice() { return entryPrice; }
    public BigDecimal getMarkPrice() { return markPrice; }
    public BigDecimal getUnrealizedProfit() { return unrealizedProfit; }
    public BigDecimal getNotional() { return notional; }
    public long getUpdateTimeMs() { return updateTimeMs; }
    public boolean isFlat() { return positionAmt.signum() == 0; }

    @Override
    public String toString() {
        return "PositionInfo{" + symbol + " " + positionSide + " amt=" + positionAmt + " entry=" + entryPrice
                + " mark=" + markPrice + " upnl=" + unrealizedProfit + "}";
    }
}
