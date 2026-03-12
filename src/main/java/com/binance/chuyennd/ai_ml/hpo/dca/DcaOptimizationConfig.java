package com.binance.chuyennd.ai_ml.hpo.dca; // Dat cung package voi BackTestEngine

/**
 * Lop nay chua 9 tham so se duoc Jenetics toi uu hoa
 * cho logic DCA.
 */
public class DcaOptimizationConfig {

    // 5 Tham so tu 'getDcaConfig'
    // 5 Tham so tu 'getDcaConfig'
    public float rateLossBigDown     = -0.05f;
    public float rateLossMediumDown  = -0.08f;
    public float rateLossMediumUp    = -0.15f;
    public float rateLossSmallDown   = -0.20f;
    public float rateLossNull        = -0.4f;

    // 4 Tham so tu 'calculateAdjustedRateLoss'
    public float marginRate_1_5      = -0.6f;
    public float marginRate_2_0      = -0.7f;
    public float marginRate_2_5      = -0.9f;

    /**
     * Constructor mac dinh (khong can lam gi,
     * vi gia tri da duoc gan o tren)
     */
    public DcaOptimizationConfig() {
    }
    // (Muc 3.0 van giu nguyen la -0.99 nhu yeu cau)
}