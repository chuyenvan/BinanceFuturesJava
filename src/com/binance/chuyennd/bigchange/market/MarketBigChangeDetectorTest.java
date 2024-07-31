package com.binance.chuyennd.bigchange.market;

import com.binance.chuyennd.bigchange.statistic.data.DataStatisticHelper;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TrendObject;
import com.binance.chuyennd.object.TrendState;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.apache.commons.io.FileUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.text.ParseException;
import java.util.*;

public class MarketBigChangeDetectorTest {
    public static final Logger LOG = LoggerFactory.getLogger(MarketBigChangeDetectorTest.class);
    public static String TIME_RUN = Configs.getString("TIME_RUN");

    public static void main(String[] args) throws ParseException {
//        traceCommandSellBigChange();
//        testDataStatistic();
//        writeLevelChange2File();
        traceCommandMarketTrend();
        printDataByTime(20);
//        printDataSell();

//        Long time = Utils.sdfFileHour.parse("20240629 14:00").getTime();
//        Double rateMarket = getRateMarket(time);
//        System.out.println(rateMarket);
//        testTrading1h();
//        testBtcTradingStatus();
//        testBtcBottomTrading();
//        printTrendVolumeBtc();
//        printBtcBigChangeReverse();
        System.exit(1);
    }

    private static List<Long> extractBtcUpReverse() {
        List<Long> results = new ArrayList<>();
        try {
            List<KlineObjectNumber> btcTickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(DataManager.FOLDER_TICKER_15M + Constants.SYMBOL_PAIR_BTC);
            LOG.info("FinalTicker: {}", Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(btcTickers.size() - 1).startTime.longValue()));
            for (int i = 0; i < btcTickers.size(); i++) {
                KlineObjectNumber ticker = btcTickers.get(i);
                Long timeLong = ticker.startTime.longValue();
                KlineObjectNumber ticker2Hours = TickerFuturesHelper.extractKlineByNumberTicker(btcTickers, i, 8);
                if (ticker2Hours != null) {
                    Double breadAbove = Utils.rateOf2Double(ticker.maxPrice, ticker.priceOpen);
                    Double rateChange = Utils.rateOf2Double(ticker.maxPrice, ticker.minPrice);
                    if (breadAbove > 0.004 && rateChange > 0.005 && ticker.priceOpen > ticker.priceClose) {
                        if (ticker.maxPrice >= ticker2Hours.maxPrice) {
                            results.add(timeLong);
                        }
                    }
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
        return results;
    }

    private static void testDataStatistic() {
        Long duration = 48 * Utils.TIME_HOUR;
        Long numberTicker = duration / (15 * Utils.TIME_MINUTE);
        try {
            Long time = Utils.sdfFileHour.parse("20240708 16:00").getTime();
            Map<String, KlineObjectNumber> symbol2DataStatistic =
                    DataStatisticHelper.getInstance().readDataStaticByTimeAndNumberTickerStatic(time, numberTicker);
            LOG.info("{}", Utils.toJson(symbol2DataStatistic.get("XLMUSDT")));
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void writeLevelChange2File() throws ParseException {
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        Map<Long, MarketLevelChange> time2Level = new HashMap<>();
        while (true) {
            TreeMap<Long, Map<String, KlineObjectNumber>> time2Tickers;
            try {
                time2Tickers = DataManager.readDataFromFile(startTime);
                for (Map.Entry<Long, Map<String, KlineObjectNumber>> entry : time2Tickers.entrySet()) {
                    Long time = entry.getKey();
                    Double volumeAvg = calVolumeAvg(entry.getValue());
                    Double rateChangeAvg = calRateChangeAvg(entry.getValue());
                    MarketLevelChange level = getMarketStatus(rateChangeAvg, volumeAvg);
                    if (level != null) {
                        time2Level.put(time, level);
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            startTime += Utils.TIME_DAY;
            if (startTime > System.currentTimeMillis()) {
                break;
            }
        }
        Storage.writeObject2File("target/time2marketLevel.data", time2Level);
    }

    private static void traceCommandSellBigChange() throws ParseException {
        Long duration = 48 * Utils.TIME_HOUR;
        Long numberTicker = duration / (15 * Utils.TIME_MINUTE);

        Double target = 0.007;
        LOG.info("Finish read data statistic");

        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        TreeMap<Long, List<OrderTargetInfoTest>> time2Orders = new TreeMap<>();
        Map<String, KlineObjectNumber> lastTicker = null;

        while (true) {
            TreeMap<Long, Map<String, KlineObjectNumber>> time2Tickers;
            try {
                time2Tickers = DataManager.readDataFromFile(startTime);
                for (Map.Entry<Long, Map<String, KlineObjectNumber>> entry : time2Tickers.entrySet()) {
                    Long time = entry.getKey();
                    List<OrderTargetInfoTest> ordersByTime = new ArrayList<>();
                    time2Orders.put(time, ordersByTime);
                    Double volumeAvg = calVolumeAvg(entry.getValue());
                    Double rateChangeAvg = calRateChangeAvg(entry.getValue());
                    List<String> symbols = getTopSymbol2TradeTest(entry.getValue(), 10);
                    Map<String, KlineObjectNumber> symbol2DataStatistic =
                            DataStatisticHelper.getInstance().readDataStaticByTimeAndNumberTickerStatic(time, numberTicker);
                    for (String symbol : symbols) {
                        KlineObjectNumber ticker = entry.getValue().get(symbol);
                        KlineObjectNumber klineOfSymbol = symbol2DataStatistic.get(symbol);
                        if (klineOfSymbol == null) {
//                            LOG.info("Error get ticker statistic: {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time));
                            continue;
                        }
                        Double priceTp = Utils.calPriceTarget(symbol, ticker.priceClose, OrderSide.SELL, target);
                        Double budget = 10d;
                        Double quantity = Utils.calQuantity(budget, 10, ticker.priceClose, symbol);
                        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, ticker.priceClose, priceTp, quantity,
                                10, symbol, ticker.startTime.longValue(), ticker.endTime.longValue(), OrderSide.SELL);
                        order.minPrice = klineOfSymbol.minPrice;
                        order.lastPrice = klineOfSymbol.priceClose;
                        order.maxPrice = klineOfSymbol.maxPrice;
                        order.tickerOpen = ticker;
                        order.ma201d = rateChangeAvg;
                        order.volume = volumeAvg;
                        if (lastTicker != null && lastTicker.get(symbol) != null) {
                            order.avgVolume24h = lastTicker.get(symbol).totalUsdt;
                        }
                        if (klineOfSymbol.minPrice < order.priceTP && klineOfSymbol.maxPrice > order.priceTP) {
                            order.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                        } else {
                            order.status = OrderTargetStatus.STOP_LOSS_DONE;
                            order.priceTP = klineOfSymbol.priceClose;
                        }
                        ordersByTime.add(order);
                    }
                    lastTicker = entry.getValue();
                }

            } catch (Exception e) {
                e.printStackTrace();
            }
            startTime += Utils.TIME_DAY;
            if (startTime > System.currentTimeMillis()) {
                break;
            }
        }
        Storage.writeObject2File("target/MarketOrderSELL.data", time2Orders);
        LOG.info("Finished!");
    }

    private static Double getRateMarket(Long time) {
        Long timeDate = Utils.getDate(time);
        TreeMap<Long, Map<String, KlineObjectNumber>> time2Tickers = DataManager.readDataFromFile(timeDate);
        for (Map.Entry<Long, Map<String, KlineObjectNumber>> entry : time2Tickers.entrySet()) {
            Long timeTicker = entry.getKey();
            if (timeTicker.equals(time)) {
                return calRateChangeAvg(entry.getValue());
            }
        }
        return null;
    }

    private static void testBtcBottomTrading() {
        String symbol = "BTCUSDT";
        List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_15M);
        for (int i = 20; i < tickers.size(); i++) {
            if (isBtcBottomReverse(tickers, i)) {
                LOG.info("{}", Utils.normalizeDateYYYYMMDDHHmm(tickers.get(i).startTime.longValue()));
            }

        }

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

    private static void testBtcTradingStatus() throws ParseException {
        List<KlineObjectNumber> btcTickers = TickerFuturesHelper.getTicker(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_15M);
        Long time = Utils.sdfFile.parse("20240712").getTime() + 7 * Utils.TIME_HOUR;

//        List<KlineObjectNumber> btcTickers = (List<KlineObjectNumber>)
//                Storage.readObjectFromFile(DataManager.FOLDER_TICKER_15M + Constants.SYMBOL_PAIR_BTC);
//        Long time = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;

        Map<Long, MarketLevelChange> time2Level = (Map<Long, MarketLevelChange>) Storage.readObjectFromFile("target/time2marketLevel.data");
        Map<Long, KlineObjectNumber> time2BtcKline = new HashMap<>();
        for (KlineObjectNumber klineBtc : btcTickers) {
            time2BtcKline.put(klineBtc.startTime.longValue(), klineBtc);
        }


        while (true) {
            if (time == Utils.sdfFileHour.parse("20240713 03:30").getTime()) {
                System.out.println("Debug");
            }
            if (!time2Level.containsKey(time)) {
                Double rateChange = getStatusTradingBtc(btcTickers, time);
                if (rateChange != null) {
                    LOG.info("{} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), time2BtcKline.get(time).priceClose, rateChange);
                }
            }
            time = time + 15 * Utils.TIME_MINUTE;
            if (time2BtcKline.get(time) == null) {
                break;
            }
        }
    }

    private static void testTrading1h() {
        String symbol = "BLZUSDT";
        List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker(symbol,
                Constants.INTERVAL_1H);
        for (int i = 0; i < tickers.size(); i++) {
            if (getStatusTradingAlt1H(tickers, i) == 1) {
                LOG.info("BUY {} {} {}", symbol,
                        Utils.normalizeDateYYYYMMDDHHmm(tickers.get(i).startTime.longValue()), tickers.get(i).priceClose);
            }
        }
    }

    private static void printBtcBigChangeReverse() {
//        List<KlineObjectNumber> btcTickers = (List<KlineObjectNumber>)
//                Storage.readObjectFromFile(DataManager.FOLDER_TICKER_15M + Constants.SYMBOL_PAIR_BTC);
        List<KlineObjectNumber> btcTickers = TickerFuturesHelper.getTicker(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_15M);
        int index = 0;
        for (KlineObjectNumber klineBtc : btcTickers) {
            Long time = klineBtc.startTime.longValue();
            try {
                if (Utils.rateOf2Double(klineBtc.priceClose, klineBtc.priceOpen) < -0.004
                        && Utils.rateOf2Double(klineBtc.maxPrice, klineBtc.minPrice) > 0.008) {
                    LOG.info("{} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), Utils.rateOf2Double(klineBtc.maxPrice, klineBtc.minPrice),
                            counterSupport(btcTickers, 48, index));
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            index++;
        }
    }

    private static Integer counterSupport(List<KlineObjectNumber> tickers, int period, int index) {
        int counter = 0;
        Double priceCheck = tickers.get(index).priceClose;
        for (int i = index - period; i < index; i++) {
            if (i >= 0) {
                if (tickers.get(i).minPrice <= priceCheck && tickers.get(i).maxPrice >= priceCheck) {
                    counter++;
                }
            }
        }
        return counter;
    }

    private static void printTrendVolumeBtc() {
        List<KlineObjectNumber> btcTickers = (List<KlineObjectNumber>)
                Storage.readObjectFromFile(DataManager.FOLDER_TICKER_15M + Constants.SYMBOL_PAIR_BTC);
        Map<Long, KlineObjectNumber> time2BtcKline = new HashMap<>();
        for (KlineObjectNumber klineBtc : btcTickers) {
            time2BtcKline.put(klineBtc.startTime.longValue(), klineBtc);
        }
        int period = 32;
        Double rate = 2.5;
        TrendState state = null;
        for (KlineObjectNumber klineBtc : btcTickers) {
            Long time = klineBtc.startTime.longValue();
            try {
                if (time == Utils.sdfFileHour.parse("20240607 19:15").getTime()) {
                    System.out.println("Debug");
                }
                TrendState trend = detectTrend(time2BtcKline, time, period, rate, state);
                if (trend != null) {
                    state = trend;
                }
                if (trend != null) {
                    LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(time), trend);
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private static TrendState detectTrend(Map<Long, KlineObjectNumber> time2BtcKline, Long time, int period, Double rate, TrendState lastTrend) {
        Double volumeBtcAvg = calVolumeAvgByTime(time2BtcKline, time, period);
        KlineObjectNumber lastKlineBtc = time2BtcKline.get(time - 15 * Utils.TIME_MINUTE);
        KlineObjectNumber klineBtc = time2BtcKline.get(time);
        if (lastKlineBtc != null) {
            double btcVolume = lastKlineBtc.totalUsdt / 1E6;
            TrendState state;
            // volume tăng đột biến tính theo ticker tiếp theo
            if (btcVolume / volumeBtcAvg > rate) {
                // volume trươc đó đã tăng mà volume hiện tại tiếp tục tăng -> tính theo ticker hiện tại
                if (klineBtc.totalUsdt > lastKlineBtc.totalUsdt) {
                    if (klineBtc.priceClose > klineBtc.priceOpen) {
                        state = TrendState.UP;
                    } else {
                        state = TrendState.DOWN;
                    }
                    return state;
                }
                if (lastTrend == null) {
                    if (lastKlineBtc.priceClose < klineBtc.priceClose) {
                        state = TrendState.UP;
                    } else {
                        state = TrendState.DOWN;
                    }
                    return state;
                }
                if (lastTrend.equals(TrendState.UP)) {
                    if (klineBtc.minPrice > lastKlineBtc.minPrice || klineBtc.maxPrice > lastKlineBtc.maxPrice) {
                        state = TrendState.UP;
                    } else {
                        state = TrendState.DOWN;
                    }
                } else {
                    if (klineBtc.maxPrice < lastKlineBtc.maxPrice) {
                        state = TrendState.DOWN;
                    } else {
                        state = TrendState.UP;
                    }
                }

                return state;
            }
        }
        return null;
    }


    public static List<String> getTopSymbol2TradeTest(Map<String, KlineObjectNumber> value, int period) {
        TreeMap<Double, String> rateChange2Symbols = new TreeMap<>();
        for (Map.Entry<String, KlineObjectNumber> entry1 : value.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            if (Constants.specialSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectNumber ticker = entry1.getValue();
            Double rateChange;
            rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
            rateChange2Symbols.put(rateChange, symbol);
        }
        return getTopSymbol(value, rateChange2Symbols, period, null);
    }

    public static List<String> getTopSymbolByBreadAbove(Map<String, KlineObjectNumber> value, int period) {
        TreeMap<Double, String> rateChange2Symbols = new TreeMap<>();
        for (Map.Entry<String, KlineObjectNumber> entry1 : value.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectNumber ticker = entry1.getValue();
//            Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.maxPrice);
            Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
            rateChange2Symbols.put(rateChange, symbol);
//            if (ticker.priceClose > ticker.priceOpen) {
//                rateChange = Utils.rateOf2Double(ticker.priceOpen, ticker.maxPrice);
//                rateChange2Symbols.put(-rateChange, symbol);
//            }
        }
        return getTopSymbol(value, rateChange2Symbols, period, null);
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
                Double rateChangeVolume = Utils.rateOf2Double(lastTicker.totalUsdt, ticker.totalUsdt);
                rateChange2Symbols.put(rateChangeVolume, symbol);
            }
        }
        return getTopSymbol(value, rateChange2Symbols, period, null);
    }

    private static void traceCommandMarketTrend() throws ParseException {
        Long duration = 48 * Utils.TIME_HOUR;
        Long numberTicker = duration / (15 * Utils.TIME_MINUTE);
        Double target = 0.007;
        LOG.info("Finish read data statistic");
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
//        Map<String, List<OrderTargetInfoTest>> rateChange2Orders = new HashMap<>();
        TreeMap<Long, List<OrderTargetInfoTest>> time2Orders = new TreeMap<>();
        Map<String, KlineObjectNumber> lastTicker = null;
        while (true) {
            TreeMap<Long, Map<String, KlineObjectNumber>> time2Tickers;
            try {
                time2Tickers = DataManager.readDataFromFile(startTime);
                for (Map.Entry<Long, Map<String, KlineObjectNumber>> entry : time2Tickers.entrySet()) {
                    Long time = entry.getKey();
                    Double volumeAvg = calVolumeAvg(entry.getValue());
                    Double rateChangeAvg = calRateChangeAvg(entry.getValue());
                    MarketLevelChange level = getMarketStatus(rateChangeAvg, volumeAvg);
                    List<String> symbols;
                    int period = 30;
                    symbols = getTopSymbolByBreadAbove(entry.getValue(), period);

                    List<OrderTargetInfoTest> ordersByTime = new ArrayList<>();
                    time2Orders.put(time, ordersByTime);

//                    Map<String, KlineObjectNumber> symbol2DataStatistic = time2SymbolAndRateChange.get(time);
                    Map<String, KlineObjectNumber> symbol2DataStatistic =
                            DataStatisticHelper.getInstance().readDataStaticByTimeAndNumberTickerStatic(time, numberTicker);
                    if (symbol2DataStatistic == null) {
                        LOG.info("Error get data statistic: {}", Utils.normalizeDateYYYYMMDDHHmm(time));
                        continue;
                    }

                    for (String symbol : symbols) {
                        KlineObjectNumber ticker = entry.getValue().get(symbol);
                        KlineObjectNumber klineOfSymbol = symbol2DataStatistic.get(symbol);
                        if (klineOfSymbol == null) {
//                            LOG.info("Error get ticker statistic: {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time));
                            continue;
                        }
                        Double priceTp = Utils.calPriceTarget(symbol, ticker.priceClose, OrderSide.BUY, target);
                        Double budget = 10d;
                        Double quantity = Utils.calQuantity(budget, 10, ticker.priceClose, symbol);
                        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, ticker.priceClose, priceTp, quantity,
                                10, symbol, ticker.startTime.longValue(), ticker.endTime.longValue(), OrderSide.BUY);
                        order.minPrice = klineOfSymbol.minPrice;
                        order.lastPrice = klineOfSymbol.priceClose;
                        order.maxPrice = klineOfSymbol.maxPrice;
                        order.marketLevelChange = level;
                        order.tickerOpen = ticker;
                        order.ma201d = rateChangeAvg;
                        order.volume = volumeAvg;
                        if (lastTicker != null && lastTicker.get(symbol) != null) {
                            order.avgVolume24h = lastTicker.get(symbol).totalUsdt;
                        }
                        if (klineOfSymbol.minPrice < order.priceTP && klineOfSymbol.maxPrice > order.priceTP) {
                            order.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                        } else {
                            order.status = OrderTargetStatus.STOP_LOSS_DONE;
                            order.priceTP = klineOfSymbol.priceClose;
                        }
//                        orders.add(order);
                        ordersByTime.add(order);
                    }
                    lastTicker = entry.getValue();
                }

            } catch (Exception e) {
                e.printStackTrace();
            }
            startTime += Utils.TIME_DAY;
            if (startTime > System.currentTimeMillis()) {
                break;
            }
        }
//        Storage.writeObject2File("target/MarketOrderStatisticMacd.data", rateChange2Orders);
        Storage.writeObject2File("target/MarketOrderByTimeMacd.data", time2Orders);
        LOG.info("Finished!");
    }


    public static List<String> getTopSymbol2TradeWithMacdTrend(Map<String, KlineObjectNumber> lastValue,
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
//                if (lastTicker.histogram != null && lastTicker.histogram > 0 && ticker.histogram > 0) {
//                    Double macdRateChange = Utils.rateOf2Double(lastTicker.histogram, ticker.histogram);
//                    rateChange2Symbols.put(macdRateChange, symbol);
//                }
                if (ticker.totalUsdt / lastTicker.totalUsdt >= 5 && ticker.totalUsdt / lastTicker.totalUsdt < 10
                        && Utils.rateOf2Double(ticker.maxPrice, ticker.minPrice) > 0.022
                        && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < -0.01) {
                    Double macdRateChange = Utils.rateOf2Double(ticker.maxPrice, ticker.minPrice);
                    rateChange2Symbols.put(macdRateChange, symbol);
                }
            }
        }
        return getTopSymbol(value, rateChange2Symbols, period, null);
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

        return calRateLossAvg(rateLoss2Symbols);
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


    private static Double calRateLossAvg(TreeMap<Double, String> rateLoss2Symbols) {
        Double total = 0d;
        int counter = 0;
        for (Map.Entry<Double, String> entry : rateLoss2Symbols.entrySet()) {
            Double key = entry.getKey();
            counter++;
            total += key;
        }
        if (rateLoss2Symbols.isEmpty()) {
            return 0d;
        }
        return total / counter;
    }


    private static void printDataByTime(int numberOrderCheck) {
        TreeMap<Long, List<OrderTargetInfoTest>> time2Orders =
                (TreeMap<Long, List<OrderTargetInfoTest>>) Storage.readObjectFromFile("target/MarketOrderByTimeMacd.data");
        List<KlineObjectNumber> btcTickers = (List<KlineObjectNumber>)
                Storage.readObjectFromFile(DataManager.FOLDER_TICKER_15M + Constants.SYMBOL_PAIR_BTC);

        Map<Long, KlineObjectNumber> time2BtcKline = new HashMap<>();
        for (KlineObjectNumber klineBtc : btcTickers) {
            time2BtcKline.put(klineBtc.startTime.longValue(), klineBtc);
        }
        Double target = 0.007;
        List<String> lines = new ArrayList<>();
        StringBuilder builder = new StringBuilder();
        for (Map.Entry<Long, List<OrderTargetInfoTest>> entry : time2Orders.entrySet()) {
            Long time = entry.getKey();
            List<OrderTargetInfoTest> orders = entry.getValue();
            if (orders.size() == 0) {
                continue;
            }
            Integer counterSuccess = 0;
            double totalFalse = 0d;
            List<String> symbols = new ArrayList<>();
            int counter = 0;
            for (OrderTargetInfoTest order : orders) {
                Double rateChange = Utils.rateOf2Double(order.tickerOpen.priceClose, order.tickerOpen.priceOpen);
                Double rateMa15 = 0d;
                if (order.tickerOpen.ma20 != null) {
                    rateMa15 = Utils.rateOf2Double(order.tickerOpen.priceClose, order.tickerOpen.ma20);
                }
                if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                    symbols.add(order.symbol + " " + rateMa15 + " True " + rateChange);
                    counterSuccess++;
                } else {
                    Double rateFalse = Utils.rateOf2Double(order.priceTP, order.priceEntry);
                    totalFalse += rateFalse;
                    symbols.add(order.symbol + " " + rateMa15 + " False " + rateChange + " " + rateFalse);
                }
                counter++;
                if (counter >= numberOrderCheck) {
                    break;
                }
            }
            double totalAll = counterSuccess * target + totalFalse;
            Double rateFalseTotal = -totalFalse * 100 / (counterSuccess * target);
            if (counterSuccess == 0) {
                rateFalseTotal = 100d;
            }
            rateFalseTotal = rateFalseTotal.longValue() / 100d;
            Double rateDone = counterSuccess.doubleValue() / orders.size();


            LOG.info("{} {}-> orders: {}/{} {}% rateLoss:{}% All:{}%", Utils.normalizeDateYYYYMMDDHHmm(time),
                    Utils.formatMoneyByPeriod(orders.get(0).ma201d * 100, 4),
                    counterSuccess, orders.size(), rateDone * 100, Utils.formatPercent(rateFalseTotal), Utils.formatPercent(totalAll));
            builder.setLength(0);
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(time)).append(",");
            builder.append(orders.get(0).marketLevelChange).append(",");
            builder.append(Utils.formatMoneyByPeriod(orders.get(0).ma201d * 100, 4)).append(",");
            builder.append(orders.get(0).volume).append(",");

            int period = 32;
            Double volumeBtcTotal = calVolumeTotalByTime(time2BtcKline, time, period);
            Double volumeBtcAvg = calVolumeAvgByTime(time2BtcKline, time, period);

            KlineObjectNumber klineBtc = time2BtcKline.get(time);
            KlineObjectNumber klineStatistic2Hour = TickerFuturesHelper.extractKlineByTime(btcTickers, time, 2 * Utils.TIME_HOUR);
            KlineObjectNumber klineStatistic24hr = TickerFuturesHelper.extractKline24hr(btcTickers, time);
            if (klineBtc == null) {
                builder.append("null").append(",");
                builder.append("null").append(",");
                builder.append("null").append(",");
                builder.append("null").append(",");
                builder.append("null").append(",");
                builder.append("null").append(",");
                builder.append("null").append(",");
            } else {
                Double breadAbove = Utils.rateOf2Double(klineBtc.maxPrice, klineBtc.priceOpen);
                Double breadBellow = Utils.rateOf2Double(klineBtc.priceClose, klineBtc.minPrice);
                if (klineBtc.priceClose > klineBtc.priceOpen) {
                    breadAbove = Utils.rateOf2Double(klineBtc.maxPrice, klineBtc.priceClose);
                    breadBellow = Utils.rateOf2Double(klineBtc.priceOpen, klineBtc.minPrice);
                }
                builder.append(Utils.rateOf2Double(klineBtc.priceClose, klineBtc.priceOpen)).append(",");
                builder.append(breadAbove).append(",");
                builder.append(breadBellow).append(",");
                builder.append(klineStatistic2Hour.maxPrice).append(",");
                builder.append(Utils.rateOf2Double(klineStatistic2Hour.maxPrice, klineBtc.priceClose)).append(",");
                builder.append(Utils.rateOf2Double(klineBtc.priceClose, klineStatistic24hr.priceOpen)).append(",");
                builder.append(klineBtc.totalUsdt / 1E6).append(",");
            }

//            builder.append(btcRating15m.get(time)).append(",");
//            builder.append(btcRating1h.get(Utils.getHour(time))).append(",");
            builder.append(volumeBtcAvg).append(",");
            builder.append(volumeBtcTotal).append(",");
            builder.append(counterSuccess).append(",");
            builder.append(orders.size()).append(",");
            builder.append(rateDone * 100).append("%,");
            builder.append(Utils.formatPercent(rateFalseTotal)).append("%,");
            builder.append(Utils.formatPercent(totalAll)).append("%,");
            builder.append(symbols).append(",");
            lines.add(builder.toString());
        }
        try {
            FileUtils.writeLines(new File("target/markettrace_macd.csv"), lines);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void printDataSell() {
        TreeMap<Long, List<OrderTargetInfoTest>> time2Orders =
                (TreeMap<Long, List<OrderTargetInfoTest>>) Storage.readObjectFromFile("target/MarketOrderSELL.data");
        List<KlineObjectNumber> btcTickers = (List<KlineObjectNumber>)
                Storage.readObjectFromFile(DataManager.FOLDER_TICKER_15M + Constants.SYMBOL_PAIR_BTC);

        Map<Long, KlineObjectNumber> time2BtcKline = new HashMap<>();
        for (KlineObjectNumber klineBtc : btcTickers) {
            time2BtcKline.put(klineBtc.startTime.longValue(), klineBtc);
        }
        Double target = 0.007;
        List<String> lines = new ArrayList<>();
        StringBuilder builder = new StringBuilder();
//        try {
//            Long time = Utils.sdfFileHour.parse("20240711 19:00").getTime();
//            List<OrderTargetInfoTest> orders = time2Orders.get(time);
//            LOG.info("{}", Utils.toJson(orders));
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
        List<Long> timeBtcUpReverse = extractBtcUpReverse();
        for (Map.Entry<Long, List<OrderTargetInfoTest>> entry : time2Orders.entrySet()) {
            Long time = entry.getKey();
            List<OrderTargetInfoTest> orders = entry.getValue();
            if (orders.size() == 0) {
                continue;
            }
            Integer counterSuccess = 0;
            double totalFalse = 0d;
            List<String> symbols = new ArrayList<>();
            for (OrderTargetInfoTest order : orders) {
                Double rateChange = Utils.rateOf2Double(order.tickerOpen.priceClose, order.tickerOpen.priceOpen);
                Double rateMa15 = 0d;
                if (order.tickerOpen.ma20 != null) {
                    rateMa15 = Utils.rateOf2Double(order.tickerOpen.priceClose, order.tickerOpen.ma20);
                }
                if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                    symbols.add(order.symbol + " " + rateMa15 + " True " + rateChange);
                    counterSuccess++;
                } else {
                    Double rateFalse = -Utils.rateOf2Double(order.priceTP, order.priceEntry);
                    totalFalse += rateFalse;
                    symbols.add(order.symbol + " " + rateMa15 + " False " + rateChange + " " + rateFalse);
                }

            }
            double totalAll = counterSuccess * target + totalFalse;
            Double rateFalseTotal = -totalFalse * 100 / (counterSuccess * target);
            if (counterSuccess == 0) {
                rateFalseTotal = 100d;
            }
            rateFalseTotal = rateFalseTotal.longValue() / 100d;
            Double rateDone = counterSuccess.doubleValue() / orders.size();


            KlineObjectNumber btcKline = time2BtcKline.get(time);
            LOG.info("{} {}-> orders: {}/{} {}% rateLoss:{}% All:{}%", Utils.normalizeDateYYYYMMDDHHmm(time),
                    Utils.formatMoneyByPeriod(orders.get(0).ma201d * 100, 4),
                    counterSuccess, orders.size(), rateDone * 100, Utils.formatPercent(rateFalseTotal), Utils.formatPercent(totalAll));
            builder.setLength(0);
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(time)).append(",");
            builder.append(Utils.formatMoneyByPeriod(orders.get(0).ma201d * 100, 4)).append(",");
            builder.append(orders.get(0).volume).append(",");
            if (btcKline == null) {
                builder.append("null").append(",");
                builder.append("null").append(",");
                builder.append("null").append(",");
            } else {
                builder.append(Utils.rateOf2Double(btcKline.priceClose, btcKline.priceOpen)).append(",");
                double btcVolume = btcKline.totalUsdt / 1E6;
                builder.append(btcVolume).append(",");
                builder.append(Utils.rateOf2Double(btcKline.maxPrice, btcKline.minPrice)).append(",");
            }

            builder.append(timeBtcUpReverse.contains(time)).append(",");
            builder.append(counterSuccess).append(",");
            builder.append(orders.size()).append(",");
            builder.append(rateDone * 100).append("%,");
            builder.append(Utils.formatPercent(rateFalseTotal)).append("%,");
            builder.append(Utils.formatPercent(totalAll)).append("%,");
            builder.append(symbols).append(",");
            lines.add(builder.toString());
        }
        try {
            FileUtils.writeLines(new File("target/market_sell_entry.csv"), lines);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static Boolean isBtcBottomReverse(List<KlineObjectNumber> btcTickers, Long startTime) {
        Integer index = null;
        for (int i = 0; i < btcTickers.size(); i++) {
            KlineObjectNumber ticker = btcTickers.get(i);
            if (ticker.startTime.longValue() == startTime) {
                index = i;
                break;
            }
        }
        if (index == null) {
            return false;
        }
        return isBtcBottomReverse(btcTickers, index);
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

    public static OrderSide isAltReverseAtBottom(List<KlineObjectNumber> altTickers, Integer index) {
        try {
            if (index < 200) {
                return null;
            }
            // check 200 ticker ago had change 4%
            int counterBuy = 0;
            int counterSell = 0;
            int counterNeutral = 0;
            for (int i = 0; i < 100; i++) {
                KlineObjectNumber kline = altTickers.get(index - i);
                if (kline.maxPrice < kline.ma20) {
                    counterSell++;
                } else {
                    if (kline.minPrice > kline.ma20) {
                        counterBuy++;
                    } else {
                        counterNeutral++;
                    }
                }
//                if (Utils.rateOf2Double(kline.maxPrice, kline.minPrice) >= 0.04) {
//                    return null;
//                }
            }
            ArrayList<KlineObjectNumber> tickers = new ArrayList<>();
            KlineObjectNumber beforeLastFinalTicker = altTickers.get(index - 2);
            KlineObjectNumber lastFinalTicker = altTickers.get(index - 1);
            KlineObjectNumber finalTicker = altTickers.get(index);
            for (int i = index - 100; i <= index; i++) {
                tickers.add(altTickers.get(i));
            }
            List<TrendObject> trends = TickerFuturesHelper.extractTopBottomObjectInTicker(tickers);
            if (trends.size() > 1) {
                TrendObject lastFinalTrend = trends.get(trends.size() - 3);
                TrendObject finalTrend = trends.get(trends.size() - 1);
                if (finalTicker.totalUsdt / lastFinalTicker.totalUsdt < 0.4
                        && beforeLastFinalTicker.totalUsdt / lastFinalTicker.totalUsdt < 0.4
                        && finalTrend.kline.startTime == lastFinalTicker.startTime) {
                    LOG.info("{} {} {} {} {}/{}/{}", Utils.normalizeDateYYYYMMDDHHmm(finalTicker.startTime.longValue()),
                            lastFinalTicker.totalUsdt / 1E6, finalTicker.totalUsdt / 1E6, finalTrend.status,
                            counterBuy, counterSell, counterNeutral);
                    if (finalTrend.status.equals(TrendState.BOTTOM)) {
//                        if (lastFinalTrend.getMinPrice() < finalTrend.getMinPrice()) {
                        return OrderSide.BUY;
//                        }
                    } else {
//                        if (lastFinalTrend.getMaxPrice() > finalTrend.getMaxPrice()) {
                        return OrderSide.SELL;
//                        }
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static OrderSide isAltVolumeReverse(List<KlineObjectNumber> altTickers, Integer index) {
        try {
            if (index < 100) {
                return null;
            }
            // check 200 ticker ago had change 4%
            int counterBuy = 0;
            int counterSell = 0;
            int counterNeutral = 0;
            Double totalVolume = 0d;
            Double priceChange = 0d;

            for (int i = 0; i < 100; i++) {
                KlineObjectNumber kline = altTickers.get(index - i);
                if (kline.maxPrice < kline.ma20) {
                    counterSell++;
                } else {
                    if (kline.minPrice > kline.ma20) {
                        counterBuy++;
                    } else {
                        counterNeutral++;
                    }
                }
                totalVolume += kline.totalUsdt;
                priceChange += Utils.rateOf2Double(kline.priceClose, kline.priceOpen);
//                if (Utils.rateOf2Double(kline.maxPrice, kline.minPrice) >= 0.04) {
//                    return null;
//                }
            }
            Double volumeAvg = totalVolume / 100;
            KlineObjectNumber beforeLastFinalTicker = altTickers.get(index - 2);
            KlineObjectNumber lastFinalTicker = altTickers.get(index - 1);
            KlineObjectNumber finalTicker = altTickers.get(index);
            OrderSide side = null;
            if (finalTicker.totalUsdt < volumeAvg) {
                if (Math.abs(priceChange) > 0.02) {
                    if (finalTicker.priceClose < finalTicker.ma20) {
                        side = OrderSide.BUY;
                    } else {
                        side = OrderSide.SELL;
                    }
                }
            }
//            LOG.info("{} {} {} {} {} {} {}/{}/{}", Utils.normalizeDateYYYYMMDDHHmm(finalTicker.startTime.longValue()), side,
//                    finalTicker.totalUsdt,finalTicker.totalUsdt/volumeAvg, volumeAvg, priceChange,
//                    counterBuy, counterSell, counterNeutral);
            LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(finalTicker.startTime.longValue()), priceChange * 100);
            return side;
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static List<Integer> getSignalBuyAlt15M(List<KlineObjectNumber> altTickers, Integer index) {
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
                Double rateChange = Utils.rateOf2Double(finalTicker.priceClose, finalTicker.priceOpen);
                Double rateChangeTotal = Utils.rateOf2Double(finalTicker.maxPrice, finalTicker.minPrice);
                if (
                        finalTrendTop.status.equals(TrendState.TOP)
                                && rateChange < -0.003
                                && finalTicker.totalUsdt > lastTicker.totalUsdt * 2
                                && finalTicker.totalUsdt < lastTicker.totalUsdt * 10
                ) {
                    Double rateChangeWithTop = Utils.rateOf2Double(finalTrendTop.kline.maxPrice, finalTicker.priceClose);
                    if (rateChangeWithTop > 0.030) {
                        results.add(1);
                    }
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

//    public static Integer getSignalBuyAlt15MExtend(List<KlineObjectNumber> altTickers, Integer index) {
//        try {
//            if (index == null || index < 2) {
//                return 0;
//            }
//            ArrayList<KlineObjectNumber> tickers = new ArrayList<>();
//            KlineObjectNumber finalTicker = altTickers.get(index);
//            KlineObjectNumber lastTicker = altTickers.get(index - 1);
//            int start = 0;
//            if (index > 100) {
//                start = index - 100;
//            }
//            for (int i = start; i <= index; i++) {
//                tickers.add(altTickers.get(i));
//            }
//            // check 20 ticker ko co ticker vượt 5%
//            Double min24h = lastTicker.minPrice;
//            Boolean isHaveTickerOver = false;
//            for (int i = 0; i < 192; i++) {
//                if (index >= i) {
//                    KlineObjectNumber ticker = altTickers.get(index - i);
//                    if (Utils.rateOf2Double(ticker.maxPrice, ticker.minPrice) > 0.05) {
//                        isHaveTickerOver = true;
//                        break;
//                    }
//                    if (i < 96
//                            && min24h > ticker.minPrice) {
//                        min24h = ticker.minPrice;
//                    }
//                }
//            }
//            Double rateChange = Utils.rateOf2Double(finalTicker.priceClose, finalTicker.priceOpen);
//            Double rateChangeTotal = Utils.rateOf2Double(finalTicker.maxPrice, finalTicker.minPrice);
//            List<TrendObject> trends = TickerFuturesHelper.extractTopBottomObjectInTicker(tickers);
//            if (trends.size() > 1) {
//                TrendObject finalTrendTop = trends.get(trends.size() - 1);
//                if (
//                        finalTrendTop.status.equals(TrendState.TOP)
//                                && rateChange < -0.003
//                                && finalTicker.totalUsdt > lastTicker.totalUsdt * 2
//                                && finalTicker.totalUsdt < lastTicker.totalUsdt * 10
//                                && !isHaveTickerOver
//                                && rateChangeTotal < 0.04
//                                && finalTicker.minPrice > min24h
//                ) {
//                    if (Utils.rateOf2Double(finalTrendTop.kline.maxPrice, finalTicker.priceClose) > 0.04) {
////                        KlineObjectNumber ticker2Hours = TickerFuturesHelper.extractKlineByNumberTicker(altTickers, index, 5);
////                        if (ticker2Hours.maxPrice != finalTrendTop.getMaxPrice()) {
////                            LOG.info("{} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(altTickers.get(index).startTime.longValue()),
////                                    finalTrendTop.kline.startTime.longValue(), finalTrendTop.getMaxPrice(), ticker2Hours.maxPrice);
////                        }
//                        return 1;
//                    }
//
//                }
//            }
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
//        return 0;
//    }

    public static Integer getSignalSellAlt15M(List<KlineObjectNumber> altTickers, Integer index) {
        try {
            if (index == null || index < 2) {
                return 0;
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
            List<TrendObject> trends = TickerFuturesHelper.extractTopBottomObjectInTicker(tickers);
            if (trends.size() > 1) {
                TrendObject finalTrendTop = trends.get(trends.size() - 1);
                if (
                        finalTrendTop.status.equals(TrendState.BOTTOM)
                                && Utils.rateOf2Double(finalTicker.priceClose, finalTicker.priceOpen) > 0.003
                                && finalTicker.totalUsdt < lastTicker.totalUsdt * 2
                ) {
                    if (Utils.rateOf2Double(finalTrendTop.kline.minPrice, finalTicker.priceClose) < -0.05) {
//                        KlineObjectNumber ticker2Hours = TickerFuturesHelper.extractKlineByNumberTicker(altTickers, index, 5);
//                        if (ticker2Hours.maxPrice != finalTrendTop.getMaxPrice()) {
//                            LOG.info("{} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(altTickers.get(index).startTime.longValue()),
//                                    finalTrendTop.kline.startTime.longValue(), finalTrendTop.getMaxPrice(), ticker2Hours.maxPrice);
//                        }
                        return 1;
                    }

                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return 0;
    }

    private static Double calVolumeTotalByTime(Map<Long, KlineObjectNumber> btcTickers, Long time, int period) {
        KlineObjectNumber tickerCurrent = btcTickers.get(time);
        Double volumeTotal = 0d;
        if (tickerCurrent != null) {
            for (int i = 0; i < period; i++) {
                KlineObjectNumber ticker = btcTickers.get(time - i * 15 * Utils.TIME_MINUTE);
                if (ticker == null) {
                    break;
                }
                if (ticker.priceClose < ticker.priceOpen) {
                    volumeTotal -= ticker.totalUsdt;
                } else {
                    volumeTotal += ticker.totalUsdt;
                }
            }
        }
        return volumeTotal / 1E6;
    }

    private static Double calVolumeAvgByTime(Map<Long, KlineObjectNumber> btcTickers, Long time, int period) {
        KlineObjectNumber tickerCurrent = btcTickers.get(time);
        Double volumeTotal = 0d;
        int counter = 0;
        if (tickerCurrent != null) {
            for (int i = 0; i < period; i++) {
                KlineObjectNumber ticker = btcTickers.get(time - i * 15 * Utils.TIME_MINUTE);
                if (ticker == null) {
                    break;
                }
                counter++;
                volumeTotal += ticker.totalUsdt;
            }
        }
        volumeTotal = volumeTotal / 1E6;
        return volumeTotal / counter;
    }

    private static Double calVolumeAvgByTime(List<KlineObjectNumber> tickers, int period) {
        Double volumeTotal = 0d;
        int counter = 0;
        for (int i = 0; i < period; i++) {
            if (tickers.size() - 1 - i < 0) {
                break;
            }
            KlineObjectNumber ticker = tickers.get(tickers.size() - 1 - i);
            counter++;
            volumeTotal += ticker.totalUsdt;
        }
        return volumeTotal / counter;
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
//        if (rateLossAvg < -0.019 && volumeAvg > 9) {
//            return MarketLevelChange.MINI_DOWN_EXTEND;
//        }
        if (rateLossAvg > 0.04) {
            return MarketLevelChange.BIG_UP;
        }
        if (rateLossAvg > 0.035) {
            return MarketLevelChange.MEDIUM_UP;
        }
        if (rateLossAvg > 0.021) {
            return MarketLevelChange.SMALL_UP;
        }
        return null;
    }
}
