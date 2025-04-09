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
package com.binance.chuyennd.trading.grid;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.trading.BudgetManager;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.GridConfigs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.trade.Order;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.Serializable;
import java.util.*;

/**
 * @author pc
 */
public class GridObjectProduction implements Serializable {
    public static final Logger LOG = LoggerFactory.getLogger(GridObjectProduction.class);

    public String symbol;
    public OrderTargetStatus status;
    public OrderSide side;
    public Double quantity;
    public Double priceStartGrid;
    public Double maxPrice;
    public Double minPrice;
    public Double bestPrice;

    public Long startTime;


    public int leverage;
    public Map<Double, GridOrderProd> price2Order;
    public List<Double> prices;
    public List<Double> pricesActive;


    public GridObjectProduction(String symbol, OrderSide side, Double maxPrice, Double minPrice, KlineObjectSimple tickerStart) {
        this.symbol = symbol;
        this.side = side;
        this.priceStartGrid = tickerStart.priceClose;
        this.bestPrice = tickerStart.priceClose;
        this.startTime = tickerStart.startTime.longValue();
        this.maxPrice = maxPrice;
        this.minPrice = minPrice;
        this.status = OrderTargetStatus.REQUEST;
        this.price2Order = new HashMap<>();
        this.prices = new ArrayList<>();
        this.pricesActive = new ArrayList<>();


    }

    public void initGrid() {
        initPrice();
        initOrder();
    }

    private void initOrder() {
        leverage = BudgetManager.getInstance().getLeverage();
        quantity = Utils.calQuantityTest(BudgetManager.getInstance().getBudgetGrid() / GridConfigs.GRID_NUMBER_ORDER_ACTIVE, leverage
                , priceStartGrid, symbol);
        if (symbol.equals(Constants.SYMBOL_PAIR_BTC)) {
            if (quantity < 0.002) {
                quantity = 0.002;
            }
        }
        // list price order current -> create orderMarker
        double quantityInitGrid = quantity * 2;
        Integer numberOrderMarketCreated = calNumberOrderMarket();
        Order orderMarket = GridOrderHelper.newOrderMarket(symbol, side, quantityInitGrid * numberOrderMarketCreated);
        if (orderMarket == null) {
            LOG.info("Error init order market when create grid: {} {} {}",
                    symbol, side, Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
            return;
        }
        for (int i = 0; i < prices.size() - 1; i++) {
            Double price = prices.get(i);
            Order order = null;
            GridOrderProd orderGrid = new GridOrderProd(price);
            if (side.equals(OrderSide.BUY)) {
                if (price < priceStartGrid) {
                    order = newOrder(symbol, OrderSide.BUY, price, null);
                    orderGrid.orderBuy = order;
                } else {
                    if (pricesActive.contains(price)) {
                        order = newOrder(symbol, OrderSide.SELL, prices.get(i + 1), quantityInitGrid);
                        orderGrid.orderBuy = orderMarket;
                        orderGrid.orderSell = order;
                    }
                }
                if (orderGrid.orderBuy != null) {
                    price2Order.put(price, orderGrid);
                }
            } else {
                if (price > priceStartGrid) {
                    order = newOrder(symbol, OrderSide.SELL, price, null);
                    orderGrid.orderSell = order;
                } else {
                    if (pricesActive.contains(price)) {
                        order = newOrder(symbol, OrderSide.BUY, prices.get(i + 1), quantityInitGrid);
                        orderGrid.orderBuy = order;
                        orderGrid.orderSell = orderMarket;
                    }
                }
                if (orderGrid.orderSell != null) {
                    price2Order.put(price, orderGrid);
                }
            }

        }
        status = OrderTargetStatus.POSITION_RUNNING;
    }

    public Order
    newOrder(String symbol, OrderSide side, Double price, Double quantityOrder) {
        if (side.equals(this.side) && !pricesActive.contains(price)) {
            return null;
        }
        Double quantityRun = quantityOrder;
        if (quantityOrder == null){
            quantityRun = this.quantity;
        }
        if (price != prices.get(prices.size() - 1)) {
            LOG.info("Create order limit: {}-{} {} {} {}", symbol, this.side, side, quantityRun, price);
            return GridOrderHelper.newOrder(symbol, side, quantityRun, price);
        }
        return null;
    }

    private Integer calNumberOrderMarket() {
        Integer counter = 0;
        for (Double price : pricesActive) {
            if (side.equals(OrderSide.BUY)) {
                if (price > priceStartGrid && price != maxPrice) {
                    counter++;
                }
            } else {
                if (price < priceStartGrid && price != minPrice) {
                    counter++;
                }
            }
        }
        return counter;
    }

    public void updatePriceBefore() {
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

    private void initPrice() {
        if (side.equals(OrderSide.BUY)) {
            prices.add(minPrice);
            while (true) {
                Double priceNew = Utils.calPriceTarget(symbol, prices.get(prices.size() - 1), OrderSide.BUY, GridConfigs.GRID_RATE_TRADE);
                if (priceNew < maxPrice) {
                    prices.add(priceNew);
                } else {
                    break;
                }
            }
            prices.add(maxPrice);
        } else {
            prices.add(maxPrice);
            while (true) {
                Double priceNew = Utils.calPriceTarget(symbol, prices.get(prices.size() - 1), OrderSide.SELL, GridConfigs.GRID_RATE_TRADE);
                if (priceNew > minPrice) {
                    prices.add(priceNew);
                } else {
                    break;
                }
            }
            prices.add(minPrice);
        }
        leverage = BudgetManagerSimple.getInstance().getLeverage();
        updatePriceActive(priceStartGrid);
    }

    public void updatePriceActive(Double currentPrice) {
        Integer index = null;
        if (pricesActive.size() < 2
                || currentPrice < Math.min(pricesActive.get(0), pricesActive.get(pricesActive.size() - 1))
                || currentPrice > Math.max(pricesActive.get(0), pricesActive.get(pricesActive.size() - 1))) {
            for (int i = 0; i < prices.size(); i++) {
                if (side.equals(OrderSide.BUY)) {
                    if (prices.get(i) > currentPrice) {
                        index = i;
                        break;
                    }
                } else {
                    if (prices.get(i) < currentPrice) {
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


}
