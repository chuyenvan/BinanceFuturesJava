package com.binance.chuyennd.websocket.checkdata;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.stream.Collectors;

public class PriceRealtimeValidator {
    private static final Logger LOG = LoggerFactory.getLogger(PriceRealtimeValidator.class);
    private static final float PRICE_THRESHOLD = 0.002f; // Ngưỡng lệch 0.2%
    public static final String URL_PREMIUM_INDEX = "https://fapi.binance.com/fapi/v1/premiumIndex";

    public static void main(String[] args) {
        new PriceRealtimeValidator().validateRealtimePrice(200);
    }

    public void validateRealtimePrice(int limit) {
        LOG.info("🚀 BẮT ĐẦU ĐỐI SOÁT GIÁ (SỬ DỤNG SCAN ALL PRICE)");

        // 1. Lấy danh sách symbols từ Redis
        List<String> allSymbols = RedisHelper.getInstance()
                .readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS).stream()
                .filter(s -> s.toUpperCase().endsWith("USDT"))
                .filter(s -> !Constants.diedSymbol.contains(s.toUpperCase()))
                .filter(s -> s.toUpperCase().matches("^[A-Z0-9]+$"))
                .limit(limit)
                .collect(Collectors.toList());

        // 2. Lấy dữ liệu MarkPrice từ API Binance
        Map<String, Float> apiPrices = new HashMap<>();
        try {
            String response = HttpRequest.getContentFromUrl(URL_PREMIUM_INDEX);
            List<Map<String, Object>> objects = Utils.gson.fromJson(response, List.class);

            for (Map<String, Object> data : objects) {
                String symbol = data.get("symbol").toString().toUpperCase();
                if (symbol.endsWith("USDT")) {
                    float markPrice = Float.parseFloat(data.get("markPrice").toString());
                    apiPrices.put(symbol, markPrice);
                }
            }
            LOG.info("📥 Đã lấy giá MarkPrice của {} mã từ API.", apiPrices.size());
        } catch (Exception e) {
            LOG.error("❌ Lỗi gọi API premiumIndex: {}", e.getMessage());
            return;
        }

        // 3. 🔥 ĐỐI SOÁT: Lấy toàn bộ giá từ Aerospike bằng hàm tối ưu
        Map<String, Float> asPrices = DataManagerAerospikeFloatSim.getAllPriceRealtimeLegacy(apiPrices.keySet());
        LOG.info("📥 Đã lấy {} bản ghi giá từ Aerospike (Scan).", asPrices.size());

        int totalMatches = 0;
        int totalChecks = 0;

        for (String symbol : allSymbols) {
            String upperS = symbol.toUpperCase();
            Float apiPrice = apiPrices.get(upperS);
            Float asPrice = asPrices.get(upperS); // Lấy trực tiếp từ Map snapshot

            if (apiPrice == null) continue;

            if (asPrice != null) {
                totalChecks++;
                float diff = Math.abs(apiPrice - asPrice) / apiPrice;
                boolean isMatch = diff <= PRICE_THRESHOLD;

                if (isMatch) {
                    totalMatches++;
                } else {
                    LOG.warn("[{}] ❌ Lệch: API(Mark)={} | AS(Realtime)={} | Diff={}%",
                            upperS, apiPrice, asPrice, String.format("%.4f", diff * 100));
                }
            } else {
                LOG.warn("[{}] ⚠️ Aerospike KHÔNG có dữ liệu giá realtime", upperS);
            }
        }

        LOG.info("------------------------------------------------------------------");
        LOG.info("📊 TỔNG KẾT: Khớp {}/{} mã USDT ({}%)",
                totalMatches, totalChecks,
                String.format("%.2f", (totalChecks > 0 ? (totalMatches * 100.0 / totalChecks) : 0)));
    }
}