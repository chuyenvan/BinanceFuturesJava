package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * Test logic xếp hạng dựa trên dữ liệu thật từ Aerospike.
 */
public class CoinRankRealDataTest {
    private static final Logger LOG = LoggerFactory.getLogger(CoinRankRealDataTest.class);

    public static void main(String[] args) {
        new CoinRankRealDataTest().runTestWithAerospikeData();
    }

    public void runTestWithAerospikeData() {
        LOG.info("🚀 ĐANG KÉO DỮ LIỆU THẬT TỪ AEROSPIKE ĐỂ TEST RANKING...");

        // 1. Xác định mốc thời gian (Lùi lại 2 ngày từ hiện tại cho chắc chắn có data)
        long endTime = (System.currentTimeMillis() / 60000L) * 60000L;
        long startTime = endTime - (1500 * Utils.TIME_MINUTE); // Lấy 1500 phút

        try {
            // 2. Kéo dữ liệu thực từ Aerospike
            LOG.info("📥 Đang đọc data từ {} đến {}...",
                    Utils.normalizeDateYYYYMMDDHHmm(startTime),
                    Utils.normalizeDateYYYYMMDDHHmm(endTime));

            TreeMap<Long, Map<String, KlineObjectSimple>> realData =
                    DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(startTime, 1500);

            if (realData == null || realData.isEmpty()) {
                LOG.error("❌ Không lấy được dữ liệu từ Aerospike. Kiểm tra lại kết nối hoặc mốc thời gian!");
                return;
            }

            HistoryManager historyManager = HistoryManager.getInstance();
            CoinRankManager rankManager = CoinRankManager.getInstance();

            // 3. Đổ dữ liệu vào HistoryManager từng phút một để mô phỏng luồng chạy thực tế
            int minuteCount = 0;
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : realData.entrySet()) {
                long timestamp = entry.getKey();
                Map<String, KlineObjectSimple> tickerMap = entry.getValue();

                // Nạp vào Singleton HistoryManager
                historyManager.updateHistory(tickerMap);
                minuteCount++;

                // 4. Cứ mỗi mốc 15 phút chẵn, chúng ta sẽ check bảng xếp hạng
                if ((timestamp / Utils.TIME_MINUTE) % 15 == 0) {
                    LOG.info("\n--- 🕒 Checkpoint: {} ---", Utils.normalizeDateYYYYMMDDHHmm(timestamp));

                    // Gọi hàm lấy Top Coin (hàm này sẽ tự trigger updateRanking bên trong)
                    List<String> top50Percent = rankManager.getTopCoin(timestamp);

                    if (top50Percent.isEmpty()) {
                        LOG.warn("⚠️ Top 50% đang rỗng (Có thể do chưa đủ nến warmup)");
                        continue;
                    }

                    LOG.info("✅ Tổng số coin ghi nhận: {}", historyManager.getAllHistory().size());
                    LOG.info("🔥 Số lượng coin trong Standard Universe (Top 50%): {}", top50Percent.size());

                    // In ra Top 10 đồng có Volume lớn nhất thực tế tại thời điểm đó
                    LOG.info("🏆 TOP 10 THANH KHOẢN CAO NHẤT:");
                    int limit = Math.min(10, top50Percent.size());
                    for (int i = 0; i < limit; i++) {
                        String sym = top50Percent.get(i);
                        LOG.info("   Rank {}: {} (Tier: {})", (i + 1), sym, rankManager.getCoinTier(sym, timestamp));
                    }
                }
            }

            LOG.info("\n🎉 HOÀN TẤT ĐỐI SOÁT DỮ LIỆU THẬT. Đã xử lý {} phút dữ liệu.", minuteCount);

        } catch (Exception e) {
            LOG.error("❌ Lỗi trong quá trình chạy test data thực:", e);
        }
    }
}