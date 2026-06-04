package com.binance.chuyennd.ai_ml.hpo.kaggle;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculator;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;

import java.util.TreeMap;

public class BackTestEngineMarketThresholds {

    private AIRejectFilter aiRejectFilter;

    // Khởi tạo Engine với 6 tham số thị trường
    public BackTestEngineMarketThresholds(float dSmall, float dMed, float dBig, float uSmall, float uMed, float uBig) {
        // 1. Ép 6 tham số vào Configs hệ thống (Biến Static)
        Configs.MS_DOWN_SMALL_AVG_OR_15M = dMed;
        Configs.MS_DOWN_BIG_AVG = dBig;

        Configs.MS_UP_SMALL_THRES = uSmall;

        Configs.MS_UP_BIG_THRES = uBig;

        // 2. KHÓA CỨNG BỘ LỌC AI (Dùng thông số chuẩn bác đang có để làm nền tảng)
        // Bác có thể tự thay đổi 3 số này theo bộ gen AI tốt nhất bác từng chạy ra
        this.aiRejectFilter = new AIRejectFilter();
        this.aiRejectFilter.setConfig(-0.1f, 0.015f);
    }

    public HPOFitnessCalculator.FitnessReport run(TreeMap<Long, MarketDataObject> time2MarketData,
                                                  TreeMap<Long, AiPredictionData> predictionMap,
                                                  TreeMap<Long, long[]> time2FundingPre,
                                                  long offlineEndTime) {
        try {
            Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;

            // Xóa rác
            BudgetManagerSimple.resetInstance();
            HistoryManager.getInstance().resetCache();
            CoinRankManager.getInstance().resetCache();

            // Chạy Simulator
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