package com.binance.chuyennd.trading.grid;

import com.binance.chuyennd.position.manager.PositionHelper;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.trading.BudgetManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderType;
import com.binance.client.model.trade.Asset;
import com.binance.client.model.trade.Order;
import com.binance.client.model.trade.PositionRisk;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;

public class CreateGridProductionByHand {
    public static final Logger LOG = LoggerFactory.getLogger(CreateGridProductionByHand.class);

    public static void main(String[] args) {
//        List<Order> orders = GridFuturesClientSingleton.getInstance().getOpenOrders(Constants.SYMBOL_PAIR_XRP);
//        for (Order order : orders) {
//            if (order.getPrice().doubleValue() == 2.4399) {
//                GridFuturesClientSingleton.getInstance().cancelOrder(order.getSymbol(), order.getClientOrderId());
//                break;
//            }
//        }
//        List<PositionRisk> positions = GridFuturesClientSingleton.getInstance().getAllPositionInfos();
//        for (PositionRisk position : positions) {
//            if (position.getSymbol().equals(Constants.SYMBOL_PAIR_ETH)) {
//                LOG.info("{} {} {} {} {}", position.getSymbol(), position.getEntryPrice().doubleValue(),
//                        position.getMarkPrice().doubleValue(), position.getPositionAmt().doubleValue(), position.getLeverage().doubleValue());
//                PositionHelper.closePositionGrid(position);
//            }
//        }

//        // create order by hand

//        BudgetManager.getInstance().balanceBasic = 500d;
//        System.out.println(BudgetManager.getInstance().getBudgetGrid());
//        String symbol = "XRPUSDT";
//        Configs.LEVERAGE_ORDER = 10;
//        System.out.println(BudgetManager.getInstance().getLeverage(symbol));
//        SimpleMovingAverageDayManagerProduction.getInstance().printMaDif("XRPUSDT");
//
//        GridObjectProduction grid = GridDetectorProd.findRange2RunProd("ETHUSDT");
//
//        System.out.println(grid.maxPrice + "-" + grid.minPrice);
//        new GridTradingManager().processGridNew(grid);
//        for (String symbol:RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO)){
//            String orderJson = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, symbol);
//            if (StringUtils.isNotBlank(orderJson)) {
//                GridObjectProduction grid = Utils.gson.fromJson(orderJson, GridObjectProduction.class);
//                LOG.info("{}", Utils.toJson(grid.prices));
//                LOG.info("{} {} {} {}", symbol, grid.quantity, grid.priceStartGrid, grid.pricesActive);
//            }
//        }

//        new GridTradingManager().processUpdateAllGridRunning();

//        closePositionRunning(symbol);
//        GridFuturesClientSingleton.getInstance().cancelOrder("XRPUSDT", "UJdTtGJNvqRKvQs0PiLYzm");
//        fixData(symbol);
//
        Asset umGridInfo = GridFuturesClientSingleton.getInstance().getAccountUMInfo();
        LOG.info("{} {} {} {}", umGridInfo.getAvailableBalance().doubleValue(),
                umGridInfo.getCrossUnPnl().doubleValue(), umGridInfo.getWalletBalance().doubleValue(),
                umGridInfo.getMarginBalance().doubleValue());
    }

    private static void fixData(String symbol) {

//        List<Order> ordersOpen = GridFuturesClientSingleton.getInstance().getAllOpenOrderInfos();
//        Map<String, Order> id2Order = new HashMap<>();
//        for (Order order : ordersOpen) {
//            id2Order.put(order.getClientOrderId(), order);
//            LOG.info("{} {} {} {}", order.getClientOrderId(), order.getPrice(), order.getSide(), Utils.normalizeDateYYYYMMDDHHmm(order.getUpdateTime()));
//        }
        String orderJson = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_SYMBOL_2_GRID_INFO, symbol);
//        System.out.println(orderJson);
//        if (StringUtils.isNotBlank(orderJson)) {
//            GridObjectProduction grid = Utils.gson.fromJson(orderJson, GridObjectProduction.class);
//            for (Double price : grid.price2Order.keySet()) {
//                GridOrderProd order = grid.price2Order.get(price);
//                if (order.orderSell != null) {
//                    LOG.info("Grid: {} {} {} {} {} {}", order.orderBuy.getClientOrderId(), order.orderBuy.getPrice(),
//                            order.orderBuy.getSide(), Utils.normalizeDateYYYYMMDDHHmm(order.orderBuy.getUpdateTime())
//                            , order.orderSell.getClientOrderId(), order.orderSell.getPrice());
//                }else{
//                    LOG.info("Grid: {} {} {} {} {} {}", order.orderBuy.getClientOrderId(), order.orderBuy.getPrice(),
//                            order.orderBuy.getSide(), Utils.normalizeDateYYYYMMDDHHmm(order.orderBuy.getUpdateTime())                            );
//                }
//            }
//        }
        if (StringUtils.isNotBlank(orderJson)) {
            GridObjectProduction grid = Utils.gson.fromJson(orderJson, GridObjectProduction.class);
//            System.out.println(Utils.normalizeDateYYYYMMDDHHmm(grid.startTime));
            for (Double price : grid.price2Order.keySet()) {
                GridOrderProd order = grid.price2Order.get(price);
                if (order.orderBuy != null && StringUtils.equals(order.orderBuy.getClientOrderId(), "6TSo7hDEc8fqXjo2n6jDeW")) {
                    LOG.info("price: {}", price);
                }
            }
        }
    }

    private static void closePositionRunning(String symbol) {

        List<Order> ordersOpen = GridFuturesClientSingleton.getInstance().getAllOpenOrderInfos();
        List<Order> ordersOfSymbol = new ArrayList<>();
        PositionRisk positionOfSymbol = null;
        List<PositionRisk> positions = GridFuturesClientSingleton.getInstance().getAllPositionInfos();
        for (PositionRisk position : positions) {
            if (position.getSymbol().equals(symbol)) {
                positionOfSymbol = position;
                break;
            }
        }
        for (Order order : ordersOpen) {
            if (StringUtils.equals(order.getType(), OrderType.LIMIT.toString())) {
                if (order.getSymbol().equals(symbol)) {
                    ordersOfSymbol.add(order);
                }
            }
        }
        GridTradingManager trading = new GridTradingManager();
        GridObjectProduction grid = trading.getGridInfo(symbol);
        if (grid != null) {
            trading.closeGridRunning(grid, positionOfSymbol, ordersOfSymbol);
        }
    }
}
