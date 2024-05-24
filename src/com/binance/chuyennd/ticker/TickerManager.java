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
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;

import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import org.bson.Document;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * @author pc
 */
public class TickerManager {

    public static final Logger LOG = LoggerFactory.getLogger(TickerManager.class);

    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.getInt("NUMBER_THREAD_ORDER_MANAGER"));

    public static void main(String[] args) {
//        new TickerManager().startThreadUpdateTicker();
//        new TickerManager().startThreadUpdateTicker15m();
//        new TickerManager().startUpdateTicker15m();
        new TickerManager().startResetTicker15m();
        new TickerManager().updateAllTicker1h();
        new TickerManager().updateAllTicker4h();
        new TickerManager().updateAllTicker1d();

//        new TickerManager().updateDataBySymbol("LEVERUSDT");
//        new TickerManager().writeTicker15MMongo2File();
//        new TickerManager().writeTicker1hMMongo2File();

//        new TickerManager().updateTicker1hForASymbol("BLZUSDT");
//        new TickerManager().updateAllTicker1h("BLZUSDT");
//        new TickerManager().writeTicker1HourMongo2FileASymbol("BLZUSDT");
//        new TickerManager().updateTickerASymbol("PIXELUSDT");
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
        TickerMongoHelper.getInstance().deleteTicker4h(symbol);
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
            executorService.execute(() -> writeTicker15MMongo2FileASymbol(symbol));
        }
    }

    public void writeTicker1hMMongo2File() {
        for (String symbol : TickerMongoHelper.getInstance().getAllSymbol15m()) {
            LOG.info("Start executor read ticker of {} ", symbol);
            executorService.execute(() -> writeTicker1HourMongo2FileASymbol(symbol));
        }
    }

    public void writeTicker4hMMongo2File() {
        for (String symbol : TickerMongoHelper.getInstance().getAllSymbol15m()) {
            LOG.info("Start executor read ticker of {} ", symbol);
            executorService.execute(() -> writeTicker4HourMongo2FileASymbol(symbol));
        }
    }

    public void writeTicker1dMMongo2File() {
        for (String symbol : TickerMongoHelper.getInstance().getAllSymbol15m()) {
            LOG.info("Start executor read ticker of {} ", symbol);
            executorService.execute(() -> writeTicker1dMongo2FileASymbol(symbol));
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
                symbols.removeAll(Constants.specialSymbol);
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
                symbols.removeAll(Constants.specialSymbol);
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

        Map<Double, Double> time2Rsi = new HashMap<>();
        Map<Double, Double> time2Ma = new HashMap<>();
        Map<Double, MACDEntry> time2Macd = new HashMap<>();
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

}
