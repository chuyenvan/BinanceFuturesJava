package com.binance.chuyennd.ai_ml.hpo.general;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.HPOSmartCache;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculator;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.tradecore.Configs;
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

public class RunOptimizationTrailingStop {
    public static final Logger LOG = LoggerFactory.getLogger(RunOptimizationTrailingStop.class);
    private static final int POPULATION_SIZE = 15;
    private static final int GENERATIONS = 30;

    private static final AtomicLong testCounter = new AtomicLong(0);
    private static final long TOTAL_TRIALS = (long) POPULATION_SIZE * GENERATIONS;

    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static TreeMap<Long, long[]> time2FundingPre;

    // Thêm biến này ở trên cùng của Class
    private static final java.util.concurrent.ConcurrentHashMap<String, Float> fitnessCache = new java.util.concurrent.ConcurrentHashMap<>();

    private static float evaluate(Genotype<DoubleGene> genotype) {
        long currentTest = testCounter.incrementAndGet();

        float baseRate = genotype.get(0).gene().floatValue();
        float dynamicK = genotype.get(1).gene().floatValue();
        float profitMultiplier = genotype.get(2).gene().floatValue();

        // 🔥 TẠO CHÌA KHÓA CACHE (Làm tròn đến 5 chữ số thập phân)
        String cacheKey = String.format("%.5f_%.5f_%.5f", baseRate, dynamicK, profitMultiplier);

        // NẾU ĐÃ CHẠY RỒI -> TRẢ VỀ KẾT QUẢ LUÔN, KHÔNG BACKTEST NỮA
        if (fitnessCache.containsKey(cacheKey)) {
            float cachedScore = fitnessCache.get(cacheKey);
            LOG.info("Trial {:4d}/{} | CACHED | Score: {:8.1f} | Base: {:.5f} | K: {:.5f} | Mult: {:.5f}",
                    currentTest, TOTAL_TRIALS, cachedScore, baseRate, dynamicK, profitMultiplier);
            return cachedScore;
        }

        try {
            BackTestEngineTrailingStop engine = new BackTestEngineTrailingStop(baseRate, dynamicK, profitMultiplier);
            HPOFitnessCalculator.FitnessReport report = engine.run(time2MarketData, predictionMap, time2FundingPre);

            // ========================================================
            // 🔥 LUẬT THÉP: SOFT PENALTY (PHẠT CÓ ĐỘ DỐC)
            // ========================================================
            float maxAllowedDrawdown = -10000f; // Ngưỡng Drawdown
            if (report.maxDrawdown < maxAllowedDrawdown) {
                float excessDrawdown = Math.abs(report.maxDrawdown) - Math.abs(maxAllowedDrawdown);
                report.finalFitness = report.finalFitness - (excessDrawdown * 5f);
                report.note = "PENALTY: Over MaxDD";
            }

            LOG.info(String.format("Trial %4d/%d | Score: %8.1f | Trades: %4d | PnL: %6.1f$ | MaxDD: %6.1f$ | Pen: %4.1f$ | Base: %.5f | K: %.5f | Mult: %.5f | %s",
                    currentTest, TOTAL_TRIALS, report.finalFitness,
                    report.tradeCount, report.totalProfit, report.maxDrawdown,
                    report.penaltyCost, baseRate, dynamicK, profitMultiplier, report.note));
            // 🔥 LƯU VÀO CACHE TRƯỚC KHI RETURN
            fitnessCache.put(cacheKey, report.finalFitness);

            return report.finalFitness;

        } catch (Exception e) {
            e.printStackTrace();
            return -10000.0f;
        }
    }
    public static void main(String[] args) throws Exception {
        LOG.info("=== BẮT ĐẦU TỐI ƯU TRAILING STOP ĐỘNG (3 PARAMS) ===");

        // TẮT ĐỂ GIỮ LỊCH SỬ LỆNH CHO CALCULATOR ĐẾM TRADES
        Configs.IS_HPO_MODE = false;
        Configs.TIME_RUN = "20251001";

        loadAndWarmUpData();

        long startTime = System.currentTimeMillis();

        // Dải tìm kiếm tham số Trailing
        Genotype<DoubleGene> genotypeFactory = Genotype.of(
                DoubleChromosome.of(DoubleRange.of(0.008, 0.03)), // 0: Base Rate
                DoubleChromosome.of(DoubleRange.of(0.1, 6.0)),    // 1: Dynamic K
                DoubleChromosome.of(DoubleRange.of(1.5, 5.0))     // 2: Profit Multiplier
        );

        // ÁP DỤNG ENGINE COMBO 3 ALTERERS CHUYÊN TRỊ FLOAT XGBOOST
        Engine<DoubleGene, Float> engine = Engine
                .builder(RunOptimizationTrailingStop::evaluate, genotypeFactory)
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
        LOG.info("\n=======================================================");
        LOG.info("=== KẾT QUẢ TỐI ƯU TRAILING STOP ĐỘNG (3 PARAMS) ===");
        LOG.info("Time: {} mins", Duration.ofMillis(System.currentTimeMillis() - startTime).toMinutes());
        LOG.info("Profit Max: {}", String.format("%.2f", result.bestFitness()));
        LOG.info("-------------------------------------------------------");
        LOG.info("Configs.RATE_PROFIT_STOP_MARKET (Base) : {}f;", String.format("%.5f", best.get(0).gene().floatValue()));
        LOG.info("Configs.TS_DYNAMIC_K            (K)    : {}f;", String.format("%.5f", best.get(1).gene().floatValue()));
        LOG.info("Configs.TS_PROFIT_MULTIPLIER    (Mult) : {}f;", String.format("%.5f", best.get(2).gene().floatValue()));
        LOG.info("=======================================================");
    }
}