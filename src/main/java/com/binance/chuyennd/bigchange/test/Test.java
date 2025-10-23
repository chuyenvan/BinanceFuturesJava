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

import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.grid.SimpleMovingAverage4hManager;
import com.binance.chuyennd.grid.SimpleMovingAverageDayManager;
import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.indicators.MACD;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.MACDEntry;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.RsiEntry;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.trading.BinanceOrderTradingManager;
import com.binance.chuyennd.trading.BudgetManager;
import com.binance.chuyennd.trading.OrderTargetInfo;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.SubscriptionClient;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.CandlestickInterval;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.event.CandlestickEvent;
import com.binance.client.model.event.SymbolTickerEvent;
import com.binance.client.model.market.ExchangeInfoEntry;
import com.google.gson.internal.LinkedTreeMap;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.math.BigDecimal;
import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

/**
 * @author pc
 */
public class Test {

    public static final Logger LOG = LoggerFactory.getLogger(Test.class);

    public static final String FILE_STORAGE_ORDER_DONE = "target/OrderTestDone.data";

    private final ConcurrentHashMap<String, Long> symbol2Processing = new ConcurrentHashMap<>();

    public static void main(String[] args) throws Exception {
//        testProduction();
//        checkRateProduction();
//        changeLeverage();
//        deleteAllSLAtRedis();
//        StorageSnappy.writeObject2File("target/test.data", new HashMap<>());
//        checkSellSignal();
//        checkTickerProduct();
//                removeSLRedis();
//        difProductionWithTest();
//        System.out.println(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO).size());

//        testsublist();
        testWS();
//        System.out.println(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS));
//        findsymbolErrorStreming();
//        testShuffle();
//        System.out.println(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS).size());
        //        difTestBetween2File();
//
//        TreeMap<Long, OrderTargetInfoTest> allOrderDone = (TreeMap<Long, OrderTargetInfoTest>) Storage.readObjectFromFile("target/OrderTestDone.data");
//        int counter = 0;
//        for (OrderTargetInfoTest order : allOrderDone.values()) {
//            if (Utils.normalizeDateYYYYMMDDHHmm(order.timeStart).contains("202101")) {
//                LOG.info("{} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(order.timeStart), order.symbol,
//                        order.marketData.rateDownAvg, order.marketData.rateUpAvg);
//                counter++;
//                if (counter > 100) {
//                    break;
//                }
//            }
//        }
//        new TickerManager().startUpdateFundingFee();
//        Long timeStart = Utils.sdfFile.parse(Configs.TIME_RUN).getTime();
//        new TickerManager().updateFundingFeeBySymbol("HIPPOUSDT", timeStart);


    }

    private static void testWS() {
        SubscriptionClient client = SubscriptionClient.create();
        // Giả sử client có phương thức subscribeMarkPriceStreamForAllSymbols
// update price
        client.subscribeAllTickerEvent(((events) -> {
            for (SymbolTickerEvent event : events) {
               LOG.info(Utils.toJson(event));
            }
        }), null);
    }

    private static void testShuffle() {
        // 1. Tạo danh sách 100 số từ 1 tới 100
        List<Integer> numberList = IntStream.rangeClosed(1, 100)
                .boxed()
                .collect(Collectors.toList());

        System.out.println("Danh sách gốc (10 số đầu): " + numberList.subList(0, 10));
        System.out.println("-------------------------------------------------");

        // 2. Chạy lần 1
        System.out.println("--- CHẠY LẦN 1 ---");
        Collections.shuffle(numberList); // Xáo trộn
        List<List<Integer>> sublists1 = Utils.subListPartInput(numberList, 3);

        System.out.println("Danh sách đã xáo trộn (10 số đầu): " + numberList.subList(0, 10));
        System.out.println("Sublist đầu tiên (Lần 1): " + sublists1.get(0));
        System.out.println("Sublist thứ hai (Lần 1): " + sublists1.get(1));

        System.out.println("-------------------------------------------------");

        // 3. Chạy lần 2 (xáo trộn lại chính danh sách đó)
        System.out.println("--- CHẠY LẦN 2 ---");
        Collections.shuffle(numberList); // Xáo trộn một lần nữa
        List<List<Integer>> sublists2 =  Utils.subListPartInput(numberList, 3);

        System.out.println("Danh sách đã xáo trộn (10 số đầu): " + numberList.subList(0, 10));
        System.out.println("Sublist đầu tiên (Lần 2): " + sublists2.get(0));
        System.out.println("Sublist thứ hai (Lần 2): " + sublists2.get(1));

        System.out.println("-------------------------------------------------");

        // 4. Xác minh
        boolean isDifferent = !sublists1.get(0).equals(sublists2.get(0));
        System.out.println("So sánh sublist đầu tiên của Lần 1 và Lần 2:");
        System.out.println("Kết quả có khác nhau không? " + (isDifferent ? "CÓ 👍" : "KHÔNG 👎"));
    }

    private static void findsymbolErrorStreming() {
        // update ticker
        List<String> symbols = new ArrayList<>();
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS)) {
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            symbols.add(symbol.toLowerCase());
        }
        List<List<String>> sublistBase = Utils.subListPartInput(symbols, 3);
        List<List<String>> sublist = Utils.subListPartInput(sublistBase.get(0), 4);
        SubscriptionClient client = SubscriptionClient.create();
        for (List<String> list: sublistBase) {
            client.subscribeAllCandlestickEvent(list, CandlestickInterval.ONE_MINUTE, ((event) -> {
//                LOG.info("Update ticker: {}", Utils.gson.toJson(event));

            }), null);
        }
    }

    private static void testsublist() {
        Set<String> symbolActive = new HashSet<>();
        for (ExchangeInfoEntry symbol : ClientSingleton.getInstance().syncRequestClient.getExchangeInformation().getSymbols()) {
            if (symbol.getStatus().contains("TRADING")) {
                symbolActive.add(symbol.getSymbol());
//                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS, symbol.getSymbol(), symbol.getSymbol());
            }
        }
        System.out.println(symbolActive.size());
        List<String> symbols = new ArrayList<>();
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS)) {
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            if (!symbolActive.contains(symbol.toUpperCase())) {
                LOG.info("symbol not active: {}", symbol);
                RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS, symbol);
            }
        }
//
//        LOG.info("Total: {}", symbols.size());
//        List<List<String>> sublist = Utils.subList(symbols, 170);
//        for (List<String> list : sublist) {
//            for (String symbol: list){
//                if (!symbolActive.contains(symbol.toUpperCase())){
//                    LOG.info("symbol not active: {}", symbol);
//                }
//            }
//            LOG.info("Size: {}", list.size());
//        }
//        sublist = Utils.subListPartInput(symbols, 3);
//        for (List<String> list : sublist) {
//            LOG.info("Size: {}", list.size());
//            for (String symbol: list){
//                if (!symbolActive.contains(symbol.toUpperCase())){
//                    LOG.info("symbol not active: {}", symbol);
//                }
//            }
//        }
    }

    private static void checkTickerProduct() {
        String FILE_TICKER_1M_STORAGE = "storage/tickers/symbol2ticker1Ms";
        ConcurrentHashMap<String, TreeMap<Long, KlineObjectSimple>> symbo2Tickers = (ConcurrentHashMap<String, TreeMap<Long, KlineObjectSimple>>)
                StorageSnappy.readObjectFromFile(FILE_TICKER_1M_STORAGE);
        for (String symbol : symbo2Tickers.keySet()) {
            TreeMap<Long, KlineObjectSimple> tickers = symbo2Tickers.get(symbol);
            LOG.info("{} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(tickers.firstKey()),
                    Utils.normalizeDateYYYYMMDDHHmm(tickers.lastKey()));
        }
    }

    private static void checkSellSignal() throws ParseException {
        long time = Utils.sdfFileHour.parse("20250603 11:00").getTime();
        String symbol = "NEIROETHUSDT";
//        Double priceMin2d = Price4hManager.getInstance().getPriceMinIn2D(symbol, time);
//        Double priceMax2d = Price4hManager.getInstance().getPriceMaxIn2D(symbol, time);
//        Double priceClose = 0.10107;
//        if (priceMax2d != null && Utils.rateOf2Double(priceClose, priceMax2d) < 0
//                && priceMin2d != null && Utils.rateOf2Double(priceClose, priceMin2d) > 0.5) {
//            LOG.info(" {} {}", Utils.rateOf2Double(priceClose, priceMax2d), Utils.rateOf2Double(priceClose, priceMin2d));
//        }
//        LOG.info("{} {}", priceMin2d, priceMax2d);


        Double maDif1d = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
        Double maDif4h = SimpleMovingAverage4hManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
        LOG.info("{} {}", maDif4h, maDif1d);
    }

    private static void removeSLRedis() {
        String symbol = "SPELLUSDT";
        String orderJson = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol);
        OrderTargetInfo order = Utils.gson.fromJson(orderJson, OrderTargetInfo.class);
        order.priceTP = null;
        order.priceSL = null;
        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol, Utils.toJson(order));
    }

    private static void difTestBetween2File() {
        try {
            String file1 = "target/printDone_50.csv";
            String file2 = "target/printDone.csv";
            List<String> lines1 = FileUtils.readLines(new File(file1));
            List<String> lines2 = FileUtils.readLines(new File(file2));
            Map<MarketLevelChange, Map<Long, MarketRateChange>> level2RateMin1 = new HashMap<>();
            Map<Long, MarketRateChange> time2Rate2 = new HashMap<>();
            MarketLevelChange level;
            for (String line : lines1) {
                level = extractLevelInLine(line);
                if (level != null) {
                    Map<Long, MarketRateChange> time2Rate = level2RateMin1.get(level);
                    if (time2Rate == null) {
                        time2Rate = new HashMap<>();
                        level2RateMin1.put(level, time2Rate);
                    }
                    time2Rate.put(extractTimeInLine(line), extractMarketRateInLine(line));
                }
            }
            for (String line : lines2) {
                time2Rate2.put(extractTimeInLine(line), extractMarketRateInLine(line));
            }


            // print by level
            level = MarketLevelChange.BIG_UP;
            Map<Long, MarketRateChange> time2Rate1 = level2RateMin1.get(level);
            MarketRateChange rateMin = null;
            for (Long time : time2Rate1.keySet()) {
                MarketRateChange rate = time2Rate2.get(time);
                if (rate != null) {
                    if (rateMin == null || rateMin.rateUpAvg > rate.rateUpAvg) {
                        rateMin = rate;
                    }
                    LOG.info("{} {} {} {} {}", level, rateMin.rateDownAvg, rateMin.rateUpAvg, rateMin.rateDown15MAvg
                            , Utils.normalizeDateYYYYMMDDHHmm(time));
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static MarketRateChange extractMarketRateInLine(String line) {
        try {
            String[] parts = StringUtils.split(line, ",");
            MarketRateChange rate = new MarketRateChange(Double.parseDouble(parts[18]),
                    Double.parseDouble(parts[20]), Double.parseDouble(parts[19]));
            return rate;
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    private static Long extractTimeInLine(String line) {
        try {
            String[] parts = StringUtils.split(line, ",");
            return Utils.sdfFileHour.parse(parts[6]).getTime();
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    private static MarketLevelChange extractLevelInLine(String line) {
        try {
            String[] parts = StringUtils.split(line, ",");
            return MarketLevelChange.valueOf(parts[9]);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    private static void checkRateProduction() {
        TreeMap<Long, MarketRateChange> time2MarketRateChange = (TreeMap<Long, MarketRateChange>) Storage.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);

        Long lastTime = time2MarketRateChange.lastKey();
        for (int i = 0; i < 100; i++) {
            long time = lastTime - (100 - i) * Utils.TIME_MINUTE;
            MarketRateChange data = time2MarketRateChange.get(time);
            LOG.info("{} {} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time),
                    Utils.formatDouble(data.rateDownAvg * 100, 3),
                    Utils.formatDouble(data.rateUpAvg * 100, 3),
                    Utils.formatDouble(data.rateDown15MAvg * 100, 3));

        }

    }


    private static void testFundingRate() {
//        try {
//            Long time = Utils.sdfFileHour.parse("20210101 07:00").getTime();
//            Set<String> allSymbols = TickerFuturesHelper.getAllSymbol();
//            while (true) {
//                TreeMap<Double, String> funding2Symbol = FundingFeeManager.getInstance().getTopFundingFee(time, allSymbols);
//                if (!funding2Symbol.isEmpty() && funding2Symbol.firstKey() < -0.005) {
//                    LOG.info("{} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), funding2Symbol.firstKey(), funding2Symbol.firstEntry().getValue());
//                }
////                LOG.info("{} {} {}", funding2Symbol.lastKey(), funding2Symbol.lastEntry().getValue());
//                time +=  Utils.TIME_MINUTE;
//                if (time > System.currentTimeMillis()) {
//                    break;
//                }
//            }
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
        try {
            Long time = Utils.sdfFileHour.parse("20250106 10:19").getTime();
            TreeMap<Double, String> funding2Symbol = FundingFeeManager.getInstance().getTopDownFundingFee(
                    Utils.get4Hour(time), TickerFuturesHelper.getAllSymbol());
            LOG.info("{}", funding2Symbol);
            for (Double funding : funding2Symbol.keySet()) {
                if (funding > 0.002) {
                    String symbol = funding2Symbol.lastEntry().getValue();

                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }


    private static void difProductionWithTest() {
        try {
            String dateCheck = "20250420 07:00";
            Long dateCheckL = Utils.sdfFileHour.parse(dateCheck).getTime();
            String folderProduct = "storage/data/rateMax15M/" + Utils.normalizeDateYYYYMMDD(dateCheckL);

            TreeMap<Long, MarketDataObject> time2MarketData =
                    (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);

            for (Long time : time2MarketData.keySet()) {

                if (Utils.getDate(time) == dateCheckL) {
                    TreeMap<Double, String> rate2MaxTest = time2MarketData.get(time).rate2Max;
                    TreeMap<Double, String> rate2MaxProduct = (TreeMap<Double, String>)
                            Storage.readObjectFromFile(folderProduct + "/" + time);
                    LOG.info("{} p:{} t:{}", Utils.normalizeDateYYYYMMDDHHmm(time),
                            MarketBigChangeDetector.calRateChangeAvg(rate2MaxProduct, 50),
                            time2MarketData.get(time).rateDown15MAvg);
                    Map<String, Double> symbol2RatePro = new HashMap<>();
                    for (Map.Entry<Double, String> entry : rate2MaxProduct.entrySet()) {
                        Double key = entry.getKey();
                        String values = entry.getValue();
                        symbol2RatePro.put(values, key);
                    }
                    List<String> lines = new ArrayList<>();
                    for (Map.Entry<Double, String> entry : rate2MaxTest.entrySet()) {
                        Double key = entry.getKey();
                        String symbol = entry.getValue();
                        StringBuilder sb = new StringBuilder();
                        sb.append(symbol).append(",");
                        sb.append(key).append(",");
                        sb.append(symbol2RatePro.get(symbol)).append(",");
                        lines.add(sb.toString());
                    }
                    String fileOutput = "target/" + time + ".csv";
                    LOG.info("output: {}", fileOutput);
                    FileUtils.writeLines(new File(fileOutput), lines);
                }
            }


        } catch (Exception e) {
            e.printStackTrace();
        }
    }


    private static void deleteAllSLAtRedis() {
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO)) {
            String orderJson = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol);
            OrderTargetInfo order = Utils.gson.fromJson(orderJson, OrderTargetInfo.class);
            order.priceSL = null;
            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol, Utils.toJson(order));
        }
    }

    private static void testTimeDetectProduction() throws IOException {
        List<String> lines = FileUtils.readLines(new File("target/full.log"));
        for (String line : lines) {
            if (StringUtils.contains(line, "Check btc revers")) {
                String timeRun = line.split("INFO")[0].trim();
                String timeCheck = line.split("Check btc reverse:")[1].substring(1, 15);
                Integer minuteRun = Integer.parseInt(timeRun.split(":")[1]);
                Integer minuteCheck = Integer.parseInt(timeCheck.split(":")[1]);
                if (minuteRun - minuteCheck == 2) {
                    LOG.info("{} {} {} {}", timeRun, timeCheck, minuteRun, minuteCheck);
//                    break;
                }
            }
        }
    }


    private static void testProduction() {

//        createAOrderTest();
//        System.out.println(FuturesRules.getInstance().getSymsLocked());
//        System.out.println(Utils.getYear(System.currentTimeMillis()));
//        new BinanceOrderTradingManager().processManagerPosition();
//        List<PositionRisk> positions = BinanceFuturesClientSingleton.getInstance().getAllPositionInfos();
//        for (int i = 1; i < 10; i++) {
//            double rateLoss = 0.01 * i;
//            double rateMin2MoveSl = 0.01;
//            LOG.info("{} {} {}", rateLoss, rateMin2MoveSl,
//                    BudgetManagerSimple.getInstance().calRateLossDynamicBuy(rateLoss, rateMin2MoveSl));
//        }
//        System.out.println(FundingFeeManagerProduction.getInstance().fundingBuy.size());
//        FundingFeeManagerProduction.getInstance().getFundingBySymbol("NXPCUSDT");
//        FundingFeeManagerProduction.getInstance().updateListBuySell();
//        System.out.println(FundingFeeManagerProduction.getInstance().fundingBuy.size());

//
        BinanceOrderTradingManager test = new BinanceOrderTradingManager();
        test.updatePositionInfo();
//        test.processDynamicTP_SL();
        test.initSLFirst();
        test.checkSLErrorAtRedis();

        // delete all order not rung at redis
//        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO)) {
//            if (!BudgetManager.getInstance().symbol2Pos.containsKey(symbol)){
//                LOG.info("Delete order at redis of: {}", symbol);
//                RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol);
//            }
//        }
//        PositionRisk pos = BinanceFuturesClientSingleton.getInstance().getPositionInfo("BTCUSDT");
//        test.createSL(pos, 0.04);

//        System.out.println(Utils.toJson(test.getOrderInfo("CRVUSDT")));
////
//        for (PositionRisk position : positions) {
//            if (position.getPositionAmt().doubleValue() != 0) {
//                BudgetManager.getInstance().symbol2Pos.put(position.getSymbol(), position);
//            }
//
//        }
//        DetectEntrySignal2TradeNormal.getDCA(null);
////        for (String symbol:Constants.specialSymbol){

//        String fileName = "target/OrderTestDone.data-5";
////        fileName = "target/" + fileName;
//        TreeMap<Long, OrderTargetInfoTest> allOrderDone = (TreeMap<Long, OrderTargetInfoTest>) Storage.readObjectFromFile(fileName);
//        String statisticLog = TraceData2Test.statisticResult(allOrderDone);
//        LOG.info(statisticLog);
////            ClientSingleton.getInstance().syncRequestClient.changeInitialLeverage(symbol, 8);
////        }

//        Set<String> symbols = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
//        System.out.println(symbols.contains("RAREUSDT"));

//        System.out.println(Utils.toJson(order));
//        for (String symbol : Constants.diedSymbol) {
//            if (symbols.contains(symbol)) {
//                RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS, symbol);
//            }
//        }
//        LOG.info("{} -> {}", symbols.size(), RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS).size());


//        System.out.println(BinanceFuturesClientSingleton.getInstance().getFundingRate("REEFUSDT"));
//                List<PositionRisk> positions = BinanceFuturesClientSingleton.getInstance().getAllPositionInfos();
//        testRateBtc24HrByTime("20240801 03:00");
//        System.out.println(new BinanceOrderTradingManager().getPositionBuyRunning());

//        System.out.println(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS));
        //        String symbol = "REEFUSDT";
//
//        PositionRisk pos = BinanceFuturesClientSingleton.getInstance().getPositionInfo(symbol);
//        String orderJson = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol);
//        OrderTargetInfo order = Utils.gson.fromJson(orderJson, OrderTargetInfo.class);
//        System.out.println(Utils.formatMoney(order.priceSL));

//        new BinanceOrderTradingManager().createSL(pos, order.priceSL);
//        testBigDecimal();
    }

    private static void testBigDecimal() {
        BigDecimal test = new BigDecimal("0.0");
        LOG.info(test.toString());
        BigDecimal testAdd = test.subtract(new BigDecimal("0.01"));
        LOG.info(testAdd.toString());
        LOG.info("{}", testAdd.compareTo(new BigDecimal("0")));
    }

    private static void createAOrderTest() {
        String symbol = "BNBUSDT";
        MarketLevelChange levelChange = MarketLevelChange.SMALL_DOWN;
        Double budget = 2d;
        List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_1M);
        KlineObjectNumber ticker = tickers.get(tickers.size() - 1);
        Double quantity = Utils.calQuantity(budget, BudgetManager.getInstance().getLeverage(), ticker.priceClose, symbol);
        OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, ticker.priceClose,
                null, quantity, BudgetManager.getInstance().getLeverage(), symbol, ticker.startTime.longValue(),
                ticker.startTime.longValue(), OrderSide.BUY, Constants.TRADING_TYPE_VOLUME_MINI);
        orderTrade.marketLevel = levelChange;
        LOG.info("Push redis order: {} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()),
                symbol, levelChange, quantity, ticker.priceClose);
        RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_BINANCE_TD_ORDER_MANAGER_QUEUE, Utils.toJson(orderTrade));
    }

    private static void testTime() {
        while (true) {
            try {
                long time = System.currentTimeMillis();
                long second = (time / Utils.TIME_SECOND) % 60;
                long miniSecond = (time % Utils.TIME_SECOND);
                boolean isTimeCheck = second == 0 && miniSecond < 100;
                boolean isGet = second == 58 && miniSecond < 100;
                LOG.info("{} {} {} {}", second, miniSecond, isGet, isTimeCheck);
                Thread.sleep(Utils.TIME_SECOND / 10);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private static void testData1MProduct() {
        File folder = new File(Configs.FOLDER_TICKER_1M_PRODUCTION);
        File[] dateFolder = folder.listFiles();
        for (File folderDate : dateFolder) {
            for (File file : folderDate.listFiles()) {
                Map<String, KlineObjectNumber> symbol2Tickers = (Map<String, KlineObjectNumber>) Storage.readObjectFromFile(file.getPath());
                int counterGap = 0;
                for (Map.Entry<String, KlineObjectNumber> entry : symbol2Tickers.entrySet()) {
                    String symbol = entry.getKey();
                    KlineObjectNumber ticker = entry.getValue();
                    try {
                        List<KlineObjectNumber> tickerOnlines = TickerFuturesHelper.getTickerWithStartTime(symbol, Constants.INTERVAL_1M, ticker.startTime.longValue());
                        KlineObjectNumber tickerOnline = tickerOnlines.get(0);
                        if (!tickerOnline.priceClose.equals(ticker.priceClose)) {
//                            LOG.info("{} {} {} {} {}", symbol, tickerOnline.priceClose, ticker.priceClose,
//                                    Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), Utils.toJson(ticker));
                            counterGap++;
                        }
//                        if (symbol.equals("CKBUSDT")){
//                        List<KlineObjectNumber> tickerOnlines = TickerFuturesHelper.getTickerWithStartTime(symbol, Constants.INTERVAL_1M, ticker.startTime.longValue());
//                        KlineObjectNumber tickerOnline = tickerOnlines.get(0);
//                            LOG.info("{} {} {} {} {}", symbol, tickerOnline.priceClose, ticker.priceClose,
//                                    Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), Utils.toJson(ticker));
//                        }
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
                LOG.info("{} {}/{}", Utils.normalizeDateYYYYMMDDHHmm(Long.parseLong(file.getName())), counterGap, symbol2Tickers.size());
            }
        }
    }

    private static void testRateBtc24HrByTime(String s) {
        try {
            long time = Utils.sdfFileHour.parse(s).getTime();
            List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_15M);
            List<KlineObjectNumber> btcTickers = new ArrayList<>();
            for (KlineObjectNumber ticker : tickers) {
                if (ticker.startTime.longValue() <= time) {
                    btcTickers.add(ticker);
                }
            }
            KlineObjectNumber btcStatistic24h = null;
            KlineObjectNumber lastBtcTicker = null;
            if (btcTickers != null) {
                btcStatistic24h = TickerFuturesHelper.extractKlineByNumberTicker(btcTickers, btcTickers.size() - 1, 96, 8);
                lastBtcTicker = btcTickers.get(btcTickers.size() - 1);
            }
            Double rateBtc24h = Utils.rateOf2Double(btcStatistic24h.minPrice, lastBtcTicker.minPrice);
            LOG.info("{} {} {}", btcStatistic24h.minPrice, lastBtcTicker.minPrice, rateBtc24h);
        } catch (Exception e) {
            e.printStackTrace();
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
        Set<String> allSymbols = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
        Integer counter = 0;
        int leverage = BudgetManagerSimple.getInstance().getLeverage();
        for (String symbol : allSymbols) {
            try {
//                if (StringUtils.equals(symbol, "AKTUSDT")) {
//                    counter = 0;
//                }
                if (counter != null) {
                    counter++;
                    LOG.info("Set leverage {} {} {}", symbol, leverage, counter);
                    ClientSingleton.getInstance().syncRequestClient.changeInitialLeverage(symbol, leverage);
                    Thread.sleep(300);
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
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
