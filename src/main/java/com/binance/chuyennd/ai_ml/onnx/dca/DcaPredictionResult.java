package com.binance.chuyennd.ai_ml.onnx.dca;

public class DcaPredictionResult {
    // Dự báo mức lỗ tối đa thêm trong 3 ngày (Risk - Số âm)
    public float predictedMaxDrawdown;

    // Dự báo mức hồi phục tối đa trong 3 ngày (Reward - Số dương)
    public float predictedMaxRise;

    public DcaPredictionResult(float predictedDD, float predictedRise) {
        this.predictedMaxDrawdown = predictedDD;
        this.predictedMaxRise = predictedRise;
    }

    @Override
    public String toString() {
        return String.format("AI_DCA[Risk(MaxDD): %.2f%% | Reward(MaxRise): %.2f%%]",
                predictedMaxDrawdown * 100, predictedMaxRise * 100);
    }
}