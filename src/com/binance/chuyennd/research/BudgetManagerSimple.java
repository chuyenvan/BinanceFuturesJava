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
        if (Constants.specialSymbol.contains(symbol)) {
            return Configs.LEVERAGE_ORDER * 2;
        }
        return Configs.LEVERAGE_ORDER;
    }

    public void updatePnl(OrderTargetInfoTest orderInfo) {
        if (orderInfo != null) {
            if (orderInfo.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                totalSL++;
            }
//            if (orderInfo.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
//                if (orderInfo.side.equals(OrderSide.BUY)) {
//                    if (orderInfo.priceTP < orderInfo.priceEntry) {
//                        totalSL++;
//                    }
//                } else {
//                    if (orderInfo.priceTP > orderInfo.priceEntry) {
//                        totalSL++;
//                    }
//                }
//            }
            fee += calFee(orderInfo);
            profit += orderInfo.calTp();
        }
    }

    public void updateBalance(Long timeUpdate, TreeMap<Long, OrderTargetInfoTest> allOrderDone,
                              ConcurrentHashMap<String, OrderTargetInfoTest> orderRunning, ConcurrentHashMap<String, List<OrderTargetInfoTest>> symbol2OrdersEntry, boolean isPrintBalance) {
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
        balanceIndex.updateIndex(balanceBasic, positionMargin, timeUpdate, profitLossMax, unrealizedProfitMin, symbol2OrdersEntry,
                orderRunning);
        if (isPrintBalance) {
            time2Balance.put(timeUpdate, balance);
            Double balanceYesterday = time2Balance.get(timeUpdate - Utils.TIME_DAY);
            Double profitOfDate = 0d;
            if (balanceYesterday != null) {
                profitOfDate = balance - balanceYesterday;
            }

            Double marginMaxDate = balanceIndex.date2MarginMax.get(Utils.getDate(timeUpdate - Utils.TIME_MINUTE));
            if (marginMaxDate == null) {
                marginMaxDate = 0d;
            }
            Double marginMaxMonth = balanceIndex.month2MarginMax.get(Utils.getMonth(timeUpdate - Utils.TIME_DAY));
            if (marginMaxMonth == null) {
                marginMaxMonth = 0d;
            }
            Double unProfitDate = balanceIndex.date2ProfitMin.get(Utils.getDate(timeUpdate - Utils.TIME_MINUTE));
            if (unProfitDate == null) {
                unProfitDate = 0d;
            }
            Double unProfitMonth = balanceIndex.month2ProfitMin.get(Utils.getMonth(timeUpdate - Utils.TIME_DAY));
            if (unProfitMonth == null) {
                unProfitMonth = 0d;
            }
            Double slMonth = balanceIndex.month2SLMax.get(Utils.getMonth(timeUpdate - Utils.TIME_DAY));
            if (slMonth == null) {
                slMonth = 0d;
            }

            Double rateMarginMaxDouble = balanceIndex.rateMarginMax * 100;

            LOG.info("Update {} => b:{} pDate:{}\tm:{}\tmax:{}%\t{}\t{}\t" +
                            "p:{}\tunP:{}\tunPMin:{}\t{}\t{}\t{}%\t{}\t{}%\tdone:{}/{} run:{}/{}",
                    Utils.normalizeDateYYYYMMDDHHmm(timeUpdate), Utils.formatLog(balance.longValue(), 5),
                    Utils.formatLog(profitOfDate.longValue(), 4),
                    Utils.formatLog(positionMargin.longValue(), 4),
                    Utils.formatLog(rateMarginMaxDouble.longValue(), 3),
                    Utils.formatLog(marginMaxDate.longValue(), 5),
                    Utils.formatLog(marginMaxMonth.longValue(), 5),
                    Utils.formatLog(profit.longValue(), 5),
                    Utils.formatLog(unProfit.longValue(), 5),
                    Utils.formatLog(balanceIndex.unProfitMin.longValue(), 5),
                    Utils.formatLog(unProfitDate.longValue(), 5),
                    Utils.formatLog(unProfitMonth.longValue(), 5),
                    Utils.formatPercentNew(balanceIndex.unProfitMin / balanceBasic),
                    slMonth.longValue(),
                    Utils.formatPercentNew(balanceIndex.profitLossMax / balanceBasic),
                    totalSL, allOrderDone.size(), symbolRunning.size(), maxOrderRunning);
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
                builder.append(balanceIndex.marginMax + " " + balanceIndex.rateMarginMax + " "
                        + Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeMarginMax) + " " +
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
        Double rateLoss = unProfit * 1000;
        Double rateStopLoss = Configs.RATE_STOP_LOSS;
        if (!Constants.specialSymbol.contains(symbol)) {
            rateStopLoss = Configs.RATE_STOP_LOSS * 2;
        }
        Long tradingStopRate = rateLoss.longValue() / 2;
        Integer rateProfit2Shard = 100;
        if (Constants.specialSymbol.contains(symbol)) {
            rateProfit2Shard = 60;
        }
        if (rateLoss > rateProfit2Shard) {
            tradingStopRate = rateLoss.longValue() / 3;
            if (rateLoss > 2 * rateProfit2Shard) {
                tradingStopRate = rateLoss.longValue() / 4;
            } else {
                if (rateLoss > 3 * rateProfit2Shard) {
                    tradingStopRate = rateLoss.longValue() / 5;
                }
            }
        }
        if (rateLoss < 6) {
            rateLoss = rateLoss.longValue() - rateStopLoss * 1000;
        } else {
            rateLoss = rateLoss.longValue() - tradingStopRate.doubleValue();
        }

        return rateLoss / 1000;
    }


    public static void main(String[] args) {
//        for (int i = 2; i < 11; i++) {
//            int numberOrder = i * 2;
//            Configs.NUMBER_ENTRY_EACH_SIGNAL = numberOrder;
//            BudgetManagerSimple.getInstance().updateBudget();
//            LOG.info("{} -> {}", Configs.NUMBER_ENTRY_EACH_SIGNAL, BudgetManagerSimple.getInstance().getBudget());
//        }
        String symbol = "CATIUSDT";
//        Double rate = Utils.rateOf2Double(1.454, 1.441);
//        System.out.println(BudgetManagerSimple.getInstance().calRateStop(rate,symbol));
        for (int i = 0; i < 100; i++) {
            Double rate = -0.2 + i * 0.01;
            LOG.info("{}  -> {}", rate, BudgetManagerSimple.getInstance().calRateLossDynamic(rate, symbol));
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

    public void updateMaxOrderRunning(Integer counterOrderRunning) {
        if (maxOrderRunning < counterOrderRunning) {
            maxOrderRunning = counterOrderRunning;
        }
    }

    public Double calRateStop(Double rateLoss, String symbol) {
        Double rateStopLoss = Configs.RATE_STOP_LOSS;
        if (!Constants.specialSymbol.contains(symbol)) {
            rateStopLoss = Configs.RATE_STOP_LOSS * 2;
        }
        Double rateStop;
        Double rateMin2MoveSl = Configs.RATE_PROFIT_STOP_MARKET;
        if (Constants.specialSymbol.contains(symbol)) {
            rateMin2MoveSl = 0.01;
        }
        if (rateLoss < rateMin2MoveSl) {
            rateStop = -rateLoss + rateStopLoss;
        } else {
            rateStop = -rateLoss / 2;
        }
        return rateStop;
    }
}
