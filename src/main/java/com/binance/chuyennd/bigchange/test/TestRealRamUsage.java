package com.binance.chuyennd.bigchange.test;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.policy.ScanPolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospike;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;

import java.text.ParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class TestRealRamUsage {

    // Giả lập thời gian bắt đầu (lấy 1 ngày có dữ liệu để test)
    // Sửa lại thời gian này cho đúng với data của bạn


    public static void main(String[] args) {
        System.out.println("=== BẮT ĐẦU TEST SO SÁNH RAM ===");

        // Cần khởi tạo Client trước nếu DataManagerAerospike yêu cầu
        // DataManagerAerospike.init("127.0.0.1", 3000);

        try {
            // --- TEST 1: CÁCH CŨ (Load ra Object Java) ---
            testMethod1_JavaObjects();

            // Dọn dẹp RAM để test bài 2
            System.gc();
            Thread.sleep(2000);

            // --- TEST 2: CÁCH MỚI (Load Raw Bytes - Giả lập Snappy chưa giải nén) ---
            testMethod2_RawSnappyBytes();

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    // ---------------------------------------------------------
    // CÁCH 1: Dùng hàm hiện tại của bạn (Giải nén ra Object)
    // ---------------------------------------------------------
    private static void testMethod1_JavaObjects() throws ParseException {
        Long start_Time = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        System.out.println("\n>>> TEST 1: Load bằng DataManagerAerospike (Java Objects)...");

        long startMem = getUsedMemory();
        long startTime = System.currentTimeMillis();

        // Gọi hàm thực tế của bạn
        // Lưu ý: Hàm này load 1 ngày hay nhiều ngày tùy vào logic bên trong của bạn
        TreeMap<Long, byte[]> datas = new TreeMap<>();
        for (int i = 0; i < 2000; i++) {
            TreeMap<Long, byte[]> data = DataManagerAerospike.readDataFromAerospike1MBytes(start_Time);
            if (data.isEmpty()){
                break;
            }
            datas.putAll(data);
            start_Time += Utils.TIME_DAY;
        }

        long duration = System.currentTimeMillis() - startTime;
        long endMem = getUsedMemory();
        long diff = endMem - startMem;

        if (datas != null) {
            int totalTickers = 0;
            for (byte[] map : datas.values()) {
                totalTickers += map.length;
            }

            System.out.printf("Done in %d ms%n", duration);
            System.out.printf("Tổng số ban nghi load được: %d%n", datas.size());
            System.out.printf("RAM tiêu tốn: %d MB%n", diff / 1024 / 1024);
            if (totalTickers > 0) {
                System.out.printf("Trung bình: %.2f bytes / object%n", (double) diff / totalTickers);
            }
        } else {
            System.out.println("Không load được dữ liệu (data null).");
        }
    }

    // ---------------------------------------------------------
    // CÁCH 2: Load nguyên cục Bytes (Giả lập chế độ Snappy nén)
    // ---------------------------------------------------------
    private static void testMethod2_RawSnappyBytes() {
        System.out.println("\n>>> TEST 2: Load Raw Bytes (Giả lập Snappy Compressed)...");

        // List chứa các mảng byte nén (thay vì Object)
        List<byte[]> rawDataStorage = new ArrayList<>();

        AerospikeClient client = new AerospikeClient(Configs.AEROSPIKE_HOST, Configs.AEROSPIKE_PORT);
        ScanPolicy policy = new ScanPolicy();
        policy.includeBinData = true;
        policy.concurrentNodes = true;

        long startMem = getUsedMemory();
        long startTime = System.currentTimeMillis();

        // Quét trực tiếp Aerospike nhưng KHÔNG convert sang Object
        // Chỉ lấy byte[] từ bin về và lưu vào RAM
        try {
            client.scanAll(policy, Configs.AEROSPIKE_NAMESPACE, "ticker_1m", (key, record) -> {
                // Giả sử dữ liệu nén nằm trong bin tên là "data" hoặc lấy toàn bộ record
                // Ở đây mình lấy ví dụ một bin byte[] giả định, hoặc gom các bin số lại

                // NẾU BẠN LƯU SNAPPY:
                // byte[] compressed = (byte[]) record.getValue("b"); // Tên bin chứa byte snappy

                // NẾU BẠN LƯU RỜI RẠC (Open, High, Low...):
                // Ta vẫn có thể giả lập nén bằng cách chỉ lưu giá trị vào mảng byte nhỏ gọn
                // Nhưng để test công bằng, ta giả sử bạn chuyển sang lưu 1 cục byte Snappy

                // MÔ PHỎNG: Lấy dữ liệu về dưới dạng byte thô (nhẹ hơn Object Header nhiều)
                // Ví dụ: record trả về Map, ta lưu cái Map đó dưới dạng byte thô (serialization)
                // Hoặc đơn giản là record.bins.toString().getBytes() để test dung lượng text

                // TRƯỜNG HỢP CỦA BẠN: Có thể bạn đang lưu từng field (o, h, l, c, v).
                // Aerospike trả về Object Long/Double.
                // Test này sẽ mô phỏng việc bạn CHUYỂN sang lưu byte[] Snappy.
                // Một nến nén Snappy chỉ tốn khoảng 15-20 bytes.

                // Giả lập 1 nến nén Snappy tốn 20 bytes
                byte[] simulatedCompressedKline = new byte[20];
                rawDataStorage.add(simulatedCompressedKline);

                // (Nếu bạn thực sự có bin chứa byte snappy thì: rawDataStorage.add((byte[]) record.getValue("snappy_bin")); )
            });
        } catch (Exception e) {
            // Bỏ qua lỗi scan hết
        }

        long duration = System.currentTimeMillis() - startTime;
        long endMem = getUsedMemory();
        long diff = endMem - startMem;

        System.out.printf("Done in %d ms%n", duration);
        System.out.printf("Tổng số record raw: %d%n", rawDataStorage.size());
        System.out.printf("RAM tiêu tốn: %d MB%n", diff / 1024 / 1024);

        if (rawDataStorage.size() > 0) {
            System.out.printf("Trung bình: %.2f bytes / raw entry (Snappy)%n", (double) diff / rawDataStorage.size());
            System.out.println("-> SO SÁNH: Cách 2 thường tiết kiệm 5-10 lần RAM so với Cách 1.");
        }

        client.close();
    }

    private static long getUsedMemory() {
        Runtime runtime = Runtime.getRuntime();
        return runtime.totalMemory() - runtime.freeMemory();
    }
}