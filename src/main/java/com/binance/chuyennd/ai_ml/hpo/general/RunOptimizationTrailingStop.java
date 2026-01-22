package com.binance.chuyennd.ai_ml.hpo.general;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import io.jenetics.DoubleChromosome;
import io.jenetics.DoubleGene;
import io.jenetics.Genotype;
import io.jenetics.engine.Engine;
import io.jenetics.engine.EvolutionResult;
import io.jenetics.util.DoubleRange;

import java.time.Duration;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class RunOptimizationTrailingStop {

    // === CẤU HÌNH HPO ===
    private static final int POPULATION_SIZE = 15; // Số lượng cá thể mỗi thế hệ
    private static final int GENERATIONS = 30;     // Số thế hệ
    // ====================

    private static final AtomicLong testCounter = new AtomicLong(0);
    public static TreeMap<Long, MarketDataObject> time2MarketData;

    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static final String FILE_FUNDING_FEE = "storage/fundingfee_time.data";
    public static ConcurrentHashMap<Long, Set<String>> CACHED_time2FundingFeeTrade;

    private static double evaluate(Genotype<DoubleGene> genotype) {
        long currentTest = testCounter.incrementAndGet();

        // 1. Giải mã Gen (7 tham số)
        double baseRate     = genotype.get(0).gene().doubleValue(); // Gen 0: Base Rate

        double volHighThres = genotype.get(1).gene().doubleValue(); // Gen 1: Volatility High Threshold
        double rateHigh     = genotype.get(2).gene().doubleValue(); // Gen 2: Rate High

        double volMedThres  = genotype.get(3).gene().doubleValue(); // Gen 3: Volatility Med Threshold
        double rateMed      = genotype.get(4).gene().doubleValue(); // Gen 4: Rate Med

        double volLowThres  = genotype.get(5).gene().doubleValue(); // Gen 5: Volatility Low Threshold
        double rateLow      = genotype.get(6).gene().doubleValue(); // Gen 6: Rate Low

        // --- Ràng buộc Logic (Constraints) ---
        // Volatility High > Med > Low VÀ Rate High > Med > Low
        // Nếu gen sinh ra không thỏa mãn logic này, trả về điểm thấp để loại bỏ
        if (volHighThres <= volMedThres || volMedThres <= volLowThres ||
                rateHigh <= rateMed || rateMed <= rateLow || rateLow <= baseRate) {
            return -1000.0; // Phạt nặng
        }

        double profit = 0.0;
        try {
            BackTestEngineTrailingStop engine = new BackTestEngineTrailingStop(
                    baseRate,
                    volHighThres, rateHigh,
                    volMedThres, rateMed,
                    volLowThres, rateLow
            );
            profit = engine.run(time2MarketData, predictionMap);

            System.out.printf("Test #%d: Profit=%.2f | Base=%.4f | Vol[H/M/L]=[%.4f, %.4f, %.4f] | Rate[H/M/L]=[%.4f, %.4f, %.4f]%n",
                    currentTest, profit, baseRate, volHighThres, volMedThres, volLowThres, rateHigh, rateMed, rateLow);

        } catch (Exception e) {
            e.printStackTrace();
            return 0.0;
        }
        return profit;
    }

    public static void main(String[] args) {
        System.out.println("=== BAT DAU TOI UU TRAILING STOP ===");
        loadData(); // Load data 1 lần

        long startTime = System.currentTimeMillis();

        // 2. ĐỊNH NGHĨA KHÔNG GIAN TÌM KIẾM (Search Space)
        // Range được mở rộng so với mặc định cũ (0.01)
        Genotype<DoubleGene> genotypeFactory = Genotype.of(
                // 0. Base Rate (Default 0.01) -> Range: 0.005 -> 0.02
                DoubleChromosome.of(DoubleRange.of(0.01, 0.03)),

                // 1. Vol High Thres (Def 0.01) -> Range: 0.008 -> 0.025
                DoubleChromosome.of(DoubleRange.of(0.008, 0.025)),
                // 2. Rate High (Def 0.03) -> Range: 0.025 -> 0.06 (Cho phép ăn dày hơn)
                DoubleChromosome.of(DoubleRange.of(0.03, 0.1)),

                // 3. Vol Med Thres (Def 0.006) -> Range: 0.005 -> 0.012
                DoubleChromosome.of(DoubleRange.of(0.005, 0.012)),
                // 4. Rate Med (Def 0.02) -> Range: 0.015 -> 0.035
                DoubleChromosome.of(DoubleRange.of(0.015, 0.05)),

                // 5. Vol Low Thres (Def 0.004) -> Range: 0.002 -> 0.007
                DoubleChromosome.of(DoubleRange.of(0.002, 0.007)),
                // 6. Rate Low (Def 0.016) -> Range: 0.01 -> 0.025
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

    private static void loadData() {
        try {
            System.out.println("Loading Data...");
            CACHED_time2FundingFeeTrade = (ConcurrentHashMap<Long, Set<String>>) StorageSnappy.readObjectFromFile(FILE_FUNDING_FEE);
            time2MarketData = (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
            predictionMap = (TreeMap<Long, AiPredictionData>) StorageSnappy.readObjectFromFile(Configs.FILE_AI_ENTRY_PREDICTIONS);
            FundingFeeManager.getInstance();
            System.out.println("Data Loaded.");
        } catch (Exception e) {
            e.printStackTrace();
            System.exit(1);
        }
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