package com.binance.chuyennd.bigchange.test;

import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.client.SubscriptionClient;
import com.binance.client.SubscriptionOptions;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.CandlestickInterval;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

public class SymbolValidator {

    private static final Logger LOG = LoggerFactory.getLogger(SymbolValidator.class);

    // Thời gian (giây) để chờ một tin nhắn trước khi coi là TIMEOUT
    // Nến 1 phút thường gửi cập nhật mỗi 2-3 giây, vì vậy 30 giây là rất an toàn.
    private static final int TIMEOUT_SECONDS = 30;

    /**
     * Tải danh sách symbol của bạn tại đây
     * @return List<String> danh sách symbol
     */
    private static List<String> getSymbolsToTest() {
        List<String> symbols = new ArrayList<>();
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS)) {
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            symbols.add(symbol.toLowerCase());
        }

        return symbols;
    }

    /**
     * Phương thức Main để chạy kiểm tra
     */
    public static void main(String[] args) {
        List<String> symbols = getSymbolsToTest();
        List<String> faultySymbols = validateSymbols(symbols);

        LOG.info("=====================================================");
        LOG.info("KIỂM TRA HOÀN TẤT. TỔNG SỐ SYMBOL LỖI: {}", faultySymbols.size());
        LOG.info("{}", faultySymbols);
        LOG.info("=====================================================");
    }

    /**
     * Lặp qua từng symbol và kiểm tra
     * @param symbols Danh sách symbol
     * @return Danh sách các symbol bị lỗi
     */
    public static List<String> validateSymbols(List<String> symbols) {
        LOG.info("Bắt đầu kiểm tra {} symbol...", symbols.size());
        List<String> faultySymbols = new ArrayList<>();

        for (String symbol : symbols) {

            final CountDownLatch latch = new CountDownLatch(1);
            final AtomicBoolean receivedSuccess = new AtomicBoolean(false);
            final AtomicBoolean receivedError = new AtomicBoolean(false);

            // *** QUAN TRỌNG ***
            // Chúng ta tạo một client MỚI cho mỗi symbol.
            // Đây là cách duy nhất để đảm bảo 100% rằng lỗi kết nối
            // là do symbol này gây ra, chứ không phải do lỗi còn sót lại từ symbol trước.
            SubscriptionOptions options = new SubscriptionOptions();
            options.setUri("https://fstream.binance.com"); // Đảm bảo đây là máy chủ FUTURES
            SubscriptionClient client = SubscriptionClient.create(options);

            try {
                LOG.info("[Test] Đang đăng ký: {}", symbol);

                // Sử dụng phương thức cho 1 symbol (singular),
                // không dùng "subscribeAllCandlestickEvent" (plural)
                client.subscribeCandlestickEvent(
                        symbol,
                        CandlestickInterval.ONE_MINUTE,
                        (event) -> {
                            // === THÀNH CÔNG ===
                            LOG.info("[Test] OK: Đã nhận được dữ liệu cho {}", symbol);
                            receivedSuccess.set(true);
                            latch.countDown(); // Báo cho thread main "Tôi xong rồi"
                        },
                        (error) -> {
                            // === LỖI ===
                            // Thư viện đã phát hiện lỗi (ví dụ: symbol không tồn tại)
                            LOG.warn("[Test] LỖI: Callback báo lỗi cho {}: {}", symbol, error.getMessage());
                            receivedError.set(true);
                            latch.countDown(); // Báo cho thread main "Tôi xong rồi"
                        }
                );

                // Thread Main sẽ đợi ở đây tối đa TIMEOUT_SECONDS
                boolean signalReceived = latch.await(TIMEOUT_SECONDS, TimeUnit.SECONDS);

                // Phân tích kết quả
                if (signalReceived && receivedSuccess.get()) {
                    // 1. Thành công: Nhận được tin nhắn
                    LOG.info("[Test] KẾT QUẢ: {} HOẠT ĐỘNG.", symbol);
                } else if (signalReceived && receivedError.get()) {
                    // 2. Lỗi Callback: Nhận được lỗi (ví dụ: invalid symbol)
                    LOG.warn("[Test] KẾT QUẢ: {} BỊ LỖI (Callback error).", symbol);
                    faultySymbols.add(symbol);
                } else if (!signalReceived) {
                    // 3. Hết giờ: Không nhận được gì (tin nhắn hay lỗi)
                    LOG.warn("[Test] KẾT QUẢ: {} BỊ TIMEOUT (Không có sự kiện trong {}s).", symbol, TIMEOUT_SECONDS);
                    faultySymbols.add(symbol);
                }

            } catch (InterruptedException e) {
                LOG.error("Tiến trình kiểm tra bị gián đoạn", e);
                Thread.currentThread().interrupt();
                break; // Dừng vòng lặp for
            } catch (Exception e) {
                // Lỗi này xảy ra nếu lệnh subscribe bị lỗi ngay lập tức
                LOG.error("[Test] KẾT QUẢ: {} BỊ LỖI (Ngoại lệ khi đăng ký: {})", symbol, e.getMessage());
                faultySymbols.add(symbol);
            } finally {
                // *** CỰC KỲ QUAN TRỌNG ***
                // Dọn dẹp kết nối cho client này trước khi đi đến symbol tiếp theo.
                client.unsubscribeAll();
                LOG.info("[Test] Đã đóng kết nối cho: {}", symbol);
            }

            // Thêm một độ trễ nhỏ để tránh spam API của Binance
            try {
                Thread.sleep(500); // 0.5 giây
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        } // kết thúc vòng lặp for

        return faultySymbols;
    }
}