package com.binance.chuyennd.ai_ml.data;

import java.util.Collections;
import java.util.Map;

/**
 * [MAPAUD 2026-10-11] Nguon luu symbol_mapper cho {@link SimpleSymbolMapper} — tach I/O de cap id CAS duoc kiem
 * bang JUnit (2 "JVM" gia dung chung 1 store). Ban that: {@code aerospike.AerospikeSymbolMapperStore}.
 */
public interface SymbolMapperStore {

    /** Anh chup map + generation cua record (token CAS). generation=0 khi record chua ton tai. */
    final class Snapshot {
        public final Map<String, Short> map;
        public final int generation;

        public Snapshot(Map<String, Short> map, int generation) {
            this.map = Collections.unmodifiableMap(map);
            this.generation = generation;
        }
    }

    /** Doc map luc khoi tao (cum DOC theo cau hinh box — hanh vi cu {@code loadSymbolMapper}). */
    Map<String, Short> loadForInit();

    /** true neu process nay DUOC ghi mapper (Live242WriteGuard cho phep). false = shadow/kaggle/tool chi doc. */
    boolean writable();

    /** Doc map + generation tu CHINH cum se ghi (242) — dung cho cap id; KHONG doc ban sao (tranh cap tu map cu). */
    Snapshot readForWrite();

    /**
     * Ghi symbol-&gt;id CHI KHI generation record van = expectedGeneration VA symbol chua co trong map.
     *
     * @return true = da ghi; false = xung dot (process khac vua ghi) — goi lai readForWrite roi thu lai.
     */
    boolean putIfGenerationMatches(String symbol, short id, int expectedGeneration);
}
