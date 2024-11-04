package com.binance.chuyennd.trading;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;

public class MarketBigChangeDetector {
    public static final Logger LOG = LoggerFactory.getLogger(MarketBigChangeDetector.class);
    public static final String TIME_RUN = Configs.getString("TIME_RUN");

    public static void main(String[] args) throws ParseException {
        System.exit(1);
    }


    public static boolean isBtcTrendReverse(List<KlineObjectNumber> btcTickers) {
        int index = btcTickers.size() - 1;
        Double rateTrend = 0.006;
        KlineObjectNumber lastTicker = btcTickers.get(index);
        Double priceReverse = null;
        Integer indexMin = null;
        for (int i = 0; i < index; i++) {
            if (index >= i + 29) {
                KlineObjectNumber ticker = btcTickers.get(index - i);
                long minute = Utils.getCurrentMinute(ticker.startTime.longValue()) % 15;
                if (minute != 14) {
                    continue;
                }
                KlineObjectNumber ticker15m = btcTickers.get(index - i - 14);
                KlineObjectNumber ticker30m = btcTickers.get(index - i - 29);
                double rate = Math.min(Utils.rateOf2Double(ticker.priceClose, ticker30m.priceOpen),
                        Utils.rateOf2Double(ticker.priceClose, ticker15m.priceOpen));
                if (rate < -rateTrend) {
                    priceReverse = ticker15m.priceOpen;
                    indexMin = i;
                    break;
                }
            }
        }
        if (priceReverse != null
                && lastTicker.priceClose > priceReverse
        ) {
            // by pass if last ticker not ticker first up over bottom 1%
            for (int i = 1; i < indexMin; i++) {
                KlineObjectNumber ticker = btcTickers.get(index - i);
                if (ticker.priceClose >= priceReverse) {
                    return false;
                }
            }
            LOG.info("IsBtcTrendReverse: {} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(lastTicker.startTime.longValue()),
                    lastTicker.priceClose, priceReverse, Utils.rateOf2Double(lastTicker.priceClose, priceReverse),
                    Utils.sdfGoogle.format(new Date(lastTicker.startTime.longValue())));
            return true;
        }
        return false;
    }

    public static boolean isBtcReverse(List<KlineObjectNumber> btcTickers, Double rateDown15MAvg) {
        int period = 15;
        int index = btcTickers.size() - 1;
        if (index < period + 3) {
            return false;
        }
        KlineObjectNumber finalTicker = btcTickers.get(index);
        KlineObjectNumber lastTicker = btcTickers.get(index - 1);
        Double volumeTotal = 0d;
        for (int i = 3; i < period + 3; i++) {
            KlineObjectNumber ticker = btcTickers.get(index - i);
            volumeTotal += ticker.totalUsdt;
        }
        double volumeAvg = volumeTotal / period;
        Double rateBtc = Utils.rateOf2Double(finalTicker.priceClose, finalTicker.priceOpen);
        Double rateBtc2Ticker = Utils.rateOf2Double(finalTicker.priceClose, lastTicker.priceOpen);
        LOG.info("Check btc reverse: {} {} {}% {} {}% {} {}", Utils.normalizeDateYYYYMMDDHHmm(finalTicker.startTime.longValue()),
                finalTicker.priceClose, Utils.formatDouble(rateBtc * 100, 3), finalTicker.totalUsdt / volumeAvg,
                Utils.formatDouble(rateBtc2Ticker * 100, 3), lastTicker.totalUsdt / volumeAvg,
                Utils.formatDouble(rateDown15MAvg * 100, 3));
        if ((finalTicker.totalUsdt > 10 * volumeAvg || lastTicker.totalUsdt > 10 * volumeAvg)
                && (rateBtc < -0.0029 || rateBtc2Ticker < -0.0029)
                && rateBtc > -0.02
                && rateBtc < 0.002
        ) {
            return true;
        }

        return false;
    }


    public static List<String> getTopSymbol(TreeMap<Double, String> rateLoss2Symbols, int period, Map<String,
            KlineObjectNumber> symbol2FinalTicker, Set<String> symbolLocked) {
        List<String> symbols = new ArrayList<>();
        for (Map.Entry<Double, String> entry : rateLoss2Symbols.entrySet()) {
            String symbol = entry.getValue();
            if (symbolLocked.contains(symbol)) {
                LOG.info("Not trade {} because symbol locking: {}",
                        symbol, Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
                continue;
            }
            KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
            if (ticker != null
                    && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < Configs.RATE_TICKER_MAX_SCAN_ORDER) {
                symbols.add(symbol);
            }
            if (symbols.size() >= period) {
                break;
            }
        }
        return symbols;
    }


    public static Double calRateChangeAvg(TreeMap<Double, String> rateLoss2Symbols, Integer period) {
        Double total = 0d;
        int counter = 0;
        for (Map.Entry<Double, String> entry : rateLoss2Symbols.entrySet()) {
            Double key = entry.getKey();
            counter++;
            if (period != null && counter >= period) {
                break;
            }
            total += key;
        }
        if (rateLoss2Symbols.isEmpty()) {
            return 0d;
        }
        return total / counter;
    }

    public static MarketLevelChange getMarketStatus15M(Double rateDown15MAvg, Double rateUp15MAvg, Double rateBtcDown15M) {

        if (rateDown15MAvg < -0.055) {
            return MarketLevelChange.MEDIUM_DOWN;
        }
        if (rateDown15MAvg < -0.029) {
            return MarketLevelChange.SMALL_DOWN_15M;
        }
        if (rateUp15MAvg > 0.06) {
            return MarketLevelChange.MEDIUM_UP_15M;
        }
        if (rateUp15MAvg > 0.034
                && rateDown15MAvg < -0.013
                && rateDown15MAvg > -0.026
        ) {
            return MarketLevelChange.SMALL_UP_15M;
        }
        if (rateDown15MAvg < -0.025 && rateBtcDown15M < -0.014) {
            return MarketLevelChange.TINY_DOWN_15M;
        }
        return null;
    }

    public static MarketLevelChange getMarketStatus1M(Double rateDownAvg, Double rateUpAvg,
                                                      Double btcRateChange, Double rateDown15MAvg,
                                                      Double rateUp15MAvg, Double rateBtcDown15M) {
        // big -> 2 order and x2 budget
        if (rateUpAvg > 0.025) {
            return MarketLevelChange.BIG_UP;
        }
        if (rateDownAvg < -0.04
                && rateUpAvg < -0.01
                && btcRateChange < -0.01) {
            return MarketLevelChange.BIG_DOWN;
        }

        // medium 2 order
        if (rateUpAvg > 0.023
                || (rateUpAvg > 0.015 && rateUp15MAvg > 0.11)
        ) {
            return MarketLevelChange.MEDIUM_UP;
        }
        if (rateDownAvg < -0.032 ||
                (rateDownAvg < -0.015
                        && rateDown15MAvg < -0.09)
        ) {
            return MarketLevelChange.MEDIUM_DOWN;
        }

        // small 1 order
        if (rateUpAvg > 0.009
                && rateUp15MAvg > 0.07) {
            return MarketLevelChange.SMALL_UP;
        }
        if (rateDownAvg < -0.011
                && rateDown15MAvg < -0.03) {
            return MarketLevelChange.SMALL_DOWN;
        }

        // tiny 1 order and budget/2
        if ((rateUpAvg > 0.009 && rateUp15MAvg > 0.015)
                || (rateUpAvg > 0.007 && rateUp15MAvg > 0.015 && rateBtcDown15M < -0.007)) {
            return MarketLevelChange.TINY_UP;
        }
        if (rateDownAvg < -0.008
                && rateDown15MAvg < -0.025
        ) {
            return MarketLevelChange.TINY_DOWN;
        }

        return null;
    }


}


