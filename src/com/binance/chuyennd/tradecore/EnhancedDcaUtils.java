package com.binance.chuyennd.tradecore; // Hoặc package bạn muốn

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.TechnicalAnalysisUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Map;

/**
 * Lớp này chứa logic DCA nâng cao, kết hợp nhiều yếu tố để quyết định.
 */
public class EnhancedDcaUtils {
    public static final Logger LOG = LoggerFactory.getLogger(EnhancedDcaUtils.class);

    /**
     * Phương thức chính để quyết định có nên DCA hay không.
     *
     * @param recentKlines Danh sách các nến 1 phút gần nhất của symbol đó.
     * @return true nếu nên DCA, false nếu không.
     */
    public static boolean shouldDca(List<KlineObjectSimple> recentKlines) {

        // ================== CÁC THAM SỐ ĐÃ ĐƯỢC TỐI ƯU (TUNED PARAMETERS) ==================
        // Chu kỳ dài hơn giúp tín hiệu ổn định và đáng tin cậy hơn
        final int TREND_PERIOD = 360;      // SMA 360 trên chart 1M (tương đương xu hướng 6 giờ)
        final int RSI_PERIOD = 21;         // RSI dài hơn, ít nhạy cảm hơn với nhiễu
        final int BB_PERIOD = 21;          // Đồng bộ với chu kỳ RSI
        final double BB_STD_DEV = 2.0;       // Độ lệch chuẩn cho Bollinger Bands

        final double RSI_OVERSOLD_LEVEL = 30.0;   // Ngưỡng quá bán

        // --- BỘ LỌC 3: XÁC NHẬN KỸ THUẬT (QUAN TRỌNG NHẤT) ---
        // Kiểm tra dữ liệu đầu vào
        if (recentKlines == null || recentKlines.size() < TREND_PERIOD) {
            try {
                LOG.info("Should DCA not enough data ticker: {}", recentKlines.size());
            } catch (Exception e) {
                e.printStackTrace();
            }
            return false; // Cần đủ dữ liệu cho chu kỳ dài nhất
        }

        // Tính toán các chỉ báo
        double rsi = TechnicalAnalysisUtils.calculateRSI(recentKlines, RSI_PERIOD);
        Map<String, Double> bands = TechnicalAnalysisUtils.calculateBollingerBands(recentKlines, BB_PERIOD, BB_STD_DEV);

        // Nếu không đủ dữ liệu để tính chỉ báo, bỏ qua
        if (rsi < 0 || bands == null) {
            return false;
        }

        // Lấy giá hiện tại và dải bollinger dưới
        double currentPrice = recentKlines.get(recentKlines.size() - 1).priceClose;
        double lowerBand = bands.get("LOWER");

        // Điều kiện "VÀNG": Giá bị đẩy ra ngoài dải BB VÀ RSI xác nhận quá bán
        boolean isOverextended = (currentPrice <= lowerBand);
        boolean isOversold = (rsi <= RSI_OVERSOLD_LEVEL);

        if (isOverextended && isOversold) {
            // Thỏa mãn tất cả điều kiện -> thực hiện DCA
            return true;
        }

        // Nếu không thỏa mãn, không DCA
        return false;
    }
}