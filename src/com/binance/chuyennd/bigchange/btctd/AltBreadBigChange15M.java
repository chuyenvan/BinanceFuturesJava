package com.binance.chuyennd.bigchange.btctd;

import com.educa.mail.funcs.BreadFunctions;
import com.binance.chuyennd.funcs.PriceManager;
import com.binance.chuyennd.funcs.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.trading.OrderTargetInfo;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.binance.chuyennd.trading.OrderTargetInfoTest;
import java.io.File;
import java.io.IOException;
import java.text.ParseException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.logging.Level;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class AltBreadBigChange15M {

    public static final Logger LOG = LoggerFactory.getLogger(AltBreadBigChange15M.class);

    public AtomicBoolean isTrading = new AtomicBoolean(false);
    public BreadDetectObject lastBreadTrader = null;
    public Long EVENT_TIME = Utils.TIME_MINUTE * 15;
    public Integer NUMBER_TICKER_TO_TRADE = 10 * 96;
    public Long lastTimeBreadTrader = 0l;
    public Double RATE_CHANGE_BREAD_MIN_2TRADE = 0.04;
    public Double RATE_TARGET = 0.02;
    public Double TOTAL_RATE_CHANGE_WITHBREAD_2TRADING = 0.01;
    public Double ALT_BREAD_BIGCHANE_15M = 0.008;
    public Double ALT_BREAD_BIGCHANE_STOPPLOSS = 0.1;
    public Double RATE_CHANGE_WITHBREAD_2TRADING_TARGET = 0.009;
    public Integer counterTotal = 0;
    public Integer counterSuccess = 0;
    public Integer counterStoploss = 0;
    public Integer counterTotalBtcBigchane = 0;
    public Integer counterSuccessBtcBigchane = 0;
    public Integer counterStoplossBtcBigchane = 0;
    public Map<String, Double> symbol2LastPrice = new HashMap<>();

    public void startThreadTradingAlt(OrderSide orderSide) {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadTradingAltBreadBtcBigChan");
            LOG.info("Start ThreadTradingAltBreadBtcBigChan !");
            try {
                Collection<? extends String> allSymbol = TickerFuturesHelper.getAllSymbol();
                for (String symbol : allSymbol) {
//                    boolean result = PositionHelper.getInstance().addOrderByTarget(symbol, orderSide);
//                    if (!result) {
//                        LOG.info("Break because balance not enough!");
//                        break;
//                    }
                }
                isTrading.set(false);
            } catch (Exception e) {
                LOG.error("ERROR during ThreadTradingAltBreadBtcBigChan: {}", e);
                e.printStackTrace();
            }

        }).start();
    }

    private void startDetectBreadAlt() throws ParseException {
        Long startTime = 1679158800000L;
//        Long startTime = 1695574800000L;
//        Long startTime = Utils.sdfFileHour.parse("20240124 09:15").getTime();
//        Long startTime = Utils.getStartTimeDayAgo(10);
        LOG.info("Start detect with time start: {}- {}", startTime, new Date(startTime));
        long numberDay = (System.currentTimeMillis() - startTime) / Utils.TIME_DAY;
        Map<String, List<KlineObjectNumber>> allSymbolTickers = TickerFuturesHelper.getAllKlineStartTime(Constants.INTERVAL_15M, startTime);
        List<KlineObjectNumber> btcKlines = allSymbolTickers.get(Constants.SYMBOL_PAIR_BTC);
        Set<Double> btcBigChangeTimes = extractBtcBigChange(btcKlines);

        // test for multi param
        try {
            ArrayList<Double> rateBreads = new ArrayList<>(Arrays.asList(
                    0.006,
                    0.007,
                    0.008,
                    0.01,
                    0.012,
                    0.014,
                    0.016,
                    0.02,
                    0.025,
                    0.03,
                    0.035,
                    0.04,
                    0.045,
                    0.05,
                    0.06
            ));
            ArrayList<Double> rateTargets = new ArrayList<>(Arrays.asList(
                    0.009,
                    0.01,
                    0.011,
                    0.013,
                    0.014,
                    0.015,
                    0.02,
                    0.025,
                    //                                        0.03
                    0.03,
                    0.035,
                    0.040,
                    0.045,
                    0.05,
                    0.055,
                    0.06,
                    0.065,
                    0.1
            ));

            ArrayList<Double> listRateChanges = new ArrayList<>(Arrays.asList(
                    0.02,
                    0.025,
                    0.03,
                    0.035,
                    //                                        0.04
                    0.04,
                    0.05,
                    0.06,
                    0.07,
                    0.08,
                    0.09,
                    0.10
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
        Long startTime = 1695574800000L;
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
            ArrayList<Double> rateBreads = new ArrayList<>(Arrays.asList(
                    0.001
            //                    0.008,
            //                    0.009,
            //                    0.01,
            //                    0.012
            //                    0.014,
            //                    0.016,
            //                    0.02,
            //                    0.025,
            //                    0.03,
            //                    0.035,
            //                    0.04,
            //                    0.045,
            //                    0.05,
            //                    0.06
            ));
            ArrayList<Double> rateTargets = new ArrayList<>(Arrays.asList(   
                    0.02
            ));
            ArrayList<Double> volumes = new ArrayList<>(Arrays.asList(
                    //                    0.2,
                    //                    0.3,
                    //                    0.4,
//                    0.7,
//                    0.8,
//                    0.9,
                    0.5
            //                    1.0,
            //                    2.0,
            //                    3.0,
            //                    4.0,
            //                    5.0,
            //                    10.0
            //                    0.008,
            //                    0.009,
            //                    0.01,
            //                    0.012
            //                    0.014,
            //                    0.016,
            //                    0.02,
            //                    0.025,
            //                    0.03,
            //                    0.035,
            //                    0.04,
            //                    0.045,
            //                    0.05,
            //                    0.06
            ));

            ArrayList<Double> listRateChanges = new ArrayList<>(Arrays.asList(
                    0.021
            ));
            List<String> lines = new ArrayList<>();

            for (Double volume : volumes) {
                for (Double rateChange : listRateChanges) {
                    for (Double rateTarget : rateTargets) {
                        lines.addAll(detectBigChangeWithParam(rateTarget, rateChange, volume, allSymbolTickers, numberDay, btcBigChangeTimes));
                    }

                }
            }
//            printbyDate(lines);
            FileUtils.writeLines(new File("target/data/failTradeWithVolume.csv"), lines);

        } catch (Exception e) {
            e.printStackTrace();
        }
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
            ArrayList<Double> rateBreads = new ArrayList<>(Arrays.asList(
                    0.01,
                    0.012,
                    0.014,
                    0.016,
                    0.018,
                    0.02,
                    0.022,
                    0.024,
                    0.026,
                    0.028,
                    0.03,
                    0.035,
                    0.04,
                    0.045,
                    0.05,
                    0.055,
                    0.06
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

            ArrayList<Double> listRateChanges = new ArrayList<>(Arrays.asList(
                    0.02,
                    0.025,
                    0.03,
                    0.035,
                    //                                        0.04
                    0.04,
                    0.05,
                    0.06,
                    0.07,
                    0.08,
                    0.09,
                    0.10,
                    0.12,
                    0.14,
                    0.16,
                    0.20
            //                    0.11,
            //                    0.12,
            //                    0.13
            ));
            List<String> lines = new ArrayList<>();

            for (Double rateBread : rateBreads) {
                for (Double rateChange : listRateChanges) {
                    Double rateTarget = 0.01;
                    lines.addAll(detectBigChangeWithParam(rateBread, rateChange, rateTarget, allSymbolTickers, numberDay, btcBigChangeTimes));

                }
            }

            printbyDate(lines);

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
            ArrayList<Double> rateTargets = new ArrayList<>(Arrays.asList(
                    0.03,
                    0.04,
                    0.05,
                    0.06,
                    0.07,
                    0.08,
                    0.09,
                    0.1
            ));

            ArrayList<Double> listRateChanges = new ArrayList<>(Arrays.asList(
                    0.08,
                    0.09,
                    0.10,
                    0.11,
                    0.12,
                    0.13,
                    0.14,
                    0.15,
                    0.16,
                    0.17,
                    0.18,
                    0.19,
                    0.20,
                    0.21
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
                    lineFalses.add(sym + "," + breadData.orderSide + "," + breadData.breadAbove + "," + breadData.breadBelow
                            + "," + breadData.rateChange + "," + breadData.totalRate + "," + breadData.volume);
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
                            OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry,
                                    priceTP, 1.0, 10, symbolMax, kline.startTime.longValue(),
                                    kline.startTime.longValue(), sideMax, Constants.TRADING_TYPE_BREAD, false);
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
                                        java.util.logging.Logger.getLogger(AltBreadBigChange15M.class.getName()).log(Level.SEVERE, null, ex);
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
            java.util.logging.Logger.getLogger(AltBreadBigChange15M.class.getName()).log(Level.SEVERE, null, ex);
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
            ArrayList<Double> rateBreads = new ArrayList<>(Arrays.asList(
                    0.09
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
                                    0.0, 1.0, 10, symbol, kline.startTime.longValue(),
                                    kline.startTime.longValue(), breadData.orderSide, Constants.TRADING_TYPE_BREAD, false);
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
                        String line = order.symbol + "," + order.rateChange + "," + rateBread + "," + Utils.sdfFileHour.format(new Date(order.timeStart)) + "," + order.side + "," + order.priceEntry
                                + "," + order.maxPrice + "," + order.minPrice + "," + order.avgVolume24h + "," + rateVolume + "," + order.volume + "," + rateSide;
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
                java.util.logging.Logger.getLogger(AltBreadBigChange15M.class.getName()).log(Level.SEVERE, null, ex);
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
                        BreadDetectObject breadData = BreadFunctions.calBreadDataAlt(kline, ALT_BREAD_BIGCHANE_15M);
                        if (breadData.orderSide != null
                                && breadData.rateChange > RATE_CHANGE_BREAD_MIN_2TRADE) {
//                                            && breadData.totalRate >= TOTAL_RATE_CHANGE_WITHBREAD_2TRADING) {
                            lastTimeBreadTrader = kline.startTime.longValue();
                            lastBreadTrader = breadData;
                            try {
                                Double priceEntry = kline.priceClose;
                                Double priceTarget = getPriceTarget(priceEntry, breadData.orderSide, RATE_CHANGE_WITHBREAD_2TRADING_TARGET);
//                                    Double priceTarget = getPriceTarget(priceEntry, breadData.orderSide, breadData.rateChange * 0.5);
                                OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, priceEntry,
                                        priceTarget, 1.0, 10, symbol, kline.startTime.longValue(), kline.startTime.longValue(), breadData.orderSide, Constants.TRADING_TYPE_BREAD);
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
            LOG.info("Result All: rateBread:{} rateChange:{} rateTarget:{} numberOrderofDay {} {}/{} {}%", ALT_BREAD_BIGCHANE_15M, RATE_CHANGE_BREAD_MIN_2TRADE,
                    RATE_CHANGE_WITHBREAD_2TRADING_TARGET, counterTotal / numberDay, counterSuccess, counterTotal, counterSuccess * 100 / counterTotal);

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

//        String symbol = orders.get(0).symbol;
        for (OrderTargetInfoTest order : orders) {
            if (order.btcBigchange) {
//                counterTotalBtcBigchane++;
//                if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
//                    counterSuccessBtcBigchane++;
//                    lines.add(buildLineTest(order, true));
//                } else {
//                    if (order.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
//                        counterStoplossBtcBigchane++;
//                    } else {
//                        lines.add(buildLineTest(order, false));
//                    }
//                }
            } else {
                counterTotal++;
                if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                    counterSuccess++;
                    lines.add(buildLineTest(order, true, null));
                } else {
                    if (order.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                        counterStoploss++;
                    } else {
                        double rateLoss = Utils.rateOf2Double(symbol2LastPrice.get(order.symbol), order.priceEntry);
                        if (order.side.equals(OrderSide.BUY)) {
                            rateLoss = -rateLoss;
                        }
                        if ((symbol2LastPrice.get(order.symbol) >= order.priceTP && order.side.equals(OrderSide.BUY))
                                || (symbol2LastPrice.get(order.symbol) <= order.priceTP && order.side.equals(OrderSide.SELL))) {
                            lines.add(buildLineTest(order, true, rateLoss));
                        } else {
                            lines.add(buildLineTest(order, false, rateLoss));
                        }
                    }

                }
            }
        }
//        LOG.info("Trade result: {} -> total:{} success:{} ratesuccess:{}% ", symbol, orders.size(), counterSuccess, counterSuccess * 100 / orders.size());
        return lines;
    }

    private String buildLine(OrderTargetInfo order, boolean orderState) {
        return order.symbol + "," + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart) + "," + order.side + "," + order.priceEntry + "," + order.priceTP + "," + symbol2LastPrice.get(order.symbol) + "," + orderState;
    }

    private String buildLineTest(OrderTargetInfoTest order, boolean orderState, Double rateloss) {
        return order.symbol + "," + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart) + "," + order.side + "," + order.priceEntry
                + "," + order.priceTP + "," + symbol2LastPrice.get(order.symbol) + "," + order.volume + "," + order.rateChange
                + "," + orderState + "," + rateloss;
    }

    private Set<Double> extractBtcBigChange(List<KlineObjectNumber> btcKlines) {
        Set<Double> results = new HashSet<>();

        for (KlineObjectNumber kline : btcKlines) {
            BreadDetectObject breadData = BreadFunctions.calBreadDataBtc(kline, 0.006);
            if (breadData.orderSide != null
                    && breadData.rateChange > 0.015) {
                results.add(kline.startTime);
                LOG.info("{} {} bread above:{} bread below:{} rateChange:{} totalRate: {}", new Date(kline.startTime.longValue()),
                        breadData.orderSide, breadData.breadAbove, breadData.breadBelow, breadData.rateChange, breadData.totalRate);
            }
        }
        return results;
    }

    private List<String> detectBigChangeWithParam(Double rateTarget, Double rateChange, Double volume,
            Map<String, List<KlineObjectNumber>> allSymbolTickers, long numberDay, Set<Double> btcBigChangeTimes) {
        //                    for (Integer volume : volumes) {
        counterTotal = 0;
        counterSuccess = 0;
        counterStoploss = 0;
        counterTotalBtcBigchane = 0;
        counterSuccessBtcBigchane = 0;
        counterStoplossBtcBigchane = 0;

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
                    BreadDetectObject breadData = BreadFunctions.calBreadDataAltWithBtcTrend(tickers, i, 0.001);
                    if (breadData.orderSide != null
                            && breadData.orderSide.equals(OrderSide.BUY)
                            && PriceManager.getInstance().isAvalible2Trade(symbol, kline.minPrice, breadData.orderSide)
                            && breadData.totalRate >= rateChange
                            && kline.totalUsdt <= volume * 1000000) {

//                                            && breadData.totalRate >= TOTAL_RATE_CHANGE_WITHBREAD_2TRADING) {
                        lastTimeBreadTrader = kline.startTime.longValue();
                        lastBreadTrader = breadData;
                        try {
                            Double priceEntry = kline.priceClose;
                            Double priceTarget = getPriceTarget(priceEntry, breadData.orderSide, rateTarget);
                            Double priceSTL = getPriceSL(priceEntry, breadData.orderSide, ALT_BREAD_BIGCHANE_STOPPLOSS);
                            OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry,
                                    priceTarget, 1.0, 10, symbol, kline.startTime.longValue(),
                                    kline.startTime.longValue(), breadData.orderSide, Constants.TRADING_TYPE_BREAD, btcBigchange);
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
        Integer rateSuccessLossBTC = 0;
        Integer rateBtcBigchangeSuccess = 0;
        if (counterTotal != 0) {
            rateSuccess = counterSuccess * 100 / counterTotal;
        }
        if (counterTotalBtcBigchane != 0) {
            rateBtcBigchangeSuccess = counterSuccessBtcBigchane * 100 / counterTotalBtcBigchane;
        }
        if (counterSuccessBtcBigchane != 0) {
            rateSuccessLossBTC = counterStoplossBtcBigchane * 100 / counterSuccessBtcBigchane;
        }
        if (counterSuccess != 0) {
            rateSuccessLoss = counterStoploss * 100 / counterSuccess;
        }
        LOG.info("Result All: rateTarget:{} rateChange:{} volume:{} numberOrderofDay {} {}-{}-{}%-{}/{} {}% btcbigchange: {}-{}-{}%-{}/{} {}%",
                rateTarget, rateChange, volume,
                counterTotal / numberDay,
                counterSuccess, counterStoploss, rateSuccessLoss, counterSuccess + counterStoploss, counterTotal, rateSuccess,
                counterSuccessBtcBigchane, counterStoplossBtcBigchane, rateSuccessLossBTC, counterSuccessBtcBigchane + counterStoplossBtcBigchane, counterTotalBtcBigchane, rateBtcBigchangeSuccess,
                Utils.toJson(date2Counter));
        return lines;
    }

    private List<String> detectBigChangeWithParamWeek(Double rateBread, Double rateTarget,
            Map<String, List<KlineObjectNumber>> allSymbolTickers, long numberDay) {
        //                    for (Integer volume : volumes) {
        counterTotal = 0;
        counterSuccess = 0;
        counterStoploss = 0;
        counterTotalBtcBigchane = 0;
        counterSuccessBtcBigchane = 0;
        counterStoplossBtcBigchane = 0;

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

                    BreadDetectObject breadData = BreadFunctions.calBreadDataAltWeek(tickers, i, rateBread);
                    if (breadData.orderSide != null) {
//                                            && breadData.totalRate >= TOTAL_RATE_CHANGE_WITHBREAD_2TRADING) {
                        lastTimeBreadTrader = kline.startTime.longValue();
                        lastBreadTrader = breadData;
                        try {
                            Double priceEntry = kline.priceClose;
                            Double priceTarget = getPriceTarget(priceEntry, breadData.orderSide, rateTarget);
                            Double priceSTL = getPriceSL(priceEntry, breadData.orderSide, ALT_BREAD_BIGCHANE_STOPPLOSS);
                            OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry,
                                    priceTarget, 1.0, 10, symbol, kline.startTime.longValue(),
                                    kline.startTime.longValue(), breadData.orderSide, Constants.TRADING_TYPE_BREAD, false);
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

        LOG.info("Result All: rateBread:{} rateTarget:{} numberOrderofDay {} {}/{} {}%",
                rateBread, rateTarget,
                counterTotal / numberDay,
                counterSuccess, counterTotal, rateSuccess);
        return lines;
    }

    private void printbyDate(List<String> lines) {
        TreeMap<Integer, Integer> date2orderFalse = new TreeMap<>();
        TreeMap<Integer, Integer> daste2OrderSuccess = new TreeMap<>();
        for (String line : lines) {
            String[] parts = line.split(",");
            try {
                String date = parts[1].split(" ")[0];
                if (StringUtils.equalsIgnoreCase(parts[parts.length - 1], "false")) {
                    Integer counter = date2orderFalse.get(Integer.parseInt(date));
                    if (counter == null) {
                        counter = 0;
                    }
                    counter++;
                    date2orderFalse.put(Integer.parseInt(date), counter);
                } else {
                    Integer counter = daste2OrderSuccess.get(Integer.parseInt(date));
                    if (counter == null) {
                        counter = 0;
                    }
                    counter++;
                    daste2OrderSuccess.put(Integer.parseInt(date), counter);
                }
            } catch (Exception e) {
            }
        }
        for (Map.Entry<Integer, Integer> entry : daste2OrderSuccess.entrySet()) {
            Integer key = entry.getKey();
            Integer value = entry.getValue();
            LOG.info("{} -> {} success {} falses", key, value, date2orderFalse.get(key));
        }
    }

    public static void main(String[] args) throws ParseException {
//        new BtcBreadBigChange1M().startThreadDetectBreadBigChange2Trade();
//        new BtcBreadBigChange2T().startThreadTradingAlt(OrderSide.BUY);
//        new AltBreadBigChange15M().startDetectBreadAlt();
//        long startTime = Utils.getStartTimeDayAgo(1000);
//        System.out.println(startTime);
//        Map<String, List<KlineObjectNumber>> allSymbolTickers = TickerHelper.getAllKlineStartTime(Constants.INTERVAL_1W, startTime);
//        allSymbolTickers = TickerHelper.getAllKlineStartTime(Constants.INTERVAL_4H, startTime);
        new AltBreadBigChange15M().startDetectBigChangeVolumeMiniInterval15M();
//        new AltBreadBigChange15M().startDetectWithTargetIntervalOneWeek();
//        new AltBreadBigChange15M().startDetectWithTargetIntervalOneHour();
//        new AltBreadBigChange15M().startDetectWithTargetInterval4Hour();
//        new AltBreadBigChange15M().startTradeMaxBreadInterval15M();
//        new AltBreadBigChange15M().startTraceBreadAlt();
//        new AltBreadBigChange15M().startDetectBreadAltWithConstant();
    }

}
