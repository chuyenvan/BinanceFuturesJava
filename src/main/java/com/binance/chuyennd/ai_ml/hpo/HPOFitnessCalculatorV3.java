package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.utils.Utils;

import java.util.Collection;
import java.util.TreeMap;

public class HPOFitnessCalculatorV3 {

    public static class FitnessReport {
        public int tradeCount = 0;
        public float totalProfit = 0f;
        public float maxDrawdown = 0f;
        public float penaltyCost = 0f;
        public float netScore = 0f;
        public float finalFitness = 0f;
        public String note = "";
    }

    public static FitnessReport evaluateDetailed(TreeMap<Long, OrderTargetInfoTest> allOrderDone) {
        FitnessReport report = new FitnessReport();
        int windowDays = 90;

        if (allOrderDone == null || allOrderDone.isEmpty()) {
            report.note = "NO_TRADES";
            report.finalFitness = -10000f;
            return report;
        }

        Collection<OrderTargetInfoTest> orders = allOrderDone.values();
        report.tradeCount = orders.size();

        if (report.tradeCount >= 2) {
            long timeTrade = (allOrderDone.lastKey() - allOrderDone.firstKey()) / Utils.TIME_DAY;
            windowDays = (int) Math.max(1, timeTrade);
        }

        int minRequiredTrades = (int) (windowDays * 0.33f);
        if (minRequiredTrades < 5) minRequiredTrades = 5;

        // Phạt lười trade
        if (report.tradeCount == 0) {
            report.finalFitness = -10000.0f;
            report.note = "ZERO_TRADES";
            return report;
        }
        if (report.tradeCount < minRequiredTrades) {
            report.finalFitness = -5000.0f + (report.tradeCount * (5000.0f / minRequiredTrades));
            report.note = "TOO_FEW_TRADES";
            return report;
        }

        // =======================================================
        // 1. TÍNH LỢI NHUẬN VÀ PHÍ NGÂM VỐN (RETAIL LOGARITHMIC PENALTY)
        // =======================================================
        for (OrderTargetInfoTest order : orders) {
            report.totalProfit += order.calTp();

            float holdTimeHours = (order.timeUpdate - order.timeStart) / (float) Utils.TIME_HOUR;
            float holdTimeDays = holdTimeHours / 24f;

            // Ân hạn 3 ngày cho Bot DCA thoải mái rung lắc
            float gracePeriodDays = 3.0f;

            if (holdTimeDays > gracePeriodDays) {
                float excessDays = holdTimeDays - gracePeriodDays;
                float margin = order.calMargin();

                // Hàm phạt Logarit (Cap ở mức 2.5% tổng vốn ngâm)
                float timeMultiplier = (float) Math.log1p(excessDays * 0.2);
                float maxPenaltyRate = 0.025f;
                float penaltyRate = timeMultiplier * 0.003f;

                if (penaltyRate > maxPenaltyRate) {
                    penaltyRate = maxPenaltyRate;
                }

                report.penaltyCost += (margin * penaltyRate);
            }
        }

        // =======================================================
        // 2. LẤY DRAWDOWN THỰC TẾ (Toàn danh mục)
        // =======================================================
        Float portfolioUnProfitMin = BudgetManagerSimple.getInstance().balanceIndex.unProfitMin;
        if (portfolioUnProfitMin != null) {
            report.maxDrawdown = portfolioUnProfitMin;
        }

        float absMaxDrawdown = Math.abs(report.maxDrawdown);
        if (absMaxDrawdown < 1.0f) absMaxDrawdown = 1.0f;

        if (report.totalProfit <= 0) {
            report.finalFitness = report.totalProfit - absMaxDrawdown;
            report.note = "BURN_ACCOUNT";
            return report;
        }

        // Lãi ròng thực tế
        report.netScore = report.totalProfit - report.penaltyCost;

        if (report.netScore <= 0) {
            report.finalFitness = report.netScore;
            report.note = "EATEN_BY_PENALTY";
            return report;
        }

        // =======================================================
        // 3. TÍNH TOÁN FITNESS: RETAIL DRAWDOWN TOLERANCE
        // =======================================================

        float startingCapital = BudgetManagerSimple.getInstance().balanceBasic;
        float drawdownPercent = absMaxDrawdown / startingCapital;
        float drawdownPenalty = 0f;

        // Vùng 1: < 15% -> Miễn nhiễm, thả rông cho HPO kiếm PnL
        if (drawdownPercent <= 0.15f) {
            drawdownPenalty = 0f;
        }
        // Vùng 2: 15% - 30% -> Phạt nhẹ phần vượt mốc 15%
        else if (drawdownPercent <= 0.30f) {
            float excessDD = absMaxDrawdown - (startingCapital * 0.15f);
            drawdownPenalty = excessDD * 1.0f;
        }
        // Vùng 3: > 30% -> Phạt cực rát phần vượt mốc 30% (Hệ số x3)
        else {
            float excessDD_Level1 = startingCapital * 0.15f;
            float excessDD_Level2 = absMaxDrawdown - (startingCapital * 0.30f);
            drawdownPenalty = (excessDD_Level1 * 1.0f) + (excessDD_Level2 * 3.0f);
        }

        report.finalFitness = report.netScore - drawdownPenalty;

        // Thưởng Trade Count (Tie-breaker)
        report.finalFitness += (report.tradeCount * 0.1f);

        // =======================================================
        // 4. KIỂM SOÁT DRAWDOWN TỔNG (Kill Switch)
        // =======================================================
        if (drawdownPercent > 0.40f) {
            report.finalFitness -= 50000f;
            report.note = "OVER_MAX_DD_40%";
        } else {
            report.note = "SUCCESS";
        }

        return report;
    }
}