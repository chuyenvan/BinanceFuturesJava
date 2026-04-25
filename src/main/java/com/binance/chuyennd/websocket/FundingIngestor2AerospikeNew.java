package com.binance.chuyennd.websocket;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.client.constant.Constants;
import org.apache.commons.lang.StringUtils;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Thu thập Funding Rate toàn sàn và lưu vào Aerospike vĩnh viễn qua DataManager.
 * Phiên bản V2: Nâng cấp REST API Polling, vượt tường lửa và chống rò rỉ RAM.
 */
public class FundingIngestor2AerospikeNew {
    private static final Logger LOG = LoggerFactory.getLogger(FundingIngestor2AerospikeNew.class);

    // Buffer RAM: Symbol -> (Mốc thời gian kỳ funding -> Tỷ lệ Funding Float)
    private final ConcurrentHashMap<String, Map<Long, Float>> fundingBuffer = new ConcurrentHashMap<>();

    public static void main(String[] args) {
        new FundingIngestor2AerospikeNew().start();
    }

    public void start() {
        LOG.info("🚀 Khởi động FundingIngestor V2 (REST POLLING - Vượt mọi tường lửa)...");

        startPollingLoop();
        startFlushLoop();
    }

    private void startPollingLoop() {
        new Thread(() -> {
            Thread.currentThread().setName("Funding-Polling-Thread");
            // Endpoint lấy Funding Rate toàn sàn (Tốn đúng 1 Weight)
            String endpoint = "https://fapi.binance.com/fapi/v1/premiumIndex";

            while (true) {
                try {
                    String response = HttpRequest.getContentFromUrl(endpoint, 5000);

                    // Bọc thép: Đảm bảo JSON là một Mảng hợp lệ
                    if (StringUtils.isNotBlank(response) && response.trim().startsWith("[")) {
                        JSONArray symbolList = new JSONArray(response);

                        for (int i = 0; i < symbolList.length(); i++) {
                            JSONObject data = symbolList.getJSONObject(i);

                            // Trong REST API, key là "symbol" thay vì "s" như ở WebSocket
                            String symbol = data.getString("symbol").toUpperCase();

                            // Lọc các cặp USDT hợp lệ và bỏ qua coin chết
                            if (symbol.endsWith("USDT") && !Constants.diedSymbol.contains(symbol)) {
                                // REST API dùng "lastFundingRate" và "nextFundingTime" (WebSocket dùng "r" và "T")
                                float fundingRate = data.getFloat("lastFundingRate");
                                long nextFundingTime = data.getLong("nextFundingTime");

                                fundingBuffer.computeIfAbsent(symbol, k -> new HashMap<>())
                                        .put(nextFundingTime, fundingRate);
                            }
                        }
                    } else if (StringUtils.isNotBlank(response) && response.trim().startsWith("{")) {
                        LOG.warn("⚠️ API PremiumIndex trả về lỗi (Có thể do Limit): {}", response);
                    }

                    // Funding Rate thay đổi rất chậm, 30 giây cập nhật 1 lần là quá dư dả và an toàn
                    Thread.sleep(30000);

                } catch (Exception e) {
                    LOG.error("❌ Lỗi luồng Polling Funding: {}", e.getMessage());
                    try { Thread.sleep(5000); } catch (InterruptedException ignored) {}
                }
            }
        }).start();
    }

    private void startFlushLoop() {
        new Thread(() -> {
            Thread.currentThread().setName("Funding-Sync-Thread");
            while (true) {
                try {
                    Thread.sleep(60000); // Lưu mỗi phút 1 lần
                    if (fundingBuffer.isEmpty()) continue;

                    // Lấy bản sao của Buffer hiện tại
                    Map<String, Map<Long, Float>> snapshot = new HashMap<>(fundingBuffer);

                    // 🔥 SỬA LỖI TRÀN RAM: Xóa sạch Buffer gốc sau khi lấy snapshot.
                    // Nếu không xóa, Map này sẽ phình to vĩnh viễn và bị ghi đè lặp đi lặp lại vào DB mỗi phút.
                    fundingBuffer.clear();

                    for (Map.Entry<String, Map<Long, Float>> entry : snapshot.entrySet()) {
                        DataManagerAerospikeFloatSim.writeFundingMap(entry.getKey(), entry.getValue());
                    }

                    LOG.info("✅ Đã đồng bộ Funding Rate cho {} mã vào Aerospike.", snapshot.size());
                } catch (Exception e) {
                    LOG.error("❌ Lỗi luồng Flush Funding: {}", e.getMessage());
                }
            }
        }).start();
    }
}