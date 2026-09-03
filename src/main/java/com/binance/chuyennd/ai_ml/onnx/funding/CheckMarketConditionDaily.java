package com.binance.chuyennd.ai_ml.onnx.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.TreeMap;

public class CheckMarketConditionDaily {
    private static final Logger LOG = LoggerFactory.getLogger(CheckMarketConditionDaily.class);

    public static void main(String[] args) throws Exception {
        // 1. CẤU HÌNH THAM SỐ (Giống hệt lúc chạy Generate Tool)

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

            // --- CHỈ CHECK TRONG NGÀY MỤC TIÊU ---
            if (time >= targetStart && time < targetEnd) {
                countMet++;
                MarketDataObject mData = entry.getValue();

                LOG.info("✅ MATCH: {} | Rate15M: {} ",
                        Utils.normalizeDateYYYYMMDDHHmm(time),
                        String.format("%.4f", mData.rateDown15MAvg)
                       );
            }

            // Dừng nếu vượt quá ngày cần check
            if (time >= targetEnd) break;
        }

        LOG.info("==========================================");
        LOG.info("📊 TỔNG KẾT NGÀY {}", targetDateStr);
        LOG.info("   - Tổng số phút thỏa mãn: {} phút", countMet);
        LOG.info("==========================================");
    }



}