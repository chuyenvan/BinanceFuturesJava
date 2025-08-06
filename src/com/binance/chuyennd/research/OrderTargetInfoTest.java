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
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.market.FundingRate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.Serializable;
import java.math.BigDecimal;
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
    public Long timeJoin = null;
    public long timeUpdate;

    public Double maxPrice;
    public Double minPrice;
    public Double lastPrice;

    public Double rateChange;
    public Double avgVolume24h;
    public Double volume;

    public Boolean isOrderStart = false;
    public TreeMap<Long, Double> time2FundingFee = new TreeMap<>();
    public MarketRateChange marketData;
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

    public Double calRateLossMax() {
        double rate = Utils.rateOf2Double(maxPrice, priceEntry);
        if (side.equals(OrderSide.SELL)) {
            rate = -Utils.rateOf2Double(minPrice, priceEntry);
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

    public void updateStatusNew(Double maxChange15M) {
        Double rateLoss = calRateLossMax();
        Double rateMin2MoveSl = BudgetManagerSimple.getInstance().calRateMin2MoveSL(symbol, priceEntry,
                rateChange, marketLevelChange, side, timeUpdate);

        if (maxChange15M != null && maxChange15M > 0.005) {
            if (maxChange15M < 0.01) {
                if (rateMin2MoveSl < 0.015) {
                    rateMin2MoveSl = 0.015;
                }
            } else {
                if (maxChange15M < 0.015) {
                    if (rateMin2MoveSl < 0.02) {
                        rateMin2MoveSl = 0.02;
                    }
                } else {
                    if (maxChange15M < 0.025) {
                        if (rateMin2MoveSl < 0.025) {
                            rateMin2MoveSl = 0.025;
                        }
                    } else {
                        if (maxChange15M < 0.035) {
                            if (rateMin2MoveSl < 0.04) {
                                rateMin2MoveSl = 0.04;
                            }
                        } else {
                            if (rateMin2MoveSl < 0.06) {
                                rateMin2MoveSl = 0.06;
                            }
                        }
                    }
                }
            }
        }
        Double rateStop = BudgetManagerSimple.getInstance().calRateLossDynamicBuy(rateLoss, maxChange15M);
        Double priceSLNew = Utils.calPriceTarget(symbol, priceEntry, OrderSide.SELL, -rateStop);
        if (rateLoss > rateMin2MoveSl) {
            if (priceSL == null) {
                minPrice = lastPrice;
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

    public void updateTPSL(Double maxChange15M) {
        Double rateLoss = calRateLossMax();
        Double rateMin2MoveSl = BudgetManagerSimple.getInstance().calRateMin2MoveSL(symbol, priceEntry,
                rateChange, marketLevelChange, side, timeUpdate);
        if (!Constants.specialSymbol.contains(symbol)) {
            rateMin2MoveSl = 4 * rateMin2MoveSl;
        }
        Double rateSL = BudgetManagerSimple.getInstance().calRateLossDynamicBuy(rateLoss, maxChange15M);
        // move SL
        if (priceSL != null) {
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

    public Double calLossMax() {
        OrderTargetInfoTest orderInfo = this;
        Double tp = orderInfo.quantity * (orderInfo.minPrice - orderInfo.priceEntry)
                - orderInfo.quantity * orderInfo.priceEntry * Configs.RATE_FEE;
        if (orderInfo.side.equals(OrderSide.SELL)) {
            tp = orderInfo.quantity * (orderInfo.priceEntry - orderInfo.maxPrice)
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
