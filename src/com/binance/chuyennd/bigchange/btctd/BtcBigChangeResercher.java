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

import com.educa.mail.funcs.BreadFunctions;
import com.binance.chuyennd.funcs.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Utils;
import com.binance.chuyennd.volume.DayVolumeManager;
import com.binance.chuyennd.statistic24hr.Volume24hrManager;
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
public class BtcBigChangeResercher {

    public static final Logger LOG = LoggerFactory.getLogger(BtcBigChangeResercher.class);
    public BreadDetectObject lastBreadTrader = null;
    public Long EVENT_TIME = Utils.TIME_MINUTE * 15;
    public Integer NUMBER_TICKER_TO_TRADE = 10;
    public Long lastTimeBreadTrader = 0l;
    public Double TOTAL_RATE_CHANGE_WITHBREAD_2TRADING = 0.014;
    public Double BTC_BREAD_BIGCHANE_15M = 0.006;
    public Double RATE_CHANGE_WITHBREAD_2TRADING = 0.003;

    public static void main(String[] args) {
//        new BtcBigChangeDetector().startThreadDetectBigChangeBTCIntervalOneMinute();
//        System.out.println(Utils.getStartTimeDayAgo(100));
        Long startTime = 1695574800000L;
//            Long startTime = Utils.getStartTimeDayAgo(20);
//        new BtcBigChangeResercher().detectBtcBreadWithTrend(startTime);
        new BtcBigChangeResercher().detectBtcBreadWithTrendTestCloseWithTicker(startTime);

    }

    private void detectBtcBreadWithTrend(long startTime) {
        try {
            Map<String, List<KlineObjectNumber>> allSymbolTickers = TickerFuturesHelper.getAllKlineStartTime(Constants.INTERVAL_15M, startTime);
            List<KlineObjectNumber> allKlines = allSymbolTickers.get(Constants.SYMBOL_PAIR_BTC);

            LOG.info("Last time ticker btc: {}", new Date(allKlines.get(allKlines.size() - 1).startTime.longValue()));

            for (KlineObjectNumber kline : allKlines) {
                if (kline.startTime.longValue() > lastTimeBreadTrader + NUMBER_TICKER_TO_TRADE * EVENT_TIME) {
                    BreadDetectObject breadData = BreadFunctions.calBreadDataBtc(kline, BTC_BREAD_BIGCHANE_15M);
                    List<String> lines = new ArrayList<>();
                    StringBuilder builder = new StringBuilder();
                    if (breadData.orderSide != null
                            && breadData.rateChange > RATE_CHANGE_WITHBREAD_2TRADING
                            && breadData.totalRate >= TOTAL_RATE_CHANGE_WITHBREAD_2TRADING) {
                        lastTimeBreadTrader = kline.startTime.longValue();
                        lastBreadTrader = breadData;

                        LOG.info("{} {} bread above:{} bread below:{} rateChange:{} totalRate: {}", new Date(kline.startTime.longValue()),
                                breadData.orderSide, breadData.breadAbove, breadData.breadBelow, breadData.rateChange, breadData.totalRate);
                        builder.setLength(0);
                        builder.append("Bread ").append(breadData.orderSide).append(",");
                        builder.append(breadData.breadAbove).append(" - ").append(breadData.breadBelow).append(",");
                        builder.append(breadData.rateChange).append(",");
                        lines.add(builder.toString());
                        TreeMap<Double, String> rate2Symbols = TickerFuturesHelper.getMaxRateWithTime(kline.startTime.longValue(),
                                breadData.orderSide, Constants.INTERVAL_15M, NUMBER_TICKER_TO_TRADE, startTime, allSymbolTickers);
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
                            if (Constants.specialSymbol.contains(symbol.split("#")[0])) {
                                continue;
                            }
                            try {
                                builder.setLength(0);
                                builder.append(symbol).append(",");
                                builder.append(extractRate(symbol)).append(",");
                                builder.append(extractVolume(symbol)).append(",");
                                builder.append(rate).append(",");
                                Double volume = null;
                                if (symbol2Volume != null) {
                                    volume = symbol2Volume.get(symbol.split("#")[0]);
                                }
                                builder.append(String.valueOf(volume)).append(",");
                                // feature to trade
//                            Double volumeMinimum = 1000000d;
                                if (rate < 0.004) {
//                                LOG.info("-----------------------------------------------------------: {} -> {} {} {}", symbol, rate, rateloss, volume);
                                    numberSymbolNotCanTrade++;
                                    builder.append("Fail");
                                } else {
//                                if (volume != null) {
                                    builder.append("Yes");
                                    numberSymbolCanTrade++;
//                                } else {
//                                    builder.append("No");
//                                }
                                }
                                lines.add(builder.toString());
//                            LOG.info("{} {} {}", symbol, rate, volume);
                            } catch (Exception e) {
                                e.printStackTrace();
                            }
                        }
                        String fileName = "target/data/" + "Bread-" + Utils.normalizeDateYYYYMMDDHHmm(kline.startTime.longValue()) + ".csv";
                        fileName = fileName.replace(":", " ");
                        LOG.info("Write data to file: {} number can trade: {}/{}", fileName, numberSymbolCanTrade, numberSymbolNotCanTrade);
                        FileUtils.writeLines(new File(fileName), lines);
                        lines.clear();
                    }
                } else {
//                    LOG.info("Not process because is Trading for bigchange: {}", Utils.toJson(lastBreadTrader));
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

    private String extractVolume(String symbol) {
        String[] parts = StringUtils.split(symbol, "#");
        return parts[parts.length - 2];
    }

    private void detectBtcBreadWithTrendTestCloseWithTicker(Long startTime) {
        try {
            Map<String, List<KlineObjectNumber>> allSymbolTickers = TickerFuturesHelper.getAllKlineStartTime(Constants.INTERVAL_15M, startTime);
            List<KlineObjectNumber> allKlines = allSymbolTickers.get(Constants.SYMBOL_PAIR_BTC);
            LOG.info("Last time ticker btc: {}", new Date(allKlines.get(allKlines.size() - 1).startTime.longValue()));
            for (KlineObjectNumber kline : allKlines) {
                if (kline.startTime.longValue() > lastTimeBreadTrader + NUMBER_TICKER_TO_TRADE * EVENT_TIME) {
                    BreadDetectObject breadData = BreadFunctions.calBreadDataBtc(kline, BTC_BREAD_BIGCHANE_15M);
                    List<String> lines = new ArrayList<>();
                    StringBuilder builder = new StringBuilder();
                    if (breadData.orderSide != null
                            && breadData.rateChange > RATE_CHANGE_WITHBREAD_2TRADING
                            && breadData.totalRate >= TOTAL_RATE_CHANGE_WITHBREAD_2TRADING) {
                        lastTimeBreadTrader = kline.startTime.longValue();
                        lastBreadTrader = breadData;

                        LOG.info("{} {} bread above:{} bread below:{} rateChange:{} totalRate: {}", new Date(kline.startTime.longValue()),
                                breadData.orderSide, breadData.breadAbove, breadData.breadBelow, breadData.rateChange, breadData.totalRate);
                        builder.setLength(0);
                        builder.append("Bread ").append(breadData.orderSide).append(",");
                        builder.append(breadData.breadAbove).append(" - ").append(breadData.breadBelow).append(",");
                        builder.append(breadData.rateChange).append(",");
                        lines.add(builder.toString());
                        TreeMap<Double, String> rate2Symbols = getRateWithNumberTicker(kline.startTime.longValue(),
                                breadData.orderSide, Constants.INTERVAL_15M, NUMBER_TICKER_TO_TRADE, startTime, allSymbolTickers);
                        int numberSymbolCanTrade = 0;
                        int numberSymbolNotCanTrade = 0;
                        for (Map.Entry<Double, String> entry : rate2Symbols.entrySet()) {
                            Double rate = entry.getKey();
                            String symbol = entry.getValue();
                            if (Constants.specialSymbol.contains(symbol.split("#")[0])) {
                                continue;
                            }
                            try {
                                builder.setLength(0);
                                builder.append(symbol).append(",");
                                builder.append(rate).append(",");

                                if (rate < 0.004) {
//                                LOG.info("-----------------------------------------------------------: {} -> {} {} {}", symbol, rate, rateloss, volume);
                                    numberSymbolNotCanTrade++;
                                    builder.append("Fail");
                                } else {
                                    builder.append("Yes");
                                    numberSymbolCanTrade++;

                                }
                                lines.add(builder.toString());
//                            LOG.info("{} {} {}", symbol, rate, volume);
                            } catch (Exception e) {
                                e.printStackTrace();
                            }
                        }
                        String fileName = "target/data/" + "Bread-WithNumberTicker-" + NUMBER_TICKER_TO_TRADE + "-" + breadData.orderSide + "-" + Utils.normalizeDateYYYYMMDDHHmm(kline.startTime.longValue()) + ".csv";
                        fileName = fileName.replace(":", " ");
                        LOG.info("Write data to file: {} number can trade: {}/{}", fileName, numberSymbolCanTrade, numberSymbolNotCanTrade);
                        FileUtils.writeLines(new File(fileName), lines);
                        lines.clear();
                    }
                } else {
//                    LOG.info("Not process because is Trading for bigchange: {}", Utils.toJson(lastBreadTrader));
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static TreeMap<Double, String> getRateWithNumberTicker(long timeCheckPoint, OrderSide side, String interval,
            int numberTicker, long startTime, Map<String, List<KlineObjectNumber>> allSymbolTickers) {
        TreeMap<Double, String> rate2Symbol = new TreeMap<>();
        for (Map.Entry<String, List<KlineObjectNumber>> entry : allSymbolTickers.entrySet()) {
            String symbol = entry.getKey();
            List<KlineObjectNumber> tickers = entry.getValue();
            try {
                KlineObjectNumber klineCheckPoint = null;
                KlineObjectNumber klineTarget = null;
                for (int i = 0; i < tickers.size(); i++) {
                    KlineObjectNumber ticker = tickers.get(i);
                    if (ticker.startTime.longValue() == timeCheckPoint) {
                        klineCheckPoint = ticker;
                        klineTarget = tickers.get(tickers.size() - 1);
                        if (i + numberTicker < tickers.size()) {
                            klineTarget = tickers.get(i + numberTicker);
                        }
                    }
                }
                if (klineCheckPoint != null) {
                    Double priceEntry = klineCheckPoint.priceClose;
                    Double lastPrice = klineTarget.priceClose;
                    if (side.equals(OrderSide.BUY)) {
                        rate2Symbol.put(Utils.rateOf2Double(lastPrice, priceEntry), symbol + "#" + priceEntry + "#" + lastPrice);
                    } else {
                        rate2Symbol.put(-Utils.rateOf2Double(lastPrice, priceEntry), symbol + "#" + priceEntry + "#" + lastPrice);
                    }
                }

            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return rate2Symbol;
    }
}
