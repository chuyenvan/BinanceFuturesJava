package com.binance.chuyennd.bigchange.btctd;

import com.binance.chuyennd.client.PriceManager;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.movingaverage.MAStatus;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetInfo;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.educa.chuyennd.funcs.BreadFunctions;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.text.ParseException;
import java.util.*;
import java.util.logging.Level;

/**
 * @author pc
 */
public class BigChange15M2Mongo {

    public static final Logger LOG = LoggerFactory.getLogger(BigChange15M2Mongo.class);
    private static final int NUMBER_TICKER_TO_TRADE = 30 * 96;
    public BreadDetectObject lastBreadTrader = null;
    public Long lastTimeBreadTrader = 0l;
    public Double RATE_BREAD_MIN_2TRADE = Configs.getDouble("RATE_BREAD_MIN_2TRADE");
    public Double ALT_BREAD_BIGCHANGE_15M = 0.008;
    public Double ALT_BREAD_BIGCHANE_STOPPLOSS = 0.1;
    public Double RATE_CHANGE_WITHBREAD_2TRADING_TARGET = 0.009;
    public Integer counterTotal = 0;
    public Integer counterSuccess = 0;
    public Integer counterStoploss = 0;
    public Double totalLoss = 0d;
    public String FOLDER_TICKER_15M = "storage/ticker/symbols-15m/";
    public Map<String, Double> symbol2LastPrice = new HashMap<>();
    public Map<Long, Map<String, MAStatus>> time2MaInfos = new HashMap<>();

    private void startDetectBreadAlt() throws ParseException {
//        Long startTime = 1679158800000L;
//        Long startTime = 1695574800000L;
        Long startTime = 1705078800000L;
//        Long startTime = Utils.sdfFileHour.parse("20240124 09:15").getTime();
//        Long startTime = Utils.getStartTimeDayAgo(10);
        LOG.info("Start detect with time start: {}- {}", startTime, new Date(startTime));
        long numberDay = (System.currentTimeMillis() - startTime) / Utils.TIME_DAY;
        Map<String, List<KlineObjectNumber>> allSymbolTickers = TickerFuturesHelper.getAllKlineStartTime(Constants.INTERVAL_15M, startTime);
        List<KlineObjectNumber> btcKlines = allSymbolTickers.get(Constants.SYMBOL_PAIR_BTC);
        Set<Double> btcBigChangeTimes = extractBtcBigChange(btcKlines);

        // test for multi param
        try {
            ArrayList<Double> rateBreads = new ArrayList<>(Arrays.asList(0.006, 0.007, 0.008, 0.01, 0.012, 0.014, 0.016, 0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.06));
            ArrayList<Double> rateTargets = new ArrayList<>(Arrays.asList(0.009, 0.01, 0.011, 0.013, 0.014, 0.015, 0.02, 0.025,
                    //                                        0.03
                    0.03, 0.035, 0.040, 0.045, 0.05, 0.055, 0.06, 0.065, 0.1));

            ArrayList<Double> listRateChanges = new ArrayList<>(Arrays.asList(0.02, 0.025, 0.03, 0.035,
                    //                                        0.04
                    0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10
                    //                    0.11,
                    //                    0.12,
                    //                    0.13
            ));
            List<String> lines = new ArrayList<>();

            for (Double rateBread : rateBreads) {
                for (Double rateChange : listRateChanges) {
                    for (Double rateTarget : rateTargets) {
                        lines.addAll(detectBigChangeWithParam(rateBread, rateChange, rateTarget, allSymbolTickers, numberDay, btcBigChangeTimes));
                    }
                }
            }
            FileUtils.writeLines(new File("target/data/failTradeWithBread.csv"), lines);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void startDetectBigChangeVolumeMiniInterval15M() throws ParseException {
//        Long startTime = 1679158800000L;
        Long startTime = 1709658000000L;
//        Long startTime = Utils.sdfFileHour.parse("20240124 09:15").getTime();
//        Long startTime = Utils.getStartTimeDayAgo(10);
        PriceManager.getInstance();
        LOG.info("Start detect with time start: {}- {}", startTime, new Date(startTime));
        long numberDay = (System.currentTimeMillis() - startTime) / Utils.TIME_DAY;
        Map<String, List<KlineObjectNumber>> allSymbolTickers = TickerFuturesHelper.getAllKlineStartTime(Constants.INTERVAL_15M, startTime, 4 * Utils.TIME_HOUR);
//        List<KlineObjectNumber> btcKlines = allSymbolTickers.get(Constants.SYMBOL_PAIR_BTC);
//        Set<Double> btcBigChangeTimes = extractBtcBigChange(btcKlines);
        Set<Double> btcBigChangeTimes = new HashSet<>();

        // test for multi param
        try {

            ArrayList<Double> rateTargets = new ArrayList<>(Arrays.asList(0.01));
            ArrayList<Double> volumes = new ArrayList<>(Arrays.asList(
                    //                    0.2,
                    //                    0.3,
                    //                    0.4,
//                    0.5,
//                    0.7,
//                    0.8,
//                    0.9,
                    1.4
//                    2.0

            ));

            ArrayList<Double> listRateChanges = new ArrayList<>(Arrays.asList(0.021));
            List<String> lines = new ArrayList<>();

            for (Double volume : volumes) {
                for (Double rateChange : listRateChanges) {
                    for (Double rateTarget : rateTargets) {
                        lines.addAll(detectBigChangeWithParam(rateTarget, rateChange, volume, allSymbolTickers, numberDay, btcBigChangeTimes));
                    }

                }
            }
            printByDate(lines);
            FileUtils.writeLines(new File("failTradeWithVolume.csv"), lines);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void startDetectBigChangeVolumeMiniInterval15MDataMongo() throws ParseException {

        long start_time = Configs.getLong("start_time");
        // test for multi param
        try {
            ArrayList<Double> volumes = new ArrayList<>(Arrays.asList());
            for (int i = 0; i < 30; i++) {
                volumes.add(0.4 + i * 0.1);
            }
            ArrayList<Double> rateTargets = new ArrayList<>(Arrays.asList(0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06, 0.065, 0.07));
            ArrayList<Double> listRateChanges = new ArrayList<>(Arrays.asList(0.02, 0.021, 0.022, 0.023, 0.024, 0.025, 0.026, 0.027, 0.028, 0.029,
                    0.03, 0.032, 0.034, 0.036, 0.038, 0.040, 0.045, 0.050, 0.06, 0.07, 0.08, 0.09, 0.1, 0.11, 0.12, 0.13, 0.14, 0.15));
            List<String> lines = new ArrayList<>();
            Map<String, List<KlineObjectNumber>> symbol2Tickers = readData(start_time);
            for (Double rateTarget : rateTargets) {
                for (Double volume : volumes) {
                    for (Double rateChange : listRateChanges) {
//                        lines.addAll(detectBigChangeWithParamNew(rateTarget, rateChange, symbol2Tickers, volume));
                        detectBigChangeWithParamNew(rateTarget, rateChange, symbol2Tickers, volume);
//                    executorService.execute(() -> detectBigChangeWithParamNew(RATE_TARGET, rateChange, symbol2Tickers, volume));
                    }
                }
            }
//            printByDate(lines);
            FileUtils.writeLines(new File("failTradeWithVolume.csv"), lines);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void startDetectBigChangeVolumeMiniInterval15MDataMongoNew() throws ParseException {
        long start_time = Configs.getLong("start_time");
        // test for multi param
        try {
            List<String> lines = new ArrayList<>();

            Map<String, List<KlineObjectNumber>> symbol2Tickers = readData(start_time);
            ArrayList<Double> rateTargets = new ArrayList<>(Arrays.asList(0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06, 0.065, 0.07));
//            ArrayList<Double> rateTargets = new ArrayList<>(Arrays.asList(0.02,0.025,0.03, 0.035));
            ArrayList<Integer> NUMBER_TICKER_TO_TRADES = new ArrayList<>();
//            for (int i = 1; i < 20; i++) {
            for (int i = 16; i < 17; i++) {
                NUMBER_TICKER_TO_TRADES.add(i);
            }
            for (Integer NUMBER_TICKER_TO_TRADE : NUMBER_TICKER_TO_TRADES) {
                for (Double rateTarget : rateTargets) {
                    lines.addAll(detectBigChangeWithVolumeFixRate(rateTarget, symbol2Tickers, NUMBER_TICKER_TO_TRADE * 96));
                }
            }
//            printByDate(lines);
            FileUtils.writeLines(new File("failTradeWithVolume.csv"), lines);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }


    private Map<String, List<KlineObjectNumber>> readData(long startTime) {
        Map<String, List<KlineObjectNumber>> symbol2Tickers = null;
        String fileName = FOLDER_TICKER_15M + startTime + ".data";
        File fileDataAll = new File(fileName);
        if (fileDataAll.exists() && fileDataAll.lastModified() > Utils.getStartTimeDayAgo(1)) {
            symbol2Tickers = (Map<String, List<KlineObjectNumber>>) Storage.readObjectFromFile(fileName);
        }
        if (symbol2Tickers == null) {
            symbol2Tickers = readFromFileSymbol(startTime);
            Storage.writeObject2File(fileName, symbol2Tickers);
        }
        return symbol2Tickers;
    }

    private Map<String, List<KlineObjectNumber>> readFromFileSymbol(long startTime) {
        Map<String, List<KlineObjectNumber>> symbol2Tickers = new HashMap<>();
        File[] symbolFiles = new File(FOLDER_TICKER_15M).listFiles();
        long startAt = System.currentTimeMillis();
        for (File symbolFile : symbolFiles) {
            String symbol = symbolFile.getName();
            if (!StringUtils.endsWithIgnoreCase(symbol, "usdt")) {
                continue;
            }
            List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(symbolFile.getPath());
            while (true) {
                long time = tickers.get(0).startTime.longValue();
                if (time < startTime) {
                    tickers.remove(0);
                } else {
                    break;
                }
            }
            symbol2Tickers.put(symbol, tickers);
        }
        LOG.info("Read data: {}s", (System.currentTimeMillis() - startAt) / Utils.TIME_SECOND);
        return symbol2Tickers;
    }

    private void startDetectWithTargetIntervalOneHour() throws ParseException {
        Long startTime = 1680541200000L;
        LOG.info("Start detect with time start: {}- {}", startTime, new Date(startTime));
        long numberDay = (System.currentTimeMillis() - startTime) / Utils.TIME_DAY;
        Map<String, List<KlineObjectNumber>> allSymbolTickers = TickerFuturesHelper.getAllKlineStartTime(Constants.INTERVAL_1H, startTime);
        List<KlineObjectNumber> btcKlines = allSymbolTickers.get(Constants.SYMBOL_PAIR_BTC);
        Set<Double> btcBigChangeTimes = extractBtcBigChange(btcKlines);

        // test for multi param
        try {
            ArrayList<Double> rateTargets = new ArrayList<>(Arrays.asList(0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1));
            ArrayList<Double> rateBreads = new ArrayList<>(Arrays.asList(0.01, 0.012, 0.014, 0.016, 0.018, 0.02, 0.022, 0.024, 0.026, 0.028, 0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06));
//            ArrayList<Double> rateTargets = new ArrayList<>(Arrays.asList(
//                    0.009,
//                    0.01,
//                    0.011,
//                    0.013,
//                    0.014,
//                    0.015,
//                    0.02,
//                    0.025,
//                    0.03,
//                    0.035
//
//            ));

            ArrayList<Double> listRateChanges = new ArrayList<>(Arrays.asList(0.02, 0.025, 0.03, 0.035,
                    //                                        0.04
                    0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.12, 0.14, 0.16, 0.20
                    //                    0.11,
                    //                    0.12,
                    //                    0.13
            ));
            List<String> lines = new ArrayList<>();

            for (Double rateTarget : rateTargets) {
                for (Double rateBread : rateBreads) {
                    for (Double rateChange : listRateChanges) {
                        lines.addAll(detectBigChangeWithParam(rateBread, rateChange, rateTarget, allSymbolTickers, numberDay, btcBigChangeTimes));
                    }
                }
            }

            printByDate(lines);

            FileUtils.writeLines(new File("target/data/failTradeWithBreadIntervalOneHour.csv"), lines);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void startDetectWithTargetInterval4Hour() throws ParseException {
        Long startTime = 1680541200000L;
        LOG.info("Start detect with time start: {}- {}", startTime, new Date(startTime));
        long numberDay = (System.currentTimeMillis() - startTime) / Utils.TIME_DAY;
        Map<String, List<KlineObjectNumber>> allSymbolTickers = TickerFuturesHelper.getAllKlineStartTime(Constants.INTERVAL_4H, startTime);
        List<KlineObjectNumber> btcKlines = allSymbolTickers.get(Constants.SYMBOL_PAIR_BTC);
        Set<Double> btcBigChangeTimes = extractBtcBigChange(btcKlines);
//        Set<Double> btcBigChangeTimes = new HashSet<>();

        // test for multi param
        try {
//            ArrayList<Double> rateBreads = new ArrayList<>(Arrays.asList(
//                    0.01
            //                    0.012,
            //                    0.014,
            //                    0.016,
            //                    0.018,
            //                    0.02,
            //                    0.022,
            //                    0.024,
            //                    0.026,
            //                    0.028,
            //                    0.03,
            //                    0.035,
            //                    0.04,
            //                    0.045,
            //                    0.05,
            //                    0.055,
            //                    0.06
//            ));
            ArrayList<Double> rateTargets = new ArrayList<>(Arrays.asList(0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1));

            ArrayList<Double> listRateChanges = new ArrayList<>(Arrays.asList(0.08, 0.09, 0.10, 0.11, 0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19, 0.20, 0.21
                    //                                0.11,
                    //                                0.12,
                    //                                0.13
            ));
            List<String> lines = new ArrayList<>();

            for (Double rateTarget : rateTargets) {
                for (Double rateChange : listRateChanges) {
                    lines.addAll(detectBigChangeWithParam(0.01, rateChange, rateTarget, allSymbolTickers, numberDay, btcBigChangeTimes));

                }
            }
            FileUtils.writeLines(new File("target/BreadInterval4Hour.csv"), lines);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void startTradeMaxBreadInterval15M() throws ParseException {
//        Long startTime = 1695574800000L;
        Long startTime = 1680541200000L;
//        Long startTime = 1705165200000L;
        List<String> lines = new ArrayList<>();
        LOG.info("Start detect with time start: {}- {}", startTime, new Date(startTime));
        Map<String, List<KlineObjectNumber>> allSymbolTickers = TickerFuturesHelper.getAllKlineStartTime(Constants.INTERVAL_4H, startTime);
        Long time = startTime;
        Map<Long, Map<String, KlineObjectNumber>> time2Klines = new HashMap<>();
        for (Map.Entry<String, List<KlineObjectNumber>> entry : allSymbolTickers.entrySet()) {
            String sym = entry.getKey();
            List<KlineObjectNumber> tickers = entry.getValue();
            for (KlineObjectNumber ticker : tickers) {
                Map<String, KlineObjectNumber> symbol2Kline = time2Klines.get(ticker.startTime.longValue());
                if (symbol2Kline == null) {
                    symbol2Kline = new HashMap();
                    time2Klines.put(ticker.startTime.longValue(), symbol2Kline);
                }
                symbol2Kline.put(sym, ticker);
            }
        }
        while (true) {
            Double maxBread = 0d;
            Double volumeMin = null;
            String symbolMax = "";
            OrderSide sideMax = null;
            Map<String, KlineObjectNumber> klines = time2Klines.get(time);
            if (klines == null) {
                break;
            }
            List<String> lineFalses = new ArrayList<>();
            for (Map.Entry<String, KlineObjectNumber> entry : klines.entrySet()) {
                String sym = entry.getKey();
                KlineObjectNumber kline = entry.getValue();
                BreadDetectObject breadData = BreadFunctions.calBreadDataAlt(kline, 0.012);
                breadData.symbol = sym;
                if (breadData.orderSide != null && breadData.rateChange > 0.09) {
                    lineFalses.add(sym + "," + breadData.orderSide + "," + breadData.breadAbove + "," + breadData.breadBelow + "," + breadData.rateChange + "," + breadData.totalRate + "," + breadData.volume);
//---------------------------------- bread                    
                    if (maxBread < breadData.breadAbove) {
                        maxBread = breadData.breadAbove;
                        symbolMax = sym;
                        sideMax = breadData.orderSide;
                    }
                    if (maxBread < breadData.breadBelow) {
                        maxBread = breadData.breadBelow;
                        symbolMax = sym;
                        sideMax = breadData.orderSide;
                    }
//-------------------------------- rate change
//                    if (maxBread < breadData.rateChange) {
//                        maxBread = breadData.rateChange;
//                        symbolMax = sym;
//                        sideMax = breadData.orderSide;
//                    }
//--------------------------------- total rate

//                    if (maxBread < breadData.totalRate) {
//                        maxBread = breadData.totalRate;
//                        symbolMax = sym;
//                        sideMax = breadData.orderSide;
//                    }
//--------------------------------- volume min
//                    if (volumeMin == null || volumeMin < breadData.volume) {
//                        volumeMin = breadData.volume;
//                        symbolMax = sym;
//                        sideMax = breadData.orderSide;
//                    }
//--------------------------------- volume max
//                    if (volumeMin == null || volumeMin > breadData.volume) {
//                        volumeMin = breadData.volume;
//                        symbolMax = sym;
//                        sideMax = breadData.orderSide;
//                    }
                }
            }
            if (sideMax != null) {
                List<KlineObjectNumber> tickers = allSymbolTickers.get(symbolMax);
                for (int i = 0; i < tickers.size(); i++) {
                    KlineObjectNumber kline = tickers.get(i);
                    if (kline.startTime.longValue() == time) {
                        KlineObjectNumber klineHistory = TickerFuturesHelper.extractKline(tickers, 1000, i - 1000);
                        if (kline.maxPrice < klineHistory.maxPrice && kline.minPrice > klineHistory.minPrice) {

                            Double priceEntry = kline.priceClose;
                            Double priceTP = Utils.calPriceTarget(symbolMax, priceEntry, sideMax, 0.015);
                            OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry, priceTP, 1.0, 10, symbolMax, kline.startTime.longValue(), kline.startTime.longValue(), sideMax);
                            counterTotal++;
                            for (int j = i + 1; j < i + NUMBER_TICKER_TO_TRADE; j++) {
                                if (j < tickers.size()) {
                                    KlineObjectNumber ticker = tickers.get(j);
                                    if (ticker.maxPrice > order.priceTP && ticker.minPrice < order.priceTP) {
                                        order.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                                        break;
                                    }
                                }
                            }
                            if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                                counterSuccess++;
                                lines.add(buildLineTest(order, true, null));
                            } else {
                                if (order.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                                    counterStoploss++;
                                } else {
                                    lines.add(buildLineTest(order, false, null));
                                    try {
                                        FileUtils.writeLines(new File("target/data-false/" + Utils.normalizeDateYYYYMMDDHHmm(time) + ".csv"), lineFalses);
                                    } catch (IOException ex) {
                                        java.util.logging.Logger.getLogger(BigChange15M2Mongo.class.getName()).log(Level.SEVERE, null, ex);
                                    }
                                }

                            }
                        }
                    }
                }
            }
            time += 15 * Utils.TIME_MINUTE;
            if (time > System.currentTimeMillis()) {
                break;
            }
        }
        double rate = 0.0;
        if (counterTotal != 0) {
            rate = counterSuccess * 100 / counterTotal;
        }
        LOG.info("result {}/{} {}%", counterSuccess, counterTotal, rate);
        try {
            FileUtils.writeLines(new File("target/data/tradeByBreadMax.csv"), lines);
        } catch (IOException ex) {
            java.util.logging.Logger.getLogger(BigChange15M2Mongo.class.getName()).log(Level.SEVERE, null, ex);
        }
    }

    private void startDetectWithTargetIntervalOneWeek() throws ParseException {
//        Long startTime = 1620147600000L;
        Long startTime = Utils.getStartTimeDayAgo(7);
        LOG.info("Start detect with time start: {}- {}", startTime, new Date(startTime));
        long numberDay = (System.currentTimeMillis() - startTime) / Utils.TIME_DAY;
        Map<String, List<KlineObjectNumber>> allSymbolTickers = TickerFuturesHelper.getAllKlineStartTime(Constants.INTERVAL_1W, startTime);

        // test for multi param
        try {
            ArrayList<Double> rateBreads = new ArrayList<>(Arrays.asList(0.09
                    //                    0.1,
                    //                    0.12,
                    //                    0.14,
                    //                    0.16,
                    //                    0.18,
                    //                    0.2,
                    //                    0.3,
                    //                    0.4,
                    //                    0.5,
                    //                    0.6
            ));
//            ArrayList<Double> rateTargets = new ArrayList<>(Arrays.asList(
//                    0.009,
//                    0.01,
//                    0.011,
//                    0.013,
//                    0.014,
//                    0.015,
//                    0.02,
//                    0.025,
//                    0.03,
//                    0.035
//
//            ));

//            ArrayList<Double> listRateChanges = new ArrayList<>(Arrays.asList(
//                    0.05,
//                    0.06,
//                    0.07,
//                    0.08,
//                    0.09,
//                    0.10,
//                    0.12,
//                    0.14,
//                    0.16,
//                    0.18,
//                    0.2,
//                    0.25,
//                    0.30,
//                    0.40,
//                    0.50
//            //                    0.11,
//            //                    0.12,
//            //                    0.13
//            ));
            List<String> lines = new ArrayList<>();

            for (Double rateBread : rateBreads) {
//                for (Double rateChange : listRateChanges) {
                Double rateTarget = 0.03;
                lines.addAll(detectBigChangeWithParamWeek(rateBread, rateTarget, allSymbolTickers, numberDay));
//                }
            }
            FileUtils.writeLines(new File("target/data/failTradeWithBreadIntervalWeekr.csv"), lines);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void startTraceBreadAlt() throws ParseException {
//        Long startTime = Utils.sdfFileHour.parse("20240124 09:15").getTime();
//        Long startTime = 1702573200000L;
        Long startTime = 1695574800000L;
        Map<String, List<KlineObjectNumber>> allSymbolTickers = TickerFuturesHelper.getAllKlineStartTime(Constants.INTERVAL_15M, startTime);
        List<String> lines = new ArrayList<>();
        List<String> lineAlls = new ArrayList<>();
        double rateBreadMin = 0.008;
        double rateChangeMin = 0.02;
        for (Map.Entry<String, List<KlineObjectNumber>> entry : allSymbolTickers.entrySet()) {
            lines.clear();
            String symbol = entry.getKey();
            if (Constants.specialSymbol.contains(symbol)) {
                continue;
            }

            try {
                List<OrderTargetInfoTest> orders = new ArrayList<>();
                List<KlineObjectNumber> tickers = entry.getValue();
                for (int i = 0; i < tickers.size(); i++) {
                    KlineObjectNumber kline = tickers.get(i);
                    int lastIndex = i - 1;
                    if (lastIndex < 0) {
                        lastIndex = 0;
                    }
                    KlineObjectNumber lastKline = tickers.get(lastIndex);
                    BreadDetectObject breadData = BreadFunctions.calBreadDataAlt(kline, rateBreadMin);
                    if (breadData.orderSide != null && breadData.rateChange > rateChangeMin) {
                        try {
                            Double priceEntry = kline.priceClose;
                            OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry,
                                    0.0, 1.0, 10, symbol, kline.startTime.longValue(), kline.startTime.longValue(), breadData.orderSide);
                            KlineObjectNumber klineData = TickerFuturesHelper.extractKline(tickers, NUMBER_TICKER_TO_TRADE, i + 1);
                            orderTrade.maxPrice = klineData.maxPrice;
                            orderTrade.minPrice = klineData.minPrice;
                            orderTrade.rateBreadAbove = breadData.breadAbove;
                            orderTrade.rateBreadBelow = breadData.breadBelow;
                            orderTrade.rateChange = breadData.rateChange;
                            orderTrade.avgVolume24h = TickerFuturesHelper.getAvgLastVolume24h(tickers, i);
                            orderTrade.volume = kline.totalUsdt;

                            orders.add(orderTrade);
                        } catch (Exception e) {
                            LOG.info("Error: {}", Utils.toJson(kline));
                            e.printStackTrace();
                        }
                    }

                }
                if (!orders.isEmpty()) {
                    for (OrderTargetInfoTest order : orders) {
                        Double rateSide = Utils.rateOf2Double(order.maxPrice, order.priceEntry);
                        Double rateVolume = Utils.rateOf2Double(order.volume, order.avgVolume24h);
                        Double rateBread = order.rateBreadBelow;
                        if (order.side.equals(OrderSide.SELL)) {
                            rateBread = order.rateBreadAbove;
                            rateSide = -Utils.rateOf2Double(order.minPrice, order.priceEntry);
                        }
                        String line = order.symbol + "," + order.rateChange + "," + rateBread + "," + Utils.sdfFileHour.format(new Date(order.timeStart)) + "," + order.side + "," + order.priceEntry + "," + order.maxPrice + "," + order.minPrice + "," + order.avgVolume24h + "," + rateVolume + "," + order.volume + "," + rateSide;
                        lines.add(line);
                        lineAlls.add(line);
                    }
                } else {
                    LOG.info("Symbol not map: {} {}", symbol, tickers.size());
                }
                FileUtils.writeLines(new File("data-alt/" + symbol + "-bread.csv"), lines);
            } catch (Exception e) {
                e.printStackTrace();
            }
            try {
                FileUtils.writeLines(new File("data-alt/" + "ALL" + "-bread.csv"), lineAlls);
            } catch (IOException ex) {
                java.util.logging.Logger.getLogger(BigChange15M2Mongo.class.getName()).log(Level.SEVERE, null, ex);
            }
        }

    }

    private void startDetectBreadAltWithConstant() {
//        Long startTime = 1679158800000L;
//        Long startTime = 1695574800000L;
        Long startTime = Utils.getStartTimeDayAgo(5);
        long numberDay = (System.currentTimeMillis() - startTime) / Utils.TIME_DAY;
        Map<String, List<KlineObjectNumber>> allSymbolTickers = TickerFuturesHelper.getAllKlineStartTime(Constants.INTERVAL_15M, startTime);

        // test for multi param
        try {

            counterSuccess = 0;
            counterTotal = 0;

            List<String> lines = new ArrayList<>();
            for (Map.Entry<String, List<KlineObjectNumber>> entry : allSymbolTickers.entrySet()) {
                String symbol = entry.getKey();
                lastTimeBreadTrader = 0l;
                if (Constants.specialSymbol.contains(symbol)) {
                    continue;
                }
//                if (!StringUtils.equals(symbol, "RIFUSDT")) {
//                    continue;
//                }
                try {
                    List<OrderTargetInfo> orders = new ArrayList<>();
                    List<KlineObjectNumber> tickers = entry.getValue();
                    symbol2LastPrice.put(symbol, tickers.get(tickers.size() - 1).priceClose);
                    for (int i = 0; i < tickers.size(); i++) {
                        KlineObjectNumber kline = tickers.get(i);

//                        if (kline.startTime.longValue() > lastTimeBreadTrader + NUMBER_TICKER_TO_TRADE * EVENT_TIME) {
//                            if (kline.startTime > Utils.getStartTimeDayAgo(0)) {
//                                System.out.println("Debug:" + new Date(kline.startTime.longValue()));                                
//                            }
                        BreadDetectObject breadData = BreadFunctions.calBreadDataAlt(kline, ALT_BREAD_BIGCHANGE_15M);
                        if (breadData.orderSide != null && breadData.rateChange > RATE_BREAD_MIN_2TRADE) {
//                                            && breadData.totalRate >= TOTAL_RATE_CHANGE_WITHBREAD_2TRADING) {
                            lastTimeBreadTrader = kline.startTime.longValue();
                            lastBreadTrader = breadData;
                            try {
                                Double priceEntry = kline.priceClose;
                                Double priceTarget = getPriceTarget(priceEntry, breadData.orderSide, RATE_CHANGE_WITHBREAD_2TRADING_TARGET);
//                                    Double priceTarget = getPriceTarget(priceEntry, breadData.orderSide, breadData.rateChange * 0.5);
                                OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, priceEntry, priceTarget, 1.0, 10, symbol, kline.startTime.longValue(), kline.startTime.longValue(), breadData.orderSide, Constants.TRADING_TYPE_BREAD);
                                for (int j = i + 1; j < i + NUMBER_TICKER_TO_TRADE; j++) {
                                    if (j < tickers.size()) {
                                        KlineObjectNumber ticker = tickers.get(j);
                                        if (ticker.maxPrice > orderTrade.priceTP && ticker.minPrice < orderTrade.priceTP) {
                                            orderTrade.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                                            break;
                                        }
                                    }
                                }
                                if (!orderTrade.status.equals(OrderTargetStatus.REQUEST)) {
                                    orderTrade.status = OrderTargetStatus.POSITION_RUNNING;
                                }
                                orders.add(orderTrade);
                            } catch (Exception e) {
                                LOG.info("Error: {}", Utils.toJson(kline));
                                e.printStackTrace();
                            }
                        }

                    }
                    if (!orders.isEmpty()) {
                        lines.addAll(printResultTrade(orders));
                    } else {
                        LOG.info("Symbol not map: {} {}", symbol, tickers.size());
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
            FileUtils.writeLines(new File("target/data/failTradeWithBread.csv"), lines);
            LOG.info("Result All: rateBread:{} rateChange:{} rateTarget:{} numberOrderofDay {} {}/{} {}%", ALT_BREAD_BIGCHANGE_15M, RATE_BREAD_MIN_2TRADE, RATE_CHANGE_WITHBREAD_2TRADING_TARGET, counterTotal / numberDay, counterSuccess, counterTotal, counterSuccess * 100 / counterTotal);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private Double getPriceTarget(Double priceEntry, OrderSide orderSide, Double rateTarget) {
        double priceChange2Target = rateTarget * priceEntry;
        if (orderSide.equals(OrderSide.BUY)) {
            return priceEntry + priceChange2Target;
        } else {
            return priceEntry - priceChange2Target;
        }
    }

    private Double getPriceSL(Double priceEntry, OrderSide orderSide, Double rateTarget) {
        double priceChange2Target = rateTarget * priceEntry;
        if (orderSide.equals(OrderSide.BUY)) {
            return priceEntry - priceChange2Target;
        } else {
            return priceEntry + priceChange2Target;
        }
    }

    private List<String> printResultTrade(List<OrderTargetInfo> orders) {
        List<String> lines = new ArrayList<>();
        int counterSuccess = 0;

//        String symbol = orders.get(0).symbol;
        for (OrderTargetInfo order : orders) {
            counterTotal++;
            if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                this.counterSuccess++;
                counterSuccess++;
                lines.add(buildLine(order, true));
            } else {
                lines.add(buildLine(order, false));
            }
        }
//        LOG.info("Trade result: {} -> total:{} success:{} ratesuccess:{}% ", symbol, orders.size(), counterSuccess, counterSuccess * 100 / orders.size());
        return lines;
    }

    private List<String> printResultTradeTest(List<OrderTargetInfoTest> orders) {
        List<String> lines = new ArrayList<>();
        for (OrderTargetInfoTest order : orders) {
            counterTotal++;
            if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                counterSuccess++;
                lines.add(buildLineTest(order, true, null));
            } else {
                if (order.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                    counterStoploss++;
                } else {
                    double rateLoss = Utils.rateOf2Double(order.lastPrice, order.priceEntry);
                    if (order.side.equals(OrderSide.BUY)) {
                        rateLoss = -rateLoss;
                    }
                    totalLoss += rateLoss;
                    lines.add(buildLineTest(order, false, rateLoss));
                }

            }
//            }
        }
        return lines;
    }

    private String buildLine(OrderTargetInfo order, boolean orderState) {
        return order.symbol + "," + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart) + "," + order.side
                + "," + order.priceEntry + "," + order.priceTP + "," + symbol2LastPrice.get(order.symbol) + "," + orderState;
    }

    private String buildLineTest(OrderTargetInfoTest order, boolean orderState, Double rateloss) {
        Map<String, MAStatus> symbol2Status = time2MaInfos.get(Utils.getDate(order.timeStart));

        MAStatus btcStatus = null;
        MAStatus maStatus = null;
        if (symbol2Status != null) {
            maStatus = symbol2Status.get(order.symbol);
            btcStatus = symbol2Status.get(Constants.SYMBOL_PAIR_BTC);
        }
        return order.symbol + "," + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart) + "," + order.side + ","
                + order.priceEntry + "," + order.priceTP + "," + symbol2LastPrice.get(order.symbol) + ","
                + order.volume + "," + order.avgVolume24h + "," + order.rateChange + "," + orderState + ","
                + rateloss + "," + order.maxPrice + "," + Utils.rateOf2Double(order.maxPrice, order.priceEntry)
                + "," + (order.timeUpdate - order.timeStart) / Utils.TIME_MINUTE + "," + maStatus + "," + btcStatus;
    }

    private Set<Double> extractBtcBigChange(List<KlineObjectNumber> btcKlines) {
        Set<Double> results = new HashSet<>();

        for (KlineObjectNumber kline : btcKlines) {
            BreadDetectObject breadData = BreadFunctions.calBreadDataBtc(kline, 0.006);
            if (breadData.orderSide != null && breadData.rateChange > 0.015) {
                results.add(kline.startTime);
                LOG.info("{} {} bread above:{} bread below:{} rateChange:{} totalRate: {}",
                        new Date(kline.startTime.longValue()), breadData.orderSide, breadData.breadAbove,
                        breadData.breadBelow, breadData.rateChange, breadData.totalRate);
            }
        }
        return results;
    }

    private List<String> detectBigChangeWithParam(Double rateTarget, Double rateChange, Double volume,
                                                  Map<String, List<KlineObjectNumber>> allSymbolTickers,
                                                  long numberDay, Set<Double> btcBigChangeTimes) {
        //                    for (Integer volume : volumes) {
        counterTotal = 0;
        counterSuccess = 0;
        counterStoploss = 0;


        List<String> lines = new ArrayList<>();
// end test multi param
        Map<String, Integer> date2Counter = new HashMap<>();
        for (Map.Entry<String, List<KlineObjectNumber>> entry : allSymbolTickers.entrySet()) {
            String symbol = entry.getKey();
            lastTimeBreadTrader = 0l;
            if (Constants.specialSymbol.contains(symbol)) {
                continue;
            }
//                if (!StringUtils.equals(symbol, "RIFUSDT")) {
//                    continue;
//                }
            try {
                List<OrderTargetInfoTest> orders = new ArrayList<>();
                List<KlineObjectNumber> tickers = entry.getValue();
                symbol2LastPrice.put(symbol, tickers.get(tickers.size() - 1).priceClose);
                for (int i = 0; i < tickers.size(); i++) {
                    KlineObjectNumber kline = tickers.get(i);
                    int lastIndex = i - 1;
                    if (lastIndex < 0) {
                        lastIndex = 0;
                    }
                    boolean btcBigchange = false;
                    if (btcBigChangeTimes.contains(kline.startTime)) {
                        btcBigchange = true;
                    }
//                                    if (kline.totalUsdt > volume * 1000000) {
//                                        continue;
//                                    }
//                            if (kline.startTime > Utils.getStartTimeDayAgo(0)) {
//                                System.out.println("Debug:" + new Date(kline.startTime.longValue()));
//                            }
                    BreadDetectObject breadData = BreadFunctions.calBreadDataAltWithBtcTrend(tickers, i, RATE_BREAD_MIN_2TRADE);
                    if (breadData.orderSide != null && breadData.orderSide.equals(OrderSide.BUY) && PriceManager.getInstance().isAvalible2Trade(symbol, kline.minPrice, breadData.orderSide) && breadData.totalRate >= rateChange
//                            && breadData.rateChange >= rateChange
                            && kline.totalUsdt <= volume * 1000000) {

//                                            && breadData.totalRate >= TOTAL_RATE_CHANGE_WITHBREAD_2TRADING) {
                        lastTimeBreadTrader = kline.startTime.longValue();
                        lastBreadTrader = breadData;
                        try {
                            Double priceEntry = kline.priceClose;
                            Double priceTarget = getPriceTarget(priceEntry, breadData.orderSide, rateTarget);
                            Double priceSTL = getPriceSL(priceEntry, breadData.orderSide, ALT_BREAD_BIGCHANE_STOPPLOSS);
                            OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry,
                                    priceTarget, 1.0, 10, symbol, kline.startTime.longValue(), kline.startTime.longValue(), breadData.orderSide);
                            orderTrade.priceSL = priceSTL;
                            String date = Utils.sdfFile.format(new Date(kline.startTime.longValue()));
                            orderTrade.maxPrice = kline.maxPrice;
                            orderTrade.minPrice = kline.minPrice;
                            orderTrade.rateBreadAbove = breadData.breadAbove;
                            orderTrade.rateBreadBelow = breadData.breadBelow;
                            orderTrade.rateChange = breadData.rateChange;
                            orderTrade.avgVolume24h = TickerFuturesHelper.getAvgLastVolume7D(tickers, i);
//                            if (TickerHelper.getSideOfTicer(lastKline).equals(breadData.orderSide)) {
//                                orderTrade.avgVolume24h = 0.0;
//                            } else {
//                                orderTrade.avgVolume24h = 1.0;
//                            }
                            orderTrade.volume = kline.totalUsdt;

                            Integer counter = date2Counter.get(date);
                            if (counter == null) {
                                counter = 0;
                            }
                            counter++;
                            date2Counter.put(date, counter);
                            for (int j = i + 1; j < i + NUMBER_TICKER_TO_TRADE; j++) {
                                if (j < tickers.size()) {
                                    KlineObjectNumber ticker = tickers.get(j);
//                                    if (ticker.maxPrice > orderTrade.priceSL && ticker.minPrice < orderTrade.priceSL) {
//                                        orderTrade.status = OrderTargetStatus.STOP_LOSS_DONE;
//                                        break;
//                                    }
                                    if (ticker.maxPrice > orderTrade.priceTP && ticker.minPrice < orderTrade.priceTP) {
                                        orderTrade.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                                        break;
                                    }
                                }
                            }
                            if (orderTrade.status.equals(OrderTargetStatus.REQUEST)) {
                                orderTrade.status = OrderTargetStatus.POSITION_RUNNING;
                            }
                            orders.add(orderTrade);
                        } catch (Exception e) {
                            LOG.info("Error: {}", Utils.toJson(kline));
                            e.printStackTrace();
                        }
                    }

                }
                if (!orders.isEmpty()) {
                    lines.addAll(printResultTradeTest(orders));
                } else {
//                                    LOG.info("Symbol not map: {} {}", symbol, tickers.size());
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        Integer rateSuccess = 0;
        Integer rateSuccessLoss = 0;

        if (counterTotal != 0) {
            rateSuccess = counterSuccess * 100 / counterTotal;
        }

        if (counterSuccess != 0) {
            rateSuccessLoss = counterStoploss * 100 / counterSuccess;
        }
        LOG.info("Result All: rateTarget:{} rateChange:{} volume:{} numberOrderofDay {} {}-{}-{}%-{}/{} {}% {}",
                rateTarget, rateChange, volume, counterTotal / numberDay, counterSuccess, counterStoploss, rateSuccessLoss,
                counterSuccess + counterStoploss, counterTotal, rateSuccess, Utils.toJson(date2Counter));
        return lines;
    }

    List<String> detectBigChangeWithParamNew(Double rateTarget, Double rateChange,
                                             Map<String, List<KlineObjectNumber>> allSymbolTickers, Double volume) {
        counterTotal = 0;
        counterSuccess = 0;
        counterStoploss = 0;
        List<String> lines = new ArrayList<>();
        for (String symbol : allSymbolTickers.keySet()) {
            if (Constants.specialSymbol.contains(symbol)) {
                continue;
            }
            try {
                List<OrderTargetInfoTest> orders = new ArrayList<>();
                List<KlineObjectNumber> tickers = allSymbolTickers.get(symbol);
                symbol2LastPrice.put(symbol, tickers.get(tickers.size() - 1).priceClose);
                for (int i = 0; i < tickers.size(); i++) {
                    KlineObjectNumber kline = tickers.get(i);
                    Map<String, MAStatus> symbol2MaInfo = time2MaInfos.get(Utils.getDate(kline.startTime.longValue()));
                    MAStatus maStatus = null;
                    if (symbol2MaInfo != null) {
                        maStatus = symbol2MaInfo.get(symbol);
                    }

                    BreadDetectObject breadData = BreadFunctions.calBreadDataAltWithBtcTrend(tickers, i, RATE_BREAD_MIN_2TRADE);
                    if (breadData.orderSide != null && breadData.orderSide.equals(OrderSide.BUY)
                            && breadData.totalRate >= rateChange
                            // ma20
                            && maStatus != null && maStatus.equals(MAStatus.TOP)

                            && kline.totalUsdt <= volume * 1000000) {
                        lastBreadTrader = breadData;
                        try {
                            Double priceEntry = kline.priceClose;
                            Double priceTarget = getPriceTarget(priceEntry, breadData.orderSide, rateTarget);
                            Double priceSTL = getPriceSL(priceEntry, breadData.orderSide, ALT_BREAD_BIGCHANE_STOPPLOSS);
                            OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry, priceTarget,
                                    1.0, 10, symbol, kline.startTime.longValue(), kline.startTime.longValue(), breadData.orderSide);
                            orderTrade.priceSL = priceSTL;
                            String date = Utils.sdfFile.format(new Date(kline.startTime.longValue()));
                            orderTrade.maxPrice = kline.maxPrice;
                            orderTrade.minPrice = kline.minPrice;
                            orderTrade.rateBreadAbove = breadData.breadAbove;
                            orderTrade.rateBreadBelow = breadData.breadBelow;
                            orderTrade.rateChange = breadData.totalRate;
                            orderTrade.avgVolume24h = TickerFuturesHelper.getAvgLastVolume7D(tickers, i);
                            orderTrade.volume = kline.totalUsdt;

//                            Integer counter = date2Counter.get(date);
//                            if (counter == null) {
//                                counter = 0;
//                            }
//                            counter++;
//                            date2Counter.put(date, counter);
                            int startCheck = i;
                            for (int j = startCheck + 1; j < startCheck + NUMBER_TICKER_TO_TRADE; j++) {
                                if (j < tickers.size()) {
                                    i = j;
                                    KlineObjectNumber ticker = tickers.get(j);
                                    if (ticker.maxPrice > orderTrade.priceTP && ticker.minPrice < orderTrade.priceTP) {
                                        orderTrade.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                                        break;
                                    }
                                }
                            }
                            if (orderTrade.status.equals(OrderTargetStatus.REQUEST)) {
                                orderTrade.status = OrderTargetStatus.POSITION_RUNNING;
                            }
                            orders.add(orderTrade);
                        } catch (Exception e) {
                            LOG.info("Error: {}", Utils.toJson(kline));
                            e.printStackTrace();
                        }
                    }

                }
                if (!orders.isEmpty()) {
                    lines.addAll(printResultTradeTest(orders));
                } else {
//                                    LOG.info("Symbol not map: {} {}", symbol, tickers.size());
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        Integer rateSuccess = 0;
        Integer rateSuccessLoss = 0;

        if (counterTotal != 0) {
            rateSuccess = counterSuccess * 1000 / counterTotal;
        }

        if (counterSuccess != 0) {
            rateSuccessLoss = counterStoploss * 1000 / counterSuccess;
        }
        LOG.info("Result All: rateTarget:{} rateChange:{} volume:{}  {}-{}-{}%-{}/{} {}% ", rateTarget, rateChange, volume, counterSuccess, counterStoploss, rateSuccessLoss.doubleValue() / 10, counterSuccess + counterStoploss, counterTotal, rateSuccess.doubleValue() / 10);
        return lines;
    }

    List<String> detectBigChangeWithVolumeFixRate(Double rateTarget, Map<String, List<KlineObjectNumber>> allSymbolTickers,
                                                  Integer NUMBER_TICKER_TO_TRADE) {
//        LOG.info("Number ticker check: {} {} minutes", NUMBER_TICKER_TO_TRADE, NUMBER_TICKER_TO_TRADE * 15);
        counterTotal = 0;
        counterSuccess = 0;
        counterStoploss = 0;
        totalLoss = 0d;
        List<String> lines = new ArrayList<>();

        for (String symbol : allSymbolTickers.keySet()) {
            if (Constants.specialSymbol.contains(symbol)) {
                continue;
            }
            try {
                List<OrderTargetInfoTest> orders = new ArrayList<>();
                List<KlineObjectNumber> tickers = allSymbolTickers.get(symbol);
                symbol2LastPrice.put(symbol, tickers.get(tickers.size() - 1).priceClose);
                for (int i = 0; i < tickers.size(); i++) {
                    KlineObjectNumber kline = tickers.get(i);
                    BreadDetectObject breadData = BreadFunctions.calBreadDataAltWithBtcTrend(tickers, i, RATE_BREAD_MIN_2TRADE);
                    Double rateChange = BreadFunctions.getRateChangeWithVolume(kline.totalUsdt / 1E6);
                    if (rateChange == null) {
//                        LOG.info("Error rateChange with ticker: {} {}", symbol, Utils.toJson(kline));
                        continue;
                    } else {
//                        LOG.info("RateAndVolume {} -> {}", kline.totalUsdt, rateChange);
                    }
                    Map<String, MAStatus> symbol2MaInfo = time2MaInfos.get(Utils.getDate(kline.startTime.longValue()));
                    MAStatus maStatus = null;
                    MAStatus btcStatus = null;
                    if (symbol2MaInfo != null) {
                        maStatus = symbol2MaInfo.get(symbol);
                        btcStatus = symbol2MaInfo.get(Constants.SYMBOL_PAIR_BTC);
                    }
                    if (breadData.orderSide != null
                            && breadData.orderSide.equals(OrderSide.BUY)
                            // ma20
                            && maStatus != null && maStatus.equals(MAStatus.TOP)
                            && btcStatus != null && btcStatus.equals(MAStatus.TOP)

                            && breadData.totalRate >= rateChange) {
                        lastBreadTrader = breadData;
                        try {
                            Double priceEntry = kline.priceClose;
                            Double priceTarget = getPriceTarget(priceEntry, breadData.orderSide, rateTarget);
                            Double priceSTL = getPriceSL(priceEntry, breadData.orderSide, ALT_BREAD_BIGCHANE_STOPPLOSS);
                            OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry, priceTarget,
                                    1.0, 10, symbol, kline.startTime.longValue(), kline.startTime.longValue(),
                                    breadData.orderSide);
                            orderTrade.priceSL = priceSTL;
                            orderTrade.maxPrice = kline.priceClose;
                            orderTrade.minPrice = kline.minPrice;
                            orderTrade.rateBreadAbove = breadData.breadAbove;
                            orderTrade.rateBreadBelow = breadData.breadBelow;
                            orderTrade.rateChange = breadData.totalRate;
                            orderTrade.avgVolume24h = TickerFuturesHelper.getAvgLastVolume7D(tickers, i);
                            orderTrade.volume = kline.totalUsdt;
                            int startCheck = i;
                            for (int j = startCheck + 1; j < startCheck + NUMBER_TICKER_TO_TRADE; j++) {
                                if (j < tickers.size()) {
                                    i = j;
                                    KlineObjectNumber ticker = tickers.get(j);
                                    orderTrade.lastPrice = ticker.priceClose;
                                    if (orderTrade.maxPrice == null || ticker.maxPrice > orderTrade.maxPrice) {
                                        orderTrade.maxPrice = ticker.maxPrice;
                                        orderTrade.timeUpdate = ticker.endTime.longValue();
                                    }
                                    if (ticker.maxPrice > orderTrade.priceTP && ticker.minPrice < orderTrade.priceTP) {
                                        orderTrade.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                                        orderTrade.timeUpdate = ticker.endTime.longValue();
                                        break;
                                    }
                                }
                            }
                            if (orderTrade.status.equals(OrderTargetStatus.REQUEST)) {
                                orderTrade.status = OrderTargetStatus.POSITION_RUNNING;
                            }
                            orders.add(orderTrade);
                        } catch (Exception e) {
                            LOG.info("Error: {}", Utils.toJson(kline));
                            e.printStackTrace();
                        }
                    }

                }
                if (!orders.isEmpty()) {
                    lines.addAll(printResultTradeTest(orders));
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        Integer rateSuccess = 0;
        Integer rateSuccessLoss = 0;

        if (counterTotal != 0) {
            rateSuccess = counterSuccess * 1000 / counterTotal;
        }

        if (counterSuccess != 0) {
            rateSuccessLoss = counterStoploss * 1000 / counterSuccess;
        }
        Double pnl = counterSuccess * rateTarget;
        LOG.info("Result All:numberDay2Trade:{} hours rateTarget:{}  {}-{}-{}%-{}/{} {}% pl: {}/{} {}%", NUMBER_TICKER_TO_TRADE / 4, rateTarget,
                counterSuccess, counterStoploss, rateSuccessLoss.doubleValue() / 10, counterSuccess + counterStoploss,
                counterTotal, rateSuccess.doubleValue() / 10, totalLoss.longValue(), pnl.longValue(),
                Utils.formatPercent(totalLoss / pnl));
        return lines;
    }

    private List<String> detectBigChangeWithParamWeek(Double rateBread, Double rateTarget, Map<String, List<KlineObjectNumber>> allSymbolTickers, long numberDay) {
        //                    for (Integer volume : volumes) {
        counterTotal = 0;
        counterSuccess = 0;
        counterStoploss = 0;

        List<String> lines = new ArrayList<>();
// end test multi param
        Map<String, Integer> date2Counter = new HashMap<>();
        for (Map.Entry<String, List<KlineObjectNumber>> entry : allSymbolTickers.entrySet()) {
            String symbol = entry.getKey();
            lastTimeBreadTrader = 0l;
            if (Constants.specialSymbol.contains(symbol)) {
                continue;
            }
            try {
                List<OrderTargetInfoTest> orders = new ArrayList<>();
                List<KlineObjectNumber> tickers = entry.getValue();
                symbol2LastPrice.put(symbol, tickers.get(tickers.size() - 1).priceClose);
                for (int i = 0; i < tickers.size(); i++) {
                    KlineObjectNumber kline = tickers.get(i);
                    int lastIndex = i - 1;
                    if (lastIndex < 0) {
                        lastIndex = 0;
                    }

                    BreadDetectObject breadData = BreadFunctions.calBreadDataAltWithBtcTrend(tickers, i, rateBread);
                    if (breadData.orderSide != null) {
//                                            && breadData.totalRate >= TOTAL_RATE_CHANGE_WITHBREAD_2TRADING) {
                        lastTimeBreadTrader = kline.startTime.longValue();
                        lastBreadTrader = breadData;
                        try {
                            Double priceEntry = kline.priceClose;
                            Double priceTarget = getPriceTarget(priceEntry, breadData.orderSide, rateTarget);
                            Double priceSTL = getPriceSL(priceEntry, breadData.orderSide, ALT_BREAD_BIGCHANE_STOPPLOSS);
                            OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry, priceTarget,
                                    1.0, 10, symbol, kline.startTime.longValue(), kline.startTime.longValue(), breadData.orderSide);
                            orderTrade.priceSL = priceSTL;
                            String date = Utils.sdfFile.format(new Date(kline.startTime.longValue()));
                            orderTrade.maxPrice = kline.maxPrice;
                            orderTrade.minPrice = kline.minPrice;
                            orderTrade.rateBreadAbove = breadData.breadAbove;
                            orderTrade.rateBreadBelow = breadData.breadBelow;
                            orderTrade.rateChange = breadData.rateChange;
                            orderTrade.avgVolume24h = TickerFuturesHelper.getAvgLastVolume24h(tickers, i);
//                            if (TickerHelper.getSideOfTicer(lastKline).equals(breadData.orderSide)) {
//                                orderTrade.avgVolume24h = 0.0;
//                            } else {
//                                orderTrade.avgVolume24h = 1.0;
//                            }
                            orderTrade.volume = kline.totalUsdt;

                            Integer counter = date2Counter.get(date);
                            if (counter == null) {
                                counter = 0;
                            }
                            counter++;
                            date2Counter.put(date, counter);
                            for (int j = i + 1; j < i + NUMBER_TICKER_TO_TRADE; j++) {
                                if (j < tickers.size()) {
                                    KlineObjectNumber ticker = tickers.get(j);
//                                                    if (ticker.maxPrice > orderTrade.priceSL && ticker.minPrice < orderTrade.priceSL) {
//                                                        orderTrade.status = OrderTargetStatus.STOP_LOSS_DONE;
//                                                        break;
//                                                    }
                                    if (ticker.maxPrice > orderTrade.priceTP && ticker.minPrice < orderTrade.priceTP) {
                                        orderTrade.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                                        break;
                                    }
                                }
                            }
                            if (orderTrade.status.equals(OrderTargetStatus.REQUEST)) {
                                orderTrade.status = OrderTargetStatus.POSITION_RUNNING;
                            }
                            orders.add(orderTrade);
                        } catch (Exception e) {
                            LOG.info("Error: {}", Utils.toJson(kline));
                            e.printStackTrace();
                        }
                    }

                }
                if (!orders.isEmpty()) {
                    lines.addAll(printResultTradeTest(orders));
                } else {
//                                    LOG.info("Symbol not map: {} {}", symbol, tickers.size());
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        Integer rateSuccess = 0;

        if (counterTotal != 0) {
            rateSuccess = counterSuccess * 100 / counterTotal;
        }

        LOG.info("Result All: rateBread:{} rateTarget:{} numberOrderofDay {} {}/{} {}%", rateBread, rateTarget, counterTotal / numberDay, counterSuccess, counterTotal, rateSuccess);
        return lines;
    }

    private void printByDate(List<String> lines) {
        TreeMap<Long, Integer> date2orderFalse = new TreeMap<>();
        TreeMap<Long, Integer> date2OrderTotal = new TreeMap<>();
        for (String line : lines) {
            String[] parts = line.split(",");
            try {
                String date = parts[1];
                Long time = Utils.sdfFileHour.parse(date).getTime();
                if (StringUtils.equalsIgnoreCase(parts[parts.length - 2], "false")) {
                    Integer counter = date2orderFalse.get(time);
                    if (counter == null) {
                        counter = 0;
                    }
                    counter++;
                    date2orderFalse.put(time, counter);
                }
                Integer counter = date2OrderTotal.get(time);
                if (counter == null) {
                    counter = 0;
                }
                counter++;
                date2OrderTotal.put(time, counter);

            } catch (Exception e) {
            }
        }
        for (Map.Entry<Long, Integer> entry : date2OrderTotal.entrySet()) {
            Long time = entry.getKey();
            Integer value = entry.getValue();
            if ((date2orderFalse.get(time) != null && date2orderFalse.get(time) > 1) || value > 50) {
                LOG.info("{} -> {} total {} falses", Utils.normalizeDateYYYYMMDDHHmm(time), value, date2orderFalse.get(time));
            }
        }
    }

    public static void main(String[] args) throws ParseException {
        new BigChange15M2Mongo().startDetectBigChangeVolumeMiniInterval15MDataMongo();

    }

}
