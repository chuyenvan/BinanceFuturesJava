package com.binance.chuyennd.aerospike.validate_data.ticker;

import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.nio.ByteBuffer;
import java.text.SimpleDateFormat;
import java.util.*;

public class TickerGapRepairTool15M {
    public static final Logger LOG = LoggerFactory.getLogger(TickerGapRepairTool15M.class);
    private static final String SET_NAME = "kline_15m_opt";

    public static void main(String[] args) {
        LOG.info("🚀 KHỞI ĐỘNG CÔNG CỤ VÁ LỖ HỔNG TICKER 15M...");

        // Bắt buộc init Mapper để có danh sách ID chuẩn
        SimpleSymbolMapper.getInstance().init();

        // 1. Lấy danh sách phút bị thiếu
        List<Long> missingTimestamps = CheckGapTicker15M.getMissingTimestamps("20210101-0700");

        if (missingTimestamps.isEmpty()) {
            LOG.info("🎉 Hệ thống hoàn hảo, không thiếu block 15m nào!");
            return;
        }

        LOG.info("⚠️ PHÁT HIỆN {} LỖ HỔNG. CHI TIẾT:", missingTimestamps.size());
        for (Long ts : missingTimestamps) {
            LOG.info("   -> Thiếu mốc: {}", Utils.normalizeDateYYYYMMDDHHmm(ts));
        }

        // 2. Gom các phút bị thiếu thành các khoảng (1 khoảng tối đa 500 nến 15m)
        List<RepairTask> tasks = groupMissingTimestamps(missingTimestamps, 500);
        LOG.info("🛠️ Gom được {} task vá lỗi.", tasks.size());

        // 3. Lấy danh sách Coin từ Redis
        List<String> symbols = collectSymbolsFromRedis();
        if (symbols == null || symbols.isEmpty()) {
            LOG.error("❌ Không lấy được danh sách coin từ Redis!");
            return;
        }

        // 4. Bắt đầu vá lỗ hổng
        for (int i = 0; i < tasks.size(); i++) {
            RepairTask task = tasks.get(i);
            LOG.info("\n🔄 [Task {}/{}] Đang gọi API Binance để vá từ {} đến {} (Sẽ kéo {} nến/coin)...",
                    (i + 1), tasks.size(),
                    Utils.normalizeDateYYYYMMDDHHmm(task.startTime),
                    Utils.normalizeDateYYYYMMDDHHmm(task.endTime),
                    task.limit);

            repairBatch(symbols, task.startTime, task.limit);

            try {
                // Nghỉ 1 chút giữa các chunk để tránh Limit IP của Binance
                Thread.sleep(3000);
            } catch (InterruptedException ignored) {}
        }

        LOG.info("✅ HOÀN TẤT VÁ LỖ HỔNG TICKER 15M!");
    }

    private static void repairBatch(List<String> symbols, long batchStartTime, int limit) {
        // RAM Buffer để gom nến của tất cả các coin theo mốc thời gian
        // Map<Thời_gian, Map<Short_ID, Kline>>
        Map<Long, Map<Short, KlineObjectSimple>> timeToSymbolMap = new HashMap<>();

        int symbolCount = 0;
        for (String s : symbols) {
            try {
                if (StringUtils.isBlank(s) || !s.matches("^[A-Z0-9]+$")) continue;

                // Lấy lượng nến 15M từ Binance
                List<KlineObjectSimple> candles = TickerFuturesHelper.getTickerSimpleWithStartTimeAndLimit(s, "15m", batchStartTime, limit);
                if (candles == null || candles.isEmpty()) continue;

                // Đảm bảo có đuôi USDT để map ID chuẩn
                String fullSymbol = s.endsWith("USDT") ? s : s + "USDT";
                short symId = SimpleSymbolMapper.getInstance().getId(fullSymbol);

                // Nạp vào RAM Buffer
                for (KlineObjectSimple c : candles) {
                    if (c == null || c.startTime == null) continue;
                    long ts = c.startTime.longValue();

                    if (ts >= batchStartTime && ts < batchStartTime + (long) limit * 15 * Utils.TIME_MINUTE) {
                        timeToSymbolMap.computeIfAbsent(ts, k -> new HashMap<>()).put(symId, c);
                    }
                }

                symbolCount++;
                if (symbolCount % 50 == 0) {
                    LOG.info("   ... Đã tải API xong {}/{} mã", symbolCount, symbols.size());
                }

                // Nghỉ để tránh Rate Limit Binance
                Thread.sleep(100);

            } catch (Exception e) {
                LOG.error("   ❌ Lỗi khi tải coin " + s, e);
            }
        }

        // Sau khi đã gom đủ dữ liệu của toàn thị trường, tiến hành ghi lên Aerospike .226
        WritePolicy wp = new WritePolicy();
        wp.sendKey = true;
        SimpleDateFormat keyFmt = new SimpleDateFormat("yyyyMMdd-HHmm");

        for (Map.Entry<Long, Map<Short, KlineObjectSimple>> entry : timeToSymbolMap.entrySet()) {
            try {
                long ts = entry.getKey();
                Map<Short, KlineObjectSimple> map15m = entry.getValue();

                // Mã hóa Custom Binary và Nén Snappy
                byte[] rawBytes = encodeKline15mMapToBinary(map15m);
                byte[] compressedBytes = Snappy.compress(rawBytes);

                String keyString = keyFmt.format(new Date(ts));
                Key asKey = new Key(Configs.AEROSPIKE_NAMESPACE, SET_NAME, keyString);

                // Ghi đè vào Node 226
                DataManagerAerospikeFloatSim.getClient226().put(wp, asKey, new Bin("data", compressedBytes));

                LOG.info("   💾 Đã vá thành công nến 15M tại: {} (Bao gồm {} symbols)",
                        Utils.normalizeDateYYYYMMDDHHmm(ts), map15m.size());
            } catch (Exception e) {
                LOG.error("   ❌ Lỗi ghi Aerospike tại mốc " + Utils.normalizeDateYYYYMMDDHHmm(entry.getKey()), e);
            }
        }
    }

    /**
     * TỐI ƯU CỰC ĐỘ: Custom Binary Codec cho nến 15M
     */
    private static byte[] encodeKline15mMapToBinary(Map<Short, KlineObjectSimple> map) {
        if (map == null || map.isEmpty()) return new byte[0];
        int requiredSize = 4 + map.size() * 22;
        ByteBuffer buffer = ByteBuffer.allocate(requiredSize);
        buffer.putInt(map.size());
        for (Map.Entry<Short, KlineObjectSimple> entry : map.entrySet()) {
            buffer.putShort(entry.getKey());
            KlineObjectSimple k = entry.getValue();
            buffer.putFloat(k.priceOpen);
            buffer.putFloat(k.maxPrice);
            buffer.putFloat(k.minPrice);
            buffer.putFloat(k.priceClose);
            buffer.putFloat(k.totalUsdt);
        }
        return buffer.array();
    }

    /**
     * Thuật toán gom nhóm các mốc 15 phút.
     */
    private static List<RepairTask> groupMissingTimestamps(List<Long> timestamps, int maxLimit) {
        List<RepairTask> tasks = new ArrayList<>();
        if (timestamps.isEmpty()) return tasks;

        Collections.sort(timestamps);

        long currentStart = timestamps.get(0);
        long currentEnd = currentStart;

        for (int i = 1; i < timestamps.size(); i++) {
            long ts = timestamps.get(i);
            // 🔥 ĐỔI SANG BƯỚC NHẢY 15 PHÚT
            if (ts == currentEnd + (15 * Utils.TIME_MINUTE) && ((ts - currentStart) / (15 * Utils.TIME_MINUTE)) < maxLimit) {
                currentEnd = ts;
            } else {
                int limit = (int) ((currentEnd - currentStart) / (15 * Utils.TIME_MINUTE)) + 1;
                tasks.add(new RepairTask(currentStart, currentEnd, limit));
                currentStart = ts;
                currentEnd = ts;
            }
        }

        // Thêm task cuối cùng
        int limit = (int) ((currentEnd - currentStart) / (15 * Utils.TIME_MINUTE)) + 1;
        tasks.add(new RepairTask(currentStart, currentEnd, limit));

        return tasks;
    }

    private static List<String> collectSymbolsFromRedis() {
        try {
            Set<String> data = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
            if (data != null && !data.isEmpty()) {
                return new ArrayList<>(data);
            }
        } catch (Exception e) {
            LOG.error("Lỗi lấy symbol redis", e);
        }
        return Collections.emptyList();
    }

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