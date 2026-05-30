//package com.binance.chuyennd.ai_ml.hpo;
//
//import com.binance.chuyennd.ai_ml.onnx.entry.AiPredictionData;
//import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
//import com.binance.chuyennd.object.MarketDataObject;
//import com.binance.chuyennd.research.BudgetManagerSimple;
//import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
//import com.binance.chuyennd.utils.Configs;
//import com.binance.chuyennd.utils.Utils;
//
//import java.util.TreeMap;
//
//public class BackTestEngineAIMarket {
//
//    public AIRejectFilter aiRejectFilter;
//
//    public BackTestEngineAIMarket(float risk, float minRet1H, float highRet,
//                                  float minMom15M, float minTrend4H, float deadTrend24H) {
//        aiRejectFilter = new AIRejectFilter();
//        aiRejectFilter.setConfig(risk,  minMom15M, deadTrend24H);
//    }
//
//    public float run(TreeMap<Long, MarketDataObject> time2MarketData,
//                      TreeMap<Long, AiPredictionData> predictionMap,
//                      TreeMap<Long, long[]> time2FundingPre) {
//        try {
//            Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
//            BudgetManagerSimple.resetInstance();
//            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();
//
//            test.initDataReady(time2MarketData, predictionMap, time2FundingPre, aiRejectFilter);
//            test.simulatorWithInitEntry(startTime, System.currentTimeMillis());
//
//            return BudgetManagerSimple.getInstance().balanceCurrent;
//
//        } catch (Exception e) {
//            return -100000.0f;
//        }
//    }
//
//
//}