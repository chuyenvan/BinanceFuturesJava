package com.binance.chuyennd.client;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class P2PTelegramNotifier {
    private static final Logger LOG = LoggerFactory.getLogger(P2PTelegramNotifier.class);

    // =====================================================================
    // ⚙️ CẤU HÌNH TELEGRAM API (CHÍNH CHỦ - KHÔNG BAO GIỜ CHẾT)
    // =====================================================================
    // 1. Điền Token lấy từ @BotFather
    private static final String TELEGRAM_BOT_TOKEN = "6158571844:AAHgemRZAWCFARpkyiZkpc9iTT4hEKMtUvw";

    // 2. Điền ID lấy từ @userinfobot
    private static final String TELEGRAM_CHAT_ID = "6548680563";

    private static final String BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search";
    private static final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();

    public static void main(String[] args) {
        LOG.info("🚀 KHỞI ĐỘNG TIẾN TRÌNH QUÉT VIP P2P & BÁO CÁO TELEGRAM (10 phút/lần)");

        ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();

        scheduler.scheduleAtFixedRate(() -> {
            try {
                LOG.info("🔍 Đang quét thị trường P2P...");

                String buyData = getTop3VipMerchants("BUY", "5000000");
                String sellData = getTop3VipMerchants("SELL", "5000000");

                StringBuilder messageBuilder = new StringBuilder();
                messageBuilder.append("🚨 *BÁO CÁO P2P BINANCE VIP* 🚨\n\n");

                if (!buyData.isEmpty()) {
                    messageBuilder.append("🟢 *MUA USDT VÀO (Rẻ nhất)*\n").append(buyData).append("\n");
                } else {
                    messageBuilder.append("🟢 *MUA USDT VÀO:*\n_Không có VIP nào thỏa mãn_\n\n");
                }

                if (!sellData.isEmpty()) {
                    messageBuilder.append("🔴 *BÁN USDT RA (Đắt nhất)*\n").append(sellData);
                } else {
                    messageBuilder.append("🔴 *BÁN USDT RA:*\n_Không có VIP nào thỏa mãn_\n");
                }

                // Gửi tin nhắn qua Telegram
                sendTelegramMessage(messageBuilder.toString());

            } catch (Exception e) {
                LOG.error("❌ Lỗi tiến trình: ", e);
            }
        }, 0, 10, TimeUnit.MINUTES);
    }

    private static String getTop3VipMerchants(String tradeType, String transAmount) {
        StringBuilder result = new StringBuilder();
        try {
            JsonObject payload = new JsonObject();
            payload.addProperty("fiat", "VND");
            payload.addProperty("page", 1);
            payload.addProperty("rows", 20); // Lấy 20 để lọc ra 3 VIP
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

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(BINANCE_P2P_URL))
                    .header("Content-Type", "application/json")
                    .header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                    .POST(HttpRequest.BodyPublishers.ofString(payload.toString()))
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                JsonObject jsonObj = JsonParser.parseString(response.body()).getAsJsonObject();
                if (jsonObj.get("code").getAsString().equals("000000")) {
                    JsonArray dataArr = jsonObj.getAsJsonArray("data");

                    int vipCount = 0;
                    for (JsonElement itemElement : dataArr) {
                        JsonObject item = itemElement.getAsJsonObject();
                        JsonObject adv = item.getAsJsonObject("adv");
                        JsonObject advertiser = item.getAsJsonObject("advertiser");

                        int monthOrderCount = advertiser.has("monthOrderCount") && !advertiser.get("monthOrderCount").isJsonNull()
                                ? advertiser.get("monthOrderCount").getAsInt() : 0;
                        double monthFinishRate = advertiser.has("monthFinishRate") && !advertiser.get("monthFinishRate").isJsonNull()
                                ? advertiser.get("monthFinishRate").getAsDouble() * 100 : 0.0;

                        // 🔥 LỌC VIP TẠI ĐÂY
                        if (monthOrderCount > 1000 && monthFinishRate >= 99.9) {
                            String price = adv.get("price").getAsString();
                            String merchantName = advertiser.get("nickName").getAsString();

                            JsonArray methodsArr = adv.getAsJsonArray("tradeMethods");
                            List<String> methods = new ArrayList<>();
                            for (JsonElement m : methodsArr) {
                                methods.add(m.getAsJsonObject().get("identifier").getAsString());
                            }
                            String paymentStr = String.join(", ", methods);

                            // Format Telegram Markdown (dùng * để in đậm, _ để in nghiêng)
                            result.append(String.format("▪️ *%s* đ | %s\n", price, merchantName));
                            result.append(String.format("   _%d lệnh (%.2f%%) | %s_\n", monthOrderCount, monthFinishRate, paymentStr));

                            vipCount++;
                            if (vipCount == 3) break;
                        }
                    }
                }
            }
        } catch (Exception e) {
            LOG.error("❌ Lỗi khi lọc VIP: ", e);
        }
        return result.toString();
    }

    private static void sendTelegramMessage(String message) {
        try {
            // Encode URL cho tin nhắn để tránh lỗi ký tự đặc biệt
            String encodedMessage = URLEncoder.encode(message, StandardCharsets.UTF_8.toString());

            // API Telegram chính chủ, parse_mode=Markdown để nhận diện in đậm/nghiêng
            String url = String.format("https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s&parse_mode=Markdown",
                    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, encodedMessage);

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .GET()
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                LOG.info("✅ Đã gửi báo cáo qua Telegram thành công!");
            } else {
                LOG.error("❌ Gửi Telegram thất bại. HTTP Code: {} - Lỗi: {}", response.statusCode(), response.body());
            }
        } catch (Exception e) {
            LOG.error("❌ Exception khi gửi Telegram: ", e);
        }
    }
}