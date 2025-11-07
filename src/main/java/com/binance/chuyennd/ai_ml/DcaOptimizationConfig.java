package com.binance.chuyennd.ai_ml; // Dat cung package voi BackTestEngine

/**
 * Lop nay chua 9 tham so se duoc Jenetics toi uu hoa
 * cho logic DCA.
 */
public class DcaOptimizationConfig {

    // 5 Tham so tu 'getDcaConfig'
    public double rateLossBigDown;     // Muc tieu: -0.05
    public double rateLossMediumDown;  // Muc tieu: -0.08
    public double rateLossMediumUp;    // Muc tieu: -0.15
    public double rateLossSmallDown;   // Muc tieu: -0.20
    public double rateLossNull;        // Muc tieu: -0.4

    // 4 Tham so tu 'calculateAdjustedRateLoss'
    public double marginRate_1_5;      // Muc tieu: -0.6
    public double marginRate_2_0;      // Muc tieu: -0.7
    public double marginRate_2_5;      // Muc tieu: -0.9
    // (Muc 3.0 van giu nguyen la -0.99 nhu yeu cau)
}