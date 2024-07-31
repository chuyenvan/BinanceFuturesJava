package com.binance.chuyennd.bigchange.statistic;

import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class BTCTicker15MManager {
    public static final Logger LOG = LoggerFactory.getLogger(BTCTicker15MManager.class);
    private static volatile BTCTicker15MManager INSTANCE = null;
    private static String FILE_DATA_STORAGE_MADETAIL = "storage/btc_price_15m.data";
    public Map<Long, KlineObjectNumber> time2Ticker = new HashMap<>();


    public static BTCTicker15MManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new BTCTicker15MManager();
            INSTANCE.initData();
        }
        return INSTANCE;
    }

    private void initData() {
        List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile("storage/ticker/symbols-15m/" + Constants.SYMBOL_PAIR_BTC);
        for (KlineObjectNumber ticker : tickers) {
            time2Ticker.put(ticker.startTime.longValue(), ticker);
        }
        LOG.info("Init data success");
    }

    public static void main(String[] args) throws ParseException {
//        List<KlineObjectNumber> ticker1ps = TickerFuturesHelper.getTickerWithStartTimeFull(Constants.SYMBOL_PAIR_BTC,
//                Constants.INTERVAL_15M, System.currentTimeMillis() - Utils.TIME_DAY - 15 * Utils.TIME_MINUTE);
//        LOG.info("{} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker1ps.get(0).startTime.longValue()),
//                Utils.normalizeDateYYYYMMDDHHmm(ticker1ps.get(ticker1ps.size() - 1).startTime.longValue()),
//                ticker1ps.get(ticker1ps.size() - 1).priceClose, ticker1ps.get(0).priceOpen,
//                Utils.rateOf2Double(ticker1ps.get(ticker1ps.size() - 1).priceClose, ticker1ps.get(0).priceOpen));
        long time = Utils.sdfFileHour.parse("20240401 07:00").getTime();
//        for (int i = 0; i < 10; i++) {
//            long time = Utils.getStartTimeDayAgo(5 + i) + 7 * Utils.TIME_HOUR;
//            BTCTicker15MManager.getInstance().getRate24h(time);
//        }

    }

    public Double getRate24h(long time) {
//        long lastTime = time - Utils.TIME_DAY;
        long lastTime = time - 4 * Utils.TIME_HOUR;
        KlineObjectNumber lastTicker = time2Ticker.get(lastTime);
        KlineObjectNumber ticker = time2Ticker.get(time);
        if (lastTicker != null && ticker != null) {
//            LOG.info("{} {} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time),
//                    lastTicker.priceOpen, ticker.priceOpen, Utils.rateOf2Double(ticker.priceOpen, lastTicker.priceOpen),
//                    Utils.normalizeDateYYYYMMDDHHmm(lastTicker.startTime.longValue()), Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
            return Utils.rateOf2Double(ticker.priceOpen, lastTicker.priceOpen);
        }
        return null;
    }
    public Double getRateWithMaxByDuration(long time, Long duration) {
        long lastTime = time - duration;
        Double minPriceClosed = null;
        Double priceCheck = null;
        KlineObjectNumber tickerCheck = time2Ticker.get(time);
        if (tickerCheck != null) {
            priceCheck = tickerCheck.priceClose;
        }
        while (true) {
            if (lastTime > time){
                break;
            }
            KlineObjectNumber ticker = time2Ticker.get(lastTime);
            if (ticker != null) {
                if (minPriceClosed == null || minPriceClosed > ticker.priceClose){
                    minPriceClosed = ticker.priceClose;
                }
            }
            lastTime += 15 * Utils.TIME_MINUTE;
        }
        if (minPriceClosed != null && priceCheck != null){
            return Utils.rateOf2Double(priceCheck, minPriceClosed);
        }
        return null;
    }

    public KlineObjectNumber getTickerByTime(Long time) {
        return time2Ticker.get(time);
    }
}
