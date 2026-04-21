package com.binance.chuyennd.object;

import java.io.Serializable;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class MarketDataObject implements Serializable {
    public float rateDownAvg;
    public float rateDown15MAvg;
    public float rateUpAvg;
    public float rateBtc;




    public MarketDataObject(Float rateDownAvg, Float rateUpAvg, Float rateDown15MAvg) {
        this.rateDownAvg = rateDownAvg;
        this.rateUpAvg = rateUpAvg;
        this.rateDown15MAvg = rateDown15MAvg;
    }
}
