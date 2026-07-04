package com.binance.chuyennd.research;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class DataManager {
    private static final Logger LOG = LoggerFactory.getLogger(DataManager.class);
    public static String DATA_DIR = "storage_data/";
    public static boolean isDumpingMode = false;

    // Bộ nhớ đệm Static - Duy nhất cho toàn bộ chương trình
    private static volatile TreeMap<Long, MarketDataObject> cachedMarketData = null;
    private static volatile TreeMap<Long, AiPredictionData> cachedAiPredictionData = null;
    private static volatile TreeMap<Long, long[]> cachedFundingPred = null;
    private static final ConcurrentHashMap<Long, TreeMap<Long, Map<String, KlineObjectSimple>>>
            cachedTickers1M = new ConcurrentHashMap<>();

    private static final Object lockMarket = new Object();
    private static final Object lockAi = new Object();
    private static final Object lockFunding = new Object();

    public static TreeMap<Long, MarketDataObject> getMarketData() {
        if (cachedMarketData == null) {
            synchronized (lockMarket) {
                if (cachedMarketData == null) {
                    LOG.info("📥 [RAM] Đang nạp Market Data độc quyền từ Aerospike...");
                    cachedMarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
                }
            }
        }
        return cachedMarketData;
    }

    public static TreeMap<Long, AiPredictionData> getAiPredictionData() {
        if (cachedAiPredictionData == null) {
            synchronized (lockAi) {
                if (cachedAiPredictionData == null) {
                    LOG.info("📥 [RAM] Đang nạp AI Predictions độc quyền từ Aerospike...");
                    cachedAiPredictionData = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
                }
            }
        }
        return cachedAiPredictionData;
    }

//    // Hàm trả về Funding Pred (Dùng trong HPO và Simulator)
//    public static TreeMap<Long, long[]> getFundingPredictionData(Long startTime, int numberMinutes) {
//        if (cachedFundingPred == null) {
//            synchronized (lockFunding) {
//                if (cachedFundingPred == null) {
//                    LOG.info("📥 [RAM] Đang nạp Funding Predictions độc quyền cho dải thời gian này...");
//                    cachedFundingPred = DataManagerAerospikeFloatSim.getFundingPredictionsPrimitiveByRange(startTime, numberMinutes);
//                }
//            }
//        }
//        return cachedFundingPred;
//    }



}