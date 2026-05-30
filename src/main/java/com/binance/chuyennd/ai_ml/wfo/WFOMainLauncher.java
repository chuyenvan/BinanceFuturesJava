//package com.binance.chuyennd.ai_ml.wfo;
//
//import com.binance.chuyennd.research.DataManager;
//import com.binance.chuyennd.utils.Configs;
//import com.binance.chuyennd.utils.Utils;
//import org.slf4j.Logger;
//import org.slf4j.LoggerFactory;
//
//public class WFOMainLauncher {
//    private static final Logger LOG = LoggerFactory.getLogger(WFOMainLauncher.class);
//
//    public static void main(String[] args) throws Exception {
//        LOG.info("=== 🚀 KHỞI ĐỘNG HỆ THỐNG WFO CHẾ ĐỘ TUẦN TỰ ===");
//        Configs.IS_HPO_MODE = true;
//
//        // ÉP NẠP DỮ LIỆU TẠI LUỒNG MAIN TRƯỚC
//        LOG.info("Step 1: Nạp Market Data...");
//        DataManager.getMarketData();
//
//        LOG.info("Step 2: Nạp AI Predictions...");
//        DataManager.getAiPredictionData();
//
//        // Xác định dải thời gian
//        long startTs = Utils.sdfFile.parse("20240101").getTime();
//
//        if (Configs.IS_KAGGLE_MODE) {
//            LOG.info("Step 3: Nạp Tickers 1M...");
//            long current = startTs;
//            while (current < System.currentTimeMillis()) {
//                DataManager.getTickers1M(current);
//                current += Utils.TIME_DAY;
//            }
//        }
//
//
//        LOG.info("✅ TẤT CẢ DỮ LIỆU ĐÃ SẴN SÀNG TRONG RAM. Bắt đầu tối ưu...");
//
//        // Bây giờ mới khởi chạy tối ưu
//        new WFOOrchestrator().startProcess(startTs, System.currentTimeMillis());
//    }
//}