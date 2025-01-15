package com.binance.chuyennd.trading;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
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
        try {
            Long startTime = Utils.sdfFileHour.parse("20250107 07:35").getTime();

            List<KlineObjectNumber> btcTickers = TickerFuturesHelper.getTickerWithStartTime(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_1M,
                    startTime - 400 * Utils.TIME_MINUTE);
            while (true) {
                if (btcTickers.get(btcTickers.size() - 1).startTime.longValue() > startTime) {
                    btcTickers.remove(btcTickers.size() - 1);
                } else {
                    break;
                }
            }
            LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(0).startTime.longValue()),
                    Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(btcTickers.size() - 1).startTime.longValue()));

            System.out.println(MarketBigChangeDetector.isBtcTrendReverse(btcTickers));

            btcTickers.remove(btcTickers.size() - 1);
            if (MarketBigChangeDetector.isBtcTrendReverse(btcTickers)) {
                // check last time not btc trend reverse -> btc trend reverse
                String finalTimeTrendReverse = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_MARKET_LEVEL_FINAL,
                        MarketLevelChange.BTC_TREND_REVERSE.toString());
                if (finalTimeTrendReverse == null || Long.parseLong(finalTimeTrendReverse) < btcTickers.get(btcTickers.size() - 1).startTime.longValue()) {
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_MARKET_LEVEL_FINAL,
                            MarketLevelChange.BTC_TREND_REVERSE.toString(), String.valueOf(btcTickers.get(btcTickers.size() - 1).startTime.longValue()));
                    LOG.info("Fixbug btc trend reverse error {} ",
                            Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(btcTickers.size() - 1).startTime.longValue()));
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }


    public static boolean isBtcTrendReverse(List<KlineObjectNumber> btcTickers) {
        int index = btcTickers.size() - 1;
        Double rateTrend = 0.01;
        KlineObjectNumber lastTicker = btcTickers.get(index);
        Double priceReverse = null;
        Integer indexMin = null;
        while (priceReverse == null) {
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
            rateTrend = rateTrend - 0.0005;
            if (rateTrend < 0.0046) {
                break;
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
                Utils.formatDouble(rateBtc2Ticker * 100, 3),
                Utils.formatDouble(rateDown15MAvg * 100, 3), lastTicker.totalUsdt / volumeAvg);
        if ((finalTicker.totalUsdt > 10 * volumeAvg || lastTicker.totalUsdt > 10 * volumeAvg)
                && (rateBtc < -0.0029 || rateBtc2Ticker < -0.0029)
                && rateBtc > -0.02
                && rateBtc < 0.002
        ) {
            return true;
        }

        return false;
    }
    public static boolean isBtcReverse15M(List<KlineObjectNumber> btcTickers) {
        int period = 15;
        int index = btcTickers.size() - 1;
        if (index < period * 3) {
            return false;
        }
        KlineObjectNumber finalTicker = btcTickers.get(index);
        long minute = Utils.getCurrentMinute(finalTicker.startTime.longValue()) % 15;
        if (minute != 14) {
            return false;
        }
        KlineObjectNumber ticker15m = btcTickers.get(index - 14);
        KlineObjectNumber ticker30m = btcTickers.get(index - 29);
        if (Utils.rateOf2Double(finalTicker.priceClose, ticker15m.priceOpen) < -0.004
                || Utils.rateOf2Double(finalTicker.priceClose, ticker30m.priceOpen) < -0.007) {
            return true;
        }
        return false;
    }


    public static List<String> getTopSymbol(TreeMap<Double, String> rateLoss2Symbols, int period, Map<String,
            KlineObjectNumber> symbol2FinalTicker, Set<String> symbolLocked) {
        List<String> symbols = new ArrayList<>();
        for (Map.Entry<Double, String> entry : rateLoss2Symbols.entrySet()) {
            String symbol = entry.getValue();
            if (symbolLocked != null && symbolLocked.contains(symbol)) {
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
            total += key;
            if (period != null && counter >= period) {
                break;
            }
        }
        if (rateLoss2Symbols.isEmpty()) {
            return 0d;
        }
        return total / counter;
    }

    public static MarketLevelChange getMarketStatus15M(Double rateDown15MAvg, List<Double> lastRateDown15Ms) {

        if (rateDown15MAvg < -0.05) {
            return MarketLevelChange.MEDIUM_DOWN_15M;
        }
        if (rateDown15MAvg < -0.0285) {
            return MarketLevelChange.SMALL_DOWN_15M;
        }
        if (lastRateDown15Ms != null
                && !lastRateDown15Ms.isEmpty()
                && rateDown15MAvg < -0.0265
                && rateDown15MAvg > lastRateDown15Ms.get(lastRateDown15Ms.size() - 1)) {
            return MarketLevelChange.SMALL_DOWN_15M;
        }
        if (isDoubleReverse(lastRateDown15Ms, 10, rateDown15MAvg) && rateDown15MAvg < -0.02) {
            return MarketLevelChange.TINY_DOWN_15M;
        }
        if (isDoubleReverse(lastRateDown15Ms, 20, rateDown15MAvg) && rateDown15MAvg < -0.015) {
            return MarketLevelChange.TINY_DOWN_15M;
        }
        if (isDoubleReverse(lastRateDown15Ms, 25, rateDown15MAvg) && rateDown15MAvg < -0.01) {
            return MarketLevelChange.TINY_DOWN_15M;
        }
        return null;
    }

    private static boolean isDoubleReverse(List<Double> lastRateDown15Ms, int period, Double rateDown15MAvg) {
        if (lastRateDown15Ms != null && lastRateDown15Ms.size() > period) {
            int size = lastRateDown15Ms.size();
            List<Long> lastRateLong = new ArrayList<>();
            for (int i = 0; i < size; i++) {
                Double rate = lastRateDown15Ms.get(i);
                rate = rate * 1000;
                lastRateLong.add(rate.longValue());
            }

            for (int i = 0; i < period; i++) {
                if (lastRateLong.get(size - i - 1) > lastRateLong.get(size - i - 2)) {
                    return false;
                }
            }
            if (lastRateDown15Ms.get(size - 1) < rateDown15MAvg) {
                return true;
            }
        }
        return false;
    }

    public static MarketLevelChange getMarketStatus1M(Double rateDownAvg, Double rateUpAvg,
                                                      Double btcRateChange, Double rateDown15MAvg,
                                                      Double rateUp15MAvg, Double rateBtcDown15M) {
        // big -> 2 order and x2 budget
        if (rateUpAvg > 0.025) {
            return MarketLevelChange.BIG_UP;
        }
        if (rateDownAvg < -0.04
                && btcRateChange < -0.01) {
            return MarketLevelChange.BIG_DOWN;
        }

        // medium 2 order
        if (rateUpAvg > 0.023
                || (rateUpAvg > 0.015 && rateUp15MAvg > 0.11)
        ) {
            return MarketLevelChange.MEDIUM_UP;
        }
        if (rateDownAvg < -0.030 ||
                (rateDownAvg < -0.015
                        && rateDown15MAvg < -0.08
                )
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
        if (rateDownAvg < -0.006
                && rateDown15MAvg < -0.025
        ) {
            return MarketLevelChange.TINY_DOWN;
        }

        return null;
    }


}


