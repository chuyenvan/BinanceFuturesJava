package com.binance.chuyennd.ai_ml.onnx.funding;

import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtSession;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.fundingv2.FundingFeatureExtractorV2;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;
import java.util.zip.GZIPInputStream;
import java.util.zip.GZIPOutputStream;

public class GenerateFundingPredictionsFromFileTool {
    private static final Logger LOG = LoggerFactory.getLogger(GenerateFundingPredictionsFromFileTool.class);
    private static final int MAX_BATCH_SIZE = 150000;

    private static class PrepareData {
        long time;
        short id;
        float[] features;
        public PrepareData(long time, short id, float[] features) {
            this.time = time; this.id = id; this.features = features;
        }
    }

    public static void main(String[] args) throws Exception {
        System.setProperty("java.util.concurrent.ForkJoinPool.common.parallelism", "8");

        String inputDir = "market_data_export/";
        String outputDir = "predict_results_export/";
        new File(outputDir).mkdirs();

        new GenerateFundingPredictionsFromFileTool().startGeneration(inputDir, outputDir);
    }

    public void startGeneration(String inputDir, String outputDir) throws Exception {
        String modelPath = "models_funding/Funding_Classifier_Final_Fixed.onnx";

        LOG.info("📥 Đang tải Market Data & Symbol Mapper...");
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        Map<String, Short> globalMapper = DataManagerAerospikeFloatSim.loadSymbolMapper();

        Map<Short, String> idToSymbolMap = new HashMap<>();
        for (Map.Entry<String, Short> entry : globalMapper.entrySet()) {
            idToSymbolMap.put(entry.getValue(), entry.getKey());
        }
        final ConcurrentHashMap<String, Short> symbolMap = new ConcurrentHashMap<>(globalMapper);
        SimpleDateFormat sdf = new SimpleDateFormat("yyyyMMdd-HHmm");

        OrtEnvironment env = OrtEnvironment.getEnvironment();
        OrtSession.SessionOptions options = new OrtSession.SessionOptions();
        options.setIntraOpNumThreads(8);
        options.setInterOpNumThreads(8);

        try (FundingOnnxInferenceManager aiBrain = new FundingOnnxInferenceManager(modelPath)) {
            // SỬ DỤNG BẢN V2 SIÊU TỐC
            FundingFeatureExtractorV2 extractor = new FundingFeatureExtractorV2();

            for (int year = 2026; year <= 2026; year++) {
                for (int q = 1; q <= 4; q++) {
                    String inputFilePath = inputDir + "market_data_" + year + "_Q" + q + ".bin.gz";
                    String outputFilePath = outputDir + "predict_data_" + year + "_Q" + q + ".bin.gz";

                    File inFile = new File(inputFilePath);
                    if (!inFile.exists()) continue;

                    String startStr = "";
                    if (q == 1) startStr = year + "0101-0000";
                    else if (q == 2) startStr = year + "0401-0000";
                    else if (q == 3) startStr = year + "0701-0000";
                    else if (q == 4) startStr = year + "1001-0000";
                    long startOfQuarterTs = sdf.parse(startStr).getTime();

                    LOG.info("🚀 ĐANG NẠP NĂM {} QUÝ {} VÀO RAM...", year, q);
                    TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = loadKlinesFromBinary(inputFilePath, idToSymbolMap);
                    LOG.info("✅ Đã load xong {} phút vào RAM. Bắt đầu xử lý...", time2Tickers.size());

                    try (DataOutputStream dos = new DataOutputStream(
                            new BufferedOutputStream(new GZIPOutputStream(new FileOutputStream(outputFilePath))))) {

                        int count = 0;
                        long lastKey = time2Tickers.lastKey();
                        List<PrepareData> giantBatch = new ArrayList<>();
                        long sumTimeWarmup = 0, sumTimeExtract = 0, sumTimePredict = 0, sumTimeWrite = 0;

                        for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : time2Tickers.entrySet()) {
                            long time = timeEntry.getKey();
                            Map<String, KlineObjectSimple> symbol2Ticker = timeEntry.getValue();

                            long t0 = System.nanoTime();
                            extractor.updateMarketHistory(symbol2Ticker);
                            long t1 = System.nanoTime();
                            sumTimeWarmup += (t1 - t0);

                            if (time < startOfQuarterTs) continue;

                            final List<String> basket = CoinRankManager.getInstance().getTopCoin(time);
                            List<PrepareData> minuteData = symbol2Ticker.keySet().parallelStream()
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
                                                    time, dummyOrder, symbol2Ticker, time2MarketData.get(time), basket);

                                            if (features != null) {
                                                return new PrepareData(time, symId, aiBrain.extractFeaturesToArray(features));
                                            }
                                        } catch (Exception e) {}
                                        return null;
                                    })
                                    .filter(Objects::nonNull)
                                    .collect(Collectors.toList());

                            long t2 = System.nanoTime();
                            sumTimeExtract += (t2 - t1);

                            giantBatch.addAll(minuteData);

                            // BATCH PREDICT
                            if (giantBatch.size() >= MAX_BATCH_SIZE || time == lastKey) {
                                List<float[]> allFeaturesList = giantBatch.stream().map(p -> p.features).collect(Collectors.toList());
                                try {
                                    List<float[]> results = aiBrain.predictBatch(allFeaturesList);
                                    long t3 = System.nanoTime();
                                    sumTimePredict += (t3 - t2);

                                    TreeMap<Long, Map<Short, float[]>> groupedResults = new TreeMap<>();
                                    for (int i = 0; i < giantBatch.size(); i++) {
                                        groupedResults.computeIfAbsent(giantBatch.get(i).time, k -> new HashMap<>())
                                                .put(giantBatch.get(i).id, results.get(i));
                                    }

                                    for (Map.Entry<Long, Map<Short, float[]>> entry : groupedResults.entrySet()) {
                                        dos.writeLong(entry.getKey());
                                        dos.writeShort(entry.getValue().size());
                                        for (Map.Entry<Short, float[]> symEntry : entry.getValue().entrySet()) {
                                            dos.writeShort(symEntry.getKey());
                                            float[] preds = symEntry.getValue();
                                            dos.writeShort(preds.length);
                                            for (float f : preds) dos.writeFloat(f);
                                        }

                                        count++;
                                        if (count % 1440 == 0) {
                                            printProfilerReport(sumTimeWarmup, sumTimeExtract, sumTimePredict, sumTimeWrite);
                                            sumTimeWarmup = 0; sumTimeExtract = 0; sumTimePredict = 0; sumTimeWrite = 0;
                                        }
                                    }
                                    long t4 = System.nanoTime();
                                    sumTimeWrite += (t4 - t3);

                                } catch (Exception e) {
                                    LOG.error("Lỗi AI Inference Batch", e);
                                }
                                giantBatch.clear();
                            }
                        }
                    }

                    LOG.info("✅ HOÀN TẤT NĂM {} QUÝ {}! Đang xả RAM...", year, q);
                    time2Tickers.clear();
                    System.gc();
                }
            }
        }
        LOG.info("🎉 HOÀN TẤT TOÀN BỘ QUÁ TRÌNH SINH DỮ LIỆU ĐẾN 2026.");
        System.exit(0);
    }

    private void printProfilerReport(long w, long e, long p, long wr) {
        double totalMs = (w + e + p + wr) / 1_000_000.0;
        LOG.info("📊 --- PROFILER REPORT (1 NGÀY CHẠY) ---");
        LOG.info("   ⏳ Tổng: {} ms", String.format("%.0f", totalMs));
        LOG.info("   👉 1. Warmup: {}% ({} ms)", String.format("%.2f", (w/1_000_000.0)/totalMs*100), w/1000000);
        LOG.info("   👉 2. Extract: {}% ({} ms)", String.format("%.2f", (e/1_000_000.0)/totalMs*100), e/1000000);
        LOG.info("   👉 3. Predict: {}% ({} ms)", String.format("%.2f", (p/1_000_000.0)/totalMs*100), p/1000000);
        LOG.info("   👉 4. File I/O: {}% ({} ms)", String.format("%.2f", (wr/1_000_000.0)/totalMs*100), wr/1000000);
        LOG.info("----------------------------------------");
    }

    private TreeMap<Long, Map<String, KlineObjectSimple>> loadKlinesFromBinary(String filePath, Map<Short, String> idToSymbolMap) throws Exception {
        TreeMap<Long, Map<String, KlineObjectSimple>> result = new TreeMap<>();
        try (DataInputStream dis = new DataInputStream(new BufferedInputStream(new GZIPInputStream(new FileInputStream(filePath))))) {
            while (true) {
                try {
                    long time = dis.readLong(); short symId = dis.readShort();
                    float open = dis.readFloat(); float high = dis.readFloat();
                    float low = dis.readFloat(); float close = dis.readFloat(); float volume = dis.readFloat();
                    String sym = idToSymbolMap.get(symId);
                    if (sym == null) continue;
                    KlineObjectSimple k = new KlineObjectSimple();
                    k.startTime = time; k.priceOpen = open; k.maxPrice = high;
                    k.minPrice = low; k.priceClose = close; k.totalUsdt = volume;
                    result.computeIfAbsent(time, t -> new HashMap<>()).put(sym, k);
                } catch (EOFException e) { break; }
            }
        }
        return result;
    }
}