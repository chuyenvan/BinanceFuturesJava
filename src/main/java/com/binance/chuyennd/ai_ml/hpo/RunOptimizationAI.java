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
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class RunOptimizationAI {

    private static final Logger LOG = LoggerFactory.getLogger(RunOptimizationAI.class);

    // --- GLOBAL DATA STORE ---
    public static ConcurrentHashMap<String, Map<Long, Boolean>> symbol2TrendData;
    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, MarketRateChange> time2MarketRateChange;
    public static TreeMap<Long, Double> time2BtcReverse;
    public static TreeMap<Long, AiPredictionData> predictionMap;
    public static ConcurrentHashMap<Long, Set<String>> CACHED_time2FundingFeeTrade;

    // --- CẤU HÌNH GIỚI HẠN (RANGE) MỚI ---
    // Đã ép Max xuống thấp để AI buộc phải trade nhiều hơn, không chờ kèo lịch sử
    private static final double MIN_RISK = -0.15, MAX_RISK = -0.01;

    // Giảm kỳ vọng lãi 1H xuống 3% (thay vì 5%)
    private static final double MIN_RET1H = 0.005, MAX_RET1H = 0.03;

    // Giảm ngưỡng "Kèo thơm" xuống 6% (thay vì 15%) để bắt các kèo trung bình
    private static final double MIN_HIGHRET = 0.02, MAX_HIGHRET = 0.06;

    // Giảm đà tăng 15M xuống 1%
    private static final double MIN_MOM15M = 0.001, MAX_MOM15M = 0.01;

    // QUAN TRỌNG: Ép Trend 4H xuống tối đa 1.2% (thay vì 5%)
    // AI sẽ phải học cách vào lệnh ở sóng nhỏ, thay vì chờ sóng thần 4.2%
    private static final double MIN_TREND4H = 0.001, MAX_TREND4H = 0.012;

    private static final double MIN_DEADTREND = -0.20, MAX_DEADTREND = -0.01;

    public static void main(String[] args) {
        LOG.info("==============================================");
        LOG.info("===   AI HYPERPARAMETER OPTIMIZATION SYSTEM   ===");
        LOG.info("===   MODE: FAST RUN (50% LOAD) & ANTI-OVERFIT ===");
        LOG.info("==============================================\n");

        // 1. LOAD DATA VÀO RAM
        // Load từ 2024 (hoặc 2023 nếu RAM > 20GB)
        try {
            Configs.TIME_RUN = "20240101";
            loadAndWarmUpData();
        } catch (Exception e) {
            e.printStackTrace();
            LOG.error("❌ CRITICAL ERROR: Failed to load data.");
            return;
        }

        // 2. CHẠY KIỂM TRA TÍNH NHẤT QUÁN
        LOG.info("\n🛑 --- STARTING CONSISTENCY CHECK (3 RUNS) ---");
        Configs.TIME_RUN = "20250101";
        boolean isStable = runConsistencyCheck();

        if (!isStable) {
            LOG.error("❌ DATA IS UNSTABLE: Scores differ! Check Variables.");
        } else {
            LOG.info("✅ SYSTEM STABLE. Proceeding...");
        }

        // =====================================================================
        // PHASE 1: QUÉT THÔ (COARSE SEARCH) - DATA 2025
        // =====================================================================
        LOG.info("\n🚀 --- PHASE 1: COARSE SEARCH (Data from 20250101) ---");
        Configs.TIME_RUN = "20250101";

        Factory<Genotype<DoubleGene>> gtfPhase1 = Genotype.of(
                DoubleChromosome.of(MIN_RISK, MAX_RISK),
                DoubleChromosome.of(MIN_RET1H, MAX_RET1H),
                DoubleChromosome.of(MIN_HIGHRET, MAX_HIGHRET),
                DoubleChromosome.of(MIN_MOM15M, MAX_MOM15M),
                DoubleChromosome.of(MIN_TREND4H, MAX_TREND4H),
                DoubleChromosome.of(MIN_DEADTREND, MAX_DEADTREND)
        );

        Engine<DoubleGene, Double> engine1 = Engine.builder(RunOptimizationAI::eval, gtfPhase1)
                .populationSize(10) // GIẢM TỪ 16 -> 10 (Chạy nhanh)
                .survivorsSelector(new TournamentSelector<>(3))
                .offspringSelector(new RouletteWheelSelector<>())
                .alterers(new Mutator<>(0.2), new MeanAlterer<>(0.2))
                .executor(Runnable::run)
                .build();

        // GIẢM SỐ VÒNG TỪ 10 -> 5
        EvolutionResult<DoubleGene, Double> bestResultPhase1 = runEvolutionLoop(engine1, 5, "PHASE 1");

        LOG.info("🏆 BEST PHASE 1 SCORE: " + bestResultPhase1.bestFitness());
        printParams("PHASE 1 RESULT", bestResultPhase1.bestPhenotype().genotype());

        // =====================================================================
        // PHASE 2: TINH CHỈNH (FINE TUNING) - DATA 2024 (FULL)
        // =====================================================================
        LOG.info("\n🚀 --- PHASE 2: FINE TUNING (Data from 20240101) ---");
        Configs.TIME_RUN = "20240101";

        Genotype<DoubleGene> bestGt1 = bestResultPhase1.bestPhenotype().genotype();

        // Tạo không gian tìm kiếm hẹp (±20%) quanh kết quả Phase 1
        Factory<Genotype<DoubleGene>> gtfPhase2 = Genotype.of(
                createNarrowChromo(bestGt1.get(0), MIN_RISK, MAX_RISK, 0.2),
                createNarrowChromo(bestGt1.get(1), MIN_RET1H, MAX_RET1H, 0.2),
                createNarrowChromo(bestGt1.get(2), MIN_HIGHRET, MAX_HIGHRET, 0.2),
                createNarrowChromo(bestGt1.get(3), MIN_MOM15M, MAX_MOM15M, 0.2),
                createNarrowChromo(bestGt1.get(4), MIN_TREND4H, MAX_TREND4H, 0.2),
                createNarrowChromo(bestGt1.get(5), MIN_DEADTREND, MAX_DEADTREND, 0.2)
        );

        Engine<DoubleGene, Double> engine2 = Engine.builder(RunOptimizationAI::eval, gtfPhase2)
                .populationSize(10) // GIẢM TỪ 16 -> 10
                .survivorsSelector(new TournamentSelector<>(3))
                .offspringSelector(new RouletteWheelSelector<>())
                .alterers(new Mutator<>(0.05), new MeanAlterer<>(0.5))
                .executor(Runnable::run)
                .build();

        // GIẢM SỐ VÒNG TỪ 50 -> 25
        EvolutionResult<DoubleGene, Double> bestResultPhase2 = runEvolutionLoop(engine2, 25, "PHASE 2");

        // 6. KẾT QUẢ CUỐI CÙNG
        LOG.info("\n=== OPTIMIZATION FINISHED ===");
        LOG.info("🏆 FINAL BEST PROFIT: " + bestResultPhase2.bestFitness());
        printParams("FINAL RESULT", bestResultPhase2.bestPhenotype().genotype());
    }

    /**
     * HÀM CHẠY VÒNG LẶP TIẾN HÓA (MEMORY SAFE)
     */
    private static EvolutionResult<DoubleGene, Double> runEvolutionLoop(
            Engine<DoubleGene, Double> engine, int maxGenerations, String phaseName) {

        LOG.info(">>> STARTING {} (Max Gen: {})", phaseName, maxGenerations);

        Iterator<EvolutionResult<DoubleGene, Double>> stream = engine.stream().iterator();
        EvolutionResult<DoubleGene, Double> bestResult = null;
        int currentGen = 1;

        while (stream.hasNext() && currentGen <= maxGenerations) {
            EvolutionResult<DoubleGene, Double> result = stream.next();

            if (bestResult == null || result.bestFitness() > bestResult.bestFitness()) {
                bestResult = result;
                LOG.info("[{}] NEW BEST at Gen {}: {}", phaseName, currentGen, String.format("%.4f", bestResult.bestFitness()));
            } else {
                // In log mỗi 2 vòng cho đỡ sốt ruột (vì số vòng ít)
                if (currentGen % 2 == 0) {
                    LOG.info("[{}] Gen {} | Current Best: {}", phaseName, currentGen, String.format("%.4f", bestResult.bestFitness()));
                }
            }

            // Dọn dẹp bộ nhớ mỗi 5 vòng
            if (currentGen % 5 == 0) {
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

    private static DoubleChromosome createNarrowChromo(Chromosome<DoubleGene> geneBase, double globalMin, double globalMax, double spreadRatio) {
        double centerValue = geneBase.gene().doubleValue();
        double rangeSpan = (globalMax - globalMin) * spreadRatio;

        double newMin = Math.max(globalMin, centerValue - rangeSpan / 2);
        double newMax = Math.min(globalMax, centerValue + rangeSpan / 2);

        if (newMin >= newMax) newMax = newMin + 0.0001;
        return DoubleChromosome.of(newMin, newMax);
    }

    private static Double eval(Genotype<DoubleGene> gt) {
        try {
            return new BackTestEngineAI(
                    gt.get(0).gene().doubleValue(),
                    gt.get(1).gene().doubleValue(),
                    gt.get(2).gene().doubleValue(),
                    gt.get(3).gene().doubleValue(),
                    gt.get(4).gene().doubleValue(),
                    gt.get(5).gene().doubleValue()
            ).run(time2MarketData, time2MarketRateChange, time2BtcReverse, symbol2TrendData, predictionMap);
        } catch (Exception e) {
            e.printStackTrace();
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
        LOG.info("   DeadTrend24H : {}", String.format("%.5f", bestGt.get(5).gene().doubleValue()));
    }

    private static boolean runConsistencyCheck() {
        double pRisk = -0.05;
        double pMinRet1H = 0.02;
        double pHighRet = 0.08;
        double pMinMom15M = 0.01;
        double pMinTrend4H = 0.03;
        double pDeadTrend24H = -0.10;

        LOG.info("   [Test Params]: Risk={}, Ret1H={} ...", pRisk, pMinRet1H);
        Double firstScore = null;
        boolean isConsistent = true;

        for (int i = 1; i <= 3; i++) {
            long tStart = System.currentTimeMillis();
            BackTestEngineAI testEngine = new BackTestEngineAI(
                    pRisk, pMinRet1H, pHighRet, pMinMom15M, pMinTrend4H, pDeadTrend24H
            );
            Double currentScore = testEngine.run(
                    time2MarketData, time2MarketRateChange, time2BtcReverse,
                    symbol2TrendData, predictionMap
            );
            long tEnd = System.currentTimeMillis();
            LOG.info("   Run #{} | Score: {} | Time: {} ms", i, String.format("%.8f", currentScore), (tEnd - tStart));

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
        LOG.info("Before load data cache:");
        printRamUsage();
        CACHED_time2FundingFeeTrade = (ConcurrentHashMap<Long, Set<String>>) StorageSnappy.readObjectFromFile(FundingFeeManager.FILE_FUNDING_FEE);
        time2MarketRateChange = (TreeMap<Long, MarketRateChange>) StorageSnappy.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);
        time2MarketData = (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
        time2BtcReverse = (TreeMap<Long, Double>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_BTC_REVERSE);
        symbol2TrendData = (ConcurrentHashMap<String, Map<Long, Boolean>>) StorageSnappy.readObjectFromFile(Configs.FILE_TREND_BY_TIME);
        predictionMap = (TreeMap<Long, AiPredictionData>) StorageSnappy.readObjectFromFile(Configs.FILE_AI_PREDICTIONS);
        FundingFeeManager.getInstance();

        LOG.info("After load data cache:");
        printRamUsage();
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