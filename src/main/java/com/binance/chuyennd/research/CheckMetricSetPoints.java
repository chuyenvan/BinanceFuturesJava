package com.binance.chuyennd.research;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.TreeMap;

/**
 * Kiểm số ĐIỂM THỰC bên trong record của set selector pred (xác nhận record gói đủ điểm, không thiếu).
 * Đọc lại qua getMetricMap226 (chunk-THÁNG) hoặc getMetricMapDay226 (chunk-NGÀY) tùy granularity.
 *
 * <p>Args: [set=funding_selector_pred_v1] [bin=p24h] [symbol=BTCUSDT] [gran=month|day]
 */
public class CheckMetricSetPoints {
    static final Logger LOG = LoggerFactory.getLogger(CheckMetricSetPoints.class);

    public static void main(String[] args) {
        String set = args.length > 0 ? args[0] : "funding_selector_pred_v1";
        String bin = args.length > 1 ? args[1] : "p24h";
        String sym = args.length > 2 ? args[2] : "BTCUSDT";
        String gran = args.length > 3 ? args[3] : "month";

        TreeMap<Long, Float> m = gran.equalsIgnoreCase("day")
                ? DataManagerAerospikeFloatSim.getMetricMapDay226(set, bin, sym)
                : DataManagerAerospikeFloatSim.getMetricMap226(set, bin, sym);
        LOG.info("set={} bin={} symbol={} gran={} => {} diem", set, bin, sym, gran, m.size());
        if (!m.isEmpty()) {
            long first = m.firstKey(), last = m.lastKey();
            LOG.info("  range ts: {} .. {}", new java.util.Date(first), new java.util.Date(last));
            // kiem khoang cach ts pho bien (xac nhan cadence 1 phut cho set 1m)
            long prev = -1; java.util.Map<Long,Integer> gap = new java.util.HashMap<>();
            int n = 0;
            for (var e : m.entrySet()) {
                if (prev > 0) { long g = (e.getKey()-prev)/60000; gap.merge(g, 1, Integer::sum); }
                prev = e.getKey();
                if (n < 3) { LOG.info("    {} -> {}", new java.util.Date(e.getKey()), e.getValue()); n++; }
            }
            LOG.info("  khoang cach ts (phut) -> so lan: {}", gap.entrySet().stream()
                    .sorted((a,b)->b.getValue()-a.getValue()).limit(4).collect(java.util.stream.Collectors.toList()));
            long spanDays = (last - first) / (24L * 3600 * 1000);
            LOG.info("  span ~{} ngay", spanDays);
        }
    }
}
