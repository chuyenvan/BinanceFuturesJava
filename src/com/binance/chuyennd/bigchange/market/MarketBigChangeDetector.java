package com.binance.chuyennd.bigchange.market;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TrendObject;
import com.binance.chuyennd.object.TrendState;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class MarketBigChangeDetector {
    public static final Logger LOG = LoggerFactory.getLogger(MarketBigChangeDetector.class);
    public static final String TIME_RUN = Configs.getString("TIME_RUN");

    public static void main(String[] args) throws ParseException {
        System.exit(1);
    }

    public static List<String> getTopSymbol2TradeWithRateChange(Map<String, KlineObjectNumber> value, int period, MarketLevelChange level) {
        TreeMap<Double, String> rateChange2Symbols = new TreeMap<>();
        for (Map.Entry<String, KlineObjectNumber> entry1 : value.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectNumber ticker = entry1.getValue();
            if (Utils.isTickerAvailable(ticker)) {
                Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
                rateChange2Symbols.put(rateChange, symbol);
            }
        }
        Double maxVolume = null;
        if (level.equals(MarketLevelChange.MINI_DOWN)) {
            maxVolume = 10 * 1E6;
        }
        return getTopSymbol(value, rateChange2Symbols, period, maxVolume);
    }

    public static List<String> getTopSymbol2TradeWithRateMax(Map<String, KlineObjectNumber> value, int period, MarketLevelChange level) {
        TreeMap<Double, String> rateChange2Symbols = new TreeMap<>();
        for (Map.Entry<String, KlineObjectNumber> entry1 : value.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectNumber ticker = entry1.getValue();
            if (Utils.isTickerAvailable(ticker)) {
                Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.maxPrice);
                rateChange2Symbols.put(rateChange, symbol);
            }
        }
        Double maxVolume = null;
        if (level.equals(MarketLevelChange.MINI_DOWN)) {
            maxVolume = 10 * 1E6;
        }
        return getTopSymbol(value, rateChange2Symbols, period, maxVolume);
    }

    public static List<String> getTopSymbolReverse2Trade(Map<String, KlineObjectNumber> value, int period, MarketLevelChange level) {
        TreeMap<Double, String> rateChange2Symbols = new TreeMap<>();
        for (Map.Entry<String, KlineObjectNumber> entry1 : value.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectNumber ticker = entry1.getValue();
            Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
            if (rateChange < 0.005) {
                rateChange2Symbols.put(-rateChange, symbol);
            }
        }
        Double maxVolume = null;
        if (level.equals(MarketLevelChange.MINI_DOWN)) {
            maxVolume = 10 * 1E6;
        }
        return getTopSymbol(value, rateChange2Symbols, period, maxVolume);
    }

    public static List<String> getTopSymbol2TradeWithVolumeBigUp(Map<String, KlineObjectNumber> lastValue,
                                                                 Map<String, KlineObjectNumber> value, int period) {
        if (lastValue == null) {
            return new ArrayList<>();
        }
        TreeMap<Double, String> rateChange2Symbols = new TreeMap<>();
        for (Map.Entry<String, KlineObjectNumber> entry1 : value.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectNumber ticker = entry1.getValue();
            KlineObjectNumber lastTicker = lastValue.get(symbol);
            if (lastTicker != null && ticker != null) {
                // bigup -> trade with up
//                if (Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) > 0.0) {
                Double rateChangeVolume = Utils.rateOf2Double(lastTicker.totalUsdt, ticker.totalUsdt);
                rateChange2Symbols.put(rateChangeVolume, symbol);
//                }
            }
        }
        return getTopSymbol(value, rateChange2Symbols, period, null);
    }

    public static Integer getStatusTradingBtc(List<KlineObjectNumber> btcTickers, Long startTime) {
        try {
            if (btcTickers == null) {
                return 0;
            }
            Integer index = null;
            for (int i = 0; i < btcTickers.size(); i++) {
                KlineObjectNumber ticker = btcTickers.get(i);
                if (ticker.startTime.longValue() == startTime) {
                    index = i;
                    break;
                }
            }
            if (index == null) {
                return 0;
            }
            ArrayList<KlineObjectNumber> tickers = new ArrayList<>();
            KlineObjectNumber finalTicker = btcTickers.get(index);
            for (int i = 0; i <= index; i++) {
                tickers.add(btcTickers.get(i));
            }
            List<TrendObject> trends = TickerFuturesHelper.extractTopBottomObjectInTicker(tickers);
            if (trends.size() > 1) {
                TrendObject finalTrend = trends.get(trends.size() - 1);
                String log = "Check btc top:" + Utils.normalizeDateYYYYMMDDHHmm(finalTrend.kline.startTime.longValue()) + " "
                        + finalTrend.status + " " + finalTrend.kline.maxPrice;
                LOG.info(log);
                if (finalTrend.status.equals(TrendState.TOP)) {
                    if (Utils.rateOf2Double(finalTrend.kline.maxPrice, finalTicker.priceClose) > 0.011) {
                        return 1;
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return 0;
    }


    public static List<String> getTopSymbol2TradeBtcSignal(Map<String, KlineObjectNumber> value, int period) {
        TreeMap<Double, String> rateLoss2Symbols = new TreeMap<>();
        for (Map.Entry<String, KlineObjectNumber> entry1 : value.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectNumber ticker = entry1.getValue();
            Double rateLoss = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
            rateLoss2Symbols.put(-rateLoss, symbol);
        }
        return getTopSymbol(value, rateLoss2Symbols, period, null);
    }

    public static MarketLevelChange detectLevelChange(Map<String, KlineObjectNumber> entry) {
        Double volumeAvg = calVolumeAvg(entry);
        Double rateChangeAvg = calRateChangeAvg(entry);
        MarketLevelChange level = getMarketStatus(rateChangeAvg, volumeAvg);
        return level;
    }


    public static MarketLevelChange detectLevelChangeProduction(Map<String, KlineObjectNumber> entry) {
        TreeMap<Double, String> rateLoss2Symbols = new TreeMap<>();
        Double totalVolume = 0d;
        int counter = 0;
        for (Map.Entry<String, KlineObjectNumber> entry1 : entry.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectNumber ticker = entry1.getValue();
            Double rateChange = null;
            if (ticker.priceClose > ticker.priceOpen) {
                rateChange = Utils.rateOf2Double(ticker.maxPrice, ticker.minPrice);
            } else {
                rateChange = Utils.rateOf2Double(ticker.minPrice, ticker.maxPrice);
            }
            counter++;
            rateLoss2Symbols.put(rateChange, symbol);
            totalVolume += ticker.totalUsdt;
        }
        Double rateLossAvg = calRateLossAvg(rateLoss2Symbols, null);
        totalVolume = totalVolume / 1E6;
        Double volumeAvg = totalVolume / counter;
        LOG.info("Check level market: {} rateChangeAvg: {} {}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()), rateLossAvg, volumeAvg);
        try {
            Utils.sendSms2Telegram("Check market : " + Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis() - 15 * Utils.TIME_MINUTE)
                    + " rate:" + Utils.formatDouble(rateLossAvg * 100, 4) + "% volumeAvg: " + volumeAvg);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return getMarketStatus(rateLossAvg, volumeAvg);
    }

    public static Double calRateChangeAvg(Map<String, KlineObjectNumber> entry) {
        TreeMap<Double, String> rateLoss2Symbols = new TreeMap<>();
        for (Map.Entry<String, KlineObjectNumber> entry1 : entry.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectNumber ticker = entry1.getValue();
            if (!Utils.isTickerAvailable(ticker)) {
                continue;
            }
            Double rateChange = null;
            if (ticker.priceClose > ticker.priceOpen) {
                rateChange = Utils.rateOf2Double(ticker.maxPrice, ticker.minPrice);
            } else {
                rateChange = Utils.rateOf2Double(ticker.minPrice, ticker.maxPrice);
            }
            rateLoss2Symbols.put(rateChange, symbol);
        }

        return calRateLossAvg(rateLoss2Symbols, null);
    }


    public static Double calVolumeAvg(Map<String, KlineObjectNumber> entry) {
        Double totalVolume = 0d;
        int counter = 0;
        for (Map.Entry<String, KlineObjectNumber> entry1 : entry.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectNumber ticker = entry1.getValue();
            totalVolume += ticker.totalUsdt;
            counter++;
        }
        Double volumeAvg = totalVolume / counter;
        return volumeAvg / 1E6;
    }

    private static List<String> getTopSymbol(Map<String, KlineObjectNumber> symbol2Kline,
                                             TreeMap<Double, String> rateLoss2Symbols, int period, Double maxVolume) {
        List<String> symbols = new ArrayList<>();
        for (Map.Entry<Double, String> entry : rateLoss2Symbols.entrySet()) {
            KlineObjectNumber ticker = symbol2Kline.get(entry.getValue());
            if (!Constants.specialSymbol.contains(entry.getValue())) {
                if (maxVolume != null) {
                    if (ticker != null
                            && ticker.totalUsdt < maxVolume) {
                        symbols.add(entry.getValue());
                    }
                } else {
                    symbols.add(entry.getValue());
                }
            }
            if (symbols.size() >= period) {
                break;
            }
        }
        return symbols;
    }


    private static Double calRateLossAvg(TreeMap<Double, String> rateLoss2Symbols, Integer period) {
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


    public static List<Integer> getStatusTradingAlt15M(List<KlineObjectNumber> altTickers, Integer index) {
        List<Integer> results = new ArrayList<>();
        try {
            if (index == null || index < 2) {
                return results;
            }
            ArrayList<KlineObjectNumber> tickers = new ArrayList<>();
            KlineObjectNumber finalTicker = altTickers.get(index);
            KlineObjectNumber lastTicker = altTickers.get(index - 1);
            int start = 0;
            if (index > 100) {
                start = index - 100;
            }
            for (int i = start; i <= index; i++) {
                tickers.add(altTickers.get(i));
            }
            Double min24h = lastTicker.minPrice;
            Double min4h = lastTicker.minPrice;
            Boolean isHaveTickerOver = false;
            for (int i = 0; i < 192; i++) {
                if (index >= i) {
                    KlineObjectNumber ticker = altTickers.get(index - i);
                    if (Utils.rateOf2Double(ticker.maxPrice, ticker.minPrice) > 0.05) {
                        isHaveTickerOver = true;
                        break;
                    }
                    if (i < 96
                            && min24h > ticker.minPrice) {
                        min24h = ticker.minPrice;
                    }
                    if (i < 16
                            && min4h > ticker.minPrice) {
                        min4h = ticker.minPrice;
                    }
                }
            }
            List<TrendObject> trends = TickerFuturesHelper.extractTopBottomObjectInTicker(tickers);
            if (trends.size() > 1) {
                TrendObject finalTrendTop = trends.get(trends.size() - 1);
                if (finalTrendTop.status.equals(TrendState.TOP)
                        && Utils.rateOf2Double(finalTicker.priceClose, finalTicker.priceOpen) < -0.003
                        && finalTicker.totalUsdt > lastTicker.totalUsdt * 2
                        && finalTicker.totalUsdt < lastTicker.totalUsdt * 10
                ) {
                    Double rateChangeWithTop = Utils.rateOf2Double(finalTrendTop.kline.maxPrice, finalTicker.priceClose);
                    if (rateChangeWithTop > 0.030) {
                        results.add(1);
                    }
                    Double rateChangeTotal = Utils.rateOf2Double(finalTicker.maxPrice, finalTicker.minPrice);
                    if (rateChangeWithTop > 0.04
                            && !isHaveTickerOver
                            && rateChangeTotal < 0.04
                            && finalTicker.minPrice > min24h) {
                        results.add(2);
                    }
                    if (rateChangeWithTop > 0.030
                            && !isHaveTickerOver
                            && finalTicker.minPrice > min4h) {
                        results.add(3);
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return results;
    }

    private static MarketLevelChange getMarketStatus(Double rateLossAvg, Double volumeAvg) {
        if (rateLossAvg < -0.12) {
            return MarketLevelChange.BIG_DOWN;
        }
        if (rateLossAvg < -0.055) {
            if (volumeAvg >= 20 && volumeAvg < 35) {
                return MarketLevelChange.MAYBE_BIG_DOWN_AFTER;
//                return null;
            }
            return MarketLevelChange.MEDIUM_DOWN;
        }
        if (rateLossAvg < -0.04) {
            return MarketLevelChange.SMALL_DOWN;
        }
        if (rateLossAvg < -0.03) {
            return MarketLevelChange.TINY_DOWN;
        }
        if (rateLossAvg < -0.020) {
            return MarketLevelChange.MINI_DOWN;
        }

        if (rateLossAvg > 0.04) {
            return MarketLevelChange.BIG_UP;
        }
        if (rateLossAvg > 0.035) {
            return MarketLevelChange.MEDIUM_UP;
        }
        if (rateLossAvg > 0.021) {
            return MarketLevelChange.SMALL_UP;
        }


//        if (rateLossAvg < -0.019 && volumeAvg > 9) {
//            return MarketLevelChange.MINI_DOWN_EXTEND;
//        }


        return null;
    }

    public static boolean isSignalSELL(List<KlineObjectNumber> altTickers, Integer index) {
        try {
            if (index == null || index < 2) {
                return false;
            }
            KlineObjectNumber finalTicker = altTickers.get(index);
            KlineObjectNumber lastTicker = altTickers.get(index - 1);
            Double max24h = lastTicker.maxPrice;
            Double maxVolume24h = lastTicker.totalUsdt;

            Boolean isHaveTickerBigUp = false;
            for (int i = 0; i < 96; i++) {
                if (index >= i) {
                    KlineObjectNumber ticker = altTickers.get(index - i);
                    if (Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) > 0.05) {
                        isHaveTickerBigUp = true;
                    }
                    if (maxVolume24h < ticker.totalUsdt) {
                        maxVolume24h = ticker.totalUsdt;
                    }
                    if (max24h < ticker.maxPrice) {
                        max24h = ticker.maxPrice;
                    }
                }
            }
            Double rateFinal = Utils.rateOf2Double(finalTicker.priceClose, finalTicker.priceOpen);

            if (rateFinal < -0.015
                    && rateFinal > -0.05
                    && (finalTicker.maxPrice >= max24h || lastTicker.maxPrice >= max24h)
//                    && finalTicker.minPrice < lastTicker.priceOpen
                    && (finalTicker.totalUsdt >= maxVolume24h || lastTicker.totalUsdt >= maxVolume24h)
                    && isHaveTickerBigUp
            ) {
                return true;
            }

        } catch (
                Exception e) {
            e.printStackTrace();
        }
        return false;
    }
}
