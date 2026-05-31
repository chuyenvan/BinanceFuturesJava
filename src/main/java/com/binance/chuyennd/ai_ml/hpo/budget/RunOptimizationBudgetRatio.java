package com.binance.chuyennd.ai_ml.hpo.budget;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.HPOSmartCache;
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

public class RunOptimizationBudgetRatio {
    public static final Logger LOG = LoggerFactory.getLogger(RunOptimizationBudgetRatio.class);
    private static final int POPULATION_SIZE = 10;
    private static final int GENERATIONS = 20;
    private static final long TOTAL_TRIALS = POPULATION_SIZE * GENERATIONS;

    private static final AtomicLong testCounter = new AtomicLong(0);

    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static TreeMap<Long, long[]> time2FundingPre;

    private static float evaluate(Genotype<DoubleGene> genotype) {

        long currentTestNumber = testCounter.incrementAndGet();

        float ratio1 = genotype.get(0).gene().floatValue();
        float divider1 = genotype.get(1).gene().floatValue();
        float ratio2 = genotype.get(2).gene().floatValue();
        float divider2 = genotype.get(3).gene().floatValue();
        float trendUp = genotype.get(4).gene().floatValue();
        float trendDown = genotype.get(5).gene().floatValue();

        float finalBalance = 0.0f;

        LOG.info("--- Bat dau Test #%d / %d ---%n{R1=%.2f, D1=%.1f, R2=%.2f, D2=%.1f, Up=%.1f, Down=%.1f}%n",
                currentTestNumber, TOTAL_TRIALS, ratio1, divider1, ratio2, divider2, trendUp, trendDown);

        try {
            BackTestEngineBudgetRatio engine = new BackTestEngineBudgetRatio(ratio1, divider1, ratio2, divider2);

            finalBalance = engine.run(time2MarketData, predictionMap, time2FundingPre);

            LOG.info("--- Ket thuc Test #%d / %d => Loi nhuan: %.2f ---%n", currentTestNumber, TOTAL_TRIALS, finalBalance);

        } catch (Exception e) {
            e.printStackTrace();
            LOG.info("--- Test #%d / %d BI LOI => Loi nhuan: 0.0 ---%n", currentTestNumber, TOTAL_TRIALS);
            return 0.0f;
        }

        return finalBalance;
    }

    private static void loadAndWarmUpData() throws Exception {
        LOG.info("Loading Data... {}", Configs.TIME_RUN);
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        int numberMinutes = System.currentTimeMillis() - startTime > 0 ? (int) ((System.currentTimeMillis() - startTime) / Utils.TIME_MINUTE) : 0;

        time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        Utils.printMemoryUsage("Load time2MarketData");

        predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        Utils.printMemoryUsage("Load predictionMap");

        time2FundingPre = DataManagerAerospikeFloatSim.getFundingPredictionsPrimitiveByRange(startTime, numberMinutes); // HOẶC HÀM GET THEO RANGE CỦA BẠN
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

    public static void main(String[] args) throws Exception {

        Configs.IS_HPO_MODE = true;
        loadAndWarmUpData();

        long startTime = System.currentTimeMillis();

        Genotype<DoubleGene> genotypeFactory = Genotype.of(DoubleChromosome.of(DoubleRange.of(0.2, 0.5)), DoubleChromosome.of(DoubleRange.of(1.5, 2.5)), DoubleChromosome.of(DoubleRange.of(0.5, 0.8)), DoubleChromosome.of(DoubleRange.of(1.5, 2.5)), DoubleChromosome.of(DoubleRange.of(1.0, 1.2)), DoubleChromosome.of(DoubleRange.of(0.8, 1.0)));

        Engine<DoubleGene, Float> engine = Engine.builder(RunOptimizationBudgetRatio::evaluate, genotypeFactory).populationSize(POPULATION_SIZE).maximizing().executor(Executors.newSingleThreadExecutor()).build();

        EvolutionResult<DoubleGene, Float> result = engine.stream().peek(
                er -> LOG.info("%n>>> Hoan tat The he %d / %d. Loi nhuan tot nhat hien tai: %.2f%n%n", er.generation(), GENERATIONS, er.bestFitness())).limit(GENERATIONS).collect(EvolutionResult.toBestEvolutionResult());

        Genotype<DoubleGene> bestParams = result.bestPhenotype().genotype();
        float bestProfit = result.bestFitness();
        long totalTime = System.currentTimeMillis() - startTime;

        float r1 = bestParams.get(0).gene().floatValue();
        float d1 = bestParams.get(1).gene().floatValue();
        float r2 = bestParams.get(2).gene().floatValue();
        float d2 = bestParams.get(3).gene().floatValue();
        float tUp = bestParams.get(4).gene().floatValue();
        float tDown = bestParams.get(5).gene().floatValue();

        LOG.info("\n=============================================");
        LOG.info("=== TOI UU HOA QUAN LY VON HOAN TAT ===");
        LOG.info("Thoi gian chay: " + Duration.ofMillis(totalTime).toMinutes() + " phut");
        LOG.info(String.format("Loi nhuan cao nhat: %.2f", bestProfit));
        LOG.info("Voi cac tham so tot nhat:");
        LOG.info(String.format(" - BUDGET_MARGIN_RATIO_1:     %.4f", r1));
        LOG.info(String.format(" - BUDGET_DIVIDER_1:          %.4f", d1));
        LOG.info(String.format(" - BUDGET_MARGIN_RATIO_2:     %.4f", r2));
        LOG.info(String.format(" - BUDGET_DIVIDER_2:          %.4f", d2));
        LOG.info(String.format(" - BUDGET_TREND_UP_MULTIPLIER:  %.4f", tUp));
        LOG.info(String.format(" - BUDGET_TREND_DOWN_MULTIPLIER:%.4f", tDown));
        LOG.info("=============================================");
    }
}