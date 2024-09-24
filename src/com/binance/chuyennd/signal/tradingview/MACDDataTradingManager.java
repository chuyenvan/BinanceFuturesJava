package com.binance.chuyennd.signal.tradingview;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.indicators.MACD;
import com.binance.chuyennd.indicators.RelativeStrengthIndex;
import com.binance.chuyennd.indicators.SimpleMovingAverage;
import com.binance.chuyennd.object.IndicatorEntry;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.MACDEntry;
import com.binance.chuyennd.object.RsiEntry;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class MACDDataTradingManager {
    public static final Logger LOG = LoggerFactory.getLogger(MACDDataTradingManager.class);
    private static volatile MACDDataTradingManager INSTANCE = null;
    public ConcurrentHashMap<String, Map<String, Map<Long, KlineObjectNumber>>> interval2Symbol2TimeAndTicker;

    public static MACDDataTradingManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new MACDDataTradingManager();
            INSTANCE.initData();
        }
        return INSTANCE;
    }

    private void initData() {
        interval2Symbol2TimeAndTicker = new ConcurrentHashMap<>();
        updateData();
        LOG.info("Finish get ticker data: {} {} {}"
                , interval2Symbol2TimeAndTicker.get(Constants.INTERVAL_1H).size()
                , interval2Symbol2TimeAndTicker.get(Constants.INTERVAL_4H).size()
                , interval2Symbol2TimeAndTicker.get(Constants.INTERVAL_1D).size()
        );
    }

    private void updateData() {
        long startTime = System.currentTimeMillis();
        interval2Symbol2TimeAndTicker.put(Constants.INTERVAL_1D, getMacdData(Constants.INTERVAL_1D));
        interval2Symbol2TimeAndTicker.put(Constants.INTERVAL_1H, getMacdData(Constants.INTERVAL_1H));
        interval2Symbol2TimeAndTicker.put(Constants.INTERVAL_4H, getMacdData(Constants.INTERVAL_4H));
        LOG.info("Finished update macd data: {} seconds", (System.currentTimeMillis() - startTime) / Utils.TIME_SECOND);
    }

    private Map<String, Map<Long, KlineObjectNumber>> getMacdData(String interval) {
        Map<String, Map<Long, KlineObjectNumber>> results = new HashMap<>();
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS)) {
            try {
                Map<Long, KlineObjectNumber> time2Ticker = new HashMap<>();
                List<KlineObjectNumber> allTickers = TickerFuturesHelper.getTicker(symbol, interval);
                RsiEntry[] rsi = RelativeStrengthIndex.calculateRSI(allTickers, 14);
                MACDEntry[] entries = MACD.calculate(allTickers, 12, 26, 9);
                Map<Double, Double> time2Rsi = new HashMap<>();
                Map<Double, Double> time2Ma = new HashMap<>();
                Map<Double, MACDEntry> time2Macd = new HashMap<>();
                for (RsiEntry rs : rsi) {
                    time2Rsi.put(rs.startTime, rs.getRsi());
                }
                for (MACDEntry entry : entries) {
                    time2Macd.put(entry.startTime, entry);
                }
                IndicatorEntry[] smaEntries = SimpleMovingAverage.calculate(allTickers, 20);
                for (IndicatorEntry sma : smaEntries) {
                    time2Ma.put(sma.startTime, sma.getValue());
                }
                for (KlineObjectNumber ticker : allTickers) {
                    MACDEntry macd = time2Macd.get(ticker.startTime);
                    ticker.rsi = time2Rsi.get(ticker.startTime);
                    ticker.ma20 = time2Ma.get(ticker.startTime);
                    if (macd != null) {
                        ticker.signal = macd.getSignal();
                        ticker.macd = macd.getMacd();
                        ticker.histogram = macd.getHistogram();
                    }
                    time2Ticker.put(ticker.startTime.longValue(), ticker);
                }
                results.put(symbol, time2Ticker);
            } catch (Exception e) {
                LOG.info("Error get macd data for: {} {}", symbol, interval);
                e.printStackTrace();
            }
        }
        return results;
    }


    public static void main(String[] args) throws ParseException {
        LOG.info("{}", MACDDataTradingManager.getInstance().interval2Symbol2TimeAndTicker.get(Constants.INTERVAL_1D).size());
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
