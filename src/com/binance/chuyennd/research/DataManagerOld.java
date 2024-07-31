package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.text.ParseException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class DataManagerOld {
    public static final Logger LOG = LoggerFactory.getLogger(DataManagerOld.class);
    public static String FOLDER_TICKER_15M = Configs.getString("FOLDER_TICKER_15M");//"../ticker/storage/ticker/symbols-15m/";
    public static String FOLDER_TICKER_HOUR = Configs.getString("FOLDER_TICKER_1H");//"../ticker/storage/ticker/symbols-1h/";
    public static String FOLDER_TICKER_4HOUR = Configs.getString("FOLDER_TICKER_4H");//"../ticker/storage/ticker/symbols-4h/";
    public static String FOLDER_TICKER_1D = Configs.getString("FOLDER_TICKER_1D");//"../ticker/storage/ticker/symbols-4h/";
    private static volatile DataManagerOld INSTANCE = null;
    public ConcurrentHashMap<String, Map<String, Map<Long, KlineObjectNumber>>> interval2Symbol2TimeAndTicker;

    public static DataManagerOld getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new DataManagerOld();
            INSTANCE.initData();
        }
        return INSTANCE;
    }

    private void initData() {
        interval2Symbol2TimeAndTicker = new ConcurrentHashMap<>();
        interval2Symbol2TimeAndTicker.put(Constants.INTERVAL_1H, getData(Constants.INTERVAL_1H));
        interval2Symbol2TimeAndTicker.put(Constants.INTERVAL_4H, getData(Constants.INTERVAL_4H));
        interval2Symbol2TimeAndTicker.put(Constants.INTERVAL_1D, getData(Constants.INTERVAL_1D));
        LOG.info("Finish get ticker data: {} {} {}"
                , interval2Symbol2TimeAndTicker.get(Constants.INTERVAL_1H).size()
                , interval2Symbol2TimeAndTicker.get(Constants.INTERVAL_4H).size()
                , interval2Symbol2TimeAndTicker.get(Constants.INTERVAL_1D).size()
        );
    }

    private Map<String, Map<Long, KlineObjectNumber>> getData(String interval) {
        Map<String, Map<Long, KlineObjectNumber>> results = new HashMap<>();
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
                Map<Long, KlineObjectNumber> time2Ticker = new HashMap<>();
                for (KlineObjectNumber ticker : tickers) {
                    time2Ticker.put(ticker.startTime.longValue(), ticker);
                }
                results.put(symbol, time2Ticker);
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
}
