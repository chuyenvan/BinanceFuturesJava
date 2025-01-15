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
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.Serializable;
import java.util.TreeMap;

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
    public Double avgVolume24h;
    public Double volume;
    public Integer ordersRunning;
    public Double unProfitTotal;
    public Double slTotal;
    public Double marginRunning;
    public Double marginRealRunning;
    public TreeMap<Long, Double> time2FundingFee = new TreeMap<>();
    public MarketDataObject marketData;
    public MarketLevelChange marketLevelChange;
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

    public void updateStatusFixTPSL() {
        if (timeUpdate - timeStart >= 12 * Utils.TIME_HOUR) {
            status = OrderTargetStatus.STOP_LOSS_DONE;
            priceTP = lastPrice;
            return;
        }
        if (priceTP != null && maxPrice > priceTP && minPrice < priceTP) {
            status = OrderTargetStatus.TAKE_PROFIT_DONE;
        }

    }

    public void updateStatus() {
    }


    public Double calRateLoss() {
        double rate = Utils.rateOf2Double(lastPrice, priceEntry);
        if (side.equals(OrderSide.SELL)) {
            rate = -rate;
        }
        return rate;
    }

    public Double calCurrentRateSL() {
        double rate = Utils.rateOf2Double(lastPrice, priceSL);
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

    public Double calFundingFee() {
        double fundingTotal = 0;
        for (Double funding : time2FundingFee.values()) {
            fundingTotal += funding;
        }
        return fundingTotal;
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
        Double priceLoss = priceSL;
        if (priceSL == null) {
            priceLoss = minPrice;
        }
        double profit = quantity * (priceLoss - priceEntry);
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

    public void updateStatusNew(Double rateMin) {
        Double rateLoss = calRateLoss();
        Double rateMin2MoveSl = Configs.RATE_PROFIT_STOP_MARKET;
        if (Constants.specialSymbol.contains(symbol)
                || Constants.stableSymbol.contains(symbol)
        ) {
            rateMin2MoveSl = 0.01;
        }
        // for buy
        if (side.equals(OrderSide.BUY)) {
            Double rateStop = BudgetManagerSimple.getInstance().calRateLossDynamic(rateLoss, symbol, rateMin2MoveSl);
            Double priceSLNew = Utils.calPriceTarget(symbol, priceEntry, OrderSide.SELL, -rateStop);
            if (timeUpdate - timeStart >= Configs.TIME_AFTER_ORDER_2_SL * Utils.TIME_MINUTE
                    || rateLoss > rateMin2MoveSl) {
                if (priceSL == null) {
                    if (priceSLNew <= priceEntry && rateLoss > 0) {
                        Double rateStopLoss = Configs.RATE_STOP_LOSS_ALT;
                        if (Constants.specialSymbol.contains(symbol) || Constants.stableSymbol.contains(symbol)) {
                            rateStopLoss = Configs.RATE_STOP_LOSS_SPECIAL;
                        }
                        priceSLNew = Utils.calPriceTarget(symbol, priceEntry, OrderSide.SELL, rateStopLoss);
                    }
                    minPrice = lastPrice;
//                    LOG.info("Create price SL:{} {} {} {} {} {} -> {} {}%", symbol, marketLevelChange, Utils.normalizeDateYYYYMMDDHHmm(timeStart),
//                            Utils.normalizeDateYYYYMMDDHHmm(timeUpdate), lastPrice, priceSL, priceSLNew,
//                            Utils.formatPercent(Utils.rateOf2Double(priceSLNew, priceEntry)));
                    this.priceSL = priceSLNew;
                }
            }
            if (priceSL != null && minPrice <= priceSL) {
                if (priceSL > priceEntry) {
                    status = OrderTargetStatus.STOP_MARKET_DONE;
                } else {
                    status = OrderTargetStatus.STOP_LOSS_DONE;
                }
                priceTP = priceSL;
            }
        }
    }

    public void updateTPSL(Double rateMin) {
        Double rateLoss = calRateLoss();
        // for BUY
        if (side.equals(OrderSide.BUY)) {
            // move SL
            if (priceSL != null) {
                Double rateMin2MoveSl = Configs.RATE_PROFIT_STOP_MARKET;
                if (Constants.specialSymbol.contains(symbol)
                        || Constants.stableSymbol.contains(symbol)
                ) {
                    rateMin2MoveSl = 0.01;
                }

                Double rateSL = BudgetManagerSimple.getInstance().calRateLossDynamic(rateLoss, symbol, rateMin2MoveSl);
                OrderSide side2Sl = OrderSide.SELL;
                Double priceSLNew = Utils.calPriceTarget(symbol, priceEntry, side2Sl, -rateSL);
                double priceSLChange = priceSLNew - priceSL;
                if (priceSLChange > 0
                        && rateLoss >= rateMin2MoveSl
                        && priceSLNew > priceEntry
                ) {
//                    String prefix = "Move SL market";
//                    if (rateLoss < 0) {
//                        prefix = "Move SL";
//                    }
//                    LOG.info("{}:{} {} {} {} {} {} -> {} {} {}%", prefix, symbol, marketLevelChange,
//                            Utils.normalizeDateYYYYMMDDHHmm(timeStart),
//                            Utils.normalizeDateYYYYMMDDHHmm(timeUpdate), lastPrice, priceSL,
//                            priceSLNew, Utils.formatPercent(rateLoss),
//                            Utils.formatPercent(Utils.rateOf2Double(priceSLNew, priceEntry)));
                    priceSL = priceSLNew;
                    minPrice = lastPrice;
                }
            }
        }
    }


    public Double calTp() {
        OrderTargetInfoTest orderInfo = this;
        Double tp = orderInfo.quantity * (orderInfo.priceTP - orderInfo.priceEntry)
                - orderInfo.quantity * orderInfo.priceEntry * Configs.RATE_FEE;
        if (orderInfo.side.equals(OrderSide.SELL)) {
            tp = orderInfo.quantity * (orderInfo.priceEntry - orderInfo.priceTP)
                    - orderInfo.quantity * orderInfo.priceEntry * Configs.RATE_FEE;
        }
        return tp;
    }

    public void updateFundingFee(Long time) {
        try {
            if (time == Utils.sdfFileHour.parse("20241210 11:00").getTime()) {
                System.out.println("Debug");
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        Double fundingRate = FundingFeeManager.getInstance().getFundingFee(symbol, time);
        if (fundingRate != null) {
            time2FundingFee.put(time, quantity * lastPrice * fundingRate);
        }
    }
}
