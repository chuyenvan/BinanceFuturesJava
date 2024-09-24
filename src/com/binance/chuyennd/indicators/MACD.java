package com.binance.chuyennd.indicators;


import com.binance.chuyennd.config.Labels;
import com.binance.chuyennd.object.IndicatorEntry;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.MACDEntry;
import com.binance.chuyennd.object.sw.KlineObjectSimple;

import java.util.List;

/**
 * MACD - Moving Average Convergence / Divergence
 */
public class MACD {

    public static MACDEntry[] calculate(List<KlineObjectNumber> candles, int fastPeriods, int slowPeriods, int signalPeriods) {
        if (candles.size() < slowPeriods + signalPeriods) {
            throw new IllegalArgumentException(Labels.NOT_ENOUGH_VALUES);
        }

        if (fastPeriods >= slowPeriods) {
            throw new IllegalArgumentException("'slowPeriods' must be greater than 'fastPeriods'");
        }

        // ---- ema fast & slow -------------------

        IndicatorEntry[] emaFast = ExponentialMovingAverage.calculate(candles, fastPeriods);
        IndicatorEntry[] emaSlow = ExponentialMovingAverage.calculate(candles, slowPeriods);
        int baseFast = emaFast.length - emaSlow.length;

        // ---- macd ------------------------------
        double[] macd = new double[emaSlow.length];
        for (int i = 0; i < emaSlow.length; i++) {
            macd[i] = emaFast[i + baseFast].getValue() - emaSlow[i].getValue();
        }

        // ---- Signal ----------------------------
        double[] signals = ExponentialMovingAverage.calculate(macd, signalPeriods);
        int baseMacd = macd.length - signals.length;
        int baseCandles = candles.size() - signals.length;

        // ---- Create response -------------------
        MACDEntry[] macdEntries = new MACDEntry[signals.length];

        // ---- Historam --------------------------
        for (int i = 0; i < signals.length; i++) {
            double histogram = macd[i + baseMacd] - signals[i];
            macdEntries[i] = new MACDEntry(candles.get(i + baseCandles), emaFast[i + baseFast].getValue(),
                    emaSlow[i + baseMacd].getValue(), macd[i + baseMacd], signals[i], histogram);
        }

        return macdEntries;
    }
    public static MACDEntry[] calculateSimple(List<KlineObjectSimple> candles, int fastPeriods, int slowPeriods, int signalPeriods) {
        if (candles.size() < slowPeriods + signalPeriods) {
            throw new IllegalArgumentException(Labels.NOT_ENOUGH_VALUES);
        }

        if (fastPeriods >= slowPeriods) {
            throw new IllegalArgumentException("'slowPeriods' must be greater than 'fastPeriods'");
        }

        // ---- ema fast & slow -------------------

        IndicatorEntry[] emaFast = ExponentialMovingAverage.calculateSimple(candles, fastPeriods);
        IndicatorEntry[] emaSlow = ExponentialMovingAverage.calculateSimple(candles, slowPeriods);
        int baseFast = emaFast.length - emaSlow.length;

        // ---- macd ------------------------------
        double[] macd = new double[emaSlow.length];
        for (int i = 0; i < emaSlow.length; i++) {
            macd[i] = emaFast[i + baseFast].getValue() - emaSlow[i].getValue();
        }

        // ---- Signal ----------------------------
        double[] signals = ExponentialMovingAverage.calculate(macd, signalPeriods);
        int baseMacd = macd.length - signals.length;
        int baseCandles = candles.size() - signals.length;

        // ---- Create response -------------------
        MACDEntry[] macdEntries = new MACDEntry[signals.length];

        // ---- Historam --------------------------
        for (int i = 0; i < signals.length; i++) {
            double histogram = macd[i + baseMacd] - signals[i];
            macdEntries[i] = new MACDEntry(candles.get(i + baseCandles), emaFast[i + baseFast].getValue(),
                    emaSlow[i + baseMacd].getValue(), macd[i + baseMacd], signals[i], histogram);
        }

        return macdEntries;
    }

}
