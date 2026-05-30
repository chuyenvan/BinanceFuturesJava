package com.binance.chuyennd.ai_ml.hpo.master;

import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.hpo.kaggle.KaggleDataLoader;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import io.jenetics.*;
import io.jenetics.engine.Engine;
import io.jenetics.engine.EvolutionResult;
import io.jenetics.util.DoubleRange;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Locale;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class RunHpoMaster_EntryLogic {

    private static final Logger LOG = LoggerFactory.getLogger(RunHpoMaster_EntryLogic.class);

    // Cấu hình HPO
    private static final int POPULATION_SIZE = 50;  // 50 cá thể / 1 thế hệ
    private static final int GENERATIONS = 100;     // Chạy tối đa 100 thế hệ
    private static final int MAX_STEADY_GENERATIONS = 15; // Dừng sớm nếu 15 Gen không có tiến bộ

    private static final String TASK_SET = "hpo_task_queue";
    private static final AtomicLong testCounter = new AtomicLong(0);

    // =========================================================
    // 🔥 CLASS ĐỊNH NGHĨA GÓI HÀNG (TASK) ĐỂ GIAO CHO KAGGLE
    // =========================================================
    public static class HpoTask {
        public String taskId;
        public String status; // PENDING, RUNNING, DONE

        // 11 Tham số giao dịch
        public float ds, dm, db, us, um, ub, d15s;
        public float aiRisk, ai15m, ai24h, aiMaxThres;

        // Kết quả từ Kaggle trả về
        public float fitnessScore = -10000f;
        public String logDetail = "";
        public long startTime = 0L;
    }

    public static void main(String[] args) {
        LOG.info("👑 MÁY CHỦ ORACLE (MASTER) KHỞI ĐỘNG...");
        LOG.info("⚡ Chế độ: KHÔNG BACKTEST. Phân phát Task cho Kaggle Worker qua Aerospike.");

        Configs.IS_HPO_MODE = true;
        Configs.IS_KAGGLE_MODE = true;

        Genotype<DoubleGene> gtf = Genotype.of(
                // 7 Tham số thị trường
                DoubleChromosome.of(DoubleRange.of(-0.020, -0.005)), // 0: Down Small
                DoubleChromosome.of(DoubleRange.of(-0.040, -0.021)), // 1: Down Med
                DoubleChromosome.of(DoubleRange.of(-0.100, -0.041)), // 2: Down Big
                DoubleChromosome.of(DoubleRange.of(0.005, 0.020)),   // 3: Up Small
                DoubleChromosome.of(DoubleRange.of(0.021, 0.040)),   // 4: Up Med
                DoubleChromosome.of(DoubleRange.of(0.041, 0.100)),   // 5: Up Big
                DoubleChromosome.of(DoubleRange.of(-0.035, -0.015)), // 6: Down 4H Small (đã đổi logic thành 4H)

                // 4 Tham số AI Filter
                DoubleChromosome.of(DoubleRange.of(-0.20, -0.08)),   // 7: AI Risk 4H
                DoubleChromosome.of(DoubleRange.of(0.010, 0.025)),   // 8: AI Mom 15M
                DoubleChromosome.of(DoubleRange.of(0.010, 0.060)),   // 9: AI Mom 24H
                DoubleChromosome.of(DoubleRange.of(0.10, 0.25))      // 10: AI Max Thres (Funding)
        );

        // Khởi tạo Engine
        // Dùng ThreadPool 50 luồng để đẩy 50 task lên DB CÙNG MỘT LÚC và đứng chờ
        Engine<DoubleGene, Float> engine = Engine.builder(RunHpoMaster_EntryLogic::eval, gtf)
                .populationSize(POPULATION_SIZE)
                .maximizing()
                .alterers(new Mutator<>(0.15), new MeanAlterer<>(0.60))
                .executor(Executors.newFixedThreadPool(POPULATION_SIZE))
                .build();

        long startTime = System.currentTimeMillis();
        EvolutionResult<DoubleGene, Float> result = null;
        float globalBestScore = -Float.MAX_VALUE;
        int steadyCount = 0;

        for (int gen = 1; gen <= GENERATIONS; gen++) {
            LOG.info("🚀 ĐANG BẮT ĐẦU GEN {}/{} - Đang giao việc cho Kaggle...", gen, GENERATIONS);

            if (result == null) {
                result = engine.stream().limit(1).collect(EvolutionResult.toBestEvolutionResult());
            } else {
                result = engine.stream(result.population()).limit(1).collect(EvolutionResult.toBestEvolutionResult());
            }

            float currentGenBest = result.bestFitness();

            LOG.info("===================================================================");
            LOG.info(">>> 🏆 KẾT THÚC GEN {}/{} | SCORE BEST: {} <<<", gen, GENERATIONS, String.format("%.2f", currentGenBest));
            LOG.info("===================================================================\n");

            if (currentGenBest > globalBestScore) {
                globalBestScore = currentGenBest;
                steadyCount = 0;
            } else {
                steadyCount++;
            }

            if (steadyCount >= MAX_STEADY_GENERATIONS) {
                LOG.info("🛑 EARLY STOPPING: Đã hội tụ sau {} thế hệ không cải thiện!", steadyCount);
                break;
            }
        }

        printFinalResult(result, startTime);
        System.exit(0);
    }

    /**
     * 🔥 HÀM EVAL: Không làm việc nặng, chỉ ném Task lên Aerospike và đợi kết quả
     */
    private static Float eval(Genotype<DoubleGene> gt) {
        long c = testCounter.incrementAndGet();

        // 1. Trích xuất 11 tham số
        float ds = gt.get(0).gene().floatValue();
        float dm = gt.get(1).gene().floatValue();
        float db = gt.get(2).gene().floatValue();
        float us = gt.get(3).gene().floatValue();
        float um = gt.get(4).gene().floatValue();
        float ub = gt.get(5).gene().floatValue();
        float d15s = gt.get(6).gene().floatValue();
        float aiRisk = gt.get(7).gene().floatValue();
        float ai15m = gt.get(8).gene().floatValue();
        float ai24h = gt.get(9).gene().floatValue();
        float aiMaxThres = gt.get(10).gene().floatValue();

        // 2. Tạo Mã Hash Duy Nhất (Dùng Locale.US để đảm bảo dấu chấm thập phân)
        String taskId = String.format(Locale.US, "G_%.4f_%.4f_%.4f_%.4f_%.4f_%.4f_%.4f_%.4f_%.4f_%.4f_%.4f",
                ds, dm, db, us, um, ub, d15s, aiRisk, ai15m, ai24h, aiMaxThres);

        Key key = new Key(Configs.AEROSPIKE_NAMESPACE, TASK_SET, taskId);

        try {
            // 3. CACHE SIÊU TỐC: Quá khứ chạy rồi thì lấy luôn điểm, khỏi cần Kaggle cày lại
            Record record = DataManagerAerospikeFloatSim.getClient226().get(null, key);
            if (record != null && "DONE".equals(record.getString("status"))) {
                return record.getFloat("score");
            }

            // 4. Nếu chưa ai làm -> Đóng gói gửi lên Aerospike
            HpoTask task = new HpoTask();
            task.taskId = taskId;
            task.status = "PENDING";
            task.ds = ds; task.dm = dm; task.db = db; task.us = us; task.um = um; task.ub = ub; task.d15s = d15s;
            task.aiRisk = aiRisk; task.ai15m = ai15m; task.ai24h = ai24h; task.aiMaxThres = aiMaxThres;

            WritePolicy wp = new WritePolicy();
            wp.recordExistsAction = RecordExistsAction.CREATE_ONLY; // Chỉ tạo mới, nếu có rồi thì thôi

            try {
                DataManagerAerospikeFloatSim.getClient226().put(wp, key,
                        new com.aerospike.client.Bin("status", "PENDING"),
                        new com.aerospike.client.Bin("startTime", 0L),
                        new com.aerospike.client.Bin("data", Utils.gson.toJson(task))
                );
            } catch (com.aerospike.client.AerospikeException e) {
                // Lỗi CREATE_ONLY nghĩa là đã có luồng khác nhét vào rồi, cứ việc đi tiếp xuống vòng lặp chờ
            }

            // 5. TRẠM CHỜ (Chờ Kaggle Worker báo DONE)
            while (true) {
                Thread.sleep(5000); // Check DB mỗi 5 giây

                Record checkRec = DataManagerAerospikeFloatSim.getClient226().get(null, key);
                if (checkRec != null && "DONE".equals(checkRec.getString("status"))) {
                    float finalScore = checkRec.getFloat("score");
                    String dataJson = checkRec.getString("data");

                    HpoTask finishedTask = Utils.gson.fromJson(dataJson, HpoTask.class);

                    // In Log như bình thường
                    LOG.info(String.format("Trial %4d | %s | [D_Big:%.3f, aiR:%.3f, aiMax:%.3f]",
                            c, finishedTask.logDetail, db, aiRisk, aiMaxThres));

                    return finalScore;
                }
            }

        } catch (Exception e) {
            LOG.error("❌ Lỗi Eval Master: ", e);
            return -10000.0f;
        }
    }

    private static void printFinalResult(EvolutionResult<DoubleGene, Float> result, long startTime) {
        Genotype<DoubleGene> best = result.bestPhenotype().genotype();
        LOG.info("\n=============================================");
        LOG.info("=== 👑 KẾT QUẢ MASTER VÔ ĐỊCH (11 PARAMS) ===");
        LOG.info("Fitness tốt nhất: {}", String.format("%.4f", result.bestFitness()));
        LOG.info("MS_DOWN_SMALL_AVG = {}f;", String.format(Locale.US, "%.5f", best.get(0).gene().floatValue()));
        LOG.info("MS_DOWN_MED_AVG   = {}f;", String.format(Locale.US, "%.5f", best.get(1).gene().floatValue()));
        LOG.info("MS_DOWN_BIG_AVG   = {}f;", String.format(Locale.US, "%.5f", best.get(2).gene().floatValue()));
        LOG.info("MS_UP_SMALL_THRES = {}f;", String.format(Locale.US, "%.5f", best.get(3).gene().floatValue()));
        LOG.info("MS_UP_MED_THRES   = {}f;", String.format(Locale.US, "%.5f", best.get(4).gene().floatValue()));
        LOG.info("MS_UP_BIG_THRES   = {}f;", String.format(Locale.US, "%.5f", best.get(5).gene().floatValue()));
        LOG.info("MS_DOWN_4H_SMALL  = {}f;", String.format(Locale.US, "%.5f", best.get(6).gene().floatValue()));
        LOG.info("HARD_RISK_LIMIT_4H= {}f;", String.format(Locale.US, "%.5f", best.get(7).gene().floatValue()));
        LOG.info("MIN_MOMENTUM_15M  = {}f;", String.format(Locale.US, "%.5f", best.get(8).gene().floatValue()));
        LOG.info("MIN_MOMENTUM_24H  = {}f;", String.format(Locale.US, "%.5f", best.get(9).gene().floatValue()));
        LOG.info("AI_MAX_THRES(Fund)= {}f;", String.format(Locale.US, "%.5f", best.get(10).gene().floatValue()));
        LOG.info("=============================================");
    }
}