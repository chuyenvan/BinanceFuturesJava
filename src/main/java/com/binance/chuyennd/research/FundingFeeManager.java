package com.binance.chuyennd.research;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.chuyennd.ai_ml.RunOptimizationBudgetRatio;
import com.binance.client.model.market.FundingRate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class FundingFeeManager {
    public static final Logger LOG = LoggerFactory.getLogger(FundingFeeManager.class);
    private ConcurrentHashMap<String, TreeMap<Long, Double>> symbol2FundingFee = new ConcurrentHashMap<>();
    public static final String FILE_FUNDING_FEE = "storage/fundingfee_time.data";
    public ConcurrentHashMap<Long, Set<String>> time2FundingFeeTrade;

    private static volatile FundingFeeManager INSTANCE = null;

    public static FundingFeeManager getInstance() {
        if (INSTANCE == null) {
            synchronized (FundingFeeManager.class) {
                if (INSTANCE == null) {
                    INSTANCE = new FundingFeeManager();
                    INSTANCE.initData();
                }
            }
        }
        return INSTANCE;
    }

    private void initData() {
        try {
            Map<String, TreeMap<Long, Double>> symbol2Funding = DataManagerAerospikeFloatSim.getAllFundingMap();
            for (String symbol : symbol2Funding.keySet()) {
                symbol2FundingFee.put(symbol, symbol2Funding.get(symbol));
            }
            if (RunOptimizationBudgetRatio.CACHED_time2FundingFeeTrade != null) {
                this.time2FundingFeeTrade = RunOptimizationBudgetRatio.CACHED_time2FundingFeeTrade;
            } else {
                if (new File(FILE_FUNDING_FEE).exists()) {
                    time2FundingFeeTrade = (ConcurrentHashMap<Long, Set<String>>) StorageSnappy.readObjectFromFile(FILE_FUNDING_FEE);
                } else {
                    time2FundingFeeTrade = new ConcurrentHashMap<>();
                }
            }
            LOG.info("Init funding fee: {} symbols", symbol2FundingFee.size());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void writeData2File() {
        try {
            StorageSnappy.writeObject2File(FILE_FUNDING_FEE, time2FundingFeeTrade);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public Double getFundingFee(String symbol, long time) {
        TreeMap<Long, Double> time2RateFunding = symbol2FundingFee.get(symbol);
        if (time2RateFunding == null) {
            // Thử load lại nếu chưa có (Lazy loading)
            try {
                time2RateFunding = DataManagerAerospikeFloatSim.getFundingMap(symbol);
                if (time2RateFunding != null) {
                    symbol2FundingFee.put(symbol, time2RateFunding);
                }
            } catch (Exception e) {
                return null;
            }
        }

        if (time2RateFunding != null && time2RateFunding.containsKey(time)) {
            return time2RateFunding.get(time);
        }
        return null;
    }

    /**
     * 🔥 HÀM MỚI QUAN TRỌNG: Lấy Funding Fee gần nhất (Hỗ trợ mọi khung 1h/4h/8h)
     * Dùng TreeMap.floorEntry để tìm bản ghi có thời gian <= timestamp
     */
    public Double getNearestFundingFee(String symbol, long timestamp) {
        TreeMap<Long, Double> time2RateFunding = symbol2FundingFee.get(symbol);
        if (time2RateFunding == null) {
            try {
                time2RateFunding = DataManagerAerospikeFloatSim.getFundingMap(symbol);
                if (time2RateFunding != null) symbol2FundingFee.put(symbol, time2RateFunding);
            } catch (Exception e) {
                return null;
            }
        }

        if (time2RateFunding == null || time2RateFunding.isEmpty()) return null;

        // Tìm mốc thời gian gần nhất <= timestamp
        java.util.Map.Entry<Long, Double> entry = time2RateFunding.floorEntry(timestamp);

        if (entry != null) {
            // Nếu dữ liệu quá cũ (ví dụ > 24h trước) thì coi như không có (tránh lấy data năm ngoái)
            if (timestamp - entry.getKey() > 24 * 3600 * 1000L) {
                return 0.0;
            }
            return entry.getValue();
        }

        return null;
    }

    public Set<String> getFundingBuyNew(long time) {
        long timeGet = Utils.getHour(time);
        if (time2FundingFeeTrade == null) time2FundingFeeTrade = new ConcurrentHashMap<>();

        if (time2FundingFeeTrade.containsKey(timeGet)) {
            return time2FundingFeeTrade.get(timeGet);
        } else {
            Set<String> symbols = new HashSet<>();
            for (String symbol : symbol2FundingFee.keySet()) {
                TreeMap<Long, Double> time2Funding = symbol2FundingFee.get(symbol);
                if (time2Funding == null) continue;

                TreeMap<Long, Double> time2FundingGet = new TreeMap<>();
                for (int i = 0; i < Configs.NUMBER_HOUR_FUNDING_CAL; i++) {
                    Long timeF = timeGet - i * Utils.TIME_HOUR;
                    if (time2Funding.containsKey(timeF)) {
                        time2FundingGet.put(timeF, time2Funding.get(timeF));
                    }
                }
                for (Double funding : time2FundingGet.values()) {
                    if (funding < Configs.FUNDING_MAX_TRADE
                            || funding > Configs.FUNDING_MIN_TRADE) {
                        symbols.add(symbol);
                    }
                }
            }
            time2FundingFeeTrade.put(timeGet, symbols);
            return symbols;
        }
    }

    public TreeMap<Long, Double> getFundingFeeByTime(String symbol, long startTime, long endTime) {
        TreeMap<Long, Double> time2RateFunding = symbol2FundingFee.get(symbol);
        if (time2RateFunding == null) {
            time2RateFunding = DataManagerAerospikeFloatSim.getFundingMap(symbol);
        }
        if (time2RateFunding != null) {
            symbol2FundingFee.put(symbol, time2RateFunding);
            TreeMap<Long, Double> results = new TreeMap<>();
            for (Long time : time2RateFunding.keySet()) {
                if (time <= startTime) {
                    continue;
                }
                if (time > endTime) {
                    break;
                }
                results.put(time, time2RateFunding.get(time));
            }
            return results;
        }
        return null;
    }
}