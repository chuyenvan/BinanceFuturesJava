import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;

import java.util.*;

/**
 * Standalone helper (khong doi jar): doc storage/OrderTestDone.data (sau khi Simulator chay xong) va
 * dem so lenh (cluster) + ti le success theo QUY (dua tren timeStart - quy uoc SAN CO trong
 * TraceData2Test.year2Orders, tuc leg-cuoi/DCA-cuoi cua cluster, khong phai leg dau vi clusterFirstLegTime
 * la transient nen mat sau deserialize).
 * Success = calRateTp() > 0 (giu duoc lai toi cuoi, khong phu thuoc status vi SL/TimeStop dang tat).
 * Usage: java -cp <jar>:. QuarterTradeAnalyze <path-to-OrderTestDone.data>
 */
public class QuarterTradeAnalyze {
    public static void main(String[] args) {
        String path = args.length > 0 ? args[0] : "storage/OrderTestDone.data";
        @SuppressWarnings("unchecked")
        TreeMap<Long, OrderTargetInfoTest> all = (TreeMap<Long, OrderTargetInfoTest>) Storage.readObjectFromFile(path);
        if (all == null) {
            System.out.println("KHONG DOC DUOC: " + path);
            System.exit(1);
        }
        TreeMap<String, Integer> q2count = new TreeMap<>();
        TreeMap<String, Integer> q2success = new TreeMap<>();
        TreeMap<String, Integer> q2slDone = new TreeMap<>();
        int total = 0, totalSuccess = 0;
        for (OrderTargetInfoTest o : all.values()) {
            String ym = Utils.getMonth(o.timeStart); // yyyyMM (GMT+7)
            int year = Integer.parseInt(ym.substring(0, 4));
            int month = Integer.parseInt(ym.substring(4, 6));
            int q = (month - 1) / 3 + 1;
            String key = year + "Q" + q;
            q2count.merge(key, 1, Integer::sum);
            total++;
            Float rate = o.calRateTp();
            boolean success = rate != null && rate > 0f;
            if (success) {
                q2success.merge(key, 1, Integer::sum);
                totalSuccess++;
            }
            if (o.status == OrderTargetStatus.STOP_LOSS_DONE) {
                q2slDone.merge(key, 1, Integer::sum);
            }
        }
        System.out.println("TOTAL_ORDERS=" + total + " TOTAL_SUCCESS=" + totalSuccess
                + " SUCCESS_RATE=" + String.format("%.2f%%", total > 0 ? 100.0 * totalSuccess / total : 0));
        int quartersWithGe10 = 0, quartersTotal = 0;
        System.out.println("QUARTER\tCOUNT\tSUCCESS\tSUCCESS_RATE");
        for (String key : q2count.keySet()) {
            int c = q2count.get(key);
            int s = q2success.getOrDefault(key, 0);
            quartersTotal++;
            if (c >= 10) quartersWithGe10++;
            System.out.printf("%s\t%d\t%d\t%.1f%%%n", key, c, s, c > 0 ? 100.0 * s / c : 0.0);
        }
        System.out.println("QUARTERS_WITH_GE10_TRADES=" + quartersWithGe10 + "/" + quartersTotal);
    }
}
