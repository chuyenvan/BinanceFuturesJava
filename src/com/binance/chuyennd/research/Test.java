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

import com.binance.chuyennd.funcs.ClientSingleton;
import com.binance.chuyennd.funcs.TickerHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TickerStatistics;
import com.binance.chuyennd.object.TrendObject;
import com.binance.chuyennd.object.TrendObjectDetail;
import com.binance.chuyennd.object.TrendState;
import com.binance.chuyennd.position.manager.PositionHelper;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.SubscriptionClient;
import com.binance.client.SubscriptionErrorHandler;
import com.binance.client.constant.Constants;
import com.binance.client.exception.BinanceApiException;
import com.binance.client.model.enums.CandlestickInterval;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.event.CandlestickEvent;
import com.binance.client.model.event.SymbolTickerEvent;
import com.binance.client.model.market.ExchangeInfoEntry;
import com.binance.client.model.market.ExchangeInformation;
import com.binance.client.model.trade.Order;
import java.text.ParseException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.logging.Level;
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

    public static void main(String[] args) throws ParseException, InterruptedException {

//        ExchangeInformation data = ClientSingleton.getInstance().syncRequestClient.getExchangeInformation();
//        for (ExchangeInfoEntry symbolData : data.getSymbols()) {
//            LOG.info("{} -> {}", symbolData.getSymbol(), symbolData.getQuotePrecision());
//        }
        Integer date = Integer.valueOf(Utils.normalizeDateYYYYMMDD(1704436975000L));
        Integer today = Integer.parseInt(Utils.getToDayFileName());
        boolean eq = false;
        if (date == Integer.parseInt(Utils.getToDayFileName())) {
            eq = true;
        }
        LOG.info("{} {} {}", today, date, eq);
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

        Collection<? extends String> symbols = TickerHelper.getAllSymbol();
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
            List<KlineObjectNumber> allKlines = TickerHelper.getTicker(symbol, Constants.INTERVAL_1D);
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
        List<KlineObjectNumber> tickers = TickerHelper.getTicker(symbol, Constants.INTERVAL_15M);
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
        List<KlineObjectNumber> tickers = TickerHelper.getTicker("CYBERUSDT", Constants.INTERVAL_1D);
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
