package com.binance.chuyennd.ai_ml.onnx;

import java.io.Serializable;

public class AiPredictionData implements Serializable {
    private static final long serialVersionUID = 1L;

    public long timestamp;

    // Dự báo Lợi nhuận
    public float predReturn15M;
    public float predReturn24H;

    // Dự báo Rủi ro
    public float predRisk4H;


    public AiPredictionData(long timestamp, float p15m, float p24h, float r4h) {
        this.timestamp = timestamp;
        this.predReturn15M = p15m;
        this.predReturn24H = p24h;
        this.predRisk4H = r4h;
    }

    @Override
    public String toString() {
        return String.format("T:%d [15M:%.2f%% 24H:%.2f%% | Risk:%.2f%%]",
                timestamp, predReturn15M*100, predReturn24H*100, predRisk4H*100);
    }
}