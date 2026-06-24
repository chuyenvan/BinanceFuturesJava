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
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.*;
import java.util.stream.Collectors;

/**
 * TASK-109 bước 3 (B1b) — GENERATE selector prediction TRỌN VẸN bằng JAVA (KHÔNG dùng lại gì của Python
 * trừ model train). Sinh 4 cột P(win) (4h/12h/24h/72h) per (symbol, phút) ra set Aerospike để engine đọc sẵn.
 *
 * 45 FEATURE = 40 Tool1 (FundingFeatureExtractorV2.extractFeatures, KHỚP convertFeaturesToArray)
 *   + #33-35 cross-sectional (applyCrossSectional, rank cùng mốc t)
 *   + #41-45 OI (SelectorOiProvider, OI cách 1: nạp Aerospike → merge backward tol 2h).
 * extractFeatures để #33-35 và #41-45 = NaN; tool này ĐIỀN chúng (đúng việc PASS-2 + merge Python làm).
 *
 * TỔ CHỨC: chạy TUẦN TỰ per-tháng trong 1 process (Oracle 23GB/4core đủ). KHÁC funding (queue 5 Kaggle):
 *   selector generate 1 lần, OI provider nạp per-coin 1 lần dùng lại → 1 process đơn giản + đỡ lệch.
 *   Range qua arg: START END (yyyyMMdd). Mặc định 2021-01 → nay. Ghi set SEL_SET (env, mặc định
 *   funding_selector_pred_1m_java — TÁCH set Python 039d để validate compare).
 *
 * Reproduce Python ~0.000000: feature pipeline Java = nguồn sinh ff_*.bin; OI provider = reproduce writeCoin;
 *   ONNX inference đã validate == Python (SelectorValidateTool). Validate set Java vs set Python ở bước sau.
 */
public class GenerateSelectorPredictionsTool {
    private static final Logger LOG = LoggerFactory.getLogger(GenerateSelectorPredictionsTool.class);

    private static final String MODEL_DIR = System.getenv().getOrDefault("SEL_MODEL_DIR", "ml/funding_selector/models_v1");
    private static final String SEL_SET = System.getenv().getOrDefault("SEL_SET", "funding_selector_pred_1m_java");
    private static final String DUMP_FEATURES = System.getenv("SEL_DUMP_FEATURES");   // null = không dump (validate-only)
    private static final int PREDICT_CHUNK_SIZE = 256;
    private static final int WRITE_THREADS = 4;
    private static final int WRITE_QUEUE = 240;

    private static class PrepareData {
        final short id;
        final String symbol;
        final FundingMarketFeatures features;   // giữ object để điền cross-sectional PASS-2 + OI rồi mới ráp 45
        PrepareData(short id, String symbol, FundingMarketFeatures features) {
            this.id = id; this.symbol = symbol; this.features = features;
        }
    }

    public static void main(String[] args) throws Exception {
        // Đọc dữ liệu-nguồn từ 226 (như funding) trừ khi GEN_USE_242=1.
        if (!"1".equals(System.getenv("GEN_USE_242"))) {
            Configs.IS_KAGGLE_MODE = true;
            LOG.info("🌐 Đọc dữ liệu-nguồn từ 226 (IS_KAGGLE_MODE=true).");
        }
        int threads = Math.max(1, Integer.parseInt(System.getenv().getOrDefault("GEN_THREADS", "4")));
        System.setProperty("java.util.concurrent.ForkJoinPool.common.parallelism", String.valueOf(threads));
        DataManagerAerospikeFloatSim.setThreadCount(threads);

        long start = Utils.sdfFile.parse("20210101").getTime() + 7 * Utils.TIME_HOUR;
        long end = System.currentTimeMillis();
        if (args.length >= 1 && args[0].length() == 8) start = Utils.sdfFile.parse(args[0]).getTime() + 7 * Utils.TIME_HOUR;
        if (args.length >= 2 && args[1].length() == 8) end = Utils.sdfFile.parse(args[1]).getTime() + 7 * Utils.TIME_HOUR;

        // Verify model dir có đủ 4 ONNX
        for (String h : SelectorOnnxInferenceManager.HORIZONS) {
            File f = new File(MODEL_DIR + "/model_" + h + ".onnx");
            if (!f.exists()) { LOG.error("⛔ Thiếu model {}", f.getAbsolutePath()); System.exit(1); }
        }
        LOG.info("🔎 Model dir={} | set ghi={} | range {} -> {} | threads={}", MODEL_DIR, SEL_SET,
                Utils.normalizeDateYYYYMMDD(start), Utils.normalizeDateYYYYMMDD(end), threads);

        // HOIST: load 1 lần
        LOG.info("📥 Load market data + symbol mapper...");
        TreeMap<Long, MarketDataObject> mdTree = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        Map<Long, MarketDataObject> time2MarketData = new HashMap<>(mdTree);
        ConcurrentHashMap<String, Short> symbolMap =
                new ConcurrentHashMap<>(DataManagerAerospikeFloatSim.loadSymbolMapper());
        LOG.info("✅ market={} | mapper={}", time2MarketData.size(), symbolMap.size());

        GenerateSelectorPredictionsTool tool = new GenerateSelectorPredictionsTool();
        SelectorOiProvider oiProvider = new SelectorOiProvider();   // OI cách 1: nạp per-coin lazy, dùng lại xuyên tháng
        try (SelectorOnnxInferenceManager brain = new SelectorOnnxInferenceManager(MODEL_DIR, threads)) {
            // Chạy tuần tự per-tháng (warmup 24h mỗi tháng để history/rank tịnh tiến đúng như set v5).
            Calendar cal = Calendar.getInstance();
            cal.setTimeInMillis(start);
            while (cal.getTimeInMillis() < end) {
                long mStart = cal.getTimeInMillis();
                cal.add(Calendar.MONTH, 1);
                long mEnd = Math.min(cal.getTimeInMillis(), end);
                LOG.info("▶️ THÁNG {} -> {}", Utils.normalizeDateYYYYMMDD(mStart), Utils.normalizeDateYYYYMMDD(mEnd));
                tool.startGeneration(mStart, mEnd, brain, oiProvider, time2MarketData, symbolMap);
            }
        }
        LOG.info("🏁 HOÀN TẤT generate selector [{} -> {}]",
                Utils.normalizeDateYYYYMMDD(start), Utils.normalizeDateYYYYMMDD(end));
        System.exit(0);
    }

    public void startGeneration(long startTs, long endTs, SelectorOnnxInferenceManager brain,
                                SelectorOiProvider oiProvider,
                                Map<Long, MarketDataObject> time2MarketData,
                                ConcurrentHashMap<String, Short> symbolMap) throws Exception {
        // RESET state tịnh tiến TRƯỚC warmup mỗi tháng (giống GenerateFundingPredictionsTool).
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();

        FundingDataCollectionManager.FundingFeatureExtractorV2 extractor =
                new FundingDataCollectionManager.FundingFeatureExtractorV2();

        ThreadPoolExecutor writerPool = new ThreadPoolExecutor(
                WRITE_THREADS, WRITE_THREADS, 0L, TimeUnit.MILLISECONDS,
                new ArrayBlockingQueue<>(WRITE_QUEUE), new ThreadPoolExecutor.CallerRunsPolicy());

        try {
            long warmupStart = startTs - 24 * 60 * 60 * 1000L;
            LOG.info("🔥 WARMUP 24H: {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(warmupStart), Utils.normalizeDateYYYYMMDDHHmm(startTs));
            runDataLoop(warmupStart, startTs, time2MarketData, brain, oiProvider, symbolMap, true, extractor, null);

            LOG.info("🚀 GENERATE: {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(startTs), Utils.normalizeDateYYYYMMDDHHmm(endTs));
            runDataLoop(startTs, endTs, time2MarketData, brain, oiProvider, symbolMap, false, extractor, writerPool);
        } finally {
            writerPool.shutdown();
            if (!writerPool.awaitTermination(15, TimeUnit.MINUTES))
                LOG.error("⚠️ Writer pool CHƯA flush hết sau 15' — dữ liệu có thể THIẾU.");
        }
    }

    private void runDataLoop(long start, long end, Map<Long, MarketDataObject> time2MarketData,
                             SelectorOnnxInferenceManager brain, SelectorOiProvider oiProvider,
                             ConcurrentHashMap<String, Short> symbolMap, boolean isWarmup,
                             FundingDataCollectionManager.FundingFeatureExtractorV2 extractor,
                             ExecutorService writerPool) {
        long currentTime = start;
        while (currentTime < end) {
            int minutesToRead = 1440;
            if (currentTime + minutesToRead * Utils.TIME_MINUTE > end)
                minutesToRead = (int) ((end - currentTime) / Utils.TIME_MINUTE) + 1;

            long ioReadNs = System.nanoTime();
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers =
                    DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(currentTime, minutesToRead);
            ioReadNs = System.nanoTime() - ioReadNs;
            if (time2Tickers.isEmpty()) { currentTime += minutesToRead * Utils.TIME_MINUTE; continue; }

            long extractNs = 0, inferNs = 0;
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> te : time2Tickers.entrySet()) {
                final long time = te.getKey();
                final Map<String, KlineObjectSimple> symbol2Ticker = te.getValue();
                extractor.updateMarketHistory(symbol2Ticker);
                if (isWarmup) continue;

                final MarketDataObject marketDataAtTime = time2MarketData.get(time);
                final List<String> basket = CoinRankManager.getInstance().getTopCoin(time);

                // ⚠️ KHỚP PYTHON: ExportFeaturesForPythonTool chỉ tính feature cho coin qua EntrySignalFilter,
                //   và cross-sectional #33-35 rank TRONG tập đã-filter. Nếu Java rank trên MỌI coin → tập khác
                //   → #33-35 lệch → P(win) lệch (đã đo: diff ~0.02-0.04, tăng theo horizon). PHẢI áp cùng filter.
                final java.util.Set<String> passFilter = com.binance.chuyennd.ai_ml.features.export.funding.EntrySignalFilter
                        .selectCoins(symbol2Ticker, HistoryManager.getInstance());
                if (passFilter.isEmpty()) continue;

                // 1) EXTRACT per-coin (40 Tool1; #33-35 và #41-45 còn NaN) — parallel, CHỈ coin lọt filter.
                long e0 = System.nanoTime();
                List<PrepareData> batch = passFilter.parallelStream()
                        .map(symbol -> {
                            try {
                                Short symId = symbolMap.get(symbol);
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                if (symId == null || ticker == null || !Utils.isTickerAvailable(ticker)) return null;
                                OrderTargetInfoTest dummy = new OrderTargetInfoTest(
                                        OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0f,
                                        Configs.LEVERAGE_ORDER, symbol, time, time, OrderSide.BUY);
                                dummy.lastEntry = ticker.priceClose;
                                FundingMarketFeatures f = extractor.extractFeatures(time, dummy, symbol2Ticker, marketDataAtTime, basket);
                                return f != null ? new PrepareData(symId, symbol, f) : null;
                            } catch (Exception ex) {
                                LOG.error("extract lỗi {} @ {}", symbol, time, ex);
                                return null;
                            }
                        })
                        .filter(Objects::nonNull)
                        .collect(Collectors.toList());
                extractNs += System.nanoTime() - e0;
                if (batch.isEmpty()) continue;

                // 2) CROSS-SECTIONAL #33-35: rank cùng mốc t (KHỚP ExportFeaturesForPythonTool.applyCrossSectional).
                applyCrossSectional(batch);

                // 3) OI #41-45 (cách 1: merge backward tol 2h) + ráp 45 feature.
                List<float[]> featList = new ArrayList<>(batch.size());
                for (PrepareData pd : batch) {
                    float[] oi5 = oiProvider.lookup(pd.symbol, time);
                    featList.add(SelectorOnnxInferenceManager.extractFeatures45(pd.features, oi5));
                }

                // DEBUG (SEL_DUMP_FEATURES=path): dump 45 feature Java per (ts,symbol) ra CSV để VALIDATE so Python.
                //   1 dòng = ts,symbol,f0..f44. Python đọc .bin Tool1 + oi_percoin cùng (ts,symbol) so từng feature.
                if (DUMP_FEATURES != null) {
                    synchronized (GenerateSelectorPredictionsTool.class) {
                        try (java.io.FileWriter fw = new java.io.FileWriter(DUMP_FEATURES, true)) {
                            for (int bi = 0; bi < batch.size(); bi++) {
                                StringBuilder sb = new StringBuilder();
                                sb.append(time).append(',').append(batch.get(bi).symbol);
                                for (float v : featList.get(bi)) sb.append(',').append(v);
                                fw.write(sb.append('\n').toString());
                            }
                        } catch (Exception ex) {
                            LOG.error("dump feature lỗi: {}", ex.getMessage());
                        }
                    }
                }

                // 4) PREDICT 4 horizon theo chunk → 4 cột P(win).
                long i0 = System.nanoTime();
                Map<Short, float[]> results = new ConcurrentHashMap<>();
                for (int i = 0; i < featList.size(); i += PREDICT_CHUNK_SIZE) {
                    int to = Math.min(featList.size(), i + PREDICT_CHUNK_SIZE);
                    List<float[]> chunk = featList.subList(i, to);
                    float[][] p4 = brain.predictAll4(chunk);   // [n][4]
                    for (int j = 0; j < p4.length; j++) {
                        results.put(batch.get(i + j).id, p4[j]);   // float[4] = P(win) 4h/12h/24h/72h
                    }
                }
                inferNs += System.nanoTime() - i0;

                // 5) GHI async vào set selector riêng.
                if (!results.isEmpty()) {
                    final long ft = time;
                    final Map<Short, float[]> fr = results;
                    writerPool.execute(() -> DataManagerAerospikeFloatSim.saveSelectorPredictions1M(ft, fr, SEL_SET));
                }
            }
            if (!isWarmup) {
                LOG.info("✅ {} | last {} | read={}ms extract={}ms infer={}ms",
                        Utils.normalizeDateYYYYMMDD(currentTime), Utils.normalizeDateYYYYMMDDHHmm(time2Tickers.lastKey()),
                        ioReadNs / 1_000_000, extractNs / 1_000_000, inferNs / 1_000_000);
            }
            currentTime = time2Tickers.lastKey() + Utils.TIME_MINUTE;
        }
    }

    /** Cross-sectional #33-35: rank-percentile coinFundingRate/volumeZCoin/momentum24H giữa coin cùng mốc t.
     *  KHỚP ExportFeaturesForPythonTool.applyCrossSectional + percentileRanks (midrank, NaN giữ NaN, <2 valid → NaN). */
    private void applyCrossSectional(List<PrepareData> list) {
        int m = list.size();
        if (m == 0) return;
        float[] funding = new float[m], volz = new float[m], mom = new float[m];
        for (int i = 0; i < m; i++) {
            FundingMarketFeatures f = list.get(i).features;
            funding[i] = f.coinFundingRate;
            volz[i] = f.volumeZCoin;
            mom[i] = f.momentum24H;
        }
        float[] fr = percentileRanks(funding), vr = percentileRanks(volz), mr = percentileRanks(mom);
        for (int i = 0; i < m; i++) {
            FundingMarketFeatures f = list.get(i).features;
            f.fundingRankCS = fr[i];
            f.volumeZRankCS = vr[i];
            f.momentumRankCS = mr[i];
        }
    }

    /** Rank-percentile (midrank) ∈ [0,1] so với phần tử KHÔNG-NaN; NaN giữ NaN; <2 valid → tất cả NaN.
     *  COPY CHÍNH XÁC ExportFeaturesForPythonTool.percentileRanks (less+0.5*equal)/validCount để khớp bit. */
    private static float[] percentileRanks(float[] vals) {
        int m = vals.length;
        float[] out = new float[m];
        int validCount = 0;
        for (float v : vals) if (!Float.isNaN(v)) validCount++;
        if (validCount <= 1) { Arrays.fill(out, Float.NaN); return out; }
        float[] sorted = new float[validCount];
        int k = 0;
        for (float v : vals) if (!Float.isNaN(v)) sorted[k++] = v;
        Arrays.sort(sorted);
        for (int i = 0; i < m; i++) {
            float v = vals[i];
            if (Float.isNaN(v)) { out[i] = Float.NaN; continue; }
            int less = lowerBound(sorted, v);
            int equal = upperBound(sorted, v) - less;
            out[i] = (float) ((less + 0.5 * equal) / validCount);
        }
        return out;
    }

    /** Số phần tử < key trong mảng đã sort tăng dần. */
    private static int lowerBound(float[] a, float key) {
        int lo = 0, hi = a.length;
        while (lo < hi) {
            int mid = (lo + hi) >>> 1;
            if (a[mid] < key) lo = mid + 1; else hi = mid;
        }
        return lo;
    }

    /** Số phần tử ≤ key trong mảng đã sort tăng dần. */
    private static int upperBound(float[] a, float key) {
        int lo = 0, hi = a.length;
        while (lo < hi) {
            int mid = (lo + hi) >>> 1;
            if (a[mid] <= key) lo = mid + 1; else hi = mid;
        }
        return lo;
    }
}
