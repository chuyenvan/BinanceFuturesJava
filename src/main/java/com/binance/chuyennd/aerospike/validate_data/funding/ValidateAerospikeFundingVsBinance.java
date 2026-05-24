package com.binance.chuyennd.aerospike.validate_data.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.client.model.market.FundingRate;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.stream.Collectors;

public class ValidateAerospikeFundingVsBinance {
    public static final Logger LOG = LoggerFactory.getLogger(ValidateAerospikeFundingVsBinance.class);

    public static void main(String[] args) throws Exception {
        // Test 5 coin ngẫu nhiên, check từ đầu năm 2025
        new ValidateAerospikeFundingVsBinance().runValidation(5, "20250101 00:00");
    }

    public void runValidation(int numSymbols, String startDateStr) throws Exception {
        LOG.info("🚀 BẮT ĐẦU ĐỐI SOÁT FUNDING RATE: AEROSPIKE vs BINANCE API...");

        long startTime = Utils.sdfFileHour.parse(startDateStr).getTime();

        // 1. Lấy random N coin
        List<String> allSymbols = RedisHelper.getInstance()
                .readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS).stream()
                .filter(s -> !Constants.diedSymbol.contains(s.toUpperCase()) && StringUtils.endsWithIgnoreCase(s, "USDT"))
                .collect(Collectors.toList());

        Collections.shuffle(allSymbols);
        List<String> targetSymbols = allSymbols.subList(0, Math.min(numSymbols, allSymbols.size()));

        LOG.info("🎯 Danh sách coin test: {}", targetSymbols);

        int totalChecks = 0;
        int totalMissing = 0;
        int totalMismatch = 0;

        for (String symbol : targetSymbols) {
            LOG.info("\n========================================================");
            LOG.info("🔍 KIỂM TRA MÃ: {}", symbol);

            // 2. Kéo dữ liệu từ Binance API
            // API getFundingFeeWithStartTime của bác trả về map: <HourTimestamp, FundingRate>
            TreeMap<Long, FundingRate> apiData = TickerFuturesHelper.getFundingFeeWithStartTime(symbol, startTime);

            if (apiData == null || apiData.isEmpty()) {
                LOG.warn("   ⚠️ Binance API không trả về dữ liệu Funding cho {} từ mốc {}", symbol, startDateStr);
                continue;
            }

            // 3. Kéo dữ liệu từ Aerospike DB
            TreeMap<Long, Float> asData = DataManagerAerospikeFloatSim.getFundingMap(symbol);

            LOG.info("   -> API Binance trả về {} kỳ Funding.", apiData.size());
            LOG.info("   -> Aerospike đang lưu tổng cộng {} kỳ Funding.", asData == null ? 0 : asData.size());

            if (asData == null || asData.isEmpty()) {
                LOG.error("   ❌ Aerospike HOÀN TOÀN TRỐNG DỮ LIỆU Funding cho mã này!");
                totalMissing += apiData.size();
                totalChecks += apiData.size();
                continue;
            }

            // 4. Đối soát 1:1
            int matchInSymbol = 0;
            for (Map.Entry<Long, FundingRate> entry : apiData.entrySet()) {
                long targetTs = entry.getKey(); // Đây là timestamp của kỳ funding (thường chẵn 8 tiếng)
                float apiRate = entry.getValue().getFundingRate().floatValue();

                totalChecks++;

                // Dùng floorEntry (như logic trong FundingFeeManager của bác) để tìm kỳ gần nhất
                Map.Entry<Long, Float> asEntry = asData.floorEntry(targetTs);

                if (asEntry == null) {
                    LOG.error("   ❌ THIẾU DATA: Aerospike không có kỳ Funding nào trước mốc {}", Utils.normalizeDateYYYYMMDDHHmm(targetTs));
                    totalMissing++;
                } else {
                    float asRate = asEntry.getValue();

                    // Khoảng cách giữa mốc của API và mốc tìm thấy trong DB
                    long timeDiff = Math.abs(targetTs - asEntry.getKey());

                    // Nếu mốc thời gian lệch quá 24h, coi như thiếu data tại khu vực đó
                    if (timeDiff > 24 * 3600 * 1000L) {
                        LOG.error("   ❌ THIẾU DATA CỤC BỘ: Record gần nhất trong AS cách đây tận {} giờ (Mốc test: {})",
                                (timeDiff / 3600000L), Utils.normalizeDateYYYYMMDDHHmm(targetTs));
                        totalMissing++;
                    } else {
                        // So sánh giá trị với sai số nhỏ
                        float diff = Math.abs(apiRate - asRate);
                        if (diff > 0.0000001f) {
                            LOG.error("   ❌ LỆCH GIÁ TRỊ [{}]: API = {} | AS = {}", Utils.normalizeDateYYYYMMDDHHmm(targetTs), apiRate, asRate);
                            totalMismatch++;
                        } else {
                            matchInSymbol++;
                        }
                    }
                }
            }
            LOG.info("   ✅ {}: Khớp {}/{} kỳ.", symbol, matchInSymbol, apiData.size());
            Thread.sleep(500); // Nghỉ nhẹ tránh bị Binance chặn IP
        }

        LOG.info("\n========================================================");
        LOG.info("📊 TỔNG KẾT ĐỐI SOÁT FUNDING FEE");
        LOG.info("Tổng số kỳ đã kiểm tra : {}", totalChecks);
        LOG.info("Số kỳ KHỚP 100%        : {}", (totalChecks - totalMissing - totalMismatch));
        LOG.info("Số kỳ BỊ THIẾU TRONG DB: {}", totalMissing);
        LOG.info("Số kỳ BỊ LỆCH GIÁ TRỊ  : {}", totalMismatch);
        LOG.info("========================================================");
    }
}