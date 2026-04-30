package com.binance.chuyennd.aerospike.validate_data.marketobject;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.policy.BatchPolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.*;

public class MarketObjectGapRepairTool {
    public static final Logger LOG = LoggerFactory.getLogger(MarketObjectGapRepairTool.class);
    private static final String SET_NAME = "market_data_object";

    public static void main(String[] args) {
        LOG.info("🚀 KHỞI ĐỘNG CÔNG CỤ VÁ LỖ HỔNG MARKET DATA OBJECT...");

        // 1. Tìm các phút bị thiếu
        List<Long> missingTimestamps = getMissingTimestamps("20210101-0700");
        if (missingTimestamps.isEmpty()) {
            LOG.info("🎉 Dữ liệu Market Object đã đầy đủ!");
            return;
        }

        // 2. Gom nhóm để xử lý (Mỗi task 1000 phút để tránh quá tải RAM khi kéo Ticker)
        List<RepairTask> tasks = groupMissingTimestamps(missingTimestamps, 1000);
        LOG.info("🛠️ Gom được {} phút thiếu thành {} Task.", missingTimestamps.size(), tasks.size());

        for (int i = 0; i < tasks.size(); i++) {
            RepairTask task = tasks.get(i);
            LOG.info("\n🔄 [TASK {}/{}] Vá từ {} ({} phút)", (i + 1), tasks.size(),
                    Utils.normalizeDateYYYYMMDDHHmm(task.startTime), task.limit);

            try {
                // Kéo dữ liệu Ticker cần thiết (Bao gồm cả 15 phút trước đó để tính Max/Min)
                long fetchStart = task.startTime - 15 * Utils.TIME_MINUTE;
                int fetchLimit = task.limit + 15;

                TreeMap<Long, Map<String, KlineObjectSimple>> allTickers =
                        DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(fetchStart, fetchLimit);

                if (allTickers == null || allTickers.isEmpty()) {
                    LOG.warn("   ⚠️ Không tìm thấy Ticker trong Aerospike để tính toán.");
                    continue;
                }

                int count = 0;
                TreeMap<Long, MarketDataObject> dailyMarketData = new TreeMap<>();
                for (long t = task.startTime; t <= task.endTime; t += Utils.TIME_MINUTE) {
                    Map<String, KlineObjectSimple> currentTickers = allTickers.get(t);
                    if (currentTickers == null || currentTickers.isEmpty()) continue;

                    // Tính toán MarketDataObject On-The-Fly
                    MarketDataObject mdo = calculateMDO(t, allTickers, currentTickers);

                    if (mdo != null) {
                        dailyMarketData.put(t, mdo);
                        count++;
                    }
                }
                DataManagerAerospikeFloatSim.saveMarketDataBatch(dailyMarketData);
                LOG.info("   ✅ Đã vá xong {} phút.", count);

            } catch (Exception e) {
                LOG.error("❌ Lỗi Task: " + task.startTime, e);
            }
        }
    }

    private static MarketDataObject calculateMDO(long targetTime, TreeMap<Long, Map<String, KlineObjectSimple>> history, Map<String, KlineObjectSimple> current) {
        Map<String, Float> symbol2Max = new HashMap<>();
        Map<String, Float> symbol2Min = new HashMap<>();

        for (String sym : current.keySet()) {
            float max = -1; float min = Float.MAX_VALUE;
            for (int i = 0; i < 15; i++) {
                long time = targetTime - (i * 60000L);
                Map<String, KlineObjectSimple> snap = history.get(time);
                if (snap != null && snap.get(sym) != null) {
                    KlineObjectSimple k = snap.get(sym);
                    if (k.maxPrice > max) max = k.maxPrice;
                    if (k.minPrice < min) min = k.minPrice;
                }
            }
            if (max != -1) { symbol2Max.put(sym, max); symbol2Min.put(sym, min); }
        }
        try {
            return MarketBigChangeDetector.calMarketData(current, symbol2Max, symbol2Min);
        } catch (Exception e) { return null; }
    }

    // Các hàm getMissingTimestamps và groupMissingTimestamps giữ nguyên logic như các tool trước
    private static List<Long> getMissingTimestamps(String start) {
        List<Long> missing = new ArrayList<>();
        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            long t = fmt.parse(start).getTime();
            long end = System.currentTimeMillis();
            BatchPolicy bp = new BatchPolicy();
            bp.maxConcurrentThreads = 4;
            while (t <= end) {
                List<Key> keys = new ArrayList<>();
                List<Long> times = new ArrayList<>();
                for (int i = 0; i < 5000 && t <= end; i++, t += 60000L) {
                    keys.add(new Key(Configs.AEROSPIKE_NAMESPACE, SET_NAME, fmt.format(new Date(t))));
                    times.add(t);
                }
                boolean[] exists = DataManagerAerospikeFloatSim.getClient226().exists(bp, keys.toArray(new Key[0]));
                for (int i = 0; i < exists.length; i++) if (!exists[i]) missing.add(times.get(i));
            }
        } catch (Exception e) {}
        return missing;
    }

    private static List<RepairTask> groupMissingTimestamps(List<Long> ts, int max) {
        List<RepairTask> tasks = new ArrayList<>();
        if (ts.isEmpty()) return tasks;
        Collections.sort(ts);
        long s = ts.get(0), e = s;
        for (int i = 1; i < ts.size(); i++) {
            if (ts.get(i) == e + 60000L && (ts.get(i) - s) / 60000L < max) e = ts.get(i);
            else { tasks.add(new RepairTask(s, e)); s = ts.get(i); e = s; }
        }
        tasks.add(new RepairTask(s, e));
        return tasks;
    }

    static class RepairTask {
        long startTime, endTime; int limit;
        RepairTask(long s, long e) { this.startTime = s; this.endTime = e; this.limit = (int)((e-s)/60000L)+1; }
    }
}