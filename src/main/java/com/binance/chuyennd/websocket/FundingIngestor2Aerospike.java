package com.binance.chuyennd.websocket;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.utils.Utils;
import com.binance.connector.futures.client.impl.UMWebsocketClientImpl;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Thu thập Funding Rate toàn sàn và lưu vào Aerospike vĩnh viễn qua DataManager.
 */
public class FundingIngestor2Aerospike {
    private static final Logger LOG = LoggerFactory.getLogger(FundingIngestor2Aerospike.class);

    // Buffer RAM: Symbol -> (Mốc thời gian kỳ funding -> Tỷ lệ Funding Float)
    private final ConcurrentHashMap<String, Map<Long, Float>> fundingBuffer = new ConcurrentHashMap<>();

    public static void main(String[] args) {
        new FundingIngestor2Aerospike().start();
    }

    public void start() {
        LOG.info("🚀 Khởi động FundingIngestor (Lưu trữ Float & Pruning)...");

        UMWebsocketClientImpl client = new UMWebsocketClientImpl();

        // speed = 3: Cập nhật mỗi 3 giây
        client.allMarkPriceStream(3, (event) -> {
            processMarkPriceArray(event);
        });

        startFlushLoop();
    }

    private void processMarkPriceArray(String eventStr) {
        try {
            JSONArray symbolList = new JSONArray(eventStr);
            for (int i = 0; i < symbolList.length(); i++) {
                JSONObject data = symbolList.getJSONObject(i);
                String symbol = data.getString("s").toUpperCase();

                if (symbol.endsWith("USDT")) {
                    float fundingRate = data.getFloat("r"); // Lấy float trực tiếp
                    long nextFundingTime = data.getLong("T");
                    long periodStart = nextFundingTime - (8 * Utils.TIME_HOUR);

                    fundingBuffer.computeIfAbsent(symbol, k -> new HashMap<>())
                            .put(periodStart, fundingRate);
                }
            }
        } catch (Exception e) {
            LOG.error("❌ Parse MarkPrice Error: {}", e.getMessage());
        }
    }

    private void startFlushLoop() {
        new Thread(() -> {
            Thread.currentThread().setName("Funding-Sync-Thread");
            while (true) {
                try {
                    Thread.sleep(60000); // Lưu mỗi phút
                    if (fundingBuffer.isEmpty()) continue;

                    Map<String, Map<Long, Float>> snapshot = new HashMap<>(fundingBuffer);
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