package com.binance.chuyennd.aerospike.validate_data.marketobject;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.reflect.Field;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;

public class ValidateMarketObjectConsistency {
    public static final Logger LOG = LoggerFactory.getLogger(ValidateMarketObjectConsistency.class);

    public static void main(String[] args) {
        LOG.info("🚀 KHỞI ĐỘNG CHECK RANDOM MARKET DATA OBJECT (AEROSPIKE vs RE-CALCULATED)...");
        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            long start = fmt.parse("20210101-0700").getTime();
            long end = System.currentTimeMillis() - 2 * Utils.TIME_MINUTE;
            long thirtyDaysAgo = end - (30L * 24 * 3600 * 1000);

            Set<Long> samples = new HashSet<>();
            while (samples.size() < 10) samples.add(Utils.getMinute(ThreadLocalRandom.current().nextLong(thirtyDaysAgo, end)));
            while (samples.size() < 20) samples.add(Utils.getMinute(ThreadLocalRandom.current().nextLong(start, thirtyDaysAgo)));

            List<Long> testTimes = new ArrayList<>(samples);
            Collections.sort(testTimes);

            int totalErrors = 0;
            for (int i = 0; i < testTimes.size(); i++) {
                long t = testTimes.get(i);
                LOG.info("\n🔍 MẪU {}/20 TẠI: {}", (i+1), Utils.normalizeDateYYYYMMDDHHmm(t));

                // 1. Lấy MDO cũ từ DB
                MarketDataObject oldMdo = DataManagerAerospikeFloatSim.getMarketDataAtTime(t);
                if (oldMdo == null) { LOG.warn("   ⚠️ DB không có MDO tại phút này. Bỏ qua."); continue; }

                // 2. Tính lại MDO từ Ticker gốc
                TreeMap<Long, Map<String, KlineObjectSimple>> tickers =
                        DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(t - 15 * Utils.TIME_MINUTE, 16);

                MarketDataObject newMdo = calculateMDO(t, tickers, tickers != null ? tickers.get(t) : null);

                if (newMdo == null) { LOG.error("   ❌ Không thể tính lại MDO do thiếu Ticker gốc."); continue; }

                // 3. So sánh
                if (compare(oldMdo, newMdo)) LOG.info("   ✅ KHỚP!");
                else { totalErrors++; LOG.error("   ❌ SAI LỆCH!"); }
            }
            LOG.info("\n==========================================================");
            LOG.info("📊 TỔNG KẾT: {}/20 mẫu bị sai lệch.", totalErrors);
        } catch (Exception e) { LOG.error("Lỗi đối soát", e); }
    }

    private static boolean compare(MarketDataObject o, MarketDataObject n) {
        boolean match = true;
        String[] fields = {"rateDownAvg", "rateUpAvg", "rateDown15MAvg", "rateUp15MAvg"};
        for (String fName : fields) {
            try {
                Field f = MarketDataObject.class.getField(fName);
                float v1 = f.getFloat(o), v2 = f.getFloat(n);
                float diff = (Math.max(Math.abs(v1), Math.abs(v2)) == 0) ? 0 : Math.abs(v1 - v2) / Math.max(Math.abs(v1), Math.abs(v2)) * 100f;
                if (diff > 0.5f) {
                    LOG.error("      ❌ Lệch {}: Cũ={} | Mới={} ({}%)", fName, v1, v2, String.format("%.2f", diff));
                    match = false;
                }
            } catch (Exception e) {}
        }
        return match;
    }

    private static MarketDataObject calculateMDO(long targetTime, TreeMap<Long, Map<String, KlineObjectSimple>> history, Map<String, KlineObjectSimple> current) {
        if (current == null || history == null) return null;
        Map<String, Float> symbol2Max = new HashMap<>(); Map<String, Float> symbol2Min = new HashMap<>();
        for (String sym : current.keySet()) {
            float max = -1, min = Float.MAX_VALUE;
            for (int i = 0; i < 15; i++) {
                Map<String, KlineObjectSimple> snap = history.get(targetTime - i * 60000L);
                if (snap != null && snap.get(sym) != null) {
                    KlineObjectSimple k = snap.get(sym);
                    if (k.maxPrice > max) max = k.maxPrice;
                    if (k.minPrice < min) min = k.minPrice;
                }
            }
            if (max != -1) { symbol2Max.put(sym, max); symbol2Min.put(sym, min); }
        }
        try { return MarketBigChangeDetector.calMarketData(current, symbol2Max, symbol2Min); } catch (Exception e) { return null; }
    }
}