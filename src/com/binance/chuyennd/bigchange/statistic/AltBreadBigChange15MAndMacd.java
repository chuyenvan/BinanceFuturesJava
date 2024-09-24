package com.binance.chuyennd.bigchange.statistic;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.indicators.SimpleMovingAverage1DManager;
import com.binance.chuyennd.movingaverage.MAStatus;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TrendState;
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
public class AltBreadBigChange15MAndMacd {

    public static final Logger LOG = LoggerFactory.getLogger(AltBreadBigChange15MAndMacd.class);
    private static final int NUMBER_HOURS_STOP_TRADE = Configs.getInt("NUMBER_HOURS_STOP_TRADE") * 4;
    public BreadDetectObject lastBreadTrader = null;
    public Long lastTimeBreadTrader = 0l;
    public Double RATE_BREAD_MIN_2TRADE = Configs.getDouble("RATE_BREAD_MIN_2TRADE");
    public final Double RATE_MA_MAX = Configs.getDouble("RATE_MA_MAX");
    public final Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
    public Double ALT_BREAD_BIGCHANGE_15M = 0.008;
    public Double ALT_BREAD_BIGCHANE_STOPPLOSS = 0.1;
    public Double RATE_CHANGE_WITHBREAD_2TRADING_TARGET = 0.009;
    public Integer counterTotal = 0;
    public Integer counterSuccess = 0;
    public Integer counterStoploss = 0;
    public Double totalLoss = 0d;
    public Map<String, Double> symbol2LastPrice = new HashMap<>();

    private void fixRateChangeAndVolume() throws ParseException {
        long start_time = Configs.getLong("start_time");

        // test for multi param
        try {
            List<String> lines = new ArrayList<>();
//            ArrayList<Double> rateSuccesses = new ArrayList<>(Arrays.asList(
////                    92.0,
////                    93.0,
//                    94.0));
            ArrayList<Integer> NUMBER_HOURS_TO_STOP = new ArrayList<>();
            for (int i = 3; i < 5; i++) {
                NUMBER_HOURS_TO_STOP.add(i);
            }
            int numberCheckMacdReverse = 10;
            for (Integer numberHourStopLoss : NUMBER_HOURS_TO_STOP) {
//                for (Double rateSuccess : rateSuccesses) {
//                    BreadFunctions.updateVolumeRateChange(numberHourStopLoss, rateSuccess);
                    lines.addAll(detectBigChangeWithVolumeFixRate(RATE_TARGET,
                            numberHourStopLoss * 4 * 12, numberCheckMacdReverse));
//                }
            }
//            printByDate(lines);
            FileUtils.writeLines(new File(AltBreadBigChange15MAndMacd.class.getSimpleName() + ".csv"), lines);

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
        for (OrderTargetInfoTest order : orders) {
            counterTotal++;
            if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                counterSuccess++;
                lines.add(buildLineTest(order, true, null));
            } else {
                double rateLoss = Utils.rateOf2Double(order.lastPrice, order.priceEntry);
                if (order.side.equals(OrderSide.BUY)) {
                    rateLoss = -rateLoss;
                }
                totalLoss += rateLoss;
                lines.add(buildLineTest(order, false, rateLoss));
            }
//            }
        }
        return lines;
    }


    private String buildLineTest(OrderTargetInfoTest order, boolean orderState, Double rateLoss) {
        MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(order.timeStart, order.symbol);
//        TrendState btcTrend1d = BTCMacdTrendManager.getInstance().getTrend(Constants.INTERVAL_1D, order.timeStart);
//        TrendState btcTrend4h = BTCMacdTrendManager.getInstance().getTrend(Constants.INTERVAL_4H, order.timeStart);
//        TrendState btcTrend1h = BTCMacdTrendManager.getInstance().getTrend(Constants.INTERVAL_1H, order.timeStart);
//        TrendState btcTrend15m = BTCMacdTrendManager.getInstance().getTrend(Constants.INTERVAL_15M, order.timeStart);
        return order.symbol + "," + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart) + "," + order.side + ","
                + order.priceEntry + "," + order.priceTP + "," + symbol2LastPrice.get(order.symbol) + ","
                + order.volume + "," + order.avgVolume24h + "," + order.rateChange + "," + orderState + ","
                + rateLoss + "," + order.maxPrice + "," + Utils.rateOf2Double(order.maxPrice, order.priceEntry)
                + "," + (order.timeUpdate - order.timeStart) / Utils.TIME_MINUTE + "," + maStatus + "," + order.rateBtc15m;
//                + "," + btcTrend1d + "," + btcTrend4h + "," + btcTrend1h + "," + btcTrend15m;
    }

    List<String> detectBigChangeWithVolumeFixRate(Double rateTarget, Integer NUMBER_TICKER_TO_TRADE, Integer numberTickerWaitMacdReverse) {
//        LOG.info("Number ticker check: {} {} minutes", NUMBER_TICKER_TO_TRADE, NUMBER_TICKER_TO_TRADE * 15);
        counterTotal = 0;
        counterSuccess = 0;
        counterStoploss = 0;
        totalLoss = 0d;
        List<String> lines = new ArrayList<>();

        File[] symbolFiles = new File(Configs.FOLDER_TICKER_15M).listFiles();

        for (File symbolFile : symbolFiles) {
            String symbol = symbolFile.getName();
            if (!StringUtils.endsWithIgnoreCase(symbol, "usdt")) {
                continue;
            }
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
//            LOG.info("Statistic of symbol: {}", symbol);
            List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(symbolFile.getPath());
            try {
                List<OrderTargetInfoTest> orders = new ArrayList<>();

                symbol2LastPrice.put(symbol, tickers.get(tickers.size() - 1).priceClose);
                for (int i = 0; i < tickers.size(); i++) {
                    KlineObjectNumber kline = tickers.get(i);
//                    if (StringUtils.equals(symbol, "HIGHUSDT")
//                            && kline.startTime.longValue() == Utils.sdfFileHour.parse("20240513 15:00").getTime()) {
//                        System.out.println("Debug");
//                    }
                    BreadDetectObject breadData = BreadFunctions.calBreadDataAltWithBtcTrend(tickers, i, RATE_BREAD_MIN_2TRADE);
                    Double rateChange = BreadFunctions.getRateChangeWithVolume(kline.totalUsdt / 1E6);
                    if (rateChange == null) {
//                        LOG.info("Error rateChange with ticker: {} {}", symbol, Utils.toJson(kline));
                        continue;
                    } else {
//                        LOG.info("RateAndVolume {} -> {}", kline.totalUsdt, rateChange);
                    }
                    MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(kline.startTime.longValue(), symbol);
                    Double maValue = SimpleMovingAverage1DManager.getInstance().getMaValue(symbol, Utils.getDate(kline.startTime.longValue()));
                    Double rateMa = Utils.rateOf2Double(kline.priceClose, maValue);
                    Double rsi = TickerFuturesHelper.calRSI(tickers, i, 14);
                    TrendState btcTrendHour = BTCMacdTrendManager.getInstance().getTrend(Constants.INTERVAL_1H, kline.startTime.longValue());
                    if (breadData.orderSide != null
                            && breadData.orderSide.equals(OrderSide.BUY)
                            && maStatus != null && maStatus.equals(MAStatus.TOP)
                            && rateMa < RATE_MA_MAX
                            && btcTrendHour != null && (btcTrendHour.equals(TrendState.STRONG_UP) || btcTrendHour.equals(TrendState.UP))
                            // new entry >= ma20 15m
//                            && kline.priceClose < kline.ma20
                            && breadData.totalRate >= rateChange) {
                        lastBreadTrader = breadData;
                        try {
                            KlineObjectNumber nextKline = tickers.get(i + 1);
                            int startWait = i;
                            Integer indexTrade = null;
                            // wait macd reverse || ticker next is incre
//                            if (Utils.rateOf2Double(nextKline.priceClose, nextKline.priceOpen) > 0.005
////                                    && Utils.rateOf2Double(kline.priceOpen, nextKline.priceClose) >= 0.02
//                            ) {
//                                indexTrade = i + 1;
//                            } else {
                            for (int j = startWait + 1; j < startWait + numberTickerWaitMacdReverse; j++) {
                                if (j < tickers.size()) {
                                    KlineObjectNumber lastTicker = tickers.get(j - 1);
                                    KlineObjectNumber ticker = tickers.get(j);
                                    if (ticker.histogram > lastTicker.histogram
                                            && ticker.histogram < 0
                                            && Utils.rateOf2Double(kline.priceOpen, ticker.priceClose) >= 0.02) {
                                        indexTrade = j;
                                        break;
                                    }
                                }
                            }
//                            }
//                            if (indexTrade == null){
//                                LOG.info("{} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(kline.startTime.longValue()));
//                            }
                            if (indexTrade != null) {
                                i = indexTrade;
                                kline = tickers.get(i);
                                // end wait
                                Double priceEntry = kline.priceClose;
                                Double priceTarget = getPriceTarget(priceEntry, breadData.orderSide, rateTarget);
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
                                orderTrade.avgVolume24h = TickerFuturesHelper.getAvgLastVolume7D(tickers, i);
                                orderTrade.volume = kline.totalUsdt;
                                orderTrade.rateBtc15m = rsi;
                                int startCheck = i;
                                for (int j = startCheck + 1; j < startCheck + NUMBER_TICKER_TO_TRADE; j++) {
                                    if (j < tickers.size()) {
                                        i = j;
                                        KlineObjectNumber ticker = tickers.get(j);
                                        orderTrade.lastPrice = ticker.priceClose;
                                        if (orderTrade.maxPrice == null || ticker.maxPrice > orderTrade.maxPrice) {
                                            orderTrade.maxPrice = ticker.maxPrice;
                                            orderTrade.timeUpdate = ticker.endTime.longValue();
                                        }
                                        if (ticker.maxPrice > orderTrade.priceTP && ticker.minPrice < orderTrade.priceTP) {
                                            orderTrade.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                                            orderTrade.timeUpdate = ticker.endTime.longValue();
                                            break;
                                        }
                                    }
                                }
                                if (orderTrade.status.equals(OrderTargetStatus.REQUEST)) {
                                    orderTrade.status = OrderTargetStatus.POSITION_RUNNING;
                                }
                                orders.add(orderTrade);
                            }
                        } catch (Exception e) {
                            LOG.info("Error: {}", Utils.toJson(kline));
                            e.printStackTrace();
                        }
                    }

                }
                if (!orders.isEmpty()) {
                    lines.addAll(printResultTradeTest(orders));
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
        Double pnl = counterSuccess * rateTarget;
        LOG.info("Result All:numberHour2Trade:{} hours rateTarget:{}  {}-{}-{}%-{}/{} {}% pl: {}/{} {}%", NUMBER_TICKER_TO_TRADE / 4, rateTarget,
                counterSuccess, counterStoploss, rateSuccessLoss.doubleValue() / 10, counterSuccess + counterStoploss,
                counterTotal, rateSuccess.doubleValue() / 10, totalLoss.longValue(), pnl.longValue(),
                Utils.formatPercent(totalLoss / pnl));
        return lines;
    }

    public static void main(String[] args) throws ParseException {
        new AltBreadBigChange15MAndMacd().fixRateChangeAndVolume();
        System.exit(1);
    }

}
