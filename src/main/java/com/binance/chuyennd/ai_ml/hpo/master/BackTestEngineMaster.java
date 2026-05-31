package com.binance.chuyennd.ai_ml.hpo.master;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculatorV3;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;

import java.util.TreeMap;

public class BackTestEngineMaster {

    private AIRejectFilter aiRejectFilter;

    // Không cần nhận tham số nữa, AIRejectFilter sẽ đọc trực tiếp từ Configs
    public BackTestEngineMaster() {
        this.aiRejectFilter = new AIRejectFilter();
        // Không gọi setConfig nữa vì AIRejectFilter tự gọi Configs.xxx
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