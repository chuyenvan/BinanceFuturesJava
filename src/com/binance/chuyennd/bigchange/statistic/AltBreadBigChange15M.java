package com.binance.chuyennd.bigchange.statistic;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetStatus;
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

/**
 * @author pc
 */
public class AltBreadBigChange15M {

    public static final Logger LOG = LoggerFactory.getLogger(AltBreadBigChange15M.class);

    public Integer counterTotal = 0;
    public Integer counterSuccess = 0;
    public Integer counterDcaSuccess = 0;
    public Integer counterStoploss = 0;
    public Double totalLoss = 0d;

    private void fixRateChangeAndVolume() throws ParseException {

        // test for multi param
        try {
            List<String> lines = new ArrayList<>();
//            for (int i = 35; i < 50; i += 5) {
//                for (int k = 0; k < 10; k++) {
//                    for (int j = 0; j < 10; j++) {
//                        Double rateMax = -0.07 - j * 0.01;
//                        Double rateUp = 0.016 + k * 0.002;
////                        LOG.info("{} {} {}", i, rateMax, rateUp);
//                        lines.addAll(detectBuyWithBreadBellow(i, rateMax, rateUp));
//                    }
//                }
//            }

            lines.addAll(detectSELLWithBreadBellow(25));
            FileUtils.writeLines(new File(AltBreadBigChange15M.class.getSimpleName() + ".csv"), lines);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private Double getPriceTarget(Double priceEntry, OrderSide orderSide, Double rateTarget) {
        double priceChange2Target = rateTarget * priceEntry;
        if (orderSide.equals(OrderSide.BUY)) {
            return priceEntry + priceChange2Target;
        } else {
            return priceEntry - priceChange2Target;
        }
    }

    private Double getPriceSL(Double priceEntry, OrderSide orderSide, Double rateTarget) {
        double priceChange2Target = rateTarget * priceEntry;
        if (orderSide.equals(OrderSide.BUY)) {
            return priceEntry - priceChange2Target;
        } else {
            return priceEntry + priceChange2Target;
        }
    }


    private List<String> printResultTradeTest(List<OrderTargetInfoTest> orders) {
        List<String> lines = new ArrayList<>();
        TreeMap<Long, OrderTargetInfoTest> time2Orders = new TreeMap<>();
        int counter = 0;
        for (OrderTargetInfoTest order : orders) {
            counter++;
            time2Orders.put(-(order.timeStart + counter), order);
        }
        lines.add("");
        for (OrderTargetInfoTest order : time2Orders.values()) {
            counterTotal++;
            Boolean orderState;
            Double rateLoss = Utils.rateOf2Double(order.priceTP, order.priceEntry);
            if (order.side.equals(OrderSide.SELL)) {
                rateLoss = -rateLoss;
            }
            totalLoss += rateLoss;
            if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                counterSuccess++;
                if (order.dynamicTP_SL != null) {
                    counterDcaSuccess += order.dynamicTP_SL;
                }
                orderState = true;
                rateLoss = Configs.RATE_TARGET;
            } else {
                if (order.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                    counterStoploss++;
                }
                orderState = false;
            }
            lines.add(buildLineTest(order, orderState, rateLoss));

        }
        return lines;
    }

    private String buildLineTest(OrderTargetInfoTest order, boolean orderState, Double rateLoss) {
        if (rateLoss == null) {
            rateLoss = Configs.RATE_TARGET;
        }

        return order.symbol.replace("USDT", "") + "," + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)
                + ",'" + Utils.sdfGoogle.format(new Date(order.timeStart)) + "," + order.side + ","
                + order.priceEntry + "," + order.priceTP + "," + order.priceSL + ","
                + order.lastPrice + "," + orderState + ","
                + rateLoss + "," + Utils.rateOf2Double(order.tickerOpen.priceClose, order.tickerOpen.priceOpen)
                + "," + order.maxPrice + "," + Utils.rateOf2Double(order.maxPrice, order.priceEntry)
                + "," + (order.timeUpdate - order.timeStart) / Utils.TIME_MINUTE;
    }

    List<String> detectSELLWithBreadBellow(Integer period) {
        List<String> lines = new ArrayList<>();
        File[] symbolFiles = new File(Configs.FOLDER_TICKER_15M).listFiles();
        TreeMap<Long, List<String>> time2Entry = new TreeMap<>();
        List<OrderTargetInfoTest> orderTrades = new ArrayList<>();
        for (File symbolFile : symbolFiles) {
            String symbol = symbolFile.getName();
            if (!StringUtils.endsWithIgnoreCase(symbol, "usdt")
                    || Constants.diedSymbol.contains(symbol)
            ) {
                continue;
            }

            try {
                List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(symbolFile.getPath());
                for (int i = 1; i < tickers.size(); i++) {
                    KlineObjectNumber kline = tickers.get(i);
//                    if (StringUtils.equals(symbol,"BAKEUSDT") && Utils.sdfFileHour.parse("20240705 11:15").getTime() == kline.startTime.longValue()){
//                        System.out.println("Debug");
//                    }
                    if (MarketBigChangeDetectorTest.isSignalSell(tickers, i)) {
                        Long time = kline.startTime.longValue() + 14 * Utils.TIME_MINUTE;
                        List<String> symbolsEntry = time2Entry.get(time);
                        if (symbolsEntry == null) {
                            symbolsEntry = new ArrayList<>();
                            time2Entry.put(time, symbolsEntry);
                        }
                        symbolsEntry.add(symbol);
                        try {
                            Double priceEntry = kline.priceClose;
                            Double priceTarget = Utils.calPriceTarget(symbol, priceEntry, OrderSide.SELL, 3 * Configs.RATE_TARGET);
                            Double priceSTL = Utils.calPriceTarget(symbol, priceEntry, OrderSide.BUY, 3 * Configs.RATE_TARGET);
                            OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry, priceTarget,
                                    1.0, 10, symbol, kline.startTime.longValue(), kline.startTime.longValue(),
                                    OrderSide.SELL);
                            orderTrade.priceSL = priceSTL;
                            orderTrade.maxPrice = kline.priceClose;
                            orderTrade.minPrice = kline.minPrice;
                            orderTrade.volume = kline.totalUsdt;
                            orderTrade.tickerOpen = kline;
                            int startCheck = i;
                            for (int j = startCheck + 1; j < tickers.size(); j++) {
                                i = j;

                                KlineObjectNumber ticker = tickers.get(j);
                                orderTrade.lastPrice = ticker.priceClose;
                                orderTrade.timeUpdate = ticker.endTime.longValue();
                                if (orderTrade.maxPrice == null || ticker.maxPrice > orderTrade.maxPrice) {
                                    orderTrade.maxPrice = ticker.maxPrice;
                                }
                                if (orderTrade.minPrice == null || ticker.minPrice < orderTrade.minPrice) {
                                    orderTrade.minPrice = ticker.minPrice;
                                }
                                // stoploss by price
                                if (ticker.maxPrice >= orderTrade.priceSL && ticker.minPrice <= orderTrade.priceSL) {
                                    orderTrade.status = OrderTargetStatus.STOP_LOSS_DONE;
//                                    if (ticker.maxPrice > orderTrade.priceTP && ticker.minPrice < orderTrade.priceTP) {
//                                        orderTrade.priceTP = orderTrade.priceEntry;
//                                    } else {
//                                        orderTrade.priceTP = orderTrade.priceSL;
//                                    }
                                    orderTrade.priceTP = orderTrade.priceSL;
                                    break;
                                }

                                // stoploss by time
//                                if (ticker.startTime.longValue() - orderTrade.timeStart > 24 * Utils.TIME_HOUR) {
//                                    orderTrade.status = OrderTargetStatus.STOP_LOSS_DONE;
//                                    orderTrade.priceTP = ticker.priceOpen;
//                                    break;
//                                }

                                if (ticker.maxPrice > orderTrade.priceTP && ticker.minPrice < orderTrade.priceTP) {
                                    orderTrade.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                                    break;
                                }

                            }
                            orderTrades.add(orderTrade);
                            LOG.info("{} {} {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(kline.startTime.longValue()),
                                    Utils.sdfGoogle.format(new Date(kline.startTime.longValue())), kline.priceClose,
                                    orderTrade.status);
                        } catch (Exception e) {
                            LOG.info("Error: {}", Utils.toJson(kline));
                            e.printStackTrace();
                        }
                    }
                }

            } catch (Exception e) {
                LOG.info("Error process symbol: {}", symbol);
                e.printStackTrace();
            }
        }
//        for (Long time : time2rateMaxAndSymbol.keySet()) {
//            if (!timeBtcReverse.contains(time)) {
//                continue;
//            }
//            int counter = 0;
//            for (Double rateMax : time2rateMaxAndSymbol.get(time).keySet()) {
//                LOG.info("{} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), time2rateMaxAndSymbol.get(time).get(rateMax),
//                        Utils.formatDouble(rateMax, 2));
//                long timeEntry = time + 14 * Utils.TIME_MINUTE;
//                List<String> symbolsEntry = time2Entry.get(timeEntry);
//                if (symbolsEntry == null) {
//                    symbolsEntry = new ArrayList<>();
//                    time2Entry.put(timeEntry, symbolsEntry);
//                }
//                symbolsEntry.add(time2rateMaxAndSymbol.get(time).get(rateMax));
//                counter++;
//                if (counter >= 2) {
//                    break;
//                }
//            }
//        }

        Storage.writeObject2File("target/entry/volumeBigSignalSELL.data", time2Entry);
//        for (int minEntry = 1; minEntry < 2; minEntry++) {
//            for (int numberOrder2Trade = 5; numberOrder2Trade < 6; numberOrder2Trade++) {
        // remove order by rule
        counterTotal = 0;
        counterSuccess = 0;
        counterDcaSuccess = 0;
        counterStoploss = 0;
        totalLoss = 0.0;
        //        List<OrderTargetInfoTest> orders = cleanOrder(orderTrades, numberOrder2Trade, minEntry);
//            List<OrderTargetInfoTest> orders = cleanOrder(orderTrades, null, minEntry);
        List<OrderTargetInfoTest> orders = orderTrades;

        if (!orderTrades.isEmpty()) {
            lines.addAll(printResultTradeTest(orders));
        }

        Integer rateSuccess = 0;
        Integer rateSuccessLoss = 0;

        if (counterTotal != 0) {
            rateSuccess = counterSuccess * 1000 / counterTotal;
        }

        if (counterSuccess != 0) {
            rateSuccessLoss = counterStoploss * 1000 / counterSuccess;
        }
        if (counterSuccess > 0) {
            Double pnl = (counterSuccess + counterDcaSuccess) * Configs.RATE_TARGET;
            LOG.info("Result target:{} period:{} {}-{}-{}%-{}/{} {}% pl: {}%", Configs.RATE_TARGET,
                    period,
                    counterSuccess, counterStoploss,
                    rateSuccessLoss.doubleValue() / 10, counterSuccess + counterStoploss, counterTotal,
                    rateSuccess.doubleValue() / 10, Utils.formatPercent(totalLoss / orders.size()));
//                }
//            }
        }
        return lines;
    }

    private TreeSet<Long> extractBtcReverse(List<KlineObjectNumber> tickers) {
        TreeSet<Long> results = new TreeSet<>();
        for (int index = 6; index < tickers.size(); index++) {
            try {
                KlineObjectNumber finalTicker = tickers.get(index);
                if (Utils.rateOf2Double(finalTicker.priceClose, finalTicker.priceOpen) < -0.005) {
                    Double maxPrice = null;
                    for (int i = 1; i < 6; i++) {
                        KlineObjectNumber ticker = tickers.get(index - i);
                        if (maxPrice == null || maxPrice < ticker.maxPrice) {
                            maxPrice = ticker.maxPrice;
                        }
                    }
                    if (Utils.rateOf2Double(finalTicker.priceClose, maxPrice) < -0.02) {
                        results.add(finalTicker.startTime.longValue());
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return results;
    }

    private List<OrderTargetInfoTest> cleanOrder(List<OrderTargetInfoTest> orders, Integer numberOrder, Integer minEntry) {
        List<OrderTargetInfoTest> orderResult = new ArrayList<>();
        Map<Long, List<OrderTargetInfoTest>> time2Orders = new HashMap<>();
        for (OrderTargetInfoTest order : orders) {
            List<OrderTargetInfoTest> orderOfTime = time2Orders.get(order.timeStart);
            if (orderOfTime == null) {
                orderOfTime = new ArrayList<>();
            }
            orderOfTime.add(order);
            time2Orders.put(order.timeStart, orderOfTime);
        }
        for (Map.Entry<Long, List<OrderTargetInfoTest>> entry : time2Orders.entrySet()) {
            List<OrderTargetInfoTest> orderOfTime = entry.getValue();
            if (orderOfTime.size() >= minEntry) {
//            if (orderOfTime.size() == 1) {
                TreeMap<Double, OrderTargetInfoTest> rateChange2Symbol = new TreeMap<>();
                for (OrderTargetInfoTest order : orderOfTime) {
//                    if (order.tickerClose != null) {
//                        Double rateChangeVolume = Utils.rateOf2Double(order.tickerOpen.totalUsdt, order.tickerClose.totalUsdt);
                    Double rateChangeVolume = Utils.rateOf2Double(order.tickerOpen.priceClose, order.tickerOpen.priceOpen);
                    rateChange2Symbol.put(rateChangeVolume, order);
//                    }
                }
                int counter = 0;
                for (Map.Entry<Double, OrderTargetInfoTest> entry2 : rateChange2Symbol.entrySet()) {
                    orderResult.add(entry2.getValue());
                    counter++;
                    if (numberOrder != null
                            && counter >= numberOrder) {
                        break;
                    }
                }
            }
        }
        return orderResult;
    }


    public static void main(String[] args) throws ParseException {
        new AltBreadBigChange15M().fixRateChangeAndVolume();
        System.exit(1);
    }
}
