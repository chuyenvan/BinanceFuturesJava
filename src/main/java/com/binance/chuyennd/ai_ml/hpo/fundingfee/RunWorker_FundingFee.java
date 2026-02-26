package com.binance.chuyennd.ai_ml.hpo.fundingfee;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.hpo.distributed.DistributedQueueManager;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.utils.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class RunWorker_FundingFee {
    private static final Logger LOG = LoggerFactory.getLogger(RunWorker_FundingFee.class);

    // Dữ liệu dùng chung (Read-only) cho mọi luồng
    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static TreeMap<Long, Map<Short, float[]>> time2FundingPre;

    public static void main(String[] args) {
        LOG.info("=== 👷 WORKER NODE: KHỞI TẠO ===");

        try {
            Configs.TIME_RUN = "20250101";
            loadAndWarmUpData();
        } catch (Exception e) {
            e.printStackTrace();
            return;
        }

        // Đếm số CPU thực tế của máy (Kaggle = 5, VPS = ?)
        int processors = Runtime.getRuntime().availableProcessors();
        LOG.info("🚀 Phát hiện {} CPUs. Đang khởi tạo {} luồng Worker...", processors, processors);

        ExecutorService executor = Executors.newFixedThreadPool(processors);

        for (int i = 0; i < processors; i++) {
            final int workerId = i + 1;
            executor.submit(() -> startWorkerLoop(workerId));
        }
    }

    private static void startWorkerLoop(int workerId) {
        LOG.info("👷 Worker-{} đã sẵn sàng nhận việc!", workerId);
        while (true) {
            try {
                // 1. Rút Task từ Hàng đợi
                String genomeKey = DistributedQueueManager.popTask();

                if (genomeKey == null) {
                    // Nếu rỗng, ngủ 2 giây rồi tìm tiếp (tránh spam Aerospike)
                    Thread.sleep(2000);
                    continue;
                }

                LOG.info("🔥 Worker-{} nhận Task: {}", workerId, genomeKey);

                // 2. Lấy tham số
                String paramsStr = DistributedQueueManager.getTaskParams(genomeKey);
                if (paramsStr == null) {
                    DistributedQueueManager.submitResult(genomeKey, -10000.0);
                    continue;
                }

                String[] p = paramsStr.split(",");
                double pMinTrade = Double.parseDouble(p[0]);
                double pMinFull = Double.parseDouble(p[1]);
                double pUpAvg = Double.parseDouble(p[2]);
                double pDownAvg = Double.parseDouble(p[3]);
                double pFundingPred = Double.parseDouble(p[4]);

                // 3. Chạy Backtest
                BackTestEngineFundingFee engine = new BackTestEngineFundingFee(
                        pMinTrade, pMinFull, pUpAvg, pDownAvg, pFundingPred
                );

                double score = engine.run(time2MarketData, predictionMap, time2FundingPre);

                // 4. Trả kết quả
                DistributedQueueManager.submitResult(genomeKey, score);
                LOG.info("✅ Worker-{} Hoàn thành! Score: {}", workerId, score);

            } catch (Exception e) {
                LOG.error("Lỗi Worker-{}: {}", workerId, e.getMessage());
            }
        }
    }

    private static void loadAndWarmUpData() throws Exception {
        LOG.info("📥 Đang load 25GB dữ liệu từ Aerospike vào RAM (1 lần duy nhất)...");
        time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        time2FundingPre = DataManagerAerospikeFloatSim.getAllFundingPredictionsDataFromAerospike();
        LOG.info("✅ Load dữ liệu vào RAM thành công.");
    }
}