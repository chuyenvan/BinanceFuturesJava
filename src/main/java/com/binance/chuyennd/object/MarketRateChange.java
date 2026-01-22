package com.binance.chuyennd.object;

import java.io.Serializable;

public class MarketRateChange implements Serializable {
    public Float rateDownAvg;
    public Float rateDown15MAvg;
    public Float rateUpAvg;


    public MarketRateChange(Float rateDownAvg, Float rateDown15MAvg, Float rateUpAvg) {
        this.rateDownAvg = rateDownAvg;
        this.rateDown15MAvg = rateDown15MAvg;
        this.rateUpAvg = rateUpAvg;
    }
}
