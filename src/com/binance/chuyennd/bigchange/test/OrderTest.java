package com.binance.chuyennd.bigchange.test;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;

public class OrderTest {
    public static final Logger LOG = LoggerFactory.getLogger(OrderTest.class);

    public static void main(String[] args) {
        try {
            String symbol = "IOTAUSDT";
            Long startTime = Utils.sdfFileHour.parse("20210519 19:43").getTime();
            List<KlineObjectSimple> tickers = TickerFuturesHelper.getTickerSimpleWithStartTime(symbol, Constants.INTERVAL_1M, startTime);
            KlineObjectSimple lastTicker = tickers.get(0);
            KlineObjectSimple ticker = tickers.get(1);
            Double target = Utils.rateOf2Double(ticker.priceOpen, ticker.priceClose);
            if (lastTicker != null
                    && Utils.rateOf2Double(lastTicker.priceClose, lastTicker.priceOpen) < 0) {
                target = Utils.rateOf2Double(lastTicker.priceOpen, ticker.priceClose);
            }
            new SimulatorMarketLevelTicker1MStopLoss().createOrderBUYTarget(symbol, ticker, MarketLevelChange.BIG_DOWN, null);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
