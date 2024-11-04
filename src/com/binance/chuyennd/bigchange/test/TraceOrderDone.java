package com.binance.chuyennd.bigchange.test;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.research.BTCTrendManagerTest;
import com.binance.chuyennd.research.OrderTargetInfoTest;
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

    public static String FILE_STORAGE_ORDER_DONE = "target/OrderTestDone.data-16-0.04";
//    public static String FILE_STORAGE_ORDER_DONE = "target/OrderTestDone-ALT_REVERSE_EXTEND-16-0.04";
//    public static String FILE_STORAGE_ORDER_DONE = "target/OrderTestDone.data-20-0.04";
//    public static String FILE_STORAGE_ORDER_DONE = "target/OrderSpecialDone.data";
//    public static String FILE_STORAGE_ORDER_DONE = "target/AltBigChangeReverse.data";


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

        printOrderTestDone(fileName);
//        traceOrderTestDone(fileOut);

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

    public static void printOrderTestDone(String fileName) throws IOException {
        TreeMap<Long, OrderTargetInfoTest> time2Order =
                (TreeMap<Long, OrderTargetInfoTest>) Storage.readObjectFromFile(FILE_STORAGE_ORDER_DONE);

        List<String> lines = new ArrayList<>();
        lines.add("sym,side,entry,tp,sl,min,rate,max,rate,profit,status,start,time, end,level, rate max 15m, rate ticker,volume,quantity,margin,pnl,time");
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

        for (OrderTargetInfoTest order : time2Order.values()) {
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
            builder.append(profit * 100).append(",");
            builder.append(order.status.toString()).append(",");
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)).append(",'");
            builder.append(Utils.sdfGoogle.format(new Date(order.timeStart))).append(",");
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate)).append(",");
//            builder.append(Utils.isEndWeek(order.timeStart)).append(",");

            builder.append(order.marketLevelChange).append(",");
            builder.append(order.rateChange).append(",");
            builder.append(Utils.rateOf2Double(order.tickerOpen.priceClose, order.tickerOpen.priceOpen)).append(",");
            builder.append(order.tickerOpen.totalUsdt).append(",");
            builder.append(order.quantity).append(",");
            builder.append(order.calMargin()).append(",");
            builder.append(order.calTp()).append(",");
            builder.append((order.timeUpdate - order.timeStart) / Utils.TIME_MINUTE).append(",");
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
        TreeMap<Double, String> profit2Symbol = new TreeMap<>();
        for (Map.Entry<String, Double> entry : symbol2Profit.entrySet()) {
            String key = entry.getKey();
            Double values = entry.getValue();
            profit2Symbol.put(values, key);
        }
        for (Map.Entry<Double, String> entry : profit2Symbol.entrySet()) {
            String key = entry.getValue();
            Double values = entry.getKey();
            LOG.info("{} {}", values, key);
        }

        LOG.info("\n PnlMin: {} {} \n PnlMinNot20210519:{} {} \n PnlMinNot2021: {} {} \n pnlMin2024: {} {}",
                Utils.findMinSubarraySum(pnls.toArray(new Double[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnls.toArray(new Double[0]))),
                Utils.findMinSubarraySum(pnlNotMays.toArray(new Double[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnlNotMays.toArray(new Double[0]))),
                Utils.findMinSubarraySum(pnlNot2021.toArray(new Double[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnlNot2021.toArray(new Double[0]))),
                Utils.findMinSubarraySum(pnl2024.toArray(new Double[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnl2024.toArray(new Double[0]))));
        FileUtils.writeLines(new File(fileName), lines);
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
