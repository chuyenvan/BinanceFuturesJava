package com.binance.chuyennd.trading;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.client.BinanceFuturesClientSingleton;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.trade.PositionRisk;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
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
        if (orderInfo.dcaLevel == null) {
            orderInfo.dcaLevel = 0;
        }
        orderInfo.dcaLevel++;
        return orderInfo;
    }

//    public static boolean isDcaOrder(List<KlineObjectNumber> tickers, OrderTargetInfoTest orderInfo, int index) {
//        KlineObjectNumber ticker = tickers.get(index);
//        // rate loss > 10%
//        Double rateLoss = Utils.rateOf2Double(ticker.priceClose, orderInfo.priceEntry);
//        if (rateLoss < -0.08) {
//            // ticker reverse
//            if (index > 1) {
//                KlineObjectNumber lastTicker = tickers.get(index - 1);
//                KlineObjectNumber ticker4h = TickerFuturesHelper.extractKlineByNumberTicker(tickers, index, 32);
//                if (ticker.priceClose > ticker.priceOpen
//                        && ticker.priceClose > lastTicker.priceOpen
//                        && lastTicker.priceClose < lastTicker.priceOpen
//                        && ticker4h != null
//                        && (ticker.minPrice <= ticker4h.minPrice * 1.004
//                        || lastTicker.minPrice <= ticker4h.minPrice * 1.004)
//                ) return true;
//                return Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < -0.03;
//            }
//        }
//
//
//        return false;
//    }

    public static boolean isDcaOrderBuy(List<KlineObjectNumber> tickers, OrderTargetInfoTest order, int index) {
        if (order != null) {
            return isDcaOrderBuyWithEntry(tickers, order.priceEntry, index);
        }
        return false;
    }

    private static boolean isDcaOrderBuyWithEntry(List<KlineObjectNumber> tickers, Double priceEntry, int index) {

        KlineObjectNumber ticker = tickers.get(index);
//        if (Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < -0.1) {
//            return true;
//        }
        // rate loss > 10%
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


    public static void startCheckAndProcessDca(ConcurrentHashMap<String, List<KlineObjectNumber>> symbol2Tickers) {
        try {
            List<PositionRisk> positions = BinanceFuturesClientSingleton.getInstance().getAllPositionInfos();
            for (PositionRisk position : positions) {
                try {
                    if (position.getPositionAmt().doubleValue() > 0) {
                        String marketLevel = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_SYMBOL_POS_MARKET_LEVEL,
                                position.getSymbol());
                        // for alt reverse extend
                        if (
                                StringUtils.equals(marketLevel, MarketLevelChange.ALT_BIG_CHANGE_REVERSE_EXTEND.toString())
                        ) {
                            List<KlineObjectNumber> tickers = symbol2Tickers.get(position.getSymbol());
                            // check budget
                            Double budget = BudgetManager.getInstance().getBudget() * 4;
                            double margin = position.getPositionAmt().doubleValue() * position.getEntryPrice().doubleValue();
                            if (margin <= budget) {
                                if (isDcaOrderBuyWithEntry(tickers, position.getEntryPrice().doubleValue(), tickers.size() - 1)) {
                                    BinanceOrderTradingManager.dcaForPosition(position);
                                }
                            }
                        }
                        // for sell order
                        if (
                                StringUtils.equals(marketLevel, MarketLevelChange.ALT_SIGNAL_SELL.toString())
                        ) {
                            List<KlineObjectNumber> tickers = symbol2Tickers.get(position.getSymbol());
                            // check budget
                            Double budget = BudgetManager.getInstance().getBudget();
                            double margin = position.getPositionAmt().doubleValue() * position.getEntryPrice().doubleValue();
                            Double rateLoss = Utils.rateOf2Double(tickers.get(tickers.size() - 1).priceClose, position.getEntryPrice().doubleValue());
                            if (margin <= budget || rateLoss > 0.4) {
                                if (isDcaOrderSellWithEntry(tickers, position.getEntryPrice().doubleValue(), tickers.size() - 1)
                                        || rateLoss > 0.4) {
                                    BinanceOrderTradingManager.dcaForPosition(position);
                                }
                            }
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
