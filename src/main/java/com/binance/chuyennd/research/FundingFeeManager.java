package com.binance.chuyennd.research;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

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

    // TASK-019 A: refresh cache funding ở production (live chạy lâu → funding mới phải vào cache,
    // tránh getNearestFundingFee trả funding cũ/0 sau 24h). N ≤ chu kỳ funding (1h/4h/8h) → 30'.
    private static final long REFRESH_INTERVAL_MIN = 30;
    private volatile boolean refreshStarted = false;
    private ScheduledExecutorService refreshScheduler;

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

    // Hàm switch sang chế độ Production (Gọi ở DetectEntrySignal2TradeNormal.initData live)
    public void setProductionMode(boolean isProduction) {
        this.isProductionMode = isProduction;
        if (isProduction) {
            startProductionRefresh();
        }
    }

    /**
     * Bật scheduler reload funding định kỳ (CHỈ production). Idempotent — gọi nhiều lần chỉ start 1 lần.
     * Backtest KHÔNG gọi → không scheduler → load 1 lần như cũ (determinism giữ nguyên).
     */
    private synchronized void startProductionRefresh() {
        if (refreshStarted) return;
        refreshStarted = true;
        refreshScheduler = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "FundingFee-Refresh");
            t.setDaemon(true);
            return t;
        });
        refreshScheduler.scheduleAtFixedRate(this::refreshCache,
                REFRESH_INTERVAL_MIN, REFRESH_INTERVAL_MIN, TimeUnit.MINUTES);
        LOG.info("🔄 FundingFeeManager: BẬT production refresh (mỗi {} phút).", REFRESH_INTERVAL_MIN);
    }

    /**
     * Reload funding cho các symbol ĐANG có trong cache (atomic-swap per symbol). Bỏ qua symbol đọc
     * ra rỗng (lỗi đọc tạm thời) để KHÔNG xoá cache. Symbol mới vẫn được lazy-load ở getNearestFundingFee.
     */
    private void refreshCache() {
        int updated = 0;
        try {
            for (String symbol : new ArrayList<>(symbol2FundingFee.keySet())) {
                TreeMap<Long, Float> fresh = DataManagerAerospikeFloatSim.getFundingMap(symbol);
                if (fresh != null && !fresh.isEmpty()) {
                    symbol2FundingFee.put(symbol, fresh); // swap reference — thread-safe với reader
                    updated++;
                }
            }
            LOG.info("🔄 FundingFee refresh: cập nhật {} symbol.", updated);
        } catch (Exception e) {
            LOG.error("❌ FundingFee refresh lỗi: {}", e.getMessage());
        }
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

    /**
     * Trả về toàn bộ lịch sử funding (settlement-time → rate) của 1 coin để tính các feature
     * funding-sâu expanding (TASK-037): percentile/z/persistence/sum24h. Caller PHẢI tự cắt
     * {@code headMap(t, true)} để không look-ahead. Lazy-load như {@link #getNearestFundingFee}.
     *
     * @param symbol coin cần lấy lịch sử funding
     * @return {@link TreeMap} settlement-time→rate (có thể rỗng), hoặc null nếu không có/đọc lỗi
     */
    public TreeMap<Long, Float> getFundingHistory(String symbol) {
        TreeMap<Long, Float> map = symbol2FundingFee.get(symbol);
        if (map == null) {
            try {
                map = DataManagerAerospikeFloatSim.getFundingMap(symbol);
                if (map != null) symbol2FundingFee.put(symbol, map);
            } catch (Exception e) {
                LOG.warn("getFundingHistory lỗi đọc funding symbol={}: {}", symbol, e.getMessage());
                return null;
            }
        }
        return map;
    }



}
