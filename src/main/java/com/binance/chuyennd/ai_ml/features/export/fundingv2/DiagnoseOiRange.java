package com.binance.chuyennd.ai_ml.features.export.fundingv2;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.research.oibackfill.OiMetricSets;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.*;

/**
 * TASK-101: Chan doan range OI trong Aerospike - 5 coin dai dien, dem record theo nam.
 * Chay tren 226 (box can AEROSPIKE_READ_CLUSTER=226), KHONG ghi gi.
 * Usage: java DiagnoseOiRange [BTCUSDT ETHUSDT ...]
 */
public class DiagnoseOiRange {
    private static final Logger LOG = LoggerFactory.getLogger(DiagnoseOiRange.class);

    public static void main(String[] args) throws Exception {
        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd");
        sdf.setTimeZone(TimeZone.getTimeZone("UTC"));

        long y2021 = 1609459200000L;
        long y2022 = 1640995200000L;
        long y2023 = 1672531200000L;
        long y2024 = 1704067200000L;
        long y2025 = 1735689600000L;
        long y2026 = 1767225600000L;

        String[] coins = args.length > 0 ? args
                : new String[]{"BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT"};

        for (String coin : coins) {
            TreeMap<Long, Float> oi = DataManagerAerospikeFloatSim.getMetricMap226(
                    OiMetricSets.OI.set, OiMetricSets.OI.bin, coin);
            if (oi == null || oi.isEmpty()) {
                LOG.info("COIN={} OI=EMPTY", coin);
                continue;
            }
            long minTs = oi.firstKey(), maxTs = oi.lastKey();
            int n2021 = count(oi, y2021, y2022);
            int n2022 = count(oi, y2022, y2023);
            int n2023 = count(oi, y2023, y2024);
            int n2024 = count(oi, y2024, y2025);
            int n2025 = count(oi, y2025, y2026);
            LOG.info("COIN={} total={} range=[{} .. {}] | 2021={} 2022={} 2023={} 2024={} 2025={}",
                    coin, oi.size(), sdf.format(new Date(minTs)), sdf.format(new Date(maxTs)),
                    n2021, n2022, n2023, n2024, n2025);
        }
        LOG.info("DONE");
    }

    private static int count(TreeMap<Long, Float> m, long from, long to) {
        return m.subMap(from, to).size();
    }
}
