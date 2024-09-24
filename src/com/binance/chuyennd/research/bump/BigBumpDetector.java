package com.binance.chuyennd.research.bump;

import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;

public class BigBumpDetector {
    public static final Logger LOG = LoggerFactory.getLogger(BigBumpDetector.class);
    public final String TIME_RUN = Configs.getString("TIME_RUN");

    public static void main(String[] args) throws ParseException {
        new BigBumpDetector().startThreadBigBumpDetector();
    }

    private void startThreadBigBumpDetector() throws ParseException {
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        Map<String, List<KlineObjectSimple>> symbol2Tickers = new HashMap<>();
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManager.readDataFromFile1M(startTime);
            if (time2Tickers != null) {
                for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                    Long time = entry.getKey();
                    Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                    // update order Old
                    for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
                        String symbol = entry1.getKey();
                        if (Constants.diedSymbol.contains(symbol)) {
                            continue;
                        }
                        if (Constants.specialSymbol.contains(symbol)) {
                            continue;
                        }
                        KlineObjectSimple ticker = entry1.getValue();
                        List<KlineObjectSimple> tickers = symbol2Tickers.get(symbol);
                        if (tickers == null) {
                            tickers = new ArrayList<>();
                            symbol2Tickers.put(symbol, tickers);
                        }
                        tickers.add(ticker);
                        if (tickers.size() > 200) {
                            for (int i = 0; i < 100; i++) {
                                tickers.remove(0);
                            }
                        }
                        if (isSignalBigBump(tickers)) {
                            LOG.info("{} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
                        }
                    }
                }
            }
            startTime += Utils.TIME_DAY;
            if (startTime > System.currentTimeMillis()) {
                break;
            }
        }
    }

    public static boolean isSignalBigBump(List<KlineObjectSimple> tickers) {
        try {

            KlineObjectSimple ticker = tickers.get(tickers.size() - 1);
            Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
            Double volumeAvg = 0d;
            int counter = 0;
            for (int i = 1; i < 20; i++) {
                if (tickers.size() > i) {
                    KlineObjectSimple lastTicker = tickers.get(i);
                    volumeAvg += lastTicker.totalUsdt;
                    counter++;
                }
            }
            volumeAvg = volumeAvg / counter;
            double rateVolumeChange = ticker.totalUsdt / volumeAvg;
            if (rateVolumeChange >= 70
                    && rateChange > 0.005
                    && rateChange < 0.01) {
                return true;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
    }
}
