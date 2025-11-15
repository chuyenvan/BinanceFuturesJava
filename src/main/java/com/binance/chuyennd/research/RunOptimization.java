//package com.binance.chuyennd.research;
//
//import com.binance.chuyennd.aerospike.DataManagerAerospike;
//import com.binance.chuyennd.ai_ml.extractor.DataContext;
//import com.binance.chuyennd.research.FundingFeeManager;
//import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
//import org.slf4j.Logger;
//import org.slf4j.LoggerFactory;
//
//// === IMPORT MOI CHO ONNX ===
//import ai.onnxruntime.OrtEnvironment;
//import ai.onnxruntime.OrtSession;
//// ==========================
//
///**
// * LOP CHAY CHINH (MAIN CLASS)
// * Phien ban V17: Chay Backtest voi Model AI (thay the HPO/Jenetics)
// * Model AI se duoc dung lam "Bo loc Chat luong" (AI Checker).
// */
//public class RunOptimization {
//
//    public static final Logger LOG = LoggerFactory.getLogger(RunOptimization.class);
//
//    // === MODEL ONNX (MOI) ===
//    // (Cac bien static Cache data (DataContext, ...) giu nguyen)
//    public static OrtEnvironment ONNX_ENV;
//    public static OrtSession MODEL_PNL;      // Model du doan PnL
//    public static OrtSession MODEL_DRAWDOWN; // Model du doan Drawdown
//
//    // Duong dan den file model ban vua tao (phai chinh xac)
//    private static final String PATH_PNL = "../storage/ai_ml/dl4j/Model_PnL.onnx";
//    private static final String PATH_DD = "../storage/ai_ml/dl4j/Model_Drawdown.onnx";
//
//
//    public static void main(String[] args) {
//
//        LOG.info("BAT DAU CHAY BACKTEST VOI AI CHECKER (V17)...");
//
//        try {
//            // --- BUOC 1: TAI TAT CA DU LIEU "STATIC" VAO CACHE (6GB RAM) ---
//            LOG.info("Dang tai du lieu tinh (BTC, ETH, Trend, MarketData) vao DataContext...");
//            DataContext.loadAllStaticData();
//            LOG.info("Tai du lieu static thanh cong.");
//
//            // (Tai cac cache khac neu can)
//            FundingFeeManager.getInstance();
//            LOG.info("Tai FundingFee thanh cong.");
//
//            // --- BUOC 2: TAI 2 MODEL ONNX ---
//            LOG.info("Tai model ONNX PnL tu: {}", PATH_PNL);
//            LOG.info("Tai model ONNX Drawdown tu: {}", PATH_DD);
//
//            ONNX_ENV = OrtEnvironment.getEnvironment();
//            OrtSession.SessionOptions options = new OrtSession.SessionOptions();
//
//            MODEL_PNL = ONNX_ENV.createSession(PATH_PNL, options);
//            MODEL_DRAWDOWN = ONNX_ENV.createSession(PATH_DD, options);
//
//            LOG.info("Tai 2 model ONNX thanh cong.");
//
//            // --- BUOC 3: KHOI DONG SIMULATOR ---
//            LOG.info("Khoi dong SimulatorMarketLevelTicker1MStopLoss...");
//            // (Tao Simulator voi Constructor mac dinh)
//            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();
//
//            test.initData(); // (Ham nay se doc tu DataContext/Cache)
//            test.simulatorWithInitEntry(); // Bat dau chay 5 nam backtest
//
//            LOG.info("\n--- HOAN TAT TOAN BO QUA TRINH BACKTEST ---");
//
//        } catch (Exception e) {
//            LOG.error("!!! LOI NGHIEM TRONG KHI KHOI TAO HOAC CHAY SIMULATOR !!!", e);
//        } finally {
//            // Dong ket noi
//            if (MODEL_PNL != null) try { MODEL_PNL.close(); } catch (Exception e) {}
//            if (MODEL_DRAWDOWN != null) try { MODEL_DRAWDOWN.close(); } catch (Exception e) {}
//            if (ONNX_ENV != null) try { ONNX_ENV.close(); } catch (Exception e) {}
//            DataManagerAerospike.closeConnection();
//            LOG.info("Da dong tat ca ket noi.");
//        }
//    }
//}