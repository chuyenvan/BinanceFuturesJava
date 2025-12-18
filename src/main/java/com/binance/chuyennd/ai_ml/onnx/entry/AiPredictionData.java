package com.binance.chuyennd.ai_ml.onnx.entry;

import java.io.Serializable;

public class AiPredictionData implements Serializable {
    private static final long serialVersionUID = 1L;

    public long timestamp;

    // Dự báo Lợi nhuận
    public float predReturn15M;
    public float predReturn1H;
    public float predReturn4H;
    public float predReturn24H;

    // Dự báo Rủi ro
    public float predRisk4H;
    public float predRisk24H;

    public AiPredictionData(long timestamp, float p15m, float p1h, float p4h, float p24h, float r4h, float r24h) {
        this.timestamp = timestamp;
        this.predReturn15M = p15m;
        this.predReturn1H = p1h;
        this.predReturn4H = p4h;
        this.predReturn24H = p24h;
        this.predRisk4H = r4h;
        this.predRisk24H = r24h;
    }

    @Override
    public String toString() {
        return String.format("T:%d [15M:%.2f%% 1H:%.2f%% | Risk:%.2f%%]",
                timestamp, predReturn15M*100, predReturn1H*100, predRisk4H*100);
    }
}