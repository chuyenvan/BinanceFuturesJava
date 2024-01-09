/*
 * Copyright 2023 pc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.binance.chuyennd.bigchange.btctd;

import com.binance.chuyennd.funcs.TickerHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Utils;
import com.binance.chuyennd.volume.DayVolumeManager;
import com.binance.chuyennd.volume.Volume24hrManager;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import java.io.File;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class BtcBigChangeDetector {

    public static final Logger LOG = LoggerFactory.getLogger(BtcBigChangeDetector.class);
//    public static Integer LEVERAGE_TRADING = Configs.getInt("BtcBigLeverageTrading");
//    public static Integer BUDGET_PER_ORDER = Configs.getInt("BtcBigBudgetPerOrder");
//    public static Double RATE_PROFIT = Configs.getDouble("BtcBigRateProfit");
//    public static Double RATE_STOPLOSS = Configs.getDouble("BtcBigRateStopLoss");
//    public static final Double RATE_BIG_CHANGE_TD = Configs.getDouble("BtcBigRateBigChangeTD");
//    public static final Integer NUMBER_TICKER_CHECK = Configs.getInt("NumberTickerCheckRate");
//    public static final Integer NUMBER_TOP_SYMBOL2TRADE = Configs.getInt("BtcBigNumberSymbol4Trade");

    public static void main(String[] args) {
//        new BtcBigChangeDetector().startThreadDetectBigChangeBTCIntervalOneMinute();
//        System.out.println(Utils.getStartTimeDayAgo(100));
        Long startTime = 1695574800000L;
//            Long startTime = Utils.getStartTimeDayAgo(20);
        new BtcBigChangeDetector().detectBtcBreadWithTrend(0.005, 0.002, startTime);

    }

//    public void processTradingForList(OrderSide orderSide) {
//        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_BTCBIGCHANGETD_SYMBOLS4TRADE)) {
//            try {
//                Double priceEntryTarget = ClientSingleton.getInstance().getCurrentPrice(symbol);
//                Double quantity = Double.valueOf(Utils.normalQuantity2Api(BUDGET_PER_ORDER * LEVERAGE_TRADING / priceEntryTarget));
//                Order orderResult = OrderHelper.newOrderMarket(symbol, orderSide, quantity, LEVERAGE_TRADING);
//                if (orderResult != null) {
//                    PositionRisk pos = PositionHelper.getPositionBySymbol(symbol);
//                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_BTCBIGCHANGETD_POS_MANAGER, symbol, Utils.gson.toJson(pos));
//                    String telegramAler = symbol + " bigchangebtc -> " + orderSide + " entry: " + orderResult.getAvgPrice().doubleValue();
//                    // create tp sl                    
//                    Order slOrder = OrderHelper.stopLoss(orderResult, RATE_STOPLOSS);
//                    if (slOrder != null) {
//                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_BTCBIGCHANGETD_ORDER_SL_MANAGER, symbol, Utils.gson.toJson(slOrder));
//                    }
//                    Order tpOrder = OrderHelper.takeProfit(orderResult, RATE_PROFIT);
//                    if (tpOrder != null) {
//                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_BTCBIGCHANGETD_ORDER_TP_MANAGER, symbol, Utils.gson.toJson(tpOrder));
//                    }
//                    Utils.sendSms2Telegram(telegramAler);
//                    LOG.info("Add order success:{} {} entry: {} quantity:{} {} {}", orderSide, symbol, orderResult.getAvgPrice().doubleValue(), quantity, new Date(), telegramAler);
//                } else {
//                    String log = "Add order fail because can not create order symbol: " + symbol;
//                    LOG.info(log);
//                    Utils.sendSms2Telegram(log);
//                }
//            } catch (Exception e) {
//                LOG.info("Error during create order for {} btcbigchangetrading", symbol);
//                e.printStackTrace();
//            }
//        }
//    }
//
//    private void startThreadDetectBigChangeBTCIntervalOneMinute() {
//        new Thread(() -> {
//            Thread.currentThread().setName("ThreadDetectBigChangeBTCIntervalOneMinute");
//            LOG.info("Start ThreadDetectBigChangeBTCIntervalOneMinute !");
//            Set<String> symbols = new HashSet<>();
//            symbols.addAll(TickerHelper.getAllSymbol());
//            while (true) {
//                try {
//                    if (System.currentTimeMillis() % Utils.TIME_MINUTE <= Utils.TIME_SECOND) {
//                        LOG.info("Detect bigchane in month kline!");
////                        KlineObjectNumber ticker = TickerHelper.getLastTicker(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_1M);
////                        Double rate = (ticker.priceMax - ticker.priceMin) / ticker.priceMin;
//                        List<KlineObjectNumber> tickers = TickerHelper.getTicker(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_1M);
//
//                        Double maxprice = TickerHelper.getMaxPrice(tickers, NUMBER_TICKER_CHECK);
//                        Double minprice = TickerHelper.getMinPrice(tickers, NUMBER_TICKER_CHECK);
//                        Double priceChange = TickerHelper.getMinPrice(tickers, NUMBER_TICKER_CHECK);
//                        Double rate = (maxprice - minprice) / maxprice;
//                        if (rate > RATE_BIG_CHANGE_TD) {
//                            LOG.info("{} {} {}", "BTCUSDT", rate, priceChange);
//                            OrderSide side = OrderSide.BUY;
//                            if (priceChange < 0) {
//                                side = OrderSide.SELL;
//                            }
////                            startThreadTradingWithListTradingBefore(side);
//                            startThreadExtractAllTopAltChange(priceChange, symbols);
//                        }
//                    }
//                    Thread.sleep(Utils.TIME_SECOND);
//                } catch (Exception e) {
//                    LOG.error("ERROR during ThreadDetectBigChangeBTCIntervalOneMinute: {}", e);
//                    e.printStackTrace();
//                }
//            }
//        }).start();
//    }
//
//    private void startThreadExtractAllTopAltChange(Double priceChange, Set<String> symbols) {
//        new Thread(() -> {
//            Thread.currentThread().setName("ThreadExtractAllTopAltChange");
//            LOG.info("Start ThreadExtractAllTopAltChange !");
//            try {
//                int numberMinuteCheckRateChange = 10;
//                Thread.sleep(numberMinuteCheckRateChange * Utils.TIME_MINUTE);
//                TreeMap<Double, String> rate2Symbol = new TreeMap<>();
//                Map<String, Double> symbol2Rate = new HashMap<>();
//                OrderSide side = OrderSide.BUY;
//                if (priceChange < 0) {
//                    side = OrderSide.SELL;
//                }
//                List<String> symbols4Trade = new ArrayList<>();
//                Map<String, KlineObjectNumber> symbol2KlineTarget = new HashMap<>();
//                for (String symbol : symbols) {
//                    try {
//                        List<KlineObjectNumber> tickers = TickerHelper.getTicker(symbol, Constants.INTERVAL_1M);
//                        Double maxPrice = null;
//                        Double minPrice = null;
//                        KlineObjectNumber klineCheckPoint = tickers.get(tickers.size() - 1 - numberMinuteCheckRateChange);
//                        symbol2KlineTarget.put(symbol, klineCheckPoint);
//                        for (int i = 0; i < numberMinuteCheckRateChange + 1; i++) {
//                            KlineObjectNumber kline = tickers.get(tickers.size() - 1 - i);
//                            if (maxPrice == null || kline.priceMax > maxPrice) {
//                                maxPrice = kline.priceMax;
//                            }
//                            if (minPrice == null || kline.priceMin < minPrice) {
//                                minPrice = kline.priceMin;
//                            }
//                        }
//                        Double rateDown = (klineCheckPoint.priceOpen - minPrice) / klineCheckPoint.priceOpen;
//                        Double rateUp = (maxPrice - klineCheckPoint.priceOpen) / klineCheckPoint.priceOpen;
//                        Double rateChange = 0d;
//                        if (side.equals(OrderSide.BUY)) {
//                            rateChange = rateUp;
//                            symbol2Rate.put(symbol, rateDown);
//                        } else {
//                            rateChange = rateDown;
//                            symbol2Rate.put(symbol, rateUp);
//                        }
//                        rate2Symbol.put(rateChange, symbol);
//                    } catch (Exception e) {
//                        e.printStackTrace();
//                    }
//                }
//                for (Map.Entry<Double, String> entry : rate2Symbol.entrySet()) {
//                    Double rate = entry.getKey();
//                    String symbol = entry.getValue();
//                    if (rate > RATE_PROFIT) {
//                        symbols4Trade.add(symbol);
//                        LOG.info("{} -> {} {}", symbol, Utils.normalPrice2Api(rate), Utils.normalPrice2Api(symbol2Rate.get(symbol)));
//                    }
//                }
//                // clear list trade old
//                RedisHelper.getInstance().get().del(RedisConst.REDIS_KEY_EDUCA_BTCBIGCHANGETD_SYMBOLS4TRADE);
//                // update list trade new
//                for (int i = 0; i < NUMBER_TOP_SYMBOL2TRADE; i++) {
//                    String symbol = symbols4Trade.get(symbols4Trade.size() - 1 - i);
//                    KlineObjectNumber klineTarget = symbol2KlineTarget.get(symbol);
//                    LOG.info("Add symbol new: {} to list trade next btc bigchange", symbol);
//                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_BTCBIGCHANGETD_SYMBOLS4TRADE, symbol, Utils.toJson(klineTarget));
//                }
//            } catch (Exception e) {
//                e.printStackTrace();
//            }
//        }).start();
//    }
//
//    public void startThreadTradingWithListTradingBefore(OrderSide side) {
//        new Thread(() -> {
//            Thread.currentThread().setName("ThreadTradingWithListTradingBefore");
//            LOG.info("Start thread ThreadTradingWithListTradingBefore!");
//            processTradingForList(side);
//        }).start();
//
//    }
    private void detectBtcBreadWithTrend(Double rateBread, Double rate2Trade, long startTime) {
        try {
            Map<String, List<KlineObjectNumber>> allSymbolTickers = TickerHelper.getAllKlineStartTime(Constants.INTERVAL_15M, startTime);
            List<KlineObjectNumber> allKlines = allSymbolTickers.get(Constants.SYMBOL_PAIR_BTC);
//            long time = Utils.getStartTimeDayAgo(200);
//            List<KlineObjectNumber> allKlines = TickerHelper.getTickerWithStartTime(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_15M, time);
            LOG.info("Last time ticker btc: {}", new Date(allKlines.get(allKlines.size() - 1).startTime.longValue()));
//            List<KlineObjectNumber> allKlines = TickerHelper.getTicker(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_15M);
            for (KlineObjectNumber kline : allKlines) {
                Double beardAbove = 0d;
                Double beardBelow = 0d;
                Double rateChange = null;

                if (kline.priceClose > kline.priceOpen) {
                    beardAbove = kline.maxPrice - kline.priceClose;
                    beardBelow = kline.priceOpen - kline.minPrice;
                } else {
                    beardAbove = kline.maxPrice - kline.priceOpen;
                    beardBelow = kline.priceClose - kline.minPrice;
                }
                rateChange = Math.abs(Utils.rateOf2Double(kline.priceOpen, kline.priceClose));
                double rateChangeAbove = beardAbove / kline.priceClose;
                double rateChangeBelow = beardBelow / kline.priceClose;
                OrderSide side = null;
                if (rateChangeAbove > rateBread) {
//                    LOG.info("bread: {} {}", rateChangeAbove, new Date(kline.startTime.longValue()));
                    side = OrderSide.SELL;
                } else {
                    if (rateChangeBelow > rateBread) {
                        side = OrderSide.BUY;
//                        LOG.info("bread: {} {}", rateChangeBelow, new Date(kline.startTime.longValue()));
                    }
                }
                List<String> lines = new ArrayList<>();
                StringBuilder builder = new StringBuilder();
                if (side != null && rateChange >= rate2Trade) {
                    LOG.info("{} {} bread above:{} bread below:{} rateChange:{}", new Date(kline.startTime.longValue()),
                            side, rateChangeAbove, rateChangeBelow, rateChange);
                    builder.setLength(0);
                    builder.append("Bread ").append(side).append(",");
                    builder.append(rateChangeAbove).append(" - ").append(rateChangeBelow).append(",");
                    builder.append(rateChange).append(",");
                    lines.add(builder.toString());
                    TreeMap<Double, String> rate2Symbols = TickerHelper.getMaxRateWithTime(kline.startTime.longValue(),
                            side, Constants.INTERVAL_15M, 100, startTime, allSymbolTickers);
                    Integer date = Integer.valueOf(Utils.normalizeDateYYYYMMDD(kline.startTime.longValue()));
                    Map<String, Double> symbol2Volume;
                    if (Utils.normalizeDateYYYYMMDD(kline.startTime.longValue()).equals(Utils.getToDayFileName())) {
                        symbol2Volume = new HashMap<>();
                        symbol2Volume.putAll(Volume24hrManager.getInstance().symbol2Volume);
                    } else {
                        symbol2Volume = DayVolumeManager.getInstance().date2SymbolVolume.get(date);
                    }
                    int numberSymbolCanTrade = 0;
                    int numberSymbolNotCanTrade = 0;
                    for (Map.Entry<Double, String> entry : rate2Symbols.entrySet()) {
                        Double rate = entry.getKey();
                        String symbol = entry.getValue();
                        Double rateloss = extractRateLoss(symbol);
                        if (Constants.specialSymbol.contains(symbol.split("#")[0])) {
                            continue;
                        }
                        try {
                            builder.setLength(0);
                            builder.append(symbol).append(",");
                            builder.append(rate).append(",");
                            Double volume = null;
                            if (symbol2Volume != null) {
                                volume = symbol2Volume.get(symbol.split("#")[0]);
                            }
                            builder.append(String.valueOf(volume)).append(",");
                            // feature to trade
                            Double volumeMinimum = 80000000d;
                            Double rateChange2Trade = 2.0;
                            if (volume != null && rate < 0.009
                                    && volume > volumeMinimum
                                    && extractRate(symbol) > rateChange2Trade) {
                                LOG.info("-----------------------------------------------------------: {} -> {} {} {}", symbol, rate, rateloss, volume);
                                numberSymbolNotCanTrade++;
                                builder.append("No");
                            } else {
                                if (volume != null && volume > volumeMinimum && extractRate(symbol) > rateChange2Trade) {
                                    builder.append("Yes");
                                    numberSymbolCanTrade++;
                                } else {
                                    builder.append("No");
                                }
                            }
                            lines.add(builder.toString());
//                            LOG.info("{} {} {}", symbol, rate, volume);
                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }
                    String fileName = "target/" + "Bread-" + Utils.normalizeDateYYYYMMDDHHmm(kline.startTime.longValue()) + ".csv";
                    fileName = fileName.replace(":", " ");
                    LOG.info("Write data to file: {} number can trade: {}/{}", fileName, numberSymbolCanTrade, numberSymbolNotCanTrade);
                    FileUtils.writeLines(new File(fileName), lines);
                    lines.clear();
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private double extractRate(String symbol) {
//       BTCUSDT-42015.7-42215.5-0.006995004248411939
        String[] parts = StringUtils.split(symbol, "#");
        return Double.parseDouble(parts[parts.length - 1]);
    }

    private Double extractRateLoss(String symbol) {
        String[] parts = StringUtils.split(symbol, "#");
        return Utils.rateOf2Double(Double.parseDouble(parts[parts.length - 2]), Double.parseDouble(parts[parts.length - 4]));
    }

}
