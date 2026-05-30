package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.HPOSmartCache;
import com.binance.chuyennd.ai_ml.onnx.entry.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject15M;
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
import java.util.TreeMap;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class RunOptimizationAIMarket {

    private static final Logger LOG = LoggerFactory.getLogger(RunOptimizationAIMarket.class);

    private static final int POPULATION_SIZE = 15;
    private static final int GENERATIONS = 30;

    public static TreeMap<Long, MarketDataObject15M> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static TreeMap<Long, long[]> time2FundingPre;
    private static final AtomicLong testCounter = new AtomicLong(0);

    private static final float MIN_RISK = -0.06f, MAX_RISK = -0.01f;
    private static final float MIN_RET1H = 0.005f, MAX_RET1H = 0.06f;
    private static final float MIN_HIGHRET = 0.01f, MAX_HIGHRET = 0.10f;
    private static final float MIN_MOM15M = 0.001f, MAX_MOM15M = 0.02f;
    private static final float MIN_TREND4H = 0.001f, MAX_TREND4H = 0.03f;

    public static void main(String[] args) {
        LOG.info("=== START OPTIMIZING AI MARKET THRESHOLDS ===");

        try {
            Configs.TIME_RUN = "20250101";
            loadAndWarmUpData();
        } catch (Exception e) {
            LOG.error("Lỗi khởi tạo: ", e);
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

        Engine<DoubleGene, Float> engine = Engine.builder(RunOptimizationAIMarket::evaluate, genotypeFactory)
                .populationSize(POPULATION_SIZE)
                .maximizing()
                .executor(Executors.newSingleThreadExecutor())
                .build();

        EvolutionResult<DoubleGene, Float> result = engine.stream()
                .limit(GENERATIONS)
                .peek(r -> LOG.info(">>> Generation {} Best: {}", r.generation(), String.format("%.2f", r.bestFitness())))
                .collect(EvolutionResult.toBestEvolutionResult());

        printResult(result, startTime);
    }

    private static Float evaluate(Genotype<DoubleGene> genotype) {
        long currentTest = testCounter.incrementAndGet();

        float pRisk = genotype.get(0).gene().floatValue();
        float pRet1H = genotype.get(1).gene().floatValue();
        float pHighRet = genotype.get(2).gene().floatValue();
        float pMom15M = genotype.get(3).gene().floatValue();
        float pTrend4H = genotype.get(4).gene().floatValue();

        try {
            // Logic tính toán profit thực tế của bạn
            float profit = 0f;

            LOG.info("Test #{}: Profit={} | Risk={} | R1H={} | HighR={} | Mom15={} | Trend4={}",
                    currentTest, String.format("%.2f", profit),
                    String.format("%.4f", pRisk), String.format("%.4f", pRet1H),
                    String.format("%.4f", pHighRet), String.format("%.4f", pMom15M),
                    String.format("%.4f", pTrend4H));

            return profit;
        } catch (Exception e) {
            LOG.error("Lỗi Eval: ", e);
            return -100000.0f;
        }
    }

    private static void loadAndWarmUpData() throws Exception {
        LOG.info("Loading Data... {}", Configs.TIME_RUN);
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        int numberMinutes = System.currentTimeMillis() - startTime > 0 ? (int) ((System.currentTimeMillis() - startTime) / Utils.TIME_MINUTE) : 0;

        time2MarketData = DataManagerAerospikeFloatSim.getAllMarketData15MFromAerospike();
        predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        time2FundingPre = DataManagerAerospikeFloatSim.getFundingPredictionsPrimitiveByRange(startTime, numberMinutes);

        LOG.info("🔥 Warming up cache...");
        long startTimeLoad = Utils.sdfFile.parse(Configs.TIME_RUN).getTime();
        long current = startTimeLoad;
        while (current < System.currentTimeMillis()) {
            HPOSmartCache.getData(current);
            current += Utils.TIME_DAY;
        }
    }

    private static void printResult(EvolutionResult<DoubleGene, Float> result, long startTime) {
        Genotype<DoubleGene> best = result.bestPhenotype().genotype();
        LOG.info("");
        LOG.info("=== KẾT QUẢ TỐI ƯU AI MARKET THRESHOLDS ===");
        LOG.info("Time: {} mins", Duration.ofMillis(System.currentTimeMillis() - startTime).toMinutes());
        LOG.info("Profit Max: {}", result.bestFitness());
        LOG.info("------------------------------------");
        LOG.info("RISK_MAX_DD4H:  {}", String.format("%.5f", best.get(0).gene().floatValue()));
        LOG.info("MIN_RET_1H:     {}", String.format("%.5f", best.get(1).gene().floatValue()));
        LOG.info("HIGH_RET:       {}", String.format("%.5f", best.get(2).gene().floatValue()));
        LOG.info("MIN_MOM_15M:    {}", String.format("%.5f", best.get(3).gene().floatValue()));
        LOG.info("MIN_TREND_4H:   {}", String.format("%.5f", best.get(4).gene().floatValue()));
        LOG.info("====================================");
    }
}