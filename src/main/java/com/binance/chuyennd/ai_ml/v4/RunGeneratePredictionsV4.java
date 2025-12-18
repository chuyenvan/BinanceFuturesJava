package com.binance.chuyennd.ai_ml.v4;

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

public class RunGeneratePredictionsV4 {
    private static final Logger LOG = LoggerFactory.getLogger(RunGeneratePredictionsV4.class);

    private static final String MODEL_DIR_V4 = "../storage/ai_ml_data/ai_models_reg_v4";
    // Tên file output V4 riêng biệt
    private static final String OUTPUT_FILE_PREFIX = Configs.FILE_AI_ENTRY_PREDICTIONS + "_v4";

    public static void main(String[] args) {
        try {
            FundingFeeManager.getInstance();
            new RunGeneratePredictionsV4().generate();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void generate() throws Exception {
        LOG.info("🔥 STARTING V4 GENERATION ENGINE (ENSEMBLE + NEW FEATURES)...");

        OnnxInferenceManagerV4 aiBrain = new OnnxInferenceManagerV4(MODEL_DIR_V4);
        FeatureEngineerV4 featureEngineer = new FeatureEngineerV4();

        // Vẫn dùng Extractor cũ để lấy dữ liệu thô
        ComprehensiveMarketFeatureExtractor baseExtractor = new ComprehensiveMarketFeatureExtractor();
        TreeMap<Long, MarketRateChange> time2Rate = (TreeMap<Long, MarketRateChange>)
                StorageSnappy.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);

        TreeMap<Long, AiPredictionDataV4> predictionMap = new TreeMap<>();
        long currentTime = Utils.sdfFile.parse("20210101").getTime();
        long endTime = System.currentTimeMillis();

        int processed = 0;

        while (currentTime <= endTime) {
            try {
                // ... (Code check file existing & save year giống V3 - tự copy vào đây) ...

                TreeMap<Long, Map<String, KlineObjectSimple>> todayData =
                        DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTime);

                if (todayData != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : todayData.entrySet()) {
                        Long timestamp = entry.getKey();

                        MarketFeatures rawV2 = baseExtractor.extractAllFeatures(
                                timestamp, entry.getValue(), time2Rate.get(timestamp), null);

                        // 1. Convert V2 -> V4 Object (Map thêm volume, vol4H)
                        MarketFeaturesV4 rawV4 = convertToV4(rawV2, entry.getValue());

                        // 2. Feature Engineering (Phức tạp hơn V3)
                        float[] onnxInput = featureEngineer.processAndGetInputArray(rawV4);

                        if (onnxInput != null) {
                            rawV4.onnxInputData = onnxInput;
                            OnnxInferenceManagerV4.PredictionResultV4 res = aiBrain.predict(rawV4);

                            predictionMap.put(timestamp, new AiPredictionDataV4(
                                    timestamp, res.p15M, res.p1H, res.p4H, res.p24H, res.maxDD4H
                            ));
                        }
                    }
                }

                processed++;
                if (processed % 20 == 0) LOG.info("Day {} processed. V4 Map: {}",
                        Utils.normalizeDateYYYYMMDD(currentTime), predictionMap.size());

            } catch (Exception e) {
                LOG.error("Error day " + currentTime, e);
            }
            currentTime += Utils.TIME_DAY;
        }

        if(!predictionMap.isEmpty()) StorageSnappy.writeObject2File(OUTPUT_FILE_PREFIX + "_final", predictionMap);
        aiBrain.close();
        LOG.info("✅ V4 GENERATION COMPLETE!");
    }

    private MarketFeaturesV4 convertToV4(MarketFeatures v2, Map<String, KlineObjectSimple> marketData) {
        MarketFeaturesV4 v4 = new MarketFeaturesV4();
        // Copy Base Features
        v4.timestamp = v2.timestamp;
        v4.momentum1M = v2.momentum1M; v4.momentum5M = v2.momentum5M; v4.momentum15M = v2.momentum15M;
        v4.momentum1H = v2.momentum1H; v4.momentum4H = v2.momentum4H; v4.momentum24H = v2.momentum24H;
        v4.momentumAcceleration = v2.momentumAcceleration;
        v4.trendStrengthETH = v2.trendStrengthETH; v4.trendConsistency = v2.trendConsistency;

        v4.volatility1M = v2.volatility1M; v4.volatility15M = v2.volatility15M;
        v4.volatility1H = v2.volatility1H; v4.volatility24H = v2.volatility24H;
        // Ước lượng volatility4H (Vì V2 không có)
        v4.volatility4H = (v2.volatility1H + v2.volatility24H) / 2.0;
        v4.volatilityTermStructure = v2.volatilityTermStructure;

        v4.rsi14 = v2.rsi14; v4.volumeSpike = v2.volumeSpike; v4.distMA20 = v2.distMA20;
        v4.advanceDeclineRatio = v2.advanceDeclineRatio; v4.percentAboveMA20 = v2.percentAboveMA20;
        v4.volumeRatioUpDown = v2.volumeRatioUpDown; v4.marketBreadthStrength = v2.marketBreadthStrength;
        v4.btcDominance = v2.btcDominance;

        v4.fundingRateRaw = v2.fundingRateRaw; v4.fundingRateAvg24H = v2.fundingRateAvg24H;
        v4.fundingRateTrend = v2.fundingRateTrend;

        v4.basketMomentum15M = v2.basketMomentum15M; v4.basketMomentum1H = v2.basketMomentum1H;
        v4.basketRsi14 = v2.basketRsi14; v4.basketVolSpike = v2.basketVolSpike;

        v4.hourOfDay = v2.hourOfDay; v4.dayOfWeek = v2.dayOfWeek;
        v4.weekOfMonth = v2.weekOfMonth; v4.monthOfYear = v2.monthOfYear;

        // Tính Total USDT (Volume) cho Price Impact
        double totalVol = 0;
        if (marketData != null) {
            for (KlineObjectSimple k : marketData.values()) totalVol += k.totalUsdt;
        }
        v4.totalUsdt = totalVol;

        return v4;
    }
}