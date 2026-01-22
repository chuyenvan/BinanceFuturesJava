package com.binance.chuyennd.ai_ml.hpo.fundingfee;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import io.jenetics.*;
import io.jenetics.engine.Engine;
import io.jenetics.engine.EvolutionResult;
import io.jenetics.util.Factory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class RunOptimizationFundingFee {

    private static final Logger LOG = LoggerFactory.getLogger(RunOptimizationFundingFee.class);

    // CẤU HÌNH SỐ LƯỢNG CHẠY
    private static final int POPULATION_SIZE = 20;
    private static final int GENERATIONS = 30;
    private static final AtomicLong testCounter = new AtomicLong(0);
    private static final long TOTAL_TRIALS = POPULATION_SIZE * GENERATIONS;

    // DATA STORE
    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static ConcurrentHashMap<Long, Set<String>> CACHED_time2FundingFeeTrade;

    public static void main(String[] args) {
        LOG.info("=== BẮT ĐẦU TỐI ƯU HÓA FUNDING FEE PARAMETERS ===");
        try {
            Configs.TIME_RUN = "20250101"; // Cấu hình thời gian chạy giả lập
            loadAndWarmUpData();
        } catch (Exception e) {
            e.printStackTrace();
            return;
        }

        // 1. ĐỊNH NGHĨA GEN (4 Tham số)
        // Param 0: FUNDING_RATE_MIN_TRADE (Default: -0.025)
        // Param 1: FUNDING_RATE_MIN_TRADE_FULL (Default: -0.03)
        // Param 2: FUNDING_RATE_UP_AVG (Default: 0.005)
        // Param 3: FUNDING_RATE_DOWN_AVG (Default: -0.005)
        Factory<Genotype<DoubleGene>> gtf = Genotype.of(
                DoubleChromosome.of(-0.04, -0.015), // Range MinTrade
                DoubleChromosome.of(-0.05, -0.02),  // Range MinTradeFull
                DoubleChromosome.of(0.004, 0.012),  // Range UpAvg
                DoubleChromosome.of(-0.012, -0.004) // Range DownAvg
        );

        // 2. CẤU HÌNH ENGINE
        // Quan trọng: Dùng singleThreadExecutor vì Configs là static global
        Engine<DoubleGene, Double> engine = Engine.builder(RunOptimizationFundingFee::eval, gtf)
                .populationSize(POPULATION_SIZE)
                .survivorsSelector(new TournamentSelector<>(3))
                .offspringSelector(new RouletteWheelSelector<>())
                .alterers(new Mutator<>(0.2), new MeanAlterer<>(0.6))
                .executor(Executors.newSingleThreadExecutor())
                .build();

        // 3. CHẠY
        long startTime = System.currentTimeMillis();
        EvolutionResult<DoubleGene, Double> bestResult = engine.stream()
                .limit(GENERATIONS)
                .peek(result -> {
                    System.out.printf(">>> Gen %d/%d Xong. PnL Tốt nhất: %.2f%n",
                            result.generation(), GENERATIONS, result.bestFitness());
                })
                .collect(EvolutionResult.toBestEvolutionResult());

        // 4. IN KẾT QUẢ
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
        System.out.println("=============================================");
    }

    private static Double eval(Genotype<DoubleGene> gt) {
        long c = testCounter.incrementAndGet();

        double pMinTrade = gt.get(0).gene().doubleValue();
        double pMinFull = gt.get(1).gene().doubleValue();
        double pUpAvg = gt.get(2).gene().doubleValue();
        double pDownAvg = gt.get(3).gene().doubleValue();

        // Ràng buộc logic: MinFull phải bé hơn MinTrade (điều kiện khắt khe hơn thì số âm phải bé hơn)
        if (pMinFull > pMinTrade) return -10000.0;

        try {
            // Khởi tạo Engine, nó sẽ tự update Configs
            BackTestEngineFundingFee engine = new BackTestEngineFundingFee(
                    pMinTrade, pMinFull, pUpAvg, pDownAvg
            );

            double score = engine.run(time2MarketData, predictionMap);

            System.out.printf("Trial #%d/%d: Score=%.2f | Params: %.4f, %.4f, %.4f, %.4f%n",
                    c, TOTAL_TRIALS, score, pMinTrade, pMinFull, pUpAvg, pDownAvg);

            return score;

        } catch (Exception e) {
            e.printStackTrace();
            return 0.0;
        }
    }

    private static void loadAndWarmUpData() throws Exception {
        System.out.println("Đang load dữ liệu vào RAM...");
        CACHED_time2FundingFeeTrade = (ConcurrentHashMap<Long, Set<String>>) StorageSnappy.readObjectFromFile(FundingFeeManager.FILE_FUNDING_FEE);
        time2MarketData = (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
        predictionMap = (TreeMap<Long, AiPredictionData>) StorageSnappy.readObjectFromFile(Configs.FILE_AI_ENTRY_PREDICTIONS);
        FundingFeeManager.getInstance();
        System.out.println("Load dữ liệu thành công.");
    }
}