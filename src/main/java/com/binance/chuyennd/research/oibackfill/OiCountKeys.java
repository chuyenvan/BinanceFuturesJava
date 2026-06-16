package com.binance.chuyennd.research.oibackfill;

import com.aerospike.client.AerospikeClient;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import java.util.regex.Pattern;

/**
 * TASK-013 — DEM CHINH XAC key 5 set OI/LS/taker (226 vs 242) de nail nghi van object-count xap xi cua Info.
 * Phan loai userKey: chunk-thang khop {@code _\d{6}$} (SYMBOL_yyyyMM) vs forward (con lai, key=SYMBOL).
 * DOC-ONLY (scanAll). Chay TREN 226. SLF4j.
 */
public class OiCountKeys {

    private static final Logger LOG = LoggerFactory.getLogger(OiCountKeys.class);
    private static final String NS = Configs.AEROSPIKE_NAMESPACE;
    private static final Pattern CHUNK = Pattern.compile(".*_\\d{6}$");

    public static void main(String[] args) {
        try {
            AerospikeClient c226 = DataManagerAerospikeFloatSim.getClient226();
            AerospikeClient c242 = DataManagerAerospikeFloatSim.getClient242();
            boolean pass = true;
            for (OiMetricSets.Metric m : OiMetricSets.ALL) {
                long[] a = count(c226, m.set);   // [total, chunk, forward]
                long[] b = count(c242, m.set);
                boolean chunkOk = a[1] == b[1];
                if (!chunkOk) pass = false;
                LOG.info("{} | 226[total={} chunk={} fwd={}] vs 242[total={} chunk={} fwd={}] | chunk-thang {}",
                        m.set, a[0], a[1], a[2], b[0], b[1], b[2],
                        chunkOk ? "KHOP" : ("LECH " + (b[1] - a[1])));
            }
            LOG.info("################ CHUNK-THANG 226 vs 242: {} ################", pass ? "KHOP HET" : "CO LECH (xem tren)");
        } catch (Exception e) {
            LOG.error("OiCountKeys loi: ", e);
            System.exit(1);
        }
        System.exit(0);
    }

    /** @return [total, chunk, forward] */
    private static long[] count(AerospikeClient client, String set) {
        AtomicLong chunk = new AtomicLong(), forward = new AtomicLong(), total = new AtomicLong();
        client.scanAll(null, NS, set, (key, rec) -> {
            total.incrementAndGet();
            if (key.userKey == null) return;
            if (CHUNK.matcher(key.userKey.toString()).matches()) chunk.incrementAndGet();
            else forward.incrementAndGet();
        });
        return new long[]{total.get(), chunk.get(), forward.get()};
    }
}
