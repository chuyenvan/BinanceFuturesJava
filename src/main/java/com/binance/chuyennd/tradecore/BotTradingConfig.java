package com.binance.chuyennd.tradecore;

import java.io.Serializable;

/**
 * Object lưu trữ toàn bộ Tham số Giao dịch (Trading Parameters) đã được làm sạch.
 * Phục vụ cho việc chạy Bot Live và quá trình HPO (Hyperparameter Optimization).
 */
public class BotTradingConfig implements Serializable {
    private static final long serialVersionUID = 1L;

    // =========================================================
    // 1. NHÓM BỘ LỌC AI & DỰ ĐOÁN (Từ HPO Funding/AI Reject)
    // =========================================================
    public double aiPredictRateMaxThreshold = 0.19076;
    public double aiPredictRateDown15m = -0.04749;
    public double aiPredictRateUpAvg = 0.00958;
    public double aiPredictRateDownAvg = -0.00683;

    // =========================================================
    // 2. NHÓM ĐIỀU KIỆN THỊ TRƯỜNG (Market Signal Thresholds)
    // =========================================================
    // --- Đã được HPO tối ưu ---
    public double msUpBigThres = 0.02046;
    public double msDownBigAvg = -0.03157;
    public double msUpMedThres = 0.01204;
    public double msDownMedAvg = -0.02069;
    public double msUpSmallThres = 0.00442;
    public double msDownSmallAvg = -0.01713;
    public double msDown15mMedOnly = -0.06725;
    public double msDown15mSmallOnly = -0.02145;

    // --- Nhóm giữ nguyên Default (Kết hợp Logic & BTC) ---
    public double msDownBigBtc = -0.010;
    public double msDownMedAvgCmb = -0.014;
    public double msDownMed15mCmb = -0.070;
    public double msDownSmall15m = -0.025;

    // =========================================================
    // 3. NHÓM CHỐT LỜI & DỜI CẮT LỖ ĐỘNG (Trailing Stop)
    // =========================================================
    public double rateProfitStopMarket = 0.01151; // Mức chốt lời Market cơ bản

    public double tsVolHighThres = 0.01760; // Ngưỡng nhận diện Volatility Cao
    public double tsRateHigh = 0.05549; // Target dời SL khi Volatility Cao

    public double tsVolMedThres = 0.01020; // Ngưỡng nhận diện Volatility Vừa
    public double tsRateMed = 0.04172; // Target dời SL khi Volatility Vừa

    public double tsVolLowThres = 0.00239; // Ngưỡng nhận diện Volatility Thấp
    public double tsRateLow = 0.01189; // Target dời SL khi Volatility Thấp

    // =========================================================
    // 4. NHÓM QUẢN LÝ VỊ THẾ & TRUNG BÌNH GIÁ (DCA)
    // =========================================================
    public double dcaRateLossBigDown = -0.05;
    public double dcaRateLossMediumDown = -0.08;
    public double dcaRateLossMediumUp = -0.15;
    public double dcaRateLossSmallDown = -0.20;
    public double dcaRateLossNull = -0.40;

    // Các mốc xả margin rủi ro cao (Ép DCA ở vùng sâu)
    public double dcaMarginRate1_5 = -0.60;
    public double dcaMarginRate2_0 = -0.70;
    public double dcaMarginRate2_5 = -0.90;
    public double dcaMarginRate3_0 = -0.99;

    // =========================================================
    // 5. NHÓM QUẢN TRỊ VỐN & NGÂN SÁCH (Budget Management)
    // =========================================================
    public int numberOrderBudget = 70; // Tổng số phần chia ngân sách

    // Ngưỡng giảm ngân sách khi Margin Ratio tăng cao
    public double budgetMarginRatio1 = 0.4820;
    public double budgetDivider1 = 1.5578;

    public double budgetMarginRatio2 = 0.7475;
    public double budgetDivider2 = 1.5984;

    // =========================================================
    // 6. NHÓM HẰNG SỐ HỆ THỐNG (System Constants)
    // =========================================================
    public int leverageOrder = 1;     // Đánh spot trên futures
    public double rateFee = 0.0004;   // Phí giao dịch
    public int numberRateDownHistoryTrade = 60;
    public int numberEntryEachSignal = 1;

    // Constructor mặc định
    public BotTradingConfig() {
    }
}