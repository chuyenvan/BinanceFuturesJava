package com.binance.chuyennd.bigchange.statistic.data;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
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
import java.util.concurrent.ConcurrentHashMap;

public class DataStatisticHelper {
    public static final Logger LOG = LoggerFactory.getLogger(DataStatisticHelper.class);
    public ConcurrentHashMap<String, Map<Long, Map<String, KlineObjectNumber>>> month2DataStatistic = new ConcurrentHashMap<>();
    private static volatile DataStatisticHelper INSTANCE = null;
    public static final String TIME_RUN = Configs.getString("TIME_RUN");

    public static DataStatisticHelper getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new DataStatisticHelper();
        }
        return INSTANCE;
    }

    public Map<Long, Map<String, KlineObjectNumber>> statisticData(int numberTicker) {
        Map<Long, Map<String, KlineObjectNumber>> time2SymbolAndRateChange = new HashMap<>();
        File[] symbolFiles = new File(DataManager.FOLDER_TICKER_15M).listFiles();
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

    public Map<String, KlineObjectNumber> readDataStaticByTimeAndNumberTickerStatic(Long time, Long numberTicker) {
        String month = Utils.getMonthByTime(time);
        if (!month2DataStatistic.containsKey(month)) {
            month2DataStatistic.put(month, readDataMonth(numberTicker, month));
        }
        Map<Long, Map<String, KlineObjectNumber>> time2SymbolAndRateChange = month2DataStatistic.get(Utils.getMonthByTime(time));
        return time2SymbolAndRateChange.get(time);
    }

    private Map<Long, Map<String, KlineObjectNumber>> readDataMonth(Long numberTicker, String month) {
        String folderData = "../storage/data_statistic/" + numberTicker + "/" + month;
        LOG.info("Read data from: {}", folderData);
        if (!new File(folderData).exists()) {
            initDataStatistic(numberTicker);
        }
        return (Map<Long, Map<String, KlineObjectNumber>>) Storage.readObjectFromFile(folderData);
    }

    private void initDataStatistic(Long numberTicker) {
        LOG.info("Init data statistic for: {} tickers", numberTicker);
        Map<Long, Map<String, KlineObjectNumber>> dataAll = statisticData(numberTicker.intValue());
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
            String folderData = "../storage/data_statistic/" + numberTicker + "/" + month;
            Storage.writeObject2File(folderData, values);
        }
        LOG.info("Finished statistic for: {} tickers", numberTicker);
    }
}
