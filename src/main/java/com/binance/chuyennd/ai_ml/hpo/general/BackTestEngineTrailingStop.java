package com.binance.chuyennd.ai_ml.hpo.general;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.utils.Configs;

import java.util.Map;
import java.util.TreeMap;

public class BackTestEngineTrailingStop {

    public BackTestEngineTrailingStop(
            double baseRate,
            double volHighThres, double rateHigh,
            double volMedThres, double rateMed,
            double volLowThres, double rateLow) {

        Configs.RATE_PROFIT_STOP_MARKET = baseRate;

        Configs.TS_VOL_HIGH_THRES = volHighThres;
        Configs.TS_VOL_MED_THRES = volMedThres;
        Configs.TS_VOL_LOW_THRES = volLowThres;

        Configs.TS_RATE_HIGH = rateHigh;
        Configs.TS_RATE_MED = rateMed;
        Configs.TS_RATE_LOW = rateLow;
    }

    public double run(TreeMap<Long, MarketDataObject> time2MarketData,
                      TreeMap<Long, AiPredictionData> predictionMap,
                      TreeMap<Long, long[]> time2FundingPre) {
        try {
            BudgetManagerSimple.resetInstance();
            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();

            test.initDataReady(time2MarketData, predictionMap, time2FundingPre, new AIRejectFilter());

            test.simulatorWithInitEntry();
            return BudgetManagerSimple.getInstance().balanceCurrent;
        } catch (Exception e) {
            e.printStackTrace();
            return 0.0;
        }
    }
}