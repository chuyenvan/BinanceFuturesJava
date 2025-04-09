package com.binance.chuyennd.bigchange.market;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.grid.SimpleMovingAverage4hManager;
import com.binance.chuyennd.grid.SimpleMovingAverageDayManager;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TrendObject;
import com.binance.chuyennd.object.TrendState;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
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


//        List<KlineObjectNumber> btcTickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_4HOUR + Constants.SYMBOL_PAIR_BTC);
//        LOG.info("End ticker: {} {}", Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(btcTickers.size() - 1).startTime.longValue()),
//                btcTickers.get(btcTickers.size() - 1).priceClose);
//        int counter = 0;
//        int duration = 70;
//        for (int i = duration; i < btcTickers.size(); i++) {
//            KlineObjectNumber btcTicker = btcTickers.get(i);
//            List<KlineObjectNumber> tickerChecks = new ArrayList<>();
//            for (int j = 0; j < duration; j++) {
//                tickerChecks.add(btcTickers.get(i - j));
//            }
//            if (isBtcTrendReverse4h(tickerChecks, 0.04) != null) {
//                counter++;
//                LOG.info("{} {} {}", Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()), btcTicker.priceClose, counter);
//            }
//        }

//        LOG.info("{}", isBtcReverseBig15M(btcTickers));
//        traceCommandSellBigChange();
//        testDataStatistic();
//        testBtcReverse();
//        testAltReverse();
//        writeLevel15MChange2File();
//        writeLevel1MChange2File();
//        traceCommandMarketTrend();
//        traceCommandMarketTrend();
//        traceCommandMarketTrendInterval1M();
//        printDataByTime(20);
//        printDataSell();

//        Long time = Utils.sdfFileHour.parse("20240629 14:00").getTime();
//        Double rateMarket = getRateMarket(time);
//        System.out.println(rateMarket);
//        testTrading1h();
//        testBtcTradingStatus();
//        testBtcBottomTrading();
//        printTrendVolumeBtc();
//        printBtcBigChangeReverse();
//        System.exit(1);
//        List<Double> doubleList = new ArrayList<>();
//        doubleList.add(-0.0143);
//        doubleList.add(-0.0141);
//        doubleList.add(-0.0144);
//        doubleList.add(-0.015);
//        doubleList.add(-0.0166);
//        doubleList.add(-0.0161);
//        doubleList.add(-0.017);
//        doubleList.add(-0.0181);
//        doubleList.add(-0.0183);
//        doubleList.add(-0.02);
//        System.out.println(isDoubleReverse(doubleList, 5, -0.019));
//        System.out.println(isDoubleReverse(doubleList, 9, -0.019));
//        System.out.println(isDoubleReverse(doubleList, 10, -0.019));
//        System.out.println(isDoubleReverse(doubleList, 5, -0.02));
//        System.out.println(isDoubleReverse(doubleList, 5, -0.021));
//        LOG.info("{}", doubleList);
//        Long startTime = Utils.sdfFileHour.parse("20241229 21:00").getTime();
//        List<KlineObjectSimple> btcTickers = TickerFuturesHelper.getTickerSimpleWithStartTime("BTCUSDT",
//                Constants.INTERVAL_1M, startTime - 400 * Utils.TIME_MINUTE);
//        while (true) {
//            if (btcTickers.get(btcTickers.size() - 1).startTime.longValue() > startTime) {
//                btcTickers.remove(btcTickers.size() - 1);
//            } else {
//                break;
//            }
//        }
//        System.out.println(isBtcSideWay(btcTickers, 0.005));

    }

    private static void testAltReverse() {

        try {
            Long startTime = Utils.sdfFileHour.parse("20241020 21:09").getTime();
            List<KlineObjectSimple> tickers = TickerFuturesHelper.getTickerSimpleWithStartTime("APEUSDT",
                    Constants.INTERVAL_1M, startTime - 400 * Utils.TIME_MINUTE);
            List<KlineObjectSimple> tickerTests = new ArrayList<>();
            for (KlineObjectSimple ticker : tickers) {
                tickerTests.add(ticker);
                if (isAltTrendReverse(tickerTests, null, null)) {
                    LOG.info("{} {}", ticker.priceClose,
                            Utils.normalizeDateYYYYMMDDHHmm(tickerTests.get(tickerTests.size() - 1).startTime.longValue()));
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    public static boolean isAltTrendReverse(List<KlineObjectSimple> tickers, Double maxPrice, Double minPrice) {
        if (tickers.size() < Configs.NUMBER_TICKER_CAL_RATE_CHANGE + 2) {
            return false;
        }
        int size = tickers.size();
        Double priceMin2Trend = -0.01;
        if (maxPrice != null && Utils.rateOf2Double(tickers.get(size - 1).priceClose, maxPrice) < -0.05) {
            return false;
        }
        if (minPrice != null && Utils.rateOf2Double(tickers.get(size - 1).priceClose, minPrice) > 0.1) {
            return false;
        }
        try {
            Double priceReverse = null;
            for (int i = 1; i < 5; i++) {
//                if (tickers.get(size - 1).startTime.longValue() == Utils.sdfFileHour.parse("20241020 21:20").getTime()){
//                    System.out.println("Debug");
//                }
                KlineObjectSimple lastTicker = tickers.get(size - i - 1);
                KlineObjectSimple ticker = tickers.get(size - i);
                Double rate = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
//                rate = Math.min(rate, Utils.rateOf2Double(ticker.priceClose, lastTicker.priceOpen));
                if (rate <= priceMin2Trend) {
                    priceReverse = ticker.priceOpen;
//                    if (Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) > 0.8 * priceMin2Trend) {
//                        priceReverse = lastTicker.priceOpen;
//                    }
                    break;
                }
            }
            if (priceReverse != null
                    && tickers.get(size - 1).priceClose > priceReverse
                    && tickers.get(size - 2).priceClose < priceReverse
                    && Utils.rateOf2Double(tickers.get(size - 1).priceClose, tickers.get(size - 1).priceOpen) < 0.015
                    && tickers.get(size - 2).totalUsdt < tickers.get(size - 1).totalUsdt
            ) {
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


    public static boolean isBtcBottomReverse(List<KlineObjectNumber> tickers, int i) {
        List<TrendObject> trends = extractTopBottomObjectInTicker(tickers, i);
        if (!trends.isEmpty()) {
            TrendObject lastTrend = trends.get(trends.size() - 1);
            if (lastTrend.status.equals(TrendState.BOTTOM)
                    && lastTrend.kline.priceClose > lastTrend.kline.priceOpen
                    && lastTrend.kline.equals(tickers.get(i - 1))) {

                LOG.info(" {} {} {} priceMin: {}", lastTrend.status,
                        Utils.normalizeDateYYYYMMDDHHmm(lastTrend.kline.startTime.longValue()),
                        Utils.normalizeDateYYYYMMDDHHmm(tickers.get(i).startTime.longValue()), lastTrend.kline.minPrice);
                return true;
            }

        }
        return false;
    }

    public static List<TrendObject> extractTopBottomObjectInTicker(List<KlineObjectNumber> tickers, int index) {
        List<TrendObject> objects = new ArrayList<>();
        int period = 5;
        // tìm đáy hoặc đỉnh đầu tiên
        KlineObjectNumber lastTickerCheck = tickers.get(0);
        TrendState state = TrendState.TOP;
        if (tickers.get(0).priceOpen > tickers.get(0).priceClose) {
            state = TrendState.BOTTOM;
        }
        int start;
        for (start = 0; start < index; start++) {
            if (start + period > index) {
                break;
            }
            // tìm đỉnh gần nhất
            if (state.equals(TrendState.TOP)) {
                boolean top = true;
                for (int j = start; j < period + start; j++) {
                    if (tickers.get(j).maxPrice > lastTickerCheck.maxPrice) {
                        lastTickerCheck = tickers.get(j);
                        start = j;
                        top = false;
                        break;
                    }
                }
                if (top) {
                    objects.add(new TrendObject(state, lastTickerCheck));
                    lastTickerCheck = tickers.get(start + 1);
                    state = TrendState.BOTTOM;
                }
            } else {// tìm đáy gần nhất
                boolean bottom = true;
                for (int j = start; j < period + start; j++) {
                    if (tickers.get(j).minPrice < lastTickerCheck.minPrice) {
                        lastTickerCheck = tickers.get(j);
                        start = j;
                        bottom = false;
                        break;
                    }
                }
                if (bottom) {
                    objects.add(new TrendObject(state, lastTickerCheck));
                    lastTickerCheck = tickers.get(start + 1);
                    state = TrendState.TOP;
                }
            }
            if (!objects.isEmpty()) {
                break;
            }
        }
        // tìm các đỉnh, đáy tiếp theo
        for (int i = start; i < index; i++) {
            // tìm đỉnh gần nhất
            if (state.equals(TrendState.TOP)) {
                boolean top = true;
                for (int j = i; j < period + i; j++) {
                    if (j >= index) {
                        top = false;
                        break;
                    }
                    if (tickers.get(j).maxPrice > lastTickerCheck.maxPrice) {
                        lastTickerCheck = tickers.get(j);
                        i = j;
                        top = false;
                        break;
                    }
                }
                if (top) {
                    objects.add(new TrendObject(state, lastTickerCheck));
                    lastTickerCheck = tickers.get(i + 1);
                    state = TrendState.BOTTOM;
                }
            } else {// tìm đáy gần nhất
                boolean top = true;
                for (int j = i; j < period + i; j++) {
                    if (j >= index) {
                        top = false;
                        break;
                    }
                    if (tickers.get(j).minPrice < lastTickerCheck.minPrice) {
                        lastTickerCheck = tickers.get(j);
                        i = j;
                        top = false;
                        break;
                    }
                }
                if (top) {
                    objects.add(new TrendObject(state, lastTickerCheck));
                    lastTickerCheck = tickers.get(i + 1);
                    state = TrendState.TOP;
                }
            }
        }
        objects.add(new TrendObject(state, lastTickerCheck));
        return objects;
    }


    public static List<String> getTopSymbol2TradeTest(Map<String, KlineObjectNumber> value, int period) {
        TreeMap<Double, String> rateChange2Symbols = new TreeMap<>();
        for (Map.Entry<String, KlineObjectNumber> entry1 : value.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectNumber ticker = entry1.getValue();
            Double rateChange;
            rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
            rateChange2Symbols.put(rateChange, symbol);
        }
        return getTopSymbol(value, rateChange2Symbols, period, null);
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
            if (rateChangeBtc > -0.002 && rateChange < -0.15) {
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
        Double rateChangeDownAvg = MarketBigChangeDetectorTest.calRateLossAvg(rateDown2Symbols, 50);
        Double rateChangeUpAvg = -MarketBigChangeDetectorTest.calRateLossAvg(rateUp2Symbols, 50);
        Double rateChangeDown15MAvg = MarketBigChangeDetectorTest.calRateLossAvg(rateMax2Symbols, 50);
        Double rateChangeUp15MAvg = -MarketBigChangeDetectorTest.calRateLossAvg(rateMin2Symbols, 50);

//        List<String> symbolsTopDown = MarketBigChangeDetectorTest.getTopSymbolSimple(rateDown2Symbols,
//                Configs.NUMBER_ENTRY_EACH_SIGNAL, null);
        MarketDataObject result = new MarketDataObject(rateChangeDownAvg, rateChangeUpAvg, btcRateChange, btcTicker.totalUsdt,
                null, null);
        result.rateDown2Symbols = rateDown2Symbols;
        result.rate2Max = rateMax2Symbols;
        result.rate2Min = rateMin2Symbols;
        result.rateDown15MAvg = rateChangeDown15MAvg;
        result.rateUp15MAvg = rateChangeUp15MAvg;
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


    public static Double calRateChangeAvg(Map<String, KlineObjectNumber> entry) {
        TreeMap<Double, String> rateLoss2Symbols = new TreeMap<>();
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

    public static Double calVolumeAvgSimple(Map<String, KlineObjectSimple> entry) {
        Double totalVolume = 0d;
        int counter = 0;
        for (Map.Entry<String, KlineObjectSimple> entry1 : entry.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectSimple ticker = entry1.getValue();
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

    public static List<String> getTopSymbolSimpleNew(TreeMap<Double, String> rateLoss2Symbols, MarketLevelChange levelChange, int period,
                                                     Map<String, KlineObjectSimple> symbol2Ticker, Set<String> symbolLock) {

        List<String> symbols = new ArrayList<>();
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
//                if (levelChange != null
//                        && !levelChange.equals(MarketLevelChange.BIG_DOWN)
//                        && !StringUtils.containsIgnoreCase(levelChange.toString(), "sell")
//                        && !levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
//                        && entry.getKey() < -0.15) {
//                    LOG.info("Scam symbol: {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), levelChange, symbol);
//                    continue;
//                }
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


    public static Double getStatusTradingBtc(List<KlineObjectNumber> btcTickers, Long startTime) {
        try {
            Integer index = null;
            for (int i = 0; i < btcTickers.size(); i++) {
                KlineObjectNumber ticker = btcTickers.get(i);
                if (ticker.startTime.longValue() == startTime) {
                    index = i;
                    break;
                }
            }
            if (index == null || index < 100) {
                return null;
            }
            ArrayList<KlineObjectNumber> tickers = new ArrayList<>();

            KlineObjectNumber lastFinalTicker = btcTickers.get(index - 1);
            KlineObjectNumber finalTicker = btcTickers.get(index);
//            if (finalTicker.minPrice > btcTickers.get(index - 1).minPrice) {
//                return null;
//            }
            for (int i = index - 100; i <= index; i++) {
                tickers.add(btcTickers.get(i));
            }
            List<TrendObject> trends = TickerFuturesHelper.extractTopBottomObjectInTicker(tickers);
            if (trends.size() > 1) {
                TrendObject lastFinalTrend = trends.get(trends.size() - 2);
                TrendObject finalTrend = trends.get(trends.size() - 1);

                if (finalTrend.status.equals(TrendState.BOTTOM)
                        && lastFinalTicker.minPrice == finalTrend.getMinPrice()
                        && lastFinalTrend.kline.ma20 != null
                        && lastFinalTrend.kline.priceClose > lastFinalTrend.kline.ma20
                ) {
                    if (Utils.rateOf2Double(lastFinalTrend.getDefaultPrice(), finalTicker.priceClose) > 0.01) {
                        return Utils.rateOf2Double(lastFinalTrend.getDefaultPrice(), finalTicker.priceClose);
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }


    public static Double isAltVolumeReverse(List<KlineObjectNumber> altTickers, Integer index) {
        try {
            if (index < 101) {
                return null;
            }
            Double totalVolume = 0d;
            Double priceChange = 0d;
            for (int i = 1; i < 101; i++) {
                KlineObjectNumber kline = altTickers.get(index - i);
                totalVolume += kline.totalUsdt;
                priceChange += Utils.rateOf2Double(kline.priceClose, kline.priceOpen);

            }
            Double volumeAvg = totalVolume / 100;
            KlineObjectNumber finalTicker = altTickers.get(index);
            OrderSide side = null;
            if (finalTicker.totalUsdt > 2 * volumeAvg
                    && finalTicker.totalUsdt < 5 * volumeAvg
                    && Utils.rateOf2Double(finalTicker.priceClose, finalTicker.priceOpen) < -0.005) {
                return finalTicker.totalUsdt / volumeAvg;
            }
            LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(finalTicker.startTime.longValue()), priceChange * 100);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }


    public static boolean isCoupleTickerBuy(List<KlineObjectNumber> altTickers, Integer index) {
        List<Integer> results = new ArrayList<>();
        try {
            if (index == null || index < 2) {
                return false;
            }
            KlineObjectNumber finalTicker = altTickers.get(index);
            KlineObjectNumber lastTicker = altTickers.get(index - 1);
            Double max4h = lastTicker.maxPrice;
            Double min4h = lastTicker.minPrice;
            Boolean isHaveTickerOver = false;
            for (int i = 0; i < 96; i++) {
                if (index >= i) {
                    KlineObjectNumber ticker = altTickers.get(index - i);
                    if (Utils.rateOf2Double(ticker.maxPrice, ticker.minPrice) > 0.1) {
                        isHaveTickerOver = true;
                    }
                    if (max4h < ticker.maxPrice) {
                        max4h = ticker.maxPrice;
                    }
                    if (i < 16
                            && min4h > ticker.minPrice) {
                        min4h = ticker.minPrice;
                    }
                }
            }
            Double rateFinal = Utils.rateOf2Double(finalTicker.priceClose, finalTicker.priceOpen);
            Double rateLast = Utils.rateOf2Double(lastTicker.priceClose, lastTicker.priceOpen);
            if (Math.abs(rateFinal) > 0.02
                    && Math.abs(rateLast) > 0.02
                    && Math.abs(rateLast + rateFinal) < 0.01
                    && finalTicker.maxPrice < max4h && lastTicker.maxPrice < max4h
//                    && (finalTicker.minPrice <= min4h || lastTicker.minPrice <= min4h)
                    && !isHaveTickerOver
//                    && finalTicker.priceClose < finalTicker.priceOpen // -> BUY
//                    && finalTicker.priceClose > finalTicker.priceOpen // -> SELL
                    && (Math.abs(Utils.rateOf2Double(lastTicker.priceClose, finalTicker.priceOpen)) < 0.001)) {
                return true;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
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

    public static int getStatusTradingAlt1H(List<KlineObjectNumber> altTickers, Integer index) {
        try {
            if (index == null || index < 2) {
                return 0;
            }
            ArrayList<KlineObjectNumber> tickers = new ArrayList<>();
            KlineObjectNumber finalTicker = altTickers.get(index);
//            if (finalTicker.startTime.longValue() == Utils.sdfFileHour.parse("20240630 13:00").getTime()) {
//                System.out.println("Debug");
//            }
            KlineObjectNumber lastTicker = altTickers.get(index - 1);
            int start = 0;
            if (index > 100) {
                start = index - 100;
            }
            for (int i = start; i <= index; i++) {
                tickers.add(altTickers.get(i));
            }
            List<TrendObject> trends = TickerFuturesHelper.extractTopBottomObjectInTicker(tickers);
            if (trends.size() > 1) {
                TrendObject finalTrendTop = trends.get(trends.size() - 1);
                if (finalTrendTop.status.equals(TrendState.TOP)
                        && Utils.rateOf2Double(finalTicker.priceClose, finalTicker.priceOpen) < -0.005
                ) {
                    if (Utils.rateOf2Double(finalTrendTop.kline.maxPrice, finalTicker.priceClose) > 0.030) {
                        return 1;
                    }

                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return 0;
    }

    public static List<Object> isUnderSideWay2Trade(List<KlineObjectSimple> tickers) {
        List<Object> results = new ArrayList<>();

        Double duration = 0.005;
        KlineObjectSimple tickerClose = tickers.get(tickers.size() - 1);
        Double priceClose = tickerClose.priceClose;

        TreeMap<Double, Integer> price2Counter = new TreeMap<>();
        for (int i = 0; i < 9; i++) {
            price2Counter.put(priceClose + (i - 2) * duration * priceClose, 0);
        }
        for (KlineObjectSimple ticker : tickers) {
            for (Map.Entry<Double, Integer> entry : price2Counter.entrySet()) {
                Double price = entry.getKey();
                Integer counter = entry.getValue();
                if (ticker.minPrice <= price && price <= ticker.maxPrice) {
                    counter++;
                    price2Counter.put(price, counter);
                }
            }
        }
        Integer priceCloseCounter = price2Counter.get(priceClose);
        int counterBelow = 0;
        int counterAbove = 0;
        for (Map.Entry<Double, Integer> entry : price2Counter.entrySet()) {
            Double price = entry.getKey();
            Integer counter = entry.getValue();
            if (price < priceClose) {
                counterBelow += counter;
            } else {
                if (price > priceClose) {
                    counterAbove += counter;
                }
            }
//            LOG.info("{} {}", price, counter);
        }
        if (priceCloseCounter >= 70
                && counterAbove > priceCloseCounter
                && counterBelow > priceCloseCounter
        ) {
//            LOG.info("Under sideWay: {} {} {} {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(tickers.get(tickers.size() - 1).startTime.longValue())
//                    , priceClose, priceCloseCounter, counterAbove, counterBelow);
            results.add(priceClose);
            results.add(priceCloseCounter);
            results.add(counterAbove);
            results.add(counterBelow);
            results.add(duration);
            return results;
        }

//        if (Utils.rateOf2Double(tickerClose.priceClose, tickerClose.priceOpen) < -0.005){
//            results.add(tickerClose.priceClose);
//            results.add(Utils.rateOf2Double(tickerClose.priceClose, tickerClose.priceOpen));
//            return results;
//        }
        return null;
    }

    private static boolean isDoubleReverse(List<Double> lastRateDown15Ms, int period) {
        if (lastRateDown15Ms != null && lastRateDown15Ms.size() > period) {
            int size = lastRateDown15Ms.size();
            List<Long> lastRateLong = new ArrayList<>();
            for (int i = 0; i < size; i++) {
                Double rate = lastRateDown15Ms.get(i);
                rate = rate * 1000;
                lastRateLong.add(rate.longValue());
            }

            for (int i = 1; i < period; i++) {
                if (size - i - 1 >= 0) {
                    if (lastRateLong.get(size - i) < lastRateLong.get(size - i - 1)) {
                        return false;
                    }
                }
            }
            return true;
        }
        return false;
    }

    public static MarketLevelChange getMarketStatusSimple(Double rateDownAvg, Double rateUpAvg,
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
                && rateUp15MAvg > 0.12) {
            return MarketLevelChange.SMALL_UP;
        }
        if (rateDownAvg < -0.011
                && rateDown15MAvg < -0.03) {
            return MarketLevelChange.SMALL_DOWN;
        }

        // tiny 1 order and budget/2
        if (rateUpAvg > 0.009 && rateDownAvg > 0 && rateUp15MAvg > 0.016) {
            return MarketLevelChange.TINY_UP;
        }
        if (rateDownAvg < -0.0065 && rateUpAvg < 0
                && rateDown15MAvg < -0.028
        ) {
            return MarketLevelChange.TINY_DOWN;
        }

        if (rateDown15MAvg < -0.05) {
            return MarketLevelChange.MEDIUM_DOWN_15M;
        }
        if (rateDown15MAvg < -0.033) {
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


    public static Double isBtcTrendReverse4h(List<KlineObjectNumber> btcTickers, Double rateTrend) {
        int index = btcTickers.size() - 1;
        KlineObjectNumber lastTicker = btcTickers.get(index);
        Double priceReverse = null;
        Integer indexMin = null;

        while (priceReverse == null) {
//            LOG.info("Check btc reverse with rate: {}", rateTrend);
            for (int i = 0; i < index; i++) {
                if (index >= i + 2) {
                    KlineObjectNumber ticker = btcTickers.get(index - i);
                    KlineObjectNumber ticker4HoursAgo = btcTickers.get(index - i - 1);
                    KlineObjectNumber ticker8HoursAgo = btcTickers.get(index - i - 2);
                    double rate = Math.min(Utils.rateOf2Double(ticker.priceClose, ticker8HoursAgo.priceOpen),
                            Utils.rateOf2Double(ticker.priceClose, ticker4HoursAgo.priceOpen));
                    if (rate < -rateTrend) {
                        priceReverse = ticker4HoursAgo.priceOpen;
//                        priceReverse = Math.max(ticker15m.priceOpen, ticker15m.priceClose);
                        indexMin = i;
                        break;
                    }
                }
            }
            rateTrend = rateTrend - 0.005;
            if (rateTrend < 0.0345) {
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
                    return null;
                }
            }
//            LOG.info("IsBtc4hReverse: {} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(lastTicker.startTime.longValue()),
//                    lastTicker.priceClose, priceReverse, Utils.rateOf2Double(lastTicker.priceClose, priceReverse),
//                    Utils.sdfGoogle.format(new Date(lastTicker.startTime.longValue())));
            return rateTrend;
        }

        return null;
    }

    public static boolean isBtcSideWay(List<KlineObjectSimple> btcTickers, Double rateTrend) {
        int index = btcTickers.size() - 1;
        Double priceReverse = null;
        for (int i = 0; i < index; i++) {
            if (index >= i + 29) {
                KlineObjectSimple ticker = btcTickers.get(index - i);
                long minute = Utils.getCurrentMinute(ticker.startTime.longValue()) % 15;
                if (minute != 14) {
                    continue;
                }
                KlineObjectSimple ticker15m = btcTickers.get(index - i - 14);
                KlineObjectSimple ticker30m = btcTickers.get(index - i - 29);
                double rate = Math.min(Utils.rateOf2Double(ticker.priceClose, ticker30m.priceOpen),
                        Utils.rateOf2Double(ticker.priceClose, ticker15m.priceOpen));
                if (rate < -rateTrend) {
                    priceReverse = ticker15m.priceOpen;
                    break;
                }
            }
        }
        if (priceReverse == null) {
            return true;
        }
        return false;
    }

    public static boolean isBtcReverseVolume(List<KlineObjectSimple> btcTickers) {
        int period = 15;
        int index = btcTickers.size() - 1;
        if (index < period + 3) {
            return false;
        }
        KlineObjectSimple finalTicker = btcTickers.get(index);
        KlineObjectSimple lastTicker = btcTickers.get(index - 1);
        Double volumeTotal = 0d;
        for (int i = 3; i < period + 3; i++) {
            KlineObjectSimple ticker = btcTickers.get(index - i);
            volumeTotal += ticker.totalUsdt;
        }
        double volumeAvg = volumeTotal / period;
        Double rateBtc = Utils.rateOf2Double(finalTicker.priceClose, finalTicker.priceOpen);
        Double rateBtc2Ticker = Utils.rateOf2Double(finalTicker.priceClose, lastTicker.priceOpen);
        if ((finalTicker.totalUsdt > 10 * volumeAvg || lastTicker.totalUsdt > 10 * volumeAvg)
                && (rateBtc < -0.0029 || rateBtc2Ticker < -0.0029)
                && rateBtc > -0.02
                && rateBtc < 0.002
        ) {
            return true;
        }
        return false;
    }

    public static Boolean isBtcTrendDown(List<KlineObjectSimple> btcTickers) {
        int period = 3;
        int index = btcTickers.size() - 1;
        if (index < period + 3) {
            return false;
        }
        if (Utils.rateOf2Double(btcTickers.get(index - 3).priceClose, btcTickers.get(index - 3).priceOpen) > 0.0001) {
            for (int i = 0; i < period; i++) {
                KlineObjectSimple ticker = btcTickers.get(index - i);
                if (Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) > -0.0008) {
                    return false;
                }
            }
            return true;
        }
        return false;
    }

    public static boolean isBtcTrendUp(List<KlineObjectNumber> btcTickers) {
        int period = 3;
        int index = btcTickers.size() - 1;
        if (index < period + 3) {
            return false;
        }
        LOG.info("Check time: {} {}", btcTickers.get(index).priceClose,
                Utils.sdfGoogle.format(new Date(btcTickers.get(index).startTime.longValue())));
        if (Utils.rateOf2Double(btcTickers.get(index - 3).priceClose, btcTickers.get(index - 3).priceOpen) < -0.0001) {
            for (int i = 0; i < period; i++) {
                KlineObjectNumber ticker = btcTickers.get(index - i);
                if (Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < 0.00045) {
                    return false;
                }
            }
            return true;
        }
        return false;
    }

    public static boolean isBtcReverseBig15M(List<KlineObjectSimple> btcTickers) {
        int period = 15;
        int index = btcTickers.size() - 1;
        if (index < period * 3) {
            return false;
        }
        KlineObjectSimple finalTicker = btcTickers.get(index);
        long minute = Utils.getCurrentMinute(finalTicker.startTime.longValue()) % 15;
        if (minute != 14) {
            return false;
        }
        KlineObjectSimple ticker15m = btcTickers.get(index - 14);
        KlineObjectSimple ticker30m = btcTickers.get(index - 29);
        if (Utils.rateOf2Double(finalTicker.priceClose, ticker15m.priceOpen) < -0.004
                || Utils.rateOf2Double(finalTicker.priceClose, ticker30m.priceOpen) < -0.007) {
            return true;
        }
        return false;
    }

    public static boolean isAltReverse15M(List<KlineObjectSimple> btcTickers) {
        int period = 15;
        int index = btcTickers.size() - 1;
        if (index < period + 3) {
            return false;
        }
        KlineObjectSimple finalTicker = btcTickers.get(index);
        KlineObjectSimple lastTicker = btcTickers.get(index - 1);
        Double volumeTotal = 0d;
        for (int i = 3; i < period + 3; i++) {
            KlineObjectSimple ticker = btcTickers.get(index - i);
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

    public static TreeMap<Long, Set<String>> extractSymbolFundingChange() {
        TreeMap<Long, Set<String>> time2Symbols = new TreeMap<>();
        try {
            File folder = new File(Configs.FOLDER_FUNDING_FEE);
            for (File file : folder.listFiles()) {
                String symbol = file.getName();
                TreeMap<Long, Double> time2RateFunding = (TreeMap<Long, Double>) Storage.readObjectFromFile(file.getAbsolutePath());
                List<Double> fundings = new ArrayList<>();
                for (Long time : time2RateFunding.keySet()) {
                    Double funding = time2RateFunding.get(time);
                    fundings.add(funding);
//                    if (time == Utils.sdfFileHour.parse("20250127 07:00").getTime() && StringUtils.equals(symbol, "ACHUSDT")){
//                        System.out.println("Debug");
//                        for (int i = 1; i < 5; i++) {
//                            LOG.info("{} {} {}",fundings.get(fundings.size() - 1 - i),fundings.get(fundings.size() - 2 - i),
//                                    fundings.get(fundings.size() - 1 - i).equals(fundings.get(fundings.size() - 2 - i)));
//                        }
//                    }
                    if (fundings.size() > 5) {
                        boolean isLastFundingNotChange = true;
                        if (fundings.get(fundings.size() - 1) < 0) {
                            for (int i = 1; i < 4; i++) {
                                if (fundings.get(fundings.size() - 1 - i) < 0) {
                                    isLastFundingNotChange = false;
                                    break;
                                }
                            }
                            if (isLastFundingNotChange) {
                                Set<String> symbols = time2Symbols.get(time);
                                if (symbols == null) {
                                    symbols = new HashSet<>();
                                }
                                symbols.add(symbol);
                                time2Symbols.put(time, symbols);
                            }
                        }
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return time2Symbols;
    }
}




