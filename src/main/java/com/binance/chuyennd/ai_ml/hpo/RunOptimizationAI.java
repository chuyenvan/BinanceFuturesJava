package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.aerospike.DataManagerAerospike;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import io.jenetics.DoubleChromosome;
import io.jenetics.DoubleGene;
import io.jenetics.Genotype;
import io.jenetics.engine.Engine;
import io.jenetics.engine.EvolutionResult;
import io.jenetics.util.DoubleRange;

import java.time.Duration;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class RunOptimizationAI {

    // === CẤU HÌNH ===
    private static final int POPULATION_SIZE = 5;  // Số lượng cá thể
    private static final int GENERATIONS = 10;      // Số thế hệ
    private static final long TOTAL_TRIALS = POPULATION_SIZE * GENERATIONS;
    // ===============

    private static final AtomicLong testCounter = new AtomicLong(0);

    // CACHE DỮ LIỆU TOÀN CỤC
    public static ConcurrentHashMap<String, Map<Long, Boolean>> symbol2TrendData;
    public static TreeMap<Long, MarketDataObject> time2MarketData;
    public static TreeMap<Long, MarketRateChange> time2MarketRateChange;
    public static TreeMap<Long, Double> time2BtcReverse;
    public static TreeMap<Long, AiPredictionData> predictionMap; // <--- Cache thêm dữ liệu AI
    public static ConcurrentHashMap<Long, Set<String>> CACHED_time2FundingFeeTrade;
    //    public static ConcurrentHashMap<String, TreeMap<Long, Double>> GLOBAL_CACHE_RATE_90M = null;
// 🔥 CACHE MỚI: CHỨA RAW BYTES CỦA TOÀN BỘ THỜI GIAN CHẠY
    public static TreeMap<Long, byte[]> GLOBAL_RAW_BYTES_CACHE = new TreeMap<>();

    /**
     * HÀM ĐÁNH GIÁ (FITNESS FUNCTION)
     */
    private static double evaluate(Genotype<DoubleGene> genotype) {
        long currentTestNumber = testCounter.incrementAndGet();

        // 1. Giải mã Gen thành tham số
        // Thứ tự gen tương ứng với khai báo ở hàm main
        double risk = genotype.get(0).gene().doubleValue(); // Risk Limit
        double minRet1H = genotype.get(1).gene().doubleValue(); // Min Return 1H
        double minMom15M = genotype.get(2).gene().doubleValue(); // Min Momentum 15M
        double minTrend4H = genotype.get(3).gene().doubleValue(); // Min Trend 4H

        // HighReturn và DeadTrend có thể để cố định hoặc thêm gen nếu muốn tối ưu luôn
        double highRet = 0.04;
        double deadTrend = -0.05;

        System.out.printf(
                "\n--- Test #%d / %d --- [Risk: %.4f | 1H: %.4f | 15M: %.4f | 4H: %.4f]%n",
                currentTestNumber, TOTAL_TRIALS, risk, minRet1H, minMom15M, minTrend4H
        );

        // 2. Chạy Engine
        try {
            BackTestEngineAI engine = new BackTestEngineAI(risk, minRet1H, highRet, minMom15M, minTrend4H, deadTrend);

            double profit = engine.run(time2MarketData, time2MarketRateChange,
                    time2BtcReverse, symbol2TrendData, predictionMap, GLOBAL_RAW_BYTES_CACHE);

            System.out.printf(">>> Result #%d: Profit = %.2f%n", currentTestNumber, profit);
            return profit;

        } catch (Exception e) {
            e.printStackTrace();
            return -9999.0;
        }
    }

    public static void main(String[] args) {
        System.out.println("=== STARTING AI PARAMETER OPTIMIZATION ===");

        // 1. LOAD DATA VÀO RAM (1 LẦN DUY NHẤT)
        try {
            System.out.println("Loading data...");
            CACHED_time2FundingFeeTrade = (ConcurrentHashMap<Long, Set<String>>) StorageSnappy.readObjectFromFile(FundingFeeManager.FILE_FUNDING_FEE);
            time2MarketRateChange = (TreeMap<Long, MarketRateChange>) StorageSnappy.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);
            time2MarketData = (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
            time2BtcReverse = (TreeMap<Long, Double>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_BTC_REVERSE);
            symbol2TrendData = (ConcurrentHashMap<String, Map<Long, Boolean>>) StorageSnappy.readObjectFromFile(Configs.FILE_TREND_BY_TIME);

            // QUAN TRỌNG: Load file AI Predictions
            predictionMap = (TreeMap<Long, AiPredictionData>) StorageSnappy.readObjectFromFile(Configs.FILE_AI_PREDICTIONS);
//            GLOBAL_CACHE_RATE_90M = (ConcurrentHashMap<String, TreeMap<Long, Double>>) StorageSnappy.readObjectFromFile("storage/rate_change_90m_full.data");

            FundingFeeManager.getInstance();

            System.out.println("Loading MASSIVE RAW DATA from Aerospike to RAM...");
            long startTimeLoad = Utils.sdfFile.parse(Configs.TIME_RUN).getTime();
            long endTimeLoad = System.currentTimeMillis();

            long current = startTimeLoad;
            int daysLoaded = 0;
            while (current < endTimeLoad) {
                // Đọc bytes của 1 ngày
                TreeMap<Long, byte[]> dayBytes = DataManagerAerospike.readDataFromAerospike1MBytes(current);
                if (dayBytes != null && !dayBytes.isEmpty()) {
                    GLOBAL_RAW_BYTES_CACHE.putAll(dayBytes);
                }

                daysLoaded++;
                if (daysLoaded % 10 == 0) System.out.println("Loaded " + daysLoaded + " days...");

                current += Utils.TIME_DAY;
            }
            System.out.println("Loaded Total Raw Bytes: " + GLOBAL_RAW_BYTES_CACHE.size() + " records (minutes).");
            System.out.println("RAM Used Estimate: " + (GLOBAL_RAW_BYTES_CACHE.size() * 20 / 1024 / 1024) + " MB (Compressed)");

            System.out.println("Data Loaded Successfully!");
        } catch (Exception e) {
            System.err.println("Load data failed!");
            e.printStackTrace();
            return;
        }

        long startTime = System.currentTimeMillis();

        // 2. KHỞI TẠO KHÔNG GIAN TÌM KIẾM (GENOTYPE)
        Genotype<DoubleGene> genotypeFactory = Genotype.of(
                // Gene 0: Risk Limit (-0.08 đến -0.02) -> Rủi ro chấp nhận
                DoubleChromosome.of(DoubleRange.of(-0.08, -0.02)),

                // Gene 1: Min Return 1H (0.005 đến 0.03) -> Lãi tối thiểu để vào lệnh
                DoubleChromosome.of(DoubleRange.of(0.005, 0.03)),

                // Gene 2: Momentum 15M (0.0 đến 0.005) -> Lực nến 15M
                DoubleChromosome.of(DoubleRange.of(0.000, 0.005)),

                // Gene 3: Trend 4H (-0.01 đến 0.02) -> Xu hướng trung hạn
                DoubleChromosome.of(DoubleRange.of(-0.01, 0.02))
        );

        // 3. CẤU HÌNH ENGINE (ĐƠN LUỒNG ĐỂ AN TOÀN VỚI STATIC)
        Engine<DoubleGene, Double> engine = Engine
                .builder(RunOptimizationAI::evaluate, genotypeFactory)
                .populationSize(POPULATION_SIZE)
                .maximizing() // Tìm lợi nhuận cao nhất
                .executor(Executors.newSingleThreadExecutor()) // QUAN TRỌNG
//                .executor(Executors.newFixedThreadPool(2))
                .build();

        // 4. CHẠY TIẾN HÓA
        EvolutionResult<DoubleGene, Double> result = engine.stream()
                .peek(er -> System.out.printf(
                        "%n>>> Gen %d/%d Complete. Best Fitness: %.2f%n%n",
                        er.generation(), GENERATIONS, er.bestFitness()))
                .limit(GENERATIONS)
                .collect(EvolutionResult.toBestEvolutionResult());

        // 5. IN KẾT QUẢ
        long totalTime = System.currentTimeMillis() - startTime;
        Genotype<DoubleGene> best = result.bestPhenotype().genotype();

        System.out.println("\n========================================");
        System.out.println("OPTIMIZATION FINISHED in " + Duration.ofMillis(totalTime).toMinutes() + " mins");
        System.out.println("MAX PROFIT: " + result.bestFitness());
        System.out.println("BEST PARAMETERS:");
        System.out.printf(" - Risk Limit:       %.5f%n", best.get(0).gene().doubleValue());
        System.out.printf(" - Min Return 1H:    %.5f%n", best.get(1).gene().doubleValue());
        System.out.printf(" - Min Momentum 15M: %.5f%n", best.get(2).gene().doubleValue());
        System.out.printf(" - Min Trend 4H:     %.5f%n", best.get(3).gene().doubleValue());
        System.out.println("========================================");
    }
}