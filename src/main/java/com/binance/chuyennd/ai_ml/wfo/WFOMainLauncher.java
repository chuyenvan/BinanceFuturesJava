package com.binance.chuyennd.ai_ml.wfo;

import com.binance.chuyennd.research.DataManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class WFOMainLauncher {
    private static final Logger LOG = LoggerFactory.getLogger(WFOMainLauncher.class);

    public static void main(String[] args) throws Exception {
        LOG.info("=== 🚀 BẮT ĐẦU WALK-FORWARD OPTIMIZATION (3 TẦNG) ===");

        // 1. Cấu hình môi trường (Bật Kaggle Mode nếu chạy trên Kaggle để đọc file .dat) [cite: 946]
        Configs.IS_HPO_MODE = true;

        // 2. Nạp dữ liệu vào RAM một lần duy nhất để Backtest xé gió
        LOG.info("📥 Đang nạp dữ liệu lịch sử vào RAM...");
        DataManager.getMarketData();
        DataManager.getAiPredictionData();
        // Nạp thêm Tickers 1M cho khoảng thời gian định chạy (Ví dụ từ 20240101)
        long current = Utils.sdfFile.parse("20240101").getTime();
        while (current < System.currentTimeMillis()) {
            DataManager.getTickers1M(current);
            current += Utils.TIME_DAY;
        }

        // 3. Kích hoạt Orchestrator [cite: 739]
        WFOOrchestrator orchestrator = new WFOOrchestrator();
        long startWFO = Utils.sdfFile.parse("20240101").getTime();
        long endWFO = System.currentTimeMillis();

        orchestrator.startProcess(startWFO, endWFO);

        LOG.info("✅ QUY TRÌNH WFO HOÀN TẤT!");
    }
}