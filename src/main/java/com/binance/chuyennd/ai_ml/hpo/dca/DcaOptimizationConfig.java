package com.binance.chuyennd.ai_ml.hpo.dca; // Dat cung package voi BackTestEngine

/**
 * Lop nay chua 9 tham so se duoc Jenetics toi uu hoa
 * cho logic DCA.
 */
public class DcaOptimizationConfig {

    // 5 Tham so tu 'getDcaConfig'
    // 5 Tham so tu 'getDcaConfig'
    public double rateLossBigDown     = -0.05;
    public double rateLossMediumDown  = -0.08;
    public double rateLossMediumUp    = -0.15;
    public double rateLossSmallDown   = -0.20;
    public double rateLossNull        = -0.4;

    // 4 Tham so tu 'calculateAdjustedRateLoss'
    public double marginRate_1_5      = -0.6;
    public double marginRate_2_0      = -0.7;
    public double marginRate_2_5      = -0.9;

    /**
     * Constructor mac dinh (khong can lam gi,
     * vi gia tri da duoc gan o tren)
     */
    public DcaOptimizationConfig() {
    }
    // (Muc 3.0 van giu nguyen la -0.99 nhu yeu cau)
}