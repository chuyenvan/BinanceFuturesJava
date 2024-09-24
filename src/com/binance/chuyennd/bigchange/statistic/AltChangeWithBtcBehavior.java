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
public class AltChangeWithBtcBehavior {

    public static final Logger LOG = LoggerFactory.getLogger(AltChangeWithBtcBehavior.class);
    private static final int NUMBER_HOURS_STOP_MIN = Configs.getInt("NUMBER_HOURS_STOP_MIN");
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
            lines.addAll(detectAltBuyEntry());
            FileUtils.writeLines(new File(AltChangeWithBtcBehavior.class.getSimpleName() + ".csv"), lines);

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
        return order.symbol + "," + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart) + "," +
                Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate) + "," + order.priceEntry + "," +
                order.priceTP + "," + order.lastPrice + "," + order.volume + "," + order.rateBtc15m + "," +
                order.status + "," + rateLoss + "," + order.maxPrice + "," +
                Utils.rateOf2Double(order.maxPrice, order.priceEntry) + "," +
                Utils.rateOf2Double(order.tickerOpen.priceClose, order.tickerOpen.priceOpen) + "," +
                Utils.rateOf2Double(order.tickerClose.maxPrice, order.tickerClose.minPrice) + "," +
                (order.timeUpdate - order.timeStart) / Utils.TIME_MINUTE;
    }


    List<String> detectAltSellEntry(Double target) {

        List<String> lines = new ArrayList<>();
        File[] symbolFiles = new File(Configs.FOLDER_TICKER_15M).listFiles();
        int counterSym = 0;
        int totalSym = symbolFiles.length;
        List<OrderTargetInfoTest> orderTrades = new ArrayList<>();
        for (File symbolFile : symbolFiles) {
            String symbol = symbolFile.getName();
            counterSym++;
            LOG.info("Processing: {}/{}", counterSym, totalSym);
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
                            OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry, priceTarget, 1.0, 10, symbol, kline.startTime.longValue(), kline.startTime.longValue(), OrderSide.SELL);

                            orderTrade.maxPrice = kline.priceClose;
                            orderTrade.minPrice = kline.minPrice;
                            orderTrade.volume = kline.totalUsdt;
                            orderTrade.rateBtc15m = kline.rsi;
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
                            if (!orderTrade.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE) && !orderTrade.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
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

        for (int minEntry = 4; minEntry < 5; minEntry++) {
            for (int numberOrder2Trade = 2; numberOrder2Trade < 3; numberOrder2Trade++) {
                // remove order by rule
                counterTotal = 0;
                counterSuccess = 0;
                counterStoploss = 0;
                totalLoss = 0.0;
                List<OrderTargetInfoTest> orders = cleanOrder(orderTrades, numberOrder2Trade, minEntry);
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
                    LOG.info("Result target:{} minEntry:{} numberOrder:{} {}-{}-{}%-{}/{} {}% pl: {}/{} {}%", target, minEntry, numberOrder2Trade, counterSuccess, counterStoploss, rateSuccessLoss.doubleValue() / 10, counterSuccess + counterStoploss, counterTotal, rateSuccess.doubleValue() / 10, totalLoss.longValue(), pnl.longValue(), Utils.formatPercent(totalLoss / pnl));
                }
            }
        }

        return lines;
    }

    List<String> detectAltBuyEntry() {

        List<String> lines = new ArrayList<>();
        File[] symbolFiles = new File(Configs.FOLDER_TICKER_15M).listFiles();
        int counterSym = 0;
        int totalSym = symbolFiles.length;
        List<OrderTargetInfoTest> orderTrades = new ArrayList<>();
        Map<Long, MarketLevelChange> time2Level = (Map<Long, MarketLevelChange>) Storage.readObjectFromFile("target/time2marketLevel.data");
        List<KlineObjectNumber> btcTickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_15M + Constants.SYMBOL_PAIR_BTC);
        Map<Double, KlineObjectNumber> time2BtcDown = new HashMap<>();
        for (int i = 1; i < btcTickers.size(); i++) {

            KlineObjectNumber lastTicker = btcTickers.get(i - 1);
            KlineObjectNumber ticker = btcTickers.get(i);
            Double breadBellow = Utils.rateOf2Double(ticker.priceClose, ticker.minPrice);
            if (Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) >= 0.002
//                    && breadBellow < 0.002
//                    && Utils.rateOf2Double(lastTicker.priceClose, lastTicker.priceOpen) > 0.002
            ) {
                time2BtcDown.put(ticker.startTime, ticker);
            }
        }
        LOG.info("List level: {}", time2Level.size());
        for (File symbolFile : symbolFiles) {
            String symbol = symbolFile.getName();
            counterSym++;
            LOG.info("Processing: {}/{}", counterSym, totalSym);
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
                for (int i = 0; i < tickers.size() - 200; i++) {
                    try {
                        KlineObjectNumber kline = tickers.get(i);
                        if (time2Level.containsKey(kline.startTime.longValue())) {
                            continue;
                        }
                        if (!time2BtcDown.containsKey(kline.startTime)) {
                            continue;
                        }
                        Double rateChange = Utils.rateOf2Double(kline.priceClose, kline.priceOpen);
                        Double breadAbove = Utils.rateOf2Double(kline.maxPrice, kline.priceClose);
                        if (rateChange < -0.003
//                                && rateChange < 0.03 && breadAbove < rateChange
//                                && breadAbove < 0.003
                        ) {
                            try {
                                Double priceEntry = kline.priceClose;
                                OrderSide side = OrderSide.SELL;
                                Double priceTarget = getPriceTarget(priceEntry, side, RATE_TARGET);
                                OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry, priceTarget, 1.0, 10, symbol, kline.startTime.longValue(), kline.startTime.longValue(), side);

                                orderTrade.maxPrice = kline.priceClose;
                                orderTrade.minPrice = kline.minPrice;
                                orderTrade.volume = kline.totalUsdt;
                                orderTrade.rateBtc15m = kline.rsi;
                                orderTrade.lastPrice = kline.priceClose;
                                orderTrade.tickerOpen = kline;
                                orderTrade.tickerClose = time2BtcDown.get(kline.startTime);
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
                                if (!orderTrade.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE) && !orderTrade.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
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

        // remove order by rule
        for (int minEntry = 4; minEntry < 5; minEntry++) {
            for (int numberOrder2Trade = 2; numberOrder2Trade < 3; numberOrder2Trade++) {
                // remove order by rule
                counterTotal = 0;
                counterSuccess = 0;
                counterStoploss = 0;
                totalLoss = 0.0;
//                List<OrderTargetInfoTest> orders = cleanOrder(orderTrades, numberOrder2Trade, minEntry);
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
                    Double pnl = counterSuccess * RATE_TARGET;
                    LOG.info("Result target:{} minEntry:{} numberOrder:{} {}-{}-{}%-{}/{} {}% pl: {}/{} {}%", RATE_TARGET, minEntry, numberOrder2Trade, counterSuccess, counterStoploss, rateSuccessLoss.doubleValue() / 10, counterSuccess + counterStoploss, counterTotal, rateSuccess.doubleValue() / 10, totalLoss.longValue(), pnl.longValue(), Utils.formatPercent(totalLoss / pnl));
                }
            }
        }

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
                    rateChange2Symbol.put(-rateChangeVolume, order);
//                    }
                }
                int counter = 0;
                for (Map.Entry<Double, OrderTargetInfoTest> entry2 : rateChange2Symbol.entrySet()) {
                    orderResult.add(entry2.getValue());
                    counter++;
                    if (counter >= numberOrder) {
                        break;
                    }
                }
            }
        }
        return orderResult;
    }

    public static void main(String[] args) throws ParseException {
        new AltChangeWithBtcBehavior().statisticSellOrder();

        System.exit(1);
    }


}
