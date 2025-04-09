package com.binance.chuyennd.grid;

import com.binance.chuyennd.indicators.SimpleMovingAverage;
import com.binance.chuyennd.object.IndicatorEntry;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.GridConfigs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class SimpleMovingAverage4hManager {
    public static final Logger LOG = LoggerFactory.getLogger(SimpleMovingAverage4hManager.class);
    public ConcurrentHashMap<String, TreeMap<Long, Double>> symbol2MADifference10And60 = new ConcurrentHashMap<>();
    private static volatile SimpleMovingAverage4hManager INSTANCE = null;

    public static SimpleMovingAverage4hManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new SimpleMovingAverage4hManager();
            INSTANCE.startThreadUpdateData();
        }
        return INSTANCE;
    }

    public static void main(String[] args) throws ParseException {
        String symbol = Constants.SYMBOL_PAIR_BTC;
        Long time = Utils.sdfFileHour.parse("20250204 08:00").getTime();
        System.out.println(SimpleMovingAverage4hManager.getInstance().getDifferenceMa10AndMa60(symbol, time));
    }

    public Double getDifferenceMa10AndMa60(String symbol, Long time) {
        Map<Long, Double> time2MaDifferent = symbol2MADifference10And60.get(symbol);
        if (time2MaDifferent == null) {
            updateForSymbol(symbol);
        }
        time2MaDifferent = symbol2MADifference10And60.get(symbol);
        if (time2MaDifferent != null) {
            return time2MaDifferent.get(Utils.get4Hour(time));
        }
        return null;
    }

    private void startThreadUpdateData() {
        for (String symbol : symbol2MADifference10And60.keySet()) {
            updateForSymbol(symbol);
        }
    }

    private void updateForSymbol(String symbol) {

        try {
            List<KlineObjectNumber> ticker4Hours = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_4HOUR + symbol);
//            LOG.info("Update ma different for symbol: {} {} {}", symbol, Utils.normalizeDateYYYYMMDD(ticker1Ws.get(0).startTime.longValue()),
//                    Utils.normalizeDateYYYYMMDD(ticker1Ws.get(ticker1Ws.size() - 1).startTime.longValue()));
            TreeMap<Long, Double> time2Sma60 = new TreeMap<>();
            TreeMap<Long, Double> time2Sma20 = new TreeMap<>();
            TreeMap<Long, Double> time2MaDifferent = new TreeMap<>();
            if (ticker4Hours == null || ticker4Hours.size() < 100){
                return ;
            }
            IndicatorEntry[] smaEntries = SimpleMovingAverage.calculate(ticker4Hours, GridConfigs.SMA_LONG);
            for (int i = 0; i < smaEntries.length; i++) {
                IndicatorEntry sma = smaEntries[i];
                time2Sma60.put(sma.startTime.longValue() + 4 * Utils.TIME_HOUR, sma.getValue());
//                time2Sma60.put(sma.startTime.longValue(), sma.getValue());
            }
            smaEntries = SimpleMovingAverage.calculate(ticker4Hours, GridConfigs.SMA_SHORT);
            for (int i = 0; i < smaEntries.length; i++) {
                IndicatorEntry sma = smaEntries[i];
                time2Sma20.put(sma.startTime.longValue() + 4 * Utils.TIME_HOUR, sma.getValue());
//                time2Sma20.put(sma.startTime.longValue(), sma.getValue());
            }
            for (Long time : time2Sma20.keySet()) {
                Double ma10 = time2Sma20.get(time);
                Double ma60 = time2Sma60.get(time);
                if (ma60 != null && ma10 != null) {
                    double maDif = ma10 - ma60;
                    time2MaDifferent.put(time, maDif);
                }
            }
            symbol2MADifference10And60.put(symbol, time2MaDifferent);
//            LOG.info("Finish update ma different for symbol: {} {}", symbol, time2MaDifferent.size());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }


}
