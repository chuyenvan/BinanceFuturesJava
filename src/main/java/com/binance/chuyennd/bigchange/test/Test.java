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

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.trading.BinanceOrderTradingManager;
import com.binance.chuyennd.trading.OrderTargetInfo;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * @author pc
 */
public class Test {

    public static final Logger LOG = LoggerFactory.getLogger(Test.class);


    private final ConcurrentHashMap<String, Long> symbol2Processing = new ConcurrentHashMap<>();

    public static void main(String[] args) throws Exception {
//        testProduction();
//        testAIDATA();
//        long startTime = Utils.sdfFileHour.parse("20250410 22:32").getTime();

//        TreeMap<Long, MarketDataObject> time2MarketData =  DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
//        MarketDataObject marketData = DataManagerAerospikeFloatSim.getMarketDataAtTime(startTime);
//        System.out.println(Utils.toJson(marketData));
//        Float minRate15Min60M = -0.005f;
//        System.out.println(Utils.toJson(DataManagerAerospikeFloatSim.getFundingPredictionAtTime(startTime)));


//        TreeMap<Long, MarketDataObject> time2MarketData = (TreeMap<Long, MarketDataObject>)
//                StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
//        LOG.info("{} {} {}", time2MarketData.size(),
//                Utils.normalizeDateYYYYMMDDHHmm(time2MarketData.firstKey()) + " -> " +
//                        Utils.normalizeDateYYYYMMDDHHmm(time2MarketData.lastKey()));
//        checkRateProduction();
//        changeLeverage();
//        deleteAllSLAtRedis();
//        StorageSnappy.writeObject2File("target/test.data", new HashMap<>());
//        checkSellSignal();
//        checkTickerProduct();
//                removeSLRedis();
//        difProductionWithTest();

        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO)) {
            String orderJson = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol);
            OrderTargetInfo order = Utils.gson.fromJson(orderJson, OrderTargetInfo.class);
            if (order.priceSL != null) {
                order.priceSL = null;
                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol, Utils.toJson(order));
                LOG.info("{} --> {}", order.symbol, Utils.toJson(order));
            }
        }


//        testsublist();
//        try (AerospikeClient client = new AerospikeClient("103.157.218.242", 3222)) {
//            client.truncate(null, Configs.AEROSPIKE_NAMESPACE, "kline_1m_opt", null);
//            System.out.println("✅ Đã dọn sạch set kline_1m_opt trên .242");
//        } catch (Exception e) { e.printStackTrace(); }

//        Long startTime = Utils.sdfFile.parse("20210102").getTime() + 7 * Utils.TIME_HOUR;
//        TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManagerAerospikeFloatSim.readDataFromAerospike1M(startTime);
//        LOG.info("time2Tickers size: {}", time2Tickers.size());


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

private static void testProduction() {

//        createAOrderTest();
//        System.out.println(FuturesRules.getInstance().getSymsLocked());
//        System.out.println(Utils.getYear(System.currentTimeMillis()));
//        new BinanceOrderTradingManager().processManagerPosition();
//        List<PositionRisk> positions = BinanceFuturesClientSingleton.getInstance().getAllPositionInfos();
//        for (int i = 1; i < 10; i++) {
//            float rateLoss = 0.01 * i;
//            float rateMin2MoveSl = 0.01;
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
        test.initSLFirst();
//    test.processDynamicTP_SL();


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
