/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
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
    public Double fee = 0d;
    public int totalSL = 0;


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


    public Integer getLeverage() {
        return Configs.LEVERAGE_ORDER;
    }

    public void updatePnl(OrderTargetInfoTest orderInfo) {
        if (orderInfo != null) {
            if (orderInfo.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                totalSL++;
            }
            if (orderInfo.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                if (orderInfo.side.equals(OrderSide.BUY)){
                    if (orderInfo.priceTP < orderInfo.priceEntry) {
                        totalSL++;
                    }
                }else{
                    if (orderInfo.priceTP > orderInfo.priceEntry) {
                        totalSL++;
                    }
                }
            }
            fee += calFee(orderInfo);
            profit += calTp(orderInfo);
        }
    }

    public void updateBalance(Long timeUpdate, ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone,
                              ConcurrentHashMap<String, OrderTargetInfoTest> orderRunning, boolean isPrintBalance) {
        Double balance = balanceBasic;
        Set<String> symbolRunning = orderRunning.keySet();
        totalFee = fee;
        balance = balance + profit - totalFee;
        balanceCurrent = balance;
        unProfit = calUnrealizedProfit(orderRunning.values());
        profitLossMax = calProfitLossMax(orderRunning.values());
        Double positionMargin = calPositionMargin(orderRunning.values());
        Double balanceReal = balance + unProfit;
        Double unrealizedProfitMin = calUnrealizedProfitMin(orderRunning.values());
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
                            "profit:{} unProfit:{} {}% unProfitMin:{} {}% fee:{} done: {}/{} run:{}", Configs.TIME_AFTER_ORDER_2_TP,
                    Configs.TIME_AFTER_ORDER_2_SL,
                    Utils.normalizeDateYYYYMMDDHHmm(timeUpdate), balance.longValue(), profitOfDate.longValue(),
                    rateProfitDate.longValue(), positionMargin.longValue(), investing.longValue(), profit.longValue(),
                    unProfit.longValue(), rateLoss.longValue(), balanceIndex.unProfitMin.longValue(),
                    Utils.formatPercent(balanceIndex.unProfitMin / balanceBasic), totalFee.longValue(), totalSL,
                    allOrderDone.size(), symbolRunning.size());
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


    private Double calTp(OrderTargetInfoTest orderInfo) {
        Double tp = orderInfo.quantity * (orderInfo.priceTP - orderInfo.priceEntry);
        if (orderInfo.side.equals(OrderSide.SELL)) {
            tp = orderInfo.quantity * (orderInfo.priceEntry - orderInfo.priceTP);
        }
        return tp;
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

    public Double calRateLossDynamic(Double unProfit) {
        Double rateLoss = unProfit * 100;
        Long tradingStopRate;
        if (rateLoss >= 5) {
            tradingStopRate = rateLoss.longValue() / 4;
            if (tradingStopRate < Configs.RATE_TRADING_DYNAMIC) {
                tradingStopRate = Configs.RATE_TRADING_DYNAMIC.longValue();
            }
            if (tradingStopRate > 5) {
                tradingStopRate = 5l;
            }
        } else {
            if (rateLoss > 2) {
                tradingStopRate = 1l;
            } else {
                if (rateLoss > 3) {
                    tradingStopRate = 2l;
                }else{
                    tradingStopRate = 3l;
                }
            }
        }
        rateLoss = rateLoss.longValue() - tradingStopRate.doubleValue();
        return rateLoss;
    }


    public Double calTPDynamic(Double unProfit) {
        Double rateLoss = unProfit * 100;
        Long tradingTPRate = rateLoss.longValue() / 2;
        if (tradingTPRate < 2 * Configs.RATE_TRADING_DYNAMIC) {
            tradingTPRate = 2 * Configs.RATE_TRADING_DYNAMIC.longValue();
        }
        rateLoss = rateLoss.longValue() + tradingTPRate.doubleValue();
//        rateLoss = rateLoss.longValue() + 2 * RATE_TRADING_DYNAMIC;
        return rateLoss;
    }

    public static void main(String[] args) {
//        for (int i = 2; i < 11; i++) {
//            int numberOrder = i * 2;
//            Configs.NUMBER_ENTRY_EACH_SIGNAL = numberOrder;
//            BudgetManagerSimple.getInstance().updateBudget(null);
//            LOG.info("{} -> {}", Configs.NUMBER_ENTRY_EACH_SIGNAL, BudgetManagerSimple.getInstance().getBudget());
//        }
//        for (int i = 0; i < 100; i++) {
//            Double rate = i * 0.01;
//            LOG.info("{}  -> {}", rate, BudgetManagerSimple.getInstance().calRateLossDynamic(rate));
//        }
    }

    public static Double calBalanceBasicNew(Double balanceBasic, Double balance) {
        Long shard = 500l;
        if (balance.longValue() / shard / 3 > balanceBasic / shard) {
            return balanceBasic + shard;
        } else {
            return balanceBasic;
        }
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
}
