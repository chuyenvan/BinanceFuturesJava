package com.binance.chuyennd.bigchange.test;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.bigchange.statistic.data.DataStatisticHelper;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
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
        // for debug
//        args = new String[4];
//        args[0] = "rate_change";
//        args[3] = "btc";
//        args[1] = "20210201";
//        args[2] = "07:05";
        // end debug
        if (args.length > 2) {
            traceDataByHand(args);
        } else {

//        String symbol = "TIAUSDT";
//        traceRateChangeCloseListOnExchange(symbol);
//        testTrendDetector(symbol);
            Long time = Utils.sdfFileHour.parse(Configs.getString("TIME_CHECK")).getTime();
//        traceDataRateChange(time);
            traceDataStatistic(time);
//        printRateChange1MofBTC();
//        List<Long> timeBtcCutUp = extractBtcUpReverse();
//        diffFileCsv();
        }
    }

    private static void traceDataRateChange(Long startTime) {

        TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
        time2Tickers = DataManager.readDataFromFile1M(startTime);
        LOG.info("Check time:{}", startTime);
        if (time2Tickers != null) {
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                Long time = entry.getKey();
                Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                TreeMap<Double, String> rateDown2Symbols = new TreeMap<>();
                TreeMap<Double, String> rateUp2Symbols = new TreeMap<>();
                for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
                    String symbol = entry1.getKey();
                    if (Constants.diedSymbol.contains(symbol)) {
                        continue;
                    }

                    KlineObjectSimple ticker = entry1.getValue();
                    // update order Old

                    if (Utils.isTickerAvailable(ticker)) {
                        Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
                        rateDown2Symbols.put(rateChange, symbol);
                        rateUp2Symbols.put(-rateChange, symbol);
                    }
                }
                // stop trade when capital over
//                        if (BudgetManagerSimple.getInstance().isAvailableTrade()) {
                KlineObjectSimple btcTicker = symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC);
                Double btcRateChange = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen);
                Double rateChangeDownAvg = MarketBigChangeDetectorTest.calRateLossAvg(rateDown2Symbols, 50);
                Double rateChangeUpAvg = -MarketBigChangeDetectorTest.calRateLossAvg(rateUp2Symbols, 50);
                LOG.info("{} down:{} up:{} btcRate:{} btcVol:{}", Utils.normalizeDateYYYYMMDDHHmm(time),
                        Utils.formatDouble(rateChangeDownAvg * 100, 2), Utils.formatDouble(rateChangeUpAvg * 100, 2),
                        Utils.formatDouble(btcRateChange * 100, 2), btcTicker.totalUsdt / 1E6);
            }
        }
    }

    private static void traceDataByHand(String[] args) {
        LOG.info(args[0] + " " + args[1]);
        String mode = args[0];
        switch (mode) {
            case "rate_change":
                printData1M(args[1], args[2], args[3]);
                break;
            case "get_top_down":
                getTopDown(args[1], args[2]);
                break;
            case "get_top_up":
                getTopUp(args[1], args[2]);
                break;
            case "trace_loss":
                traceLog();
                break;
            case "trade_detail":
                try {
                    new TraceDetailAllDataWithTime().simulatorEntryByTime(args[1], args[2], args[3]);
                } catch (Exception e) {
                    e.printStackTrace();
                }
                break;
        }
    }

    private static Double extractProfitOfLine(String line) {
        try {
            String[] parts = StringUtils.split(line, ":");
            String pDate = parts[6];
            pDate = StringUtils.split(pDate, " ")[0];
            return Double.parseDouble(pDate);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }
    private static Double extractBalanceOfLine(String line) {
        try {
            String[] parts = StringUtils.split(line, ":");
            String pDate = parts[5];
            pDate = StringUtils.split(pDate, " ")[0];
            return Double.parseDouble(pDate);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    private static String extractDateOfLine(String line) {
        try {
            String[] parts = StringUtils.split(line, " ");
            String date = parts[6];
            return date;
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    private static void traceLog() {
        try {
//            System.out.println(extractProfitOfLine("2024-09-01 10:58:13,545  INFO [main] BudgetManagerSimple: Update-1-1 20240901 07:00 => balance:87221 pDate:-1211 0%  margin:159 0% profit:95561 unProfit:5 0% unProfitMin:-690 -34.51% fee:10340 done: 5343/10334 run:"));
//            System.out.println(extractDateOfLine("2024-09-01 10:58:13,545  INFO [main] BudgetManagerSimple: Update-1-1 20240901 07:00 => balance:87221 pDate:-1211 0%  margin:159 0% profit:95561 unProfit:5 0% unProfitMin:-690 -34.51% fee:10340 done: 5343/10334 run:"));
            List<String> lines = FileUtils.readLines(new File("../simulator/logs/nohup.out"));
            // 2024-09-01 10:58:13,545  INFO [main] BudgetManagerSimple: Update-1-1 20240901 07:00 => balance:87221 pDate:0 0%  margin:159 0% profit:95561 unProfit:5 0% unProfitMin:-690 -34.51% fee:10340 done: 5343/10334 run:
            TreeMap<Double, String> profit2Date = new TreeMap();
            TreeMap<Long, Double> date2Profit = new TreeMap();
            TreeMap<Long, Double> date2Balance = new TreeMap();
            for (String line : lines) {
                if (StringUtils.contains(line, "Update-")) {
                    Double profit = extractProfitOfLine(line);
                    Double balance = extractBalanceOfLine(line);
                    String date = extractDateOfLine(line);
//                    LOG.info("Balance: {} {}",date, balance);
                    profit2Date.put(profit, date);
                    date2Profit.put(Utils.sdfFile.parse(date).getTime(), profit);
                    date2Balance.put(Utils.sdfFile.parse(date).getTime(), balance);
                }
            }
            TreeMap<Double, Long> profit30d2Date = new TreeMap();
            int counter = 0;
            Set<String> hashSet = new HashSet<>();
            for (Map.Entry<Double, String> entry : profit2Date.entrySet()) {
                if (hashSet.contains(entry.getValue())) {
                    continue;
                }
                LOG.info("{} {}", entry.getValue(), entry.getKey());
                hashSet.add(entry.getValue());
                counter++;
                if (counter > 10) {
                    break;
                }
            }
            Long dateFirst = date2Profit.firstKey();
            for (int i = 30; i < date2Profit.size(); i++) {
                Double profit30d = 0d;
                for (int j = 0; j < 30; j++) {
                    Long date30 = dateFirst + (i - 30 + j) * Utils.TIME_DAY;
                    profit30d += date2Profit.get(date30);
                }
                profit30d2Date.put(profit30d, dateFirst + i * Utils.TIME_DAY);
            }
            counter = 0;
            Double profit2021 = date2Balance.get(Utils.sdfFile.parse("20220101").getTime()) - date2Balance.firstEntry().getValue();
            Double profit2022 = date2Balance.get(Utils.sdfFile.parse("20230101").getTime())
                    - date2Balance.get(Utils.sdfFile.parse("20220101").getTime());
            Double profit2023 = date2Balance.get(Utils.sdfFile.parse("20240101").getTime()) -
                    date2Balance.get(Utils.sdfFile.parse("20230101").getTime());
            Double profit2024 = date2Balance.lastEntry().getValue() - date2Balance.get(Utils.sdfFile.parse("20240101").getTime());
            LOG.info("Year 2021: {} \t{}\t{}",date2Balance.get(Utils.sdfFile.parse("20220101").getTime()),
                    profit2021, Utils.formatDouble(profit2021/2000, 2));
            LOG.info("Year 2022: {}\t{}\t{}",date2Balance.get(Utils.sdfFile.parse("20230101").getTime()),
                    profit2022, Utils.formatDouble(profit2022/2000, 2));
            LOG.info("Year 2023: {}\t{}\t{}",date2Balance.get(Utils.sdfFile.parse("20240101").getTime()),
                    profit2023, Utils.formatDouble(profit2023/2000, 2));
            LOG.info("Year 2024: {}\t{}\t{}",date2Balance.lastEntry().getValue(),
                    profit2024, Utils.formatDouble(profit2024/2000, 2));
            for (Map.Entry<Double, Long> entry : profit30d2Date.entrySet()) {
                LOG.info("{} {}", Utils.normalizeDateYYYYMMDD(entry.getValue()), entry.getKey());
                counter++;
                if (counter > 10) {
                    break;
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    private static void printData1M(String timeInput1, String timeInput2, String symbol) {
        try {
            String timeInput = timeInput1.trim() + " " + timeInput2.trim();
            if (!timeInput1.startsWith("202")) {
                timeInput = timeInput2.trim() + " " + symbol.trim();
                symbol = timeInput1;
            }
            Long time = Utils.sdfFileHour.parse(timeInput).getTime();
//            Long time = Utils.sdfFileHour.parse("20230724 16:50").getTime();
//            String symbol = "KEYUSDT";
            Long startTime = Utils.getDate(time - 15 * Utils.TIME_MINUTE);

            // data ticker
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManager.readDataFromFile1M(startTime);
            TreeMap<Long, Map<String, KlineObjectSimple>> dataNextDate = DataManager.readDataFromFile1M(startTime + Utils.TIME_DAY);
            TreeMap<Long, Map<String, KlineObjectSimple>> dataNext1Date = DataManager.readDataFromFile1M(startTime + 2 * Utils.TIME_DAY);
            if (dataNextDate != null) {
                time2Tickers.putAll(dataNextDate);
            }
            if (dataNext1Date != null) {
                time2Tickers.putAll(dataNext1Date);
            }
            if (!StringUtils.containsIgnoreCase(symbol, "USDT")) {
                symbol += "USDT";
            }
            symbol = symbol.toUpperCase();
            LOG.info("{} {} {} {} {}", time, startTime, Utils.normalizeDateYYYYMMDDHHmm(startTime), time2Tickers.size());
            Double priceEntry = time2Tickers.get(time).get(symbol).priceClose;
            Double minPrice = 0d;
            Double maxPrice = 0d;
            for (int i = -2; i < 3000; i++) {
                Long timeCheck = time + i * Utils.TIME_MINUTE;
                Map<String, KlineObjectSimple> symbol2Ticker = time2Tickers.get(timeCheck);
                if (symbol2Ticker == null) {
                    if (i < 0) {
                        continue;
                    } else {
                        break;
                    }
                }
                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                if (i > 0 && (minPrice == 0d || minPrice > ticker.minPrice)) {
                    minPrice = ticker.minPrice;
                }
                if (i > 0 && (maxPrice == 0d || maxPrice < ticker.maxPrice)) {
                    maxPrice = ticker.maxPrice;
                }
                Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
                Double rateChangeMax = Utils.rateOf2Double(ticker.maxPrice, ticker.priceOpen);
                Double rateChangeMin = Utils.rateOf2Double(ticker.minPrice, ticker.priceOpen);
                Double rateEntry = 0D;
                Double rateEntryMin = 0D;
                Double rateEntryMax = 0d;
                if (i > 0) {
                    rateEntry = Utils.rateOf2Double(ticker.priceClose, priceEntry);
                    rateEntryMin = Utils.rateOf2Double(minPrice, priceEntry);
                    rateEntryMax = Utils.rateOf2Double(maxPrice, priceEntry);
                }
                if (i < 29
                        || timeCheck % (4 * Utils.TIME_HOUR) == 0
                        || timeCheck.equals(time2Tickers.lastKey())
                ) {
                    LOG.info("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}", Utils.normalizeDateYYYYMMDDHHmm(timeCheck),
                            Utils.formatDouble(rateChange * 100, 2),
                            Utils.formatDouble(rateChangeMax * 100, 2),
                            Utils.formatDouble(rateChangeMin * 100, 2),
                            Utils.formatDouble(rateEntryMax * 100, 2),
                            Utils.formatDouble(rateEntryMin * 100, 2),
                            Utils.formatDouble(rateEntry * 100, 2),
                            priceEntry, ticker.totalUsdt,
                            ticker.priceClose);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void getTopDown(String timeInput1, String timeInput2) {
        try {
            String timeInput = timeInput1.trim() + " " + timeInput2.trim();
            Long time = Utils.sdfFileHour.parse(timeInput).getTime();
            Long startTime = Utils.getDate(time - 15 * Utils.TIME_MINUTE);

            // data ticker
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManager.readDataFromFile1M(startTime);
            TreeMap<Long, Map<String, KlineObjectSimple>> dataNextDate = DataManager.readDataFromFile1M(startTime + Utils.TIME_DAY);
            TreeMap<Long, Map<String, KlineObjectSimple>> dataNext1Date = DataManager.readDataFromFile1M(startTime + 2 * Utils.TIME_DAY);
            if (dataNextDate != null) {
                time2Tickers.putAll(dataNextDate);
            }
            if (dataNext1Date != null) {
                time2Tickers.putAll(dataNext1Date);
            }
            Map<String, Double> symbol2MaxPrice = new HashMap<>();
            Map<String, Double> symbol2MinPrice = new HashMap<>();
            Map<String, Double> symbol2Volume = new HashMap<>();
            for (int i = 1; i < 16; i++) {
                Map<String, KlineObjectSimple> symbol2Ticker = time2Tickers.get(time - i * Utils.TIME_MINUTE);
                for (String symbol : symbol2Ticker.keySet()) {
                    KlineObjectSimple kline = symbol2Ticker.get(symbol);
                    Double volume15m = symbol2Volume.get(symbol);
                    if (volume15m == null) {
                        volume15m = 0d;
                    }
                    volume15m += kline.totalUsdt;
                    symbol2Volume.put(symbol, volume15m);

                    Double priceMax = symbol2MaxPrice.get(symbol);
                    Double minPrice = symbol2MinPrice.get(symbol);
                    if (priceMax == null || priceMax < kline.maxPrice) {
                        priceMax = kline.maxPrice;
                    }
                    if (minPrice == null || minPrice > kline.minPrice) {
                        minPrice = kline.minPrice;
                    }
                    symbol2MaxPrice.put(symbol, priceMax);
                    symbol2MinPrice.put(symbol, minPrice);
                }
            }
            MarketDataObject marketData = MarketBigChangeDetectorTest.calMarketData(time2Tickers.get(time), symbol2MaxPrice,
                    symbol2MinPrice, symbol2Volume);
            List<String> symbols = MarketBigChangeDetectorTest.getTopSymbolSimple(marketData.rate2Max, 4, null);
            marketData.rate2Max.clear();
            LOG.info("{} {}", symbols, Utils.toJson(marketData));
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void getTopUp(String timeInput1, String timeInput2) {
        try {
            String timeInput = timeInput1.trim() + " " + timeInput2.trim();
            Long time = Utils.sdfFileHour.parse(timeInput).getTime();
            Long startTime = Utils.getDate(time);
            LOG.info("{} {} {}", time, startTime, Utils.normalizeDateYYYYMMDDHHmm(startTime));
            // data ticker
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManager.readDataFromFile1M(startTime);
            LOG.info("{}", MarketBigChangeDetectorTest.getTopUpSymbol2TradeSimple(time2Tickers.get(time), 4));
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void printRateChange1MofBTC() {
        List<KlineObjectNumber> btcTickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(
                Configs.FOLDER_TICKER_1M + Constants.SYMBOL_PAIR_BTC);
        List<String> lines = new ArrayList<>();
        lines.add("time, open, close, min, max, volume, rate");
        StringBuilder builder = new StringBuilder();
        for (KlineObjectNumber btcTicker : btcTickers) {
            builder.setLength(0);
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue())).append(",");
            builder.append(btcTicker.priceOpen).append(",");
            builder.append(btcTicker.priceClose).append(",");
            builder.append(btcTicker.minPrice).append(",");
            builder.append(btcTicker.maxPrice).append(",");
            builder.append(btcTicker.totalUsdt).append(",");
            builder.append(Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen));
            lines.add(builder.toString());
        }
        try {
            FileUtils.writeLines(new File("target/btc_1m_rate.csv"), lines);
        } catch (Exception e) {
            e.printStackTrace();
        }
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
                if (!order2s.contains(order)) {
                    LOG.info("{} not in file2", order);
                }
            }
            for (String order : order2s) {
                if (!order1s.contains(order)) {
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
        List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_15M + symbol);
        for (int i = 0; i < tickers.size(); i++) {
            if (MarketBigChangeDetectorTest.getSignalBuyAlt15M(tickers, i).contains(1)) {
                LOG.info("{} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(tickers.get(i).startTime.longValue()));
            }
        }
    }

    private static List<Long> extractBtcUpReverse() {
        List<Long> results = new ArrayList<>();
        try {
            List<KlineObjectNumber> btcTickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_15M + Constants.SYMBOL_PAIR_BTC);
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
                    DataStatisticHelper.getInstance().readDataStatic_15m(time, numberTicker);
            TreeMap<Long, Map<String, KlineObjectNumber>> time2Tickers = DataManager.readData15mFromFile(Utils.getDate(time));
            TreeMap<Long, Map<String, KlineObjectNumber>> time2LastTickers = DataManager.readData15mFromFile(Utils.getDate(lastTime));
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
                builder.append(Utils.rateOf2Double(tickerStatistic.minPrice, ticker.priceClose)).append(",");
                builder.append(tickerStatistic.maxPrice);
                builder.append(Utils.rateOf2Double(tickerStatistic.maxPrice, ticker.priceClose)).append(",");
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
