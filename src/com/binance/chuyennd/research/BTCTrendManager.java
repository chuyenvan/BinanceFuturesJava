package com.binance.chuyennd.research;

import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.indicators.SimpleMovingAverage;
import com.binance.chuyennd.object.*;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class

BTCTrendManager {
    public static final Logger LOG = LoggerFactory.getLogger(BTCTrendManager.class);

    public String symbol = Constants.SYMBOL_PAIR_BTC;
    public TreeMap<Long, ResistanceAndSupport> time2TrendWeek;
    public TreeMap<Long, TrendState> time2TrendDay;
    public TreeMap<Long, TrendState> time2Trend4H;
    private static volatile BTCTrendManager INSTANCE = null;

    public static BTCTrendManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new BTCTrendManager();
            INSTANCE.initTrend4Hours();
        }
        return INSTANCE;
    }

    private void initTrend() {
        initTrendWeek();
    }

    private void initTrendWeek() {
        time2TrendWeek = new TreeMap<>();
        try {

           List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_4HOUR + symbol);
            IndicatorEntry[] smaEntries = SimpleMovingAverage.calculate(tickers, 60);
            long timeCheck = tickers.get(51).startTime.longValue();
            Map<Long, Double> time2Sma = new HashMap<>();
            for (int i = 0; i < smaEntries.length; i++) {
                IndicatorEntry sma = smaEntries[i];
                time2Sma.put(sma.startTime.longValue() - 7 * Utils.TIME_DAY, sma.getValue());
            }
            Long startTime = timeCheck;
            for (KlineObjectNumber ticker : tickers) {
                if (startTime > ticker.startTime.longValue()) {
                    continue;
                }
                timeCheck = ticker.startTime.longValue();
                List<KlineObjectNumber> ticker2Test = new ArrayList<>();
                for (int i = 0; i < tickers.size(); i++) {
                    if (tickers.get(i).startTime.longValue() < timeCheck) {
                        ticker2Test.add(tickers.get(i));
                    }
                }

                List<TrendObject> trends = TickerFuturesHelper.extractTopBottomObjectInTicker1W(ticker2Test);
                ResistanceAndSupport rsDetector = new ResistanceAndSupport(trends, ticker2Test.get(ticker2Test.size() - 1));
                ResistanceAndSupport lastTrendObject = time2TrendWeek.get(timeCheck - Utils.TIME_WEEK);
                TrendState lastTrend = null;
                if (lastTrendObject != null) {
                    lastTrend = lastTrendObject.trendDetail.status;
                }
                rsDetector.detectTrendGrid(lastTrend, time2Sma);
                time2TrendWeek.put(timeCheck, rsDetector);
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
    private void initTrend4Hours() {
        time2TrendWeek = new TreeMap<>();
        try {

//            List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_1W);
            List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_1D + symbol);
            IndicatorEntry[] smaEntries = SimpleMovingAverage.calculate(tickers, 60);
            long timeCheck = tickers.get(51).startTime.longValue();
            Map<Long, Double> time2Sma = new HashMap<>();
            for (int i = 0; i < smaEntries.length; i++) {
                IndicatorEntry sma = smaEntries[i];
                time2Sma.put(sma.startTime.longValue() - 7 * Utils.TIME_DAY, sma.getValue());
            }
            Long startTime = timeCheck;
            for (KlineObjectNumber ticker : tickers) {
                if (startTime > ticker.startTime.longValue()) {
                    continue;
                }
                timeCheck = ticker.startTime.longValue();
                List<KlineObjectNumber> ticker2Test = new ArrayList<>();
                for (int i = 0; i < tickers.size(); i++) {
                    if (tickers.get(i).startTime.longValue() < timeCheck) {
                        ticker2Test.add(tickers.get(i));
                    }
                }

                List<TrendObject> trends = TickerFuturesHelper.extractTopBottomObjectInTicker1W(ticker2Test);

                ResistanceAndSupport rsDetector = new ResistanceAndSupport(trends, ticker2Test.get(ticker2Test.size() - 1));
                ResistanceAndSupport lastTrendObject = time2TrendWeek.get(timeCheck - Utils.TIME_WEEK);
                TrendState lastTrend = null;
                if (lastTrendObject != null) {
                    lastTrend = lastTrendObject.trendDetail.status;
                }
                rsDetector.detectTrendGrid(lastTrend, time2Sma);
                time2TrendWeek.put(timeCheck, rsDetector);
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
    public static void main(String[] args) {
//        BTCTrendManager.getInstance().printTrendWeek();
                BTCTrendManager.getInstance().printTrendWeek();
    }

    private void printTrendWeek() {
        ResistanceAndSupport lastTrend = null;
        for (Long time : time2TrendWeek.keySet()) {
            ResistanceAndSupport trend = time2TrendWeek.get(time);
            if (lastTrend == null) {
                lastTrend = trend;
            } else {
                if (lastTrend.trendDetail.status != trend.trendDetail.status) {
                    LOG.info("-------------------------------------------------------{} -> {} {}",
                            Utils.normalizeDateYYYYMMDD(lastTrend.currentTicker.startTime.longValue()),
                            Utils.normalizeDateYYYYMMDD(trend.currentTicker.startTime.longValue()), lastTrend.trendDetail.status);
                    lastTrend = trend;
                }
            }
            LOG.info(trend.printTrend());
        }
    }
}
