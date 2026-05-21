package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.utils.Utils;

import java.util.Collection;
import java.util.TreeMap;

public class HPOFitnessCalculatorV2 {

    // --- OBJECT ĐỂ CHỨA BÁO CÁO CHI TIẾT ---
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

        // 1. TÍNH TOÁN CỬA SỔ THỜI GIAN VÀ RÀNG BUỘC SỐ LỆNH TỐI THIỂU (TINH HOA BẢN CŨ)
        if (report.tradeCount >= 2) {
            long timeTrade = (allOrderDone.lastKey() - allOrderDone.firstKey()) / Utils.TIME_DAY;
            windowDays = (int) Math.max(1, timeTrade);
        }

        int minRequiredTrades = (int) (windowDays * 0.33f);
        if (minRequiredTrades < 5) minRequiredTrades = 5;

        // Phạt nếu bot quá hèn nhát
        if (report.tradeCount < minRequiredTrades) {
            report.finalFitness = -5000.0f + (report.tradeCount * (5000.0f / minRequiredTrades));
            report.note = "TOO_FEW_TRADES";
            return report;
        }

        // 2. TÍNH LỢI NHUẬN VÀ PHẠT NGÂM VỐN (CAPITAL-WEIGHTED APR PENALTY)
        for (OrderTargetInfoTest order : orders) {
            report.totalProfit += order.calProfit(); // Sử dụng hàm calPnl() để lấy chuẩn PnL thực tế

            long holdTimeHours = (order.timeUpdate - order.timeStart) / Utils.TIME_HOUR;

            // Vùng miễn trừ: 12 giờ đầu tiên ôm lệnh KHÔNG BỊ PHẠT (Dành cho sóng ngắn)
            if (holdTimeHours > 12) {
                float margin = order.calMargin(); // Lấy số vốn thực tế đang ngâm của lệnh này
                // Mức phạt: 0.02% tổng vốn ngâm cho MỖI GIỜ (Tương đương 0.48%/ngày - Phạt theo kiểu tính Lãi Vay)
                float hourlyPenaltyRate = 0.0002f;
                report.penaltyCost += (margin * hourlyPenaltyRate * (holdTimeHours - 12));
            }
        }

        // 3. FIX LỖI MAXDD: Lấy Drawdown thực tế của TOÀN BỘ DANH MỤC từ BudgetManager (TINH HOA BẢN CŨ)
        Float portfolioUnProfitMin = BudgetManagerSimple.getInstance().balanceIndex.unProfitMin;
        if (portfolioUnProfitMin != null) {
            report.maxDrawdown = portfolioUnProfitMin; // Giá trị này là số âm (VD: -4000$)
        }

        float absMaxDrawdown = Math.abs(report.maxDrawdown);
        if (absMaxDrawdown < 1.0f) absMaxDrawdown = 1.0f; // Tránh lỗi chia cho 0

        // Nếu tổng kết lỗ (Burn account)
        if (report.totalProfit <= 0) {
            report.finalFitness = report.totalProfit - absMaxDrawdown;
            report.note = "BURN_ACCOUNT";
            return report;
        }

        // 4. NET SCORE (Tiền mang về sau khi nộp "lãi vay" phạt ngâm lệnh)
        report.netScore = report.totalProfit - report.penaltyCost;

        if (report.netScore <= 0) {
            report.finalFitness = report.netScore - absMaxDrawdown;
            report.note = "LOSING (EATEN_BY_PENALTY)";
            return report;
        }

        report.recoveryFactor = report.totalProfit / absMaxDrawdown;

        // =========================================================
        // 5. TÍNH TOÁN FITNESS CUỐI CÙNG (CÂN BẰNG RETAIL QUANT)
        // =========================================================

        // Ngưỡng rung lắc cho phép: Chấp nhận gồng lỗ 3000$ để ăn lớn
        float acceptableDrawdown = 3000f;
        float ddPenalty = 0f;

        if (absMaxDrawdown > acceptableDrawdown) {
            // Phạt lũy tiến phần vượt ngưỡng (Vượt càng nhiều phạt càng nặng)
            ddPenalty = (absMaxDrawdown - acceptableDrawdown) * 2.5f;
        }

        // Công thức chuẩn: Tối đa hóa Lợi nhuận Ròng - Trừ đi phí phạt rủi ro
        report.finalFitness = report.netScore - ddPenalty;

        // Khuyến khích bot trade nhiều (Tie-breaker phá vỡ thế hòa - Tinh hoa bản cũ)
        report.finalFitness += (report.tradeCount * 0.1f);

        // KIỂM SOÁT DRAWDOWN MAXIMUM TỔNG (Kill Switch - Chặn cháy tài khoản)
        float startingCapital = BudgetManagerSimple.getInstance().balanceBasic;
        float maxAllowedDrawdownCash = startingCapital * 0.40f; // Ngưỡng chết: 40% vốn

        if (absMaxDrawdown > maxAllowedDrawdownCash) {
            report.finalFitness -= 50000f; // Phạt chết luôn không cho ngóc đầu lên
            report.note = "OVER_MAX_DD_40%";
        } else {
            report.note = "SUCCESS";
        }

        return report;
    }
}