package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.utils.Utils;

import java.util.Collection;

public class HPOFitnessCalculator {
    private static final float HOURLY_COST = 0.0002f; // Phạt 0.02%/giờ giam vốn

    // --- OBJECT ĐỂ CHỨA BÁO CÁO CHI TIẾT ---
    public static class FitnessReport {
        public int tradeCount = 0;
        public float totalProfit = 0f;
        public float maxDrawdown = 0f;
        public float penaltyCost = 0f;
        public float netScore = 0f;
        public float calmarRatio = 0f;
        public float finalFitness = 0f;
        public String note = "";
    }

    public static float evaluateProfitVelocity(SimulatorMarketLevelTicker1MStopLoss simulator) {
        return evaluateDetailed(simulator).finalFitness;
    }

    public static FitnessReport evaluateDetailed(SimulatorMarketLevelTicker1MStopLoss simulator) {
        FitnessReport report = new FitnessReport();
        int windowDays = 90;

        Collection<OrderTargetInfoTest> orders = simulator.allOrderDone.values();
        report.tradeCount = orders.size();

        if (report.tradeCount >= 2) {
            long timeTrade = (simulator.allOrderDone.lastKey() - simulator.allOrderDone.firstKey()) / Utils.TIME_DAY;
            windowDays = (int) Math.max(1, timeTrade);
        }

        int minRequiredTrades = (int) (windowDays * 0.33f);
        if (minRequiredTrades < 5) minRequiredTrades = 5;

        // 1. Phạt nếu không có lệnh hoặc quá ít lệnh
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

        double totalCapitalTimeLocked = 0;

        for (OrderTargetInfoTest order : orders) {
            report.totalProfit += order.calTp();

            float hoursHeld = (order.timeUpdate - order.timeStart) / (float) Utils.TIME_HOUR;
            if (hoursHeld <= 0.016f) hoursHeld = 0.016f;
            totalCapitalTimeLocked += (order.calMargin() * hoursHeld);
        }

        // 🔥 FIX LỖI MAXDD 0.0: Lấy Drawdown thực tế của TOÀN BỘ DANH MỤC từ BudgetManager
        Float portfolioUnProfitMin = BudgetManagerSimple.getInstance().balanceIndex.unProfitMin;
        if (portfolioUnProfitMin != null) {
            report.maxDrawdown = portfolioUnProfitMin; // Giá trị này là số âm (VD: -4000$)
        }

        float absMaxDrawdown = Math.abs(report.maxDrawdown);
        if (absMaxDrawdown < 1.0f) absMaxDrawdown = 1.0f;

        // Nếu tổng kết lỗ (Burn account)
        if (report.totalProfit <= 0) {
            report.finalFitness = report.totalProfit - absMaxDrawdown;
            report.note = "BURN_ACCOUNT";
            return report;
        }

        // 2. Tính toán Net Score
        report.penaltyCost = (float) (totalCapitalTimeLocked * HOURLY_COST);
        report.netScore = report.totalProfit - report.penaltyCost;

        if (report.netScore <= 0) {
            report.finalFitness = report.netScore;
            report.note = "EATEN_BY_PENALTY";
            return report;
        }

        report.calmarRatio = report.netScore / absMaxDrawdown;

        // 🔥 SỬA LỖI ĐIỂM SỐ BÙNG NỔ: TUYẾN TÍNH HÓA (Linear Penalty)
        // Hệ số 1.5 nghĩa là: Gồng lỗ 1$ bị trừ 1.5$ vào điểm thành tích.
        float drawdownPenalty = absMaxDrawdown * 1.5f;
        report.finalFitness = report.netScore - drawdownPenalty;

        // Khuyến khích nhẹ bot trade nhiều (cộng thêm vài chục điểm để phá vỡ thế hòa)
        report.finalFitness += (report.tradeCount * 0.1f);

        report.note = "SUCCESS";
        return report;
    }
}