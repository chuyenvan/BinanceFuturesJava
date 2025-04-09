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
package com.binance.chuyennd.grid;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.Serializable;
import java.text.ParseException;
import java.util.*;

/**
 * @author pc
 */
public class GridObjectTest implements Serializable {
    public static final Logger LOG = LoggerFactory.getLogger(GridObjectTest.class);

    public String symbol;
    public OrderTargetStatus status;
    public OrderSide side;
    public Double quantity;
    public Double priceStartGrid;
    public Double maxPrice;
    public Double bestPrice;
    public Double minPrice;
    public Double priceTop;
    public Double priceBottom;
    public Double balance;
    public Long endTime;
    public String closeDesc;
    public MarketLevelChange levelChange;


    public KlineObjectSimple tickerStart;
    public int range;
    public Double target;
    public int leverage;
    public Map<Double, OrderTargetInfoTest> price2Order;
    public List<Double> prices;
    public TreeMap<Long, OrderTargetInfoTest> time2OrderDone;

    public GridObjectTest(String symbol, OrderSide side, KlineObjectSimple tickerStart, int range) {
        this.symbol = symbol;
        this.side = side;
        this.priceStartGrid = tickerStart.priceClose;
        this.maxPrice = tickerStart.priceClose * 1.05;
        this.minPrice = tickerStart.priceClose * 0.95;
        this.priceTop = tickerStart.priceClose * 1.06;
        this.priceBottom = tickerStart.priceClose * 0.94;
        this.range = range;
        this.tickerStart = tickerStart;
        this.status = OrderTargetStatus.REQUEST;
        price2Order = new HashMap<>();
        time2OrderDone = new TreeMap<>();
        prices = new ArrayList<>();
    }

    public GridObjectTest(String symbol, OrderSide side, Double maxPrice, Double minPrice, Double priceTop,
                          Double priceBottom, int range, KlineObjectSimple tickerStart) {
        this.symbol = symbol;
        this.side = side;
        this.priceStartGrid = tickerStart.priceClose;
        this.maxPrice = maxPrice;
        this.minPrice = minPrice;
        this.priceTop = priceTop;
        this.priceBottom = priceBottom;
        this.range = range;
        this.tickerStart = tickerStart;
        this.status = OrderTargetStatus.REQUEST;
        price2Order = new HashMap<>();
        time2OrderDone = new TreeMap<>();
        prices = new ArrayList<>();
        bestPrice = priceStartGrid;
    }

    public void initGrid() {
        initPrice();
        initOrder();
    }

    private void initOrder() {
        leverage = BudgetManagerSimple.getInstance().getLeverage();
        quantity = Utils.calQuantityTest(BudgetManagerSimple.getInstance().getBudgetGrid() / range, leverage
                , priceStartGrid, symbol);
        // list price order current
//        for (Double price : prices) {
        for (int i = 0; i < prices.size() - 1; i++) {
            Double price = prices.get(i);
            OrderTargetInfoTest order;
            if (side.equals(OrderSide.BUY)) {
                if (price < priceStartGrid) {
                    order = createOrder(symbol, price, OrderSide.BUY, tickerStart);
                    order.status = OrderTargetStatus.REQUEST;
                    order.priceSL = prices.get(i + 1);
                    order.lastPrice = tickerStart.priceClose;
                } else {
                    order = createOrder(symbol, priceStartGrid, OrderSide.BUY, tickerStart);
                    order.status = OrderTargetStatus.POSITION_RUNNING;
                    order.timeJoin = tickerStart.startTime.longValue();
                    order.priceSL = prices.get(i + 1);
                    order.lastPrice = tickerStart.priceClose;
                }
            } else {
                if (price > priceStartGrid) {
                    order = createOrder(symbol, price, OrderSide.SELL, tickerStart);
                    order.status = OrderTargetStatus.REQUEST;
                    order.priceSL = prices.get(i + 1);
                    order.lastPrice = tickerStart.priceClose;
                } else {
                    order = createOrder(symbol, priceStartGrid, OrderSide.SELL, tickerStart);
                    order.status = OrderTargetStatus.POSITION_RUNNING;
                    order.timeJoin = tickerStart.startTime.longValue();
                    order.priceSL = prices.get(i + 1);
                    order.lastPrice = tickerStart.priceClose;
                }
            }
            price2Order.put(price, order);
        }
        status = OrderTargetStatus.POSITION_RUNNING;
    }

    private OrderTargetInfoTest createOrder(String symbol, Double price, OrderSide side, KlineObjectSimple ticker) {
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, price,
                null, quantity, leverage, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), side);
        order.tickerOpen = Utils.convertKlineSimple(ticker);
        order.marketLevelChange = MarketLevelChange.GRID_TRADE;
        return order;
    }

    private void initPrice() {
        double rateRange = Utils.rateOf2Double(maxPrice, minPrice) / range;
        LOG.info("Create Grid {} rate: {}%", symbol, Utils.formatPercent(rateRange));
        if (side.equals(OrderSide.BUY)) {
            prices.add(minPrice);
            for (int i = 1; i < range; i++) {
                prices.add(Utils.calPriceTarget(symbol, minPrice, OrderSide.BUY, i * rateRange));
            }
            prices.add(maxPrice);
        } else {
            prices.add(maxPrice);
            for (int i = 1; i < range; i++) {
                prices.add(Utils.calPriceTarget(symbol, maxPrice, OrderSide.SELL, i * rateRange));
            }
            prices.add(minPrice);
        }
    }

    public void updateGrid(KlineObjectSimple ticker) {
        if (ticker.startTime.longValue() <= tickerStart.startTime.longValue()) {
            return;
        }
        endTime = ticker.startTime.longValue();
        // update grid => update order, create order, finish grid
        // update all order running
        for (int i = 0; i < prices.size(); i++) {
            Double price = prices.get(i);
            OrderTargetInfoTest order = price2Order.get(price);
            if (order != null) {
                updateOrder(ticker, order);
                if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                    order.priceTP = order.priceSL;
                    OrderSide sideDone = OrderSide.BUY;
                    if (order.side.equals(OrderSide.BUY)) {
                        sideDone = OrderSide.SELL;
                    }
                    LOG.info("{} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()),
                            sideDone, order.symbol, order.priceSL, order.quantity);
//                    LOG.info("Done order in Grid: {} {} {} {} {} {}", order.symbol, Utils.sdfGoogle.format(new Date(order.timeStart))
//                            , Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate), order.side, order.priceEntry, order.priceSL);
                    time2OrderDone.put(-order.timeUpdate + time2OrderDone.size(), order);
                    OrderTargetInfoTest orderNew = createOrderNew(price, prices.get(i + 1), ticker);
                    price2Order.put(price, orderNew);
                }
            }
        }
        // Close grid when price over range
        if (ticker.minPrice < priceBottom || ticker.maxPrice > priceTop) {
            closeGrid(ticker, "over price");
        }
        // Close when price reverse
        if (bestPrice < ticker.maxPrice) {
            bestPrice = ticker.maxPrice;
        }
        Double rateDown = Utils.rateOf2Double(bestPrice, ticker.priceClose);
        Double rateUpMax = Utils.rateOf2Double(bestPrice, tickerStart.priceClose);
        if (rateDown > 0.03
                && rateUpMax > 0.04) {
            closeGrid(ticker, "down with max");
            return;
        }

        if (price2Order.isEmpty()) {
            LOG.info("Grid finished: {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), ticker.priceClose);
            status = OrderTargetStatus.FINISHED;
            endTime = ticker.startTime.longValue();
        }
    }

    public void closeGrid(KlineObjectSimple ticker, String desc) {
        closeDesc = desc;
        for (int i = 0; i < prices.size(); i++) {
            Double price = prices.get(i);
            OrderTargetInfoTest order = price2Order.get(price);
            if (order == null) {
                continue;
            }
            if (order.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                order.priceTP = ticker.priceClose;
                order.status = OrderTargetStatus.STOP_LOSS_DONE;
                LOG.info("Close Grid: {} {} {} {} {}", order.symbol, Utils.sdfGoogle.format(new Date(order.timeStart)),
                        order.side, order.priceEntry, order.priceSL);
                time2OrderDone.put(-order.timeUpdate + time2OrderDone.size(), order);
                price2Order.remove(price);
            }
            if (order.status.equals(OrderTargetStatus.REQUEST)) {
                price2Order.remove(price);
            }
        }
    }

    private OrderTargetInfoTest createOrderNew(Double price, Double nextPrice, KlineObjectSimple ticker) {
        OrderTargetInfoTest orderNew;
        if (side.equals(OrderSide.BUY)) {
            orderNew = createOrder(symbol, price, OrderSide.BUY, ticker);
            orderNew.status = OrderTargetStatus.REQUEST;
            orderNew.priceSL = nextPrice;
            orderNew.lastPrice = ticker.priceClose;
        } else {
            orderNew = createOrder(symbol, price, OrderSide.SELL, ticker);
            orderNew.status = OrderTargetStatus.REQUEST;
            orderNew.priceSL = nextPrice;
            orderNew.lastPrice = ticker.priceClose;
        }
        return orderNew;
    }

    private void updateOrder(KlineObjectSimple ticker, OrderTargetInfoTest order) {
        if (order.timeStart < ticker.startTime.longValue()) {
            order.lastPrice = ticker.priceClose;
            if (order.status.equals(OrderTargetStatus.REQUEST)) {
                if (order.side.equals(OrderSide.BUY)) {
                    if (ticker.minPrice <= order.priceEntry) {
                        order.status = OrderTargetStatus.POSITION_RUNNING;
                        order.timeJoin = ticker.startTime.longValue();
                        LOG.info("{} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()),
                                order.side, order.symbol, order.priceEntry, order.quantity);
                    }
                } else {
                    if (ticker.maxPrice >= order.priceEntry) {
                        order.status = OrderTargetStatus.POSITION_RUNNING;
                        order.timeJoin = ticker.startTime.longValue();
                    }
                }
                order.timeUpdate = ticker.startTime.longValue();
            }
            if (order.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                if (order.timeJoin < ticker.startTime.longValue()) {
                    if (order.side.equals(OrderSide.BUY)) {
                        if (ticker.maxPrice >= order.priceSL) {
                            order.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                        }
                    } else {
                        if (ticker.minPrice <= order.priceSL) {
                            order.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                        }
                    }
                    order.timeUpdate = ticker.startTime.longValue();
                }
            }
        }
    }

    public void printResult() {
        Double profit = calProfit();
        LOG.info("Grid done:{} {} {} {} {} budget:{} profit: {}/{} {} -> {} {} days rate: {}%", closeDesc,
                Utils.normalizeDateYYYYMMDDHHmm(tickerStart.startTime.longValue()), symbol, tickerStart.priceClose,
                time2OrderDone.size(), BudgetManagerSimple.getInstance().getBudgetGrid().longValue(),
                profit.longValue(), calProfitRunning().longValue(),
                Utils.normalizeDateYYYYMMDDHHmm(tickerStart.startTime.longValue()), Utils.normalizeDateYYYYMMDDHHmm(endTime),
                (endTime - tickerStart.startTime.longValue()) / Utils.TIME_DAY, Utils.formatPercent(profit / BudgetManagerSimple.getInstance().getBudgetGrid()));
    }

    public Double calProfit() {
        Double profit = 0d;
        for (OrderTargetInfoTest order : time2OrderDone.values()) {
            profit += order.calTp();
//            LOG.info("Order done: start: {} {} join: {} {} end: {} {} quantity:{} profit:{} "
//                    , Utils.normalizeDateYYYYMMDDHHmm(order.timeStart), order.priceEntry
//                    , Utils.normalizeDateYYYYMMDDHHmm(order.timeJoin), order.priceEntry
//                    , Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate), order.priceTP
//                    , quantity, order.calTp()
//            );
        }
        profit += calProfitRunning();
        return profit;
    }

    private Double calProfitRunning() {
        Double profit = 0d;
        for (OrderTargetInfoTest order : price2Order.values()) {
            if (order.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                order.priceTP = order.lastPrice;
                profit += order.calTp();
                LOG.info("Order running: start: {} {} join: {} {} end: {} {} quantity:{} profit:{} "
                        , Utils.normalizeDateYYYYMMDDHHmm(order.timeStart), order.priceEntry
                        , Utils.normalizeDateYYYYMMDDHHmm(order.timeJoin), order.priceEntry
                        , Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate), order.priceSL
                        , quantity, order.calTp()
                );
            }
        }
        return profit;
    }

    public static void main(String[] args) throws ParseException {
//        String symbol = "MKRUSDT";
//        OrderSide side = OrderSide.BUY;
//        Double price = 884.1;
//        Double maxPrice = 960.0;
//        Double priceTop = 970.0;
//        Double minPrice = 880.0;
//        Double priceBottom = 870.0;
//        Integer range = 10;
//        GridObject simulator = new GridObject(symbol, side, price, maxPrice, minPrice, priceTop, priceBottom, range);
//        simulator.createOrder();
//        LOG.info("{}", Utils.toJson(simulator.prices)) ;
        String symbol = "BNBUSDT";
        OrderSide side = OrderSide.BUY;
        long startTime = Utils.sdfFileHour.parse("20250214 10:31").getTime();
        List<KlineObjectSimple> tickers = new ArrayList<>();
        for (int i = 0; i < 30; i++) {
            long time = startTime + i * 500 * Utils.TIME_MINUTE;
            tickers.addAll(TickerFuturesHelper.getTickerSimpleWithStartTime(symbol,
                    Constants.INTERVAL_1M, time));
            if (time > System.currentTimeMillis()) {
                break;
            }
        }
//        tickers.get(tickers.size() - 1).minPrice = 90800.0;
        KlineObjectSimple tickerStart = tickers.get(0);
        tickerStart.priceClose = 682.48;
        LOG.info("Time create grid: {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(tickerStart.startTime.longValue()),
                symbol, tickerStart.priceClose);
        GridObjectTest simulator = new GridObjectTest(symbol, OrderSide.BUY,
                735.0, 630.0, 736.0, 625.0, 30, tickerStart);
//        GridObject simulator = new GridObject(symbol, side, tickerStart, range);
        simulator.initGrid();
        LOG.info("{}", Utils.toJson(simulator.prices));
        for (KlineObjectSimple ticker : tickers) {
//            if (ticker.startTime.longValue() == Utils.sdfFileHour.parse("20250209 10:59").getTime()) {
//                System.out.println("Debug");
//            }
            if (simulator.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                simulator.updateGrid(ticker);
            } else {
                break;
            }
        }
        simulator.printResult();
    }

}
