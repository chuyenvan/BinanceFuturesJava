package com.binance.chuyennd.ai_ml.hpo.fundingfee;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.utils.Configs;
import io.jenetics.*;
import io.jenetics.engine.Engine;
import io.jenetics.engine.EvolutionResult;
import io.jenetics.util.Factory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class RunOptimizationFundingFee {

    private static final Logger LOG = LoggerFactory.getLogger(RunOptimizationFundingFee.class);

    private static final int POPULATION_SIZE = 20;
    private static final int GENERATIONS = 30;
    private static final AtomicLong testCounter = new AtomicLong(0);
    private static final long TOTAL_TRIALS = POPULATION_SIZE * GENERATIONS;

    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static TreeMap<Long, Map<Short, float[]>> time2FundingPre; // 🔥 THÊM BIẾN NÀY

    public static void main(String[] args) {
        LOG.info("=== BẮT ĐẦU TỐI ƯU HÓA FUNDING FEE PARAMETERS ===");
        try {
            Configs.TIME_RUN = "20250101";
            loadAndWarmUpData();
        } catch (Exception e) {
            e.printStackTrace();
            return;
        }

        // 1. ĐỊNH NGHĨA GEN (5 Tham số)
        Factory<Genotype<DoubleGene>> gtf = Genotype.of(
                DoubleChromosome.of(-0.04, -0.015), // 0: MinTrade
                DoubleChromosome.of(-0.05, -0.02),  // 1: MinTradeFull
                DoubleChromosome.of(0.004, 0.012),  // 2: UpAvg
                DoubleChromosome.of(-0.012, -0.004),// 3: DownAvg
                DoubleChromosome.of(0.1, 0.5)       // 🔥 4: AI Funding Threshold (Tìm từ 10% đến 50%)
        );

        Engine<DoubleGene, Double> engine = Engine.builder(RunOptimizationFundingFee::eval, gtf)
                .populationSize(POPULATION_SIZE)
                .survivorsSelector(new TournamentSelector<>(3))
                .offspringSelector(new RouletteWheelSelector<>())
                .alterers(new Mutator<>(0.2), new MeanAlterer<>(0.6))
                .executor(Executors.newSingleThreadExecutor())
                .build();

        long startTime = System.currentTimeMillis();
        EvolutionResult<DoubleGene, Double> bestResult = engine.stream()
                .limit(GENERATIONS)
                .peek(result -> {
                    System.out.printf(">>> Gen %d/%d Xong. PnL Tốt nhất: %.2f%n",
                            result.generation(), GENERATIONS, result.bestFitness());
                })
                .collect(EvolutionResult.toBestEvolutionResult());

        long totalTime = System.currentTimeMillis() - startTime;
        Genotype<DoubleGene> bestGt = bestResult.bestPhenotype().genotype();

        System.out.println("\n=============================================");
        System.out.println("=== KẾT QUẢ TỐI ƯU HÓA FUNDING FEE ===");
        System.out.println("Thời gian: " + Duration.ofMillis(totalTime).toMinutes() + " phút");
        System.out.println("Lợi nhuận Max: " + bestResult.bestFitness());
        System.out.println("Configs tốt nhất:");
        System.out.printf("Configs.FUNDING_RATE_MIN_TRADE      = %.5f;%n", bestGt.get(0).gene().doubleValue());
        System.out.printf("Configs.FUNDING_RATE_MIN_TRADE_FULL = %.5f;%n", bestGt.get(1).gene().doubleValue());
        System.out.printf("Configs.FUNDING_RATE_UP_AVG         = %.5f;%n", bestGt.get(2).gene().doubleValue());
        System.out.printf("Configs.FUNDING_RATE_DOWN_AVG       = %.5f;%n", bestGt.get(3).gene().doubleValue());
        System.out.printf("Configs.FUNDING_PRED_MAX_THRESHOLD  = %.5f;%n", bestGt.get(4).gene().doubleValue());
        System.out.println("=============================================");
    }

    private static Double eval(Genotype<DoubleGene> gt) {
        long c = testCounter.incrementAndGet();

        double pMinTrade = gt.get(0).gene().doubleValue();
        double pMinFull = gt.get(1).gene().doubleValue();
        double pUpAvg = gt.get(2).gene().doubleValue();
        double pDownAvg = gt.get(3).gene().doubleValue();
        double pFundingPred = gt.get(4).gene().doubleValue(); // Lấy gen thứ 5

        if (pMinFull > pMinTrade) return -10000.0;

        try {
            BackTestEngineFundingFee engine = new BackTestEngineFundingFee(
                    pMinTrade, pMinFull, pUpAvg, pDownAvg, pFundingPred
            );

            // 🔥 Truyền đủ 3 bộ RAM vào
            double score = engine.run(time2MarketData, predictionMap, time2FundingPre);

            System.out.printf("Trial #%d/%d: Score=%.2f | Param: %.4f, %.4f, %.4f, %.4f, Thresh: %.4f%n",
                    c, TOTAL_TRIALS, score, pMinTrade, pMinFull, pUpAvg, pDownAvg, pFundingPred);

            return score;

        } catch (Exception e) {
            e.printStackTrace();
            return 0.0;
        }
    }

    private static void loadAndWarmUpData() throws Exception {
        System.out.println("🚀 Đang load TẤT CẢ dữ liệu từ Aerospike vào RAM...");

        // 🔥 ĐỌC THẲNG TỪ AEROSPIKE (KHÔNG CẦN CHỜ CHECK SINH BÙ NỮA)
        time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        time2FundingPre = DataManagerAerospikeFloatSim.getAllFundingPredictionsDataFromAerospike();

        System.out.println("✅ Load dữ liệu vào RAM thành công.");
    }
}