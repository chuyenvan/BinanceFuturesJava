package com.binance.chuyennd.ai_ml;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
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
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class RunOptimizationBudgetRatio {

    // === DINH NGHIA CAU HINH CHAY ===
    // So lan thu trong moi "the he"
    private static final int POPULATION_SIZE = 10;
    // Tong so "the he" se chay
    private static final int GENERATIONS = 20;
    // Tong so lan chay backtest = 50 * 100 = 5000
    private static final long TOTAL_TRIALS = POPULATION_SIZE * GENERATIONS;
    // ==================================

    // Bo dem an toan, dung de biet dang o lan test thu may
    private static final AtomicLong testCounter = new AtomicLong(0);

    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, MarketRateChange> time2MarketRateChange;
    public static TreeMap<Long, Double> time2BtcReverse;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static final String FILE_FUNDING_FEE = "storage/fundingfee_time.data";
    public static ConcurrentHashMap<Long, Set<String>> CACHED_time2FundingFeeTrade;


    /**
     * HAM CHAM DIEM (FITNESS FUNCTION)
     */
    private static double evaluate(Genotype<DoubleGene> genotype) {

        long currentTestNumber = testCounter.incrementAndGet();

        // 1. Lay 6 tham so tu "bo gen"
        double ratio1 = genotype.get(0).gene().doubleValue();
        double divider1 = genotype.get(1).gene().doubleValue();
        double ratio2 = genotype.get(2).gene().doubleValue();
        double divider2 = genotype.get(3).gene().doubleValue();
        double trendUp = genotype.get(4).gene().doubleValue();
        double trendDown = genotype.get(5).gene().doubleValue();

        double finalBalance = 0.0;

        // In log *truoc khi* chay (DA THEM TONG SO)
        System.out.printf(
                "\n--- Bat dau Test #%d / %d ---%n{R1=%.2f, D1=%.1f, R2=%.2f, D2=%.1f, Up=%.1f, Down=%.1f}%n",
                currentTestNumber, TOTAL_TRIALS, // <--- THEM O DAY
                ratio1, divider1, ratio2, divider2, trendUp, trendDown
        );

        try {
            // 2. Khoi tao BacktestEngine
            BackTestEngineBudgetRatio engine = new BackTestEngineBudgetRatio(
                    ratio1, divider1, ratio2, divider2
            );

            // 3. Chay backtest
            finalBalance = engine.run(time2MarketData, time2MarketRateChange, time2BtcReverse, predictionMap);

            // In log *sau khi* chay (DA THEM TONG SO)
            System.out.printf(
                    "--- Ket thuc Test #%d / %d => Loi nhuan: %.2f ---%n",
                    currentTestNumber, TOTAL_TRIALS, finalBalance // <--- THEM O DAY
            );

        } catch (Exception e) {
            e.printStackTrace();
            System.out.printf("--- Test #%d / %d BI LOI => Loi nhuan: 0.0 ---%n",
                    currentTestNumber, TOTAL_TRIALS // <--- THEM O DAY
            );
            return 0.0; // Phat neu co loi
        }

        return finalBalance;
    }

    /**
     * HAM MAIN DE CHAY TOI UU HOA
     */
    public static void main(String[] args) {

        System.out.println("BAT DAU TOI UU HOA QUAN LY VON...");

        // === TAI DU LIEU VAO CACHE (1 LAN DUY NHAT) ===
        System.out.println("Dang tai du lieu vao bo nho (1 lan duy nhat)...");
        try {
            CACHED_time2FundingFeeTrade = (ConcurrentHashMap<Long, Set<String>>) StorageSnappy.readObjectFromFile(FILE_FUNDING_FEE);
            time2MarketRateChange = (TreeMap<Long, MarketRateChange>) StorageSnappy.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);
            time2MarketData = (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
            time2BtcReverse = (TreeMap<Long, Double>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_BTC_REVERSE);
            predictionMap = (TreeMap<Long, AiPredictionData>) StorageSnappy.readObjectFromFile(Configs.FILE_AI_ENTRY_PREDICTIONS);
            FundingFeeManager.getInstance();
            // (Ban them file trend o day neu can)
            System.out.println("Tai du lieu thanh cong. Bat dau toi uu hoa...");
        } catch (Exception e) {
            System.err.println("KHONG THE TAI DU LIEU. DUNG CHUONG TRINH.");
            e.printStackTrace();
            return;
        }

        long startTime = System.currentTimeMillis();

        // 1. DINH NGHIA "BO GEN"
        Genotype<DoubleGene> genotypeFactory = Genotype.of(
                DoubleChromosome.of(DoubleRange.of(0.2, 0.5)),    // ratio1
                DoubleChromosome.of(DoubleRange.of(1.5, 2.5)),    // divider1
                DoubleChromosome.of(DoubleRange.of(0.5, 0.8)),    // ratio2
                DoubleChromosome.of(DoubleRange.of(1.5, 2.5)),    // divider2
                DoubleChromosome.of(DoubleRange.of(1.0, 1.2)),    // trendUp
                DoubleChromosome.of(DoubleRange.of(0.8, 1.0))     // trendDown
        );

        // 2. CAU HINH "ENGINE" (Su dung HANG SO)
//        Engine<DoubleGene, Double> engine = Engine
//                .builder(RunOptimization::evaluate, genotypeFactory)
//                .populationSize(POPULATION_SIZE) // Su dung hang so
//                .maximizing()
//                .build();

        Engine<DoubleGene, Double> engine = Engine
                .builder(RunOptimizationBudgetRatio::evaluate, genotypeFactory)
                .populationSize(POPULATION_SIZE)
                .maximizing()
                // !!! THEM DONG NAY DE BUOC CHAY 1 LUONG !!!
                .executor(Executors.newSingleThreadExecutor())
                .build();

        // 3. CHAY TOI UU HOA (Su dung HANG SO)
        EvolutionResult<DoubleGene, Double> result = engine.stream()
                // Log tien do cua TUNG THE HE (DA THEM TONG SO)
                .peek(er -> System.out.printf(
                        "%n>>> Hoan tat The he %d / %d. Loi nhuan tot nhat hien tai: %.2f%n%n",
                        er.generation(), GENERATIONS, er.bestFitness() // <--- THEM O DAY
                ))
                .limit(GENERATIONS) // Su dung hang so
                .collect(EvolutionResult.toBestEvolutionResult());

        // 4. LAY KET QUA TOT NHAT
        Genotype<DoubleGene> bestParams = result.bestPhenotype().genotype();
        double bestProfit = result.bestFitness();
        long totalTime = System.currentTimeMillis() - startTime;

        double r1 = bestParams.get(0).gene().doubleValue();
        double d1 = bestParams.get(1).gene().doubleValue();
        double r2 = bestParams.get(2).gene().doubleValue();
        double d2 = bestParams.get(3).gene().doubleValue();
        double tUp = bestParams.get(4).gene().doubleValue();
        double tDown = bestParams.get(5).gene().doubleValue();

        // 5. IN KET QUA
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