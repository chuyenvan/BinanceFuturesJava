package com.binance.chuyennd.ai_ml.onnx.entry;

import java.io.Serializable;

public class AiPredictionData implements Serializable {
    private static final long serialVersionUID = 1L;

    public long timestamp;

    // 🔥 Đã đổi tên biến theo đúng Tầm nhìn mới
    public float predReturn1H;
    public float predReturn4H;
    public float predRisk4H;

    public AiPredictionData(long timestamp, float p1h, float p4h, float r4h) {
        this.timestamp = timestamp;
        this.predReturn1H = p1h;
        this.predReturn4H = p4h;
        this.predRisk4H = r4h;
    }

    @Override
    public String toString() {
        return String.format("T:%d [1H:%.2f%% 4H:%.2f%% | Risk4H:%.2f%%]",
                timestamp, predReturn1H*100, predReturn4H*100, predRisk4H*100);
    }
}