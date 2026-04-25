package com.binance.chuyennd.websocket.checkdata;

import okhttp3.*;
import org.json.JSONArray;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.TimeUnit;

public class RestMiniTickerIngestor {
    private static final Logger LOG = LoggerFactory.getLogger(RestMiniTickerIngestor.class);

    public static void main(String[] args) {
        LOG.info("🚀 BẮT ĐẦU TEST LEO CỬA SỔ BẰNG REST API POLLING");

        OkHttpClient client = new OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(10, TimeUnit.SECONDS)
                .build();

        // Lấy đúng 1 cây nến 1 phút mới nhất của BTC
        String url = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=1";

        new Thread(() -> {
            while (true) {
                try {
                    Request request = new Request.Builder()
                            .url(url)
                            .addHeader("User-Agent", "Mozilla/5.0")
                            .build();

                    try (Response response = client.newCall(request).execute()) {
                        if (response.isSuccessful() && response.body() != null) {
                            String responseBody = response.body().string();

                            // Parse JSON Array của Binance
                            JSONArray klines = new JSONArray(responseBody);
                            if (klines.length() > 0) {
                                JSONArray latestKline = klines.getJSONArray(0);
                                long startTime = latestKline.getLong(0);
                                float open = latestKline.getFloat(1);
                                float high = latestKline.getFloat(2);
                                float low = latestKline.getFloat(3);
                                float close = latestKline.getFloat(4);
                                float volume = latestKline.getFloat(7); // Quote Asset Volume

                                LOG.info("📥 [REST DATA] BTCUSDT | Đang chạy: {} | Close: {}", startTime, close);
                            }
                        } else {
                            LOG.error("❌ Gọi API thất bại: HTTP {}", response.code());
                        }
                    }

                    // Ngủ 2 giây rồi hỏi tiếp (Cực kỳ an toàn với Rate Limit của Binance)
                    Thread.sleep(2000);

                } catch (Exception e) {
                    LOG.error("❌ Lỗi Polling: ", e);
                    try { Thread.sleep(2000); } catch (InterruptedException ignored) {}
                }
            }
        }).start();
    }
}