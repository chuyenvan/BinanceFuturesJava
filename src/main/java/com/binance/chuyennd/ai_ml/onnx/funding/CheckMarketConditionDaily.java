package com.binance.chuyennd.ai_ml.onnx.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.Collections;
import java.util.Map;
import java.util.TreeMap;

public class CheckMarketConditionDaily {
    private static final Logger LOG = LoggerFactory.getLogger(CheckMarketConditionDaily.class);

    // Biến lưu lịch sử Rate (Quan trọng để tính minRate60M)
    private static final TreeMap<Long, Float> time2RateDown15MAvg = new TreeMap<>();

    public static void main(String[] args) throws Exception {
        // 1. CẤU HÌNH THAM SỐ (Giống hệt lúc chạy Generate Tool)
        Configs.FUNDING_RATE_MIN_TRADE = -0.013;
        Configs.FUNDING_RATE_MIN_TRADE_FULL = -0.025;
        Configs.FUNDING_RATE_UP_AVG = 0.004;
        Configs.FUNDING_RATE_DOWN_AVG = -0.005;
        Configs.NUMBER_RATE_DOWN_HISTORY_TRADE = 60; // Giữ lịch sử 60 phút

        // 2. NGÀY CẦN CHECK (Sửa ngày tại đây)
        String targetDateStr = "20221007";

        long targetStart = Utils.sdfFile.parse(targetDateStr).getTime();
        long targetEnd = targetStart + Utils.TIME_DAY;


        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();

        LOG.info("✅ Đã load {} records. Bắt đầu quét...", time2MarketData.size());

        int countMet = 0;

        // 3. DUYỆT DATA (Duyệt từ đầu hoặc từ trước đó vài tiếng để Warmup history)
        // Lấy key đầu tiên để bắt đầu update history từ sớm
        long dataStart = time2MarketData.firstKey();

        // Nếu data quá lớn, có thể nhảy đến trước targetDate 24h để tiết kiệm thời gian
        if (dataStart < targetStart - Utils.TIME_DAY) {
            dataStart = targetStart - Utils.TIME_DAY;
        }

        for (Map.Entry<Long, MarketDataObject> entry : time2MarketData.tailMap(dataStart).entrySet()) {
            long time = entry.getKey();

            // --- BƯỚC QUAN TRỌNG: UPDATE HISTORY ---
            // Phải chạy bước này cho MỌI phút (kể cả trước targetStart) để time2RateDown15MAvg luôn đúng
            updateMarketRateHistory(time, time2MarketData);

            // --- CHỈ CHECK TRONG NGÀY MỤC TIÊU ---
            if (time >= targetStart && time < targetEnd) {
                if (isMarketConditionMet(time, time2MarketData)) {
                    countMet++;
                    MarketDataObject mData = entry.getValue();
                    Float minRate60M = Collections.min(time2RateDown15MAvg.values());

                    LOG.info("✅ MATCH: {} | Rate15M: {} | Min60M: {}",
                            Utils.normalizeDateYYYYMMDDHHmm(time),
                            String.format("%.4f", mData.rateDown15MAvg),
                            String.format("%.4f", minRate60M));
                }
            }

            // Dừng nếu vượt quá ngày cần check
            if (time >= targetEnd) break;
        }

        LOG.info("==========================================");
        LOG.info("📊 TỔNG KẾT NGÀY {}", targetDateStr);
        LOG.info("   - Tổng số phút thỏa mãn: {} phút", countMet);
        LOG.info("==========================================");
    }

    // --- CÁC HÀM HELPER (COPY TỪ GENERATE TOOL) ---

    private static void updateMarketRateHistory(long time, TreeMap<Long, MarketDataObject> time2MarketData) {
        MarketDataObject marketData = time2MarketData.get(time);
        if (marketData == null) return;

        // Thêm rate hiện tại vào lịch sử
        time2RateDown15MAvg.put(time, marketData.rateDown15MAvg);

        // Xóa các rate cũ quá 60 phút (để tính minRate60M chính xác)
        while (time2RateDown15MAvg.size() > Configs.NUMBER_RATE_DOWN_HISTORY_TRADE) {
            time2RateDown15MAvg.remove(time2RateDown15MAvg.firstKey());
        }
    }

    private static boolean isMarketConditionMet(long time, TreeMap<Long, MarketDataObject> time2MarketData) {
        MarketDataObject marketData = time2MarketData.get(time);
        if (marketData == null) return false;

        // Tính min rate trong 60 phút gần nhất từ lịch sử đã update
        Float minRate15Min60M = time2RateDown15MAvg.isEmpty() ? 0f : Collections.min(time2RateDown15MAvg.values());

        return MarketBigChangeDetector.isFundingFeeTrade(
                marketData.rateDown15MAvg,
                marketData.rateDownAvg,
                marketData.rateUpAvg,
                minRate15Min60M);
    }
}