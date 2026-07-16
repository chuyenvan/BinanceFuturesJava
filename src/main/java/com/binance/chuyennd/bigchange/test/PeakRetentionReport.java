package com.binance.chuyennd.bigchange.test;

import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.utils.Storage;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;

/**
 * TASK-151: đo "% đỉnh giữ được" + PnL trung bình/lệnh THẮNG cho lệnh nuôi-lãi (giveback sweep).
 * Đọc lại storage/OrderTestDone.data (đã ghi bởi SimulatorMarketLevelTicker1MStopLoss với
 * WRITE_SIM_STORAGE=true) — KHÔNG chạy sim lại, chỉ đo-lường thêm trên field maePeak (ĐO LƯỜNG ONLY).
 */
public class PeakRetentionReport {
    public static final Logger LOG = LoggerFactory.getLogger(PeakRetentionReport.class);

    public static void main(String[] args) {
        String fileName = "../simulator/storage/OrderTestDone.data";
        TreeMap<Long, OrderTargetInfoTest> allOrderDone =
                (TreeMap<Long, OrderTargetInfoTest>) Storage.readObjectFromFile(fileName);
        if (allOrderDone == null) {
            LOG.error("Khong doc duoc {}", fileName);
            return;
        }
        Map<MarketLevelChange, double[]> level2Agg = new HashMap<>(); // [sumRetention, sumPnlWin, nWin, nSkipNoPeak]
        for (OrderTargetInfoTest order : allOrderDone.values()) {
            float pnl = order.calProfit();
            if (pnl <= 0) {
                continue; // chỉ đo lệnh THẮNG (đúng scope "nuôi lãi")
            }
            double[] agg = level2Agg.computeIfAbsent(order.marketLevelChange, k -> new double[4]);
            if (order.maePeak == null || order.priceEntry == null || order.maePeak <= order.priceEntry) {
                agg[3]++;
                continue;
            }
            float peakPnl = order.quantity * (order.maePeak - order.priceEntry);
            float retention = peakPnl > 0 ? pnl / peakPnl : 0f;
            agg[0] += Math.min(retention, 1.0); // clamp phòng sai số float hiếm gặp
            agg[1] += pnl;
            agg[2]++;
        }
        System.out.println("=== PeakRetentionReport (lệnh THẮNG, pnl>0) ===");
        for (Map.Entry<MarketLevelChange, double[]> e : level2Agg.entrySet()) {
            double[] agg = e.getValue();
            double n = agg[2];
            double avgRetention = n > 0 ? agg[0] / n * 100.0 : 0;
            double avgPnl = n > 0 ? agg[1] / n : 0;
            System.out.printf("%-25s n_win=%-6d avgRetention=%.1f%% avgPnlPerWin=%.2f skip_no_peak=%d%n",
                    e.getKey(), (long) n, avgRetention, avgPnl, (long) agg[3]);
        }
    }
}
