package com.binance.chuyennd.research;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.utils.StorageSnappy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
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
            if (new File(FILE_FUNDING_FEE).exists()) {
                time2FundingFeeTrade = (ConcurrentHashMap<Long, Set<String>>) StorageSnappy.readObjectFromFile(FILE_FUNDING_FEE);
                LOG.info("Init funding fee time cache: {} records", time2FundingFeeTrade.size());
            } else {
                time2FundingFeeTrade = new ConcurrentHashMap<>();
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

}