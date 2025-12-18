package com.binance.chuyennd.ai_ml.v3;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.entry.ComprehensiveMarketFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class RunGeneratePredictionsV3 {
    private static final Logger LOG = LoggerFactory.getLogger(RunGeneratePredictionsV3.class);

    // Thư mục chứa Model V3
    private static final String MODEL_DIR_V3 = "../storage/ai_ml_data/ai_models_reg_v3";
    // Tên file output V3 (để không đè lên file cũ)
    private static final String OUTPUT_FILE_PREFIX = Configs.FILE_AI_ENTRY_PREDICTIONS + "_v3";

    public static void main(String[] args) {
        try {
            FundingFeeManager.getInstance();
            new RunGeneratePredictionsV3().generate();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void generate() throws Exception {
        LOG.info("🔥 STARTING V3 GENERATION ENGINE...");

        // 1. Init Components V3
        OnnxInferenceManagerV3 aiBrain = new OnnxInferenceManagerV3(MODEL_DIR_V3);
        FeatureEngineerV3 featureEngineer = new FeatureEngineerV3();

        // Extractor cũ vẫn dùng tốt, chỉ cần map sang MarketFeaturesV3
        ComprehensiveMarketFeatureExtractor baseExtractor = new ComprehensiveMarketFeatureExtractor();

        TreeMap<Long, MarketRateChange> time2Rate = (TreeMap<Long, MarketRateChange>)
                StorageSnappy.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);

        // Map kết quả: Timestamp -> AiPredictionDataV3
        TreeMap<Long, AiPredictionDataV3> predictionMap = new TreeMap<>();

        long currentTime = Utils.sdfFile.parse("20210101").getTime();
        long endTime = System.currentTimeMillis();

        Calendar cal = Calendar.getInstance();
        int processed = 0;

        while (currentTime <= endTime) {
            try {
                // ... (Logic check file exist & year transition giữ nguyên như V2) ...
                // ... (Chỉ đổi tên file save thành ai_predictions_v3_202x) ...

                TreeMap<Long, Map<String, KlineObjectSimple>> todayData =
                        DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTime);
                int counterSuccess = 0;
                if (todayData != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : todayData.entrySet()) {
                        Long timestamp = entry.getKey();

                        // 1. Lấy Feature Thô (V2)
                        // Lưu ý: Extractor cần chạy liên tục để update history, không được skip
                        MarketFeatures rawV2 = baseExtractor.extractAllFeatures(
                                timestamp, entry.getValue(), time2Rate.get(timestamp), null);

                        // 2. Convert V2 -> V3 Object
                        MarketFeaturesV3 rawV3 = convertToV3(rawV2);

                        // 3. Feature Engineering (Lag, ZScore...) -> Lấy Input Vector
                        float[] onnxInput = featureEngineer.processAndGetInputArray(rawV3);

                        // 4. Nếu đủ dữ liệu (không null) -> Predict
                        if (onnxInput != null) {
                            counterSuccess++;
                            rawV3.onnxInputData = onnxInput;
                            OnnxInferenceManagerV3.PredictionResultV3 res = aiBrain.predict(rawV3);

                            predictionMap.put(timestamp, new AiPredictionDataV3(
                                    timestamp, res.return15M, res.return1H, res.return4H, res.maxDrawdown4H
                            ));
                        }
                    }
                }

                processed++;
                LOG.info("Day {} processed {}/{}. V3 Map: {}", Utils.normalizeDateYYYYMMDD(currentTime),
                        counterSuccess, todayData.size(), predictionMap.size());
                if (counterSuccess != todayData.size())
                    LOG.info("⚠️ Some timestamps missing in V3 generation!-----------------");

            } catch (Exception e) {
                LOG.error("Error day " + currentTime, e);
            }
            currentTime += Utils.TIME_DAY;
        }

        // Save phần còn lại...
        if (!predictionMap.isEmpty()) StorageSnappy.writeObject2File(OUTPUT_FILE_PREFIX + "_final", predictionMap);

        aiBrain.close();
        LOG.info("✅ V3 GENERATION COMPLETE!");
    }

    // Mapper thủ công từ V2 sang V3 (Hơi dài nhưng an toàn)
    private MarketFeaturesV3 convertToV3(MarketFeatures v2) {
        MarketFeaturesV3 v3 = new MarketFeaturesV3();
        v3.timestamp = v2.timestamp;
        v3.momentum1H = v2.momentum1H;
        v3.momentum1M = v2.momentum1M;
        v3.rsi14 = v2.rsi14;
        v3.volatility1H = v2.volatility1H;
        v3.fundingRateRaw = v2.fundingRateRaw;
        v3.volumeSpike = v2.volumeSpike;
        v3.btcDominance = v2.btcDominance;
        v3.basketMomentum15M = v2.basketMomentum15M;
        // ... (Map hết tất cả các trường còn lại) ...
        return v3;
    }
}