package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.utils.Utils;
import java.util.Collection;

public class HPOEvaluator {
    public static double evaluateProfitVelocity(SimulatorMarketLevelTicker1MStopLoss simulator) {
        Collection<OrderTargetInfoTest> orders = simulator.allOrderDone.values();
        if (orders.isEmpty()) return -1000.0; // Phạt nếu không có lệnh nào

        double totalProfit = 0;
        long totalHoldingTime = 0;

        for (OrderTargetInfoTest order : orders) {
            totalProfit += order.calTp(); // Đã trừ funding [cite: 752]
            totalHoldingTime += (order.timeUpdate - order.timeStart);
        }

        double avgHoldingTimeHours = (double) totalHoldingTime / orders.size() / Utils.TIME_HOUR;
        if (avgHoldingTimeHours <= 0) avgHoldingTimeHours = 1;

        if (totalProfit > 0) {
            // Lãi: Càng nhanh càng tốt
            return totalProfit / avgHoldingTimeHours;
        } else {
            // Lỗ: Càng gồng lâu càng phạt nặng
            return totalProfit * avgHoldingTimeHours;
        }
    }
}