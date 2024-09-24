package com.binance.chuyennd.indicators;


import com.binance.chuyennd.config.Labels;
import com.binance.chuyennd.object.IndicatorEntry;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.CandleUtils;
import com.binance.chuyennd.utils.DoubleArrayUtils;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.TreeMap;

/**
 * SMA - Simple Moving Average
 */
public class SimpleMovingAverage {
    public static final Logger LOG = LoggerFactory.getLogger(SimpleMovingAverage.class);

    public static double[] calculate(double[] values, int periods) {
        if (values.length < periods) {
            throw new IllegalArgumentException(Labels.NOT_ENOUGH_VALUES);
        }

        int len = values.length;
        double[] results = new double[len];

        for (int i = 0; i < len; i++) {
            if (i >= periods) {
                results[i] = DoubleArrayUtils.avg(values, i - periods + 1, i);
            } else {
                results[i] = 0d;
            }
        }

        return results;
    }

    public static IndicatorEntry[] calculate(List<KlineObjectNumber> candles, int periods) {
        if (candles.size() < periods) {
            return null;
        }

        int len = candles.size();
        IndicatorEntry[] smaEntries = new IndicatorEntry[len];
        for (int i = 0; i < len; i++) {
            smaEntries[i] = new IndicatorEntry(candles.get(i));
            if (i >= periods) {
                smaEntries[i].setValue(CandleUtils.avgPrice(candles, i - periods + 1, i));
            }
        }

        return smaEntries;
    }
    public static IndicatorEntry[] calculateSimple(List<KlineObjectSimple> candles, int periods) {
        if (candles.size() < periods) {
            return null;
        }

        int len = candles.size();
        IndicatorEntry[] smaEntries = new IndicatorEntry[len];
        for (int i = 0; i < len; i++) {
            smaEntries[i] = new IndicatorEntry(candles.get(i));
            if (i >= periods) {
                smaEntries[i].setValue(CandleUtils.avgPriceSimple(candles, i - periods + 1, i));
            }
        }

        return smaEntries;
    }

    public static void updateDataWithTicker(TreeMap<Long, IndicatorEntry> smaEntries, KlineObjectNumber candle, int periods) {
        if (smaEntries == null) {
            return;
        }
        if (candle != null) {
            if (smaEntries.size() - periods >= 0) {
                Long timeUpdate = Utils.getDate(candle.startTime.longValue());
                IndicatorEntry entrieUpdate;
                entrieUpdate = smaEntries.get(timeUpdate);
                if (entrieUpdate == null) {
                    LOG.info("Error update : {}", Utils.normalizeDateYYYYMMDDHHmm(candle.startTime.longValue()));
                }
                IndicatorEntry[] candleUpdate = new IndicatorEntry[periods];
                for (int i = 0; i < periods - 1; i++) {
                    long timeGet = timeUpdate - (periods - i - 1) * Utils.TIME_DAY;
                    if (smaEntries.get(timeGet) != null) {
                        candleUpdate[i] = smaEntries.get(timeGet);
                    } else {
                        return;
                    }
                }
                if (entrieUpdate.startTime.longValue() == timeUpdate) {
                    entrieUpdate = new IndicatorEntry(candle);
                } else {
                    entrieUpdate.priceClose = candle.priceClose;
                    if (entrieUpdate.maxPrice < candle.maxPrice) {
                        entrieUpdate.maxPrice = candle.maxPrice;
                    }
                    if (entrieUpdate.minPrice > candle.minPrice) {
                        entrieUpdate.minPrice = candle.minPrice;
                    }
                    entrieUpdate.totalUsdt += candle.totalUsdt;
                }
                candleUpdate[periods - 1] = entrieUpdate;
                entrieUpdate.setValue(CandleUtils.avgPrice(candleUpdate, 0, periods - 1));
                smaEntries.put(timeUpdate, entrieUpdate);
            }
        }


    }

}
