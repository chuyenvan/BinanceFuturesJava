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

    // 🔥 PHỤC HỒI 3 THAM SỐ
    public BackTestEngineFundingFee(float risk, float min15m, float min24h) {
        this.aiRejectFilter = new AIRejectFilter();
        this.aiRejectFilter.setConfig(risk, min15m, min24h);
    }

    public HPOFitnessCalculator.FitnessReport run(TreeMap<Long, MarketDataObject> time2MarketData,
                                                  TreeMap<Long, AiPredictionData> predictionMap,
                                                  TreeMap<Long, long[]> time2FundingPre,
                                                  long offlineEndTime) {
        try {
            Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
            BudgetManagerSimple.resetInstance();
            HistoryManager.getInstance().resetCache();
            CoinRankManager.getInstance().resetCache();

            // DÙNG SIMULATOR GỐC (Bản đã được bác tối ưu tốc độ siêu nhanh)
            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();

            test.initDataReady(time2MarketData, predictionMap, time2FundingPre, aiRejectFilter);
            test.simulatorWithInitEntry(startTime, offlineEndTime);

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