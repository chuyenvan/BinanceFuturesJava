package com.binance.chuyennd.ai_ml.onnx.dca;

public class DcaPredictionResult {
    // Xác suất về bờ trong 3 ngày (0.0 -> 1.0)
    // Nếu > 0.5 (hoặc ngưỡng bạn chọn) -> Cứu được
    public float recoverProbability;

    // Dự báo mức lỗ tối đa thêm trong 3 ngày (Số âm, ví dụ -0.05 là lỗ thêm 5%)
    public float predictedMaxDrawdown;

    public DcaPredictionResult(float recoverProb, float predictedDD) {
        this.recoverProbability = recoverProb;
        this.predictedMaxDrawdown = predictedDD;
    }

    @Override
    public String toString() {
        return String.format("AI_DCA[RecoverProb: %.2f%% | MaxDD: %.2f%%]",
                recoverProbability * 100, predictedMaxDrawdown * 100);
    }
}