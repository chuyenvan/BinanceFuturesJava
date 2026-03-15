package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.utils.Utils;
import java.util.Collection;

public class HPOFitnessCalculator {
    public static float evaluateProfitVelocity(SimulatorMarketLevelTicker1MStopLoss simulator) {
        Collection<OrderTargetInfoTest> orders = simulator.allOrderDone.values();
        int tradeCount = orders.size();

        // 🔥 LOGIC CHỈ ĐƯỜNG CHO AI (GRADIENT PENALTY)
        if (tradeCount == 0) {
            return -10000.0f; // Ngu nhất: Phạt kịch khung
        } else if (tradeCount < 20) {
            // Khôn hơn 1 chút: 1 lệnh bị phạt -9500, 10 lệnh bị phạt -5000...
            // AI sẽ tự hiểu là phải tăng số lệnh lên để đỡ bị phạt!
            return -10000.0f + (tradeCount * 500.0f);
        }

        // Nếu qua được mốc 20 lệnh (Sống sót), mới bắt đầu tính toán lợi nhuận
        float totalProfit = 0;
        long totalHoldingTime = 0;

        for (OrderTargetInfoTest order : orders) {
            totalProfit += order.calTp();
            totalHoldingTime += (order.timeUpdate - order.timeStart);
        }

//        float avgHoldingTimeHours = (float) totalHoldingTime / tradeCount / Utils.TIME_HOUR;
//        if (avgHoldingTimeHours <= 0) avgHoldingTimeHours = 1;
//
//        float fitnessScore;
//        if (totalProfit > 0) {
//            fitnessScore = totalProfit / avgHoldingTimeHours;
//        } else {
//            fitnessScore = totalProfit * avgHoldingTimeHours;
//        }

//        return fitnessScore;
        return totalProfit;
    }
}