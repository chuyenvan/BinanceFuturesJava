package com.binance.chuyennd.bigchange.test;

import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * Tool TraceData2TestQuarter - Phân tích dữ liệu lịch sử đóng lệnh theo QUÝ (Quarter).
 * Được thiết kế để kế thừa hoàn hảo logic của TraceData2Test nhưng nâng cấp độ phân giải từ Năm lên Quý.
 */
public class TraceData2TestQuarter {
    public static final Logger LOG = LoggerFactory.getLogger(TraceData2TestQuarter.class);

    public static void main(String[] args) {
        try {
            String fileName = "storage/OrderTestDone.data";
            if (args != null && args.length > 0) {
                fileName = args[0];
            }

            LOG.info("📊 Đang đọc file dữ liệu đóng lệnh: {}", fileName);
            Object obj = Storage.readObjectFromFile(fileName);
            if (obj == null) {
                LOG.error("⛔ Không thể đọc được file: {}", fileName);
                return;
            }

            TreeMap<Long, OrderTargetInfoTest> allOrderDone = (TreeMap<Long, OrderTargetInfoTest>) obj;
            LOG.info("✅ Đã tải thành công {} lệnh.", allOrderDone.size());

            // 1. Phân nhóm toàn bộ lệnh theo Quý để in bảng tổng hợp
            TreeMap<String, List<OrderTargetInfoTest>> quarter2AllOrders = new TreeMap<>();
            
            // 2. Phân nhóm theo Tín hiệu -> Quý
            TreeMap<MarketLevelChange, TreeMap<String, List<OrderTargetInfoTest>>> level2Quarter2Orders = new TreeMap<>();

            for (OrderTargetInfoTest order : allOrderDone.values()) {
                if (order == null) continue;
                
                // Xác định Quý dựa trên thời gian bắt đầu (timeStart)
                String quarter = getQuarterKey(order.timeStart);
                
                // Gom vào danh sách tổng của Quý
                quarter2AllOrders.computeIfAbsent(quarter, k -> new ArrayList<>()).add(order);

                // Gom vào danh sách theo Tín hiệu
                MarketLevelChange mlc = order.marketLevelChange;
                if (mlc == null) {
                    mlc = MarketLevelChange.PREDICT_SYMBOL_TRADE; // Mặc định nếu null
                }
                level2Quarter2Orders
                    .computeIfAbsent(mlc, k -> new TreeMap<>())
                    .computeIfAbsent(quarter, k -> new ArrayList<>())
                    .add(order);
            }

            // --- PHẦN 1: IN BẢNG TỔNG HỢP QUÝ ---
            LOG.info("\n\n================= 📊 BẢNG TỔNG HỢP THEO QUÝ =================");
            LOG.info("Quarter\tMargin_Max\tProfitMin_Min\tProfit_Total\tOrders_Count");
            LOG.info("------------------------------------------------------------------");
            
            for (Map.Entry<String, List<OrderTargetInfoTest>> entry : quarter2AllOrders.entrySet()) {
                String quarter = entry.getKey();
                List<OrderTargetInfoTest> orders = entry.getValue();

                float maxMargin = 0f;
                float minProfitMin = 0f;
                float totalProfit = 0f;

                for (OrderTargetInfoTest order : orders) {
                    if (order.calMargin() != null && order.calMargin() > maxMargin) {
                        maxMargin = order.calMargin();
                    }
                    if (order.profitMin != null && order.profitMin < minProfitMin) {
                        minProfitMin = order.profitMin;
                    }
                    totalProfit += order.calTp();
                }

                LOG.info("{}\tMargin: {}\tProfitMin_Min: {}\tProfit: {} $\tCount: {}",
                        quarter,
                        Utils.formatLog((long) maxMargin, 5),
                        Utils.formatLog((long) minProfitMin, 6),
                        Utils.formatLog((long) totalProfit, 6),
                        Utils.formatLog(orders.size(), 5)
                );
            }

            // --- PHẦN 2: IN CHI TIẾT THEO TỪNG CỔNG TÍN HIỆU (MARKET LEVEL CHANGE) ---
            LOG.info("\n\n================= ⚙️ CHI TIẾT THEO CỔNG TÍN HIỆU THEO QUÝ =================");
            
            for (Map.Entry<MarketLevelChange, TreeMap<String, List<OrderTargetInfoTest>>> levelEntry : level2Quarter2Orders.entrySet()) {
                MarketLevelChange mlc = levelEntry.getKey();
                TreeMap<String, List<OrderTargetInfoTest>> quarter2Orders = levelEntry.getValue();

                StringBuilder sb = new StringBuilder();
                sb.append(String.format("%-24s => ", mlc.toString()));

                float totalAllRate = 0f;
                int totalAllCount = 0;
                float totalAllProfit = 0f;

                StringBuilder quarterDetails = new StringBuilder();
                for (Map.Entry<String, List<OrderTargetInfoTest>> qEntry : quarter2Orders.entrySet()) {
                    String quarter = qEntry.getKey();
                    List<OrderTargetInfoTest> qOrders = qEntry.getValue();

                    float totalQuarterRate = 0f;
                    float totalQuarterProfit = 0f;

                    for (OrderTargetInfoTest order : qOrders) {
                        totalQuarterRate += order.calRateTp();
                        totalQuarterProfit += order.calTp();
                    }

                    totalAllRate += totalQuarterRate;
                    totalAllCount += qOrders.size();
                    totalAllProfit += totalQuarterProfit;

                    // Định dạng hiển thị cho mỗi Quý của cổng tín hiệu này
                    quarterDetails.append("\n\t")
                            .append(quarter).append(": ")
                            .append(Utils.formatLog(Utils.formatDouble(totalQuarterRate * 100 / qOrders.size(), 3), 6)).append("\t")
                            .append(Utils.formatLog(qOrders.size(), 5)).append("\t")
                            .append(Utils.formatLog((long) totalQuarterProfit, 5)).append(" $");
                }

                // In phần tổng hợp của cả cổng tín hiệu
                sb.append("All: ")
                  .append(Utils.formatLog(Utils.formatDouble(totalAllRate * 100 / totalAllCount, 3), 6)).append("\t")
                  .append(Utils.formatLog(totalAllCount, 5)).append("\t")
                  .append(Utils.formatLog((long) totalAllProfit, 5)).append(" $")
                  .append(quarterDetails);

                LOG.info(sb.toString());
                LOG.info("----------------------------------------------------------------------------------");
            }

        } catch (Exception e) {
            LOG.error("❌ Đã xảy ra lỗi trong quá trình phân tích dữ liệu Quý", e);
        }
    }

    /**
     * Xác định Quý theo múi giờ GMT+7 mặc định của hệ thống (TimeZoneGuard).
     */
    public static String getQuarterKey(long timeMs) {
        Calendar cal = Calendar.getInstance(TimeZone.getTimeZone("GMT+7"));
        cal.setTimeInMillis(timeMs);
        int year = cal.get(cal.get(Calendar.YEAR) < 2000 ? Calendar.YEAR : Calendar.YEAR); // Bảo vệ chống trôi năm
        int yearVal = cal.get(Calendar.YEAR);
        int month0 = cal.get(Calendar.MONTH); // 0-based (0 = Jan, 11 = Dec)
        int q = (month0 / 3) + 1;             // Q1, Q2, Q3, Q4
        return yearVal + "Q" + q;
    }
}
