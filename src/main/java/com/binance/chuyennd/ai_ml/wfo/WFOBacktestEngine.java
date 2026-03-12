package com.binance.chuyennd.ai_ml.wfo;

import com.binance.chuyennd.tradecore.BotTradingConfig;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculator;
import com.binance.chuyennd.research.BudgetManagerSimple;

public class WFOBacktestEngine {
    public static double run(long start, long end, BotTradingConfig config) {
        try {
            BudgetManagerSimple.resetInstance();

            // Khởi tạo Class Simulator mới dành riêng cho WFO
            WFOSimulator simulator = new WFOSimulator(config);

            // Thực thi mô phỏng trong dải thời gian yêu cầu
            simulator.run(start, end);

            // Tính điểm Fitness để Jenetics tối ưu
            return HPOFitnessCalculator.evaluateProfitVelocity(simulator);
        } catch (Exception e) {
            return -100000.0;
        }
    }
}