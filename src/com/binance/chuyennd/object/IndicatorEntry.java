package com.binance.chuyennd.object;


import com.binance.chuyennd.utils.Utils;

public class IndicatorEntry extends KlineObjectNumber {
    private double value;

    public IndicatorEntry() {
        //
    }

    public IndicatorEntry(KlineObjectNumber kline) {
        startTime = kline.startTime;
        priceOpen = kline.priceOpen;
        maxPrice = kline.maxPrice;
        minPrice = kline.minPrice;
        priceClose = kline.priceClose;
        totalUsdt = kline.totalUsdt;
        endTime = kline.endTime;
    }

    public double getValue() {
        return value;
    }

    public void setValue(double value) {
        this.value = value;
    }

    @Override
    public String toString() {
        return String.format("%s\t%f\t\t%f", Utils.normalizeDateYYYYMMDDHHmm(startTime.longValue()), priceClose, value);
    }

    // ---- STATICS -----------------------------------------------------------

    public static double[] toDoubleArray(IndicatorEntry[] entries) {
        double[] doubleValues = new double[entries.length];

        for (int i = 0; i < entries.length; i++) {
            doubleValues[i] = entries[i].getValue();
        }

        return doubleValues;
    }

}
