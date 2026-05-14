package com.binance.chuyennd.aerospike;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.BatchPolicy;
import com.aerospike.client.policy.ClientPolicy;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicInteger;

public class TickerReadSpeedTest {

    // --- CẤU HÌNH THÔNG SỐ TEST ---
    private static final String HOST = "103.157.218.242"; // Client242 theo logic của bạn
    private static final int PORT = 3222;
    private static final String NAMESPACE = "ticker";     // Thường là ticker, thay đổi nếu cần
    private static final String SET_NAME = "kline_1m_opt";

    private static final int THREAD_COUNT = 4;            // Số luồng gọi đồng thời
    private static final int MINUTES_TO_TEST = 10000;     // Số lượng phút (records) muốn đọc thử (~1 tuần)

    // Đặt thời gian bắt đầu test. LƯU Ý: Hãy set về 1 khoảng thời gian BẠN CHẮC CHẮN CÓ DỮ LIỆU
    // Để test đúng tải Payload thay vì load ra null. (Ví dụ: 1/1/2024)
    private static final long START_TIME_MS = 1704067200000L; // 01/01/2024 00:00:00 UTC

    public static void main(String[] args) {
        ClientPolicy cp = new ClientPolicy();
        cp.timeout = 5000;

        System.out.println("Đang kết nối tới Aerospike " + HOST + ":" + PORT + "...");
        try (AerospikeClient client = new AerospikeClient(cp, HOST, PORT)) {
            System.out.println("Kết nối thành công! Chuẩn bị dữ liệu test...");

            // 1. Tạo danh sách Timestamps
            long[] allTimestamps = new long[MINUTES_TO_TEST];
            for (int i = 0; i < MINUTES_TO_TEST; i++) {
                allTimestamps[i] = START_TIME_MS + (i * 60000L); // Nhảy từng phút
            }

            ExecutorService executor = Executors.newFixedThreadPool(THREAD_COUNT);
            List<Future<TestResult>> futures = new ArrayList<>();
            BatchPolicy batchPolicy = new BatchPolicy();
            int chunkSize = (MINUTES_TO_TEST + THREAD_COUNT - 1) / THREAD_COUNT;

            System.out.println("Bắt đầu test tốc độ Đọc Batch đa luồng (" + THREAD_COUNT + " threads)...");
            long startTimeGlobal = System.currentTimeMillis();

            // 2. Phân chia công việc cho các Threads
            for (int i = 0; i < THREAD_COUNT; i++) {
                final int startIdx = i * chunkSize;
                final int endIdx = Math.min(startIdx + chunkSize, MINUTES_TO_TEST);
                if (startIdx >= endIdx) break;

                futures.add(executor.submit(new Callable<TestResult>() {
                    @Override
                    public TestResult call() {
                        TestResult result = new TestResult();
                        SimpleDateFormat localKeyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");

                        // Lấy mảng timestamp cho chunk này
                        long[] chunkTimestamps = Arrays.copyOfRange(allTimestamps, startIdx, endIdx);
                        Key[] chunkKeys = new Key[chunkTimestamps.length];

                        // Khởi tạo Key
                        for (int k = 0; k < chunkKeys.length; k++) {
                            String keyString = localKeyFormat.format(new Date(chunkTimestamps[k]));
                            chunkKeys[k] = new Key(NAMESPACE, SET_NAME, keyString);
                        }

                        // Thực hiện BATCH GET từ Aerospike
                        long startBatch = System.currentTimeMillis();
                        Record[] records = client.get(batchPolicy, chunkKeys);
                        result.latencyMs = System.currentTimeMillis() - startBatch;

                        // Đếm số lượng record có dữ liệu thật (tránh đếm null)
                        if (records != null) {
                            for (Record record : records) {
                                if (record != null && record.getValue("data") != null) {
                                    result.hitCount++;
                                }
                            }
                        }
                        return result;
                    }
                }));
            }

            // 3. Chờ và tổng hợp kết quả
            int totalHits = 0;
            long totalThreadLatency = 0;

            for (Future<TestResult> future : futures) {
                TestResult res = future.get();
                totalHits += res.hitCount;
                totalThreadLatency += res.latencyMs;
            }

            executor.shutdown();
            long endTimeGlobal = System.currentTimeMillis();
            long durationMs = endTimeGlobal - startTimeGlobal;

            // 4. In báo cáo thống kê
            System.out.println("\n==============================================");
            System.out.println("📊 BÁO CÁO TỐC ĐỘ ĐỌC AEROSPIKE (TICKER 1M)");
            System.out.println("==============================================");
            System.out.println("Tổng số Records yêu cầu: " + MINUTES_TO_TEST);
            System.out.println("Số Records tìm thấy (Hit): " + totalHits);
            System.out.println("Tổng thời gian thực thi: " + durationMs + " ms");

            if (durationMs > 0) {
                long tps = (MINUTES_TO_TEST * 1000L) / durationMs;
                System.out.println("Tốc độ trung bình (TPS): ~" + tps + " records/giây");

                // Độ trễ trung bình của mỗi Thread xử lý 1 Batch
                long avgBatchLatency = totalThreadLatency / THREAD_COUNT;
                System.out.println("Độ trễ trung bình mỗi luồng (Batch Latency): " + avgBatchLatency + " ms / " + chunkSize + " records");
            }
            System.out.println("==============================================");

            if (totalHits == 0) {
                System.out.println("⚠️ CẢNH BÁO: Tất cả đều trả về NULL. Bạn hãy sửa biến START_TIME_MS về một ngày có dữ liệu để test tải payload chuẩn hơn!");
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    // Class phụ để lưu kết quả từ Thread
    static class TestResult {
        int hitCount = 0;
        long latencyMs = 0;
    }
}