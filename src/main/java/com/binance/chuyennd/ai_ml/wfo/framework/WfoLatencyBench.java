package com.binance.chuyennd.ai_ml.wfo.framework;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.WritePolicy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Arrays;
import java.util.Collections;
import java.util.Locale;

/**
 * Benchmark latency GET 1 ban ghi (tuong dong WfoJob ~370B) toi 1 Aerospike host.
 * Dung de so sanh vi tri state-store (226 remote vs Oracle-local vs ...).
 * args: host port ns set [N=300] [warmup=30]
 */
public class WfoLatencyBench {
    private static final Logger LOG = LoggerFactory.getLogger(WfoLatencyBench.class);

    public static void main(String[] a) {
        String host = a[0];
        int port = Integer.parseInt(a[1]);
        String ns = a[2];
        String set = a[3];
        int n = a.length > 4 ? Integer.parseInt(a[4]) : 300;
        int warm = a.length > 5 ? Integer.parseInt(a[5]) : 30;

        AerospikeClient c = new AerospikeClient(host, port);
        Key k = new Key(ns, set, "wfo_bench_key");
        String payload = String.join(",", Collections.nCopies(20, "gene=0.12345678"));

        boolean writeOk = false;
        try {
            WritePolicy wp = new WritePolicy();
            c.put(wp, k,
                    new Bin("type", "strategy_window"), new Bin("state", "PENDING"),
                    new Bin("payload", payload), new Bin("result", ""), new Bin("owner", ""),
                    new Bin("lease", 0L), new Bin("retry", 0),
                    new Bin("created", System.currentTimeMillis()), new Bin("id", "wfo_bench_key"));
            writeOk = true;
        } catch (Exception e) {
            LOG.warn("WRITE_FAIL host={}: {}", host, e.getMessage());
        }

        for (int i = 0; i < warm; i++) { try { c.get(null, k); } catch (Exception ignore) {} }

        long[] t = new long[n];
        boolean hit = false;
        for (int i = 0; i < n; i++) {
            long s = System.nanoTime();
            Record r = null;
            try { r = c.get(null, k); } catch (Exception ignore) {}
            t[i] = System.nanoTime() - s;
            if (r != null) hit = true;
        }
        Arrays.sort(t);
        double mean = 0; for (long x : t) mean += x; mean /= n;
        LOG.info(String.format(Locale.US,
            "RESULT host=%s:%d ns=%s set=%s N=%d writeOK=%b getHit=%b | min=%.2f p50=%.2f p90=%.2f p99=%.2f max=%.2f mean=%.2f (us)",
            host, port, ns, set, n, writeOk, hit,
            t[0]/1000.0, t[(int)(n*0.5)]/1000.0, t[(int)(n*0.9)]/1000.0,
            t[(int)(n*0.99)]/1000.0, t[n-1]/1000.0, mean/1000.0));
        c.close();
    }
}
