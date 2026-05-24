package com.binance.chuyennd.aerospike.validate_data.ticker;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.Collectors;

public class ValidateResampled15mVsBinance {
    public static final Logger LOG = LoggerFactory.getLogger(ValidateResampled15mVsBinance.class);

    private static final float TOLERANCE_PRICE = 0.005f;
    private static final float TOLERANCE_VOL = 0.01f;

    public static void main(String[] args) {
        // Init mapper trước khi chạy để map được Short <-> String
        com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper.getInstance().init();

        new ValidateResampled15mVsBinance().runRandomValidation(5, 200);
    }

    public void runRandomValidation(int numSymbols, int numTimestamps) {
        LOG.info("🚀 KHỞI ĐỘNG ĐỐI SOÁT DỮ LIỆU: AEROSPIKE 15M (.226) vs BINANCE API...");

        try {
            List<String> allSymbols = RedisHelper.getInstance()
                    .readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS).stream()
                    .filter(s -> !Constants.diedSymbol.contains(s.toUpperCase()) && StringUtils.endsWithIgnoreCase(s, "USDT"))
                    .collect(Collectors.toList());

            Collections.shuffle(allSymbols);
            List<String> targetSymbols = allSymbols.subList(0, Math.min(numSymbols, allSymbols.size()));
            LOG.info("🎯 Danh sách coin test: {}", targetSymbols);

            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            long startTime = fmt.parse("20210101-0700").getTime();
            long endTime = System.currentTimeMillis() - 24 * Utils.TIME_HOUR;

            Set<Long> randomTimestamps = new HashSet<>();
            while (randomTimestamps.size() < numTimestamps) {
                long randomTs = ThreadLocalRandom.current().nextLong(startTime, endTime);
                // Căn chỉnh chuẩn xác về mốc 15 phút
                long aligned15mTs = randomTs - (randomTs % (15 * Utils.TIME_MINUTE));
                randomTimestamps.add(aligned15mTs);
            }

            List<Long> testTimestamps = new ArrayList<>(randomTimestamps);
            Collections.sort(testTimestamps);

            int totalChecks = 0, matchO = 0, matchH = 0, matchL = 0, matchC = 0, matchV = 0, perfectMatch = 0;

            for (int i = 0; i < testTimestamps.size(); i++) {
                long targetTime = testTimestamps.get(i);
                String timeStr = Utils.normalizeDateYYYYMMDDHHmm(targetTime);
                LOG.info("\n========================================================");
                LOG.info("🔍 MẪU {}/{} TẠI PHÚT: {}", (i + 1), numTimestamps, timeStr);

                // 1. Lấy đúng 1 block 15m từ Aerospike
                TreeMap<Long, Map<Short, KlineObjectSimple>> asData =
                        DataManagerAerospikeFloatSim.readDataFromAerospike15mCustom(targetTime, 1);

                if (asData == null || !asData.containsKey(targetTime)) {
                    LOG.warn("   ⚠️ Aerospike KHÔNG CÓ dữ liệu tại mốc {}. Bỏ qua!", timeStr);
                    continue;
                }

                Map<Short, KlineObjectSimple> asSymbolsData = asData.get(targetTime);

                for (String symbol : targetSymbols) {
                    KlineObjectSimple asKline = asSymbolsData.get(SimpleSymbolMapper.getInstance().getId(symbol));
                    if (asKline == null) continue; // Coin này chưa trade tại thời điểm đó

                    try {
                        // 2. Gọi API Binance lấy nến 15m
                        List<KlineObjectSimple> binanceCandles =
                                TickerFuturesHelper.getTickerSimpleWithStartTimeAndLimit(symbol, "15m", targetTime, 1);

                        if (binanceCandles == null || binanceCandles.isEmpty() || binanceCandles.get(0).startTime.longValue() != targetTime) {
                            continue;
                        }

                        KlineObjectSimple binanceKline = binanceCandles.get(0);
                        totalChecks++;

                        // 3. Đối soát
                        boolean o = checkDiff(symbol, "OPEN", asKline.priceOpen, binanceKline.priceOpen, TOLERANCE_PRICE);
                        boolean h = checkDiff(symbol, "HIGH", asKline.maxPrice, binanceKline.maxPrice, TOLERANCE_PRICE);
                        boolean l = checkDiff(symbol, "LOW", asKline.minPrice, binanceKline.minPrice, TOLERANCE_PRICE);
                        boolean c = checkDiff(symbol, "CLOSE", asKline.priceClose, binanceKline.priceClose, TOLERANCE_PRICE);
                        boolean v = checkDiff(symbol, "VOLUME", asKline.totalUsdt, binanceKline.totalUsdt, TOLERANCE_VOL);

                        if (o) matchO++;
                        if (h) matchH++;
                        if (l) matchL++;
                        if (c) matchC++;
                        if (v) matchV++;

                        if (o && h && l && c && v) {
                            perfectMatch++;
                        } else {
                            LOG.error("   ❌ [{}] LỆCH NẾN | AS [O:{}, H:{}, L:{}, C:{}, V:{}] vs BIN [O:{}, H:{}, L:{}, C:{}, V:{}]",
                                    symbol,
                                    asKline.priceOpen, asKline.maxPrice, asKline.minPrice, asKline.priceClose, asKline.totalUsdt,
                                    binanceKline.priceOpen, binanceKline.maxPrice, binanceKline.minPrice, binanceKline.priceClose, binanceKline.totalUsdt);
                        }
                        Thread.sleep(50); // Nghỉ tránh bị Binance block IP
                    } catch (Exception e) {
                        LOG.error("   ⚠️ Lỗi so sánh cho " + symbol, e);
                    }
                }
            }

            LOG.info("\n========================================================");
            LOG.info("🎉 TỔNG KẾT DB ĐỌC LÊN vs BINANCE API (15M)");
            LOG.info("📊 Tổng số nến đã so sánh : {}", totalChecks);
            LOG.info("✅ Khớp OPEN   : {}/{} ({}%)", matchO, totalChecks, formatPct(matchO, totalChecks));
            LOG.info("✅ Khớp HIGH   : {}/{} ({}%)", matchH, totalChecks, formatPct(matchH, totalChecks));
            LOG.info("✅ Khớp LOW    : {}/{} ({}%)", matchL, totalChecks, formatPct(matchL, totalChecks));
            LOG.info("✅ Khớp CLOSE  : {}/{} ({}%)", matchC, totalChecks, formatPct(matchC, totalChecks));
            LOG.info("✅ Khớp VOLUME : {}/{} ({}%)", matchV, totalChecks, formatPct(matchV, totalChecks));
            LOG.info("🏆 HOÀN HẢO (Khớp 5/5) : {}/{} ({}%)", perfectMatch, totalChecks, formatPct(perfectMatch, totalChecks));
            LOG.info("========================================================");

        } catch (Exception e) {
            LOG.error("Lỗi quá trình Validation", e);
        }
    }

    private boolean checkDiff(String symbol, String type, float asVal, float binVal, float tolerance) {
        float maxAbs = Math.max(Math.abs(asVal), Math.abs(binVal));
        if (maxAbs == 0) return true;

        float diff = Math.abs(asVal - binVal) / maxAbs;
        return diff <= tolerance;
    }

    private String formatPct(int match, int total) {
        if (total == 0) return "0.00";
        return String.format("%.2f", (match * 100.0f) / total);
    }
}