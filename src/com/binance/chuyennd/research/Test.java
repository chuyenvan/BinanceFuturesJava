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
package com.binance.chuyennd.research;

import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TrendObject;
import com.binance.chuyennd.object.TrendState;
import com.binance.chuyennd.position.manager.PositionHelper;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.signal.tradingview.SingalTWSimulator;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.SubscriptionClient;
import com.binance.client.SubscriptionErrorHandler;
import com.binance.client.constant.Constants;
import com.binance.client.exception.BinanceApiException;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.event.CandlestickEvent;
import com.binance.client.model.event.SymbolTickerEvent;
import com.binance.client.model.trade.Order;
import com.binance.chuyennd.trading.OrderTargetInfo;
import com.binance.chuyennd.trading.OrderTargetInfoTest;
import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.text.ParseException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import static jdk.internal.org.jline.utils.Colors.s;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class Test {

    public static final Logger LOG = LoggerFactory.getLogger(Test.class);
    private static Object rateChangeInMonth;

    public static void main(String[] args) throws ParseException, InterruptedException, IOException {
//        String symbol = "TWTUSDT";
//        OrderTargetInfo order = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, symbol),
//                OrderTargetInfo.class);
//        System.out.println(Utils.toJson(order));
//        System.out.println(RedisHelper.getInstance().get().llen(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER));
        long currentTime = System.currentTimeMillis();
        System.out.println(Utils.getCurrentMinute()%10);
        System.out.println(new Date(calTimeLock(currentTime)));
//        Double total = 4800.0;
//        long today = System.currentTimeMillis();
//        for (int i = 0; i < 7; i++) {
//            for (int j = 0; j < 7; j++) {
//                today += Utils.TIME_DAY;
//                Double inc = total * 0.08;
//                total += inc;
//                Double budget = 0.42 * total / 100;
//                LOG.info("{} {} {} -> {}", Utils.normalizeDateYYYYMMDD(today), total.longValue(), inc.longValue(), budget.longValue());
//            }
//        }
//        System.out.println(total.longValue());
//        Utils.sendSms2Skype("Check Signal API");
//        List<Order> orders = ClientSingleton.getInstance().syncRequestClient.getOpenOrders("SKLUSDT");
//        for (Order order : orders) {
//            LOG.info("{} {} {}", order.getSide(), order.getPrice(), Utils.sdfFileHour.format(new Date(order.getUpdateTime())));
//        }
//        System.out.println(new Date(TickerMongoHelper.getInstance().getFirstHourTickerBySymbol("ZECUSDT")));
//        System.out.println(new Date(TickerMongoHelper.getInstance().getLastHourTickerBySymbol("ZECUSDT")));
//        MongoCursor<Document> docs = TickerMongoHelper.getInstance().getAllTickerBySymbol("ZECUSDT");
//        while (TickerMongoHelper.getInstance().getAllTickerBySymbol("ZECUSDT").hasNext()) {
//            Document doc = TickerMongoHelper.getInstance().getAllTickerBySymbol("ZECUSDT").next();
//            
//        }
//        System.out.println(new Date(Utils.getHour(System.currentTimeMillis())));
//        System.out.println(Utils.getHour(System.currentTimeMillis()));
//        for (String sym : TickerHelper.getAllSymbol()) {            
//            Long date = TickerHelper.getDateReleseASymbol(sym);
//            LOG.info("{} -> {} {} days", sym, Utils.normalizeDateYYYYMMDDHHmm(date), (System.currentTimeMillis() - date)/Utils.TIME_DAY);
////        }
//        System.out.println((System.currentTimeMillis() - 1567965420000L) * 200 / Utils.TIME_HOUR);
//        System.out.println(calReportRunning());
//new VolumeMiniManager().checkUpdateBalanceAvalible();
//        System.out.println(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER).size());
//        System.out.println(RedisHelper.getInstance().get().del(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER));
//        System.out.println(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER).size());
//System.out.println(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER).size());
//        Map<String, Double> sym2Volume = TickerHelper.getAllVolume24hr();
//        for (Map.Entry<String, Double> entry : sym2Volume.entrySet()) {
//            String sym = entry.getKey();
//            Double volume = entry.getValue();
//            volume = volume / 1000000;
//            if ((volume) >= 50) {
//                LOG.info("{} {}M", sym, volume.longValue());
//            }
//        }
//        System.out.println(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_SYMBOL_TREND, Constants.SYMBOL_PAIR_BTC));
//        List<AccountBalance> balanceInfos = ClientSingleton.getInstance().syncRequestClient.getBalance();
//        for (AccountBalance balanceInfo : balanceInfos) {
//            if (StringUtils.equalsIgnoreCase(balanceInfo.getAsset(), "usdt")) {
//                double balance = balanceInfo.getAvailableBalance().doubleValue();
//                Double budget = 0.4 * balance;
//                Long budgetLong = budget.longValue();
//                Double bugetDouble = budgetLong.doubleValue() / 100;
//                if (bugetDouble * 5 < 7) {
//                    bugetDouble = 1.3;
//                }
//                LOG.info("{}-> {}", balance, bugetDouble);
//            }
//        }
//        printAllOrderDone();
//        printAllOrderRunning();
//        printAllOrderDoneTest();
//        ExchangeInformation data = ClientSingleton.getInstance().syncRequestClient.getExchangeInformation();
//        for (ExchangeInfoEntry symbolData : data.getSymbols()) {
//            LOG.info("{} -> {}", symbolData.getSymbol(), Utils.toJson(symbolData));
//        }
//        KlineObjectNumber ticker = TickerHelper.getTickerByTime("BTCUSDT", Constants.INTERVAL_15M, Utils.sdfFileHour.parse("20240206 12:34").getTime());
//        System.out.println(Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()) + " -> " + Utils.toJson(ticker));
//        BreadDetectObject breadData = BreadFunctions.calBreadDataAlt(ticker, 0.008);
//        System.out.println(Utils.toJson(breadData));
//        System.out.println(RedisHelper.getInstance().get().del(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER));
//        Double  balanceAvalible = ClientSingleton.getInstance().getBalanceAvalible();
//        Integer BUDGET_PER_ORDER = 2 * balanceAvalible.intValue() / 100;
//        System.out.println(BUDGET_PER_ORDER);
//        System.out.println(RedisHelper.getInstance().get().hdel(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, "ASTRUSDT"));
//        System.out.println(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER));
//        for (String symbol : ClientSingleton.getInstance().getAllSymbol()) {
//            try {
//
//                Double entry = ClientSingleton.getInstance().getCurrentPrice(symbol);
//                LOG.info("{} {} {} {}", symbol, entry, Utils.calPriceTarget(entry, OrderSide.SELL, 0.01), Utils.rateOf2Double(entry, Utils.calPriceTarget(entry, OrderSide.SELL, 0.01)));
//                LOG.info("{} {} {} {}", symbol, entry, Utils.calPriceTarget(entry, OrderSide.BUY, 0.01), Utils.rateOf2Double(entry, Utils.calPriceTarget(entry, OrderSide.BUY, 0.01)));
//            } catch (Exception e) {
//            }
//        }
//        Double price = 0.7273;
//        System.out.println(Utils.normalPrice2Api(price));
//        System.out.println(Utils.calPriceTarget(price, OrderSide.BUY, 0.005));
//        System.out.println(OrderHelper.readOrderInfo("ARKUSDT", 1054878866L));
//        String symbol = "1INCHUSDT";
//        List<KlineObjectNumber> tickers = TickerHelper.getTicker(symbol, Constants.INTERVAL_15M);
//        for (KlineObjectNumber ticker : tickers) {
//            LOG.info(" {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), TickerHelper.getSideOfTicer(ticker));
//        }
////
//        testTraceBreadOfSymbol(tickers, symbol);
//        for (KlineObjectNumber ticker : tickers) {
//            BreadDetectObject breadData = BreadFunctions.calBreadDataAlt(ticker, 0.009);
//            if (breadData.orderSide != null && breadData.rateChange >= 0.008) {
//                LOG.info("Bigchange: {} {} bread above:{} bread below:{} rateChange:{}", new Date(ticker.startTime.longValue()), breadData.orderSide,
//                        breadData.breadAbove, breadData.breadBelow, breadData.totalRate);
//                Double priceEntry = ticker.priceClose;
//                Double priceTarget = getPriceTarget(priceEntry, breadData.orderSide, 0.004);
//                Double quantity = Double.valueOf(Utils.normalQuantity2Api(5 * 5 / priceEntry));
//                OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, ticker.priceClose,
//                        priceTarget, quantity, 5, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(),
//                        breadData.orderSide);
//                LOG.info("{}", Utils.toJson(orderTrade));
//            }
//        }
//        testUserDataStream();
//        Double priceEntry = 0.03108;
//        Double priceTarget = Utils.calPriceTarget(priceEntry, OrderSide.BUY, 0.004);
//        System.out.println(priceTarget);
//        System.out.println(Utils.rateOf2Double(priceTarget, priceEntry));
//        priceTarget = Utils.calPriceTarget(priceEntry, OrderSide.SELL, 0.004);
//        System.out.println(priceTarget);
//        System.out.println(Utils.rateOf2Double(priceTarget, priceEntry));
//        Double quantity = Double.valueOf(Utils.normalQuantity2Api(5 * 4 / priceEntry));
//        System.out.println(quantity);
        //        while (true) {
        //            Thread.sleep(Utils.TIME_SECOND);
        //            if (isTimeRun()) {
        //                System.out.println("RUN:  " + new Date());
        //            }
        //        }
        //        new Test().threadListenVolume();
        //        System.out.println(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER));
        //        System.out.println(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_BTCBIGCHANGETD_SYMBOLS4TRADE));
        //        System.out.println(PositionHelper.getPositionBySymbol("LTCUSDT"));
        //        String timeStr = "20231016";
        //        System.out.println(Utils.sdfFile.parse(timeStr).getTime());
        //        extractRateChangeInMonth(Utils.sdfFile.parse(timeStr).getTime());
        //        System.out.println(RedisHelper.getInstance().readAllId("k12:product:user:profile:info.1"));
        //        SubscriptionClient client = SubscriptionClient.create();
        //        client.subscribeCandlestickEvent("btcusdt", CandlestickInterval.ONE_MINUTE, ((event) -> {
        //            Long startTime = System.currentTimeMillis();
        //            process(event);
        //            Long endTime = System.currentTimeMillis();
        //            LOG.info("{} {}", startTime - event.getEventTime(), endTime - startTime);
        //           
        //        }), null);
        //        testListenPrice();
        //        System.out.println(ClientSingleton.getInstance().getBalanceAvalible());
        //        System.out.println(Utils.marginOfPosition(PositionHelper.getPositionBySymbol("BIGTIMEUSDT")));
        //        List<KlineObjectNumber> tickers = TickerHelper.getTicker(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_1M);
        //        for (int i = 0; i < 100; i++) {
        //            System.out.println(TickerHelper.getPriceChange(tickers, i + 1));
        //        }
        //        showStatusOrderDCA();
        //        detectTopBottomObjectInTicker("BTCUSDT");
        //        extractVolume();
    }

    public static int fibonacci(int n) {
        int f0 = 0;
        int f1 = 1;
        int fn = 1;

        if (n < 0) {
            return -1;
        } else if (n == 0 || n == 1) {
            return n;
        } else {
            for (int i = 2; i < n; i++) {
                f0 = f1;
                f1 = fn;
                fn = f0 + f1;
            }
        }
        return fn;
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

    private static void printAllOrderDoneTest() {
        Map<String, Double> sym2Volume = TickerFuturesHelper.getAllVolume24hr();
        ConcurrentHashMap<Long, OrderTargetInfoTest> allOrderDone = (ConcurrentHashMap<Long, OrderTargetInfoTest>) Storage.readObjectFromFile(SingalTWSimulator.FILE_STORAGE_ORDER_DONE);
        Integer counter50M = 0;
        for (Map.Entry<Long, OrderTargetInfoTest> entry : allOrderDone.entrySet()) {
            Long time = entry.getKey();
            OrderTargetInfoTest order = entry.getValue();
            Double volume = sym2Volume.get(order.symbol) / 1000000;
            if (volume < 50) {
                counter50M++;
            }
            try {
//                KlineObjectNumber tickerOrder = TickerHelper.getTickerByTime(order.symbol, Constants.INTERVAL_15M, order.timeStart);
//                Double tickerChange = Utils.rateOf2Double(tickerOrder.maxPrice, tickerOrder.minPrice) * 1000;
//                LOG.info("{}", Utils.toJson(tickerOrder));

//                KlineObjectNumber ticker24hr = TickerHelper.getTickerLast24h(order.symbol, order.timeStart);
//                Double tickerChange = Utils.rateOf2Double(ticker24hr.priceClose, ticker24hr.priceOpen) * 10000;
//                double rate = tickerChange.longValue();
//                KlineObjectNumber tickerDone = TickerHelper.getTickerByTime(order.symbol, Constants.INTERVAL_15M, time);
//                boolean check = false;
//                if (tickerOrder.maxPrice >= order.priceEntry
//                        && tickerOrder.minPrice < order.priceEntry
//                        && tickerDone.maxPrice >= order.priceTP
//                        && tickerDone.minPrice < order.priceTP) {
//                    check = true;
//                }
//                if (volume.longValue() > 200) {
                LOG.info("{} {} {} {} {} {} {} {} {} => {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(order.timeStart), Utils.normalizeDateYYYYMMDDHHmm(time),
                        order.side, order.symbol, order.priceEntry, order.priceTP, order.minPrice, order.maxPrice,
                        order.lastPrice, true, volume.longValue() + "M", "  tickerchange: " + 1 / 100 + "%");
//                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        Double rate50M = counter50M.doubleValue() / allOrderDone.size();
        LOG.info("{} {} {}", counter50M, allOrderDone.size(), rate50M);
    }

    private static void printAllOrderDone() throws IOException {
        Map<String, Double> sym2Volume = TickerFuturesHelper.getAllVolume24hr();
        List<String> lines = FileUtils.readLines(new File("storage/trading/order-volume-success.data"));
        Integer counter50M = 0;
        Map<String, Integer> symbol2Counter = new HashMap<String, Integer>();
        for (String line : lines) {
            OrderTargetInfo order = Utils.gson.fromJson(line, OrderTargetInfo.class);
            Double volume = sym2Volume.get(order.symbol) / 1000000;
            Integer counter = symbol2Counter.get(order.symbol);
            if (counter == null) {
                counter = 0;
            }
            counter++;
            symbol2Counter.put(order.symbol, counter);
            if (volume < 50) {
                counter50M++;
            }
            try {
//                KlineObjectNumber tickerOrder = TickerHelper.getTickerByTime(order.symbol, Constants.INTERVAL_15M, order.timeStart);
//                Double tickerChange = Utils.rateOf2Double(tickerOrder.maxPrice, tickerOrder.minPrice) * 1000;
//                LOG.info("{}", Utils.toJson(tickerOrder));

//                KlineObjectNumber ticker24hr = TickerHelper.getTickerLast24h(order.symbol, order.timeStart);
//                Double tickerChange = Utils.rateOf2Double(ticker24hr.priceClose, ticker24hr.priceOpen) * 10000;
//                double rate = tickerChange.longValue();
//                KlineObjectNumber tickerDone = TickerHelper.getTickerByTime(order.symbol, Constants.INTERVAL_15M, time);
//                boolean check = false;
//                if (tickerOrder.maxPrice >= order.priceEntry
//                        && tickerOrder.minPrice < order.priceEntry
//                        && tickerDone.maxPrice >= order.priceTP
//                        && tickerDone.minPrice < order.priceTP) {
//                    check = true;
//                }
//                if (volume.longValue() > 200) {
                LOG.info("{} {} {} {} {} {} => {} {}", Utils.normalizeDateYYYYMMDDHHmm(order.timeStart), Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate),
                        order.side, order.symbol, order.priceEntry, order.priceTP, volume.longValue() + "M", order.tradingType);
//                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        Double rate50M = counter50M.doubleValue() / lines.size();
        LOG.info("{} {} {}", counter50M, lines.size(), rate50M);
        LOG.info("{}", Utils.toJson(symbol2Counter));
    }

    private static void printAllOrderRunning() {
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER)) {
            OrderTargetInfo order = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, symbol),
                    OrderTargetInfo.class);
            LOG.info("{} {} {}", order.side, order.symbol, order.tradingType);
        }

    }

    public static Double calRateLoss(OrderTargetInfo orderInfo, Double lastPrice) {
        double rate = Utils.rateOf2Double(lastPrice, orderInfo.priceEntry);
        if (orderInfo.side.equals(OrderSide.SELL)) {
            rate = -rate;
        }
        return rate * 7 / 10;
    }

    public static StringBuilder calReportRunning() {
        StringBuilder builder = new StringBuilder();
        Map<String, Double> sym2Volume = TickerFuturesHelper.getAllVolume24hr();
        Map<String, Double> sym2LastPrice = TickerFuturesHelper.getAllLastPrice();
        Long totalLoss = 0l;
        Long totalBuy = 0l;
        Long totalSell = 0l;
        TreeMap<Double, OrderTargetInfo> rate2Order = new TreeMap<>();
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER)) {
            OrderTargetInfo orderInfo = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, symbol),
                    OrderTargetInfo.class);
            Double rateLoss = calRateLoss(orderInfo, sym2LastPrice.get(orderInfo.symbol)) * 10000;
            rate2Order.put(rateLoss, orderInfo);
        }
        int counterLog = 0;
        for (Map.Entry<Double, OrderTargetInfo> entry : rate2Order.entrySet()) {
            Double rateLoss = entry.getKey();
            OrderTargetInfo orderInfo = entry.getValue();
            Long ratePercent = rateLoss.longValue();
            totalLoss += ratePercent;
            if (orderInfo.side.equals(OrderSide.BUY)) {
                totalBuy += ratePercent;
            } else {
                totalSell += ratePercent;
            }

            if (Math.abs(rateLoss) > 60 && counterLog < 15) {
                counterLog++;

                Double volume24hr = sym2Volume.get(orderInfo.symbol);
                builder.append(Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart)).append(" ")
                        .append(orderInfo.side).append(" ")
                        .append(orderInfo.symbol).append(" ")
                        .append(volume24hr.longValue() / 1000000).append("M ")
                        .append(orderInfo.priceEntry).append("->").append(sym2LastPrice.get(orderInfo.symbol))
                        .append(" ").append(ratePercent.doubleValue() / 100).append("$")
                        .append("\n");
            }
        }

        builder.append("Total: ").append(totalLoss.doubleValue() / 100).append("%");
        builder.append(" Buy: ").append(totalBuy.doubleValue() / 100).append("%");
        builder.append(" Sell: ").append(totalSell.doubleValue() / 100).append("%");
        return builder;
    }

    private static void testDCA() {
        Double priceStart = 1d;
        Double rate = 0.15;
        Double total;
        Double quantity = 10d;

        for (int i = 1; i < 10; i++) {
            rate = 0.15 * fibonacci(i);
            double priceCurrent = priceStart * (1 - rate);
            priceStart = (priceStart + priceCurrent) / 2;
            quantity += quantity;
            total = quantity * priceStart;
            LOG.info("Number dca: {} rate:{}% quantity:{} priceAvg:{} priceCurrent:{} total: {}$",
                    i, rate * 100, quantity, priceStart, priceCurrent, total);
        }
    }

    private static long calTimeLock(long currentTime) {
        return currentTime + (10 - Utils.getCurrentMinute(currentTime) % 10)* Utils.TIME_MINUTE;
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

    private static void detectTopBottomObjectInTicker(String symbol) {
        double rateCheck = 0.0008;
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

    private static void showStatusOrderDCA() {
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_DCA_MANAGER)) {
            Order orderDCA = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_DCA_MANAGER, symbol), Order.class
            );
            Order orderDcaInfo = PositionHelper.getInstance().readOrderInfo(symbol, orderDCA.getOrderId());
            LOG.info("{} {} {}", symbol, orderDcaInfo.getOrderId(), orderDcaInfo.getStatus());
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

}
