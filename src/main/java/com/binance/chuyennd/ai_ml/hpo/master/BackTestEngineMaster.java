package com.binance.chuyennd.ai_ml.hpo.master;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculatorV3;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;

import java.util.TreeMap;

public class BackTestEngineMaster {

    private AIRejectFilter aiRejectFilter;

    // Nhận 11 Tham số từ HPO (Đã thêm aiMaxThres)
    public BackTestEngineMaster(float dSmall, float dMed, float dBig, float uSmall, float uMed, float uBig,
                                float d15mSmall,
                                float aiRisk, float ai15m, float ai24h,
                                float aiMaxThres) { // 🔥 THÊM MỚI Ở ĐÂY

        // 1. Gán 7 Ngưỡng Thị trường
        Configs.MS_DOWN_MED_AVG = dMed;
        Configs.MS_DOWN_BIG_AVG = dBig;
        Configs.MS_UP_SMALL_THRES = uSmall;
        Configs.MS_UP_BIG_THRES = uBig;
        Configs.MS_DOWN_15M_SMALL_ONLY = d15mSmall;

        // 2. Gán 4 Ngưỡng AI Filter
        Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD = aiMaxThres; // 🔥 THÊM MỚI Ở ĐÂY

        this.aiRejectFilter = new AIRejectFilter();
        this.aiRejectFilter.setConfig(aiRisk, ai15m, ai24h);
    }
    public HPOFitnessCalculatorV3.FitnessReport run(TreeMap<Long, MarketDataObject> time2MarketData,
                                                    TreeMap<Long, AiPredictionData> predictionMap,
                                                    TreeMap<Long, long[]> time2FundingPre,
                                                    long offlineEndTime) {
        try {
            Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
            BudgetManagerSimple.resetInstance();
            HistoryManager.getInstance().resetCache();
            CoinRankManager.getInstance().resetCache();

            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();
            test.initDataReady(time2MarketData, predictionMap, time2FundingPre, aiRejectFilter);
            test.simulatorWithInitEntry(startTime, offlineEndTime);

            // Dùng Fitness Calculator V2
            return HPOFitnessCalculatorV3.evaluateDetailed(test.allOrderDone);

        } catch (Exception e) {
            e.printStackTrace();
            HPOFitnessCalculatorV3.FitnessReport err = new HPOFitnessCalculatorV3.FitnessReport();
            err.finalFitness = -10000f;
            err.note = "EXCEPTION_ERROR";
            return err;
        }
    }
}