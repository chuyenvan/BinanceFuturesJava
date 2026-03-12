package com.binance.chuyennd.websocket.checkdata;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.stream.Collectors;

public class AdvancedDataValidator {
    private static final Logger LOG = LoggerFactory.getLogger(AdvancedDataValidator.class);

    public static void main(String[] args) {
        try {
            // Thiết lập mốc bắt đầu: 2026-01-01 22:00:00
            String startTimeStr = "20260102 11:00";
            long startTimestamp = Utils.sdfFileHour.parse(startTimeStr).getTime();

            AdvancedDataValidator validator = new AdvancedDataValidator();
            validator.runDeepValidation(startTimestamp, 10, 100);
        } catch (Exception e) {
            LOG.error("Lỗi khởi chạy Validator: {}", e.getMessage());
        }
    }

    public void runDeepValidation(long startTs, int durationMinutes, int symbolLimit) {
        LOG.info("🚀 BẮT ĐẦU ĐỐI SOÁT CHUYÊN SÂU");
        LOG.info("Bắt đầu: {} | Số phút: {} | Số lượng mã: {}",
                Utils.normalizeDateYYYYMMDDHHmm(startTs), durationMinutes, symbolLimit);

        // 1. Lấy danh sách 100 symbols từ Redis (Giống logic Ingestor)
        List<String> allSymbols = RedisHelper.getInstance()
                .readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS).stream()
                .filter(s -> !Constants.diedSymbol.contains(s) && StringUtils.endsWithIgnoreCase(s, "usdt"))
                .limit(symbolLimit)
                .collect(Collectors.toList());

        float priceThreshold = 0.00001f; // 0.05%
        int totalChecks = 0;
        int totalMatches = 0;
        Map<Long, Integer> minuteStats = new HashMap<>();

        for (int i = 0; i < durationMinutes; i++) {
            long currentMinute = startTs + (i * Utils.TIME_MINUTE);
            String minuteStr = Utils.normalizeDateYYYYMMDDHHmm(currentMinute);

            // 2. Lấy Snapshot toàn thị trường từ Aerospike cho phút này
            TreeMap<Long, Map<String, KlineObjectSimple>> asSnapshot =
                    DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentMinute);
            Map<String, KlineObjectSimple> asMap = asSnapshot.get(currentMinute);

            if (asMap == null || asMap.isEmpty()) {
                LOG.error("[{}] ❌ Aerospike KHÔNG có dữ liệu!", minuteStr);
                continue;
            }

            int minuteMatches = 0;
            for (String fullSymbol : allSymbols) {
                try {
                    // Lấy dữ liệu chuẩn từ API
                    List<KlineObjectSimple> apiData = TickerFuturesHelper.getTickerSimpleWithStartTime(
                            fullSymbol, Constants.INTERVAL_1M, currentMinute);

                    if (apiData == null || apiData.isEmpty()) continue;
                    KlineObjectSimple apiKline = apiData.get(0);

                    // Tìm key trong Aerospike (thử full "BTCUSDT" hoặc short "BTC")
                    String shortSymbol = fullSymbol.replace("USDT", "");
                    KlineObjectSimple asKline = asMap.getOrDefault(fullSymbol, asMap.get(shortSymbol));

                    if (asKline == null) continue;

                    totalChecks++;

                    // So sánh giá (Ngưỡng 0.05%)
                    float priceDiff = Math.abs(apiKline.priceClose - asKline.priceClose) / apiKline.priceClose;

                    // So sánh Volume (Ngưỡng 1% do sai số float và thời điểm chốt nến)
                    float volDiff = Math.abs(apiKline.totalUsdt - asKline.totalUsdt) / (apiKline.totalUsdt + 1);

                    if (priceDiff <= priceThreshold) {
                        minuteMatches++;
                        totalMatches++;
                    } else {
                        LOG.warn("[{}] ❌ {} Lệch giá: API={} vs AS={}",
                                minuteStr, fullSymbol, apiKline.priceClose, asKline.priceClose);
                    }
                } catch (Exception e) {
                    LOG.error("Lỗi đối soát {}: {}", fullSymbol, e.getMessage());
                }
            }
            minuteStats.put(currentMinute, minuteMatches);
            LOG.info("[{}] Done: Khớp {}/{} mã.", minuteStr, minuteMatches, allSymbols.size());
        }

        // 3. Báo cáo tổng kết
        printSummary(totalChecks, totalMatches, minuteStats, allSymbols.size());
    }

    private void printSummary(int total, int matches, Map<Long, Integer> stats, int symbolsPerMin) {
        LOG.info("==================================================================");
        LOG.info("📊 BÁO CÁO TỔNG KẾT ĐỐI SOÁT");
        LOG.info("Tỉ lệ khớp tổng quát: {}/{} ({}%)", matches, total, String.format("%.2f", (matches * 100.0 / total)));

        stats.forEach((time, count) -> {
            LOG.info(" - {}: Khớp {}%", Utils.normalizeDateYYYYMMDDHHmm(time), String.format("%.1f", (count * 100.0 / symbolsPerMin)));
        });

        if (matches == total) {
            LOG.info("✅ DỮ LIỆU HOÀN HẢO (Với ngưỡng sai số 0.05%)");
        } else {
            LOG.warn("⚠️ CÓ SAI LỆCH: Cần kiểm tra lại logic QuoteAssetVolume trong Ingestor.");
        }
        LOG.info("==================================================================");
    }
}