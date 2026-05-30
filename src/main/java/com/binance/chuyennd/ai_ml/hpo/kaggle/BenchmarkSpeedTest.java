//package com.binance.chuyennd.ai_ml.hpo.kaggle;
//
//import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculatorV3;
//import com.binance.chuyennd.ai_ml.onnx.entry.AiPredictionData;
//import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
//import com.binance.chuyennd.object.MarketDataObject;
//import com.binance.chuyennd.research.BudgetManagerSimple;
//import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
//import com.binance.chuyennd.utils.Configs;
//import com.binance.chuyennd.utils.Utils;
//import org.slf4j.Logger;
//import org.slf4j.LoggerFactory;
//
//import java.util.TreeMap;
//
//public class BenchmarkSpeedTest {
//    private static final Logger LOG = LoggerFactory.getLogger(BenchmarkSpeedTest.class);
//
//    public static void main(String[] args) {
//        try {
//            LOG.info("=== BẮT ĐẦU BENCHMARK THUẦN (KIỂM TRA LOGIC & TỐC ĐỘ) ===");
//
//            // 1. Cấu hình chạy thuần (Tắt HPO để in log Balance mỗi ngày)
//            Configs.IS_HPO_MODE = false; // 🔥 QUAN TRỌNG: Để false mới in log chi tiết
//            Configs.IS_KAGGLE_MODE = true;
//            Configs.TIME_RUN = "20251001";
//            long offlineEndTime = Utils.sdfFile.parse("20260430").getTime() + (24 * Utils.TIME_HOUR) - Utils.TIME_MINUTE;
//
//            // Nạp thông số "Cứng" để test logic
//            Configs.MS_DOWN_SMALL_AVG = -0.01214f;
//            Configs.MS_DOWN_MED_AVG = -0.02658f;
//            Configs.MS_DOWN_BIG_AVG = -0.04165f;
//            Configs.MS_UP_SMALL_THRES = 0.00897f;
//            Configs.MS_UP_MED_THRES = 0.03801f;
//            Configs.MS_UP_BIG_THRES = 0.07208f;
//            Configs.MS_DOWN_15M_SMALL_ONLY = -0.03283f;
//            Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD = 0.15f; // Ngưỡng AI Funding
//
//            AIRejectFilter aiFilter = new AIRejectFilter();
//            aiFilter.setConfig(-0.16107f, 0.02282f, 0.02513f);
//
//            // 2. Load Dữ liệu
//            LOG.info("Đang nạp dữ liệu Kaggle/Aerospike vào RAM...");
//            TreeMap<Long, MarketDataObject> time2MarketData = KaggleDataLoader.loadMarketData();
//            TreeMap<Long, AiPredictionData> predictionMap = KaggleDataLoader.loadAiPred();
//            TreeMap<Long, long[]> time2FundingPre = KaggleDataLoader.loadFundingPred();
//
//            // 4. Khởi tạo Simulator độc lập
//            Long startTimeSimulator = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
//            BudgetManagerSimple.resetInstance();
//            HistoryManager.getInstance().resetCache();
//            CoinRankManager.getInstance().resetCache();
//
//            SimulatorMarketLevelTicker1MStopLoss simulator = new SimulatorMarketLevelTicker1MStopLoss();
//            simulator.initDataReady(time2MarketData, predictionMap, time2FundingPre, aiFilter);
//
//            // 5. Chạy test và đo thời gian
//            LOG.info("🚀 Bắt đầu Simulator chạy thuần (In Log chi tiết)...");
//            long startMs = System.currentTimeMillis();
//
//            simulator.simulatorWithInitEntry(startTimeSimulator, offlineEndTime);
//
//            long duration = System.currentTimeMillis() - startMs;
//
//            // In kết quả
//            LOG.info("=================================================");
//            LOG.info("✅ HOÀN TẤT BENCHMARK!");
//            LOG.info("⏱️ THỜI GIAN CHẠY: {} ms", duration);
//            LOG.info("📦 TỔNG SỐ LỆNH ĐÃ ĐÓNG: {}", simulator.allOrderDone.size());
//            LOG.info("📦 Profit: {}", HPOFitnessCalculatorV3.evaluateDetailed(simulator.allOrderDone).totalProfit);
//            LOG.info("=================================================");
//
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
//    }
//
//
//}