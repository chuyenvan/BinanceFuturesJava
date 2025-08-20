package com.binance.chuyennd.bigchange.market;

import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;

public class MarketBigChangeDetectorTest {
    public static final Logger LOG = LoggerFactory.getLogger(MarketBigChangeDetectorTest.class);
    public static String TIME_RUN = Configs.getString("TIME_RUN");


    public static void main(String[] args) throws ParseException {
        List<KlineObjectSimple> tickerSimples = TickerFuturesHelper.getTickerSimpleWithStartTime(Constants.SYMBOL_PAIR_BTC,
                Constants.INTERVAL_1M, Utils.sdfFileHour.parse("20250321 20:30").getTime() - 499 * Utils.TIME_MINUTE);
        while (tickerSimples.size() > 360) {
            tickerSimples.remove(0);
        }
        LOG.info("time check: {}", Utils.normalizeDateYYYYMMDDHHmm(tickerSimples.get(tickerSimples.size() - 1).startTime.longValue()));
        System.out.println(MarketBigChangeDetectorTest.isBtcTrendReverse(tickerSimples, Configs.BTC_TREND_REVERSE_RATE_MAX,
                Configs.BTC_TREND_REVERSE_RATE_MIN));


    }

    private static void testAltReverse() {

        try {
            Long startTime = Utils.sdfFileHour.parse("20241020 21:09").getTime();
            List<KlineObjectSimple> tickers = TickerFuturesHelper.getTickerSimpleWithStartTime("APEUSDT",
                    Constants.INTERVAL_1M, startTime - 400 * Utils.TIME_MINUTE);
            List<KlineObjectSimple> tickerTests = new ArrayList<>();
            for (KlineObjectSimple ticker : tickers) {
                tickerTests.add(ticker);
                if (isAltTrendReverse(tickerTests)) {
                    LOG.info("{} {}", ticker.priceClose,
                            Utils.normalizeDateYYYYMMDDHHmm(tickerTests.get(tickerTests.size() - 1).startTime.longValue()));
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    public static boolean isAltTrendReverse(List<KlineObjectSimple> tickers) {
        if (tickers.size() < Configs.NUMBER_TICKER_CAL_RATE_CHANGE + 2) {
            return false;
        }
        int size = tickers.size();
        Double priceMin2Trend = -0.01;
        try {
            Double priceReverse = null;
            for (int i = 1; i < 20; i++) {
                KlineObjectSimple ticker = tickers.get(size - i);
                Double rate = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
                if (rate <= priceMin2Trend) {
                    priceReverse = ticker.priceOpen;
                    break;
                }
            }
            if (priceReverse != null) {
                // pass if before ticker over reverse
                for (int i = 1; i < Configs.NUMBER_TICKER_CAL_RATE_CHANGE; i++) {
                    KlineObjectSimple ticker = tickers.get(size - i - 1);
                    if (ticker.priceClose >= tickers.get(size - 1).priceClose) {
                        return false;
                    }
                    if (ticker.priceOpen == priceReverse) {
                        break;
                    }
                }
                return true;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
    }


    public static MarketDataObject calMarketData(Map<String, KlineObjectSimple> symbol2Ticker, Map<String, Double> symbol2PriceMax,
                                                 Map<String, Double> symbol2MinPrice) {
        TreeMap<Double, String> rateDown2Symbols = new TreeMap<>();
        TreeMap<Double, String> rateMin2Symbols = new TreeMap<>();
        TreeMap<Double, String> rateMax2Symbols = new TreeMap<>();
        TreeMap<Double, String> rateUp2Symbols = new TreeMap<>();
        KlineObjectSimple btcTicker = symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC);
        Double rateChangeBtc = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen);
        for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectSimple ticker = entry1.getValue();
            Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
            // pass symbol big dump(delist/waring/monitor...)
            if (rateChangeBtc > -0.004 && rateChange < -0.15) {
                continue;
            }
            rateDown2Symbols.put(rateChange, symbol);
            rateUp2Symbols.put(-rateChange, symbol);
            Double maxPrice = symbol2PriceMax.get(symbol);
            if (maxPrice != null) {
                rateMax2Symbols.put(Utils.rateOf2Double(ticker.priceClose, maxPrice), symbol);
            }
            Double minPrice = symbol2MinPrice.get(symbol);
            if (minPrice != null) {
                rateMin2Symbols.put(-Utils.rateOf2Double(ticker.priceClose, minPrice), symbol);
            }
        }
        Double btcRateChange = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen);
        Double rateChangeDownAvg = MarketBigChangeDetectorTest.calRateLossAvg(rateDown2Symbols, 100);
        Double rateChangeUpAvg = -MarketBigChangeDetectorTest.calRateLossAvg(rateUp2Symbols, 100);
        Double rateChangeDown15MAvg = MarketBigChangeDetectorTest.calRateLossAvg(rateMax2Symbols, 100);

//        List<String> symbolsTopDown = MarketBigChangeDetectorTest.getTopSymbolSimple(rateDown2Symbols,
//                Configs.NUMBER_ENTRY_EACH_SIGNAL, null);
        MarketDataObject result = new MarketDataObject(rateChangeDownAvg, rateChangeUpAvg, btcRateChange,
                null, null);
        result.rate2Max = rateMax2Symbols;
        result.rate2Min = rateMin2Symbols;
        result.rateDown15MAvg = rateChangeDown15MAvg;
        result.rateBtcUp15M = Utils.rateOf2Double(btcTicker.priceClose, symbol2MinPrice.get(Constants.SYMBOL_PAIR_BTC));
        result.rateBtcDown15M = Utils.rateOf2Double(btcTicker.priceClose, symbol2PriceMax.get(Constants.SYMBOL_PAIR_BTC));
        result.symbol2PriceMax15M = symbol2PriceMax;
        return result;
    }

    public static List<String> getTopUpSymbol2TradeSimple(Map<String, KlineObjectSimple> value, int period) {
        TreeMap<Double, String> rateChange2Symbols = new TreeMap<>();
        for (Map.Entry<String, KlineObjectSimple> entry1 : value.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectSimple ticker = entry1.getValue();
            Double rateChange;
            rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
            rateChange2Symbols.put(-rateChange, symbol);
        }
        return getTopSymbolSimple(rateChange2Symbols, period, null);
    }


    private static List<String> getTopSymbol(Map<String, KlineObjectNumber> symbol2Kline,
                                             TreeMap<Double, String> rateLoss2Symbols, int period, Double maxVolume) {
        List<String> symbols = new ArrayList<>();
        for (Map.Entry<Double, String> entry : rateLoss2Symbols.entrySet()) {
            KlineObjectNumber ticker = symbol2Kline.get(entry.getValue());
            if (maxVolume != null) {
                if (ticker != null
                        && ticker.totalUsdt < maxVolume) {
                    symbols.add(entry.getValue());
                }
            } else {
                symbols.add(entry.getValue());
            }
            if (symbols.size() >= period) {
                break;
            }
        }
        return symbols;
    }

    public static List<String> getTopSymbolSimple(TreeMap<Double, String> rateLoss2Symbols, int period, Set<String> symbolsRunning) {
        List<String> symbols = new ArrayList<>();

        for (Map.Entry<Double, String> entry : rateLoss2Symbols.entrySet()) {
            if (symbolsRunning != null && symbolsRunning.contains(entry.getValue())) {
                continue;
            }
            symbols.add(entry.getValue());
            if (symbols.size() >= period) {
                break;
            }
        }
        return symbols;
    }

    public static Set<String> getTopSymbolSimpleNew(TreeMap<Double, String> rateLoss2Symbols, MarketLevelChange levelChange, int period,
                                                     Map<String, KlineObjectSimple> symbol2Ticker, Set<String> symbolLock) {

        Set<String> symbols = new HashSet<>();
        for (Map.Entry<Double, String> entry : rateLoss2Symbols.entrySet()) {
            String symbol = entry.getValue();
            Double rateScam = Configs.RATE_TICKER_MAX_SCAN_ORDER;
            if (symbolLock != null && symbolLock.contains(symbol)) {
                continue;
            }
            KlineObjectSimple ticker = symbol2Ticker.get(symbol);
            if (ticker != null
                    && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < rateScam
            ) {
                symbols.add(symbol);
                if (symbols.size() >= period) {
                    break;
                }
            }
        }
        return symbols;
    }
    public static List<String> getUnderTopSymbolSimpleNew(TreeMap<Double, String> rateLoss2Symbols, MarketLevelChange levelChange, int period,
                                                     Map<String, KlineObjectSimple> symbol2Ticker, Set<String> symbolLock) {

        List<String> symbols = new ArrayList<>();
        for (Map.Entry<Double, String> entry : rateLoss2Symbols.descendingMap().entrySet()) {
            String symbol = entry.getValue();
            Double rateScam = Configs.RATE_TICKER_MAX_SCAN_ORDER;
            if (symbolLock != null && symbolLock.contains(symbol)) {
                continue;
            }
            KlineObjectSimple ticker = symbol2Ticker.get(symbol);
            if (ticker != null
                    && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < rateScam
            ) {
                symbols.add(symbol);
                if (symbols.size() >= period) {
                    break;
                }
            }
        }
        return symbols;
    }

    public static Double calRateLossAvg(TreeMap<Double, String> rateLoss2Symbols, Integer period) {
        Double total = 0d;
        int counter = 0;
        if (period > rateLoss2Symbols.size() * 4 / 5) {
            period = rateLoss2Symbols.size() * 4 / 5;
        }
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


    public static Boolean isSignalSell(List<KlineObjectNumber> tickers) {
        try {
            int index = tickers.size() - 1;
            KlineObjectNumber ticker = tickers.get(tickers.size() - 1);
            Double minPrice = ticker.minPrice;
            for (int j = 0; j < 12; j++) {
                if (index - j - 1 > 0) {
                    minPrice = Math.min(minPrice, tickers.get(index - j - 1).minPrice);
                }
            }
            if (Utils.rateOf2Double(ticker.priceClose, minPrice) > 0.9) {
                return true;
            }
        } catch (
                Exception e) {
            e.printStackTrace();
        }
        return false;
    }


    public static MarketLevelChange getMarketStatusSimple(Double rateDownAvg, Double rateUpAvg,
                                                          Double btcRateChange, Double rateDown15MAvg) {
        // big -> 2 order and x2 budget
        if (rateUpAvg > 0.025) {
            return MarketLevelChange.BIG_UP;
        }
        if (rateDownAvg < -0.032
                && btcRateChange < -0.01) {
            return MarketLevelChange.BIG_DOWN;
        }

        // medium 2 order
        if (rateUpAvg > 0.015) {
            return MarketLevelChange.MEDIUM_UP;
        }
        if (rateDownAvg < -0.030 ||
                (rateDownAvg < -0.014
                        && rateDown15MAvg < -0.07
                )
        ) {
            return MarketLevelChange.MEDIUM_DOWN;
        }
        if (rateUpAvg > 0.008 && rateDownAvg > 0) {
            return MarketLevelChange.SMALL_UP;
        }
        if (rateDownAvg < -0.006 && rateUpAvg < 0
                && rateDown15MAvg < -0.025
        ) {
            return MarketLevelChange.SMALL_DOWN;
        }

        if (rateDown15MAvg < -0.045) {
            return MarketLevelChange.MEDIUM_DOWN_15M;
        }
        if (rateDown15MAvg < -0.028) {
            return MarketLevelChange.SMALL_DOWN_15M;
        }

        return null;
    }


    public static Double isBtcTrendReverse(List<KlineObjectSimple> btcTickers, Double rateTrend, Double rateTrendMin) {
        int index = btcTickers.size() - 1;
        KlineObjectSimple lastTicker = btcTickers.get(index);
        Double priceReverse = null;
        Integer indexMin = null;

        while (priceReverse == null) {
//            LOG.info("Check btc reverse with rate: {}", rateTrend);
            for (int i = 0; i < index; i++) {
                if (index >= i + 29) {
                    KlineObjectSimple ticker = btcTickers.get(index - i);
                    long minute = Utils.getCurrentMinute(ticker.startTime.longValue()) % 15;
                    if (minute != 14) {
                        continue;
                    }
                    KlineObjectSimple ticker15m = btcTickers.get(index - i - 14);
                    KlineObjectSimple ticker30m = btcTickers.get(index - i - 29);
                    double rate = Math.min(Utils.rateOf2Double(ticker.priceClose, ticker30m.maxPrice),
                            Utils.rateOf2Double(ticker.priceClose, ticker15m.maxPrice));
                    if (rate < -rateTrend) {
                        priceReverse = ticker15m.priceOpen;
//                        priceReverse = Math.max(ticker15m.priceOpen, ticker15m.priceClose);
                        indexMin = i;
                        break;
                    }
                }
            }
            if (rateTrend > 0.01) {
                rateTrend = rateTrend - 0.002;
            } else {
                rateTrend = rateTrend - 0.0005;
            }
            if (rateTrend < rateTrendMin - 0.00005) {
                break;
            }
        }
        if (priceReverse != null
                && lastTicker.priceClose > priceReverse
        ) {
            // by pass if last ticker not ticker first up over bottom 1%
            for (int i = 1; i < indexMin; i++) {
                KlineObjectSimple ticker = btcTickers.get(index - i);
                if (ticker.priceClose >= priceReverse) {
                    return null;
                }
            }
            LOG.info("IsBtcTrendReverse: {} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(lastTicker.startTime.longValue()),
                    lastTicker.priceClose, priceReverse, Utils.rateOf2Double(lastTicker.priceClose, priceReverse),
                    Utils.sdfGoogle.format(new Date(lastTicker.startTime.longValue())));
            return rateTrend;
        }

        return null;
    }


    public static boolean isAltReverse15M(List<KlineObjectSimple> tickers) {
        int period = 15;
        int index = tickers.size() - 1;
        if (index < period + 3) {
            return false;
        }
        KlineObjectSimple finalTicker = tickers.get(index);
        KlineObjectSimple lastTicker = tickers.get(index - 1);
        Double volumeTotal = 0d;
        for (int i = 3; i < period + 3; i++) {
            KlineObjectSimple ticker = tickers.get(index - i);
            volumeTotal += ticker.totalUsdt;
        }
        double volumeAvg = volumeTotal / period;
        Double rateTicker = Utils.rateOf2Double(finalTicker.priceClose, finalTicker.priceOpen);
        Double lastRateTicker = Utils.rateOf2Double(finalTicker.priceClose, lastTicker.priceOpen);

        if ((finalTicker.totalUsdt > 10 * volumeAvg || lastTicker.totalUsdt > 10 * volumeAvg)
                && (rateTicker < -0.018 || lastRateTicker < -0.02)
                && rateTicker < -0.01
        ) {
            return true;
        }
        return false;
    }

}




