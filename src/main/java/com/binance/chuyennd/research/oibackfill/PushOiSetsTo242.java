package com.binance.chuyennd.research.oibackfill;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * TASK-013 — ĐẨY 5 set metrics 226→242 (kiến trúc A: 242 = source). Worker Kaggle chỉ ghi được 226;
 * sau khi backfill xong (226 đủ), chạy tool NÀY <b>TRÊN 226</b> (226 mới thông 242) để bổ sung lịch sử
 * vào 242 — cùng đơn vị/khoá với forward 007-C ({@code open_interest}/{@code oi_data}).
 *
 * <p>Đọc 226 ({@code getMetricMap226}) → ghi 242 ({@code writeMetricMap242}, merge-guard chống mất lịch sử).
 * Idempotent (merge theo ts). Args: danh sách symbol, hoặc rỗng = mọi symbol trong {@link OiMetricSets#DONE_SET}.
 * {@code System.exit(0)} cuối main (CLAUDE.md #6).
 *
 * <p>⚠️ KHÔNG chạy trên dev/Kaggle (không tới 242). Chạy SSH-226.
 */
public class PushOiSetsTo242 {

    private static final Logger LOG = LoggerFactory.getLogger(PushOiSetsTo242.class);

    public static void main(String[] args) {
        try {
            List<String> symbols = resolveSymbols(args);
            LOG.info("📤 ĐẨY 226→242: {} symbol × {} set.", symbols.size(), OiMetricSets.ALL.length);

            int doneSym = 0;
            for (String symbol : symbols) {
                long totalPushed = 0;
                for (OiMetricSets.Metric m : OiMetricSets.ALL) {
                    try {
                        TreeMap<Long, Float> map = DataManagerAerospikeFloatSim.getMetricMap226(m.set, m.bin, symbol);
                        if (map.isEmpty()) continue;
                        DataManagerAerospikeFloatSim.writeMetricMap242(m.set, m.bin, symbol, map);
                        totalPushed += map.size();
                    } catch (Exception e) {
                        LOG.warn("⚠️ {} set={} đẩy lỗi: {}", symbol, m.set, e.getMessage());
                    }
                }
                doneSym++;
                if (doneSym % 50 == 0 || totalPushed > 0) {
                    LOG.info("   [{}/{}] {} → đẩy {} record (mọi set).", doneSym, symbols.size(), symbol, totalPushed);
                }
            }
            LOG.info("✅ ĐẨY 226→242 xong: {} symbol.", doneSym);
        } catch (Exception e) {
            LOG.error("❌ PushOiSetsTo242 lỗi: ", e);
            System.exit(1);
        }
        System.exit(0);
    }

    private static List<String> resolveSymbols(String[] args) {
        TreeSet<String> set = new TreeSet<>();
        if (args != null && args.length > 0) {
            for (String a : args) {
                for (String s : a.split("[,\\s]+")) {
                    if (!s.trim().isEmpty()) set.add(s.trim().toUpperCase());
                }
            }
            return new ArrayList<>(set);
        }
        // rỗng → mọi symbol đã DONE (scan done set).
        try {
            DataManagerAerospikeFloatSim.getClientOracle().scanAll(null, Configs.AEROSPIKE_NAMESPACE, OiMetricSets.DONE_SET,
                    (key, record) -> {
                        String sym = record.getString("symbol");
                        if (sym == null && key.userKey != null) sym = key.userKey.toString();
                        if (sym != null) set.add(sym.toUpperCase());
                    }, "symbol");
        } catch (Exception e) {
            LOG.error("❌ scan done set lỗi: {}", e.getMessage());
        }
        return new ArrayList<>(set);
    }
}
