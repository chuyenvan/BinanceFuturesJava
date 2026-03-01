package com.binance.chuyennd.ai_ml.hpo.general;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.HPOSmartCache;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import io.jenetics.DoubleChromosome;
import io.jenetics.DoubleGene;
import io.jenetics.Genotype;
import io.jenetics.engine.Engine;
import io.jenetics.engine.EvolutionResult;
import io.jenetics.util.DoubleRange;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class RunOptimizationTrailingStop {
    public static final Logger LOG = LoggerFactory.getLogger(RunOptimizationTrailingStop.class);
    private static final int POPULATION_SIZE = 15;
    private static final int GENERATIONS = 30;

    private static final AtomicLong testCounter = new AtomicLong(0);
    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static TreeMap<Long, long[]> time2FundingPre;
    public static final String FILE_FUNDING_FEE = "storage/fundingfee_time.data";

    private static double evaluate(Genotype<DoubleGene> genotype) {
        long currentTest = testCounter.incrementAndGet();

        double baseRate = genotype.get(0).gene().doubleValue();

        double volHighThres = genotype.get(1).gene().doubleValue();
        double rateHigh = genotype.get(2).gene().doubleValue();

        double volMedThres = genotype.get(3).gene().doubleValue();
        double rateMed = genotype.get(4).gene().doubleValue();

        double volLowThres = genotype.get(5).gene().doubleValue();
        double rateLow = genotype.get(6).gene().doubleValue();

        if (volHighThres <= volMedThres || volMedThres <= volLowThres ||
                rateHigh <= rateMed || rateMed <= rateLow || rateLow <= baseRate) {
            return -1000.0;
        }

        double profit = 0.0;
        try {
            BackTestEngineTrailingStop engine = new BackTestEngineTrailingStop(
                    baseRate,
                    volHighThres, rateHigh,
                    volMedThres, rateMed,
                    volLowThres, rateLow
            );
            profit = engine.run(time2MarketData, predictionMap, time2FundingPre);

            System.out.printf("Test #%d: Profit=%.2f | Base=%.4f | Vol[H/M/L]=[%.4f, %.4f, %.4f] | Rate[H/M/L]=[%.4f, %.4f, %.4f]%n",
                    currentTest, profit, baseRate, volHighThres, volMedThres, volLowThres, rateHigh, rateMed, rateLow);

        } catch (Exception e) {
            e.printStackTrace();
            return 0.0;
        }
        return profit;
    }

    public static void main(String[] args) throws Exception {
        System.out.println("=== BAT DAU TOI UU TRAILING STOP ===");
        loadAndWarmUpData();

        long startTime = System.currentTimeMillis();

        Genotype<DoubleGene> genotypeFactory = Genotype.of(
                DoubleChromosome.of(DoubleRange.of(0.01, 0.03)),
                DoubleChromosome.of(DoubleRange.of(0.008, 0.025)),
                DoubleChromosome.of(DoubleRange.of(0.03, 0.1)),
                DoubleChromosome.of(DoubleRange.of(0.005, 0.012)),
                DoubleChromosome.of(DoubleRange.of(0.015, 0.05)),
                DoubleChromosome.of(DoubleRange.of(0.002, 0.007)),
                DoubleChromosome.of(DoubleRange.of(0.01, 0.03))
        );

        Engine<DoubleGene, Double> engine = Engine
                .builder(RunOptimizationTrailingStop::evaluate, genotypeFactory)
                .populationSize(POPULATION_SIZE)
                .maximizing()
                .executor(Executors.newSingleThreadExecutor())
                .build();

        EvolutionResult<DoubleGene, Double> result = engine.stream()
                .limit(GENERATIONS)
                .peek(r -> System.out.printf(">>> Generation %d Best: %.2f%n", r.generation(), r.bestFitness()))
                .collect(EvolutionResult.toBestEvolutionResult());

        printResult(result, startTime);
    }

    private static void loadAndWarmUpData() throws Exception {
        LOG.info("Loading Data... {}", Configs.TIME_RUN);
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        int numberMinutes = System.currentTimeMillis() - startTime > 0 ? (int) ((System.currentTimeMillis() - startTime) / Utils.TIME_MINUTE) : 0;

        time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        Utils.printMemoryUsage("Load time2MarketData");

        predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        Utils.printMemoryUsage("Load predictionMap");

        time2FundingPre = DataManagerAerospikeFloatSim.getFundingPredictionsPrimitiveByRange(startTime, numberMinutes); // HOẶC HÀM GET THEO RANGE CỦA BẠN
        Utils.printMemoryUsage("Load time2FundingPre (time2SymbolPred)");

        // Warmup HPOSmartCache...
        LOG.info("🔥 Warming up cache ({}-NOW)...", Configs.TIME_RUN);
        long startTimeLoad = Utils.sdfFile.parse(Configs.TIME_RUN).getTime();
        long endTimeLoad = System.currentTimeMillis();
        long current = startTimeLoad;
        while (current < endTimeLoad) {
            HPOSmartCache.getData(current);
            current += Utils.TIME_DAY;
        }
        Utils.printMemoryUsage("Load HPOSmartCache");

    }

    private static void printResult(EvolutionResult<DoubleGene, Double> result, long startTime) {
        Genotype<DoubleGene> best = result.bestPhenotype().genotype();
        System.out.println("\n=== KẾT QUẢ TỐI ƯU TRAILING STOP ===");
        System.out.println("Time: " + Duration.ofMillis(System.currentTimeMillis() - startTime).toMinutes() + " mins");
        System.out.println("Profit Max: " + result.bestFitness());
        System.out.println("------------------------------------");
        System.out.printf("Base Rate:             %.5f%n", best.get(0).gene().doubleValue());
        System.out.println("--- HIGH VOLATILITY ---");
        System.out.printf("Threshold:             %.5f%n", best.get(1).gene().doubleValue());
        System.out.printf("Target Rate:           %.5f%n", best.get(2).gene().doubleValue());
        System.out.println("--- MEDIUM VOLATILITY ---");
        System.out.printf("Threshold:             %.5f%n", best.get(3).gene().doubleValue());
        System.out.printf("Target Rate:           %.5f%n", best.get(4).gene().doubleValue());
        System.out.println("--- LOW VOLATILITY ---");
        System.out.printf("Threshold:             %.5f%n", best.get(5).gene().doubleValue());
        System.out.printf("Target Rate:           %.5f%n", best.get(6).gene().doubleValue());
    }
}