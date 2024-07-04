package com.educa.chuyennd.funcs;

import com.binance.chuyennd.bigchange.btctd.BreadDetectObject;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Utils;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.util.*;

public class TraderScoring {
    public static final Logger LOG = LoggerFactory.getLogger(TraderScoring.class);

    public static void main(String[] args) throws IOException {
        traceData();
    }

    private static void traceData() throws IOException {
        String fileName = "target/AltBreadBigChange15M-rate-ma-0.15.csv";

        List<String> lines = FileUtils.readLines(new File(fileName));
        Map<Long, List<OrderTargetInfoTest>> time2Orders = new HashMap<>();
        List<OrderTargetInfoTest> order2Trades = new ArrayList<>();
        for (String line : lines) {
            try {
                String[] parts = StringUtils.split(line, ",");
                String symbol = parts[0];
                Long time = Utils.sdfFileHour.parse(parts[1]).getTime();
                Double entry = Double.parseDouble(parts[3]);
                Double lastPrice = Double.parseDouble(parts[5]);
                Double volume = Double.parseDouble(parts[7]);
                Boolean status = Boolean.parseBoolean(parts[9]);
                int timeTrade = Integer.parseInt(parts[13]);
                OrderTargetInfoTest orderTargetInfo = new OrderTargetInfoTest();
                orderTargetInfo.symbol = symbol;
                orderTargetInfo.timeStart = time;
                orderTargetInfo.priceEntry = entry;
                orderTargetInfo.lastPrice = lastPrice;
                orderTargetInfo.avgVolume24h = volume;
                orderTargetInfo.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                if (!status) {
                    orderTargetInfo.status = OrderTargetStatus.STOP_LOSS_DONE;
                }
                orderTargetInfo.timeUpdate = time + timeTrade * Utils.TIME_MINUTE;
                List<OrderTargetInfoTest> orders = time2Orders.get(time);
                if (orders == null) {
                    orders = new ArrayList<>();
                    time2Orders.put(time, orders);
                }
                orders.add(orderTargetInfo);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        TreeMap<Double, Long> rate2Time = new TreeMap<>();
        int period = 5;
        int counterSuccessPeriod = 0;
        int totalPeriod = 0;
        Double pnlSLPeriod = 0d;
        Double pnlSLNotPeriod = 0d;
        int counterSuccessNotPeriod = 0;
        int totalNotPeriod = 0;
        for (Map.Entry<Long, List<OrderTargetInfoTest>> entry : time2Orders.entrySet()) {
            Long key = entry.getKey();
            List<OrderTargetInfoTest> orders = entry.getValue();
            int counterDone = 0;
            Double pnlSL = 0d;
            for (OrderTargetInfoTest orderTargetInfo : orders) {
                if (orderTargetInfo.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                    counterDone++;
                } else {
                    pnlSL += Utils.rateOf2Double(orderTargetInfo.lastPrice, orderTargetInfo.priceEntry);
                }
            }
            Double rate = counterDone * 1000d / orders.size();
            if (orders.size() >= period) {
                totalPeriod += orders.size();
                counterSuccessPeriod += counterDone;
                if (rate2Time.containsKey(rate)){
                    rate += 0.001;
                }
                rate2Time.put(rate, key);
                pnlSLPeriod += pnlSL;
            } else {
                totalNotPeriod += orders.size();
                counterSuccessNotPeriod += counterDone;
                pnlSLNotPeriod += pnlSL;
            }
        }
        for (Map.Entry<Double, Long> entry : rate2Time.entrySet()) {
            Double rate = entry.getKey();
            Long time = entry.getValue();
            List<OrderTargetInfoTest> orders = time2Orders.get(time);
            int counterDone = 0;
            for (OrderTargetInfoTest orderTargetInfo : orders) {
                if (orderTargetInfo.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                    counterDone++;
                }
            }

            LOG.info("{} {}/{} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), counterDone, orders.size(), rate / 10);
        }
        LOG.info("Period: {}/{} rate: {}% {} NotPeriod:{}/{} rate: {}% {} totalAll:{}",
                counterSuccessPeriod, totalPeriod, counterSuccessPeriod * 100 / totalPeriod,
                pnlSLPeriod * 100 / (totalPeriod ),
                counterSuccessNotPeriod, totalNotPeriod, counterSuccessNotPeriod * 100 / totalNotPeriod,
                pnlSLNotPeriod * 100 / (totalNotPeriod ),
                totalNotPeriod + totalPeriod);
    }

    public static Double calScore(List<KlineObjectNumber> tickers, int i) {
        Double maxPriceBefore = null;
        KlineObjectNumber ticker24h = TickerFuturesHelper.extractKline24hr(tickers, tickers.get(i).startTime.longValue());
        Double rateWithMax24hr = Utils.rateOf2Double(ticker24h.maxPrice, tickers.get(i).priceClose);
        for (int j = 0; j < 25; j++) {
            if (i - j >= 0) {
                KlineObjectNumber ticker = tickers.get(i - j);
                if (maxPriceBefore == null || maxPriceBefore < ticker.maxPrice) {
                    maxPriceBefore = ticker.maxPrice;
                }
            }
        }
        Double rateWithMaxBefore6h = Utils.rateOf2Double(maxPriceBefore, tickers.get(i).priceClose);
        return rateWithMaxBefore6h;
    }

    public static StringBuilder buildLineData(List<KlineObjectNumber> tickers, Double maValue, int i, String symbol,
                                              BreadDetectObject breadData, Double rateMa) {
        KlineObjectNumber kline = tickers.get(i);
        Double maxPrice = null;
        Double minPrice = null;
        Double maxPriceBefore = null;
        Double minPriceBefore = null;
        Double maxHistogramBefore = null;
        for (int j = i + 1; j < i + 64; j++) {
            if (j < tickers.size()) {
                KlineObjectNumber ticker = tickers.get(j);
                if (maxPrice == null || maxPrice < ticker.maxPrice) {
                    maxPrice = ticker.maxPrice;
                }
                if (minPrice == null || minPrice > ticker.minPrice) {
                    minPrice = ticker.minPrice;
                }
            }
        }
        for (int j = 0; j < 25; j++) {
            if (i - j >= 0) {
                KlineObjectNumber ticker = tickers.get(i - j);
                if (maxPriceBefore == null || maxPriceBefore < ticker.maxPrice) {
                    maxPriceBefore = ticker.maxPrice;
                }
                if (minPriceBefore == null || minPriceBefore > ticker.minPrice) {
                    minPriceBefore = ticker.minPrice;
                }
                if (ticker.histogram != null && (maxHistogramBefore == null || maxHistogramBefore < Math.abs(ticker.histogram))) {
                    maxHistogramBefore = Math.abs(ticker.histogram);

                }
            }
        }
        StringBuilder builder = new StringBuilder();
        KlineObjectNumber ticker24h = TickerFuturesHelper.extractKline24hr(tickers, kline.startTime.longValue());
        Double rate24hr = Utils.rateOf2Double(ticker24h.priceClose, ticker24h.priceOpen);
        Double rateWithMax24hr = Utils.rateOf2Double(ticker24h.maxPrice, kline.priceClose);
        builder.append(symbol).append(",");
        builder.append(kline.priceClose).append(",");
        builder.append(maxPrice).append(",");
        builder.append(Utils.rateOf2Double(maxPrice, kline.priceClose)).append(",");
        builder.append(Utils.rateOf2Double(maxPrice, kline.priceClose) > 0.01).append(",");
        builder.append(minPrice).append(",");
        builder.append(Utils.rateOf2Double(minPrice, kline.priceClose)).append(",");
        builder.append(breadData.totalRate).append(",");
        builder.append(Math.abs(Utils.rateOf2Double(kline.priceClose, kline.priceOpen))).append(",");
        builder.append(Utils.rateOf2Double(kline.priceClose, kline.ma20)).append(",");
        builder.append(Utils.rateOf2Double(kline.priceClose, maValue)).append(",");
        builder.append(rateMa).append(",");
        builder.append(kline.rsi).append(",");
        builder.append(rate24hr).append(",");
        builder.append(rateWithMax24hr).append(",");
        builder.append(ticker24h.totalUsdt / 1E6).append(",");
        builder.append(Utils.rateOf2Double(maxPriceBefore, kline.priceClose)).append(",");
        builder.append(TraderScoring.calScore(tickers, i)).append(",");
        builder.append(Utils.rateOf2Double(kline.priceClose, minPriceBefore)).append(",");
        builder.append(kline.histogram / maxHistogramBefore).append(",");
        return builder;
    }
}
