package com.binance.chuyennd.ai_ml.hpo.master;

import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculatorV3;
import com.binance.chuyennd.ai_ml.hpo.kaggle.KaggleDataLoader;
import com.binance.chuyennd.ai_ml.onnx.entry.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Arrays;
import java.util.TreeMap;

public class RunWorkerKaggle {
    private static final Logger LOG = LoggerFactory.getLogger(RunWorkerKaggle.class);
    private static final String TASK_SET = "hpo_task_queue";

    // Dữ liệu tĩnh lưu trên RAM của Worker Kaggle để cày Backtest
    public static TreeMap<Long, MarketDataObject15M> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static TreeMap<Long, long[]> time2FundingPre;
    public static long offlineEndTime;

    /**
     * 🔥 TỐI ƯU: Nạp dữ liệu HPO hệ 15M vào RAM và in Log chi tiết kiểm tra số lượng
     */
    public static void loadKaggleData() {
        try {
            offlineEndTime = Utils.sdfFile.parse("20260430").getTime() + (24 * Utils.TIME_HOUR) - Utils.TIME_MINUTE;
            LOG.info("📥 [KAGGLE WORKER] Bắt đầu kích hoạt tiến trình nạp bộ dữ liệu HPO 15M...");

            // 1. Tải dữ liệu Market Data 15M
            time2MarketData = KaggleDataLoader.loadMarketData();
            if (time2MarketData != null) {
                LOG.info("✅ [LOAD SUCCESS] Đã nạp thành công 'time2MarketData' -> Quy mô: {} records.", time2MarketData.size());
            } else {
                LOG.error("❌ [LOAD FAILED] Lỗi nghiêm trọng: Tập dữ liệu 'time2MarketData' bị NULL!");
            }

            // 2. Tải dữ liệu AI Prediction (Entry/Risk)
            predictionMap = KaggleDataLoader.loadAiPred();
            if (predictionMap != null) {
                LOG.info("✅ [LOAD SUCCESS] Đã nạp thành công 'predictionMap' -> Quy mô: {} records.", predictionMap.size());
            } else {
                LOG.error("❌ [LOAD FAILED] Lỗi nghiêm trọng: Tập dữ liệu 'predictionMap' bị NULL!");
            }

            // 3. Tải dữ liệu AI Funding Prediction (Primitive Array)
            time2FundingPre = KaggleDataLoader.loadFundingPred();
            if (time2FundingPre != null) {
                LOG.info("✅ [LOAD SUCCESS] Đã nạp thành công 'time2FundingPre' -> Quy mô: {} records.", time2FundingPre.size());
            } else {
                LOG.error("❌ [LOAD FAILED] Lỗi nghiêm trọng: Tập dữ liệu 'time2FundingPre' bị NULL!");
            }

            // --- KIỂM TRA CHỐT SỔ TÍNH TOÀN VẸN ---
            if (time2MarketData != null && predictionMap != null && time2FundingPre != null) {
                LOG.info("🎉 [RAM READY] Tuyệt vời! Toàn bộ 3 tập dữ liệu hệ 15M đã sẵn sàng. Bắt đầu mở cầu dao gắp việc!");
            } else {
                LOG.warn("⚠️ [DATA WARNING] Bộ dữ liệu nạp lên không toàn vẹn! Vui lòng kiểm tra lại đường dẫn Dataset trên Kaggle.");
            }

        } catch (Exception e) {
            LOG.error("❌ Lỗi hệ thống trong quá trình nạp dữ liệu cào Kaggle: ", e);
        }
    }

    public static void main(String[] args) {
        LOG.info("👷 KAGGLE WORKER TRÂU CÀY KHỞI ĐỘNG - Kết nối tới Hàng đợi Aerospike...");
        Configs.IS_HPO_MODE = true;
        Configs.IS_KAGGLE_MODE = true;

        Configs.TIME_RUN = "20251001"; // Hoặc "20260101" tùy vào mốc bác đã Export

        // Tải data vào RAM một lần duy nhất khi khởi động Worker
        loadKaggleData();

        while (true) {
            try {
                // Đi lùng sục hàng đợi xem Master có giao việc gì PENDING không
                RunHpoMaster_EntryLogic.HpoTask task = fetchTaskFromAerospike();

                if (task == null) {
                    LOG.info("☕ Hàng đợi trống hoặc các Task đang được các Worker khác gắp. Nghỉ ngơi 10 giây...");
                    Thread.sleep(10000);
                    continue;
                }

                LOG.info("🔨 Khởi động động cơ Backtest. Đang xử lý Task ID: {}", task.taskId);
                long t1 = System.currentTimeMillis();

                // Vắt kiệt luồng CPU để chạy Simulator Backtest
                BackTestEngineMaster engine = new BackTestEngineMaster(
                        task.ds, task.dm, task.db, task.us, task.um, task.ub, task.d15s,
                        task.aiRisk, task.ai15m, task.ai24h, task.aiMaxThres
                );

                HPOFitnessCalculatorV3.FitnessReport report = engine.run(
                        time2MarketData,
                        predictionMap,
                        time2FundingPre,
                        offlineEndTime
                );

                // Đóng gói kết quả gửi trả về cho Master Oracle
                task.fitnessScore = report.finalFitness;
                task.logDetail = String.format("Fit: %8.0f | PnL: %5.0f$ | DD: %5.0f$ | Trades: %d | %s",
                        report.finalFitness, report.totalProfit, report.maxDrawdown, report.tradeCount, report.note);
                task.status = "DONE";

                submitResultToAerospike(task);
                LOG.info("✅ Gửi kết quả thành công cho Task: {} trong {} ms. -> {}", task.taskId, (System.currentTimeMillis() - t1), task.logDetail);

            } catch (Exception e) {
                LOG.error("❌ Lỗi tiến trình xử lý vòng lặp Worker: ", e);
                try { Thread.sleep(5000); } catch (Exception ignored) {}
            }
        }
    }

    private static RunHpoMaster_EntryLogic.HpoTask fetchTaskFromAerospike() {
        final RunHpoMaster_EntryLogic.HpoTask[] foundTask = {null};

        try {
            DataManagerAerospikeFloatSim.getClient226().scanAll(null, Configs.AEROSPIKE_NAMESPACE, TASK_SET, (key, record) -> {
                if (foundTask[0] != null) return;

                String status = record.getString("status");
                long startTime = record.getLong("startTime");

                // Điều kiện gắp task: Đang đợi (PENDING) hoặc đang chạy (RUNNING) nhưng bị đơ quá 30 phút
                if ("PENDING".equals(status) || ("RUNNING".equals(status) && (System.currentTimeMillis() - startTime) > 30 * 60000L)) {

                    // CƠ CHẾ KHÓA NGUYÊN TỬ (Atomic Lock): Đứa nào Put chữ RUNNING lên DB thành công trước thì sở hữu task
                    WritePolicy lockPolicy = new WritePolicy();
                    lockPolicy.generationPolicy = com.aerospike.client.policy.GenerationPolicy.EXPECT_GEN_EQUAL;
                    lockPolicy.generation = record.generation; // Chống tranh chấp nếu Worker khác sờ vào cùng mili-giây

                    try {
                        DataManagerAerospikeFloatSim.getClient226().put(lockPolicy, key,
                                new com.aerospike.client.Bin("status", "RUNNING"),
                                new com.aerospike.client.Bin("startTime", System.currentTimeMillis())
                        );

                        // Đóng dấu chủ quyền thành công, tiến hành parse Object ra chạy
                        String json = record.getString("data");
                        foundTask[0] = Utils.gson.fromJson(json, RunHpoMaster_EntryLogic.HpoTask.class);

                    } catch (com.aerospike.client.AerospikeException e) {
                        e.printStackTrace();
                        // Thua cuộc do bị Worker khác nẫng tay trên, tiếp tục scan bản ghi tiếp theo
                    }
                }
            }, "status", "startTime", "data");
        } catch (Exception e) {}

        return foundTask[0];
    }

    private static void submitResultToAerospike(RunHpoMaster_EntryLogic.HpoTask task) {
        Key key = new Key(Configs.AEROSPIKE_NAMESPACE, TASK_SET, task.taskId);
        WritePolicy wp = new WritePolicy();
        DataManagerAerospikeFloatSim.getClient226().put(wp, key,
                new com.aerospike.client.Bin("status", "DONE"),
                new com.aerospike.client.Bin("score", task.fitnessScore),
                new com.aerospike.client.Bin("data", Utils.gson.toJson(task))
        );
    }
}