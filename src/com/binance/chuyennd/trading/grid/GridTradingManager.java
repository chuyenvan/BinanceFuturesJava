package com.binance.chuyennd.trading.grid;

import com.binance.chuyennd.position.manager.PositionHelper;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.trading.bak.DetectEntrySignal2GridTrade;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.GridConfigs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.enums.OrderStatus;
import com.binance.client.model.enums.OrderType;
import com.binance.client.model.trade.Order;
import com.binance.client.model.trade.PositionRisk;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.logging.Level;

public class GridTradingManager {
    public static final Logger LOG = LoggerFactory.getLogger(GridTradingManager.class);
    public ExecutorService executorServiceGridNew = Executors.newFixedThreadPool(Configs.NUMBER_THREAD_ORDER_MANAGER);
    private final ConcurrentHashMap<String, Long> symbol2Processing = new ConcurrentHashMap<>();

    private void startThreadListenQueueOrder2ManagerNew() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadListenQueueGrid2ManagerNew");
            LOG.info("Start thread ThreadListenQueueGrid2ManagerNew!");
            while (true) {
                List<String> data;
                try {
                    data = RedisHelper.getInstance().get().blpop(0, RedisConst.REDIS_KEY_BINANCE_TD_GRID_MANAGER_QUEUE);
                    String orderJson = data.get(1);
                    try {
                        GridObjectProduction grid = Utils.gson.fromJson(orderJson, GridObjectProduction.class);
                        LOG.info("Queue listen grid to manager order received : {} {} ", grid.side, grid.symbol);
                        GridObjectProduction gridRunning = getGridInfo(grid.symbol);
                        if (gridRunning != null) {
                            LOG.info("Reject grid of {} {} {}", grid.side, grid.symbol, Utils.normalizeDateYYYYMMDDHHmm(grid.startTime));
                        } else {
                            if (!symbol2Processing.containsKey(grid.symbol)) {
                                symbol2Processing.put(grid.symbol, System.currentTimeMillis());
                                executorServiceGridNew.execute(() -> processGridNew(grid));
                            }
                        }
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadListenQueueGrid2ManagerNew {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    public void processGridNew(GridObjectProduction grid) {
        grid.initGrid();
        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, grid.symbol, Utils.toJson(grid));
        symbol2Processing.remove(grid.symbol);
    }

    public GridObjectProduction getGridInfo(String symbol) {
        try {
            String orderJson = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, symbol);
            if (StringUtils.isNotBlank(orderJson)) {
                GridObjectProduction grid = Utils.gson.fromJson(orderJson, GridObjectProduction.class);
                return grid;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static void main(String[] args) throws ParseException, InterruptedException {
        new GridTradingManager().start();
    }

    private void start() throws ParseException, InterruptedException {
        startThreadListenQueueOrder2ManagerNew();
        startThreadUpdateGridRunning();
    }

    public boolean isTimeProcessUpdateGrid() {
        long time = System.currentTimeMillis();
        long second = (time / Utils.TIME_SECOND) % 60;
        long miniSecond = (time % Utils.TIME_SECOND);
        return second % 20 == 0 && miniSecond < 100;
    }

    private void startThreadUpdateGridRunning() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadUpdateGridRunning");
            LOG.info("Start thread ThreadUpdateGridRunning!");
            while (true) {
                if (isTimeProcessUpdateGrid()) {
                    try {
                        executorServiceGridNew.execute(() -> processUpdateAllGridRunning());
                        executorServiceGridNew.execute(() -> findGridNew2Run());
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
                try {
                    Thread.sleep(Utils.TIME_SECOND / 10);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(DetectEntrySignal2GridTrade.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }).start();

    }

    private void findGridNew2Run() {
        try {
            Set<String> symbolRunning = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO);
            for (String symbol : Constants.specialSymbol) {
                if (!symbolRunning.contains(symbol)) {
                    GridObjectProduction grid = GridDetectorProd.findRange2RunProd(symbol);
                    if (grid != null) {
                        LOG.info("Push redis grid: {} {} {}", symbol, grid.side, Utils.normalizeDateYYYYMMDDHHmm(grid.startTime));
                        RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_BINANCE_TD_GRID_MANAGER_QUEUE, Utils.toJson(grid));
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void processUpdateAllGridRunning() {
        try {
            Set<String> symbols = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO);
            if (symbols == null || symbols.isEmpty()) {
                LOG.info("Not grid running!");
                return;
            }
            LOG.info("Start process list grid running: {}", symbols);
            long startTime = System.currentTimeMillis();
            List<Order> ordersOpen = GridFuturesClientSingleton.getInstance().getAllOpenOrderInfos();
            List<PositionRisk> positions = GridFuturesClientSingleton.getInstance().getAllPositionInfos();
            Map<String, PositionRisk> symbol2Pos = new HashMap<>();
            Map<String, List<Order>> symbol2OrderLimit = new HashMap<>();
            for (PositionRisk position : positions) {
                symbol2Pos.put(position.getSymbol(), position);
            }
            for (Order order : ordersOpen) {
                if (StringUtils.equals(order.getType(), OrderType.LIMIT.toString())) {
                    List<Order> orders = symbol2OrderLimit.get(order.getSymbol());
                    if (orders == null) {
                        orders = new ArrayList<>();
                    }
                    orders.add(order);
                    symbol2OrderLimit.put(order.getSymbol(), orders);
                }
            }
            for (String symbol : symbols) {
                if (!symbol2Processing.containsKey(symbol)) {
                    GridObjectProduction grid = getGridInfo(symbol);
                    if (grid == null) {
                        LOG.info("Error get grid info from redis: {}", symbol);
                    } else {
                        PositionRisk position = symbol2Pos.get(symbol);
                        List<Order> orders = symbol2OrderLimit.get(symbol);
                        if (position == null || orders == null) {
                            LOG.info("Error get pos/orders info from binance: {}", symbol);
                        } else {
                            double currentPrice = position.getMarkPrice().doubleValue();
                            // Close when price reverse
                            if (System.currentTimeMillis() - GridConfigs.NUMBER_MIN_CLOSE_PRICE_REVERSE * Utils.TIME_MINUTE > grid.startTime) {

                                double rateOver = GridConfigs.GRID_RATE_BUY_OVER;
                                if (grid.side.equals(OrderSide.SELL)) {
                                    rateOver = GridConfigs.GRID_RATE_SELL_OVER;

                                    Double rateUp = Utils.rateOf2Double(currentPrice, grid.bestPrice);
                                    if (rateUp > rateOver) {
                                        LOG.info("Close grid price reverse: {} {} min: {} max: {} current:{} {}", grid.symbol, grid.side,
                                                grid.minPrice, grid.maxPrice, currentPrice, grid.bestPrice);
                                        closeGridRunning(grid, position, orders);
                                        continue;
                                    }
                                } else {
                                    Double rateDown = Utils.rateOf2Double(grid.bestPrice, currentPrice);
                                    if (currentPrice < grid.priceStartGrid) {
                                        rateOver = rateOver * 2;
                                    }
                                    if (rateDown > rateOver) {
                                        LOG.info("Close grid price reverse: {} {} min: {} max: {} current:{} {}", grid.symbol, grid.side,
                                                grid.minPrice, grid.maxPrice, currentPrice, grid.bestPrice);
                                        closeGridRunning(grid, position, orders);
                                        continue;
                                    }
                                }
                            }
                            // update bestprice
                            if (grid.side.equals(OrderSide.BUY)) {
                                if (currentPrice > grid.bestPrice) {
                                    grid.bestPrice = currentPrice;
                                }
                            } else {
                                if (currentPrice < grid.bestPrice) {
                                    grid.bestPrice = currentPrice;
                                }
                            }
                            grid.updatePriceActive(currentPrice);
                            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, grid.symbol, Utils.toJson(grid));
                            List<String> orderLimitBuys = new ArrayList<>();
                            List<String> orderLimitSells = new ArrayList<>();
                            Double quantitySell = 0d;
                            Double quantityBuy = 0d;
                            for (Order order : orders) {
                                if (StringUtils.equalsIgnoreCase(order.getSide(), OrderSide.BUY.toString())) {
                                    orderLimitBuys.add(order.getClientOrderId());
                                    quantityBuy += order.getOrigQty().doubleValue() * 1E9;
                                } else {
                                    orderLimitSells.add(order.getClientOrderId());
                                    quantitySell += order.getOrigQty().doubleValue() * 1E9;
                                }
                            }
                            if (grid.side.equals(OrderSide.BUY)) {
                                if (currentPrice < grid.minPrice) {
                                    LOG.info("Extend price end: {} {} {}", grid.minPrice, grid.minPrice * 0.8);
                                    grid.minPrice = grid.minPrice * 0.8;
                                    grid.updatePriceBefore();
                                    grid.updatePriceActive(currentPrice);
                                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, grid.symbol, Utils.toJson(grid));
                                }
                                if (currentPrice > grid.maxPrice) {
                                    LOG.info("Close grid over maxprice: {} {} min: {} max: {} current:{}", grid.symbol, grid.side,
                                            grid.minPrice, grid.maxPrice, currentPrice);
                                    closeGridRunning(grid, position, orders);
                                    continue;
                                }
                                LOG.info("Grid : {} {} {} {} entry/mark: {}/{}", grid.side, symbol, quantitySell,
                                        position.getPositionAmt().doubleValue() * 1E9,
                                        position.getEntryPrice().doubleValue(),
                                        position.getMarkPrice().doubleValue());
                                Double quantitySellLong = quantitySell;
                                Double quantityPosition = position.getPositionAmt().doubleValue() * 1E9;
                                if (quantitySellLong.longValue() != quantityPosition.longValue()) {
                                    LOG.info("Grid order buy not match position: {} {} {}", symbol, quantitySellLong, position.getPositionAmt().doubleValue());
                                }
                                for (int i = 0; i < grid.prices.size() - 1; i++) {
                                    Double price = grid.prices.get(i);
                                    GridOrderProd orderStorage = grid.price2Order.get(price);
                                    if (orderStorage == null) {
                                        if (price < currentPrice) {
                                            orderStorage = new GridOrderProd(price);
                                            Order orderNew = grid.newOrder(symbol, OrderSide.BUY, price, null);
                                            if (orderNew != null) {
                                                orderStorage.orderBuy = orderNew;
                                                grid.price2Order.put(price, orderStorage);
                                                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, grid.symbol, Utils.toJson(grid));
                                            }
                                        }
                                    } else {
                                        if (orderStorage.orderBuy == null) {
                                            if (orderStorage.orderSell != null) {
                                                LOG.info("Error order grid: {} {} {}", grid.symbol, grid.side, price);
                                            }
                                        } else {
                                            if (StringUtils.equalsIgnoreCase(orderStorage.orderBuy.getStatus(), OrderStatus.FILLED.toString())) {
                                                if (orderStorage.orderSell == null) {
                                                    Order orderNew = grid.newOrder(symbol, OrderSide.SELL, grid.prices.get(i + 1), null);
                                                    if (orderNew != null) {
                                                        orderStorage.orderSell = orderNew;
                                                        grid.price2Order.put(price, orderStorage);
                                                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, grid.symbol, Utils.toJson(grid));
                                                    }
                                                } else {
                                                    if (StringUtils.equalsIgnoreCase(orderStorage.orderSell.getStatus(), OrderStatus.FILLED.toString())) {
                                                        if (price < currentPrice) {
                                                            orderStorage = new GridOrderProd(price);
                                                            Order orderNew = grid.newOrder(symbol, OrderSide.BUY, price, null);
                                                            if (orderNew != null) {
                                                                orderStorage.orderBuy = orderNew;
                                                                grid.price2Order.put(price, orderStorage);
                                                                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, grid.symbol, Utils.toJson(grid));
                                                            }
                                                        }
                                                    } else {
                                                        if (!orderLimitSells.contains(orderStorage.orderSell.getClientOrderId())) {
                                                            orderStorage.orderSell = GridFuturesClientSingleton.getInstance().readOrder(orderStorage.orderSell.getSymbol(),
                                                                    orderStorage.orderSell.getClientOrderId());
                                                            if (StringUtils.equalsIgnoreCase(orderStorage.orderSell.getStatus(), OrderStatus.FILLED.toString())) {
                                                                if (price < currentPrice) {
                                                                    orderStorage = new GridOrderProd(price);
                                                                    Order orderNew = grid.newOrder(symbol, OrderSide.BUY, price, null);
                                                                    if (orderNew != null) {
                                                                        orderStorage.orderBuy = orderNew;
                                                                        grid.price2Order.put(price, orderStorage);
                                                                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, grid.symbol, Utils.toJson(grid));
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            } else {
                                                if (!orderLimitBuys.contains(orderStorage.orderBuy.getClientOrderId())) {
                                                    orderStorage.orderBuy = GridFuturesClientSingleton.getInstance().readOrder(orderStorage.orderBuy.getSymbol(),
                                                            orderStorage.orderBuy.getClientOrderId());
                                                    if (StringUtils.equalsIgnoreCase(orderStorage.orderBuy.getStatus(), OrderStatus.FILLED.toString())) {
                                                        if (orderStorage.orderSell == null) {
                                                            Order orderNew = grid.newOrder(symbol, OrderSide.SELL, grid.prices.get(i + 1), null);
                                                            if (orderNew != null) {
                                                                orderStorage.orderSell = orderNew;
                                                                grid.price2Order.put(price, orderStorage);
                                                                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, grid.symbol, Utils.toJson(grid));
                                                            }
                                                        } else {
                                                            if (StringUtils.equalsIgnoreCase(orderStorage.orderSell.getStatus(), OrderStatus.FILLED.toString())) {
                                                                if (price < currentPrice) {
                                                                    orderStorage = new GridOrderProd(price);
                                                                    Order orderNew = grid.newOrder(symbol, OrderSide.BUY, price, null);
                                                                    if (orderNew != null) {
                                                                        orderStorage.orderBuy = orderNew;
                                                                        grid.price2Order.put(price, orderStorage);
                                                                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, grid.symbol, Utils.toJson(grid));
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            } else { // for SELL
                                if (currentPrice > grid.maxPrice) {
                                    LOG.info("Extend price end: {} {} {}", grid.minPrice, grid.minPrice * 0.8);
                                    grid.maxPrice = grid.maxPrice * 1.2;
                                    grid.updatePriceBefore();
                                    grid.updatePriceActive(currentPrice);
                                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, grid.symbol, Utils.toJson(grid));
                                }
                                if (currentPrice < grid.minPrice) {
                                    LOG.info("Close grid: {} {} min: {} max: {} current:{}", grid.symbol, grid.side,
                                            grid.minPrice, grid.maxPrice, currentPrice);
                                    closeGridRunning(grid, position, orders);
                                    continue;
                                }
                                LOG.info("Grid : {} {} {} {} entry/mark: {}/{}", grid.side, symbol, quantityBuy,
                                        position.getPositionAmt().doubleValue() * 1E9,
                                        position.getEntryPrice().doubleValue(),
                                        position.getMarkPrice().doubleValue());
                                Double quantityBuyLong = quantityBuy;
                                Double quantityPosition = -position.getPositionAmt().doubleValue() * 1E9;
                                if (quantityBuyLong.longValue() != quantityPosition.longValue()) {
                                    LOG.info("Grid order buy not match position: {} {} {}", symbol, quantityBuyLong, quantityPosition);
                                }
                                for (int i = 0; i < grid.prices.size() - 1; i++) {
                                    Double price = grid.prices.get(i);
                                    GridOrderProd orderStorage = grid.price2Order.get(price);
                                    if (orderStorage == null) {
                                        if (price > currentPrice) {
                                            orderStorage = new GridOrderProd(price);
                                            Order orderNew = grid.newOrder(symbol, OrderSide.SELL, price, null);
                                            if (orderNew != null) {
                                                orderStorage.orderSell = orderNew;
                                                grid.price2Order.put(price, orderStorage);
                                                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, grid.symbol, Utils.toJson(grid));
                                            }
                                        }
                                    } else {
                                        if (orderStorage.orderSell == null) {
                                            if (orderStorage.orderBuy != null) {
                                                LOG.info("Error order grid: {} {} {}", grid.symbol, grid.side, price);
                                            }
                                        } else {
                                            if (StringUtils.equalsIgnoreCase(orderStorage.orderSell.getStatus(), OrderStatus.FILLED.toString())) {
                                                if (orderStorage.orderBuy == null) {
                                                    Order orderNew = grid.newOrder(symbol, OrderSide.BUY, grid.prices.get(i + 1), null);
                                                    if (orderNew != null) {
                                                        orderStorage.orderBuy = orderNew;
                                                        grid.price2Order.put(price, orderStorage);
                                                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, grid.symbol, Utils.toJson(grid));
                                                    }
                                                } else {
                                                    if (StringUtils.equalsIgnoreCase(orderStorage.orderBuy.getStatus(), OrderStatus.FILLED.toString())) {
                                                        if (price < currentPrice) {
                                                            orderStorage = new GridOrderProd(price);
                                                            Order orderNew = grid.newOrder(symbol, OrderSide.SELL, price, null);
                                                            if (orderNew != null) {
                                                                orderStorage.orderSell = orderNew;
                                                                grid.price2Order.put(price, orderStorage);
                                                                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, grid.symbol, Utils.toJson(grid));
                                                            }
                                                        }
                                                    } else {
                                                        if (!orderLimitBuys.contains(orderStorage.orderBuy.getClientOrderId())) {
                                                            orderStorage.orderBuy = GridFuturesClientSingleton.getInstance().readOrder(orderStorage.orderBuy.getSymbol(),
                                                                    orderStorage.orderBuy.getClientOrderId());
                                                            if (StringUtils.equalsIgnoreCase(orderStorage.orderBuy.getStatus(), OrderStatus.FILLED.toString())) {
                                                                if (price > currentPrice) {
                                                                    orderStorage = new GridOrderProd(price);
                                                                    Order orderNew = grid.newOrder(symbol, OrderSide.SELL, price, null);
                                                                    if (orderNew != null) {
                                                                        orderStorage.orderSell = orderNew;
                                                                        grid.price2Order.put(price, orderStorage);
                                                                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, grid.symbol, Utils.toJson(grid));
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            } else {
                                                if (!orderLimitSells.contains(orderStorage.orderSell.getClientOrderId())) {
                                                    orderStorage.orderSell = GridFuturesClientSingleton.getInstance().readOrder(orderStorage.orderSell.getSymbol(),
                                                            orderStorage.orderSell.getClientOrderId());
                                                    if (StringUtils.equalsIgnoreCase(orderStorage.orderSell.getStatus(), OrderStatus.FILLED.toString())) {
                                                        if (orderStorage.orderBuy == null) {
                                                            Order orderNew = grid.newOrder(symbol, OrderSide.BUY, grid.prices.get(i + 1), null);
                                                            if (orderNew != null) {
                                                                orderStorage.orderBuy = orderNew;
                                                                grid.price2Order.put(price, orderStorage);
                                                                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, grid.symbol, Utils.toJson(grid));
                                                            }
                                                        } else {
                                                            if (StringUtils.equalsIgnoreCase(orderStorage.orderBuy.getStatus(), OrderStatus.FILLED.toString())) {
                                                                if (price > currentPrice) {
                                                                    orderStorage = new GridOrderProd(price);
                                                                    Order orderNew = grid.newOrder(symbol, OrderSide.SELL, price, null);
                                                                    if (orderNew != null) {
                                                                        orderStorage.orderSell = orderNew;
                                                                        grid.price2Order.put(price, orderStorage);
                                                                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, grid.symbol, Utils.toJson(grid));
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            LOG.info("Finish update grid running {}s", (System.currentTimeMillis() - startTime) / Utils.TIME_SECOND);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void closeGridRunning(GridObjectProduction grid, PositionRisk position, List<Order> orders) {
        closeGrid(grid);
        if (position.getSymbol() != null && position.getPositionAmt().doubleValue() != 0) {
            PositionHelper.closePositionGrid(position);
        }
        closeOpenOrder(orders);
    }

    private void closeOpenOrder(List<Order> orders) {
        for (Order order : orders) {
            GridFuturesClientSingleton.getInstance().cancelOrder(order.getSymbol(), order.getClientOrderId());
        }
    }


    private void closeGrid(GridObjectProduction grid) {
        try {
            RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, grid.symbol);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
