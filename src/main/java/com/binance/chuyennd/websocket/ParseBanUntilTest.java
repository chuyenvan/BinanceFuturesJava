package com.binance.chuyennd.websocket;

import com.binance.chuyennd.utils.BinanceRestGuard;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Unit test standalone (chạy main) cho {@link BinanceRestGuard#parseBanUntilMs(String)}.
 * <p>Không có JUnit trong repo (xem CLAUDE.md) nên test = class main() tự kiểm + log kết quả.
 * Chạy: {@code java -cp target/binance-java-sdk-1.2.4.jar com.binance.chuyennd.websocket.ParseBanUntilTest}
 */
public class ParseBanUntilTest {
    private static final Logger LOG = LoggerFactory.getLogger(ParseBanUntilTest.class);

    private static int pass = 0;
    private static int fail = 0;

    public static void main(String[] args) {
        // 1) Body ban THẬT (mẫu từ log): phải lấy đúng mốc ms-epoch.
        check("ban-with-ts",
                "{\"code\":-1003,\"msg\":\"Way too many requests; IP(103.157.218.242) banned until 1781262464241. Please use the websocket for live updates to avoid bans.\"}",
                1781262464241L);

        // 2) Body mảng giá bình thường → KHÔNG ban → 0.
        check("normal-price-array",
                "[{\"symbol\":\"BTCUSDT\",\"price\":\"60000.10\"},{\"symbol\":\"ETHUSDT\",\"price\":\"3000.5\"}]",
                0L);

        // 3) Có -1003 nhưng KHÔNG kèm số → fallback now + 5' (chấp nhận sai số ±2s khi chạy).
        long before = System.currentTimeMillis();
        long got = BinanceRestGuard.parseBanUntilMs("{\"code\":-1003,\"msg\":\"Too many requests.\"}");
        long lo = before + BinanceRestGuard.DEFAULT_COOLDOWN_MS - 2000;
        long hi = System.currentTimeMillis() + BinanceRestGuard.DEFAULT_COOLDOWN_MS + 2000;
        if (got >= lo && got <= hi) {
            pass++;
            LOG.info("✅ [-1003-no-number] PASS got={} (kỳ vọng ~ now+5')", got);
        } else {
            fail++;
            LOG.error("❌ [-1003-no-number] FAIL got={} (ngoài [{}..{}])", got, lo, hi);
        }

        // 4) Bonus: null/blank → 0; và KHÔNG bắt nhầm số trong IP khi không có "banned until".
        check("null", null, 0L);
        check("blank", "   ", 0L);
        check("ip-no-ban", "{\"msg\":\"IP 103.157.218.242 ok\"}", 0L);

        LOG.info("================ KẾT QUẢ: pass={} fail={} ================", pass, fail);
        if (fail > 0) {
            throw new AssertionError("parseBanUntilMs có " + fail + " case FAIL");
        }
    }

    private static void check(String name, String body, long expected) {
        long got = BinanceRestGuard.parseBanUntilMs(body);
        if (got == expected) {
            pass++;
            LOG.info("✅ [{}] PASS got={}", name, got);
        } else {
            fail++;
            LOG.error("❌ [{}] FAIL got={} expected={}", name, got, expected);
        }
    }
}
