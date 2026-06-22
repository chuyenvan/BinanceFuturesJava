package com.binance.chuyennd.research;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.TreeMap;

/**
 * Kiểm số ĐIỂM THỰC bên trong record chunk-tháng của set selector pred mới (xác nhận 17k record
 * gói đủ điểm, không thiếu). Đọc lại qua getMetricMap226 (gộp toàn bộ chunk-tháng của 1 symbol).
 *
 * <p>Args: [set=funding_selector_pred_v1] [bin=p24h] [symbol=BTCUSDT]
 */
public class CheckMetricSetPoints {
    static final Logger LOG = LoggerFactory.getLogger(CheckMetricSetPoints.class);

    public static void main(String[] args) {
        String set = args.length > 0 ? args[0] : "funding_selector_pred_v1";
        String bin = args.length > 1 ? args[1] : "p24h";
        String sym = args.length > 2 ? args[2] : "BTCUSDT";

        TreeMap<Long, Float> m = DataManagerAerospikeFloatSim.getMetricMap226(set, bin, sym);
        LOG.info("set={} bin={} symbol={} => {} diem", set, bin, sym, m.size());
        if (!m.isEmpty()) {
            long first = m.firstKey(), last = m.lastKey();
            LOG.info("  range ts: {} .. {}", new java.util.Date(first), new java.util.Date(last));
            int n = 0;
            for (var e : m.entrySet()) {
                LOG.info("    {} -> {}", new java.util.Date(e.getKey()), e.getValue());
                if (++n >= 3) break;
            }
            // uoc luong so thang
            long spanDays = (last - first) / (24L * 3600 * 1000);
            LOG.info("  span ~{} ngay; neu cadence 15m thi ~{} diem ly thuyet", spanDays, spanDays * 96);
        }
    }
}
