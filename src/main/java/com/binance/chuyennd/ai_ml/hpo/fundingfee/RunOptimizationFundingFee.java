package com.binance.chuyennd.ai_ml.hpo.fundingfee;

import com.binance.chuyennd.ai_ml.data.HPOSmartCache;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.DataManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import io.jenetics.*;
import io.jenetics.engine.Engine;
import io.jenetics.engine.EvolutionResult;
import io.jenetics.util.Factory;
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

    public static void main(String[] args) {
        LOG.info("=== BẮT ĐẦU TỐI ƯU HÓA FUNDING FEE (4 PARAMS) ===");
        try {
            Configs.IS_HPO_MODE = true; // Bật chế độ HPO để tiết kiệm RAM
            Configs.TIME_RUN = "20250101";
            loadAndWarmUpData();
        } catch (Exception e) {
            e.printStackTrace();
            return;
        }

        // ĐỊNH NGHĨA GEN MỚI (Loại bỏ chromosome index 1 cũ)
        Factory<Genotype<DoubleGene>> gtf = Genotype.of(
                DoubleChromosome.of(-0.04, -0.015), // 0: MinTrade (DOWN_15M)
                DoubleChromosome.of(0.004, 0.012),  // 1: UpAvg
                DoubleChromosome.of(-0.012, -0.004),// 2: DownAvg
                DoubleChromosome.of(0.1, 0.5)       // 3: Funding Max Threshold
        );

        Engine<DoubleGene, Float> engine = Engine.builder(RunOptimizationFundingFee::eval, gtf)
                .populationSize(POPULATION_SIZE)
                .survivorsSelector(new TournamentSelector<>(3))
                .offspringSelector(new RouletteWheelSelector<>())
                .alterers(new Mutator<>(0.2), new MeanAlterer<>(0.6))
                .executor(Executors.newSingleThreadExecutor()) // An toàn cho VPS RAM thấp
                .build();

        long startTime = System.currentTimeMillis();
        EvolutionResult<DoubleGene, Float> bestResult = engine.stream()
                .limit(GENERATIONS)
                .peek(r -> LOG.info(">>> Gen {}/{} | Best Fitness: {}",
                        r.generation(), GENERATIONS, String.format("%.4f", r.bestFitness())))
                .collect(EvolutionResult.toBestEvolutionResult());

        printFinalResult(bestResult, startTime);
    }

    private static Float eval(Genotype<DoubleGene> gt) {
        long c = testCounter.incrementAndGet();

        // Map lại index sau khi đã xóa pMinFull
        float pMinTrade    = gt.get(0).gene().floatValue();
        float pUpAvg       = gt.get(1).gene().floatValue();
        float pDownAvg     = gt.get(2).gene().floatValue();
        float pFundingPred = gt.get(3).gene().floatValue();

        try {
            BackTestEngineFundingFee engine = new BackTestEngineFundingFee(
                    pMinTrade, pUpAvg, pDownAvg, pFundingPred
            );

            float score = engine.run(time2MarketData, predictionMap, time2FundingPre);

            LOG.info("Trial #{}/{}: Score={} | Params: [Min15m:{}, Up:{}, Down:{}, Thresh:{}]",
                    c, TOTAL_TRIALS, String.format("%.2f", score),
                    String.format("%.4f", pMinTrade), String.format("%.4f", pUpAvg),
                    String.format("%.4f", pDownAvg), String.format("%.4f", pFundingPred));

            return score;
        } catch (Exception e) {
            e.printStackTrace();
            return 0.0f;
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
        LOG.info("=== KẾT QUẢ TỐI ƯU HÓA HOÀN TẤT (4 PARAMS) ===");
        LOG.info("Thời gian chạy: {} phút", Duration.ofMillis(System.currentTimeMillis() - startTime).toMinutes());
        LOG.info("Fitness tốt nhất: {}", String.format("%.4f", result.bestFitness()));
        LOG.info("---------------------------------------------");
        LOG.info("Configs.PREDICT_SYMBOL_RATE_DOWN_15M      = {};", String.format("%.5f", best.get(0).gene().doubleValue()));
        LOG.info("Configs.PREDICT_SYMBOL_RATE_UP_AVG        = {};", String.format("%.5f", best.get(1).gene().doubleValue()));
        LOG.info("Configs.PREDICT_SYMBOL_RATE_DOWN_AVG      = {};", String.format("%.5f", best.get(2).gene().doubleValue()));
        LOG.info("Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD = {};", String.format("%.5f", best.get(3).gene().doubleValue()));
        LOG.info("=============================================");
    }
}