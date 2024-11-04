package com.binance.chuyennd.research;

import com.binance.chuyennd.indicators.SimpleMovingAverage;
import com.binance.chuyennd.object.IndicatorEntry;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TrendState;
import com.binance.chuyennd.trend.BtcTrendObject;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class

BTCTrendManagerTest {
    public static final Logger LOG = LoggerFactory.getLogger(BTCTrendManagerTest.class);

    public static void main(String[] args) {
        try {
//            Long time = Utils.sdfFileHour.parse("20241011 02:40").getTime();
//            System.out.println(BTCTrendManager.getInstance().getTrend(time));
//            BTCTrendManager.getInstance().printTrend();
//            System.out.println(new BTCTrendManagerTest().readTimeReverse(Constants.SYMBOL_PAIR_BNB).size());
//            String symbol = "OGNUSDT";
//            Set<Long> times = new BTCTrendManagerTest().extractBtcSideWayWithVolumeMa300(symbol);
//            System.out.println(new BTCTrendManagerTest().readTimeReverse(Constants.SYMBOL_PAIR_BNB).size());
//            System.out.println(new BTCTrendManagerTest().readTimeReverse(Constants.SYMBOL_PAIR_ETH).size());
//            System.out.println(new BTCTrendManagerTest().readTimeReverse(Constants.SYMBOL_PAIR_XRP).size());
//            System.out.println(new BTCTrendManagerTest().readTimeReverse(Constants.SYMBOL_PAIR_SOL).size());
            for (Long time : new BTCTrendManagerTest().readTimeReverse(Constants.SYMBOL_PAIR_BTC)) {
                LOG.info("{}", Utils.sdfGoogle.format(new Date(time)));
            }
//            new BTCTrendManagerTest().printTrendUpNew();
//            BTCTrendManagerTest.testTrend();
//
//            Set<Long> time1 = (Set<Long>) Storage.readObjectFromFile("storage/btc15m_reverse_new.data");
//            Set<Long> time2 = (Set<Long>) Storage.readObjectFromFile("storage/btc15m_reverse.data");
//            for (Long time : time1) {
//                if (!time2.contains(time)) {
//                    LOG.info("1 not 2 {}", Utils.normalizeDateYYYYMMDDHHmm(time));
//                }
//            }
//            for (Long time : time2) {
//                if (!time1.contains(time)) {
//                    LOG.info("2 not 1 {}", Utils.normalizeDateYYYYMMDDHHmm(time));
//                }
//            }
//            LOG.info("{} {}", time1.size(), time2.size());
        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    private static void testTrend() {

        List<KlineObjectNumber> btcTickers = (List<KlineObjectNumber>)
                Storage.readObjectFromFile(Configs.FOLDER_TICKER_15M + Constants.SYMBOL_PAIR_BTC);
        Set<Long> times = new HashSet<>();
        for (int i = 1; i < btcTickers.size(); i++) {
            if (i < 100) {
                continue;
            }
            try {
                if (btcTickers.get(i).startTime.longValue() == Utils.sdfFileHour.parse("20241015 21:45").getTime()) {
                    System.out.println("Debug");
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            List<KlineObjectNumber> tickers = new ArrayList<>();
            for (int j = 0; j < 101; j++) {
                tickers.add(btcTickers.get(i - 100 + j));
            }
            if (BTCTrendManagerTest.isTrendBuy(tickers)) {
                LOG.info("Btc trend: {}", Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(i).startTime.longValue()),
                        Utils.normalizeDateYYYYMMDDHHmm(tickers.get(tickers.size() - 1).startTime.longValue()));
                times.add(btcTickers.get(i).startTime.longValue() + 15 * Utils.TIME_MINUTE);
            }
        }
        Storage.writeObject2File("storage/btc15m_reverse_new.data", times);
    }

    private static boolean isTrendBuy(List<KlineObjectNumber> tickers) {
        Double rateOfTrend = 0.008;
        BtcTrendObject lastTrend = null;
        TreeMap<Long, BtcTrendObject> time2TrendDetect = new TreeMap<>();
        for (int i = 1; i < tickers.size(); i++) {
            KlineObjectNumber lastTicker = tickers.get(i - 1);
            KlineObjectNumber ticker = tickers.get(i);
            Double rate = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
            rate = Math.min(rate, Utils.rateOf2Double(ticker.priceClose, lastTicker.priceOpen));
            if (lastTrend == null && Math.abs(rate) > rateOfTrend) {
                TrendState state = TrendState.TREND_DOWN;
                if (rate > 0) {
                    state = TrendState.TREND_UP;
                }
                lastTrend = new BtcTrendObject(state, ticker);
            } else {
                if (lastTrend != null) {
                    if (lastTrend.ticker.startTime.longValue() == ticker.startTime.longValue()) {
                        continue;
                    }
                    // update when ticker rate > 1%
                    if (Math.abs(rate) > rateOfTrend) {
                        TrendState state = TrendState.TREND_DOWN;
                        if (rate > 0) {
                            state = TrendState.TREND_UP;
                        }
                        lastTrend = new BtcTrendObject(state, ticker);
                    } else {
                        // update when price over trend
                        if (Utils.rateOf2Double(lastTrend.ticker.priceClose, lastTrend.ticker.priceOpen) > 0) {
                            if (ticker.priceClose < lastTrend.ticker.priceOpen) {
                                lastTrend.state = TrendState.TREND_DOWN;
                            } else {
                                if (ticker.priceClose > lastTrend.ticker.priceClose) {
                                    lastTrend.state = TrendState.TREND_UP;
                                } else {
                                    lastTrend.state = TrendState.SIDEWAY;
                                }
                            }
                        } else {
                            if (ticker.priceClose > lastTrend.ticker.priceOpen) {
                                lastTrend.state = TrendState.TREND_UP;
                            } else {
                                if (ticker.priceClose < lastTrend.ticker.priceClose) {
                                    lastTrend.state = TrendState.TREND_DOWN;
                                } else {
                                    lastTrend.state = TrendState.SIDEWAY;
                                }
                            }
                        }
                    }
                }
            }
            if (lastTrend != null) {
                time2TrendDetect.put(ticker.startTime.longValue(), new BtcTrendObject(lastTrend.state, ticker));
            }
        }
        lastTrend = time2TrendDetect.get(tickers.get(tickers.size() - 2).startTime.longValue());
        BtcTrendObject finalTrend = time2TrendDetect.get(tickers.get(tickers.size() - 1).startTime.longValue());
        if (lastTrend != null && !lastTrend.state.equals(finalTrend.state)
                && (finalTrend.state.equals(TrendState.TREND_UP)
//                || lastTrend.state.equals(TrendState.TREND_DOWN)
        )) {
            return true;
        } else {
            return false;
        }
    }

    public Set<Long> printTrendUp(String symbol, TreeMap<Long, BtcTrendObject> time2Trend) {
        Set<Long> times = new HashSet<>();
        TrendState lastTrend = time2Trend.firstEntry().getValue().state;
        for (Long time : time2Trend.keySet()) {
            if (!lastTrend.equals(time2Trend.get(time).state)) {
                if (time2Trend.get(time).state.equals(TrendState.TREND_UP)) {
                    times.add(time + 15 * Utils.TIME_MINUTE);
                    LOG.info("{} trend: {} {} -> {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time + 15 * Utils.TIME_MINUTE),
                            Utils.sdfGoogle.format(new Date(time + 15 * Utils.TIME_MINUTE)), lastTrend, time2Trend.get(time).state,
                            time2Trend.get(time).ticker.priceClose);
                }
                lastTrend = time2Trend.get(time).state;
            }
        }
        return times;
    }

    public TreeMap<Long, BtcTrendObject> initWithDataRaw(String symbol) {
        TreeMap<Long, BtcTrendObject> time2Trend = new TreeMap<>();
        Double rateOfTrend = 0.01;
        List<KlineObjectNumber> btcTickers = (List<KlineObjectNumber>)
                Storage.readObjectFromFile(Configs.FOLDER_TICKER_15M + symbol);
        LOG.info("Read data new: {}", Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(0).startTime.longValue()));
        BtcTrendObject lastTrend = null;
        Double maxTime = 0d;
        for (int i = 1; i < btcTickers.size(); i++) {
            KlineObjectNumber lastTicker = btcTickers.get(i - 1);
            KlineObjectNumber ticker = btcTickers.get(i);
            try {
                if (ticker.startTime.longValue() == Utils.sdfFileHour.parse("20240823 21:45").getTime()) {
                    System.out.println("Debug");
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            Double rate = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
            if (rate > -rateOfTrend) {
                rate = Math.min(rate, Utils.rateOf2Double(ticker.priceClose, lastTicker.priceOpen));
            }
            if (lastTrend == null && rate < -rateOfTrend) {
                TrendState state = TrendState.TREND_DOWN;
                KlineObjectNumber tickerTrend = Utils.cloneKlineObjectNumber(ticker);
                tickerTrend.priceOpen = Math.max(ticker.priceOpen, lastTicker.priceOpen);
                lastTrend = new BtcTrendObject(state, tickerTrend);
                LOG.info("TrendStart: {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()),
                        lastTrend.state.toString(), ticker.priceClose);

            } else {
                if (lastTrend != null) {
                    if (lastTrend.ticker.startTime.longValue() == ticker.startTime.longValue()) {
                        continue;
                    }
                    // update when ticker rate > 1%
                    if (rate < -rateOfTrend) {
                        TrendState state = TrendState.TREND_DOWN;
                        KlineObjectNumber tickerTrend = Utils.cloneKlineObjectNumber(ticker);
                        tickerTrend.priceOpen = Math.max(ticker.priceOpen, lastTicker.priceOpen);
                        lastTrend = new BtcTrendObject(state, tickerTrend);
                        LOG.info("TrendUpdate: {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()),
                                lastTrend.state.toString(), ticker.priceClose);
                    } else {
                        if (ticker.startTime.longValue() - lastTrend.ticker.startTime.longValue() >= 4 * Utils.TIME_HOUR
                                || lastTrend.state.equals(TrendState.TREND_UP)) {
                            lastTrend.state = TrendState.UNKNOWN;
                        }
                        // not update until trendown new if state UNKNOWN
                        if (!lastTrend.state.equals(TrendState.UNKNOWN)) {
                            // update when price over trend
                            if (ticker.priceClose > lastTrend.ticker.priceOpen) {
                                if (lastTrend.state.equals(TrendState.SIDEWAY)) {
                                    double timeDistance = (ticker.endTime - lastTrend.ticker.startTime) / Utils.TIME_MINUTE;
                                    if (timeDistance > maxTime) {
                                        maxTime = timeDistance;
                                        LOG.info("Time 2 reverse: {} {} {}",
                                                timeDistance, lastTrend.ticker.priceOpen, ticker.priceClose);
                                    }

                                    lastTrend.state = TrendState.TREND_UP;
                                } else {
                                    lastTrend.state = TrendState.UNKNOWN;
                                }
                            } else {
                                if (ticker.priceClose < lastTrend.ticker.priceClose) {
                                    lastTrend.state = TrendState.TREND_DOWN;
                                } else {
                                    lastTrend.state = TrendState.SIDEWAY;
                                }
                            }
                        }
                    }
                }
            }
            if (lastTrend != null) {
                time2Trend.put(ticker.startTime.longValue(), new BtcTrendObject(lastTrend.state, ticker));
                LOG.info("Ticker: {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()),
                        lastTrend.state.toString(), ticker.priceClose);
            }
        }
        return time2Trend;
    }

    public Set<Long> readTimeReverse(String symbol) {
        TreeMap<Long, BtcTrendObject> time2Trend = initWithDataRaw(symbol);
        return printTrendUp(symbol, time2Trend);

    }
}
