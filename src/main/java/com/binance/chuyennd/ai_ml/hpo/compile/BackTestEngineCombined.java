package com.binance.chuyennd.ai_ml.hpo.compile;

import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculator;
import com.binance.chuyennd.ai_ml.onnx.entry.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;

import java.util.TreeMap;

public class BackTestEngineCombined {

    public AIRejectFilter aiRejectFilter;

    public BackTestEngineCombined(
            // --- 4 Tham số Funding Fee / Tín hiệu Entry ---
            float rateMin2Trade,
            float rateUpAvg,
            float rateDownAvg,
            float fundingPredMaxThreshold,

            // --- 6 Tham số AI Reject Filter ---
            float risk,
            float minRet1H,
            float highRet,
            float minMom15M,
            float minTrend4H,
            float deadTrend24H,

            // --- 2 Tham số DYNAMIC MARKET MỚI ---
            float dynKDown,
            float dynKUp) {

        // 1. Gán tham số Tín hiệu vào Configs
        Configs.PREDICT_SYMBOL_RATE_DOWN_15M = rateMin2Trade;
        Configs.PREDICT_SYMBOL_RATE_UP_AVG = rateUpAvg;
        Configs.PREDICT_SYMBOL_RATE_DOWN_AVG = rateDownAvg;
        Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD = fundingPredMaxThreshold;

        // 2. Gán 2 tham số Dynamic Market mới vào Configs

        // 3. Khởi tạo và gán tham số cho AI Reject Filter
        aiRejectFilter = new AIRejectFilter();
        aiRejectFilter.setConfig(risk,  minMom15M, deadTrend24H);
    }

    public float run(TreeMap<Long, MarketDataObject15M> time2MarketData,
                     TreeMap<Long, AiPredictionData> predictionMap,
                     TreeMap<Long, long[]> time2FundingPre) {
        try {
            Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
            BudgetManagerSimple.resetInstance();

            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();

            // Truyền time2FundingPre và aiRejectFilter vào Simulator
            test.initDataReady(time2MarketData, predictionMap, time2FundingPre, aiRejectFilter);
            test.simulatorWithInitEntry(startTime, System.currentTimeMillis());

            // Chấm điểm
            return HPOFitnessCalculator.evaluateProfitVelocity(test);
        } catch (Exception e) {
            e.printStackTrace();
            return -1000000f; // Điểm âm nặng để loại bỏ Gen lỗi
        }
    }
}