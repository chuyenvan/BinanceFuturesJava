package com.binance.chuyennd.aerospike;

// Import Aerospike client
import com.aerospike.client.AerospikeClient;
import com.aerospike.client.AerospikeException; // <-- NHAP IMPORT MOI
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.policy.WritePolicy;

// Import cac lop du an cua ban
import com.binance.chuyennd.bigchange.data.DataManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.proto.MinuteDataProto;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import org.xerial.snappy.Snappy;

// Import cac lop Protobuf
import java.text.SimpleDateFormat;
import java.util.Calendar; // <-- NHAP IMPORT MOI
import java.util.Map;
import java.util.TreeMap;

import static com.binance.chuyennd.proto.MinuteDataProto.*;

/**
 * Lop nay doc du lieu tu cac file snappy va ghi vao Aerospike theo tung phut.
 * DA CAP NHAT: Kiem tra su ton tai cua du lieu truoc khi ghi.
 */
public class DataMigratorToAerospike {

    // --- Cau hinh Aerospike (theo file config cua ban) ---
    private static AerospikeClient client;
    private static final String AEROSPIKE_HOST = "127.0.0.1";
    private static final int AEROSPIKE_PORT = 3000;
    private static final String AEROSPIKE_NAMESPACE = "ticker"; // <--- Tu file config
    private static final String AEROSPIKE_SET_NAME = "kline_1m"; // <--- Ten chung ta tu dat
    // --------------------------------------------------

    private static final SimpleDateFormat keyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");
    private static final WritePolicy writePolicy = new WritePolicy();

    /**
     * Ham chinh de chay
     */
    public static void main(String[] args) {
        try {
            connectToAerospike();
            migrateData();
        } catch (Exception e) {
            System.err.println("Gap loi nghiem trong trong qua trinh di tru:");
            e.printStackTrace();
        } finally {
            disconnectFromAerospike();
        }
    }

    // ... (ham connectToAerospike va disconnectFromAerospike giu nguyen) ...
    private static void connectToAerospike() {
        System.out.println("Dang ket noi den Aerospike tai " + AEROSPIKE_HOST + "...");
        client = new AerospikeClient(AEROSPIKE_HOST, AEROSPIKE_PORT);
        if (client.isConnected()) {
            System.out.println("Ket noi Aerospike thanh cong.");
        } else {
            throw new RuntimeException("Khong the ket noi den Aerospike. Hay kiem tra server!");
        }
    }

    private static void disconnectFromAerospike() {
        if (client != null) {
            client.close();
            System.out.println("Da ngat ket noi Aerospike.");
        }
    }


    /**
     * Logic chinh: Doc file -> Ghi DB (DA CAP NHAT)
     */
    private static void migrateData() throws Exception {
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        long endTime = System.currentTimeMillis();

        while (startTime < endTime) {
            String ngayHienTai = Utils.normalizeDateYYYYMMDD(startTime);
            System.out.println("\n--- Dang xu ly ngay: " + ngayHienTai + " ---");

            // === BAT DAU: PHAN KIEM TRA (CHECK) MOI ===
            try {
                // 1. Tao key cho phut dau tien cua ngay (00:00) de kiem tra
                Calendar cal = Calendar.getInstance();
                cal.setTimeInMillis(startTime);
                cal.set(Calendar.HOUR_OF_DAY, 23);
                cal.set(Calendar.MINUTE, 59);
                String firstKeyString = keyFormat.format(cal.getTime());
                Key firstKey = new Key(AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME, firstKeyString);

                // 2. Kiem tra xem key nay da ton tai chua (dung client.exists)
                System.out.println("Kiem tra su ton tai cua key: " + firstKeyString);
                boolean exists = client.exists(null, firstKey); // Dung read policy mac dinh (null)

                // 3. Neu da ton tai, bo qua ngay nay
                if (exists) {
                    System.out.println("=> Du lieu cho ngay " + ngayHienTai + " da ton tai. Bo qua.");
                    startTime += Utils.TIME_DAY;
                    continue; // Chuyen sang ngay tiep theo
                }

                System.out.println("=> Du lieu chua ton tai. Bat dau doc file de di tru...");

            } catch (Exception e) {
                System.err.println("Loi khi kiem tra su ton tai cua key: " + e.getMessage());
                e.printStackTrace();
                break; // Thoat khoi vong while
            }
            // === KET THUC: PHAN KIEM TRA (CHECK) MOI ===


            // 1. DOC DU LIEU TU FILE (Giong code cu)
            System.out.println("Dang doc file DataManager.readDataFromFile1M...");
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            time2Tickers = DataManager.readDataFromFile1M(startTime);

            if (time2Tickers == null || time2Tickers.isEmpty()) {
                System.out.println("Khong co du lieu file cho ngay nay, bo qua.");
                startTime += Utils.TIME_DAY;
                continue;
            }

            System.out.println("Doc thanh cong " + time2Tickers.size() + " phut du lieu. Bat dau ghi vao Aerospike...");

            int counter = 0;
            boolean hasErrorThisDay = false; // Co de theo doi loi trong ngay

            // 2. LAP QUA TUNG PHUT VA GHI VAO AEROSPIKE
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> minuteEntry : time2Tickers.entrySet()) {
                Long minuteTimestamp = minuteEntry.getKey();
                Map<String, KlineObjectSimple> minuteDataMap = minuteEntry.getValue();
                String keyString = null; // Dinh nghia o ngoai de log loi

                try {
                    // 2a. Chuyen Map thanh Protobuf byte[]
                    byte[] protoAsBytes = convertMapToProtoBytes(minuteDataMap);
                    // 2b. Nen mang byte[] Protobuf bang Snappy
                    byte[] snappyCompressedBytes = Snappy.compress(protoAsBytes);

                    // 2b. Tao Key
                    keyString = keyFormat.format(new java.util.Date(minuteTimestamp));
                    Key key = new Key(AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME, keyString);

                    // 2c. Tao Bin
                    Bin dataBin = new Bin("data", snappyCompressedBytes);

                    // 2d. Ghi vao Database
                    client.put(writePolicy, key, dataBin);
                    counter++;

                }
                // === BAT DAU: PHAN KIEM TRA (CHECK) KHI GHI ===
                catch (AerospikeException ae) {
                    // Day chinh la "check" - neu .put() that bai, no se vang loi o day
                    System.err.println("!!! LOI KHI GHI KEY: " + keyString + " !!!");
                    System.err.println("Ma loi Aerospike (ResultCode): " + ae.getResultCode());
                    System.err.println("Thong diep: " + ae.getMessage());
                    hasErrorThisDay = true;
                    break; // Dung ghi ngay nay lai
                } catch (Exception e) {
                    // Loi khac (vi du: Loi Protobuf)
                    System.err.println("Loi xu ly du lieu cho key " + keyString + ": " + e.getMessage());
                    hasErrorThisDay = true;
                    break; // Dung ghi ngay nay lai
                }
                // === KET THUC: PHAN KIEM TRA (CHECK) KHI GHI ===
            }

            // Neu ngay hien tai bi loi, dung toan bo script
            if (hasErrorThisDay) {
                System.err.println("Da xay ra loi trong qua trinh ghi ngay " + ngayHienTai + ". DUNG chuong trinh di tru.");
                break; // Thoat khoi while loop
            }

            System.out.println("Ghi thanh cong " + counter + " ban ghi (phut) vao Aerospike.");

            // Chuyen sang ngay tiep theo
            startTime += Utils.TIME_DAY;
        }
        System.out.println("\n--- HOAN TAT TOAN BO QUA TRINH DI TRU DU LIEU ---");
    }

    /**
     * Ham ho tro: Chuyen doi Map Java (code cua ban) sang mang byte[] (Protobuf)
     */
    private static byte[] convertMapToProtoBytes(Map<String, KlineObjectSimple> javaMap) {
        // ... (Ham nay giu nguyen nhu cu) ...
        MinuteData.Builder minuteBuilder = MinuteData.newBuilder();
        for (Map.Entry<String, KlineObjectSimple> entry : javaMap.entrySet()) {
            String symbol = entry.getKey();
            KlineObjectSimple javaTicker = entry.getValue();
            KlineObjectSimpleProto.Builder protoTickerBuilder = KlineObjectSimpleProto.newBuilder()
                    .setStartTime(javaTicker.startTime)
                    .setPriceOpen(javaTicker.priceOpen)
                    .setMaxPrice(javaTicker.maxPrice)
                    .setMinPrice(javaTicker.minPrice)
                    .setPriceClose(javaTicker.priceClose)
                    .setTotalUsdt(javaTicker.totalUsdt);
            minuteBuilder.putTickers(symbol, protoTickerBuilder.build());
        }
        return minuteBuilder.build().toByteArray();
    }
}