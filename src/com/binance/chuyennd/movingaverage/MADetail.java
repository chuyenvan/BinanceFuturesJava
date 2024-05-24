package com.binance.chuyennd.movingaverage;

import java.io.Serializable;

public class MADetail implements Serializable {
    public String symbol;
    public Double date;
    public Double priceOpen;
    public Double maxPrice;
    public Double minPrice;
    public Double priceClose;
    public Double totalUsdt;
    public Double ma20;
    public Double ma50;
    public Double ma100;
}
