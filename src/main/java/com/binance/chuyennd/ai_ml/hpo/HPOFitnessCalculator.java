package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.utils.Utils;
import java.util.Collection;

public class HPOFitnessCalculator {
    public static double evaluateProfitVelocity(SimulatorMarketLevelTicker1MStopLoss simulator) {
        Collection<OrderTargetInfoTest> orders = simulator.allOrderDone.values();
        if (orders.isEmpty()) return 0;

        double totalProfit = 0;
        long totalHoldingTime = 0;

        for (OrderTargetInfoTest order : orders) {
            // 1. calTp() đã tự động trừ đi calFundingFee() ở bên trong class OrderTargetInfoTest
            totalProfit += order.calTp();

            // 2. Tính thời gian giữ lệnh (từ lúc Start đến lúc Update/Close)
            totalHoldingTime += (order.timeUpdate - order.timeStart);
        }

        // 3. Tính thời gian giữ lệnh trung bình quy đổi ra GIỜ (hoặc NGÀY)
        // Utils.TIME_HOUR = 60 * 60 * 1000
        double avgHoldingTimeHours = (double) totalHoldingTime / orders.size() / Utils.TIME_HOUR;

        // Đảm bảo không bị lỗi chia cho 0 nếu lệnh đóng/mở ngay tức thì
        if (avgHoldingTimeHours <= 0) avgHoldingTimeHours = 1;

        // 4. Đưa hệ số vòng quay vốn vào Hàm mục tiêu (Fitness)
        double fitnessScore;
        if (totalProfit > 0) {
            // Lãi: Tối đa hóa Lợi nhuận sinh ra TRÊN MỖI GIỜ KẸT VỐN (Profit Velocity)
            fitnessScore = totalProfit / avgHoldingTimeHours;
        } else {
            // Lỗ: Trừng phạt nặng thêm nếu đã lỗ mà còn gồng lâu (nhân thời gian kẹt vốn)
            fitnessScore = totalProfit * avgHoldingTimeHours;
        }

        return fitnessScore;
    }
}