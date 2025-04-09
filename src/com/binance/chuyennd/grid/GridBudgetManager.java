/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.grid;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.research.OrderTargetInfoTest;
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
public class GridBudgetManager {

    public static final Logger LOG = LoggerFactory.getLogger(GridBudgetManager.class);
    private static volatile GridBudgetManager INSTANCE = null;
    public GridBalanceIndex balanceIndex = new GridBalanceIndex();
    public Integer number_order_budget = 100;
    public Double BUDGET_PER_ORDER;
    public Double investing = null;
    public Map<Long, Double> time2Balance = new HashMap<>();
    public Double unProfit = 0d;
    public Double profitLossMax = 0d;
    public Double totalFee = 0d;
    public Double totalFundingFee = 0d;
    public Double balanceBasic = Configs.getDouble("CAPITAL_START");
    public Double balanceCurrent = balanceBasic;

    public Double profit = 0d;
    public Integer maxOrderRunning = 0;
    public Double fee = 0d;
    public int totalSL = 0;
    public int totalTP = 0;
    public MarketLevelChange levelRun;


    public static GridBudgetManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new GridBudgetManager();
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

    public void updatePnl(OrderTargetInfoTest orderInfo) {
        if (orderInfo != null) {
            if (orderInfo.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                totalSL++;
            } else {
                totalTP++;
            }
            fee += calFee(orderInfo);
            totalFundingFee += orderInfo.calFundingFee();
            profit += orderInfo.calTp();
        }
    }

    public Integer getLeverage(String symbol) {
        if (Constants.specialSymbol.contains(symbol)) {
            return Configs.LEVERAGE_ORDER * 2;
        }
        if (Constants.stableSymbol.contains(symbol)) {
            return Configs.LEVERAGE_ORDER * 2;
        }
        return Configs.LEVERAGE_ORDER;
    }

    public void updateBalanceMulti(Long timeUpdate, ConcurrentHashMap<Long, GridObjectTestResearch> allGridDone,
                              ConcurrentHashMap<String, List<GridObjectTestResearch>> symbol2GridRunning, boolean isPrintBalance) {

        Double balance = balanceBasic;
        Set<String> symbolRunning = symbol2GridRunning.keySet();
        totalFee = fee;
        balance = balance + profit;
        balanceCurrent = balance;
        List<GridObjectTestResearch> gridRunning = new ArrayList<>();
        for (List<GridObjectTestResearch> grids : symbol2GridRunning.values()){
            gridRunning.addAll(grids);
        }
        unProfit = calUnrealizedProfit(gridRunning);
        profitLossMax = calProfitLostMax(gridRunning);
        Double positionMargin = calPositionMargin(gridRunning);
        Double positionMarginReal = calPositionMarginReal(gridRunning);
        Double balanceReal = balance + unProfit;
        Double unrealizedProfitMin = calUnProfitMin(gridRunning);
        balanceIndex.updateIndexMulti(balanceBasic, positionMargin, positionMarginReal, timeUpdate, profitLossMax, unrealizedProfitMin, symbol2GridRunning);
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
            Double marginRealMaxDate = balanceIndex.date2MarginRealMax.get(Utils.getDate(timeUpdate - Utils.TIME_MINUTE));
            if (marginRealMaxDate == null) {
                marginRealMaxDate = 0d;
            }
            Double marginRealMaxMonth = balanceIndex.month2MarginRealMax.get(Utils.getMonth(timeUpdate - Utils.TIME_DAY));
            if (marginRealMaxMonth == null) {
                marginRealMaxMonth = 0d;
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

            LOG.info("Update {} => b:{} pD:{}\tm:{}\tmax:{}%\t{}\t{}\t{}\t{}\t" +
                            "unP:{}\tunPMin:{}\t{}\t{}\t{}%\t{}\tdone:{}/{} run:{}/{} f:{}",
                    Utils.normalizeDateYYYYMMDDHHmm(timeUpdate), Utils.formatLog(balance.longValue(), 5),
                    Utils.formatLog(profitOfDate.longValue(), 4),
                    Utils.formatLog(positionMargin.longValue(), 4),
                    Utils.formatLog(rateMarginMaxDouble.longValue(), 3),
                    Utils.formatLog(marginMaxDate.longValue(), 5),
                    Utils.formatLog(marginMaxMonth.longValue(), 5),
                    Utils.formatLog(marginRealMaxDate.longValue(), 5),
                    Utils.formatLog(marginRealMaxMonth.longValue(), 5),
                    Utils.formatLog(unProfit.longValue(), 5),
                    Utils.formatLog(balanceIndex.unProfitMin.longValue(), 5),
                    Utils.formatLog(unProfitDate.longValue(), 5),
                    Utils.formatLog(unProfitMonth.longValue(), 5),
                    Utils.formatPercentNew(balanceIndex.unProfitMin / balanceBasic),
                    slMonth.longValue(),
                    totalSL, totalTP, symbolRunning.size(), maxOrderRunning, totalFundingFee.longValue());
            if (timeUpdate.equals(Utils.getToDay() + 7 * Utils.TIME_HOUR)) {
//                LOG.info("Report: {}", Utils.normalizeDateYYYYMMDDHHmm(timeUpdate));
                List<String> lines =
                        new ArrayList<>();
                StringBuilder builder = new StringBuilder();
                builder.append("capital: ").append(Configs.MAX_CAPITAL_RATE).append(" rateBudget: ")
                        .append(Configs.RATE_BUDGET_LIMIT_A_SIGNAL);
                builder.append(" balance: ").append(balance.longValue());
                builder.append(" balanceReal: ").append(balanceReal.longValue());
                builder.append(" done: ").append(allGridDone.size());
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
//        if ((balance + unrealizedProfitMin) < 0) {
//            LOG.info("Chay tai khoan {} -----------------------------------!", Utils.normalizeDateYYYYMMDDHHmm(timeUpdate));
//        }
        updateBudget();
    }
    public void updateBalance(Long timeUpdate, ConcurrentHashMap<Long, GridObjectTestResearch> allGridDone,
                              ConcurrentHashMap<String, GridObjectTestResearch> symbol2GridRunning, boolean isPrintBalance) {

        Double balance = balanceBasic;
        Set<String> symbolRunning = symbol2GridRunning.keySet();
        totalFee = fee;
        balance = balance + profit;
        balanceCurrent = balance;

        unProfit = calUnrealizedProfit(symbol2GridRunning.values());
        profitLossMax = calProfitLostMax(symbol2GridRunning.values());
        Double positionMargin = calPositionMargin(symbol2GridRunning.values());
        Double positionMarginReal = calPositionMarginReal(symbol2GridRunning.values());
        Double balanceReal = balance + unProfit;
        Double unrealizedProfitMin = calUnProfitMin(symbol2GridRunning.values());
        balanceIndex.updateIndex(balanceBasic, positionMargin, positionMarginReal, timeUpdate, profitLossMax, unrealizedProfitMin, symbol2GridRunning);
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
            Double marginRealMaxDate = balanceIndex.date2MarginRealMax.get(Utils.getDate(timeUpdate - Utils.TIME_MINUTE));
            if (marginRealMaxDate == null) {
                marginRealMaxDate = 0d;
            }
            Double marginRealMaxMonth = balanceIndex.month2MarginRealMax.get(Utils.getMonth(timeUpdate - Utils.TIME_DAY));
            if (marginRealMaxMonth == null) {
                marginRealMaxMonth = 0d;
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

            LOG.info("Update {} => b:{} pD:{}\tm:{}\tmax:{}%\t{}\t{}\t{}\t{}\t" +
                            "unP:{}\tunPMin:{}\t{}\t{}\t{}%\t{}\tdone:{}/{} run:{}/{} f:{}",
                    Utils.normalizeDateYYYYMMDDHHmm(timeUpdate), Utils.formatLog(balance.longValue(), 5),
                    Utils.formatLog(profitOfDate.longValue(), 4),
                    Utils.formatLog(positionMargin.longValue(), 4),
                    Utils.formatLog(rateMarginMaxDouble.longValue(), 3),
                    Utils.formatLog(marginMaxDate.longValue(), 5),
                    Utils.formatLog(marginMaxMonth.longValue(), 5),
                    Utils.formatLog(marginRealMaxDate.longValue(), 5),
                    Utils.formatLog(marginRealMaxMonth.longValue(), 5),
                    Utils.formatLog(unProfit.longValue(), 5),
                    Utils.formatLog(balanceIndex.unProfitMin.longValue(), 5),
                    Utils.formatLog(unProfitDate.longValue(), 5),
                    Utils.formatLog(unProfitMonth.longValue(), 5),
                    Utils.formatPercentNew(balanceIndex.unProfitMin / balanceBasic),
                    slMonth.longValue(),
                    totalSL, totalTP, symbolRunning.size(), maxOrderRunning, totalFundingFee.longValue());
            if (timeUpdate.equals(Utils.getToDay() + 7 * Utils.TIME_HOUR)) {
//                LOG.info("Report: {}", Utils.normalizeDateYYYYMMDDHHmm(timeUpdate));
                List<String> lines =
                        new ArrayList<>();
                StringBuilder builder = new StringBuilder();
                builder.append("capital: ").append(Configs.MAX_CAPITAL_RATE).append(" rateBudget: ")
                        .append(Configs.RATE_BUDGET_LIMIT_A_SIGNAL);
                builder.append(" balance: ").append(balance.longValue());
                builder.append(" balanceReal: ").append(balanceReal.longValue());
                builder.append(" done: ").append(allGridDone.size());
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
//        if ((balance + unrealizedProfitMin) < 0) {
//            LOG.info("Chay tai khoan {} -----------------------------------!", Utils.normalizeDateYYYYMMDDHHmm(timeUpdate));
//        }
        updateBudget();
    }

    private Double calFee(OrderTargetInfoTest orderInfo) {
        return orderInfo.quantity * orderInfo.priceEntry * Configs.RATE_FEE;
    }

    public Double calUnrealizedProfit(Collection<GridObjectTestResearch> orderInfos) {
        Double result = 0d;
        for (GridObjectTestResearch orderInfo : orderInfos) {
            Double profit = orderInfo.calProfitRunning();
            result += profit;
        }
        return result;
    }

    public Double calUnProfitMin(Collection<GridObjectTestResearch> orderInfos) {
        Double result = 0d;
        for (GridObjectTestResearch orderInfo : orderInfos) {
            result += orderInfo.unProfitMin;
        }
        return result;
    }

    public Double calProfitLostMax(Collection<GridObjectTestResearch> orderInfos) {
        Double result = 0d;
        for (GridObjectTestResearch orderInfo : orderInfos) {
            result += orderInfo.profitLossMax;
        }
        return result;
    }


    public Double calPositionMargin(Collection<GridObjectTestResearch> values) {
        Double totalMargin = 0d;
        if (values != null) {
            for (GridObjectTestResearch orderInfo : values) {
                Double margin = orderInfo.marginMax;
                totalMargin += margin;
            }
        }
        return totalMargin;
    }

    public Double calPositionMarginReal(Collection<GridObjectTestResearch> values) {
        Double totalMargin = 0d;
        if (values != null) {
            for (GridObjectTestResearch orderInfo : values) {
                Double margin = orderInfo.marginRealMax;
                totalMargin += margin;
            }
        }
        return totalMargin;
    }


    public void updateInvesting(Collection<OrderTargetInfoTest> orderRunning) {
        LOG.info("Update for symbol: {}", orderRunning.stream().count());
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

}
