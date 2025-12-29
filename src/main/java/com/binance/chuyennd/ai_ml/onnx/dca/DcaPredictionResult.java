package com.binance.chuyennd.ai_ml.onnx.dca;

public class DcaPredictionResult {
    // --- Regression Outputs ---
    // Dự báo mức lỗ tối đa thêm trong 3 ngày (Risk - Số âm)
    public float predictedMaxDrawdown;

    // Dự báo mức hồi phục tối đa trong 3 ngày (Reward - Số dương)
    public float predictedMaxRise;

    // --- Classification Probabilities ---
    // Xác suất sắp Pump > 20% (0.0 -> 1.0)
    public float probPump20Pct;

    // Xác suất sắp Dump > 30% (0.0 -> 1.0)
    public float probDump30Pct;

    public DcaPredictionResult(float predictedDD, float predictedRise, float probPump, float probDump) {
        this.predictedMaxDrawdown = predictedDD;
        this.predictedMaxRise = predictedRise;
        this.probPump20Pct = probPump;
        this.probDump30Pct = probDump;
    }

    @Override
    public String toString() {
        return String.format("AI_DCA[Risk: %.2f%% | Reward: %.2f%% | PumpProb: %.2f | DumpProb: %.2f]",
                predictedMaxDrawdown * 100, predictedMaxRise * 100, probPump20Pct, probDump30Pct);
    }

    // Helper để ra quyết định nhanh (Threshold có thể tùy chỉnh)
    public boolean isSafeToBuy() {
        // Không mua nếu Risk quá cao hoặc khả năng Dump mạnh quá lớn
        return predictedMaxDrawdown > -0.30 && probDump30Pct < 0.5;
    }
}