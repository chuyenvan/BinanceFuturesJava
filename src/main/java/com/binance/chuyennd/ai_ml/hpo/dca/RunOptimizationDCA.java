package com.binance.chuyennd.ai_ml.hpo.dca;

import com.binance.chuyennd.research.FundingFeeManager;
import io.jenetics.DoubleChromosome;
import io.jenetics.DoubleGene;
import io.jenetics.Genotype;
import io.jenetics.engine.Engine;
import io.jenetics.engine.EvolutionResult;
import io.jenetics.util.DoubleRange;

import java.time.Duration;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class RunOptimizationDCA {

    // === DINH NGHIA CAU HINH CHAY ===
    private static final int POPULATION_SIZE = 20;
    private static final int GENERATIONS = 10;
    private static final long TOTAL_TRIALS = POPULATION_SIZE * GENERATIONS;

    private static final AtomicLong testCounter = new AtomicLong(0);

    // === CACHE DU LIEU ===




    /**
     * HAM CHAM DIEM (FITNESS FUNCTION)
     */
    private static double evaluate(Genotype<DoubleGene> genotype) {

        long currentTestNumber = testCounter.incrementAndGet();

        // 1. Lay 9 tham so tu "bo gen"
        double p1 = genotype.get(0).gene().doubleValue(); // rateLossBigDown
        double p2 = genotype.get(1).gene().doubleValue(); // rateLossMediumDown
        double p3 = genotype.get(2).gene().doubleValue(); // rateLossMediumUp
        double p4 = genotype.get(3).gene().doubleValue(); // rateLossSmallDown
        double p5 = genotype.get(4).gene().doubleValue(); // rateLossNull
        double p6 = genotype.get(5).gene().doubleValue(); // marginRate_1_5
        double p7 = genotype.get(6).gene().doubleValue(); // marginRate_2_0
        double p8 = genotype.get(7).gene().doubleValue(); // marginRate_2_5
        // (p9 la gene_marginRate_base, chung ta da thay bang p5 (rateLossNull))

        double finalBalance = 0.0;

        System.out.printf(
                "\n--- Bat dau Test #%d / %d ---%n",
                currentTestNumber, TOTAL_TRIALS
        );

        try {
            // 2. Khoi tao BacktestEngine
            BackTestEngineDCA engine = new BackTestEngineDCA(p1, p2, p3, p4, p5, p6, p7, p8);

            // 3. Chay backtest
            finalBalance = engine.run();

            System.out.printf(
                    "--- Ket thuc Test #%d / %d => Loi nhuan: %.2f ---%n",
                    currentTestNumber, TOTAL_TRIALS, finalBalance
            );

        } catch (Exception e) {
            e.printStackTrace();
            System.out.printf("--- Test #%d / %d BI LOI => Loi nhuan: 0.0 ---%n",
                    currentTestNumber, TOTAL_TRIALS
            );
            return 0.0; // Phat neu co loi
        }

        return finalBalance;
    }

    /**
     * HAM MAIN DE CHAY TOI UU HOA
     */
    public static void main(String[] args) {

        System.out.println("BAT DAU TOI UU HOA LOGIC DCA...");

        // === TAI DU LIEU VAO CACHE (1 LAN DUY NHAT) ===
        // (Giu nguyen code tai cache cua ban)
        try {
            System.out.println("Dang tai du lieu vao bo nho (1 lan duy nhat)...");

            // Goi de tai symbol2FundingFee vao bo nho
            FundingFeeManager.getInstance();
            System.out.println("Tai du lieu thanh cong. Bat dau toi uu hoa...");
        } catch (Exception e) {
            e.printStackTrace();
            return;
        }
        // ================================================

        long startTime = System.currentTimeMillis();

        // 1. DINH NGHIA "BO GEN" (8 THAM SO VA PHAM VI CUA CHUNG)
        Genotype<DoubleGene> genotypeFactory = Genotype.of(
                // p1: rateLossBigDown (Gia tri goc: -0.05)
                DoubleChromosome.of(DoubleRange.of(-0.10, -0.05)),

                // p2: rateLossMediumDown (Gia tri goc: -0.08)
                DoubleChromosome.of(DoubleRange.of(-0.15, -0.08)),

                // p3: rateLossMediumUp (Gia tri goc: -0.15)
                DoubleChromosome.of(DoubleRange.of(-0.25, -0.15)),

                // p4: rateLossSmallDown (Gia tri goc: -0.20)
                DoubleChromosome.of(DoubleRange.of(-0.30, -0.2)),

                // p5: rateLossNull (Gia tri goc: -0.4)
                DoubleChromosome.of(DoubleRange.of(-0.50, -0.30)),

                // p6: marginRate_1_5 (Gia tri goc: -0.6)
                DoubleChromosome.of(DoubleRange.of(-0.70, -0.50)),

                // p7: marginRate_2_0 (Gia tri goc: -0.7)
                DoubleChromosome.of(DoubleRange.of(-0.80, -0.60)),

                // p8: marginRate_2_5 (Gia tri goc: -0.9)
                DoubleChromosome.of(DoubleRange.of(-0.95, -0.80))
        );

        // 2. CAU HINH "ENGINE" (BUOC CHAY 1 LUONG)
        Engine<DoubleGene, Double> engine = Engine
                .builder(RunOptimizationDCA::evaluate, genotypeFactory)
                .populationSize(POPULATION_SIZE)
                .maximizing()
                // Buoc chay 1 luong de tranh loi ghi de Configs
                .executor(Executors.newSingleThreadExecutor())
                .build();

        // 3. CHAY TOI UU HOA
        EvolutionResult<DoubleGene, Double> result = engine.stream()
                .peek(er -> System.out.printf(
                        "%n>>> Hoan tat The he %d / %d. Loi nhuan tot nhat hien tai: %.2f%n%n",
                        er.generation(), GENERATIONS, er.bestFitness()
                ))
                .limit(GENERATIONS)
                .collect(EvolutionResult.toBestEvolutionResult());

        // 4. LAY KET QUA TOT NHAT
        Genotype<DoubleGene> bestParams = result.bestPhenotype().genotype();
        double bestProfit = result.bestFitness();
        long totalTime = System.currentTimeMillis() - startTime;

        double p1 = bestParams.get(0).gene().doubleValue();
        double p2 = bestParams.get(1).gene().doubleValue();
        double p3 = bestParams.get(2).gene().doubleValue();
        double p4 = bestParams.get(3).gene().doubleValue();
        double p5 = bestParams.get(4).gene().doubleValue();
        double p6 = bestParams.get(5).gene().doubleValue();
        double p7 = bestParams.get(6).gene().doubleValue();
        double p8 = bestParams.get(7).gene().doubleValue();

        // 5. IN KET QUA
        System.out.println("\n=============================================");
        System.out.println("=== TOI UU HOA LOGIC DCA HOAN TAT ===");
        System.out.println("Thoi gian chay: " + Duration.ofMillis(totalTime).toMinutes() + " phut");
        System.out.println(String.format("Loi nhuan cao nhat: %.2f", bestProfit));
        System.out.println("Voi cac tham so tot nhat:");
        System.out.println(String.format(" - rateLossBigDown:    %.4f (Goc: -0.05)", p1));
        System.out.println(String.format(" - rateLossMediumDown: %.4f (Goc: -0.08)", p2));
        System.out.println(String.format(" - rateLossMediumUp:   %.4f (Goc: -0.15)", p3));
        System.out.println(String.format(" - rateLossSmallDown:  %.4f (Goc: -0.20)", p4));
        System.out.println(String.format(" - rateLossNull:       %.4f (Goc: -0.40)", p5));
        System.out.println(String.format(" - marginRate_1_5:     %.4f (Goc: -0.60)", p6));
        System.out.println(String.format(" - marginRate_2_0:     %.4f (Goc: -0.70)", p7));
        System.out.println(String.format(" - marginRate_2_5:     %.4f (Goc: -0.90)", p8));
        System.out.println("=============================================");
    }
}