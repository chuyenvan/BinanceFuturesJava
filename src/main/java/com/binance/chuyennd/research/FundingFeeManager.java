package com.binance.chuyennd.research;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class FundingFeeManager {
    public static final Logger LOG = LoggerFactory.getLogger(FundingFeeManager.class);

    // Cache danh sách Funding Rate của từng coin
    private ConcurrentHashMap<String, TreeMap<Long, Float>> symbol2FundingFee = new ConcurrentHashMap<>();

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
            Map<String, TreeMap<Long, Float>> symbol2Funding = DataManagerAerospikeFloatSim.getAllFundingMap();
            for (String symbol : symbol2Funding.keySet()) {
                symbol2FundingFee.put(symbol, symbol2Funding.get(symbol));
            }
            LOG.info("Init funding fee data: {} symbols", symbol2FundingFee.size());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public Float getNearestFundingFee(String symbol, long timestamp) {
        TreeMap<Long, Float> time2RateFunding = symbol2FundingFee.get(symbol);

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

        Map.Entry<Long, Float> entry = time2RateFunding.floorEntry(timestamp);
        if (entry != null) {
            if (timestamp - entry.getKey() > 24 * 3600 * 1000L) return 0.0f;
            return entry.getValue();
        }
        return null;
    }



}
