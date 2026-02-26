package com.binance.chuyennd.ai_ml.hpo.budget;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import io.jenetics.DoubleChromosome;
import io.jenetics.DoubleGene;
import io.jenetics.Genotype;
import io.jenetics.engine.Engine;
import io.jenetics.engine.EvolutionResult;
import io.jenetics.util.DoubleRange;

import java.time.Duration;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class RunOptimizationBudgetRatio {

    private static final int POPULATION_SIZE = 10;
    private static final int GENERATIONS = 20;
    private static final long TOTAL_TRIALS = POPULATION_SIZE * GENERATIONS;

    private static final AtomicLong testCounter = new AtomicLong(0);

    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static TreeMap<Long, Map<Short, float[]>> time2FundingPre;

    private static double evaluate(Genotype<DoubleGene> genotype) {

        long currentTestNumber = testCounter.incrementAndGet();

        double ratio1 = genotype.get(0).gene().doubleValue();
        double divider1 = genotype.get(1).gene().doubleValue();
        double ratio2 = genotype.get(2).gene().doubleValue();
        double divider2 = genotype.get(3).gene().doubleValue();
        double trendUp = genotype.get(4).gene().doubleValue();
        double trendDown = genotype.get(5).gene().doubleValue();

        double finalBalance = 0.0;

        System.out.printf(
                "\n--- Bat dau Test #%d / %d ---%n{R1=%.2f, D1=%.1f, R2=%.2f, D2=%.1f, Up=%.1f, Down=%.1f}%n",
                currentTestNumber, TOTAL_TRIALS,
                ratio1, divider1, ratio2, divider2, trendUp, trendDown
        );

        try {
            BackTestEngineBudgetRatio engine = new BackTestEngineBudgetRatio(
                    ratio1, divider1, ratio2, divider2
            );

            finalBalance = engine.run(time2MarketData, predictionMap, time2FundingPre);

            System.out.printf(
                    "--- Ket thuc Test #%d / %d => Loi nhuan: %.2f ---%n",
                    currentTestNumber, TOTAL_TRIALS, finalBalance
            );

        } catch (Exception e) {
            e.printStackTrace();
            System.out.printf("--- Test #%d / %d BI LOI => Loi nhuan: 0.0 ---%n",
                    currentTestNumber, TOTAL_TRIALS
            );
            return 0.0;
        }

        return finalBalance;
    }

    public static void main(String[] args) {

        System.out.println("BAT DAU TOI UU HOA QUAN LY VON...");

        System.out.println("Dang tai du lieu vao bo nho (1 lan duy nhat)...");
        try {
            time2MarketData =  DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
            predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
            time2FundingPre = DataManagerAerospikeFloatSim.getAllFundingPredictionsDataFromAerospike();
            System.out.println("Tai du lieu thanh cong. Bat dau toi uu hoa...");
        } catch (Exception e) {
            System.err.println("KHONG THE TAI DU LIEU. DUNG CHUONG TRINH.");
            e.printStackTrace();
            return;
        }

        long startTime = System.currentTimeMillis();

        Genotype<DoubleGene> genotypeFactory = Genotype.of(
                DoubleChromosome.of(DoubleRange.of(0.2, 0.5)),
                DoubleChromosome.of(DoubleRange.of(1.5, 2.5)),
                DoubleChromosome.of(DoubleRange.of(0.5, 0.8)),
                DoubleChromosome.of(DoubleRange.of(1.5, 2.5)),
                DoubleChromosome.of(DoubleRange.of(1.0, 1.2)),
                DoubleChromosome.of(DoubleRange.of(0.8, 1.0))
        );

        Engine<DoubleGene, Double> engine = Engine
                .builder(RunOptimizationBudgetRatio::evaluate, genotypeFactory)
                .populationSize(POPULATION_SIZE)
                .maximizing()
                .executor(Executors.newSingleThreadExecutor())
                .build();

        EvolutionResult<DoubleGene, Double> result = engine.stream()
                .peek(er -> System.out.printf(
                        "%n>>> Hoan tat The he %d / %d. Loi nhuan tot nhat hien tai: %.2f%n%n",
                        er.generation(), GENERATIONS, er.bestFitness()
                ))
                .limit(GENERATIONS)
                .collect(EvolutionResult.toBestEvolutionResult());

        Genotype<DoubleGene> bestParams = result.bestPhenotype().genotype();
        double bestProfit = result.bestFitness();
        long totalTime = System.currentTimeMillis() - startTime;

        double r1 = bestParams.get(0).gene().doubleValue();
        double d1 = bestParams.get(1).gene().doubleValue();
        double r2 = bestParams.get(2).gene().doubleValue();
        double d2 = bestParams.get(3).gene().doubleValue();
        double tUp = bestParams.get(4).gene().doubleValue();
        double tDown = bestParams.get(5).gene().doubleValue();

        System.out.println("\n=============================================");
        System.out.println("=== TOI UU HOA QUAN LY VON HOAN TAT ===");
        System.out.println("Thoi gian chay: " + Duration.ofMillis(totalTime).toMinutes() + " phut");
        System.out.println(String.format("Loi nhuan cao nhat: %.2f", bestProfit));
        System.out.println("Voi cac tham so tot nhat:");
        System.out.println(String.format(" - BUDGET_MARGIN_RATIO_1:     %.4f", r1));
        System.out.println(String.format(" - BUDGET_DIVIDER_1:          %.4f", d1));
        System.out.println(String.format(" - BUDGET_MARGIN_RATIO_2:     %.4f", r2));
        System.out.println(String.format(" - BUDGET_DIVIDER_2:          %.4f", d2));
        System.out.println(String.format(" - BUDGET_TREND_UP_MULTIPLIER:  %.4f", tUp));
        System.out.println(String.format(" - BUDGET_TREND_DOWN_MULTIPLIER:%.4f", tDown));
        System.out.println("=============================================");
    }
}