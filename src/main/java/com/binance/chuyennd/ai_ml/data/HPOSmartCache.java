package com.binance.chuyennd.ai_ml.data;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.io.*;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Cache thông minh (Optimized & Deterministic Version).
 * - Sử dụng TreeMap để đảm bảo thứ tự Symbol (A->Z).
 * - Chuyển Double -> Float để tiết kiệm RAM.
 * - [MỚI] Map String Symbol -> Short ID để tối ưu kích thước cache.
 * - Loại bỏ startTime thừa trong object con.
 * - Nén Snappy.
 */
public class HPOSmartCache {

    private static final Logger LOG = LoggerFactory.getLogger(HPOSmartCache.class);

    // Key: StartTime của ngày (Long)
    // Value: Byte array nén (Float data + Symbol Short ID)
    private static final ConcurrentHashMap<Long, byte[]> MEMORY_CACHE = new ConcurrentHashMap<>();

    public static TreeMap<Long, Map<String, KlineObjectSimple>> getData(long startTime) {

        // 1. Kiểm tra Cache RAM
        if (MEMORY_CACHE.containsKey(startTime)) {
            try {
                // LOG.info("HIT CACHE (Optimized): {}", startTime);
                return deserializeAndDecompress(MEMORY_CACHE.get(startTime));
            } catch (IOException e) {
                LOG.error("CACHE CORRUPT: " + startTime, e);
            }
        }

        // 2. Cache Miss -> Đọc từ Aerospike
        TreeMap<Long, Map<String, KlineObjectSimple>> data = DataManagerAerospikeFloatSim.readDataFromAerospike1M(startTime);

        if (data != null && !data.isEmpty()) {
            // QUAN TRỌNG: Vẫn phải normalize về TreeMap để đảm bảo thứ tự A-Z
            data = normalizeToTreeMap(data);

            try {
                // Nén tối ưu (Float + No StartTime + Symbol Mapping)
                byte[] compressed = serializeAndCompress(data);
                MEMORY_CACHE.put(startTime, compressed);
            } catch (Exception e) {
                LOG.error("CACHE WRITE ERROR", e);
            }
        }

        return data;
    }

    /**
     * Chuyển đổi toàn bộ Map con thành TreeMap để đảm bảo thứ tự duyệt Symbol luôn là A->Z
     */
    private static TreeMap<Long, Map<String, KlineObjectSimple>> normalizeToTreeMap(TreeMap<Long, Map<String,
            KlineObjectSimple>> original) {
        TreeMap<Long, Map<String, KlineObjectSimple>> sortedData = new TreeMap<>();
        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : original.entrySet()) {
            sortedData.put(entry.getKey(), new TreeMap<>(entry.getValue()));
        }
        return sortedData;
    }

    /**
     * Ghi dữ liệu: Ép kiểu Float, BỎ startTime, và dùng Short ID cho Symbol
     */
    private static byte[] serializeAndCompress(TreeMap<Long, Map<String, KlineObjectSimple>> data) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        DataOutputStream dos = new DataOutputStream(baos);

        dos.writeInt(data.size());

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : data.entrySet()) {
            Long timeKey = entry.getKey();
            dos.writeLong(timeKey); // Chỉ ghi timeKey 1 lần cho cả phút đó

            Map<String, KlineObjectSimple> tickers = entry.getValue();
            dos.writeInt(tickers.size());

            // Duyệt theo thứ tự A-Z (do đã normalize)
            for (Map.Entry<String, KlineObjectSimple> tickerEntry : tickers.entrySet()) {

                // --- TỐI ƯU HÓA Ở ĐÂY ---
                // Thay vì ghi String (tốn kém), ta lấy ID và ghi Short
                String symbol = tickerEntry.getKey();
                short symbolId = SimpleSymbolMapper.getId(symbol);
                dos.writeShort(symbolId);
                // ------------------------

                KlineObjectSimple kline = tickerEntry.getValue();

                // TỐI ƯU: Ghi Float (4 bytes) thay vì Double (8 bytes)
                // KHÔNG ghi kline.startTime nữa
                dos.writeFloat(kline.priceOpen.floatValue());
                dos.writeFloat(kline.maxPrice.floatValue());
                dos.writeFloat(kline.minPrice.floatValue());
                dos.writeFloat(kline.priceClose.floatValue());
                dos.writeFloat(kline.totalUsdt.floatValue());
            }
        }
        dos.flush();
        return Snappy.compress(baos.toByteArray());
    }

    /**
     * Đọc dữ liệu: Đọc Short ID -> Map ra String, Đọc Float -> Cast về Double
     */
    private static TreeMap<Long, Map<String, KlineObjectSimple>> deserializeAndDecompress(byte[] compressedData) throws IOException {
        byte[] uncompressed = Snappy.uncompress(compressedData);
        ByteArrayInputStream bais = new ByteArrayInputStream(uncompressed);
        DataInputStream dis = new DataInputStream(bais);

        TreeMap<Long, Map<String, KlineObjectSimple>> result = new TreeMap<>();

        int size = dis.readInt();
        for (int i = 0; i < size; i++) {
            long timeKey = dis.readLong(); // Đọc timeKey chung
            double timeKeyDouble = (double) timeKey; // Chuẩn bị để inject

            int tickerCount = dis.readInt();

            // QUAN TRỌNG: Vẫn dùng TreeMap để Output đảm bảo thứ tự A-Z
            Map<String, KlineObjectSimple> tickerMap = new TreeMap<>();

            for (int j = 0; j < tickerCount; j++) {

                // --- TỐI ƯU HÓA Ở ĐÂY ---
                // Đọc Short ID và convert ngược lại thành String Symbol
                short symbolId = dis.readShort();
                String symbol = SimpleSymbolMapper.getSymbol(symbolId);
                // ------------------------

                // Đọc Float
                float open = dis.readFloat();
                float max = dis.readFloat();
                float min = dis.readFloat();
                float close = dis.readFloat();
                float total = dis.readFloat();

                // Tái tạo Object (Cast về Double)
                KlineObjectSimple kline = new KlineObjectSimple();
                kline.startTime = timeKeyDouble; // Inject startTime từ key
                kline.priceOpen = (double) open;
                kline.maxPrice = (double) max;
                kline.minPrice = (double) min;
                kline.priceClose = (double) close;
                kline.totalUsdt = (double) total;

                tickerMap.put(symbol, kline);
            }
            result.put(timeKey, tickerMap);
        }
        return result;
    }

    public static void clearCache() {
        MEMORY_CACHE.clear();
    }
}