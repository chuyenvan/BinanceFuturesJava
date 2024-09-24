package com.binance.chuyennd.bigchange.statistic;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TrendObject;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;

public class Trend4hManager {
    public static final Logger LOG = LoggerFactory.getLogger(Trend4hManager.class);
    private static volatile Trend4hManager INSTANCE = null;

    public String SYMBOL;
    public Long startTime;
    public List<KlineObjectNumber> ticker4Hours;
    public List<TrendObject> trends;

    public static Trend4hManager getInstance(String symbol, Long startTime) {
        if (INSTANCE == null) {
            if (Utils.get4Hour(startTime) != startTime) {
                LOG.info("Time init error: {} timeCorrect:{}", Utils.normalizeDateYYYYMMDDHHmm(startTime),
                        Utils.normalizeDateYYYYMMDDHHmm(Utils.get4Hour(startTime)));
                return null;
            }
            INSTANCE = new Trend4hManager();
            INSTANCE.SYMBOL = symbol;
            INSTANCE.startTime = startTime;
            INSTANCE.ticker4Hours = new ArrayList<>();
            if (StringUtils.isEmpty(INSTANCE.SYMBOL) || startTime == null) {
                return null;
            } else {
                INSTANCE.initTickers();
            }
            LOG.info("Init trend manager for: {} {}", INSTANCE.SYMBOL, Utils.normalizeDateYYYYMMDDHHmm(startTime));
        }
        return INSTANCE;
    }


    public void updateTicker(KlineObjectNumber ticker) {
        KlineObjectNumber lastTicker = ticker4Hours.get(ticker4Hours.size() - 1);
        Long time = Utils.get4Hour(ticker.startTime.longValue());
        if (time.equals(lastTicker.startTime.longValue())) {
            if (lastTicker.maxPrice < ticker.maxPrice) {
                lastTicker.maxPrice = ticker.maxPrice;
            }
            if (lastTicker.minPrice > ticker.minPrice) {
                lastTicker.minPrice = ticker.minPrice;
            }
            lastTicker.totalUsdt += ticker.totalUsdt;
            lastTicker.priceClose = ticker.priceClose;
        } else {
            if (time < lastTicker.startTime.longValue()){
                return;
            }
//            LOG.info("Add new ticker -> lastTicker: {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(lastTicker.startTime.longValue()),
//                    lastTicker.totalUsdt, lastTicker.maxPrice, lastTicker.priceClose, lastTicker.priceOpen);
            lastTicker = ticker;
            lastTicker.startTime = time.doubleValue();
            lastTicker.endTime = time.doubleValue() + 4 * Utils.TIME_HOUR - 1;
            ticker4Hours.add(lastTicker);
        }
//        trends = TickerFuturesHelper.extractTopBottomObjectInTicker(ticker4Hours);
    }

    private void initTickers() {
        List<KlineObjectNumber> tickers = TickerFuturesHelper.getTickerWithStartTime(SYMBOL, Constants.INTERVAL_4H,
                startTime - 100 * 4 * Utils.TIME_HOUR);
        LOG.info("Ticker 4h for init data time from: {} to {}", Utils.normalizeDateYYYYMMDDHHmm(tickers.get(0).startTime.longValue()),
                Utils.normalizeDateYYYYMMDDHHmm(tickers.get(tickers.size() - 1).startTime.longValue()));
        for (KlineObjectNumber ticker : tickers) {
            if (startTime.equals(ticker.startTime.longValue())) {
                break;
            }
            ticker4Hours.add(ticker);
        }
        trends = TickerFuturesHelper.extractTopBottomObjectInTicker(ticker4Hours);
    }

    public OrderSide getCurrentTrend(KlineObjectNumber kline) {
//        TrendObject finalTrend = trends.get(trends.size() - 1);
        KlineObjectNumber lastFinalTicker4h = ticker4Hours.get(ticker4Hours.size() - 2);
        KlineObjectNumber finalTicker4h = ticker4Hours.get(ticker4Hours.size() - 1);
        OrderSide result = null;
//        if (finalTrend.status.equals(TrendState.TOP)) {
            if (finalTicker4h.minPrice > lastFinalTicker4h.minPrice) {
                result = OrderSide.BUY;
            }
//            if (finalTicker4h.minPrice < finalTrend.getMinPrice()) {
//                result = OrderSide.SELL;
//            }
//        }
//        if (finalTrend.status.equals(TrendState.BOTTOM)) {
//            if (kline.minPrice <= finalTrend.getMinPrice()) {
//                result = OrderSide.SELL;
//            }
//            if (finalTicker4h.minPrice > finalTrend.getMinPrice()) {
//                result = OrderSide.BUY;
//            }
//        }
//        LOG.info("{} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(kline.startTime.longValue()), finalTrend.status,
//                Utils.normalizeDateYYYYMMDDHHmm(finalTrend.kline.startTime.longValue()), result);
        return result;
    }

    private static void testTrend4h() {
        String symbol = "BAKEUSDT";
        List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_15M + symbol);
        long timeInitTrend4h = Utils.get4Hour(tickers.get(0).startTime.longValue()) + 4 * Utils.TIME_HOUR;
        long timeStart = Utils.get4Hour(timeInitTrend4h) + 4 * Utils.TIME_HOUR;
        for (KlineObjectNumber ticker : tickers) {
            if (ticker.startTime.longValue() < timeStart) {
                continue;
            }
            Trend4hManager.getInstance(symbol, timeStart).updateTicker(ticker);
            OrderSide trend = Trend4hManager.getInstance(symbol, timeStart).getCurrentTrend(ticker);

        }
    }

    public static void main(String[] args) {
        testTrend4h();
    }
}
