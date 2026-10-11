package com.binance.chuyennd.aerospike.tools;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Record;
import com.aerospike.client.Value;
import com.aerospike.client.cdt.MapOperation;
import com.aerospike.client.cdt.MapPolicy;
import com.aerospike.client.policy.GenerationPolicy;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.AerospikeSymbolMapperStore;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.aerospike.Live242WriteGuard;
import com.binance.chuyennd.ai_ml.data.SymbolIdRules;
import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * [MAPAUD 2026-10-11] Kiem / sua id trung trong symbol_mapper 242 (docs/audit/MAPPER_AUDIT_20261011.md, muc Runbook).
 *
 * <pre>
 *   check                 : CHI DOC — n, max id, id trung, id lo; exit 3 neu co id trung.
 *   plan                  : CHI DOC — in ke hoach {@link SymbolIdRules#planRepair} (moi symbol cua id trung -&gt; id moi).
 *   apply &lt;backup.json&gt;  : GHI 242 — can MAPPER_REPAIR_CONFIRM=YES + Live242WriteGuard cho ghi; backup record
 *                           (file chua ton tai) TRUOC; 1 lenh operate CAS (generation) putItems; doc lai, assert 0 trung.
 * </pre>
 * Khong goi SimpleSymbolMapper (init se fail-fast khi map dang co id trung).
 */
public class SymbolMapperRepairTool {

    private static final Logger LOG = LoggerFactory.getLogger(SymbolMapperRepairTool.class);
    public static final String KEY_CONFIRM = "MAPPER_REPAIR_CONFIRM";

    public static void main(String[] args) throws Exception {
        String mode = args.length > 0 ? args[0] : "check";
        AerospikeClient c = DataManagerAerospikeFloatSim.getClient242();
        Record r = c.get(null, AerospikeSymbolMapperStore.key());
        if (r == null) {
            LOG.error("⛔ symbol_mapper khong ton tai tren 242");
            System.exit(2);
        }
        Map<String, Short> m = AerospikeSymbolMapperStore.toShortMap(r.getMap(DataManagerAerospikeFloatSim.MAPPER_BIN_NAME));
        Map<Short, List<String>> dups = SymbolIdRules.duplicateIds(m);
        int holes = SymbolIdRules.maxId(m) - (int) m.values().stream().distinct().count();
        LOG.info("[MAPPER-CHECK] n={} maxId={} gen={} idTrung={} {} idLo={}", m.size(), SymbolIdRules.maxId(m),
                r.generation, dups.size(), dups, holes);
        Map<String, Short> plan = SymbolIdRules.planRepair(m);
        if ("check".equals(mode)) System.exit(dups.isEmpty() ? 0 : 3);
        LOG.info("[MAPPER-PLAN] {} symbol doi id: {}", plan.size(), plan);
        if ("plan".equals(mode) || plan.isEmpty()) return;
        if (!"apply".equals(mode)) throw new IllegalArgumentException("mode = check|plan|apply");
        apply(c, r, m, plan, args.length > 1 ? args[1] : null);
    }

    static String toJson(Map<String, Short> m, int generation) {
        StringBuilder sb = new StringBuilder("{\"generation\":").append(generation).append(",\"map\":{");
        boolean first = true;
        for (Map.Entry<String, Short> e : new TreeMap<>(m).entrySet()) {
            if (!first) sb.append(',');
            first = false;
            sb.append('"').append(e.getKey().replace("\\", "\\\\").replace("\"", "\\\"")).append("\":").append(e.getValue());
        }
        return sb.append("}}\n").toString();
    }

    private static void apply(AerospikeClient c, Record r, Map<String, Short> m, Map<String, Short> plan,
                              String backupPath) throws Exception {
        if (!"YES".equals(Cfg.get(KEY_CONFIRM))) throw new IllegalStateException("can " + KEY_CONFIRM + "=YES");
        if (!Live242WriteGuard.writesEnabled()) throw new IllegalStateException("Live242WriteGuard chan ghi (shadow host?)");
        if (backupPath == null || new File(backupPath).exists()) {
            throw new IllegalStateException("can duong dan backup CHUA ton tai: " + backupPath);
        }
        Files.write(new File(backupPath).toPath(), toJson(m, r.generation).getBytes(StandardCharsets.UTF_8));
        LOG.info("💾 backup {} ({} symbol, gen={})", backupPath, m.size(), r.generation);
        Map<Value, Value> items = new HashMap<>();
        for (Map.Entry<String, Short> e : plan.entrySet()) items.put(Value.get(e.getKey()), Value.get((long) e.getValue()));
        WritePolicy wp = new WritePolicy();
        wp.sendKey = true;
        wp.expiration = 0;
        wp.recordExistsAction = RecordExistsAction.UPDATE_ONLY;
        wp.generationPolicy = GenerationPolicy.EXPECT_GEN_EQUAL;
        wp.generation = r.generation;
        c.operate(wp, AerospikeSymbolMapperStore.key(),
                MapOperation.putItems(MapPolicy.Default, DataManagerAerospikeFloatSim.MAPPER_BIN_NAME, items));
        Record after = c.get(null, AerospikeSymbolMapperStore.key());
        Map<String, Short> m2 = AerospikeSymbolMapperStore.toShortMap(after.getMap(DataManagerAerospikeFloatSim.MAPPER_BIN_NAME));
        SymbolIdRules.assertUniqueIds(m2, "after-repair");
        for (Map.Entry<String, Short> e : plan.entrySet()) {
            if (!e.getValue().equals(m2.get(e.getKey()))) throw new IllegalStateException("sau sua lech: " + e);
        }
        if (m2.size() != m.size()) throw new IllegalStateException("so symbol doi " + m.size() + " -> " + m2.size());
        LOG.info("✅ [MAPPER-REPAIR] OK: n={} maxId={} gen={} 0 id trung. KHOI DONG LAI moi JVM ghi mapper.",
                m2.size(), SymbolIdRules.maxId(m2), after.generation);
    }
}
