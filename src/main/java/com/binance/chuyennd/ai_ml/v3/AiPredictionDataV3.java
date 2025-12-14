package com.binance.chuyennd.ai_ml.v3;
import java.io.Serializable;

public class AiPredictionDataV3 implements Serializable {
    private static final long serialVersionUID = 3L;
    public long timestamp;
    public float p15M, p1H, p4H, maxDD4H;

    public AiPredictionDataV3(long t, float p15, float p1, float p4, float dd) {
        this.timestamp = t;
        this.p15M = p15; this.p1H = p1; this.p4H = p4; this.maxDD4H = dd;
    }
}