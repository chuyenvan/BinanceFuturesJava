package com.binance.chuyennd.ai_ml.hpo.kaggle;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculator;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.tradecore.CoinRankManager;

import java.util.TreeMap;

public class BackTestEngineOfflineKaggle {

    private AIRejectFilter aiRejectFilter;

    public BackTestEngineOfflineKaggle(float min15m, float min24h) {
        this.aiRejectFilter = new AIRejectFilter();
        this.aiRejectFilter.setConfig(min15m, min24h);
    }

    public HPOFitnessCalculator.FitnessReport run(TreeMap<Long, MarketDataObject> time2MarketData,
                                                  TreeMap<Long, AiPredictionData> predictionMap,
                                                  TreeMap<Long, long[]> time2FundingPre,
                                                  long startTs, long endTs) {
        try {
            // Reset global managers before running simulation
            BudgetManagerSimple.getInstance().resetInstance();
            HistoryManager.getInstance().resetCache();
            CoinRankManager.getInstance().resetCache();

            // Use the offline simulator
            SimulatorOfflineKaggle test = new SimulatorOfflineKaggle();

            test.initDataReady(time2MarketData, predictionMap, time2FundingPre, aiRejectFilter);
            test.simulate(startTs, endTs);

            // Pass the completed offline simulator to the original HPOFitnessCalculator.
            // Since SimulatorOfflineKaggle maintains `allOrderDone` now, this will work perfectly.
            return HPOFitnessCalculator.evaluateDetailed(test.allOrderDone);

        } catch (Exception e) {
            e.printStackTrace();
            HPOFitnessCalculator.FitnessReport err = new HPOFitnessCalculator.FitnessReport();
            err.finalFitness = -10000f;
            err.note = "EXCEPTION_ERROR";
            return err;
        }
    }
}