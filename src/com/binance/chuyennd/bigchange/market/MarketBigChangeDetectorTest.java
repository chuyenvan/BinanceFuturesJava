package com.binance.chuyennd.bigchange.market;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TrendObject;
import com.binance.chuyennd.object.TrendState;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;

public class MarketBigChangeDetectorTest {
    public static final Logger LOG = LoggerFactory.getLogger(MarketBigChangeDetectorTest.class);
    public static String TIME_RUN = Configs.getString("TIME_RUN");


    public static void main(String[] args) throws ParseException {
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
        List<Double> doubleList = new ArrayList<>();
        doubleList.add(-0.0143);
        doubleList.add(-0.0141);
        doubleList.add(-0.0144);
        doubleList.add(-0.015);
        doubleList.add(-0.0166);
        doubleList.add(-0.0161);
        doubleList.add(-0.017);
        doubleList.add(-0.0181);
        doubleList.add(-0.0183);
        doubleList.add(-0.02);
        System.out.println(isDoubleReverse(doubleList, 5, -0.019));
        System.out.println(isDoubleReverse(doubleList, 9, -0.019));
        System.out.println(isDoubleReverse(doubleList, 10, -0.019));
        System.out.println(isDoubleReverse(doubleList, 5, -0.02));
        System.out.println(isDoubleReverse(doubleList, 5, -0.021));
        LOG.info("{}", doubleList);
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
        for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectSimple ticker = entry1.getValue();
            Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
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
        KlineObjectSimple btcTicker = symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC);
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

    public static List<String> getTopSymbolSimpleNew(TreeMap<Double, String> rateLoss2Symbols, int period,
                                                     Map<String, KlineObjectSimple> symbol2Ticker, Set<String> symbolLock) {
        List<String> symbols = new ArrayList<>();
        for (Map.Entry<Double, String> entry : rateLoss2Symbols.entrySet()) {
            String symbol = entry.getValue();
            if (symbolLock != null && symbolLock.contains(symbol)) {
                continue;
            }
            KlineObjectSimple ticker = symbol2Ticker.get(symbol);
            if (ticker != null
                    && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < Configs.RATE_TICKER_MAX_SCAN_ORDER
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


    public static Boolean isSignalSell(List<KlineObjectNumber> altTickers, Integer index) {
        try {
            if (index < 1) {
                return false;
            }
            KlineObjectNumber finalTicker = altTickers.get(index);
            if (finalTicker.rsi != null
                    && finalTicker.rsi <= 62
                    && Utils.rateOf2Double(finalTicker.priceClose, finalTicker.priceOpen) < 0
            ) {
                for (int i = 1; i < 5; i++) {
                    if (index >= i) {
                        KlineObjectNumber ticker = altTickers.get(index - i);
                        if (ticker.rsi != null && ticker.rsi >= 70) {
                            return true;
                        }
                    }
                }
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

    public static MarketLevelChange getMarketStatus15M(Double rateDown15MAvg, Double rateUp15MAvg, List<Double> lastRateDown15Ms, List<Double> lastRateDowns) {

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

    public static Double isBtcTrendReverse(List<KlineObjectSimple> btcTickers, Double rateTrend) {
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
}




