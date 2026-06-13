package com.binance.chuyennd.trading.monitor;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.client.BinanceP2PTracker;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * TEST IN MÀN HÌNH (TASK-007 B4) — kiểm thử ĐỘC LẬP 3 giá trị mới TRƯỚC khi ghép vào
 * {@link Reporter#buildReport()}: giá BTC (Aerospike 242) + P2P mua/bán thấp nhất.
 * <p>⚠️ KHÔNG gọi {@code buildReport()} để tránh gửi Telegram thật + chạm account live.
 * Chạy: {@code java -cp target/binance-java-sdk-1.2.4.jar com.binance.chuyennd.trading.monitor.ReportExtrasTest}
 */
public class ReportExtrasTest {
    private static final Logger LOG = LoggerFactory.getLogger(ReportExtrasTest.class);

    public static void main(String[] args) {
        LOG.info("===== TASK-007 B4: TEST giá BTC + P2P (in màn hình, KHÔNG ghép report) =====");

        // 1) Giá BTC từ Aerospike 242 (price_realtime) + tuổi dữ liệu.
        try {
            Float btc = DataManagerAerospikeFloatSim.getPriceRealtime("BTCUSDT");
            Long ts = DataManagerAerospikeFloatSim.getPriceRealtimeTs("BTCUSDT");
            if (btc == null) {
                LOG.info("BTC: N/A (không đọc được price_realtime từ 242)");
            } else {
                String age = (ts == null) ? "?" : ((System.currentTimeMillis() - ts) / 1000) + "s";
                LOG.info("BTC: {}$ (cập nhật {} trước)", btc, age);
            }
        } catch (Exception e) {
            LOG.error("❌ Lỗi đọc BTC từ Aerospike: {}", e.getMessage());
        }

        // 2) P2P mua thấp nhất / bán thấp nhất (try-catch RIÊNG, lỗi P2P không làm hỏng phần khác).
        try {
            Double buyLow = BinanceP2PTracker.getLowestPrice("BUY", "5000000");
            Double sellLow = BinanceP2PTracker.getLowestPrice("SELL", "5000000");
            LOG.info("P2P: mua thấp nhất {} | bán thấp nhất {}",
                    buyLow == null ? "N/A" : buyLow,
                    sellLow == null ? "N/A" : sellLow);
        } catch (Exception e) {
            LOG.error("❌ Lỗi đọc P2P: {}", e.getMessage());
        }

        LOG.info("===== HẾT TEST =====");
        // Đóng client Aerospike để JVM thoát gọn.
        try {
            DataManagerAerospikeFloatSim.closeConnection();
        } catch (Exception ignore) {
        }
        Utils.sleep(200L);
        System.exit(0);
    }
}
