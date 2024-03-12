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

import com.binance.chuyennd.client.BinanceFuturesClientSingleton;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.client.OrderHelper;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.mongo.TickerMongoHelper;
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
import com.binance.chuyennd.utils.Configs;
import com.mongodb.client.MongoCursor;
import java.io.File;
import java.io.IOException;
import java.text.ParseException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.logging.Level;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang.StringUtils;
import org.bson.Document;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class Test {

    public static final Logger LOG = LoggerFactory.getLogger(Test.class);
    public static Double balanceStart = 4100.0;
    public static Double rateProfit = 0.05;
    public static long timeStartRun = 1709683200000L;

    public static Double RATE_TARGET_VOLUME_MINI = Configs.getDouble("RATE_TARGET_VOLUME_MINI");
    public static Double RATE_TARGET_SIGNAL = Configs.getDouble("RATE_TARGET_SIGNAL");
    public static Double MAX_CAPITAL_RATE = Configs.getDouble("MAX_CAPITAL_RATE");
    public static final String FILE_STORAGE_ORDER_DONE = "storage/trading/order-volume-success.data";

    public ExecutorService executorServiceOrderNew = Executors.newFixedThreadPool(Configs.getInt("NUMBER_THREAD_ORDER_MANAGER"));
    private final ConcurrentHashMap<String, Long> symbol2Processing = new ConcurrentHashMap<>();

    public static void main(String[] args) throws ParseException, InterruptedException, IOException {
//        testRateProfit();

//        printAllOrderOverBudget(8.0);
//        System.out.println(SymbolTradingManager.getInstance().getAllSymbol2TradingSignal());
//        System.out.println(Utils.sdfFile.parse("20240305").getTime());
//       Order orderInfo = OrderHelper.readOrderInfo("RSRUSDT", 633327755582725248L);
        System.out.println(BinanceFuturesClientSingleton.getInstance().readOrder("RSRUSDT", "android_gpgfpyhkgVGKcdrRrmSD"));
//        List<Order> orderOpen = BinanceFuturesClientSingleton.getInstance().getOpenOrders("RSRUSDT");
//        for (Order order : orderOpen) {
//            System.out.println(Utils.toJson(order));
////            if (order.getOrderId() == 633327755571642112L) {
////                BinanceFuturesClientSingleton.getInstance().cancelOrder("RSRUSDT", order.getClientOrderId());
////            }
//        }
//        new BinanceOrderTradingManager().recheckOrderTP("RSRUSDT");
//        traceSuccessBySymbol();
//        new BinanceOrderTradingManager().();
//        testDCA();
//writeAllSymbol2Redis();
//        checkPriceMax();
//        checkTimeLock();
//        System.out.println(getTargetBalance() + " -> " + getTarget());
//        System.out.println(BudgetManager.getInstance().getBudget());
//        System.out.println(Utils.toJson(
//                BinanceFuturesClientSingleton.getInstance().getAccountUMInfo()));
//        System.out.println(RedisHelper.getInstance().get().llen(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER_QUEUE));
//        System.out.println(new Date(1709571600000L + Utils.TIME_DAY + 7 * Utils.TIME_HOUR).getTime());
//        System.out.println(total * 4100);
//        System.out.println(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS));
//System.out.println(new BinanceOrderTradingManager().callRateDump2Die());
//        System.out.println(new BudgetManager().getInvesting());
//        Utils.sendSms2Telegram("<b style=\"color:blue\">foo</b>");
//        Utils.sendSms2Telegram("<b>This is a paragraph.</b>");
        //        Utils.sendSms2Skype("Check Signal API");
        //        System.out.println(calReportRunning());
        //        printAllOrderDone();
        //        printAllOrderRunning();
        //        printAllOrderDoneTest();
        //        System.out.println(RedisHelper.getInstance().get().hdel(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, "ASTRUSDT"));
        //        System.out.println(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER));
        //        testTraceBreadOfSymbol(tickers, symbol);
        //        testUserDataStream();
        //        new Test().threadListenVolume();
        //        showStatusOrderDCA();
        //        detectTopBottomObjectInTicker("BTCUSDT");
        //        extractVolume();
    }

    private void testLock() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadListenQueueOrder2Manager");
            LOG.info("Start thread ThreadListenQueueOrder2Manager!");
            while (true) {
                List<String> data;
                try {
                    data = RedisHelper.getInstance().get().blpop(0, RedisConst.REDIS_KEY_EDUCA_TEST);
                    String symbol = data.get(1);
                    try {

                        if (!symbol2Processing.containsKey(symbol)) {
                            symbol2Processing.put(symbol, System.currentTimeMillis());
                            executorServiceOrderNew.execute(() -> processOrderNewMarket(symbol));

                        } else {
                            LOG.info("{} is lock because processing! {}", symbol, symbol2Processing.size());
                        }
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadListenQueuePosition2Manager {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    public static int fibonacci(int n) {
        int f0 = 0;
        int f1 = 1;
        int fn = 1;

        if (n < 0) {
            return -1;
        } else if (n == 0 || n == 1) {
            return 1;
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

    private static void printAllOrderOverBudget(Double budget) {
        Set<String> symbols = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER);
        LOG.info("Have {} orders running.", symbols.size());
        for (String symbol : symbols) {
            OrderTargetInfo order = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, symbol),
                    OrderTargetInfo.class);
            Double budgetOfOrder = order.quantity * order.priceEntry / order.leverage;
//            if (budgetOfOrder > budget
//                    || order.symbol.equalsIgnoreCase(/"mkrusdt")) {
            LOG.info("{} -> {}", order.symbol, budgetOfOrder.longValue());
//            }
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

    private static void testRateProfit() throws ParseException {
        Double total = balanceStart;
        long timeStart = timeStartRun;
        for (int j = 1; j < 1100; j++) {
            String prefix = "";
            if (j % 15 == 0) {
                prefix = "-------------------";
            }
            timeStart += Utils.TIME_DAY;
            Double inc = total * rateProfit;
            total += inc;
            Double budget = 0.15 * total / 10;
            budget = budget.longValue() / 10.0;
            LOG.info("{} {} {} {} -> {}", prefix,
                    Utils.normalizeDateYYYYMMDDHHmm(timeStart), total.longValue(), inc.longValue(), budget);
            if (total > 500000) {
                break;
            }
        }

    }

    private static Double getTargetBalance() throws ParseException {
        Double total = 1400.0;
        long timeStart = Utils.sdfFile.parse("20240306").getTime();
        Long numberDay = (System.currentTimeMillis() - timeStart) / Utils.TIME_DAY;
        for (int i = 0; i < numberDay + 1; i++) {
            Double inc = total * 0.02;
            total += inc;
        }
        return total;
    }

    private static Double getTarget() throws ParseException {
        Double total = 1400.0;
        long timeStart = Utils.sdfFile.parse("20240306").getTime();
        Long numberDay = (System.currentTimeMillis() - timeStart) / Utils.TIME_DAY;
        for (int i = 0; i < numberDay; i++) {
            Double inc = total * 0.02;
            total += inc;
        }
        return total / 10;
    }

    private static void checkPriceMax() {
        Set<String> symbols = TickerMongoHelper.getInstance().getAllSymbol();
        try {
            FileUtils.writeLines(new File("target/allsymbols.txt"), symbols);
        } catch (IOException ex) {
            java.util.logging.Logger.getLogger(Test.class.getName()).log(Level.SEVERE, null, ex);
        }
        for (String symbol : symbols) {
            MongoCursor<Document> docs = TickerMongoHelper.getInstance().getAllTickerBySymbol(symbol);
            List<Document> docsSorted = new ArrayList<>();
            Double priceMax = 0.0;
            Double priceMin = 0.0;
            while (docs.hasNext()) {
                Document doc = docs.next();
                docsSorted.add(doc);
            }
            for (int i = 0; i < docsSorted.size(); i++) {
                Document doc = docsSorted.get(docsSorted.size() - i - 1);
                try {
                    LOG.info("{} -> {}", symbol, new Date(doc.getLong("hour")));
                } catch (Exception e) {
                    e.printStackTrace();
                }

            }
            break;
        }
        System.out.println(symbols.size());

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

    private void processOrderNewMarket(String symbol) {
        try {
            LOG.info("Processing {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
            Thread.sleep(10 * Utils.TIME_SECOND);
        } catch (Exception e) {
        }
        symbol2Processing.remove(symbol);
    }

}
