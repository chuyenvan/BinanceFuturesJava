package com.binance.chuyennd.ai_ml.hpo.fundingfee;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.utils.Configs;

import java.util.Map;
import java.util.TreeMap;

public class BackTestEngineFundingFee {

    // 🔥 THÊM THAM SỐ THỨ 5
    public BackTestEngineFundingFee(double rateMin2Trade, double rateMin2TradeFull,
                                    double rateUpAvg, double rateDownAvg, double fundingPredMaxThreshold) {

        Configs.PREDICT_SYMBOL_RATE_DOWN_15M = rateMin2Trade;
        Configs.PREDICT_SYMBOL_RATE_DOWN_15M = rateMin2TradeFull;
        Configs.PREDICT_SYMBOL_RATE_UP_AVG = rateUpAvg;
        Configs.PREDICT_SYMBOL_RATE_DOWN_AVG = rateDownAvg;
        Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD = fundingPredMaxThreshold; // Nhận biến mới
    }

    // 🔥 THÊM time2FundingPre VÀO HÀM RUN
    public double run(TreeMap<Long, MarketDataObject> time2MarketData,
                      TreeMap<Long, AiPredictionData> predictionMap,
                      TreeMap<Long, Map<Short, float[]>> time2FundingPre) {
        try {
            BudgetManagerSimple.resetInstance();
            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();

            // 🔥 TRUYỀN ĐỦ 3 MAP VÀO
            test.initDataReady(time2MarketData, predictionMap, time2FundingPre, new AIRejectFilter());
            test.simulatorWithInitEntry();

            return BudgetManagerSimple.getInstance().balanceCurrent;
        } catch (Exception e) {
            e.printStackTrace();
            return 0.0;
        }
    }
}