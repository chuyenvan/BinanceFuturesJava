package com.binance.chuyennd.ai_ml.onnx.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingDataCollectionManager;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.*;
import java.util.concurrent.*;
import java.util.stream.Collectors;

/**
 * Tool sinh dữ liệu dự báo Funding cho TOÀN BỘ thị trường (No Filter) — BẢN WORKER PHÂN TÁN.
 *
 * CÁCH CHẠY:
 *  1. ADMIN (1 lần): AerospikeTaskCoordinator.initTasks(...) tạo queue task theo THÁNG.
 *  2. WORKER (mọi máy): chạy main này. Mỗi worker tự claim task tháng (atomic delete), gen xong claim tiếp.
 *     Tham số luồng: arg[0] hoặc env GEN_THREADS (default 4) — máy nhiều core (Oracle/VPS) nâng lên.
 *
 * TỐI ƯU (output BẤT BIẾN — verify bằng regression cùng-ngày):
 *  - HOIST khỏi vòng task (load 1 lần trong main): model ONNX 263M (~10s/lần), market data 2.8M (~15s),
 *    symbol mapper. Trước đây load lại MỖI task → lãng phí N-1 lần.
 *  - market data: TreeMap → HashMap (chỉ dùng .get(time) → O(1)).
 *  - hoist time2MarketData.get(time) ra NGOÀI parallelStream (trước gọi ~500 lần/phút cho cùng key).
 *  - RESET HistoryManager + CoinRankManager TRƯỚC warmup MỖI task: state tịnh tiến nằm ở 2 singleton này
 *    (extractor chỉ là vỏ); queue shuffle (làm task sau rồi claim task trước) khiến CoinRankManager.
 *    lastIntervalKey quá cao → updateRanking KHÔNG chạy → ranking task cũ làm bẩn task mới. Reset =
 *    mỗi task chạy như tiến trình riêng (đúng cách set v5 từng gen theo tháng). Trên JVM mới, reset là
 *    no-op nên regression cùng-ngày vẫn bit-identical với bản cũ.
 *  - profiling thô mỗi ngày: read / extract / inference / write (ms) để tối ưu tiếp dựa trên SỐ ĐO.
 *
 * GIỮ NGUYÊN: warmup 24h trước chunk; chỉ lưu pred[0] (len=1); guard model ≥100MB; log TASK LỖI để re-queue;
 *             updateMarketHistory mỗi phút kể cả warmup; 21 feature; format lưu; logic claim/retry.
 */
public class GenerateFundingPredictionsTool {
    private static final Logger LOG = LoggerFactory.getLogger(GenerateFundingPredictionsTool.class);

    private static final String MODEL_PATH = "models_funding/Funding_Classifier_Final.onnx";
    private static final long MIN_MODEL_SIZE_MB = 100;

    private static final int PREDICT_CHUNK_SIZE = 256;
    private static final int CLAIM_RETRY = 3;
    private static final long CLAIM_RETRY_SLEEP_MS = 5000;
    private static final int DEFAULT_THREADS = 4;
    private static final int WRITE_THREADS = 4;     // ghi 226 song song (giấu latency WAN sau infer)
    private static final int WRITE_QUEUE = 240;     // backpressure: tối đa ~240 phút chờ ghi (chặn phình RAM)

    private static class PrepareData {
        short id;
        float[] features;

        public PrepareData(short id, float[] features) {
            this.id = id;
            this.features = features;
        }
    }

    public static void main(String[] args) throws Exception {
        // Worker phân tán đọc DỮ LIỆU-NGUỒN (ticker/symbol_mapper/funding_data) từ 226 vì 242 khóa
        // firewall (Kaggle/máy cá nhân không với được 242). Bật cờ để DataManager.getReadClient() -> 226.
        // Hiếm khi chạy trên máy CÓ 242: đặt env GEN_USE_242=1 để đọc thẳng 242.
        if (!"1".equals(System.getenv("GEN_USE_242"))) {
            Configs.IS_KAGGLE_MODE = true;
            LOG.info("🌐 Đọc dữ liệu-nguồn từ 226 (IS_KAGGLE_MODE=true). Đặt GEN_USE_242=1 nếu muốn đọc 242.");
        }

        int threads = resolveThreads(args);
        // Cấu hình luồng (ForkJoin cho parallelStream + Aerospike IO + ONNX intraOp). Thread count KHÔNG
        // ảnh hưởng output (batchInput giữ encounter-order, kết quả map theo id) — chỉ ảnh hưởng tốc độ.
        System.setProperty("java.util.concurrent.ForkJoinPool.common.parallelism", String.valueOf(threads));
        DataManagerAerospikeFloatSim.setThreadCount(threads);
        LOG.info("⚙️ threads={} (ForkJoin + Aerospike + ONNX intraOp). Đổi qua arg[0] hoặc env GEN_THREADS.", threads);

        verifyModelOrDie();

        // === HOIST: load 1 lần cho TẤT CẢ task ===
        LOG.info("📥 Load 1 lần (hoist khỏi vòng task): market data + symbol mapper...");
        TreeMap<Long, MarketDataObject> mdTree = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        Map<Long, MarketDataObject> time2MarketData = new HashMap<>(mdTree);  // chỉ .get(time) → HashMap O(1)
        ConcurrentHashMap<String, Short> symbolMap =
                new ConcurrentHashMap<>(DataManagerAerospikeFloatSim.loadSymbolMapper());
        LOG.info("✅ market={} record | mapper={} symbol", time2MarketData.size(), symbolMap.size());

        GenerateFundingPredictionsTool tool = new GenerateFundingPredictionsTool();
        int done = 0;

        // Model load 1 lần, đóng (session+env) lúc kết thúc worker.
        try (FundingOnnxInferenceManager aiBrain = new FundingOnnxInferenceManager(MODEL_PATH, threads)) {
            while (true) {
                AerospikeTaskCoordinator.TaskRange task = claimWithRetry();
                if (task == null) {
                    LOG.info("🏁 Hết task trong queue. Worker đã hoàn thành {} task. Thoát.", done);
                    break;
                }
                LOG.info("▶️ BẮT ĐẦU TASK: {} -> {}",
                        Utils.normalizeDateYYYYMMDD(task.start), Utils.normalizeDateYYYYMMDD(task.end));
                try {
                    tool.startGeneration(task.start, task.end, aiBrain, time2MarketData, symbolMap);
                    done++;
                    LOG.info("✅ XONG TASK {} (tổng đã xong: {})", Utils.normalizeDateYYYYMMDD(task.start), done);
                } catch (Exception e) {
                    LOG.error("❌ TASK LỖI {} — cần re-queue thủ công bằng reInitSpecificTasks!",
                            Utils.normalizeDateYYYYMMDD(task.start), e);
                }
            }
        }
        System.exit(0);
    }

    /** Luồng: arg[0] > env GEN_THREADS > default 4. */
    private static int resolveThreads(String[] args) {
        if (args != null && args.length > 0) {
            try { return Math.max(1, Integer.parseInt(args[0].trim())); } catch (Exception ignored) { }
        }
        String env = System.getenv("GEN_THREADS");
        if (env != null) {
            try { return Math.max(1, Integer.parseInt(env.trim())); } catch (Exception ignored) { }
        }
        return DEFAULT_THREADS;
    }

    private static AerospikeTaskCoordinator.TaskRange claimWithRetry() throws InterruptedException {
        for (int i = 0; i <= CLAIM_RETRY; i++) {
            AerospikeTaskCoordinator.TaskRange task = AerospikeTaskCoordinator.claimNextTask();
            if (task != null) return task;
            if (i < CLAIM_RETRY) Thread.sleep(CLAIM_RETRY_SLEEP_MS);
        }
        return null;
    }

    /** Chặn thảm họa gen 5 năm bằng nhầm model (hai thế hệ trùng tên file). */
    private static void verifyModelOrDie() {
        File f = new File(MODEL_PATH);
        if (!f.exists()) {
            LOG.error("⛔ Không thấy model: {}", f.getAbsolutePath());
            System.exit(1);
        }
        long sizeMb = f.length() / (1024 * 1024);
        LOG.info("🔎 Model: {} | size = {} MB", f.getAbsolutePath(), sizeMb);
        if (sizeMb < MIN_MODEL_SIZE_MB) {
            LOG.error("⛔ Model chỉ {} MB < {} MB — khả năng cao là model 2026 (50M, ĐÃ THUA head-to-head),"
                    + " không phải model LIVE 12/2025 (263M). DỪNG. Nếu cố ý deploy model mới,"
                    + " sửa MIN_MODEL_SIZE_MB một cách CÓ CHỦ ĐÍCH.", sizeMb, MIN_MODEL_SIZE_MB);
            System.exit(1);
        }
    }

    /**
     * Sinh dự báo cho 1 task tháng. Model/market/mapper được truyền vào (hoist, dùng chung mọi task).
     */
    public void startGeneration(long startTs, long endTs, FundingOnnxInferenceManager aiBrain,
                                Map<Long, MarketDataObject> time2MarketData,
                                ConcurrentHashMap<String, Short> symbolMap) throws Exception {
        // 🔴 RESET state tịnh tiến TRƯỚC warmup mỗi task. State nằm ở 2 SINGLETON (không ở extractor):
        //    - HistoryManager: ring buffer 2048 nến (không tự giới hạn 24h).
        //    - CoinRankManager: lastIntervalKey + ranking cache (persist xuyên task).
        //    Không reset + queue shuffle = ranking/history task cũ làm bẩn task mới (sai basket → sai feature).
        //    Reset = mỗi task như tiến trình riêng (canonical set v5). JVM mới: reset là no-op → bit-identical.
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();

        FundingDataCollectionManager.FundingFeatureExtractorV2 extractor =
                new FundingDataCollectionManager.FundingFeatureExtractorV2();

        // 🔄 Pool GHI BẤT ĐỒNG BỘ: put 226 (WAN ~21% thời gian, core ngồi chờ mạng) đẩy ra nhiều thread
        //    ghi song song để GIẤU sau infer. Bit-identical: cùng giá trị, key theo phút nên thứ tự ghi vô hại.
        //    Queue bounded + CallerRuns => backpressure (writer chậm thì main tự ghi, không phình RAM, không mất).
        ThreadPoolExecutor writerPool = new ThreadPoolExecutor(
                WRITE_THREADS, WRITE_THREADS, 0L, TimeUnit.MILLISECONDS,
                new ArrayBlockingQueue<>(WRITE_QUEUE), new ThreadPoolExecutor.CallerRunsPolicy());

        try {
            // --- BƯỚC 1: WARMUP 24H (giữ nguyên cách gen set v5; không ghi) ---
            long warmupStart = startTs - (24 * 60 * 60 * 1000L);
            LOG.info("🔥 WARMUP 24H: {} -> {}",
                    Utils.normalizeDateYYYYMMDDHHmm(warmupStart), Utils.normalizeDateYYYYMMDDHHmm(startTs));
            runDataLoop(warmupStart, startTs, time2MarketData, null, symbolMap, true, extractor, null);

            // --- BƯỚC 2: GENERATE ---
            LOG.info("🚀 GENERATE ALL SYMBOLS: {} -> {}",
                    Utils.normalizeDateYYYYMMDDHHmm(startTs), Utils.normalizeDateYYYYMMDDHHmm(endTs));
            runDataLoop(startTs, endTs, time2MarketData, aiBrain, symbolMap, false, extractor, writerPool);
        } finally {
            // FLUSH hết writes TRƯỚC khi coi task xong (đảm bảo dữ liệu đã ghi, không hụt khi re-queue).
            writerPool.shutdown();
            if (!writerPool.awaitTermination(15, TimeUnit.MINUTES))
                LOG.error("⚠️ Writer pool CHƯA flush hết sau 15' — dữ liệu có thể THIẾU, kiểm tra trước khi tin task này.");
        }

        LOG.info("✅ HOÀN TẤT CHUNK {} -> {}.",
                Utils.normalizeDateYYYYMMDD(startTs), Utils.normalizeDateYYYYMMDD(endTs));
    }

    private void runDataLoop(long start, long end,
                             Map<Long, MarketDataObject> time2MarketData,
                             FundingOnnxInferenceManager aiBrain,
                             ConcurrentHashMap<String, Short> symbolMap,
                             boolean isWarmup,
                             FundingDataCollectionManager.FundingFeatureExtractorV2 extractor,
                             ExecutorService writerPool
    ) {
        long currentTime = start;

        while (currentTime < end) {
            int minutesToRead = 1440;
            if (currentTime + minutesToRead * Utils.TIME_MINUTE > end) {
                minutesToRead = (int) ((end - currentTime) / Utils.TIME_MINUTE) + 1;
            }

            long ioReadNs = System.nanoTime();
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers =
                    DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(currentTime, minutesToRead);
            ioReadNs = System.nanoTime() - ioReadNs;

            if (time2Tickers.isEmpty()) {
                currentTime += minutesToRead * Utils.TIME_MINUTE;
                continue;
            }

            long extractNs = 0, inferNs = 0, ioWriteNs = 0;

            for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : time2Tickers.entrySet()) {
                final long time = timeEntry.getKey();
                final Map<String, KlineObjectSimple> symbol2Ticker = timeEntry.getValue();

                // 1. CẬP NHẬT LỊCH SỬ (mỗi phút, kể cả warmup — bắt buộc cho tính tịnh tiến)
                extractor.updateMarketHistory(symbol2Ticker);

                if (isWarmup) continue;

                // HOIST: market data của phút này lấy MỘT lần (trước gọi trong lambda ~500 lần/phút cùng key)
                final MarketDataObject marketDataAtTime = time2MarketData.get(time);
                final List<String> basket = CoinRankManager.getInstance().getTopCoin(time);

                // 2. TRÍCH XUẤT ĐẶC TRƯNG — TOÀN BỘ COIN (NO FILTER)
                long e0 = System.nanoTime();
                List<PrepareData> batchInput = symbol2Ticker.keySet().parallelStream()
                        .map(symbol -> {
                            try {
                                Short symId = symbolMap.get(symbol);
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                if (symId == null || ticker == null || !Utils.isTickerAvailable(ticker)) return null;

                                OrderTargetInfoTest dummyOrder = new OrderTargetInfoTest(
                                        OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0f,
                                        Configs.LEVERAGE_ORDER, symbol, time, time, OrderSide.BUY
                                );
                                dummyOrder.lastEntry = ticker.priceClose;

                                FundingMarketFeatures features = extractor.extractFeatures(
                                        time, dummyOrder, symbol2Ticker, marketDataAtTime, basket
                                );
                                if (features != null) {
                                    return new PrepareData(symId, aiBrain.extractFeaturesToArray(features));
                                }
                            } catch (Exception e) {
                                LOG.error("Lỗi extract symbol " + symbol + " tại " + time, e);
                            }
                            return null;
                        })
                        .filter(Objects::nonNull)
                        .collect(Collectors.toList());
                extractNs += System.nanoTime() - e0;

                if (batchInput.isEmpty()) continue;

                // 3. PREDICTION THEO BATCH LỚN (256/lần)
                long i0 = System.nanoTime();
                Map<Short, float[]> finalResults = new ConcurrentHashMap<>();
                for (int i = 0; i < batchInput.size(); i += PREDICT_CHUNK_SIZE) {
                    List<PrepareData> chunk = batchInput.subList(i, Math.min(batchInput.size(), i + PREDICT_CHUNK_SIZE));
                    List<float[]> featureList = chunk.stream().map(p -> p.features).collect(Collectors.toList());

                    try {
                        List<float[]> chunkResults = aiBrain.predictBatch(featureList);
                        for (int j = 0; j < chunkResults.size(); j++) {
                            float[] full = chunkResults.get(j);
                            if (full == null || full.length == 0) continue;
                            // ⚠️ CHỈ LƯU pred[0] = P(fail): khớp format set v5 (len=1).
                            finalResults.put(chunk.get(j).id, new float[]{full[0]});
                        }
                    } catch (Exception e) {
                        LOG.error("Lỗi AI Inference tại " + time, e);
                    }
                }
                inferNs += System.nanoTime() - i0;

                // 4. LƯU KẾT QUẢ
                if (!finalResults.isEmpty()) {
                    long w0 = System.nanoTime();
                    final long ft = time;
                    final Map<Short, float[]> fr = finalResults;
                    // ASYNC: ghi nền song song (giấu latency 226). CallerRuns => nếu writer nghẽn thì main tự ghi.
                    writerPool.execute(() -> DataManagerAerospikeFloatSim.saveFundingPredictions1M(ft, fr));
                    ioWriteNs += System.nanoTime() - w0;   // chỉ còn thời gian SUBMIT (~0); ghi thật chạy nền
                }
            }

            if (!isWarmup) {
                // Profiling thô (SỐ ĐO để tối ưu tiếp — read/extract/infer/write). Không đổi output.
                LOG.info("✅ Đã xử lý xong: {} | Last: {} | ⏱ read={}ms extract={}ms infer={}ms write={}ms",
                        Utils.normalizeDateYYYYMMDD(currentTime),
                        Utils.normalizeDateYYYYMMDDHHmm(time2Tickers.lastKey()),
                        ioReadNs / 1_000_000, extractNs / 1_000_000, inferNs / 1_000_000, ioWriteNs / 1_000_000);
            }

            currentTime = time2Tickers.lastKey() + Utils.TIME_MINUTE;
            time2Tickers = null;
        }
    }
}
