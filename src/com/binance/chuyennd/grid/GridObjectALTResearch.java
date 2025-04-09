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

import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.GridConfigs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.apache.commons.io.FileUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.Serializable;
import java.text.ParseException;
import java.util.*;

/**
 * @author pc
 */
public class GridObjectALTResearch implements Serializable {
    public static final Logger LOG = LoggerFactory.getLogger(GridObjectALTResearch.class);
    private static final long serialVersionUID = 6529685098267757690L;
    public String symbol;

    public OrderTargetStatus status;
    public OrderSide side;
    public Double quantity;
    public List<Double> datas;

    public Double priceStartGrid;

    public Double maxPrice;
    public Double bestPrice;
    public int numberOrderStart = 0;
    public Double minPrice;

    public Double balance;
    public Long endTime;
    public Double closePrice;
    public String closeDesc;
    public MarketLevelChange levelChange;
    public MarketDataObject marketData;


    public KlineObjectSimple tickerStart;
    public Double target;
    public Double unProfitMin;
    public Double marginMax;
    public Double marginRealMax;
    public Double profitLossMax;
    public Double budget;
    public int leverage;
    public Map<Double, OrderTargetInfoTest> price2Order;
    public List<Double> prices;
    public List<Double> pricesActive;
    public int positionOrderRunning;
    public TreeMap<Long, OrderTargetInfoTest> time2OrderDone;

    public static void main(String[] args) throws ParseException {

        String symbol = "BNBUSDT";
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
        KlineObjectSimple tickerStart = tickers.get(0);
        tickerStart.priceClose = 682.48;
        LOG.info("Time create grid: {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(tickerStart.startTime.longValue()),
                symbol, tickerStart.priceClose);
        GridObjectALTResearch simulator = new GridObjectALTResearch(symbol, OrderSide.BUY,
                800.0, 200.0, tickerStart);
        simulator.initGrid();
        LOG.info("{}", Utils.toJson(simulator.prices));
        for (KlineObjectSimple ticker : tickers) {
            if (simulator.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                simulator.updateGridWithMaBtc(ticker);
            } else {
                break;
            }
        }
        simulator.printResult();
    }

    public GridObjectALTResearch(String symbol, OrderSide side, Double maxPrice, Double minPrice, KlineObjectSimple tickerStart) {
        this.symbol = symbol;
        this.side = side;
        this.priceStartGrid = tickerStart.priceClose;
        this.maxPrice = maxPrice;
        this.minPrice = minPrice;
        this.tickerStart = tickerStart;
        this.status = OrderTargetStatus.REQUEST;
        price2Order = new HashMap<>();
        time2OrderDone = new TreeMap<>();
        prices = new ArrayList<>();
        datas = new ArrayList<>();
        bestPrice = priceStartGrid;
        pricesActive = new ArrayList<>();
        unProfitMin = 0d;
        profitLossMax = 0d;
        marginMax = 0d;
        marginRealMax = 0d;
        budget = null;
    }

    public GridObjectALTResearch(String symbol, OrderSide side, Double maxPrice, Double minPrice, KlineObjectSimple tickerStart, Double budget) {
        this.symbol = symbol;
        this.side = side;
        this.priceStartGrid = tickerStart.priceClose;
        this.maxPrice = maxPrice;
        this.minPrice = minPrice;
        this.tickerStart = tickerStart;
        this.budget = budget;
        this.status = OrderTargetStatus.REQUEST;
        price2Order = new HashMap<>();
        time2OrderDone = new TreeMap<>();
        prices = new ArrayList<>();
        datas = new ArrayList<>();
        bestPrice = priceStartGrid;
        pricesActive = new ArrayList<>();
        unProfitMin = 0d;
        profitLossMax = 0d;
        marginMax = 0d;
        marginRealMax = 0d;
    }


    public void initGrid() {
        initPrice(priceStartGrid);
        initOrder();
    }

    private void initOrder() {
        // list price order current
//        for (Double price : prices) {
        for (int i = 0; i < prices.size() - 1; i++) {
            Double price = prices.get(i);
            if (!pricesActive.contains(price)) {
                continue;
            }
            OrderTargetInfoTest order = null;

            if (side.equals(OrderSide.BUY)) {
                if (price < priceStartGrid) {
                    order = createOrder(symbol, price, OrderSide.BUY, tickerStart);
                    order.status = OrderTargetStatus.REQUEST;
                    order.priceSL = prices.get(i + 1);
                    order.lastPrice = tickerStart.priceClose;
                } else {
                    if (price != maxPrice) {
                        numberOrderStart++;
                        order = createOrderStart(symbol, priceStartGrid, OrderSide.BUY, tickerStart);
                        order.status = OrderTargetStatus.POSITION_RUNNING;
                        order.timeJoin = tickerStart.startTime.longValue();
                        order.priceSL = prices.get(i + 1);
                        order.lastPrice = tickerStart.priceClose;
                        order.minPrice = tickerStart.priceClose;
                        order.maxPrice = tickerStart.priceClose;

                    }
                }
            } else {
                if (price > priceStartGrid) {
                    order = createOrder(symbol, price, OrderSide.SELL, tickerStart);
                    order.status = OrderTargetStatus.REQUEST;
                    order.priceSL = prices.get(i + 1);
                    order.lastPrice = tickerStart.priceClose;
                } else {
                    if (price != minPrice) {
                        numberOrderStart++;
                        order = createOrderStart(symbol, priceStartGrid, OrderSide.SELL, tickerStart);
                        order.status = OrderTargetStatus.POSITION_RUNNING;
                        order.timeJoin = tickerStart.startTime.longValue();
                        order.priceSL = prices.get(i + 1);
                        order.lastPrice = tickerStart.priceClose;
                        order.minPrice = tickerStart.priceClose;
                        order.maxPrice = tickerStart.priceClose;

                    }
                }
            }
            if (order != null) {
                price2Order.put(price, order);
            }
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

    private OrderTargetInfoTest createOrderStart(String symbol, Double price, OrderSide side, KlineObjectSimple ticker) {
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, price,
                null, quantity * 2, leverage, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), side);
        order.tickerOpen = Utils.convertKlineSimple(ticker);
        order.marketLevelChange = MarketLevelChange.GRID_TRADE;
        return order;
    }

    private void initPrice(Double priceStart) {
//        LOG.info("Create Grid {} max:{} min:{} range:{} rate: {}%", symbol, maxPrice, minPrice, range, Utils.formatPercent(rateRange));

        if (side.equals(OrderSide.BUY)) {// BUY
            prices.add(minPrice);
            while (true) {
                Double priceNew = Utils.calPriceTarget(symbol, prices.get(prices.size() - 1), side, GridConfigs.GRID_RATE_TRADE);
                if (priceNew.equals(prices.get(prices.size() - 1))) {
                    priceNew = Utils.calPriceTarget(symbol, prices.get(prices.size() - 1), side, 2 * GridConfigs.GRID_RATE_TRADE);
                }
                if (priceNew < maxPrice) {
                    prices.add(priceNew);
                } else {
                    break;
                }
            }
            prices.add(maxPrice);
        } else {                        // SELL
            prices.add(maxPrice);
            while (true) {
                Double priceNew = Utils.calPriceTarget(symbol, prices.get(prices.size() - 1), side, GridConfigs.GRID_RATE_TRADE);
                if (priceNew > minPrice) {
                    prices.add(priceNew);
                } else {
                    break;
                }
            }
            prices.add(minPrice);
        }
        leverage = BudgetManagerSimple.getInstance().getLeverage();
        Double budgetRun = budget;
        if (budgetRun == null) {
            budgetRun = BudgetManagerSimple.getInstance().getBudgetGrid();
        }
        quantity = Utils.calQuantityTest(budgetRun / GridConfigs.GRID_NUMBER_ORDER_ACTIVE, leverage
                , priceStart, symbol);
        if (symbol.equals(Constants.SYMBOL_PAIR_BTC)) {
            if (quantity < 0.002) {
                quantity = 0.002;
            }
        }
        updatePriceActive(priceStart);
//        LOG.info("prices: {} \npriceActive:{}", prices, pricesActive);
    }

    private void updatePriceAfter() {
        prices.remove(prices.size() - 1);
        if (side.equals(OrderSide.BUY)) {
            while (prices.size() > 0) {
                if (prices.get(0) < minPrice) {
                    prices.remove(0);
                } else {
                    break;
                }
            }
            while (prices.size() > 0) {
                Double priceNew = Utils.calPriceTarget(symbol, prices.get(prices.size() - 1), OrderSide.BUY, GridConfigs.GRID_RATE_TRADE);
                if (priceNew < maxPrice) {
                    prices.add(priceNew);
                } else {
                    break;
                }
            }
            prices.add(maxPrice);
        } else {
            while (prices.size() > 0) {
                if (prices.get(0) > maxPrice) {
                    prices.remove(0);
                } else {
                    break;
                }
            }
            while (prices.size() > 0) {
                Double priceNew = Utils.calPriceTarget(symbol, prices.get(prices.size() - 1), OrderSide.SELL, GridConfigs.GRID_RATE_TRADE);
                if (priceNew > minPrice) {
                    prices.add(priceNew);
                } else {
                    break;
                }
            }
            prices.add(minPrice);
        }

//        LOG.info("prices: {} \npriceActive:{}", prices, pricesActive);
    }

    public void updateGridWithMaBtc(KlineObjectSimple ticker) {
        if (ticker.startTime.longValue() <= tickerStart.startTime.longValue()) {
            return;
        }
        endTime = ticker.startTime.longValue();
        updatePriceActive(ticker.priceClose);
        // update grid => update order, create order, finish grid
        // update all order running
        int counterPositionRunning = 0;
        for (int i = 0; i < prices.size(); i++) {
            Double price = prices.get(i);
            OrderTargetInfoTest order = price2Order.get(price);
            if (order != null) {
                updateOrder(ticker, order);
                if (order.status.equals(OrderTargetStatus.REQUEST) && !pricesActive.contains(price)) {
                    price2Order.remove(price);
                }
                if (order.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                    counterPositionRunning++;
                }
                if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                    order.priceTP = order.priceSL;
                    if (!Configs.MODE_RUN_SERVER) {
                        OrderSide sideDone = OrderSide.BUY;
                        if (order.side.equals(OrderSide.BUY)) {
                            sideDone = OrderSide.SELL;
                        }
                        LOG.info("{} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()),
                                sideDone, order.symbol, order.priceSL, order.quantity);
                    }

                    time2OrderDone.put(-order.timeUpdate + time2OrderDone.size(), order);
                    GridBudgetManager.getInstance().updatePnl(order);
                    price2Order.remove(price);
                    if (pricesActive.contains(price) && i < prices.size() - 2) {
                        OrderTargetInfoTest orderNew = createOrderNew(price, prices.get(i + 1), ticker);
                        price2Order.put(price, orderNew);
                    }
                }
            } else {
                if (pricesActive.contains(price) && i < prices.size() - 2) {
                    OrderTargetInfoTest orderNew = createOrderNew(price, prices.get(i + 1), ticker);
                    price2Order.put(price, orderNew);
                }
            }
            this.positionOrderRunning = counterPositionRunning;
        }
        unProfitMin = Math.min(unProfitMin, calProfitRunning());
        profitLossMax = Math.min(profitLossMax, calProfitLossMax());
        marginMax = Math.max(marginMax, calMargin());
        marginRealMax = Math.max(marginRealMax, calMargin() - calProfitRunning());


        if (side.equals(OrderSide.BUY)) {
//            if (ticker.priceClose > maxPrice) {
//                closeGrid(ticker, "over price max");
//                return;
//            }
            if (ticker.priceClose < minPrice) {
                closeGrid(ticker, "over price min");
                return;
            }
//            if (ticker.minPrice < minPrice) {
////                LOG.info("Init price top: {} {} {} {}", priceTop, ticker.maxPrice * 1.1, ticker.maxPrice * 0.9, positionOrderRunning);
//                minPrice = minPrice * 0.8;
//                updatePriceBefore();
//                updatePriceActive(ticker.priceClose);
//            }
            if (ticker.maxPrice > maxPrice) {
//                LOG.info("Init price top: {} {} {} {}", priceTop, ticker.maxPrice * 1.1, ticker.maxPrice * 0.9, positionOrderRunning);
                maxPrice = maxPrice * 1.2;
                updatePriceBefore();
                updatePriceActive(ticker.priceClose);
            }
        } else {
//            if (ticker.priceClose < minPrice) {
//                closeGrid(ticker, "over price min");
//                return;
//            }
            if (ticker.priceClose > maxPrice) {
                closeGrid(ticker, "over price max");
                return;
            }
//            if (ticker.maxPrice > maxPrice) {
////                LOG.info("Init price top: {} {} {} {}", priceTop, ticker.maxPrice * 1.1, ticker.maxPrice * 0.9, positionOrderRunning);
//                maxPrice = maxPrice * 1.2;
//                updatePriceBefore();
//                updatePriceActive(ticker.priceClose);
//            }
            if (ticker.minPrice < minPrice) {
//                LOG.info("Init price top: {} {} {} {}", priceTop, ticker.maxPrice * 1.1, ticker.maxPrice * 0.9, positionOrderRunning);
                minPrice = minPrice * 0.8;
                updatePriceBefore();
                updatePriceActive(ticker.priceClose);
            }

        }

        // Close when price reverse
//        double rateOver = GridConfigs.GRID_RATE_BUY_OVER;
        double rateOver = 0.5;
//        if (budget != null) {
//            rateOver = 0.05;
//        }
        if (ticker.startTime.longValue() > tickerStart.startTime.longValue() + GridConfigs.NUMBER_MIN_CLOSE_PRICE_REVERSE * Utils.TIME_MINUTE) {
            if (side.equals(OrderSide.SELL)) {
//                rateOver = GridConfigs.GRID_RATE_SELL_OVER;
                if (bestPrice > ticker.minPrice) {
                    bestPrice = ticker.minPrice;
                }
                Double rateUp = Utils.rateOf2Double(ticker.priceClose, bestPrice);

                if (rateUp > rateOver) {
                    closeGrid(ticker, "Up with min");
                    return;
                }
            } else {
                if (bestPrice < ticker.maxPrice) {
                    bestPrice = ticker.maxPrice;
                }
                Double rateDown = Utils.rateOf2Double(bestPrice, ticker.priceClose);
                if (ticker.priceClose < priceStartGrid) {
                    rateOver = rateOver * 2;
                }
                if (rateDown > rateOver) {
                    closeGrid(ticker, "down with max");
                    return;
                }
            }
        }else{
            bestPrice = priceStartGrid;
        }

        if (price2Order.isEmpty()) {
//            LOG.info("Grid finished: {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), ticker.priceClose);
            status = OrderTargetStatus.FINISHED;
            endTime = ticker.startTime.longValue();
        }
    }

    private void updatePriceBefore() {
        prices.remove(0);
        if (side.equals(OrderSide.BUY)) {
            while (prices.size() > 0) {
                Double priceNew = Utils.calPriceTarget(symbol, prices.get(0), OrderSide.SELL, GridConfigs.GRID_RATE_TRADE);
                if (priceNew > minPrice) {
                    prices.add(0, priceNew);
                } else {
                    break;
                }
            }
            prices.add(0, minPrice);
        } else {
            while (prices.size() > 0) {
                Double priceNew = Utils.calPriceTarget(symbol, prices.get(0), OrderSide.BUY, GridConfigs.GRID_RATE_TRADE);
                if (priceNew < maxPrice) {
                    prices.add(0, priceNew);
                } else {
                    break;
                }
            }
            prices.add(0, maxPrice);
        }
    }


    private void updatePriceActive(Double priceClose) {
        if (pricesActive.size() < 2
                || priceClose < Math.min(pricesActive.get(0), pricesActive.get(pricesActive.size() - 1))
                || priceClose > Math.max(pricesActive.get(0), pricesActive.get(pricesActive.size() - 1))) {
            Integer index = null;
            for (int i = 0; i < prices.size(); i++) {
                if (side.equals(OrderSide.BUY)) {
                    if (prices.get(i) > priceClose) {
                        index = i;
                        break;
                    }
                } else {
                    if (prices.get(i) < priceClose) {
                        index = i;
                        break;
                    }
                }
            }
            if (index != null) {
                pricesActive.clear();
                for (int i = 0; i < GridConfigs.GRID_NUMBER_ORDER_ACTIVE; i++) {
                    int j = i + index - GridConfigs.GRID_NUMBER_ORDER_ACTIVE / 2;
                    if (j >= 0 && j < prices.size()) {
                        pricesActive.add(prices.get(j));
                    }
                }
            }
        }
    }

    public void closeGrid(KlineObjectSimple ticker, String desc) {
        closeDesc = desc;
        closePrice = ticker.priceClose;
        for (int i = 0; i < prices.size(); i++) {
            Double price = prices.get(i);
            OrderTargetInfoTest order = price2Order.get(price);
            if (order == null) {
                continue;
            }
            if (order.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                order.priceTP = ticker.priceClose;
                order.status = OrderTargetStatus.STOP_LOSS_DONE;
                if (!Configs.MODE_RUN_SERVER) {
                    LOG.info("Close Grid: {} {} {} {} {}", order.symbol, Utils.sdfGoogle.format(new Date(order.timeStart)),
                            order.side, order.priceEntry, order.priceSL);
                }
                time2OrderDone.put(-order.timeUpdate + time2OrderDone.size(), order);
                GridBudgetManager.getInstance().updatePnl(order);
                price2Order.remove(price);
            }
            if (order.status.equals(OrderTargetStatus.REQUEST)) {
                price2Order.remove(price);
            }
        }
        status = OrderTargetStatus.FINISHED;
    }

    private OrderTargetInfoTest createOrderNew(Double price, Double nextPrice, KlineObjectSimple ticker) {
        OrderTargetInfoTest orderNew;
        orderNew = createOrder(symbol, price, side, ticker);
        orderNew.status = OrderTargetStatus.REQUEST;
        orderNew.priceSL = nextPrice;
        orderNew.lastPrice = ticker.priceClose;
        orderNew.minPrice = ticker.priceClose;
        orderNew.maxPrice = ticker.priceClose;
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
                        order.minPrice = ticker.priceClose;
                        order.maxPrice = ticker.priceClose;
                        if (!Configs.MODE_RUN_SERVER) {
                            LOG.info("{} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()),
                                    order.side, order.symbol, order.priceEntry, order.quantity);
                        }
                    }
                } else {
                    if (ticker.maxPrice >= order.priceEntry) {
                        order.status = OrderTargetStatus.POSITION_RUNNING;
                        order.timeJoin = ticker.startTime.longValue();
                        order.minPrice = ticker.priceClose;
                        order.maxPrice = ticker.priceClose;
                        if (!Configs.MODE_RUN_SERVER) {
                            LOG.info("{} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()),
                                    order.side, order.symbol, order.priceEntry, order.quantity);
                        }
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
                    order.minPrice = Math.min(order.minPrice, ticker.minPrice);
                    order.maxPrice = Math.max(order.maxPrice, ticker.maxPrice);
                    order.timeUpdate = ticker.startTime.longValue();
                }
            }
        }
    }

    public void printResult() {
        Double profit = calProfit();
//        if (side.equals(OrderSide.BUY)){
//            return;
//        }
        Double budgetRun = budget;
        if (budgetRun == null) {
            budgetRun = BudgetManagerSimple.getInstance().getBudgetGrid();
        }
        LOG.info("Grid done:{} {} {} {}% orderStart:{} s-c-b {}-{}-{} {} mMax:{} mRealMax: {} p: {}/{} uMin:{} lossMax:{} {} -> {} {} days {}%", closeDesc,
                side, symbol, Utils.formatPercent(GridConfigs.GRID_RATE_TRADE), numberOrderStart, priceStartGrid, closePrice, bestPrice,
                time2OrderDone.size(), marginMax.longValue(), marginRealMax.longValue(),
                profit.longValue(), calProfitRunning().longValue(), unProfitMin.longValue(), profitLossMax.longValue(),
                Utils.normalizeDateYYYYMMDDHHmm(tickerStart.startTime.longValue()), Utils.normalizeDateYYYYMMDDHHmm(endTime),
                (endTime - tickerStart.startTime.longValue()) / Utils.TIME_DAY, Utils.formatPercent(profit / budgetRun));
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

    public Double calProfitRunning() {
        Double profit = 0d;
        for (OrderTargetInfoTest order : price2Order.values()) {
            if (order.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                order.priceTP = order.lastPrice;
                profit += order.calTp();
            }
        }
        return profit;
    }

    public Integer countOrderRunning() {
        Integer counter = 0;
        for (OrderTargetInfoTest order : price2Order.values()) {
            if (order.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                counter++;
            }
        }
        return counter;
    }


    public Double calProfitLossMax() {
        Double profit = 0d;
        for (OrderTargetInfoTest order : price2Order.values()) {
            if (order.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                profit += order.calLossMax();
            }
        }
        return profit;
    }

    public Double calMargin() {
        Double margin = 0d;
        for (OrderTargetInfoTest order : price2Order.values()) {
            margin += order.calMargin();
        }
        return margin;
    }

    public void exportFile() {
        List<String> lines = new ArrayList<>();
        lines.add("symbol, time,join, end,entry,tp,sl,quantity,status,profit");
        for (OrderTargetInfoTest order : time2OrderDone.values()) {
            StringBuilder sb = new StringBuilder();
            sb.append(symbol).append(",");
            sb.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)).append(",");
            sb.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeJoin)).append(",");
            sb.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate)).append(",");
            sb.append(order.priceEntry).append(",");
            sb.append(order.priceTP).append(",");
            sb.append(order.priceSL).append(",");
            sb.append(order.quantity).append(",");
            sb.append(order.status).append(",");
            sb.append(order.calTp()).append(",");
            lines.add(sb.toString());
        }
        for (OrderTargetInfoTest order : price2Order.values()) {
            if (!order.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                continue;
            }
            order.priceTP = order.lastPrice;
            StringBuilder sb = new StringBuilder();
            sb.append(symbol).append(",");
            sb.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)).append(",");
            sb.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeJoin)).append(",");
            sb.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate)).append(",");
            sb.append(order.priceEntry).append(",");
            sb.append(order.priceTP).append(",");
            sb.append(order.priceSL).append(",");
            sb.append(order.quantity).append(",");
            sb.append(order.status).append(",");
            sb.append(order.calTp()).append(",");
            lines.add(sb.toString());
        }


        try {
            FileUtils.writeLines(new File("target/" + symbol + "-" + side + "-" + Utils.normalizeDateYYYYMMDD(tickerStart.startTime.longValue())
                    + "-" + tickerStart.startTime.longValue() / 1000 + ".csv"), lines);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
