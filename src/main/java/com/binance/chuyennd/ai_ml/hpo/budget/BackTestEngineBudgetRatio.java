package com.binance.chuyennd.ai_ml.hpo.budget;

import com.binance.chuyennd.ai_ml.onnx.entry.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;

import java.util.TreeMap;

public class BackTestEngineBudgetRatio {

    public BackTestEngineBudgetRatio(
            float budgetRatio1, float budgetDivider1,
            float budgetRatio2, float budgetDivider2) {

        Configs.BUDGET_MARGIN_RATIO_1 = budgetRatio1;
        Configs.BUDGET_DIVIDER_1 = budgetDivider1;
        Configs.BUDGET_MARGIN_RATIO_2 = budgetRatio2;
        Configs.BUDGET_DIVIDER_2 = budgetDivider2;
    }

    public float run(TreeMap<Long, MarketDataObject15M> time2MarketData,
                      TreeMap<Long, AiPredictionData> predictionMap,
                      TreeMap<Long, long[]> time2FundingPre) {
        try {
            Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
            BudgetManagerSimple.resetInstance();
            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();

            test.initDataReady(time2MarketData, predictionMap, time2FundingPre, new AIRejectFilter());
            test.simulatorWithInitEntry(startTime, System.currentTimeMillis());

        } catch (Exception e) {
            e.printStackTrace();
            return 0.0f;
        }

        return BudgetManagerSimple.getInstance().balanceCurrent;
    }
}