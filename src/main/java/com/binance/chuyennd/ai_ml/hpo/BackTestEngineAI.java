package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.ai_ml.onnx.AIRejectFilter;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;

import java.util.Calendar;
import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;

public class BackTestEngineAI {

    public AIRejectFilter aiRejectFilter;

    // --- CẬP NHẬT MỤC TIÊU LỢI NHUẬN CẦN VƯỢT QUA (DATA MỚI) ---
    private static final double TARGET_2022 = 19157.0;
    private static final double TARGET_2023 = 14929.0;
    private static final double TARGET_2024 = 29243.0;
    private static final double TARGET_2025 = 21009.0;

    public BackTestEngineAI(double risk, double minRet1H, double highRet,
                            double minMom15M, double minTrend4H, double deadTrend24H) {
        aiRejectFilter = new AIRejectFilter();
        aiRejectFilter.setConfig(risk, minRet1H, highRet, minMom15M, minTrend4H, deadTrend24H);
    }

    public double run(TreeMap<Long, MarketDataObject> time2MarketData,
                      TreeMap<Long, MarketRateChange> time2MarketRateChange,
                      TreeMap<Long, Double> time2BtcReverse,
                      TreeMap<Long, AiPredictionData> predictionMap) {
        try {
            // 1. Reset
            BudgetManagerSimple.resetInstance();
            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();

            // 2. Inject Data
            test.initDataReady(time2MarketData, time2MarketRateChange, time2BtcReverse,
                    predictionMap, aiRejectFilter);

            // 3. Chạy Simulation
            // Lưu ý: Đảm bảo Configs.TIME_RUN bên ngoài đã set về "20220101" để chạy đủ 4 năm
            test.simulatorWithInitEntry();

            // 4. --- TÍNH ĐIỂM (FITNESS FUNCTION) ---
            return calculateFitnessWithConstraints(test);

        } catch (Exception e) {
            e.printStackTrace();
            return -100000.0;
        }
    }

    private double calculateFitnessWithConstraints(SimulatorMarketLevelTicker1MStopLoss simulator) {
        // Map: Năm -> Lợi nhuận
        Map<Integer, Double> yearProfits = new HashMap<>();
        yearProfits.put(2022, 0.0);
        yearProfits.put(2023, 0.0);
        yearProfits.put(2024, 0.0);
        yearProfits.put(2025, 0.0);

        Calendar cal = Calendar.getInstance();

        // Duyệt qua tất cả các lệnh đã đóng để cộng dồn lợi nhuận theo năm
        for (OrderTargetInfoTest order : simulator.allOrderDone.values()) {
            cal.setTimeInMillis(order.timeUpdate); // Lấy thời gian đóng lệnh
            int year = cal.get(Calendar.YEAR);

            if (yearProfits.containsKey(year)) {
                yearProfits.put(year, yearProfits.get(year) + order.calTp());
            }
        }

        // Lấy lợi nhuận từng năm (dùng getOrDefault để an toàn)
        double p22 = yearProfits.getOrDefault(2022, 0.0);
        double p23 = yearProfits.getOrDefault(2023, 0.0);
        double p24 = yearProfits.getOrDefault(2024, 0.0);
        double p25 = yearProfits.getOrDefault(2025, 0.0);

        double totalProfit = p22 + p23 + p24 + p25;

        // --- KIỂM TRA RÀNG BUỘC (CONSTRAINTS) ---

        // 1. Nếu bất kỳ năm nào lỗ (Profit < 0) -> Phạt cực nặng (Loại ngay)
        if (p22 < 0 || p23 < 0 || p24 < 0 || p25 < 0) {
            return -50000.0 + totalProfit; // Rất thấp
        }

        // 2. Nếu năm nào thấp hơn Target cũ -> Phạt nặng theo mức độ thiếu hụt
        // Mục đích: Ép AI phải tìm ra bộ tham số tốt hơn lịch sử cũ
        double penalty = 0;
        boolean failConstraint = false;

        // Check 2022
        if (p22 < TARGET_2022) {
            penalty += (TARGET_2022 - p22) * 3;
            failConstraint = true;
        }
        // Check 2023
        if (p23 < TARGET_2023) {
            penalty += (TARGET_2023 - p23) * 3;
            failConstraint = true;
        }
        // Check 2024
        if (p24 < TARGET_2024) {
            penalty += (TARGET_2024 - p24) * 3;
            failConstraint = true;
        }
        // Check 2025
        if (p25 < TARGET_2025) {
            penalty += (TARGET_2025 - p25) * 3;
            failConstraint = true;
        }

        if (failConstraint) {
            // Trả về điểm thấp để AI biết hướng này không tốt
            return totalProfit - penalty - 10000;
        }

        // 3. Nếu vượt qua mọi chỉ tiêu -> Trả về tổng lợi nhuận (Càng cao càng tốt)
        return totalProfit;
    }
}