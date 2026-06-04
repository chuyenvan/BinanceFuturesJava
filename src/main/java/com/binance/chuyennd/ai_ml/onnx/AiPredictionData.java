package com.binance.chuyennd.ai_ml.onnx;

import java.io.Serializable;

public class AiPredictionData implements Serializable {
    private static final long serialVersionUID = 1L;

    public long timestamp;

    // Dự báo Lợi nhuận
    public float predReturn15M;

    // Dự báo Rủi ro
    public float predRisk4H;


    public AiPredictionData(long timestamp, float p15m, float r4h) {
        this.timestamp = timestamp;
        this.predReturn15M = p15m;
        this.predRisk4H = r4h;
    }

    @Override
    public String toString() {
        return String.format("T:%d [15M:%.2f%% | Risk:%.2f%%]",
                timestamp, predReturn15M*100, predRisk4H*100);
    }
}