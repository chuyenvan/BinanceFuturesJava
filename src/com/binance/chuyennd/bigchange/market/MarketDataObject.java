package com.binance.chuyennd.bigchange.market;

import java.io.Serializable;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class MarketDataObject implements Serializable {
    public Double rateDownAvg;
    public Double rateDown15MAvg;
    public Double rateUpAvg;
    public Double rateUp15MAvg;
    public Double rateBtc;
    public Double rateBtcUp15M;
    public Double rateBtcDown15M;
    public Double volumeBtc;
    public MarketLevelChange level;
    public List<String> symbolsTopDown;
    public TreeMap<Double, String> rateDown2Symbols;
    public TreeMap<Double, String> rateUp2Symbols;
    public TreeMap<Double, String> rate2Max;
    public Map<String, Double> symbol2PriceMax15M;


    public MarketDataObject(Double rateDownAvg, Double rateUpAvg, Double rateBtc,
                            Double volumeBtc, MarketLevelChange level, List<String> symbolsTopDown) {
        this.rateDownAvg = rateDownAvg;
        this.rateUpAvg = rateUpAvg;
        this.rateBtc = rateBtc;
        this.volumeBtc = volumeBtc;
        this.level = level;
        this.symbolsTopDown = symbolsTopDown;

    }
}
