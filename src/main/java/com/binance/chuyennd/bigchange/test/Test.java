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

import com.aerospike.client.AerospikeClient;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.trading.BinanceOrderTradingManager;
import com.binance.chuyennd.trading.OrderTargetInfo;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
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


    private final ConcurrentHashMap<String, Long> symbol2Processing = new ConcurrentHashMap<>();

    public static void main(String[] args) throws Exception {
//        testProduction();
//        testAIDATA();

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
//        try (AerospikeClient client = new AerospikeClient("103.157.218.242", 3222)) {
//            client.truncate(null, Configs.AEROSPIKE_NAMESPACE, "kline_1m_opt", null);
//            System.out.println("✅ Đã dọn sạch set kline_1m_opt trên .242");
//        } catch (Exception e) { e.printStackTrace(); }

        Long startTime = Utils.sdfFile.parse("20210102").getTime() + 7 * Utils.TIME_HOUR;
        TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManagerAerospikeFloatSim.readDataFromAerospike1M(startTime);
        LOG.info("time2Tickers size: {}", time2Tickers.size());
//        LOG.info("First key: {} time:{} size: {}",time2Tickers.firstKey(), Utils.normalizeDateYYYYMMDDHHmm(time2Tickers.firstKey()),
//                time2Tickers.firstEntry().getValue().size());
//        Utils.writePid2File();
//        while (true) {
//            if (Utils.getCurrentSecond() == 0) {
//                Utils.reset("Reset by time: " + Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
//            }
//            Thread.sleep(1000);
//        }
//        testWS();
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

    private static void testAIDATA() throws ParseException {
        Long startTime = Utils.sdfFile.parse("20251217").getTime() + 7 * Utils.TIME_HOUR;


        TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
        for (int i = 0; i < 10; i++) {
            time2Tickers = DataManagerAerospikeFloatSim.readDataFromAerospike1M(startTime);
            LOG.info("{} {} {}", Utils.normalizeDateYYYYMMDDHHmm(startTime), time2Tickers.size(), time2Tickers.firstEntry().getValue().get("BTCDOMUSDT"));
            startTime += Utils.TIME_DAY;
        }
    }

    private static void testWS() {
        System.out.println(1755820800000L - Utils.TIME_DAY);
//        String timeLastCheck = RedisHelper.getInstance().get().get(RedisConst.REDIS_KEY_LAST_TIME_CHECK_MARKET);
//        if (StringUtils.isNotEmpty(timeLastCheck)) {
//            long time = Long.parseLong(timeLastCheck);
//            if (System.currentTimeMillis() - time > 15 * Utils.TIME_MINUTE) {
//                LOG.info("Reset by last check market over 15m: " + Utils.normalizeDateYYYYMMDDHHmm(time));
//            } else {
//                LOG.info("Not reset by last check market over 15m: " + Utils.normalizeDateYYYYMMDDHHmm(time));
//            }
//        }
//        SubscriptionClient client = SubscriptionClient.create();
//        // Giả sử client có phương thức subscribeMarkPriceStreamForAllSymbols
//// update price
//        client.subscribeAllTickerEvent(((events) -> {
//            for (SymbolTickerEvent event : events) {
//               LOG.info(Utils.toJson(event));
//            }
//        }), null);
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
        List<List<Integer>> sublists2 = Utils.subListPartInput(numberList, 3);

        System.out.println("Danh sách đã xáo trộn (10 số đầu): " + numberList.subList(0, 10));
        System.out.println("Sublist đầu tiên (Lần 2): " + sublists2.get(0));
        System.out.println("Sublist thứ hai (Lần 2): " + sublists2.get(1));

        System.out.println("-------------------------------------------------");

        // 4. Xác minh
        boolean isDifferent = !sublists1.get(0).equals(sublists2.get(0));
        System.out.println("So sánh sublist đầu tiên của Lần 1 và Lần 2:");
        System.out.println("Kết quả có khác nhau không? " + (isDifferent ? "CÓ 👍" : "KHÔNG 👎"));
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

    }

    private static void removeSLRedis() {
        String symbol = "SPELLUSDT";
        String orderJson = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol);
        OrderTargetInfo order = Utils.gson.fromJson(orderJson, OrderTargetInfo.class);
        order.priceTP = null;
        order.priceSL = null;
        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol, Utils.toJson(order));
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
//        test.initSLFirst();
        test.processDynamicTP_SL();


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


    private static void createAOrderTest() {
        String symbol = "BNBUSDT";
        MarketLevelChange levelChange = MarketLevelChange.SMALL_DOWN;
        Double budget = 2d;
        List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_1M);
        KlineObjectNumber ticker = tickers.get(tickers.size() - 1);
        Double quantity = Utils.calQuantity(budget, Configs.LEVERAGE_ORDER, ticker.priceClose, symbol);
        OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, ticker.priceClose,
                null, quantity, Configs.LEVERAGE_ORDER, symbol, ticker.startTime.longValue(),
                ticker.startTime.longValue(), OrderSide.BUY, Constants.TRADING_TYPE_VOLUME_MINI);
        orderTrade.marketLevel = levelChange;
        LOG.info("Push redis order: {} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()),
                symbol, levelChange, quantity, ticker.priceClose);
        RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_BINANCE_TD_ORDER_MANAGER_QUEUE, Utils.toJson(orderTrade));
    }


    private static void changeLeverage() {
        Set<String> allSymbols = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
        Integer counter = 0;
        int leverage = Configs.LEVERAGE_ORDER;
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

}
