package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.utils.Utils;

import java.util.TreeMap;

public class HPOFitnessCalculatorV2 {

    public static class FitnessReport {
        public int tradeCount = 0;
        public float totalProfit = 0f;
        public float maxDrawdown = 0f;
        public float recoveryFactor = 0f;
        public float penaltyCost = 0f;
        public float finalFitness = 0f;
        public String note = "";
    }

    public static FitnessReport evaluateDetailed(TreeMap<Long, OrderTargetInfoTest> allOrderDone) {
        FitnessReport report = new FitnessReport();

        if (allOrderDone == null || allOrderDone.isEmpty()) {
            report.note = "NO_TRADES";
            report.finalFitness = -10000f;
            return report;
        }

        report.tradeCount = allOrderDone.size();
        float currentDrawdown = 0f;
        float maxDrawdown = 0f;
        float peakEquity = BudgetManagerSimple.getInstance().balanceBasic;
        float currentEquity = peakEquity;

        for (OrderTargetInfoTest order : allOrderDone.values()) {
            float pnl = order.calProfit();
            report.totalProfit += pnl;
            currentEquity += pnl;

            // Tính Drawdown trên đường cong vốn thực tế
            if (currentEquity > peakEquity) {
                peakEquity = currentEquity;
                currentDrawdown = 0f;
            } else {
                currentDrawdown = currentEquity - peakEquity;
                if (currentDrawdown < maxDrawdown) {
                    maxDrawdown = currentDrawdown;
                }
            }

            // Phạt thời gian ngâm vốn: 0.05$ cho mỗi phút ôm lệnh
            // Phạt thời gian ngâm vốn (Chỉ phạt các lệnh kẹt quá lâu)
            // 3. Phạt thời gian ngâm vốn (Capital-Weighted Time Penalty)
            long holdTimeHours = (order.timeUpdate - order.timeStart) / Utils.TIME_HOUR;

            // Vùng miễn trừ: 12 giờ đầu tiên ôm lệnh KHÔNG BỊ PHẠT
            if (holdTimeHours > 12) {
                float margin = order.calMargin(); // Lấy số vốn thực tế đang ngâm của lệnh này

                // Mức phạt: 0.02% tổng vốn ngâm cho MỖI GIỜ (Tương đương 0.48%/ngày - Rất rát với lệnh to, nhẹ nhàng với lệnh nhỏ)
                float hourlyPenaltyRate = 0.0002f;

                report.penaltyCost += (margin * hourlyPenaltyRate * (holdTimeHours - 12));
            }
        }

        report.maxDrawdown = maxDrawdown;

        if (currentEquity <= 0) {
            report.finalFitness = -20000f;
            report.note = "BURN_ACCOUNT";
            return report;
        }

        float absMaxDrawdown = Math.abs(maxDrawdown);
        if (absMaxDrawdown < 1.0f) absMaxDrawdown = 1.0f;

        // 1. Hệ số Hồi phục (Recovery Factor)
        report.recoveryFactor = report.totalProfit / absMaxDrawdown;

        // 2. Net Score (Lợi nhuận sau khi trừ phí giam vốn)
        float netScore = report.totalProfit - report.penaltyCost;

        if (netScore <= 0) {
            report.finalFitness = netScore - absMaxDrawdown;
            report.note = "LOSING_STRATEGY";
            return report;
        }

        // Capped Recovery Factor (Tối đa 10.0 để tránh lạm phát điểm)
        float cappedRF = Math.min(report.recoveryFactor, 10.0f);
        report.finalFitness = netScore * (cappedRF / 3.0f);

        // =========================================================
        // 🔥 KIỂM SOÁT DRAWDOWN THEO TỶ LỆ PHẦN TRĂM (%) VỐN
        // =========================================================
        float startingCapital = BudgetManagerSimple.getInstance().balanceBasic;
        float maxAllowedDrawdownPercent = 0.40f; // Ngưỡng chịu đựng: Âm 40% vốn
        float maxAllowedDrawdownCash = - (startingCapital * maxAllowedDrawdownPercent);

        if (maxDrawdown < maxAllowedDrawdownCash) {
            // Tính số tiền vượt ngưỡng cho phép
            float excessDrawdown = Math.abs(maxDrawdown) - Math.abs(maxAllowedDrawdownCash);

            // Phạt cực nặng: Trừ 5 lần số tiền âm vượt ngưỡng
            report.finalFitness = report.finalFitness - (excessDrawdown * 5f);
            report.note = "PENALTY: Over MaxDD (" + String.format("%.1f", (Math.abs(maxDrawdown)/startingCapital)*100) + "%)";
        }

        return report;
    }
}