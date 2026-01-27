package com.binance.chuyennd.ai_ml.hpo.market;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.utils.Configs;

import java.util.TreeMap;

public class BackTestEngineMarketThreshold {

    public BackTestEngineMarketThreshold(
            double upBig, double downBigAvg,
            double upMed, double downMedAvg,
            double upSmall, double downSmallAvg,
            double down15mMed, double down15mSmall) {

        // Inject Params vào Configs
        Configs.MS_UP_BIG_THRES = upBig;
        Configs.MS_DOWN_BIG_AVG = downBigAvg;

        Configs.MS_UP_MED_THRES = upMed;
        Configs.MS_DOWN_MED_AVG = downMedAvg;

        Configs.MS_UP_SMALL_THRES = upSmall;
        Configs.MS_DOWN_SMALL_AVG = downSmallAvg;

        Configs.MS_DOWN_15M_MED_ONLY = down15mMed;
        Configs.MS_DOWN_15M_SMALL_ONLY = down15mSmall;

        // Lưu ý: Các chỉ số phụ (BTC threshold, Combined logic...)
        // có thể giữ mặc định hoặc thêm vào gen nếu muốn tối ưu sâu hơn.
    }

    public double run(TreeMap<Long, MarketDataObject> time2MarketData,
                      TreeMap<Long, AiPredictionData> predictionMap) {
        try {
            BudgetManagerSimple.resetInstance();
            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();

            // Init Data Ready (Giả sử bạn đã tích hợp method này từ các bước trước)
            test.initDataReady(time2MarketData, predictionMap, new AIRejectFilter());

            test.simulatorWithInitEntry();
            return BudgetManagerSimple.getInstance().balanceCurrent;
        } catch (Exception e) {
            e.printStackTrace();
            return 0.0;
        }
    }
}