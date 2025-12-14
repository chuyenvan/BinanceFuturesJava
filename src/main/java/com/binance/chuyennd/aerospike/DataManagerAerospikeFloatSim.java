package com.binance.chuyennd.aerospike;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.BatchPolicy;

// Import Object Java cũ
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;

// --- QUAN TRỌNG: Import Proto MỚI (Float + No Time) ---
import com.binance.chuyennd.proto.MinuteDataFinalProto.MinuteDataFinal;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;

import org.xerial.snappy.Snappy;

import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

public class DataManagerAerospikeFloatSim {

    // --- CẤU HÌNH ---
    // Đổi sang Set mới đã tối ưu
    private static final String AEROSPIKE_SET_NAME = "kline_1m_opt";

    private static volatile AerospikeClient client;
    private static final BatchPolicy batchPolicy = new BatchPolicy();
    private static final int BATCH_CHUNK_SIZE = 2000;

    // Cấu hình đa luồng
    public static int threadCount = 2;
    public static ExecutorService executor = Executors.newFixedThreadPool(threadCount);

    private static AerospikeClient getClient() {
        if (client == null) {
            synchronized (DataManagerAerospike.class) {
                if (client == null) {
                    client = new AerospikeClient(Configs.AEROSPIKE_HOST, Configs.AEROSPIKE_PORT);
                }
            }
        }
        return client;
    }

    /**
     * Đọc dữ liệu toàn bộ thị trường trong 1 ngày (1440 phút)
     */
    public static TreeMap<Long, Map<String, KlineObjectSimple>> readDataFromAerospike1M(long startTime) {
        TreeMap<Long, Map<String, KlineObjectSimple>> results = new TreeMap<>();
        int totalRecords = 1440;

        // Tạo Key và Timestamp
        long[] allTimestamps = new long[totalRecords];
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(startTime);
        cal.set(Calendar.HOUR_OF_DAY, 7);
        cal.set(Calendar.MINUTE, 0);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);

        for (int i = 0; i < totalRecords; i++) {
            allTimestamps[i] = cal.getTimeInMillis();
            cal.add(Calendar.MINUTE, 1);
        }

        List<Future<Map<Long, Map<String, KlineObjectSimple>>>> futures = new ArrayList<>();
        int chunkSize = (totalRecords + threadCount - 1) / threadCount;

        for (int i = 0; i < threadCount; i++) {
            final int startIdx = i * chunkSize;
            final int endIdx = Math.min(startIdx + chunkSize, totalRecords);
            if (startIdx >= endIdx) break;

            futures.add(executor.submit(() -> {
                // --- FIX THREAD SAFETY: Tạo SimpleDateFormat riêng cho từng luồng ---
                SimpleDateFormat localKeyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");

                Map<Long, Map<String, KlineObjectSimple>> chunkResult = new HashMap<>();
                try {
                    // Tạo Keys cho chunk này
                    Key[] chunkKeys = new Key[endIdx - startIdx];
                    long[] chunkTimestamps = Arrays.copyOfRange(allTimestamps, startIdx, endIdx);

                    for (int k = 0; k < chunkKeys.length; k++) {
                        String keyString = localKeyFormat.format(new Date(chunkTimestamps[k]));
                        chunkKeys[k] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME, keyString);
                    }

                    // Batch Read
                    Record[] records = getClient().get(batchPolicy, chunkKeys);

                    for (int j = 0; j < records.length; j++) {
                        Record record = records[j];
                        if (record == null) continue;

                        // Lấy timestamp từ mảng (Vì trong Data không còn lưu timestamp nữa)
                        long minuteTimestamp = chunkTimestamps[j];

                        byte[] snappyCompressedBytes = (byte[]) record.getValue("data");
                        if (snappyCompressedBytes != null) {
                            byte[] protoAsBytes = Snappy.uncompress(snappyCompressedBytes);

                            // --- DÙNG PROTO MỚI ---
                            MinuteDataFinal protoData = MinuteDataFinal.parseFrom(protoAsBytes);

                            // Convert và truyền timestamp vào
                            Map<String, KlineObjectSimple> javaMap = convertProtoMapToJavaMap(protoData.getTickersMap(), minuteTimestamp);
                            chunkResult.put(minuteTimestamp, javaMap);
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
                return chunkResult;
            }));
        }

        // Tổng hợp kết quả
        for (Future<Map<Long, Map<String, KlineObjectSimple>>> future : futures) {
            try {
                results.putAll(future.get());
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return results;
    }

    /**
     * Đọc dữ liệu lịch sử của 1 Symbol cụ thể
     */
    public static TreeMap<Long, KlineObjectSimple> readDataForPeriod(String symbol, long startTime, long endTime) {
        TreeMap<Long, KlineObjectSimple> results = new TreeMap<>();

        // Xử lý Symbol: Vì DB lưu "BTC" mà input là "BTCUSDT", ta cần cắt đuôi
        final String shortSymbol = symbol.endsWith("USDT") ? symbol.substring(0, symbol.length() - 4) : symbol;

        int minutesToRead = (int) ((endTime - startTime) / Utils.TIME_MINUTE) + 1;
        if (minutesToRead <= 0) return results;

        List<Long> allTimestamps = new ArrayList<>(minutesToRead);
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(startTime);
        for (int i = 0; i < minutesToRead; i++) {
            allTimestamps.add(cal.getTimeInMillis());
            cal.add(Calendar.MINUTE, 1);
        }

        try {
            // Chia nhỏ request (Chunking)
            for (int i = 0; i < allTimestamps.size(); i += BATCH_CHUNK_SIZE) {
                int endIndex = Math.min(i + BATCH_CHUNK_SIZE, allTimestamps.size());
                List<Long> timestampChunk = allTimestamps.subList(i, endIndex);

                // Tạo Keys (Dùng Local Formatter)
                SimpleDateFormat localKeyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");
                Key[] keyChunk = new Key[timestampChunk.size()];
                for (int k = 0; k < timestampChunk.size(); k++) {
                    String keyString = localKeyFormat.format(new Date(timestampChunk.get(k)));
                    keyChunk[k] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME, keyString);
                }

                Record[] records = getClient().get(batchPolicy, keyChunk);

                for (int j = 0; j < records.length; j++) {
                    Record record = records[j];
                    if (record == null) continue;

                    long minuteTimestamp = timestampChunk.get(j);
                    byte[] snappyCompressedBytes = (byte[]) record.getValue("data");

                    if (snappyCompressedBytes != null && snappyCompressedBytes.length > 0) {
                        byte[] protoAsBytes = Snappy.uncompress(snappyCompressedBytes);

                        // --- DÙNG PROTO MỚI ---
                        MinuteDataFinal protoData = MinuteDataFinal.parseFrom(protoAsBytes);
                        Map<String, KlineObjectOptimized> protoMap = protoData.getTickersMap();

                        // Tìm theo Short Symbol (ví dụ "BTC")
                        if (protoMap.containsKey(shortSymbol)) {
                            KlineObjectSimple javaKline = convertProtoToKline(protoMap.get(shortSymbol), minuteTimestamp);
                            results.put(minuteTimestamp, javaKline);
                        }
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return results;
    }

    // =========================================================================
    // LOGIC CONVERT MỚI (FLOAT -> DOUBLE, APPEND USDT, INJECT TIME)
    // =========================================================================

    public static Map<String, KlineObjectSimple> convertProtoMapToJavaMap(Map<String, KlineObjectOptimized> protoMap, long timestamp) {
        Map<String, KlineObjectSimple> javaMap = new HashMap<>(protoMap.size());

        for (Map.Entry<String, KlineObjectOptimized> entry : protoMap.entrySet()) {
            String shortSymbol = entry.getKey(); // Đang là "BTC"
            KlineObjectOptimized protoTicker = entry.getValue();

            // 1. Khôi phục tên đầy đủ: BTC -> BTCUSDT

            String fullSymbol = shortSymbol;

            // 2. Convert Object
            javaMap.put(fullSymbol, convertProtoToKline(protoTicker, timestamp));
        }
        return javaMap;
    }

    private static KlineObjectSimple convertProtoToKline(KlineObjectOptimized protoTicker, long timestamp) {
        KlineObjectSimple javaTicker = new KlineObjectSimple();

        // 1. INJECT TIMESTAMP TỪ BÊN NGOÀI VÀO (Vì trong DB không còn lưu nữa)
        // Ép kiểu về double theo đúng định nghĩa class cũ của bạn
        javaTicker.startTime = (double) timestamp;

        // 2. ÉP KIỂU FLOAT (DB) -> DOUBLE (JAVA)
        javaTicker.priceOpen = (double) protoTicker.getPriceOpen();
        javaTicker.maxPrice = (double) protoTicker.getMaxPrice();
        javaTicker.minPrice = (double) protoTicker.getMinPrice();
        javaTicker.priceClose = (double) protoTicker.getPriceClose();
        javaTicker.totalUsdt = (double) protoTicker.getTotalUsdt();

        return javaTicker;
    }

    public static void closeConnection() {
        if (client != null) {
            client.close();
        }
    }
}