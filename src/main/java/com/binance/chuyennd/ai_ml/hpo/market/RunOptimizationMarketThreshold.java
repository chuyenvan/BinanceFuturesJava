package com.binance.chuyennd.ai_ml.hpo.market;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
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

public class RunOptimizationMarketThreshold {

    // === CẤU HÌNH HPO ===
    private static final int POPULATION_SIZE = 15;
    private static final int GENERATIONS = 30;
    // ====================

    private static final AtomicLong testCounter = new AtomicLong(0);
    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static final String FILE_FUNDING_FEE = "storage/fundingfee_time.data";
    public static ConcurrentHashMap<Long, Set<String>> CACHED_time2FundingFeeTrade;

    private static double evaluate(Genotype<DoubleGene> genotype) {
        long currentTest = testCounter.incrementAndGet();

        // 1. Giải mã Gen (8 tham số chính)
        double upBig       = genotype.get(0).gene().doubleValue(); // Gen 0
        double downBigAvg  = genotype.get(1).gene().doubleValue(); // Gen 1 (Negative)

        double upMed       = genotype.get(2).gene().doubleValue(); // Gen 2
        double downMedAvg  = genotype.get(3).gene().doubleValue(); // Gen 3 (Negative)

        double upSmall     = genotype.get(4).gene().doubleValue(); // Gen 4
        double downSmallAvg= genotype.get(5).gene().doubleValue(); // Gen 5 (Negative)

        double down15mMed  = genotype.get(6).gene().doubleValue(); // Gen 6 (Negative)
        double down15mSmall= genotype.get(7).gene().doubleValue(); // Gen 7 (Negative)

        // --- Ràng buộc Logic (Constraint Penalty) ---
        // Logic: Big Up > Med Up > Small Up
        // Logic: Big Down < Med Down < Small Down (Vì là số âm nên Big Down phải nhỏ nhất)
        // Ví dụ: -0.05 < -0.03 < -0.01

        boolean invalidUp = (upBig <= upMed) || (upMed <= upSmall);
        boolean invalidDown = (downBigAvg >= downMedAvg) || (downMedAvg >= downSmallAvg);
        boolean invalid15m = (down15mMed >= down15mSmall);

        if (invalidUp || invalidDown || invalid15m) {
            // Phạt nặng các bộ gen phi logic để thuật toán loại bỏ
            return -10000.0;
        }

        double profit = 0.0;
        try {
            BackTestEngineMarketThreshold engine = new BackTestEngineMarketThreshold(
                    upBig, downBigAvg,
                    upMed, downMedAvg,
                    upSmall, downSmallAvg,
                    down15mMed, down15mSmall
            );
            profit = engine.run(time2MarketData, predictionMap);

            System.out.printf("Test #%d: Profit=%.2f | Up[B/M/S]=[%.3f, %.3f, %.3f] | Down[B/M/S]=[%.3f, %.3f, %.3f]%n",
                    currentTest, profit, upBig, upMed, upSmall, downBigAvg, downMedAvg, downSmallAvg);

        } catch (Exception e) {
            e.printStackTrace();
            return 0.0;
        }
        return profit;
    }

    public static void main(String[] args) {
        System.out.println("=== START OPTIMIZING MARKET THRESHOLDS ===");
        loadData();

        long startTime = System.currentTimeMillis();

        // 2. KHÔNG GIAN TÌM KIẾM (Search Space) - Dựa trên giá trị mặc định cũ
        Genotype<DoubleGene> genotypeFactory = Genotype.of(
                // 0. Up Big (Def: 0.025) -> Range: 0.02 -> 0.05
                DoubleChromosome.of(DoubleRange.of(0.02, 0.05)),
                // 1. Down Big (Def: -0.032) -> Range: -0.06 -> -0.031
                DoubleChromosome.of(DoubleRange.of(-0.06, -0.031)),

                // 2. Up Med (Def: 0.015) -> Range: 0.012 -> 0.025
                DoubleChromosome.of(DoubleRange.of(0.012, 0.025)),
                // 3. Down Med (Def: -0.030) -> Range: -0.04 -> -0.02
                DoubleChromosome.of(DoubleRange.of(-0.04, -0.02)),

                // 4. Up Small (Def: 0.008) -> Range: 0.004 -> 0.012
                DoubleChromosome.of(DoubleRange.of(0.004, 0.012)),
                // 5. Down Small (Def: -0.006) -> Range: -0.02 -> -0.004
                DoubleChromosome.of(DoubleRange.of(-0.02, -0.004)),

                // 6. Down 15M Med (Def: -0.045) -> Range: -0.08 -> -0.04
                DoubleChromosome.of(DoubleRange.of(-0.08, -0.04)),
                // 7. Down 15M Small (Def: -0.028) -> Range: -0.045 -> -0.02
                DoubleChromosome.of(DoubleRange.of(-0.045, -0.02))
        );

        Engine<DoubleGene, Double> engine = Engine
                .builder(RunOptimizationMarketThreshold::evaluate, genotypeFactory)
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
        System.out.println("\n=== KẾT QUẢ TỐI ƯU MARKET THRESHOLDS ===");
        System.out.println("Time: " + Duration.ofMillis(System.currentTimeMillis() - startTime).toMinutes() + " mins");
        System.out.println("Profit Max: " + result.bestFitness());
        System.out.println("------------------------------------");
        System.out.printf("MS_UP_BIG_THRES:        %.5f%n", best.get(0).gene().doubleValue());
        System.out.printf("MS_DOWN_BIG_AVG:        %.5f%n", best.get(1).gene().doubleValue());
        System.out.println("---");
        System.out.printf("MS_UP_MED_THRES:        %.5f%n", best.get(2).gene().doubleValue());
        System.out.printf("MS_DOWN_MED_AVG:        %.5f%n", best.get(3).gene().doubleValue());
        System.out.println("---");
        System.out.printf("MS_UP_SMALL_THRES:      %.5f%n", best.get(4).gene().doubleValue());
        System.out.printf("MS_DOWN_SMALL_AVG:      %.5f%n", best.get(5).gene().doubleValue());
        System.out.println("---");
        System.out.printf("MS_DOWN_15M_MED_ONLY:   %.5f%n", best.get(6).gene().doubleValue());
        System.out.printf("MS_DOWN_15M_SMALL_ONLY: %.5f%n", best.get(7).gene().doubleValue());
    }
}