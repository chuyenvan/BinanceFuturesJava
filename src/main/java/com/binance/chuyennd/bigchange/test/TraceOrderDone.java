package com.binance.chuyennd.bigchange.test;

import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetInfo;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
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

    public static String FILE_STORAGE_ORDER_DONE = "target/OrderTestDone.data";
    //    public static String FILE_STORAGE_ORDER_DONE = "target/FundingStatisticResearch.data-5";
//    public static String FILE_STORAGE_ORDER_DONE = "target/OrderSELLDone.data";
//    public static String FILE_STORAGE_ORDER_DONE = "target/SellTicker1MStatisticResearch.data-5";
//    public static String FILE_STORAGE_ORDER_GRID_DONE = "storage/GridTestDone.data";


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
//        TreeMap<Long, OrderTargetInfoTest> time2Order =
//                (TreeMap<Long, OrderTargetInfoTest>) Storage.readObjectFromFile(FILE_STORAGE_ORDER_DONE);
//        printOrderTestDone(fileName, time2Order);
//        printOrderTestStatistic(fileName);
//        printOrderRunning("target/202502");
//        printOrderRunningAll("storage/data/unProfitMin/all-202102");

//        traceOrderGrid();
//        traceOrderGridAlt();
//        testGridSide();
        printOrderProduct();
    }

    private static void printOrderProduct() throws IOException {
        File folder = new File("target/order");
        TreeMap<Long, StringBuilder> time2OrderInfo = new TreeMap<>();
        for (File date : folder.listFiles()) {
            for (File order : date.listFiles()) {
                try {
                    LOG.info("Read file: {}", order.getAbsolutePath());
                    Map<Object, Object> data = (Map<Object, Object>) StorageSnappy.readObjectFromFile(order.getAbsolutePath());
                    KlineObjectSimple ticker = (KlineObjectSimple) data.get("ticker");
                    OrderTargetInfo orderTrade = (OrderTargetInfo) data.get("order");
                    MarketDataObject marketRate = (MarketDataObject) data.get("marketRate");
                    Float priceMax15M = (Float) data.get("max15M");
                    List<String> symbol2Sell = (List<String>) data.get("symbol2Sell");
                    Set<String> fundingBuy = (Set<String>) data.get("fundingBuy");
                    Set<String> fundingSell = (Set<String>) data.get("fundingSell");
                    time2OrderInfo.put(orderTrade.timeStart + time2OrderInfo.size(), buildOrderInfo(ticker, orderTrade, marketRate, priceMax15M,
                            symbol2Sell, fundingBuy, fundingSell));
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }
        StringBuilder header = new StringBuilder();
        List<String> lines = new ArrayList<>();
        header.append("symbol, side, entry, start, quantity, level, open, max15M, Down, Up, Down15M, Up15M, sell, fbuy, fsell");
        lines.add(header.toString());
        for (StringBuilder builder : time2OrderInfo.values()) {
            lines.add(builder.toString());
        }
        FileUtils.writeLines(new File("target/productOrder.csv"), lines);
    }

    private static StringBuilder buildOrderInfo(KlineObjectSimple ticker,
                                                OrderTargetInfo orderTrade, MarketDataObject marketRate,
                                                Float priceMax15M, List<String> symbol2Sell,
                                                Set<String> fundingBuy, Set<String> fundingSell) {
        StringBuilder builder = new StringBuilder();
        builder.append(orderTrade.symbol.replace("USDT", "")).append(",");
        builder.append(orderTrade.side).append(",");
        builder.append(orderTrade.priceEntry).append(",");
        builder.append(Utils.normalizeDateYYYYMMDDHHmm(orderTrade.timeStart)).append(",");
        builder.append(orderTrade.quantity).append(",");
        builder.append(orderTrade.marketLevel).append(",");
        builder.append(ticker.priceOpen).append(",");
        builder.append(priceMax15M).append(",");
        builder.append(marketRate.rateDownAvg).append(",");
        builder.append(marketRate.rateUpAvg).append(",");
        builder.append(marketRate.rateDown15MAvg).append(",");
        builder.append(Utils.toJson(symbol2Sell).replaceAll(",", " ").replaceAll("USDT", "")).append(",");
        builder.append(Utils.toJson(fundingBuy).replaceAll(",", " ").replaceAll("USDT", "")).append(",");
        builder.append(Utils.toJson(fundingSell).replaceAll(",", " ").replaceAll("USDT", "")).append(",");
        return builder;
    }

//    private static void testGridSide() {
//        ConcurrentHashMap<Long, GridObjectTestResearch> allGridDone = (ConcurrentHashMap<Long, GridObjectTestResearch>) Storage.readObjectFromFile(FILE_STORAGE_ORDER_GRID_DONE);
//        for (GridObjectTestResearch grid: allGridDone.values()){
//            gridLocal = GridDetector.findRange2RunTest()
//        }
//
//    }

    private static void traceOrderTestDone(String fileOut) throws IOException {

        ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone =
                (ConcurrentHashMap<String, OrderTargetInfoTest>) Storage.readObjectFromFile(FILE_STORAGE_ORDER_DONE);
        Map<Long, Float> date2Profit = new HashMap<>();
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
            Float profit = 0f;
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
                    Float profitOfDate = date2Profit.get(date);
                    if (profitOfDate == null) {
                        profitOfDate = 0f;
                    }
                    profitOfDate += order.calProfit();
                    date2Profit.put(date, profitOfDate);
                }
                totalOrder = orders.size();
                // statistic with ratechange
                Float rateChange;

                if (orders.get(0).marketLevelChange.equals(MarketLevelChange.BIG_DOWN)
                        || orders.get(0).marketLevelChange.equals(MarketLevelChange.MEDIUM_DOWN)
//                        || orders.get(0).marketLevelChange.equals(MarketLevelChange.SMALL_DOWN)
//                        || orders.get(0).marketLevelChange.equals(MarketLevelChange.SMALL_DOWN_EXTEND)
                ) {
                    // ratedown = 1, rateup = 2, ratebtc = 4
                    rateChange = Float.parseFloat(marketInfos[1]) * shardNumber;
//                    rateChange = orders.get(0).marketData.rateDownAvg * 100 * shardNumber;
//                } else {
//                    rateChange = Float.parseFloat(marketInfos[2]) * shardNumber;
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
        TreeMap<Float, Long> profit2Date = new TreeMap<>();
        for (Map.Entry<Long, Float> entry : date2Profit.entrySet()) {
            Long date = entry.getKey();
            Float profit = entry.getValue();
            profit2Date.put(profit, date);
        }
        int counter = 0;
        for (Float profit : profit2Date.keySet()) {
            LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(profit2Date.get(profit)), profit);
            counter++;
            if (counter > 10) {
                break;
            }
        }
        counter = 0;
        for (Float profit : profit2Date.descendingMap().keySet()) {
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
            Float rateLoss = 0f;
            Float rateSuccess = 0f;

            for (OrderTargetInfoTest order : orders) {
                if (order.priceTP > order.priceEntry) {
                    counterSuccess++;
                    rateSuccess += Utils.rateOf2Double(order.priceTP, order.priceEntry);
                } else {
                    rateLoss += Utils.rateOf2Double(order.priceTP, order.priceEntry);
                }
            }
            Float rateAvg = (rateLoss + rateSuccess) / orders.size();
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

    public static void printOrderTestDone(String fileName, TreeMap<Long, OrderTargetInfoTest> time2Order) throws
            IOException {



        List<String> lines = new ArrayList<>();
        lines.add("sym,side,entry,tp,profit,status,start,time_start_format,end,level,maxmin15m,lastentry,volume,quantity,margin," +
                "pnl,time_order,funding,dow,up,dow15m,predictedMaxDrawdown,predictedMaxRise,probPump20Pct,probDump30Pct");
//                "pnl,time_order,funding,dow,up,dow15m,return15M,return1H,return4H,return24H,predRisk4H, predRisk24H");
//        List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(DataManager.FOLDER_TICKER_15M + Constants.SYMBOL_PAIR_BTC);
        Map<Long, KlineObjectNumber> time2Ticker = new HashMap<>();
        Map<Long, Integer> time2Index = new HashMap<>();
//        for (int i = 0; i < tickers.size(); i++) {
//            KlineObjectNumber ticker = tickers.get(i);
//            time2Ticker.put(ticker.startTime.longValue(), ticker);
//            time2Index.put(ticker.startTime.longValue(), i);
//        }
        Map<String, Float> symbol2Profit = new HashMap<>();
        List<Float> pnls = new ArrayList<>();
        List<Float> pnlNotMays = new ArrayList<>();
        List<Float> pnlNot2021 = new ArrayList<>();
        List<Float> pnl2024 = new ArrayList<>();
        Map<Float, String> pnl2Info = new HashMap<>();
//        Float rateTrend = 0.01;
//        Integer duration = 360;
//        String fileNameBtcReverse = "../storage/btc/btcReverse-" + rateTrend + "-" + duration;
//
//        TreeMap<Long, Float> timeBtcReverse = null;
//
//        if (new File(fileNameBtcReverse).exists()) {
//            timeBtcReverse = (TreeMap<Long, Float>) Storage.readObjectFromFile(fileNameBtcReverse);
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
            Float profitOfSymbol = symbol2Profit.get(order.symbol);
            if (profitOfSymbol == null) {
                profitOfSymbol = 0f;
            }
            Float profit = Utils.rateOf2Double(order.priceTP, order.priceEntry);
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
            }

            lines.add(builder.toString());
        }
        TreeMap<Float, String> profit2Symbol = new TreeMap<>();
        for (Map.Entry<String, Float> entry : symbol2Profit.entrySet()) {
            String key = entry.getKey();
            Float values = entry.getValue();
            profit2Symbol.put(values, key);
        }
//        for (Map.Entry<Float, String> entry : profit2Symbol.entrySet()) {
//            String key = entry.getValue();
//            Float values = entry.getKey();
//            LOG.info("{} {}", values, key);
//        }

//        LOG.info("\n PnlMin: {} {} \n PnlMinNot20210519:{} {} \n PnlMinNot2021: {} {} \n pnlMin2024: {} {}",
//                Utils.findMinSubarraySum(pnls.toArray(new Float[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnls.toArray(new Float[0]))),
//                Utils.findMinSubarraySum(pnlNotMays.toArray(new Float[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnlNotMays.toArray(new Float[0]))),
//                Utils.findMinSubarraySum(pnlNot2021.toArray(new Float[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnlNot2021.toArray(new Float[0]))),
//                Utils.findMinSubarraySum(pnl2024.toArray(new Float[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnl2024.toArray(new Float[0]))));
        FileUtils.writeLines(new File(fileName), lines);
    }

    public static void printOrderRunningNew(TreeMap<Long, OrderTargetInfoTest> time2Order) throws IOException {
        List<String> lines = new ArrayList<>();
        lines.add("sym,side,entry,tp,min,rate,max,rate,profit,status,start,time, end,level,rate60m,rate ticker,volume,quantity,margin,pnl,time,funding,dow,up,dow15m,up15m,btcrate,btcdown15m,btcup15m");
        Map<Long, KlineObjectNumber> time2Ticker = new HashMap<>();
        Map<Long, Integer> time2Index = new HashMap<>();
        Map<String, Float> symbol2Profit = new HashMap<>();
        List<Float> pnls = new ArrayList<>();
        List<Float> pnlNotMays = new ArrayList<>();
        List<Float> pnlNot2021 = new ArrayList<>();
        List<Float> pnl2024 = new ArrayList<>();
        Map<Float, String> pnl2Info = new HashMap<>();
//        Float rateTrend = 0.01;
//        Integer duration = 360;
//        String fileNameBtcReverse = "../storage/btc/btcReverse-" + rateTrend + "-" + duration;
//
//        TreeMap<Long, Float> timeBtcReverse = null;
//
//        if (new File(fileNameBtcReverse).exists()) {
//            timeBtcReverse = (TreeMap<Long, Float>) Storage.readObjectFromFile(fileNameBtcReverse);
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
            Float profitOfSymbol = symbol2Profit.get(order.symbol);
            if (profitOfSymbol == null) {
                profitOfSymbol = 0f;
            }
            Float profit = Utils.rateOf2Double(order.priceTP, order.priceEntry);
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
            if (order.marketData != null) {
                builder.append(order.marketData.rateDownAvg).append(",");
                builder.append(order.marketData.rateUpAvg).append(",");
                builder.append(order.marketData.rateDown15MAvg).append(",");
            }
//            builder.append(timeBtcReverse.get(order.timeStart)).append(",");
            lines.add(builder.toString());
        }
        TreeMap<Float, String> profit2Symbol = new TreeMap<>();
        for (Map.Entry<String, Float> entry : symbol2Profit.entrySet()) {
            String key = entry.getKey();
            Float values = entry.getValue();
            profit2Symbol.put(values, key);
        }
//        for (Map.Entry<Float, String> entry : profit2Symbol.entrySet()) {
//            String key = entry.getValue();
//            Float values = entry.getKey();
//            LOG.info("{} {}", values, key);
//        }

//        LOG.info("\n PnlMin: {} {} \n PnlMinNot20210519:{} {} \n PnlMinNot2021: {} {} \n pnlMin2024: {} {}",
//                Utils.findMinSubarraySum(pnls.toArray(new Float[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnls.toArray(new Float[0]))),
//                Utils.findMinSubarraySum(pnlNotMays.toArray(new Float[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnlNotMays.toArray(new Float[0]))),
//                Utils.findMinSubarraySum(pnlNot2021.toArray(new Float[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnlNot2021.toArray(new Float[0]))),
//                Utils.findMinSubarraySum(pnl2024.toArray(new Float[0])), pnl2Info.get(Utils.findMinSubarraySumIndex(pnl2024.toArray(new Float[0]))));
//        FileUtils.writeLines(new File("storage/" + SellTicker1MStatisticResearch.class.getSimpleName() + ".csv"), lines);
    }

    public static void printOrderRunning(String fileInput) throws IOException {
        ConcurrentHashMap<String, List<OrderTargetInfoTest>> allOrderDone =
                (ConcurrentHashMap<String, List<OrderTargetInfoTest>>) Storage.readObjectFromFile(fileInput);

        TreeMap<Long, OrderTargetInfoTest> time2Order = new TreeMap<>();
        List<String> lines = new ArrayList<>();
        lines.add("sym,side,entry,tp,tp rate,status,start,time, end,level,rate ticker,quantity,margin,mreal, pnl,time");
        int counter = 0;
        for (List<OrderTargetInfoTest> orders : allOrderDone.values()) {
            for (OrderTargetInfoTest order : orders) {
                order.priceTP = order.minPrice;

                Float profit = Utils.rateOf2Double(order.priceTP, order.priceEntry);
                if (order.side.equals(OrderSide.SELL)) {
                    profit = -Utils.rateOf2Double(order.priceTP, order.priceEntry);
                }
                StringBuilder builder = new StringBuilder();
                builder.append(order.symbol.replace("USDT", "")).append(",");
                builder.append(order.side).append(",");
                builder.append(order.priceEntry).append(",");
                builder.append(order.priceTP).append(",");
//                builder.append(order.minPrice).append(",");
//                builder.append(Utils.rateOf2Double(order.minPrice, order.priceEntry)).append(",");
//                builder.append(order.maxPrice).append(",");
//                builder.append(Utils.rateOf2Double(order.maxPrice, order.priceEntry)).append(",");
                builder.append(profit * 100).append(",");
                builder.append(order.status.toString()).append(",");
                builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)).append(",'");
                builder.append(Utils.sdfGoogle.format(new Date(order.timeStart))).append(",");
                builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate)).append(",");
                builder.append(order.marketLevelChange).append(",");
                builder.append(Utils.rateOf2Double(order.tickerOpen.priceClose, order.tickerOpen.priceOpen)).append(",");
                builder.append(order.quantity).append(",");

                builder.append(order.calMargin() - order.calTp()).append(",");
                builder.append(order.calMargin()).append(",");
                builder.append(order.calTp()).append(",");
                builder.append((order.timeUpdate - order.timeStart) / Utils.TIME_MINUTE).append(",");
                if (order.marketData != null) {
                    builder.append(order.marketData.rateDownAvg).append(",");
                    builder.append(order.marketData.rateUpAvg).append(",");
                    builder.append(order.marketData.rateDown15MAvg).append(",");
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
            Float profit = Utils.rateOf2Double(order.priceTP, order.priceEntry);
            if (order.side.equals(OrderSide.SELL)) {
                profit = -Utils.rateOf2Double(order.priceTP, order.priceEntry);
            }
            StringBuilder builder = new StringBuilder();
            builder.append(order.symbol.replace("USDT", "")).append(",");
            builder.append(order.priceEntry).append(",");
            builder.append(order.priceTP).append(",");
            builder.append(order.minPrice).append(",");
            builder.append(Utils.rateOf2Double(order.minPrice, order.priceEntry)).append(",");
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
        Map<String, Float> symbol2Profit = new HashMap<>();
        for (OrderTargetInfoTest order : time2Order.values()) {
            Float profitOfSymbol = symbol2Profit.get(order.symbol);
            if (profitOfSymbol == null) {
                profitOfSymbol = 0f;
            }
            profitOfSymbol += Utils.rateOf2Double(order.priceTP, order.priceEntry);
            Float profit = Utils.rateOf2Double(order.priceTP, order.priceEntry);
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
