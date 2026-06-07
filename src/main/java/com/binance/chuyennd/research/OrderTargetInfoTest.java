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

import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.TradeUtils;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;

import java.io.Serializable;
import java.util.TreeMap;

/**
 * @author pc
 */
public class OrderTargetInfoTest implements Serializable {
    private static final long serialVersionUID = 6529685098267757691L;

    public OrderTargetStatus status;
    public OrderSide side;
    public Float priceEntry;
    public Float lastEntry;

    public Float priceTP;
    public Float priceSL;
    public Float quantity;
    public Integer leverage;
    public String symbol;
    public short symbolId;   // Dùng cho Simulator tốc độ cao
    public long timeStart;
    public long timeUpdate;
    public Float profitMin = 0f;

    //    public Float maxPrice;
    public Float minPrice;
    // 🔎 ĐO LƯỜNG ONLY: đáy THẬT của cụm kể từ leg đầu — chỉ đi XUỐNG, KHÔNG bao giờ reset-lên như
    //    minPrice (minPrice là tham chiếu trailing-stop, bị reset lên ở updateStatusNew/updateTPSL/mergeOrder).
    //    maeLow CHỈ phục vụ tính MAE trong report; TUYỆT ĐỐI không tham gia quyết định vào/ra lệnh/SL.
    public Float maeLow;
    public Float lastPrice;

    public Float rateChange;
    public Float volume;
    public TreeMap<Long, Float> time2FundingFee = new TreeMap<>();
    public MarketDataObject marketData;
    public MarketLevelChange marketLevelChange;
    public KlineObjectSimple tickerOpen;
    public AiPredictionData predict;
    public Float symbolPred;


    public OrderTargetInfoTest(OrderTargetStatus status, Float priceEntry,
                               Float priceTP, Float quantity, Integer leverage, String symbol,
                               long timeStart, long timeUpdate, OrderSide side) {
        this.status = status;
        this.priceEntry = priceEntry;
        this.priceTP = priceTP;
        this.quantity = quantity;
        this.leverage = leverage;
        this.symbol = symbol;
        if (symbol != null) {
            this.symbolId = SimpleSymbolMapper.getInstance().getId(symbol);
        }
        this.timeStart = timeStart;
        this.timeUpdate = timeUpdate;
        this.side = side;

    }


    public void updatePriceByKlineSimple(KlineObjectSimple ticker) {
        this.lastPrice = ticker.priceClose;
        if (this.minPrice > ticker.minPrice) {
            this.minPrice = ticker.minPrice;
            profitMin = quantity * (minPrice - priceEntry);
        }
        // 🔎 maeLow: bám đáy nến, CHỈ đi xuống. Cố ý KHÔNG reset ở updateStatusNew/updateTPSL/mergeOrder
        //    (khác hẳn minPrice) để giữ đáy THẬT từ leg đầu — phục vụ MAE chuẩn. Không đụng giao dịch.
        if (this.maeLow == null || this.maeLow > ticker.minPrice) {
            this.maeLow = ticker.minPrice;
        }
        this.timeUpdate = ticker.startTime.longValue();
    }

    public Float calRateLoss() {
        float rate = Utils.rateOf2Double(lastPrice, priceEntry);
        return rate;
    }

    public Float calRateLossMax(Float maxPriceTicker) {
        float rate = Utils.rateOf2Double(maxPriceTicker, priceEntry);
        return rate;
    }


    public Float calFundingFee() {
        float fundingTotal = 0;
        for (Float funding : time2FundingFee.values()) {
            fundingTotal += funding;
        }
        return fundingTotal;
    }


    public Float calRateTp() {
        float rate = Utils.rateOf2Double(priceTP, priceEntry);
        return rate;
    }

    public Float calProfit() {
        float profit = quantity * (lastPrice - priceEntry);
        return profit;
    }

    public Float calMargin() {
        return quantity * priceEntry / leverage;
    }

    public void updateStatusNew(Float predReturn15M, KlineObjectSimple ticker) {
        if (priceSL == null) {
            Float rateLoss = calRateLossMax(ticker.maxPrice);
            Float rateMin2MoveSl = TradeUtils.calRateMinWithPredReturn15MForTradingStop(predReturn15M);
            if (rateLoss > rateMin2MoveSl) {
                Float rateStop = TradeUtils.calRateLossDynamicBuy(rateLoss, predReturn15M);
                Float priceSLNew = Utils.calPriceTarget(symbol, priceEntry, OrderSide.SELL, -rateStop);
                minPrice = lastPrice;
                this.priceSL = priceSLNew;

                if (Configs.BLOCK_INTRABAR_LOOKAHEAD) {
                    // BỊT: chỉ vừa đặt SL trong nến này. Không khớp ngay.
                    // Nến SAU nếu minPrice <= priceSL sẽ khớp qua nhánh else bên dưới.
                    // (Nếu giá đã nằm dưới SL ngay lúc đặt thì để nến kế xử lý — bảo thủ.)
                    return;
                }

                // HÀNH VI CŨ (look-ahead) — chỉ chạy khi tắt guard để đo đối chứng.
                if (lastPrice <= priceSLNew) {
                    status = OrderTargetStatus.TAKE_PROFIT_DONE;
                    priceTP = Math.min(priceSL, ticker.maxPrice);   // kẹp ≤ high (đồng bộ booking fix; nhánh này bất hoạt khi guard bật)
                }
            }
        } else {
            // Nhánh này KHÔNG look-ahead: SL đã tồn tại từ nến trước, nến này chạm đáy thì khớp.
            if (minPrice <= priceSL) {
                if (priceSL > priceEntry) {
                    status = OrderTargetStatus.STOP_MARKET_DONE;
                } else {
                    status = OrderTargetStatus.STOP_LOSS_DONE;
                }
                // 🔴 BOOKING FIX (KHÔNG đụng trigger minPrice<=priceSL): kẹp giá chốt ≤ high nến khớp.
                //    priceSL là level set ở nến TRƯỚC; khi nến trigger GAP thủng xuống (high<priceSL) thì
                //    KHÔNG thể bán được priceSL — long-only => sell fill ≤ ticker.maxPrice. Ca thường
                //    (low≤priceSL≤high) min=priceSL nên KHÔNG đổi; chỉ ca gap mới bị kẹp (sửa PnL thổi).
                priceTP = Math.min(priceSL, ticker.maxPrice);
            }
        }
    }


    public void updateTPSL(Float rateChangeMax90M, KlineObjectSimple ticker) {
        // move SL
        if (priceSL != null) {
            Float rateLoss = calRateLossMax(ticker.maxPrice);
            Float rateMin2MoveSl = Configs.TS_PROFIT_MULTIPLIER * TradeUtils.calRateMinWithPredReturn15MForTradingStop(rateChangeMax90M);
            if (rateLoss >= rateMin2MoveSl) {
                Float rateSL = TradeUtils.calRateLossDynamicBuy(rateLoss, rateChangeMax90M);
                OrderSide side2Sl = OrderSide.SELL;
                Float priceSLNew = Utils.calPriceTarget(symbol, priceEntry, side2Sl, -rateSL);
                float priceSLChange = priceSLNew - priceSL;
                if (priceSLChange > 0
                        && priceSLNew > priceEntry
                ) {
                    priceSL = priceSLNew;
                    minPrice = lastPrice;
                }
            }
        }
    }


    public Float calTp() {
        OrderTargetInfoTest orderInfo = this;
        if (orderInfo.priceTP == null) {
            return 0f;
        }
        Float tp = orderInfo.quantity * (orderInfo.priceTP - orderInfo.priceEntry)
                - orderInfo.quantity * orderInfo.priceEntry * Configs.RATE_FEE;
        if (orderInfo.side.equals(OrderSide.SELL)) {
            tp = orderInfo.quantity * (orderInfo.priceEntry - orderInfo.priceTP)
                    - orderInfo.quantity * orderInfo.priceEntry * Configs.RATE_FEE;
        }

        // 🔥 SLIPPAGE 2 chân
        if (Configs.APPLY_SLIPPAGE) {
            float slip = orderInfo.quantity * orderInfo.priceEntry * Configs.SLIPPAGE_RATE * 2f;
            tp = tp - slip;
        }

        tp = tp - calFundingFee();
        return tp;
    }

    public void updateFundingFee() {
//        TreeMap<Long, Float> fundingFee = FundingFeeManager.getInstance().getFundingFeeByTime(symbol, timeStart, timeUpdate);
//        if (fundingFee != null) {
//            for (Long time : fundingFee.keySet()) {
//                FundingRate fund = fundingFee.get(time);
//                BigDecimal markPrice = fund.getMarkPrice();
//                BigDecimal fundingRate = fund.getFundingRate();
//                if (markPrice.equals(new BigDecimal("0"))) {
//                    markPrice = markPrice.add(new BigDecimal(lastPrice));
//                }
//                BigDecimal funding = fundingRate.multiply(new BigDecimal(quantity));
//                funding = funding.multiply(markPrice);
//                if (side.equals(OrderSide.SELL)) {
//                    time2FundingFee.put(time, -funding.doubleValue());
//                } else {
//                    time2FundingFee.put(time, funding.doubleValue());
//                }
//            }
//        }
    }
}
