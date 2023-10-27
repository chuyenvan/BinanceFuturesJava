/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd;

import com.binance.chuyennd.object.FilterSymbolWIthRateChange;
import com.binance.chuyennd.object.KlineObject;
import com.binance.chuyennd.object.TickerStatistics;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class TDWithRateChange {

    public static final Logger LOG = LoggerFactory.getLogger(TDWithRateChange.class);
    public static final String URL_KLINE_D1 = "https://api.binance.com/api/v3/klines?symbol=xxxxxx&interval=1d";

    public static void main(String[] args) throws IOException {
//        checkChangeRateAllSymbolInmonth();
//        exportDataFilterWithRateChange();
//        exportDataFilterWithRateChange();
        TDbyRateChange();
        System.exit(1);
    }

    private static void checkChangeRateAllSymbolInmonth() {
        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
//        TickerStatistics
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
        for (Object futurePrice : futurePrices) {
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (ticker.getLastPrice().equals(ticker.getHighPrice())) {
                LOG.info("Symbol price api erorr: {}", ticker.getSymbol());
            } else {
                // get all 1d 
                // get price max, min, current, rate change
                getData(ticker.getSymbol());
            }
        }
    }

    private static boolean getData(String symbol) {
        String urlM1 = URL_KLINE_D1.replace("xxxxxx", symbol);
        String respon = HttpRequest.getContentFromUrl(urlM1);
        try {
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            KlineObject klineObjectFinal = KlineObject.convertString2Kline(allKlines.get(allKlines.size() - 1));
            Double volumeAvg = 0d;
            Double maxPrice = 0d;
            Double minPrice = 0d;
            Double currentPrice = Double.parseDouble(klineObjectFinal.priceClose);
            for (List<Object> kline : allKlines) {
                KlineObject klineObject = KlineObject.convertString2Kline(kline);
                if (System.currentTimeMillis() - klineObject.startTime > Utils.TIME_DAY * 30) {
                    continue;
                }
                if (maxPrice < Double.parseDouble(klineObject.priceMax)) {
                    maxPrice = Double.parseDouble(klineObject.priceMax);
                }
                if (minPrice == 0d || minPrice > Double.parseDouble(klineObject.priceMin)) {
                    minPrice = Double.parseDouble(klineObject.priceMin);
                }
                volumeAvg += Double.parseDouble(klineObject.volume);
            }
            volumeAvg = volumeAvg / allKlines.size();
            double rateMax = (maxPrice - currentPrice) / currentPrice;
            double rateMin = (currentPrice - minPrice) / currentPrice;
            double rateChange = (maxPrice - minPrice) / currentPrice;
            LOG.info("{}: min: {} max: {} current: {} rateMax: {} rateMin: {} rateChange: {} volumeAvg:{} : volumeCurrent: {}", symbol, minPrice, maxPrice, currentPrice, Utils.formatPercent(rateMax), Utils.formatPercent(rateMin), Utils.formatPercent(rateChange), volumeAvg, klineObjectFinal.volume);

        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
    }

    private static void exportDataFilterWithRateChange() throws IOException {
        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
//        TickerStatistics
        List<FilterSymbolWIthRateChange> datas = new ArrayList();
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
        for (Object futurePrice : futurePrices) {
            List<Double> pricesByKline = new ArrayList();
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (ticker.getLastPrice().equals(ticker.getHighPrice())) {
                LOG.info("Symbol price api erorr: {}", ticker.getSymbol());
            } else {
                if (!StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt") || StringUtils.containsIgnoreCase(ticker.getSymbol(), "usdc")) {
                    LOG.info("Reject all stable coin or not pair usdt: {}", ticker.getSymbol());
                    continue;
                }
                // get all 1d 
                // get price max, min, current, rate change
                String urlM1 = URL_KLINE_D1.replace("xxxxxx", ticker.getSymbol());
                String respon = HttpRequest.getContentFromUrl(urlM1);
                try {
                    List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
                    KlineObject klineObjectFinal = KlineObject.convertString2Kline(allKlines.get(allKlines.size() - 1));
                    Double volumeAvg = 0d;
                    Double maxPriceTotal = 0d;
                    Double minPriceTotal = 0d;
                    Double maxPriceMonth = 0d;
                    Double minPriceMonth = 0d;
                    Double currentPrice = Double.valueOf(klineObjectFinal.priceClose);
                    for (List<Object> kline : allKlines) {
                        KlineObject klineObject = KlineObject.convertString2Kline(kline);

                        if (maxPriceTotal < Double.valueOf(klineObject.priceMax)) {
                            maxPriceTotal = Double.valueOf(klineObject.priceMax);
                        }
                        if (minPriceTotal == 0d || minPriceTotal > Double.valueOf(klineObject.priceMin)) {
                            minPriceTotal = Double.valueOf(klineObject.priceMin);
                        }
                        // get data current month
                        if (System.currentTimeMillis() - klineObject.startTime > Utils.TIME_DAY * 30) {
                            continue;
                        }
                        if (maxPriceMonth < Double.valueOf(klineObject.priceMax)) {
                            maxPriceMonth = Double.valueOf(klineObject.priceMax);
                        }
                        if (minPriceMonth == 0d || minPriceMonth > Double.valueOf(klineObject.priceMin)) {
                            minPriceMonth = Double.valueOf(klineObject.priceMin);
                        }
                        volumeAvg += Double.parseDouble(klineObject.volume);
                        pricesByKline.add(Double.valueOf(klineObject.priceClose));
                    }
                    volumeAvg = volumeAvg / allKlines.size();
                    double rateMin = (currentPrice - minPriceMonth) / currentPrice;
                    double rateChange = (maxPriceMonth - minPriceMonth) / currentPrice;
                    FilterSymbolWIthRateChange data = new FilterSymbolWIthRateChange();
                    data.maxPriceByDate = pricesByKline;
                    data.symbol = ticker.getSymbol();
                    data.currentPrice = currentPrice;
                    data.maxPriceInMonth = maxPriceMonth;
                    data.minPriceInMonth = minPriceMonth;
                    data.maxPriceTotal = maxPriceTotal;
                    data.minPriceTotal = minPriceTotal;
                    data.volume = volumeAvg;
                    data.rateWithMinAndCurrent = rateMin;
                    data.rateTotal = rateChange;
                    datas.add(data);
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }
        List<String> lines = new ArrayList();
        for (FilterSymbolWIthRateChange data : datas) {
            lines.add(data.toString());
        }
        FileUtils.writeLines(new File("target/filterSymbol.csv"), lines);
    }

    private static void TDbyRateChange() throws IOException {
        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
//        get data
        List<FilterSymbolWIthRateChange> datas = new ArrayList();
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
        for (Object futurePrice : futurePrices) {
            List<Double> pricesByKline = new ArrayList();
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (ticker.getLastPrice().equals(ticker.getHighPrice())) {
                LOG.info("Symbol price api erorr: {}", ticker.getSymbol());
            } else {
                if (!StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt") || StringUtils.containsIgnoreCase(ticker.getSymbol(), "usdc")) {
                    LOG.info("Reject all stable coin or not pair usdt: {}", ticker.getSymbol());
                    continue;
                }
                // get all 1d 
                // get price max, min, current, rate change
                String urlM1 = URL_KLINE_D1.replace("xxxxxx", ticker.getSymbol());
                String respon = HttpRequest.getContentFromUrl(urlM1);
                try {
                    List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
                    KlineObject klineObjectFinal = KlineObject.convertString2Kline(allKlines.get(allKlines.size() - 1));
                    Double volumeAvg = 0d;
                    Double maxPriceTotal = 0d;
                    Double minPriceTotal = 0d;
                    Double maxPriceMonth = 0d;
                    Double minPriceMonth = 0d;
                    Double currentPrice = Double.valueOf(klineObjectFinal.priceClose);
                    for (List<Object> kline : allKlines) {
                        KlineObject klineObject = KlineObject.convertString2Kline(kline);

                        if (maxPriceTotal < Double.valueOf(klineObject.priceMax)) {
                            maxPriceTotal = Double.valueOf(klineObject.priceMax);
                        }
                        if (minPriceTotal == 0d || minPriceTotal > Double.valueOf(klineObject.priceMin)) {
                            minPriceTotal = Double.valueOf(klineObject.priceMin);
                        }
                        // get data current month
                        if (System.currentTimeMillis() - klineObject.startTime > Utils.TIME_DAY * 30) {
                            continue;
                        }
                        if (maxPriceMonth < Double.valueOf(klineObject.priceMax)) {
                            maxPriceMonth = Double.valueOf(klineObject.priceMax);
                        }
                        if (minPriceMonth == 0d || minPriceMonth > Double.valueOf(klineObject.priceMin)) {
                            minPriceMonth = Double.valueOf(klineObject.priceMin);
                        }
                        volumeAvg += Double.parseDouble(klineObject.volume);
                        pricesByKline.add(Double.valueOf(klineObject.priceClose));
                    }
                    volumeAvg = volumeAvg / allKlines.size();
                    double rateMin = (currentPrice - minPriceMonth) / currentPrice;
                    double rateChange = (maxPriceMonth - minPriceMonth) / currentPrice;
                    FilterSymbolWIthRateChange data = new FilterSymbolWIthRateChange();
                    data.maxPriceByDate = pricesByKline;
                    data.symbol = ticker.getSymbol();
                    data.currentPrice = currentPrice;
                    data.maxPriceInMonth = maxPriceMonth;
                    data.minPriceInMonth = minPriceMonth;
                    data.maxPriceTotal = maxPriceTotal;
                    data.minPriceTotal = minPriceTotal;
                    data.volume = volumeAvg;
                    data.rateWithMinAndCurrent = rateMin;
                    data.rateTotal = rateChange;
                    datas.add(data);
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }
        // short by rate min
        List<Object> results = new ArrayList();
        for (FilterSymbolWIthRateChange data : datas) {
            results.add(data);
        }
        results = Utils.sortObjectByKey(results, "rateWithMinAndCurrent");
        for (FilterSymbolWIthRateChange data : datas) {
            LOG.info("{} {}", data.symbol, data.rateWithMinAndCurrent);
        }
    }
}