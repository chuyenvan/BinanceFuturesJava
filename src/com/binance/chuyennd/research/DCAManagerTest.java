///*
// * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
// * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
// */
//package com.binance.chuyennd.research;
//
//import com.binance.chuyennd.utils.Utils;
//import com.binance.client.model.enums.OrderSide;
//
//import java.util.HashMap;
//import java.util.Map;
//
//import org.slf4j.Logger;
//import org.slf4j.LoggerFactory;
//
///**
// * @author pc
// */
//public class DCAManagerTest {
//
//    public static final Logger LOG = LoggerFactory.getLogger(DCAManagerTest.class);
//    public static Map<Integer, Integer> level2Rate = new HashMap<>();
//
//    static {
//        level2Rate.put(0, 50);
//        level2Rate.put(1, 99);
//        level2Rate.put(2, 99);
//        level2Rate.put(3, 99);
//    }
//
//    public static void main(String[] args) {
//    }
//
//    private static Double calPriceDca(double priceOld, double priceNew) {
//        return (priceNew + priceOld) / 2;
//    }
//
//    public static Double getMinRateDCA() {
//        return level2Rate.get(0).doubleValue();
//    }
//
//    public static Integer getLevelBudget(Double budgetOfOrder) {
//        return budgetOfOrder.intValue() / BudgetManagerTest.getInstance().getBudget().intValue();
//    }
//
//    public static Integer getRateDcaWithBudget(Double budgetOfOrder) {
//        Integer level = getLevelBudget(budgetOfOrder);
//        return getRateOfLevel(level);
//    }
//
//    public static Integer getRateOfLevel(Integer level) {
//        if (level >= 3) {
//            return 99;
//        }
//        return level2Rate.get(level);
//    }
//
//    public static void checkAndDcaOrder(OrderTargetInfoTest orderInfo, Double rateTarget) {
//        try {
////            Double budgetOfOrder = callBudgetOfOrder(orderInfo);
////            Integer levelDca = getLevelBudget(budgetOfOrder);
////            LOG.info("Level dca: {} budgetPos: {} BudgetCurrent: {}", orderInfo.symbol,
////                    budgetOfOrder, BudgetManagerTest.getInstance().getBudget());
////            Integer rate2Dca = getRateDcaWithBudget(budgetOfOrder);
//            Integer levelDca = orderInfo.dcaLevel;
//            if (levelDca == null) {
//                levelDca = 0;
//            }else{
//                levelDca = 10;
//            }
//            Integer rate2Dca = getRateOfLevel(levelDca);
//
//            Double rateLoss = Math.abs(Utils.rateOf2Double(orderInfo.lastPrice, orderInfo.priceEntry));
//            if (Math.abs(rateLoss) * 100 >= rate2Dca.doubleValue()) {
//                LOG.info("Dca for {} margin:{} budget:{} entry: {} lastprice: {} rateLoss: {} levelDca: {} rateDca: {} quantity: {}",
//                        orderInfo.symbol, orderInfo.calMargin(), BudgetManagerTest.getInstance().getBudget(), orderInfo.priceEntry,
//                        orderInfo.lastPrice, rateLoss * 100, levelDca, rate2Dca, orderInfo.quantity);
//                orderInfo.quantity *= 2;
//                orderInfo.priceEntry = calPriceDca(orderInfo.priceEntry, orderInfo.lastPrice);
//                Double priceTp = Utils.calPriceTarget(orderInfo.symbol, orderInfo.priceEntry, OrderSide.BUY, rateTarget);
//                orderInfo.priceTP = priceTp;
//                if (orderInfo.dcaLevel == null) {
//                    orderInfo.dcaLevel = 0;
//                }
//                orderInfo.dcaLevel++;
//                LOG.info("After dca {} entry: {} tp: {} quantity: {} {}",
//                        orderInfo.symbol, orderInfo.priceEntry, orderInfo.priceTP, orderInfo.quantity, Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeUpdate));
//                BudgetManagerTest.getInstance().updateInvesting();
//            } else {
////                LOG.info("Not Dca for {} entry: {} lastprice: {} rateLoss: {} levelDca: {} rateDca: {} quantity: {}",
////                        orderInfo.symbol, orderInfo.priceEntry, orderInfo.lastPrice,
////                        rateLoss * 100, levelDca, rate2Dca, orderInfo.quantity);
//            }
//
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
//    }
//
//
//}
