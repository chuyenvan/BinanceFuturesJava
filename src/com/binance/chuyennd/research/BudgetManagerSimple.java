/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * @author pc
 */
public class BudgetManagerSimple {

    public static final Logger LOG = LoggerFactory.getLogger(BudgetManagerSimple.class);
    private static volatile BudgetManagerSimple INSTANCE = null;
    public BalanceIndex balanceIndex = new BalanceIndex();
    public Double MAX_CAPITAL_RATE = Configs.getDouble("MAX_CAPITAL_RATE");
    public Double RATE_FEE = Configs.getDouble("RATE_FEE");
    public Double RATE_BUDGET_PER_ORDER = Configs.getDouble("RATE_BUDGET_PER_ORDER");
    public Integer number_order_budget = 100;
    public Integer LEVERAGE_ORDER = Configs.getInt("LEVERAGE_ORDER");
    public Double BUDGET_PER_ORDER;
    public Double investing = null;
    public Double unProfit = 0d;
    public Double totalFee = 0d;
    public Double balanceStart = Configs.getDouble("CAPITAL_START");
    public Double balanceCurrent = balanceStart;

    public boolean stop = false;


    public static BudgetManagerSimple getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new BudgetManagerSimple();
            INSTANCE.updateBudget(null);
        }
        return INSTANCE;
    }

    private void updateBudget(ConcurrentHashMap<String, OrderTargetInfoTest> orderRunning) {
        investing = 0d;
        try {
            Double positionMargin = 0d;
            if (orderRunning != null) {
                positionMargin = calPositionMargin(orderRunning.values());
            }
            Double budget = RATE_BUDGET_PER_ORDER * (balanceCurrent - positionMargin);
            BUDGET_PER_ORDER = budget / number_order_budget;

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public Double getBudget() {
        Double budget = BUDGET_PER_ORDER;
//        if (budget >=5000){
//            budget = 5000d;
//        }
        BUDGET_PER_ORDER = BUDGET_PER_ORDER * (number_order_budget - 1) / number_order_budget;

        return budget;
    }

    public Boolean isAvailableTrade() {
        return investing < MAX_CAPITAL_RATE;
    }


    public Integer getLeverage() {
        return LEVERAGE_ORDER;
    }

    public void updateBalance(Long timeUpdate, ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone,
                              ConcurrentHashMap<String, OrderTargetInfoTest> orderRunning) {
        Double balance = balanceStart;
        Double profit = 0d;
        Double profitOfDate = 0d;
        Double fee = 0d;
        int totalSL = 0;
        if (allOrderDone != null) {
            for (Map.Entry<String, OrderTargetInfoTest> entry : allOrderDone.entrySet()) {
                String key = entry.getKey();
                OrderTargetInfoTest orderInfo = entry.getValue();
                if (orderInfo.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                    totalSL++;
                }
                if (Utils.getDate(Long.parseLong(key.split("-")[0])) == (timeUpdate - Utils.TIME_DAY)) {
                    profitOfDate += calTp(orderInfo);
                }
                fee += calFee(orderInfo);
                profit += calTp(orderInfo);
            }
        }


        Set<String> symbolRunning = orderRunning.keySet();

        totalFee = fee;
        balance = balance + profit - totalFee;
        balanceCurrent = balance;

        Double unrealizedProfit = calUnrealizedProfit(orderRunning.values());
        unProfit = -unrealizedProfit;
        Double unrealizedProfitMin = calUnrealizedProfitMin(orderRunning.values());
        Double positionMargin = calPositionMargin(orderRunning.values());
        Double balanceReal = balance + unrealizedProfit;
        Double balanceMin = balance + unrealizedProfitMin;
        balanceIndex.updateIndex(balance, balanceMin, positionMargin, unrealizedProfitMin, timeUpdate);
        if (timeUpdate % Utils.TIME_DAY == 0) {
            Double rateLoss = unProfit * 100 / balanceCurrent;
            Double rateProfitDate = profitOfDate * 100 / (balanceCurrent - profitOfDate);
            LOG.info("Update {} => balance:{} pDate:{} {}% margin:{} {}% " +
                            "profit:{} unProfit:{} {}% fee:{} done: {}/{} run:{}",
                    Utils.normalizeDateYYYYMMDDHHmm(timeUpdate), balance.longValue(), profitOfDate.longValue(),
                    rateProfitDate.longValue(), positionMargin.longValue(), investing.longValue(), profit.longValue(),
                    unrealizedProfit.longValue(), rateLoss.longValue(), totalFee.longValue(), totalSL,
                    allOrderDone.size(), symbolRunning.size());
            if (timeUpdate.equals(Utils.getToDay() + 7 * Utils.TIME_HOUR)) {
//                LOG.info("Report: {}", Utils.normalizeDateYYYYMMDDHHmm(timeUpdate));
                List<String> lines =
                        new ArrayList<>();
                StringBuilder builder = new StringBuilder();
                builder.append("capital: ").append(MAX_CAPITAL_RATE).append(" rateBudget: ").append(RATE_BUDGET_PER_ORDER);
                builder.append(" balance: ").append(balance.longValue());
                builder.append(" balanceReal: ").append(balanceReal.longValue());
                builder.append(" done: ").append(allOrderDone.size());
                builder.append(" " + balanceIndex.balanceMin + " " + balanceIndex.rateBalanceMin + " " +
                        Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeBalanceMin) + " " + balanceIndex.marginMax +
                        " " + balanceIndex.rateMarginMax + " " + Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeMarginMax) + " " +
                        balanceIndex.unProfitMax + " " + balanceIndex.rateUnProfitMax + " " +
                        Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeRateUnProfitMax));
                lines.add(builder.toString());
                try {
                    FileUtils.writeLines(new File("storage/report.txt"), lines, true);
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }
        }
        if ((balance + unrealizedProfitMin) < 0) {
            stop = true;
            LOG.info("Chay tai khoan {} -----------------------------------!", Utils.normalizeDateYYYYMMDDHHmm(timeUpdate));
        }
        updateBudget(orderRunning);
    }

    private Double calFee(OrderTargetInfoTest orderInfo) {
        return orderInfo.quantity * orderInfo.priceEntry * RATE_FEE;
    }


    public Double calUnrealizedProfit(Collection<OrderTargetInfoTest> orderInfos) {
        Double result = 0d;
        for (OrderTargetInfoTest orderInfo : orderInfos) {
            Double profit = orderInfo.calProfit();
            result += profit;
        }
        return result;
    }

    public Double calUnrealizedProfitMin(Collection<OrderTargetInfoTest> orderInfos) {
        Double result = 0d;
        for (OrderTargetInfoTest orderInfo : orderInfos) {
            Double profit = orderInfo.calProfitMin();
            result += profit;
        }
        return result;
    }

    public Double calPositionMargin(Collection<OrderTargetInfoTest> values) {
        Double totalMargin = 0d;
        if (values != null) {
            for (OrderTargetInfoTest orderInfo : values) {
                Double margin = orderInfo.calMargin();
                totalMargin += margin;
            }
        }
        return totalMargin;
    }

    private Double calTp(OrderTargetInfoTest orderInfo) {
        Double tp = orderInfo.quantity * (orderInfo.priceTP - orderInfo.priceEntry);
        return tp;
    }

    public void updateInvesting(Collection<OrderTargetInfoTest> orderRunning) {
        Double margin = calPositionMargin(orderRunning);
        investing = margin * 100 / balanceCurrent;
    }

    public void printBalanceIndex() {
        LOG.info("BalanceMin: {} {} {} MarginMax: {} {} {} unProfitMax: {} {} {}",
                balanceIndex.balanceMin, balanceIndex.rateBalanceMin, Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeBalanceMin),
                balanceIndex.marginMax, balanceIndex.rateMarginMax, Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeMarginMax),
                balanceIndex.unProfitMax, balanceIndex.rateUnProfitMax, Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeRateUnProfitMax)
        );
    }

    public void resetCapitalAndRateBudget(Double capital, Double rateBudget) {
        RATE_BUDGET_PER_ORDER = rateBudget;
        MAX_CAPITAL_RATE = capital;
        balanceCurrent = balanceStart;
    }
}
