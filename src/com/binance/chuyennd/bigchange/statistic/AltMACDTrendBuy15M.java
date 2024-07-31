package com.binance.chuyennd.bigchange.statistic;

import com.binance.chuyennd.indicators.MACDTradingController;
import com.binance.chuyennd.indicators.SimpleMovingAverage1DManager;
import com.binance.chuyennd.movingaverage.MAStatus;
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
public class AltMACDTrendBuy15M {

    public static final Logger LOG = LoggerFactory.getLogger(AltMACDTrendBuy15M.class);
    private static final int NUMBER_HOURS_STOP_TRADE = Configs.getInt("NUMBER_HOURS_STOP_TRADE") * 4;
    public Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
    public Double RATE_MA_MAX = Configs.getDouble("RATE_MA_MAX");
    public Integer counterTotal = 0;
    public Integer counterSuccess = 0;
    public Integer counterStoploss = 0;
    public Double totalLoss = 0d;


    private void multiRsiAndRateMa() throws ParseException {

        long start_time = Configs.getLong("start_time");
        // test for multi param
        try {
            List<String> lines = new ArrayList<>();
//            ArrayList<Double> maMaxes = new ArrayList<>(Arrays.asList());
//            for (int i = 0; i < 1; i++) {
//                maMaxes.add(0.25 + i * 0.02);
//            }
//            for (Double maMax : maMaxes) {
            lines.addAll(detectBigChangeWithParamNew(RATE_MA_MAX));
//            }
            FileUtils.writeLines(new File(AltMACDTrendBuy15M.class.getSimpleName() + ".csv"), lines);

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
        MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(order.timeStart, order.symbol);
        return order.symbol + "," + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart) + "," + Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate)
                + "," + order.priceEntry + "," + order.priceTP + "," + order.lastPrice
                + "," + order.volume + "," + order.rsi14
                + "," + order.status + "," + rateLoss + "," + order.maxPrice + ","
                + Utils.rateOf2Double(order.maxPrice, order.priceEntry) + "," + (order.timeUpdate - order.timeStart) / Utils.TIME_MINUTE
                + "," + maStatus;
    }


    List<String> detectBigChangeWithParamNew(Double maMax) {
        counterTotal = 0;
        counterSuccess = 0;
        counterStoploss = 0;
        totalLoss = 0.0;

        List<String> lines = new ArrayList<>();
        File[] symbolFiles = new File(DataManager.FOLDER_TICKER_15M).listFiles();
        int counter = 0;
        for (File symbolFile : symbolFiles) {
            String symbol = symbolFile.getName();
            counter++;
            LOG.info("Statistic of: {} {}/{}", symbol, counter, symbolFiles.length);
            if (!StringUtils.endsWithIgnoreCase(symbol, "usdt")) {
                continue;
            }
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }

            List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(symbolFile.getPath());
            try {
                List<OrderTargetInfoTest> orders = new ArrayList<>();
                for (int i = 0; i < tickers.size(); i++) {
                    KlineObjectNumber kline = tickers.get(i);
                    try {
//                        DataManager.getInstance().updateData(kline, symbol);
//                        KlineObjectNumber lastTicker1H = DataManager.getInstance().getTicker(symbol, Constants.INTERVAL_1H,
//                                Utils.getHour(kline.startTime.longValue()) - Utils.TIME_HOUR);
//                        KlineObjectNumber ticker1H = DataManager.getInstance().getTicker(symbol, Constants.INTERVAL_1H,
//                                Utils.getHour(kline.startTime.longValue()));
//                        KlineObjectNumber lastTicker4H = DataManager.getInstance().getTicker(symbol, Constants.INTERVAL_4H,
//                                Utils.get4Hour(kline.startTime.longValue()) - 4 * Utils.TIME_HOUR);
//                        KlineObjectNumber ticker4H = DataManager.getInstance().getTicker(symbol, Constants.INTERVAL_4H,
//                                Utils.get4Hour(kline.startTime.longValue()));
//                        KlineObjectNumber lastTicker1d = DataManager.getInstance().getTicker(symbol, Constants.INTERVAL_1D,
//                                Utils.getDate(kline.startTime.longValue()) - Utils.TIME_DAY);
//                        KlineObjectNumber ticker1d = DataManager.getInstance().getTicker(symbol, Constants.INTERVAL_1D,
//                                Utils.getDate(kline.startTime.longValue()));
                        MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(kline.startTime.longValue(), symbol);
                        Double maValue = SimpleMovingAverage1DManager.getInstance().getMaValue(symbol, Utils.getDate(kline.startTime.longValue()));
                        if (maValue == null) {
                            continue;
                        }

                        if (MACDTradingController.isMacdCutUpSignalFirst(tickers, i)
                                && maStatus != null && !maStatus.equals(MAStatus.UNDER)
//                                && lastTicker1H != null && ticker1H != null && ticker1H.histogram > lastTicker1H.histogram
//                                && lastTicker4H != null && ticker4H != null && ticker4H.histogram > lastTicker4H.histogram
//                                && lastTicker1d != null && lastTicker1d != null && lastTicker1d.histogram != null
//                                && ticker1d.histogram > lastTicker1d.histogram

                        ) {
                            Double priceEntry = kline.priceClose;
                            Double priceTarget = getPriceTarget(priceEntry, OrderSide.BUY, RATE_TARGET);
                            OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry,
                                    priceTarget, 1.0, 10, symbol, kline.startTime.longValue(), kline.startTime.longValue(), OrderSide.BUY);

                            orderTrade.maxPrice = kline.priceClose;
                            orderTrade.minPrice = kline.minPrice;
                            orderTrade.volume = kline.totalUsdt;
                            orderTrade.rsi14 = kline.rsi;
                            orderTrade.lastPrice = kline.priceClose;

                            int startCheck = i;
                            for (int j = startCheck + 1; j < startCheck + NUMBER_HOURS_STOP_TRADE; j++) {
                                if (j < tickers.size()) {
                                    i = j;
                                    KlineObjectNumber ticker = tickers.get(j);
                                    orderTrade.lastPrice = ticker.priceClose;
                                    orderTrade.timeUpdate = ticker.startTime.longValue();
                                    if (ticker.maxPrice > orderTrade.priceTP && ticker.minPrice < orderTrade.priceTP) {
                                        orderTrade.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                                        break;
                                    }
                                    if (orderTrade.maxPrice > ticker.maxPrice) {
                                        orderTrade.maxPrice = ticker.maxPrice;
                                    }
//                                    if (MACDTradingController.isMacdStopTrendBuyNew(tickers, j, orderTrade.timeStart)) {
//                                        orderTrade.status = OrderTargetStatus.STOP_LOSS_DONE;
//                                        break;
//                                    }
                                }
                            }
                            if (!orderTrade.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                                    && !orderTrade.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                                orderTrade.status = OrderTargetStatus.POSITION_RUNNING;
                            }
                            orders.add(orderTrade);
                        }
                    } catch (Exception e) {
                        LOG.info("Error: {}", Utils.toJson(kline));
                        e.printStackTrace();
                    }
                }
                if (!orders.isEmpty()) {
                    lines.addAll(printResultTradeTest(orders));
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            try {
                FileUtils.writeLines(new File(AltMACDTrendBuy15M.class.getSimpleName() + ".csv"), lines);
                if (counterSuccess > 0) {
                    Integer rateSuccess = 0;
                    Integer rateSuccessLoss = 0;

                    if (counterTotal != 0) {
                        rateSuccess = counterSuccess * 1000 / counterTotal;
                    }

                    if (counterSuccess != 0) {
                        rateSuccessLoss = counterStoploss * 1000 / counterSuccess;
                    }
                    Double pnl = counterSuccess * RATE_TARGET;
                    LOG.info("Result maMax:{} {}-{}-{}%-{}/{} {}% pl: {}/{} {}%", maMax, counterSuccess, counterStoploss,
                            rateSuccessLoss.doubleValue() / 10, counterSuccess + counterStoploss, counterTotal,
                            rateSuccess.doubleValue() / 10, totalLoss.longValue(), pnl.longValue(),
                            Utils.formatPercent(totalLoss / pnl));
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
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
            LOG.info("Result maMax:{} {}-{}-{}%-{}/{} {}% pl: {}/{} {}%", maMax, counterSuccess, counterStoploss,
                    rateSuccessLoss.doubleValue() / 10, counterSuccess + counterStoploss, counterTotal,
                    rateSuccess.doubleValue() / 10, totalLoss.longValue(), pnl.longValue(),
                    Utils.formatPercent(totalLoss / pnl));
        }
        return lines;
    }

    public static void main(String[] args) throws ParseException {
        new AltMACDTrendBuy15M().multiRsiAndRateMa();
        System.exit(1);
    }

}
