package com.binance.chuyennd.c3live.api;

import java.math.BigDecimal;

/** [V12] So du 1 tai san trong vi Futures (USDT, BFUSD ...). */
public final class AssetBalance {
    private final String asset;
    private final BigDecimal walletBalance;
    private final BigDecimal marginBalance;
    private final BigDecimal availableBalance;
    private final BigDecimal unrealizedProfit;

    public AssetBalance(String asset, BigDecimal walletBalance, BigDecimal marginBalance,
                        BigDecimal availableBalance, BigDecimal unrealizedProfit) {
        this.asset = asset;
        this.walletBalance = walletBalance;
        this.marginBalance = marginBalance;
        this.availableBalance = availableBalance;
        this.unrealizedProfit = unrealizedProfit;
    }

    public String getAsset() { return asset; }
    public BigDecimal getWalletBalance() { return walletBalance; }
    public BigDecimal getMarginBalance() { return marginBalance; }
    public BigDecimal getAvailableBalance() { return availableBalance; }
    public BigDecimal getUnrealizedProfit() { return unrealizedProfit; }

    @Override
    public String toString() {
        return "AssetBalance{" + asset + " wallet=" + walletBalance + " margin=" + marginBalance
                + " avail=" + availableBalance + "}";
    }
}
