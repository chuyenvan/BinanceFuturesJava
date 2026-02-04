package com.binance.chuyennd.research;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.chuyennd.ai_ml.hpo.budget.RunOptimizationBudgetRatio;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class FundingFeeManager {
    public static final Logger LOG = LoggerFactory.getLogger(FundingFeeManager.class);

    // Cache danh sách Funding Rate của từng coin
    private ConcurrentHashMap<String, TreeMap<Long, Double>> symbol2FundingFee = new ConcurrentHashMap<>();

    // Cache danh sách coin cần trade theo giờ (Dùng cho Backtest)
    public static final String FILE_FUNDING_FEE = "storage/fundingfee_time.data";
    public ConcurrentHashMap<Long, Set<String>> time2FundingFeeTrade;

    private static volatile FundingFeeManager INSTANCE = null;

    // Cờ đánh dấu chế độ Production hay Backtest
    private boolean isProductionMode = false;

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

    // Hàm switch sang chế độ Production (Gọi ở DetectEntrySignal2TradeNormal)
    public void setProductionMode(boolean isProduction) {
        this.isProductionMode = isProduction;
    }

    private void initData() {
        try {
            // Load toàn bộ Funding Data từ Aerospike (Nặng nhưng cần thiết cho Backtest nhanh)
            Map<String, TreeMap<Long, Double>> symbol2Funding = DataManagerAerospikeFloatSim.getAllFundingMap();
            for (String symbol : symbol2Funding.keySet()) {
                symbol2FundingFee.put(symbol, symbol2Funding.get(symbol));
            }

            // Load Cache danh sách coin trade (Chỉ cho Backtest)
            if (RunOptimizationBudgetRatio.CACHED_time2FundingFeeTrade != null) {
                this.time2FundingFeeTrade = RunOptimizationBudgetRatio.CACHED_time2FundingFeeTrade;
            } else {
                if (new File(FILE_FUNDING_FEE).exists()) {
                    time2FundingFeeTrade = (ConcurrentHashMap<Long, Set<String>>) StorageSnappy.readObjectFromFile(FILE_FUNDING_FEE);
                    LOG.info("Init funding fee time cache: {} records", time2FundingFeeTrade.size());
                } else {
                    time2FundingFeeTrade = new ConcurrentHashMap<>();
                }
            }
            LOG.info("Init funding fee data: {} symbols", symbol2FundingFee.size());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void writeData2File() {
        if (isProductionMode) return; // Production không ghi file
        try {
            StorageSnappy.writeObject2File(FILE_FUNDING_FEE, time2FundingFeeTrade);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    /**
     * 🔥 HÀM CHUNG DUY NHẤT ĐỂ LẤY LIST COIN CẦN TRADE
     * Hỗ trợ cả Backtest (có cache) và Production (Live check)
     */
    public Set<String> getFundingBuyNew(long currentTime) {
        // PRODUCTION MODE: Tính toán trực tiếp, không dùng Cache file
        if (isProductionMode) {
            return calculateFundingBuyList(currentTime);
        }

        // BACKTEST MODE: Dùng Cache để tăng tốc
        long timeGet = Utils.getHour(currentTime);
        if (time2FundingFeeTrade == null) time2FundingFeeTrade = new ConcurrentHashMap<>();

        if (time2FundingFeeTrade.containsKey(timeGet)) {
            return time2FundingFeeTrade.get(timeGet);
        } else {
            // Nếu chưa có trong cache -> Tính toán và lưu lại
            Set<String> symbols = calculateFundingBuyList(currentTime);
            time2FundingFeeTrade.put(timeGet, symbols);
            return symbols;
        }
    }

    /**
     * Logic cốt lõi: Tính toán danh sách coin thỏa mãn Funding tại thời điểm T
     */
    private Set<String> calculateFundingBuyList(long currentTime) {
        Set<String> symbols = new HashSet<>();
        long startTimeCalc = currentTime - (Configs.NUMBER_HOUR_FUNDING_CAL * Utils.TIME_HOUR);

        for (String symbol : symbol2FundingFee.keySet()) {
            TreeMap<Long, Double> time2Funding = symbol2FundingFee.get(symbol);

            // Lazy load cho Production: Nếu chưa có data thì load từ Aerospike
            if (time2Funding == null && isProductionMode) {
                time2Funding = DataManagerAerospikeFloatSim.getFundingMap(symbol);
                if (time2Funding != null) symbol2FundingFee.put(symbol, time2Funding);
            }

            if (time2Funding == null || time2Funding.isEmpty()) continue;

            // Kiểm tra trong khoảng thời gian quy định (ví dụ 48h qua)
            // Lấy subset từ map để tối ưu
            SortedMap<Long, Double> subMap = time2Funding.subMap(startTimeCalc, true, currentTime, true);

            for (Double funding : subMap.values()) {
                if (funding < Configs.FUNDING_MAX_TRADE || funding > Configs.FUNDING_MIN_TRADE) {
                    symbols.add(symbol);
                    break; // Chỉ cần 1 lần thỏa mãn là add luôn
                }
            }
        }
        return symbols;
    }

    public Double getNearestFundingFee(String symbol, long timestamp) {
        TreeMap<Long, Double> time2RateFunding = symbol2FundingFee.get(symbol);

        // Lazy load
        if (time2RateFunding == null) {
            try {
                time2RateFunding = DataManagerAerospikeFloatSim.getFundingMap(symbol);
                if (time2RateFunding != null) symbol2FundingFee.put(symbol, time2RateFunding);
            } catch (Exception e) {
                return null;
            }
        }

        if (time2RateFunding == null || time2RateFunding.isEmpty()) return null;

        Map.Entry<Long, Double> entry = time2RateFunding.floorEntry(timestamp);
        if (entry != null) {
            if (timestamp - entry.getKey() > 24 * 3600 * 1000L) return 0.0;
            return entry.getValue();
        }
        return null;
    }

    // Giữ lại hàm cũ để tương thích ngược nếu cần, trỏ về hàm mới
    public Set<String> getFundingListSymbol2Trade(long time) {
        return getFundingBuyNew(time);
    }
}