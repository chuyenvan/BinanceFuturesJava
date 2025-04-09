package com.binance.chuyennd.bigchange.test;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.grid.GridObjectALTResearch;
import com.binance.chuyennd.grid.GridObjectTestResearch;
import com.binance.chuyennd.grid.SimpleMovingAverageDayManager;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.research.SellTicker1MStatisticResearch;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class TraceOrderDone {
    public static final Logger LOG = LoggerFactory.getLogger(TraceOrderDone.class);

//    public static String FILE_STORAGE_ORDER_DONE = "storage/OrderTestDone.data-5";
    //    public static String FILE_STORAGE_ORDER_DONE = "target/FundingStatisticResearch.data-5";
//    public static String FILE_STORAGE_ORDER_DONE = "target/OrderSELLDone.data";
    public static String FILE_STORAGE_ORDER_DONE = "target/SellTicker1MStatisticResearch.data-5";
    public static String FILE_STORAGE_ORDER_GRID_DONE = "storage/GridTestDone.data";


    public static void main(String[] args) throws IOException {
        boolean modeStatistic = false;
        String fileName = "target/printDone.csv";
        String fileOut = "target/market_level_full.csv";
        // for statistic all
        if (modeStatistic) {
            fileName = "target/printDoneStatistic.csv";
            fileOut = "target/market_level_statistic.csv";
            FILE_STORAGE_ORDER_DONE = "target/OrderStatisticDone.data";
        }

//        printOrderTestDone(fileName);
//        printOrderTestStatistic(fileName);
        printOrderRunning("target/202112");
//        printOrderRunningAll("storage/data/unProfitMin/all-202102");

//        traceOrderGrid();
//        traceOrderGridAlt();
//        testGridSide();
    }

//    private static void testGridSide() {
//        ConcurrentHashMap<Long, GridObjectTestResearch> allGridDone = (ConcurrentHashMap<Long, GridObjectTestResearch>) Storage.readObjectFromFile(FILE_STORAGE_ORDER_GRID_DONE);
//        for (GridObjectTestResearch grid: allGridDone.values()){
//            gridLocal = GridDetector.findRange2RunTest()
//        }
//
//    }

    private static void traceOrderGrid() throws IOException {
        ConcurrentHashMap<Long, GridObjectTestResearch> allGridDone = (ConcurrentHashMap<Long, GridObjectTestResearch>) Storage.readObjectFromFile(FILE_STORAGE_ORDER_GRID_DONE);
        Map<String, TreeMap<Long, GridObjectTestResearch>> symbol2Grids = new HashMap<>();
        List<String> lines = new ArrayList<>();
        lines.add("symbol, side,number start, time,timefull, end, min, max, pricestart, best price, close price, ratemax, ratemin, " +
                "orders, time_trade, profit, close desc");
        for (GridObjectTestResearch grid : allGridDone.values()) {
            TreeMap<Long, GridObjectTestResearch> grids = symbol2Grids.get(grid.symbol);
            if (grids == null) {
                grids = new TreeMap<>();
            }
            grids.put(grid.tickerStart.startTime.longValue() + grids.size(), grid);
            symbol2Grids.put(grid.symbol, grids);
        }
//        Map<Long, MarketDataObject> time2MarketData = (Map<Long, MarketDataObject>)
//                Storage.readObjectFromFile("storage/market_data/time2market.data");
        for (String symbol : symbol2Grids.keySet()) {
            TreeMap<Long, GridObjectTestResearch> grids = symbol2Grids.get(symbol);
            int counterSuccess = 0;
            int counterFlase = 0;
            Double totalProfit = 0d;
            for (GridObjectTestResearch grid : grids.values()) {
//                Double maDif = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, grid.tickerStart.startTime.longValue());
//                if (maDif != null && maDif > 0) {
//                    btcTrend = OrderSide.BUY;
//                } else {
//                    btcTrend = OrderSide.SELL;
//                }
//                try {
//                    if (grid.symbol.equals("ZRXUSDT") && Utils.sdfFileHour.parse("20210519 19:37").getTime() == grid.tickerStart.startTime.longValue()) {
//                        grid.exportFile();
//                    }
//
//                } catch (Exception e) {
//                    e.printStackTrace();
//                }
//                MarketDataObject marketData = time2MarketData.get(grid.tickerStart.startTime.longValue());
                StringBuilder sb = new StringBuilder();
                sb.append(symbol).append(",");
                sb.append(grid.side).append(",");
                sb.append(grid.numberOrderStart).append(",");
                sb.append(Utils.normalizeDateYYYYMMDDHHmm(grid.tickerStart.startTime.longValue())).append(",'");
                sb.append(Utils.sdfGoogle.format(new Date(grid.tickerStart.startTime.longValue()))).append(",");
                sb.append(Utils.normalizeDateYYYYMMDDHHmm(grid.endTime)).append(",");
                Double profit = grid.calProfit();
                sb.append(grid.minPrice).append(",");
                sb.append(grid.maxPrice).append(",");
                sb.append(grid.tickerStart.priceClose).append(",");
                sb.append(grid.bestPrice).append(",");
                sb.append(grid.closePrice).append(",");
                sb.append(Utils.rateOf2Double(grid.tickerStart.priceClose, grid.maxPrice)).append(",");
                sb.append(Utils.rateOf2Double(grid.tickerStart.priceClose, grid.minPrice)).append(",");
                sb.append(grid.time2OrderDone.size()).append(",");
                sb.append((grid.endTime - grid.tickerStart.startTime.longValue()) / Utils.TIME_MINUTE).append(",");
                sb.append(profit.longValue()).append(",");
                sb.append(grid.levelChange).append(",");
//                sb.append(SimpleMovingAverage4hManager.getInstance().getDifferenceMa10AndMa60(symbol, grid.tickerStart.startTime.longValue())).append(",");
//                sb.append(SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(symbol, grid.tickerStart.startTime.longValue())).append(",");
//                if (grid.datas != null) {
//                    for (Double data : grid.datas) {
//                        sb.append(data).append(",");
//                    }
//                }
//                if (marketData != null) {
//                    sb.append(marketData.rateDownAvg).append(",");
//                    sb.append(marketData.rateUpAvg).append(",");
//                    sb.append(marketData.rateDown15MAvg).append(",");
//                    sb.append(marketData.rateUp15MAvg).append(",");
//                    sb.append(marketData.rateBtc).append(",");
//                    sb.append(marketData.rateBtcDown15M).append(",");
//                    sb.append(marketData.rateBtcUp15M).append(",");
//                }
                sb.append(grid.closeDesc);
                lines.add(sb.toString());
                if (profit > 0) {
                    counterSuccess++;
                } else {
                    counterFlase++;
                }
                totalProfit += profit;
            }
//            for (OrderTargetInfoTest order : grids.lastEntry().getValue().time2OrderDone.values()) {
//                StringBuilder sb = new StringBuilder();
//                sb.append(symbol).append(",");
//                sb.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)).append(",");
//                sb.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeJoin)).append(",");
//                sb.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate)).append(",");
//                sb.append(order.side).append(",");
//                sb.append(order.priceEntry).append(",");
//                sb.append(order.priceTP).append(",");
//                sb.append(order.priceSL).append(",");
//                sb.append(order.quantity).append(",");
//                sb.append(order.status).append(",");
//                sb.append(order.calTp()).append(",");
//                lines.add(sb.toString());
//
//            }
            LOG.info("ResultAll: {} s {} f {} {} profit:{} avg:{} ", symbol, counterSuccess, counterFlase, grids.size(),
                    totalProfit, totalProfit / grids.size());
        }
        FileUtils.writeLines(new File("target/GridDone.csv"), lines);
    }


    private static void traceOrderGridAlt() throws IOException {
        ConcurrentHashMap<Long, GridObjectALTResearch> allGridDone = (ConcurrentHashMap<Long, GridObjectALTResearch>) Storage.readObjectFromFile(FILE_STORAGE_ORDER_GRID_DONE);
        Map<String, TreeMap<Long, GridObjectALTResearch>> symbol2Grids = new HashMap<>();
        List<String> lines = new ArrayList<>();
        lines.add("symbol, side,number start, time,timefull, end, min, max, pricestart, best price, close price, ratemax, ratemin, " +
                "orders, time_trade, profit,btctrend, close desc");
        for (GridObjectALTResearch grid : allGridDone.values()) {
            TreeMap<Long, GridObjectALTResearch> grids = symbol2Grids.get(grid.symbol);
            if (grids == null) {
                grids = new TreeMap<>();
            }
            grids.put(grid.tickerStart.startTime.longValue(), grid);
            symbol2Grids.put(grid.symbol, grids);
        }
//        Map<Long, MarketDataObject> time2MarketData = (Map<Long, MarketDataObject>)
//                Storage.readObjectFromFile("storage/market_data/time2market.data");
        for (String symbol : symbol2Grids.keySet()) {
            TreeMap<Long, GridObjectALTResearch> grids = symbol2Grids.get(symbol);
            int counterSuccess = 0;
            int counterFlase = 0;
            OrderSide btcTrend = OrderSide.BUY;
            Double totalProfit = 0d;
            for (GridObjectALTResearch grid : grids.values()) {
                Double maDif = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, grid.tickerStart.startTime.longValue());
                if (maDif != null && maDif > 0) {
                    btcTrend = OrderSide.BUY;
                } else {
                    btcTrend = OrderSide.SELL;
                }
//                MarketDataObject marketData = time2MarketData.get(grid.tickerStart.startTime.longValue());
                StringBuilder sb = new StringBuilder();
                sb.append(symbol).append(",");
                sb.append(grid.side).append(",");
                sb.append(grid.numberOrderStart).append(",");
                sb.append(Utils.normalizeDateYYYYMMDDHHmm(grid.tickerStart.startTime.longValue())).append(",'");
                sb.append(Utils.sdfGoogle.format(new Date(grid.tickerStart.startTime.longValue()))).append(",");
                sb.append(Utils.normalizeDateYYYYMMDDHHmm(grid.endTime)).append(",");
                Double profit = grid.calProfit();
                sb.append(grid.minPrice).append(",");
                sb.append(grid.maxPrice).append(",");
                sb.append(grid.tickerStart.priceClose).append(",");
                sb.append(grid.bestPrice).append(",");
                sb.append(grid.closePrice).append(",");
                sb.append(Utils.rateOf2Double(grid.tickerStart.priceClose, grid.maxPrice)).append(",");
                sb.append(Utils.rateOf2Double(grid.tickerStart.priceClose, grid.minPrice)).append(",");
                sb.append(grid.time2OrderDone.size()).append(",");
                sb.append((grid.endTime - grid.tickerStart.startTime.longValue()) / Utils.TIME_MINUTE).append(",");
                sb.append(profit.longValue()).append(",");
                sb.append(btcTrend).append(",");
                sb.append(grid.levelChange).append(",");
//                if (grid.datas != null) {
//                    for (Double data : grid.datas) {
//                        sb.append(data).append(",");
//                    }
//                }
//                if (marketData != null) {
//                    sb.append(marketData.rateDownAvg).append(",");
//                    sb.append(marketData.rateUpAvg).append(",");
//                    sb.append(marketData.rateDown15MAvg).append(",");
//                    sb.append(marketData.rateUp15MAvg).append(",");
//                    sb.append(marketData.rateBtc).append(",");
//                    sb.append(marketData.rateBtcDown15M).append(",");
//                    sb.append(marketData.rateBtcUp15M).append(",");
//                }
                sb.append(grid.closeDesc);
                lines.add(sb.toString());
                if (profit > 0) {
                    counterSuccess++;
                } else {
                    counterFlase++;
                }
                totalProfit += profit;
            }
//            for (OrderTargetInfoTest order : grids.lastEntry().getValue().time2OrderDone.values()) {
//                StringBuilder sb = new StringBuilder();
//                sb.append(symbol).append(",");
//                sb.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)).append(",");
//                sb.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeJoin)).append(",");
//                sb.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate)).append(",");
//                sb.append(order.side).append(",");
//                sb.append(order.priceEntry).append(",");
//                sb.append(order.priceTP).append(",");
//                sb.append(order.priceSL).append(",");
//                sb.append(order.quantity).append(",");
//                sb.append(order.status).append(",");
//                sb.append(order.calTp()).append(",");
//                lines.add(sb.toString());
//
//            }
            LOG.info("ResultAll: {} s {} f {} {} profit:{} avg:{} ", symbol, counterSuccess, counterFlase, grids.size(),
                    totalProfit, totalProfit / grids.size());
        }
        FileUtils.writeLines(new File("target/GridDone.csv"), lines);
    }

    private static void printOrderTestStatistic(String fileName) {
        try {
            TreeMap<Long, OrderTargetInfoTest> time2Order =
                    (TreeMap<Long, OrderTargetInfoTest>) Storage.readObjectFromFile(FILE_STORAGE_ORDER_DONE);
            List<String> lines = new ArrayList<>();
            lines.add("sym,entry,tp,min,rate,max,rate,profit,status,start,time, end,rate ticker,volume,quantity,margin,tp");
            Map<Long, KlineObjectNumber> time2Ticker = new HashMap<>();
            Map<String, Double> symbol2Profit = new HashMap<>();

            for (OrderTargetInfoTest order : time2Order.values()) {
                if (!order.time2FundingFee.isEmpty()) {
                    LOG.info("{} {} {} {} {}", order.symbol, Utils.normalizeDateYYYYMMDDHHmm(order.timeStart), Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate),
                            order.calFundingFee(), Utils.toJson(order.time2FundingFee));
                }
                Double profitOfSymbol = symbol2Profit.get(order.symbol);
                if (profitOfSymbol == null) {
                    profitOfSymbol = 0d;
                }
                profitOfSymbol += Utils.rateOf2Double(order.priceTP, order.priceEntry);
                Double profit = Utils.rateOf2Double(order.priceTP, order.priceEntry);
                if (order.dynamicTP_SL != null) {
                    profit = profit * 3;
                }
                symbol2Profit.put(order.symbol, profitOfSymbol);
                StringBuilder builder = new StringBuilder();
                builder.append(order.symbol.replace("USDT", "")).append(",");
                builder.append(order.priceEntry).append(",");
                builder.append(order.priceTP).append(",");
                builder.append(order.minPrice).append(",");
                builder.append(Utils.rateOf2Double(order.minPrice, order.priceEntry)).append(",");
                builder.append(order.maxPrice).append(",");
                builder.append(Utils.rateOf2Double(order.maxPrice, order.priceEntry)).append(",");
                builder.append(profit * 100).append(",");
                builder.append(order.status.toString()).append(",");
                builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)).append(",'");
                builder.append(Utils.sdfGoogle.format(new Date(order.timeStart))).append(",");
                builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate)).append(",");
                builder.append(Utils.rateOf2Double(order.tickerOpen.priceClose, order.tickerOpen.priceOpen)).append(",");
                builder.append(order.tickerOpen.totalUsdt).append(",");
                builder.append(order.quantity).append(",");
                builder.append(order.dynamicTP_SL).append(",");
                builder.append(order.calMargin()).append(",");
                if (order.priceTP == null) {
                    order.priceTP = order.lastPrice;
                }
                builder.append(order.calTp()).append(",");
                if (order.datas != null) {
                    for (Object data : order.datas) {
                        builder.append(data).append(",");
                    }
                }
                lines.add(builder.toString());
            }

            FileUtils.writeLines(new File(fileName), lines);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void traceOrderTestDone(String fileOut) throws IOException {

        ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone =
                (ConcurrentHashMap<String, OrderTargetInfoTest>) Storage.readObjectFromFile(FILE_STORAGE_ORDER_DONE);
        Map<Long, Double> date2Profit = new HashMap<>();
        TreeMap<Long, List<OrderTargetInfoTest>> rateChange2Orders = new TreeMap<>();
        int shardNumber = 20;
        List<String> lines = FileUtils.readLines(new File("target/market_level_1m.csv"));
        lines.remove(0);
        TreeMap<Long, String[]> time2MarketInfo = new TreeMap<>();
        for (String line : lines) {
            try {
                String[] parts = StringUtils.split(line, ",");
                long time = Utils.sdfFileHour.parse(parts[0]).getTime();
                time2MarketInfo.put(time, parts);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        TreeMap<Long, List<OrderTargetInfoTest>> time2Orders = new TreeMap<>();

        for (OrderTargetInfoTest order : allOrderDone.values()) {
            List<OrderTargetInfoTest> orders = time2Orders.get(order.timeStart);
            if (orders == null) {
                orders = new ArrayList<>();
                time2Orders.put(order.timeUpdate, orders);
            }
            orders.add(order);
        }
        lines.clear();

        for (Long time : time2MarketInfo.keySet()) {
            List<OrderTargetInfoTest> orders = time2Orders.get(time);
            String[] marketInfos = time2MarketInfo.get(time);
            int counterSuccess = 0;
            Double profit = 0d;
            int totalOrder = 0;
            if (orders != null) {
//                if (orders.size() != 20){
//                    LOG.info("Order not enough 20: {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), orders.size());
//                }
                for (OrderTargetInfoTest order : orders) {
                    if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                        counterSuccess++;
                    }
                    profit += Utils.rateOf2Double(order.priceTP, order.priceEntry);
                    Long date = Utils.getDate(order.timeUpdate);
                    Double profitOfDate = date2Profit.get(date);
                    if (profitOfDate == null) {
                        profitOfDate = 0d;
                    }
                    profitOfDate += order.calProfit();
                    date2Profit.put(date, profitOfDate);
                }
                totalOrder = orders.size();
                // statistic with ratechange
                Double rateChange;

                if (orders.get(0).marketLevelChange.equals(MarketLevelChange.BIG_DOWN)
                        || orders.get(0).marketLevelChange.equals(MarketLevelChange.MEDIUM_DOWN)
//                        || orders.get(0).marketLevelChange.equals(MarketLevelChange.SMALL_DOWN)
//                        || orders.get(0).marketLevelChange.equals(MarketLevelChange.SMALL_DOWN_EXTEND)
                ) {
                    // ratedown = 1, rateup = 2, ratebtc = 4
                    rateChange = Double.parseDouble(marketInfos[1]) * shardNumber;
//                    rateChange = orders.get(0).marketData.rateDownAvg * 100 * shardNumber;
//                } else {
//                    rateChange = Double.parseDouble(marketInfos[2]) * shardNumber;
                    Long rateChangeL = rateChange.longValue();
                    List<OrderTargetInfoTest> ordersOfRate = rateChange2Orders.get(rateChangeL);
                    if (ordersOfRate == null) {
                        ordersOfRate = new ArrayList<>();
                        rateChange2Orders.put(rateChangeL, ordersOfRate);
                    }
                    ordersOfRate.addAll(orders);
                }
            }

            try {

                String line = "";
                for (int i = 0; i < 6; i++) {
                    line += marketInfos[i] + ",";
                }
                line += "'" + counterSuccess + "/" + totalOrder;
                line += "," + Utils.formatDouble(profit * 100 / totalOrder, 2);
                if (totalOrder != 0 && counterSuccess < 14) {
                    line += ",TRUE";
                } else {
                    line += ",FALSE";
                }
                for (int i = 6; i < marketInfos.length; i++) {
                    line += "," + marketInfos[i];
                }
                lines.add(line);

//                LOG.info("{} {} {}/{} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), orders.get(0).marketLevelChange, counterSuccess, orders.size()
//                        , marketInfos[1], marketInfos[2], marketInfos[4]);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }


        // print profit min
        TreeMap<Double, Long> profit2Date = new TreeMap<>();
        for (Map.Entry<Long, Double> entry : date2Profit.entrySet()) {
            Long date = entry.getKey();
            Double profit = entry.getValue();
            profit2Date.put(profit, date);
        }
        int counter = 0;
        for (Double profit : profit2Date.keySet()) {
            LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(profit2Date.get(profit)), profit);
            counter++;
            if (counter > 10) {
                break;
            }
        }
        counter = 0;
        for (Double profit : profit2Date.descendingMap().keySet()) {
            LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(profit2Date.descendingMap().get(profit)), profit);
            counter++;
            if (counter > 10) {
                break;
            }
        }
        List<String> lineOfRateSuccess = new ArrayList<>();
        lineOfRateSuccess.add("rate,tp,sl,total, loss, profit, rateLoss");
        for (Long rate : rateChange2Orders.keySet()) {
            List<OrderTargetInfoTest> orders = rateChange2Orders.get(rate);

            int counterSuccess = 0;
            Double rateLoss = 0d;
            Double rateSuccess = 0d;

            for (OrderTargetInfoTest order : orders) {
                if (order.priceTP > order.priceEntry) {
                    counterSuccess++;
                    rateSuccess += Utils.rateOf2Double(order.priceTP, order.priceEntry);
                } else {
                    rateLoss += Utils.rateOf2Double(order.priceTP, order.priceEntry);
                }
            }
            Double rateAvg = (rateLoss + rateSuccess) / orders.size();
            LOG.info("rateChange: {} {}/{} {}/{} {}%", rate.doubleValue() / shardNumber,
                    counterSuccess, orders.size(), Utils.formatDouble(rateLoss, 2),
                    Utils.formatDouble(rateSuccess, 2), Utils.formatPercent(rateAvg));
            StringBuilder builder = new StringBuilder();
            builder.append(rate.doubleValue() / shardNumber).append(",");
            builder.append(counterSuccess).append(",");
            builder.append(orders.size() - counterSuccess).append(",");
            builder.append(orders.size()).append(",");
            builder.append(Utils.formatDouble(rateLoss, 2)).append(",");
            builder.append(Utils.formatDouble(rateSuccess, 2)).append(",");
            builder.append(Utils.formatPercent(rateAvg)).append(",");
            lineOfRateSuccess.add(builder.toString());

        }
        FileUtils.writeLines(new File(fileOut), lines);
        FileUtils.writeLines(new File("target/rate2result.csv"), lineOfRateSuccess);
    }

    public static void printOrderTestDone(String fileName, TreeMap<Long, OrderTargetInfoTest> time2Order) throws IOException {

        List<String> lines = new ArrayList<>();
        lines.add("sym,side,entry,tp,min,rate,max,rate,profit,status,start,time, end,level,rate60m,rate ticker,volume,quantity,margin,pnl,time,funding,dow,up,dow15m,up15m,btcrate,btcdown15m,btcup15m");
//        List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(DataManager.FOLDER_TICKER_15M + Constants.SYMBOL_PAIR_BTC);
        Map<Long, KlineObjectNumber> time2Ticker = new HashMap<>();
        Map<Long, Integer> time2Index = new HashMap<>();
//        for (int i = 0; i < tickers.size(); i++) {
//            KlineObjectNumber ticker = tickers.get(i);
//            time2Ticker.put(ticker.startTime.longValue(), ticker);
//            time2Index.put(ticker.startTime.longValue(), i);
//        }
        Map<String, Double> symbol2Profit = new HashMap<>();
        List<Double> pnls = new ArrayList<>();
        List<Double> pnlNotMays = new ArrayList<>();
        List<Double> pnlNot2021 = new ArrayList<>();
        List<Double> pnl2024 = new ArrayList<>();
        Map<Double, String> pnl2Info = new HashMap<>();
//        Double rateTrend = 0.01;
//        Integer duration = 360;
//        String fileNameBtcReverse = "../storage/btc/btcReverse-" + rateTrend + "-" + duration;
//
//        TreeMap<Long, Double> timeBtcReverse = null;
//
//        if (new File(fileNameBtcReverse).exists()) {
//            timeBtcReverse = (TreeMap<Long, Double>) Storage.readObjectFromFile(fileNameBtcReverse);
//        }
        for (OrderTargetInfoTest order : time2Order.values()) {
//            if (!order.time2FundingFee.isEmpty()) {
//                LOG.info("{} {} {} {} {}", order.symbol, Utils.normalizeDateYYYYMMDDHHmm(order.timeStart), Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate),
//                        order.calFundingFee(), Utils.toJson(order.time2FundingFee));
//            }
            pnls.add(order.calTp());
            pnl2Info.put(order.calTp(), order.symbol + "-" + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart));
            if (!org.apache.commons.lang.StringUtils.equals(Utils.sdfFile.format(new Date(order.timeStart)), "20210519")) {
                pnlNotMays.add(order.calTp());
            }
            if (!org.apache.commons.lang.StringUtils.startsWith(Utils.sdfFile.format(new Date(order.timeStart)), "2021")) {
                pnlNot2021.add(order.calTp());
            }
            if (org.apache.commons.lang.StringUtils.startsWith(Utils.sdfFile.format(new Date(order.timeStart)), "2024")) {
                pnl2024.add(order.calTp());
            }
            long date = Utils.getDate(order.timeStart);
            KlineObjectNumber ticker = time2Ticker.get(order.timeStart);
//            if (StringUtils.equals(order.symbol, "GALAUSDT")) {
//                System.out.println("Debug");
//            }
            Double profitOfSymbol = symbol2Profit.get(order.symbol);
            if (profitOfSymbol == null) {
                profitOfSymbol = 0d;
            }
            Double profit = Utils.rateOf2Double(order.priceTP, order.priceEntry);
            if (order.side.equals(OrderSide.SELL)) {
                profit = -Utils.rateOf2Double(order.priceTP, order.priceEntry);
            }
            profitOfSymbol += profit;
            symbol2Profit.put(order.symbol, profitOfSymbol);
            StringBuilder builder = new StringBuilder();
            builder.append(order.symbol.replace("USDT", "")).append(",");
            builder.append(order.side).append(",");
            builder.append(order.priceEntry).append(",");
            builder.append(order.priceTP).append(",");
            builder.append(order.minPrice).append(",");
            builder.append(Utils.rateOf2Double(order.minPrice, order.priceEntry)).append(",");
            builder.append(order.maxPrice).append(",");
            builder.append(Utils.rateOf2Double(order.maxPrice, order.priceEntry)).append(",");
            builder.append(profit * 100).append(",");
            builder.append(order.status.toString()).append(",");
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)).append(",'");
            builder.append(Utils.sdfGoogle.format(new Date(order.timeStart))).append(",");
//            if (order.timeJoin == null){
//                order.timeJoin = order.timeStart;
//            }
//            builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeJoin)).append(",'");
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate)).append(",");
            builder.append(order.marketLevelChange).append(",");
            builder.append(order.rateChange).append(",");
            builder.append(order.lastEntry).append(",");
//            builder.append(Utils.rateOf2Double(order.tickerOpen.priceClose, order.tickerOpen.priceOpen)).append(",");
            builder.append(order.tickerOpen.totalUsdt).append(",");
            builder.append(order.quantity).append(",");
            builder.append(order.calMargin()).append(",");
            builder.append(order.calTp()).append(",");
            builder.append((order.timeUpdate - order.timeStart) / Utils.TIME_HOUR).append(",");
            builder.append((order.calFundingFee())).append(",");
            if (order.marketData != null) {
                builder.append(order.marketData.rateDownAvg).append(",");
                builder.append(order.marketData.rateUpAvg).append(",");
                builder.append(order.marketData.rateDown15MAvg).append(",");
                builder.append(order.marketData.rateUp15MAvg).append(",");
                builder.append(order.marketData.rateBtc).append(",");
                builder.append(order.marketData.rateBtcDown15M).append(",");
                builder.append(order.marketData.rateBtcUp15M).append(",");
            }
//            builder.append(timeBtcReverse.get(order.timeStart)).append(",");
            if (order.datas != null) {
                for (Object data : order.datas) {
                    builder.append(data).append(",");
                }
            }
            lines.add(builder.toString());
        }
        TreeMap<Double, String> profit2Symbol = new TreeMap<>();
        for (Map.Entry<String, Double> entry : symbol2Profit.entrySet()) {
            String key = entry.getKey();
            Double values = entry.getValue();
            profit2Symbol.put(values, key);
        }
//        for (Map.Entry<Double, String> entry : profit2Symbol.entrySet()) {
//            String key = entry.getValue();
//            Double values = entry.getKey();
//            LOG.info("{} {}", values, key);
//        }

//        LOG.info("\n PnlMin: {} {} \n PnlMinNot20210519:{} {} \n PnlMinNot2021: {} {} \n pnlMin2024: {} {}",
//                Utils.findMinSubarraySum(pnls.toArray(new Double[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnls.toArray(new Double[0]))),
//                Utils.findMinSubarraySum(pnlNotMays.toArray(new Double[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnlNotMays.toArray(new Double[0]))),
//                Utils.findMinSubarraySum(pnlNot2021.toArray(new Double[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnlNot2021.toArray(new Double[0]))),
//                Utils.findMinSubarraySum(pnl2024.toArray(new Double[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnl2024.toArray(new Double[0]))));
        FileUtils.writeLines(new File(fileName), lines);
    }
    public static void printOrderRunningNew(TreeMap<Long, OrderTargetInfoTest> time2Order) throws IOException {
        List<String> lines = new ArrayList<>();
        lines.add("sym,side,entry,tp,min,rate,max,rate,profit,status,start,time, end,level,rate60m,rate ticker,volume,quantity,margin,pnl,time,funding,dow,up,dow15m,up15m,btcrate,btcdown15m,btcup15m");
        Map<Long, KlineObjectNumber> time2Ticker = new HashMap<>();
        Map<Long, Integer> time2Index = new HashMap<>();
        Map<String, Double> symbol2Profit = new HashMap<>();
        List<Double> pnls = new ArrayList<>();
        List<Double> pnlNotMays = new ArrayList<>();
        List<Double> pnlNot2021 = new ArrayList<>();
        List<Double> pnl2024 = new ArrayList<>();
        Map<Double, String> pnl2Info = new HashMap<>();
//        Double rateTrend = 0.01;
//        Integer duration = 360;
//        String fileNameBtcReverse = "../storage/btc/btcReverse-" + rateTrend + "-" + duration;
//
//        TreeMap<Long, Double> timeBtcReverse = null;
//
//        if (new File(fileNameBtcReverse).exists()) {
//            timeBtcReverse = (TreeMap<Long, Double>) Storage.readObjectFromFile(fileNameBtcReverse);
//        }
        for (OrderTargetInfoTest order : time2Order.values()) {
//            if (!order.time2FundingFee.isEmpty()) {
//                LOG.info("{} {} {} {} {}", order.symbol, Utils.normalizeDateYYYYMMDDHHmm(order.timeStart), Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate),
//                        order.calFundingFee(), Utils.toJson(order.time2FundingFee));
//            }
            pnls.add(order.calTp());
            pnl2Info.put(order.calTp(), order.symbol + "-" + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart));
            if (!org.apache.commons.lang.StringUtils.equals(Utils.sdfFile.format(new Date(order.timeStart)), "20210519")) {
                pnlNotMays.add(order.calTp());
            }
            if (!org.apache.commons.lang.StringUtils.startsWith(Utils.sdfFile.format(new Date(order.timeStart)), "2021")) {
                pnlNot2021.add(order.calTp());
            }
            if (org.apache.commons.lang.StringUtils.startsWith(Utils.sdfFile.format(new Date(order.timeStart)), "2024")) {
                pnl2024.add(order.calTp());
            }
            long date = Utils.getDate(order.timeStart);
            KlineObjectNumber ticker = time2Ticker.get(order.timeStart);
//            if (StringUtils.equals(order.symbol, "GALAUSDT")) {
//                System.out.println("Debug");
//            }
            Double profitOfSymbol = symbol2Profit.get(order.symbol);
            if (profitOfSymbol == null) {
                profitOfSymbol = 0d;
            }
            Double profit = Utils.rateOf2Double(order.priceTP, order.priceEntry);
            if (order.side.equals(OrderSide.SELL)) {
                profit = -Utils.rateOf2Double(order.priceTP, order.priceEntry);
            }
            profitOfSymbol += profit;
            symbol2Profit.put(order.symbol, profitOfSymbol);
            StringBuilder builder = new StringBuilder();
            builder.append(order.symbol.replace("USDT", "")).append(",");
            builder.append(order.side).append(",");
            builder.append(order.priceEntry).append(",");
            builder.append(order.priceTP).append(",");
            builder.append(order.minPrice).append(",");
            builder.append(Utils.rateOf2Double(order.minPrice, order.priceEntry)).append(",");
            builder.append(order.maxPrice).append(",");
            builder.append(Utils.rateOf2Double(order.maxPrice, order.priceEntry)).append(",");
            builder.append(profit * 100).append(",");
            builder.append(order.status.toString()).append(",");
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)).append(",'");
            builder.append(Utils.sdfGoogle.format(new Date(order.timeStart))).append(",");
//            if (order.timeJoin == null){
//                order.timeJoin = order.timeStart;
//            }
//            builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeJoin)).append(",'");
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate)).append(",");
            builder.append(order.marketLevelChange).append(",");
            builder.append(order.rateChange).append(",");
            builder.append(order.lastEntry).append(",");
//            builder.append(Utils.rateOf2Double(order.tickerOpen.priceClose, order.tickerOpen.priceOpen)).append(",");
            builder.append(order.tickerOpen.totalUsdt).append(",");
            builder.append(order.quantity).append(",");
            builder.append(order.calMargin()).append(",");
            builder.append(order.calTp()).append(",");
            builder.append((order.timeUpdate - order.timeStart) / Utils.TIME_HOUR).append(",");
            builder.append((order.calFundingFee())).append(",");
            if (order.marketData != null) {
                builder.append(order.marketData.rateDownAvg).append(",");
                builder.append(order.marketData.rateUpAvg).append(",");
                builder.append(order.marketData.rateDown15MAvg).append(",");
                builder.append(order.marketData.rateUp15MAvg).append(",");
                builder.append(order.marketData.rateBtc).append(",");
                builder.append(order.marketData.rateBtcDown15M).append(",");
                builder.append(order.marketData.rateBtcUp15M).append(",");
            }
//            builder.append(timeBtcReverse.get(order.timeStart)).append(",");
            if (order.datas != null) {
                for (Object data : order.datas) {
                    builder.append(data).append(",");
                }
            }
            lines.add(builder.toString());
        }
        TreeMap<Double, String> profit2Symbol = new TreeMap<>();
        for (Map.Entry<String, Double> entry : symbol2Profit.entrySet()) {
            String key = entry.getKey();
            Double values = entry.getValue();
            profit2Symbol.put(values, key);
        }
//        for (Map.Entry<Double, String> entry : profit2Symbol.entrySet()) {
//            String key = entry.getValue();
//            Double values = entry.getKey();
//            LOG.info("{} {}", values, key);
//        }

//        LOG.info("\n PnlMin: {} {} \n PnlMinNot20210519:{} {} \n PnlMinNot2021: {} {} \n pnlMin2024: {} {}",
//                Utils.findMinSubarraySum(pnls.toArray(new Double[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnls.toArray(new Double[0]))),
//                Utils.findMinSubarraySum(pnlNotMays.toArray(new Double[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnlNotMays.toArray(new Double[0]))),
//                Utils.findMinSubarraySum(pnlNot2021.toArray(new Double[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnlNot2021.toArray(new Double[0]))),
//                Utils.findMinSubarraySum(pnl2024.toArray(new Double[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnl2024.toArray(new Double[0]))));
        FileUtils.writeLines(new File("storage/" + SellTicker1MStatisticResearch.class.getSimpleName() + ".csv"), lines);
    }

    public static void printOrderRunning(String fileInput) throws IOException {
        ConcurrentHashMap<String, List<OrderTargetInfoTest>> allOrderDone =
                (ConcurrentHashMap<String, List<OrderTargetInfoTest>>) Storage.readObjectFromFile(fileInput);

        TreeMap<Long, OrderTargetInfoTest> time2Order = new TreeMap<>();
        List<String> lines = new ArrayList<>();
        lines.add("sym,entry,tp,min,rate,max,rate,profit,status,start,time, end,level,rate ticker,volume,quantity,orders,unP, SLTotal, marginTotal,margin,pnl,time,leverage");
        int counter = 0;
        for (List<OrderTargetInfoTest> orders : allOrderDone.values()) {
            for (OrderTargetInfoTest order : orders) {
                if (order.side.equals(OrderSide.BUY)) {
                    order.priceTP = order.minPrice;
                } else {
                    order.priceTP = order.maxPrice;
                }
                Double profit = Utils.rateOf2Double(order.priceTP, order.priceEntry);
                if (order.side.equals(OrderSide.SELL)) {
                    profit = -Utils.rateOf2Double(order.priceTP, order.priceEntry);
                }
                StringBuilder builder = new StringBuilder();
                builder.append(order.symbol.replace("USDT", "")).append(",");
                builder.append(order.priceEntry).append(",");
                builder.append(order.priceTP).append(",");
                builder.append(order.minPrice).append(",");
                builder.append(Utils.rateOf2Double(order.minPrice, order.priceEntry)).append(",");
                builder.append(order.maxPrice).append(",");
                builder.append(Utils.rateOf2Double(order.maxPrice, order.priceEntry)).append(",");
                builder.append(profit * 100).append(",");
                builder.append(order.status.toString()).append(",");
                builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)).append(",'");
                builder.append(Utils.sdfGoogle.format(new Date(order.timeStart))).append(",");
                builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate)).append(",");
                builder.append(order.marketLevelChange).append(",");
                builder.append(Utils.rateOf2Double(order.tickerOpen.priceClose, order.tickerOpen.priceOpen)).append(",");
                builder.append(order.tickerOpen.totalUsdt).append(",");
                builder.append(order.quantity).append(",");
                builder.append(order.ordersRunning).append(",");
                builder.append(order.unProfitTotal.longValue()).append(",");
                builder.append(order.slTotal.longValue()).append(",");
                builder.append(order.marginRunning.longValue()).append(",");
                builder.append(order.calMargin()).append(",");
                builder.append(order.calTp()).append(",");
                builder.append((order.timeUpdate - order.timeStart) / Utils.TIME_MINUTE).append(",");
                builder.append(order.leverage).append(",");
                if (order.marketData != null) {
                    builder.append(order.marketData.rateDownAvg).append(",");
                    builder.append(order.marketData.rateUpAvg).append(",");
                    builder.append(order.marketData.rateDown15MAvg).append(",");
                    builder.append(order.marketData.rateUp15MAvg).append(",");
                    builder.append(order.marketData.rateBtc).append(",");
                    builder.append(order.marketData.rateBtcDown15M).append(",");
                    builder.append(order.marketData.rateBtcUp15M).append(",");
                }
                lines.add(builder.toString());
            }
        }

        FileUtils.writeLines(new File("target/order_running.csv"), lines);
    }

    public static void printOrderRunningAll(String fileInput) throws IOException {
        ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone =
                (ConcurrentHashMap<String, OrderTargetInfoTest>) Storage.readObjectFromFile(fileInput);

        TreeMap<Long, OrderTargetInfoTest> time2Order = new TreeMap<>();
        List<String> lines = new ArrayList<>();
        lines.add("sym,entry,tp,min,rate,max,rate,profit,status,start,time, end,level,rate ticker,volume,quantity,margin,pnl,time,leverage");
        int counter = 0;
        for (OrderTargetInfoTest order : allOrderDone.values()) {
            order.priceTP = order.minPrice;
            Double profit = Utils.rateOf2Double(order.priceTP, order.priceEntry);
            if (order.side.equals(OrderSide.SELL)) {
                profit = -Utils.rateOf2Double(order.priceTP, order.priceEntry);
            }
            StringBuilder builder = new StringBuilder();
            builder.append(order.symbol.replace("USDT", "")).append(",");
            builder.append(order.priceEntry).append(",");
            builder.append(order.priceTP).append(",");
            builder.append(order.minPrice).append(",");
            builder.append(Utils.rateOf2Double(order.minPrice, order.priceEntry)).append(",");
            builder.append(order.maxPrice).append(",");
            builder.append(Utils.rateOf2Double(order.maxPrice, order.priceEntry)).append(",");
            builder.append(profit * 100).append(",");
            builder.append(order.status.toString()).append(",");
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)).append(",'");
            builder.append(Utils.sdfGoogle.format(new Date(order.timeStart))).append(",");
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate)).append(",");
            builder.append(order.marketLevelChange).append(",");
            builder.append(Utils.rateOf2Double(order.tickerOpen.priceClose, order.tickerOpen.priceOpen)).append(",");
            builder.append(order.tickerOpen.totalUsdt).append(",");
            builder.append(order.quantity).append(",");
            builder.append(order.calMargin()).append(",");
            builder.append(order.calTp()).append(",");
            builder.append((order.timeUpdate - order.timeStart) / Utils.TIME_MINUTE).append(",");
            builder.append(order.leverage).append(",");
            if (order.marketData != null) {
                builder.append(order.marketData.rateDownAvg).append(",");
                builder.append(order.marketData.rateUpAvg).append(",");
                builder.append(order.marketData.rateDown15MAvg).append(",");
                builder.append(order.marketData.rateUp15MAvg).append(",");
                builder.append(order.marketData.rateBtc).append(",");
                builder.append(order.marketData.rateBtcDown15M).append(",");
                builder.append(order.marketData.rateBtcUp15M).append(",");
            }
            lines.add(builder.toString());
        }


        FileUtils.writeLines(new File("target/order_running_all.csv"), lines);
    }


    public static void printOrderTestDone(String fileIn, String fileOut) throws IOException {
        ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone =
                (ConcurrentHashMap<String, OrderTargetInfoTest>) Storage.readObjectFromFile(fileIn);
        TreeMap<Long, OrderTargetInfoTest> time2Order = new TreeMap<>();
        int counter = 0;
        for (OrderTargetInfoTest order : allOrderDone.values()) {
            counter++;
            time2Order.put(-order.timeStart + counter, order);
        }
        List<String> lines = new ArrayList<>();
        lines.add("sym,side,entry,tp,sl,min,rate,max,rate,profit,status,start,end,rateBtc15M,rateTicker,rateBtc,volume,quantity,pnl,time");
        Map<String, Double> symbol2Profit = new HashMap<>();
        for (OrderTargetInfoTest order : time2Order.values()) {
            Double profitOfSymbol = symbol2Profit.get(order.symbol);
            if (profitOfSymbol == null) {
                profitOfSymbol = 0d;
            }
            profitOfSymbol += Utils.rateOf2Double(order.priceTP, order.priceEntry);
            Double profit = Utils.rateOf2Double(order.priceTP, order.priceEntry);
            if (order.side.equals(OrderSide.SELL)) {
                profit = -Utils.rateOf2Double(order.priceTP, order.priceEntry);
            }
            symbol2Profit.put(order.symbol, profitOfSymbol);
            StringBuilder builder = new StringBuilder();
            builder.append(order.symbol.replace("USDT", "")).append(",");
            builder.append(order.side).append(",");
            builder.append(order.priceEntry).append(",");
            builder.append(order.priceTP).append(",");
            builder.append(order.priceSL).append(",");
            builder.append(order.minPrice).append(",");
            builder.append(Utils.rateOf2Double(order.minPrice, order.priceEntry)).append(",");
            builder.append(order.maxPrice).append(",");
            builder.append(Utils.rateOf2Double(order.maxPrice, order.priceEntry)).append(",");
            builder.append(profit).append(",");
            builder.append(order.status.toString()).append(",");
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)).append(",'");
            builder.append(Utils.sdfGoogle.format(new Date(order.timeStart))).append(",");
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate)).append(",");
            builder.append(order.rateChange).append(",");
            builder.append(Utils.rateOf2Double(order.tickerOpen.priceClose, order.tickerOpen.priceOpen)).append(",");
//            builder.append(Utils.rateOf2Double(order.tickerClose.priceClose, order.tickerClose.priceOpen)).append(",");
            builder.append(order.tickerOpen.totalUsdt).append(",");
            builder.append(order.quantity).append(",");
            builder.append(order.calTp()).append(",");
            builder.append((order.timeUpdate - order.timeStart) / Utils.TIME_MINUTE).append(",");
            lines.add(builder.toString());
        }
        FileUtils.writeLines(new File(fileOut), lines);
    }


}
