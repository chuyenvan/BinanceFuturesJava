package com.binance.chuyennd.bigchange.test;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.bigchange.statistic.data.DataStatisticHelper;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


import java.io.File;
import java.text.ParseException;
import java.util.*;

public class TraceData2Test {
    public static final Logger LOG = LoggerFactory.getLogger(TraceData2Test.class);

    public static void main(String[] args) throws ParseException {
//        String symbol = "TIAUSDT";
//        traceRateChangeCloseListOnExchange(symbol);
//        testTrendDetector(symbol);
        Long time = Utils.sdfFileHour.parse(Configs.getString("TIME_CHECK")).getTime();
        traceDataStatistic(time);
//        List<Long> timeBtcCutUp = extractBtcUpReverse();
//        diffFileCsv();
    }

    private static void diffFileCsv() {
        try {
            String file1 = "target/printDone.csv";
            String file2 = "target/printDone_max.csv";
            List<String> lines1 = FileUtils.readLines(new File(file1));
            List<String> lines2 = FileUtils.readLines(new File(file2));
            Set<String> order1s = readAllOrderByLevel(lines1, "MINI_DOWN");
            Set<String> order2s = readAllOrderByLevel(lines2, "MINI_DOWN");
            for (String order : order1s) {
                if (!order2s.contains(order)){
                    LOG.info("{} not in file2", order);
                }
            }
            for (String order : order2s) {
                if (!order1s.contains(order)){
                    LOG.info("{} not in file1", order);
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static Set<String> readAllOrderByLevel(List<String> lines1, String levelFilter) {
        Set<String> hashSet = new HashSet<>();
        for (String line1 : lines1) {
            String[] parts = StringUtils.split(line1, ",");
            String level = parts[9];
            if (level.equals(levelFilter)) {
                hashSet.add(parts[0] + " " + parts[7]);
            }
        }
        return hashSet;
    }

    private static void testTrendDetector(String symbol) {
        List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(DataManager.FOLDER_TICKER_15M + symbol);
        for (int i = 0; i < tickers.size(); i++) {
            if (MarketBigChangeDetectorTest.getSignalBuyAlt15M(tickers, i).contains(1)) {
                LOG.info("{} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(tickers.get(i).startTime.longValue()));
            }
        }
    }

    private static List<Long> extractBtcUpReverse() {
        List<Long> results = new ArrayList<>();
        try {
            List<KlineObjectNumber> btcTickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(DataManager.FOLDER_TICKER_15M + Constants.SYMBOL_PAIR_BTC);
            LOG.info("FinalTicker: {}", Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(btcTickers.size() - 1).startTime.longValue()));
            for (int i = 0; i < btcTickers.size(); i++) {
                KlineObjectNumber ticker = btcTickers.get(i);
                Long timeLong = ticker.startTime.longValue();
                KlineObjectNumber ticker2Hours = TickerFuturesHelper.extractKlineByNumberTicker(btcTickers, i, 8);
                KlineObjectNumber ticker24Hours = TickerFuturesHelper.extractKlineByNumberTicker(btcTickers, i, 32);
                if (ticker2Hours != null) {
                    Double breadAbove = Utils.rateOf2Double(ticker.maxPrice, ticker.priceOpen);
                    Double rateChange = Utils.rateOf2Double(ticker.maxPrice, ticker.minPrice);
                    if (breadAbove > 0.004 && rateChange > 0.005 && ticker.priceOpen > ticker.priceClose) {
                        if (ticker.maxPrice >= ticker2Hours.maxPrice) {
                            LOG.info("Btc UpdateReverse: {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()),
                                    Utils.rateOf2Double(ticker.priceClose, ticker24Hours.minPrice));
                        }
                    }
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }

        return null;
    }

    private static void traceDataStatistic(Long time) {
        Long duration = 48 * Utils.TIME_HOUR;
        Long numberTicker = duration / (15 * Utils.TIME_MINUTE);
        Long lastTime = time - 15 * Utils.TIME_MINUTE;
        try {
            Map<String, KlineObjectNumber> symbol2DataStatistic =
                    DataStatisticHelper.getInstance().readDataStaticByTimeAndNumberTickerStatic(time, numberTicker);
            TreeMap<Long, Map<String, KlineObjectNumber>> time2Tickers = DataManager.readDataFromFile(Utils.getDate(time));
            TreeMap<Long, Map<String, KlineObjectNumber>> time2LastTickers = DataManager.readDataFromFile(Utils.getDate(lastTime));
            Map<String, KlineObjectNumber> symbol2Ticker = time2Tickers.get(time);
            Map<String, KlineObjectNumber> symbol2LastTicker = time2LastTickers.get(lastTime);
            List<String> lines = new ArrayList<>();
            for (Map.Entry<String, KlineObjectNumber> entry : symbol2DataStatistic.entrySet()) {
                String symbol = entry.getKey();
                KlineObjectNumber tickerStatistic = entry.getValue();
                KlineObjectNumber lastTicker = symbol2LastTicker.get(symbol);
                KlineObjectNumber ticker = symbol2Ticker.get(symbol);
                StringBuilder builder = new StringBuilder();
                builder.append(symbol).append(",");
                builder.append(ticker.priceOpen).append(",");
                builder.append(ticker.priceClose).append(",");
                builder.append(ticker.maxPrice).append(",");
                builder.append(ticker.minPrice).append(",");
                builder.append(Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen)).append(",");
                builder.append(lastTicker.totalUsdt).append(",");
                builder.append(ticker.totalUsdt).append(",");
                builder.append(tickerStatistic.minPrice).append(",");
                builder.append(Utils.rateOf2Double(tickerStatistic.minPrice, ticker.priceClose )).append(",");
                builder.append(tickerStatistic.maxPrice);
                builder.append(Utils.rateOf2Double(tickerStatistic.maxPrice, ticker.priceClose )).append(",");
                lines.add(builder.toString());

            }
            String fileName = Utils.normalizeDateYYYYMMDDHHmm(time).replace(" ", "_");
            FileUtils.writeLines(new File("target/" + fileName.replace(":", "_") + ".csv"), lines);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void traceRateChangeCloseListOnExchange(String symbol) {
        List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_1D);
        for (KlineObjectNumber ticker : tickers) {
            Double rate = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
            if (rate != 0) {
                LOG.info("{} {} {}", Utils.normalizeDateYYYYMMDD(ticker.startTime.longValue()), rate, ticker.totalUsdt / 1E6);
            }
        }
    }
}
