package com.binance.chuyennd.research;

import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * TASK-152 [TEAM FAIL] — công cụ ĐO-ONLY (không đổi hành vi engine): đọc storage/OrderTestDone.data
 * (đã ghi bởi SimulatorMarketLevelTicker1MStopLoss với WRITE_SIM_STORAGE=true) và xuất phân bố
 * holding-time + tỉ lệ-cứu (lỗ→hồi) + danh sách cụm nghi không-hồi (candidate delist).
 *
 * <p>GIỚI HẠN ĐÃ BIẾT: {@code timeStart} là mốc leg CUỐI (bị reset mỗi lần DCA nhồi thêm — xem comment
 * {@link OrderTargetInfoTest#clusterFirstLegTime}), KHÔNG phải leg đầu. holdDays = timeUpdate-timeStart
 * do đó là cận DƯỚI của thời gian giữ vốn thật (undercount cho cụm bị DCA muộn). Số leg (độ sâu DCA)
 * KHÔNG được lưu trực tiếp — dùng calMargin()/baseBudget làm proxy độ sâu (xấp xỉ, không chính xác tuyệt đối).
 *
 * <p>Usage: {@code java -cp <jar> com.binance.chuyennd.research.ClusterFailAnalysisTool <path/to/OrderTestDone.data> <baseBudget>}
 */
public class ClusterFailAnalysisTool {

    private static final long DAY_MS = 24L * 3600_000L;
    private static final long[] BUCKET_EDGES_DAYS = {1, 7, 30, 90, 180, 270, 365};

    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: ClusterFailAnalysisTool <OrderTestDone.data> [baseBudget=700]");
            System.exit(2);
        }
        String path = args[0];
        float baseBudget = args.length > 1 ? Float.parseFloat(args[1]) : 700f;

        @SuppressWarnings("unchecked")
        TreeMap<Long, OrderTargetInfoTest> all = (TreeMap<Long, OrderTargetInfoTest>) Storage.readObjectFromFile(path);
        if (all == null) {
            System.err.println("KHONG DOC DUOC file: " + path);
            System.exit(1);
        }
        System.out.println("Tong so cum dong: " + all.size());

        long[] bucketCounts = new long[BUCKET_EDGES_DAYS.length + 1];
        Map<MarketLevelChange, long[]> level2Buckets = new HashMap<>();

        int totalWasInLoss = 0, totalRescued = 0;
        int totalClusters = 0;
        double sumHoldDays = 0;
        long maxHoldDays = 0;
        List<OrderTargetInfoTest> neverRecovered = new ArrayList<>();

        for (OrderTargetInfoTest o : all.values()) {
            if (o.priceEntry == null || o.status == null) continue;
            totalClusters++;

            long holdMs = o.timeUpdate - o.timeStart;
            double holdDays = holdMs / (double) DAY_MS;
            if (holdDays < 0) holdDays = 0;
            sumHoldDays += holdDays;
            if (holdMs > maxHoldDays) maxHoldDays = holdMs;

            int bucketIdx = BUCKET_EDGES_DAYS.length;
            for (int i = 0; i < BUCKET_EDGES_DAYS.length; i++) {
                if (holdDays < BUCKET_EDGES_DAYS[i]) { bucketIdx = i; break; }
            }
            bucketCounts[bucketIdx]++;
            MarketLevelChange level = o.marketLevelChange;
            long[] lvlBuckets = level2Buckets.computeIfAbsent(level, k -> new long[BUCKET_EDGES_DAYS.length + 1]);
            lvlBuckets[bucketIdx]++;

            boolean wasInLoss = o.maeLow != null && o.maeLow < o.priceEntry;
            Float tp = o.calTp();
            boolean closedProfit = tp != null && tp > 0;
            if (wasInLoss) {
                totalWasInLoss++;
                if (closedProfit) totalRescued++;
            }

            boolean lossExit = o.status == OrderTargetStatus.STOP_LOSS_DONE
                    || (o.status == OrderTargetStatus.STOP_MARKET_DONE && tp != null && tp <= 0);
            if (lossExit && tp != null && tp < 0) {
                neverRecovered.add(o);
            }
        }

        System.out.println("\n=== PHAN BO HOLDING-TIME (proxy = timeUpdate-timeStart, xem GIOI HAN o Javadoc) ===");
        printBucketHeader();
        printBucketRow("ALL", bucketCounts, totalClusters);
        for (Map.Entry<MarketLevelChange, long[]> e : level2Buckets.entrySet()) {
            long sum = 0; for (long c : e.getValue()) sum += c;
            printBucketRow(String.valueOf(e.getKey()), e.getValue(), sum);
        }
        System.out.println("Trung binh hold-day (proxy): " + Utils.formatDouble((float) (sumHoldDays / Math.max(1, totalClusters)), 2));
        System.out.println("Max hold-day (proxy) mot cum: " + Utils.formatDouble((float) (maxHoldDays / (double) DAY_MS), 2));

        System.out.println("\n=== TI LE-CUU (lo->hoi) ===");
        System.out.println("So cum tung am (maeLow<priceEntry): " + totalWasInLoss + " / " + totalClusters);
        System.out.println("Trong do dong LAI (calTp>0) = duoc CUU: " + totalRescued
                + " (" + Utils.formatDouble(totalWasInLoss == 0 ? 0f : 100f * totalRescued / totalWasInLoss, 2) + "%)");

        neverRecovered.sort((a, b) -> Float.compare(a.calTp(), b.calTp()));
        System.out.println("\n=== TOP 20 CUM KHONG HOI (loss exit, PnL am nhat — candidate delist/never-recover) ===");
        int shown = 0;
        for (OrderTargetInfoTest o : neverRecovered) {
            if (shown++ >= 20) break;
            double holdDays = (o.timeUpdate - o.timeStart) / (double) DAY_MS;
            float maeRate = o.maeLow == null ? 0f : (o.maeLow - o.priceEntry) / o.priceEntry;
            float sizeMultiple = o.calMargin() == null ? 0f : o.calMargin() / baseBudget;
            System.out.println(o.symbol + "\t" + o.marketLevelChange + "\t"
                    + Utils.normalizeDateYYYYMMDD(o.timeUpdate)
                    + "\tholdDays=" + Utils.formatDouble((float) holdDays, 1)
                    + "\tmaeRate=" + Utils.formatDouble(maeRate * 100, 2) + "%"
                    + "\tsizeMultiple=" + Utils.formatDouble(sizeMultiple, 2)
                    + "\tpnl=" + o.calTp().longValue());
        }
        System.out.println("\nSo cum loss-exit PnL am (tong): " + neverRecovered.size());
        System.exit(0);
    }

    private static void printBucketHeader() {
        StringBuilder sb = new StringBuilder("LEVEL\t<1d\t1-7d\t7-30d\t30-90d\t90-180d\t180-270d\t270-365d\t>365d\tTOTAL");
        System.out.println(sb);
    }

    private static void printBucketRow(String label, long[] buckets, long total) {
        StringBuilder sb = new StringBuilder(label);
        for (long c : buckets) sb.append("\t").append(c);
        sb.append("\t").append(total);
        System.out.println(sb);
    }
}
