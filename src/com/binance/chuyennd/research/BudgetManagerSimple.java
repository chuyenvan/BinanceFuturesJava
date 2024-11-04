/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.apache.commons.io.FileUtils;
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
    public Integer number_order_budget = 100;
    public Double BUDGET_PER_ORDER;
    public Double investing = null;
    public Map<Long, Double> time2Balance = new HashMap<>();
    public Double unProfit = 0d;
    public Double profitLossMax = 0d;
    public Double totalFee = 0d;
    public Double balanceBasic = Configs.getDouble("CAPITAL_START");
    public Double balanceCurrent = balanceBasic;

    public Double profit = 0d;
    public Integer maxOrderRunning = 0;
    public Double fee = 0d;
    public int totalSL = 0;
    public MarketLevelChange levelRun;


    public static BudgetManagerSimple getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new BudgetManagerSimple();
            INSTANCE.updateBudget();
        }
        return INSTANCE;
    }

    public void updateBudget() {
        investing = 0d;
        try {
            Double ratePerOrder = Configs.RATE_BUDGET_LIMIT_A_SIGNAL / Configs.NUMBER_ENTRY_EACH_SIGNAL;
            // for test number order
            if (Configs.MOD_RUN_CAPITAL_CONSTANT) {
                BUDGET_PER_ORDER = ratePerOrder * balanceBasic / number_order_budget;
            } else {
                if (balanceCurrent / 3 > balanceBasic) {
                    BUDGET_PER_ORDER = ratePerOrder * (balanceCurrent / 3) / number_order_budget;
                } else {
                    BUDGET_PER_ORDER = ratePerOrder * balanceBasic / number_order_budget;
                }
            }


//            LOG.info("Update Budget: {}", BUDGET_PER_ORDER);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public Double getBudget() {
        return BUDGET_PER_ORDER;
    }

    public Boolean isAvailableTrade() {
        return investing < Configs.MAX_CAPITAL_RATE;
    }


    public Integer getLeverage(String symbol) {
        if (Constants.specialSymbol.contains(symbol)){
            return Configs.LEVERAGE_ORDER * 2;
        }
        return Configs.LEVERAGE_ORDER;
    }

    public void updatePnl(OrderTargetInfoTest orderInfo) {
        if (orderInfo != null) {
            if (orderInfo.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                totalSL++;
            }
            if (orderInfo.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                if (orderInfo.side.equals(OrderSide.BUY)) {
                    if (orderInfo.priceTP < orderInfo.priceEntry) {
                        totalSL++;
                    }
                } else {
                    if (orderInfo.priceTP > orderInfo.priceEntry) {
                        totalSL++;
                    }
                }
            }
            fee += calFee(orderInfo);
            profit += orderInfo.calTp();
        }
    }

    public void updateBalance(Long timeUpdate, TreeMap<Long, OrderTargetInfoTest> allOrderDone,
                              ConcurrentHashMap<String, OrderTargetInfoTest> orderRunning, boolean isPrintBalance) {
        Double balance = balanceBasic;
        Set<String> symbolRunning = orderRunning.keySet();
        totalFee = fee;
        balance = balance + profit;
        balanceCurrent = balance;
        unProfit = calUnrealizedProfit(orderRunning.values());
        profitLossMax = calProfitLossMax(orderRunning.values());
        Double positionMargin = calPositionMargin(orderRunning.values());
        Double balanceReal = balance + unProfit;
        Double unrealizedProfitMin = calUnrealizedProfitMin(orderRunning.values());
        balanceIndex.updateIndex(balanceBasic, positionMargin, timeUpdate, profitLossMax, unrealizedProfitMin);
        if (isPrintBalance) {
            time2Balance.put(timeUpdate, balance);
            Double rateLoss = unProfit * 100 / balanceCurrent;
//            Double rateProfitDate = profitOfDate * 100 / (balanceCurrent - profitOfDate);
            Double balanceYesterday = time2Balance.get(timeUpdate - Utils.TIME_DAY);
            Double profitOfDate = 0d;
            if (balanceYesterday != null) {
                profitOfDate = balance - balanceYesterday;
            }

            Double rateProfitDate = profitOfDate * 100 / balanceBasic;
            if (!Configs.MOD_RUN_CAPITAL_CONSTANT) {
                rateProfitDate = profitOfDate * 100 / balanceCurrent;
            }
            LOG.info("Update-{}-{} {} => balance:{} pDate:{} {}%  margin:{} max:{}% " +
                            "profit:{} unProfit:{} {}% unProfitMin:{} {}% {}% fee:{} done: {}/{} run:{}/{}", Configs.TIME_AFTER_ORDER_2_SL,
                    levelRun,
                    Utils.normalizeDateYYYYMMDDHHmm(timeUpdate), balance.longValue(), profitOfDate.longValue(),
                    rateProfitDate.longValue(), positionMargin.longValue(),
                    Utils.formatPercent(balanceIndex.rateMarginMax), profit.longValue(),
                    unProfit.longValue(), rateLoss.longValue(), balanceIndex.unProfitMin.longValue(),
                    Utils.formatPercent(balanceIndex.unProfitMin / balanceBasic),
                    Utils.formatPercent(balanceIndex.profitLossMax / balanceBasic), totalFee.longValue(), totalSL,
                    allOrderDone.size(), symbolRunning.size(), maxOrderRunning);
            if (timeUpdate.equals(Utils.getToDay() + 7 * Utils.TIME_HOUR)) {
//                LOG.info("Report: {}", Utils.normalizeDateYYYYMMDDHHmm(timeUpdate));
                List<String> lines =
                        new ArrayList<>();
                StringBuilder builder = new StringBuilder();
                builder.append("capital: ").append(Configs.MAX_CAPITAL_RATE).append(" rateBudget: ")
                        .append(Configs.RATE_BUDGET_LIMIT_A_SIGNAL);
                builder.append(" balance: ").append(balance.longValue());
                builder.append(" balanceReal: ").append(balanceReal.longValue());
                builder.append(" done: ").append(allOrderDone.size());
                builder.append(balanceIndex.marginMax + " " + balanceIndex.rateMarginMax + " " + Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeMarginMax) + " " +
                        balanceIndex.profitLossMax);
                lines.add(builder.toString());
                try {
                    FileUtils.writeLines(new File("storage/report.txt"), lines, true);
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }
        }
        if ((balance + unrealizedProfitMin) < 0) {
            LOG.info("Chay tai khoan {} -----------------------------------!", Utils.normalizeDateYYYYMMDDHHmm(timeUpdate));
        }
        updateBudget();
    }

    public void updateBalanceMulti(Long timeUpdate, ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone,
                                   ConcurrentHashMap<String, List<OrderTargetInfoTest>> symbol2OrdersRunning, boolean isPrintBalance) {

        Double balance = balanceBasic;
        List<OrderTargetInfoTest> orderRunning = new ArrayList<>();
        for (List<OrderTargetInfoTest> orders : symbol2OrdersRunning.values()) {
            if (orders != null && !orders.isEmpty()) {
                orderRunning.addAll(orders);
            }
        }
        Set<String> symbolRunning = symbol2OrdersRunning.keySet();
        totalFee = fee;
        balance = balance + profit - totalFee;
        balanceCurrent = balance;
        unProfit = calUnrealizedProfit(orderRunning);
        profitLossMax = calProfitLossMax(orderRunning);
        Double positionMargin = calPositionMargin(orderRunning);
        Double balanceReal = balance + unProfit;
        Double unrealizedProfitMin = calUnrealizedProfitMin(orderRunning);
        balanceIndex.updateIndex(balance, positionMargin, timeUpdate, profitLossMax, unrealizedProfitMin);
        if (isPrintBalance) {
            time2Balance.put(timeUpdate, balance);
            Double rateLoss = unProfit * 100 / balanceCurrent;
//            Double rateProfitDate = profitOfDate * 100 / (balanceCurrent - profitOfDate);
            Double balanceYesterday = time2Balance.get(timeUpdate - Utils.TIME_DAY);
            Double profitOfDate = 0d;
            if (balanceYesterday != null) {
                profitOfDate = balance - balanceYesterday;
            }

            Double rateProfitDate = profitOfDate * 100 / balanceBasic;
            if (!Configs.MOD_RUN_CAPITAL_CONSTANT) {
                rateProfitDate = profitOfDate * 100 / balanceCurrent;
            }
            LOG.info("Update-{}-{} {} => balance:{} pDate:{} {}%  margin:{} {}% " +
                            "profit:{} unProfit:{} {}% unProfitMin:{} {}% fee:{} done: {}/{} run:{}", Configs.TIME_AFTER_ORDER_2_SL,
                    Configs.RATE_TICKER_MAX_SCAN_ORDER,
                    Utils.normalizeDateYYYYMMDDHHmm(timeUpdate), balance.longValue(), profitOfDate.longValue(),
                    rateProfitDate.longValue(), positionMargin.longValue(), investing.longValue(), profit.longValue(),
                    unProfit.longValue(), rateLoss.longValue(), balanceIndex.unProfitMin.longValue(),
                    Utils.formatPercent(balanceIndex.unProfitMin / balanceBasic), totalFee.longValue(), totalSL,
                    allOrderDone.size(), orderRunning.size());
            if (timeUpdate.equals(Utils.getToDay() + 7 * Utils.TIME_HOUR)) {
//                LOG.info("Report: {}", Utils.normalizeDateYYYYMMDDHHmm(timeUpdate));
                List<String> lines =
                        new ArrayList<>();
                StringBuilder builder = new StringBuilder();
                builder.append("capital: ").append(Configs.MAX_CAPITAL_RATE).append(" rateBudget: ")
                        .append(Configs.RATE_BUDGET_LIMIT_A_SIGNAL);
                builder.append(" balance: ").append(balance.longValue());
                builder.append(" balanceReal: ").append(balanceReal.longValue());
                builder.append(" done: ").append(allOrderDone.size());
                builder.append(balanceIndex.marginMax + " " + balanceIndex.rateMarginMax + " " + Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeMarginMax) + " " +
                        balanceIndex.profitLossMax);
                lines.add(builder.toString());
                try {
                    FileUtils.writeLines(new File("storage/report.txt"), lines, true);
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }
        }
        if ((balance + unrealizedProfitMin) < 0) {
            LOG.info("Chay tai khoan {} -----------------------------------!", Utils.normalizeDateYYYYMMDDHHmm(timeUpdate));
        }
        updateBudget();
    }

    private Double calFee(OrderTargetInfoTest orderInfo) {
        return orderInfo.quantity * orderInfo.priceEntry * Configs.RATE_FEE;
    }

    public Double calUnrealizedProfitMin(Collection<OrderTargetInfoTest> orderInfos) {
        Double result = 0d;
        for (OrderTargetInfoTest orderInfo : orderInfos) {
            Double profit = orderInfo.calProfitMin();
            result += profit;
        }
        return result;
    }

    public Double calUnrealizedProfit(Collection<OrderTargetInfoTest> orderInfos) {
        Double result = 0d;
        for (OrderTargetInfoTest orderInfo : orderInfos) {
            Double profit = orderInfo.calProfit();
            result += profit;
        }
        return result;
    }

    public Double calProfitLossMax(Collection<OrderTargetInfoTest> orderInfos) {
        Double result = 0d;
        for (OrderTargetInfoTest orderInfo : orderInfos) {
            Double profit = orderInfo.calProfitLossMax();
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


    public void updateInvesting(Collection<OrderTargetInfoTest> orderRunning) {
        Double margin = calPositionMargin(orderRunning);
        investing = margin * 100 / balanceCurrent;
    }

    public void printBalanceIndex() {
        LOG.info("MarginMax: {} {}% {} profitLossMax: {} {}% {} unProfitMin: {} {}% {}",
                balanceIndex.marginMax, Utils.formatPercent(balanceIndex.rateMarginMax),
                Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeMarginMax),
                balanceIndex.profitLossMax, Utils.formatPercent(balanceIndex.profitLossMax / balanceBasic),
                Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeProfitLossMax),
                balanceIndex.unProfitMin, Utils.formatPercent(balanceIndex.unProfitMin / balanceBasic),
                Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeUnProfitMin)
        );
    }

    public Double calRateLossDynamic(Double unProfit, String symbol) {
        Double rateLoss = unProfit * 100;
        Long tradingStopRate = rateLoss.longValue() / 2;
        Integer rateProfit2Shard=  10;
        if (Constants.specialSymbol.contains(symbol)){
            rateProfit2Shard = 6;
        }
        if (rateLoss > rateProfit2Shard) {
            tradingStopRate = rateLoss.longValue() / 3;
            if (rateLoss > 2 * rateProfit2Shard) {
                tradingStopRate = rateLoss.longValue() / 4;
            }else{
                if (rateLoss > 3 * rateProfit2Shard) {
                    tradingStopRate = rateLoss.longValue() / 5;
                }
            }
        }
        if (rateLoss < 0) {
            rateLoss = rateLoss.longValue() - Configs.RATE_STOP_LOSS * 100;
        } else {
            rateLoss = rateLoss.longValue() - tradingStopRate.doubleValue();
        }

        return rateLoss / 100;
    }


    public static void main(String[] args) {
//        for (int i = 2; i < 11; i++) {
//            int numberOrder = i * 2;
//            Configs.NUMBER_ENTRY_EACH_SIGNAL = numberOrder;
//            BudgetManagerSimple.getInstance().updateBudget(null);
//            LOG.info("{} -> {}", Configs.NUMBER_ENTRY_EACH_SIGNAL, BudgetManagerSimple.getInstance().getBudget());
//        }
//        Double rate = Utils.rateOf2Double(1.454, 1.441);
//        System.out.println(BudgetManagerSimple.getInstance().calRateStop(rate));
//        for (int i = 0; i < 100; i++) {
//            Double rate = -0.2 + i * 0.01;
//            LOG.info("{}  -> {}", rate, BudgetManagerSimple.getInstance().calRateLossDynamic(rate));
//        }
    }


    public void resetHistory() {
        totalSL = 0;
        fee = 0d;
        profit = 0d;
        balanceCurrent = balanceBasic;
        unProfit = 0d;
        profitLossMax = 0d;
        totalFee = 0d;
        balanceIndex = new BalanceIndex();
    }

    public void updateMaxOrderRunning(Integer counterOrderRunning) {
        if (maxOrderRunning < counterOrderRunning) {
            maxOrderRunning = counterOrderRunning;
        }
    }

    public Double calRateStop(Double rateLoss, String symbol) {
        Double rateStopLoss = Configs.RATE_STOP_LOSS;
        if (Constants.specialSymbol.contains(symbol)){
            rateStopLoss = rateStopLoss * 2;
        }
        Double rateStop;
        if (rateLoss < 0.01) {
            rateStop = -rateLoss + rateStopLoss;
        } else {
            rateStop = -rateLoss / 2;
        }
        return rateStop;
    }
}
