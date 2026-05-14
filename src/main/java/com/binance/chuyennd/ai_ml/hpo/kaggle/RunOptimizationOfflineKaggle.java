package com.binance.chuyennd.ai_ml.hpo.kaggle;

import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculator;
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

public class RunOptimizationOfflineKaggle {

    private static final Logger LOG = LoggerFactory.getLogger(RunOptimizationOfflineKaggle.class);

    private static final int POPULATION_SIZE = 30;
    private static final int GENERATIONS = 30;
    private static final AtomicLong testCounter = new AtomicLong(0);

    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static TreeMap<Long, long[]> time2FundingPre;
    public static long offlineStartTime;
    public static long offlineEndTime;

    static class GeneRecord {
        public float p15M;
        public float p24H;
        public float score;
        public GeneRecord(float p15M, float p24H, float score) {
            this.p15M = p15M; this.p24H = p24H; this.score = score;
        }
    }

    public static void main(String[] args) {
        LOG.info("=== BẮT ĐẦU TỐI ƯU HÓA HPO (ISLAND MODEL - KAGGLE OFFLINE CHUNK) ===");
        try {
            Configs.IS_HPO_MODE = true;
            Configs.IS_KAGGLE_MODE = true;

            Configs.TIME_RUN = "20251001";

            offlineStartTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + (7 * Utils.TIME_HOUR);
            offlineEndTime = Utils.sdfFile.parse("20260430").getTime() + (24 * Utils.TIME_HOUR) - Utils.TIME_MINUTE;

            loadKaggleData();
        } catch (Exception e) {
            e.printStackTrace();
            return;
        }

        Genotype<DoubleGene> gtf = Genotype.of(
                DoubleChromosome.of(DoubleRange.of(0.01, 0.025)), // 0: MIN_MOMENTUM_15M
                DoubleChromosome.of(DoubleRange.of(0.01, 0.09))    // 1: MIN_MOMENTUM_24H
        );

        Engine<DoubleGene, Float> engine = Engine.builder(RunOptimizationOfflineKaggle::eval, gtf)
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
                    LOG.info("🚀 Warm-start: Bắt đầu Gen 1 từ tinh hoa đã có trên Aerospike.");
                    result = engine.stream(initialPopulation).limit(1).collect(EvolutionResult.toBestEvolutionResult());
                } else {
                    LOG.info("🌱 Không có dữ liệu cũ, khởi tạo Gen 1 ngẫu nhiên.");
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
                LOG.info("🛑 KÍCH HOẠT EARLY STOPPING: Điểm số đã đi ngang (hội tụ) trong {} thế hệ liên tiếp. Tiết kiệm thời gian, dừng chương trình!", MAX_STEADY_GENERATIONS);
                break;
            }
        }

        printFinalResult(result, startTime);
    }

    private static Float eval(Genotype<DoubleGene> gt) {
        long c = testCounter.incrementAndGet();

        float pMin15M = gt.get(0).gene().floatValue();
        float pMin24H = gt.get(1).gene().floatValue();

        try {
            // 🔥 GỌI ENGINE OFFLINE ĐỂ TRÁNH THẮT CỔ CHAI AEROSPIKE I/O
            BackTestEngineOfflineKaggle engine = new BackTestEngineOfflineKaggle(pMin15M, pMin24H);

            HPOFitnessCalculator.FitnessReport report = engine.run(time2MarketData, predictionMap, time2FundingPre, offlineStartTime, offlineEndTime);

            float maxAllowedDrawdown = -15000f;
            if (report.maxDrawdown < maxAllowedDrawdown) {
                float excessDrawdown = Math.abs(report.maxDrawdown) - Math.abs(maxAllowedDrawdown);
                report.finalFitness = report.finalFitness - (excessDrawdown * 5f);
                report.note = "PENALTY: Over MaxDD";
            }

            LOG.info(String.format("Trial %4d | Score: %8.1f | Trades: %4d | PnL: %6.1f$ | MaxDD: %6.1f$ | Pen: %4.1f$ | 15M: %.5f | 24H: %.5f | %s",
                    c, report.finalFitness,
                    report.tradeCount, report.totalProfit, report.maxDrawdown,
                    report.penaltyCost, pMin15M, pMin24H, report.note));

            return report.finalFitness;

        } catch (Exception e) {
            e.printStackTrace();
            return -10000.0f;
        } finally {
            System.gc();
        }
    }

    private static ISeq<Phenotype<DoubleGene, Float>> loadInitialPopulationFromAerospike(Genotype<DoubleGene> gtf) {
        try {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, "hpo_island_pool", Configs.TIME_RUN);
            Record record = DataManagerAerospikeFloatSim.getClient226().get(null, key);
            if (record == null) return null;

            String json = record.getString("pool");
            if (json == null) return null;

            List<GeneRecord> pool = Utils.gson.fromJson(json, new TypeToken<List<GeneRecord>>(){}.getType());
            if (pool == null || pool.isEmpty()) return null;

            LOG.info("📥 Tìm thấy {} hạt giống tinh hoa trên mạng để khởi động.", pool.size());

            List<Phenotype<DoubleGene, Float>> seedPop = new ArrayList<>();
            for (GeneRecord gr : pool) {
                Genotype<DoubleGene> genotype = Genotype.of(
                        DoubleChromosome.of(DoubleGene.of(gr.p15M, 0.012, 0.025)),
                        DoubleChromosome.of(DoubleGene.of(gr.p24H, 0.01, 0.06))
                );
                seedPop.add(Phenotype.of(genotype, 1, gr.score));
            }
            return ISeq.of(seedPop);
        } catch (Exception e) {
            LOG.warn("⚠️ Không thể Warm-start: " + e.getMessage());
            return null;
        }
    }

    private static ISeq<Phenotype<DoubleGene, Float>> syncIslandModelWithAerospike(ISeq<Phenotype<DoubleGene, Float>> population) {
        try {
            Phenotype<DoubleGene, Float> myBest = population.stream().max(Comparator.comparing(Phenotype::fitness)).orElse(null);
            if (myBest == null) return population;

            float myScore = myBest.fitness();
            float my15M = myBest.genotype().get(0).gene().floatValue();
            float my24H = myBest.genotype().get(1).gene().floatValue();

            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, "hpo_island_pool", Configs.TIME_RUN);
            List<GeneRecord> globalPool = new ArrayList<>();

            int maxRetries = 3;
            for (int attempt = 0; attempt < maxRetries; attempt++) {
                Record record = DataManagerAerospikeFloatSim.getClient226().get(null, key);
                int currentGen = 0;

                if (record != null) {
                    currentGen = record.generation;
                    String json = record.getString("pool");
                    if (json != null) {
                        globalPool = Utils.gson.fromJson(json, new TypeToken<List<GeneRecord>>(){}.getType());
                    }
                }

                if (globalPool.size() >= 10 && myScore <= globalPool.get(globalPool.size() - 1).score) {
                    break;
                }

                globalPool.add(new GeneRecord(my15M, my24H, myScore));
                globalPool.sort((a, b) -> Float.compare(b.score, a.score));

                List<GeneRecord> uniquePool = new ArrayList<>();
                for (GeneRecord g : globalPool) {
                    boolean isDup = false;
                    for (GeneRecord u : uniquePool) {
                        if (Math.abs(g.p15M - u.p15M) < 0.0001 && Math.abs(g.p24H - u.p24H) < 0.0001) {
                            isDup = true; break;
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
                    if (e.getResultCode() == com.aerospike.client.ResultCode.GENERATION_ERROR) {
                        LOG.warn("⚠️ Đụng độ ghi Aerospike (CAS)! Đang thử lại ({}/{})", attempt + 1, maxRetries);
                        continue;
                    }
                    throw e;
                }
            }

            List<Phenotype<DoubleGene, Float>> popList = new ArrayList<>(population.asList());
            popList.sort(Comparator.comparing(Phenotype::fitness));

            int replacedCount = 0;
            for (GeneRecord immigrant : globalPool) {
                if (immigrant.score > myScore || (immigrant.score == myScore && (immigrant.p15M != my15M || immigrant.p24H != my24H))) {

                    Genotype<DoubleGene> newGt = Genotype.of(
                            DoubleChromosome.of(DoubleGene.of(immigrant.p15M, 0.012, 0.025)),
                            DoubleChromosome.of(DoubleGene.of(immigrant.p24H, 0.01, 0.06))
                    );

                    popList.set(replacedCount, Phenotype.of(newGt, 1));
                    replacedCount++;

                    LOG.info("🛸 Đã tiếp nhận Gen Tinh Hoa từ mảng (Score: {}, 15M: {}, 24H: {})",
                            String.format("%.2f", immigrant.score), immigrant.p15M, immigrant.p24H);

                    if (replacedCount >= 3) break;
                }
            }
            return ISeq.of(popList);

        } catch (Exception e) {
            LOG.error("❌ Lỗi mạng khi đồng bộ Island Model: {}", e.getMessage());
            return population;
        }
    }

    private static void loadKaggleData() {
        LOG.info("📥 Loading Offline Core Data from kaggle_data_hpo/...");
        time2MarketData = KaggleDataLoader.loadMarketData();
        predictionMap = KaggleDataLoader.loadAiPred();
        time2FundingPre = KaggleDataLoader.loadFundingPred();

        if (time2MarketData == null) {
            throw new RuntimeException("❌ KHÔNG TÌM THẤY DỮ LIỆU! Kiểm tra thư mục kaggle_data_hpo/");
        }
        LOG.info("✅ Core Data Ready. Đã chốt thời gian mô phỏng đến {}", Utils.normalizeDateYYYYMMDDHHmm(offlineEndTime));
    }

    private static void printFinalResult(EvolutionResult<DoubleGene, Float> result, long startTime) {
        Genotype<DoubleGene> best = result.bestPhenotype().genotype();
        LOG.info("\n=============================================");
        LOG.info("=== KẾT QUẢ TỐI ƯU HÓA HPO (ISLAND MODEL) ===");
        LOG.info("Thời gian chạy: {} phút", Duration.ofMillis(System.currentTimeMillis() - startTime).toMinutes());
        LOG.info("Fitness tốt nhất: {}", String.format("%.4f", result.bestFitness()));
        LOG.info("---------------------------------------------");
        LOG.info("MIN_MOMENTUM_15M   = {}f;", String.format("%.5f", best.get(0).gene().floatValue()));
        LOG.info("MIN_MOMENTUM_24H   = {}f;", String.format("%.5f", best.get(1).gene().floatValue()));
        LOG.info("=============================================");
    }
}