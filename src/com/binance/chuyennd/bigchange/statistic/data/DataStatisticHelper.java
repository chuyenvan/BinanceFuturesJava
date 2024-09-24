package com.binance.chuyennd.bigchange.statistic.data;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class DataStatisticHelper {
    public static final Logger LOG = LoggerFactory.getLogger(DataStatisticHelper.class);
    public ConcurrentHashMap<String, Map<Long, Map<String, KlineObjectNumber>>> month2DataStatistic_15m = new ConcurrentHashMap<>();
    public ConcurrentHashMap<Long, Map<Long, Map<String, KlineObjectNumber>>> month2DataStatistic_1m = new ConcurrentHashMap<>();
    private static volatile DataStatisticHelper INSTANCE = null;
    public static final String TIME_RUN = Configs.getString("TIME_RUN");

    public static DataStatisticHelper getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new DataStatisticHelper();
        }
        return INSTANCE;
    }

    public Map<Long, Map<String, KlineObjectNumber>> statisticData15m(int numberTicker) {
        Map<Long, Map<String, KlineObjectNumber>> time2SymbolAndRateChange = new HashMap<>();
        File[] symbolFiles = new File(Configs.FOLDER_TICKER_15M).listFiles();
        for (File symbolFile : symbolFiles) {
            try {
                String symbol = symbolFile.getName();
                if (!StringUtils.endsWithIgnoreCase(symbol, "usdt")
                        || Constants.diedSymbol.contains(symbol)) {
                    continue;
                }
                List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(symbolFile.getPath());
                for (int i = 0; i < tickers.size(); i++) {
                    Long time = tickers.get(i).startTime.longValue();
                    Map<String, KlineObjectNumber> symbol2RateChange = time2SymbolAndRateChange.get(time);
                    if (symbol2RateChange == null) {
                        symbol2RateChange = new HashMap<>();
                        time2SymbolAndRateChange.put(time, symbol2RateChange);
                    }
                    KlineObjectNumber tickerChange = TickerFuturesHelper.extractKline(tickers, numberTicker, i + 1);
                    tickerChange.priceOpen = tickers.get(i).priceClose;
                    tickerChange.totalUsdt = tickers.get(i).totalUsdt;
                    symbol2RateChange.put(symbol, tickerChange);
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return time2SymbolAndRateChange;
    }

    public Map<String, KlineObjectNumber> readDataStatic_15m(Long time, Long numberTicker) {
        String month = Utils.getMonthByTime(time);
        if (!month2DataStatistic_15m.containsKey(month)) {
            month2DataStatistic_15m.put(month, readDataMonth15m(numberTicker, month));
        }
        Map<Long, Map<String, KlineObjectNumber>> time2SymbolAndRateChange = month2DataStatistic_15m.get(Utils.getMonthByTime(time));
        return time2SymbolAndRateChange.get(time);
    }

    public Map<String, KlineObjectNumber> readDataStatic_1m(Long time) {
        Long date = Utils.getDate(time);
        if (!month2DataStatistic_1m.containsKey(date)) {
            month2DataStatistic_1m.put(date, readDataDate1m(date));
        }
        Map<Long, Map<String, KlineObjectNumber>> time2SymbolAndRateChange = month2DataStatistic_1m.get(Utils.getDate(time));
        return time2SymbolAndRateChange.get(time);
    }


    private Map<Long, Map<String, KlineObjectNumber>> readDataMonth15m(Long numberTicker, String month) {
        String folderData = "../storage/data_statistic/15m/" + numberTicker + "/" + month;
        LOG.info("Read data from: {}", folderData);
        if (!new File(folderData).exists()) {
            initDataStatistic15m(numberTicker);
        }
        return (Map<Long, Map<String, KlineObjectNumber>>) Storage.readObjectFromFile(folderData);
    }

    private Map<Long, Map<String, KlineObjectNumber>> readDataDate1m(Long date) {
        String folderData = "../storage/data_statistic/1m/" + "/" + date;
        LOG.info("Read data from: {}", folderData);
        if (!new File(folderData).exists()) {
            initDataStatistic1M();
        }
        return (Map<Long, Map<String, KlineObjectNumber>>) Storage.readObjectFromFile(folderData);
    }

    private void initDataStatistic15m(Long numberTicker) {
        LOG.info("Init data statistic 15m for: {} tickers", numberTicker);
        Map<Long, Map<String, KlineObjectNumber>> dataAll = statisticData15m(numberTicker.intValue());
        Map<String, Map<Long, Map<String, KlineObjectNumber>>> month2Data = new HashMap<>();
        for (Map.Entry<Long, Map<String, KlineObjectNumber>> entry : dataAll.entrySet()) {
            Long time = entry.getKey();
            Map<String, KlineObjectNumber> values = entry.getValue();
            String month = Utils.getMonthByTime(time);
            Map<Long, Map<String, KlineObjectNumber>> dataMonth = month2Data.get(month);
            if (dataMonth == null) {
                dataMonth = new HashMap<>();
                month2Data.put(month, dataMonth);
            }
            dataMonth.put(time, values);
        }
        for (Map.Entry<String, Map<Long, Map<String, KlineObjectNumber>>> entry : month2Data.entrySet()) {
            String month = entry.getKey();
            Map<Long, Map<String, KlineObjectNumber>> values = entry.getValue();
            String folderData = "../storage/data_statistic/15m/" + numberTicker + "/" + month;
            Storage.writeObject2File(folderData, values);
        }
        LOG.info("Finished statistic for 15m: {} tickers", numberTicker);
    }

    private void initDataStatistic1M() {
        LOG.info("Init data statistic for 1m");
        Long dateStatistic = Utils.getDate(System.currentTimeMillis()) - 2 * Utils.TIME_DAY;
        while (true) {
            String fileData = "../storage/data_statistic/1m/" + dateStatistic;
            if (!new File(fileData).exists()) {
                LOG.info("Statistic data 1m of date: {} -> {}", Utils.normalizeDateYYYYMMDD(dateStatistic), fileData);
                Map<Long, Map<String, KlineObjectNumber>> values = statisticData1m(dateStatistic);
                if (values != null) {
                    Storage.writeObject2File(fileData, values);
                }
                if (dateStatistic < Utils.getStartTimeDayAgo(300)) {
                    break;
                }
            }
            dateStatistic = dateStatistic - Utils.TIME_DAY;
        }
        LOG.info("Finished statistic for: 1m");
    }

    private Map<Long, Map<String, KlineObjectNumber>> statisticData1m(Long date) {
        try {
            TreeMap<Long, Map<String, KlineObjectSimple>> dataAfter2d = DataManager.readDataFromFile1M(date + 2 * Utils.TIME_DAY);
            if (dataAfter2d == null) {
                return null;
            }
            TreeMap<Long, Map<String, KlineObjectSimple>> dataAfter1d = DataManager.readDataFromFile1M(date + Utils.TIME_DAY);
            if (dataAfter1d == null) {
                return null;
            }
            TreeMap<Long, Map<String, KlineObjectSimple>> time2SymbolAndTicker = DataManager.readDataFromFile1M(date);
            if (time2SymbolAndTicker == null) {
                return null;
            }
            Map<Long, Map<String, KlineObjectNumber>> results = new HashMap<>();
            // process init and update data
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2SymbolAndTicker.entrySet()) {
                Long time = entry.getKey();
//                    init
                Map<String, KlineObjectNumber> symbol2TickerStatistic = new HashMap<>();
                results.put(time, symbol2TickerStatistic);
                for (Map.Entry<String, KlineObjectSimple> entry1 : entry.getValue().entrySet()) {
                    String symbol = entry1.getKey();
                    KlineObjectNumber tickerStatistic = new KlineObjectNumber();
                    symbol2TickerStatistic.put(symbol, tickerStatistic);
                }
                // update
                updateDataForAllTickerStatistic(results, entry);
            }
            // process statistic date 1
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : dataAfter1d.entrySet()) {
                updateDataForAllTickerStatistic(results, entry);
            }
            //  process statistic date 2
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : dataAfter2d.entrySet()) {
                Long time = entry.getKey();
                updateDataForAllTickerStatistic(results, entry);
            }
            return results;

        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    private void updateDataForAllTickerStatistic(Map<Long, Map<String, KlineObjectNumber>> results,
                                                 Map.Entry<Long, Map<String, KlineObjectSimple>> entryTicker) {
        Long time = entryTicker.getKey();
        Map<String, KlineObjectSimple> symbol2Ticker = entryTicker.getValue();
        for (Map.Entry<Long, Map<String, KlineObjectNumber>> entry : results.entrySet()) {
            Long timeStatistic = entry.getKey();
            Map<String, KlineObjectNumber> symbol2TickerStatistic = entry.getValue();
            if (timeStatistic > time - 2 * Utils.TIME_DAY) {
                for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
                    String symbol = entry1.getKey();
                    KlineObjectSimple ticker = entry1.getValue();
                    KlineObjectNumber tickerStatistic = symbol2TickerStatistic.get(symbol);
                    if (tickerStatistic != null) {
                        updateDataStatistic(tickerStatistic, ticker);
                    }
                }
            }
        }
    }

    private void updateDataStatistic(KlineObjectNumber tickerStatistic, KlineObjectSimple ticker) {
        if (tickerStatistic.startTime == null) {
            tickerStatistic.startTime = ticker.startTime;
            tickerStatistic.endTime = ticker.startTime + Utils.TIME_MINUTE - 1;
        }
        if (tickerStatistic.priceOpen == null) {
            tickerStatistic.priceOpen = ticker.priceOpen;
        }
        tickerStatistic.priceClose = ticker.priceClose;
        if (tickerStatistic.minPrice == null || tickerStatistic.minPrice > ticker.minPrice) {
            tickerStatistic.minPrice = ticker.minPrice;
        }
        if (tickerStatistic.maxPrice == null || tickerStatistic.maxPrice < ticker.maxPrice) {
            tickerStatistic.maxPrice = ticker.maxPrice;
        }
        if (tickerStatistic.totalUsdt == null) {
            tickerStatistic.totalUsdt = 0d;
        }
        tickerStatistic.totalUsdt += ticker.totalUsdt;
    }

    public static void main(String[] args) {
        DataStatisticHelper.getInstance().initDataStatistic1M();
    }
}
