package com.binance.chuyennd.ai_ml.hpo.fundingfee;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculator;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;

import java.util.TreeMap;

public class BackTestEngineFundingFee {

    private AIRejectFilter aiRejectFilter;

    // 🔥 CHỈ CÒN NHẬN 2 THAM SỐ
    public BackTestEngineFundingFee(float min15m, float min24h) {
        this.aiRejectFilter = new AIRejectFilter();
        this.aiRejectFilter.setConfig(min15m, min24h);
    }

    public HPOFitnessCalculator.FitnessReport run(TreeMap<Long, MarketDataObject> time2MarketData,
                                                  TreeMap<Long, AiPredictionData> predictionMap,
                                                  TreeMap<Long, long[]> time2FundingPre) {
        try {
            Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
            BudgetManagerSimple.getInstance().resetInstance(); // Gọi instance chuẩn
            HistoryManager.getInstance().resetCache();
            CoinRankManager.getInstance().resetCache();
            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();

            test.initDataReady(time2MarketData, predictionMap, time2FundingPre, aiRejectFilter);
            test.simulatorWithInitEntry(startTime, System.currentTimeMillis());

            return HPOFitnessCalculator.evaluateDetailed(test);

        } catch (Exception e) {
            e.printStackTrace();
            HPOFitnessCalculator.FitnessReport err = new HPOFitnessCalculator.FitnessReport();
            err.finalFitness = -10000f;
            err.note = "EXCEPTION_ERROR";
            return err;
        }
    }

    // PHƯƠNG THỨC MỚI DÀNH CHO OFFLINE/KAGGLE (END TIME LIMIT)
    public HPOFitnessCalculator.FitnessReport run(TreeMap<Long, MarketDataObject> time2MarketData,
                                                  TreeMap<Long, AiPredictionData> predictionMap,
                                                  TreeMap<Long, long[]> time2FundingPre,
                                                  long endTime) {
        try {
            Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
            BudgetManagerSimple.getInstance().resetInstance();
            HistoryManager.getInstance().resetCache();
            CoinRankManager.getInstance().resetCache();
            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();

            test.initDataReady(time2MarketData, predictionMap, time2FundingPre, aiRejectFilter);
            test.simulatorWithInitEntry(startTime, endTime);

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