package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Cổng liêm chính backtest. Gọi assertProductionGrade() ở đầu mọi lần chạy
 * backtest "thật" (HPO, WFO, validation). Nó đảm bảo không bao giờ vô tình
 * đo lợi nhuận trong điều kiện look-ahead hoặc zero-slippage.
 *
 * Chỉ được phép tắt guard khi CỐ Ý chạy đối chứng (so trước/sau khi bịt) —
 * lúc đó dùng allowDiagnostic=true và hệ thống sẽ log cảnh báo to.
 */
public final class BacktestIntegrityGuard {

    private static final Logger LOG = LoggerFactory.getLogger(BacktestIntegrityGuard.class);

    private BacktestIntegrityGuard() {}

    /** Gọi ở đầu mỗi backtest thật. Ném lỗi nếu cấu hình không "production-grade". */
    public static void assertProductionGrade() {
        check(false);
    }

    /** Dùng khi cố ý chạy đối chứng look-ahead/slippage. */
    public static void assertProductionGrade(boolean allowDiagnostic) {
        check(allowDiagnostic);
    }

    private static void check(boolean allowDiagnostic) {
        StringBuilder violations = new StringBuilder();

        if (!Configs.BLOCK_INTRABAR_LOOKAHEAD) {
            violations.append("\n  - BLOCK_INTRABAR_LOOKAHEAD=false (đang cho phép look-ahead nội-nến!)");
        }
        if (!Configs.APPLY_SLIPPAGE) {
            violations.append("\n  - APPLY_SLIPPAGE=false (không tính trượt giá!)");
        }
        if (Configs.APPLY_SLIPPAGE && Configs.SLIPPAGE_RATE <= 0f) {
            violations.append("\n  - SLIPPAGE_RATE<=0 (slippage bật nhưng bằng 0!)");
        }
        if (Configs.RATE_FEE <= 0f) {
            violations.append("\n  - RATE_FEE<=0 (không tính phí sàn!)");
        }

        if (violations.length() == 0) {
            return; // sạch
        }

        String msg = "⛔ BACKTEST INTEGRITY VIOLATION:" + violations
                + "\n  => Kết quả sẽ LẠC QUAN GIẢ. Sửa cấu hình hoặc dùng chế độ diagnostic.";

        if (allowDiagnostic) {
            LOG.warn("⚠️⚠️⚠️ DIAGNOSTIC MODE — guard đang bị nới lỏng CÓ CHỦ Ý: {}", msg);
        } else {
            throw new IllegalStateException(msg);
        }
    }
}