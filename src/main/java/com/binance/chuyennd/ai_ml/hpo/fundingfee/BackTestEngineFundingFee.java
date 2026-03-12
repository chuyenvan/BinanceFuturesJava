package com.binance.chuyennd.ai_ml.hpo.fundingfee;

import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculator;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;

import java.util.TreeMap;

public class BackTestEngineFundingFee {

    // Đã loại bỏ rateMin2TradeFull (pMinFull)
    public BackTestEngineFundingFee(float rateMin2Trade,
                                    float rateUpAvg,
                                    float rateDownAvg,
                                    float fundingPredMaxThreshold) {
        Configs.PREDICT_SYMBOL_RATE_DOWN_15M = rateMin2Trade;
        Configs.PREDICT_SYMBOL_RATE_UP_AVG = rateUpAvg;
        Configs.PREDICT_SYMBOL_RATE_DOWN_AVG = rateDownAvg;
        Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD = fundingPredMaxThreshold;
    }

    public float run(TreeMap<Long, MarketDataObject> time2MarketData,
                      TreeMap<Long, AiPredictionData> predictionMap,
                      TreeMap<Long, long[]> time2FundingPre) {
        try {
            Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
            BudgetManagerSimple.resetInstance();
            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();

            test.initDataReady(time2MarketData, predictionMap, time2FundingPre, new AIRejectFilter());
            test.simulatorWithInitEntry(startTime, System.currentTimeMillis());

            return HPOFitnessCalculator.evaluateProfitVelocity(test);
        } catch (Exception e) {
            e.printStackTrace();
            return 0.0f;
        }
    }
}