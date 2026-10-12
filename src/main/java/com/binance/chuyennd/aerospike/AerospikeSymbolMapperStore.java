package com.binance.chuyennd.aerospike;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.AerospikeException;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.ResultCode;
import com.aerospike.client.Value;
import com.aerospike.client.cdt.MapOperation;
import com.aerospike.client.cdt.MapOrder;
import com.aerospike.client.cdt.MapPolicy;
import com.aerospike.client.cdt.MapWriteFlags;
import com.aerospike.client.policy.GenerationPolicy;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.ai_ml.data.SymbolMapperStore;
import com.binance.chuyennd.tradecore.Configs;

import java.util.HashMap;
import java.util.Map;

/**
 * [MAPAUD 2026-10-11] Store that cua symbol_mapper (Aerospike set {@code symbol_mapper}, key {@code global_id_map},
 * bin map String-&gt;Long). Cap id = doc + ghi tren CUNG client 242 voi kiem generation (CAS) + CREATE_ONLY cho
 * phan tu map — 2 process khong the cung ghi 1 id cho 2 symbol, va khong process nao ghi de id cua symbol da co.
 * Ghi van qua {@link Live242WriteGuard} (shadow/kaggle khong ghi).
 */
public class AerospikeSymbolMapperStore implements SymbolMapperStore {

    private final AerospikeClient testClient;   // null = getClient242()

    public AerospikeSymbolMapperStore() {
        this(null);
    }

    AerospikeSymbolMapperStore(AerospikeClient client) {
        this.testClient = client;
    }

    private AerospikeClient client() {
        return testClient != null ? testClient : DataManagerAerospikeFloatSim.getClient242();
    }

    public static Key key() {
        return new Key(Configs.AEROSPIKE_NAMESPACE, DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_MAPPER,
                DataManagerAerospikeFloatSim.MAPPER_KEY_GLOBAL);
    }

    /** Chuyen bin map Aerospike (String-&gt;Long) sang String-&gt;Short; id ngoai [1, Short.MAX] =&gt; nem (hong du lieu). */
    public static Map<String, Short> toShortMap(Map<?, ?> raw) {
        Map<String, Short> m = new HashMap<>();
        if (raw == null) return m;
        for (Map.Entry<?, ?> e : raw.entrySet()) {
            long v = ((Number) e.getValue()).longValue();
            if (v < 1 || v > Short.MAX_VALUE) {
                throw new IllegalStateException("symbol_mapper id ngoai mien short: " + e.getKey() + "=" + v);
            }
            m.put(String.valueOf(e.getKey()), (short) v);
        }
        return m;
    }

    @Override
    public Map<String, Short> loadForInit() {
        return DataManagerAerospikeFloatSim.loadSymbolMapper();
    }

    @Override
    public boolean writable() {
        return Live242WriteGuard.writesEnabled();
    }

    @Override
    public Snapshot readForWrite() {
        Record r = client().get(null, key());
        if (r == null) return new Snapshot(new HashMap<>(), 0);
        return new Snapshot(toShortMap(r.getMap(DataManagerAerospikeFloatSim.MAPPER_BIN_NAME)), r.generation);
    }

    @Override
    public boolean putIfGenerationMatches(String symbol, short id, int expectedGeneration) {
        if (!Live242WriteGuard.allowed("symbol_mapper")) {
            throw new IllegalStateException("Live242WriteGuard chan ghi symbol_mapper");
        }
        WritePolicy wp = new WritePolicy();
        wp.sendKey = true;
        wp.expiration = 0;
        if (expectedGeneration > 0) {
            wp.generationPolicy = GenerationPolicy.EXPECT_GEN_EQUAL;
            wp.generation = expectedGeneration;
            wp.recordExistsAction = RecordExistsAction.UPDATE_ONLY;
        } else {
            wp.recordExistsAction = RecordExistsAction.CREATE_ONLY;
        }
        MapPolicy mp = new MapPolicy(MapOrder.UNORDERED, MapWriteFlags.CREATE_ONLY);
        try {
            client().operate(wp, key(), MapOperation.put(mp, DataManagerAerospikeFloatSim.MAPPER_BIN_NAME,
                    Value.get(symbol), Value.get((long) id)));
            return true;
        } catch (AerospikeException e) {
            int rc = e.getResultCode();
            if (rc == ResultCode.GENERATION_ERROR || rc == ResultCode.ELEMENT_EXISTS
                    || rc == ResultCode.KEY_EXISTS_ERROR || rc == ResultCode.KEY_NOT_FOUND_ERROR) {
                return false;   // xung dot: process khac vua ghi
            }
            throw e;
        }
    }
}
