package com.binance.chuyennd.research;

public class BalanceIndex {
    public Double balanceMin;
    public Double rateBalanceMin;
    public Long timeBalanceMin;
    public Double marginMax;
    public Double rateMarginMax;
    public Long timeMarginMax;
    public Double unProfitMax;
    public Double rateUnProfitMax;
    public Long timeRateUnProfitMax;

    public void updateIndex(Double balance, Double balanceMin, Double positionMargin, Double unrealizedProfitMin, Long timeUpdate) {
        if (rateBalanceMin == null) {
            rateBalanceMin = balanceMin / balance;
            this.balanceMin = balanceMin;
            timeBalanceMin = timeUpdate;
        } else {
            if (rateBalanceMin > balanceMin / balance) {
                rateBalanceMin = balanceMin / balance;
                this.balanceMin = balanceMin;
                timeBalanceMin = timeUpdate;
            }
        }
        if (rateMarginMax == null) {
            rateMarginMax = positionMargin / balance;
            this.marginMax = positionMargin;
            timeMarginMax = timeUpdate;
        } else {
            if (rateMarginMax < positionMargin / balance) {
                rateMarginMax = positionMargin / balance;
                this.marginMax = positionMargin;
                timeMarginMax = timeUpdate;
            }
        }
        if (rateUnProfitMax == null) {
            rateUnProfitMax = unrealizedProfitMin / balance;
            this.unProfitMax = unrealizedProfitMin;
            timeRateUnProfitMax = timeUpdate;
        } else {
            if (rateUnProfitMax > unrealizedProfitMin / balance) {
                rateUnProfitMax = unrealizedProfitMin / balance;
                this.unProfitMax = unrealizedProfitMin;
                timeRateUnProfitMax = timeUpdate;
            }
        }
    }
}
