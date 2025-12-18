package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.ai_ml.data.HPOSmartCache;
import com.binance.chuyennd.ai_ml.onnx.entry.AiPredictionData;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import io.jenetics.*;
import io.jenetics.engine.Engine;
import io.jenetics.engine.EvolutionResult;
import io.jenetics.engine.Limits;
import io.jenetics.util.Factory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class RunOptimizationAI {

    private static final Logger LOG = LoggerFactory.getLogger(RunOptimizationAI.class);

    // --- GLOBAL DATA STORE ---
    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, MarketRateChange> time2MarketRateChange;
    public static TreeMap<Long, Double> time2BtcReverse;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static ConcurrentHashMap<Long, Set<String>> CACHED_time2FundingFeeTrade;

    // --- CẤU HÌNH PARAM GEN (NỚI RỘNG ĐỂ TÌM KIẾM ĐỘT PHÁ) ---
    // 1. Risk: Cho phép rủi ro sâu hơn (từ -1% đến -6%) để bắt dao sâu hơn
    private static final double MIN_RISK = -0.06, MAX_RISK = -0.01;

    // 2. Ret1H: Mở rộng biên độ lợi nhuận (từ 0.5% đến 6%)
    private static final double MIN_RET1H = 0.005, MAX_RET1H = 0.06;

    // 3. HighRet: Ngưỡng "kèo thơm"
    private static final double MIN_HIGHRET = 0.03, MAX_HIGHRET = 0.10;

    // 4. Momentum & Trend: Cho phép bắt cả sóng yếu lẫn sóng mạnh
    private static final double MIN_MOM15M = 0.001, MAX_MOM15M = 0.02;
    private static final double MIN_TREND4H = 0.001, MAX_TREND4H = 0.03;

    public static void main(String[] args) {
        LOG.info("==============================================");
        LOG.info("===   AI HPO: DEEP SEARCH MODE             ===");
        LOG.info("===   STRATEGY: WIDER RANGE & SMART SCORE  ===");
        LOG.info("==============================================\n");

        try {
            // TIME_RUN phải là 2021 hoặc 2022 để bao phủ đủ dữ liệu
            Configs.TIME_RUN = "20210101";
            loadAndWarmUpData();
        } catch (Exception e) {
            e.printStackTrace();
            return;
        }

        LOG.info("\n🚀 --- STARTING EVOLUTION ---");

        // Tăng số luồng để chạy nhanh
        int nThreads = Runtime.getRuntime().availableProcessors();
        ExecutorService executor = Executors.newFixedThreadPool(nThreads);
        LOG.info("⚡ Engine running with {} threads.", nThreads);

        Factory<Genotype<DoubleGene>> gtf = Genotype.of(
                DoubleChromosome.of(MIN_RISK, MAX_RISK),
                DoubleChromosome.of(MIN_RET1H, MAX_RET1H),
                DoubleChromosome.of(MIN_HIGHRET, MAX_HIGHRET),
                DoubleChromosome.of(MIN_MOM15M, MAX_MOM15M),
                DoubleChromosome.of(MIN_TREND4H, MAX_TREND4H)
        );

        Engine<DoubleGene, Double> engine = Engine.builder(RunOptimizationAI::eval, gtf)
                // --- TĂNG NHẸ QUY MÔ ĐỂ THOÁT KHỎI CỰC TRỊ CỤC BỘ ---
                .populationSize(30) // Tăng từ 15 -> 30 để đa dạng gen hơn
                .survivorsSelector(new TournamentSelector<>(3))
                .offspringSelector(new RouletteWheelSelector<>())
                // Tăng Mutation (0.25) để AI dám thử nghiệm cái mới lạ
                .alterers(new Mutator<>(0.25), new MeanAlterer<>(0.6))
                .executor(executor)
                .build();

        EvolutionResult<DoubleGene, Double> bestResult = engine.stream()
                // Cho phép chạy lâu hơn 1 chút để tìm ra kết quả tốt nhất
                .limit(Limits.bySteadyFitness(5))
                .limit(20) // Max 20 thế hệ (khoảng 600 lần test)
                .peek(RunOptimizationAI::monitor)
                .collect(EvolutionResult.toBestEvolutionResult());

        executor.shutdown();

        LOG.info("\n=== 🏁 OPTIMIZATION FINISHED ===");
        LOG.info("🏆 BEST PROFIT SCORE: " + bestResult.bestFitness());
        printParams("BEST PARAMS FOUND", bestResult.bestPhenotype().genotype());
    }

    private static void monitor(EvolutionResult<DoubleGene, Double> result) {
        LOG.info("Gen {}: Best Score = {}", result.generation(), String.format("%.2f", result.bestFitness()));
    }

    private static Double eval(Genotype<DoubleGene> gt) {
        try {
            BackTestEngineAI engine = new BackTestEngineAI(
                    gt.get(0).gene().doubleValue(),
                    gt.get(1).gene().doubleValue(),
                    gt.get(2).gene().doubleValue(),
                    gt.get(3).gene().doubleValue(),
                    gt.get(4).gene().doubleValue(),
                    -0.99
            );
            return engine.run(time2MarketData, time2MarketRateChange, time2BtcReverse, predictionMap);
        } catch (Exception e) {
            return -100000.0;
        }
    }

    private static void printParams(String title, Genotype<DoubleGene> bestGt) {
        LOG.info("🛠 {}: ", title);
        LOG.info("   Risk (MaxDD4H): {}", String.format("%.5f", bestGt.get(0).gene().doubleValue()));
        LOG.info("   MinRet1H      : {}", String.format("%.5f", bestGt.get(1).gene().doubleValue()));
        LOG.info("   HighRet       : {}", String.format("%.5f", bestGt.get(2).gene().doubleValue()));
        LOG.info("   MinMom15M     : {}", String.format("%.5f", bestGt.get(3).gene().doubleValue()));
        LOG.info("   MinTrend4H    : {}", String.format("%.5f", bestGt.get(4).gene().doubleValue()));
    }

    private static void loadAndWarmUpData() throws Exception {
        LOG.info("Loading Data...");
        CACHED_time2FundingFeeTrade = (ConcurrentHashMap<Long, Set<String>>) StorageSnappy.readObjectFromFile(FundingFeeManager.FILE_FUNDING_FEE);
        time2MarketRateChange = (TreeMap<Long, MarketRateChange>) StorageSnappy.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);
        time2MarketData = (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
        time2BtcReverse = (TreeMap<Long, Double>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_BTC_REVERSE);
        predictionMap = (TreeMap<Long, AiPredictionData>) StorageSnappy.readObjectFromFile(Configs.FILE_AI_ENTRY_PREDICTIONS);
        FundingFeeManager.getInstance();

        LOG.info("🔥 Warming up cache...");
        long startTimeLoad = Utils.sdfFile.parse(Configs.TIME_RUN).getTime();
        long endTimeLoad = System.currentTimeMillis();
        long current = startTimeLoad;
        while (current < endTimeLoad) {
            HPOSmartCache.getData(current);
            current += Utils.TIME_DAY;
        }
        LOG.info("✅ Cache Ready.");
    }
}