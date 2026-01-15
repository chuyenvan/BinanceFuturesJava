package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.ai_ml.data.HPOSmartCache;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
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
import java.util.concurrent.atomic.AtomicInteger;

public class RunOptimizationAI {

    private static final Logger LOG = LoggerFactory.getLogger(RunOptimizationAI.class);

    // --- GLOBAL DATA STORE ---
    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, MarketRateChange> time2MarketRateChange;
    public static TreeMap<Long, Double> time2BtcReverse;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static ConcurrentHashMap<Long, Set<String>> CACHED_time2FundingFeeTrade;

    // Bộ đếm số lần thử nghiệm để biết tiến độ
    private static final AtomicInteger evalCounter = new AtomicInteger(0);

    // --- CẤU HÌNH PARAM GEN ---
    private static final double MIN_RISK = -0.06, MAX_RISK = -0.01;
    private static final double MIN_RET1H = 0.005, MAX_RET1H = 0.06;
    private static final double MIN_HIGHRET = 0.01, MAX_HIGHRET = 0.10;
    private static final double MIN_MOM15M = 0.001, MAX_MOM15M = 0.02;
    private static final double MIN_TREND4H = 0.001, MAX_TREND4H = 0.03;

    public static void main(String[] args) {
        LOG.info("==============================================");
        LOG.info("===   AI HPO: SINGLE THREAD (SAFE MODE)    ===");
        LOG.info("===   Fix: Data Race & Real-time Log       ===");
        LOG.info("==============================================\n");

        try {
            Configs.TIME_RUN = "20250101";
            loadAndWarmUpData();
        } catch (Exception e) {
            e.printStackTrace();
            return;
        }

        LOG.info("\n🚀 --- STARTING EVOLUTION ---");

        // CẤU HÌNH GENE
        Factory<Genotype<DoubleGene>> gtf = Genotype.of(
                DoubleChromosome.of(MIN_RISK, MAX_RISK),
                DoubleChromosome.of(MIN_RET1H, MAX_RET1H),
                DoubleChromosome.of(MIN_HIGHRET, MAX_HIGHRET),
                DoubleChromosome.of(MIN_MOM15M, MAX_MOM15M),
                DoubleChromosome.of(MIN_TREND4H, MAX_TREND4H)
        );

        // --- QUAN TRỌNG: CHẠY 1 LUỒNG ĐỂ TRÁNH LỖI SINGLETON ---
        // Đã bỏ .executor() để mặc định chạy main thread
        Engine<DoubleGene, Double> engine = Engine.builder(RunOptimizationAI::eval, gtf)
                .populationSize(20) // 20 cá thể mỗi thế hệ
                .survivorsSelector(new TournamentSelector<>(3))
                .offspringSelector(new RouletteWheelSelector<>())
                .alterers(new Mutator<>(0.25), new MeanAlterer<>(0.6))
                .build();

        EvolutionResult<DoubleGene, Double> bestResult = engine.stream()
                .limit(Limits.bySteadyFitness(5)) // Dừng nếu 5 gen không cải thiện
                .limit(20) // Chạy tối đa 20 gen
                .peek(RunOptimizationAI::monitor)
                .collect(EvolutionResult.toBestEvolutionResult());

        LOG.info("\n=== 🏁 OPTIMIZATION FINISHED ===");
        LOG.info("🏆 FINAL BEST SCORE: " + bestResult.bestFitness());
        printParams("FINAL PARAMS", bestResult.bestPhenotype().genotype());
    }

    // --- MONITOR: TỔNG KẾT SAU MỖI GEN ---
    private static void monitor(EvolutionResult<DoubleGene, Double> result) {
        Genotype<DoubleGene> bestGt = result.bestPhenotype().genotype();
        double bestScore = result.bestFitness();
        int gen = (int) result.generation();

        LOG.info("----------------------------------------------------------------");
        LOG.info("📍 Gen {:02d} COMPLETE | Best Score So Far: {:.2f}", gen, bestScore);
        printParams("BEST OF GEN " + gen, bestGt);
        evalCounter.set(0); // Reset bộ đếm cho Gen mới để dễ theo dõi
        LOG.info("----------------------------------------------------------------");
    }

    // --- EVAL: ĐÁNH GIÁ TỪNG CÁ THỂ (CÓ LOG CHI TIẾT) ---
    private static Double eval(Genotype<DoubleGene> gt) {
        int count = evalCounter.incrementAndGet();

        // Lấy tham số ra để log
        double pRisk = gt.get(0).gene().doubleValue();
        double pRet1H = gt.get(1).gene().doubleValue();
        double pHighRet = gt.get(2).gene().doubleValue();
        double pMom15M = gt.get(3).gene().doubleValue();
        double pTrend4H = gt.get(4).gene().doubleValue();

        long start = System.currentTimeMillis();
        try {
            // Khởi tạo Engine Backtest với bộ tham số của cá thể này
            BackTestEngineAI engine = new BackTestEngineAI(
                    pRisk, pRet1H, pHighRet, pMom15M, pTrend4H, -0.99
            );

            Double score = engine.run(time2MarketData, time2MarketRateChange, time2BtcReverse, predictionMap);

            long duration = (System.currentTimeMillis() - start) / 1000;

            // --- LOG TIẾN ĐỘ THỜI GIAN THỰC ---
            // Format: [#STT] Score | Time | Các tham số chính
            LOG.info("   [#{}] Score: {:8.0f} ({:3}s) | Risk:{:.4f} | R1H:{:.4f} | Mom:{:.4f}",
                    count, score, duration, pRisk, pRet1H, pMom15M);

            return score;
        } catch (Exception e) {
            LOG.error("Eval Error", e);
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

//        LOG.info("🔥 Warming up cache ({}-NOW)...", Configs.TIME_RUN);
//        long startTimeLoad = Utils.sdfFile.parse(Configs.TIME_RUN).getTime();
//        long endTimeLoad = System.currentTimeMillis();
//        long current = startTimeLoad;
//        while (current < endTimeLoad) {
//            HPOSmartCache.getData(current);
//            current += Utils.TIME_DAY;
//        }
//        LOG.info("✅ Cache Ready. Start Optimization!");
    }
}