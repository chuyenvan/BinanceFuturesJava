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
        public float recoveryFactor = 0f;
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

        if (report.tradeCount < minRequiredTrades) {
            report.finalFitness = -5000.0f + (report.tradeCount * (5000.0f / minRequiredTrades));
            report.note = "TOO_FEW_TRADES";
            return report;
        }

        // =======================================================
        // 1. TÍNH LỢI NHUẬN THỰC TẾ VÀ PHÍ NGÂM VỐN
        // =======================================================
        for (OrderTargetInfoTest order : orders) {
            // 🔥 CHUẨN XÁC: Dùng calTp() để trừ sạch Fee sàn và Funding Fee
            report.totalProfit += order.calTp();

            long holdTimeHours = (order.timeUpdate - order.timeStart) / Utils.TIME_HOUR;

            // Ân hạn 8 giờ đầu tiên (Sóng scalping). Sau 8h, phạt ngâm vốn 0.02%/giờ
            if (holdTimeHours > 8) {
                float margin = order.calMargin();
                report.penaltyCost += (margin * 0.0002f * (holdTimeHours - 8));
            }
        }

        // =======================================================
        // 2. LẤY DRAWDOWN THỰC TẾ TOÀN DANH MỤC
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

        // Lãi ròng sau khi nộp "lãi vay" ngâm lệnh
        report.netScore = report.totalProfit - report.penaltyCost;

        if (report.netScore <= 0) {
            report.finalFitness = report.netScore - absMaxDrawdown;
            report.note = "EATEN_BY_PENALTY";
            return report;
        }

        report.recoveryFactor = report.netScore / absMaxDrawdown;

        // =======================================================
        // 3. TÍNH TOÁN FITNESS: SỨC MẠNH CỦA ĐƯỜNG CONG
        // =======================================================
        float startingCapital = BudgetManagerSimple.getInstance().balanceBasic;

        // 🔥 HÀM PHẠT BẬC 2 (QUADRATIC PENALTY):
        // Tránh tạo vách đá (Genetic Cliff). Cho AI thoải mái rung lắc.
        // Ví dụ vốn 100k:
        // - DD 2k -> Phạt 40$ (Rất nhẹ, Bot dám bắt đáy)
        // - DD 10k -> Phạt 1000$ (Bắt đầu chú ý)
        // - DD 30k -> Phạt 9000$ (Ép AI phải cắt lỗ)
        float drawdownPenalty = (absMaxDrawdown * absMaxDrawdown) / startingCapital;

        // 🔥 THƯỞNG HỆ SỐ PHỤC HỒI (RECOVERY FACTOR BONUS)
        // Nếu Bot kiếm được lãi cao gấp 2 lần rủi ro nó gánh chịu (RF > 2.0), cộng điểm mạnh!
        float rfBonus = 0f;
        if (report.recoveryFactor > 2.0f) {
            rfBonus = (report.recoveryFactor - 2.0f) * 1000f; // Điểm thưởng chất lượng
        }

        // Công thức chuẩn: Tối đa hóa Lợi nhuận Ròng - Rủi ro + Thưởng Thông minh
        report.finalFitness = report.netScore - drawdownPenalty + rfBonus;

        // Tie-breaker: Bot trade nhiều hơn sẽ thắng nếu điểm bằng nhau
        report.finalFitness += (report.tradeCount * 0.1f);

        // KILL SWITCH: Vượt 40% vốn là loại luôn
        if (absMaxDrawdown > (startingCapital * 0.40f)) {
            report.finalFitness -= 50000f;
            report.note = "OVER_MAX_DD_40%";
        } else {
            report.note = "SUCCESS";
        }

        return report;
    }
}