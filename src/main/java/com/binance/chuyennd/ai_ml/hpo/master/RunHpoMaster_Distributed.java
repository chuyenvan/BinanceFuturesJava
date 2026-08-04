package com.binance.chuyennd.ai_ml.hpo.master;

import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
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

public class RunHpoMaster_Distributed {

    private static final Logger LOG = LoggerFactory.getLogger(RunHpoMaster_Distributed.class);

    // Cấu hình HPO cho Master
    private static final int POPULATION_SIZE = 50;  // 50 Task mỗi Gen ném lên DB
    private static final int GENERATIONS = 100;     // Tối đa 100 thế hệ
    private static final int MAX_STEADY_GENERATIONS = 15; // Dừng sớm

    private static final int TOTAL_PARAMS = 13;

    // =========================================================
    // 🔥 VERSION HOÁ CACHE
    // BẮT BUỘC bump biến này MỖI KHI đổi bất cứ thứ gì ngoài genome mà có ảnh
    // hưởng tới kết quả backtest: RATE_FEE, logic trailing (calRateLossDynamicBuy),
    // budget divider, MAX_CONCURRENT_ORDERS, circuit breaker, hay thêm/bớt gene...
    // =========================================================
    // v4 -> v5: Bước 0 thêm slippage 2 chân (SLIPPAGE_RATE/APPLY_SLIPPAGE) và bịt
    // look-ahead nội-nến (BLOCK_INTRABAR_LOOKAHEAD). Cả hai ảnh hưởng PnL backtest
    // nhưng không nằm trong genome => phải đổi version để bỏ cache điểm cũ (v4).
    // v5 -> v6: BỎ gene MIN_MOMENTUM_24H khỏi genome (14 -> 13 gene). Đổi layout genome +
    // buildTaskId => taskId cũ không còn hợp lệ, BẮT BUỘC version mới để bỏ cache v5.
    // v6 -> v7: maxDD (unProfitMin) đổi nguồn từ Σ profitMin/minPrice (hụt, mẫu theo giờ) sang đáy
    // unrealized THẬT per-tick (bar.low) trong BudgetManagerSimple.updateTrueUnrealizedMin. unProfitMin
    // nuôi finalFitness V3 (phạt DD 15/30/40% + kill-switch >40%) => DD thật sâu hơn ~1.1-1.6x làm
    // finalFitness đổi cho MỌI genome (không nằm trong genome) => BẮT BUỘC version mới bỏ cache v6.
    // v7 -> v8: BOOKING FIX giá chốt trailing-stop — kẹp priceTP=min(priceSL, ticker.maxPrice) trong
    // updateStatusNew (gap thủng SL thì không bán được level cũ). Giảm calTp ~6% PnL (toàn STOP_MARKET,
    // dồn 2025). Đổi PnL backtest mọi genome => BẮT BUỘC version mới bỏ cache v7.
    // v8 -> v9: PARITY FIX (TASK-030 #10, một bộ não) — SIM createOrderBUY khi predict==null TRƯỚC ĐÂY
    // BỎ filter → VẪN vào lệnh; LIVE createOrderBuyRequest reject khi prediction==null. Nay SIM cũng reject
    // pred==null (khớp live) => bớt entry ở mốc thiếu pred => đổi PnL backtest mọi genome => bỏ cache v8.
    // v9 -> v10: BƯỚC 3 (ruin) — BẬT CIRCUIT BREAKER MẶC ĐỊNH. BREAKER_MODE=MARGIN, BREAKER_MARGIN_HALT=0.50
    // (chặn MỞ MỚI khi margin/vốn >= 0.50). Quét ngưỡng 2021→2026: 0.50 cho return/maxDD tốt nhất 4.88
    // (maxDD -58.6%→-29.5%, maxMargR 0.99→0.51, PnL -27%). Cap %vốn/cụm đã thử & GỠ (veto 0-8 lần, vô dụng
    // trên danh mục). Breaker đổi PnL/DD mọi genome => bỏ cache v10.
    // v10 -> v11: TASK-112 — bỏ 2 flag runtime kaggle/HPO-mode, nguồn dữ liệu tường minh per-box
    // (AEROSPIKE_READ_CLUSTER + TICKER_SOURCE trong config.properties) + fail-fast thiếu data.
    // Logic sim/PnL KHÔNG đổi (GATE khớp 100%), nhưng wiring nguồn data đổi → version mới để
    // cache HPO cũ không trộn kết quả chạy dưới cơ chế mode cũ (đã 2 lần chạy hỏng vì quên set mode).
    // v11 -> v12: TASK-118 — exit clamp từ min(priceSL, bar.high) → min(priceSL, bar.open).
    // Ca gap-down: bar.open là giá thực thi đầu tiên (haircut thực), bar.high có thể cao hơn open nội nến
    // → old formula overshoot PnL khi gap. Fix giảm PnL backtest (~4k toàn range, đúng hướng). Bỏ cache v11.
    public static final String CONFIG_VERSION = "v12";

    // 🔥 TÁCH 2 SET:
    //  - QUEUE_SET: chỉ chứa task ĐANG active (PENDING/RUNNING). Worker scanAll cái này nên LUÔN NHỎ.
    //    Task xong là bị XOÁ khỏi đây => scan không bao giờ chậm dần theo số thế hệ.
    //  - RESULT_SET: kho điểm vĩnh viễn (cache). Chỉ truy cập bằng get(key), KHÔNG bao giờ scan.
    public static final String QUEUE_SET  = "hpo_queue_"   + CONFIG_VERSION;
    public static final String RESULT_SET = "hpo_results_" + CONFIG_VERSION;

    private static final AtomicLong testCounter = new AtomicLong(0);

    // =========================================================
    // 🔥 CLASS DEFINITION: THE WORK PACKAGE (TASK)
    // =========================================================
    public static class HpoDistributedTask {
        public String taskId;
        public String status; // PENDING, RUNNING, DONE

        // NHÓM 1: Market Signals (3 Tham số)
        public float msUpBig, msDownBig, msSmall;

        // NHÓM 2: AI & ONNX (6 Tham số)
        public float aiMaxThres, aiMin15M, aiRisk4H;
        public float aiDynMul, aiDynMin, aiDynMax;

        // NHÓM 3: DCA (4 Tham số)
        public float dcaLossBigDown, dcaLossBigUp, dcaTimeBigDown, dcaTimeBigUp;

        // Báo cáo
        public float fitnessScore = -10000f;
        public String logDetail = "";
        public long startTime = 0L;
    }

    public static void main(String[] args) {
        LOG.info("👑 MÁY CHỦ ORACLE (MASTER) KHỞI ĐỘNG HỆ THỐNG PHÂN TÁN ({} PARAMS)...", TOTAL_PARAMS);
        LOG.info("⚡ Queue set={} | Result set={}", QUEUE_SET, RESULT_SET);

        // Nhóm 1 (3) + Nhóm 2 (6) + Nhóm 3 DCA (4) = 13 Genes (đã bỏ MIN_MOMENTUM_24H)
        Genotype<DoubleGene> gtf = Genotype.of(
                // NHÓM 1
                DoubleChromosome.of(DoubleRange.of(0.010, 0.040)),   // 0: MS_UP_BIG_THRES
                DoubleChromosome.of(DoubleRange.of(-0.100, -0.025)), // 1: MS_DOWN_BIG_AVG
                DoubleChromosome.of(DoubleRange.of(-0.030, -0.010)), // 2: MS_DOWN_SMALL_AVG_OR_15M

                // NHÓM 2
                DoubleChromosome.of(DoubleRange.of(0.10, 0.25)),     // 3: AI_MAX_THRES
                DoubleChromosome.of(DoubleRange.of(0.010, 0.035)),   // 4: MIN_MOMENTUM_15M
                DoubleChromosome.of(DoubleRange.of(-0.25, -0.05)),   // 5: HARD_RISK_LIMIT_4H
                DoubleChromosome.of(DoubleRange.of(1.0, 2.0)),       // 6: AI_DYN_MULTIPLIER
                DoubleChromosome.of(DoubleRange.of(0.1, 0.5)),       // 7: AI_DYN_MIN
                DoubleChromosome.of(DoubleRange.of(1.5, 3.0)),       // 8: AI_DYN_MAX

                // NHÓM 3 - DCA
                DoubleChromosome.of(DoubleRange.of(-0.30, -0.08)),   // 9: DCA_LOSS_BIG_DOWN
                DoubleChromosome.of(DoubleRange.of(-0.40, -0.10)),   // 10: DCA_LOSS_BIG_UP
                DoubleChromosome.of(DoubleRange.of(3, 20)),          // 11: DCA_TIME_BIG_DOWN (phút)
                DoubleChromosome.of(DoubleRange.of(5, 30))           // 12: DCA_TIME_BIG_Up   (phút)
        );

        Engine<DoubleGene, Float> engine = Engine.builder(RunHpoMaster_Distributed::eval, gtf)
                .populationSize(POPULATION_SIZE)
                .maximizing()
                .alterers(new Mutator<>(0.15), new MeanAlterer<>(0.60))
                .executor(Executors.newFixedThreadPool(POPULATION_SIZE)) // Nhồi 50 Task lên DB cùng lúc
                .build();

        EvolutionResult<DoubleGene, Float> result = null;
        float globalBestScore = -Float.MAX_VALUE;
        int steadyCount = 0;

        for (int gen = 1; gen <= GENERATIONS; gen++) {
            LOG.info("🚀 ĐANG BẮT ĐẦU GEN {}/{} - Đang bơm việc vào Hàng đợi...", gen, GENERATIONS);

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

        printFinalResult(result);
        System.exit(0);
    }

    /**
     * 🔥 EVAL MASTER: KHÔNG CHẠY BACKTEST.
     *  1. Tra RESULT_SET theo key -> trúng cache thì trả điểm tức thì.
     *  2. Trượt cache -> tạo task PENDING trong QUEUE_SET (set nhỏ).
     *  3. Poll RESULT_SET (get theo key) tới khi worker ghi điểm xong.
     */
    private static Float eval(Genotype<DoubleGene> gt) {
        long c = testCounter.incrementAndGet();

        HpoDistributedTask task = new HpoDistributedTask();
        task.msUpBig = gt.get(0).gene().floatValue();
        task.msDownBig = gt.get(1).gene().floatValue();
        task.msSmall = gt.get(2).gene().floatValue();
        task.aiMaxThres = gt.get(3).gene().floatValue();
        task.aiMin15M = gt.get(4).gene().floatValue();
        task.aiRisk4H = gt.get(5).gene().floatValue();
        task.aiDynMul = gt.get(6).gene().floatValue();
        task.aiDynMin = gt.get(7).gene().floatValue();
        task.aiDynMax = gt.get(8).gene().floatValue();
        task.dcaLossBigDown = gt.get(9).gene().floatValue();
        task.dcaLossBigUp = gt.get(10).gene().floatValue();
        task.dcaTimeBigDown = gt.get(11).gene().floatValue();
        task.dcaTimeBigUp = gt.get(12).gene().floatValue();

        task.taskId = buildTaskId(task);

        Key resultKey = new Key(Configs.AEROSPIKE_NAMESPACE, RESULT_SET, task.taskId);
        Key queueKey  = new Key(Configs.AEROSPIKE_NAMESPACE, QUEUE_SET,  task.taskId);

        try {
            // 1. Tra cache kết quả (point get, không scan)
            Record done = DataManagerAerospikeFloatSim.getClientOracle().get(null, resultKey);
            if (done != null) {
                return done.getFloat("score"); // 0.001 giây trả điểm, cứu hàng tiếng CPU
            }

            // 2. Chưa ai làm -> đẩy vào QUEUE (CREATE_ONLY chống 2 luồng cùng tạo)
            WritePolicy wp = new WritePolicy();
            wp.recordExistsAction = RecordExistsAction.CREATE_ONLY;
            try {
                DataManagerAerospikeFloatSim.getClientOracle().put(wp, queueKey,
                        new com.aerospike.client.Bin("status", "PENDING"),
                        new com.aerospike.client.Bin("startTime", 0L),
                        new com.aerospike.client.Bin("data", Utils.gson.toJson(task))
                );
            } catch (com.aerospike.client.AerospikeException e) {
                // Ignore: luồng khác vừa nhét task này vào queue
            }

            // 3. TRẠM CHỜ ORACLE: poll kho kết quả theo key.
            // Lưu ý: nếu KHÔNG có worker nào sống, thread này chờ vô hạn.
            while (true) {
                Thread.sleep(5000);

                Record checkRec = DataManagerAerospikeFloatSim.getClientOracle().get(null, resultKey);
                if (checkRec != null) {
                    float finalScore = checkRec.getFloat("score");
                    String dataJson = checkRec.getString("data");
                    HpoDistributedTask finishedTask = Utils.gson.fromJson(dataJson, HpoDistributedTask.class);
                    LOG.info(String.format("Trial %4d | %s | [ID: %s]", c, finishedTask.logDetail, task.taskId));
                    return finalScore;
                }
            }
        } catch (Exception e) {
            LOG.error("❌ Lỗi Eval Master: ", e);
            return -10000.0f;
        }
    }

    /**
     * Khóa cache PHẢI phản ánh đúng cấu hình thực sự chạy:
     * - 11 tham số float băm %.4f (đã bỏ MIN_MOMENTUM_24H)
     * - 2 tham số TIME băm theo giá trị ĐÃ LÀM TRÒN (đúng bằng giá trị apply vào Configs)
     *   để 12.31 và 12.49 (cùng round = 12) không sinh 2 trial trùng nhau.
     * - CONFIG_VERSION làm tiền tố để truy vết.
     */
    private static String buildTaskId(HpoDistributedTask task) {
        return String.format(Locale.US,
                "%s_%.4f_%.4f_%.4f_%.4f_%.4f_%.4f_%.4f_%.4f_%.4f_%.4f_%.4f_%d_%d",
                CONFIG_VERSION,
                task.msUpBig, task.msDownBig, task.msSmall,
                task.aiMaxThres, task.aiMin15M, task.aiRisk4H,
                task.aiDynMul, task.aiDynMin, task.aiDynMax,
                task.dcaLossBigDown, task.dcaLossBigUp,
                Math.round(task.dcaTimeBigDown), Math.round(task.dcaTimeBigUp));
    }

    private static void printFinalResult(EvolutionResult<DoubleGene, Float> result) {
        Genotype<DoubleGene> best = result.bestPhenotype().genotype();
        LOG.info("\n=============================================");
        LOG.info("=== 👑 KẾT QUẢ VÔ ĐỊCH ({} PARAMS) ===", TOTAL_PARAMS);
        LOG.info("Fitness: {}", String.format("%.4f", result.bestFitness()));
        LOG.info("MS_UP_BIG_THRES          = {}f;", String.format(Locale.US, "%.5f", best.get(0).gene().floatValue()));
        LOG.info("MS_DOWN_BIG_AVG          = {}f;", String.format(Locale.US, "%.5f", best.get(1).gene().floatValue()));
        LOG.info("MS_DOWN_SMALL_AVG_OR_15M = {}f;", String.format(Locale.US, "%.5f", best.get(2).gene().floatValue()));
        LOG.info("PREDICT_MAX_THRES        = {}f;", String.format(Locale.US, "%.5f", best.get(3).gene().floatValue()));
        LOG.info("MIN_MOMENTUM_15M         = {}f;", String.format(Locale.US, "%.5f", best.get(4).gene().floatValue()));
        LOG.info("HARD_RISK_LIMIT_4H       = {}f;", String.format(Locale.US, "%.5f", best.get(5).gene().floatValue()));
        LOG.info("AI_DYNAMIC_MULTIPLIER    = {}f;", String.format(Locale.US, "%.5f", best.get(6).gene().floatValue()));
        LOG.info("AI_DYNAMIC_MIN           = {}f;", String.format(Locale.US, "%.5f", best.get(7).gene().floatValue()));
        LOG.info("AI_DYNAMIC_MAX           = {}f;", String.format(Locale.US, "%.5f", best.get(8).gene().floatValue()));
        LOG.info("DCA_LOSS_BIG_DOWN        = {}f;", String.format(Locale.US, "%.5f", best.get(9).gene().floatValue()));
        LOG.info("DCA_LOSS_BIG_UP          = {}f;", String.format(Locale.US, "%.5f", best.get(10).gene().floatValue()));
        LOG.info("DCA_TIME_BIG_DOWN        = {};", Math.round(best.get(11).gene().floatValue()));
        LOG.info("DCA_TIME_BIG_Up          = {};", Math.round(best.get(12).gene().floatValue()));
        LOG.info("=============================================");
    }
}