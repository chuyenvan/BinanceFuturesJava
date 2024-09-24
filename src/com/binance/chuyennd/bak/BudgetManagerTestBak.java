///*
// * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
// * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
// */
//package com.binance.chuyennd.research;
//
//import com.binance.chuyennd.redis.RedisConst;
//import com.binance.chuyennd.redis.RedisHelper;
//import com.binance.chuyennd.utils.Configs;
//import com.binance.chuyennd.utils.Utils;
//import org.apache.commons.io.FileUtils;
//import org.apache.commons.lang.StringUtils;
//import org.slf4j.Logger;
//import org.slf4j.LoggerFactory;
//
//import java.io.File;
//import java.io.IOException;
//import java.util.ArrayList;
//import java.util.List;
//import java.util.Map;
//import java.util.Set;
//import java.util.concurrent.ConcurrentHashMap;
//
///**
// * @author pc
// */
//public class BudgetManagerTestBak {
//
//    public static final Logger LOG = LoggerFactory.getLogger(BudgetManagerTestBak.class);
//    private static volatile BudgetManagerTestBak INSTANCE = null;
//    public BalanceIndex balanceIndex = new BalanceIndex();
//    public Double MAX_CAPITAL_RATE = Configs.getDouble("MAX_CAPITAL_RATE");
//    public Double RATE_BUDGET_PER_ORDER = Configs.getDouble("RATE_BUDGET_PER_ORDER");
//    public Integer LEVERAGE_ORDER = Configs.getInt("LEVERAGE_ORDER");
//    public Double BUDGET_PER_ORDER;
//    public Double investing = null;
//    //    public Double balanceStart = 10000d;
//    public Double totalFee = 0d;
//    public Double balanceStart = Configs.getDouble("CAPITAL_START");
//    public Double balanceCurrent = balanceStart;
//    //    public Long timeStart = 1640970000000L;
//    public Long lastTimeUpdate = null;
//
//    public boolean stop = false;
//
//
//    public static BudgetManagerTestBak getInstance() {
//        if (INSTANCE == null) {
//            INSTANCE = new BudgetManagerTestBak();
//            INSTANCE.updateBudget();
//        }
//        return INSTANCE;
//    }
//
//    private void updateBudget() {
//        try {
//            Double budget = RATE_BUDGET_PER_ORDER * balanceCurrent;
//            BUDGET_PER_ORDER = budget / 100;
//            if (BUDGET_PER_ORDER < 7) {
//                BUDGET_PER_ORDER = 7.0;
//            }
//            if (BUDGET_PER_ORDER > 1000) {
//                BUDGET_PER_ORDER = 1000.0;
//            }
////            LOG.info("Ba and Bu to t: {} -> {}", balanceCurrent, BUDGET_PER_ORDER);
//
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
//    }
//
//    public Double getBudget() {
//        return BUDGET_PER_ORDER;
//    }
//
//    public Double getBudgetNew() {
//        Double budget = BUDGET_PER_ORDER;
//        BUDGET_PER_ORDER = BUDGET_PER_ORDER * (100 - 1) / 100;
//        return budget;
//    }
//
//    public Double getInvesting() {
//        if (investing == null) {
//            Double margin = calPositionMargin(getListOrderRunning());
//            investing = margin * 100 / balanceCurrent;
//        }
//        return investing;
//    }
//
//    public Integer getLeverage() {
//        return LEVERAGE_ORDER;
//    }
//
//    public void updateBalance(Long timeUpdate, ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone) {
//        Double balance = balanceStart;
//        Double profit = 0d;
//        Double profitOfDate = 0d;
//
//        if (allOrderDone != null) {
//            for (Map.Entry<String, OrderTargetInfoTest> entry : allOrderDone.entrySet()) {
//                String key = entry.getKey();
//                OrderTargetInfoTest orderInfo = entry.getValue();
//                if (Utils.getDate(Long.parseLong(key.split("-")[0])) == (timeUpdate - Utils.TIME_DAY)) {
//                    profitOfDate += calTp(orderInfo);
//                }
//                profit += calTp(orderInfo);
//            }
//        }
//
//
//        Set<String> symbolRunning = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER);
//
//        totalFee = profit * 0.2;
//        balance = balance + profit - totalFee;
//        balanceCurrent = balance;
//        List<OrderTargetInfoTest> orderInfos = getListOrderRunning();
//        Double unrealizedProfit = calUnrealizedProfit(orderInfos);
//        Double unrealizedProfitMin = calUnrealizedProfitMin(orderInfos);
//        Double positionMargin = calPositionMargin(orderInfos);
//        Double balanceReal = balance + unrealizedProfit;
//        Double balanceMin = balance + unrealizedProfitMin;
//        balanceIndex.updateIndex(balance, balanceMin, positionMargin, unrealizedProfit, timeUpdate);
//        if (timeUpdate % Utils.TIME_DAY == 0) {
//            LOG.info("Update balance {} => balance:{} real:{} balanceMin:{} margin:{} " +
//                            "profit:{} pDate:{} unProfit:{} fee:{} done: {} running:{}",
//                    Utils.normalizeDateYYYYMMDDHHmm(timeUpdate), balance.longValue(), balanceReal.longValue(),
//                    balanceMin.longValue(), positionMargin.longValue(), profit.longValue(),
//                    profitOfDate.longValue(), unrealizedProfit.longValue(), totalFee.longValue(), allOrderDone.size(), symbolRunning.size());
//            if (timeUpdate.equals(Utils.getToDay() + 7 * Utils.TIME_HOUR)) {
//                LOG.info("Update report: {}", Utils.normalizeDateYYYYMMDDHHmm(timeUpdate));
//                List<String> lines = new ArrayList<>();
//                StringBuilder builder = new StringBuilder();
//                builder.append("capital: ").append(MAX_CAPITAL_RATE).append(" rateBudget: ").append(RATE_BUDGET_PER_ORDER);
//                builder.append(" balance: ").append(balance.longValue());
//                builder.append(" balanceReal: ").append(balanceReal.longValue());
//                builder.append(" balanceMin: ").append(balanceMin.longValue());
//                builder.append(" done: ").append(allOrderDone.size());
//                builder.append(" " + balanceIndex.balanceMin + " " + balanceIndex.rateBalanceMin + " " +
//                        Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeBalanceMin) + " " + balanceIndex.marginMax +
//                        " " + balanceIndex.rateMarginMax + " " + Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeMarginMax) + " " +
//                        balanceIndex.unProfitMax + " " + balanceIndex.rateUnProfitMax + " " +
//                        Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeRateUnProfitMax));
//                lines.add(builder.toString());
//                try {
//                    FileUtils.writeLines(new File("storage/report.txt"), lines, true);
//                } catch (IOException e) {
//                    e.printStackTrace();
//                }
//            }
//        }
//        if ((balance + unrealizedProfitMin) < 0) {
//            stop = true;
//            LOG.info("Chay tai khoan {} -----------------------------------!", Utils.normalizeDateYYYYMMDDHHmm(timeUpdate));
//        }
//        updateBudget();
//    }
//
//    public List<String> marginHealthCheck(Long timeUpdate) {
//        LOG.info("Margin health check! {}", Utils.normalizeDateYYYYMMDDHHmm(timeUpdate));
//        List<String> symbol2StopLoss = new ArrayList<>();
//        List<OrderTargetInfoTest> orderInfos = getListOrderRunning();
//        Double unrealizedProfit = calUnrealizedProfit(orderInfos);
//        Double positionMargin = calPositionMargin(orderInfos);
//        while (positionMargin / balanceCurrent > 0.2
//                && -unrealizedProfit / positionMargin > 2) {
//            Long timeMin = null;
//            int indexMin = 0;
//            for (int i = 0; i < orderInfos.size(); i++) {
//                OrderTargetInfoTest order = orderInfos.get(i);
//                if (timeMin == null || timeMin < order.timeStart) {
//                    timeMin = order.timeStart;
//                    indexMin = i;
//                }
//            }
//            OrderTargetInfoTest order2Cancel = orderInfos.get(indexMin);
//            symbol2StopLoss.add(order2Cancel.symbol);
//            orderInfos.remove(indexMin);
//            unrealizedProfit = calUnrealizedProfit(orderInfos);
//            positionMargin = calPositionMargin(orderInfos);
//        }
//        return symbol2StopLoss;
//    }
//
//
//    public List<OrderTargetInfoTest> getListOrderRunning() {
//        List<OrderTargetInfoTest> results = new ArrayList<>();
//        Set<String> symbolsRunning = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER);
//        for (String symbol : symbolsRunning) {
//            String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER, symbol);
//            if (StringUtils.isNotEmpty(json)) {
//                OrderTargetInfoTest orderInfo = Utils.gson.fromJson(json, OrderTargetInfoTest.class);
//                if (orderInfo != null) {
//                    results.add(orderInfo);
//                }
//            }
//        }
//        return results;
//    }
//
//    public Double calUnrealizedProfit(List<OrderTargetInfoTest> orderInfos) {
//        Double result = 0d;
//        for (OrderTargetInfoTest orderInfo : orderInfos) {
//            Double profit = orderInfo.calProfit();
//            result += profit;
//        }
//        return result;
//    }
//
//    public Double calUnrealizedProfitMin(List<OrderTargetInfoTest> orderInfos) {
//        Double result = 0d;
//        for (OrderTargetInfoTest orderInfo : orderInfos) {
//            Double profit = orderInfo.calProfitMin();
//            result += profit;
//        }
//        return result;
//    }
//
//    public Double calPositionMargin(List<OrderTargetInfoTest> orderInfos) {
//        Double totalMargin = 0d;
//        for (OrderTargetInfoTest orderInfo : orderInfos) {
//            Double margin = orderInfo.calMargin();
//            totalMargin += margin;
//        }
//        return totalMargin;
//    }
//
//    private Double calTp(OrderTargetInfoTest orderInfo) {
//        Double tp = orderInfo.quantity * (orderInfo.priceTP - orderInfo.priceEntry);
//        return tp;
//    }
//
//    public void updateInvesting() {
//        Double margin = calPositionMargin(getListOrderRunning());
//        investing = margin * 100 / balanceCurrent;
//    }
//
//    public void printBalanceIndex() {
//        LOG.info("BalanceMin: {} {} {} MarginMax: {} {} {} unProfitMax: {} {} {}",
//                balanceIndex.balanceMin, balanceIndex.rateBalanceMin, Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeBalanceMin),
//                balanceIndex.marginMax, balanceIndex.rateMarginMax, Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeMarginMax),
//                balanceIndex.unProfitMax, balanceIndex.rateUnProfitMax, Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeRateUnProfitMax)
//        );
//    }
//
//    public void resetCapitalAndRateBudget(Double capital, Double rateBudget) {
//        RATE_BUDGET_PER_ORDER = rateBudget;
//        MAX_CAPITAL_RATE = capital;
//        balanceCurrent = balanceStart;
//    }
//}
