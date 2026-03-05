package com.binance.chuyennd.ai_ml.hpo.fundingfee;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
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
    public static TreeMap<Long, long[]> time2FundingPre; // 🔥 THÊM BIẾN NÀY

    public static void main(String[] args) {
        LOG.info("=== BẮT ĐẦU TỐI ƯU HÓA FUNDING FEE PARAMETERS ===");
        try {
//            Configs.IS_HPO_MODE = true;
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
                .peek(r -> LOG.info(">>> Gen {}/{} Xong. Fitness Tốt nhất: {}",
                        r.generation(), GENERATIONS, String.format("%.4f", r.bestFitness())))
                .collect(EvolutionResult.toBestEvolutionResult());

        printFinalResult(bestResult, startTime);
    }

    private static void printFinalResult(EvolutionResult<DoubleGene, Double> result, long startTime) {
        Genotype<DoubleGene> best = result.bestPhenotype().genotype();
        LOG.info("");
        LOG.info("=============================================");
        LOG.info("=== KẾT QUẢ TỐI ƯU HÓA HOÀN TẤT ===");
        LOG.info("Thời gian chạy: {} phút", Duration.ofMillis(System.currentTimeMillis() - startTime).toMinutes());
        LOG.info("Điểm Fitness cao nhất: {}", String.format("%.4f", result.bestFitness()));
        LOG.info("---------------------------------------------");
        LOG.info("aiPredictRateMaxThreshold = {};", String.format("%.5f", best.get(0).gene().doubleValue()));
        LOG.info("aiPredictRateDown15m      = {};", String.format("%.5f", best.get(1).gene().doubleValue()));
        LOG.info("aiPredictRateUpAvg        = {};", String.format("%.5f", best.get(2).gene().doubleValue()));
        LOG.info("aiPredictRateDownAvg      = {};", String.format("%.5f", best.get(3).gene().doubleValue()));
        LOG.info("=============================================");
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

            LOG.info("Trial #{}/{}: Score={} | Param: {}, {}, {}, {}, Thresh: {}",
                    c, TOTAL_TRIALS, String.format("%.2f", score),
                    String.format("%.4f", pMinTrade), String.format("%.4f", pMinFull),
                    String.format("%.4f", pUpAvg), String.format("%.4f", pDownAvg),
                    String.format("%.4f", pFundingPred));

            return score;

        } catch (Exception e) {
            e.printStackTrace();
            return 0.0;
        }
    }

    // Trong class RunOptimizationFundingFee

    private static void loadAndWarmUpData() throws Exception {
        LOG.info("Loading Data... {}", Configs.TIME_RUN);
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        int numberMinutes = System.currentTimeMillis() - startTime > 0 ? (int) ((System.currentTimeMillis() - startTime) / Utils.TIME_MINUTE) : 0;

        // SỬ DỤNG DATAMANAGER
        time2MarketData = DataManager.getMarketData();
        Utils.printMemoryUsage("Load time2MarketData");

        predictionMap = DataManager.getAiPredictionData();
        Utils.printMemoryUsage("Load predictionMap");

        time2FundingPre = DataManager.getFundingPredictionData(startTime, numberMinutes);
        Utils.printMemoryUsage("Load time2FundingPre");

        // Warmup HPOSmartCache (Đảm bảo HPOSmartCache bên trong cũng gọi DataManager.getTickers1M)
        LOG.info("🔥 Warming up cache ({}-NOW)...", Configs.TIME_RUN);
        long startTimeLoad = Utils.sdfFile.parse(Configs.TIME_RUN).getTime();
        long endTimeLoad = System.currentTimeMillis();
        long current = startTimeLoad;
        while (current < endTimeLoad) {
            // Lấy dữ liệu thông qua DataManager thay vì Aerospike trực tiếp
            DataManager.getTickers1M(current);
            // Nếu bạn vẫn muốn dùng HPOSmartCache thì gọi HPOSmartCache.getData(current);
            current += Utils.TIME_DAY;
        }
        Utils.printMemoryUsage("Load HPOSmartCache");
    }
}