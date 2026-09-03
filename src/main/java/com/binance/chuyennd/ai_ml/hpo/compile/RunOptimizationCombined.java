package com.binance.chuyennd.ai_ml.hpo.compile;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.tradecore.Configs;
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

public class RunOptimizationCombined {

    private static final Logger LOG = LoggerFactory.getLogger(RunOptimizationCombined.class);

    private static final int POPULATION_SIZE = 20;
    private static final int GENERATIONS = 30;
    private static final AtomicLong testCounter = new AtomicLong(0);
    private static final long TOTAL_TRIALS = (long) POPULATION_SIZE * GENERATIONS;

    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static TreeMap<Long, long[]> time2FundingPre;

    public static void main(String[] args) {
        LOG.info("=== BẮT ĐẦU HPO COMBINED (12 PARAMETERS) ===");
        try {
            Configs.TIME_RUN = "20251101"; // Setup thời gian chạy tại đây
            loadDataReady();
        } catch (Exception e) {
            e.printStackTrace();
            return;
        }

        // =========================================================
        // KHAI BÁO 12 NHIỄM SẮC THỂ (12 CHROMOSOMES)
        // ĐÃ ÁP DỤNG TRACE DATA CHO MOMENTUM 15M VÀ DYNAMIC K
        // =========================================================
        Genotype<DoubleGene> genotypeFactory = Genotype.of(
                // --- 4 THAM SỐ FUNDING FEE / ENTRY ---
                DoubleChromosome.of(DoubleRange.of(-0.02, 0.0)),     // 0: RATE_DOWN_15M
                DoubleChromosome.of(DoubleRange.of(0.005, 0.05)),    // 1: RATE_UP_AVG
                DoubleChromosome.of(DoubleRange.of(-0.05, -0.005)),  // 2: RATE_DOWN_AVG
                DoubleChromosome.of(DoubleRange.of(0.1, 0.5)),       // 3: FUNDING_MAX_THRESHOLD (Rate lỗi của Classifier)

                // --- 6 THAM SỐ AI REJECT FILTER ---
                DoubleChromosome.of(DoubleRange.of(-0.15, -0.02)),   // 4: RISK_MAX_DD4H
                DoubleChromosome.of(DoubleRange.of(0.005, 0.04)),    // 5: MIN_RET_1H
                DoubleChromosome.of(DoubleRange.of(0.02, 0.10)),     // 6: HIGH_RET
                DoubleChromosome.of(DoubleRange.of(0.0048, 0.0094)), // 7: MIN_MOM_15M (🔥 FIX: LẤY THEO P10-P90 TRACE)
                DoubleChromosome.of(DoubleRange.of(-0.02, 0.05)),    // 8: MIN_TREND_4H
                DoubleChromosome.of(DoubleRange.of(-0.05, 0.0)),     // 9: DEAD_TREND_24H

                // --- 2 THAM SỐ DYNAMIC MARKET MỚI ---
                DoubleChromosome.of(DoubleRange.of(0.31, 1.14)),     // 10: DYN_K_DOWN (🔥 TỪ TRACE)
                DoubleChromosome.of(DoubleRange.of(0.33, 1.21))      // 11: DYN_K_UP (🔥 TỪ TRACE)
        );

        Engine<DoubleGene, Float> engine = Engine.builder(RunOptimizationCombined::evaluate, genotypeFactory)
                .populationSize(POPULATION_SIZE)
                .maximizing()
                .executor(Executors.newSingleThreadExecutor())
                .build();

        long startTime = System.currentTimeMillis();

        EvolutionResult<DoubleGene, Float> bestResult = engine.stream()
                .limit(GENERATIONS)
                .peek(r -> {
                    LOG.info(">>> Hoàn thành Thế hệ {}/{} | Điểm tốt nhất hiện tại: {}",
                            r.generation(), GENERATIONS, String.format("%.2f", r.bestFitness()));
                })
                .collect(EvolutionResult.toBestEvolutionResult());

        printFinalResult(bestResult, startTime);
    }

    private static Float evaluate(Genotype<DoubleGene> genotype) {
        long currentTest = testCounter.incrementAndGet();
        LOG.info("⏳ Trial #{} / {} ...", currentTest, TOTAL_TRIALS);

        // Bóc tách 12 biến từ Gen
        float pRateDown15M  = genotype.get(0).gene().floatValue();
        float pRateUpAvg    = genotype.get(1).gene().floatValue();
        float pRateDownAvg  = genotype.get(2).gene().floatValue();
        float pFundingThres = genotype.get(3).gene().floatValue();

        float pRisk         = genotype.get(4).gene().floatValue();
        float pMinRet1H     = genotype.get(5).gene().floatValue();
        float pHighRet      = genotype.get(6).gene().floatValue();
        float pMinMom15M    = genotype.get(7).gene().floatValue();
        float pMinTrend4H   = genotype.get(8).gene().floatValue();
        float pDeadTrend    = genotype.get(9).gene().floatValue();

        float pDynKDown     = genotype.get(10).gene().floatValue();
        float pDynKUp       = genotype.get(11).gene().floatValue();

        // Nạp vào Engine
        BackTestEngineCombined engine = new BackTestEngineCombined(
                pRateDown15M, pRateUpAvg, pRateDownAvg, pFundingThres,
                pRisk, pMinRet1H, pHighRet, pMinMom15M, pMinTrend4H, pDeadTrend,
                pDynKDown, pDynKUp
        );

        return engine.run(time2MarketData, predictionMap, time2FundingPre);
    }

    private static void loadDataReady() throws Exception {
        LOG.info("Loading Data from Aerospike...");
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;

        time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        time2FundingPre = DataManagerAerospikeFloatSim.getFundingPredictionsPrimitiveByRange(startTime, 60 * 24 * 30); // Giả sử cache 30 ngày

        LOG.info("✅ Data Ready.");
    }

    private static void printFinalResult(EvolutionResult<DoubleGene, Float> result, long startTime) {
        Genotype<DoubleGene> best = result.bestPhenotype().genotype();
        LOG.info("\n============================================================");
        LOG.info("=== KẾT QUẢ TỐI ƯU HÓA HOÀN TẤT (12 PARAMETERS COMBINED) ===");
        LOG.info("Thời gian chạy: {} phút", Duration.ofMillis(System.currentTimeMillis() - startTime).toMinutes());
        LOG.info("Fitness tốt nhất: {}", String.format("%.4f", result.bestFitness()));
        LOG.info("------------------------------------------------------------");
        LOG.info("--- 1. FUNDING FEE & ENTRY CONFIGS ---");
        LOG.info("Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD = {}f;", String.format("%.5f", best.get(3).gene().floatValue()));

        LOG.info("--- 2. AI REJECT FILTER CONFIGS ---");
        LOG.info("RISK_MAX_DD4H:  {}f;", String.format("%.5f", best.get(4).gene().floatValue()));
        LOG.info("MIN_RET_1H:     {}f;", String.format("%.5f", best.get(5).gene().floatValue()));
        LOG.info("HIGH_RET:       {}f;", String.format("%.5f", best.get(6).gene().floatValue()));
        LOG.info("MIN_MOM_15M:    {}f;", String.format("%.5f", best.get(7).gene().floatValue()));
        LOG.info("MIN_TREND_4H:   {}f;", String.format("%.5f", best.get(8).gene().floatValue()));
        LOG.info("DEAD_TREND_24H: {}f;", String.format("%.5f", best.get(9).gene().floatValue()));

        LOG.info("--- 3. DYNAMIC MARKET THRESHOLDS ---");
        LOG.info("Configs.DYN_K_DOWN: {}f;", String.format("%.5f", best.get(10).gene().floatValue()));
        LOG.info("Configs.DYN_K_UP:   {}f;", String.format("%.5f", best.get(11).gene().floatValue()));
        LOG.info("============================================================");
    }
}