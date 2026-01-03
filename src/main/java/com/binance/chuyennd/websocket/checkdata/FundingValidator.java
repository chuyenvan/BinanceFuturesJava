package com.binance.chuyennd.websocket.checkdata;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.stream.Collectors;

public class FundingValidator {
    private static final Logger LOG = LoggerFactory.getLogger(FundingValidator.class);
    public static final String URL_PREMIUM_INDEX = "https://fapi.binance.com/fapi/v1/premiumIndex";

    public static void main(String[] args) {
        FundingValidator validator = new FundingValidator();
        // 1. Đối soát dữ liệu
        validator.validateFunding(200);
        // 2. In mẫu dữ liệu lịch sử của 5 mã
        validator.printSampleHistoricalFunding(5);
    }

    public void validateFunding(int limit) {
        LOG.info("🚀 BẮT ĐẦU ĐỐI SOÁT FUNDING RATE (CHỈ CẶP USDT)");

        List<String> allSymbols = RedisHelper.getInstance()
                .readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS).stream()
                .filter(s -> s.toUpperCase().endsWith("USDT"))
                .filter(s -> !Constants.diedSymbol.contains(s.toUpperCase()))
                .filter(s -> s.toUpperCase().matches("^[A-Z0-9]+$"))
                .limit(limit)
                .collect(Collectors.toList());

        Map<String, Double> apiFundingRates = new HashMap<>();
        try {
            String response = HttpRequest.getContentFromUrl(URL_PREMIUM_INDEX);
            List<Map<String, Object>> objects = Utils.gson.fromJson(response, List.class);

            for (Map<String, Object> data : objects) {
                String symbol = data.get("symbol").toString().toUpperCase();
                if (symbol.endsWith("USDT")) {
                    double lastFundingRate = Double.parseDouble(data.get("lastFundingRate").toString());
                    apiFundingRates.put(symbol, lastFundingRate);
                }
            }
        } catch (Exception e) {
            LOG.error("❌ Lỗi gọi API premiumIndex: {}", e.getMessage());
            return;
        }

        int totalMatches = 0;
        int totalChecks = 0;

        for (String symbol : allSymbols) {
            String upperS = symbol.toUpperCase();
            Double apiRate = apiFundingRates.get(upperS);
            if (apiRate == null) continue;

            Map<Long, Double> asFundingMap = DataManagerAerospikeFloatSim.getFundingMap(upperS);

            if (asFundingMap != null && !asFundingMap.isEmpty()) {
                totalChecks++;
                Long latestTs = Collections.max(asFundingMap.keySet());
                Double asRate = asFundingMap.get(latestTs);

                boolean isMatch = Math.abs(apiRate - asRate) < 0.00000001;
                if (isMatch) totalMatches++;
                else {
                    LOG.warn("[{}] ❌ Lệch: API={} | AS={} (Kỳ: {})",
                            upperS, apiRate, asRate, Utils.normalizeDateYYYYMMDDHHmm(latestTs));
                }
            }
        }
        LOG.info("📊 TỔNG KẾT: Khớp {}/{} mã USDT ({}%)",
                totalMatches, totalChecks, String.format("%.2f", (totalChecks > 0 ? (totalMatches * 100.0 / totalChecks) : 0)));
    }

    /**
     * In toàn bộ lịch sử Funding đang có trong Aerospike của N mã bất kỳ
     */
    public void printSampleHistoricalFunding(int sampleLimit) {
        LOG.info("📂 IN MẪU DỮ LIỆU LỊCH SỬ FUNDING TRONG AEROSPIKE");

        List<String> symbols = RedisHelper.getInstance()
                .readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS).stream()
                .filter(s -> s.toUpperCase().endsWith("USDT"))
                .limit(sampleLimit)
                .collect(Collectors.toList());

        for (String symbol : symbols) {
            String upperS = symbol.toUpperCase();
            Map<Long, Double> asFundingMap = DataManagerAerospikeFloatSim.getFundingMap(upperS);

            LOG.info("--------------------------------------------------");
            LOG.info("📝 Symbol: {} (Số kỳ ghi nhận: {})", upperS, asFundingMap.size());

            if (asFundingMap.isEmpty()) {
                LOG.warn("   ⚠️ Không có dữ liệu.");
                continue;
            }

            // Sắp xếp theo thời gian tăng dần để in
            TreeMap<Long, Double> sortedMap = new TreeMap<>(asFundingMap);

                LOG.info("   [🕒 {}] Rate: {}", Utils.normalizeDateYYYYMMDDHHmm(sortedMap.firstKey()),
                        String.format("%.8f", sortedMap.firstEntry().getValue()));

        }
        LOG.info("--------------------------------------------------");
    }
}