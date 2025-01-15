package com.binance.chuyennd.bigchange.test;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TrendState;
import com.binance.chuyennd.trading.DetectEntrySignal2Trader;
import com.binance.chuyennd.trend.BtcTrendObject;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.logging.Level;

public class BTCTrendManager {
    public static final Logger LOG = LoggerFactory.getLogger(BTCTrendManager.class);
    public static TreeMap<Long, TrendState> time2Trend;
    private static volatile BTCTrendManager INSTANCE = null;

    public static BTCTrendManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new BTCTrendManager();
            INSTANCE.startThreadUpdateBtcTrend();
        }
        return INSTANCE;
    }


    public static void main(String[] args) {
//        try {
//            BTCTrendManager.getInstance().printTrendUp();
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
        System.out.println(BTCTrendManager.getInstance().getCurrentTrend());

    }

    private void printTrendUp() {
        Set<Long> times = new HashSet<>();
        TrendState lastTrend = null;
        for (Long time : time2Trend.keySet()) {
            if (lastTrend == null || !lastTrend.equals(time2Trend.get(time))) {
                if (time2Trend.get(time).equals(TrendState.TREND_UP)) {
                    times.add(time + 15 * Utils.TIME_MINUTE);
                    LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), lastTrend, time2Trend.get(time));
                }
                lastTrend = time2Trend.get(time);
            }
        }
        Storage.writeObject2File("storage/btc15m_reverse.data", times);
    }

    private void printTrend() {
        TrendState lastTrend = null;
        for (Long time : time2Trend.keySet()) {
            if (lastTrend == null || !lastTrend.equals(time2Trend.get(time))) {
                LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), lastTrend, time2Trend.get(time));
                lastTrend = time2Trend.get(time);
            }
        }
    }

    public TrendState getCurrentTrend() {
        long time = System.currentTimeMillis();
        time = Utils.getTimeInterval15m(time);
        return time2Trend.get(time);
    }


    private void startThreadUpdateBtcTrend() {
        time2Trend = new TreeMap<>();
        try {
            updateTrend();
        } catch (Exception e) {
            e.printStackTrace();
        }
        new Thread(() -> {
            Thread.currentThread().setName("ThreadUpdateBtcTrend15M");
            LOG.info("Start thread ThreadUpdateBtcTrend!");
            while (true) {
                if (Utils.getCurrentMinute() % 15 == 14 && Utils.getCurrentSecond() == 59) {
                    try {
                        updateTrend();
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
                try {
                    Thread.sleep(Utils.TIME_SECOND);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(DetectEntrySignal2Trader.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }).start();
    }

    private void updateTrend() {
        List<KlineObjectNumber> btcTickers = TickerFuturesHelper.getTicker(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_15M);
        LOG.info("Update btcTrend: {}", Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(btcTickers.size() - 1).startTime.longValue()));
        BtcTrendObject lastTrend = null;
        for (int i = 1; i < btcTickers.size(); i++) {
            KlineObjectNumber lastTicker = btcTickers.get(i - 1);
            KlineObjectNumber ticker = btcTickers.get(i);
            Double rate = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
            rate = Math.min(rate, Utils.rateOf2Double(ticker.priceClose, lastTicker.priceOpen));
            if (lastTrend == null && Math.abs(rate) > 0.008) {
                TrendState state = TrendState.TREND_DOWN;
                if (rate > 0) {
                    state = TrendState.TREND_UP;
                }
                lastTrend = new BtcTrendObject(state, ticker);
                LOG.info("TrendStart: {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()),
                        lastTrend.state.toString(), ticker.priceClose);

            } else {
                if (lastTrend != null) {
                    if (lastTrend.ticker.startTime.longValue() == ticker.startTime.longValue()) {
                        continue;
                    }
                    // update when ticker rate > 1%
                    if (Math.abs(rate) > 0.01) {
                        TrendState state = TrendState.TREND_DOWN;
                        if (rate > 0) {
                            state = TrendState.TREND_UP;
                        }
                        lastTrend = new BtcTrendObject(state, ticker);
                        LOG.info("TrendUpdate: {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()),
                                lastTrend.state.toString(), ticker.priceClose);
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
                        LOG.info("Ticker: {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()),
                                lastTrend.state.toString(), ticker.priceClose);
                    }
                }
            }
            if (lastTrend != null) {
                time2Trend.put(ticker.startTime.longValue(), lastTrend.state);
            }
        }
    }
}
