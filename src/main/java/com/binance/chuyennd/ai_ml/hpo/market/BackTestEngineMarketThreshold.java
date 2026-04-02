package com.binance.chuyennd.ai_ml.hpo.market;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;

import java.util.TreeMap;

public class BackTestEngineMarketThreshold {

    public BackTestEngineMarketThreshold(float baseDown, float ratioDown, float baseUp, float ratioUp) {
        // Gán 4 tham số Geometric (Cấp số nhân) vào Configs
        Configs.BASE_DOWN = baseDown;
        Configs.RATIO_DOWN = ratioDown;
        Configs.BASE_UP = baseUp;
        Configs.RATIO_UP = ratioUp;
    }

    public float run(TreeMap<Long, MarketDataObject> time2MarketData,
                     TreeMap<Long, AiPredictionData> predictionMap,
                     TreeMap<Long, long[]> time2FundingPre) {
        try {
            BudgetManagerSimple.resetInstance();
            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();

            test.initDataReady(time2MarketData, predictionMap, time2FundingPre, new AIRejectFilter());
            Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
            test.simulatorWithInitEntry(startTime, System.currentTimeMillis());
            return BudgetManagerSimple.getInstance().balanceCurrent;
        } catch (Exception e) {
            e.printStackTrace();
            return 0.0f;
        }
    }
}