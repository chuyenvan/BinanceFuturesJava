package com.binance.chuyennd.research.oibackfill;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import com.google.gson.reflect.TypeToken;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.lang.reflect.Type;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.regex.Pattern;

/**
 * TASK-035 — MIGRATE record forward "1-record/symbol" (key=SYMBOL) cua set open_interest sang chunk-thang
 * (SYMBOL_yyyyMM), de thong nhat schema voi history 013 + ingest moi. Voi tung record forward:
 *   1) doc + giai nen map (ts->OI),
 *   2) MERGE vao chunk-thang (writeMetricMap, merge-guard san),
 *   3) VERIFY chunk-thang da hap thu DU moi ts (gia tri khop),
 *   4) chi khi verify OK moi XOA record key=SYMBOL.
 *
 * <p>Chi cham set open_interest. Chunk-thang (key match {@code _\d{6}$}) KHONG bao gio bi xoa.
 * Args: [target=226|242 (mac dinh 242)] [migrate] (khong co "migrate" -> DRY-RUN, khong ghi/khong xoa).
 * Chay TREN 226. SLF4j.
 */
public class OiMigrateForwardToChunk {

    private static final Logger LOG = LoggerFactory.getLogger(OiMigrateForwardToChunk.class);
    private static final String NS = Configs.AEROSPIKE_NAMESPACE;
    private static final String SET = OiMetricSets.OI.set;   // open_interest
    private static final String BIN = OiMetricSets.OI.bin;   // oi_data
    private static final Pattern CHUNK = Pattern.compile(".*_\\d{6}$");
    private static final Type MAP_SF = new TypeToken<Map<String, Float>>() {}.getType();

    public static void main(String[] args) {
        String target = "242";
        boolean doMigrate = false;
        for (String a : args) {
            if ("226".equals(a) || "242".equals(a)) target = a;
            if ("migrate".equalsIgnoreCase(a)) doMigrate = true;
        }
        final boolean is226 = "226".equals(target);
        try {
            AerospikeClient client = is226 ? DataManagerAerospikeFloatSim.getClient226()
                                           : DataManagerAerospikeFloatSim.getClient242();
            LOG.info("################ MIGRATE forward->chunk | target={} | mode={} ################",
                    target, doMigrate ? "MIGRATE" : "DRY-RUN");

            // 1) Thu thap key forward (key=SYMBOL, KHONG match _yyyyMM).
            List<Key> fwdKeys = new ArrayList<>();
            client.scanAll(null, NS, SET, (key, rec) -> {
                if (key.userKey != null && !CHUNK.matcher(key.userKey.toString()).matches()) fwdKeys.add(key);
            });
            LOG.info("Tim thay {} record forward key=SYMBOL tren open_interest@{}.", fwdKeys.size(), target);
            if (fwdKeys.isEmpty()) { LOG.info("Khong co gi de migrate."); System.exit(0); }

            int merged = 0, deleted = 0, skipped = 0;
            for (Key k : fwdKeys) {
                String symbol = k.userKey.toString();
                TreeMap<Long, Float> fwd = decode(client.get(null, k));
                if (fwd.isEmpty()) {
                    LOG.warn("  [SKIP] {} : record forward rong/loi giai nen -> khong dung", symbol);
                    skipped++;
                    continue;
                }
                long tMin = fwd.firstKey(), tMax = fwd.lastKey();
                if (!doMigrate) {
                    LOG.info("  [DRY] {} : {} diem, ts[{}..{}] -> se merge vao chunk-thang roi xoa", symbol, fwd.size(), tMin, tMax);
                    continue;
                }

                // 2) MERGE vao chunk-thang.
                int err = is226 ? DataManagerAerospikeFloatSim.writeMetricMap226(SET, BIN, symbol, fwd)
                                : DataManagerAerospikeFloatSim.writeMetricMap242(SET, BIN, symbol, fwd);
                if (err != 0) {
                    LOG.warn("  [SKIP] {} : merge loi {} chunk -> KHONG xoa record forward", symbol, err);
                    skipped++;
                    continue;
                }
                merged++;

                // 3) VERIFY chunk-thang hap thu du moi ts + gia tri khop.
                TreeMap<Long, Float> chunk = is226 ? DataManagerAerospikeFloatSim.getMetricMap226(SET, BIN, symbol)
                                                   : DataManagerAerospikeFloatSim.getMetricMap242(SET, BIN, symbol);
                long miss = 0;
                for (Map.Entry<Long, Float> e : fwd.entrySet()) {
                    Float c = chunk.get(e.getKey());
                    if (c == null || Math.abs(c - e.getValue()) > 1e-6) miss++;
                }
                if (miss > 0) {
                    LOG.warn("  [SKIP] {} : chunk-thang thieu/lech {} ts sau merge -> KHONG xoa (giu record forward)", symbol, miss);
                    skipped++;
                    continue;
                }

                // 4) Verify OK -> xoa record forward key=SYMBOL.
                boolean existed = client.delete(null, k);
                if (existed) deleted++;
                LOG.info("  [OK] {} : merged {} diem -> chunk, da xoa record forward (existed={})", symbol, fwd.size(), existed);
            }

            LOG.info("================ KET QUA: merged={} deleted={} skipped={} (mode={}) ================",
                    merged, deleted, skipped, doMigrate ? "MIGRATE" : "DRY-RUN");

            if (doMigrate) {
                final int[] remain = {0};
                client.scanAll(null, NS, SET, (key, rec) -> {
                    if (key.userKey != null && !CHUNK.matcher(key.userKey.toString()).matches()) remain[0]++;
                });
                LOG.info("[VERIFY] open_interest@{} : forward con lai = {}", target, remain[0]);
            } else {
                LOG.info("DRY-RUN: chua ghi/xoa gi. Chay lai voi args \"{} migrate\" de thuc thi.", target);
            }
        } catch (Exception e) {
            LOG.error("OiMigrateForwardToChunk loi: ", e);
            System.exit(1);
        }
        System.exit(0);
    }

    private static TreeMap<Long, Float> decode(Record r) {
        TreeMap<Long, Float> out = new TreeMap<>();
        try {
            if (r == null) return out;
            byte[] c = (byte[]) r.getValue(BIN);
            if (c == null || c.length == 0) return out;
            String json = new String(Snappy.uncompress(c), "UTF-8");
            Map<String, Float> raw = Utils.gson.fromJson(json, MAP_SF);
            if (raw != null) raw.forEach((k, v) -> out.put(Long.parseLong(k), v));
        } catch (Exception e) {
            LOG.warn("decode loi: {}", e.getMessage());
        }
        return out;
    }
}
