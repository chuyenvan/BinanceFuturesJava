package com.binance.chuyennd.bigchange.statistic;

import com.binance.chuyennd.trading.DcaHelper;
import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.educa.chuyennd.funcs.BreadFunctions;
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

    private static final int NUMBER_HOURS_STOP_MIN = Configs.getInt("NUMBER_HOURS_STOP_MIN");
    public BreadDetectObject lastBreadTrader = null;
    public Long lastTimeBreadTrader = 0l;
    public Double RATE_BREAD_MIN_2TRADE = Configs.getDouble("RATE_BREAD_MIN_2TRADE");
    public final Double RATE_MA_MAX = Configs.getDouble("RATE_MA_MAX");
    public static final Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
    public Double ALT_BREAD_BIGCHANGE_15M = 0.008;
    public Double ALT_BREAD_BIGCHANE_STOPPLOSS = 0.1;
    public Double RATE_CHANGE_WITHBREAD_2TRADING_TARGET = 0.009;
    public Integer counterTotal = 0;
    public Integer counterSuccess = 0;
    public Integer counterDcaSuccess = 0;
    public Integer counterStoploss = 0;
    public Double totalLoss = 0d;

    private void fixRateChangeAndVolume() throws ParseException {
//        long start_time = Configs.getLong("start_time");

        // test for multi param
        try {
            List<String> lines = new ArrayList<>();
            lines.addAll(detectBuyWithBreadBellow());

//            printByDate(lines);
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
            Double rateLoss = Utils.rateOf2Double(order.lastPrice, order.priceEntry);
            if (order.side.equals(OrderSide.SELL)) {
                rateLoss = -rateLoss;
            }
            if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                counterSuccess++;
                if (order.dcaLevel != null) {
                    counterDcaSuccess += order.dcaLevel;
                }
                orderState = true;
                rateLoss = RATE_TARGET;
            } else {
                if (order.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                    counterStoploss++;
                } else {

                    if (order.dcaLevel != null) {
                        totalLoss += rateLoss * (order.dcaLevel + 1);
                    } else {
                        totalLoss += rateLoss;
                    }
                }
                orderState = false;
            }
            lines.add(buildLineTest(order, orderState, rateLoss));

        }
        return lines;
    }

    private String buildLineTest(OrderTargetInfoTest order, boolean orderState, Double rateLoss) {
        if (rateLoss == null) {
            rateLoss = RATE_TARGET;
        }
//        Map<String, KlineObjectNumber> symbolsStatisticAfter48h = DataStatisticHelper.getInstance().readDataStaticByTimeAndNumberTickerStatic(order.timeStart, 192l);
//        Double minPriceStatistic = 0d;
//        Double rateMin = 0d;
//        KlineObjectNumber tickerStatistics = null;
//        if (symbolsStatisticAfter48h != null) {
//            tickerStatistics = symbolsStatisticAfter48h.get(order.symbol);
//        }
//        if (tickerStatistics != null) {
//            minPriceStatistic = tickerStatistics.minPrice;
//            rateMin = -Utils.rateOf2Double(tickerStatistics.minPrice, order.priceEntry);
//        }
        return order.symbol + "," + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart) + "," + order.side + ","
                + order.priceEntry + "," + order.priceTP + "," + order.lastPrice + ","
                + order.volume + "," + order.avgVolume24h + "," + order.rateChange + "," + orderState + ","
                + rateLoss + "," + Utils.rateOf2Double(order.minPrice, order.priceEntry)
                + "," + Utils.rateOf2Double(order.tickerClose.priceClose, order.tickerClose.priceOpen)
                + "," + order.maxPrice + "," + Utils.rateOf2Double(order.maxPrice, order.priceEntry)
                + "," + (order.timeUpdate - order.timeStart) / Utils.TIME_MINUTE + "," + order.dcaLevel;
//                + "," + minPriceStatistic + "," + rateMin;
    }

    List<String> detectBuyWithBreadBellow() {
        List<String> lines = new ArrayList<>();
        File[] symbolFiles = new File(DataManager.FOLDER_TICKER_15M).listFiles();
        Map<Long, MarketLevelChange> time2Level = (Map<Long, MarketLevelChange>) Storage.readObjectFromFile("target/time2marketLevel.data");
        List<OrderTargetInfoTest> orderTrades = new ArrayList<>();
        for (File symbolFile : symbolFiles) {
            String symbol = symbolFile.getName();
            if (!StringUtils.endsWithIgnoreCase(symbol, "usdt")
                    || Constants.diedSymbol.contains(symbol)
                    || Constants.specialSymbol.contains(symbol)
            ) {
                continue;
            }
//            LOG.info("Statistic of symbol: {}", symbol);
            List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(symbolFile.getPath());
            Long timeInitTrend4Hash = Utils.get4Hour(tickers.get(0).startTime.longValue()) + 4 * Utils.TIME_HOUR;
            try {
                for (int i = 1; i < tickers.size(); i++) {
                    KlineObjectNumber lastKline = tickers.get(i - 1);
                    KlineObjectNumber kline = tickers.get(i);
                    // remove command with market level
                    if (time2Level.containsKey(kline.startTime.longValue())) {
                        continue;
                    }
//                    Trend4hManager.getInstance(symbol, timeInitTrend4Hash).updateTicker(kline);
//                    OrderSide trend = Trend4hManager.getInstance(symbol, timeInitTrend4Hash).getCurrentTrend(kline);
//                    if (StringUtils.equals(symbol, "WLDUSDT")
//                            && Utils.sdfFileHour.parse("20240704 00:00").getTime() == kline.startTime.longValue()) {
//                        System.out.println("Debug");
//                    }
                    BreadDetectObject breadData = BreadFunctions.calBreadDataAltWithBtcTrend(kline);
//                    KlineObjectNumber ticker2Hours = TickerFuturesHelper.extractKlineByNumberTicker(tickers, i, 8);

                    if (
//                            MarketBigChangeDetectorTest.isCoupleTickerBuy(tickers, i)
                            MarketBigChangeDetectorTest.isSignalSELL(tickers, i)
//                            isReversePoint(tickers, i)
//                            breadData.breadAbove < 0.001
//                            && breadData.breadBelow >= 0.003
//                            && breadData.rateChange > 0.003
//                            && ticker2Hours != null
//                            kline.totalUsdt / lastKline.totalUsdt > 3
//                                    && Utils.rateOf2Double(kline.priceClose, kline.priceOpen) < -0.01
//                                    && Utils.rateOf2Double(kline.priceClose, kline.priceOpen) > -0.02
//                                    && trend != null && trend.equals(OrderSide.BUY)
//                            && Utils.rateOf2Double(ticker2Hours.maxPrice, kline.priceClose) < -0.03
                    ) {
//                        LOG.info("{} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(kline.startTime.longValue()));
                        lastBreadTrader = breadData;
                        try {
                            Double priceEntry = kline.priceClose;
                            breadData.orderSide = OrderSide.SELL;
                            Double priceTarget = getPriceTarget(priceEntry, breadData.orderSide, RATE_TARGET);
                            Double priceSTL = getPriceSL(priceEntry, breadData.orderSide, ALT_BREAD_BIGCHANE_STOPPLOSS);
                            OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry, priceTarget,
                                    1.0, 10, symbol, kline.startTime.longValue(), kline.startTime.longValue(),
                                    breadData.orderSide);
                            orderTrade.priceSL = priceSTL;
                            orderTrade.maxPrice = kline.priceClose;
                            orderTrade.minPrice = kline.minPrice;
                            orderTrade.rateBreadAbove = breadData.breadAbove;
                            orderTrade.rateBreadBelow = breadData.breadBelow;
                            orderTrade.rateChange = breadData.totalRate;
                            KlineObjectNumber ticker24h = TickerFuturesHelper.extractKline24hr(tickers, kline.startTime.longValue());
//                            orderTrade.avgVolume24h = TickerFuturesHelper.getAvgLastVolume7D(tickers, i);
                            orderTrade.avgVolume24h = ticker24h.totalUsdt / 1E6;
                            orderTrade.volume = kline.totalUsdt;

                            orderTrade.tickerOpen = kline;
                            orderTrade.tickerClose = ticker24h;
//                            orderTrade.lastMarketLevelChange = trend.toString();
//                            orderTrade.traderScore = TraderScoring.calScore(tickers, i);
                            int startCheck = i;
                            for (int j = startCheck + 1; j < tickers.size(); j++) {
                                KlineObjectNumber ticker = tickers.get(j);
                                if (orderTrade.timeStart + NUMBER_HOURS_STOP_MIN * Utils.TIME_HOUR < ticker.startTime.longValue()) {
                                    break;
                                }
//                                    i = j;
//                                    if (StringUtils.equals(symbol, "SPELLUSDT")
//                                            && Utils.sdfFileHour.parse("20240222 20:15").getTime() == ticker.startTime.longValue()) {
//                                        System.out.println("Debug");
//                                    }
                                orderTrade.lastPrice = ticker.priceClose;
                                orderTrade.timeUpdate = ticker.endTime.longValue();
                                if (orderTrade.maxPrice == null || ticker.maxPrice > orderTrade.maxPrice) {
                                    orderTrade.maxPrice = ticker.maxPrice;
                                }
                                if (orderTrade.minPrice == null || ticker.minPrice < orderTrade.minPrice) {
                                    orderTrade.minPrice = ticker.minPrice;
                                }
                                if (ticker.maxPrice > orderTrade.priceTP && ticker.minPrice < orderTrade.priceTP) {
                                    orderTrade.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                                    break;
                                }
                                if (orderTrade.side.equals(OrderSide.BUY)) {
                                    if (DcaHelper.isDcaOrderBuy(tickers, orderTrade, j)
                                            && (orderTrade.dcaLevel == null || orderTrade.dcaLevel < 1)
                                            && (ticker.startTime.longValue() - orderTrade.timeStart) >= 6 * Utils.TIME_HOUR) {
                                        orderTrade = DcaHelper.dcaOrder(orderTrade, ticker, RATE_TARGET);
                                    }
                                } else {
                                    Double rateLoss = Utils.rateOf2Double(ticker.priceClose, orderTrade.priceEntry);
                                    if (rateLoss >= 0.4) {
                                        orderTrade = DcaHelper.dcaOrder(orderTrade, ticker, RATE_TARGET);
                                    } else {
                                        if (DcaHelper.isDcaOrderSellWithEntry(tickers, orderTrade.priceEntry, j)
                                                && (orderTrade.dcaLevel == null || orderTrade.dcaLevel < 1)
                                        ) {
                                            orderTrade = DcaHelper.dcaOrder(orderTrade, ticker, RATE_TARGET);
                                        }
                                    }
                                }

                            }
                            if (orderTrade.status.equals(OrderTargetStatus.REQUEST)) {
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
        for (int minEntry = 1; minEntry < 2; minEntry++) {
            for (int numberOrder2Trade = 5; numberOrder2Trade < 6; numberOrder2Trade++) {
                // remove order by rule
                counterTotal = 0;
                counterSuccess = 0;
                counterDcaSuccess = 0;
                counterStoploss = 0;
                totalLoss = 0.0;
                List<OrderTargetInfoTest> orders = cleanOrder(orderTrades, numberOrder2Trade, minEntry);
//            List<OrderTargetInfoTest> orders = cleanOrder(orderTrades, null, minEntry);
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
                    Double pnl = (counterSuccess + counterDcaSuccess) * RATE_TARGET;
                    LOG.info("Result target:{} minEntry:{} numberOrder:{} {}-{}-{}%-{}/{} {}% pl: {}/{} {}%", RATE_TARGET, minEntry, numberOrder2Trade, counterSuccess, counterStoploss,
                            rateSuccessLoss.doubleValue() / 10, counterSuccess + counterStoploss, counterTotal,
                            rateSuccess.doubleValue() / 10, totalLoss.longValue(), pnl.longValue(), Utils.formatPercent(totalLoss / pnl));
                }
            }
        }
        return lines;
    }

//    public static OrderTargetInfoTest dcaOrder(OrderTargetInfoTest orderInfo, KlineObjectNumber ticker) {
//        Double entryNew = (orderInfo.priceEntry + orderInfo.lastPrice) / 2;
//        LOG.info("Dca for {} {} {} {} {}", orderInfo.symbol, orderInfo.priceEntry, entryNew,
//                Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart), Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
//        orderInfo.quantity *= 2;
//        orderInfo.priceEntry = entryNew;
//        Double priceTp = Utils.calPriceTarget(orderInfo.symbol, orderInfo.priceEntry, OrderSide.BUY, RATE_TARGET);
//        orderInfo.priceTP = priceTp;
//        orderInfo.maxPrice = ticker.priceClose;
//        orderInfo.minPrice = ticker.minPrice;
//        orderInfo.timeStart = ticker.startTime.longValue();
//        if (orderInfo.dcaLevel == null) {
//            orderInfo.dcaLevel = 0;
//        }
//        orderInfo.dcaLevel++;
//        return orderInfo;
//    }

//    public static boolean isDcaOrder(List<KlineObjectNumber> tickers, Double priceEntry, int index) {
//        KlineObjectNumber ticker = tickers.get(index);
//        // rate loss > 10%
//        Double rateLoss = Utils.rateOf2Double(ticker.priceClose, priceEntry);
//        if (rateLoss < -0.09) {
//            // ticker reverse
//            if (index > 1) {
//                KlineObjectNumber lastTicker = tickers.get(index - 1);
//                KlineObjectNumber ticker4h = TickerFuturesHelper.extractKlineByNumberTicker(tickers, index, 32);
//                if (ticker.priceClose > ticker.priceOpen
//                        && ticker.priceClose > lastTicker.priceOpen
//                        && ticker4h != null
//                        && (ticker.minPrice <= ticker4h.minPrice * 1.005 || lastTicker.minPrice <= ticker4h.minPrice * 1.005)
//                ) {
//                    return true;
//                }
//            }
//        }
//
//        return false;
//    }

    private boolean isReversePoint(List<KlineObjectNumber> tickers, int i) {
        if (i > 10) {
            KlineObjectNumber lastTicker = tickers.get(i - 1);
            KlineObjectNumber ticker = tickers.get(i);
            if (ticker.priceClose > lastTicker.maxPrice * 1.001) {
                Double totalRate = 0d;
                for (int j = i - 8; j < i; j++) {
                    KlineObjectNumber tickerCheck = tickers.get(j);
                    Double rateChange = Utils.rateOf2Double(tickerCheck.priceClose, tickerCheck.priceOpen);
                    totalRate += rateChange;
                    if (rateChange > 0.001) {
                        return false;
                    }
                }
                if (totalRate < -0.025) {
                    return true;
                }
            }
        }
        return false;
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


    private static void testDcaPoint() {
        File[] symbolFiles = new File(DataManager.FOLDER_TICKER_15M).listFiles();

        for (File symbolFile : symbolFiles) {
            String symbol = symbolFile.getName();
            if (!StringUtils.endsWithIgnoreCase(symbol, "usdt")
                    || Constants.diedSymbol.contains(symbol)
                    || Constants.specialSymbol.contains(symbol)
            ) {
                continue;
            }
            List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(symbolFile.getPath());
            for (int i = 0; i < tickers.size(); i++) {
                KlineObjectNumber ticker = tickers.get(i);
                OrderTargetInfoTest order = new OrderTargetInfoTest();
                order.priceEntry = ticker.priceClose * 1.015;
                if (DcaHelper.isDcaOrderBuy(tickers, order, i)) {
                    LOG.info("{} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), ticker.priceClose);
                }
            }
        }
    }

    public static void main(String[] args) throws ParseException {
//        testDcaPoint();
        new AltBreadBigChange15M().fixRateChangeAndVolume();
        System.exit(1);
    }
}
