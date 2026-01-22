package com.binance.chuyennd.ai_ml.hpo.fundingfee;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.utils.Configs;

import java.util.TreeMap;

public class BackTestEngineFundingFee {

    public BackTestEngineFundingFee(double rateMin2Trade, double rateMin2TradeFull,
                                    double rateUpAvg, double rateDownAvg) {
        // GÁN GIÁ TRỊ TỪ HPO VÀO CONFIGS
        Configs.FUNDING_RATE_MIN_TRADE = rateMin2Trade;
        Configs.FUNDING_RATE_MIN_TRADE_FULL = rateMin2TradeFull;
        Configs.FUNDING_RATE_UP_AVG = rateUpAvg;
        Configs.FUNDING_RATE_DOWN_AVG = rateDownAvg;
    }

    public double run(TreeMap<Long, MarketDataObject> time2MarketData,
                       TreeMap<Long, AiPredictionData> predictionMap) {
        try {
            // Reset Budget
            BudgetManagerSimple.resetInstance();

            // Gọi Simulator Gốc (Nó sẽ tự dùng Configs mới)
            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();

            test.initDataReady(time2MarketData,
                    predictionMap, new AIRejectFilter());

            test.simulatorWithInitEntry(); // Hàm này gọi MarketBigChangeDetector -> Lấy Configs mới

            return BudgetManagerSimple.getInstance().balanceCurrent;

        } catch (Exception e) {
            e.printStackTrace();
            return 0.0;
        }
    }
}