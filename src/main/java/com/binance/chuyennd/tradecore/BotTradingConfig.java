package com.binance.chuyennd.tradecore;

import java.io.Serializable;

/**
 * Object lưu trữ toàn bộ Tham số Giao dịch (Trading Parameters) đã được làm sạch.
 * Phục vụ cho việc chạy Bot Live và quá trình HPO (Hyperparameter Optimization).
 */
public class BotTradingConfig implements Serializable, Cloneable {
    private static final long serialVersionUID = 1L;

    // =========================================================
    // 2. NHÓM ĐIỀU KIỆN THỊ TRƯỜNG (GEOMETRIC THRESHOLDS)
    // =========================================================
    public float baseDown = 0.006f;  // Ngưỡng sập cơ sở (VD: 0.6%)
    public float ratioDown = 2.0f;   // Tốc độ giãn nở chiều sập (VD: x2)
    public float baseUp = 0.005f;    // Ngưỡng bơm cơ sở
    public float ratioUp = 2.0f;     // Tốc độ giãn nở chiều bơm
    // =========================================================
    // 1. NHÓM BỘ LỌC AI & DỰ ĐOÁN (Từ HPO Funding/AI Reject)
    // =========================================================
    public float aiPredictRateMaxThreshold = 0.19076f;
    public float aiPredictRateDown15m = -0.04749f;
    public float aiPredictRateUpAvg = 0.00958f;
    public float aiPredictRateDownAvg = -0.00683f;

    // =========================================================
    // 2. NHÓM ĐIỀU KIỆN THỊ TRƯỜNG (Market Signal Thresholds)
    // =========================================================
    // --- Đã được HPO tối ưu ---
    public float msUpBigThres = 0.02046f;
    public float msDownBigAvg = -0.03157f;
    public float msUpMedThres = 0.01204f;
    public float msDownMedAvg = -0.02069f;
    public float msUpSmallThres = 0.00442f;
    public float msDownSmallAvg = -0.01713f;
    public float msDown15mMedOnly = -0.06725f;
    public float msDown15mSmallOnly = -0.02145f;


    // =========================================================
    // 3. NHÓM CHỐT LỜI & DỜI CẮT LỖ ĐỘNG (Trailing Stop)
    // =========================================================
    public float rateProfitStopMarket = 0.01151f; // Mức chốt lời Market cơ bản

    // =========================================================
    // 4. NHÓM QUẢN LÝ VỊ THẾ & TRUNG BÌNH GIÁ (DCA)
    // =========================================================
    public float dcaRateLossBigDown = -0.05f;
    public float dcaRateLossMediumDown = -0.08f;
    public float dcaRateLossMediumUp = -0.15f;
    public float dcaRateLossSmallDown = -0.20f;
    public float dcaRateLossNull = -0.40f;

    // Các mốc xả margin rủi ro cao (Ép DCA ở vùng sâu)
    public float dcaMarginRate1_5 = -0.60f;
    public float dcaMarginRate2_0 = -0.70f;
    public float dcaMarginRate2_5 = -0.90f;
    public float dcaMarginRate3_0 = -0.99f;

    // =========================================================
    // 5. NHÓM QUẢN TRỊ VỐN & NGÂN SÁCH (Budget Management)
    // =========================================================
    public int numberOrderBudget = 70; // Tổng số phần chia ngân sách

    // Ngưỡng giảm ngân sách khi Margin Ratio tăng cao
    public float budgetMarginRatio1 = 0.4820f;
    public float budgetDivider1 = 1.5578f;

    public float budgetMarginRatio2 = 0.7475f;
    public float budgetDivider2 = 1.5984f;

    // =========================================================
    // 6. NHÓM HẰNG SỐ HỆ THỐNG (System Constants)
    // =========================================================
    public int leverageOrder = 1;     // Đánh spot trên futures
    public float rateFee = 0.0004f;   // Phí giao dịch
    public int numberRateDownHistoryTrade = 60;
    public int numberEntryEachSignal = 1;

    // =========================================================
    // 7. NHÓM ĐIỀU PHỐI VÀO LỆNH (Time-Weighted & Concurrency)
    // =========================================================
    public int maxConcurrentOrders = 10;     // Tối đa ôm 10 mã cùng lúc

    // Constructor mặc định
    public BotTradingConfig() {
    }
    @Override
    public BotTradingConfig clone() {
        try {
            return (BotTradingConfig) super.clone();
        } catch (Exception e) {
            throw new RuntimeException("Error cloning BotTradingConfig");
        }
    }
}