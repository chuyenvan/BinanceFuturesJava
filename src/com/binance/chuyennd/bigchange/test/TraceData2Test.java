package com.binance.chuyennd.bigchange.test;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.bigchange.statistic.data.DataStatisticHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.*;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
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

//        writeData2Diff("20241106", "14:42");

        // end debug
        if (args.length > 2) {
            traceDataByHand(args);
        } else {

//        String symbol = "TIAUSDT";
//        traceRateChangeCloseListOnExchange(symbol);
//        testTrendDetector(symbol);
//            Long time = Utils.sdfFileHour.parse(Configs.getString("TIME_CHECK")).getTime();
//        traceDataRateChange(time);
//            traceDataStatistic(time);
//        printRateChange1MofBTC();
//        List<Long> timeBtcCutUp = extractBtcUpReverse();
//        diffFileCsv();
        }
    }

    private static void traceDataRateChange(Long startTime) {

        TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
        time2Tickers = DataManager.readDataFromFile1M(startTime);
        LOG.info("Check time:{}", startTime);
        if (time2Tickers != null) {
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                Long time = entry.getKey();
                Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                TreeMap<Double, String> rateDown2Symbols = new TreeMap<>();
                TreeMap<Double, String> rateUp2Symbols = new TreeMap<>();
                for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
                    String symbol = entry1.getKey();
                    if (Constants.diedSymbol.contains(symbol)) {
                        continue;
                    }

                    KlineObjectSimple ticker = entry1.getValue();
                    // update order Old

                    if (Utils.isTickerAvailable(ticker)) {
                        Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
                        rateDown2Symbols.put(rateChange, symbol);
                        rateUp2Symbols.put(-rateChange, symbol);
                    }
                }
                // stop trade when capital over
//                        if (BudgetManagerSimple.getInstance().isAvailableTrade()) {
                KlineObjectSimple btcTicker = symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC);
                Double btcRateChange = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen);
                Double rateChangeDownAvg = MarketBigChangeDetectorTest.calRateLossAvg(rateDown2Symbols, 50);
                Double rateChangeUpAvg = -MarketBigChangeDetectorTest.calRateLossAvg(rateUp2Symbols, 50);
                LOG.info("{} down:{} up:{} btcRate:{} btcVol:{}", Utils.normalizeDateYYYYMMDDHHmm(time),
                        Utils.formatDouble(rateChangeDownAvg * 100, 2), Utils.formatDouble(rateChangeUpAvg * 100, 2),
                        Utils.formatDouble(btcRateChange * 100, 2), btcTicker.totalUsdt / 1E6);
            }
        }
    }

    private static void traceDataByHand(String[] args) {
        LOG.info(args[0] + " " + args[1]);
        String mode = args[0];
        switch (mode) {
            case "rate_change":
                printData1M(args[1], args[2], args[3]);
                break;
            case "write_data":
                writeData2Diff(args[1], args[2]);
                break;
            case "get_top_down":
                getTopDown(args[1], args[2]);
                break;
            case "test_time":
                testTradeTime(args[1], args[2]);
                break;
            case "get_top_up":
                getTopUp(args[1], args[2]);
                break;
            case "trace_loss":
                traceLog(args[1]);
                showFileAll("OrderTestDone.data-" + args[2]);
                break;
            case "trade":
                tradeAOrder(args[1], args[2], args[3], args[4]);
                break;
            case "trade_detail":
                try {
                    new TraceDetailAllDataWithTime().simulatorEntryByTime(args[1], args[2], args[3]);
                } catch (Exception e) {
                    e.printStackTrace();
                }
                break;
            case "showbylevel":
                showByLevel();
                break;
            case "showAll":
                showFileAll(args[1]);
                break;
            case "showSymbol":
                showFileAllBySymbol(args[1], args[2]);
                break;
        }
    }

    private static void testTradeTime(String timeInput1, String timeInput2) {
        try {
            String timeInput = timeInput1.trim() + " " + timeInput2.trim();
            Long time = Utils.sdfFileHour.parse(timeInput).getTime();
            Long startTime = Utils.getDate(time - 15 * Utils.TIME_MINUTE);

            // data ticker
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManager.readDataFromFile1M(startTime);
            TreeMap<Long, Map<String, KlineObjectSimple>> dataNextDate = DataManager.readDataFromFile1M(startTime + Utils.TIME_DAY);
            TreeMap<Long, Map<String, KlineObjectSimple>> dataNext1Date = DataManager.readDataFromFile1M(startTime + 2 * Utils.TIME_DAY);
            if (dataNextDate != null) {
                time2Tickers.putAll(dataNextDate);
            }
            if (dataNext1Date != null) {
                time2Tickers.putAll(dataNext1Date);
            }
            Map<String, Double> symbol2MaxPrice = new HashMap<>();
            Map<String, Double> symbol2MinPrice = new HashMap<>();
            for (int i = 1; i < 16; i++) {
                Map<String, KlineObjectSimple> symbol2Ticker = time2Tickers.get(time - i * Utils.TIME_MINUTE);
                for (String symbol : symbol2Ticker.keySet()) {
                    KlineObjectSimple kline = symbol2Ticker.get(symbol);
                    Double priceMax = symbol2MaxPrice.get(symbol);
                    Double minPrice = symbol2MinPrice.get(symbol);
                    if (priceMax == null || priceMax < kline.maxPrice) {
                        priceMax = kline.maxPrice;
                    }
                    if (minPrice == null || minPrice > kline.minPrice) {
                        minPrice = kline.minPrice;
                    }
                    symbol2MaxPrice.put(symbol, priceMax);
                    symbol2MinPrice.put(symbol, minPrice);
                }
            }
            MarketDataObject marketData = MarketBigChangeDetectorTest.calMarketData(time2Tickers.get(time), symbol2MaxPrice,
                    symbol2MinPrice);
            List<String> symbols = MarketBigChangeDetectorTest.getTopSymbolSimple(marketData.rate2Max, 4, null);
            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();
            test.initData();
            test.runMultiOrder(symbols, timeInput);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void writeData2Diff(String timeInput1, String timeInput2) {
        try {
            String timeInput = timeInput1.trim() + " " + timeInput2.trim();
            Long time = Utils.sdfFileHour.parse(timeInput).getTime();
            Long startTime = Utils.getDate(time - 30 * Utils.TIME_MINUTE);
            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();
            test.initData();
            test.simulatorWithInitEntry(Utils.getDayByTime(startTime), timeInput);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void showByLevel() {
        EnumSet<MarketLevelChange> all = EnumSet.allOf(MarketLevelChange.class);
        List<MarketLevelChange> list = new ArrayList<>(all.size());
        int maxSize = 0;
        for (MarketLevelChange s : all) {
            list.add(s);
            if (maxSize < s.toString().length()) {
                maxSize = s.toString().length();
            }
        }

        for (MarketLevelChange level : list) {
            String fileName = "../simulator/storage/level/OrderTestDone-" + level + "-"
                    + Configs.TIME_AFTER_ORDER_2_SL;
            if (new File(fileName).exists()) {
                String levelString = level.toString();
                for (int i = 0; i < maxSize - level.toString().length(); i++) {
                    levelString += " ";
                }
                traceFile(levelString, fileName);
            }
        }
    }

    public static String statisticResult(TreeMap<Long, OrderTargetInfoTest> time2Order) {
        Map<MarketLevelChange, List<OrderTargetInfoTest>> level2Orders = new HashMap<>();
        Map<Integer, List<Double>> year2Pnl = new HashMap<>();
        TreeMap<Long, Double> date2Profit = new TreeMap();
        for (OrderTargetInfoTest orderInfo : time2Order.values()) {
            Long time = orderInfo.timeUpdate;
            List<OrderTargetInfoTest> orders = level2Orders.get(orderInfo.marketLevelChange);
            if (orders == null) {
                orders = new ArrayList<>();
            }
            orders.add(orderInfo);
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
        TreeMap<Integer, Double> year2MarginRealMax = new TreeMap();
        TreeMap<Integer, Double> year2UnProfitMin = new TreeMap();
        TreeMap<Integer, Double> year2SLMin = new TreeMap();
        BalanceIndex balanceIndex = (BalanceIndex) Storage.readObjectFromFile("../simulator/storage/BalanceIndex.data");
        for (Long date : balanceIndex.date2MarginMax.keySet()) {
            Double marginMax = balanceIndex.date2MarginMax.get(date);
            Double yearMarginMax = year2MarginMax.get(Utils.getYear(date));
            if (yearMarginMax == null || yearMarginMax < marginMax) {
                yearMarginMax = marginMax;
            }
            year2MarginMax.put(Utils.getYear(date), yearMarginMax);
        }
        for (Long date : balanceIndex.date2MarginRealMax.keySet()) {
            Double marginRealMax = balanceIndex.date2MarginRealMax.get(date);
            Double yearMarginRealMax = year2MarginRealMax.get(Utils.getYear(date));
            if (yearMarginRealMax == null || yearMarginRealMax < marginRealMax) {
                yearMarginRealMax = marginRealMax;
            }
            year2MarginRealMax.put(Utils.getYear(date), yearMarginRealMax);
        }
        for (Long date : balanceIndex.date2ProfitMin.keySet()) {
            Double profitMin = balanceIndex.date2ProfitMin.get(date);
            Double yearProfitMin = year2UnProfitMin.get(Utils.getYear(date));
            if (yearProfitMin == null || yearProfitMin > profitMin) {
                yearProfitMin = profitMin;
            }
            year2UnProfitMin.put(Utils.getYear(date), yearProfitMin);
        }
        for (String month : balanceIndex.month2SLMax.keySet()) {
            try {
                Integer year = Utils.getYear(Utils.sdfMonth.parse(month).getTime());
                Double slMin = year2SLMin.get(year);
                Double monthSLMin = balanceIndex.month2SLMax.get(month);
                if (slMin == null || slMin > monthSLMin) {
                    slMin = monthSLMin;
                }
                year2SLMin.put(year, slMin);
            } catch (Exception e) {
                e.printStackTrace();
            }
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
            builder.append("\n");
            Integer year = entry.getKey();
            builder.append(year).append("\t");
            builder.append("Margin: ").append(year2MarginMax.get(year).longValue()).append("\t");
            builder.append("MarginReal: ").append(year2MarginRealMax.get(year).longValue()).append("\t");
            builder.append("UnProfitMin: ").append(year2UnProfitMin.get(year).longValue()).append("\t");
            builder.append("SLMin: ").append(year2SLMin.get(year).longValue()).append("\t");
            builder.append("ProfitMin: ").append(Utils.formatLog(Utils.findMinSubarraySum(year2Pnl.get(year).toArray(new Double[0])).longValue(), 5)).append("\t");
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
//        fileName = "target/" + fileName;
        TreeMap<Long, OrderTargetInfoTest> allOrderDone = (TreeMap<Long, OrderTargetInfoTest>) Storage.readObjectFromFile(fileName);

        Map<MarketLevelChange, List<OrderTargetInfoTest>> level2Order = new HashMap<>();
        String statisticLog = statisticResult(allOrderDone);

        int maxSize = 0;
//        for (OrderTargetInfoTest order : allOrderDone.values()) {
        for (Long time : allOrderDone.keySet()) {
            OrderTargetInfoTest order = allOrderDone.get(time);
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
            for (OrderTargetInfoTest order : orderLevels) {
                totalRate += order.calRateTp();
                totalProfit += order.calTp();
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


    private static void showFileAllBySymbol(String fileName, String symbol) {
        fileName = "../simulator/storage/" + fileName;
        if (!StringUtils.containsIgnoreCase(symbol, "USDT")) {
            symbol += "USDT";
        }
        symbol = symbol.toUpperCase();
        TreeMap<Long, OrderTargetInfoTest> allOrderDone = (TreeMap<Long, OrderTargetInfoTest>) Storage.readObjectFromFile(fileName);
        Map<MarketLevelChange, List<OrderTargetInfoTest>> level2Order = new HashMap<>();
        int maxSize = 0;
        int counterAll = 0;
        Double profitAll = 0d;
        Double rateTPAll = 0d;
        for (OrderTargetInfoTest order : allOrderDone.values()) {
            if (!StringUtils.equals(order.symbol, symbol)) {
                continue;
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
            for (OrderTargetInfoTest order : orderLevels) {
                totalRate += order.calRateTp();
                totalProfit += order.calTp();
                profitAll += order.calTp();
                counterAll++;
                rateTPAll += order.calRateTp();
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
            sb.append("\t => All: ").append(Utils.formatDouble(totalRate * 100 / orderLevels.size(), 3))
                    .append("\t").append(totalProfit.longValue()).append("\t");
            for (String year : year2Orders.keySet()) {
                List<OrderTargetInfoTest> orders = year2Orders.get(year);
                double totalYear = 0d;
                Double totalYearProfit = 0d;
                for (OrderTargetInfoTest order : orders) {
                    totalYear += order.calRateTp();
                    totalYearProfit += order.calTp();
                }
                sb.append(year).append(": ").append(Utils.formatDouble(totalYear * 100 / orders.size(), 3))
                        .append("\t").append(totalYearProfit.longValue()).append("\t");
            }
            LOG.info(sb.toString());
        }
        LOG.info("All: {} {}", (Utils.formatDouble(rateTPAll * 100 / counterAll, 3)), profitAll.longValue());
    }

    private static void traceFile(String levelName, String fileName) {
        StringBuilder sb = new StringBuilder();
        TreeMap<Long, OrderTargetInfoTest> allOrderDone = (TreeMap<Long, OrderTargetInfoTest>) Storage.readObjectFromFile(fileName);
        TreeMap<String, List<OrderTargetInfoTest>> year2Orders = new TreeMap<>();
        Double total = 0d;
        Double totalProfit = 0d;
        for (OrderTargetInfoTest order : allOrderDone.values()) {
            total += order.calRateTp();
            totalProfit += order.calTp();
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
        sb.append("\t => All: ").append(Utils.formatDouble(total * 100 / allOrderDone.size(), 3))
                .append("\t").append(totalProfit.longValue()).append("\t");
        for (String year : year2Orders.keySet()) {
            List<OrderTargetInfoTest> orders = year2Orders.get(year);
            double totalYear = 0d;
            Double totalYearProfit = 0d;
            for (OrderTargetInfoTest order : orders) {
                totalYear += order.calRateTp();
                totalYearProfit += order.calTp();
            }
            sb.append(year).append(": ").append(Utils.formatDouble(totalYear * 100 / orders.size(), 3))
                    .append("\t").append(totalYearProfit.longValue()).append("\t");
        }
        LOG.info(sb.toString());
    }

    private static void tradeAOrder(String timeInput1, String timeInput2, String symbol, String side) {
        try {
            String timeInput = timeInput1.trim() + " " + timeInput2.trim();
            if (!timeInput1.startsWith("202")) {
                timeInput = timeInput2.trim() + " " + symbol.trim();
                symbol = timeInput1;
            }
            if (!StringUtils.containsIgnoreCase(symbol, "USDT")) {
                symbol += "USDT";
            }
            symbol = symbol.toUpperCase();

            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();
            test.initData();
//            String symbol = "NEIROUSDT";
//            String time = "20241002 00:28";
            OrderSide orderSide = OrderSide.BUY;
            if (StringUtils.containsIgnoreCase(side, "sell")) {
                orderSide = OrderSide.SELL;
            }
            test.runAOrder(symbol, timeInput, orderSide);
        } catch (Exception e) {
            e.printStackTrace();
        }
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
            String profitReport = null;
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
                    if (StringUtils.contains(line, log) && StringUtils.contains(line, "ProfitMinAll")) {
                        profitReport = "\nProfitMinAll" + line.split("ProfitMinAll")[1];
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
                profitReport = profitReport.replaceAll("\t", "\n");
                LOG.info(profitReport);
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

    private static void printData1M(String timeInput1, String timeInput2, String symbol) {
        try {
            String timeInput = timeInput1.trim() + " " + timeInput2.trim();
            if (!timeInput1.startsWith("202")) {
                timeInput = timeInput2.trim() + " " + symbol.trim();
                symbol = timeInput1;
            }
            Long time = Utils.sdfFileHour.parse(timeInput).getTime();
//            Long time = Utils.sdfFileHour.parse("20230724 16:50").getTime();
//            String symbol = "KEYUSDT";
            Long startTime = Utils.getDate(time - 15 * Utils.TIME_MINUTE);

            // data ticker
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManager.readDataFromFile1M(startTime);
            TreeMap<Long, Map<String, KlineObjectSimple>> dataNextDate = DataManager.readDataFromFile1M(startTime + Utils.TIME_DAY);
            TreeMap<Long, Map<String, KlineObjectSimple>> dataNext1Date = DataManager.readDataFromFile1M(startTime + 2 * Utils.TIME_DAY);
            if (dataNextDate != null) {
                time2Tickers.putAll(dataNextDate);
            }
            if (dataNext1Date != null) {
                time2Tickers.putAll(dataNext1Date);
            }
            if (!StringUtils.containsIgnoreCase(symbol, "USDT")) {
                symbol += "USDT";
            }
            symbol = symbol.toUpperCase();
            LOG.info("{} {} {} {} {}", time, startTime, Utils.normalizeDateYYYYMMDDHHmm(startTime), time2Tickers.size());
            Double priceEntry = time2Tickers.get(time).get(symbol).priceClose;
            Double minPrice = 0d;
            Double maxPrice = 0d;
            for (int i = -2; i < 3000; i++) {
                Long timeCheck = time + i * Utils.TIME_MINUTE;
                Map<String, KlineObjectSimple> symbol2Ticker = time2Tickers.get(timeCheck);
                if (symbol2Ticker == null) {
                    if (i < 0) {
                        continue;
                    } else {
                        break;
                    }
                }
                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                if (i > 0 && (minPrice == 0d || minPrice > ticker.minPrice)) {
                    minPrice = ticker.minPrice;
                }
                if (i > 0 && (maxPrice == 0d || maxPrice < ticker.maxPrice)) {
                    maxPrice = ticker.maxPrice;
                }
                Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
                Double rateChangeMax = Utils.rateOf2Double(ticker.maxPrice, ticker.priceOpen);
                Double rateChangeMin = Utils.rateOf2Double(ticker.minPrice, ticker.priceOpen);
                Double rateEntry = 0D;
                Double rateEntryMin = 0D;
                Double rateEntryMax = 0d;
                if (i > 0) {
                    rateEntry = Utils.rateOf2Double(ticker.priceClose, priceEntry);
                    rateEntryMin = Utils.rateOf2Double(minPrice, priceEntry);
                    rateEntryMax = Utils.rateOf2Double(maxPrice, priceEntry);
                }
                if (i < 29
                        || timeCheck % (4 * Utils.TIME_HOUR) == 0
                        || timeCheck.equals(time2Tickers.lastKey())
                ) {
                    LOG.info("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}", Utils.normalizeDateYYYYMMDDHHmm(timeCheck),
                            Utils.formatDouble(rateChange * 100, 2),
                            Utils.formatDouble(rateChangeMax * 100, 2),
                            Utils.formatDouble(rateChangeMin * 100, 2),
                            Utils.formatDouble(rateEntryMax * 100, 2),
                            Utils.formatDouble(rateEntryMin * 100, 2),
                            Utils.formatDouble(rateEntry * 100, 2),
                            priceEntry, ticker.totalUsdt,
                            ticker.priceClose);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void getTopDown(String timeInput1, String timeInput2) {
        try {
            String timeInput = timeInput1.trim() + " " + timeInput2.trim();
            Long time = Utils.sdfFileHour.parse(timeInput).getTime();
            Long startTime = Utils.getDate(time - 15 * Utils.TIME_MINUTE);

            // data ticker
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManager.readDataFromFile1M(startTime);
            TreeMap<Long, Map<String, KlineObjectSimple>> dataNextDate = DataManager.readDataFromFile1M(startTime + Utils.TIME_DAY);
            TreeMap<Long, Map<String, KlineObjectSimple>> dataNext1Date = DataManager.readDataFromFile1M(startTime + 2 * Utils.TIME_DAY);
            if (dataNextDate != null) {
                time2Tickers.putAll(dataNextDate);
            }
            if (dataNext1Date != null) {
                time2Tickers.putAll(dataNext1Date);
            }
            Map<String, Double> symbol2MaxPrice = new HashMap<>();
            Map<String, Double> symbol2MinPrice = new HashMap<>();
            for (int i = 1; i < 16; i++) {
                Map<String, KlineObjectSimple> symbol2Ticker = time2Tickers.get(time - i * Utils.TIME_MINUTE);
                for (String symbol : symbol2Ticker.keySet()) {
                    KlineObjectSimple kline = symbol2Ticker.get(symbol);
                    Double priceMax = symbol2MaxPrice.get(symbol);
                    Double minPrice = symbol2MinPrice.get(symbol);
                    if (priceMax == null || priceMax < kline.maxPrice) {
                        priceMax = kline.maxPrice;
                    }
                    if (minPrice == null || minPrice > kline.minPrice) {
                        minPrice = kline.minPrice;
                    }
                    symbol2MaxPrice.put(symbol, priceMax);
                    symbol2MinPrice.put(symbol, minPrice);
                }
            }
            MarketDataObject marketData = MarketBigChangeDetectorTest.calMarketData(time2Tickers.get(time), symbol2MaxPrice,
                    symbol2MinPrice);
            List<String> symbols = MarketBigChangeDetectorTest.getTopSymbolSimple(marketData.rate2Max, 20, null);
            marketData.rate2Max.clear();
            LOG.info("{} {}", symbols, Utils.toJson(marketData));
            Map<String, Double> symbol2Volume24h = Volume24hrManager.getInstance().getVolume24h(time);
            for (String symbol : symbols) {
                LOG.info("{} {}M", symbol, Utils.formatDouble(symbol2Volume24h.get(symbol) / 1E6, 0));
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void getTopUp(String timeInput1, String timeInput2) {
        try {
            String timeInput = timeInput1.trim() + " " + timeInput2.trim();
            Long time = Utils.sdfFileHour.parse(timeInput).getTime();
            Long startTime = Utils.getDate(time);
            LOG.info("{} {} {}", time, startTime, Utils.normalizeDateYYYYMMDDHHmm(startTime));
            // data ticker
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManager.readDataFromFile1M(startTime);
            LOG.info("{}", MarketBigChangeDetectorTest.getTopUpSymbol2TradeSimple(time2Tickers.get(time), 4));
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void printRateChange1MofBTC() {
        List<KlineObjectNumber> btcTickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(
                Configs.FOLDER_TICKER_1M + Constants.SYMBOL_PAIR_BTC);
        List<String> lines = new ArrayList<>();
        lines.add("time, open, close, min, max, volume, rate");
        StringBuilder builder = new StringBuilder();
        for (KlineObjectNumber btcTicker : btcTickers) {
            builder.setLength(0);
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue())).append(",");
            builder.append(btcTicker.priceOpen).append(",");
            builder.append(btcTicker.priceClose).append(",");
            builder.append(btcTicker.minPrice).append(",");
            builder.append(btcTicker.maxPrice).append(",");
            builder.append(btcTicker.totalUsdt).append(",");
            builder.append(Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen));
            lines.add(builder.toString());
        }
        try {
            FileUtils.writeLines(new File("target/btc_1m_rate.csv"), lines);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void diffFileCsv() {
        try {
            String file1 = "target/printDone.csv";
            String file2 = "target/printDone_max.csv";
            List<String> lines1 = FileUtils.readLines(new File(file1));
            List<String> lines2 = FileUtils.readLines(new File(file2));
            Set<String> order1s = readAllOrderByLevel(lines1, "MINI_DOWN");
            Set<String> order2s = readAllOrderByLevel(lines2, "MINI_DOWN");
            for (String order : order1s) {
                if (!order2s.contains(order)) {
                    LOG.info("{} not in file2", order);
                }
            }
            for (String order : order2s) {
                if (!order1s.contains(order)) {
                    LOG.info("{} not in file1", order);
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static Set<String> readAllOrderByLevel(List<String> lines1, String levelFilter) {
        Set<String> hashSet = new HashSet<>();
        for (String line1 : lines1) {
            String[] parts = StringUtils.split(line1, ",");
            String level = parts[9];
            if (level.equals(levelFilter)) {
                hashSet.add(parts[0] + " " + parts[7]);
            }
        }
        return hashSet;
    }

    private static void traceDataStatistic(Long time) {
        Long duration = 48 * Utils.TIME_HOUR;
        Long numberTicker = duration / (15 * Utils.TIME_MINUTE);
        Long lastTime = time - 15 * Utils.TIME_MINUTE;
        try {
            Map<String, KlineObjectNumber> symbol2DataStatistic =
                    DataStatisticHelper.getInstance().readDataStatic_15m(time, numberTicker);
            TreeMap<Long, Map<String, KlineObjectNumber>> time2Tickers = DataManager.readData15mFromFile(Utils.getDate(time));
            TreeMap<Long, Map<String, KlineObjectNumber>> time2LastTickers = DataManager.readData15mFromFile(Utils.getDate(lastTime));
            Map<String, KlineObjectNumber> symbol2Ticker = time2Tickers.get(time);
            Map<String, KlineObjectNumber> symbol2LastTicker = time2LastTickers.get(lastTime);
            List<String> lines = new ArrayList<>();
            for (Map.Entry<String, KlineObjectNumber> entry : symbol2DataStatistic.entrySet()) {
                String symbol = entry.getKey();
                KlineObjectNumber tickerStatistic = entry.getValue();
                KlineObjectNumber lastTicker = symbol2LastTicker.get(symbol);
                KlineObjectNumber ticker = symbol2Ticker.get(symbol);
                StringBuilder builder = new StringBuilder();
                builder.append(symbol).append(",");
                builder.append(ticker.priceOpen).append(",");
                builder.append(ticker.priceClose).append(",");
                builder.append(ticker.maxPrice).append(",");
                builder.append(ticker.minPrice).append(",");
                builder.append(Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen)).append(",");
                builder.append(lastTicker.totalUsdt).append(",");
                builder.append(ticker.totalUsdt).append(",");
                builder.append(tickerStatistic.minPrice).append(",");
                builder.append(Utils.rateOf2Double(tickerStatistic.minPrice, ticker.priceClose)).append(",");
                builder.append(tickerStatistic.maxPrice);
                builder.append(Utils.rateOf2Double(tickerStatistic.maxPrice, ticker.priceClose)).append(",");
                lines.add(builder.toString());

            }
            String fileName = Utils.normalizeDateYYYYMMDDHHmm(time).replace(" ", "_");
            FileUtils.writeLines(new File("target/" + fileName.replace(":", "_") + ".csv"), lines);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

}
