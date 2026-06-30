package com.binance.chuyennd.ai_ml.wfo.framework;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.BatchPolicy;
import com.aerospike.client.policy.ScanPolicy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;

/** Verify batch-get tren server dich (server 8). args: srcHost srcPort srcNs set dstHost dstPort dstNs [n=20] */
public class BatchGetVerify {
    private static final Logger LOG = LoggerFactory.getLogger(BatchGetVerify.class);
    public static void main(String[] a) {
        String sh=a[0]; int sp=Integer.parseInt(a[1]); String sns=a[2]; String set=a[3];
        String dh=a[4]; int dp=Integer.parseInt(a[5]); String dns=a[6];
        int n=a.length>7?Integer.parseInt(a[7]):20;
        AerospikeClient src=new AerospikeClient(sh,sp);
        AerospikeClient dst=new AerospikeClient(dh,dp);
        List<byte[]> digests=new ArrayList<>();
        ScanPolicy spol=new ScanPolicy(); spol.maxRecords=n;
        try {
            src.scanAll(spol, sns, set, (key, rec) -> { synchronized(digests){ if(digests.size()<n) digests.add(key.digest); } });
        } catch (Exception e) { LOG.warn("scan src thu {} key: {}", digests.size(), e.getMessage()); }
        LOG.info("Thu {} key tu 226 set={}", digests.size(), set);
        Key[] keys=new Key[digests.size()];
        for (int i=0;i<keys.length;i++) keys[i]=new Key(dns, digests.get(i), set, null);
        try {
            Record[] recs=dst.get(new BatchPolicy(), keys);
            int hit=0; for (Record r:recs) if (r!=null) hit++;
            LOG.info("BATCH_GET_OK server8 dst={}:{} set={} keys={} hit={}", dh,dp,set,keys.length,hit);
        } catch (com.aerospike.client.AerospikeException ae) {
            LOG.error("BATCH_GET_FAIL rc={} msg={}", ae.getResultCode(), ae.getMessage());
        }
        src.close(); dst.close();
    }
}
