package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.HPOSmartCache;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import io.jenetics.*;
import io.jenetics.engine.Engine;
import io.jenetics.engine.EvolutionResult;
import io.jenetics.util.DoubleRange;
import io.jenetics.util.Factory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class RunOptimizationAIMarket {

    private static final Logger LOG = LoggerFactory.getLogger(RunOptimizationAIMarket.class);

    // Đồng bộ tham số cấu hình tiến hóa giống MarketThreshold
    private static final int POPULATION_SIZE = 15;
    private static final int GENERATIONS = 30;

    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static TreeMap<Long, long[]> time2FundingPre;
    private static final AtomicLong testCounter = new AtomicLong(0);

    // Range của các thông số AI Filter
    private static final double MIN_RISK = -0.06, MAX_RISK = -0.01;
    private static final double MIN_RET1H = 0.005, MAX_RET1H = 0.06;
    private static final double MIN_HIGHRET = 0.01, MAX_HIGHRET = 0.10;
    private static final double MIN_MOM15M = 0.001, MAX_MOM15M = 0.02;
    private static final double MIN_TREND4H = 0.001, MAX_TREND4H = 0.03;

    public static void main(String[] args) {
        System.out.println("=== START OPTIMIZING AI MARKET THRESHOLDS ===");

        try {
            Configs.TIME_RUN = "20250101";
            loadAndWarmUpData();
        } catch (Exception e) {
            e.printStackTrace();
            return;
        }

        long startTime = System.currentTimeMillis();

        Factory<Genotype<DoubleGene>> genotypeFactory = Genotype.of(
                DoubleChromosome.of(DoubleRange.of(MIN_RISK, MAX_RISK)),
                DoubleChromosome.of(DoubleRange.of(MIN_RET1H, MAX_RET1H)),
                DoubleChromosome.of(DoubleRange.of(MIN_HIGHRET, MAX_HIGHRET)),
                DoubleChromosome.of(DoubleRange.of(MIN_MOM15M, MAX_MOM15M)),
                DoubleChromosome.of(DoubleRange.of(MIN_TREND4H, MAX_TREND4H))
        );

        // 🔥 THAY ĐỔI CỐT LÕI: Ép chạy Single Thread Executor giống file MarketThreshold
        Engine<DoubleGene, Double> engine = Engine.builder(RunOptimizationAIMarket::evaluate, genotypeFactory)
                .populationSize(POPULATION_SIZE)
                .maximizing() // Chế độ tìm max profit
                .executor(Executors.newSingleThreadExecutor()) // Tránh tranh chấp luồng và RAM
                .build();

        EvolutionResult<DoubleGene, Double> result = engine.stream()
                .limit(GENERATIONS)
                .peek(r -> System.out.printf(">>> Generation %d Best: %.2f%n", r.generation(), r.bestFitness()))
                .collect(EvolutionResult.toBestEvolutionResult());

        printResult(result, startTime);
    }

    private static Double evaluate(Genotype<DoubleGene> genotype) {
        long currentTest = testCounter.incrementAndGet();

        double pRisk = genotype.get(0).gene().doubleValue();
        double pRet1H = genotype.get(1).gene().doubleValue();
        double pHighRet = genotype.get(2).gene().doubleValue();
        double pMom15M = genotype.get(3).gene().doubleValue();
        double pTrend4H = genotype.get(4).gene().doubleValue();

        double profit = 0.0;
        try {
            BackTestEngineAIMarket engine = new BackTestEngineAIMarket(
                    pRisk, pRet1H, pHighRet, pMom15M, pTrend4H, -0.99
            );

            profit = engine.run(time2MarketData, predictionMap, time2FundingPre);

            // Print log giống hệt format bên MarketThreshold cho dễ nhìn
            System.out.printf("Test #%d: Profit=%.2f | Risk=%.4f | R1H=%.4f | HighR=%.4f | Mom15=%.4f | Trend4=%.4f%n",
                    currentTest, profit, pRisk, pRet1H, pHighRet, pMom15M, pTrend4H);

        } catch (Exception e) {
            e.printStackTrace();
            return -100000.0; // Điểm phạt nếu lỗi
        }
        return profit;
    }

    private static void loadAndWarmUpData() throws Exception {
        LOG.info("Loading Data... {}", Configs.TIME_RUN);
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        int numberMinutes = System.currentTimeMillis() - startTime > 0 ? (int) ((System.currentTimeMillis() - startTime) / Utils.TIME_MINUTE) : 0;

        time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        Utils.printMemoryUsage("Load time2MarketData");

        predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        Utils.printMemoryUsage("Load predictionMap");

        time2FundingPre = DataManagerAerospikeFloatSim.getFundingPredictionsPrimitiveByRange(startTime,numberMinutes); // HOẶC HÀM GET THEO RANGE CỦA BẠN
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
        System.out.println("\n=== KẾT QUẢ TỐI ƯU AI MARKET THRESHOLDS ===");
        System.out.println("Time: " + Duration.ofMillis(System.currentTimeMillis() - startTime).toMinutes() + " mins");
        System.out.println("Profit Max: " + result.bestFitness());
        System.out.println("------------------------------------");
        System.out.printf("RISK_MAX_DD4H:  %.5f%n", best.get(0).gene().doubleValue());
        System.out.printf("MIN_RET_1H:     %.5f%n", best.get(1).gene().doubleValue());
        System.out.printf("HIGH_RET:       %.5f%n", best.get(2).gene().doubleValue());
        System.out.printf("MIN_MOM_15M:    %.5f%n", best.get(3).gene().doubleValue());
        System.out.printf("MIN_TREND_4H:   %.5f%n", best.get(4).gene().doubleValue());
    }


}