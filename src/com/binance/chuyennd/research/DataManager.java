package com.binance.chuyennd.research;

import com.binance.chuyennd.indicators.MACD;
import com.binance.chuyennd.indicators.RelativeStrengthIndex;
import com.binance.chuyennd.indicators.SimpleMovingAverage;
import com.binance.chuyennd.object.IndicatorEntry;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.MACDEntry;
import com.binance.chuyennd.object.RsiEntry;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class DataManager {
    public static final Logger LOG = LoggerFactory.getLogger(DataManager.class);
    public static String FOLDER_TICKER_15M = Configs.getString("FOLDER_TICKER_15M");//"../ticker/storage/ticker/symbols-15m/";
    public static String FOLDER_TICKER_15M_FILE = Configs.getString("FOLDER_TICKER_15M_FILE");//"../ticker/storage/ticker/symbols-15m/";
    public static String FOLDER_TICKER_HOUR = Configs.getString("FOLDER_TICKER_1H");//"../ticker/storage/ticker/symbols-1h/";
    public static String FOLDER_TICKER_4HOUR = Configs.getString("FOLDER_TICKER_4H");//"../ticker/storage/ticker/symbols-4h/";
    public static String FOLDER_TICKER_1D = Configs.getString("FOLDER_TICKER_1D");//"../ticker/storage/ticker/symbols-1D/";
    public static String FILE_DATA_LOADED = Configs.getString("FILE_DATA_LOADED");//"storage/macd_data_time";
    public static String FILE_DATA_BTC_RATING = Configs.getString("FILE_DATA_BTC_RATING_15M");//"storage/macd_data_time";
    private static volatile DataManager INSTANCE = null;
    public static final String TIME_RUN = Configs.getString("TIME_RUN");
    public ConcurrentHashMap<String, Map<String, Map<Long, KlineObjectNumber>>> interval2Symbol2TimeAndTicker;
    public ConcurrentHashMap<String, Map<String, List<KlineObjectNumber>>> interval2Symbol2Tickers;

    public static DataManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new DataManager();
            try {
                Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
                INSTANCE.initData(startTime);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return INSTANCE;
    }

    public static TreeMap<Long, Map<String, KlineObjectNumber>> readDataFromFile(Long startTime) {
        try {
            if (!new File(FOLDER_TICKER_15M_FILE).exists()) {
                DataManager.createDataKlineByTime();
            }
            String fileName = FOLDER_TICKER_15M_FILE + startTime;
            if (new File(fileName).exists()) {
                return (TreeMap<Long, Map<String, KlineObjectNumber>>) Storage.readObjectFromFile(fileName);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static void createDataKlineByTime() {
        LOG.info("Create data by time from ticker file!");
        File[] symbolFiles = new File(FOLDER_TICKER_15M).listFiles();
        Map<Long, TreeMap<Long, Map<String, KlineObjectNumber>>> date2timeAndSymbolKline = new HashMap<>();
        for (File symbolFile : symbolFiles) {
            String symbol = symbolFile.getName();
            if (!StringUtils.endsWithIgnoreCase(symbol, "usdt")) {
                continue;
            }
            List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(symbolFile.getPath());
            for (KlineObjectNumber ticker : tickers) {
                Long time = ticker.startTime.longValue();
                Long date = Utils.getDate(time);
                TreeMap<Long, Map<String, KlineObjectNumber>> time2SymbolKline = date2timeAndSymbolKline.get(date);
                if (time2SymbolKline == null) {
                    time2SymbolKline = new TreeMap<>();
                }
                Map<String, KlineObjectNumber> symbol2Kline = time2SymbolKline.get(time);
                if (symbol2Kline == null) {
                    symbol2Kline = new TreeMap<>();
                }
                symbol2Kline.put(symbol, ticker);
                time2SymbolKline.put(time, symbol2Kline);
                date2timeAndSymbolKline.put(date, time2SymbolKline);
            }
        }
        for (Map.Entry<Long, TreeMap<Long, Map<String, KlineObjectNumber>>> entry : date2timeAndSymbolKline.entrySet()) {
            Long date = entry.getKey();
            TreeMap<Long, Map<String, KlineObjectNumber>> values = entry.getValue();
            String fileName = "storage/ticker/tickerFile/" + date;
            Storage.writeObject2File(fileName, values);
        }

        LOG.info("Finish create data by time from ticker file!");
    }

    private void initData(Long startTime) {
        String fileData = FILE_DATA_LOADED + startTime;
        if (new File(fileData).exists()) {
            interval2Symbol2Tickers = (ConcurrentHashMap<String, Map<String, List<KlineObjectNumber>>>) Storage.readObjectFromFile(fileData);
        } else {
            interval2Symbol2Tickers = new ConcurrentHashMap<>();
            interval2Symbol2Tickers.put(Constants.INTERVAL_1H, getData(Constants.INTERVAL_1H, startTime));
            interval2Symbol2Tickers.put(Constants.INTERVAL_4H, getData(Constants.INTERVAL_4H, startTime));
            interval2Symbol2Tickers.put(Constants.INTERVAL_1D, getData(Constants.INTERVAL_1D, startTime));
            Storage.writeObject2File(fileData, interval2Symbol2Tickers);
        }
        interval2Symbol2TimeAndTicker = new ConcurrentHashMap<>();
        interval2Symbol2TimeAndTicker.put(Constants.INTERVAL_1H, traceData(interval2Symbol2Tickers.get(Constants.INTERVAL_1H)));
        interval2Symbol2TimeAndTicker.put(Constants.INTERVAL_4H, traceData(interval2Symbol2Tickers.get(Constants.INTERVAL_4H)));
        interval2Symbol2TimeAndTicker.put(Constants.INTERVAL_1D, traceData(interval2Symbol2Tickers.get(Constants.INTERVAL_1D)));
    }

    private Map<String, Map<Long, KlineObjectNumber>> traceData(Map<String, List<KlineObjectNumber>> symbol2Tickers) {
        Map<String, Map<Long, KlineObjectNumber>> results = new HashMap<>();
        for (Map.Entry<String, List<KlineObjectNumber>> entry : symbol2Tickers.entrySet()) {
            String symbol = entry.getKey();
            List<KlineObjectNumber> tickers = entry.getValue();
            Map<Long, KlineObjectNumber> time2Ticker = new HashMap<>();
            for (KlineObjectNumber ticker : tickers) {
                time2Ticker.put(ticker.startTime.longValue(), ticker);
            }
            results.put(symbol, time2Ticker);
        }
        return results;
    }

    private Map<String, List<KlineObjectNumber>> getData(String interval, Long startTime) {
        Map<String, List<KlineObjectNumber>> results = new HashMap<>();
        String folderData = null;
        switch (interval) {
            case Constants.INTERVAL_1H:
                folderData = FOLDER_TICKER_HOUR;
                break;
            case Constants.INTERVAL_4H:
                folderData = FOLDER_TICKER_4HOUR;
                break;
            case Constants.INTERVAL_1D:
                folderData = FOLDER_TICKER_1D;
                break;
        }
        if (folderData != null) {
            File[] symbolFiles = new File(folderData).listFiles();
            for (File symbolFile : symbolFiles) {
                String symbol = symbolFile.getName();
                if (!StringUtils.endsWithIgnoreCase(symbol, "usdt")) {
                    continue;
                }
                List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(symbolFile.getPath());
                results.put(symbol, tickers);
            }
        }
        return results;
    }

    public static Map<String, List<KlineObjectNumber>> readDataTicker(long startTime) {
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

    public static Map<String, List<KlineObjectNumber>> readFromFileSymbol(long startTime) {
        Map<String, List<KlineObjectNumber>> symbol2Tickers = new HashMap<>();
        File[] symbolFiles = new File(FOLDER_TICKER_15M).listFiles();
        long startAt = System.currentTimeMillis();
        for (File symbolFile : symbolFiles) {
            String symbol = symbolFile.getName();
            if (!StringUtils.endsWithIgnoreCase(symbol, "usdt")) {
                continue;
            }
//            LOG.info("File: {}", symbolFile.getPath());
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

    public static void main(String[] args) throws ParseException {
        DataManager.readFromFileSymbol(Utils.sdfFile.parse("20210101").getTime());
    }

    public KlineObjectNumber getTicker(String symbol, String interval, long time) {
        Map<String, Map<Long, KlineObjectNumber>> symbol2TImeAndTicker = interval2Symbol2TimeAndTicker.get(interval);
        if (symbol2TImeAndTicker != null) {
            Map<Long, KlineObjectNumber> time2Ticker = symbol2TImeAndTicker.get(symbol);
            if (time2Ticker != null) {
                return time2Ticker.get(time);
            }
        }
        return null;
    }

    public KlineObjectNumber updateData(KlineObjectNumber ticker15m, String symbol) {
        updateDataAInterval(Constants.INTERVAL_1H, ticker15m, symbol);
        updateDataAInterval(Constants.INTERVAL_4H, ticker15m, symbol);
        updateDataAInterval(Constants.INTERVAL_1D, ticker15m, symbol);
        return null;
    }

    private void updateDataAInterval(String interval, KlineObjectNumber ticker15m, String symbol) {
        List<KlineObjectNumber> tickers = interval2Symbol2Tickers.get(interval).get(symbol);
        Long time2LastTicker = null;
        switch (interval) {
            case Constants.INTERVAL_1H:
                time2LastTicker = Utils.getHour(ticker15m.startTime.longValue());
                break;
            case Constants.INTERVAL_4H:
                time2LastTicker = Utils.get4Hour(ticker15m.startTime.longValue());
                break;
            case Constants.INTERVAL_1D:
                time2LastTicker = Utils.getDate(ticker15m.startTime.longValue());
                break;
        }
        if (tickers == null) {
            tickers = new ArrayList<>();
            interval2Symbol2Tickers.get(interval).put(symbol, tickers);
            tickers.add(ticker15m);
        }
        KlineObjectNumber ticker = tickers.get(tickers.size() - 1);
        if (ticker.startTime.longValue() == time2LastTicker) {
            updateTickerData(ticker, ticker15m);
        } else {
            ticker = ticker15m;
            tickers.add(ticker);
        }
        updateMacd(tickers);
        // rewrite data new 2 list ticker time
        interval2Symbol2TimeAndTicker.get(interval).get(symbol).put(ticker.startTime.longValue(), ticker);
    }

    private void updateMacd(List<KlineObjectNumber> tickers) {
        RsiEntry[] rsi = RelativeStrengthIndex.calculateRSI(tickers, 14);
        MACDEntry[] entries = MACD.calculate(tickers, 12, 26, 9);
        Map<Double, Double> time2Rsi = new HashMap<>();
        Map<Double, Double> time2Ma = new HashMap<>();
        Map<Double, MACDEntry> time2Macd = new HashMap<>();
        for (RsiEntry rs : rsi) {
            time2Rsi.put(rs.startTime, rs.getRsi());
        }
        for (MACDEntry entry : entries) {
            time2Macd.put(entry.startTime, entry);
        }
        IndicatorEntry[] smaEntries = SimpleMovingAverage.calculate(tickers, 20);
        for (IndicatorEntry sma : smaEntries) {
            time2Ma.put(sma.startTime, sma.getValue());
        }
        for (KlineObjectNumber ticker : tickers) {
            MACDEntry macd = time2Macd.get(ticker.startTime);
            ticker.rsi = time2Rsi.get(ticker.startTime);
            ticker.ma20 = time2Ma.get(ticker.startTime);
            if (macd != null) {
                ticker.signal = macd.getSignal();
                ticker.macd = macd.getMacd();
                ticker.histogram = macd.getHistogram();
            }
        }
    }

    private void updateTickerData(KlineObjectNumber ticker, KlineObjectNumber ticker15m) {
        ticker.priceClose = ticker15m.priceClose;
        if (ticker.maxPrice < ticker15m.maxPrice) {
            ticker.maxPrice = ticker15m.maxPrice;
        }
        if (ticker.minPrice > ticker15m.minPrice) {
            ticker.minPrice = ticker15m.minPrice;
        }
        ticker.totalUsdt += ticker15m.totalUsdt;
    }
}
