package com.binance.chuyennd.ai_ml.wfo.framework;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.AerospikeException;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.ResultCode;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.ScanPolicy;
import com.aerospike.client.policy.WritePolicy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Copy 1:1 mot SET tu Aerospike nguon -> dich (giu nguyen key/value). Migrate 226 -> Oracle.
 * Throttle nguon bang ScanPolicy.recordsPerSecond (tranh device-overload rc=18 tren device file ext4)
 * + retry backoff khi rc=18. Env: COPY_RPS (default 6000), COPY_RETRY (default 8).
 * args: srcHost srcPort srcNs set dstHost dstPort dstNs
 */
public class CopyAerospikeSet {
    private static final Logger LOG = LoggerFactory.getLogger(CopyAerospikeSet.class);

    public static void main(String[] a) {
        String sh=a[0]; int sp=Integer.parseInt(a[1]); String sns=a[2]; String set=a[3];
        String dh=a[4]; int dp=Integer.parseInt(a[5]); String dns=a[6];
        int rps=Integer.parseInt(System.getenv().getOrDefault("COPY_RPS","6000"));
        int maxRetry=Integer.parseInt(System.getenv().getOrDefault("COPY_RETRY","8"));

        AerospikeClient src=new AerospikeClient(sh,sp);
        AerospikeClient dst=new AerospikeClient(dh,dp);
        WritePolicy wp=new WritePolicy();
        wp.recordExistsAction=RecordExistsAction.REPLACE;
        wp.maxRetries=5; wp.sleepBetweenRetries=200; wp.socketTimeout=3000; wp.totalTimeout=20000;

        ScanPolicy spol=new ScanPolicy();
        spol.concurrentNodes=false;        // doc tuan tu, giam ap luc ghi dong thoi
        spol.recordsPerSecond=rps;         // throttle nguon -> ghi <= kha nang flush device file

        AtomicLong ok=new AtomicLong(), err=new AtomicLong(), retried=new AtomicLong();
        long t0=System.currentTimeMillis();
        LOG.info("COPY set={} rps={} {}:{}/{} -> {}:{}/{}", set, rps, sh,sp,sns, dh,dp,dns);

        src.scanAll(spol, sns, set, (key, rec) -> {
            Key dk = (key.userKey != null) ? new Key(dns, set, key.userKey)
                                            : new Key(dns, key.digest, set, null);
            List<Bin> bins=new ArrayList<>();
            for (Map.Entry<String,Object> e : rec.bins.entrySet())
                bins.add(new Bin(e.getKey(), e.getValue()));
            Bin[] arr = bins.toArray(new Bin[0]);
            for (int attempt=1; ; attempt++) {
                try {
                    dst.put(wp, dk, arr);
                    long n=ok.incrementAndGet();
                    if (n % 200000 == 0)
                        LOG.info("  set={} copied={} retried={} ({}s)", set, n, retried.get(), (System.currentTimeMillis()-t0)/1000);
                    break;
                } catch (AerospikeException ae) {
                    if (ae.getResultCode()==ResultCode.DEVICE_OVERLOAD && attempt<=maxRetry) {
                        retried.incrementAndGet();
                        try { Thread.sleep(100L*attempt); } catch (InterruptedException ignore) { Thread.currentThread().interrupt(); break; }
                        continue;   // device flush kip -> thu lai
                    }
                    if (err.incrementAndGet() <= 5) LOG.warn("  copy err set={} rc={} {}", set, ae.getResultCode(), ae.getMessage());
                    break;
                } catch (Exception ex) {
                    if (err.incrementAndGet() <= 5) LOG.warn("  copy err set={}: {}", set, ex.getMessage());
                    break;
                }
            }
        });
        LOG.info("DONE set={} ok={} err={} retried={} time={}s", set, ok.get(), err.get(), retried.get(), (System.currentTimeMillis()-t0)/1000);
        src.close(); dst.close();
    }
}
