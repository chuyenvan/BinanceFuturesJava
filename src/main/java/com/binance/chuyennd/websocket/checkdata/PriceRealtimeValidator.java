package com.binance.chuyennd.websocket.checkdata;

import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.stream.Collectors;

public class PriceRealtimeValidator {
    private static final Logger LOG = LoggerFactory.getLogger(PriceRealtimeValidator.class);
    private static final double PRICE_THRESHOLD = 0.002; // Ngưỡng lệch 0.05%
    public static final String URL_PREMIUM_INDEX = "https://fapi.binance.com/fapi/v1/premiumIndex";

    public static void main(String[] args) {
        // Kiểm tra 200 mã USDT gần nhất
        new PriceRealtimeValidator().validateRealtimePrice(200);
    }

    public void validateRealtimePrice(int limit) {
        LOG.info("🚀 BẮT ĐẦU ĐỐI SOÁT GIÁ (CHỈ CẶP USDT)");

        // 1. Lấy danh sách symbols từ Redis và lọc CHẶT CHẼ cặp USDT
        List<String> allSymbols = RedisHelper.getInstance()
                .readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS).stream()
                .filter(s -> s.toUpperCase().endsWith("USDT")) // 🔥 Chỉ lấy USDT
                .filter(s -> !Constants.diedSymbol.contains(s.toUpperCase()))
                .filter(s -> s.toUpperCase().matches("^[A-Z0-9]+$")) // Loại bỏ ký tự lạ
                .limit(limit)
                .collect(Collectors.toList());

        Map<String, Double> apiPrices = new HashMap<>();
        try {
            // 2. Lấy dữ liệu MarkPrice từ API Binance
            String response = HttpRequest.getContentFromUrl(URL_PREMIUM_INDEX);
            List<Map<String, Object>> objects = Utils.gson.fromJson(response, List.class);

            for (Map<String, Object> data : objects) {
                String symbol = data.get("symbol").toString().toUpperCase();
                // 🔥 Chỉ map các cặp USDT từ API vào danh sách đối soát
                if (symbol.endsWith("USDT")) {
                    double markPrice = Double.parseDouble(data.get("markPrice").toString());
                    apiPrices.put(symbol, markPrice);
                }
            }
            LOG.info("📥 Đã lấy giá MarkPrice của {} mã USDT từ API.", apiPrices.size());
        } catch (Exception e) {
            LOG.error("❌ Lỗi gọi API premiumIndex: {}", e.getMessage());
            return;
        }

        int totalMatches = 0;
        int totalChecks = 0;

        // 3. Đối soát với Aerospike
        for (String symbol : allSymbols) {
            String upperS = symbol.toUpperCase();
            Double apiPrice = apiPrices.get(upperS);

            if (apiPrice == null) continue;

            // Đọc giá từ Aerospike qua DataManager
            Double asPrice = null;
            try {
                // Key trong AS luôn là UPPERCASE (ví dụ: BTCUSDT)
                Key key = new Key(Configs.AEROSPIKE_NAMESPACE, "price_realtime", upperS);
                Record record = DataManagerAerospikeFloatSim.getClient().get(null, key);
                if (record != null) {
                    asPrice = record.getDouble("price");
                }
            } catch (Exception e) {}

            if (asPrice != null) {
                totalChecks++;
                double diff = Math.abs(apiPrice - asPrice) / apiPrice;
                boolean isMatch = diff <= PRICE_THRESHOLD;

                if (isMatch) {
                    totalMatches++;
                } else {
                    LOG.warn("[{}] ❌ Lệch: API(Mark)={} | AS(Realtime)={} | Diff={}%",
                            upperS, apiPrice, asPrice, String.format("%.4f", diff * 100));
                }
            } else {
                // Chỉ báo lỗi nếu đó thực sự là cặp USDT mà AS không có dữ liệu
                LOG.warn("[{}] ⚠️ Aerospike KHÔNG có dữ liệu giá realtime", upperS);
            }
        }

        LOG.info("------------------------------------------------------------------");
        LOG.info("📊 TỔNG KẾT: Khớp {}/{} mã USDT ({}%)",
                totalMatches, totalChecks, String.format("%.2f", (totalChecks > 0 ? (totalMatches * 100.0 / totalChecks) : 0)));
    }
}