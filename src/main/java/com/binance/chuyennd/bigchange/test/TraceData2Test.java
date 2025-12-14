package com.binance.chuyennd.bigchange.test;

import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.BalanceIndex;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.text.ParseException;
import java.util.*;

public class TraceData2Test {
    public static final Logger LOG = LoggerFactory.getLogger(TraceData2Test.class);

    public static void main(String[] args) throws ParseException {
        // for debug
//        args = new String[4];
//        args[0] = "rate_change";
//        args[3] = "btc";
//        args[1] = "20210201";
//        args[2] = "07:05";
//        showFileAll("OrderTestDone.data-16-0.04");
//showGrid();
//        writeData2Diff("20241106", "14:42");

        // end debug
//        if (args.length > 2) {
//        traceDataByHand(args);

        traceLog("Update");
        showFileAll("OrderTestDone.data");

//        showFileAll("OrderTestDone.data");
//        } else {

//        String symbol = "TIAUSDT";
//        traceRateChangeCloseListOnExchange(symbol);
//        testTrendDetector(symbol);
//            Long time = Utils.sdfFileHour.parse(Configs.getString("TIME_CHECK")).getTime();
//        traceDataRateChange(time);
//            traceDataStatistic(time);
//        printRateChange1MofBTC();
//        List<Long> timeBtcCutUp = extractBtcUpReverse();
//        diffFileCsv();
//        }
    }


    public static String statisticResult(TreeMap<Long, OrderTargetInfoTest> time2Order) {
        int slow_days = 45;
        Map<MarketLevelChange, List<OrderTargetInfoTest>> level2Orders = new HashMap<>();
        Map<Long, List<OrderTargetInfoTest>> times2OrderDone = new HashMap<>();
        Map<Integer, List<Double>> year2Pnl = new HashMap<>();
        TreeMap<Long, Double> date2Profit = new TreeMap();
        for (OrderTargetInfoTest orderInfo : time2Order.values()) {
//            if (orderInfo.status.equals(OrderTargetStatus.REQUEST)) {
//                continue;
//            }
            Long time = orderInfo.timeUpdate;
            List<OrderTargetInfoTest> orders = level2Orders.get(orderInfo.marketLevelChange);
            if (orders == null) {
                orders = new ArrayList<>();
            }
            orders.add(orderInfo);

            List<OrderTargetInfoTest> orderDoneByTimes = times2OrderDone.get(orderInfo.timeUpdate);
            if (orderDoneByTimes == null) {
                orderDoneByTimes = new ArrayList<>();
                times2OrderDone.put(orderInfo.timeUpdate, orderDoneByTimes);
            }
            orderDoneByTimes.add(orderInfo);

            Double profitOfDate = date2Profit.get(Utils.getDate(time));
            if (profitOfDate == null) {
                profitOfDate = 0d;
            }
            profitOfDate += orderInfo.calTp();
            date2Profit.put(Utils.getDate(time), profitOfDate);
            level2Orders.put(orderInfo.marketLevelChange, orders);
            Double tp = orderInfo.calTp();
            List<Double> pnlOfYear = year2Pnl.get(Utils.getYear(time));
            if (pnlOfYear == null) {
                pnlOfYear = new ArrayList<>();
            }
            pnlOfYear.add(tp);
            year2Pnl.put(Utils.getYear(time), pnlOfYear);
        }
        TreeMap<Double, Long> profit2Date = new TreeMap();
        TreeMap<Integer, Double> year2Profit = new TreeMap();
        TreeMap<Integer, Double> year2MarginMax = new TreeMap();
        TreeMap<Integer, Double> year2UnProfitMin = new TreeMap();
        TreeMap<Integer, Integer> year2OrderBigCounter = new TreeMap();
        TreeMap<Integer, Integer> year2OrderSpecialBigCounter = new TreeMap();
        TreeMap<Integer, Integer> year2OrderBigFalseCounter = new TreeMap();
        TreeMap<Integer, Integer> year2OrderBigSlowCounter = new TreeMap();
        TreeMap<Integer, Integer> year2OrderBuySlowCounter = new TreeMap();

        BalanceIndex balanceIndex = (BalanceIndex) Storage.readObjectFromFile("../simulator/storage/BalanceIndex.data");
//        BalanceIndex balanceIndex = (BalanceIndex) Storage.readObjectFromFile("storage/BalanceIndex.data");

        for (Long date : balanceIndex.date2MarginMax.keySet()) {
            Double marginMax = balanceIndex.date2MarginMax.get(date);
            Double yearMarginMax = year2MarginMax.get(Utils.getYear(date));
            if (yearMarginMax == null || yearMarginMax < marginMax) {
                yearMarginMax = marginMax;
            }
            year2MarginMax.put(Utils.getYear(date), yearMarginMax);
        }
        for (Integer year : year2MarginMax.keySet()) {
            year2OrderBigCounter.put(year, 0);
            year2OrderSpecialBigCounter.put(year, 0);
            year2OrderBigFalseCounter.put(year, 0);
            year2OrderBigSlowCounter.put(year, 0);
            year2OrderBuySlowCounter.put(year, 0);
        }
        for (Long time : times2OrderDone.keySet()) {

            List<OrderTargetInfoTest> orders = times2OrderDone.get(time);
            Map<String, Double> symbol2Margin = new HashMap<>();
            Long timeOrder = 0l;

            OrderTargetStatus status = orders.get(0).status;
            for (OrderTargetInfoTest orderTarget : orders) {
                Double margin = symbol2Margin.get(orderTarget.symbol);
                if (margin == null) {
                    margin = 0d;
                }
                margin += orderTarget.calMargin();
                symbol2Margin.put(orderTarget.symbol, margin);
                if (timeOrder < orderTarget.timeUpdate - orderTarget.timeStart) {
                    timeOrder = orderTarget.timeUpdate - orderTarget.timeStart;
                }
            }
            if (timeOrder > slow_days * Utils.TIME_DAY) {
                int year = Utils.getYear(orders.get(0).timeStart);
                Integer counterOrderSlow = year2OrderBuySlowCounter.get(year);
                if (counterOrderSlow == null) {
                    counterOrderSlow = 0;
                }
                counterOrderSlow++;
                year2OrderBuySlowCounter.put(year, counterOrderSlow);

            }
            for (String symbol : symbol2Margin.keySet()) {
                Double margin = symbol2Margin.get(symbol);
                int numberBudgetBig = 3;
                if (Constants.specialSymbol.contains(symbol)) {
                    numberBudgetBig = 5;
                }
                if (margin > numberBudgetBig * BudgetManagerSimple.getInstance().getBudget()) {
                    int year = Utils.getYear(time);
                    Integer counterOrder = year2OrderBigCounter.get(year);
                    if (counterOrder == null) {
                        counterOrder = 0;
                    }
                    counterOrder++;
                    year2OrderBigCounter.put(year, counterOrder);
                    if (Constants.specialSymbol.contains(symbol)) {
                        Integer counterOrderSpecial = year2OrderSpecialBigCounter.get(year);
                        if (counterOrderSpecial == null) {
                            counterOrderSpecial = 0;
                        }
                        counterOrderSpecial++;
                        year2OrderSpecialBigCounter.put(year, counterOrderSpecial);
                    }
                    OrderSide sideBig = null;
                    for (OrderTargetInfoTest order : orders) {
                        if (StringUtils.equals(symbol, order.symbol)) {
                            sideBig = order.side;
                            break;
                        }
                    }
                    LOG.info("Big: {} {} {} {} ", symbol, sideBig,
                            Utils.normalizeDateYYYYMMDDHHmm(orders.get(0).timeUpdate), margin.longValue());

                    if (timeOrder > slow_days * Utils.TIME_DAY) {
                        Integer counterOrderSlow = year2OrderBigSlowCounter.get(year);
                        if (counterOrderSlow == null) {
                            counterOrderSlow = 0;
                        }
                        counterOrderSlow++;
                        year2OrderBigSlowCounter.put(year, counterOrderSlow);
                    }
                    if (status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                        Integer counterOrderFalse = year2OrderBigFalseCounter.get(year);
                        if (counterOrderFalse == null) {
                            counterOrderFalse = 0;
                        }
                        counterOrderFalse++;
                        year2OrderBigFalseCounter.put(year, counterOrderFalse);
                    }
                }
            }
        }
        for (Long date : balanceIndex.date2ProfitMin.keySet()) {
            Double profitMin = balanceIndex.date2ProfitMin.get(date);
            Double yearProfitMin = year2UnProfitMin.get(Utils.getYear(date));
            if (yearProfitMin == null || yearProfitMin > profitMin) {
                yearProfitMin = profitMin;
            }
            year2UnProfitMin.put(Utils.getYear(date), yearProfitMin);
        }
        for (Long time : date2Profit.keySet()) {
            Integer year = Utils.getYear(time);
            Double profitOfYear = year2Profit.get(year);
            if (profitOfYear == null) {
                profitOfYear = 0d;
            }
            profitOfYear += date2Profit.get(time);
            year2Profit.put(year, profitOfYear);
            profit2Date.put(date2Profit.get(time), time);
        }
        TreeMap<Double, Long> profit30d2Date = new TreeMap();
        Long dateFirst = date2Profit.firstKey();
        for (int i = 30; i < date2Profit.size(); i++) {
            Double profit30d = 0d;
            for (int j = 0; j < 30; j++) {
                Long date30 = dateFirst + (i - 30 + j) * Utils.TIME_DAY;
                Double profitDate = date2Profit.get(date30);
                if (profitDate == null) {
                    profitDate = 0d;
                }
                profit30d += profitDate;
            }
            profit30d2Date.put(profit30d, dateFirst + i * Utils.TIME_DAY);
        }
        StringBuilder builder = new StringBuilder();
        int counter = 0;

        for (Map.Entry<Double, Long> entry : profit2Date.entrySet()) {
            builder.append("\n").append(Utils.normalizeDateYYYYMMDD(entry.getValue()))
                    .append("\t").append(entry.getKey().longValue());
            counter++;
            if (counter > 10) {
                break;
            }
        }
        for (Map.Entry<Integer, Double> entry : year2Profit.entrySet()) {
            Integer year = entry.getKey();
            int lastYear = year - 1;
            Double unPLastYear = balanceIndex.year2UnrealizedPnl.get(lastYear);
            if (unPLastYear == null) {
                unPLastYear = 0d;
            }
            Double unPYear = balanceIndex.year2UnrealizedPnl.get(year);
            if (balanceIndex.year2UnrealizedPnl.get(year + 1) == null) {
                unPYear = 0d;
            }
            double profitOfYear = entry.getValue() - unPLastYear + unPYear;
            LOG.info("{} {} {} {}-> {}", year, unPLastYear, balanceIndex.year2UnrealizedPnl.get(year), entry.getValue(), profitOfYear);
            year2Profit.put(year, profitOfYear);
        }
        for (Map.Entry<Integer, Double> entry : year2Profit.entrySet()) {
            builder.append("\n");
            Integer year = entry.getKey();
            builder.append(year).append("\t");
            builder.append("Margin: ").append(year2MarginMax.get(year).longValue()).append("\t");
            builder.append("UnProfitMin: ").append(year2UnProfitMin.get(year).longValue()).append("\t");
            builder.append("ProfitMin: ").append(Utils.formatLog(Utils.findMinSubarraySum(year2Pnl.get(year).toArray(new Double[0])).longValue(), 5)).append("\t");
            builder.append("Big: ").append(Utils.formatLog(year2OrderSpecialBigCounter.get(year), 3))
                    .append("/").append(Utils.formatLog(year2OrderBigCounter.get(year), 3)).append("\t");
            builder.append("Big_False: ").append(Utils.formatLog(year2OrderBigFalseCounter.get(year), 3)).append("\t");
            builder.append("Slow_Big_Buy: ").append(Utils.formatLog(year2OrderBigSlowCounter.get(year), 3))
                    .append("/").append(Utils.formatLog(year2OrderBuySlowCounter.get(year), 3)).append("\t");
            builder.append("UnPnl: ").append(balanceIndex.year2UnrealizedPnl.get(year).longValue()).append("\t");
            builder.append(entry.getValue().longValue()).append("\t");
            builder.append(Utils.formatDouble(entry.getValue() / BudgetManagerSimple.getInstance().balanceBasic, 2));
        }
        counter = 0;
        for (Map.Entry<Double, Long> entry : profit30d2Date.entrySet()) {
            builder.append("\n").append(Utils.normalizeDateYYYYMMDD(entry.getValue())).append("\t")
                    .append(entry.getKey().longValue());
            counter++;
            if (counter > 10) {
                break;
            }
        }
        return builder.toString();

    }


    private static Double calRateProfit(List<OrderTargetInfoTest> orders) {
        Double rate = 0d;
        Double total = 0d;
        for (OrderTargetInfoTest order : orders) {
            total += order.calRateTp();
        }
        if (!orders.isEmpty()) {
            return total / orders.size();
        }
        return rate;
    }

    private static void showFileAll(String fileName) {
        fileName = "../simulator/storage/" + fileName;
//        fileName = "storage/" + fileName;
        BudgetManagerSimple.getInstance().updateBudget();
        TreeMap<Long, OrderTargetInfoTest> allOrderDone = (TreeMap<Long, OrderTargetInfoTest>) Storage.readObjectFromFile(fileName);

        Map<MarketLevelChange, List<OrderTargetInfoTest>> level2Order = new HashMap<>();
        String statisticLog = statisticResult(allOrderDone);

        int maxSize = 0;
//        for (OrderTargetInfoTest order : allOrderDone.values()) {
        for (Long time : allOrderDone.keySet()) {
            OrderTargetInfoTest order = allOrderDone.get(time);
            if (order.marketLevelChange == null) {
//                order.marketLevelChange = MarketLevelChange.ALT_SIDEWAY_REVERSE;
            }
            List<OrderTargetInfoTest> orders = level2Order.get(order.marketLevelChange);
            if (orders == null) {
                orders = new ArrayList<>();
                level2Order.put(order.marketLevelChange, orders);
            }
            orders.add(order);
            if (maxSize < order.marketLevelChange.toString().length()) {
                maxSize = order.marketLevelChange.toString().length();
            }
        }

        TreeMap<Double, String> rateSuccess2Log = new TreeMap<>();
        for (MarketLevelChange level : level2Order.keySet()) {
            StringBuilder sb = new StringBuilder();
            String levelName = level.toString();
            for (int i = 0; i < maxSize - level.toString().length(); i++) {
                levelName += " ";
            }
            List<OrderTargetInfoTest> orderLevels = level2Order.get(level);
            TreeMap<String, List<OrderTargetInfoTest>> year2Orders = new TreeMap<>();
            Double totalRate = 0d;
            Double totalProfit = 0d;
            Integer counterFalse = 0;
            Integer counterDone = 0;
            for (OrderTargetInfoTest order : orderLevels) {
                totalRate += order.calRateTp();
                totalProfit += order.calTp();
                if (order.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                    counterFalse++;
                } else {
                    counterDone++;
                }
                String month = Utils.getMonth(order.timeStart);
                String year = month.substring(0, 4);
                List<OrderTargetInfoTest> orders = year2Orders.get(year);
                if (orders == null) {
                    orders = new ArrayList<>();
                    year2Orders.put(year, orders);
                }
                orders.add(order);
            }
            sb.append(levelName);
            sb.append("\t => All: ").append(Utils.formatLog(Utils.formatDouble(totalRate * 100 / orderLevels.size(), 3), 5))
                    .append("\t").append(Utils.formatLog(orderLevels.size(), 5))
                    .append("\t").append(Utils.formatLog(totalProfit.longValue(), 5))
//                    .append("\t").append(Utils.formatLog(counterFalse, 4)).append("/").append(Utils.formatLog(counterDone, 4))
                    .append("\t");
            for (String year : year2Orders.keySet()) {
                List<OrderTargetInfoTest> orders = year2Orders.get(year);
                double totalYear = 0d;
                Double totalYearProfit = 0d;
                for (OrderTargetInfoTest order : orders) {
                    totalYear += order.calRateTp();
                    totalYearProfit += order.calTp();
                }
                sb.append(year).append(": ")
                        .append(Utils.formatLog(Utils.formatDouble(totalYear * 100 / orders.size(), 3), 6)).append("\t")
                        .append(Utils.formatLog(orders.size(), 5)).append("\t")
                        .append(Utils.formatLog(totalYearProfit.longValue(), 5)).append(" $\t");
            }
            rateSuccess2Log.put(-totalRate * 100 / orderLevels.size(), sb.toString());
        }
        StringBuilder sb = new StringBuilder();

        sb.append(statisticLog).append("\n");
        for (String line : rateSuccess2Log.values()) {
            sb.append(line).append("\n");
        }
        LOG.info(sb.toString());
    }


    public static Double extractProfitOfLine(String line) {
        try {
            String[] parts = StringUtils.split(line, ":");
            String pDate = parts[6];
            pDate = StringUtils.split(pDate, "\t")[0];
            return Double.parseDouble(pDate);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    private static Double extractBalanceOfLine(String line) {
        try {
            String[] parts = StringUtils.split(line, ":");
            String pDate = parts[5];
            pDate = StringUtils.split(pDate, " ")[0];
            return Double.parseDouble(pDate);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    private static String extractDateOfLine(String line) {
        try {
            String[] parts = StringUtils.split(line, " ");
            String date = parts[6];
            return date;
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static void traceLog(String log) {
        try {
            List<String> lines = FileUtils.readLines(new File("../simulator/logs/nohup.out"));
            TreeMap<Double, String> profit2Date = new TreeMap();
            TreeMap<Long, Double> date2Profit = new TreeMap();
            TreeMap<Long, Double> date2Balance = new TreeMap();
            List<String> logMonths = new ArrayList<>();
//            String profitReport = null;
            try {
                for (String line : lines) {
                    if (StringUtils.contains(line, log) && StringUtils.contains(line, "b:")) {
                        Double profit = extractProfitOfLine(line);
                        Double balance = extractBalanceOfLine(line);
                        String date = extractDateOfLine(line);
//                    LOG.info("Balance: {} {}",date, balance);
                        profit2Date.put(profit, date);
                        if (StringUtils.endsWith(date, "01")) {
                            logMonths.add(line.split(log)[1]);
                        }
                        date2Profit.put(Utils.sdfFile.parse(date).getTime(), profit);
                        date2Balance.put(Utils.sdfFile.parse(date).getTime(), balance);
                    }
                }
                TreeMap<Double, Long> profit30d2Date = new TreeMap();
                int counter = 0;
                Set<String> hashSet = new HashSet<>();
//                for (Map.Entry<Double, String> entry : profit2Date.entrySet()) {
//                    if (hashSet.contains(entry.getValue())) {
//                        continue;
//                    }
//                    LOG.info("{} {}", entry.getValue(), entry.getKey());
//                    hashSet.add(entry.getValue());
//                    counter++;
//                    if (counter > 10) {
//                        break;
//                    }
//                }
                Long dateFirst = date2Profit.firstKey();
                for (int i = 30; i < date2Profit.size(); i++) {
                    Double profit30d = 0d;
                    for (int j = 0; j < 30; j++) {
                        Long date30 = dateFirst + (i - 30 + j) * Utils.TIME_DAY;
                        profit30d += date2Profit.get(date30);
                    }
                    profit30d2Date.put(profit30d, dateFirst + i * Utils.TIME_DAY);
                }
                counter = 0;
//                Double profit2021 = date2Balance.get(Utils.sdfFile.parse("20220101").getTime())
//                        - date2Balance.get(Utils.sdfFile.parse("20210101").getTime());
//                Double profit2022 = date2Balance.get(Utils.sdfFile.parse("20230101").getTime())
//                        - date2Balance.get(Utils.sdfFile.parse("20220101").getTime());
//                Double profit2023 = date2Balance.get(Utils.sdfFile.parse("20240101").getTime()) -
//                        date2Balance.get(Utils.sdfFile.parse("20230101").getTime());
//                Double profit2024 = date2Balance.lastEntry().getValue() - date2Balance.get(Utils.sdfFile.parse("20240101").getTime());
//                LOG.info("Year 2021: {}\t{}\t{}", date2Balance.get(Utils.sdfFile.parse("20220101").getTime()),
//                        profit2021, Utils.formatDouble(profit2021 / BudgetManagerSimple.getInstance().balanceBasic, 2));
//                LOG.info("Year 2022: {}\t{}\t{}", date2Balance.get(Utils.sdfFile.parse("20230101").getTime()),
//                        profit2022, Utils.formatDouble(profit2022 / BudgetManagerSimple.getInstance().balanceBasic, 2));
//                LOG.info("Year 2023: {}\t{}\t{}", date2Balance.get(Utils.sdfFile.parse("20240101").getTime()),
//                        profit2023, Utils.formatDouble(profit2023 / BudgetManagerSimple.getInstance().balanceBasic, 2));
//                LOG.info("Year 2024: {}\t{}\t{}", date2Balance.lastEntry().getValue(),
//                        profit2024, Utils.formatDouble(profit2024 / BudgetManagerSimple.getInstance().balanceBasic, 2));
//                for (Map.Entry<Double, Long> entry : profit30d2Date.entrySet()) {
//                    LOG.info("{} {}", Utils.normalizeDateYYYYMMDD(entry.getValue()), entry.getKey());
//                    counter++;
//                    if (counter > 10) {
//                        break;
//                    }
//                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            StringBuilder builder = new StringBuilder();
            for (String logMonth : logMonths) {
                builder.append(logMonth).append("\n");
            }
            LOG.info(builder.toString());
        } catch (Exception e) {
            e.printStackTrace();
        }

    }



}
