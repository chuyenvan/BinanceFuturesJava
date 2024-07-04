/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.bigchange.btctd;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.indicators.MACD;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.MACDEntry;
import com.binance.chuyennd.object.TrendState;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * @author pc
 */
public class BTCMacdTrendManager {
    public static final Logger LOG = LoggerFactory.getLogger(BTCMacdTrendManager.class);
    private static volatile BTCMacdTrendManager INSTANCE = null;
    public Boolean MOD_UPDATE_BTCMACD = Configs.getBoolean("MOD_UPDATE_BTCMACD");
    public Map<String, Map<Long, Double>> interval2TimeAndHistogram;
    public Map<String, Map<Long, Double>> interval2TimeAndPrice;
    public static final String FILE_BTC_MACD_DATA = Configs.getString("FILE_BTC_MACD_DATA");

    public static BTCMacdTrendManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new BTCMacdTrendManager();
            INSTANCE.initData();
            if (INSTANCE.MOD_UPDATE_BTCMACD) {
                INSTANCE.startThreadUpdateData();
            }
        }
        return INSTANCE;
    }

    private void startThreadUpdateData() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadUpdateDataBTCMACD");
            LOG.info("Start thread ThreadUpdateDataBTCMACD !");
            while (true) {
                try {
                    Thread.sleep(Utils.TIME_HOUR);
                    interval2TimeAndHistogram = initDataBtcMacdData();
                    Storage.writeObject2File(FILE_BTC_MACD_DATA, interval2TimeAndHistogram);
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadUpdateDataBTCMACD: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void initData() {
        if (new File(FILE_BTC_MACD_DATA).exists()) {
            interval2TimeAndHistogram = (Map<String, Map<Long, Double>>) Storage.readObjectFromFile(FILE_BTC_MACD_DATA);
        } else {
            interval2TimeAndHistogram = initDataBtcMacdData();
            Storage.writeObject2File(FILE_BTC_MACD_DATA, interval2TimeAndHistogram);
        }
    }

    private Map<String, Map<Long, Double>> initDataBtcMacdData() {
        Map<String, Map<Long, Double>> interval2TimeAndHistogram = new HashMap<>();
        LOG.info("Start init btc macd data!");
        interval2TimeAndHistogram.put(Constants.INTERVAL_1D, getBtcMacdByInterVal(Constants.INTERVAL_1D));
        interval2TimeAndHistogram.put(Constants.INTERVAL_4H, getBtcMacdByInterVal(Constants.INTERVAL_4H));
        interval2TimeAndHistogram.put(Constants.INTERVAL_1H, getBtcMacdByInterVal(Constants.INTERVAL_1H));
        interval2TimeAndHistogram.put(Constants.INTERVAL_15M, getBtcMacdByInterVal(Constants.INTERVAL_15M));
        LOG.info("Finished init btc macd data!");
        return interval2TimeAndHistogram;
    }

    private Map<Long, Double> getBtcMacdByInterVal(String interval) {
        List<KlineObjectNumber> tickers = TickerFuturesHelper.getTickerWithStartTimeFull(Constants.SYMBOL_PAIR_BTC, interval, 0l);
        Map<Long, Double> time2Histogram = new HashMap<>();
        MACDEntry[] entries = MACD.calculate(tickers, 12, 26, 9);
        for (MACDEntry entry : entries) {
            time2Histogram.put(entry.startTime.longValue(), entry.getHistogram());
        }
        return time2Histogram;
    }

    public Double getHistogram(String interval, Long time) {
        Map<Long, Double> time2Histogram = interval2TimeAndHistogram.get(interval);
        if (time2Histogram != null) {
            return time2Histogram.get(time);
        }
        return null;
    }

    public TrendState getTrend(String interval, Long time) {
        Long lastTime = null;
        switch (interval) {
            case Constants.INTERVAL_1D:
                time = Utils.getDate(time);
                lastTime = time - Utils.TIME_DAY;
                break;
            case Constants.INTERVAL_4H:
                time = Utils.get4Hour(time);
                lastTime = time - 4 * Utils.TIME_HOUR;
                break;
            case Constants.INTERVAL_1H:
                time = Utils.getHour(time);
                lastTime = time - Utils.TIME_HOUR;
                break;
            case Constants.INTERVAL_15M:
                time = Utils.getTimeInterval15m(time);
                lastTime = time - 15 * Utils.TIME_MINUTE;
                break;
        }
        Map<Long, Double> time2Histogram = interval2TimeAndHistogram.get(interval);
        if (time2Histogram != null && lastTime != null) {
            Double lastHistogram = time2Histogram.get(lastTime);
            Double histogram = time2Histogram.get(time);
            if (histogram == null || lastHistogram == null){
                return null;
            }
            if (histogram < 0) {
                if (histogram < lastHistogram) {
                    return TrendState.STRONG_DOWN;
                }else{
                    return TrendState.DOWN;
                }
            }else{
                if (histogram > lastHistogram) {
                    return TrendState.STRONG_UP;
                } else {
                    return TrendState.UP;
                }
            }
        }
        return null;
    }

    public static void main(String[] args) {
        for (int i = 0; i < 30; i++) {
            Long timeDate = Utils.getDate(System.currentTimeMillis()) - i * Utils.TIME_DAY;
            LOG.info("1d: {} -> {} {}", Utils.normalizeDateYYYYMMDDHHmm(timeDate),
                    BTCMacdTrendManager.getInstance().getHistogram(Constants.INTERVAL_1D, timeDate),
                    BTCMacdTrendManager.getInstance().getTrend(Constants.INTERVAL_1D, timeDate));
        }
        for (int i = 0; i < 30; i++) {
            Long time4h = Utils.get4Hour(System.currentTimeMillis()) - i * 4 * Utils.TIME_HOUR;
            LOG.info("4h: {} -> {} {}", Utils.normalizeDateYYYYMMDDHHmm(time4h),
                    BTCMacdTrendManager.getInstance().getHistogram(Constants.INTERVAL_4H, time4h),
                    BTCMacdTrendManager.getInstance().getTrend(Constants.INTERVAL_4H, time4h));
        }
        for (int i = 0; i < 30; i++) {
            Long time1h = Utils.getHour(System.currentTimeMillis()) - i * Utils.TIME_HOUR;
            LOG.info("1h: {} -> {} {}", Utils.normalizeDateYYYYMMDDHHmm(time1h),
                    BTCMacdTrendManager.getInstance().getHistogram(Constants.INTERVAL_1H, time1h),
                    BTCMacdTrendManager.getInstance().getTrend(Constants.INTERVAL_1H, time1h));
        }
        for (int i = 0; i < 30; i++) {
            Long time15m = Utils.getTimeInterval15m(System.currentTimeMillis()) - i * 15 * Utils.TIME_MINUTE;
            LOG.info("15m: {} -> {} {}", Utils.normalizeDateYYYYMMDDHHmm(time15m),
                    BTCMacdTrendManager.getInstance().getHistogram(Constants.INTERVAL_15M, time15m),
                    BTCMacdTrendManager.getInstance().getTrend(Constants.INTERVAL_15M, time15m));
        }
    }

}
