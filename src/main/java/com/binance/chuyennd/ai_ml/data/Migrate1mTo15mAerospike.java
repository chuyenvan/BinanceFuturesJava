package com.binance.chuyennd.ai_ml.data;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.nio.ByteBuffer;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

public class Migrate1mTo15mAerospike {
    private static final Logger LOG = LoggerFactory.getLogger(Migrate1mTo15mAerospike.class);

    // Cấu hình Set mới
    public static final String AEROSPIKE_SET_NAME_TICKER_15M = "kline_15m_opt";

    // Cấu hình Client 224 (Như bác yêu cầu)
    private static AerospikeClient client226;
    private static final WritePolicy writePolicy = new WritePolicy();

    // Đa luồng xử lý
    private static final int THREAD_COUNT = 8;
    private static final ExecutorService executor = Executors.newFixedThreadPool(THREAD_COUNT);
    private static final AtomicInteger daysProcessed = new AtomicInteger(0);

    static {
        writePolicy.sendKey = true;
        writePolicy.expiration = 0; // Lưu vĩnh viễn
        // Giả định port 3222 giống các node kia, bác sửa lại nếu port khác
        client226 = DataManagerAerospikeFloatSim.getClient226();
    }

    public static void main(String[] args) {
        LOG.info("🚀 BẮT ĐẦU CHUYỂN ĐỔI NẾN 1M -> 15M (BINARY SHORT FORMAT) LÊN NODE .224...");

        // Bắt buộc init Mapper để có bộ ID chuẩn
        SimpleSymbolMapper.getInstance().init();

        try {
            // Mốc bắt đầu (Ví dụ: 01/01/2021)
            long startTs = Utils.sdfFile.parse("20210101").getTime() + 7 * Utils.TIME_HOUR;
            long endTs = System.currentTimeMillis();

            List<Long> dailyTimestamps = new ArrayList<>();
            long currentTs = startTs;
            while (currentTs < endTs) {
                dailyTimestamps.add(currentTs);
                currentTs += Utils.TIME_DAY;
            }

            LOG.info("📦 Tổng số ngày cần xử lý: {}", dailyTimestamps.size());

            for (Long dayTs : dailyTimestamps) {
                executor.submit(() -> processOneDay(dayTs));
            }

            executor.shutdown();
            executor.awaitTermination(7, TimeUnit.DAYS);

            LOG.info("🎉 HOÀN TẤT CHUYỂN ĐỔI TOÀN BỘ DỮ LIỆU SANG NẾN 15M!");

        } catch (Exception e) {
            LOG.error("Lỗi Migration: ", e);
        } finally {
            if (client226 != null) client226.close();
            DataManagerAerospikeFloatSim.closeConnection();
        }
    }

    private static void processOneDay(long dayStartTs) {
        try {
            // Đọc nguyên 1 ngày nến 1m từ node .242
            TreeMap<Long, Map<String, KlineObjectSimple>> data1m =
                    DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(dayStartTs, 1440);

            if (data1m == null || data1m.isEmpty()) {
                return;
            }

            SimpleDateFormat keyFmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            int batch15mCount = 0;

            // Duyệt từng block 15 phút trong ngày (1440 / 15 = 96 block)
            for (long chunkStart = dayStartTs; chunkStart < dayStartTs + Utils.TIME_DAY; chunkStart += 15 * Utils.TIME_MINUTE) {

                // Map lưu nến 15m của block này (Dùng Short làm Key)
                Map<Short, KlineObjectSimple> kline15mMap = new HashMap<>();

                // Gom 15 cây nến 1m
                for (int i = 0; i < 15; i++) {
                    long minTs = chunkStart + (i * Utils.TIME_MINUTE);
                    Map<String, KlineObjectSimple> minData = data1m.get(minTs);

                    if (minData != null) {
                        for (Map.Entry<String, KlineObjectSimple> entry : minData.entrySet()) {
                            String symbol = entry.getKey();

                            // 🚀 QUAN TRỌNG: Cắt chữ USDT nếu có để map đúng chuẩn (hoặc ngược lại tùy cấu hình của bác)
                            String fullSymbol = symbol.endsWith("USDT") ? symbol : symbol + "USDT";
                            short symId = SimpleSymbolMapper.getInstance().getId(fullSymbol);

                            KlineObjectSimple k1 = entry.getValue();

                            // Logic gộp nến
                            KlineObjectSimple k15 = kline15mMap.computeIfAbsent(symId, k -> new KlineObjectSimple());

                            if (k15.startTime == null) {
                                k15.startTime = chunkStart;
                                k15.priceOpen = k1.priceOpen;
                                k15.maxPrice = k1.maxPrice;
                                k15.minPrice = k1.minPrice;
                            } else {
                                k15.maxPrice = Math.max(k15.maxPrice, k1.maxPrice);
                                k15.minPrice = Math.min(k15.minPrice, k1.minPrice);
                            }
                            k15.priceClose = k1.priceClose; // Cây 1m cuối cùng cập nhật sẽ là Close của 15m
                            k15.totalUsdt += k1.totalUsdt;
                        }
                    }
                }

                // Ghi xuống Aerospike .224 nếu block này có dữ liệu
                if (!kline15mMap.isEmpty()) {
                    String keyString = keyFmt.format(new Date(chunkStart));
                    Key asKey = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_TICKER_15M, keyString);

                    // Nén Binary Custom + Snappy
                    byte[] rawBytes = encodeKline15mMapToBinary(kline15mMap);
                    byte[] compressedBytes = Snappy.compress(rawBytes);

                    client226.put(writePolicy, asKey, new Bin("data", compressedBytes));
                    batch15mCount++;
                }
            }

            int count = daysProcessed.incrementAndGet();
            LOG.info("✅ Xong ngày {} | Tạo được {} block 15m | Tiến độ: {} days",
                    Utils.normalizeDateYYYYMMDD(dayStartTs), batch15mCount, count);

        } catch (Exception e) {
            LOG.error("Lỗi khi xử lý ngày " + Utils.normalizeDateYYYYMMDD(dayStartTs), e);
        }
    }

    /**
     * 🚀 TỐI ƯU CỰC ĐỘ: Custom Binary Codec cho nến 15M
     * Cấu trúc: [Số lượng (4 byte)] + Danh sách ( [Short ID (2 byte)] + [O,H,L,C,V (5 * 4 = 20 byte)] )
     */
    private static byte[] encodeKline15mMapToBinary(Map<Short, KlineObjectSimple> map) {
        if (map == null || map.isEmpty()) return new byte[0];

        // 4 bytes size + map.size() * (2 bytes Short + 20 bytes Float)
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
     * Hàm Decode (Bác có thể copy hàm này sang DataManagerAerospikeFloatSim để đọc nến 15m sau này)
     */
    public static Map<Short, KlineObjectSimple> decodeKline15mMapFromBinary(byte[] data, long chunkStartTs) {
        if (data == null || data.length == 0) return new HashMap<>();

        ByteBuffer buffer = ByteBuffer.wrap(data);
        int mapSize = buffer.getInt();

        Map<Short, KlineObjectSimple> map = new HashMap<>(mapSize);

        for (int i = 0; i < mapSize; i++) {
            short symId = buffer.getShort();
            KlineObjectSimple k = new KlineObjectSimple();
            k.startTime = chunkStartTs;
            k.priceOpen = buffer.getFloat();
            k.maxPrice = buffer.getFloat();
            k.minPrice = buffer.getFloat();
            k.priceClose = buffer.getFloat();
            k.totalUsdt = buffer.getFloat();

            map.put(symId, k);
        }

        return map;
    }
}