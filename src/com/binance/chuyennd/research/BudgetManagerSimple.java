/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.object.CapitalMode;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import org.apache.commons.io.FileUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;


/**
 * @author pc
 */
public class BudgetManagerSimple {

    public static final Logger LOG = LoggerFactory.getLogger(BudgetManagerSimple.class);

    public BalanceIndex balanceIndex = new BalanceIndex();
    public Integer number_order_budget = 60;
    public Double BUDGET_PER_ORDER;
    public Double investing = null;
    public Map<Long, Double> time2Balance = new HashMap<>();
    public Double unProfit = 0d;
    public Double positionMargin = 0d;

    public Double profitLossMax = 0d;
    public Double totalFee = 0d;
    public Double totalFundingFee = 0d;
    public Double balanceBasic = Configs.getDouble("CAPITAL_START");
    public Double balanceCurrent = balanceBasic;
    public AtomicInteger counterOrderCreated = new AtomicInteger(0);

    public Double profit = 0d;
    public Integer maxOrderRunning = 0;
    public Double fee = 0d;
    public int totalSL = 0;

    private static volatile BudgetManagerSimple INSTANCE = null;
    public Double marginRunning = null;

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
//        CapitalMode capitalMod = getCurrentCapitalMode();
//        switch (capitalMod) {
//            case SAFE:
//        Double ratePerOrder = Configs.RATE_BUDGET_LIMIT_A_SIGNAL / Configs.NUMBER_ENTRY_EACH_SIGNAL;
//        BUDGET_PER_ORDER = ratePerOrder * (balanceBasic + unProfit) / number_order_budget;

        return BUDGET_PER_ORDER * 0.3;
//            case DEFENSIVE:
//                return BUDGET_PER_ORDER * 0.3;
//            default:
//                return BUDGET_PER_ORDER * 0.4;
//        }

    }

    public Integer getLeverage() {
        return Configs.LEVERAGE_ORDER;
    }

    public void updatePnl(OrderTargetInfoTest orderInfo) {
        if (orderInfo != null) {
            if (orderInfo.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                totalSL++;
            }
            fee += calFee(orderInfo);
            totalFundingFee += orderInfo.calFundingFee();
            profit += orderInfo.calTp();
        }
    }

    public void updateBalance(Long timeUpdate, TreeMap<Long, OrderTargetInfoTest> allOrderDone,
                              ConcurrentHashMap<String, OrderTargetInfoTest> orderRunning,
                              ConcurrentHashMap<String, List<OrderTargetInfoTest>> symbol2OrdersEntry, boolean isPrintBalance) {
        Double balance = balanceBasic;
        totalFee = fee;
        balance = balance + profit;
        balanceCurrent = balance;
        unProfit = calUnrealizedProfit(orderRunning.values());
        profitLossMax = calProfitLossMax(orderRunning.values());
        positionMargin = calPositionMargin(orderRunning.values());
        Double positionMarginReal = calPositionMarginReal(orderRunning.values());
        Double balanceReal = balance + unProfit;
        Double unrealizedProfitMin = calUnrealizedProfitMin(orderRunning.values());
        balanceIndex.updateIndex(balanceBasic, positionMargin, positionMarginReal, timeUpdate, profitLossMax, unrealizedProfitMin, symbol2OrdersEntry,
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
                            "unP:{}\tunPMin:{}\t{}\t{}\t{}%\t{}\tdone:{}/{}/{} run:{}/{} f:{}",
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
                    slMonth.longValue(), totalSL, allOrderDone.size(), counterOrderCreated.get(),
                    counterOrderRunning(symbol2OrdersEntry), maxOrderRunning, totalFundingFee.longValue());
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

    private Integer counterOrderRunning(ConcurrentHashMap<String, List<OrderTargetInfoTest>> symbol2OrdersEntry) {
        int counter = 0;
        for (List<OrderTargetInfoTest> orders : symbol2OrdersEntry.values()) {
            counter += orders.size();
        }
        return counter;
    }

    private Double calFee(OrderTargetInfoTest orderInfo) {
        return orderInfo.quantity * orderInfo.priceEntry * Configs.RATE_FEE;
    }

    public Double calUnrealizedProfitMin(Collection<OrderTargetInfoTest> orderInfos) {
        Double result = 0d;
        for (OrderTargetInfoTest orderInfo : orderInfos) {
            Double profit = orderInfo.calProfitMin();
            result += profit;
//            LOG.info("{} {} {} {} {} {}",orderInfo.symbol, orderInfo.side, orderInfo.priceEntry, orderInfo.minPrice
//            , orderInfo.maxPrice, profit);
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

    public Double calPositionMarginReal(Collection<OrderTargetInfoTest> values) {
        Double totalMargin = 0d;
        if (values != null) {
            for (OrderTargetInfoTest orderInfo : values) {
                Double margin = orderInfo.calMargin();
                totalMargin += margin - orderInfo.calProfit();
            }
        }
        return totalMargin;
    }


    public void updateInvesting(Collection<OrderTargetInfoTest> orderRunning) {
        LOG.info("Update for symbol: {}", orderRunning.stream().count());
//        Double margin = calPositionMargin(orderRunning);
//        investing = margin * 100 / balanceCurrent;
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


    public static void main(String[] args) {
//        for (int i = 2; i < 11; i++) {
//            int numberOrder = i * 2;
//            Configs.NUMBER_ENTRY_EACH_SIGNAL = numberOrder;
//            BudgetManagerSimple.getInstance().updateBudget();
//            LOG.info("{} -> {}", Configs.NUMBER_ENTRY_EACH_SIGNAL, BudgetManagerSimple.getInstance().getBudget());
//        }
//        String symbol = "CATIUSDT";
        System.out.println(BudgetManagerSimple.getInstance().getBudget());
//        Double rate = Utils.rateOf2Double(1.454, 1.441);
//        System.out.println(BudgetManagerSimple.getInstance().calRateStop(rate,symbol));
//        for (int i = 0; i < 30; i++) {
//            Double rate = -0.032 + i * 0.005;
//            LOG.info("{}  -> {}", rate, BudgetManagerSimple.getInstance().calRateLossDynamic(rate, symbol, 0.004));
//        }
    }

    public void updateMaxOrderRunning(Integer counterOrderRunning) {
        if (maxOrderRunning < counterOrderRunning) {
            maxOrderRunning = counterOrderRunning;
        }
    }

// Thêm phương thức static này vào bên trong class BudgetManagerSimple.java

    /**
     * Xác định chế độ vốn hiện tại dựa trên mức độ sụt giảm của tài khoản.
     *
     * @return Chế độ vốn hiện tại (SAFE, CAUTION, hoặc DEFENSIVE).
     */
    public CapitalMode getCurrentCapitalMode() {
        double drawdownPercentage = unProfit / balanceBasic;

        if (drawdownPercentage < -0.50) { // Sụt giảm hơn 40% -> Phòng thủ
            return CapitalMode.DEFENSIVE;
        } else if (drawdownPercentage < -0.30) { // Sụt giảm từ 20% - 40% -> Thận trọng
            return CapitalMode.CAUTION;
        } else { // Sụt giảm dưới 30% -> An toàn
            if (positionMargin > balanceCurrent * 0.4) {
                return CapitalMode.CAUTION;
            } else {
                return CapitalMode.SAFE;
            }
        }
    }
}
