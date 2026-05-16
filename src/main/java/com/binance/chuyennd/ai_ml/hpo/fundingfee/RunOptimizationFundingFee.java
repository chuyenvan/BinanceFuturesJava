package com.binance.chuyennd.ai_ml.hpo.fundingfee;

import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculator;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.DataManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import io.jenetics.*;
import io.jenetics.engine.Engine;
import io.jenetics.engine.EvolutionResult;
import io.jenetics.util.DoubleRange;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.TreeMap;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class RunOptimizationFundingFee {

    private static final Logger LOG = LoggerFactory.getLogger(RunOptimizationFundingFee.class);

    private static final int POPULATION_SIZE = 20;
    private static final int GENERATIONS = 30;
    private static final AtomicLong testCounter = new AtomicLong(0);
    private static final long TOTAL_TRIALS = (long) POPULATION_SIZE * GENERATIONS;

    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static TreeMap<Long, long[]> time2FundingPre;
    public static long offlineEndTime;

    public static void main(String[] args) {
        LOG.info("=== BẮT ĐẦU TỐI ƯU HÓA AI REJECT FILTER (3 PARAMS) ===");
        try {
            Configs.IS_HPO_MODE = true;
            Configs.TIME_RUN = "20260101"; // Chọn mốc thời gian phù hợp của bạn
            offlineEndTime = Utils.sdfFile.parse("20260430").getTime() + (24 * Utils.TIME_HOUR) - Utils.TIME_MINUTE;
            loadAndWarmUpData();
        } catch (Exception e) {
            e.printStackTrace();
            return;
        }

        // ĐỊNH NGHĨA GEN CHO 3 THAM SỐ AI REJECT FILTER
        Genotype<DoubleGene> gtf = Genotype.of(
                DoubleChromosome.of(DoubleRange.of(-0.12, -0.08)), // 0: HARD_RISK_LIMIT_4H
                DoubleChromosome.of(DoubleRange.of(0.012, 0.025)), // 1: MIN_MOMENTUM_15M
                DoubleChromosome.of(DoubleRange.of(0.01, 0.06))    // 2: MIN_MOMENTUM_24H
        );

        Engine<DoubleGene, Float> engine = Engine.builder(RunOptimizationFundingFee::eval, gtf)
                .populationSize(POPULATION_SIZE)
                .maximizing()
                .executor(Executors.newSingleThreadExecutor())
                .build();

        long startTime = System.currentTimeMillis();
        EvolutionResult<DoubleGene, Float> bestResult = engine.stream()
                .limit(GENERATIONS)
                .peek(r -> LOG.info(String.format("\n>>> 🏆 BEST GEN %d/%d | SCORE: %.2f <<<\n", r.generation(), GENERATIONS, r.bestFitness())))
                .collect(EvolutionResult.toBestEvolutionResult());

        printFinalResult(bestResult, startTime);
    }

    private static Float eval(Genotype<DoubleGene> gt) {
        long c = testCounter.incrementAndGet();

        float pRisk = gt.get(0).gene().floatValue();
        float pMin15M = gt.get(1).gene().floatValue();
        float pMin24H = gt.get(2).gene().floatValue();

        try {
            BackTestEngineFundingFee engine = new BackTestEngineFundingFee(
                    pRisk, pMin15M, pMin24H
            );

            HPOFitnessCalculator.FitnessReport report = engine.run(time2MarketData, predictionMap, time2FundingPre, offlineEndTime);

            // ========================================================
            // 🔥 LUẬT THÉP: SOFT PENALTY (PHẠT CÓ ĐỘ DỐC)
            // ========================================================
            float maxAllowedDrawdown = -15000f; // Ngưỡng Drawdown tối đa cho phép

            if (report.maxDrawdown < maxAllowedDrawdown) {
                float excessDrawdown = Math.abs(report.maxDrawdown) - Math.abs(maxAllowedDrawdown);
                report.finalFitness = report.finalFitness - (excessDrawdown * 5f);
                report.note = "PENALTY: Over MaxDD";
            }

            LOG.info(String.format("Trial %4d/%d | Score: %8.1f | Trades: %4d | PnL: %6.1f$ | MaxDD: %6.1f$ | Pen: %4.1f$ | Risk: %.5f | 15M: %.5f | 24H: %.5f | %s",
                    c, TOTAL_TRIALS, report.finalFitness,
                    report.tradeCount, report.totalProfit, report.maxDrawdown,
                    report.penaltyCost, pRisk, pMin15M, pMin24H, report.note));

            return report.finalFitness;

        } catch (Exception e) {
            e.printStackTrace();
            return -10000.0f;
        } finally {
            System.gc(); // Giải phóng rác sau mỗi lần Backtest
        }
    }

    private static void loadAndWarmUpData() throws Exception {
        LOG.info("Loading Data (Kaggle/Offline Priority)...");
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        int numberMinutes = (int) ((System.currentTimeMillis() - startTime) / Utils.TIME_MINUTE);

        time2MarketData = DataManager.getMarketData();
        predictionMap = DataManager.getAiPredictionData();
        time2FundingPre = DataManager.getFundingPredictionData(startTime, numberMinutes);

        LOG.info("🔥 Warming up HPOSmartCache...");
        long current = Utils.sdfFile.parse(Configs.TIME_RUN).getTime();
        long endTimeLoad = System.currentTimeMillis();
        while (current < endTimeLoad) {
            DataManager.getTickers1M(current);
            current += Utils.TIME_DAY;
        }
        LOG.info("✅ Data Ready.");
    }

    private static void printFinalResult(EvolutionResult<DoubleGene, Float> result, long startTime) {
        Genotype<DoubleGene> best = result.bestPhenotype().genotype();
        LOG.info("\n=============================================");
        LOG.info("=== KẾT QUẢ TỐI ƯU HÓA AI REJECT FILTER (3 PARAMS) ===");
        LOG.info("Thời gian chạy: {} phút", Duration.ofMillis(System.currentTimeMillis() - startTime).toMinutes());
        LOG.info("Fitness tốt nhất: {}", String.format("%.4f", result.bestFitness()));
        LOG.info("---------------------------------------------");
        LOG.info("HARD_RISK_LIMIT_4H = {}f;", String.format("%.5f", best.get(0).gene().floatValue()));
        LOG.info("MIN_MOMENTUM_15M   = {}f;", String.format("%.5f", best.get(1).gene().floatValue()));
        LOG.info("MIN_MOMENTUM_24H   = {}f;", String.format("%.5f", best.get(2).gene().floatValue()));
        LOG.info("=============================================");
    }
}