package com.binance.chuyennd.bigchange.statistic;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
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
public class AltBreadBigChange15MStopLoss {

    public static final Logger LOG = LoggerFactory.getLogger(AltBreadBigChange15MStopLoss.class);

    public BreadDetectObject lastBreadTrader = null;
    //    public Integer NUMBER_TICKER_TO_TRADE = Configs.getInt("NUMBER_DAY_2TRADE") * 96;
    public Long lastTimeBreadTrader = 0l;
    public Double RATE_BREAD_MIN_2TRADE = Configs.getDouble("RATE_BREAD_MIN_2TRADE");
    public Double ALT_BREAD_BIGCHANE_STOPPLOSS = 0.1;
    public Integer counterTotal = 0;
    public Integer counterSuccess = 0;
    public Double counterStoploss = 0.0;
    public String FOLDER_TICKER_15M = "storage/ticker/symbols-15m/";
    public Map<String, Double> symbol2LastPrice = new HashMap<>();

    private void startDetectBigChangeVolumeMiniInterval15MDataMongo() throws ParseException {
        Set<Double> btcBigChangeTimes = new HashSet<>();
        long start_time = Configs.getLong("start_time");
        // test for multi param
        try {
            ArrayList<Integer> max_ticker_trades = new ArrayList<>(Arrays.asList(
                    20, 25, 30
            ));

            ArrayList<Double> volumes = new ArrayList<>(Arrays.asList(
                    0.4,
                    0.5,
                    0.6,
                    0.7,
                    0.8,
                    0.9,
                    1.0,
                    1.2,
                    1.4,
                    1.6,
                    1.8,
                    2.0,
                    5.0,
                    10.0
            ));


            ArrayList<Double> listRateChanges = new ArrayList<>(Arrays.asList(
                    0.025,
                    0.028,
                    0.03,
                    0.032,
                    0.036,
                    0.040,
                    0.12
            ));
            List<String> lines = new ArrayList<>();
            List<Double> targets = new ArrayList<>();
//            targets.add(0.02);
//            targets.add(0.025);
//            targets.add(0.03);
            targets.add(0.035);
            targets.add(0.04);
            targets.add(0.045);

            Map<String, List<KlineObjectNumber>> symbol2Tickers = readData(start_time);
            for (Integer max_ticker_trader : max_ticker_trades) {
                for (Double volume : volumes) {
                    for (Double rateChange : listRateChanges) {
                        for (Double target : targets) {
                            lines.addAll(detectBigChangeWithParamNew(target, rateChange, symbol2Tickers, volume, max_ticker_trader));
                        }
                    }
                }
            }
//            printByDate(lines);
            FileUtils.writeLines(new File("failTradeWithVolume.csv"), lines);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }


    private Map<String, List<KlineObjectNumber>> readData(long startTime) {
        Map<String, List<KlineObjectNumber>> symbol2Tickers = null;
        String fileName = FOLDER_TICKER_15M + startTime + ".data";
        File fileDataAll = new File(fileName);
        if (fileDataAll.exists() && fileDataAll.lastModified() > Utils.getStartTimeDayAgo(1)) {
            symbol2Tickers = (Map<String, List<KlineObjectNumber>>) Storage.readObjectFromFile(fileName);
        }
        if (symbol2Tickers == null) {
            symbol2Tickers = readFromFileSymbol(startTime);
            Storage.writeObject2File(fileName, symbol2Tickers);
        }
        return symbol2Tickers;
    }

    private Map<String, List<KlineObjectNumber>> readFromFileSymbol(long startTime) {
        Map<String, List<KlineObjectNumber>> symbol2Tickers = new HashMap<>();
        File[] symbolFiles = new File(FOLDER_TICKER_15M).listFiles();
        long startAt = System.currentTimeMillis();
        for (File symbolFile : symbolFiles) {
            String symbol = symbolFile.getName();
            if (!StringUtils.endsWithIgnoreCase(symbol, "usdt")) {
                continue;
            }
            List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(symbolFile.getPath());
            while (true) {
                long time = tickers.get(0).startTime.longValue();
                if (time < startTime) {
                    tickers.remove(0);
                } else {
                    break;
                }
            }
            symbol2Tickers.put(symbol, tickers);
        }
        LOG.info("Read data: {}s", (System.currentTimeMillis() - startAt) / Utils.TIME_SECOND);
        return symbol2Tickers;
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
                counterStoploss += Utils.rateOf2Double(order.lastPrice, order.priceEntry);
            }
        }
        return lines;
    }


    private String buildLineTest(OrderTargetInfoTest order, boolean orderState, Double rateloss) {
        return order.symbol + "," + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart) + "," + order.side + "," + order.priceEntry
                + "," + order.priceTP + "," + symbol2LastPrice.get(order.symbol) + "," + order.volume + ","
                + order.avgVolume24h + "," + order.rateChange + "," + orderState + "," + rateloss;
    }


    List<String> detectBigChangeWithParamNew(Double rateTarget, Double rateChange, Map<String,
            List<KlineObjectNumber>> allSymbolTickers, Double volume, int max_ticker_trade) {
        counterTotal = 0;
        counterSuccess = 0;
        counterStoploss = 0.0;
        List<String> lines = new ArrayList<>();

        for (String symbol : allSymbolTickers.keySet()) {
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            try {
                List<OrderTargetInfoTest> orders = new ArrayList<>();
                List<KlineObjectNumber> tickers = allSymbolTickers.get(symbol);
                symbol2LastPrice.put(symbol, tickers.get(tickers.size() - 1).priceClose);
                for (int i = 0; i < tickers.size(); i++) {
                    KlineObjectNumber kline = tickers.get(i);
                    BreadDetectObject breadData = BreadFunctions.calBreadDataAltWithBtcTrend(tickers, i, RATE_BREAD_MIN_2TRADE);
                    if (breadData.orderSide != null
                            && breadData.orderSide.equals(OrderSide.BUY)
                            && breadData.totalRate >= rateChange
                            && kline.totalUsdt <= volume * 1000000) {
                        lastBreadTrader = breadData;
                        try {
                            Double priceEntry = kline.priceClose;
                            Double priceTarget = getPriceTarget(priceEntry, breadData.orderSide, rateTarget);
                            Double priceSTL = getPriceSL(priceEntry, breadData.orderSide, ALT_BREAD_BIGCHANE_STOPPLOSS);
                            OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, priceEntry,
                                    priceTarget, 1.0, 10, symbol, kline.startTime.longValue(),
                                    kline.startTime.longValue(), breadData.orderSide);
                            orderTrade.priceSL = priceSTL;
                            String date = Utils.sdfFile.format(new Date(kline.startTime.longValue()));
                            orderTrade.maxPrice = kline.maxPrice;
                            orderTrade.minPrice = kline.minPrice;
                            orderTrade.rateBreadAbove = breadData.breadAbove;
                            orderTrade.rateBreadBelow = breadData.breadBelow;
                            orderTrade.rateChange = breadData.totalRate;
                            orderTrade.avgVolume24h = TickerFuturesHelper.getAvgLastVolume7D(tickers, i);
                            orderTrade.volume = kline.totalUsdt;
                            for (int j = i + 1; j < i + max_ticker_trade * 96; j++) {
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
                            if (orderTrade.status.equals(OrderTargetStatus.REQUEST)) {
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
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        Integer rateSuccess = 0;
        Double rateSuccessLoss = 0.0;

        if (counterTotal != 0) {
            rateSuccess = counterSuccess * 1000 / counterTotal;
        }

        if (counterSuccess != 0) {
            rateSuccessLoss = counterStoploss * 1000 / (counterSuccess * rateTarget);
        }
        if (Math.abs(rateSuccessLoss) < 100) {
            LOG.info("Result All:{}d rateTarget:{} rateChange:{} volume:{}  {} {} {}/{} {}% {}%",
                    max_ticker_trade, rateTarget, rateChange, volume,
                    counterSuccess, counterStoploss.longValue(), counterSuccess * rateTarget + counterStoploss,
                    counterTotal, rateSuccess.doubleValue() / 10, rateSuccessLoss.longValue() / 10);
        }
        return lines;
    }


    public static void main(String[] args) throws ParseException {
        new AltBreadBigChange15MStopLoss().startDetectBigChangeVolumeMiniInterval15MDataMongo();
//List<Double> volumes = new ArrayList<>();
//        for (int i = 0; i < 40; i++) {
//            if (i < 20) {
//                volumes.add(0.4 + i * 0.1);
//            } else {
//                volumes.add(2.5 + (i - 20) * 0.5);
//            }
//        }
//        System.out.println(volumes);
    }

}
