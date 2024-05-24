package com.binance.chuyennd.object;


import com.binance.chuyennd.utils.Utils;

public class MACDEntry extends KlineObjectNumber {
    private double emaFast;
    private double emaSlow;
    private double macd;
    private double signal;
    private double histogram;

    public MACDEntry() {
        //
    }

    public MACDEntry(KlineObjectNumber kline) {
        startTime = kline.startTime;
        priceOpen = kline.priceOpen;
        maxPrice = kline.maxPrice;
        minPrice = kline.minPrice;
        priceClose = kline.priceClose;
        totalUsdt = kline.totalUsdt;
        endTime = kline.endTime;
    }

    public MACDEntry(KlineObjectNumber kline, double emaFast, double emaSlow, double macd, double signal, double histogram) {
        startTime = kline.startTime;
        priceOpen = kline.priceOpen;
        maxPrice = kline.maxPrice;
        minPrice = kline.minPrice;
        priceClose = kline.priceClose;
        totalUsdt = kline.totalUsdt;
        endTime = kline.endTime;

        this.emaFast = emaFast;
        this.emaSlow = emaSlow;
        this.macd = macd;
        this.signal = signal;
        this.histogram = histogram;
    }

    public double getEmaFast() {
        return emaFast;
    }

    public void setEmaFast(double emaFast) {
        this.emaFast = emaFast;
    }

    public double getEmaSlow() {
        return emaSlow;
    }

    public void setEmaSlow(double emaSlow) {
        this.emaSlow = emaSlow;
    }

    public double getMacd() {
        return macd;
    }

    public void setMacd(double macd) {
        this.macd = macd;
    }

    public double getSignal() {
        return signal;
    }

    public void setSignal(double signal) {
        this.signal = signal;
    }

    public double getHistogram() {
        return histogram;
    }

    public void setHistogram(double histogram) {
        this.histogram = histogram;
    }

    @Override
    public String toString() {
        return String.format("%s\t%f\t\t%f\t%f\t%f\t%f\t%f", Utils.normalizeDateYYYYMMDDHHmm(startTime.longValue()),
                priceClose, emaFast, emaSlow, macd, signal, histogram);
    }

}
