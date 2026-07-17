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
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.Serializable;
import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * @author pc
 */
public class OrderTargetInfoTest implements Serializable {
    private static final long serialVersionUID = 6529685098267757691L;
    private static final Logger LOG = LoggerFactory.getLogger(OrderTargetInfoTest.class);
    /** Đếm tổng lệnh bị clamp về bar.open do gap trong phiên JVM — đọc từ bên ngoài để báo cáo. */
    public static final AtomicLong CLAMP_TOTAL = new AtomicLong(0);

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
    // 🔎 ĐO LƯỜNG ONLY (TASK-151): đỉnh giá THẬT đạt được kể từ leg đầu — chỉ đi LÊN, không tham gia
    //    quyết định SL/TP (đối xứng với maeLow). Phục vụ đo "% đỉnh giữ được" khi đóng lệnh thắng.
    public Float maePeak;
    public Float lastPrice;

    public Float rateChange;
    public Float volume;
    // === FUNDING (Bước 3, code lại 2026-06-28 — tính 1 LƯỢT khi đóng lệnh) ===
    // Tổng phí funding của cụm, tính DUY NHẤT 1 lần ở closeOrder (KHÔNG streaming mỗi tick → rẻ cho WFO/HPO).
    // calFundingFee() đọc field này. Giữ tên cũ time2FundingFee cho TraceOrderDone/BudgetManagerSimple tương thích,
    // nhưng giờ chỉ chứa TỐI ĐA 1 entry (tổng) thay vì mỗi settlement.
    public TreeMap<Long, Float> time2FundingFee = new TreeMap<>();
    // clusterFirstLegTime: thời điểm leg ĐẦU của cụm — chỉ để computeFundingOnClose quét đủ vòng đời funding.
    // TÁCH RIÊNG khỏi timeStart (timeStart = leg-cuối, là tham chiếu logic mở/đóng — TUYỆT ĐỐI không đụng,
    // nếu không funding sẽ rò vào logic giao dịch → đổi số lệnh → vỡ GATE). transient: không serialize.
    public transient long clusterFirstLegTime = 0L;
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
        if (this.maePeak == null || this.maePeak < ticker.maxPrice) {
            this.maePeak = ticker.maxPrice;
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
            // TASK (2026-07-09): SL cung cho lenh CHUA tung cham nguong lai de arm trailing ("nuoi lo").
            // Chi active khi Configs.HARD_STOP_LOSS_RATE > 0 (mac dinh 0 = tat, hanh vi cu y nguyen).
            // CHON LOC theo level: test A/B blanket (moi level) cho thay net AM - DCA_LEVEL1 mat loi nhuan
            // vi bi cat som luc dang lo tam thoi (se hoi). Chi ap dung cho PREDICT_SYMBOL_TRADE (dung
            // level dang lo bat thuong: rate% duong nhung $ am - xem TraceData2Test 2025).
            if (Configs.HARD_STOP_LOSS_RATE > 0f
                    && marketLevelChange == com.binance.chuyennd.object.MarketLevelChange.PREDICT_SYMBOL_TRADE) {
                Float rateLossNow = calRateLoss(); // (lastPrice - priceEntry) / priceEntry, am neu dang lo
                if (rateLossNow != null && rateLossNow <= -Configs.HARD_STOP_LOSS_RATE) {
                    status = OrderTargetStatus.STOP_LOSS_DONE;
                    priceTP = Math.min(ticker.priceOpen, lastPrice); // haircut nhu nhanh gap-down ben duoi, khong look-ahead them
                    return;
                }
            }
            // TASK (2026-07-10): time-stop thesis-expiry — lenh CHUA arm trailing qua TIME_STOP_HOURS
            // (do tu leg DAU cum, khong bi DCA reset) thi thoat. 0 = tat.
            if (Configs.TIME_STOP_HOURS > 0) {
                long anchor = clusterFirstLegTime > 0L ? clusterFirstLegTime : timeStart;
                if (ticker.startTime.longValue() - anchor > Configs.TIME_STOP_HOURS * 3600000L) {
                    status = OrderTargetStatus.STOP_LOSS_DONE;
                    priceTP = Math.min(ticker.priceOpen, lastPrice);
                    return;
                }
            }
            // TASK (2026-07-17): TRAIL_PEAK_MODE — dinh de ARM trailing. high=maxPrice (mac dinh, hanh vi cu),
            // close=priceClose (chong wick). Chi doi peak arm/ratchet, KHONG dung minPrice/MAE/disaster/time-stop.
            float trailPeak = "close".equals(Configs.TRAIL_PEAK_MODE) ? ticker.priceClose : ticker.maxPrice;
            Float rateLoss = calRateLossMax(trailPeak);
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
                    priceTP = Math.min(priceSL, ticker.priceOpen);  // TASK-118: clamp → bar.open (đồng bộ nhánh chính; bất hoạt khi guard bật)
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
                // 🔴 BOOKING FIX (TASK-118): clamp giá chốt về min(priceSL, bar.open).
                //    Ca thường (open≥priceSL): priceTP=priceSL (fill đúng stop, không đổi).
                //    Ca gap-down (open<priceSL): priceTP=open (haircut thực — không thể bán trên open).
                //    Cũ: min(priceSL, ticker.maxPrice) — maxPrice trong nến có thể cao hơn open nội nến,
                //    overshoot trên gap. bar.open là giá thực thi đầu tiên → chuẩn hơn.
                if (ticker.priceOpen < priceSL) {
                    long cnt = CLAMP_TOTAL.incrementAndGet();
                    LOG.info("[EXIT-CLAMP-118] #{} sym={} sl={} open={}→fill={}",
                            cnt, symbol, priceSL, ticker.priceOpen, ticker.priceOpen);
                }
                priceTP = Math.min(priceSL, ticker.priceOpen);
            }
        }
    }


    public void updateTPSL(Float rateChangeMax90M, KlineObjectSimple ticker) {
        // move SL
        if (priceSL != null) {
            // TASK (2026-07-17): TRAIL_PEAK_MODE — dinh de RATCHET SL. high=maxPrice (mac dinh, hanh vi cu),
            // close=priceClose (chong wick). Chi doi peak arm/ratchet, KHONG dung minPrice/MAE/disaster/time-stop.
            float trailPeak = "close".equals(Configs.TRAIL_PEAK_MODE) ? ticker.priceClose : ticker.maxPrice;
            Float rateLoss = calRateLossMax(trailPeak);
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

    /**
     * FUNDING tính 1 LƯỢT khi đóng lệnh (Bước 3, code lại 2026-06-28). Gọi DUY NHẤT ở closeOrder/cuối kỳ —
     * KHÔNG streaming mỗi tick (quá đắt cho WFO/HPO). Quét các mốc settlement THẬT của coin rơi trong
     * (timeStart, timeUpdate], cộng phí mỗi mốc rồi ghi TỔNG vào time2FundingFee (1 entry).
     *
     * <p>Công thức (long-only, lev 1x): phí = Σ rate(settle) × quantity × priceEntry. notional = avgEntry cụm
     * (priceEntry vol-weighted) — tính 1 lượt nên dùng giá vào trung bình thay vì close-tại-từng-settlement;
     * sai số nhỏ vì funding rate bé. quantity = quantity-cuối cụm. Dấu: rate>0 long TRẢ → phí DƯƠNG (calTp trừ);
     * rate<0 long NHẬN → ÂM. KHÔNG look-ahead: chỉ settle ≤ timeUpdate (thời điểm đóng).
     */
    public void computeFundingOnClose() {
        if (!Configs.APPLY_FUNDING_FEE) return;
        if (priceEntry == null || quantity == null || symbol == null) return;
        try {
            TreeMap<Long, Float> fundingMap = FundingFeeManager.getInstance().getFundingHistory(symbol);
            if (fundingMap == null || fundingMap.isEmpty()) return;
            // Cận dưới = clusterFirstLegTime (leg ĐẦU); fallback timeStart nếu chưa set. KHÔNG dùng riêng timeStart
            // vì timeStart = leg-cuối (đổi nó sẽ rò vào logic mở/đóng — đã từng vỡ GATE +69 lệnh).
            long fromTime = (clusterFirstLegTime > 0L) ? clusterFirstLegTime : timeStart;
            // các settlement trong (fromTime, timeUpdate] — đúng vòng đời cụm, KHÔNG look-ahead.
            float notional = quantity * priceEntry;
            float feeTotal = 0f;
            for (Float rate : fundingMap.subMap(fromTime, false, timeUpdate, true).values()) {
                if (rate != null) feeTotal += rate * notional;   // long: rate>0 => trả phí (dương)
            }
            if (feeTotal != 0f) time2FundingFee.put(timeUpdate, feeTotal);   // 1 entry tổng
        } catch (Exception e) {
            // coin không có funding data / lỗi đọc => phí 0 (an toàn, không chặn backtest)
        }
    }
}
