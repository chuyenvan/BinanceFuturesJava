package com.binance.chuyennd.grid;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.indicators.SimpleMovingAverage;
import com.binance.chuyennd.object.IndicatorEntry;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.GridConfigs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class SimpleMovingAverageWeekManager {
    public static final Logger LOG = LoggerFactory.getLogger(SimpleMovingAverageWeekManager.class);
    public ConcurrentHashMap<String, TreeMap<Long, Double>> symbol2MADifference10And60 = new ConcurrentHashMap<>();
    private static volatile SimpleMovingAverageWeekManager INSTANCE = null;

    public static SimpleMovingAverageWeekManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new SimpleMovingAverageWeekManager();
            INSTANCE.startThreadUpdateData();
        }
        return INSTANCE;
    }

    public static void main(String[] args) throws ParseException {
        String symbol = Constants.SYMBOL_PAIR_BTC;
        Long time = Utils.sdfFileHour.parse("20250224 05:38").getTime();
        System.out.println(SimpleMovingAverageWeekManager.getInstance().getDifferenceMa10AndMa60(symbol, time));
    }

    public Double getDifferenceMa10AndMa60(String symbol, Long time) {
        Map<Long, Double> time2MaDifferent = symbol2MADifference10And60.get(symbol);
        if (time2MaDifferent == null) {
            updateForSymbol(symbol);
        }
        time2MaDifferent = symbol2MADifference10And60.get(symbol);
        if (time2MaDifferent != null) {
            time = Utils.getTimeStartWeek(time);
            return time2MaDifferent.get(time);
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
            LOG.info("Update ma different for symbol: {}", symbol);
            List<KlineObjectNumber> ticker1Ws = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_1W);
            TreeMap<Long, Double> time2Sma60 = new TreeMap<>();
            TreeMap<Long, Double> time2Sma20 = new TreeMap<>();
            TreeMap<Long, Double> time2MaDifferent = new TreeMap<>();
            IndicatorEntry[] smaEntries = SimpleMovingAverage.calculate(ticker1Ws, GridConfigs.SMA_LONG);
            for (int i = 0; i < smaEntries.length; i++) {
                IndicatorEntry sma = smaEntries[i];
                time2Sma60.put(sma.startTime.longValue() + 7 * Utils.TIME_DAY, sma.getValue());
//                time2Sma60.put(sma.startTime.longValue(), sma.getValue());
            }
            smaEntries = SimpleMovingAverage.calculate(ticker1Ws, GridConfigs.SMA_SHORT);
            for (int i = 0; i < smaEntries.length; i++) {
                IndicatorEntry sma = smaEntries[i];
                time2Sma20.put(sma.startTime.longValue() + 7 * Utils.TIME_DAY, sma.getValue());
//                time2Sma20.put(sma.startTime.longValue(), sma.getValue());
            }
            for (Long time : time2Sma20.keySet()) {
                Double ma10 = time2Sma20.get(time);
                Double ma60 = time2Sma60.get(time);
                if (ma60 != null && ma10 != null) {
//                    LOG.info("{} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), ma10, ma60, ma10 - ma60);
                    time2MaDifferent.put(time, ma10 - ma60);
                }
            }
            symbol2MADifference10And60.put(symbol, time2MaDifferent);
            LOG.info("Finish update ma different for symbol: {} {}", symbol, time2MaDifferent.size());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }


}
