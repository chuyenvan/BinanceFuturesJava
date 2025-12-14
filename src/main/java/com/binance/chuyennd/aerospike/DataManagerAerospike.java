package com.binance.chuyennd.aerospike;
// Import Aerospike client

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.BatchPolicy;

// Import cac lop du an cua ban
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;

// Import cac lop Protobuf (tu Buoc 2 o tin nhan truoc)
import com.binance.chuyennd.proto.MinuteDataProto.MinuteData;
import com.binance.chuyennd.proto.MinuteDataProto.KlineObjectSimpleProto;
import com.google.protobuf.InvalidProtocolBufferException;
import org.xerial.snappy.Snappy;

import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

/**
 * Lop nay thay the DataManager, doc du lieu 1M (theo ngay) tu Aerospike
 * thay vi doc tu file.
 */
public class DataManagerAerospike {

    // --- Cau hinh Aerospike (phai giong file .conf) ---

    private static final String AEROSPIKE_SET_NAME = "kline_1m";
    // --------------------------------------------------

    // Dinh dang Key ma chung ta da dung de ghi


    // Tao mot client duy nhat (Singleton)
    private static volatile AerospikeClient client;

    // Chinh sach doc hang loat mac dinh
    private static final BatchPolicy batchPolicy = new BatchPolicy();
    private static final int BATCH_CHUNK_SIZE = 2000;
    // 2. Cấu hình Đa luồng (16 Threads)
    public static int threadCount = 3;
    public static ExecutorService executor = Executors.newFixedThreadPool(threadCount);
    /**
     * Khoi tao ket noi client
     */
    private static AerospikeClient getClient() {
        if (client == null) {
            synchronized (DataManagerAerospike.class) {
                if (client == null) {
                    System.out.println("Dang khoi tao ket noi Aerospike...");
                    client = new AerospikeClient(Configs.AEROSPIKE_HOST, Configs.AEROSPIKE_PORT);
                }
            }
        }
        return client;
    }

    /**
     * Ham chinh de thay the cho DataManager.readDataFromFile1M(startTime)
     * * @param startTime Thoi gian bat ky trong ngay muon doc
     *
     * @return Mot TreeMap chua toan bo 1440 phut cua ngay do
     */
    public static TreeMap<Long, Map<String, KlineObjectSimple>> readDataFromAerospike1M(long startTime) {
        // Map kết quả để trả về (TreeMap tự sắp xếp theo key)
        TreeMap<Long, Map<String, KlineObjectSimple>> results = new TreeMap<>();

        // 1. Tạo 1440 Keys và Timestamps cho cả ngày
        int totalRecords = 1440;
        Key[] allKeys = new Key[totalRecords];
        long[] allTimestamps = new long[totalRecords];

        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(startTime);
        cal.set(Calendar.HOUR_OF_DAY, 7);
        cal.set(Calendar.MINUTE, 0);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);

        for (int i = 0; i < totalRecords; i++) {
            String keyString = AerospikeConfigs.keyFormat.format(cal.getTime());
            allKeys[i] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME, keyString);
            allTimestamps[i] = cal.getTimeInMillis();
            cal.add(Calendar.MINUTE, 1);
        }


        List<Future<Map<Long, Map<String, KlineObjectSimple>>>> futures = new ArrayList<>();

        // Chia nhỏ mảng keys thành các chunk (mỗi chunk khoảng 90 key)
        int chunkSize = (totalRecords + threadCount - 1) / threadCount;

        for (int i = 0; i < threadCount; i++) {
            final int startIdx = i * chunkSize;
            final int endIdx = Math.min(startIdx + chunkSize, totalRecords);

            if (startIdx >= endIdx) break;

            // Submit task xử lý song song
            futures.add(executor.submit(() -> {
                Map<Long, Map<String, KlineObjectSimple>> chunkResult = new HashMap<>();
                try {
                    // Cắt mảng key và timestamp cho luồng này
                    Key[] chunkKeys = Arrays.copyOfRange(allKeys, startIdx, endIdx);
                    long[] chunkTimestamps = Arrays.copyOfRange(allTimestamps, startIdx, endIdx);

                    // Batch Read từ Aerospike cho chunk này
                    Record[] records = getClient().get(batchPolicy, chunkKeys);

                    // Xử lý giải nén và parse song song
                    for (int j = 0; j < records.length; j++) {
                        Record record = records[j];
                        if (record == null) continue;

                        long minuteTimestamp = chunkTimestamps[j];
                        byte[] snappyCompressedBytes = (byte[]) record.getValue("data");

                        if (snappyCompressedBytes != null) {
                            // Phần tốn CPU nhất nằm ở đây: Giải nén và Parse
                            byte[] protoAsBytes = Snappy.uncompress(snappyCompressedBytes);
                            MinuteData protoData = MinuteData.parseFrom(protoAsBytes);
                            Map<String, KlineObjectSimple> javaMap = convertProtoMapToJavaMap(protoData.getTickersMap());

                            chunkResult.put(minuteTimestamp, javaMap);
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
                return chunkResult;
            }));
        }

        // 3. Tổng hợp kết quả từ các luồng
        for (Future<Map<Long, Map<String, KlineObjectSimple>>> future : futures) {
            try {
                // get() sẽ đợi luồng chạy xong và lấy kết quả
                results.putAll(future.get());
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        return results;
    }

    public static TreeMap<Long, byte[]> readDataFromAerospike1MBytes(long startTime) {
        // Map kết quả để trả về (TreeMap tự sắp xếp theo key)
        TreeMap<Long, byte[]> results = new TreeMap<>();

        // 1. Tạo 1440 Keys và Timestamps cho cả ngày
        int totalRecords = 1440;
        Key[] allKeys = new Key[totalRecords];
        long[] allTimestamps = new long[totalRecords];

        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(startTime);
        cal.set(Calendar.HOUR_OF_DAY, 7);
        cal.set(Calendar.MINUTE, 0);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);

        for (int i = 0; i < totalRecords; i++) {
            String keyString = AerospikeConfigs.keyFormat.format(cal.getTime());
            allKeys[i] = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME, keyString);
            allTimestamps[i] = cal.getTimeInMillis();
            cal.add(Calendar.MINUTE, 1);
        }

        List<Future<Map<Long, byte[]>>> futures = new ArrayList<>();

        // Chia nhỏ mảng keys thành các chunk (mỗi chunk khoảng 90 key)
        int chunkSize = (totalRecords + threadCount - 1) / threadCount;

        for (int i = 0; i < threadCount; i++) {
            final int startIdx = i * chunkSize;
            final int endIdx = Math.min(startIdx + chunkSize, totalRecords);

            if (startIdx >= endIdx) break;

            // Submit task xử lý song song
            futures.add(executor.submit(() -> {
                Map<Long, byte[]> chunkResult = new HashMap<>();
                try {
                    // Cắt mảng key và timestamp cho luồng này
                    Key[] chunkKeys = Arrays.copyOfRange(allKeys, startIdx, endIdx);
                    long[] chunkTimestamps = Arrays.copyOfRange(allTimestamps, startIdx, endIdx);

                    // Batch Read từ Aerospike cho chunk này
                    Record[] records = getClient().get(batchPolicy, chunkKeys);

                    // Chỉ lấy raw bytes, không giải nén/parse
                    for (int j = 0; j < records.length; j++) {
                        Record record = records[j];
                        if (record == null) continue;

                        long minuteTimestamp = chunkTimestamps[j];
                        byte[] snappyCompressedBytes = (byte[]) record.getValue("data");

                        if (snappyCompressedBytes != null) {
                            chunkResult.put(minuteTimestamp, snappyCompressedBytes);
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
                return chunkResult;
            }));
        }

        // 3. Tổng hợp kết quả từ các luồng
        for (Future<Map<Long, byte[]>> future : futures) {
            try {
                results.putAll(future.get());
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        return results;
    }

    /**
     * Ham ho tro: Chuyen doi Map (Protobuf) sang Map (Java)
     */
    public static Map<String, KlineObjectSimple> convertProtoMapToJavaMap(Map<String, KlineObjectSimpleProto> protoMap) {

        Map<String, KlineObjectSimple> javaMap = new HashMap<>(protoMap.size());

        for (Map.Entry<String, KlineObjectSimpleProto> entry : protoMap.entrySet()) {
            String symbol = entry.getKey();
            KlineObjectSimpleProto protoTicker = entry.getValue();

            // Chuyen doi: Proto -> Java
            KlineObjectSimple javaTicker = new KlineObjectSimple();
            javaTicker.startTime = protoTicker.getStartTime();
            javaTicker.priceOpen = protoTicker.getPriceOpen();
            javaTicker.maxPrice = protoTicker.getMaxPrice();
            javaTicker.minPrice = protoTicker.getMinPrice();
            javaTicker.priceClose = protoTicker.getPriceClose();
            javaTicker.totalUsdt = protoTicker.getTotalUsdt();

            javaMap.put(symbol, javaTicker);
        }
        return javaMap;
    }
    /**
     * Ham doc 7 ngay (10,080 phut) (cho LabelSimulator)
     * (DA SUA LOI: Them logic chia nho - "Chunking")
     */
    public static TreeMap<Long, KlineObjectSimple> readDataForPeriod(String symbol, long startTime, long endTime) {

        TreeMap<Long, KlineObjectSimple> results = new TreeMap<>();

        // 1. Tinh toan so luong phut can doc (vi du: 10080)
        int minutesToRead = (int) ((endTime - startTime) / Utils.TIME_MINUTE) + 1;
        if (minutesToRead <= 0) return results;

        // 2. Tao danh sach TOAN BO Keys (vi du: 10080 keys)
        List<Key> allKeys = new ArrayList<>(minutesToRead);
        List<Long> allTimestamps = new ArrayList<>(minutesToRead);

        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(startTime);

        for (int i = 0; i < minutesToRead; i++) {
            String keyString = AerospikeConfigs.keyFormat.format(cal.getTime());
            allKeys.add(new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME, keyString));
            allTimestamps.add(cal.getTimeInMillis());
            cal.add(Calendar.MINUTE, 1);
        }

        try {
            // 3. === LOGIC MOI: CHIA NHO (CHUNK) 10080 KEYS ===
            // Lap qua danh sach keys, moi lan lay 2000 (BATCH_CHUNK_SIZE)
            for (int i = 0; i < allKeys.size(); i += BATCH_CHUNK_SIZE) {

                // Tinh toan diem bat dau va ket thuc cua "chunk"
                int endIndex = Math.min(i + BATCH_CHUNK_SIZE, allKeys.size());

                // Lay 1 "chunk" (vi du: 0-1999, 2000-3999, ... , 10000-10080)
                List<Key> keyChunk = allKeys.subList(i, endIndex);
                List<Long> timestampChunk = allTimestamps.subList(i, endIndex);

                // 4. Thuc hien Batch Read CHỈ TRÊN CHUNK do
                Record[] records = getClient().get(batchPolicy, keyChunk.toArray(new Key[0]));

                // 5. Xu ly ket qua (giong het code cu)
                for (int j = 0; j < records.length; j++) {
                    Record record = records[j];
                    if (record == null) {
                        continue;
                    }

                    long minuteTimestamp = timestampChunk.get(j); // Lay timestamp tuong ung

                    byte[] snappyCompressedBytes = (byte[]) record.getValue("data");

                    if (snappyCompressedBytes != null && snappyCompressedBytes.length > 0) {
                        byte[] protoAsBytes = Snappy.uncompress(snappyCompressedBytes);
                        MinuteData protoData = MinuteData.parseFrom(protoAsBytes);
                        Map<String, KlineObjectSimpleProto> protoMap = protoData.getTickersMap();

                        if (protoMap.containsKey(symbol)) {
                            KlineObjectSimple javaKline = convertProtoToKline(protoMap.get(symbol));
                            results.put(minuteTimestamp, javaKline);
                        }
                    }
                }
            } // Ket thuc vong lap "chunk"

        } catch (Exception e) {
            System.err.println("Loi khi doc batch read (readDataForPeriod) cho symbol " + symbol + ":");
            e.printStackTrace(); // In ra loi (vi du: "Batch max requests")
        }

        return results;
    }

    /**
     * Ham ho tro: Chuyen 1 Proto Kline -> 1 Java Kline
     */
    private static KlineObjectSimple convertProtoToKline(KlineObjectSimpleProto protoTicker) {
        KlineObjectSimple javaTicker = new KlineObjectSimple();
        javaTicker.startTime = protoTicker.getStartTime();
        javaTicker.priceOpen = protoTicker.getPriceOpen();
        javaTicker.maxPrice = protoTicker.getMaxPrice();
        javaTicker.minPrice = protoTicker.getMinPrice();
        javaTicker.priceClose = protoTicker.getPriceClose();
        javaTicker.totalUsdt = protoTicker.getTotalUsdt();
        return javaTicker;
    }
    /**
     * (Tuy chon) Ham de dong ket noi khi ung dung tat
     */
    public static void closeConnection() {
        if (client != null) {
            client.close();
        }
    }
    public static void writeDataToAerospike(String keyString, byte[] compressedData) {
        try {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME, keyString);
            Bin bin = new Bin("data", compressedData);
            getClient().put(AerospikeConfigs.writePolicy, key, bin);
        } catch (Exception e) {
            System.err.println("Loi khi ghi du lieu vao Aerospike voi key: " + keyString);
            e.printStackTrace();
        }
    }
    // Thêm vào DataManagerAerospike.java

    // Hàm mới để ghi vào set tối ưu
    public static void writeDataToAerospikeOptimized(String keyString, byte[] compressedData) {
        try {
            // Sử dụng tên SET mới: kline_1m_opt
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, "kline_1m_opt", keyString);
            Bin bin = new Bin("data", compressedData);
            getClient().put(AerospikeConfigs.writePolicy, key, bin);
        } catch (Exception e) {
            System.err.println("Loi khi ghi du lieu vao Aerospike Opt voi key: " + keyString);
            e.printStackTrace();
        }
    }
}