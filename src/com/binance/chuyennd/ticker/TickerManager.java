/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.ticker;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.indicators.MACD;
import com.binance.chuyennd.indicators.RelativeStrengthIndex;
import com.binance.chuyennd.indicators.SimpleMovingAverage;
import com.binance.chuyennd.mongo.TickerMongoHelper;
import com.binance.chuyennd.object.IndicatorEntry;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.MACDEntry;
import com.binance.chuyennd.object.RsiEntry;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.bson.Document;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * @author pc
 */
public class TickerManager {

    public static final Logger LOG = LoggerFactory.getLogger(TickerManager.class);

    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.getInt("NUMBER_THREAD_ORDER_MANAGER"));
    public int counter = 0;
    public int total = 0;

    public static void main(String[] args) throws ParseException {
//        new TickerManager().startThreadUpdateTicker();
//        new TickerManager().startThreadUpdateTicker15m();
//        new TickerManager().startUpdateTicker15m();
//        System.out.println(Utils.sdfFile.parse("20230101").getTime());
        new TickerManager().startResetTicker15mSimple();
//        new TickerManager().startResetTicker1hSimple();

//        new TickerManager().updateDataBySymbolSimple(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_1H);
//        new TickerManager().updateDataBySymbolSimple(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_4H);
//        new TickerManager().updateDataBySymbolSimple(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_1D);
//        printTicker(Constants.SYMBOL_PAIR_BTC);
//        printTicker("AMBUSDT");
//        new TickerManager().startResetTicker15m();
//        new TickerManager().updateAllTicker1h();
//        new TickerManager().updateAllTicker4h();
//        new TickerManager().updateAllTicker1d();
//        new TickerManager().updateDataBySymbol("LEVERUSDT");
//        new TickerManager().writeTicker15MMongo2File();
//        new TickerManager().writeTicker1dMMongo2File();

//        new TickerManager().updateTicker1hForASymbol("BLZUSDT");
//        new TickerManager().updateAllTicker1h("BLZUSDT");
//        new TickerManager().writeTicker1HourMongo2FileASymbol("BLZUSDT");
//        new TickerManager().updateTickerASymbol("PIXELUSDT");
//        System.exit(1);
    }

    private void startResetTicker1hSimple() {
        try {
            try {
                Set<String> symbols = TickerFuturesHelper.getAllSymbol();
                symbols.removeAll(Constants.diedSymbol);
                symbols.add(Constants.SYMBOL_PAIR_BTC);
                symbols.add("ETHUSDT");
                counter = 0;
                total = symbols.size();
                for (String symbol : symbols) {
                    executorService.execute(() -> updateDataBySymbolSimple(symbol, Constants.INTERVAL_1H));
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        } catch (Exception e) {
            LOG.error("ERROR during UpdateTicker15m: {}", e);
            e.printStackTrace();
        }
    }

    private static void printTicker(String symbol) {
        String fileName = DataManager.FOLDER_TICKER_15M + symbol;
        List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(fileName);
        for (KlineObjectNumber ticker : tickers) {
            LOG.info("{}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
        }
    }


    private void updateAllTicker1h() {
        for (String symbol : TickerMongoHelper.getInstance().getAllSymbol15m()) {
            try {
                updateTicker1hForASymbol(symbol);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        writeTicker1hMMongo2File();
    }

    private void updateAllTicker4h() {
        for (String symbol : TickerMongoHelper.getInstance().getAllSymbol15m()) {
            try {
                updateTicker4hForASymbol(symbol);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        writeTicker4hMMongo2File();
    }

    private void updateAllTicker1d() {
        for (String symbol : TickerMongoHelper.getInstance().getAllSymbol15m()) {
            try {
                updateTicker1dForASymbol(symbol);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        writeTicker1dMMongo2File();
    }

    private static void updateTicker1hForASymbol(String symbol) {
        LOG.info("Start update ticker 1h for {} ", symbol);
        TickerMongoHelper.getInstance().deleteTicker1h(symbol);
        List<KlineObjectNumber> allTickers = TickerFuturesHelper.getTickerWithStartTimeFull(symbol, Constants.INTERVAL_1H, 0);
        RsiEntry[] rsi = RelativeStrengthIndex.calculateRSI(allTickers, 14);
        MACDEntry[] entries = MACD.calculate(allTickers, 12, 26, 9);
        Map<Double, Double> time2Rsi = new HashMap<>();
        Map<Double, Double> time2Ma = new HashMap<>();
        Map<Double, MACDEntry> time2Macd = new HashMap<>();
        Map<Long, List<KlineObjectNumber>> time2Tickers = new HashMap<>();
        for (RsiEntry rs : rsi) {
            time2Rsi.put(rs.startTime, rs.getRsi());
        }
        for (MACDEntry entry : entries) {
            time2Macd.put(entry.startTime, entry);
        }
        IndicatorEntry[] smaEntries = SimpleMovingAverage.calculate(allTickers, 20);
        for (IndicatorEntry sma : smaEntries) {
            time2Ma.put(sma.startTime, sma.getValue());
        }
        for (KlineObjectNumber ticker : allTickers) {
            long timeDate = Utils.getDate(ticker.startTime.longValue());
            List<KlineObjectNumber> tickers = time2Tickers.get(timeDate);
            if (tickers == null) {
                tickers = new ArrayList<>();
                time2Tickers.put(timeDate, tickers);
            }
            tickers.add(ticker);
        }
        for (Map.Entry<Long, List<KlineObjectNumber>> entry : time2Tickers.entrySet()) {
            Long timeDate = entry.getKey();
            List<KlineObjectNumber> tickers = entry.getValue();
            List<Document> details = new ArrayList<>();
            Double maxPrice = null;
            Double minPrice = null;
            Double priceClose = null;
            Double priceOpen = null;
            for (KlineObjectNumber ticker : tickers) {
                details.add(Utils.convertTicker2Doc(ticker, time2Rsi, time2Ma, time2Macd));
                if (priceOpen == null) {
                    priceOpen = ticker.priceOpen;
                }
                priceClose = ticker.priceClose;
                if (maxPrice == null || maxPrice < ticker.maxPrice) {
                    maxPrice = ticker.maxPrice;
                }
                if (minPrice == null || minPrice > ticker.minPrice) {
                    minPrice = ticker.minPrice;
                }
            }
            Document doc = new Document();
            doc.append("sym", symbol);
            doc.append("date", timeDate);
            doc.append("priceOpen", priceOpen);
            doc.append("maxPrice", maxPrice);
            doc.append("minPrice", minPrice);
            doc.append("priceClose", priceClose);
            doc.append("details", details);
            TickerMongoHelper.getInstance().insertTicker1h(doc);
        }
        LOG.info("Finished update ticker 1h for {}", symbol);
    }

    private static void updateTicker4hForASymbol(String symbol) {
        LOG.info("Start update ticker 4h for {} ", symbol);
        TickerMongoHelper.getInstance().deleteTicker4h(symbol);
        List<KlineObjectNumber> allTickers = TickerFuturesHelper.getTickerWithStartTimeFull(symbol, Constants.INTERVAL_4H, 0);
        RsiEntry[] rsi = RelativeStrengthIndex.calculateRSI(allTickers, 14);
        MACDEntry[] entries = MACD.calculate(allTickers, 12, 26, 9);
        Map<Double, Double> time2Rsi = new HashMap<>();
        Map<Double, Double> time2Ma = new HashMap<>();
        Map<Double, MACDEntry> time2Macd = new HashMap<>();
        Map<Long, List<KlineObjectNumber>> time2Tickers = new HashMap<>();
        for (RsiEntry rs : rsi) {
            time2Rsi.put(rs.startTime, rs.getRsi());
        }
        for (MACDEntry entry : entries) {
            time2Macd.put(entry.startTime, entry);
        }
        IndicatorEntry[] smaEntries = SimpleMovingAverage.calculate(allTickers, 20);
        for (IndicatorEntry sma : smaEntries) {
            time2Ma.put(sma.startTime, sma.getValue());
        }
        for (KlineObjectNumber ticker : allTickers) {
            long timeDate = Utils.getDate(ticker.startTime.longValue());
            List<KlineObjectNumber> tickers = time2Tickers.get(timeDate);
            if (tickers == null) {
                tickers = new ArrayList<>();
                time2Tickers.put(timeDate, tickers);
            }
            tickers.add(ticker);
        }
        for (Map.Entry<Long, List<KlineObjectNumber>> entry : time2Tickers.entrySet()) {
            Long timeDate = entry.getKey();
            List<KlineObjectNumber> tickers = entry.getValue();
            List<Document> details = new ArrayList<>();
            Double maxPrice = null;
            Double minPrice = null;
            Double priceClose = null;
            Double priceOpen = null;
            for (KlineObjectNumber ticker : tickers) {
                details.add(Utils.convertTicker2Doc(ticker, time2Rsi, time2Ma, time2Macd));
                if (priceOpen == null) {
                    priceOpen = ticker.priceOpen;
                }
                priceClose = ticker.priceClose;
                if (maxPrice == null || maxPrice < ticker.maxPrice) {
                    maxPrice = ticker.maxPrice;
                }
                if (minPrice == null || minPrice > ticker.minPrice) {
                    minPrice = ticker.minPrice;
                }
            }
            Document doc = new Document();
            doc.append("sym", symbol);
            doc.append("date", timeDate);
            doc.append("priceOpen", priceOpen);
            doc.append("maxPrice", maxPrice);
            doc.append("minPrice", minPrice);
            doc.append("priceClose", priceClose);
            doc.append("details", details);
            TickerMongoHelper.getInstance().insertTicker4h(doc);
        }
        LOG.info("Finished update ticker 4h for {}", symbol);
    }

    private static void updateTicker1dForASymbol(String symbol) {
        LOG.info("Start update ticker 1d for {} ", symbol);
        TickerMongoHelper.getInstance().deleteTicker1d(symbol);
        List<KlineObjectNumber> allTickers = TickerFuturesHelper.getTickerWithStartTimeFull(symbol, Constants.INTERVAL_1D, 0);
        RsiEntry[] rsi = RelativeStrengthIndex.calculateRSI(allTickers, 14);

        MACDEntry[] entries = MACD.calculate(allTickers, 12, 26, 9);
        Map<Double, Double> time2Rsi = new HashMap<>();
        Map<Double, Double> time2Ma = new HashMap<>();
        Map<Double, MACDEntry> time2Macd = new HashMap<>();
        Map<Long, List<KlineObjectNumber>> time2Tickers = new HashMap<>();
        for (RsiEntry rs : rsi) {
            time2Rsi.put(rs.startTime, rs.getRsi());
        }
        for (MACDEntry entry : entries) {
            time2Macd.put(entry.startTime, entry);
        }
        IndicatorEntry[] smaEntries = SimpleMovingAverage.calculate(allTickers, 20);
        for (IndicatorEntry sma : smaEntries) {
            time2Ma.put(sma.startTime, sma.getValue());
        }
        for (KlineObjectNumber ticker : allTickers) {
            long timeDate = Utils.getDate(ticker.startTime.longValue());
            List<KlineObjectNumber> tickers = time2Tickers.get(timeDate);
            if (tickers == null) {
                tickers = new ArrayList<>();
                time2Tickers.put(timeDate, tickers);
            }
            tickers.add(ticker);
        }
        for (Map.Entry<Long, List<KlineObjectNumber>> entry : time2Tickers.entrySet()) {
            Long timeDate = entry.getKey();
            List<KlineObjectNumber> tickers = entry.getValue();
            List<Document> details = new ArrayList<>();
            Double maxPrice = null;
            Double minPrice = null;
            Double priceClose = null;
            Double priceOpen = null;
            for (KlineObjectNumber ticker : tickers) {
                details.add(Utils.convertTicker2Doc(ticker, time2Rsi, time2Ma, time2Macd));
                if (priceOpen == null) {
                    priceOpen = ticker.priceOpen;
                }
                priceClose = ticker.priceClose;
                if (maxPrice == null || maxPrice < ticker.maxPrice) {
                    maxPrice = ticker.maxPrice;
                }
                if (minPrice == null || minPrice > ticker.minPrice) {
                    minPrice = ticker.minPrice;
                }
            }
            Document doc = new Document();
            doc.append("sym", symbol);
            doc.append("date", timeDate);
            doc.append("priceOpen", priceOpen);
            doc.append("maxPrice", maxPrice);
            doc.append("minPrice", minPrice);
            doc.append("priceClose", priceClose);
            doc.append("details", details);
            TickerMongoHelper.getInstance().insertTicker1d(doc);
        }
        LOG.info("Finished update ticker 1d for {}", symbol);
    }

    public void writeTicker15MMongo2File() {
        for (String symbol : TickerMongoHelper.getInstance().getAllSymbol15m()) {
            LOG.info("Start executor read ticker of {} ", symbol);
            writeTicker15MMongo2FileASymbol(symbol);
        }
    }

    public void writeTicker1hMMongo2File() {
        for (String symbol : TickerMongoHelper.getInstance().getAllSymbol15m()) {
            LOG.info("Start executor read ticker of {} ", symbol);
            writeTicker1HourMongo2FileASymbol(symbol);
        }
    }

    public void writeTicker4hMMongo2File() {
        for (String symbol : TickerMongoHelper.getInstance().getAllSymbol15m()) {
            LOG.info("Start executor read ticker of {} ", symbol);
            writeTicker4HourMongo2FileASymbol(symbol);
        }
    }

    public void writeTicker1dMMongo2File() {
        for (String symbol : TickerMongoHelper.getInstance().getAllSymbol15m()) {
            LOG.info("Start executor read ticker of {} ", symbol);
            writeTicker1dMongo2FileASymbol(symbol);
        }
    }

    private static void writeTicker15MMongo2FileASymbol(String symbol) {
        List<KlineObjectNumber> tickers = TickerMongoHelper.getInstance().getTicker15mBySymbol(symbol);
        String fileName = "storage/ticker/symbols-15m/" + symbol;
        LOG.info("Write ticker of {} to file: {}", symbol, fileName);
        Storage.writeObject2File(fileName, tickers);
    }

    private static void writeTicker1HourMongo2FileASymbol(String symbol) {
        List<KlineObjectNumber> tickers = TickerMongoHelper.getInstance().getTicker1HourBySymbol(symbol);
        String fileName = "storage/ticker/symbols-1h/" + symbol;
        LOG.info("Write ticker of {} to file: {}", symbol, fileName);
        Storage.writeObject2File(fileName, tickers);
    }

    private static void writeTicker4HourMongo2FileASymbol(String symbol) {
        List<KlineObjectNumber> tickers = TickerMongoHelper.getInstance().getTicker4HourBySymbol(symbol);
        String fileName = "storage/ticker/symbols-4h/" + symbol;
        LOG.info("Write ticker of {} to file: {}", symbol, fileName);
        Storage.writeObject2File(fileName, tickers);
    }

    private static void writeTicker1dMongo2FileASymbol(String symbol) {
        List<KlineObjectNumber> tickers = TickerMongoHelper.getInstance().getTicker1dBySymbol(symbol);
        String fileName = "storage/ticker/symbols-1d/" + symbol;
        LOG.info("Write ticker of {} to file: {}", symbol, fileName);
        Storage.writeObject2File(fileName, tickers);
    }


    private void startUpdateTicker15m() {
        try {
            try {
                Set<String> symbols = TickerFuturesHelper.getAllSymbol();
                symbols.removeAll(Constants.diedSymbol);
                symbols.add(Constants.SYMBOL_PAIR_BTC);
                symbols.add("ETHUSDT");
                for (String symbol : symbols) {
                    executorService.execute(() -> updateTickerASymbol15m(symbol));
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            executorService.execute(() -> writeTicker15MMongo2File());
            Thread.sleep(Utils.TIME_DAY);
        } catch (Exception e) {
            LOG.error("ERROR during UpdateTicker15m: {}", e);
            e.printStackTrace();
        }
    }

    private void startResetTicker15m() {
        try {
            try {
                Set<String> symbols = TickerFuturesHelper.getAllSymbol();
                symbols.removeAll(Constants.diedSymbol);
                symbols.add(Constants.SYMBOL_PAIR_BTC);
                symbols.add("ETHUSDT");
                for (String symbol : symbols) {
                    executorService.execute(() -> updateDataBySymbol(symbol));
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            executorService.execute(() -> writeTicker15MMongo2File());

        } catch (Exception e) {
            LOG.error("ERROR during UpdateTicker15m: {}", e);
            e.printStackTrace();
        }
    }

    private void startResetTicker15mSimple() {
        try {
            try {
                Set<String> symbols = TickerFuturesHelper.getAllSymbol();
                symbols.removeAll(Constants.diedSymbol);
                symbols.add(Constants.SYMBOL_PAIR_BTC);
                symbols.add("ETHUSDT");
                counter = 0;
                total = symbols.size();
                for (String symbol : symbols) {
                    executorService.execute(() -> updateDataBySymbolSimple(symbol, Constants.INTERVAL_15M));
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        } catch (Exception e) {
            LOG.error("ERROR during UpdateTicker15m: {}", e);
            e.printStackTrace();
        }
    }


    private void updateTickerASymbol15m(String symbol) {
        try {
            LOG.info("Start update ticker 15m for {}", symbol);
            Long date = TickerMongoHelper.getInstance().getLastDateTicker15mBySymbol(symbol);
            LOG.info("update ticker 15m for {} from: {}", symbol, new Date(date));
            updateDataByDate(symbol, date);
            LOG.info("Finished update ticker 15m for {}", symbol);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }


    private void updateDataByDate(String symbol, Long date) {
        List<KlineObjectNumber> allTickers = TickerFuturesHelper.getTickerWithStartTimeFull(symbol, Constants.INTERVAL_15M, date);
        if (date != 0) {
            // delete hour start update
            TickerMongoHelper.getInstance().deleteTicker15m(symbol, date);
        }
        Map<Long, List<KlineObjectNumber>> time2Tickers = new HashMap<>();

        for (KlineObjectNumber ticker : allTickers) {
            long timeDate = Utils.getDate(ticker.startTime.longValue());
            List<KlineObjectNumber> docs = time2Tickers.get(timeDate);
            if (docs == null) {
                docs = new ArrayList<>();
                time2Tickers.put(timeDate, docs);
            }
            docs.add(ticker);
        }
        for (Map.Entry<Long, List<KlineObjectNumber>> entry : time2Tickers.entrySet()) {
            Long timeDate = entry.getKey();
            List<KlineObjectNumber> tickers = entry.getValue();
            List<Document> details = new ArrayList<>();
            Double maxPrice = null;
            Double minPrice = null;
            Double priceClose = null;
            Double priceOpen = null;
            for (KlineObjectNumber ticker : tickers) {
                details.add(Utils.convertTicker2Doc(ticker));
                if (priceOpen == null) {
                    priceOpen = ticker.priceOpen;
                }
                priceClose = ticker.priceClose;
                if (maxPrice == null || maxPrice < ticker.maxPrice) {
                    maxPrice = ticker.maxPrice;
                }
                if (minPrice == null || minPrice > ticker.minPrice) {
                    minPrice = ticker.minPrice;
                }
            }
            Document doc = new Document();
            doc.append("sym", symbol);
            doc.append("date", timeDate);
            doc.append("priceOpen", priceOpen);
            doc.append("maxPrice", maxPrice);
            doc.append("minPrice", minPrice);
            doc.append("priceClose", priceClose);
            doc.append("details", details);
            TickerMongoHelper.getInstance().insertTicker15m(doc);
        }
    }

    private void updateDataBySymbol(String symbol) {
        List<KlineObjectNumber> allTickers = TickerMongoHelper.getInstance().getTicker15mBySymbol(symbol);
        Long lastTimeUpdate = 0l;
        if (allTickers.size() > 0) {
            lastTimeUpdate = allTickers.get(allTickers.size() - 1).startTime.longValue();
        }
        LOG.info("Start update ticker 15m for {} {}", symbol, lastTimeUpdate);

        allTickers.remove(allTickers.size() - 1);
        allTickers.addAll(TickerFuturesHelper.getTickerWithStartTimeFull(symbol, Constants.INTERVAL_15M, lastTimeUpdate));
        // delete hour start update
        TickerMongoHelper.getInstance().deleteTicker15m(symbol);

        Map<Long, List<KlineObjectNumber>> time2Tickers = new HashMap<>();
        RsiEntry[] rsi = RelativeStrengthIndex.calculateRSI(allTickers, 14);
        MACDEntry[] entries = MACD.calculate(allTickers, 12, 26, 9);
        IndicatorEntry[] smaEntries = SimpleMovingAverage.calculate(allTickers, 20);
        Map<Double, Double> time2Rsi = new HashMap<>();
        Map<Double, Double> time2Ma = new HashMap<>();
        Map<Double, MACDEntry> time2Macd = new HashMap<>();
        for (RsiEntry rs : rsi) {
            time2Rsi.put(rs.startTime, rs.getRsi());
        }
        for (MACDEntry entry : entries) {
            time2Macd.put(entry.startTime, entry);
        }
        for (IndicatorEntry sma : smaEntries) {
            time2Ma.put(sma.startTime, sma.getValue());
        }
        for (KlineObjectNumber ticker : allTickers) {
            long timeDate = Utils.getDate(ticker.startTime.longValue());
            List<KlineObjectNumber> docs = time2Tickers.get(timeDate);
            if (docs == null) {
                docs = new ArrayList<>();
                time2Tickers.put(timeDate, docs);
            }
            docs.add(ticker);
        }
        for (Map.Entry<Long, List<KlineObjectNumber>> entry : time2Tickers.entrySet()) {
            Long timeDate = entry.getKey();
            List<KlineObjectNumber> tickers = entry.getValue();
            List<Document> details = new ArrayList<>();
            Double maxPrice = null;
            Double minPrice = null;
            Double priceClose = null;
            Double priceOpen = null;
            for (KlineObjectNumber ticker : tickers) {
                details.add(Utils.convertTicker2Doc(ticker, time2Rsi, time2Ma, time2Macd));
                if (priceOpen == null) {
                    priceOpen = ticker.priceOpen;
                }
                priceClose = ticker.priceClose;
                if (maxPrice == null || maxPrice < ticker.maxPrice) {
                    maxPrice = ticker.maxPrice;
                }
                if (minPrice == null || minPrice > ticker.minPrice) {
                    minPrice = ticker.minPrice;
                }
            }
            Document doc = new Document();
            doc.append("sym", symbol);
            doc.append("date", timeDate);
            doc.append("priceOpen", priceOpen);
            doc.append("maxPrice", maxPrice);
            doc.append("minPrice", minPrice);
            doc.append("priceClose", priceClose);
            doc.append("details", details);
            TickerMongoHelper.getInstance().insertTicker15m(doc);
        }
        LOG.info("Finished update ticker 15m for {}", symbol);
    }

    private void updateDataBySymbolSimple(String symbol, String interval) {
        try {
            counter++;
            LOG.info("Process: {}/{}", counter, total);
            LOG.info("Start get ticker symbol: {} {}", symbol, interval);
            Long startTime = 1672506000000L;
            String fileName = null;
            switch (interval) {
                case Constants.INTERVAL_1D:
                    fileName = DataManager.FOLDER_TICKER_1D;
                    break;
                case Constants.INTERVAL_4H:
                    fileName = DataManager.FOLDER_TICKER_4HOUR;
                    break;
                case Constants.INTERVAL_1H:
                    fileName = DataManager.FOLDER_TICKER_HOUR;
                    break;
                case Constants.INTERVAL_15M:
                    fileName = DataManager.FOLDER_TICKER_15M;
                    break;
            }
            fileName = fileName + symbol;
            List<KlineObjectNumber> tickers;
            if (new File(fileName).exists()) {
                tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(fileName);
                startTime = tickers.get(tickers.size() - 1).startTime.longValue();
                tickers.remove(tickers.size() - 1);
            } else {
                tickers = new ArrayList<>();
            }
            tickers.addAll(TickerFuturesHelper.getTickerWithStartTimeFull(symbol, interval, startTime));
            tickers = TickerFuturesHelper.updateIndicator(tickers);
            LOG.info("Write ticker of {} {} {} to file: {}", symbol, interval, tickers.size(), fileName);
            Storage.writeObject2File(fileName, tickers);
            LOG.info("Finish get ticker symbol: {} {}", symbol, interval);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

}
