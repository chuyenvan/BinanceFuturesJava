package com.binance.chuyennd.ai_ml.hpo.market;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
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
import java.util.TreeMap;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class RunOptimizationMarketThreshold {
    public static final Logger LOG = LoggerFactory.getLogger(RunOptimizationMarketThreshold.class);

    // Tăng nhẹ lên 15 Pop và 20 Gen (Tổng 300 trials) cho không gian 4 chiều
    private static final int POPULATION_SIZE = 15;
    private static final int GENERATIONS = 20;

    private static final AtomicLong testCounter = new AtomicLong(0);
    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static TreeMap<Long, long[]> time2FundingPre;

    private static float evaluate(Genotype<DoubleGene> genotype) {
        long currentTest = testCounter.incrementAndGet();

        // Bóc tách 4 biến
        float pBaseDown  = genotype.get(0).gene().floatValue();
        float pRatioDown = genotype.get(1).gene().floatValue();
        float pBaseUp    = genotype.get(2).gene().floatValue();
        float pRatioUp   = genotype.get(3).gene().floatValue();

        float profit = 0.0f;
        try {
            BackTestEngineMarketThreshold engine = new BackTestEngineMarketThreshold(pBaseDown, pRatioDown, pBaseUp, pRatioUp);
            profit = engine.run(time2MarketData, predictionMap, time2FundingPre);

            // Cập nhật Log để in ra cho dễ theo dõi
            LOG.info("Test #{}: Profit={:.2f} | B_DOWN={:.4f} | R_DOWN={:.4f} | B_UP={:.4f} | R_UP={:.4f}",
                    currentTest, profit, pBaseDown, pRatioDown, pBaseUp, pRatioUp);

        } catch (Exception e) {
            e.printStackTrace();
            return 0.0f;
        }
        return profit;
    }

    public static void main(String[] args) throws Exception {
        LOG.info("=== START OPTIMIZING MARKET GEOMETRIC THRESHOLDS ===");
        Configs.TIME_RUN = "20251001"; // Setup thời gian chạy tại đây
        loadAndWarmUpData();

        long startTime = System.currentTimeMillis();

        // 4 NHIỄM SẮC THỂ CHO MÔ HÌNH CẤP SỐ NHÂN (GEOMETRIC PROGRESSION)
        Genotype<DoubleGene> genotypeFactory = Genotype.of(
                DoubleChromosome.of(DoubleRange.of(0.003, 0.015)), // 0: BASE_DOWN (Ngưỡng rung lắc nhẹ 0.3% -> 1.5%)
                DoubleChromosome.of(DoubleRange.of(1.3, 2.5)),     // 1: RATIO_DOWN (Tốc độ giãn nở từ 1.3x đến 2.5x)
                DoubleChromosome.of(DoubleRange.of(0.003, 0.015)), // 2: BASE_UP
                DoubleChromosome.of(DoubleRange.of(1.3, 2.5))      // 3: RATIO_UP
        );

        Engine<DoubleGene, Float> engine = Engine
                .builder(RunOptimizationMarketThreshold::evaluate, genotypeFactory)
                .populationSize(POPULATION_SIZE)
                .maximizing()
                .executor(Executors.newSingleThreadExecutor())
                .build();

        EvolutionResult<DoubleGene, Float> result = engine.stream()
                .limit(GENERATIONS)
                .peek(r -> LOG.info(">>> Generation {} Best: {}", r.generation(), r.bestFitness()))
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

        LOG.info("✅ Data Ready.");
    }

    private static void printResult(EvolutionResult<DoubleGene, Float> result, long startTime) {
        Genotype<DoubleGene> best = result.bestPhenotype().genotype();
        LOG.info("\n=== KẾT QUẢ TỐI ƯU MARKET GEOMETRIC THRESHOLDS ===");
        LOG.info("Time: {} mins", Duration.ofMillis(System.currentTimeMillis() - startTime).toMinutes());
        LOG.info("Profit Max: {}", result.bestFitness());
        LOG.info("------------------------------------");
        LOG.info("Configs.BASE_DOWN:   {}f;", String.format("%.5f", best.get(0).gene().doubleValue()));
        LOG.info("Configs.RATIO_DOWN:  {}f;", String.format("%.5f", best.get(1).gene().doubleValue()));
        LOG.info("Configs.BASE_UP:     {}f;", String.format("%.5f", best.get(2).gene().doubleValue()));
        LOG.info("Configs.RATIO_UP:    {}f;", String.format("%.5f", best.get(3).gene().doubleValue()));
    }
}