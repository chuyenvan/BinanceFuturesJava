package com.binance.chuyennd.aerospike.validate_data.marketobject;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.reflect.Field;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;

public class ValidateMarketObjectConsistency15M {
    public static final Logger LOG = LoggerFactory.getLogger(ValidateMarketObjectConsistency15M.class);

    public static void main(String[] args) {
        LOG.info("🚀 KHỞI ĐỘNG CHECK RANDOM MARKET DATA 15M (AEROSPIKE vs RE-CALCULATED)...");
        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            long start = fmt.parse("20210101-0700").getTime();
            long end = System.currentTimeMillis() - 2 * Utils.TIME_MINUTE;
            long thirtyDaysAgo = end - (30L * 24 * 3600 * 1000);

            Set<Long> samples = new HashSet<>();
            while (samples.size() < 10) {
                long randomTs = ThreadLocalRandom.current().nextLong(thirtyDaysAgo, end);
                samples.add(randomTs - (randomTs % (15 * Utils.TIME_MINUTE))); // 🔥 ÉP VỀ CHẴN 15 PHÚT
            }
            while (samples.size() < 20) {
                long randomTs = ThreadLocalRandom.current().nextLong(start, thirtyDaysAgo);
                samples.add(randomTs - (randomTs % (15 * Utils.TIME_MINUTE))); // 🔥 ÉP VỀ CHẴN 15 PHÚT
            }

            List<Long> testTimes = new ArrayList<>(samples);
            Collections.sort(testTimes);

            int totalErrors = 0;
            for (int i = 0; i < testTimes.size(); i++) {
                long t = testTimes.get(i);
                LOG.info("\n🔍 MẪU {}/20 TẠI: {}", (i + 1), Utils.normalizeDateYYYYMMDDHHmm(t));

                // 1. Lấy MDO 15M cũ từ DB
                MarketDataObject15M oldMdo = DataManagerAerospikeFloatSim.getMarketData15MAtTime(t);
                if (oldMdo == null) {
                    LOG.warn("   ⚠️ DB không có MDO 15M tại phút này. Bỏ qua.");
                    continue;
                }

                // 2. Tính lại MDO từ Ticker gốc (16 nến 15m = 4 Giờ)
                long fetchStart = t - (15 * 15 * Utils.TIME_MINUTE);
                TreeMap<Long, Map<Short, KlineObjectSimple>> tickers =
                        DataManagerAerospikeFloatSim.readDataFromAerospike15mCustom(fetchStart, 16);

                MarketDataObject15M newMdo = calculateMDO15M(t, tickers, tickers != null ? tickers.get(t) : null);

                if (newMdo == null) {
                    LOG.error("   ❌ Không thể tính lại MDO do thiếu Ticker 15M gốc.");
                    continue;
                }

                // 3. So sánh
                if (compare(oldMdo, newMdo)) LOG.info("   ✅ KHỚP!");
                else {
                    totalErrors++;
                    LOG.error("   ❌ SAI LỆCH!");
                }
            }
            LOG.info("\n==========================================================");
            LOG.info("📊 TỔNG KẾT: {}/20 mẫu bị sai lệch.", totalErrors);
        } catch (Exception e) {
            LOG.error("Lỗi đối soát", e);
        }
    }

    private static boolean compare(MarketDataObject15M o, MarketDataObject15M n) {
        boolean match = true;
        // Kiểm tra đúng các biến của class MarketDataObject15M
        String[] fields = {"rateDownAvg", "rateUpAvg", "rateDown4HAvg"};
        for (String fName : fields) {
            try {
                Field f = MarketDataObject15M.class.getField(fName);
                float v1 = f.getFloat(o), v2 = f.getFloat(n);
                float diff = (Math.max(Math.abs(v1), Math.abs(v2)) == 0) ? 0 : Math.abs(v1 - v2) / Math.max(Math.abs(v1), Math.abs(v2)) * 100f;

                if (diff > 0.5f) {
                    LOG.error("      ❌ Lệch {}: DB={} | Tính lại={} ({}%)", fName, v1, v2, String.format("%.2f", diff));
                    match = false;
                }
            } catch (Exception e) {
            }
        }
        return match;
    }

    private static MarketDataObject15M calculateMDO15M(long targetTime, TreeMap<Long, Map<Short, KlineObjectSimple>> history,
                                                       Map<Short, KlineObjectSimple> current) {
        if (current == null || history == null) return null;
        Map<Short, Float> symbol2Max = new HashMap<>();
        Map<Short, Float> symbol2Min = new HashMap<>();

        for (Short sym : current.keySet()) {
            float max = -1, min = Float.MAX_VALUE;

            // 🔥 Lùi về 16 cây nến 15m để quét đỉnh đáy 4 Giờ
            for (int i = 0; i < 16; i++) {
                Map<Short, KlineObjectSimple> snap = history.get(targetTime - (i * 15 * 60000L));
                if (snap != null && snap.get(sym) != null) {
                    KlineObjectSimple k = snap.get(sym);
                    if (k.maxPrice > max) max = k.maxPrice;
                    if (k.minPrice < min) min = k.minPrice;
                }
            }
            if (max != -1) {
                symbol2Max.put(sym, max);
                symbol2Min.put(sym, min);
            }
        }
        try {
            return MarketBigChangeDetector.calMarketData15M(current, symbol2Max, symbol2Min);
        } catch (Exception e) {
            return null;
        }
    }
}