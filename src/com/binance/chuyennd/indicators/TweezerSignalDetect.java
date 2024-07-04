package com.binance.chuyennd.indicators;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.List;

public class TweezerSignalDetect {
    public static final Logger LOG = LoggerFactory.getLogger(TweezerSignalDetect.class);

    public static void main(String[] args) throws ParseException {
        String symbol = "HIGHUSDT";
        List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile("storage/ticker/symbols-15m/" + symbol);
        int counter = 0;
        int total = 0;
        for (int i = 1; i < tickers.size(); i++) {
            KlineObjectNumber ticker = tickers.get(i);
            if (tickers.get(i).startTime.longValue() == Utils.sdfFileHour.parse("20240317 08:00").getTime()) {
                System.out.println("Debug");
            }
//            if (TweezerSignalDetect.isTweezerTop(tickers.get(i), tickers.get(i - 1))) {
//                LOG.info("Top: {} {}", Utils.normalizeDateYYYYMMDDHHmm(tickers.get(i).startTime.longValue()), tickers.get(i).priceOpen);
//            }
            if (TweezerSignalDetect.isTweezerBottom(tickers.get(i), tickers.get(i - 1))
//                    && ticker.priceClose > ticker.ma20
            ) {
                Double maxPrice = TickerFuturesHelper.getMaxPrice(tickers, i, 64);
                Double rate = Utils.rateOf2Double(maxPrice, tickers.get(i).priceClose);
                LOG.info("Bottom: {} {} max:{} -> {} {}", Utils.normalizeDateYYYYMMDDHHmm(tickers.get(i).startTime.longValue()), tickers.get(i).priceOpen,
                        maxPrice, rate, tickers.get(i).rsi);
                total++;
                if (rate > 0.01) {
                    counter++;
                }
            }
        }
        LOG.info("{}/{} {}%", counter, total, counter * 100 / total);
    }

    private static boolean isTweezerTop(KlineObjectNumber kline, KlineObjectNumber lastKline) {
        if (TickerFuturesHelper.getSideOfTicer(lastKline).equals(OrderSide.BUY)
                && TickerFuturesHelper.getSideOfTicer(kline).equals(OrderSide.SELL)
                && Utils.rateOf2Double(kline.maxPrice, kline.priceOpen) <= 0.0003
                && Utils.rateOf2Double(lastKline.maxPrice, lastKline.priceClose) <= 0.0003
        ) {
            return true;
        }
        return false;
    }

    private static boolean isTweezerBottom(KlineObjectNumber kline, KlineObjectNumber lastKline) {
        if (TickerFuturesHelper.getSideOfTicer(lastKline).equals(OrderSide.SELL)
                && TickerFuturesHelper.getSideOfTicer(kline).equals(OrderSide.BUY)
                && Utils.rateOf2Double(kline.priceOpen, kline.minPrice) <= 0.0003
                && Utils.rateOf2Double(lastKline.priceClose, lastKline.minPrice) <= 0.0003
                && Math.abs(TickerFuturesHelper.getRateChangeOfTicker(kline)) > Math.abs(TickerFuturesHelper.getRateChangeOfTicker(lastKline))

        ) {
            return true;
        }
        return false;
    }
}
