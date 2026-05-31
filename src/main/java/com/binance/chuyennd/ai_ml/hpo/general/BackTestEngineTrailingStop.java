package com.binance.chuyennd.ai_ml.hpo.general;

import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculator;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;

import java.util.TreeMap;

public class BackTestEngineTrailingStop {

    public BackTestEngineTrailingStop(float baseRate, float dynamicK, float profitMultiplier) {
        Configs.RATE_PROFIT_STOP_MARKET = baseRate;
        Configs.TS_DYNAMIC_K = dynamicK;
        Configs.TS_PROFIT_MULTIPLIER = profitMultiplier;
    }

    public HPOFitnessCalculator.FitnessReport run(TreeMap<Long, MarketDataObject> time2MarketData,
                                                  TreeMap<Long, AiPredictionData> predictionMap,
                                                  TreeMap<Long, long[]> time2FundingPre) {
        try {
            Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
            BudgetManagerSimple.resetInstance();
            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();

            test.initDataReady(time2MarketData, predictionMap, time2FundingPre, new AIRejectFilter());

            test.simulatorWithInitEntry(startTime, System.currentTimeMillis());

            // Trả về báo cáo chi tiết thay vì chỉ trả về balanceCurrent
            return HPOFitnessCalculator.evaluateDetailed(test);
        } catch (Exception e) {
            e.printStackTrace();
            HPOFitnessCalculator.FitnessReport err = new HPOFitnessCalculator.FitnessReport();
            err.finalFitness = -10000f;
            err.note = "EXCEPTION_ERROR";
            return err;
        }
    }
}