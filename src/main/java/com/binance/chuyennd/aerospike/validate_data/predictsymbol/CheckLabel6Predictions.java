package com.binance.chuyennd.aerospike.validate_data.predictsymbol;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.fundingv2.FundingFeatureExtractorV2;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;

public class CheckLabel6Predictions {

    private static final Logger LOG = LoggerFactory.getLogger(CheckLabel6Predictions.class);
    private static final String TEST_SYMBOL = "BTCUSDT";

    public static void main(String[] args) throws ParseException {
        // 1. Setup time for 2021-01-02
        long startOfDay = Utils.sdfFile.parse("20210102").getTime() + 7 * Utils.TIME_HOUR; // Adjust timezone if needed
        int totalMinutesInDay = 1440;

        LOG.info("🚀 Starting validation for Label6 on {}", Utils.normalizeDateYYYYMMDDHHmm(startOfDay));

        // 2. Fetch Ticker Data for generating features
        // Assuming readDataFromAerospikeCustom is available
        TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers =
                DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(startOfDay - (60 * Utils.TIME_MINUTE), 1500);

        if (time2Tickers.isEmpty()) {
            LOG.error("❌ No ticker data found.");
            return;
        }

        // 3. Fetch the primitive predictions (Assuming this represents the Label6 predictions)
        // You specified to use getFundingPredictionsPrimitiveByRange as in the simulator
        TreeMap<Long, long[]> dbPredictions = DataManagerAerospikeFloatSim.getFundingPredictionsPrimitiveByRange(startOfDay, totalMinutesInDay);

        if (dbPredictions.isEmpty()) {
            LOG.error("❌ No predictions found in Aerospike for this range.");
            return;
        }

        // 4. Initialize the Extractor to generate features (which might contain the logic for the actual label)
        FundingFeatureExtractorV2 extractor = new FundingFeatureExtractorV2();
        for (Map<String, KlineObjectSimple> snapshot : time2Tickers.values()) {
            extractor.updateMarketHistory(snapshot);
        }

        // 5. Select 10 random timestamps
        List<Long> availableTimestamps = new ArrayList<>(dbPredictions.keySet());
        Collections.shuffle(availableTimestamps);
        List<Long> random10Times = availableTimestamps.subList(0, Math.min(10, availableTimestamps.size()));

        int matchCount = 0;
        List<String> mockBasket = Collections.singletonList(TEST_SYMBOL);

        LOG.info("🔍 Checking 10 random records...");

        for (Long timestamp : random10Times) {
            Map<String, KlineObjectSimple> currentSnapshot = time2Tickers.get(timestamp);
            if (currentSnapshot == null || !currentSnapshot.containsKey(TEST_SYMBOL)) continue;

            KlineObjectSimple currentKline = currentSnapshot.get(TEST_SYMBOL);

            // A. Retrieve Prediction from Aerospike (Primitive Array)
            long[] encodedPredictions = dbPredictions.get(timestamp);
            Float dbPred = getPredictionFromPrimitiveArray(encodedPredictions, SimpleSymbolMapper.getInstance().getId(TEST_SYMBOL));

            if (dbPred == null) {
                LOG.warn("   ⚠️ No prediction found in DB for {} at {}", TEST_SYMBOL, Utils.normalizeDateYYYYMMDDHHmm(timestamp));
                continue;
            }

            // B. Generate Features (Assuming this is how you would determine the 'expected' Label6 value)
            // Note: The FundingMarketFeatures object has an integer `label6`, but `dbPred` is a float.
            // You must adapt this based on what the float prediction actually represents versus the integer label.
            OrderTargetInfoTest dummyOrder = new OrderTargetInfoTest(
                    OrderTargetStatus.REQUEST, currentKline.priceClose, null, 1.0f,
                    Configs.LEVERAGE_ORDER, TEST_SYMBOL, timestamp, timestamp, OrderSide.BUY
            );
            MarketDataObject dummyMarketData = new MarketDataObject(0f, 0f, 0f); // Mock data

            FundingMarketFeatures generatedFeatures = extractor.extractFeatures(
                    timestamp, dummyOrder, currentSnapshot, dummyMarketData, mockBasket);

            // C. Compare (You need to define how the generated feature relates to the stored float prediction)
            // For example, if the float prediction is a probability and label6 is the actual class (0-4):
            // This is a placeholder comparison. You must replace this with your actual logic.
            int expectedLabel6 = generatedFeatures != null ? generatedFeatures.label6 : -1;

            LOG.info("▶️ Time: {} | DB Pred (Float): {} | Generated Label6 (Int): {}",
                    Utils.normalizeDateYYYYMMDDHHmm(timestamp), dbPred, expectedLabel6);

            // TODO: Implement your specific logic to verify if the float prediction matches the expected label6
            // boolean isMatch = evaluatePrediction(dbPred, expectedLabel6);
            // if (isMatch) matchCount++;
        }

        LOG.info("🏁 Validation complete.");
    }

    // Extracted from SimulatorMarketLevelTicker1MStopLoss
    private static Float getPredictionFromPrimitiveArray(long[] encodedArray, short targetId) {
        if (encodedArray == null) return null;
        for (long encodedData : encodedArray) {
            if ((short) (encodedData >> 32) == targetId) {
                return Float.intBitsToFloat((int) encodedData);
            }
        }
        return null;
    }
}