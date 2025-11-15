package com.binance.chuyennd.aerospike;
// Import Aerospike client

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.BatchPolicy;

// Import cac lop du an cua ban
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;

// Import cac lop Protobuf (tu Buoc 2 o tin nhan truoc)
import com.binance.chuyennd.proto.MinuteDataProto.MinuteData;
import com.binance.chuyennd.proto.MinuteDataProto.KlineObjectSimpleProto;
import com.google.protobuf.InvalidProtocolBufferException;
import org.xerial.snappy.Snappy;

import java.text.SimpleDateFormat;
import java.util.*;

/**
 * Lop nay thay the DataManager, doc du lieu 1M (theo ngay) tu Aerospike
 * thay vi doc tu file.
 */
public class DataManagerAerospike {

    // --- Cau hinh Aerospike (phai giong file .conf) ---
    private static final String AEROSPIKE_HOST = "127.0.0.1";
    private static final int AEROSPIKE_PORT = 3000;
    private static final String AEROSPIKE_NAMESPACE = "ticker";
    private static final String AEROSPIKE_SET_NAME = "kline_1m";
    // --------------------------------------------------

    // Dinh dang Key ma chung ta da dung de ghi
    private static final SimpleDateFormat keyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");

    // Tao mot client duy nhat (Singleton)
    private static volatile AerospikeClient client;

    // Chinh sach doc hang loat mac dinh
    private static final BatchPolicy batchPolicy = new BatchPolicy();
    private static final int BATCH_CHUNK_SIZE = 2000;

    /**
     * Khoi tao ket noi client
     */
    private static AerospikeClient getClient() {
        if (client == null) {
            synchronized (DataManagerAerospike.class) {
                if (client == null) {
                    System.out.println("Dang khoi tao ket noi Aerospike...");
                    client = new AerospikeClient(AEROSPIKE_HOST, AEROSPIKE_PORT);
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

//        System.out.println("Doc du lieu Aerospike cho ngay: " + Utils.normalizeDateYYYYMMDD(startTime));

        // Map ket qua de tra ve
        TreeMap<Long, Map<String, KlineObjectSimple>> results = new TreeMap<>();

        // 1. Tao 1440 Keys va Timestamps cho ca ngay
        Key[] keys = new Key[1440];
        long[] timestamps = new long[1440];

        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(startTime);
        cal.set(Calendar.HOUR_OF_DAY, 7);
        cal.set(Calendar.MINUTE, 0);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);

        for (int i = 0; i < 1440; i++) {
            String keyString = keyFormat.format(cal.getTime());
            keys[i] = new Key(AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME, keyString);
            timestamps[i] = cal.getTimeInMillis();
            cal.add(Calendar.MINUTE, 1);
        }

        try {
            // 2. Thuc hien 1 lenh Batch Read duy nhat
            Record[] records = getClient().get(batchPolicy, keys);

            // 3. Xu ly ket qua
            for (int i = 0; i < records.length; i++) {
                Record record = records[i];

                // Neu record la null, nghia la khong co data cho phut do -> bo qua
                if (record == null) {
                    continue;
                }

                // Lay timestamp cua phut nay
                long minuteTimestamp = timestamps[i];

                // Lay du lieu byte[] tu bin "data"
                byte[] snappyCompressedBytes = (byte[]) record.getValue("data");
                if (snappyCompressedBytes != null) {
                    byte[] protoAsBytes = Snappy.uncompress(snappyCompressedBytes);
                    // Giai ma Protobuf
                    MinuteData protoData = MinuteData.parseFrom(protoAsBytes);

                    // Chuyen doi Proto Map -> Java Map
                    Map<String, KlineObjectSimple> javaMap = convertProtoMapToJavaMap(protoData.getTickersMap());

                    // Dat vao ket qua
                    results.put(minuteTimestamp, javaMap);
                }
            }

        } catch (InvalidProtocolBufferException e) {
            System.err.println("Loi nghiem trong: Khong the giai ma Protobuf!");
            e.printStackTrace();
        } catch (Exception e) {
            System.err.println("Loi khi doc batch read tu Aerospike:");
            e.printStackTrace();
        }

//        System.out.println("Doc xong. Tim thay " + results.size() + " phut du lieu trong Aerospike.");
        return results;
    }

    /**
     * Ham ho tro: Chuyen doi Map (Protobuf) sang Map (Java)
     */
    private static Map<String, KlineObjectSimple> convertProtoMapToJavaMap(Map<String, KlineObjectSimpleProto> protoMap) {

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
            String keyString = keyFormat.format(cal.getTime());
            allKeys.add(new Key(AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME, keyString));
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
}