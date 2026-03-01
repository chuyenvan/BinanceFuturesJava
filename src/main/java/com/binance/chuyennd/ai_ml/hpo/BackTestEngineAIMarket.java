package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;

import java.util.Calendar;
import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;

public class BackTestEngineAIMarket {

    public AIRejectFilter aiRejectFilter;

    private static final double BASELINE_2021 = 81615.0;
    private static final double BASELINE_2022 = 19157.0;
    private static final double BASELINE_2023 = 14929.0;
    private static final double BASELINE_2024 = 33234.0;
    private static final double BASELINE_2025 = 26037.0;

    public BackTestEngineAIMarket(double risk, double minRet1H, double highRet,
                                  double minMom15M, double minTrend4H, double deadTrend24H) {
        aiRejectFilter = new AIRejectFilter();
        aiRejectFilter.setConfig(risk, minRet1H, highRet, minMom15M, minTrend4H, deadTrend24H);
    }

    public double run(TreeMap<Long, MarketDataObject> time2MarketData,
                      TreeMap<Long, AiPredictionData> predictionMap,
                      TreeMap<Long, long[]> time2FundingPre) {
        try {
            BudgetManagerSimple.resetInstance();
            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();

            test.initDataReady(time2MarketData, predictionMap, time2FundingPre, aiRejectFilter);
            test.simulatorWithInitEntry();

            return BudgetManagerSimple.getInstance().balanceCurrent;

        } catch (Exception e) {
            return -100000.0;
        }
    }

    private double calculateAdvancedFitness(SimulatorMarketLevelTicker1MStopLoss simulator) {
        Map<Integer, Double> yearProfits = new HashMap<>();
        yearProfits.put(2021, 0.0);
        yearProfits.put(2022, 0.0);
        yearProfits.put(2023, 0.0);
        yearProfits.put(2024, 0.0);
        yearProfits.put(2025, 0.0);

        Calendar cal = Calendar.getInstance();
        for (OrderTargetInfoTest order : simulator.allOrderDone.values()) {
            cal.setTimeInMillis(order.timeUpdate);
            int year = cal.get(Calendar.YEAR);
            yearProfits.put(year, yearProfits.getOrDefault(year, 0.0) + order.calTp());
        }

        double p21 = yearProfits.get(2021);
        double p22 = yearProfits.get(2022);
        double p23 = yearProfits.get(2023);
        double p24 = yearProfits.get(2024);
        double p25 = yearProfits.get(2025);

        if (p21 < 0 || p22 < 0 || p23 < 0 || p24 < 0 || p25 < 0) {
            return -50000.0 + (p21 + p22 + p23 + p24 + p25);
        }

        double score = 0;
        score += evaluateYear(p21, BASELINE_2021);
        score += evaluateYear(p22, BASELINE_2022);
        score += evaluateYear(p23, BASELINE_2023);
        score += evaluateYear(p24, BASELINE_2024);
        score += evaluateYear(p25, BASELINE_2025);

        if (p21 > 0.9 * BASELINE_2021 && p22 > 0.9 * BASELINE_2022 &&
                p23 > 0.9 * BASELINE_2023 && p24 > 0.9 * BASELINE_2024 && p25 > 0.9 * BASELINE_2025) {
            score += 20000;
        }

        if (p23 > BASELINE_2023) {
            score += (p23 - BASELINE_2023) * 2;
        }

        return score;
    }

    private double evaluateYear(double actual, double baseline) {
        double diff = actual - baseline;
        if (diff >= 0) {
            return actual;
        } else {
            return actual - (Math.abs(diff) * 1.5);
        }
    }
}