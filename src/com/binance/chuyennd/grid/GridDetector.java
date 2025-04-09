package com.binance.chuyennd.grid;

import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.GridConfigs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;

public class GridDetector {
    public static final Logger LOG = LoggerFactory.getLogger(GridDetector.class);

    public static GridObjectTestResearch findGridSpecialSymbol(String symbol, KlineObjectSimple ticker, Long
            startTime, List<KlineObjectNumber> ticker15Ms, Double differenceMa20AndMa60, Double difference4hMa20AndMa60, Double rate4h) {
        Double maxPrice = null;
        Double minPrice = null;

        for (KlineObjectNumber kline : ticker15Ms) {
            if (kline.startTime.longValue() < Utils.getDate(startTime)
                    && kline.startTime.longValue() > startTime - 60 * Utils.TIME_DAY) {
//                LOG.info("GetMaxMin: {} {} {}", symbol, Utils.normalizeDateYYYYMMDD(kline.startTime.longValue()), Utils.normalizeDateYYYYMMDD(startTime));
                maxPrice = Utils.maxPrice(kline, maxPrice);
                minPrice = Utils.minPrice(kline, minPrice);
            }
        }
        if (maxPrice == null || minPrice == null) {
            return null;
        }

        OrderSide side = OrderSide.BUY;

        if (differenceMa20AndMa60 != null && difference4hMa20AndMa60 != null) {
            if (symbol.equals(Constants.SYMBOL_PAIR_SOL)
                    || symbol.equals(Constants.SYMBOL_PAIR_XRP)
            ) {
                Double differenceMaBnb20AndMa60 = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(symbol
                        , ticker.startTime.longValue());
                if (differenceMaBnb20AndMa60 != null) {
                    if (differenceMa20AndMa60 < 0 && difference4hMa20AndMa60 < 0 && differenceMaBnb20AndMa60 < 0) {
                        side = OrderSide.SELL;
                    }
                }
            } else {
                if (symbol.equals(Constants.SYMBOL_PAIR_BTC)) {
                    if (differenceMa20AndMa60 < 0) {
                        side = OrderSide.SELL;
                    }
                } else {
                    if (differenceMa20AndMa60 < 0 && difference4hMa20AndMa60 < 0) {
                        side = OrderSide.SELL;
                    }
                }
            }
        }
//        if (side.equals(OrderSide.SELL)) {
//            if (rate4h != null) {
//                if (rate4h <= -GridConfigs.RATE_DOWN_4H_REVERSE) {
//                    side = OrderSide.BUY;
//                }
//            }
//        }
        if (side.equals(OrderSide.SELL)) {
            if (rate4h != null) {
                if (rate4h < GridConfigs.RATE_DOWN_4H_REVERSE) {
                    return null;
                }
            }
        } else {
            if (rate4h != null) {
                if (rate4h > -GridConfigs.RATE_DOWN_4H_REVERSE) {
                    return null;
                }
            }
        }
        if (side.equals(OrderSide.BUY)) {
            if (maxPrice < ticker.priceClose * 1.25) {
                maxPrice = ticker.priceClose * 1.25;
            }
            minPrice = ticker.priceClose * 0.8;
        } else {
            maxPrice = ticker.priceClose * 1.25;
            if (minPrice > ticker.priceClose * 0.85) {
                minPrice = ticker.priceClose * 0.85;
            }
        }
        GridObjectTestResearch simulator = new GridObjectTestResearch(symbol, side, maxPrice, minPrice, ticker);
        return simulator;
    }

    public static GridObjectALTResearch findGridAltSymbol(String symbol, List<KlineObjectNumber> ticker4Hours) {
        KlineObjectNumber ticker = ticker4Hours.get(ticker4Hours.size() - 1);
//        try {
//            if (ticker.startTime.longValue() == Utils.sdfFileHour.parse("20250215 03:00").getTime()) {
//                System.out.println("Debug");
//            }
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
        Double differenceMa4Hour20AndMa60 = SimpleMovingAverage4hManager.getInstance().getDifferenceMa10AndMa60(symbol
                , ticker.startTime.longValue());
        Double differenceMaDay20AndMa60 = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(symbol, ticker.startTime.longValue());
        Double differenceBTCMaDay20AndMa60 = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, ticker.startTime.longValue());
        if (differenceMaDay20AndMa60 != null
                && differenceMaDay20AndMa60 < 0
                && differenceBTCMaDay20AndMa60 != null
                && differenceBTCMaDay20AndMa60 < 0) {
            Double maxPrice = null;
            Double minPrice = null;

            for (int i = 0; i < 10; i++) {
                KlineObjectNumber tickerCheck = ticker4Hours.get(ticker4Hours.size() - i - 1);
                maxPrice = Utils.maxPrice(tickerCheck, maxPrice);
                minPrice = Utils.minPrice(tickerCheck, minPrice);
            }
            if (Utils.rateOf2Double(maxPrice, minPrice) < 0.1
                    && Utils.rateOf2Double(ticker.priceClose, minPrice) < 0.03) {
                OrderSide side = OrderSide.SELL;
                if (side.equals(OrderSide.BUY)) {
                    if (maxPrice < ticker.priceClose * 1.25) {
                        maxPrice = ticker.priceClose * 1.25;
                    }
                    minPrice = ticker.priceClose * 0.8;
                } else {
                    maxPrice = ticker.priceClose * 1.2;
                    if (minPrice > ticker.priceClose * 0.5) {
                        minPrice = ticker.priceClose * 0.5;
                    }
                }
                GridObjectALTResearch simulator = new GridObjectALTResearch(symbol, side, maxPrice, minPrice, Utils.convertKlineSimple(ticker));
                return simulator;
            }
        }
        return null;
    }

}
