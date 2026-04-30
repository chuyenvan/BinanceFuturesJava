package com.binance.chuyennd.aerospike.validate_data.ticker; // Sửa lại package cho đúng với TickerIngestor

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.proto.MinuteDataFinalProto;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Utils;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class TickerGapRepairTool {
    public static final Logger LOG = LoggerFactory.getLogger(TickerGapRepairTool.class);

    public static void main(String[] args) {
        LOG.info("🚀 KHỞI ĐỘNG CÔNG CỤ VÁ LỖ HỔNG TICKER...");

        // 1. Lấy danh sách phút bị thiếu từ năm 2021 (7h sáng)
        List<Long> missingTimestamps = CheckGapTicker.getMissingTimestamps("20210101-0700");

        if (missingTimestamps.isEmpty()) {
            LOG.info("🎉 Hệ thống hoàn hảo, không thiếu phút nào!");
            return;
        }

        // 2. Gom các phút bị thiếu thành các khoảng (Mỗi khoảng tối đa 500 phút để API Binance không la)
        List<RepairTask> tasks = groupMissingTimestamps(missingTimestamps, 500);
        LOG.info("🛠️ Gom được {} task vá lỗi.", tasks.size());

        // 3. Lấy danh sách Coin từ Redis (Y hệt TickerIngestor của bác)
        List<String> symbols = collectSymbolsFromRedis();
        if (symbols == null || symbols.isEmpty()) {
            LOG.error("❌ Không lấy được danh sách coin từ Redis!");
            return;
        }

        // 4. Bắt đầu vá lỗ hổng
        for (int i = 0; i < tasks.size(); i++) {
            RepairTask task = tasks.get(i);
            LOG.info("🔄 [Task {}/{}] Đang vá dữ liệu từ {} đến {} (Sẽ kéo {} nến)...",
                    (i + 1), tasks.size(),
                    Utils.normalizeDateYYYYMMDDHHmm(task.startTime),
                    Utils.normalizeDateYYYYMMDDHHmm(task.endTime),
                    task.limit);

            repairBatch(symbols, task.startTime, task.limit);

            try {
                // Nghỉ 1 chút giữa các chunk để tránh Limit IP của Binance
                Thread.sleep(5000);
            } catch (InterruptedException ignored) {}
        }

        LOG.info("✅ HOÀN TẤT VÁ LỖ HỔNG TICKER!");
    }

    // --- CÁC HÀM HỖ TRỢ BÊN DƯỚI DỰA TRÊN CODE TICKERINGESTOR CỦA BÁC ---

    private static void repairBatch(List<String> symbols, long batchStartTime, int limit) {
        for (String s : symbols) {
            try {
                if (StringUtils.isBlank(s) || !s.matches("^[A-Z0-9]+$")) continue;

                // Lấy lượng nến đủ bù lỗ hổng
                List<KlineObjectSimple> candles = TickerFuturesHelper.getTickerSimpleWithStartTimeAndLimit(s, "1m", batchStartTime, limit);
                if (candles == null || candles.isEmpty()) continue;

                String shortS = s.replace("USDT", "");

                // Nạp vào DB
                for (KlineObjectSimple c : candles) {
                    if (c == null || c.startTime == null) continue;
                    long ts = c.startTime.longValue();

                    if (ts >= batchStartTime && ts < batchStartTime + (long) limit * Utils.TIME_MINUTE) {
                        Map<String, MinuteDataFinalProto.KlineObjectOptimized> map = new HashMap<>();
                        map.put(shortS, convertToProto(c));

                        // Hàm Write của bác trong DataManagerAerospike
                        DataManagerAerospikeFloatSim.writeMinuteBatch(ts, map);
                    }
                }

                // Nghỉ để tránh Rate Limit Binance cho mỗi đồng coin
                Thread.sleep(300);

            } catch (Exception e) {
                LOG.error("Lỗi khi vá coin " + s, e);
            }
        }
    }

    /**
     * Thuật toán gom các phút lẻ tẻ thành các Block liên tiếp.
     * Ví dụ thiếu phút [1, 2, 3,  10, 11] -> Gom thành Block(start=1, limit=3) và Block(start=10, limit=2)
     */
    private static List<RepairTask> groupMissingTimestamps(List<Long> timestamps, int maxLimit) {
        List<RepairTask> tasks = new ArrayList<>();
        if (timestamps.isEmpty()) return tasks;

        Collections.sort(timestamps);

        long currentStart = timestamps.get(0);
        long currentEnd = currentStart;

        for (int i = 1; i < timestamps.size(); i++) {
            long ts = timestamps.get(i);
            // Nếu nến liên tiếp VÀ chưa vượt quá max limit
            if (ts == currentEnd + Utils.TIME_MINUTE && ((ts - currentStart) / Utils.TIME_MINUTE) < maxLimit) {
                currentEnd = ts;
            } else {
                int limit = (int) ((currentEnd - currentStart) / Utils.TIME_MINUTE) + 1;
                tasks.add(new RepairTask(currentStart, currentEnd, limit));

                currentStart = ts;
                currentEnd = ts;
            }
        }

        // Thêm task cuối cùng
        int limit = (int) ((currentEnd - currentStart) / Utils.TIME_MINUTE) + 1;
        tasks.add(new RepairTask(currentStart, currentEnd, limit));

        return tasks;
    }

    private static MinuteDataFinalProto.KlineObjectOptimized convertToProto(KlineObjectSimple k) {
        return MinuteDataFinalProto.KlineObjectOptimized.newBuilder()
                .setPriceOpen(k.priceOpen)
                .setPriceClose(k.priceClose)
                .setMaxPrice(k.maxPrice)
                .setMinPrice(k.minPrice)
                .setTotalUsdt(k.totalUsdt)
                .build();
    }

    private static List<String> collectSymbolsFromRedis() {
        try {
            Map<String, String> data = RedisHelper.getInstance().hgetAll(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
            if (data != null && !data.isEmpty()) {
                return new ArrayList<>(data.keySet());
            }
        } catch (Exception e) {
            LOG.error("Lỗi lấy symbol redis", e);
        }
        return Collections.emptyList();
    }

    // Object phụ trợ cho thuật toán gom nhóm
    static class RepairTask {
        long startTime;
        long endTime;
        int limit;

        public RepairTask(long startTime, long endTime, int limit) {
            this.startTime = startTime;
            this.endTime = endTime;
            this.limit = limit;
        }
    }
}