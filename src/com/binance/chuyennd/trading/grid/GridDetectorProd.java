package com.binance.chuyennd.trading.grid;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.grid.GridObjectTestResearch;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.GridConfigs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;

import java.util.List;

public class GridDetectorProd {
    public static GridObjectProduction findRange2RunProd(String symbol) {
        Long time = System.currentTimeMillis();
        Double maxPrice = null;
        Double minPrice = null;
        List<KlineObjectSimple> ticker1Ms = TickerFuturesHelper.getTickerSimpleWithStartTime(symbol, Constants.INTERVAL_1M,
                System.currentTimeMillis() - 4 * Utils.TIME_HOUR);
        List<KlineObjectNumber> ticker1Ds = TickerFuturesHelper.getTickerWithStartTime(symbol, Constants.INTERVAL_1D,
                System.currentTimeMillis() - 60 * Utils.TIME_DAY);
        KlineObjectSimple ticker = ticker1Ms.get(ticker1Ms.size() - 1);
        for (KlineObjectNumber kline : ticker1Ds) {
            maxPrice = Utils.maxPrice(kline, maxPrice);
            minPrice = Utils.minPrice(kline, minPrice);

        }
        if (maxPrice == null || minPrice == null) {
            return null;
        }

        Double rate4h = Utils.rateOf2Double(ticker1Ms.get(0).priceClose, ticker1Ms.get(ticker1Ms.size() - 1).priceOpen);
        OrderSide side = OrderSide.BUY;
        Double differenceMa20AndMa60 = SimpleMovingAverageDayManagerProduction.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
        Double difference4hMa20AndMa60 = SimpleMovingAverage4hManagerProduction.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
        if (differenceMa20AndMa60 != null && difference4hMa20AndMa60 != null) {
            if (symbol.equals(Constants.SYMBOL_PAIR_SOL)
                    || symbol.equals(Constants.SYMBOL_PAIR_XRP)) {
                Double differenceMaBnb20AndMa60 = SimpleMovingAverageDayManagerProduction.getInstance().getDifferenceMa10AndMa60(symbol
                        , time);
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
        if (side.equals(OrderSide.SELL)) {
            if (rate4h != null ) {
                if (rate4h < -GridConfigs.RATE_DOWN_4H_REVERSE) {
                    side = OrderSide.BUY;
                }
            }
        }
        if (side.equals(OrderSide.BUY)) {
            if (maxPrice < ticker.priceClose * 1.25) {
                maxPrice = Utils.calPriceTarget(symbol, ticker.priceClose, OrderSide.BUY, 0.25);
            }
            minPrice = Utils.calPriceTarget(symbol, ticker.priceClose, OrderSide.SELL, 0.25);
        } else {
            maxPrice = Utils.calPriceTarget(symbol, ticker.priceClose, OrderSide.BUY, 0.25);
            if (minPrice > ticker.priceClose * 0.85) {
                minPrice = Utils.calPriceTarget(symbol, ticker.priceClose, OrderSide.SELL, 0.15);
            }
        }
        GridObjectProduction simulator = new GridObjectProduction(symbol, side, maxPrice, minPrice, ticker);
        return simulator;
    }

    public static GridObjectTestResearch findRange2RunProd(String symbol, KlineObjectSimple ticker, Double rate4h) {
        Long time = System.currentTimeMillis();
        Double maxPrice = null;
        Double minPrice = null;

        List<KlineObjectNumber> ticker1Ds = TickerFuturesHelper.getTickerWithStartTime(symbol, Constants.INTERVAL_1D,
                System.currentTimeMillis() - 60 * Utils.TIME_DAY);

        for (KlineObjectNumber kline : ticker1Ds) {
            maxPrice = Utils.maxPrice(kline, maxPrice);
            minPrice = Utils.minPrice(kline, minPrice);

        }
        if (maxPrice == null || minPrice == null) {
            return null;
        }
        OrderSide side = OrderSide.BUY;
        Double differenceMa20AndMa60 = SimpleMovingAverageDayManagerProduction.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
        Double difference4hMa20AndMa60 = SimpleMovingAverage4hManagerProduction.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
        if (differenceMa20AndMa60 != null && difference4hMa20AndMa60 != null) {
            if (symbol.equals(Constants.SYMBOL_PAIR_BNB)
                    || symbol.equals(Constants.SYMBOL_PAIR_XRP)) {
                Double differenceMaBnb20AndMa60 = SimpleMovingAverageDayManagerProduction.getInstance().getDifferenceMa10AndMa60(symbol
                        , time);
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
        if (side.equals(OrderSide.SELL)) {
            if (rate4h != null) {
                if (rate4h <= -GridConfigs.RATE_DOWN_4H_REVERSE) {
                    side = OrderSide.BUY;
                }
            }
        }
        if (side.equals(OrderSide.BUY)) {
            if (maxPrice < ticker.priceClose * 1.25) {
                maxPrice = ticker.priceClose * 1.25;
            }
            minPrice = ticker.priceClose * 0.75;
        } else {
            maxPrice = ticker.priceClose * 1.25;
            if (minPrice > ticker.priceClose * 0.85) {
                minPrice = ticker.priceClose * 0.85;
            }
        }
        GridObjectTestResearch simulator = new GridObjectTestResearch(symbol, side, maxPrice, minPrice, ticker);
        return simulator;
    }
}
