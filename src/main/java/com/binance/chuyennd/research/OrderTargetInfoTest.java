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
    // HARD-SL (env SIM_HARD_SL_PCT): GIA ENTRY DAU TIEN cua cum — BAT BIEN qua DCA. Set 1 lan luc mo leg
    //   dau (createOrder) va mang theo qua mergeOrder (KHONG averaged nhu priceEntry). Chi dung cho blanket
    //   hard-SL; null cho cac duong khong set -> byte-identical khi HARD_SL_PCT=0.
    public Float firstEntryPrice;
    /** DCA GRID (2026-08-01): so leg da khop cua CUM. Set trong mergeOrder. 1 = chua nhoi lan nao.
     *  Dung de biet dang o bac nao cua grid -> lay dung moc va ti trong tiep theo. */
    public int legCount = 1;
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
    // [2026-09-02] FUNDING notional MARK (Configs.FUNDING_MARK_NOTIONAL): tich luy streaming tren object CUM
    //   (symbol2OrderRunning) tai moi tick: moi settle trong (fundingLastSettle, tick] cong rate x quantity_cum x priceClose.
    //   mergeOrder carry 2 field nay sang cum moi. computeFundingOnClose doc fundingAccrued thay cho quet lai.
    //   transient: khong serialize; time2FundingFee van la noi luu TONG (tuong thich TraceOrderDone/BudgetManager).
    public transient float fundingAccrued = 0f;
    public transient long fundingLastSettle = 0L;
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
        if (Configs.FUNDING_MARK_NOTIONAL) accrueFundingMark(ticker.startTime.longValue(), ticker.priceClose);
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
            // dinh trailing = HIGH cua nen 1m (co TRAIL_PEAK_MODE da go 2026-09-03, chi con che do "high").
            Float rateLoss = calRateLossMax(ticker.maxPrice);
            Float rateMin2MoveSl = TradeUtils.calRateMinWithPredReturn15MForTradingStop(predReturn15M);
            if (rateLoss > rateMin2MoveSl) {
                Float rateStop = trailRate(rateLoss);
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
                    LOG.info("[EXIT-CLAMP-118] #{} sym={} | Time: start={} -> trigger={} | Entry: {} | Target SL: {} | Candle: [O={} H={} L={} C={}] | Final PriceTP: {} | Qty: {}",
                            cnt,   // index cua CHINH event nay (CLAMP_TOTAL.get() bi race khi WFO chay song song)
                            symbol,
                            com.binance.chuyennd.utils.Utils.normalizeDateYYYYMMDDHHmm(timeStart),
                            com.binance.chuyennd.utils.Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime),
                            priceEntry,
                            priceSL,
                            ticker.priceOpen,
                            ticker.maxPrice,
                            ticker.minPrice,
                            ticker.priceClose,
                            priceTP, // Giá chốt thực tế sau khi kẹp (Math.min(priceSL, ticker.maxPrice))
                            quantity
                    );
                }
                priceTP = Math.min(priceSL, ticker.priceOpen);
            }
        }
    }


    public void updateTPSL(Float rateChangeMax90M, KlineObjectSimple ticker) {
        // move SL
        if (priceSL != null) {
            // dinh trailing = HIGH cua nen 1m (co TRAIL_PEAK_MODE da go 2026-09-03, chi con che do "high").
            Float rateLoss = calRateLossMax(ticker.maxPrice);
            // Ratchet LIEN TUC (SIM_TS_GIVEBACK=1 la duong DUY NHAT con lai): nguong dich SL = base,
            //   khong con dead-zone x TS_PROFIT_MULTIPLIER. Thiet ke Uni: ROI 5% -> arm SL 2.5%, sau do
            //   dich len theo cung cong thuc.
            Float rateMin2MoveSl = TradeUtils.calRateMinWithPredReturn15MForTradingStop(rateChangeMax90M);
            if (rateLoss >= rateMin2MoveSl) {
                // FROZEN v1: gap trailing theo selector CỦA CHÍNH COIN (symbolPred=pNoPump), không theo gate pred.
                Float rateSL = trailRate(rateLoss);
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
        if (Configs.FUNDING_MARK_NOTIONAL) {
            // notional MARK: don not settle con sot tu tick cuoi den timeUpdate (gia = lastPrice, fallback priceTP/priceEntry)
            Float px = lastPrice != null ? lastPrice : (priceTP != null ? priceTP : priceEntry);
            accrueFundingMark(timeUpdate, px);
            if (fundingAccrued != 0f) time2FundingFee.put(timeUpdate, fundingAccrued);
            return;
        }
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
            // === SHORT funding (DRAFT 2026-07-18) ===
            // Theo spec task: "short TRA khi funding duong" -> feeTotal DUONG khi rate>0 (giong long),
            // calTp(SELL) van tru calFundingFee() -> short BI TRU khi funding duong (mo hinh BAO THU/pessimistic).
            // Vay CONG THUC KHONG doi theo side (feeTotal=rate*notional dung cho ca long lan short).
            // ⚠️ REVIEW-POINT: funding THUC te cua Binance = SHORT NHAN khi funding duong (long tra short).
            //   Draft nay co y mo hinh short-funding nhu CHI PHI (khong thoi phong alpha) dung acceptance-test (c).
            //   Neu product quyet ghi CO cho short khi funding duong -> DAO DAU feeTotal cho side==SELL tai day.
            if (feeTotal != 0f) time2FundingFee.put(timeUpdate, feeTotal);   // 1 entry tổng
        } catch (Exception e) {
            // coin không có funding data / lỗi đọc => phí 0 (an toàn, không chặn backtest)
        }
    }

    /**
     * [2026-09-02] Tich luy funding theo notional MARK. Quet cac moc settle THAT cua coin trong
     * (from, time] voi from = fundingLastSettle (hoac clusterFirstLegTime/timeStart lan dau); phi moi moc =
     * rate x quantity (cum dang mo) x price (close tick hien tai). Dau giong computeFundingOnClose: rate>0 long TRA.
     * KHONG look-ahead (chi settle <= time). Chi goi khi Configs.FUNDING_MARK_NOTIONAL.
     */
    public void accrueFundingMark(long time, Float price) {
        if (!Configs.APPLY_FUNDING_FEE || quantity == null || symbol == null || price == null) return;
        long from = fundingLastSettle > 0L ? fundingLastSettle
                : (clusterFirstLegTime > 0L ? clusterFirstLegTime : timeStart);
        if (time <= from) return;
        try {
            TreeMap<Long, Float> fundingMap = FundingFeeManager.getInstance().getFundingHistory(symbol);
            if (fundingMap == null || fundingMap.isEmpty()) return;
            Long k = fundingMap.higherKey(from);
            while (k != null && k <= time) {
                Float rate = fundingMap.get(k);
                if (rate != null) fundingAccrued += rate * quantity * price * Configs.FUNDING_SCALE;   // FUNDING_SCALE=1 mac dinh (stress test)
                fundingLastSettle = k;
                k = fundingMap.higherKey(k);
            }
        } catch (Exception e) {
            // khong co funding data => bo qua (giong computeFundingOnClose)
        }
    }

    /**
     * [2026-09-02] Gap trailing theo THIET KE (Uni): SIM_TS_GIVEBACK=1 -> rate = maxProfit - min(maxProfit x TS_GIVEBACK_RATIO(0.5),
     * maxGap), maxGap = TS_MAX_GAP_WEAK (3%) neu pNoPump > TS_PNOPUMP_WEAK_THR (0.29) hoac chua co pNoPump, nguoc lai TS_MAX_GAP (8%).
     * Vi du arm 5% -> SL +2.5%; 10% -> +7% (weak) / +5% (strong). LUON duong => SL khong bao gio duoi entry (khop live tsGap sau fix).
     */
    float trailRate(float maxProfitRate) {
        Float pnp = (this.symbolPred != null) ? this.symbolPred : 1f;   // chua co selector -> coi nhu yeu (bao thu)
        return TradeUtils.calRateLossDynamicBuyPNoPump(maxProfitRate, pnp, Configs.tsPnoPumpWeakThr());
    }
}
