package com.binance.chuyennd.research;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class DcaHelper {
    public static final Logger LOG = LoggerFactory.getLogger(DcaHelper.class);

    public static OrderTargetInfoTest dcaOrder(OrderTargetInfoTest orderInfo, KlineObjectNumber ticker, Double rateTarget) {
        Double entryNew = (orderInfo.priceEntry + orderInfo.lastPrice) / 2;
        Double rateLoss = Utils.rateOf2Double(ticker.priceClose, orderInfo.priceEntry) * 100;
        LOG.info("Dca {} {}% entry:{} -> {} time:{} {}", orderInfo.symbol, rateLoss.longValue(), orderInfo.priceEntry, entryNew,
                Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart), Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
        orderInfo.quantity *= 2;
        orderInfo.priceEntry = entryNew;
        Double priceTp = Utils.calPriceTarget(orderInfo.symbol, orderInfo.priceEntry, orderInfo.side, rateTarget);
        orderInfo.priceTP = priceTp;
        orderInfo.maxPrice = ticker.priceClose;
        orderInfo.minPrice = ticker.minPrice;
        orderInfo.timeStart = ticker.startTime.longValue();
        if (orderInfo.dynamicTP_SL == null) {
            orderInfo.dynamicTP_SL = 0;
        }
        orderInfo.dynamicTP_SL++;
        return orderInfo;
    }

    public static boolean isDcaOrderBuy(List<KlineObjectNumber> tickers, OrderTargetInfoTest order, int index) {
        if (order != null) {
            return isDcaOrderBuyWithEntry(tickers, order.priceEntry, index);
        }
        return false;
    }

    private static boolean isDcaOrderBuyWithEntry(List<KlineObjectNumber> tickers, Double priceEntry, int index) {

        KlineObjectNumber ticker = tickers.get(index);
        // rate loss > 6%
        Double rateLoss = Utils.rateOf2Double(ticker.priceClose, priceEntry);
        if (rateLoss < -0.06) {
            // ticker reverse
            if (index > 1) {
                KlineObjectNumber lastTicker = tickers.get(index - 1);
                KlineObjectNumber ticker4h = TickerFuturesHelper.extractKlineByNumberTicker(tickers, index, 32);
                if (ticker.priceClose > ticker.priceOpen
                        && ticker.priceClose > lastTicker.priceOpen
                        && ticker4h != null
                        && (ticker.minPrice <= ticker4h.minPrice * 1.004
                        || lastTicker.minPrice <= ticker4h.minPrice * 1.004)
                ) {
                    return true;
                }
            }
        }

        return false;
    }

    public static boolean isDcaOrderSellWithEntry(List<KlineObjectNumber> tickers, Double priceEntry, int index) {
        KlineObjectNumber finalTicker = tickers.get(index);
        KlineObjectNumber lastTicker = tickers.get(index - 1);
        Double rateLoss = Utils.rateOf2Double(finalTicker.priceClose, priceEntry);
        if (rateLoss > 0.06) {
            try {
                Double max24h = lastTicker.maxPrice;
                Double maxVolume24h = lastTicker.totalUsdt;
                Boolean isHaveTickerBigUp = false;
                for (int i = 0; i < 96; i++) {
                    if (index >= i) {
                        KlineObjectNumber ticker = tickers.get(index - i);
                        if (Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) > 0.05) {
                            isHaveTickerBigUp = true;
                        }
                        if (maxVolume24h < ticker.totalUsdt) {
                            maxVolume24h = ticker.totalUsdt;
                        }
                        if (max24h < ticker.maxPrice) {
                            max24h = ticker.maxPrice;
                        }
                    }
                }
                Double rateFinal = Utils.rateOf2Double(finalTicker.priceClose, finalTicker.priceOpen);
                if (rateFinal < -0.003
                        && rateFinal > -0.05
                        && (finalTicker.maxPrice >= max24h || lastTicker.maxPrice >= max24h)
                        && (finalTicker.totalUsdt >= maxVolume24h || lastTicker.totalUsdt >= maxVolume24h)
                        && isHaveTickerBigUp
                ) {
                    return true;
                }

            } catch (
                    Exception e) {
                e.printStackTrace();
            }
            return false;
        }
        return false;
    }


//    public static void startCheckAndProcessDca(ConcurrentHashMap<String, List<KlineObjectNumber>> symbol2Tickers) {
//        try {
//            List<PositionRisk> positions = BinanceFuturesClientSingleton.getInstance().getAllPositionInfos();
//            for (PositionRisk position : positions) {
//                try {
//                    if (position.getPositionAmt().doubleValue() > 0) {
//                        String orderJson = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO,
//                                position.getSymbol());
//                        OrderTargetInfo order = Utils.gson.fromJson(orderJson, OrderTargetInfo.class);
//                        // for alt reverse extend
//                        if (
//                                StringUtils.equals(orderJson.ma, MarketLevelChange.ALT_BIG_CHANGE_REVERSE_EXTEND.toString())
//                        ) {
//                            List<KlineObjectNumber> tickers = symbol2Tickers.get(position.getSymbol());
//                            // check budget
//                            Double budget = BudgetManager.getInstance().getBudget() * 4;
//                            double margin = position.getPositionAmt().doubleValue() * position.getEntryPrice().doubleValue()
//                                    / position.getLeverage().doubleValue();
//                            if (margin <= budget * 1.05) {
//                                if (isDcaOrderBuyWithEntry(tickers, position.getEntryPrice().doubleValue(), tickers.size() - 1)) {
////                                    BinanceOrderTradingManager.dcaForPosition(position);
//                                }
//                            }
//                        }
//                        // for sell order
//                        if (
//                                StringUtils.equals(marketLevel, MarketLevelChange.ALT_SIGNAL_SELL.toString())
//                        ) {
//                            List<KlineObjectNumber> tickers = symbol2Tickers.get(position.getSymbol());
//                            // check budget
//                            Double budget = BudgetManager.getInstance().getBudget();
//                            double margin = position.getPositionAmt().doubleValue() * position.getEntryPrice().doubleValue()
//                                    / position.getLeverage().doubleValue();
//                            Double rateLoss = Utils.rateOf2Double(tickers.get(tickers.size() - 1).priceClose, position.getEntryPrice().doubleValue());
//                            if (margin <= budget * 1.05 || rateLoss > 0.4) {
//                                if (isDcaOrderSellWithEntry(tickers, position.getEntryPrice().doubleValue(), tickers.size() - 1)
//                                        || rateLoss > 0.4) {
////                                    BinanceOrderTradingManager.dcaForPosition(position);
//                                }
//                            }
//                        }
//                    }
//                } catch (Exception e) {
//                    e.printStackTrace();
//                }
//            }
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
//    }

    public static void main(String[] args) {
        try {
            String symbolCheck = "BOMEUSDT";
            Long startTime = Utils.sdfFileHour.parse("20240730 10:00").getTime();
            Long endTime = Utils.sdfFileHour.parse("20240801 05:45").getTime();
            Map<String, List<KlineObjectNumber>> symbol2Tickers = TickerFuturesHelper.getAllKlineStartTime(Constants.INTERVAL_15M, startTime);
            ConcurrentHashMap<String, List<KlineObjectNumber>> symbols2TickerCheck = new ConcurrentHashMap<>();
            symbols2TickerCheck.putAll(symbol2Tickers);
            List<KlineObjectNumber> tickers = new ArrayList<>();
            for (KlineObjectNumber ticker : symbol2Tickers.get(symbolCheck)) {
                if (ticker.startTime.longValue() <= endTime) {
                    tickers.add(ticker);
                }
            }
            symbols2TickerCheck.put(symbolCheck, tickers);
//            DcaHelper.startCheckAndProcessDca(symbols2TickerCheck);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
