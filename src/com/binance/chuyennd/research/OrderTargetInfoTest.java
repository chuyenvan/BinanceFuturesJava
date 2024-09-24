/*
 * Copyright 2024 pc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.Serializable;

/**
 * @author pc
 */
public class OrderTargetInfoTest implements Serializable {
    public static final Logger LOG = LoggerFactory.getLogger(OrderTargetInfoTest.class);

    public OrderTargetStatus status;
    public OrderSide side;
    public Double priceEntry;
    public Double priceTP;
    public Double priceSL;
    public Double quantity;
    public Integer leverage;
    public String symbol;
    public long timeStart;
    public long timeUpdate;

    public Double maxPrice;
    public Double minPrice;
    public Double lastPrice;
    public Double rateBreadAbove;
    public Double rateBreadBelow;
    public Double rateChange;
    public Double volume;
    public Double avgVolume24h;
    public Double rateBtc15m;
    public Double rateChange15MAvg;
    public MarketDataObject marketData;
    public MarketLevelChange marketLevelChange;
    public String lastMarketLevelChange;
    public Integer dynamicTP_SL;
    public KlineObjectNumber tickerOpen;
    public KlineObjectNumber tickerClose;


    public OrderTargetInfoTest(OrderTargetStatus status, Double priceEntry,
                               Double priceTP, Double quantity, Integer leverage, String symbol,
                               long timeStart, long timeUpdate, OrderSide side) {
        this.status = status;
        this.priceEntry = priceEntry;
        this.priceTP = priceTP;
        this.quantity = quantity;
        this.leverage = leverage;
        this.symbol = symbol;
        this.timeStart = timeStart;
        this.timeUpdate = timeUpdate;
        this.side = side;

    }

    public OrderTargetInfoTest(OrderTargetStatus status, Double priceEntry,
                               Double priceTP, Double quantity, Integer leverage, String symbol,
                               long timeStart, long timeUpdate, OrderSide side, String tradingType) {
        this.status = status;
        this.priceEntry = priceEntry;
        this.priceTP = priceTP;
        this.quantity = quantity;
        this.leverage = leverage;
        this.symbol = symbol;
        this.timeStart = timeStart;
        this.timeUpdate = timeUpdate;
        this.side = side;

    }

    public OrderTargetInfoTest() {

    }

    public void updatePriceByKline(KlineObjectNumber ticker) {
        this.lastPrice = ticker.priceClose;
        if (this.maxPrice < ticker.maxPrice) {
            this.maxPrice = ticker.maxPrice;
        }
        if (this.minPrice > ticker.minPrice) {
            this.minPrice = ticker.minPrice;
        }
        this.timeUpdate = ticker.endTime.longValue();
    }

    public void updatePriceByKlineSimple(KlineObjectSimple ticker) {
        this.lastPrice = ticker.priceClose;
        if (this.maxPrice < ticker.maxPrice) {
            this.maxPrice = ticker.maxPrice;
        }
        if (this.minPrice > ticker.minPrice) {
            this.minPrice = ticker.minPrice;
        }
        this.timeUpdate = ticker.startTime.longValue();
    }

    public void updatePriceByLastPrice(Double lastPrice) {
        this.lastPrice = lastPrice;
        if (this.maxPrice < lastPrice) {
            this.maxPrice = lastPrice;
        }
        if (this.minPrice > lastPrice) {
            this.minPrice = lastPrice;
        }
    }

    public void updateStatusSpecial() {
        // stop loss by time
        if (timeUpdate - timeStart > Utils.TIME_MINUTE) {
            if (timeUpdate - timeStart >= 4 * Utils.TIME_HOUR) {
                status = OrderTargetStatus.STOP_LOSS_DONE;
                priceTP = lastPrice;
                return;
            }
            if (priceSL != null && maxPrice >= priceSL && minPrice <= priceSL) {
                status = OrderTargetStatus.STOP_LOSS_DONE;
                priceTP = priceSL;
            } else {
                if (priceTP != null && maxPrice > priceTP && minPrice < priceTP) {
                    status = OrderTargetStatus.TAKE_PROFIT_DONE;
                }
            }
        } else {
//            if (priceTP != null && maxPrice > priceTP && minPrice < priceTP) {
//                status = OrderTargetStatus.TAKE_PROFIT_DONE;
//                return;
//            }
            maxPrice = lastPrice;
            minPrice = lastPrice;
            if (lastPrice > priceTP) {
                Double rateLoss = calRateLoss();
                Double rateTp = rateLoss + Configs.RATE_TRADING_DYNAMIC / 100;
                Double priceTPNew = Utils.calPriceTarget(symbol, priceEntry, OrderSide.BUY, rateTp);
                LOG.info("Renew price TP:{} {} {} {} -> {} {}%", symbol, Utils.normalizeDateYYYYMMDDHHmm(timeStart)
                        , Utils.normalizeDateYYYYMMDDHHmm(timeStart), priceTP, priceTPNew, Utils.formatPercent(rateTp));
                priceTP = priceTPNew;
//                Double rateSL = rateLoss - Configs.RATE_TRADING_DYNAMIC / 100;
//                Double priceSLNew = Utils.calPriceTarget(symbol, priceEntry, OrderSide.SELL, -rateSL);
//                LOG.info("Set price SL:{} {} {} {} -> {} {}%", symbol, Utils.normalizeDateYYYYMMDDHHmm(timeStart),
//                        Utils.normalizeDateYYYYMMDDHHmm(timeUpdate), priceSL, priceSLNew, rateSL);
//                priceSL = priceSLNew;
            }

        }
    }

    public void updateStatusFixTPSL() {
//        if (timeUpdate - timeStart > Utils.TIME_MINUTE) {
//        if (priceSL != null && maxPrice >= priceSL && minPrice <= priceSL) {
//            status = OrderTargetStatus.STOP_LOSS_DONE;
//            priceTP = priceSL;
//            return;
//        }
        if (timeUpdate - timeStart >= 12 * Utils.TIME_HOUR) {
            status = OrderTargetStatus.STOP_LOSS_DONE;
            priceTP = lastPrice;
            return;
        }
        if (priceTP != null && maxPrice > priceTP && minPrice < priceTP) {
            status = OrderTargetStatus.TAKE_PROFIT_DONE;
        }
//        } else {
//            maxPrice = lastPrice;
//            minPrice = lastPrice;
//            Double rateLoss = calRateLoss();
//            Double rateProfit = Configs.RATE_TARGET / 2;
//            Double rateSL;
//            if (rateLoss > 0) {
//                rateProfit = rateLoss + Configs.RATE_TARGET;
//                rateSL = Configs.RATE_TARGET;
//            } else {
//                rateSL = -rateLoss + 3 * Configs.RATE_TARGET;
//            }
//            priceTP = Utils.calPriceTarget(symbol, priceEntry, OrderSide.BUY, rateProfit);
//            priceSL = Utils.calPriceTarget(symbol, priceEntry, OrderSide.SELL, rateSL);
//        }
    }

    public void updateStatus() {
        Double rateLoss = calRateLoss();
        if (timeUpdate - timeStart >= Configs.TIME_AFTER_ORDER_2_SL * Utils.TIME_MINUTE) {
            if (priceSL == null) {
                maxPrice = lastPrice;
                minPrice = lastPrice;
                Double priceSLNew = Utils.calPriceTarget(symbol, priceEntry, OrderSide.SELL, -(rateLoss - Configs.RATE_STOP_LOSS));
                LOG.info("Renew price SL:{} {} {} {} {} -> {} {}%", symbol, marketLevelChange, Utils.normalizeDateYYYYMMDDHHmm(timeStart),
                        Utils.normalizeDateYYYYMMDDHHmm(timeUpdate), priceSL, priceSLNew, Utils.formatPercent(rateLoss - Configs.RATE_STOP_LOSS));
                this.priceSL = priceSLNew;
            }
            if (priceSL != null && maxPrice >= priceSL && minPrice <= priceSL) {
                if (priceSL > priceEntry) {
                    status = OrderTargetStatus.STOP_MARKET_DONE;
                } else {
                    status = OrderTargetStatus.STOP_LOSS_DONE;
                }
                priceTP = priceSL;
                return;
            }
        }
        if (timeUpdate - timeStart >= Configs.TIME_AFTER_ORDER_2_TP * Utils.TIME_MINUTE) {
            if (priceTP == null) {
                maxPrice = lastPrice;
                minPrice = lastPrice;
                Double priceTPNew = Utils.calPriceTarget(symbol, priceEntry, OrderSide.BUY, 3 * Configs.RATE_TARGET);
                if (lastPrice > priceTPNew) {
                    priceTPNew = Utils.calPriceTarget(symbol, priceEntry, OrderSide.BUY, rateLoss + 3 * Configs.RATE_TARGET);
                    LOG.info("Renew price TP:{} {} {} {} {} -> {} {}%", symbol, marketLevelChange, Utils.normalizeDateYYYYMMDDHHmm(timeStart)
                            , Utils.normalizeDateYYYYMMDDHHmm(timeStart), priceTP, priceTPNew, Utils.formatPercent(rateLoss + 3 * Configs.RATE_TARGET));
                }
                priceTP = priceTPNew;
            }
            if (priceTP != null && maxPrice > priceTP && minPrice < priceTP) {
                status = OrderTargetStatus.TAKE_PROFIT_DONE;
            }
        }
    }

    public void updateStatusNew(KlineObjectSimple ticker) {
        Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
        Double rateLoss = calRateLoss();
        Double rateStopLoss = Configs.RATE_STOP_LOSS;
        // TODO check lại rate stop loss cho 3 cặp
        if (marketLevelChange != null
                && (marketLevelChange.equals(MarketLevelChange.BTC_REVERSE)
//                || marketLevelChange.equals(MarketLevelChange.SMALL_UP_15M)
//                || marketLevelChange.equals(MarketLevelChange.BIG_UP_15M)
        )) {
            rateStopLoss = 3 * Configs.RATE_STOP_LOSS;
        }
        // for buy
        if (side.equals(OrderSide.BUY)) {
            if (timeUpdate - timeStart >= Configs.TIME_AFTER_ORDER_2_SL * Utils.TIME_MINUTE
                    || (rateChange < -0.005 && priceTP != null)
                    || rateLoss > 0.05) {
                if (priceSL == null) {
                    maxPrice = lastPrice;
                    minPrice = lastPrice;
                    Double rateStop;
                    if (rateLoss > rateStopLoss * 1 / 3) {
                        if (rateLoss > rateStopLoss * 2 / 3) {
                            rateStop = rateLoss - rateStopLoss * 2 / 3;
                        } else {
                            rateStop = rateLoss - rateStopLoss * 1 / 3;
                        }
                    } else {
                        if (rateLoss < -rateStopLoss * 5 / 6) {
                            rateStop = -rateLoss + rateStopLoss;
                        } else {
                            rateStop = rateStopLoss;
                        }
                    }
                    Double priceSLNew = Utils.calPriceTarget(symbol, priceEntry, OrderSide.SELL, rateStop);
//                if (rateLoss > 0) {
//                    priceSLNew = Utils.calPriceTarget(symbol, priceEntry, OrderSide.SELL, Configs.RATE_STOP_LOSS);
//                }
                    LOG.info("Renew price SL:{} {} {} {} {} -> {} {}%", symbol, marketLevelChange, Utils.normalizeDateYYYYMMDDHHmm(timeStart),
                            Utils.normalizeDateYYYYMMDDHHmm(timeUpdate), priceSL, priceSLNew, Utils.formatPercent(rateLoss - Configs.RATE_STOP_LOSS));
                    this.priceSL = priceSLNew;
                }
                if (priceSL != null && maxPrice >= priceSL && minPrice <= priceSL) {
                    if (priceSL > priceEntry) {
                        status = OrderTargetStatus.STOP_MARKET_DONE;
                    } else {
                        status = OrderTargetStatus.STOP_LOSS_DONE;
                    }
                    priceTP = priceSL;
                    return;
                }
            }
            if (timeUpdate - timeStart >= Configs.TIME_AFTER_ORDER_2_TP * Utils.TIME_MINUTE
                    || rateChange > 0.001
                    || rateLoss > 0.03) {
                if (priceTP == null) {
                    maxPrice = lastPrice;
                    minPrice = lastPrice;
                    Double rateProfit;
                    if (rateLoss < 0.0) {
                        rateProfit = 3 * Configs.RATE_TARGET;
                    } else {
                        rateProfit = rateLoss + 3 * Configs.RATE_TARGET;
                    }
                    Double priceTPNew = Utils.calPriceTarget(symbol, priceEntry, OrderSide.BUY, rateProfit);

                    LOG.info("Create price TP:{} {} {} {} {} -> {} {}%", symbol, marketLevelChange, Utils.normalizeDateYYYYMMDDHHmm(timeStart)
                            , Utils.normalizeDateYYYYMMDDHHmm(timeStart), priceTP, priceTPNew, Utils.formatPercent(Utils.rateOf2Double(priceTPNew, priceEntry)));
                    priceTP = priceTPNew;
                }
                if (priceTP != null && maxPrice > priceTP && minPrice < priceTP) {
                    status = OrderTargetStatus.TAKE_PROFIT_DONE;
                }
            }
        } else {
            // for sell
            if (timeUpdate - timeStart >= Configs.TIME_AFTER_ORDER_2_SL * Utils.TIME_MINUTE
                    || (rateChange > 0.005 && priceTP != null)
                    || rateLoss > 0.05) {
                if (priceSL == null) {
                    maxPrice = lastPrice;
                    minPrice = lastPrice;
                    Double rateStop;

                    if (rateLoss > Configs.RATE_STOP_LOSS * 1 / 3) {
                        if (rateLoss > Configs.RATE_STOP_LOSS * 2 / 3) {
                            rateStop = rateLoss - Configs.RATE_STOP_LOSS * 2 / 3;
                        } else {
                            rateStop = rateLoss - Configs.RATE_STOP_LOSS * 1 / 3;
                        }
                    } else {
                        if (rateLoss < -Configs.RATE_STOP_LOSS * 5 / 6) {
                            rateStop = -rateLoss + Configs.RATE_STOP_LOSS;
                        } else {
                            rateStop = Configs.RATE_STOP_LOSS;
                        }
                    }
                    Double priceSLNew = Utils.calPriceTarget(symbol, priceEntry, OrderSide.BUY, rateStop);
                    LOG.info("Renew price SL:{} {} {} {} {} -> {} {}%", symbol, marketLevelChange, Utils.normalizeDateYYYYMMDDHHmm(timeStart),
                            Utils.normalizeDateYYYYMMDDHHmm(timeUpdate), priceSL, priceSLNew, Utils.formatPercent(rateLoss - Configs.RATE_STOP_LOSS));
                    this.priceSL = priceSLNew;
                }
                if (priceSL != null && maxPrice >= priceSL && minPrice <= priceSL) {
                    if (priceSL < priceEntry) {
                        status = OrderTargetStatus.STOP_MARKET_DONE;
                    } else {
                        status = OrderTargetStatus.STOP_LOSS_DONE;
                    }
                    priceTP = priceSL;
                    return;
                }
            }
            if (timeUpdate - timeStart >= Configs.TIME_AFTER_ORDER_2_TP * Utils.TIME_MINUTE
                    || rateChange < -0.005
                    || rateLoss > 0.03) {
                if (priceTP == null) {
                    maxPrice = lastPrice;
                    minPrice = lastPrice;
                    Double rateProfit;
                    if (rateLoss < 0.0) {
                        rateProfit = 3 * Configs.RATE_TARGET;
                    } else {
                        rateProfit = rateLoss + 3 * Configs.RATE_TARGET;
                    }
                    Double priceTPNew = Utils.calPriceTarget(symbol, priceEntry, OrderSide.SELL, rateProfit);

                    LOG.info("Create price TP:{} {} {} {} {} -> {} {}%", symbol, marketLevelChange, Utils.normalizeDateYYYYMMDDHHmm(timeStart)
                            , Utils.normalizeDateYYYYMMDDHHmm(timeStart), priceTP, priceTPNew, Utils.formatPercent(Utils.rateOf2Double(priceTPNew, priceEntry)));
                    priceTP = priceTPNew;
                }
                if (priceTP != null && maxPrice > priceTP && minPrice < priceTP) {
                    status = OrderTargetStatus.TAKE_PROFIT_DONE;
                }
            }
        }
    }

    public Double calRateLoss() {
        double rate = Utils.rateOf2Double(lastPrice, priceEntry);
        if (side.equals(OrderSide.SELL)) {
            rate = -rate;
        }

        return rate;
    }

    public Double calRateStopLoss() {
        double rate = Utils.rateOf2Double(priceSL, priceEntry);
        if (side.equals(OrderSide.SELL)) {
            rate = -rate;
        }
        return rate;
    }

    public Double calRateTp() {
        double rate = Utils.rateOf2Double(priceTP, priceEntry);
        if (side.equals(OrderSide.SELL)) {
            rate = -rate;
        }
        return rate;
    }

    public Double calProfit() {
        double profit = quantity * (lastPrice - priceEntry);
        if (side.equals(OrderSide.SELL)) {
            profit = -profit;
        }
        return profit;
    }

    public Double calProfitLossMax() {
        if (priceSL == null) {
            return 0d;
        }
        double profit = quantity * (priceSL - priceEntry);
        if (side.equals(OrderSide.SELL)) {
            profit = -profit;
        }
        return profit;
    }

    public Double calMargin() {
        return quantity * priceEntry / leverage;
    }

    public Double calProfitMin() {
        double profitMin = quantity * (minPrice - priceEntry);
        if (side.equals(OrderSide.SELL)) {
            profitMin = quantity * (priceEntry - maxPrice);
        }
        return profitMin;
    }

    public void updateTPSL() {
        Double rateLoss = calRateLoss();
        // for BUY
        if (side.equals(OrderSide.BUY)) {
            // move SL
            if (priceSL != null) {
                Double rateSL = BudgetManagerSimple.getInstance().calRateLossDynamic(rateLoss);
//                if (marketLevelChange != null
//                        && (marketLevelChange.equals(MarketLevelChange.BTC_REVERSE)
//                        || marketLevelChange.equals(MarketLevelChange.SMALL_UP_15M)
//                        || marketLevelChange.equals(MarketLevelChange.BIG_UP_15M)
//                )) {
//                }
                // TODO optimize profit 3% old 0.02 -> test 0.01 0 -0.01
                Double rateMin2MoveSl = 0.006;
                if (marketLevelChange != null && marketLevelChange.equals(MarketLevelChange.SMALL_UP_15M)){
                    rateMin2MoveSl = 0.03;
                }

                if (rateLoss >= rateMin2MoveSl && rateLoss < 0.029) {
                    if (rateLoss < 0.01) {
                        rateSL = 0.5;
                    } else {
                        rateSL = rateLoss * 100 / 2;
                    }
                }

                OrderSide side2Sl = OrderSide.SELL;
                if (side.equals(OrderSide.SELL)) {
                    side2Sl = OrderSide.BUY;
                }

                Double priceSLNew = Utils.calPriceTarget(symbol, priceEntry, side2Sl, -rateSL / 100);
                double priceSLChange = priceSLNew - priceSL;
                if (side.equals(OrderSide.SELL)) {
                    priceSLChange = -priceSLChange;
                }
                if ((rateLoss >= rateMin2MoveSl && priceSLChange > 0)) {
//            LOG.info("Update SL {} {} {} {}->{} {}%->{}%", Utils.normalizeDateYYYYMMDDHHmm(timeStart),
//                    Utils.normalizeDateYYYYMMDDHHmm(timeUpdate), symbol, priceSL,
//                    priceSLNew, Utils.formatPercent(rateStopLossOld / 100), Utils.formatPercent(rateSL / 100));
                    priceSL = priceSLNew;
                    minPrice = lastPrice;
                }
            }
            // move TP
            if (priceTP != null) {
                if (rateLoss >= 0) {
                    Double rateTP = BudgetManagerSimple.getInstance().calTPDynamic(rateLoss);
                    OrderSide side2TP = OrderSide.BUY;
                    if (side.equals(OrderSide.SELL)) {
                        side2TP = OrderSide.SELL;
                    }
                    Double priceTPNew = Utils.calPriceTarget(symbol, priceEntry, side2TP, rateTP / 100);
                    if (priceTPNew > priceTP) {
                        Double rateTPOld = calRateTp();
//                LOG.info("Update TP {} {} {} {}->{} {}%->{}%", Utils.normalizeDateYYYYMMDDHHmm(timeStart),
//                        Utils.normalizeDateYYYYMMDDHHmm(timeUpdate), symbol, priceTP,
//                        priceTPNew, Utils.formatPercent(rateTPOld), Utils.formatPercent(rateTP / 100));
                        priceTP = priceTPNew;
                    }
                }
            }
        } else {
            // for sell
            // move SL
            if (priceSL != null) {
                Double rateSL = BudgetManagerSimple.getInstance().calRateLossDynamic(rateLoss);
                OrderSide side2Sl = OrderSide.BUY;
                if (side.equals(OrderSide.SELL)) {
                    side2Sl = OrderSide.BUY;
                }

                Double priceSLNew = Utils.calPriceTarget(symbol, priceEntry, side2Sl, -rateSL / 100);
                double priceSLChange = priceSLNew - priceSL;
                if (side.equals(OrderSide.SELL)) {
                    priceSLChange = -priceSLChange;
                }
                if ((rateLoss >= 0.02 && priceSLChange > 0)) {
                    priceSL = priceSLNew;
                    minPrice = lastPrice;
                }
            }
            // move TP
            if (priceTP != null) {
                if (rateLoss >= 0.02) {
                    Double rateTP = BudgetManagerSimple.getInstance().calTPDynamic(rateLoss);
                    OrderSide side2TP = OrderSide.SELL;
                    if (side.equals(OrderSide.SELL)) {
                        side2TP = OrderSide.SELL;
                    }
                    Double priceTPNew = Utils.calPriceTarget(symbol, priceEntry, side2TP, rateTP / 100);
                    if (priceTPNew < priceTP) {
                        priceTP = priceTPNew;
                    }
                }
            }
        }
    }
}
