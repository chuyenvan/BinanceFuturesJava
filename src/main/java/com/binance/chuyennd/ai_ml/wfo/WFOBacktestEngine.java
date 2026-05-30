//package com.binance.chuyennd.ai_ml.wfo;
//
//import com.binance.chuyennd.tradecore.BotTradingConfig;
//import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculator;
//import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
//import com.binance.chuyennd.research.*;
//import com.binance.chuyennd.utils.Utils;
//
//import java.util.TreeMap;
//
//public class WFOBacktestEngine {
//    public static float run(long start, long end, BotTradingConfig config) {
//        try {
//            BudgetManagerSimple.resetInstance();
//
//            // 1. Lấy dữ liệu từ RAM Cache [cite: 719-720]
//            int durationMins = (int) ((end - start) / Utils.TIME_MINUTE);
//
//            // 2. Khởi tạo Simulator GỐC
//            SimulatorMarketLevelTicker1MStopLoss simulator = new SimulatorMarketLevelTicker1MStopLoss();
//
//            // 3. Đấu nối Config và Dữ liệu
//            simulator.setConfig(config);
//            simulator.initDataReady(
//                    DataManager.getMarketData(),
//                    DataManager.getAiPredictionData(),
//                    DataManager.getFundingPredictionData(start, durationMins),
//                    new AIRejectFilter()
//            );
//
//            // 4. Thực thi mô phỏng
//            simulator.simulatorWithInitEntry(start, end);
//
//            return HPOFitnessCalculator.evaluateProfitVelocity(simulator);
//        } catch (Exception e) {
//            return -100000.0f;
//        }
//    }
//}