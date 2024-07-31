package com.binance.chuyennd.bigchange.test;

import com.binance.chuyennd.bigchange.statistic.BTCMacdTrendManager;
import com.binance.chuyennd.bigchange.statistic.BTCTicker15MManager;
import com.binance.chuyennd.mongo.TickerMongoHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TrendState;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.apache.commons.io.FileUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class TraceOrderDone {
    public static final Logger LOG = LoggerFactory.getLogger(TraceOrderDone.class);
    public static final String FILE_STORAGE_ORDER_DONE = "target/OrderTestDone.data";

    public static void main(String[] args) throws IOException {

        printOrderTestDone();
//        traceOrderTestDone();

    }

    private static void traceOrderTestDone() throws IOException {

        ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone =
                (ConcurrentHashMap<String, OrderTargetInfoTest>) Storage.readObjectFromFile(FILE_STORAGE_ORDER_DONE);
        Double profitCheck = 0d;
        Double profitTotal = 0d;

        List<KlineObjectNumber> tickers = TickerMongoHelper.getInstance().getTicker15mBySymbol(Constants.SYMBOL_PAIR_BTC);
        Map<Long, KlineObjectNumber> time2Ticker = new HashMap<>();
        Map<Long, Integer> time2Index = new HashMap<>();
        for (int i = 0; i < tickers.size(); i++) {
            KlineObjectNumber ticker = tickers.get(i);
            time2Ticker.put(ticker.startTime.longValue(), ticker);
            time2Index.put(ticker.startTime.longValue(), i);
        }
        for (OrderTargetInfoTest order : allOrderDone.values()) {
            Double rateMa = Utils.rateOf2Double(order.priceEntry, order.ma201d);
            KlineObjectNumber ticker = time2Ticker.get(order.timeStart);
            Integer index = time2Index.get(order.timeStart);
            TrendState btcTrend1H = BTCMacdTrendManager.getInstance().getTrend(Constants.INTERVAL_1H, order.timeStart);
            Double btcRsi = 0d;
            if (ticker != null) {
                btcRsi = ticker.rsi;
            }
            Double btcRsiAvg = 0d;
            if (index != null) {
                btcRsiAvg = calAvgRsi(tickers, index - 30, 30);
            }
//            if (rateMa < 0.0) { // 75%
//            if (btcTrend1H != null && btcTrend1H.equals(TrendState.STRONG_UP)) {
//            if (true) {
            if (!order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                if (BTCTicker15MManager.getInstance().getRateWithMaxByDuration(order.timeStart, 24 * Utils.TIME_HOUR) < 0.005) {
                    profitCheck += Utils.rateOf2Double(order.priceTP, order.priceEntry);
                }
                profitTotal += Utils.rateOf2Double(order.priceTP, order.priceEntry);
            }
        }
        Double rate = profitCheck * 100 / profitTotal;
        LOG.info("{}/{} {}%", profitCheck, profitTotal, rate);

    }

    private static Double calAvgRsi(List<KlineObjectNumber> tickers, int i, int duration) {
        Double total = 0d;
        for (int j = i; j < i + duration; j++) {
            KlineObjectNumber ticker = tickers.get(j);
            total += ticker.rsi;
        }
        return total / duration;
    }

    public static void printOrderTestDone() throws IOException {
        ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone =
                (ConcurrentHashMap<String, OrderTargetInfoTest>) Storage.readObjectFromFile(FILE_STORAGE_ORDER_DONE);
        TreeMap<Long, OrderTargetInfoTest> time2Order = new TreeMap<>();
        int counter = 0;
        for (OrderTargetInfoTest order : allOrderDone.values()) {
            counter++;
            time2Order.put(order.timeStart + counter, order);
        }

        List<String> lines = new ArrayList<>();
        List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(DataManager.FOLDER_TICKER_15M + Constants.SYMBOL_PAIR_BTC);
        Map<Long, KlineObjectNumber> time2Ticker = new HashMap<>();
        Map<Long, Integer> time2Index = new HashMap<>();
        for (int i = 0; i < tickers.size(); i++) {
            KlineObjectNumber ticker = tickers.get(i);
            time2Ticker.put(ticker.startTime.longValue(), ticker);
            time2Index.put(ticker.startTime.longValue(), i);
        }
        Map<String, Double> symbol2Profit = new HashMap<>();
        for (OrderTargetInfoTest order : time2Order.values()) {
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
            symbol2Profit.put(order.symbol, profitOfSymbol);
            StringBuilder builder = new StringBuilder();
            builder.append(order.symbol).append(",");
            builder.append(order.priceEntry).append(",");
            builder.append(order.priceTP).append(",");
            Double profit = Utils.rateOf2Double(order.priceTP, order.priceEntry);
            if (order.side.equals(OrderSide.SELL)) {
                profit = -Utils.rateOf2Double(order.priceTP, order.priceEntry);
            }
            builder.append(profit).append(",");
//            builder.append(order.minPrice).append(",");
//            builder.append(Utils.rateOf2Double(order.minPrice, order.priceEntry)).append(",");
//            builder.append(SimpleMovingAverage1DManager.getInstance().getRateChangeWithDuration(order.symbol,
//                    order.timeStart, 5)).append(",");
//            builder.append(SimpleMovingAverage1DManager.getInstance().getRateChangeWithDuration(order.symbol,
//                    order.timeStart, 15)).append(",");
//            builder.append(SimpleMovingAverage1DManager.getInstance().getRateChangeWithDuration(order.symbol,
//                    order.timeStart, 30)).append(",");
//            builder.append(Utils.rateOf2Double(order.priceEntry, maValue)).append(",");
//            builder.append(maValue).append(",");
//            builder.append(maStatus).append(",");
            builder.append(order.maxPrice).append(",");
            builder.append(Utils.rateOf2Double(order.maxPrice, order.priceEntry)).append(",");
//            Map<String, KlineObjectNumber> data48h = time2SymbolAndRateChange.get(order.timeStart);
//            KlineObjectNumber ticker48h = null;
//            if (data48h != null) {
//                ticker48h = data48h.get(order.symbol);
//            }
//            if (ticker48h != null) {
//                builder.append(ticker48h.maxPrice).append(",");
//                builder.append(Utils.rateOf2Double(ticker48h.maxPrice, order.priceEntry)).append(",");
//            } else {
//                builder.append("null").append(",");
//                builder.append("null").append(",");
//            }
            builder.append(order.status.toString()).append(",");
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)).append(",");
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate)).append(",");
            builder.append(order.marketLevelChange).append(",");
            builder.append(order.dcaLevel).append(",");
            builder.append(Utils.rateOf2Double(order.tickerOpen.minPrice, order.tickerOpen.maxPrice)).append(",");
            builder.append(order.tickerOpen.totalUsdt).append(",");
//            builder.append(order.rsi14).append(",");
//            builder.append(btcRsiAvg).append(",");
//            builder.append(btcRsi).append(",");
            builder.append(order.ma201d).append(",");
            builder.append(order.quantity).append(",");
            builder.append(order.leverage).append(",");
            builder.append(calTp(order)).append(",");
            builder.append((order.timeUpdate - order.timeStart) / Utils.TIME_HOUR).append(",");
//            builder.append(BTCTicker15MManager.getInstance().getRateWithMaxByDuration(order.timeStart, 8 * Utils.TIME_HOUR));

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

        FileUtils.writeLines(new File("target/printDone.csv"), lines);
    }

    public static Double calTp(OrderTargetInfoTest orderInfo) {
        Double tp = orderInfo.quantity * (orderInfo.priceTP - orderInfo.priceEntry);
        if (orderInfo.side.equals(OrderSide.SELL)) {
            tp = -tp;
        }
        return tp;
    }

}
