package com.binance.chuyennd.trading.grid;

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
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class SimpleMovingAverageDayManagerProduction {
    public static final Logger LOG = LoggerFactory.getLogger(SimpleMovingAverageDayManagerProduction.class);
    public ConcurrentHashMap<String, TreeMap<Long, Double>> symbol2MADifference10And60 = new ConcurrentHashMap<>();
    private static volatile SimpleMovingAverageDayManagerProduction INSTANCE = null;

    public static SimpleMovingAverageDayManagerProduction getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new SimpleMovingAverageDayManagerProduction();
            INSTANCE.symbol2MADifference10And60.put(Constants.SYMBOL_PAIR_BTC, new TreeMap<>());
            INSTANCE.updateAllSymbol();
            INSTANCE.startThreadUpdateData();
        }
        return INSTANCE;
    }

    public static void main(String[] args) throws ParseException {
        String symbol = Constants.SYMBOL_PAIR_BTC;
        Long time = Utils.sdfFileHour.parse("20250203 08:00").getTime();
        System.out.println(SimpleMovingAverageDayManagerProduction.getInstance().getDifferenceMa10AndMa60(symbol, time));
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
        new Thread(() -> {
            Thread.currentThread().setName("ThreadUpdateDifferentMa10And60_Day");
            LOG.info("Start thread ThreadUpdateDifferentMa10And60_Day!");
            while (true) {
                try {
                    Thread.sleep(15 * Utils.TIME_MINUTE);
                    updateAllSymbol();
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadUpdateDifferentMa10And60_Day {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void updateAllSymbol() {
        for (String symbol : symbol2MADifference10And60.keySet()) {
            updateForSymbol(symbol);
        }
    }

    private void updateForSymbol(String symbol) {
        try {
            List<KlineObjectNumber> ticker1Ds = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_1D);
            LOG.info("Update ma different 1d for symbol: {} {} {}", symbol, Utils.normalizeDateYYYYMMDD(ticker1Ds.get(0).startTime.longValue()),
                    Utils.normalizeDateYYYYMMDD(ticker1Ds.get(ticker1Ds.size() - 1).startTime.longValue()));
            TreeMap<Long, Double> time2SmaLong = new TreeMap<>();
            TreeMap<Long, Double> time2SmaShort = new TreeMap<>();
            TreeMap<Long, Double> time2MaDifferent = new TreeMap<>();
            IndicatorEntry[] smaEntries = SimpleMovingAverage.calculate(ticker1Ds, GridConfigs.SMA_LONG);
            for (int i = 0; i < smaEntries.length; i++) {
                IndicatorEntry sma = smaEntries[i];
                time2SmaLong.put(sma.startTime.longValue() + Utils.TIME_DAY, sma.getValue());
            }
            smaEntries = SimpleMovingAverage.calculate(ticker1Ds, GridConfigs.SMA_SHORT);
            for (int i = 0; i < smaEntries.length; i++) {
                IndicatorEntry sma = smaEntries[i];
                time2SmaShort.put(sma.startTime.longValue() + Utils.TIME_DAY, sma.getValue());
            }
            for (Long time : time2SmaShort.keySet()) {
                Double maShort = time2SmaShort.get(time);
                Double maLong = time2SmaLong.get(time);
                if (maLong != null && maShort != null) {
                    time2MaDifferent.put(time, maShort - maLong);
//                    LOG.info("{} {} maShort:{} maLong:{}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time), maShort, maLong);
                }
            }
            symbol2MADifference10And60.put(symbol, time2MaDifferent);
            LOG.info("Finish update ma different 1d for symbol: {} {}", symbol, time2MaDifferent.size());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void printMaDif(String symbol) {
        Map<Long, Double> time2MaDifferent = symbol2MADifference10And60.get(symbol);
        if (time2MaDifferent == null) {
            updateForSymbol(symbol);
        }
        time2MaDifferent = symbol2MADifference10And60.get(symbol);
        if (time2MaDifferent != null) {
            for (Long time:time2MaDifferent.keySet()){
                LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(time), time2MaDifferent.get(time));
            }
        }
    }
}
