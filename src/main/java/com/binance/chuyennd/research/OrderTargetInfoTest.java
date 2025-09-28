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

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.tradecore.TradeUtils;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.market.FundingRate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.Serializable;
import java.math.BigDecimal;
import java.util.Date;
import java.util.TreeMap;

/**
 * @author pc
 */
public class OrderTargetInfoTest implements Serializable {
    public static final Logger LOG = LoggerFactory.getLogger(OrderTargetInfoTest.class);
    private static final long serialVersionUID = 6529685098267757691L;

    public OrderTargetStatus status;
    public OrderSide side;
    public Double priceEntry;
    public Double lastEntry;

    public Double priceTP;
    public Double priceSL;
    public Double quantity;
    public Integer leverage;
    public String symbol;
    public long timeStart;
    public long timeUpdate;
    public Double profitMin = 0d;

    public Double maxPrice;
    public Double minPrice;
    public Double lastPrice;

    public Double rateChange;
    public Double volume;
    public TreeMap<Long, Double> time2FundingFee = new TreeMap<>();
    public MarketRateChange marketData;
    public MarketLevelChange marketLevelChange;
    public KlineObjectNumber tickerOpen;


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


    public void updatePriceByKlineSimple(KlineObjectSimple ticker) {
        this.lastPrice = ticker.priceClose;
        if (this.maxPrice < ticker.maxPrice) {
            this.maxPrice = ticker.maxPrice;
        }
        if (this.minPrice > ticker.minPrice) {
            this.minPrice = ticker.minPrice;
            profitMin = quantity * (minPrice - priceEntry);
        }
        this.timeUpdate = ticker.startTime.longValue();
    }

    public Double calRateLoss() {
        double rate = Utils.rateOf2Double(lastPrice, priceEntry);
        return rate;
    }

    public Double calRateLossMax(Double maxPriceTicker) {
        double rate = Utils.rateOf2Double(maxPriceTicker, priceEntry);
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
        return rate;
    }

    public Double calProfit() {
        double profit = quantity * (lastPrice - priceEntry);
        return profit;
    }

    public Double calMargin() {
        return quantity * priceEntry / leverage;
    }

    public void updateStatusNew(Double maxChange60M, KlineObjectSimple ticker) {
        if (priceSL == null) {
            Double rateLoss = calRateLossMax(ticker.maxPrice);
            Double rateMin2MoveSl = TradeUtils.calRateMinWithMaxChange60MForTradingStop(maxChange60M);
            Double rateStop = TradeUtils.calRateLossDynamicBuy(rateLoss);
            Double priceSLNew = Utils.calPriceTarget(symbol, priceEntry, OrderSide.SELL, -rateStop);
            if (rateLoss > rateMin2MoveSl) {
                minPrice = lastPrice;
                this.priceSL = priceSLNew;
                if (maxPrice > ticker.maxPrice) {
                    LOG.info("Update when max < entry: {} {} {} {} {} {} {} {}", symbol, maxPrice,
                            priceEntry, ticker.maxPrice, Utils.formatPercent(maxChange60M),
                            rateMin2MoveSl, priceSLNew, ticker.priceClose);
                }
                if (ticker.priceClose <= priceSLNew) {
                    LOG.info("SL over last price: {} {} {} {} {} {} {} {} {}", symbol, maxPrice,
                            priceEntry, ticker.maxPrice, Utils.formatPercent(maxChange60M),
                            rateMin2MoveSl, priceSLNew, ticker.priceClose);
                }
                if (lastPrice <= priceSLNew) {
                    LOG.info("Close now lastPrice under pSL: {} {} {} {} {} {} {} {} {}", symbol,
                            Utils.sdfGoogle.format(new Date(timeStart)), maxPrice,
                            priceEntry, ticker.maxPrice, Utils.formatPercent(maxChange60M),
                            rateMin2MoveSl, priceSLNew, ticker.priceClose);
                    status = OrderTargetStatus.TAKE_PROFIT_DONE;
                    priceTP = priceSL;
                }
            }
        } else {
            if (minPrice <= priceSL) {
                if (priceSL > priceEntry) {
                    status = OrderTargetStatus.STOP_MARKET_DONE;
                } else {
                    status = OrderTargetStatus.STOP_LOSS_DONE;
                }
                priceTP = priceSL;
            }
        }
    }


    public void updateTPSL(Double rateChangeMax60M, KlineObjectSimple ticker) {
        // move SL
        if (priceSL != null) {
            Double rateLoss = calRateLossMax(ticker.maxPrice);
            Double rateMin2MoveSl = TradeUtils.calRateMinWithMaxChange60MForTradingStop(rateChangeMax60M* 1.5);
            Double rateSL = TradeUtils.calRateLossDynamicBuy(rateLoss);
            OrderSide side2Sl = OrderSide.SELL;
            Double priceSLNew = Utils.calPriceTarget(symbol, priceEntry, side2Sl, -rateSL);
            double priceSLChange = priceSLNew - priceSL;
            if (priceSLChange > 0
                    && rateLoss >= rateMin2MoveSl
                    && priceSLNew > priceEntry
            ) {
                priceSL = priceSLNew;
                minPrice = lastPrice;
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

    public void updateFundingFee() {
        TreeMap<Long, FundingRate> fundingFee = FundingFeeManager.getInstance().getFundingFeeByTime(symbol, timeStart, timeUpdate);
        if (fundingFee != null) {
            for (Long time : fundingFee.keySet()) {
                FundingRate fund = fundingFee.get(time);
                BigDecimal markPrice = fund.getMarkPrice();
                BigDecimal fundingRate = fund.getFundingRate();
                if (markPrice.equals(new BigDecimal("0"))) {
                    markPrice = markPrice.add(new BigDecimal(lastPrice));
                }
                BigDecimal funding = fundingRate.multiply(new BigDecimal(quantity));
                funding = funding.multiply(markPrice);
                if (side.equals(OrderSide.SELL)) {
                    time2FundingFee.put(time, -funding.doubleValue());
                } else {
                    time2FundingFee.put(time, funding.doubleValue());
                }
            }
        }
    }
}
