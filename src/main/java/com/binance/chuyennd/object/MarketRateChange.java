package com.binance.chuyennd.object;

import java.io.Serializable;

public class MarketRateChange implements Serializable {
    public Double rateDownAvg;
    public Double rateDown15MAvg;
    public Double rateUpAvg;


    public MarketRateChange(Double rateDownAvg, Double rateDown15MAvg, Double rateUpAvg) {
        this.rateDownAvg = rateDownAvg;
        this.rateDown15MAvg = rateDown15MAvg;
        this.rateUpAvg = rateUpAvg;
    }
}
