package com.binance.chuyennd.ai_ml.hpo.master;

import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculatorV3;
import com.binance.chuyennd.ai_ml.hpo.kaggle.KaggleDataLoader;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.google.gson.reflect.TypeToken;
import io.jenetics.*;
import io.jenetics.engine.Engine;
import io.jenetics.engine.EvolutionResult;
import io.jenetics.util.DoubleRange;
import io.jenetics.util.ISeq;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.*;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class RunHpoMaster_EntryLogic {

    private static final Logger LOG = LoggerFactory.getLogger(RunHpoMaster_EntryLogic.class);

    // Bỏ final để cấu hình động theo Role
    private static int POPULATION_SIZE = 20;
    private static final int GENERATIONS = 60; // Tăng max Gen lên 60 vì sync chậm lại
    private static int SYNC_INTERVAL = 10;
    private static int MAX_STEADY_GENERATIONS;

    private static final AtomicLong testCounter = new AtomicLong(0);

    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static TreeMap<Long, long[]> time2FundingPre;
    public static long offlineEndTime;

    static class GeneRecord {
        public float ds, dm, db, us, um, ub, d15s;
        public float aiRisk, ai15m, ai24h, aiMaxThres; // Thêm aiMaxThres
        public float score;

        public GeneRecord(float ds, float dm, float db, float us, float um, float ub, float d15s,
                          float aiRisk, float ai15m, float ai24h, float aiMaxThres, float score) {
            this.ds = ds;
            this.dm = dm;
            this.db = db;
            this.us = us;
            this.um = um;
            this.ub = ub;
            this.d15s = d15s;
            this.aiRisk = aiRisk;
            this.ai15m = ai15m;
            this.ai24h = ai24h;
            this.aiMaxThres = aiMaxThres;
            this.score = score;
        }
    }

    public static void main(String[] args) {
        LOG.info("=== BẮT ĐẦU MASTER HPO: TỐI ƯU TOÀN DIỆN ENTRY LOGIC (11 PARAMS) ===");
        try {
            Configs.IS_HPO_MODE = true;
            Configs.IS_KAGGLE_MODE = true;
            Configs.TIME_RUN = "20251001"; // Key mới
            offlineEndTime = Utils.sdfFile.parse("20260430").getTime() + (24 * Utils.TIME_HOUR) - Utils.TIME_MINUTE;
            loadKaggleData();
        } catch (Exception e) {
            e.printStackTrace();
            return;
        }

        Genotype<DoubleGene> gtf = Genotype.of(
                // ... (7 tham số market giữ nguyên)
                DoubleChromosome.of(DoubleRange.of(-0.020, -0.005)), // 0: Down Small 1M
                DoubleChromosome.of(DoubleRange.of(-0.040, -0.021)), // 1: Down Med 1M
                DoubleChromosome.of(DoubleRange.of(-0.100, -0.041)), // 2: Down Big 1M
                DoubleChromosome.of(DoubleRange.of(0.005, 0.020)),   // 3: Up Small 1M
                DoubleChromosome.of(DoubleRange.of(0.021, 0.040)),   // 4: Up Med 1M
                DoubleChromosome.of(DoubleRange.of(0.041, 0.100)),   // 5: Up Big 1M
                DoubleChromosome.of(DoubleRange.of(-0.035, -0.015)), // 6: Down Small 15M

                DoubleChromosome.of(DoubleRange.of(-0.20, -0.08)),   // 7: AI Risk 4H
                DoubleChromosome.of(DoubleRange.of(0.010, 0.025)),   // 8: AI Mom 15M
                DoubleChromosome.of(DoubleRange.of(0.010, 0.060)),   // 9: AI Mom 24H
                DoubleChromosome.of(DoubleRange.of(0.10, 0.25))      // 10: AI Max Thres (Funding)
        );

        // 🔥 GỌI HÀM PHÂN VAI: Hàm này sẽ tự động thay đổi POPULATION_SIZE, SYNC_INTERVAL và MAX_STEADY_GENERATIONS
        Engine<DoubleGene, Float> engine = buildEngineWithRole(gtf);

        long startTime = System.currentTimeMillis();
        EvolutionResult<DoubleGene, Float> result = null;
        float globalBestScore = -Float.MAX_VALUE;
        int steadyCount = 0;

        // ❌ XÓA DÒNG NÀY: final int MAX_STEADY_GENERATIONS = 8;

        ISeq<Phenotype<DoubleGene, Float>> initialPopulation = loadInitialPopulationFromAerospike(gtf);

        for (int gen = 1; gen <= GENERATIONS; gen++) {
            if (result == null) {
                if (initialPopulation != null) {
                    LOG.info("🚀 Warm-start: Bắt đầu Gen 1 từ tinh hoa trên mạng.");
                    result = engine.stream(initialPopulation).limit(1).collect(EvolutionResult.toBestEvolutionResult());
                } else {
                    LOG.info("🌱 Khởi tạo Gen 1 ngẫu nhiên.");
                    result = engine.stream().limit(1).collect(EvolutionResult.toBestEvolutionResult());
                }
            } else {
                // 🔥 SỬ DỤNG BIẾN ĐỘNG SYNC_INTERVAL ĐÃ ĐƯỢC PHÂN VAI
                if (gen % SYNC_INTERVAL == 0) {
                    LOG.info("🌍 MỞ CỬA BIÊN GIỚI: Sync dữ liệu với Aerospike (Global Pool)...");
                    ISeq<Phenotype<DoubleGene, Float>> currentPop = syncIslandModelWithAerospike(result.population());
                    result = engine.stream(currentPop).limit(1).collect(EvolutionResult.toBestEvolutionResult());
                } else {
                    // Các thế hệ bình thường: Tiến hóa khép kín trên đảo
                    result = engine.stream(result.population()).limit(1).collect(EvolutionResult.toBestEvolutionResult());
                }
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

            // 🔥 SỬ DỤNG BIẾN ĐỘNG MAX_STEADY_GENERATIONS TỪ CLASS LEVEL
            if (steadyCount >= MAX_STEADY_GENERATIONS) {
                LOG.info("🛑 KÍCH HOẠT EARLY STOPPING: Thuật toán đã hội tụ sau {} thế hệ đi ngang!", steadyCount);
                break;
            }
        }
        printFinalResult(result, startTime);
    }

    // =========================================================
    // 🔥 AUTO NODE ROLE ASSIGNMENT VIA AEROSPIKE
    // =========================================================
    private static Engine<DoubleGene, Float> buildEngineWithRole(Genotype<DoubleGene> gtf) {
        long nodeId = 1;
        try {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, "hpo_node_roles", Configs.TIME_RUN);

            // 🔥 CÁCH CHUẨN ĐỂ ĐẾM ATOMIC TRONG AEROSPIKE: Dùng Operation.add trực tiếp lên Bin
            Record record = DataManagerAerospikeFloatSim.getClient226().operate(new WritePolicy(), key,
                    com.aerospike.client.Operation.add(new com.aerospike.client.Bin("node_count", 1)),
                    com.aerospike.client.Operation.get("node_count")
            );

            if (record != null) {
                nodeId = record.getLong("node_count");
            }
        } catch (Exception e) {
            // In luôn lỗi ra để lỡ có rớt mạng thì bác còn biết đường mà lần
            LOG.warn("⚠️ Không lấy được Node ID từ Aerospike, chạy mặc định. Chi tiết: {}", e.getMessage());
        }

        LOG.info("🖥️ NODE ID CỦA TIẾN TRÌNH NÀY TRONG CLUSTER: {}", nodeId);

        // --- CẤU HÌNH ĐỘNG DỰA TRÊN VAI TRÒ ---
        // (Phần còn lại giữ nguyên...)
        Mutator<DoubleGene, Float> mutator;
        Alterer<DoubleGene, Float> recombinator;

        if (nodeId % 3 == 1) {
            LOG.info("⚔️ VAI TRÒ: AGGRESSIVE EXPLORER (Pop: 40 | Sync: 15 Gen | Đột biến: 35%)");
            POPULATION_SIZE = 40;
            SYNC_INTERVAL = 15;
            MAX_STEADY_GENERATIONS = 12;
            mutator = new Mutator<>(0.35);
            recombinator = new UniformCrossover<>(0.50);

        } else if (nodeId % 3 == 2) {
            LOG.info("⚖️ VAI TRÒ: BALANCED (Pop: 30 | Sync: 10 Gen | Đột biến: 20%)");
            POPULATION_SIZE = 30;
            SYNC_INTERVAL = 10;
            MAX_STEADY_GENERATIONS = 8;
            mutator = new Mutator<>(0.20);
            recombinator = new MeanAlterer<>(0.50);

        } else {
            LOG.info("⛏️ VAI TRÒ: EXPLOITER (Pop: 20 | Sync: 5 Gen | Đột biến: 5%, Lai ghép: 80%)");
            POPULATION_SIZE = 20;
            SYNC_INTERVAL = 5;
            MAX_STEADY_GENERATIONS = 5;
            mutator = new Mutator<>(0.05);
            recombinator = new MeanAlterer<>(0.80);
        }

        return Engine.builder(RunHpoMaster_EntryLogic::eval, gtf)
                .populationSize(POPULATION_SIZE)
                .maximizing()
                // 🔥 Nạp các Alterers đã được thiết lập theo Role vào Engine
                .alterers(mutator, recombinator)
                .executor(Executors.newSingleThreadExecutor())
                .build();
    }

    private static Float eval(Genotype<DoubleGene> gt) {
        long c = testCounter.incrementAndGet();

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

        try {
            BackTestEngineMaster engine = new BackTestEngineMaster(ds, dm, db, us, um, ub, d15s, aiRisk, ai15m, ai24h, aiMaxThres);
            HPOFitnessCalculatorV3.FitnessReport report = engine.run(time2MarketData, predictionMap, time2FundingPre, offlineEndTime);

            LOG.info(String.format("Trial %4d | Fit: %8.0f | PnL: %6.0f$ | MaxDD: %6.0f$ | RF: %4.1f | Pen: %4.0f$ " +
                            "| Trades: %5d | [D_Big:%.3f, aiR:%.3f, ai15:%.3f, aiMax:%.3f] %s",
                    c, report.finalFitness, report.totalProfit, report.maxDrawdown, report.recoveryFactor, report.penaltyCost,
                    report.tradeCount, db, aiRisk, ai15m, aiMaxThres, report.note));

            return report.finalFitness;
        } catch (Exception e) {
            e.printStackTrace();
            return -10000.0f;
        }
        // 🔥 ĐÃ XÓA SYSTEM.GC() TẠI ĐÂY ĐỂ TRÁNH STOP-THE-WORLD
    }

    // ======================================================================================
    // LOGIC ISLAND MODEL
    // ======================================================================================
    private static ISeq<Phenotype<DoubleGene, Float>> loadInitialPopulationFromAerospike(Genotype<DoubleGene> gtf) {
        try {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, "hpo_master_entry_pool_11p", Configs.TIME_RUN);
            Record record = DataManagerAerospikeFloatSim.getClient226().get(null, key);
            if (record == null || record.getString("pool") == null) return null;

            List<GeneRecord> pool = Utils.gson.fromJson(record.getString("pool"), new TypeToken<List<GeneRecord>>() {
            }.getType());
            if (pool == null || pool.isEmpty()) return null;

            List<Phenotype<DoubleGene, Float>> seedPop = new ArrayList<>();
            for (GeneRecord gr : pool) {
                Genotype<DoubleGene> genotype = Genotype.of(
                        DoubleChromosome.of(DoubleGene.of(gr.ds, -0.020, -0.005)),
                        DoubleChromosome.of(DoubleGene.of(gr.dm, -0.040, -0.021)),
                        DoubleChromosome.of(DoubleGene.of(gr.db, -0.100, -0.041)),
                        DoubleChromosome.of(DoubleGene.of(gr.us, 0.005, 0.020)),
                        DoubleChromosome.of(DoubleGene.of(gr.um, 0.021, 0.040)),
                        DoubleChromosome.of(DoubleGene.of(gr.ub, 0.041, 0.100)),
                        DoubleChromosome.of(DoubleGene.of(gr.d15s, -0.035, -0.015)),
                        DoubleChromosome.of(DoubleGene.of(gr.aiRisk, -0.20, -0.08)),
                        DoubleChromosome.of(DoubleGene.of(gr.ai15m, 0.010, 0.025)),
                        DoubleChromosome.of(DoubleGene.of(gr.ai24h, 0.010, 0.060)),
                        DoubleChromosome.of(DoubleGene.of(gr.aiMaxThres, 0.10, 0.25))
                );
                seedPop.add(Phenotype.of(genotype, 1, gr.score));
            }
            return ISeq.of(seedPop);
        } catch (Exception e) {
            return null;
        }
    }

    private static ISeq<Phenotype<DoubleGene, Float>> syncIslandModelWithAerospike(ISeq<Phenotype<DoubleGene, Float>> population) {
        try {
            Phenotype<DoubleGene, Float> myBest = population.stream().max(Comparator.comparing(Phenotype::fitness)).orElse(null);
            if (myBest == null) return population;

            float myScore = myBest.fitness();
            float mDs = myBest.genotype().get(0).gene().floatValue();
            float mDm = myBest.genotype().get(1).gene().floatValue();
            float mDb = myBest.genotype().get(2).gene().floatValue();
            float mUs = myBest.genotype().get(3).gene().floatValue();
            float mUm = myBest.genotype().get(4).gene().floatValue();
            float mUb = myBest.genotype().get(5).gene().floatValue();
            float mD15s = myBest.genotype().get(6).gene().floatValue();
            float mAiRisk = myBest.genotype().get(7).gene().floatValue();
            float mAi15m = myBest.genotype().get(8).gene().floatValue();
            float mAi24h = myBest.genotype().get(9).gene().floatValue();
            float mAiMaxThres = myBest.genotype().get(10).gene().floatValue();

            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, "hpo_master_entry_pool_11p", Configs.TIME_RUN);
            List<GeneRecord> globalPool = new ArrayList<>();

            int maxRetries = 3;
            for (int attempt = 0; attempt < maxRetries; attempt++) {
                Record record = DataManagerAerospikeFloatSim.getClient226().get(null, key);
                int currentGen = 0;

                if (record != null && record.getString("pool") != null) {
                    currentGen = record.generation;
                    globalPool = Utils.gson.fromJson(record.getString("pool"),
                            new TypeToken<List<GeneRecord>>() {
                            }.getType());
                }

                if (globalPool.size() >= 10 && myScore <= globalPool.get(globalPool.size() - 1).score) break;

                globalPool.add(new GeneRecord(mDs, mDm, mDb, mUs, mUm, mUb, mD15s, mAiRisk, mAi15m, mAi24h, mAiMaxThres, myScore));
                globalPool.sort((a, b) -> Float.compare(b.score, a.score));

                // 🔥 LỌC TRÙNG LẶP TRÊN 4 TRỤ CỘT CHÍNH
                // Tránh giết nhầm Gen xịn (Euclidean Distance đơn giản hóa)
                List<GeneRecord> uniquePool = new ArrayList<>();
                for (GeneRecord g : globalPool) {
                    boolean isDup = false;
                    for (GeneRecord u : uniquePool) {
                        if (Math.abs(g.ds - u.ds) < 0.0001 &&
                                Math.abs(g.db - u.db) < 0.0001 &&
                                Math.abs(g.aiRisk - u.aiRisk) < 0.0001 &&
                                Math.abs(g.aiMaxThres - u.aiMaxThres) < 0.0001) {
                            isDup = true;
                            break;
                        }
                    }
                    if (!isDup) uniquePool.add(g);
                }

                if (uniquePool.size() > 10) uniquePool = uniquePool.subList(0, 10);
                globalPool = uniquePool;

                WritePolicy wp = new WritePolicy();
                wp.sendKey = true;
                if (record != null) {
                    wp.generationPolicy = com.aerospike.client.policy.GenerationPolicy.EXPECT_GEN_EQUAL;
                    wp.generation = currentGen;
                }

                try {
                    DataManagerAerospikeFloatSim.getClient226().put(wp, key, new com.aerospike.client.Bin("pool", Utils.gson.toJson(globalPool)));
                    break;
                } catch (com.aerospike.client.AerospikeException e) {
                    if (e.getResultCode() == com.aerospike.client.ResultCode.GENERATION_ERROR) continue;
                    throw e;
                }
            }

            List<Phenotype<DoubleGene, Float>> popList = new ArrayList<>(population.asList());
            popList.sort(Comparator.comparing(Phenotype::fitness));

            int replacedCount = 0;
            for (GeneRecord img : globalPool) {
                if (img.score > myScore || (img.score == myScore && img.ds != mDs)) {
                    Genotype<DoubleGene> newGt = Genotype.of(
                            DoubleChromosome.of(DoubleGene.of(img.ds, -0.020, -0.005)),
                            DoubleChromosome.of(DoubleGene.of(img.dm, -0.040, -0.021)),
                            DoubleChromosome.of(DoubleGene.of(img.db, -0.100, -0.041)),
                            DoubleChromosome.of(DoubleGene.of(img.us, 0.005, 0.020)),
                            DoubleChromosome.of(DoubleGene.of(img.um, 0.021, 0.040)),
                            DoubleChromosome.of(DoubleGene.of(img.ub, 0.041, 0.100)),
                            DoubleChromosome.of(DoubleGene.of(img.d15s, -0.035, -0.015)),
                            DoubleChromosome.of(DoubleGene.of(img.aiRisk, -0.20, -0.08)),
                            DoubleChromosome.of(DoubleGene.of(img.ai15m, 0.010, 0.025)),
                            DoubleChromosome.of(DoubleGene.of(img.ai24h, 0.010, 0.060)),
                            DoubleChromosome.of(DoubleGene.of(img.aiMaxThres, 0.10, 0.25))
                    );
                    popList.set(replacedCount++, Phenotype.of(newGt, 1));

                    // 🔥 LOG CHI TIẾT GEN NHẬP CƯ
                    LOG.info("🛸 Nhập cư Gen Tinh Hoa (Score: {:.2f} | D_Big: {:.3f} | aiRisk: {:.3f} | aiMax: {:.3f})",
                            img.score, img.db, img.aiRisk, img.aiMaxThres);

                    if (replacedCount >= 3) break;
                }
            }
            return ISeq.of(popList);
        } catch (Exception e) {
            return population;
        }
    }

    private static void loadKaggleData() {
        time2MarketData = KaggleDataLoader.loadMarketData();
        predictionMap = KaggleDataLoader.loadAiPred();
        time2FundingPre = KaggleDataLoader.loadFundingPred();
    }

    private static void printFinalResult(EvolutionResult<DoubleGene, Float> result, long startTime) {
        Genotype<DoubleGene> best = result.bestPhenotype().genotype();
        LOG.info("\n=============================================");
        LOG.info("=== KẾT QUẢ MASTER ENTRY LOGIC (11 PARAMS) ===");
        LOG.info("Fitness tốt nhất: {}", String.format("%.4f", result.bestFitness()));
        LOG.info("MS_DOWN_SMALL_AVG = {}f;", String.format("%.5f", best.get(0).gene().floatValue()));
        LOG.info("MS_DOWN_MED_AVG   = {}f;", String.format("%.5f", best.get(1).gene().floatValue()));
        LOG.info("MS_DOWN_BIG_AVG   = {}f;", String.format("%.5f", best.get(2).gene().floatValue()));
        LOG.info("MS_UP_SMALL_THRES = {}f;", String.format("%.5f", best.get(3).gene().floatValue()));
        LOG.info("MS_UP_MED_THRES   = {}f;", String.format("%.5f", best.get(4).gene().floatValue()));
        LOG.info("MS_UP_BIG_THRES   = {}f;", String.format("%.5f", best.get(5).gene().floatValue()));
        LOG.info("MS_DOWN_15M_SMALL = {}f;", String.format("%.5f", best.get(6).gene().floatValue()));
        LOG.info("HARD_RISK_LIMIT_4H = {}f;", String.format("%.5f", best.get(7).gene().floatValue()));
        LOG.info("MIN_MOMENTUM_15M   = {}f;", String.format("%.5f", best.get(8).gene().floatValue()));
        LOG.info("MIN_MOMENTUM_24H   = {}f;", String.format("%.5f", best.get(9).gene().floatValue()));
        LOG.info("PREDICT_SYMBOL_RATE_MAX_THRESHOLD = {}f;", String.format("%.5f", best.get(10).gene().floatValue()));
        LOG.info("=============================================");
    }
}