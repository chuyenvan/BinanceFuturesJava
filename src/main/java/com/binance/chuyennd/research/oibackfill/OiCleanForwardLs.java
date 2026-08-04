package com.binance.chuyennd.research.oibackfill;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * TASK-013 — DON record forward "lac" (key=SYMBOL) trong 4 set LS/taker tren 226 (rac tu test/replicate cu;
 * ingest forward KHONG ghi LS/taker nen khong tai sinh). open_interest CO TINH (forward 007-C hop le) ->
 * KHONG dung. Chunk-thang (key=SYMBOL_yyyyMM) tuyet doi khong bi xoa nho regex.
 *
 * <p>Chi cham 226. DRY-RUN mac dinh; truyen arg "delete" de xoa thuc su. Guard: neu tong record-can-xoa
 * vuot {@code MAX_DELETE} -> ABORT (khong xoa gi). Chay TREN 226. SLF4j.
 */
public class OiCleanForwardLs {

    private static final Logger LOG = LoggerFactory.getLogger(OiCleanForwardLs.class);
    private static final String NS = Configs.AEROSPIKE_NAMESPACE;
    private static final Pattern CHUNK = Pattern.compile(".*_\\d{6}$");
    private static final int MAX_DELETE = 5; // guard chong xoa nham hang loat
    // 4 set LS/taker (KHONG gom open_interest).
    private static final String[] LS_SETS = {
            OiMetricSets.LS_TOPTRADER_ACC.set,
            OiMetricSets.LS_TOPTRADER_POS.set,
            OiMetricSets.LS_GLOBAL_ACC.set,
            OiMetricSets.TAKER_VOL.set
    };

    public static void main(String[] args) {
        boolean doDelete = args.length > 0 && "delete".equalsIgnoreCase(args[0]);
        try {
            AerospikeClient c226 = DataManagerAerospikeFloatSim.getClientOracle();

            // 1) Thu thap record forward (key=SYMBOL) tren 4 set LS/taker @226.
            List<Key> targets = new ArrayList<>();
            for (String set : LS_SETS) {
                List<Key> found = new ArrayList<>();
                c226.scanAll(null, NS, set, (key, rec) -> {
                    if (key.userKey == null) return;
                    if (!CHUNK.matcher(key.userKey.toString()).matches()) found.add(key);
                });
                for (Key k : found) {
                    Record r = c226.get(null, k);
                    LOG.info("[CAN DON] set={} key={} generation={} bins={}", set, k.userKey,
                            r == null ? -1 : r.generation, r == null ? "(null)" : r.bins.keySet());
                    targets.add(k);
                }
                if (found.isEmpty()) LOG.info("[OK] set={} : 0 record forward", set);
            }

            LOG.info("================ Tong record forward-lac can don: {} (mode={}) ================",
                    targets.size(), doDelete ? "DELETE" : "DRY-RUN");

            // 2) Guard.
            if (targets.size() > MAX_DELETE) {
                LOG.error("ABORT: tim thay {} record > nguong an toan {} -> KHONG xoa gi. Kiem tra lai.", targets.size(), MAX_DELETE);
                System.exit(1);
            }
            if (targets.isEmpty()) {
                LOG.info("Khong co gi de don. Thoat.");
                System.exit(0);
            }

            // 3) Xoa (chi khi mode=delete).
            if (doDelete) {
                int ok = 0;
                for (Key k : targets) {
                    boolean existed = c226.delete(null, k);
                    LOG.info("[DELETED] set={} key={} existed={}", k.setName, k.userKey, existed);
                    if (existed) ok++;
                }
                LOG.info("Da xoa {}/{} record @226.", ok, targets.size());

                // 4) Verify lai: 0 forward tren 4 set.
                for (String set : LS_SETS) {
                    final int[] cnt = {0};
                    c226.scanAll(null, NS, set, (key, rec) -> {
                        if (key.userKey != null && !CHUNK.matcher(key.userKey.toString()).matches()) cnt[0]++;
                    });
                    LOG.info("[VERIFY] set={} : forward con lai = {}", set, cnt[0]);
                }
            } else {
                LOG.info("DRY-RUN: chua xoa. Chay lai voi arg \"delete\" de xoa.");
            }
        } catch (Exception e) {
            LOG.error("OiCleanForwardLs loi: ", e);
            System.exit(1);
        }
        System.exit(0);
    }
}
