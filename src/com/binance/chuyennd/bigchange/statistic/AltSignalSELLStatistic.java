package com.binance.chuyennd.bigchange.statistic;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.ResistanceAndSupport;
import com.binance.chuyennd.object.TrendObject;
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
public class AltSignalSELLStatistic {

    public static final Logger LOG = LoggerFactory.getLogger(AltSignalSELLStatistic.class);
    private static final int NUMBER_HOURS_STOP_MIN = Configs.getInt("NUMBER_HOURS_STOP_MIN");
    private static final int RATE_TARGETS = Configs.getInt("RATE_TARGETS");
    private static final Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
    public Integer counterTotal = 0;
    public Integer counterSuccess = 0;
    public Integer counterStoploss = 0;
    public Double totalLoss = 0d;


    private void statisticSellOrder() throws ParseException {
        // test for multi param
        try {
            List<String> lines = new ArrayList<>();
            ArrayList<Double> rateTargets = new ArrayList<>(Arrays.asList());
            for (int i = 0; i < RATE_TARGETS; i++) {
                rateTargets.add(RATE_TARGET + i * 0.01);
            }
            for (Double target : rateTargets) {
//                lines.addAll(detectAltSellEntry(target));
                lines.addAll(detectAltBuyEntry(target));
            }
            FileUtils.writeLines(new File(AltSignalSELLStatistic.class.getSimpleName() + ".csv"), lines);

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

    private List<String> printResultTradeTest(List<OrderTargetInfoTest> orders) {
        List<String> lines = new ArrayList<>();
        for (OrderTargetInfoTest order : orders) {
            counterTotal++;
            if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                counterSuccess++;
                lines.add(buildLineTest(order, null));
            } else {
                counterStoploss++;
                double rateLoss = Utils.rateOf2Double(order.lastPrice, order.priceEntry);
                if (order.side.equals(OrderSide.BUY)) {
                    rateLoss = -rateLoss;
                }
                totalLoss += rateLoss;
                lines.add(buildLineTest(order, rateLoss));
            }
        }
        return lines;
    }


    private String buildLineTest(OrderTargetInfoTest order, Double rateLoss) {
        return order.symbol + "," + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart) + "," + Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate)
                + "," + order.priceEntry + "," + order.priceTP + "," + order.lastPrice + "," +
                order.volume + "," + order.unProfitTotal + "," + order.status + "," + order.rateChange
                + "," + order.rateBreadAbove + "," + rateLoss + "," +
                order.maxPrice + "," + Utils.rateOf2Double(order.minPrice, order.priceEntry) + ","
                + (order.timeUpdate - order.timeStart) / Utils.TIME_MINUTE;
    }


    List<String> detectAltSellEntry(Double target) {

        List<String> lines = new ArrayList<>();
        File[] symbolFiles = new File(Configs.FOLDER_TICKER_15M).listFiles();
//        int counterSym = 0;
//        int totalSym = symbolFiles.length;
        List<OrderTargetInfoTest> orderTrades = new ArrayList<>();
        for (File symbolFile : symbolFiles) {
            String symbol = symbolFile.getName();
//            counterSym++;
//            LOG.info("Processing: {}/{}", counterSym, totalSym);
            if (!StringUtils.endsWithIgnoreCase(symbol, "usdt")) {
                continue;
            }
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            if (Constants.specialSymbol.contains(symbol)) {
                continue;
            }
            List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(symbolFile.getPath());
            try {
                for (int i = 100; i < tickers.size(); i++) {
                    KlineObjectNumber kline = tickers.get(i);
                    List<KlineObjectNumber> ticker2Test = new ArrayList<>();
                    for (int j = i - 100; j < 101; j++) {
                        ticker2Test.add(tickers.get(j));
                    }
                    List<TrendObject> trends = TickerFuturesHelper.extractTopBottomObjectInTicker(ticker2Test);
                    ResistanceAndSupport rsDetector = new ResistanceAndSupport(trends, ticker2Test.get(ticker2Test.size() - 1));
                    rsDetector.detectTrend(0.03);
                    if (rsDetector.sideSuggest != null && rsDetector.sideSuggest.equals(OrderSide.SELL)) {
                        try {
                            Double priceEntry = kline.priceClose;
                            Double priceTarget = getPriceTarget(priceEntry, OrderSide.SELL, target);
                            OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry,
                                    priceTarget, 1.0, 10, symbol, kline.startTime.longValue(),
                                    kline.startTime.longValue(), OrderSide.SELL);

                            orderTrade.maxPrice = kline.priceClose;
                            orderTrade.minPrice = kline.minPrice;
                            orderTrade.volume = kline.totalUsdt;
                            orderTrade.unProfitTotal = kline.rsi;
                            orderTrade.lastPrice = kline.priceClose;
                            orderTrade.tickerOpen = kline;
                            if (i > 1) {
                                orderTrade.tickerClose = tickers.get(i - 1);
                            }
                            int startCheck = i;
                            for (int j = startCheck + 1; j < tickers.size(); j++) {
                                KlineObjectNumber ticker = tickers.get(j);
                                if (orderTrade.timeStart < ticker.startTime - Utils.TIME_HOUR * NUMBER_HOURS_STOP_MIN) {
                                    break;
                                }
                                orderTrade.lastPrice = ticker.priceClose;
                                orderTrade.timeUpdate = ticker.startTime.longValue();
                                if (ticker.maxPrice > orderTrade.priceTP && ticker.minPrice < orderTrade.priceTP) {
                                    orderTrade.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                                    break;
                                }
                                if (orderTrade.maxPrice < ticker.maxPrice) {
                                    orderTrade.maxPrice = ticker.maxPrice;
                                }
                                if (orderTrade.minPrice > ticker.minPrice) {
                                    orderTrade.minPrice = ticker.minPrice;
                                }

                            }
                            if (!orderTrade.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                                    && !orderTrade.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                                orderTrade.status = OrderTargetStatus.POSITION_RUNNING;
                            }
                            orderTrades.add(orderTrade);
                        } catch (Exception e) {
                            LOG.info("Error: {}", Utils.toJson(kline));
                            e.printStackTrace();
                        }
                    }

                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        // remove order by rule
        counterTotal = 0;
        counterSuccess = 0;
        counterStoploss = 0;
        totalLoss = 0.0;


        if (!orderTrades.isEmpty()) {
            lines.addAll(printResultTradeTest(orderTrades));
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
            Double pnl = counterSuccess * target;
            LOG.info("Result target:{} {}-{}-{}%-{}/{} {}% pl: {}/{} {}%", target, counterSuccess, counterStoploss,
                    rateSuccessLoss.doubleValue() / 10, counterSuccess + counterStoploss, counterTotal,
                    rateSuccess.doubleValue() / 10, totalLoss.longValue(), pnl.longValue(), Utils.formatPercent(totalLoss / pnl));
        }

        return lines;
    }

    List<String> detectAltBuyEntry(Double target) {

        List<String> lines = new ArrayList<>();
        File[] symbolFiles = new File(Configs.FOLDER_TICKER_15M).listFiles();
//        int counterSym = 0;
//        int totalSym = symbolFiles.length;
        List<OrderTargetInfoTest> orderTrades = new ArrayList<>();
        Map<Long, MarketLevelChange> time2Level = (Map<Long, MarketLevelChange>) Storage.readObjectFromFile("target/time2marketLevel.data");
        LOG.info("List level: {}", time2Level.size());
        for (File symbolFile : symbolFiles) {
            String symbol = symbolFile.getName();
//            counterSym++;
//            LOG.info("Processing: {}/{}", counterSym, totalSym);
            if (!StringUtils.endsWithIgnoreCase(symbol, "usdt")) {
                continue;
            }
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            if (Constants.specialSymbol.contains(symbol)) {
                continue;
            }
            List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(symbolFile.getPath());
            try {
                for (int i = 2; i < tickers.size() - 200; i++) {
                    try {
                        KlineObjectNumber lastKline = tickers.get(i - 1);
                        KlineObjectNumber kline = tickers.get(i);
//                        if (kline.startTime.longValue() == Utils.sdfFileHour.parse("20240701 15:30").getTime()){
//                            System.out.println("Debug");
//                        }
                        if (time2Level.containsKey(kline.startTime.longValue())) {
//                            LOG.info("Market level duplicate: {}", Utils.normalizeDateYYYYMMDDHHmm(kline.startTime.longValue()));
                            continue;
                        }
//                        List<KlineObjectNumber> ticker2Test = new ArrayList<>();
//                        for (int j = i - 200; j < i + 1; j++) {
//                            ticker2Test.add(tickers.get(j));
//                        }
//                        List<TrendObject> trends = TickerFuturesHelper.extractTopBottomObjectInTicker(ticker2Test);
//                        if (trends == null || trends.size() < 2) {
//                            LOG.info("Error trend: {} {} {}", i, Utils.normalizeDateYYYYMMDDHHmm(kline.startTime.longValue()), symbol);
//                            continue;
//                        }
                        Double breadAbove = Utils.rateOf2Double(kline.maxPrice, kline.priceOpen);
                        if (kline.priceOpen < kline.priceClose) {
                            breadAbove = Utils.rateOf2Double(kline.maxPrice, kline.priceClose);
                        }
                        Double rateChange = Utils.rateOf2Double(kline.priceClose, kline.priceOpen);
                        Double rateChangeTotal = Utils.rateOf2Double(kline.maxPrice, kline.minPrice);
                        KlineObjectNumber ticker2Hours = TickerFuturesHelper.extractKlineByNumberTicker(tickers, i, 8);

//                        if (MarketBigChangeDetectorTest.getSignalSellAlt15M(tickers, i) == 1) {
                        if (breadAbove > 0.01
                                && rateChangeTotal > 0.02
                                && ticker2Hours != null
                                && Utils.rateOf2Double(kline.priceOpen, ticker2Hours.minPrice) > 0.1
//                                && kline.totalUsdt/lastKline.totalUsdt < 0.5
//                                && rateChange < -0.002
//                                && kline.maxPrice >= ticker2Hours.maxPrice
                        ) {
                            try {
                                Double priceEntry = kline.priceClose;
                                OrderSide side = OrderSide.SELL;
                                Double priceTarget = getPriceTarget(priceEntry, side, target);
                                OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry,
                                        priceTarget, 1.0, 10, symbol, kline.startTime.longValue(),
                                        kline.startTime.longValue(), side);

                                orderTrade.maxPrice = kline.priceClose;
                                orderTrade.minPrice = kline.minPrice;
                                orderTrade.volume = kline.totalUsdt;
                                orderTrade.unProfitTotal = kline.rsi;
                                orderTrade.rateChange = rateChange;
                                orderTrade.rateBreadAbove = Utils.rateOf2Double(kline.priceOpen, ticker2Hours.minPrice);

                                orderTrade.lastPrice = kline.priceClose;
                                orderTrade.tickerOpen = kline;
                                if (i > 1) {
                                    orderTrade.tickerClose = tickers.get(i - 1);
                                }
                                int startCheck = i;
                                for (int j = startCheck + 1; j < tickers.size(); j++) {
                                    KlineObjectNumber ticker = tickers.get(j);
                                    if (orderTrade.timeStart < ticker.startTime - Utils.TIME_HOUR * NUMBER_HOURS_STOP_MIN) {
                                        break;
                                    }
                                    orderTrade.lastPrice = ticker.priceClose;
                                    orderTrade.timeUpdate = ticker.startTime.longValue();
//                                    if (ticker.maxPrice > orderTrade.priceSL && ticker.minPrice < orderTrade.priceSL) {
//                                        orderTrade.status = OrderTargetStatus.STOP_LOSS_DONE;
//                                        orderTrade.priceTP = orderTrade.priceSL;
//                                        break;
//                                    }
                                    if (ticker.maxPrice > orderTrade.priceTP && ticker.minPrice < orderTrade.priceTP) {
                                        orderTrade.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                                        break;
                                    }

                                    if (orderTrade.maxPrice < ticker.maxPrice) {
                                        orderTrade.maxPrice = ticker.maxPrice;
                                    }
                                    if (orderTrade.minPrice > ticker.minPrice) {
                                        orderTrade.minPrice = ticker.minPrice;
                                    }

                                }
                                if (!orderTrade.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                                        && !orderTrade.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                                    orderTrade.status = OrderTargetStatus.POSITION_RUNNING;
                                }
                                orderTrades.add(orderTrade);
                            } catch (Exception e) {
                                LOG.info("Error: {}", Utils.toJson(kline));
                                e.printStackTrace();
                            }
                        }
                    } catch (Exception e) {
                        e.printStackTrace();
                    }

                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        for (int minEntry = 1; minEntry < 2; minEntry++) {
            for (int numberOrder2Trade = 4; numberOrder2Trade < 5; numberOrder2Trade++) {
                // remove order by rule
                counterTotal = 0;
                counterSuccess = 0;
                counterStoploss = 0;
                totalLoss = 0.0;
//                List<OrderTargetInfoTest> orders = cleanOrder(orderTrades, numberOrder2Trade, minEntry);
                List<OrderTargetInfoTest> orders = cleanOrder(orderTrades, null, minEntry);
//                List<OrderTargetInfoTest> orders = orderTrades;

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
                    Double pnl = counterSuccess * target;
                    LOG.info("Result target:{} minEntry:{} numberOrder:{} {}-{}-{}%-{}/{} {}% pl: {}/{} {}%", target, minEntry, numberOrder2Trade, counterSuccess, counterStoploss,
                            rateSuccessLoss.doubleValue() / 10, counterSuccess + counterStoploss, counterTotal,
                            rateSuccess.doubleValue() / 10, totalLoss.longValue(), pnl.longValue(), Utils.formatPercent(totalLoss / pnl));
                }
            }
        }
//        // remove order by rule
//        counterTotal = 0;
//        counterSuccess = 0;
//        counterStoploss = 0;
//        totalLoss = 0.0;
//
//
//        if (!orderTrades.isEmpty()) {
//            lines.addAll(printResultTradeTest(orderTrades));
//        }
//        Integer rateSuccess = 0;
//        Integer rateSuccessLoss = 0;
//
//        if (counterTotal != 0) {
//            rateSuccess = counterSuccess * 1000 / counterTotal;
//        }
//
//        if (counterSuccess != 0) {
//            rateSuccessLoss = counterStoploss * 1000 / counterSuccess;
//        }
//        if (counterSuccess > 0) {
//            Double pnl = counterSuccess * target;
//            LOG.info("Result target:{} {}-{}-{}%-{}/{} {}% pl: {}/{} {}%", target, counterSuccess, counterStoploss,
//                    rateSuccessLoss.doubleValue() / 10, counterSuccess + counterStoploss, counterTotal,
//                    rateSuccess.doubleValue() / 10, totalLoss.longValue(), pnl.longValue(), Utils.formatPercent(totalLoss / pnl));
//        }

        return lines;
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
                TreeMap<Double, OrderTargetInfoTest> rateChange2Symbol = new TreeMap<>();
                for (OrderTargetInfoTest order : orderOfTime) {
//                    if (order.tickerClose != null) {
//                        Double rateChangeVolume = Utils.rateOf2Double(order.tickerClose.totalUsdt, order.tickerOpen.totalUsdt);
                    Double rateChangeVolume = Utils.rateOf2Double(order.tickerOpen.priceClose, order.tickerOpen.priceOpen);
                    rateChange2Symbol.put(rateChangeVolume, order);
//                    }
                }
                int counter = 0;
                for (Map.Entry<Double, OrderTargetInfoTest> entry2 : rateChange2Symbol.entrySet()) {
                    orderResult.add(entry2.getValue());
                    counter++;
                    if (numberOrder != null) {
                        if (counter >= numberOrder) {
                            break;
                        }
                    }
                }
            }
        }
        return orderResult;
    }

    public static void main(String[] args) throws ParseException {
        new AltSignalSELLStatistic().statisticSellOrder();

        System.exit(1);
    }


}
