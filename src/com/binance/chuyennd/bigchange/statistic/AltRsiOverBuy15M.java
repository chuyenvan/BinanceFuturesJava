package com.binance.chuyennd.bigchange.statistic;

import com.binance.chuyennd.indicators.RelativeStrengthIndex;
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
public class AltRsiOverBuy15M {

    public static final Logger LOG = LoggerFactory.getLogger(AltRsiOverBuy15M.class);
    private static final int NUMBER_HOURS_STOP_TRADE = Configs.getInt("NUMBER_HOURS_STOP_TRADE") * 4;

    public Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
    public Integer counterTotal = 0;
    public Integer counterSuccess = 0;
    public Integer counterStoploss = 0;
    public Double totalLoss = 0d;
    public Map<String, Double> symbol2LastPrice = new HashMap<>();


    private void multiRsiAndRateMa() throws ParseException {

        // test for multi param
        try {

            List<String> lines = new ArrayList<>();
            ArrayList<Double> maMaxes = new ArrayList<>(Arrays.asList());
            for (int i = 0; i < 1; i++) {
                maMaxes.add(0.1 + i * 0.01);
            }

            for (Double maMax : maMaxes) {
                lines.addAll(detectBigChangeWithParamNew(maMax));
            }

            FileUtils.writeLines(new File(AltRsiOverBuy15M.class.getSimpleName() + ".csv"), lines);

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
                lines.add(buildLineTest(order, true, null));
            } else {
                if (order.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                    counterStoploss++;
                } else {
                    double rateLoss = Utils.rateOf2Double(order.lastPrice, order.priceEntry);
                    if (order.side.equals(OrderSide.BUY)) {
                        rateLoss = -rateLoss;
                    }
                    totalLoss += rateLoss;
                    lines.add(buildLineTest(order, false, rateLoss));
                }

            }
//            }
        }
        return lines;
    }


    private String buildLineTest(OrderTargetInfoTest order, boolean orderState, Double rateLoss) {
        MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(order.timeStart, order.symbol);
        return order.symbol + "," + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart) + "," + order.side + ","
                + order.priceEntry + "," + order.priceTP + "," + symbol2LastPrice.get(order.symbol)
                + "," + order.volume + "," + order.avgVolume24h + "," + order.rateChange
                + "," + orderState + "," + rateLoss + "," + order.maxPrice + ","
                + Utils.rateOf2Double(order.maxPrice, order.priceEntry) + "," + (order.timeUpdate - order.timeStart) / Utils.TIME_MINUTE
                + "," + maStatus + "," + order.rsi14;
    }


    List<String> detectBigChangeWithParamNew(Double maMax) {
        counterTotal = 0;
        counterSuccess = 0;
        counterStoploss = 0;
        totalLoss = 0.0;

        List<String> lines = new ArrayList<>();
        for (File file : new File(DataManager.FOLDER_TICKER_15M).listFiles()) {
//            LOG.info("{} {}", file.getName(), file.getPath());
            String symbol = file.getName();
            if (Constants.diedSymbol.contains(symbol) || !StringUtils.containsIgnoreCase(symbol, "usdt")) {
                continue;
            }
            List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(file.getPath());
            LOG.info("Statistic for {}!", symbol);
            try {
                List<OrderTargetInfoTest> orders = new ArrayList<>();
                symbol2LastPrice.put(symbol, tickers.get(tickers.size() - 1).priceClose);
                for (int i = 14; i < tickers.size(); i++) {
                    KlineObjectNumber kline = tickers.get(i);
                    MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(kline.startTime.longValue(), symbol);
                    Double maValue = SimpleMovingAverage1DManager.getInstance().getMaValue(symbol, Utils.getDate(kline.startTime.longValue()));
                    Double rateMa = Utils.rateOf2Double(kline.priceClose, maValue);
                    if (RelativeStrengthIndex.isRsiSignalBuy(tickers, i)
                            && rateMa < maMax
                            && maStatus != null && maStatus.equals(MAStatus.TOP)) {
                        try {
                            Double priceEntry = kline.priceClose;
                            Double priceTarget = getPriceTarget(priceEntry, OrderSide.BUY, RATE_TARGET);
                            OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry, priceTarget, 1.0, 10, symbol, kline.startTime.longValue(), kline.startTime.longValue(), OrderSide.BUY);

                            orderTrade.maxPrice = kline.maxPrice;
                            orderTrade.minPrice = kline.minPrice;
                            orderTrade.volume = kline.totalUsdt;
                            orderTrade.lastPrice = kline.priceClose;

                            int startCheck = i;
                            for (int j = startCheck + 1; j < startCheck + NUMBER_HOURS_STOP_TRADE; j++) {
                                if (j < tickers.size()) {
                                    i = j;
                                    KlineObjectNumber ticker = tickers.get(j);
                                    orderTrade.lastPrice = ticker.priceClose;
                                    if (ticker.maxPrice > orderTrade.priceTP && ticker.minPrice < orderTrade.priceTP) {
                                        orderTrade.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                                        break;
                                    }
                                }
                            }
                            if (!orderTrade.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                                orderTrade.status = OrderTargetStatus.POSITION_RUNNING;
                            }
                            orders.add(orderTrade);
                        } catch (Exception e) {
                            LOG.info("Error: {}", Utils.toJson(kline));
                            e.printStackTrace();
                        }
                    }

                }
                if (!orders.isEmpty()) {
                    lines.addAll(printResultTradeTest(orders));
                } else {
//                                    LOG.info("Symbol not map: {} {}", symbol, tickers.size());
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
            LOG.info("Result  maMax:{} {}-{}-{}%-{}/{} {}% pl: {}/{} {}%", maMax, counterSuccess, counterStoploss, rateSuccessLoss.doubleValue() / 10, counterSuccess + counterStoploss, counterTotal, rateSuccess.doubleValue() / 10, totalLoss.longValue(), pnl.longValue(), Utils.formatPercent(totalLoss / pnl));
        }
        return lines;
    }

    public static void main(String[] args) throws ParseException {
        new AltRsiOverBuy15M().multiRsiAndRateMa();
        System.exit(1);
    }

}
