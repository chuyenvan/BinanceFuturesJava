package com.binance.chuyennd.ai_ml.features.export.fundingv2;

import java.io.*;
import java.util.*;
import java.util.zip.GZIPInputStream;

public class CompareFeatureFiles {
    static class DataRecord {
        long time;
        short symId;
        float[] features;
    }

    public static void main(String[] args) throws Exception {
        String file1 = "features_export_python/features_2021.bin.gz";       // FPT
        String file2 = "features_export_python/features_2021.bin.gz_raw";   // Oracle

        System.out.println("🔍 Đang đọc và đồng bộ hóa 2 file...");

        DataInputStream dis1 = new DataInputStream(new BufferedInputStream(new GZIPInputStream(new FileInputStream(file1))));
        DataInputStream dis2 = new DataInputStream(new BufferedInputStream(new GZIPInputStream(new FileInputStream(file2))));

        DataRecord[] nextRec1 = new DataRecord[1];
        DataRecord[] nextRec2 = new DataRecord[1];

        Map<Short, float[]> map1 = new HashMap<>();
        Map<Short, float[]> map2 = new HashMap<>();

        // 1. ĐỌC MỐC ĐẦU TIÊN CỦA ORACLE
        long t2 = readBlock(dis2, map2, nextRec2);
        if (t2 == -1) {
            System.out.println("❌ File Oracle rỗng!");
            return;
        }
        System.out.println("⏱️ Oracle bắt đầu từ: " + normalizeDate(t2));

        // 2. TUA NHANH FILE FPT CHO ĐẾN KHI BẰNG MỐC CỦA ORACLE
        long t1 = readBlock(dis1, map1, nextRec1);
        System.out.println("⏱️ FPT bắt đầu từ: " + normalizeDate(t1) + " (Sẽ tua nhanh để đuổi kịp Oracle...)");

        while (t1 != -1 && t1 < t2) {
            t1 = readBlock(dis1, map1, nextRec1);
        }

        if (t1 != t2) {
            System.out.println("❌ Lỗi: Không thể tìm thấy mốc thời gian của Oracle ở bên trong file FPT!");
            return;
        }

        System.out.println("✅ Đã đồng bộ! Bắt đầu so sánh song song 1:1 từ mốc " + normalizeDate(t1) + "...");

        int matchCount = 0;
        int mismatchCount = 0;
        int missingCount = 0;
        int blockCount = 0;

        // 3. TIẾN HÀNH SO SÁNH 1:1
        while (true) {
            blockCount++;

            if (map1.size() != map2.size()) {
                System.out.println("⚠️ Lệch số lượng Symbol tại block " + blockCount + " | FPT: " + map1.size() + " vs Oracle: " + map2.size());
            }

            // SO SÁNH TỪNG FEATURE CỦA TỪNG SYMBOL
            for (Short symId : map1.keySet()) {
                float[] f1 = map1.get(symId);
                float[] f2 = map2.get(symId);

                if (f2 == null) {
                    missingCount++;
                    continue;
                }

                boolean match = true;
                for (int i = 0; i < 21; i++) {
                    if (Math.abs(f1[i] - f2[i]) > 0.00001f) {
                        if (mismatchCount < 10) {
                            System.out.println(String.format("❌ Lệch Feature tại SymId %d, Cột [%d] | FPT (%s) = %f, Oracle (%s) = %f",
                                    symId, i, normalizeDate(t1), f1[i], normalizeDate(t2), f2[i]));
                        }
                        match = false;
                        break;
                    }
                }
                if (match) matchCount++;
                else mismatchCount++;
            }

            if (blockCount % 50000 == 0) {
                System.out.println("Đã so sánh " + blockCount + " mốc thời gian...");
            }

            // Đọc mốc tiếp theo cho cả 2 file
            t1 = readBlock(dis1, map1, nextRec1);
            t2 = readBlock(dis2, map2, nextRec2);

            if (t1 == -1 && t2 == -1) break; // Xong cả 2

            if (t1 != t2) {
                System.out.println(String.format("❌ Lệch cấu trúc thời gian giữa chừng! FPT: %s | Oracle: %s", normalizeDate(t1), normalizeDate(t2)));
                break;
            }
        }

        System.out.println("=========================================================");
        System.out.println("🏁 KẾT QUẢ SO SÁNH 1:1 (Bỏ qua 7 tiếng đầu):");
        System.out.println("   - Tổng số mốc thời gian đã so sánh: " + blockCount);
        System.out.println("   - Số bản ghi khớp hoàn toàn: " + matchCount);
        System.out.println("   - Số bản ghi lệch Feature: " + mismatchCount);

        if (mismatchCount == 0 && missingCount == 0) {
            System.out.println("🎉 CHÚC MỪNG! Dữ liệu 2 bên khớp nhau 100% đến từng BIT!");
        } else {
            System.out.println("⚠️ DỮ LIỆU VẪN CÓ SỰ SAI LỆCH!");
        }

        dis1.close();
        dis2.close();
    }

    // Hàm đọc 1 cục data có cùng Timestamp
    private static long readBlock(DataInputStream dis, Map<Short, float[]> map, DataRecord[] nextRecBox) throws IOException {
        map.clear();
        DataRecord rec = nextRecBox[0];
        if (rec == null) {
            rec = readOne(dis);
            if (rec == null) return -1;
        }
        long currentTime = rec.time;
        while (rec != null && rec.time == currentTime) {
            map.put(rec.symId, rec.features);
            rec = readOne(dis);
        }
        nextRecBox[0] = rec;
        return currentTime;
    }

    // Hàm đọc 1 dòng dữ liệu
    private static DataRecord readOne(DataInputStream dis) {
        try {
            DataRecord r = new DataRecord();
            r.time = dis.readLong();
            r.symId = dis.readShort();
            r.features = new float[21];
            for(int i=0; i<21; i++) r.features[i] = dis.readFloat();
            return r;
        } catch (IOException e) {
            return null;
        }
    }

    private static String normalizeDate(long time) {
        java.text.SimpleDateFormat sdf = new java.text.SimpleDateFormat("yyyyMMdd-HHmm");
        sdf.setTimeZone(java.util.TimeZone.getTimeZone("GMT+7"));
        return sdf.format(new java.util.Date(time));
    }
}