package com.binance.chuyennd.client;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class BinanceP2PTracker {
    private static final Logger LOG = LoggerFactory.getLogger(BinanceP2PTracker.class);

    private static final String BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search";
    private static final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();

    public static void main(String[] args) {
        LOG.info("🚀 KHỞI ĐỘNG TRACKER P2P BINANCE (VND > 5M) - Quét 10 phút/lần");

        ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();

        scheduler.scheduleAtFixedRate(() -> {
            try {
                LOG.info("=========================================================================================================================================");
                fetchP2PBestPrice("BUY", "5000000");  // Mua USDT vào
                LOG.info("-----------------------------------------------------------------------------------------------------------------------------------------");
                fetchP2PBestPrice("SELL", "5000000"); // Bán USDT ra
            } catch (Exception e) {
                LOG.error("❌ Lỗi khi lấy dữ liệu P2P: ", e);
            }
        }, 0, 10, TimeUnit.MINUTES);
    }

    private static void fetchP2PBestPrice(String tradeType, String transAmount) {
        try {
            JsonObject payload = new JsonObject();
            payload.addProperty("fiat", "VND");
            payload.addProperty("page", 1);
            payload.addProperty("rows", 10); // Lấy TOP 10
            payload.addProperty("tradeType", tradeType);
            payload.addProperty("asset", "USDT");
            payload.addProperty("transAmount", transAmount);
            payload.add("countries", new JsonArray());
            payload.addProperty("proMerchantAds", false);
            payload.addProperty("shieldMerchantAds", false);
            payload.addProperty("publisherType", (String) null);

            JsonArray classifies = new JsonArray();
            classifies.add("mass");
            classifies.add("profession");
            payload.add("classifies", classifies);

            String requestBody = payload.toString();

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(BINANCE_P2P_URL))
                    .header("Content-Type", "application/json")
                    .header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                    .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                JsonObject jsonObj = JsonParser.parseString(response.body()).getAsJsonObject();
                if (jsonObj.get("code").getAsString().equals("000000")) {
                    JsonArray dataArr = jsonObj.getAsJsonArray("data");

                    if (dataArr.size() > 0) {
                        String typeStr = tradeType.equals("BUY") ? "🟢 [MUA USDT VÀO (Lọc giá Thấp -> Cao)]" : "🔴 [BÁN USDT RA (Lọc giá Cao -> Thấp)]";
                        LOG.info(typeStr);

                        int limit = Math.min(10, dataArr.size());
                        for (int i = 0; i < limit; i++) {
                            JsonObject item = dataArr.get(i).getAsJsonObject();
                            JsonObject adv = item.getAsJsonObject("adv");
                            JsonObject advertiser = item.getAsJsonObject("advertiser");

                            String price = adv.get("price").getAsString();
                            String merchantName = advertiser.get("nickName").getAsString();

                            // 🔥 Lấy thông số Tín nhiệm (Uy tín)
                            int monthOrderCount = advertiser.has("monthOrderCount") && !advertiser.get("monthOrderCount").isJsonNull()
                                    ? advertiser.get("monthOrderCount").getAsInt() : 0;

                            double monthFinishRate = advertiser.has("monthFinishRate") && !advertiser.get("monthFinishRate").isJsonNull()
                                    ? advertiser.get("monthFinishRate").getAsDouble() * 100 : 0.0;

                            // Đánh dấu VIP nếu > 1000 lệnh và Tỉ lệ 100%
                            String vipTag = (monthOrderCount > 1000 && monthFinishRate >= 99.9) ? "⭐ VIP" : "     ";
                            String statsStr = String.format("%s | %4d lệnh | %6.2f%%", vipTag, monthOrderCount, monthFinishRate);

                            // Các thông số chi tiết khác
                            String minLimit = adv.get("minSingleTransAmount").getAsString();
                            String maxLimit = adv.get("maxSingleTransAmount").getAsString();
                            String tradableQty = adv.get("tradableQuantity").getAsString();

                            JsonArray methodsArr = adv.getAsJsonArray("tradeMethods");
                            List<String> methods = new ArrayList<>();
                            for (JsonElement m : methodsArr) {
                                methods.add(m.getAsJsonObject().get("identifier").getAsString());
                            }
                            String paymentStr = String.join(", ", methods);

                            // In ra log console (Căn lề chuẩn chỉ)
                            LOG.info(String.format("  #%02d | Giá: %s | %-32s | Merchant: %-18s | SL: %-10s | Limit: %s - %s | Pay: %s",
                                    (i + 1), price, statsStr, merchantName, tradableQty, minLimit, maxLimit, paymentStr));
                        }
                    } else {
                        LOG.warn("⚠️ Không tìm thấy quảng cáo {} nào phù hợp.", tradeType);
                    }
                } else {
                    LOG.error("❌ Binance trả về lỗi: {}", jsonObj.get("message").getAsString());
                }
            } else {
                LOG.error("❌ HTTP Lỗi code: {}", response.statusCode());
            }
        } catch (Exception e) {
            LOG.error("❌ Exception: ", e);
        }
    }
}