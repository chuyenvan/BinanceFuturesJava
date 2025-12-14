package com.binance.chuyennd.ai_ml.hpo;

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

public class RunOptimizationAI {

    private static final Logger LOG = LoggerFactory.getLogger(RunOptimizationAI.class);

    // --- GLOBAL DATA STORE ---
    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, MarketRateChange> time2MarketRateChange;
    public static TreeMap<Long, Double> time2BtcReverse;
    public static TreeMap<Long, AiPredictionData> predictionMap; // Data V3
    public static ConcurrentHashMap<Long, Set<String>> CACHED_time2FundingFeeTrade;

    // --- CẤU HÌNH PARAM GEN (GIỮ NGUYÊN RANGE ĐỂ CÔNG BẰNG) ---
    private static final double MIN_RISK = -0.15, MAX_RISK = -0.01;
    private static final double MIN_RET1H = 0.005, MAX_RET1H = 0.03;
    private static final double MIN_HIGHRET = 0.02, MAX_HIGHRET = 0.08;
    private static final double MIN_MOM15M = 0.001, MAX_MOM15M = 0.015;
    private static final double MIN_TREND4H = 0.001, MAX_TREND4H = 0.02;

    public static void main(String[] args) {
        LOG.info("==============================================");
        LOG.info("===   AI HPO CHECKER (V3) - ULTRA FAST     ===");
        LOG.info("===   TARGET: ~100-150 ITERATIONS ONLY     ===");
        LOG.info("==============================================\n");

        try {
            // Đảm bảo Time Range phủ đủ 3 năm để so sánh công bằng với V2
            Configs.TIME_RUN = "20230101";
            loadAndWarmUpData();
        } catch (Exception e) {
            e.printStackTrace();
            return;
        }

        LOG.info("\n🚀 --- STARTING QUICK VALIDATION ---");

        // 1. TẠO THREAD POOL (BẮT BUỘC ĐỂ CHẠY NHANH)


        Factory<Genotype<DoubleGene>> gtf = Genotype.of(
                DoubleChromosome.of(MIN_RISK, MAX_RISK),
                DoubleChromosome.of(MIN_RET1H, MAX_RET1H),
                DoubleChromosome.of(MIN_HIGHRET, MAX_HIGHRET),
                DoubleChromosome.of(MIN_MOM15M, MAX_MOM15M),
                DoubleChromosome.of(MIN_TREND4H, MAX_TREND4H)
        );

        Engine<DoubleGene, Double> engine = Engine.builder(RunOptimizationAI::eval, gtf)
                // --- CẤU HÌNH TỐI ƯU SỐ LẦN CHẠY ---
                .populationSize(15) // Giảm xuống 15 (Đủ để test diversity)
                .survivorsSelector(new TournamentSelector<>(3)) // Giảm sample xuống 3 cho nhẹ
                .offspringSelector(new RouletteWheelSelector<>())
                .alterers(new Mutator<>(0.2), new MeanAlterer<>(0.6)) // Tăng mutation 0.2 để nhảy cóc nhanh hơn
                .executor(Runnable::run) // CHẠY SONG SONG
                .build();

        EvolutionResult<DoubleGene, Double> bestResult = engine.stream()
                // --- ĐIỀU KIỆN DỪNG SỚM ---
                .limit(Limits.bySteadyFitness(3)) // Dừng nếu 3 vòng không tìm thấy đỉnh mới
                .limit(10) // Tối đa 10 vòng (Tổng cộng tối đa 150 lượt chạy)
                .peek(RunOptimizationAI::monitor)
                .collect(EvolutionResult.toBestEvolutionResult());


        LOG.info("\n=== 🏁 QUICK CHECK FINISHED ===");
        LOG.info("🏆 V3 BEST SCORE: " + bestResult.bestFitness());
        printParams("BEST V3 PARAMS", bestResult.bestPhenotype().genotype());
    }

    private static void monitor(EvolutionResult<DoubleGene, Double> result) {
        LOG.info("Gen {}: Best Profit = {}", result.generation(), String.format("%.2f", result.bestFitness()));
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
            return -10000.0;
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
        LOG.info("Loading V3 Data...");
        CACHED_time2FundingFeeTrade = (ConcurrentHashMap<Long, Set<String>>) StorageSnappy.readObjectFromFile(FundingFeeManager.FILE_FUNDING_FEE);
        time2MarketRateChange = (TreeMap<Long, MarketRateChange>) StorageSnappy.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);
        time2MarketData = (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
        time2BtcReverse = (TreeMap<Long, Double>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_BTC_REVERSE);

        // Load V3 Predictions
        predictionMap = (TreeMap<Long, AiPredictionData>) StorageSnappy.readObjectFromFile(Configs.FILE_AI_PREDICTIONS);
        FundingFeeManager.getInstance();

        // Warmup (Chỉ cần 1 lần duyệt nhanh để đẩy vào RAM)
        LOG.info("🔥 Warming up cache...");
        long startTimeLoad = Utils.sdfFile.parse(Configs.TIME_RUN).getTime();
        long endTimeLoad = System.currentTimeMillis();
        long current = startTimeLoad;
//        while (current < endTimeLoad) {
//            HPOSmartCache.getData(current);
//            current += Utils.TIME_DAY;
//        }
        LOG.info("✅ Cache Ready.");
    }
}