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
import io.jenetics.util.Factory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Iterator;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class RunOptimizationAI {

    private static final Logger LOG = LoggerFactory.getLogger(RunOptimizationAI.class);

    // --- GLOBAL DATA STORE ---
    // (Đã bỏ symbol2TrendData theo code mẫu của bạn)
    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, MarketRateChange> time2MarketRateChange;
    public static TreeMap<Long, Double> time2BtcReverse;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static ConcurrentHashMap<Long, Set<String>> CACHED_time2FundingFeeTrade;

    // --- CẤU HÌNH 5 THAM SỐ (Đã thêm lại Trend 4H) ---

    // 1. Risk: Mức cắt lỗ
    private static final double MIN_RISK = -0.15, MAX_RISK = -0.01;

    // 2. Ret1H: Dự báo lợi nhuận 1H
    private static final double MIN_RET1H = 0.005, MAX_RET1H = 0.03;

    // 3. HighRet: Ngưỡng "Kèo Thơm"
    private static final double MIN_HIGHRET = 0.02, MAX_HIGHRET = 0.06;

    // 4. Mom15M: Động lượng ngắn hạn
    private static final double MIN_MOM15M = 0.001, MAX_MOM15M = 0.015;

    // 5. Trend4H: Xu hướng trung hạn (ĐÃ THÊM LẠI)
    // Range: 0.1% -> 2% (Tìm điểm cân bằng giữa an toàn và số lượng lệnh)
    private static final double MIN_TREND4H = 0.001, MAX_TREND4H = 0.02;

    // 6. DeadTrend24H: Vẫn bỏ qua
    // private static final double MIN_DEADTREND = -0.20, MAX_DEADTREND = -0.01;

    public static void main(String[] args) {
        LOG.info("==============================================");
        LOG.info("===   AI HYPERPARAMETER OPTIMIZATION SYSTEM   ===");
        LOG.info("===   MODE: SINGLE PHASE | 5 PARAMS (+Trend4H) ===");
        LOG.info("==============================================\n");

        // 1. LOAD DATA VÀO RAM
        try {
            Configs.TIME_RUN = "20220101";
            loadAndWarmUpData();
        } catch (Exception e) {
            e.printStackTrace();
            LOG.error("❌ CRITICAL ERROR: Failed to load data.");
            return;
        }

        // 2. CHẠY KIỂM TRA TÍNH NHẤT QUÁN
        LOG.info("\n🛑 --- STARTING CONSISTENCY CHECK ---");
        boolean isStable = runConsistencyCheck();
        if (isStable) {
            LOG.info("✅ SYSTEM STABLE. Proceeding...");
        } else {
            LOG.warn("⚠️ DATA UNSTABLE. Proceed with caution.");
        }

        // =====================================================================
        // SINGLE PHASE EVOLUTION (300 GENERATIONS)
        // =====================================================================
        LOG.info("\n🚀 --- STARTING EVOLUTION (300 Gens) ---");

        // Factory tạo 5 Chromosome (Risk, Ret1H, HighRet, Mom15M, Trend4H)
        Factory<Genotype<DoubleGene>> gtf = Genotype.of(
                DoubleChromosome.of(MIN_RISK, MAX_RISK),       // 0. Risk
                DoubleChromosome.of(MIN_RET1H, MAX_RET1H),     // 1. MinRet1H
                DoubleChromosome.of(MIN_HIGHRET, MAX_HIGHRET), // 2. HighRet
                DoubleChromosome.of(MIN_MOM15M, MAX_MOM15M),   // 3. Mom15M
                DoubleChromosome.of(MIN_TREND4H, MAX_TREND4H)  // 4. Trend4H (MỚI)
        );

        Engine<DoubleGene, Double> engine = Engine.builder(RunOptimizationAI::eval, gtf)
                .populationSize(20)
                .survivorsSelector(new TournamentSelector<>(3))
                .offspringSelector(new RouletteWheelSelector<>())
                .alterers(new Mutator<>(0.1), new MeanAlterer<>(0.3))
                .executor(Runnable::run)
                .build();

        EvolutionResult<DoubleGene, Double> bestResult = runEvolutionLoop(engine, 300);

        // KẾT QUẢ CUỐI CÙNG
        LOG.info("\n=== OPTIMIZATION FINISHED ===");
        LOG.info("🏆 FINAL BEST PROFIT: " + bestResult.bestFitness());
        printParams("FINAL RESULT", bestResult.bestPhenotype().genotype());
    }

    private static EvolutionResult<DoubleGene, Double> runEvolutionLoop(
            Engine<DoubleGene, Double> engine, int maxGenerations) {

        Iterator<EvolutionResult<DoubleGene, Double>> stream = engine.stream().iterator();
        EvolutionResult<DoubleGene, Double> bestResult = null;
        int currentGen = 1;

        while (stream.hasNext() && currentGen <= maxGenerations) {
            EvolutionResult<DoubleGene, Double> result = stream.next();

            if (bestResult == null || result.bestFitness() > bestResult.bestFitness()) {
                bestResult = result;
                LOG.info("🔥 NEW BEST at Gen {}: {}", currentGen, String.format("%.2f", bestResult.bestFitness()));
            } else {
                if (currentGen % 10 == 0) {
                    LOG.info("... Gen {} | Current Best: {}", currentGen, String.format("%.2f", bestResult.bestFitness()));
                }
            }

            if (currentGen % 10 == 0) {
                System.gc();
                printRamUsage();
            }

            currentGen++;
        }
        return bestResult;
    }

    private static void printRamUsage() {
        Runtime rt = Runtime.getRuntime();
        long usedMB = (rt.totalMemory() - rt.freeMemory()) / 1024 / 1024;
        LOG.info("   [RAM CHECK] Used: {} MB", usedMB);
    }

    // --- HÀM MỤC TIÊU (FITNESS FUNCTION) ---
    private static Double eval(Genotype<DoubleGene> gt) {
        try {
            // Truyền 5 tham số Gen + 1 tham số Dummy (DeadTrend24H)
            BackTestEngineAI engine = new BackTestEngineAI(
                    gt.get(0).gene().doubleValue(), // 1. Risk
                    gt.get(1).gene().doubleValue(), // 2. MinRet1H
                    gt.get(2).gene().doubleValue(), // 3. HighRet
                    gt.get(3).gene().doubleValue(), // 4. Mom15M
                    gt.get(4).gene().doubleValue(), // 5. Trend4H (Đã kích hoạt lại)
                    -0.99                           // 6. DeadTrend24H (Vẫn tắt)
            );

            // Chạy Run mà không cần symbol2TrendData (theo code mẫu bạn gửi)
            Double profit = engine.run(time2MarketData, time2MarketRateChange, time2BtcReverse, predictionMap);

            return profit;

        } catch (Exception e) {
            return -10000.0;
        }
    }

    private static void printParams(String title, Genotype<DoubleGene> bestGt) {
        LOG.info("🛠 {}: ", title);
        LOG.info("   Risk         : {}", String.format("%.5f", bestGt.get(0).gene().doubleValue()));
        LOG.info("   MinRet1H     : {}", String.format("%.5f", bestGt.get(1).gene().doubleValue()));
        LOG.info("   HighRet      : {}", String.format("%.5f", bestGt.get(2).gene().doubleValue()));
        LOG.info("   MinMom15M    : {}", String.format("%.5f", bestGt.get(3).gene().doubleValue()));
        LOG.info("   MinTrend4H   : {}", String.format("%.5f", bestGt.get(4).gene().doubleValue()));
        LOG.info("   (DeadTrend)  : DISABLED");
    }

    private static boolean runConsistencyCheck() {
        double pRisk = -0.05;
        double pMinRet1H = 0.02;
        double pHighRet = 0.08;
        double pMinMom15M = 0.01;
        double pTrend4H = 0.01; // Test value for Trend4H

        LOG.info("   [Check Params]: Risk={}, Trend4H={} ...", pRisk, pTrend4H);
        Double firstScore = null;
        boolean isConsistent = true;

        for (int i = 1; i <= 3; i++) {
            BackTestEngineAI testEngine = new BackTestEngineAI(
                    pRisk, pMinRet1H, pHighRet, pMinMom15M, pTrend4H, -0.99
            );
            Double currentScore = testEngine.run(
                    time2MarketData, time2MarketRateChange, time2BtcReverse, predictionMap);

            if (firstScore == null) {
                firstScore = currentScore;
            } else if (Math.abs(currentScore - firstScore) > 0.0000001) {
                isConsistent = false;
            }
        }
        return isConsistent;
    }

    private static void loadAndWarmUpData() throws Exception {
        LOG.info("Loading Metadata from Disk (Base Config: {})...", Configs.TIME_RUN);
        CACHED_time2FundingFeeTrade = (ConcurrentHashMap<Long, Set<String>>) StorageSnappy.readObjectFromFile(FundingFeeManager.FILE_FUNDING_FEE);
        time2MarketRateChange = (TreeMap<Long, MarketRateChange>) StorageSnappy.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);
        time2MarketData = (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
        time2BtcReverse = (TreeMap<Long, Double>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_BTC_REVERSE);
        predictionMap = (TreeMap<Long, AiPredictionData>) StorageSnappy.readObjectFromFile(Configs.FILE_AI_PREDICTIONS);
        FundingFeeManager.getInstance();

        LOG.info("🔥 PRE-WARMING CACHE (Accessing Data)...");
        long startTimeLoad = Utils.sdfFile.parse(Configs.TIME_RUN).getTime();
        long endTimeLoad = System.currentTimeMillis();
        long current = startTimeLoad;
        int count = 0;
        Runtime runtime = Runtime.getRuntime();

        while (current < endTimeLoad) {
            HPOSmartCache.getData(current);
            current += Utils.TIME_DAY;
            count++;
            if (count % 30 == 0) {
                long usedMem = (runtime.totalMemory() - runtime.freeMemory()) / (1024 * 1024);
                LOG.info("... Loaded {} days. Date: {}. RAM Used: {} MB", count, Utils.normalizeDateYYYYMMDDHHmm(current), usedMem);
            }
        }
        LOG.info("\n✅ CACHE READY (" + count + " days covered).");
    }
}