/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.object;

import java.util.List;

/**
 *
 * @author pc
 */
public class FilterSymbolWIthRateChange {

    public String symbol;
    public Double currentPrice;
    public Double maxPriceInMonth;
    public Double maxPriceTotal;
    public Double minPriceInMonth;
    public Double minPriceTotal;
    public Double volume;
    public Double rateTotal;
    public Double rateWithMinAndCurrent;
    public List<Double> maxPriceByDate;

    @Override
    public String toString() {
        StringBuilder builder = new StringBuilder();
        builder.append(symbol).append(",");
        builder.append(currentPrice).append(",");
        builder.append(maxPriceInMonth).append(",");
        builder.append(maxPriceTotal).append(",");
        builder.append(minPriceInMonth).append(",");
        builder.append(minPriceTotal).append(",");
        builder.append(volume).append(",");
        builder.append(rateTotal).append(",");
        builder.append(rateWithMinAndCurrent).append(",");
        builder.append(maxPriceByDate).append(",");
        return builder.toString();
    }
}
