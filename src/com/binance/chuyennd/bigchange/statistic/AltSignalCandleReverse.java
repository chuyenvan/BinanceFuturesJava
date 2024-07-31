package com.binance.chuyennd.bigchange.statistic;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
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
public class AltSignalCandleReverse {

    public static final Logger LOG = LoggerFactory.getLogger(AltSignalCandleReverse.class);
    private static final int NUMBER_HOURS_STOP_MIN = Configs.getInt("NUMBER_HOURS_STOP_MIN");
    private static final int RATE_TARGETS = Configs.getInt("RATE_TARGETS");
    private static final Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
    public Integer counterTotal = 0;
    public Integer counterSuccess = 0;
    public Integer counterStoploss = 0;
    public Double totalLoss = 0d;


    private void multiStatisticAltReverse15m() throws ParseException {

//        long start_time = Configs.getLong("start_time");
        // test for multi param
        try {
            List<String> lines = new ArrayList<>();
            ArrayList<Double> rateTargets = new ArrayList<>(Arrays.asList());
            for (int i = 0; i < RATE_TARGETS; i++) {
                rateTargets.add(RATE_TARGET + i * 0.01);
            }
            for (Double target : rateTargets) {
                lines.addAll(detectAltReverseAfterTopDown(target));
            }
            FileUtils.writeLines(new File(AltSignalCandleReverse.class.getSimpleName() + ".csv"), lines);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void multiStatisticAltTopMa20() throws ParseException {

//        long start_time = Configs.getLong("start_time");
        // test for multi param
        try {
            List<String> lines = new ArrayList<>();
            ArrayList<Double> rateTargets = new ArrayList<>(Arrays.asList());
            for (int i = 0; i < RATE_TARGETS; i++) {
                rateTargets.add(RATE_TARGET + i * 0.01);
            }
            for (Double target : rateTargets) {
                lines.addAll(detectAltTopMa20(target));
            }
            FileUtils.writeLines(new File(AltSignalCandleReverse.class.getSimpleName() + ".csv"), lines);

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
                + "," + order.priceEntry + "," + order.priceTP + "," + order.side + "," + order.lastPrice + "," +
                order.volume + "," + order.rsi14 + "," + order.status + "," + rateLoss + "," +
                order.maxPrice + "," + Utils.rateOf2Double(order.maxPrice, order.priceEntry) + "," +
                order.minPrice + "," + Utils.rateOf2Double(order.minPrice, order.priceEntry) + ","
                + (order.timeUpdate - order.timeStart) / Utils.TIME_MINUTE;
    }


    List<String> detectAltReverseAfterTopDown(Double target) {

        List<String> lines = new ArrayList<>();
        File[] symbolFiles = new File(DataManager.FOLDER_TICKER_15M).listFiles();
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
                for (int i = 0; i < tickers.size(); i++) {
                    KlineObjectNumber kline = tickers.get(i);
                    if (StringUtils.equals(symbol, "TAOUSDT")
                            && kline.startTime.longValue() == Utils.sdfFileHour.parse("20240705 19:15").getTime()) {
                        System.out.println("Debug");
                    }

//                    if (MarketBigChangeDetectorTest.getStatusTradingAlt15M(tickers, i) == 1
                    OrderSide orderSide = MarketBigChangeDetectorTest.isAltVolumeReverse(tickers, i);
                    if (orderSide != null
                    ) {
//                        LOG.info("{} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(kline.startTime.longValue()), orderSide);
                        try {
                            Double priceEntry = kline.priceClose;
                            Double priceTarget = getPriceTarget(priceEntry, orderSide, target);
                            OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry,
                                    priceTarget, 1.0, 10, symbol, kline.startTime.longValue(),
                                    kline.startTime.longValue(), orderSide);

                            orderTrade.maxPrice = kline.priceClose;
                            orderTrade.minPrice = kline.minPrice;
                            orderTrade.volume = kline.totalUsdt;
                            orderTrade.rsi14 = kline.rsi;
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
        for (int minEntry = 5; minEntry < 6; minEntry++) {
            for (int numberOrder2Trade = 4; numberOrder2Trade < 5; numberOrder2Trade++) {
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
                    Double pnl = counterSuccess * target;
                    LOG.info("Result target:{} minEntry:{} numberOrder:{} {}-{}-{}%-{}/{} {}% pl: {}/{} {}%", target, minEntry, numberOrder2Trade, counterSuccess, counterStoploss,
                            rateSuccessLoss.doubleValue() / 10, counterSuccess + counterStoploss, counterTotal,
                            rateSuccess.doubleValue() / 10, totalLoss.longValue(), pnl.longValue(), Utils.formatPercent(totalLoss / pnl));
                }
            }
        }
        return lines;
    }

    List<String> detectAltReverseAfterTopDown1h(Double target) {

        List<String> lines = new ArrayList<>();
        File[] symbolFiles = new File(DataManager.FOLDER_TICKER_HOUR).listFiles();
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
                for (int i = 0; i < tickers.size(); i++) {
                    KlineObjectNumber kline = tickers.get(i);
//                    if (StringUtils.equals(symbol, "REZUSDT") && kline.startTime.longValue()
//                            == Utils.sdfFileHour.parse("20240505 01:00").getTime()) {
//                        System.out.println("Debug");
//                    }

                    if (MarketBigChangeDetectorTest.getStatusTradingAlt1H(tickers, i) == 1
                    ) {
                        try {
                            Double priceEntry = kline.priceClose;
                            Double priceTarget = getPriceTarget(priceEntry, OrderSide.BUY, target);
                            OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry,
                                    priceTarget, 1.0, 10, symbol, kline.startTime.longValue(),
                                    kline.startTime.longValue(), OrderSide.BUY);

                            orderTrade.maxPrice = kline.priceClose;
                            orderTrade.minPrice = kline.minPrice;
                            orderTrade.volume = kline.totalUsdt;
                            orderTrade.rsi14 = kline.rsi;
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
        for (int minEntry = 10; minEntry < 11; minEntry++) {
            for (int numberOrder2Trade = 2; numberOrder2Trade < 3; numberOrder2Trade++) {
                // remove order by rule
                counterTotal = 0;
                counterSuccess = 0;
                counterStoploss = 0;
                totalLoss = 0.0;
                List<OrderTargetInfoTest> orders = cleanOrder(orderTrades, numberOrder2Trade, minEntry);

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
        return lines;
    }

    List<String> detectAltTopMa20(Double target) {

        List<String> lines = new ArrayList<>();
        File[] symbolFiles = new File(DataManager.FOLDER_TICKER_15M).listFiles();
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
                for (int i = 1; i < tickers.size(); i++) {

                    KlineObjectNumber lastKline = tickers.get(i - 1);
                    KlineObjectNumber kline = tickers.get(i);
//                    if (StringUtils.equals(symbol, "REZUSDT") && kline.startTime.longValue()
//                            == Utils.sdfFileHour.parse("20240505 01:00").getTime()) {
//                        System.out.println("Debug");
//                    }

                    if (lastKline.rsi != null
                            && kline.rsi > lastKline.rsi
                    ) {
                        try {
                            Double priceEntry = kline.priceClose;
                            Double priceTarget = getPriceTarget(priceEntry, OrderSide.BUY, target);
                            OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry,
                                    priceTarget, 1.0, 10, symbol, kline.startTime.longValue(),
                                    kline.startTime.longValue(), OrderSide.BUY);

                            orderTrade.maxPrice = kline.priceClose;
                            orderTrade.minPrice = kline.minPrice;
                            orderTrade.volume = kline.totalUsdt;
                            orderTrade.rsi14 = kline.rsi;
                            orderTrade.lastPrice = kline.priceClose;
                            orderTrade.tickerOpen = kline;
                            if (i > 1) {
                                orderTrade.tickerClose = tickers.get(i - 1);
                            }
                            int startCheck = i;
                            for (int j = startCheck + 1; j < tickers.size(); j++) {
//                                i = j;
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
        for (int minEntry = 10; minEntry < 11; minEntry++) {
            for (int numberOrder2Trade = 1; numberOrder2Trade < 2; numberOrder2Trade++) {
                // remove order by rule
                counterTotal = 0;
                counterSuccess = 0;
                counterStoploss = 0;
                totalLoss = 0.0;
                List<OrderTargetInfoTest> orders = cleanOrderMa20(orderTrades, numberOrder2Trade, minEntry);

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
                    if (counter >= numberOrder) {
                        break;
                    }
                }
            }
        }
        return orderResult;
    }

    private List<OrderTargetInfoTest> cleanOrderMa20(List<OrderTargetInfoTest> orders, Integer numberOrder, Integer minEntry) {
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
//                        Double rateChangeVolume = Utils.rateOf2Double(order.tickerOpen.ma20, order.tickerClose.ma20);
                    Double rateChangeVolume = Utils.rateOf2Double(order.tickerClose.rsi, order.tickerOpen.rsi);
//                    Double rateChangeVolume = Utils.rateOf2Double(order.tickerOpen.priceClose, order.tickerOpen.priceOpen);
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

    private void multiStatisticAltReverse1h() {

//        long start_time = Configs.getLong("start_time");
        // test for multi param
        try {
            List<String> lines = new ArrayList<>();
            ArrayList<Double> rateTargets = new ArrayList<>(Arrays.asList());
            for (int i = 0; i < RATE_TARGETS; i++) {
                rateTargets.add(RATE_TARGET + i * 0.01);
            }
            for (Double target : rateTargets) {
                lines.addAll(detectAltReverseAfterTopDown1h(target));
            }
            FileUtils.writeLines(new File(AltSignalCandleReverse.class.getSimpleName() + ".csv"), lines);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static void updateRateChangeAvg2Ma20(List<KlineObjectNumber> altTickers, Integer index) {
        try {
            if (index < 100) {
                return;
            }
            Double priceChange = 0d;
            for (int i = 0; i < 100; i++) {
                KlineObjectNumber kline = altTickers.get(index - i);
                priceChange += Utils.rateOf2Double(kline.priceClose, kline.priceOpen);
            }
            altTickers.get(index).ma20 = priceChange;
        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    private static void testSignalChuyennd() {
        List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(DataManager.FOLDER_TICKER_15M + "TAOUSDT");
        try {
            for (int i = 0; i < tickers.size(); i++) {
                updateRateChangeAvg2Ma20(tickers, i);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
//        prinDataRateChangeAvg(tickers);
        for (int i = 0; i < tickers.size(); i++) {
            OrderSide side = null;
            KlineObjectNumber ticker;
            for (int j = 0; j < 100; j++) {
                if (i - j < 0) {
                    break;
                }
                ticker = tickers.get(i - j);
                if (ticker.ma20 * 100 <= -5) {
                    for (int k = 0; k < 10; k++) {
                        KlineObjectNumber lastTicker = tickers.get(i - j - k);
                        if (lastTicker.ma20 < ticker.ma20 && tickers.get(i).ma20 * 100 < 5) {
                            side = OrderSide.BUY;
                            break;
                        }
                    }
                    if (side != null) {
                        break;
                    }
                }
                if (ticker.ma20 * 100 >= 5) {
                    for (int k = 0; k < 10; k++) {
                        KlineObjectNumber lastTicker = tickers.get(i - j - k);
                        if (lastTicker.ma20 > ticker.ma20 && tickers.get(i).ma20 * 100 > -5) {
                            side = OrderSide.SELL;
                            break;
                        }
                    }
                    if (side != null) {
                        break;
                    }
                }
            }
            ticker = tickers.get(i);
            LOG.info("{} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), ticker.ma20 * 100, side);
        }
    }


    private static void printDataRateChangeAvg(List<KlineObjectNumber> tickers) {
        for (int i = 0; i < tickers.size(); i++) {
            KlineObjectNumber ticker = tickers.get(i);
            LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), ticker.ma20 * 100);
        }
    }

    public static void main(String[] args) throws ParseException {
        new AltSignalCandleReverse().multiStatisticAltReverse15m();
//        testSignalChuyennd();
//        new AltSignalCandleReverse().multiStatisticAltReverse1h();
//        new AltSignalCandleReverse().multiStatisticAltTopMa20();
        System.exit(1);
    }


}
