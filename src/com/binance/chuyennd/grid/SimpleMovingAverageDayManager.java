package com.binance.chuyennd.grid;

import com.binance.chuyennd.indicators.SimpleMovingAverage;
import com.binance.chuyennd.object.IndicatorEntry;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.*;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class SimpleMovingAverageDayManager {
    public static final Logger LOG = LoggerFactory.getLogger(SimpleMovingAverageDayManager.class);
    public ConcurrentHashMap<String, TreeMap<Long, Double>> symbol2MADifference10And60 = new ConcurrentHashMap<>();
    private static volatile SimpleMovingAverageDayManager INSTANCE = null;

    public static SimpleMovingAverageDayManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new SimpleMovingAverageDayManager();
            INSTANCE.startThreadUpdateData();
        }
        return INSTANCE;
    }

    public static void main(String[] args) throws ParseException {
//        String symbol = Constants.SYMBOL_PAIR_BTC;
        Long time = Utils.sdfFileHour.parse("20250726 08:15").getTime();
////        System.out.println(SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(symbol, time));
//
//        Double maDif1d = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
//        Double maDif4h = SimpleMovingAverage4hManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
//        if ((maDif4h != null && maDif4h < 0)
//                || (maDif1d != null && maDif1d < 0)
//        ) {
//            System.out.println("True");
//        }


    }

    public Double getDifferenceMa10AndMa60(String symbol, Long time) {
        Map<Long, Double> time2MaDifferent = symbol2MADifference10And60.get(symbol);
        if (time2MaDifferent == null) {
            updateForSymbol(symbol);
        }
        time2MaDifferent = symbol2MADifference10And60.get(symbol);
        if (time2MaDifferent != null) {
            return time2MaDifferent.get(Utils.getDate(time));
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
//            LOG.info("Update ma different for symbol: {}", symbol);
            List<KlineObjectNumber> ticker1Ds = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_1D + symbol);
            TreeMap<Long, Double> time2Sma60 = new TreeMap<>();
            TreeMap<Long, Double> time2Sma20 = new TreeMap<>();
            TreeMap<Long, Double> time2MaDifferent = new TreeMap<>();
            if (ticker1Ds == null || ticker1Ds.size() < 100){
                return ;
            }
            IndicatorEntry[] smaEntries = SimpleMovingAverage.calculate(ticker1Ds, Configs.SMA_LONG);
            for (int i = 0; i < smaEntries.length; i++) {
                IndicatorEntry sma = smaEntries[i];
                time2Sma60.put(sma.startTime.longValue() + Utils.TIME_DAY, sma.getValue());
//                time2Sma60.put(sma.startTime.longValue(), sma.getValue());
            }
            smaEntries = SimpleMovingAverage.calculate(ticker1Ds, Configs.SMA_SHORT);
            for (int i = 0; i < smaEntries.length; i++) {
                IndicatorEntry sma = smaEntries[i];
                time2Sma20.put(sma.startTime.longValue() + Utils.TIME_DAY, sma.getValue());
//                time2Sma20.put(sma.startTime.longValue(), sma.getValue());
            }
            for (Long time : time2Sma20.keySet()) {
                Double ma10 = time2Sma20.get(time);
                Double ma60 = time2Sma60.get(time);
                if (ma60 != null && ma10 != null) {
//                    LOG.info("{} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), ma10, ma60, ma10 - ma60);
                    // Check ma reverse
                    int counterIncrement = 0;
                    int counterDecrement = 0;
                    double maDif = ma10 - ma60;
//                    if (symbol.equals(Constants.SYMBOL_PAIR_BTC)) {
//                        for (int i = 0; i < GridConfigs.NUMBER_MA_4H_REVERSE; i++) {
//                            Double lastMaDif = time2MaDifferent.get(time - (i + 1) * Utils.TIME_DAY);
//                            Double beforeLastMaDif = time2MaDifferent.get(time - (i + 2) * Utils.TIME_DAY);
//                            if (beforeLastMaDif != null && lastMaDif != null) {
//                                if (beforeLastMaDif > lastMaDif) {
//                                    counterDecrement++;
//                                } else {
//                                    counterIncrement++;
//                                }
//                            }
//                            if ((maDif > 0 && counterDecrement == GridConfigs.NUMBER_MA_4H_REVERSE)
//                                    || maDif < 0 && counterIncrement == GridConfigs.NUMBER_MA_4H_REVERSE) {
//                                maDif = -maDif;
//                            }
//                        }
//                    }
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
