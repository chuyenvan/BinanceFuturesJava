package com.binance.chuyennd.ai_ml.data;

import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;

import java.lang.management.ManagementFactory;
import java.lang.management.MemoryMXBean;
import java.lang.management.MemoryUsage;
import java.text.DecimalFormat;

public class MemoryAnalyzerTool {

    private static final DecimalFormat df = new DecimalFormat("#,###.##");

    public static void main(String[] args) throws Exception {
        System.out.println("=== REAL HEAP MEMORY TESTER ===");
        System.out.println("Max Heap (-Xmx): " + formatSize(Runtime.getRuntime().maxMemory()));

        // 1. Giai đoạn 1: Baseline (Khởi động và load Metadata tĩnh)
        System.out.println("\n[PHASE 1] Initializing & Loading Static Metadata...");
        // Gọi hàm load metadata nếu có (ví dụ FundingFee, Configs...)
        // Ở đây giả sử HPOSmartCache chưa có data, chỉ khởi tạo class
        forceGC();
        long memBase = getUsedHeap();
        printMemoryStatus("Baseline (Empty Cache)");

        // 2. Giai đoạn 2: Load 10 ngày đầu tiên
        int daysBatch1 = 100;
        long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime();
        long endTime1 = startTime + (daysBatch1 * Utils.TIME_DAY);

        System.out.println("\n[PHASE 2] Loading first " + daysBatch1 + " days ("
                + Utils.normalizeDateYYYYMMDDHHmm(startTime) + " -> " + Utils.normalizeDateYYYYMMDDHHmm(endTime1) + ")...");

        long t1 = System.currentTimeMillis();
        loadDataRange(startTime, endTime1);
        System.out.println("-> Load time: " + (System.currentTimeMillis() - t1) + "ms");

        forceGC(); // Dọn rác để đo chính xác object sống
        long memAfterBatch1 = getUsedHeap();
        printMemoryStatus("After Batch 1");

        long diff1 = memAfterBatch1 - memBase;
        System.out.println(">>> COST FOR 10 DAYS: " + formatSize(diff1));
        System.out.println(">>> AVG PER DAY     : " + formatSize(diff1 / daysBatch1));

        // 3. Giai đoạn 3: Load thêm 10 ngày tiếp theo
        // Để kiểm chứng xem bộ nhớ có tăng tuyến tính không
        int daysBatch2 = 10;
        long startTime2 = endTime1;
        long endTime2 = startTime2 + (daysBatch2 * Utils.TIME_DAY);

        System.out.println("\n[PHASE 3] Loading next " + daysBatch2 + " days ("
                + Utils.normalizeDateYYYYMMDDHHmm(startTime2) + " -> " + Utils.normalizeDateYYYYMMDDHHmm(endTime2) + ")...");

        long t2 = System.currentTimeMillis();
        loadDataRange(startTime2, endTime2);
        System.out.println("-> Load time: " + (System.currentTimeMillis() - t2) + "ms");

        forceGC();
        long memAfterBatch2 = getUsedHeap();
        printMemoryStatus("After Batch 2");

        long diff2 = memAfterBatch2 - memAfterBatch1;
        System.out.println(">>> COST FOR NEXT 10 DAYS: " + formatSize(diff2));
        System.out.println(">>> AVG PER DAY          : " + formatSize(diff2 / daysBatch2));

        // 4. TỔNG KẾT VÀ DỰ BÁO
        long avgPerDay = (diff1 + diff2) / (daysBatch1 + daysBatch2);
        System.out.println("\n==========================================");
        System.out.println("       KẾT LUẬN THỰC TẾ");
        System.out.println("==========================================");
        System.out.println("RAM trung bình 1 ngày : " + formatSize(avgPerDay));

        long totalDaysEstimate = 300; // 10 tháng (~300 ngày)
        long estimatedTotalRAM = memBase + (avgPerDay * totalDaysEstimate);

        System.out.println("Dự báo cho 10 tháng (" + totalDaysEstimate + " ngày): " + formatSize(estimatedTotalRAM));
        System.out.println("Heap Max (-Xmx) hiện tại: " + formatSize(Runtime.getRuntime().maxMemory()));

        if (estimatedTotalRAM > Runtime.getRuntime().maxMemory()) {
            System.out.println("❌ CẢNH BÁO: SẼ BỊ OVERHEAP! (Cần " + formatSize(estimatedTotalRAM) + ")");
        } else {
            System.out.println("✅ AN TOÀN.");
        }
    }

    // Hàm load data gọi vào Cache
    private static void loadDataRange(long start, long end) {
        long current = start;
        while (current < end) {
            HPOSmartCache.getData(current);
            current += Utils.TIME_DAY;
        }
    }

    // Ép JVM dọn rác thật kỹ để số liệu đo không bị ảo
    private static void forceGC() {
        System.out.print("Forcing GC...");
        for (int i = 0; i < 3; i++) {
            System.gc();
            try { Thread.sleep(500); } catch (InterruptedException e) {}
        }
        System.out.println(" Done.");
    }

    private static long getUsedHeap() {
        MemoryMXBean memoryBean = ManagementFactory.getMemoryMXBean();
        MemoryUsage heapUsage = memoryBean.getHeapMemoryUsage();
        return heapUsage.getUsed();
    }

    private static void printMemoryStatus(String label) {
        long used = getUsedHeap();
        long max = Runtime.getRuntime().maxMemory();
        double percent = (double) used / max * 100;
        System.out.println("MEMORY [" + label + "]: " + formatSize(used) + " / " + formatSize(max) + " (" + String.format("%.2f", percent) + "%)");
    }

    private static String formatSize(long bytes) {
        double kb = bytes / 1024.0;
        double mb = kb / 1024.0;
        double gb = mb / 1024.0;

        if (gb >= 1) return df.format(gb) + " GB";
        else if (mb >= 1) return df.format(mb) + " MB";
        else if (kb >= 1) return df.format(kb) + " KB";
        else return bytes + " B";
    }

}