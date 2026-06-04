package com.binance.chuyennd.bigchange.test;

import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetInfo;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.apache.commons.io.FileUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.util.*;

public class TraceOrderDone {
    public static final Logger LOG = LoggerFactory.getLogger(TraceOrderDone.class);

    public static String FILE_STORAGE_ORDER_DONE = "target/OrderTestDone.data";


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

    public static void printOrderTestDone(String fileName, TreeMap<Long, OrderTargetInfoTest> time2Order) throws
            IOException {



        List<String> lines = new ArrayList<>();
        lines.add("sym,side,entry,tp,profit,status,start,time_start_format,end,level,maxmin15m,lastentry,volume,quantity,margin," +
                "pnl,time_order,funding,dow,up,dow15m,pred15m,pred24h,risk4h,symbolPred");

        Map<String, Float> symbol2Profit = new HashMap<>();
        List<Float> pnls = new ArrayList<>();
        List<Float> pnlNotMays = new ArrayList<>();
        List<Float> pnlNot2021 = new ArrayList<>();
        List<Float> pnl2024 = new ArrayList<>();
        Map<Float, String> pnl2Info = new HashMap<>();
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

            if (order.predict != null) {
                builder.append(order.predict.predReturn15M).append(",");
                builder.append(order.predict.predReturn24H).append(",");
                builder.append(order.predict.predRisk4H).append(",");
                builder.append(order.symbolPred).append(",");
            }


            lines.add(builder.toString());
        }
        TreeMap<Float, String> profit2Symbol = new TreeMap<>();
        for (Map.Entry<String, Float> entry : symbol2Profit.entrySet()) {
            String key = entry.getKey();
            Float values = entry.getValue();
            profit2Symbol.put(values, key);
        }
        FileUtils.writeLines(new File(fileName), lines);
    }
}
