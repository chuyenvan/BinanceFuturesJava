package com.binance.chuyennd.ai_ml.hpo.kaggle;

import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculator;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import com.google.gson.reflect.TypeToken;
import io.jenetics.*;
import io.jenetics.engine.Engine;
import io.jenetics.engine.EvolutionResult;
import io.jenetics.util.DoubleRange;
import io.jenetics.util.ISeq;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class RunHpoPhase1_MarketThresholds {

    private static final Logger LOG = LoggerFactory.getLogger(RunHpoPhase1_MarketThresholds.class);

    private static final int POPULATION_SIZE = 30;
    private static final int GENERATIONS = 30;
    private static final AtomicLong testCounter = new AtomicLong(0);

    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static TreeMap<Long, long[]> time2FundingPre;
    public static long offlineEndTime;

    // 🔥 CẤU TRÚC GEN 6 CHIỀU (Market Thresholds)
    static class GeneRecord {
        public float ds, dm, db, us, um, ub;
        public float score;
        public GeneRecord(float ds, float dm, float db, float us, float um, float ub, float score) {
            this.ds = ds; this.dm = dm; this.db = db;
            this.us = us; this.um = um; this.ub = ub;
            this.score = score;
        }
    }

    public static void main(String[] args) {
        LOG.info("=== BẮT ĐẦU VÒNG 1: TỐI ƯU HÓA NHẬN DIỆN THỊ TRƯỜNG (6 THAM SỐ) ===");
        try {
            Configs.IS_HPO_MODE = true;
            Configs.IS_KAGGLE_MODE = true;
            Configs.TIME_RUN = "20251001";
            offlineEndTime = Utils.sdfFile.parse("20260430").getTime() + (24 * Utils.TIME_HOUR) - Utils.TIME_MINUTE;
            loadKaggleData();
        } catch (Exception e) {
            e.printStackTrace();
            return;
        }

        // 🔥 RÀNG BUỘC KHÔNG GIAN DÒ TÌM (Non-overlapping) để tránh ngáo thuật toán
        Genotype<DoubleGene> gtf = Genotype.of(
                DoubleChromosome.of(DoubleRange.of(-0.020, -0.005)), // 0: Down Small
                DoubleChromosome.of(DoubleRange.of(-0.040, -0.021)), // 1: Down Med
                DoubleChromosome.of(DoubleRange.of(-0.100, -0.041)), // 2: Down Big
                DoubleChromosome.of(DoubleRange.of(0.005, 0.020)),   // 3: Up Small
                DoubleChromosome.of(DoubleRange.of(0.021, 0.040)),   // 4: Up Med
                DoubleChromosome.of(DoubleRange.of(0.041, 0.100))    // 5: Up Big
        );

        Engine<DoubleGene, Float> engine = Engine.builder(RunHpoPhase1_MarketThresholds::eval, gtf)
                .populationSize(POPULATION_SIZE)
                .maximizing()
                .alterers(new Mutator<>(0.15), new MeanAlterer<>(0.60))
                .executor(Executors.newSingleThreadExecutor())
                .build();

        long startTime = System.currentTimeMillis();
        EvolutionResult<DoubleGene, Float> result = null;
        float globalBestScore = -Float.MAX_VALUE;
        int steadyCount = 0;
        final int MAX_STEADY_GENERATIONS = 5;

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
                ISeq<Phenotype<DoubleGene, Float>> currentPop = syncIslandModelWithAerospike(result.population());
                result = engine.stream(currentPop).limit(1).collect(EvolutionResult.toBestEvolutionResult());
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
                LOG.info("🛑 KÍCH HOẠT EARLY STOPPING: Thuật toán đã hội tụ!");
                break;
            }
        }
        printFinalResult(result, startTime);
    }

    private static Float eval(Genotype<DoubleGene> gt) {
        long c = testCounter.incrementAndGet();

        float ds = gt.get(0).gene().floatValue();
        float dm = gt.get(1).gene().floatValue();
        float db = gt.get(2).gene().floatValue();
        float us = gt.get(3).gene().floatValue();
        float um = gt.get(4).gene().floatValue();
        float ub = gt.get(5).gene().floatValue();

        try {
            com.binance.chuyennd.ai_ml.hpo.kaggle.BackTestEngineMarketThresholds engine = new com.binance.chuyennd.ai_ml.hpo.kaggle.BackTestEngineMarketThresholds(ds, dm, db, us, um, ub);
            HPOFitnessCalculator.FitnessReport report = engine.run(time2MarketData, predictionMap, time2FundingPre, offlineEndTime);

            // Phạt nếu Drawdown vượt ngưỡng
            float maxAllowedDrawdown = -15000f;
            if (report.maxDrawdown < maxAllowedDrawdown) {
                float excessDrawdown = Math.abs(report.maxDrawdown) - Math.abs(maxAllowedDrawdown);
                report.finalFitness = report.finalFitness - (excessDrawdown * 5f);
                report.note = "PENALTY: Over MaxDD";
            }

            LOG.info(String.format("Trial %4d | Score: %8.1f | PnL: %6.1f$ | MaxDD: %6.1f$ | D(Sm:%.3f, Md:%.3f, Bg:%.3f) | %s",
                    c, report.finalFitness, report.totalProfit, report.maxDrawdown, ds, dm, db, report.note));

            return report.finalFitness;
        } catch (Exception e) {
            e.printStackTrace();
            return -10000.0f;
        } finally {
            System.gc();
        }
    }

    // ======================================================================================
    // LOGIC ISLAND MODEL CHO 6 THAM SỐ (DÙNG KEY RIÊNG: hpo_market_thres_pool)
    // ======================================================================================
    private static ISeq<Phenotype<DoubleGene, Float>> loadInitialPopulationFromAerospike(Genotype<DoubleGene> gtf) {
        try {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, "hpo_market_thres_pool", Configs.TIME_RUN);
            Record record = DataManagerAerospikeFloatSim.getClient226().get(null, key);
            if (record == null || record.getString("pool") == null) return null;

            List<GeneRecord> pool = Utils.gson.fromJson(record.getString("pool"), new TypeToken<List<GeneRecord>>(){}.getType());
            if (pool == null || pool.isEmpty()) return null;

            List<Phenotype<DoubleGene, Float>> seedPop = new ArrayList<>();
            for (GeneRecord gr : pool) {
                Genotype<DoubleGene> genotype = Genotype.of(
                        DoubleChromosome.of(DoubleGene.of(gr.ds, -0.020, -0.005)),
                        DoubleChromosome.of(DoubleGene.of(gr.dm, -0.040, -0.021)),
                        DoubleChromosome.of(DoubleGene.of(gr.db, -0.100, -0.041)),
                        DoubleChromosome.of(DoubleGene.of(gr.us, 0.005, 0.020)),
                        DoubleChromosome.of(DoubleGene.of(gr.um, 0.021, 0.040)),
                        DoubleChromosome.of(DoubleGene.of(gr.ub, 0.041, 0.100))
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

            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, "hpo_market_thres_pool", Configs.TIME_RUN);
            List<GeneRecord> globalPool = new ArrayList<>();

            int maxRetries = 3;
            for (int attempt = 0; attempt < maxRetries; attempt++) {
                Record record = DataManagerAerospikeFloatSim.getClient226().get(null, key);
                int currentGen = 0;

                if (record != null && record.getString("pool") != null) {
                    currentGen = record.generation;
                    globalPool = Utils.gson.fromJson(record.getString("pool"), new TypeToken<List<GeneRecord>>(){}.getType());
                }

                if (globalPool.size() >= 10 && myScore <= globalPool.get(globalPool.size() - 1).score) break;

                globalPool.add(new GeneRecord(mDs, mDm, mDb, mUs, mUm, mUb, myScore));
                globalPool.sort((a, b) -> Float.compare(b.score, a.score));

                // Lọc trùng lặp trên 6 chiều
                List<GeneRecord> uniquePool = new ArrayList<>();
                for (GeneRecord g : globalPool) {
                    boolean isDup = false;
                    for (GeneRecord u : uniquePool) {
                        if (Math.abs(g.ds - u.ds) < 0.0001 && Math.abs(g.us - u.us) < 0.0001) {
                            isDup = true; break;
                        }
                    }
                    if (!isDup) uniquePool.add(g);
                }

                if (uniquePool.size() > 10) uniquePool = uniquePool.subList(0, 10);
                globalPool = uniquePool;

                WritePolicy wp = new WritePolicy(); wp.sendKey = true;
                if (record != null) { wp.generationPolicy = com.aerospike.client.policy.GenerationPolicy.EXPECT_GEN_EQUAL; wp.generation = currentGen; }

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
                            DoubleChromosome.of(DoubleGene.of(img.ub, 0.041, 0.100))
                    );
                    popList.set(replacedCount++, Phenotype.of(newGt, 1));
                    LOG.info("🛸 Nhập cư Gen Tinh Hoa (Score: {:.2f}, D_Big: {:.3f})", img.score, img.db);
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
        LOG.info("=== KẾT QUẢ VÒNG 1: MARKET THRESHOLDS (6 PARAMS) ===");
        LOG.info("Fitness tốt nhất: {}", String.format("%.4f", result.bestFitness()));
        LOG.info("MS_DOWN_SMALL_AVG = {}f;", String.format("%.5f", best.get(0).gene().floatValue()));
        LOG.info("MS_DOWN_MED_AVG   = {}f;", String.format("%.5f", best.get(1).gene().floatValue()));
        LOG.info("MS_DOWN_BIG_AVG   = {}f;", String.format("%.5f", best.get(2).gene().floatValue()));
        LOG.info("MS_UP_SMALL_THRES = {}f;", String.format("%.5f", best.get(3).gene().floatValue()));
        LOG.info("MS_UP_MED_THRES   = {}f;", String.format("%.5f", best.get(4).gene().floatValue()));
        LOG.info("MS_UP_BIG_THRES   = {}f;", String.format("%.5f", best.get(5).gene().floatValue()));
        LOG.info("=============================================");
    }
}