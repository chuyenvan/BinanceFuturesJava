package com.binance.chuyennd.ai_ml.hpo.general;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.HPOSmartCache;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculator;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import io.jenetics.*;
import io.jenetics.engine.Engine;
import io.jenetics.engine.EvolutionResult;
import io.jenetics.util.DoubleRange;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.TreeMap;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class RunOptimizationDynamicFilter {
    public static final Logger LOG = LoggerFactory.getLogger(RunOptimizationDynamicFilter.class);
    private static final int POPULATION_SIZE = 15;
    private static final int GENERATIONS = 30;

    private static final AtomicLong testCounter = new AtomicLong(0);
    private static final long TOTAL_TRIALS = (long) POPULATION_SIZE * GENERATIONS;

    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static TreeMap<Long, long[]> time2FundingPre;

    private static final java.util.concurrent.ConcurrentHashMap<String, Float> fitnessCache = new java.util.concurrent.ConcurrentHashMap<>();

    private static float evaluate(Genotype<DoubleGene> genotype) {
        long currentTest = testCounter.incrementAndGet();

        float multiplier = genotype.get(0).gene().floatValue();
        float minScale = genotype.get(1).gene().floatValue();
        float maxScale = genotype.get(2).gene().floatValue();

        // Đảm bảo Min không bao giờ lớn hơn Max (nếu lai tạo ngẫu nhiên bị lỗi)
        if (minScale > maxScale) {
            float temp = minScale;
            minScale = maxScale;
            maxScale = temp;
        }

        String cacheKey = String.format("%.5f_%.5f_%.5f", multiplier, minScale, maxScale);

        if (fitnessCache.containsKey(cacheKey)) {
            float cachedScore = fitnessCache.get(cacheKey);
            LOG.info(String.format("Trial %4d/%d | CACHED | Score: %8.1f | Mult: %.5f | Min: %.5f | Max: %.5f",
                    currentTest, TOTAL_TRIALS, cachedScore, multiplier, minScale, maxScale));
            return cachedScore;
        }

        try {
            BackTestEngineDynamicFilter engine = new BackTestEngineDynamicFilter(multiplier, minScale, maxScale);
            HPOFitnessCalculator.FitnessReport report = engine.run(time2MarketData, predictionMap, time2FundingPre);

            // ========================================================
            // 🔥 LUẬT THÉP: CHỐNG LẠI SỰ BÙNG NỔ DRAWDOWN
            // ========================================================
            float maxAllowedDrawdown = -6500f; // Điền ngưỡng MaxDD mà bạn chấp nhận được (VD: -6500$)
            if (report.maxDrawdown < maxAllowedDrawdown) {
                float excessDrawdown = Math.abs(report.maxDrawdown) - Math.abs(maxAllowedDrawdown);
                // Cứ lố 1$ DD thì phạt 5 điểm -> Ép AI dồn về những bộ số an toàn
                report.finalFitness = report.finalFitness - (excessDrawdown * 5f);
                report.note = "PENALTY: Over MaxDD";
            }

            LOG.info(String.format("Trial %4d/%d | Score: %8.1f | Trades: %4d | PnL: %6.1f$ | MaxDD: %6.1f$ | Pen: %4.1f$ | Mult: %.5f | Min: %.5f | Max: %.5f | %s",
                    currentTest, TOTAL_TRIALS, report.finalFitness,
                    report.tradeCount, report.totalProfit, report.maxDrawdown,
                    report.penaltyCost, multiplier, minScale, maxScale, report.note));

            fitnessCache.put(cacheKey, report.finalFitness);

            return report.finalFitness;

        } catch (Exception e) {
            e.printStackTrace();
            return -10000.0f;
        } finally {
            System.gc();
        }
    }

    public static void main(String[] args) throws Exception {
        LOG.info("=== BẮT ĐẦU TỐI ƯU AI DYNAMIC FILTER (3 PARAMS) ===");

        Configs.IS_HPO_MODE = false;
        Configs.TIME_RUN = "20251001";

        loadAndWarmUpData();

        long startTime = System.currentTimeMillis();

        // Định nghĩa vùng tìm kiếm Gen cho 3 tham số
        Genotype<DoubleGene> genotypeFactory = Genotype.of(
                DoubleChromosome.of(DoubleRange.of(0.5, 3.0)),   // 0: Multiplier (Từ 0.5x đến 3.0x)
                DoubleChromosome.of(DoubleRange.of(0.1, 1.0)),   // 1: Min Scale (Ngưỡng hạ chuẩn sâu nhất)
                DoubleChromosome.of(DoubleRange.of(0.5, 3.0))    // 2: Max Scale (Ngưỡng siết chuẩn gắt nhất)
        );

        // BỘ ENGINE TIẾN HÓA
        Engine<DoubleGene, Float> engine = Engine
                .builder(RunOptimizationDynamicFilter::evaluate, genotypeFactory)
                .populationSize(POPULATION_SIZE)
                .maximizing()
                .survivorsSelector(new io.jenetics.TournamentSelector<>(3))
                .offspringSelector(new io.jenetics.RouletteWheelSelector<>())
                .alterers(
                        new io.jenetics.UniformCrossover<>(0.7),
                        new io.jenetics.GaussianMutator<>(0.15),
                        new io.jenetics.Mutator<>(0.05)
                )
                .executor(Executors.newSingleThreadExecutor())
                .build();

        EvolutionResult<DoubleGene, Float> result = engine.stream()
                .limit(GENERATIONS)
                .peek(r -> LOG.info(String.format("\n>>> 🏆 BEST GEN %d/%d | SCORE: %.2f <<<\n", r.generation(), GENERATIONS, r.bestFitness())))
                .collect(EvolutionResult.toBestEvolutionResult());

        printResult(result, startTime);
    }

    private static void loadAndWarmUpData() throws Exception {
        LOG.info("Loading Data... {}", Configs.TIME_RUN);
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        int numberMinutes = System.currentTimeMillis() - startTime > 0 ? (int) ((System.currentTimeMillis() - startTime) / Utils.TIME_MINUTE) : 0;

        time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        time2FundingPre = DataManagerAerospikeFloatSim.getFundingPredictionsPrimitiveByRange(startTime, numberMinutes);

        LOG.info("🔥 Warming up cache ({}-NOW)...", Configs.TIME_RUN);
        long startTimeLoad = Utils.sdfFile.parse(Configs.TIME_RUN).getTime();
        long endTimeLoad = System.currentTimeMillis();
        long current = startTimeLoad;
        while (current < endTimeLoad) {
            HPOSmartCache.getData(current);
            current += Utils.TIME_DAY;
        }
        LOG.info("✅ Data Ready.");
    }

    private static void printResult(EvolutionResult<DoubleGene, Float> result, long startTime) {
        Genotype<DoubleGene> best = result.bestPhenotype().genotype();
        float multiplier = best.get(0).gene().floatValue();
        float minScale = best.get(1).gene().floatValue();
        float maxScale = best.get(2).gene().floatValue();

        if (minScale > maxScale) {
            float temp = minScale;
            minScale = maxScale;
            maxScale = temp;
        }

        LOG.info("\n=======================================================");
        LOG.info("=== KẾT QUẢ TỐI ƯU AI DYNAMIC FILTER (3 PARAMS) ===");
        LOG.info("Time: {} mins", Duration.ofMillis(System.currentTimeMillis() - startTime).toMinutes());
        LOG.info("Profit Max: {}", String.format("%.2f", result.bestFitness()));
        LOG.info("-------------------------------------------------------");
        LOG.info("Configs.AI_DYNAMIC_MULTIPLIER : {}f;", String.format("%.5f", multiplier));
        LOG.info("Configs.AI_DYNAMIC_MIN        : {}f;", String.format("%.5f", minScale));
        LOG.info("Configs.AI_DYNAMIC_MAX        : {}f;", String.format("%.5f", maxScale));
        LOG.info("=======================================================");
    }
}