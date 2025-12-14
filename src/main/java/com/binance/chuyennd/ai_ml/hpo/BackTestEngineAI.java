package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.ai_ml.onnx.AIRejectFilter;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.v3.AiPredictionDataV3;
import com.binance.chuyennd.ai_ml.v4.AiPredictionDataV4;
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

    // --- MỤC TIÊU LỢI NHUẬN CẦN VƯỢT QUA ---
    private static final double TARGET_2023 = 12005.0;
    private static final double TARGET_2024 = 24336.0;
    private static final double TARGET_2025 = 23621.0;

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

            // 3. Chạy Simulation (Phải đảm bảo Configs.TIME_RUN = "20230101" ở bên ngoài)
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

        double p23 = yearProfits.get(2023);
        double p24 = yearProfits.get(2024);
        double p25 = yearProfits.get(2025);
        double totalProfit = p23 + p24 + p25;

        // --- KIỂM TRA RÀNG BUỘC (CONSTRAINTS) ---

        // 1. Nếu bất kỳ năm nào lỗ (Profit < 0) -> Phạt cực nặng (Loại ngay)
        if (p23 < 0 || p24 < 0 || p25 < 0) {
            return -50000.0 + totalProfit; // Rất thấp
        }

        // 2. Nếu năm nào thấp hơn Target cũ -> Phạt nặng theo mức độ thiếu hụt
        // Mục đích: Ép AI phải tìm ra bộ tham số vượt qua ngưỡng cũ
        double penalty = 0;
        boolean failConstraint = false;

        if (p23 < TARGET_2023) {
            penalty += (TARGET_2023 - p23) * 10; // Phạt gấp 10 lần số tiền thiếu
            failConstraint = true;
        }
        if (p24 < TARGET_2024) {
            penalty += (TARGET_2024 - p24) * 10;
            failConstraint = true;
        }
        if (p25 < TARGET_2025) {
            penalty += (TARGET_2025 - p25) * 10;
            failConstraint = true;
        }

        if (failConstraint) {
            // Trả về điểm thấp để AI biết hướng này không tốt,
            // nhưng vẫn giữ gradient (không trả về fix cứng -10000) để nó biết đường leo lên.
            return totalProfit - penalty - 10000;
        }

        // 3. Nếu vượt qua mọi chỉ tiêu -> Trả về tổng lợi nhuận (Càng cao càng tốt)
        // Đây là vùng "Thánh địa" mà AI sẽ hướng tới
        return totalProfit;
    }
}