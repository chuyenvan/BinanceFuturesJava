package com.binance.chuyennd.aerospike;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.BatchPolicy;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.proto.MinuteDataFinalProto.MinuteDataFinal;
import com.binance.chuyennd.proto.MinuteDataProto.KlineObjectSimpleProto;
import com.binance.chuyennd.proto.MinuteDataProto.MinuteData;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import org.xerial.snappy.Snappy;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

public class DataMigrator {

    // --- CẤU HÌNH ---
    private static final String OLD_SET_NAME = "kline_1m";       // Nguồn (Double)
    private static final String NEW_SET_NAME = "kline_1m_opt";   // Đích (Optimized: Float, No Time)

    private static AerospikeClient client;
    private static final BatchPolicy batchPolicy = new BatchPolicy();
    private static final WritePolicy writePolicy = new WritePolicy();

    // Đa luồng
    private static final int THREAD_COUNT = 16;
    private static final ExecutorService executor = Executors.newFixedThreadPool(THREAD_COUNT);
    private static final AtomicInteger countSuccess = new AtomicInteger(0);
    private static final AtomicInteger countError = new AtomicInteger(0);

    public static void main(String[] args) throws ParseException {
        // Init Client
        try {
            client = new AerospikeClient(Configs.AEROSPIKE_HOST, Configs.AEROSPIKE_PORT);

            // Ví dụ: Migrate 1 năm qua
            long endTime = System.currentTimeMillis();
            Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;

            System.out.println("=== BAT DAU MIGRATION ===");
            System.out.println("From: " + OLD_SET_NAME + " -> To: " + NEW_SET_NAME);

            migrateRange(startTime, endTime);

            System.out.println("=== KET THUC MIGRATION ===");
            System.out.println("Success Records: " + countSuccess.get());
            System.out.println("Error Records  : " + countError.get());

        } finally {
            if (client != null) client.close();
            executor.shutdown();
        }
    }

    public static void migrateRange(long startTime, long endTime) {
        // 1. Tạo danh sách Keys cần migrate
        List<Long> timestamps = new ArrayList<>();
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(startTime);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);

        while (cal.getTimeInMillis() <= endTime) {
            timestamps.add(cal.getTimeInMillis());
            cal.add(Calendar.MINUTE, 1);
        }

        System.out.println("Tong so phut can xu ly: " + timestamps.size());

        // 2. Chia nhỏ thành các Chunk để xử lý đa luồng
        int chunkSize = 2000;
        for (int i = 0; i < timestamps.size(); i += chunkSize) {
            int end = Math.min(i + chunkSize, timestamps.size());
            List<Long> chunkTimestamps = timestamps.subList(i, end);

            // Submit task
            executor.submit(() -> processChunk(chunkTimestamps));
        }

        // Chờ xử lý xong
        while(true) {
            if (((java.util.concurrent.ThreadPoolExecutor)executor).getActiveCount() == 0
                    && countSuccess.get() + countError.get() >= timestamps.size()) {
                break;
            }
            try { Thread.sleep(2000); } catch (InterruptedException e) {}
            System.out.println("Progress: " + (countSuccess.get() + countError.get()) + "/" + timestamps.size());
        }
    }

    private static void processChunk(List<Long> timestamps) {
        // --- FIX TIMEZONE: Bắt buộc dùng UTC (hoặc theo Config cũ của bạn) ---
        SimpleDateFormat localKeyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");
        // QUAN TRỌNG: Phải set TimeZone giống hệt AerospikeConfigs gốc
        localKeyFormat.setTimeZone(TimeZone.getTimeZone("UTC"));
        // --------------------------------------------------------------------
        // ------------------------------------------------------------

        try {
            Key[] keys = new Key[timestamps.size()];
            for (int i = 0; i < timestamps.size(); i++) {
                // SỬ DỤNG localKeyFormat
                String keyString = localKeyFormat.format(new Date(timestamps.get(i)));
                keys[i] = new Key(Configs.AEROSPIKE_NAMESPACE, OLD_SET_NAME, keyString);
            }

            // Batch Read từ Set CŨ
            Record[] records = client.get(batchPolicy, keys);

            for (int i = 0; i < records.length; i++) {
                Record record = records[i];
                if (record == null) {
                    countSuccess.incrementAndGet();
                    continue;
                }

                // SỬ DỤNG localKeyFormat
                String keyString = localKeyFormat.format(new Date(timestamps.get(i)));

                try {
                    // 1. Đọc và giải nén dữ liệu CŨ
                    byte[] oldBytes = (byte[]) record.getValue("data");
                    if (oldBytes == null) continue;

                    byte[] protoOldBytes = Snappy.uncompress(oldBytes);
                    MinuteData oldData = MinuteData.parseFrom(protoOldBytes);

                    // 2. Convert sang cấu trúc MỚI
                    MinuteDataFinal newData = convertToOptimizedProto(oldData);

                    // 3. Nén và Ghi sang Set MỚI
                    byte[] protoNewBytes = newData.toByteArray();
                    byte[] compressedNewBytes = Snappy.compress(protoNewBytes);

                    Key newKey = new Key(Configs.AEROSPIKE_NAMESPACE, NEW_SET_NAME, keyString);
                    Bin bin = new Bin("data", compressedNewBytes);

                    client.put(writePolicy, newKey, bin);

                    countSuccess.incrementAndGet();

                } catch (Exception e) {
                    System.err.println("Loi xu ly key: " + keyString);
                    e.printStackTrace();
                    countError.incrementAndGet();
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
    /**
     * CORE LOGIC:
     * 1. Double -> Float
     * 2. Bỏ field startTime
     */
    private static MinuteDataFinal convertToOptimizedProto(MinuteData oldData) {
        MinuteDataFinal.Builder newBuilder = MinuteDataFinal.newBuilder();

        // Duyệt qua Map cũ
        for (Map.Entry<String, KlineObjectSimpleProto> entry : oldData.getTickersMap().entrySet()) {
            String symbol = entry.getKey();
            KlineObjectSimpleProto oldKline = entry.getValue();

            // Builder cho nến mới
            KlineObjectOptimized.Builder newKlineBuilder = KlineObjectOptimized.newBuilder();

            // CHỈ COPY CÁC TRƯỜNG GIÁ (Ép kiểu Float)
            // KHÔNG setStartTime nữa

            newKlineBuilder.setPriceOpen((float) oldKline.getPriceOpen());
            newKlineBuilder.setMaxPrice((float) oldKline.getMaxPrice());
            newKlineBuilder.setMinPrice((float) oldKline.getMinPrice());
            newKlineBuilder.setPriceClose((float) oldKline.getPriceClose());
            newKlineBuilder.setTotalUsdt((float) oldKline.getTotalUsdt());

            // Put vào map mới
            newBuilder.putTickers(symbol, newKlineBuilder.build());
        }

        return newBuilder.build();
    }
}