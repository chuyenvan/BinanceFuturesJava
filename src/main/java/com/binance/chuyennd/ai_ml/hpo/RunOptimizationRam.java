//package com.binance.chuyennd.ai_ml.hpo;
//
//import com.binance.chuyennd.ai_ml.onnx.entry.AiPredictionData;
//import com.binance.chuyennd.ai_ml.v3.AiPredictionDataV3;
//import com.binance.chuyennd.bigchange.market.MarketDataObject;
//import com.binance.chuyennd.object.MarketRateChange;
//import com.binance.chuyennd.research.FundingFeeManager;
//import com.binance.chuyennd.utils.Configs;
//import com.binance.chuyennd.utils.StorageSnappy;
//import org.slf4j.Logger;
//import org.slf4j.LoggerFactory;
//
//import java.util.Map;
//import java.util.Set;
//import java.util.TreeMap;
//import java.util.concurrent.ConcurrentHashMap;
//
//public class RunOptimizationRam {
//
//    private static final Logger LOG = LoggerFactory.getLogger(RunOptimizationRam.class);
//
//    // CACHE DU LIEU TOAN CUC
//    public static TreeMap<Long, MarketDataObject> time2MarketData;
//    public static TreeMap<Long, MarketRateChange> time2MarketRateChange;
//    public static TreeMap<Long, Double> time2BtcReverse;
//    public static TreeMap<Long, AiPredictionDataV4> predictionMap;
//    public static ConcurrentHashMap<Long, Set<String>> CACHED_time2FundingFeeTrade;
//
//
//    public static void main(String[] args) {
//        LOG.info("=== BAT DAU KIEM TRA TINH NHAT QUAN (3 RUNS) ===");
//
//        // =========================================================================
//        // 1. LOAD DATA VAO RAM
//        // =========================================================================
//        try {
//            LOG.info("Dang tai du lieu tu o cung (Disk)...");
//
//            CACHED_time2FundingFeeTrade = (ConcurrentHashMap<Long, Set<String>>) StorageSnappy.readObjectFromFile(FundingFeeManager.FILE_FUNDING_FEE);
//            time2MarketRateChange = (TreeMap<Long, MarketRateChange>) StorageSnappy.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);
//            time2MarketData = (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
//            time2BtcReverse = (TreeMap<Long, Double>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_BTC_REVERSE);
//            predictionMap = (TreeMap<Long, AiPredictionDataV3>) StorageSnappy.readObjectFromFile(Configs.FILE_AI_PREDICTIONS);
//
//            FundingFeeManager.getInstance();
//
//            LOG.info("Tai du lieu HOAN THANH. Bat dau xu ly...");
//
//        } catch (Exception e) {
//            LOG.error("LOI NGHIE TRONG KHI LOAD DATA!", e);
//            return;
//        }
//
//        // =========================================================================
//        // 2. CHAY TEST KIEM TRA TINH NHAT QUAN
//        // =========================================================================
//
//        double fixRisk = -0.05;
//        double fixMinRet1H = 0.015;
//        double fixMinMom15M = 0.002;
//        double fixMinTrend4H = 0.005;
//        double fixHighRet = 0.04;
//        double fixDeadTrend = -0.05;
//
//        LOG.info("--------------------------------------------------");
//        LOG.info("BAT DAU TEST 3 LAN VOI CUNG THAM SO");
//        LOG.info("Muc tieu: Profit cua 3 lan chay PHAI GIONG HET NHAU");
//        LOG.info("Params: Risk={}, Ret1H={}", fixRisk, fixMinRet1H);
//        LOG.info("--------------------------------------------------");
//
//        for (int i = 1; i <= 3; i++) {
//            LOG.info(">>> LAN CHAY #{} BAT DAU...", i);
//            long startRun = System.currentTimeMillis();
//
//            try {
//                // Tao Engine moi moi lan chay
//                BackTestEngineAI engine = new BackTestEngineAI(
//                        fixRisk, fixMinRet1H, fixHighRet, fixMinMom15M, fixMinTrend4H, fixDeadTrend
//                );
//
//                // Chay Backtest
//                double profit = engine.run(
//                        time2MarketData,
//                        time2MarketRateChange,
//                        time2BtcReverse,
//                        predictionMap
//                );
//
//                long duration = System.currentTimeMillis() - startRun;
//                LOG.info(">>> LAN CHAY #{} KET THUC. Profit: {} | Thoi gian: {} ms", i, String.format("%.4f", profit), duration);
//
//            } catch (Exception e) {
//                e.printStackTrace();
//                LOG.error("LAN CHAY #" + i + " THAT BAI!", e);
//            }
//        }
//
//        LOG.info("--------------------------------------------------");
//        LOG.info("KET QUA KIEM TRA:");
//        LOG.info("- Neu 3 so Profit tren KHAC NHAU -> Loi o Simulator (Static Var).");
//        LOG.info("- Neu 3 so Profit tren GIONG NHAU -> He thong on dinh.");
//
//        // =========================================================================
//        // 3. LOG RAM (Tieng Viet khong dau)
//        // =========================================================================
//        Runtime runtime = Runtime.getRuntime();
//        long usedMemory = (runtime.totalMemory() - runtime.freeMemory()) / (1024 * 1024);
//        long totalMemory = runtime.totalMemory() / (1024 * 1024);
//
//        LOG.info("--------------------------------------------------");
//        LOG.info("THONG TIN RAM HE THONG:");
//        LOG.info(" RAM dang dung (Used)   : {} MB", usedMemory);
//        LOG.info(" Tong RAM cap phat (JVM): {} MB", totalMemory);
//        LOG.info("--------------------------------------------------");
//    }
//}