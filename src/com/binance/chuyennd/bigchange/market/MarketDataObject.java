package com.binance.chuyennd.bigchange.market;

import java.io.Serializable;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class MarketDataObject implements Serializable {
    public Double rateDownAvg;
    public Double rateDown15MAvg;
    public Double rateUpAvg;
    public Double rateBtc;
    public Double rateBtcUp15M;
    public Double rateBtcDown15M;
    public MarketLevelChange level;
    public List<String> symbolsTopDown;
    public TreeMap<Double, String> rate2Max;
    public TreeMap<Double, String> rate2Min;
    public Map<String, Double> symbol2PriceMax15M;


    public MarketDataObject(Double rateDownAvg, Double rateUpAvg, Double rateBtc,
                            MarketLevelChange level, List<String> symbolsTopDown) {
        this.rateDownAvg = rateDownAvg;
        this.rateUpAvg = rateUpAvg;
        this.rateBtc = rateBtc;
        this.level = level;
        this.symbolsTopDown = symbolsTopDown;

    }

}
