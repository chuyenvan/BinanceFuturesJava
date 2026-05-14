package com.binance.chuyennd.ai_ml.hpo.kaggle;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculator;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.tradecore.CoinRankManager;

import java.util.TreeMap;

public class BackTestEngineOfflineKaggle {

    private AIRejectFilter aiRejectFilter;

    // Chỉ nhận 2 tham số như bản mới
    public BackTestEngineOfflineKaggle(float min15m, float min24h) {
        this.aiRejectFilter = new AIRejectFilter();
        this.aiRejectFilter.setConfig(min15m, min24h);
    }

    public HPOFitnessCalculator.FitnessReport run(TreeMap<Long, MarketDataObject> time2MarketData,
                                                  TreeMap<Long, AiPredictionData> predictionMap,
                                                  TreeMap<Long, long[]> time2FundingPre,
                                                  long startTs, long endTs) {
        try {
            // Đảm bảo các Singleton được dọn sạch trước mỗi Trial
            BudgetManagerSimple.getInstance().resetInstance();
            HistoryManager.getInstance().resetCache();
            CoinRankManager.getInstance().resetCache();

            // 🔥 SỬ DỤNG BẢN SIMULATOR OFFLINE CHUNK (Đọc bằng KaggleDataLoader)
            SimulatorOfflineKaggle test = new SimulatorOfflineKaggle();

            test.initDataReady(time2MarketData, predictionMap, time2FundingPre, aiRejectFilter);

            // Chạy mô phỏng (Ticker sẽ load lazy từ đĩa)
            test.simulate(startTs, endTs);

            // Gửi dữ liệu (allOrderDone) sang Calculator gốc để tính điểm chuẩn xác
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