package com.binance.chuyennd.ai_ml.v4;

import java.io.Serializable;

public class AiPredictionDataV4 implements Serializable {
    private static final long serialVersionUID = 4L;

    public long timestamp;

    // Return Forecasts
    public float p15M;
    public float p1H;
    public float p4H;
    public float p24H; // V4 hồi sinh target này

    // Risk Forecasts
    public float maxDD4H; // Thay thế cho riskDrawdown cũ

    public AiPredictionDataV4(long t, float p15, float p1, float p4, float p24, float dd) {
        this.timestamp = t;
        this.p15M = p15;
        this.p1H = p1;
        this.p4H = p4;
        this.p24H = p24;
        this.maxDD4H = dd;
    }

    @Override
    public String toString() {
        return String.format("V4[T:%d | 1H:%.2f%% | 24H:%.2f%% | DD:%.2f%%]",
                timestamp, p1H * 100, p24H * 100, maxDD4H * 100);
    }
}