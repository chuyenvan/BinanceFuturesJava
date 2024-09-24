package com.binance.chuyennd.research;

public class BalanceIndex {

    public Double marginMax;
    public Double rateMarginMax;
    public Long timeMarginMax;
    public Double profitLossMax;
    public Long timeProfitLossMax;

    public Double unProfitMin;
    public Long timeUnProfitMin;


    public void updateIndex(Double balance, Double positionMargin, Long timeUpdate, Double profitLossMax, Double unrealizedProfitMin) {
        if (rateMarginMax == null || rateMarginMax < positionMargin / balance) {
            rateMarginMax = positionMargin / balance;
            this.marginMax = positionMargin;
            timeMarginMax = timeUpdate;
        }
        if (this.profitLossMax == null || this.profitLossMax > profitLossMax) {
            this.profitLossMax = profitLossMax;
            this.timeProfitLossMax = timeUpdate;
        }
        if (this.unProfitMin == null || this.unProfitMin > unrealizedProfitMin) {
            this.unProfitMin = unrealizedProfitMin;
            this.timeUnProfitMin = timeUpdate;
        }
    }
}
