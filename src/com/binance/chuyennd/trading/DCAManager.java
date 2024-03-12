/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.trading;

import com.binance.chuyennd.client.BinanceFuturesClientSingleton;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.client.OrderHelper;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.trade.Asset;
import com.binance.client.model.trade.Order;
import com.binance.client.model.trade.PositionRisk;
import java.io.File;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import org.apache.commons.io.FileUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class DCAManager {

    public static final Logger LOG = LoggerFactory.getLogger(DCAManager.class);
    public static Map<Integer, Integer> level2Rate = new HashMap<>();
    public static final String FILE_STORAGE_ORDER_DCA = "storage/OrderDCA.data";
    public Double RATE_BALANCE_AVALIBLE_MIN2DCA = Configs.getDouble("RATE_BALANCE_AVALIBLE_MIN2DCA");

    static {
        level2Rate.put(0, 13);
        level2Rate.put(1, 20);
        level2Rate.put(2, 30);
        level2Rate.put(3, 40);
        level2Rate.put(4, 60);
    }

    public static void main(String[] args) {

//        testDCAWithBudget();
        checkAndDcaOrder();
    }

    private static void dcaForOrder(OrderTargetInfo order) {
        try {
            Order orderInfo = OrderHelper.newOrderMarket(order.symbol, order.side, order.quantity, BudgetManager.getInstance().getLeverage());
            if (orderInfo != null) {
                List<String> lines = new ArrayList<>();
                lines.add(Utils.toJson(order));

                //cancel order tp old
                List<Order> orderOpens = BinanceFuturesClientSingleton.getInstance().getOpenOrders(order.symbol);
                for (Order orderOpen : orderOpens) {
                    Utils.sendSms2Telegram("Cancel order: " + order.orderTakeProfit.getOrderId() + " of " + order.symbol);
                    LOG.info("Cancel order: " + order.orderTakeProfit.getOrderId() + " of " + order.symbol);
                    ClientSingleton.getInstance().syncRequestClient.cancelOrder(order.symbol,
                            orderOpen.getOrderId(), orderOpen.getOrderId().toString());
                }
                // re create tp
                PositionRisk pos = BinanceFuturesClientSingleton.getInstance().getPositionInfo(order.symbol);
                if (pos != null && pos.getPositionAmt().doubleValue() != 0) {
                    order.priceEntry = pos.getEntryPrice().doubleValue();
                    order.quantity = Math.abs(pos.getPositionAmt().doubleValue());
                    lines.add(Utils.toJson(order));
                    new BinanceOrderTradingManager().createTp(order);
                }
                FileUtils.writeLines(new File(FILE_STORAGE_ORDER_DCA), lines, true);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void testDCAWithBudget() {
        Double currentBudget = 10d;
        Integer levelBudget = -1;
        for (int i = 0; i < 1000; i++) {
            Integer level = getLevelBudget(currentBudget + i);
//            LOG.info(" {} -> {}", currentBudget + i, level);
            if (!Objects.equals(levelBudget, level)) {
                levelBudget = level;
                LOG.info("current: {} budget: {} level: {} rate2Dca: {}", currentBudget + i,
                        BudgetManager.getInstance().getBudget(), level, getRateDcaWithBudget(currentBudget + i));
            }
        }
    }

    private static Integer getLevelBudget(Double budgetOfOrder) {
        return budgetOfOrder.intValue() / BudgetManager.getInstance().getBudget().intValue();
    }

    private static Integer getRateDcaWithBudget(Double budgetOfOrder) {
        Integer level = getLevelBudget(budgetOfOrder);
        if (level >= 4) {
            return 60;
        }
        return level2Rate.get(level);
    }

    private static void checkAndDcaOrder() {
        Map<String, Double> sym2LastPrice = TickerFuturesHelper.getAllLastPrice();
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER)) {
            OrderTargetInfo order = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, symbol),
                    OrderTargetInfo.class);
            Double budgetOfOrder = callBudgetOfOrder(order);
            Integer levelDca = getLevelBudget(budgetOfOrder);
            Integer rate2Dca = getRateDcaWithBudget(budgetOfOrder);
            Double rateLoss = getRateLoss(order, sym2LastPrice);
            if (Math.abs(rateLoss) * 100 >= rate2Dca.doubleValue()) {
                LOG.info("Dca for {} budgetOrder:{} budget:{} entry: {} lastprice: {} rateLoss: {} levelDca: {} rateDca: {} quantity: {}",
                        order.symbol, budgetOfOrder, BudgetManager.getInstance().getBudget(), order.priceEntry,
                        sym2LastPrice.get(order.symbol), rateLoss * 100, levelDca, rate2Dca, order.quantity);
                dcaForOrder(order);
            } else {
//                LOG.info("Not Dca for {} entry: {} lastprice: {} rateLoss: {} levelDca: {} rateDca: {} quantity: {}",
//                        order.symbol, order.priceEntry, sym2LastPrice.get(order.symbol), rateLoss * 100, levelDca, rate2Dca, order.quantity);
            }
        }
    }

    private static Double callBudgetOfOrder(OrderTargetInfo order) {
        return order.priceEntry * order.quantity / order.leverage;
    }

    private static Double getRateLoss(OrderTargetInfo order, Map<String, Double> sym2LastPrice) {
        return Utils.rateOf2Double(sym2LastPrice.get(order.symbol), order.priceEntry);
    }

    public void startThreadDca() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadDCA");
            LOG.info("Start thread ThreadDCA!");
            while (true) {

                try {
                    Thread.sleep(Utils.TIME_HOUR);
                    Double rate = rateBalanceAvalible();
                    if (rate == null || rate < RATE_BALANCE_AVALIBLE_MIN2DCA) {
                        LOG.info("Not dca process because rate balance avalible not enough {}/{}", rate, RATE_BALANCE_AVALIBLE_MIN2DCA);
                        continue;
                    }
                    checkAndDcaOrder();
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadDCA: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private Double rateBalanceAvalible() {
        try {
            Asset asset = BinanceFuturesClientSingleton.getInstance().getAccountUMInfo();
            if (asset != null) {
                return asset.getAvailableBalance().doubleValue() * 100 / asset.getWalletBalance().doubleValue();
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        return null;
    }

}
