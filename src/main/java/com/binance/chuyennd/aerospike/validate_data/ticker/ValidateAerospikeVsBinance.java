package com.binance.chuyennd.aerospike.validate_data.ticker;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;

public class ValidateAerospikeVsBinance {
    public static final Logger LOG = LoggerFactory.getLogger(ValidateAerospikeVsBinance.class);

    public static void main(String[] args) {
        new ValidateAerospikeVsBinance().runRandomValidation();
    }

    public void runRandomValidation() {
        LOG.info("🚀 KHỞI ĐỘNG CÔNG CỤ RANDOM ĐỐI SOÁT DỮ LIỆU: AEROSPIKE vs BINANCE API...");

        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            long startTime = fmt.parse("20210101-0700").getTime();
            long endTime = System.currentTimeMillis() - 2 * Utils.TIME_MINUTE; // Bỏ qua 2 phút gần nhất để tránh nến chưa chốt
            long thirtyDaysAgo = endTime - (30L * 24 * 60 * 60 * 1000); // Mốc 30 ngày trước

            // 1. SINH 20 MỐC THỜI GIAN (Ưu tiên 50% dữ liệu gần đây)
            Set<Long> randomTimestamps = new HashSet<>();

            // --> 10 mẫu đầu tiên: Lấy ngẫu nhiên trong 30 NGÀY GẦN ĐÂY NHẤT
            while (randomTimestamps.size() < 10) {
                long randomTs = ThreadLocalRandom.current().nextLong(thirtyDaysAgo, endTime);
                randomTimestamps.add(Utils.getMinute(randomTs));
            }

            // --> 10 mẫu tiếp theo: Lấy ngẫu nhiên từ năm 2021 đến 30 ngày trước
            while (randomTimestamps.size() < 20) {
                long randomTs = ThreadLocalRandom.current().nextLong(startTime, thirtyDaysAgo);
                randomTimestamps.add(Utils.getMinute(randomTs));
            }

            List<Long> testTimestamps = new ArrayList<>(randomTimestamps);
            Collections.sort(testTimestamps); // Sắp xếp từ xưa đến nay để log nhìn cho dễ

            LOG.info("🎯 Đã sinh 20 mốc thời gian (10 mốc gần đây, 10 mốc quá khứ).");

            int totalCoinsChecked = 0;
            int totalErrors = 0;

            // 2. BẮT ĐẦU DUYỆT TỪNG PHÚT
            for (int i = 0; i < testTimestamps.size(); i++) {
                long targetTime = testTimestamps.get(i);
                String timeStr = Utils.normalizeDateYYYYMMDDHHmm(targetTime);
                LOG.info("\n========================================================");
                LOG.info("🔍 MẪU {}/20 TẠI PHÚT: {}", (i + 1), timeStr);

                // Lấy data nguyên 1 phút từ Aerospike
                TreeMap<Long, Map<String, KlineObjectSimple>> asData =
                        DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(targetTime, 1);

                if (asData == null || !asData.containsKey(targetTime)) {
                    LOG.warn("   ⚠️ Aerospike KHÔNG CÓ dữ liệu tại phút này. Bỏ qua!");
                    continue;
                }

                Map<String, KlineObjectSimple> asSymbolsData = asData.get(targetTime);
                LOG.info("   -> Phát hiện {} đồng coin trong DB. Đang gọi API Binance đối soát...", asSymbolsData.size());

                int errorInMinute = 0;

                // 3. DUYỆT TỪNG COIN ĐỂ GỌI API BINANCE
                for (Map.Entry<String, KlineObjectSimple> entry : asSymbolsData.entrySet()) {
                    String shortSymbol = entry.getKey();
                    KlineObjectSimple asKline = entry.getValue();

                    // 🔥 KIỂM TRA CHUỖI USDT: Chỉ cộng thêm nếu chưa có
                    String apiSymbol = shortSymbol;
                    if (!apiSymbol.toUpperCase().endsWith("USDT")) {
                        apiSymbol += "USDT";
                    }

                    try {
                        // Gọi API Binance lấy đúng 1 nến tại phút đó
                        List<KlineObjectSimple> binanceCandles =
                                TickerFuturesHelper.getTickerSimpleWithStartTimeAndLimit(apiSymbol, "1m", targetTime, 1);

                        if (binanceCandles == null || binanceCandles.isEmpty()) {
                            continue;
                        }

                        KlineObjectSimple binanceKline = binanceCandles.get(0);

                        // Check xem API có trả về đúng cây nến của phút đó không
                        if (binanceKline.startTime.longValue() != targetTime) {
                            continue;
                        }

                        totalCoinsChecked++;

                        // 4. KIỂM TRA LỖI LỆCH (Sai số > 0.5%)
                        float asPrice = asKline.priceClose;
                        float binPrice = binanceKline.priceClose;

                        float maxAbs = Math.max(Math.abs(asPrice), Math.abs(binPrice));
                        float diffPercent = (maxAbs == 0) ? 0 : (Math.abs(asPrice - binPrice) / maxAbs) * 100f;

                        if (diffPercent > 0.5f) {
                            errorInMinute++;
                            totalErrors++;
                            LOG.error("   ❌ [LỖI {}] Giá Close lệch {}%: AS = {} | BINANCE = {}",
                                    apiSymbol,
                                    String.format("%.2f", diffPercent),
                                    asPrice, binPrice);
                        }

                        // Nghỉ 50ms tránh bị Binance chặn IP
                        Thread.sleep(50);

                    } catch (Exception e) {
                        LOG.error("   ⚠️ Lỗi khi gọi API Binance cho " + apiSymbol, e);
                    }
                }

                if (errorInMinute == 0) {
                    LOG.info("   ✅ HOÀN HẢO! Toàn bộ coin tại phút {} đều khớp với API Binance.", timeStr);
                } else {
                    LOG.warn("   ⚠️ Phút {} có {} coin bị sai lệch giá!", timeStr, errorInMinute);
                }
            }

            LOG.info("\n========================================================");
            LOG.info("🎉 TỔNG KẾT QUÁ TRÌNH KIỂM TRA RANDOM:");
            LOG.info("📊 Tổng số phút đã test    : 20");
            LOG.info("📊 Tổng số nến đã so sánh  : {}", totalCoinsChecked);
            LOG.info("🚨 Tổng số nến BỊ LỖI      : {} (Sai lệch > 0.5%)", totalErrors);
            if (totalErrors == 0) {
                LOG.info("🏆 KẾT LUẬN: Dữ liệu Aerospike chuẩn xác 100% so với thực tế!");
            } else {
                LOG.warn("⚠️ KẾT LUẬN: Cần kiểm tra lại luồng Ingestor do có dữ liệu rác/lệch.");
            }
            LOG.info("========================================================");

        } catch (Exception e) {
            LOG.error("Lỗi quá trình Validation", e);
        }
    }
}