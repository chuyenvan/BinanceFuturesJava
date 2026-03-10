package com.binance.chuyennd.ai_ml.wfo;

import com.binance.chuyennd.research.*;
import com.binance.chuyennd.tradecore.BotTradingConfig;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculator;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.utils.Utils;
import java.util.TreeMap;

public class WFOBacktestEngine {

    public static double run(long start, long end, BotTradingConfig config) {
        try {
            // 1. Reset trạng thái vốn [cite: 703]
            BudgetManagerSimple.resetInstance();
            SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
            sim.setConfig(config);

            // 2. Nạp dữ liệu từ RAM thông qua DataManager [cite: 718, 719, 720]
            int durationMins = (int) ((end - start) / Utils.TIME_MINUTE);
            sim.initDataReady(
                    DataManager.getMarketData(),
                    DataManager.getAiPredictionData(),
                    DataManager.getFundingPredictionData(start, durationMins),
                    new AIRejectFilter()
            );

            // 3. Chạy backtest trượt theo thời gian [cite: 760, 788]
            sim.simulatorWithInitEntry();

            // 4. Chấm điểm [cite: 284, 285]
            return HPOFitnessCalculator.evaluateProfitVelocity(sim);
        } catch (Exception e) {
            return -100000.0;
        }
    }
}