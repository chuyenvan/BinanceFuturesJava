/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;


/**
 * @author pc
 */
public class BudgetManagerSimple {

    public static final Logger LOG = LoggerFactory.getLogger(BudgetManagerSimple.class);

    public BalanceIndex balanceIndex = new BalanceIndex();

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

    // 1. Dùng ThreadLocal thay vì static instance đơn thuần
    private static final ThreadLocal<BudgetManagerSimple> threadLocalInstance = ThreadLocal.withInitial(BudgetManagerSimple::new);

    public static BudgetManagerSimple getInstance() {
        // Mỗi luồng gọi hàm này sẽ nhận được một instance riêng của nó
        return threadLocalInstance.get();
    }

    public static void resetInstance() {
        // Xóa dữ liệu cũ của luồng hiện tại để bắt đầu test mới
        threadLocalInstance.remove();
    }

    public void updateBudget() {
        investing = 0d;
        try {
            BUDGET_PER_ORDER = balanceBasic / Configs.number_order_budget;
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public Double getBudget() {
        return BUDGET_PER_ORDER;
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

    public void updatePositionMargin(Collection<OrderTargetInfoTest> orderInfos) {
        positionMargin = calPositionMargin(orderInfos);
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

        Double positionMarginReal = positionMargin;
        balanceIndex.updateIndex(balanceBasic, positionMargin, positionMarginReal, timeUpdate, profitLossMax, profitLossMax, symbol2OrdersEntry,
                orderRunning, unProfit);
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


            LOG.info("Update {} => b:{} pD:{}\tm:{}\tmax:{}\t{}\t" +
                            "unP:{}\tunPMin:{}\t{}\t{}\t{}%\tdone:{}/{}/{} run:{}/{} f:{}",
                    Utils.normalizeDateYYYYMMDDHHmm(timeUpdate), Utils.formatLog(balance.longValue(), 5),
                    Utils.formatLog(profitOfDate.longValue(), 4),
                    Utils.formatLog(positionMargin.longValue(), 4),

                    Utils.formatLog(marginMaxDate.longValue(), 5),
                    Utils.formatLog(marginMaxMonth.longValue(), 5),
                    Utils.formatLog(unProfit.longValue(), 5),
                    Utils.formatLog(balanceIndex.unProfitMin.longValue(), 5),
                    Utils.formatLog(unProfitDate.longValue(), 5),
                    Utils.formatLog(unProfitMonth.longValue(), 5),
                    Utils.formatPercentNew(balanceIndex.unProfitMin / balanceBasic),
                    totalSL, allOrderDone.size(), counterOrderCreated.get(),
                    counterOrderRunning(symbol2OrdersEntry), maxOrderRunning, totalFundingFee.longValue());
//            if (timeUpdate.equals(Utils.getToDay() + 7 * Utils.TIME_HOUR)) {
////                LOG.info("Report: {}", Utils.normalizeDateYYYYMMDDHHmm(timeUpdate));
//                List<String> lines =
//                        new ArrayList<>();
//                StringBuilder builder = new StringBuilder();
//                builder.append("capital: ").append(Configs.MAX_CAPITAL_RATE);
//                builder.append(" balance: ").append(balance.longValue());
//                builder.append(" balanceReal: ").append(balanceReal.longValue());
//                builder.append(" done: ").append(allOrderDone.size());
//                builder.append(balanceIndex.marginMax + " " + balanceIndex.rateMarginMax + " "
//                        + Utils.normalizeDateYYYYMMDDHHmm(balanceIndex.timeMarginMax) + " " +
//                        balanceIndex.profitLossMax);
//                lines.add(builder.toString());
//                try {
//                    FileUtils.writeLines(new File("storage/report.txt"), lines, true);
//                } catch (IOException e) {
//                    e.printStackTrace();
//                }
//            }
        }
//        if ((balance + unrealizedProfitMin) < 0) {
//            LOG.info("Chay tai khoan {} -----------------------------------!", Utils.normalizeDateYYYYMMDDHHmm(timeUpdate));
//        }
//        updateBudget();
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
            Double profit = orderInfo.profitMin;
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
            result += orderInfo.profitMin;
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

}
