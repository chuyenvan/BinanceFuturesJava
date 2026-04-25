package com.binance.chuyennd.websocket.checkdata;

import com.binance.client.SubscriptionClient;
import com.binance.client.SubscriptionOptions;
import com.binance.client.model.enums.CandlestickInterval;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Arrays;
import java.util.List;

/**
 * Class Test: Kiểm chứng "Nhát dao phẫu thuật" vào thư viện Legacy
 */
public class TestMiniTickerIngestor {
    public static final Logger LOG = LoggerFactory.getLogger(TestMiniTickerIngestor.class);

    public static void main(String[] args) {
        new TestMiniTickerIngestor().startTest();
    }

    public void startTest() {
        LOG.info("🚀 Bắt đầu Test Mini Ticker (Thư viện CŨ - Đã vá lỗi Channels.java)");

        List<String> symbolsToTest = Arrays.asList("btcusdt", "ethusdt", "bnbusdt");

        SubscriptionOptions opt = new SubscriptionOptions();
        opt.setAutoReconnect(true);

        SubscriptionClient client = SubscriptionClient.create(opt);

        LOG.info("🔌 Đang kết nối tới Binance WebSocket (Legacy)... Chờ dữ liệu đổ về...");

        try {
            client.subscribeAllCandlestickEvent(symbolsToTest, CandlestickInterval.ONE_MINUTE, (event) -> {
                // 🔥 IN LOG TẤT CẢ DỮ LIỆU NHẬN ĐƯỢC
                String symbol = event.getSymbol().toUpperCase();
                float closePrice = event.getClose().floatValue();

                LOG.info("📥 [DATA NHẬN] Symbol: {} | Giá: {}", symbol, closePrice);

            }, (e) -> {
                LOG.error("❌ Lỗi từ WebSocket Client: ", e);
            });
        } catch (Exception e) {
            LOG.error("❌ Lỗi khi khởi tạo kết nối: ", e);
        }

        // Luồng đếm thời gian
        new Thread(() -> {
            int secondsPassed = 0;
            while (true) {
                try {
                    Thread.sleep(10000); // 10 giây
                    secondsPassed += 10;
                    LOG.info("⏱️ [{}s] TestMiniTickerIngestor (Legacy) vẫn đang sống...", secondsPassed);
                } catch (InterruptedException e) {
                    break;
                }
            }
        }).start();
    }
}