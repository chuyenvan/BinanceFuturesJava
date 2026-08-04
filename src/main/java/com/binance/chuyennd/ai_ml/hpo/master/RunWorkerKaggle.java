package com.binance.chuyennd.ai_ml.hpo.master;

import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.GenerationPolicy;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculatorV3;
import com.binance.chuyennd.ai_ml.hpo.kaggle.KaggleDataLoader;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.TreeMap;

public class RunWorkerKaggle {
    private static final Logger LOG = LoggerFactory.getLogger(RunWorkerKaggle.class);

    // 🔥 Dùng CHUNG hằng số với Master để không bao giờ lệch set name.
    private static final String QUEUE_SET  = RunHpoMaster_Distributed.QUEUE_SET;
    private static final String RESULT_SET = RunHpoMaster_Distributed.RESULT_SET;

    // Task RUNNING quá ngưỡng này coi như worker giữ nó đã chết -> cho cướp.
    // Backtest ~7.5 phút nên 15 phút là đủ rộng mà không để task chết treo cả thế hệ tới 30 phút.
    private static final long STALE_RUNNING_MS = 15 * 60_000L;

    // Dữ liệu tĩnh RAM
    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static TreeMap<Long, long[]> time2FundingPre;
    public static long offlineEndTime;

    public static void loadKaggleData() {
        try {
            offlineEndTime = Utils.sdfFile.parse("20260430").getTime() + (24 * Utils.TIME_HOUR) - Utils.TIME_MINUTE;
            LOG.info("📥 [KAGGLE WORKER] Đang nạp Data lên RAM...");
            time2MarketData = KaggleDataLoader.loadMarketData();
            predictionMap = KaggleDataLoader.loadAiPred();
            time2FundingPre = KaggleDataLoader.loadFundingPred();
            LOG.info("✅ Dữ liệu lên RAM thành công!");
        } catch (Exception e) {
            LOG.error("❌ Lỗi nạp Data: ", e);
        }
    }

    public static void main(String[] args) {
        LOG.info("👷 WORKER KHỞI ĐỘNG - queue={} | result={}", QUEUE_SET, RESULT_SET);
        Configs.TIME_RUN = "20260101"; // Khớp với Data Export

        loadKaggleData();

        while (true) {
            try {
                RunHpoMaster_Distributed.HpoDistributedTask task = fetchTaskFromAerospike();

                if (task == null) {
                    LOG.info("☕ Hàng đợi trống. Đi dạo 10s...");
                    Thread.sleep(10000);
                    continue;
                }

                Key resultKey = new Key(Configs.AEROSPIKE_NAMESPACE, RESULT_SET, task.taskId);
                Key queueKey  = new Key(Configs.AEROSPIKE_NAMESPACE, QUEUE_SET,  task.taskId);

                // Phòng race: nếu task này đã có điểm trong RESULT_SET rồi (worker khác vừa xong)
                // thì chỉ dọn queue và bỏ qua, không cày lại 7 phút vô ích.
                Record already = DataManagerAerospikeFloatSim.getClientOracle().get(null, resultKey);
                if (already != null) {
                    safeDelete(queueKey);
                    continue;
                }

                LOG.info("🔨 Đang cày Task: {}", task.taskId);
                long t1 = System.currentTimeMillis();

                // 🔥 NHỒI 14 THAM SỐ VÀO HỆ THỐNG TRƯỚC KHI CHẠY ENGINE
                applyTaskToConfigs(task);

                // Engine đọc trực tiếp từ Configs (AIRejectFilter cũng đọc Configs.xxx)
                BackTestEngineMaster engine = new BackTestEngineMaster();
                HPOFitnessCalculatorV3.FitnessReport report =
                        engine.run(time2MarketData, predictionMap, time2FundingPre, offlineEndTime);

                task.fitnessScore = report.finalFitness;
                task.logDetail = String.format("Fit: %8.0f | PnL: %5.0f$ | DD: %5.0f | Trades: %d | %s",
                        report.finalFitness, report.totalProfit, report.maxDrawdown, report.tradeCount, report.note);
                task.status = "DONE";

                // GHI KẾT QUẢ TRƯỚC, XOÁ QUEUE SAU -> không bao giờ mất task.
                submitResultToAerospike(task, resultKey);
                safeDelete(queueKey);

                LOG.info("✅ Xong Task: {} trong {} ms. -> {}", task.taskId, (System.currentTimeMillis() - t1), task.logDetail);

            } catch (Exception e) {
                LOG.error("❌ Lỗi Worker Loop: ", e);
                try { Thread.sleep(5000); } catch (Exception ignored) {}
            }
        }
    }

    private static void applyTaskToConfigs(RunHpoMaster_Distributed.HpoDistributedTask task) {
        // NHÓM 1: Market Signals
        Configs.MS_UP_BIG_THRES = task.msUpBig;
        Configs.MS_DOWN_BIG_AVG = task.msDownBig;
        Configs.MS_DOWN_SMALL_AVG_OR_15M = task.msSmall;

        // NHÓM 2: AI & ONNX
        Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD = task.aiMaxThres;
        Configs.MIN_MOMENTUM_15M = task.aiMin15M;
        Configs.HARD_RISK_LIMIT_4H = task.aiRisk4H;
        Configs.AI_DYNAMIC_MULTIPLIER = task.aiDynMul;
        Configs.AI_DYNAMIC_MIN = task.aiDynMin;
        Configs.AI_DYNAMIC_MAX = task.aiDynMax;

        // NHÓM 3: DCA (time làm tròn về int đúng như khóa cache đã băm bên Master)
        Configs.DCA_LOSS_BIG_DOWN = task.dcaLossBigDown;
        Configs.DCA_LOSS_BIG_UP   = task.dcaLossBigUp;
        Configs.DCA_TIME_BIG_DOWN = Math.round(task.dcaTimeBigDown);
        Configs.DCA_TIME_BIG_Up   = Math.round(task.dcaTimeBigUp);
    }

    /**
     * Scan QUEUE_SET (set NHỎ, chỉ chứa task active). Tìm PENDING hoặc RUNNING quá hạn,
     * chiếm task bằng optimistic lock (generation). Lỗi scan KHÔNG còn bị nuốt im lặng.
     */
    private static RunHpoMaster_Distributed.HpoDistributedTask fetchTaskFromAerospike() {
        final RunHpoMaster_Distributed.HpoDistributedTask[] foundTask = {null};
        try {
            DataManagerAerospikeFloatSim.getClientOracle().scanAll(null, Configs.AEROSPIKE_NAMESPACE, QUEUE_SET, (key, record) -> {
                if (foundTask[0] != null) return; // đã chiếm được 1 task, bỏ qua phần còn lại

                String status = record.getString("status");
                long startTime = record.getLong("startTime");

                boolean grabbable = "PENDING".equals(status)
                        || ("RUNNING".equals(status) && (System.currentTimeMillis() - startTime) > STALE_RUNNING_MS);
                if (!grabbable) return;

                WritePolicy lockPolicy = new WritePolicy();
                lockPolicy.generationPolicy = GenerationPolicy.EXPECT_GEN_EQUAL;
                lockPolicy.generation = record.generation;

                try {
                    DataManagerAerospikeFloatSim.getClientOracle().put(lockPolicy, key,
                            new com.aerospike.client.Bin("status", "RUNNING"),
                            new com.aerospike.client.Bin("startTime", System.currentTimeMillis())
                    );
                    String json = record.getString("data");
                    foundTask[0] = Utils.gson.fromJson(json, RunHpoMaster_Distributed.HpoDistributedTask.class);
                } catch (com.aerospike.client.AerospikeException e) {
                    // Generation lệch: worker khác vừa chiếm task này -> bỏ qua, scan tiếp
                }
            }, "status", "startTime", "data");
        } catch (Exception e) {
            // 🔥 KHÔNG nuốt lỗi nữa: scan fail (mạng/timeout tới host 226) là nguyên nhân
            // chính khiến worker tưởng queue trống và đi ngồi chơi.
            LOG.error("❌ Lỗi scan QUEUE (worker tưởng nhầm queue trống): ", e);
        }
        return foundTask[0];
    }

    private static void submitResultToAerospike(RunHpoMaster_Distributed.HpoDistributedTask task, Key resultKey) {
        WritePolicy wp = new WritePolicy();
        DataManagerAerospikeFloatSim.getClientOracle().put(wp, resultKey,
                new com.aerospike.client.Bin("score", task.fitnessScore),
                new com.aerospike.client.Bin("data", Utils.gson.toJson(task))
        );
    }

    private static void safeDelete(Key queueKey) {
        try {
            DataManagerAerospikeFloatSim.getClientOracle().delete(new WritePolicy(), queueKey);
        } catch (Exception e) {
            LOG.warn("⚠️ Không xoá được task khỏi queue (sẽ tự hết hạn): {}", queueKey, e);
            e.printStackTrace();
        }
    }
}