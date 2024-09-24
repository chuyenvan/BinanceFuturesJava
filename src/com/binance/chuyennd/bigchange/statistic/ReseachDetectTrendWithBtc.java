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
package com.binance.chuyennd.bigchange.statistic;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.*;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;

import java.io.File;
import java.io.IOException;
import java.text.ParseException;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import org.apache.commons.io.FileUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * @author pc
 */
public class ReseachDetectTrendWithBtc {

    public static final Logger LOG = LoggerFactory.getLogger(ReseachDetectTrendWithBtc.class);

    public static void main(String[] args) throws IOException, ParseException {
        String symbol = "TIAUSDT";
//        new ReseachDetectTrendWithBtc().detectorTrendSymbol(symbol);
//        new ReseachDetectTrendWithBtc().testResistanceAndSupport(symbol);
        new ReseachDetectTrendWithBtc().testResistanceAndSupportByTime(symbol, "20240229 00:30");
//        new ReseachDetectTrendWithBtc().testResistanceAndSupportSide(symbol);

//        for (String symbol : TickerHelper.getAllSymbol()) {
//            new ReseachDetectTrendWithBtc().chartSymbol("BTCUSDT");
//        }
//        System.out.println(ClientSingleton.getInstance().getCurrentPrice(Constants.SYMBOL_PAIR_BTC));
//        String timeStr = "20240305";
//        System.out.println(Utils.sdfFile.parse(timeStr).getTime());
//        new ReseachDetectTrendWithBtc().extractRateAltCoinWithStartTime(Utils.sdfFile.parse(timeStr).getTime());
//        new ReseachDetectTrendWithBtc().extractAltBehaviorByBtcTrend();

    }


    private void testResistanceAndSupportByTime(String symbol, String time) {
        try {
            long timeCheck = Utils.sdfFileHour.parse(time).getTime();
//            List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_15M);
            List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_15M + symbol);
            List<KlineObjectNumber> ticker2Test = new ArrayList<>();
            for (int i = 0; i < tickers.size(); i++) {
                if (tickers.get(i).startTime.longValue() <= timeCheck) {
                    ticker2Test.add(tickers.get(i));
                }
            }
            LOG.info("Last ticker time: {}", Utils.normalizeDateYYYYMMDDHHmm(ticker2Test.get(ticker2Test.size() - 1).startTime.longValue()));
            List<TrendObject> trends = TickerFuturesHelper.extractTopBottomObjectInTicker(ticker2Test);
            printTrendObject(trends);
            ResistanceAndSupport rsDetector = new ResistanceAndSupport(trends, ticker2Test.get(ticker2Test.size() - 1));
            rsDetector.detectTrend(0.03);
            LOG.info(rsDetector.printTrend() + " " +
                    Utils.normalizeDateYYYYMMDDHHmm(ticker2Test.get(ticker2Test.size() - 1).startTime.longValue())
                    + " suggest: " + rsDetector.sideSuggest);
            System.out.println(rsDetector.getStopLoss());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void testResistanceAndSupportSide(String symbol) {
        try {
            List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_15M);
            List<KlineObjectNumber> ticker2Test = new ArrayList<>();
            for (int i = 0; i < 100; i++) {
                ticker2Test.add(tickers.get(i));
            }
            for (int i = 100; i < tickers.size(); i++) {
                ticker2Test.add(tickers.get(i));
                List<TrendObject> trends = TickerFuturesHelper.extractTopBottomObjectInTicker(ticker2Test);
                ResistanceAndSupport rsDetector = new ResistanceAndSupport(trends, ticker2Test.get(ticker2Test.size() - 1));
                rsDetector.detectTrend(0.03);
                List<TrendObject> resistances = rsDetector.resistances;
                List<TrendObject> supports = rsDetector.supports;
                TrendObject r1 = resistances.get(0);
                TrendObject r2 = resistances.get(1);
                TrendObject r3 = resistances.get(2);
                TrendObject r4 = resistances.get(3);
                TrendObject r5 = resistances.get(4);
                TrendObject s1 = supports.get(0);
                TrendObject s2 = supports.get(1);
                TrendObject s3 = supports.get(2);
                TrendObject s4 = supports.get(3);
                TrendObject s5 = supports.get(4);
                TrendObject rMax1 = rsDetector.getMaxByNumber(resistances, 1, 5);
                TrendObject rMax2 = rsDetector.getMaxByNumber(resistances, 2, 5);
                TrendObject sMin1 = rsDetector.getMinByNumber(supports, 1, 5);
                TrendObject sMin2 = rsDetector.getMinByNumber(supports, 2, 5);
//                if (rsDetector.sideSuggest != null && rsDetector.sideSuggest.equals(OrderSide.BUY)) {
                LOG.info(rsDetector.printTrend() + " " +
                        Utils.normalizeDateYYYYMMDDHHmm(ticker2Test.get(ticker2Test.size() - 1).startTime.longValue())
                        + " suggest: " + rsDetector.sideSuggest);
                LOG.info("r1: {} {}", Utils.normalizeDateYYYYMMDDHHmm(r1.kline.startTime.longValue()), r1.kline.maxPrice);
                LOG.info("r2: {} {}", Utils.normalizeDateYYYYMMDDHHmm(r2.kline.startTime.longValue()), r2.kline.maxPrice);
                LOG.info("r3: {} {}", Utils.normalizeDateYYYYMMDDHHmm(r3.kline.startTime.longValue()), r3.kline.maxPrice);
                LOG.info("r4: {} {}", Utils.normalizeDateYYYYMMDDHHmm(r4.kline.startTime.longValue()), r4.kline.maxPrice);
                LOG.info("r5: {} {}", Utils.normalizeDateYYYYMMDDHHmm(r5.kline.startTime.longValue()), r5.kline.maxPrice);
                LOG.info("s1: {} {}", Utils.normalizeDateYYYYMMDDHHmm(s1.kline.startTime.longValue()), s1.kline.minPrice);
                LOG.info("s2: {} {}", Utils.normalizeDateYYYYMMDDHHmm(s2.kline.startTime.longValue()), s2.kline.minPrice);
                LOG.info("s3: {} {}", Utils.normalizeDateYYYYMMDDHHmm(s3.kline.startTime.longValue()), s3.kline.minPrice);
                LOG.info("s4: {} {}", Utils.normalizeDateYYYYMMDDHHmm(s4.kline.startTime.longValue()), s4.kline.minPrice);
                LOG.info("s5: {} {}", Utils.normalizeDateYYYYMMDDHHmm(s5.kline.startTime.longValue()), s5.kline.minPrice);
                LOG.info("Max1:{} Max2:{} Min1:{} Min2:{}", rMax1.getMaxPrice(), rMax2.getMaxPrice(),
                        sMin1.getMinPrice(), sMin2.getMinPrice());

//                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void testResistanceAndSupport(String symbol) {
//        List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_15M);
        List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_15M + symbol);
        ResistanceAndSupport lastRs = null;
        for (int i = 100; i < tickers.size(); i++) {
            List<KlineObjectNumber> ticker2Test = new ArrayList<>();
            for (int j = 0; j < i; j++) {
                ticker2Test.add(tickers.get(j));
            }
            List<TrendObject> trends = TickerFuturesHelper.extractTopBottomObjectInTicker(ticker2Test);
            ResistanceAndSupport rsDetector = new ResistanceAndSupport(trends,
                    ticker2Test.get(ticker2Test.size() - 1));
            rsDetector.detectTrend(0.03);
            if (lastRs == null) {
                lastRs = rsDetector;
            } else {
                if (!lastRs.trendDetail.status.equals(rsDetector.trendDetail.status)) {
                    LOG.info(rsDetector.printTrend() + " " + lastRs.sideSuggest + " " +
                            Utils.normalizeDateYYYYMMDDHHmm(ticker2Test.get(ticker2Test.size() - 1).startTime.longValue()));
                    lastRs = rsDetector;
                }
            }
            if (i == tickers.size() - 1) {
                lastRs = rsDetector;
            }
        }
        LOG.info(lastRs.printTrend() + " " + lastRs.sideSuggest + " " +
                Utils.normalizeDateYYYYMMDDHHmm(tickers.get(tickers.size() - 1).startTime.longValue()));
//        rsDetector.printData();

    }

    public List<TrendObjectDetail> detectorTrend(List<KlineObjectNumber> tickers, String symbol, Double rateOfSideWay) {
        List<TrendObject> btcTrends = TickerFuturesHelper.extractTopBottomObjectInTicker(tickers);
        return TickerFuturesHelper.detectTrendByKline(btcTrends, rateOfSideWay);
    }

    public void extractAltBehaviorByBtcTrend() throws IOException {
        List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_15M
                + "AMBUSDT");
        Double rateOfSideWay = 0.02;
        List<TrendObjectDetail> btcTrends = detectorTrend(tickers, Constants.SYMBOL_PAIR_BTC, rateOfSideWay);
//        updateTimeOfTrend(btcTrends);
//        Map<TrendObjectDetail, List<TrendDataTrackingObject>> altBehaviors = getAllAltBehavior(btcTrends, symbol2Kline1Ds);
//        printAltBehavior(altBehaviors);
        printTrendDetailObject(btcTrends, Constants.SYMBOL_PAIR_BTC);
    }

    public void printTrendDetailObject(List<TrendObjectDetail> trendInfos, String symbol) {
        for (TrendObjectDetail trendInfo : trendInfos) {
            String trendString = trendInfo.status.toString();
            if (trendString.length() < TrendState.TREND_DOWN.toString().length()) {
                int numberSpace = TrendState.TREND_DOWN.toString().length() - trendString.length();
                for (int i = 0; i < numberSpace; i++) {
                    trendString += " ";
                }
            }
            Double startPrice = 0d;
            Double endPrice = 0d;
            if (trendInfo.status.equals(TrendState.TREND_DOWN)) {
                startPrice = trendInfo.topBottonObjects.get(0).kline.maxPrice;
                endPrice = trendInfo.topBottonObjects.get(trendInfo.topBottonObjects.size() - 1).kline.minPrice;
            }
            if (trendInfo.status.equals(TrendState.TREND_UP)) {
                startPrice = trendInfo.topBottonObjects.get(0).kline.minPrice;
                endPrice = trendInfo.topBottonObjects.get(trendInfo.topBottonObjects.size() - 1).kline.maxPrice;
            }
            if (trendInfo.status.equals(TrendState.SIDEWAY)) {
                startPrice = trendInfo.topBottonObjects.get(0).kline.minPrice;
                endPrice = trendInfo.topBottonObjects.get(trendInfo.topBottonObjects.size() - 1).kline.maxPrice;
            }
            Double rate = Utils.rateOf2Double(startPrice, endPrice);
            LOG.info("{} {} {} {} rate:{} start:{} end:{} nextTrend:{}", symbol, trendString,
                    Utils.normalizeDateYYYYMMDDHHmm(trendInfo.startTimeTrend),
                    Utils.normalizeDateYYYYMMDDHHmm(trendInfo.endTimeTrend),
                    rate, startPrice, endPrice,
                    Utils.normalizeDateYYYYMMDDHHmm(trendInfo.timeNextTrend)
            );
        }
    }

    public void printTrendDetailObjectEnd(List<TrendObjectDetail> trendInfos, String symbol) {

        TrendObjectDetail trendInfo = trendInfos.get(trendInfos.size() - 1);
        String trendString = trendInfo.status.toString();
        if (trendString.length() < TrendState.TREND_DOWN.toString().length()) {
            int numberSpace = TrendState.TREND_DOWN.toString().length() - trendString.length();
            for (int i = 0; i < numberSpace; i++) {
                trendString += " ";
            }
        }
        Double startPrice = 0d;
        Double endPrice = 0d;
        if (trendInfo.status.equals(TrendState.TREND_DOWN)) {
            startPrice = trendInfo.topBottonObjects.get(0).kline.maxPrice;
            endPrice = trendInfo.topBottonObjects.get(trendInfo.topBottonObjects.size() - 1).kline.minPrice;
        }
        if (trendInfo.status.equals(TrendState.TREND_UP)) {
            startPrice = trendInfo.topBottonObjects.get(0).kline.minPrice;
            endPrice = trendInfo.topBottonObjects.get(trendInfo.topBottonObjects.size() - 1).kline.maxPrice;
        }
        if (trendInfo.status.equals(TrendState.SIDEWAY)) {
            startPrice = trendInfo.topBottonObjects.get(0).kline.minPrice;
            endPrice = trendInfo.topBottonObjects.get(trendInfo.topBottonObjects.size() - 1).kline.maxPrice;
        }
        Double rate = Utils.rateOf2Double(startPrice, endPrice);
        LOG.info("{} {} {} {} rate:{} min:{} max:{} starttime:{} endTime: {} nextTrend:{}", symbol, trendString,
                Utils.sdfFile.format(new Date(trendInfo.topBottonObjects.get(0).kline.startTime.longValue())),
                Utils.sdfFile.format(new Date(trendInfo.topBottonObjects.get(trendInfo.topBottonObjects.size() - 1).kline.startTime.longValue())),
                rate, startPrice, endPrice,
                Utils.normalizeDateYYYYMMDDHHmm(trendInfo.startTimeTrend),
                Utils.normalizeDateYYYYMMDDHHmm(trendInfo.endTimeTrend),
                Utils.normalizeDateYYYYMMDDHHmm(trendInfo.timeNextTrend)
        );

    }

    private Double rateOf2UpDownObject(TrendObject btcTrend, TrendObject lastObjectInListSW) {
        Double rateChange;
        if (btcTrend.status.equals(TrendState.UP)) {
            rateChange = Utils.rateOf2Double(btcTrend.kline.priceClose, lastObjectInListSW.kline.priceOpen);
        } else {
            rateChange = Utils.rateOf2Double(btcTrend.kline.priceOpen, lastObjectInListSW.kline.priceClose);
        }
        return rateChange;
    }

    private void updateTimeOfTrend(List<TrendObjectDetail> btcTrends) {
        for (int i = 0; i < btcTrends.size(); i++) {
            TrendObjectDetail trendInfo = btcTrends.get(i);
            if (!trendInfo.status.equals(TrendState.SIDEWAY)) {
                trendInfo.startTimeTrend = trendInfo.topBottonObjects.get(0).kline.startTime.longValue();
                trendInfo.endTimeTrend = trendInfo.topBottonObjects.get(trendInfo.topBottonObjects.size() - 1).kline.endTime.longValue();
                if (i == btcTrends.size() - 1) {
                    trendInfo.timeNextTrend = System.currentTimeMillis();
                } else {
                    TrendObjectDetail nextTrendInfo = btcTrends.get(i + 1);
                    trendInfo.timeNextTrend = nextTrendInfo.topBottonObjects.get(nextTrendInfo.topBottonObjects.size() - 1).kline.endTime.longValue();
                }
            }
        }
    }

    private Map<TrendObjectDetail, List<TrendDataTrackingObject>> getAllAltBehavior(List<TrendObjectDetail> btcTrends, Map<String, List<KlineObjectNumber>> symbol2Kline1Ds) {
        HashMap<TrendObjectDetail, List<TrendDataTrackingObject>> result = new HashMap<>();
        for (TrendObjectDetail btcTrend : btcTrends) {
            if (!btcTrend.status.equals(TrendState.SIDEWAY)) {
                result.put(btcTrend, extractTrendDataTracking(btcTrend, symbol2Kline1Ds));
            }
        }
        return result;
    }

    private List<TrendDataTrackingObject> extractTrendDataTracking(TrendObjectDetail btcTrend, Map<String, List<KlineObjectNumber>> symbol2Kline1Ds) {
        List<TrendDataTrackingObject> results = new ArrayList<>();
        for (Map.Entry<String, List<KlineObjectNumber>> entry : symbol2Kline1Ds.entrySet()) {
            String symbol = entry.getKey();
            List<KlineObjectNumber> tickers = entry.getValue();
            if (tickers.get(0).startTime > btcTrend.startTimeTrend) {
                continue;
            }
            TrendDataTrackingObject data = new TrendDataTrackingObject(symbol);
            for (KlineObjectNumber ticker : tickers) {
                if (ticker.startTime.longValue() == btcTrend.startTimeTrend) {
                    data.priceStart = ticker.priceClose;
                }
                if (ticker.startTime.longValue() == btcTrend.timeNextTrend + 1) {
                    data.priceEnd = ticker.priceClose;
                }
                if (ticker.startTime > btcTrend.startTimeTrend && ticker.startTime < btcTrend.timeNextTrend) {
                    if (data.priceMin == null || data.priceMin > ticker.minPrice) {
                        data.priceMin = ticker.minPrice;
                        data.timeMin = ticker.startTime.longValue();
                    }
                    if (data.priceMax == null || data.priceMax < ticker.maxPrice) {
                        data.priceMax = ticker.maxPrice;
                        data.timeMax = ticker.startTime.longValue();
                    }
                }
            }
            data.updateRate();
            results.add(data);
        }
        return results;
    }

    private void printAltBehavior(Map<TrendObjectDetail, List<TrendDataTrackingObject>> altBehaviors) throws IOException {
        for (Map.Entry<TrendObjectDetail, List<TrendDataTrackingObject>> entry : altBehaviors.entrySet()) {
            TrendObjectDetail btcTrend = entry.getKey();
            List<TrendDataTrackingObject> datas = entry.getValue();
//            LOG.info("{} {}", Utils.toJson(btcTrend), Utils.toJson(datas));
            StringBuilder builder = new StringBuilder();
            builder.append("Trend").append(",");
            builder.append("price open").append(",");
            builder.append("price close").append(",");
            builder.append("rate change").append(",");
            builder.append("time start").append(",");
            builder.append("time end").append(",");
            builder.append("time next trend").append(",");
            List<String> lines = new ArrayList<>();
            lines.add(builder.toString());
            builder.setLength(0);
            builder.append(btcTrend.status.toString()).append(",");
            builder.append(btcTrend.topBottonObjects.get(0).kline.priceClose).append(",");
            builder.append(btcTrend.topBottonObjects.get(btcTrend.topBottonObjects.size() - 1).kline.priceClose).append(",");
            builder.append(Utils.rateOf2Double(btcTrend.topBottonObjects.get(0).kline.priceClose, btcTrend.topBottonObjects.get(btcTrend.topBottonObjects.size() - 1).kline.priceClose)).append(",");
            builder.append(Utils.normalizeDateYYYYMMDD(btcTrend.startTimeTrend)).append(",");
            builder.append(Utils.normalizeDateYYYYMMDD(btcTrend.endTimeTrend)).append(",");
            builder.append(Utils.normalizeDateYYYYMMDD(btcTrend.timeNextTrend)).append(",");
            lines.add(builder.toString());
            builder.setLength(0);
            builder.append("Symbol").append(",");
            builder.append("price Start").append(",");
            builder.append("price end").append(",");
            builder.append("price max").append(",");
            builder.append("time max").append(",");
            builder.append("price min").append(",");
            builder.append("time min").append(",");
            builder.append("rate max").append(",");
            builder.append("rate min").append(",");
            builder.append("rate trend").append(",");
            lines.add(builder.toString());
            for (TrendDataTrackingObject data : datas) {
                builder.setLength(0);
                builder.append(data.symbol).append(",");
                builder.append(data.priceStart).append(",");
                builder.append(data.priceEnd).append(",");
                builder.append(data.priceMax).append(",");
                builder.append(Utils.normalizeDateYYYYMMDD(data.timeMax)).append(",");
                builder.append(data.priceMin).append(",");
                builder.append(Utils.normalizeDateYYYYMMDD(data.timeMin)).append(",");
                builder.append(data.rateMax).append(",");
                builder.append(data.rateMin).append(",");
                Double rateTrend = data.rateMax;
                if (btcTrend.status.equals(TrendState.TREND_DOWN)) {
                    rateTrend = data.rateMin;
                }
                builder.append(rateTrend).append(",");
                lines.add(builder.toString());
            }
            FileUtils.writeLines(new File("target/bgchange_" + Utils.normalizeDateYYYYMMDD(btcTrend.startTimeTrend) + "_" + Utils.normalizeDateYYYYMMDD(btcTrend.endTimeTrend) + ".csv"), lines);
        }
    }

    private void detectorTrendSymbol(String symbol) {
        List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_15M + symbol);
        List<TrendObject> trends = TickerFuturesHelper.extractTopBottomObjectInTicker(tickers);
        printTrendObject(trends);
    }

    private void printTrendObject(List<TrendObject> trends) {
        TrendObject lastTrend = trends.get(0);
        Double rateTotal = 0d;
        for (TrendObject trend : trends) {
            Double rate;
            if (trend.status.equals(TrendState.TOP)) {
                rate = Utils.rateOf2Double(trend.kline.maxPrice, lastTrend.kline.minPrice);
            } else {
                rate = Utils.rateOf2Double(trend.kline.minPrice, lastTrend.kline.maxPrice);
            }
            rateTotal += rate;
            String prefix = "";
            if (Math.abs(rate) > 0.02) {
                prefix = "------------";
            }
            LOG.info(" {} {} {} rate:{} min:{} max:{} starttime:{}", rateTotal, prefix, trend.status, rate,
                    trend.kline.minPrice, trend.kline.maxPrice, Utils.normalizeDateYYYYMMDDHHmm(trend.kline.startTime.longValue()));
            lastTrend = trend;
        }
    }

    private void extractRateAllCoinWithStartTime(long time) throws IOException {
        time = TickerFuturesHelper.nomalizeTimeWithExchange(time);
        Map<String, List<KlineObjectNumber>> symbol2Kline1Ds = TickerFuturesHelper.getAllKlineWithUpdateTime(Constants.INTERVAL_1D, Utils.TIME_DAY);
        TreeMap<Double, KlineObjectNumber> rate2ObjectKline = new TreeMap<>();
        for (Map.Entry<String, List<KlineObjectNumber>> entry : symbol2Kline1Ds.entrySet()) {
            String symbol = entry.getKey();
            List<KlineObjectNumber> tickers = entry.getValue();
            Double maxPrice = 0d;
            Double minPrice = 0d;
            Long timeMax = 0l;
            Double closePrice = tickers.get(tickers.size() - 1).priceClose;
            Double openPrice = 0d;
            for (KlineObjectNumber ticker : tickers) {
                if (ticker.startTime.longValue() >= time) {
                    if (ticker.startTime.longValue() == time) {
                        openPrice = ticker.priceOpen;
                        minPrice = ticker.minPrice;
                        maxPrice = ticker.maxPrice;
                    } else {
                        if (ticker.maxPrice > maxPrice) {
                            maxPrice = ticker.maxPrice;
                            timeMax = ticker.startTime.longValue();
                        }
                        if (ticker.minPrice < minPrice) {
                            minPrice = ticker.minPrice;
                        }
                    }
                }
            }
            Double rateMax = Utils.rateOf2Double(maxPrice, openPrice);
            Double rateCurrent = Utils.rateOf2Double(maxPrice, openPrice);
            KlineObjectNumber object = new KlineObjectNumber();
//            object.orther1 = symbol;
            object.priceClose = closePrice;
            object.maxPrice = maxPrice;
            object.minPrice = minPrice;
            object.priceOpen = openPrice;
            object.startTime = timeMax.doubleValue();
//            rate2ObjectKline.put(rateMax, object);
            rate2ObjectKline.put(rateCurrent, object);
        }
        StringBuilder builder = new StringBuilder();
        List<String> lines = new ArrayList<>();
        for (Map.Entry<Double, KlineObjectNumber> entry : rate2ObjectKline.entrySet()) {
            Double rate = entry.getKey();
            KlineObjectNumber object = entry.getValue();
//            LOG.info("{} open:{} Close{} max:{} rateMax:{} rateCurrent:{}",
//                    object.orther1, object.priceOpen, object.priceClose, object.priceMax, rate, Utils.rateOf2Double(object.priceClose, object.priceOpen));
            builder.setLength(0);
//            builder.append(object.orther1).append(",");
            builder.append(object.priceOpen).append(",");
            builder.append(object.priceClose).append(",");
            builder.append(object.maxPrice).append(",");
            builder.append(Utils.rateOf2Double(object.maxPrice, object.priceOpen)).append(",");
            builder.append(Utils.rateOf2Double(object.priceClose, object.priceOpen)).append(",");
            builder.append(Utils.normalizeDateYYYYMMDD(object.startTime.longValue())).append(",");
            lines.add(builder.toString());
        }
        FileUtils.writeLines(new File("target/rateChange.csv"), lines);
    }

    private void extractRateAltCoinWithStartTime(long time) throws IOException {
        time = TickerFuturesHelper.nomalizeTimeWithExchange(time);
        Map<String, List<KlineObjectNumber>> symbol2Kline1Ds = TickerFuturesHelper.getAllKlineWithUpdateTime(Constants.INTERVAL_1D, Utils.TIME_DAY);
        TreeMap<Double, KlineObjectNumber> rate2ObjectKline = new TreeMap<>();
        Map<Double, String> rate2Symbol = new HashMap<>();
        for (Map.Entry<String, List<KlineObjectNumber>> entry : symbol2Kline1Ds.entrySet()) {
            String symbol = entry.getKey();
            List<KlineObjectNumber> tickers = entry.getValue();
            KlineObjectNumber tickerTime = null;
            for (KlineObjectNumber ticker : tickers) {
                if (ticker.startTime.longValue() >= time) {
                    tickerTime = ticker;
                    break;
                }
            }
            Double rateCurrent = Utils.rateOf2Double(tickerTime.priceClose, tickerTime.priceOpen);
//            rate2ObjectKline.put(rateMax, object);
            rate2ObjectKline.put(rateCurrent, tickerTime);
            rate2Symbol.put(rateCurrent, symbol);
        }
        StringBuilder builder = new StringBuilder();
        List<String> lines = new ArrayList<>();
        for (Map.Entry<Double, KlineObjectNumber> entry : rate2ObjectKline.entrySet()) {
            Double rate = entry.getKey();
            String symbol = rate2Symbol.get(rate);
            KlineObjectNumber object = entry.getValue();
//            LOG.info("{} open:{} Close{} max:{} rateMax:{} rateCurrent:{}",
//                    object.orther1, object.priceOpen, object.priceClose, object.priceMax, rate, Utils.rateOf2Double(object.priceClose, object.priceOpen));
            builder.setLength(0);
//            builder.append(object.orther1).append(",");
            builder.append(symbol).append(",");
            builder.append(object.priceOpen).append(",");
            builder.append(object.priceClose).append(",");
            builder.append(rate).append(",");

            lines.add(builder.toString());
        }
        FileUtils.writeLines(new File("target/rateChangeAlt.csv"), lines);
    }

    private void chartSymbol(String symbol) {
        List<TrendObject> trends = TickerFuturesHelper.extractTopBottomObjectInTicker(TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_15M));
        List<TrendObjectDetail> trendDetails = TickerFuturesHelper.detectTrendByKline(trends, 0.003);
        if (!trendDetails.isEmpty()
                && trendDetails.get(trendDetails.size() - 1).status.equals(TrendState.SIDEWAY)) {
            printTrendDetailObjectEnd(trendDetails, symbol);
        }
    }

}
