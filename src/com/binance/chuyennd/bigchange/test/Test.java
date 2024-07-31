/*
 * Copyright 2023 pc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.binance.chuyennd.bigchange.test;

import com.binance.chuyennd.bigchange.statistic.BreadDetectObject;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.indicators.*;
import com.binance.chuyennd.mongo.TickerMongoHelper;
import com.binance.chuyennd.movingaverage.MAStatus;
import com.binance.chuyennd.object.*;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.research.BudgetManagerTest;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.signal.tradingview.OrderTargetInfoTestSignal;
import com.binance.chuyennd.signal.tradingview.SignalTWSimulator;
import com.binance.chuyennd.trading.OrderTargetInfo;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.SubscriptionClient;
import com.binance.client.SubscriptionErrorHandler;
import com.binance.client.constant.Constants;
import com.binance.client.exception.BinanceApiException;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.event.CandlestickEvent;
import com.binance.client.model.event.SymbolTickerEvent;
import com.binance.tech.indicators.complex.TechnicalRatings;
import com.binance.tech.model.TechCandle;
import com.educa.chuyennd.funcs.BreadFunctions;
import com.google.gson.internal.LinkedTreeMap;
import com.mongodb.client.MongoCursor;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang.StringUtils;
import org.bson.Document;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.text.ParseException;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.logging.Level;

/**
 * @author pc
 */
public class Test {

    public static final Logger LOG = LoggerFactory.getLogger(Test.class);

    public static final String FILE_STORAGE_ORDER_DONE = "target/OrderTestDone.data";
    public static final Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
    public static final String FILE_STORAGE_ORDER_DONE_TA = "target/OrderTestTADone.data";
    public static final String TIME_RUN = Configs.getString("TIME_RUN");
    public ExecutorService executorServiceOrderNew = Executors.newFixedThreadPool(Configs.getInt("NUMBER_THREAD_ORDER_MANAGER"));
    private final ConcurrentHashMap<String, Long> symbol2Processing = new ConcurrentHashMap<>();

    public static void main(String[] args) throws Exception {
//        List<PositionRisk> positions = BinanceFuturesClientSingleton.getInstance().getAllPositionInfos();
        // check stop all when market maybe bigdump
//        new BinanceOrderTradingManager().checkAndStopLossAll(positions);
//        System.out.println(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_MOVING_AVERAGE_DETAILS, "REZUSDT"));
//        new SignalTWSimulator().printAllOrderRunning();
//        new SignalTWSimulator().buildReportTest();
//        System.out.println(getSignalBTCHour());
//        System.out.println(Utils.sdfFile.parse("20230509").getTime() + 7 * Utils.TIME_HOUR);

//        new BinanceOrderTradingManager().processManagerPosition();

//        traceRateChangeByDate("20240412");
//        new BinanceOrderTradingManager().checkAndCloseOrderLatestOverTimeMin();
//        printOrderTATestDone();
//        RedisHelper.getInstance().get().del("redis.key.educa.test.signal.order.manager.web1");
//        System.out.println(RedisHelper.getInstance().readAllId("redis.key.educa.test.signal.order.manager.web1"));

//        detectBtcBottom("AIUSDT");
//        detectBtcBottomNew();
//        detectBtcTop();
//        testRsi();
//        testMACD();
//        testMACDTrend15M();
//        testRSITrend15M();

//        testMACDTrendNew1Hour();
//        testMACDTrendNew4Hour();
//            printTickerData();
//        traceOrderRunning();
//        testSMA();
//        changeLeverage();
//        printTickerInMongo();

//        testGetDataMongo();
//        traceInfoSymbol("TRXUSDT");


//        checkPriceMax();
//        checkTimeLock();
//        String interval = Constants.INTERVAL_1H;
//        Map<Long, TechnicalRatings.RatingStatus> ratingBtc = testTechRating(interval);
//        Storage.writeObject2File(DataManager.FILE_DATA_BTC_RATING + interval, ratingBtc);
//        interval = Constants.INTERVAL_4H;
//         ratingBtc = testTechRating(interval);
//        Storage.writeObject2File(DataManager.FILE_DATA_BTC_RATING + interval, ratingBtc);
//        interval = Constants.INTERVAL_1D;
//         ratingBtc = testTechRating(interval);
//        Storage.writeObject2File(DataManager.FILE_DATA_BTC_RATING + interval, ratingBtc);
//        System.exit(1);

    }

    public static com.binance.tech.model.TechCandle[] toCandleArray(List<KlineObjectNumber> lstCandles) {
        com.binance.tech.model.TechCandle[] candle = new com.binance.tech.model.TechCandle[lstCandles.size()];
        for (int i = 0; i < lstCandles.size(); i++) {
            candle[i] = toCandle(lstCandles.get(i));
        }
        return candle;
    }

    private static TechCandle toCandle(KlineObjectNumber kline) {
        com.binance.tech.model.TechCandle candle = new com.binance.tech.model.TechCandle();
        candle.setOpenTime(ZonedDateTime.ofInstant(Instant.ofEpochMilli(kline.startTime.longValue()), ZoneOffset.UTC));
        candle.setOpenPrice(kline.priceOpen);
        candle.setClosePrice(kline.priceClose);
        candle.setHighPrice(kline.maxPrice);
        candle.setLowPrice(kline.minPrice);
        candle.setVolume(kline.totalUsdt);
        candle.setQuoteVolume(kline.totalUsdt);
        candle.setCount(0);
        return candle;
    }

    private static Map<Long, TechnicalRatings.RatingStatus> testTechRating(String interval) throws Exception {
        Map<Long, TechnicalRatings.RatingStatus> time2BtcRating = new HashMap<>();
        String fileName = null;
        switch (interval) {
            case Constants.INTERVAL_1D:
                fileName = DataManager.FOLDER_TICKER_1D;
                break;
            case Constants.INTERVAL_4H:
                fileName = DataManager.FOLDER_TICKER_4HOUR;
                break;
            case Constants.INTERVAL_1H:
                fileName = DataManager.FOLDER_TICKER_HOUR;
                break;
            case Constants.INTERVAL_15M:
                fileName = DataManager.FOLDER_TICKER_15M;
                break;
        }
        fileName = fileName + Constants.SYMBOL_PAIR_BTC;
        List<KlineObjectNumber> btcTickers = (List<KlineObjectNumber>)
                Storage.readObjectFromFile(fileName);
        List<KlineObjectNumber> tickers = new ArrayList<>();
        int counter = 0;
        int total = btcTickers.size();
        for (KlineObjectNumber ticker : btcTickers) {
            try {
                tickers.add(ticker);
                counter ++;
                LOG.info("{}/{}", counter , total);
                if (tickers.size() < 200) {
                    continue;
                }
                com.binance.tech.model.TechCandle[] candles = toCandleArray(tickers);
                int pricePrecision = 5;
                TechnicalRatings tech = new TechnicalRatings(pricePrecision);
                tech.calculate(candles);
                time2BtcRating.put(ticker.startTime.longValue(), tech.getMaRatingStatus());
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return time2BtcRating;

    }

    private static void traceRateChangeByDate(String date) {
        try {
            Long time = Utils.sdfFile.parse(date).getTime() + 7 * Utils.TIME_HOUR;
            File[] symbolFiles = new File(DataManager.FOLDER_TICKER_1D).listFiles();
            TreeMap<Double, String> rate2Symbol = new TreeMap<>();
            for (File symbolFile : symbolFiles) {
                String symbol = symbolFile.getName();
                if (!org.apache.commons.lang.StringUtils.endsWithIgnoreCase(symbol, "usdt") ||
                        Constants.diedSymbol.contains(symbol)) {
                    continue;
                }
                List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(symbolFile.getPath());
                for (KlineObjectNumber ticker : tickers) {
                    if (ticker.startTime.longValue() == time) {
                        Double rateChange = Utils.rateOf2Double(ticker.maxPrice, ticker.priceClose);
                        rate2Symbol.put(rateChange, symbol);
                    }
                }
            }
            for (Map.Entry<Double, String> entry : rate2Symbol.entrySet()) {
                Double key = entry.getKey();
                String values = entry.getValue();
                LOG.info("{} -> {}", values, key);
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static OrderSide getSignalBTCHour() {

        try {
            String respon = new SignalTWSimulator().getRecommendationRaw(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_1H);
            List<LinkedTreeMap> responObjects = Utils.gson.fromJson(respon, List.class);
            if (responObjects != null && !responObjects.isEmpty()) {
                String sideSignal = responObjects.get(0).get("recommendation").toString();
                if (StringUtils.contains(sideSignal, "BUY")) {
                    return OrderSide.BUY;
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return OrderSide.SELL;
    }

    private static void printTickerData() {
        String symbol = "RENUSDT";
        List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile("storage/ticker/symbols-15m/" + symbol);
        for (int i = 1; i < 10000; i++) {
            KlineObjectNumber lastTicker = tickers.get(tickers.size() - i - 1);
            KlineObjectNumber ticker = tickers.get(tickers.size() - i);
            LOG.info("{} {} -> {} : {}", Utils.normalizeDateYYYYMMDDHHmm(lastTicker.startTime.longValue()),
                    lastTicker.histogram, ticker.histogram,
                    Utils.rateOf2DoubleIncre(ticker.histogram, lastTicker.histogram));
        }
    }


    private static void testMACDTrend15M() throws ParseException {
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        DataManager.getInstance();
        String symbol = "ADAUSDT";
        List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile("storage/ticker/symbols-15m/" + symbol);

        LOG.info(Utils.normalizeDateYYYYMMDDHHmm(tickers.get(tickers.size() - 1).startTime.longValue()));
        int counterSuccess = 0;
        Integer counterFalse = 0;
        for (int i = 0; i < tickers.size(); i++) {
            if (tickers.get(i).startTime.longValue() == Utils.sdfFileHour.parse("20240515 20:00").getTime()) {
                System.out.println("Debug");
            }
            KlineObjectNumber kline = tickers.get(i);
            if (kline.startTime.longValue() < startTime) {
                continue;
            }
//            LOG.info("{}", Utils.normalizeDateYYYYMMDDHHmm(tickers.get(i).startTime.longValue()));
            DataManager.getInstance().updateData(kline, symbol);
            MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(kline.startTime.longValue(), symbol);
            Double maValue = SimpleMovingAverage1DManager.getInstance().getMaValue(symbol, Utils.getDate(kline.startTime.longValue()));
            Double rateMa = Utils.rateOf2Double(kline.priceClose, maValue);
            if (maValue == null) {
                continue;
            }


            if (MACDTradingController.isMacdCutUpSignalFirst(tickers, i)
                    && maStatus != null && !maStatus.equals(MAStatus.UNDER)

            ) {

                KlineObjectNumber tickerClose = tickers.get(tickers.size() - 1);

//                if (indexStop != null) {
//                    tickerClose = tickers.get(indexStop);
//                }
                boolean tradeStatus = MACDTradingController.isTradingStatus(tickers, i, 0.01, 10);
                if (tradeStatus) {
                    counterSuccess++;
                } else {
                    counterFalse++;
                }
                LOG.info("Result: {} {} ->  {} {}", tradeStatus,
                        Utils.normalizeDateYYYYMMDDHHmm(tickers.get(i).startTime.longValue()),
                        tickers.get(i).priceClose, Utils.toJson(kline)
                );
            }
        }
        LOG.info("{}/{} {}", counterFalse, counterSuccess, counterFalse.doubleValue() / counterSuccess);
    }

    private static void testRSITrend15M() throws ParseException {


        int counterSuccess = 0;
        Integer counterFalse = 0;
        for (File file : new File(DataManager.FOLDER_TICKER_15M).listFiles()) {
//            LOG.info("{} {}", file.getName(), file.getPath());
            String symbol = file.getName();
            if (Constants.diedSymbol.contains(symbol) || !StringUtils.containsIgnoreCase(symbol, "usdt")) {
                continue;
            }
            List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(file.getPath());

            for (int i = 0; i < tickers.size(); i++) {
//                if (tickers.get(i).startTime.longValue() == Utils.sdfFileHour.parse("20240515 20:00").getTime()) {
//                    System.out.println("Debug");
//                }
                KlineObjectNumber kline = tickers.get(i);
                MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(kline.startTime.longValue(), symbol);
                Double maValue = SimpleMovingAverage1DManager.getInstance().getMaValue(symbol, Utils.getDate(kline.startTime.longValue()));
                Double rateMa = Utils.rateOf2Double(kline.priceClose, maValue);
                if (maValue == null) {
                    continue;
                }


                if (RelativeStrengthIndex.isRsiSignalBuy(tickers, i)
                        && maStatus != null && maStatus.equals(MAStatus.TOP)
                ) {

                    KlineObjectNumber tickerClose = tickers.get(tickers.size() - 1);

//                if (indexStop != null) {
//                    tickerClose = tickers.get(indexStop);
//                }
                    boolean tradeStatus = MACDTradingController.isTradingStatus(tickers, i, 0.01, 48);
                    if (tradeStatus) {
                        counterSuccess++;
                    } else {
                        counterFalse++;
                    }
                    LOG.info("Result: {} {} {} ->  {} {}", symbol, tradeStatus,
                            Utils.normalizeDateYYYYMMDDHHmm(tickers.get(i).startTime.longValue()),
                            tickers.get(i).priceClose, tickers.get(i).rsi
                    );
                }
            }
        }
        LOG.info("{}/{} {}", counterFalse, counterSuccess, counterFalse.doubleValue() / counterSuccess);
    }

    private static void testMACDTrendNew() throws ParseException {
        String symbol = "BLZUSDT";
        List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile("storage/ticker/symbols-15m/" + symbol);
        LOG.info(Utils.normalizeDateYYYYMMDDHHmm(tickers.get(tickers.size() - 1).startTime.longValue()));
        int counterSuccess = 0;
        Integer counterFalse = 0;
        for (int i = 0; i < tickers.size(); i++) {
//            if (tickers.get(i).startTime.longValue() == Utils.sdfFileHour.parse("20240509 04:15").getTime()){
//                System.out.println("Debug");
//            }
            KlineObjectNumber kline = tickers.get(i);
            MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(kline.startTime.longValue(), symbol);
            Double maValue = SimpleMovingAverage1DManager.getInstance().getMaValue(symbol, Utils.getDate(kline.startTime.longValue()));
            Double rateMa = Utils.rateOf2Double(kline.priceClose, maValue);
            if (maValue == null) {
                continue;
            }
            if (MACDTradingController.isMacdTrendBuyNew(tickers, i)
                    && maStatus != null && maStatus.equals(MAStatus.TOP)
                    && kline.priceClose > maValue
            ) {
                Integer indexStop = null;
                for (int j = i + 1; j < tickers.size(); j++) {
                    if (tickers.get(j).histogram > 0) {
                        indexStop = j;
                        break;
                    }
                }
                KlineObjectNumber tickerClose = tickers.get(tickers.size() - 1);
                if (indexStop != null) {
                    tickerClose = tickers.get(indexStop);
                }
                boolean tradeStatus = MACDTradingController.isTradingStatus(tickers, i, 0.01, 12);
                if (tradeStatus) {
                    counterSuccess++;
                } else {
                    counterFalse++;
                    LOG.info("Result: {} {} -> {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(tickers.get(i).startTime.longValue()),
                            tickers.get(i).priceClose, Utils.normalizeDateYYYYMMDDHHmm(tickerClose.startTime.longValue()),
                            tickerClose.priceClose, MACDTradingController.isTradingStatus(tickers, i, 0.01, 12));
                }
            }
        }
        LOG.info("{}/{} {}", counterFalse, counterSuccess, counterFalse.doubleValue() / counterSuccess);
    }

    private static void testMACDTrendNew1Hour() throws ParseException {
        int counterSuccess = 0;
        Integer counterFalse = 0;
        for (File file : new File(DataManager.FOLDER_TICKER_HOUR).listFiles()) {
            LOG.info("{} {}", file.getName(), file.getPath());
            String symbol = file.getName();
            if (!StringUtils.endsWithIgnoreCase(symbol, "usdt") || Constants.diedSymbol.contains(symbol)) {
                continue;
            }
//            if (!StringUtils.equals(symbol, "PEOPLEUSDT")) {
//                continue;
//            }
            List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(file.getPath());

            LOG.info(Utils.normalizeDateYYYYMMDDHHmm(tickers.get(tickers.size() - 1).startTime.longValue()));
            for (int i = 0; i < tickers.size(); i++) {
//            LOG.info("{}", Utils.normalizeDateYYYYMMDDHHmm(tickers.get(i).startTime.longValue()));
//                if (tickers.get(i).startTime.longValue() == Utils.sdfFileHour.parse("20240601 09:15").getTime()) {
//                    System.out.println("Debug");
//                }
                KlineObjectNumber kline = tickers.get(i);
                SimpleMovingAverage1DManager.getInstance().updateWithTicker(symbol, kline);
                MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(kline.startTime.longValue(), symbol);
                Double maValue = SimpleMovingAverage1DManager.getInstance().getMaValue(symbol, Utils.getDate(kline.startTime.longValue()));
                Double rateMa = Utils.rateOf2Double(kline.priceClose, maValue);
                Double rateMaWithCurrentInterval = Utils.rateOf2Double(kline.priceClose, kline.ma20);
                if (maValue == null) {
                    continue;
                }
                if (MACDTradingController.isMacdTrendUpAndTickerDown(tickers, i, 2.0)
//                        && rateMaWithCurrentInterval < 0
                        && maStatus != null && maStatus.equals(MAStatus.TOP)
                        && rateMa < 0.3
//                    && rateMa > 0.05 && rateMa < 0.3
//                    && kline.priceClose > maValue
//                        && MACDTradingController.rateChangeWithMax(tickers, i - 5, i) > 0.02
                ) {
                    Integer indexStop = null;
                    for (int j = i + 1; j < tickers.size(); j++) {
                        if (tickers.get(j).histogram > 0) {
                            indexStop = j;
                            break;
                        }
                    }
                    KlineObjectNumber tickerClose = tickers.get(tickers.size() - 1);
                    if (indexStop != null) {
                        tickerClose = tickers.get(indexStop);
                    }
                    boolean tradeStatus = MACDTradingController.isTradingStatus(tickers, i, RATE_TARGET, 16);
                    if (tradeStatus) {
                        counterSuccess++;
                    } else {
                        counterFalse++;
                    }
                    LOG.info("Result:{} {} {} -> {} {} {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(tickers.get(i).startTime.longValue()),
                            tickers.get(i).priceClose, Utils.normalizeDateYYYYMMDDHHmm(tickerClose.startTime.longValue()),
                            tickerClose.priceClose, tradeStatus
                            , MACDTradingController.rateChangeWithMax(tickers, i - 5, i),
                            Utils.rateOf2Double(tickers.get(i).priceClose, tickers.get(i).priceOpen));
                }
            }
        }
        LOG.info("{}/{} {}", counterFalse, counterSuccess, counterFalse.doubleValue() / counterSuccess);
    }

    private static void testMACDTrendNew4Hour() throws ParseException {
        int counterSuccess = 0;
        Integer counterFalse = 0;
        for (File file : new File("storage/ticker/symbols-4h/").listFiles()) {
//            LOG.info("{} {}", file.getName(), file.getPath());
            String symbol = file.getName();
            List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(file.getPath());

            LOG.info(Utils.normalizeDateYYYYMMDDHHmm(tickers.get(tickers.size() - 1).startTime.longValue()));
            for (int i = 0; i < tickers.size(); i++) {
//            LOG.info("{}", Utils.normalizeDateYYYYMMDDHHmm(tickers.get(i).startTime.longValue()));
//            if (tickers.get(i).startTime.longValue() == Utils.sdfFileHour.parse("20240514 22:00").getTime()){
//                System.out.println("Debug");
//            }
                KlineObjectNumber kline = tickers.get(i);
                MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(kline.startTime.longValue(), symbol);
                Double maValue = SimpleMovingAverage1DManager.getInstance().getMaValue(symbol, Utils.getDate(kline.startTime.longValue()));
                Double rateMa = Utils.rateOf2Double(kline.priceClose, maValue);
                if (maValue == null) {
                    continue;
                }
                if (MACDTradingController.isMacdTrendBuyNew1h(tickers, i)
                        && maStatus != null && maStatus.equals(MAStatus.TOP)
//                    && rateMa > 0.05 && rateMa < 0.3
//                    && kline.priceClose > maValue
                        && MACDTradingController.rateChangeWithMax(tickers, i - 5, i) > 0.02
                ) {
                    Integer indexStop = null;
                    for (int j = i + 1; j < tickers.size(); j++) {
                        if (tickers.get(j).histogram > 0) {
                            indexStop = j;
                            break;
                        }
                    }
                    KlineObjectNumber tickerClose = tickers.get(tickers.size() - 1);
                    if (indexStop != null) {
                        tickerClose = tickers.get(indexStop);
                    }
                    boolean tradeStatus = MACDTradingController.isTradingStatus(tickers, i, 0.005, 18);
                    if (tradeStatus) {
                        counterSuccess++;
                    } else {
                        counterFalse++;
                    }
                    LOG.info("Result:{} {} {} -> {} {} {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(tickers.get(i).startTime.longValue()),
                            tickers.get(i).priceClose, Utils.normalizeDateYYYYMMDDHHmm(tickerClose.startTime.longValue()),
                            tickerClose.priceClose, tradeStatus
                            , MACDTradingController.rateChangeWithMax(tickers, i - 5, i),
                            Utils.rateOf2Double(tickers.get(i).priceClose, tickers.get(i).priceOpen));
                }
            }
        }
        LOG.info("{}/{} {}", counterFalse, counterSuccess, counterFalse.doubleValue() / counterSuccess);
    }

    private static void detectBtcTop() {
        List<KlineObjectNumber> tickers = TickerMongoHelper.getInstance().getTicker15mBySymbol(Constants.SYMBOL_PAIR_BTC);
        Map<Long, KlineObjectNumber> time2Ticker = new HashMap<>();
        Long lastBottom = 0l;
        Integer period = 30;
        for (int i = period; i < tickers.size(); i++) {
            if (tickers.get(i - period).rsi == null) {
                continue;
            }
            Double rsiAvg = calAvgRsi(tickers, i - period, period);
            KlineObjectNumber before2Ticker = tickers.get(i - 6);
            KlineObjectNumber before1Ticker = tickers.get(i - 5);
            KlineObjectNumber beforeTicker = tickers.get(i - 4);
            KlineObjectNumber ticker = tickers.get(i - 3);
            KlineObjectNumber afterTicker = tickers.get(i - 2);
            KlineObjectNumber after1Ticker = tickers.get(i - 1);
            KlineObjectNumber after2Ticker = tickers.get(i);
            Double rateMa = Utils.rateOf2Double(afterTicker.ma20, afterTicker.priceClose);
            if (afterTicker.rsi < ticker.rsi
                    && after1Ticker.rsi < afterTicker.rsi
                    && after2Ticker.rsi < afterTicker.rsi
                    && ticker.rsi > beforeTicker.rsi
//                    && before1Ticker.rsi < ticker.rsi
//                    && beforeTicker.rsi > before2Ticker.rsi
                    && ticker.rsi - rsiAvg > 10
                    && ticker.rsi >= 60
            ) {
                LOG.info("BTC bottom: {} {} {} {} {} hours", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), rsiAvg,
                        ticker.rsi, rsiAvg - ticker.rsi, (ticker.startTime.longValue() - lastBottom) / Utils.TIME_HOUR);
                lastBottom = ticker.startTime.longValue();
            }
        }
    }

    private static void detectBtcBottom(String symbol) {
        List<KlineObjectNumber> tickers = TickerMongoHelper.getInstance().getTicker15mBySymbol(symbol);
        Map<Long, KlineObjectNumber> time2Ticker = new HashMap<>();
        Long lastBottom = 0l;
        for (int i = 0; i < tickers.size(); i++) {
            if (TickerFuturesHelper.isButton(tickers, i, 30)) {
                KlineObjectNumber ticker = tickers.get(i - 2);
                LOG.info("{} bottom: {} {} {} {} hours", symbol, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()),
                        tickers.get(i).priceClose,
                        ticker.rsi, (ticker.startTime.longValue() - lastBottom) / Utils.TIME_HOUR);
                lastBottom = ticker.startTime.longValue();
            }
        }
    }

    private static void detectBtcBottomNew() {
        List<KlineObjectNumber> tickers = TickerMongoHelper.getInstance().getTicker15mBySymbol(Constants.SYMBOL_PAIR_BTC);
        Long lastBottom = 0l;
        Integer period = 30;
        for (int i = period; i < tickers.size(); i++) {
            if (tickers.get(i - period).rsi == null) {
                continue;
            }
            Double rsiAvg = calAvgRsi(tickers, i - period, period);
            KlineObjectNumber before2Ticker = tickers.get(i - 5);
            KlineObjectNumber before1Ticker = tickers.get(i - 4);
            KlineObjectNumber beforeTicker = tickers.get(i - 3);
            KlineObjectNumber ticker = tickers.get(i - 2);
            KlineObjectNumber afterTicker = tickers.get(i - 1);
            KlineObjectNumber after1Ticker = tickers.get(i);

            if (afterTicker.rsi > ticker.rsi
                    && after1Ticker.rsi > afterTicker.rsi
                    && ticker.rsi < beforeTicker.rsi
                    && beforeTicker.rsi < before1Ticker.rsi
                    && beforeTicker.rsi < before2Ticker.rsi
                    && rsiAvg - ticker.rsi > 10
                    && ticker.rsi <= 40
            ) {
                LOG.info("BTC bottom: {} {} {} {} {} hours", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), rsiAvg,
                        ticker.rsi, rsiAvg - ticker.rsi, (ticker.startTime.longValue() - lastBottom) / Utils.TIME_HOUR);
                lastBottom = ticker.startTime.longValue();
            }
        }

    }

    private static Double calAvgRsi(List<KlineObjectNumber> tickers, int i, int duration) {
        Double total = 0d;
        for (int j = i; j < i + duration; j++) {
            KlineObjectNumber ticker = tickers.get(j);
            total += ticker.rsi;
        }
        return total / duration;
    }


    private static void testSMA() {
        List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker("BTCUSDT", Constants.INTERVAL_1D);
        IndicatorEntry[] smaEntries = SimpleMovingAverage.calculate(tickers, 20);
        Arrays.stream(smaEntries).forEach(s -> System.out.println(s));
    }

    private static void testRsi() {
        List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker("USTCUSDT", Constants.INTERVAL_15M);

        RsiEntry[] rsi = calculateRSI(tickers, 14);

        for (int index = 0; index < rsi.length; index++) {
            LOG.info("{} ->Close:{} rsi: {}", Utils.normalizeDateYYYYMMDDHHmm(tickers.get(index + 14).startTime.longValue()),
                    tickers.get(index + 14).priceClose, rsi[index].getRsi());
        }
    }

    private static void testMACD() throws ParseException {
        List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker("BTCUSDT", Constants.INTERVAL_1D);

        MACDEntry[] entries = MACD.calculate(tickers, 12, 26, 9);
//        Arrays.stream(entries).forEach(s -> System.out.println(s == null ? "null" : s));
        for (int i = 0; i < entries.length; i++) {
            if (i < 1) {
                continue;
            }

            MACDEntry lastEntrie = entries[i - 1];
            MACDEntry entrie = entries[i];
            if (lastEntrie.getHistogram() < 0
                    && entrie.getHistogram() > 0
                    && lastEntrie.getSignal() < 0
            ) {
                System.out.println(entrie == null ? "null" : entrie);
            }
        }
    }

    public static RsiEntry[] calculateRSI(List<KlineObjectNumber> candles, int periods) {
        RsiEntry[] rsiEntries;

        rsiEntries = new RsiEntry[candles.size() - periods];
        int idx = 0;

        double[] change = new double[candles.size()];
        double[] gain = new double[candles.size()];
        double[] loss = new double[candles.size()];
        double avgGain;
        double avgLoss;

        for (int i = 1; i < candles.size(); i++) {
            change[i] = candles.get(i).priceClose - candles.get(i - 1).priceClose;

            if (change[i] > 0)
                gain[i] = change[i];
            else if (change[i] < 0)
                loss[i] = change[i] * -1;

            if (i >= periods) {
                if (i == periods) {
                    avgGain = avg(gain, 1, periods);
                    avgLoss = avg(loss, 1, periods);
                } else {
                    avgGain = (rsiEntries[idx - 1].getAvgGain() * (periods - 1) + gain[i]) / periods;
                    avgLoss = (rsiEntries[idx - 1].getAvgLoss() * (periods - 1) + loss[i]) / periods;
                }
                double rs = avgGain / avgLoss;
                double rsi = 100 - (100 / (1 + rs));

                rsiEntries[idx] = new RsiEntry(candles.get(i));
                rsiEntries[idx].setChange(change[i]);
                rsiEntries[idx].setGain(gain[i]);
                rsiEntries[idx].setLoss(loss[i]);
                rsiEntries[idx].setAvgGain(avgGain);
                rsiEntries[idx].setAvgLoss(avgLoss);
                rsiEntries[idx].setRs(rs);
                rsiEntries[idx].setRsi(rsi);

                idx++;
            }

        }

        return rsiEntries;
    }

    public static double avg(double[] values, int startIndex, int endIndex) {
        double sum = 0;
        for (int i = startIndex; i <= endIndex; i++) {
            sum += values[i];
        }
        return sum / (endIndex - startIndex + 1);
    }

    private static void changeLeverage() {
        Set<String> allSymbols = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS);
        for (String symbol : allSymbols) {
            try {
                ClientSingleton.getInstance().syncRequestClient.changeInitialLeverage(symbol, 10);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }


    private static void printOrderTATestDone() throws IOException {

        ConcurrentHashMap<Long, OrderTargetInfoTestSignal> ordersDone =
                (ConcurrentHashMap<Long, OrderTargetInfoTestSignal>) Storage.readObjectFromFile(FILE_STORAGE_ORDER_DONE_TA);

        List<String> lines = new ArrayList<>();
        for (Map.Entry<Long, OrderTargetInfoTestSignal> entry : ordersDone.entrySet()) {
            Long timeUpdate = entry.getKey();
            OrderTargetInfoTestSignal order = entry.getValue();
            long date = Utils.getDate(order.timeStart);
            Double maValue = SimpleMovingAverage1DManager.getInstance().getMaValue(order.symbol, date);
            Double ma15mValue = SimpleMovingAverage15M.getInstance().getMaValue(order.symbol, order.timeStart);
            MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(order.timeStart, order.symbol);
            StringBuilder builder = new StringBuilder();
            builder.append(order.symbol).append(",");
            builder.append(order.priceEntry).append(",");
            builder.append(ma15mValue).append(",");
            builder.append(Utils.rateOf2Double(order.priceEntry, ma15mValue)).append(",");
            builder.append(order.priceTP).append(",");
            builder.append(Utils.rateOf2Double(order.priceTP, order.priceEntry)).append(",");
            builder.append(order.maxPrice).append(",");
            builder.append(Utils.rateOf2Double(order.priceEntry, maValue)).append(",");
            builder.append(maValue).append(",");
            builder.append(maStatus).append(",");
            builder.append(Utils.rateOf2Double(order.maxPrice, order.priceEntry)).append(",");
            builder.append(order.status.toString()).append(",");
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)).append(",");
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(timeUpdate)).append(",");
            builder.append(calTp(order)).append(",");
            builder.append(extractSignalVotes(order.signals)).append(",");
            builder.append(extractSignal(order.signals)).append(",");
            builder.append((timeUpdate - order.timeStart) / Utils.TIME_MINUTE);
            lines.add(builder.toString());
        }

        FileUtils.writeLines(new File("target/printTADone.csv"), lines);
    }

    private static String extractSignal(List<String> signals) {
        StringBuilder builder = new StringBuilder();
        for (String signal : signals) {
            List<LinkedTreeMap> responObjects = Utils.gson.fromJson(signal, List.class);
            if (responObjects != null && !responObjects.isEmpty()) {
                String sideSignal = responObjects.get(0).get("recommendation").toString();
                String interval = responObjects.get(0).get("interval").toString();
                String pair = responObjects.get(0).get("pair").toString();
//                builder.append(pair).append("-");
//                builder.append(interval).append("-");
//                if (StringUtils.equals(pair, "BTCUSDT")) {
                builder.append(sideSignal).append("||");
//                }
            }
        }
        return builder.toString();
    }

    private static String extractSignalVotes(List<String> signals) {

        for (String signal : signals) {
            List<LinkedTreeMap> responObjects = Utils.gson.fromJson(signal, List.class);
            if (responObjects != null && !responObjects.isEmpty()) {
                String sideSignal = responObjects.get(0).get("recommendation").toString();
                String interval = responObjects.get(0).get("interval").toString();
                String pair = responObjects.get(0).get("pair").toString();
                String votes = responObjects.get(0).get("votes").toString();
//                builder.append(pair).append("-");
//                builder.append(interval).append("-");
                return votes;
            }
        }
        return null;
    }



    public static Double calTp(OrderTargetInfoTestSignal orderInfo) {
        Double tp = orderInfo.quantity * (orderInfo.priceTP - orderInfo.priceEntry);
        return tp;
    }

    private static void testGetDataMongo() throws ParseException {
        Long startTime = Utils.sdfFile.parse("202405012").getTime() + 7 * Utils.TIME_HOUR;
        Long startTimeCheck = Utils.sdfFileHour.parse("20240511 19:15").getTime();
        TreeMap<Long, Map<String, KlineObjectNumber>> time2Tickers = TickerMongoHelper.getInstance().getDataFromDb(startTime);
        for (Map.Entry<Long, Map<String, KlineObjectNumber>> entry : time2Tickers.entrySet()) {
            Long time = entry.getKey();
            Map<String, KlineObjectNumber> symbol2Ticker = entry.getValue();
            if (time.equals(startTimeCheck)) {
                LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(time), Utils.normalizeDateYYYYMMDDHHmm(startTimeCheck));
                for (Map.Entry<String, KlineObjectNumber> entry1 : symbol2Ticker.entrySet()) {
                    String symbol = entry1.getKey();
                    KlineObjectNumber ticker = entry1.getValue();
                    LOG.info("{} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), symbol, Utils.rateOf2Double(ticker.maxPrice, ticker.minPrice),
                            Utils.toJson(ticker));
                }
            }
//            LOG.info("{} ", Utils.normalizeDateYYYYMMDDHHmm(time));

        }
    }

    private static void traceInfoSymbol(String symbol) throws ParseException {
        List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile("storage/ticker/symbols-15m/" + symbol);
        for (int i = 0; i < tickers.size(); i++) {
            if (tickers.get(i).startTime.longValue() >= Utils.sdfFileHour.parse("20240512 19:15").getTime()) {
                LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(tickers.get(i).startTime.longValue()),
                        tickers.get(i).histogram);
            }
        }

    }

    private static void testBudget() {
        Double totalMargin = 0d;
        for (int i = 0; i < 200; i++) {
            Double budget = BudgetManagerTest.getInstance().getBudget();
            totalMargin += budget;
            Double rate = budget * 10000 / 10000;
            Long rateL = rate.longValue();
            LOG.info("STT: {} budget:{} rate: {}% total: {}", i + 1, Utils.formatMoneyNew(budget), rateL.doubleValue() / 100, totalMargin);
        }
    }

    private static void traceOrderRunning() {
        BudgetManagerTest test = new BudgetManagerTest();
        List<OrderTargetInfoTest> orderInfos = test.getListOrderRunning();
        for (OrderTargetInfoTest order : orderInfos) {
            LOG.info("{} {} entry:{} tp:{} status:{}", order.symbol, Utils.normalizeDateYYYYMMDDHHmm(order.timeStart), order.priceEntry
                    , order.priceTP, order.status);
        }
    }

    private static void printTickerInMongo() throws ParseException {
        Long time = Utils.sdfFile.parse("20240509").getTime() + 7 * Utils.TIME_HOUR;
        System.out.println(time);
        String symbol = "BATUSDT";
        MongoCursor<Document> docs = TickerMongoHelper.getInstance().getTicker15m(time, symbol);
        List<KlineObjectNumber> tickersOnline = TickerFuturesHelper.getTickerWithStartTime(symbol, Constants.INTERVAL_15M, time);
        Map<Long, KlineObjectNumber> time2TickerOnline = new HashMap<>();
        for (KlineObjectNumber tickerOnline : tickersOnline) {
            time2TickerOnline.put(tickerOnline.startTime.longValue(), tickerOnline);
        }

        while (docs.hasNext()) {
            Document doc = docs.next();
            List<KlineObjectNumber> tickers = TickerMongoHelper.getInstance().extractDetails(doc);
            for (KlineObjectNumber ticker : tickers) {
                KlineObjectNumber tickerOnline = time2TickerOnline.get(ticker.startTime.longValue());
                boolean khop = true;
                if (tickersOnline == null || tickerOnline.minPrice != ticker.minPrice
                        || tickerOnline.maxPrice != ticker.maxPrice
                        || tickerOnline.priceClose != ticker.priceClose
                        || tickerOnline.priceOpen != ticker.priceOpen) {
                }
                LOG.info("{} {}  Open:{} max: {} min: {} Close: {} vol:{} khop: {} ma:{} rsi:{}", ticker.startTime,
                        Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), ticker.priceOpen, ticker.maxPrice,
                        ticker.minPrice, ticker.priceClose, ticker.totalUsdt, khop, ticker.ma20, ticker.rsi);
            }
        }
    }


    public static boolean isTimeRun() {
        return Utils.getCurrentMinute() % 15 == 9 && Utils.getCurrentSecond() == 50;
    }

    private static void testUserDataStream() {

        String listenKey = ClientSingleton.getInstance().syncRequestClient.startUserDataStream();
        System.out.println("listenKey: " + listenKey);

        // Keep user data stream
        ClientSingleton.getInstance().syncRequestClient.keepUserDataStream(listenKey);

        // Close user data stream
        //syncRequestClient.closeUserDataStream(listenKey);
        SubscriptionClient client = SubscriptionClient.create();

        client.subscribeUserDataEvent(listenKey, ((event) -> {
            //event.getEventType();
            System.out.println(event.getEventType());
        }), null);

    }

    public static Double calRateLoss(OrderTargetInfo orderInfo, Double lastPrice) {
        double rate = Utils.rateOf2Double(lastPrice, orderInfo.priceEntry);
        if (orderInfo.side.equals(OrderSide.SELL)) {
            rate = -rate;
        }
        return rate * 7 / 10;
    }

    private static long calTimeLock(long currentTime) {
        return currentTime + (10 - Utils.getCurrentMinute(currentTime) % 10) * Utils.TIME_MINUTE;
    }

    private static void checkTimeLock() {
        for (Map.Entry<String, String> entry : RedisHelper.getInstance().get().hgetAll(RedisConst.REDIS_KEY_EDUCA_SYMBOL_TIME_LOCK).entrySet()) {
            String symbol = entry.getKey();
            String timelock = entry.getValue();
            long timeLockLong = Long.parseLong(timelock);
            LOG.info("{} {} {}", symbol, new Date(timeLockLong), new Date(calTimeLock(timeLockLong)));
        }
    }


    private static void writeAllSymbol2Redis() throws IOException {
        List<String> lines = FileUtils.readLines(new File("target/allsymbols.txt"));
        for (String sym : lines) {
            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS, sym, sym);
        }
    }

    private static void traceSuccessBySymbol() {
        List<String> lines = new ArrayList<>();
        List<OrderTargetInfo> allOrderDone = getAllOrderDone();
        Map<String, Integer> sym2Success = new HashMap<>();
        for (OrderTargetInfo order : allOrderDone) {
            Integer successCounter = sym2Success.get(order.symbol);
            if (successCounter == null) {
                successCounter = 0;
            }
            successCounter++;
            sym2Success.put(order.symbol, successCounter);
        }
        for (Map.Entry<String, Integer> entry : sym2Success.entrySet()) {
            String symbol = entry.getKey();
            Integer counter = entry.getValue();
            lines.add(symbol + "," + counter);
        }
        try {
            FileUtils.writeLines(new File("target/symbol2success.csv"), lines);
        } catch (IOException ex) {
            java.util.logging.Logger.getLogger(Test.class.getName()).log(Level.SEVERE, null, ex);
        }

    }

    public static List<OrderTargetInfo> getAllOrderDone() {
        List<OrderTargetInfo> hashMap = new ArrayList<>();
        try {
            List<String> lines = FileUtils.readLines(new File(FILE_STORAGE_ORDER_DONE));
            for (String line : lines) {
                try {
                    OrderTargetInfo order = Utils.gson.fromJson(line, OrderTargetInfo.class);
                    if (order != null) {
                        hashMap.add(order);
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return hashMap;

    }

    private void threadListenVolume() {
        SubscriptionClient client = SubscriptionClient.create();
        SubscriptionErrorHandler errorHandler = (BinanceApiException exception) -> {
        };
        client.subscribeAllTickerEvent(((event) -> {
            for (SymbolTickerEvent e : event) {
                LOG.info("{} -> {}", e.getSymbol(), e);
            }
        }), errorHandler);
    }

    private static void extractRateChangeInMonth(long time) {

        Collection<? extends String> symbols = TickerFuturesHelper.getAllSymbol();
        TreeMap<Double, String> rateChangeInMonth = new TreeMap<>();
        for (String symbol : symbols) {

            if (StringUtils.endsWithIgnoreCase(symbol, "usdt")) {
                try {
                    // only get symbol over 2 months
                    double rateChange = getStartTimeAtExchange(symbol);
                    rateChangeInMonth.put(rateChange, symbol);
                } catch (Exception e) {

                }
            }
        }
        for (Map.Entry<Double, String> entry : rateChangeInMonth.entrySet()) {
            Object rate = entry.getKey();
            Object symbol = entry.getValue();
            LOG.info("{} -> {}", symbol, rate);
        }
    }

    private static double getStartTimeAtExchange(String symbol) {

        try {
            List<KlineObjectNumber> allKlines = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_1D);
            Double maxPrice = 0d;
            Double minPrice = 0d;
            if (allKlines.size() > 61) {
                KlineObjectNumber klineFinal = allKlines.get(allKlines.size() - 1);
                for (int i = 1; i < 61; i++) {
                    KlineObjectNumber kline = allKlines.get(allKlines.size() - 1 - i);
                    if (maxPrice < kline.maxPrice) {
                        maxPrice = kline.maxPrice;
                    }
                    if (minPrice == 0 || minPrice > kline.minPrice) {
                        minPrice = kline.minPrice;
                    }
                }
                double change = klineFinal.priceClose - minPrice;
                return change / minPrice;
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
        return 0;

    }

    public static Set<Double> extractBtcBigChange(List<KlineObjectNumber> btcKlines) {
        Set<Double> results = new HashSet<>();

        for (KlineObjectNumber kline : btcKlines) {
            BreadDetectObject breadData = BreadFunctions.calBreadDataBtc(kline, 0.007);
            if (breadData.orderSide != null
                    && breadData.rateChange > 0.013) {
                results.add(kline.startTime);
                LOG.info("{} {} bread above:{} bread below:{} rateChange:{} totalRate: {}", new Date(kline.startTime.longValue()),
                        breadData.orderSide, breadData.breadAbove, breadData.breadBelow, breadData.rateChange, breadData.totalRate);
            }
        }
        return results;
    }

    private static void detectTopBottomObjectInTicker(String symbol) {
        double rateCheck = 0.008;
        List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_15M);
        List<TrendObject> objects = new ArrayList<>();
        KlineObjectNumber lastTickerCheck = tickers.get(0);
        TrendState state = TrendState.UP;
        for (KlineObjectNumber ticker : tickers) {
            if (state.equals(TrendState.UP)) {
                if (Utils.rateOf2Double(lastTickerCheck.maxPrice, ticker.maxPrice) > rateCheck) {
                    if (lastTickerCheck.maxPrice > ticker.maxPrice) {
                        objects.add(new TrendObject(state, lastTickerCheck));
                    } else {
                        objects.add(new TrendObject(state, ticker));
                    }
                    state = TrendState.DOWN;
                }
            } else {
                if (Utils.rateOf2Double(ticker.minPrice, lastTickerCheck.minPrice) > rateCheck) {
                    if (lastTickerCheck.minPrice < ticker.minPrice) {
                        objects.add(new TrendObject(state, lastTickerCheck));
                    } else {
                        objects.add(new TrendObject(state, ticker));
                    }
                    state = TrendState.UP;
                }
            }
            lastTickerCheck = ticker;
        }
        int counter = 0;
        for (int i = 0; i < objects.size(); i++) {
            counter++;
            if (counter == 30) {
                break;
            }
            TrendObject object = objects.get(objects.size() - 1 - i);
            if (object.status.equals(TrendState.UP)) {
                LOG.info(" {} {} {}", new Date(object.kline.startTime.longValue()), object.status, object.kline.maxPrice);
            } else {
                LOG.info(" {} {} {}", new Date(object.kline.startTime.longValue()), object.status, object.kline.minPrice);
            }
        }
    }

    private static void extractVolume() {
        List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker("CYBERUSDT", Constants.INTERVAL_1D);
        KlineObjectNumber lastTicker = tickers.get(0);
        for (KlineObjectNumber ticker : tickers) {
            LOG.info("Date {} Volume: {} , rate: {}", new Date(ticker.startTime.longValue()),
                    ticker.totalUsdt, Utils.rateOf2Double(ticker.totalUsdt, lastTicker.totalUsdt));
            lastTicker = ticker;

        }
    }

    private static void testListenPrice() {
        SubscriptionClient client = SubscriptionClient.create();

        SubscriptionErrorHandler errorHandler = (BinanceApiException exception) -> {

//            LOG.info("Error listen -> create new listener: {}", symbol);
//            startThreadListenPriceAndUpdatePosition(symbol);
//            exception.printStackTrace();
        };
        client.subscribeAllTickerEvent(((event) -> {
            printEventAllTicker(event);
        }), errorHandler);
    }

    private static void printEventAllTicker(List<SymbolTickerEvent> events) {
        StringBuilder builder = new StringBuilder();
        builder.setLength(0);
        Map<String, Double> sym2Price = new HashMap<>();
        for (SymbolTickerEvent event : events) {
            sym2Price.put(event.getSymbol(), event.getLastPrice().doubleValue());
        }
        for (Map.Entry<String, Double> entry : sym2Price.entrySet()) {
            Object sym = entry.getKey();
            Object price = entry.getValue();
            builder.append(sym).append(" -> ").append(price).append("\t");
        }
        LOG.info("Update price: {} {}", sym2Price.size(), builder.toString());
    }

    private static void process(CandlestickEvent event) {

        try {
            Double rateBread = 0.005;
            Double rate2Trade = 0.01;
            Double beardAbove = 0d;
            Double beardBelow = 0d;
            Double rateChange = null;

            if (event.getClose().doubleValue() > event.getOpen().doubleValue()) {
                beardAbove = event.getHigh().doubleValue() - event.getClose().doubleValue();
                beardBelow = event.getOpen().doubleValue() - event.getLow().doubleValue();
                rateChange = Utils.rateOf2Double(event.getClose().doubleValue(), event.getOpen().doubleValue());
            } else {
                beardAbove = event.getHigh().doubleValue() - event.getOpen().doubleValue();
                beardBelow = event.getClose().doubleValue() - event.getLow().doubleValue();
                rateChange = Utils.rateOf2Double(event.getOpen().doubleValue(), event.getClose().doubleValue());
            }
            double rateChangeAbove = beardAbove / event.getLow().doubleValue();
            double rateChangeBelow = beardBelow / event.getLow().doubleValue();
            OrderSide side = null;
            if (rateChangeAbove > rateBread) {
//                    LOG.info("bread: {} {}", rateChangeAbove, new Date(kline.startTime.longValue()));
                side = OrderSide.SELL;
            } else {
                if (rateChangeBelow > rateBread) {
                    side = OrderSide.BUY;
//                        LOG.info("bread: {} {}", rateChangeBelow, new Date(kline.startTime.longValue()));
                }
            }
//            LOG.info("{} {} bread above:{} bread below:{} rateChange:{}", new Date(event.getStartTime()), side, rateChangeAbove, rateChangeBelow, rateChange);
            if (side != null && rateChange >= rate2Trade) {
                LOG.info("{} {} bread above:{} bread below:{} rateChange:{}", new Date(event.getStartTime()), side, rateChangeAbove, rateChangeBelow, rateChange);
            }

        } catch (Exception e) {
        }

    }

    private void processOrderNewMarket(String symbol) {
        try {
            LOG.info("Processing {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
            Thread.sleep(10 * Utils.TIME_SECOND);
        } catch (Exception e) {
        }
        symbol2Processing.remove(symbol);
    }

}
