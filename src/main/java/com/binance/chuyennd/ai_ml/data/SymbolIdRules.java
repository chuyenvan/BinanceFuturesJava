package com.binance.chuyennd.ai_ml.data;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * [MAPAUD 2026-10-11] Luat THUAN (khong I/O) cho symbol_mapper: phat hien id trung, cap id moi, ke hoach sua.
 *
 * <p>Bat bien: trong ban mapper DA GHI (Aerospike 242 set symbol_mapper/global_id_map), moi id thuoc DUNG 1 symbol.
 * Vi pham da xay ra 07/2026: 8 id 843..850 moi id 2 symbol (docs/audit/MAPPER_AUDIT_20261011.md) do nhieu JVM
 * cap id bang bo dem RIENG trong RAM ({@code ++counter}) roi {@code MapOperation.put} khong kiem trung.
 *
 * <p>Quy tac cap id: id moi = max(id da ghi, id cuc bo da cap) + 1 — KHONG BAO GIO tai su dung id da tung xuat hien
 * (ke ca id "lo" 752..759 va id trung 843..850 sau khi sua) de du lieu cu khoa theo id khong bi gan nham sang symbol moi.
 */
public final class SymbolIdRules {

    private SymbolIdRules() { }

    /** id -> danh sach symbol (sap xep) cho moi id co &gt;= 2 symbol. Rong = mapper hop le. Thu tu id tang dan. */
    public static Map<Short, List<String>> duplicateIds(Map<String, Short> symbolToId) {
        Map<Short, List<String>> inv = new TreeMap<>();
        for (Map.Entry<String, Short> e : symbolToId.entrySet()) {
            inv.computeIfAbsent(e.getValue(), k -> new ArrayList<>()).add(e.getKey());
        }
        Map<Short, List<String>> dups = new TreeMap<>();
        for (Map.Entry<Short, List<String>> e : inv.entrySet()) {
            if (e.getValue().size() > 1) {
                List<String> l = new ArrayList<>(e.getValue());
                Collections.sort(l);
                dups.put(e.getKey(), l);
            }
        }
        return dups;
    }

    /** Fail-fast: nem IllegalStateException neu co id trung (thong diep liet ke du id/symbol de sua). */
    public static void assertUniqueIds(Map<String, Short> symbolToId, String source) {
        Map<Short, List<String>> d = duplicateIds(symbolToId);
        if (!d.isEmpty()) {
            throw new IllegalStateException("symbol_mapper [" + source + "] co " + d.size() + " id dung chung: " + d
                    + " — sua bang SymbolMapperRepairTool (docs/audit/MAPPER_AUDIT_20261011.md, muc Runbook)"
                    + " hoac tam dat SYMBOL_MAPPER_DUP_POLICY=WARN");
        }
    }

    /** Id lon nhat trong map (0 neu rong). */
    public static short maxId(Map<String, Short> symbolToId) {
        short m = 0;
        for (Short v : symbolToId.values()) {
            if (v != null && v > m) m = v;
        }
        return m;
    }

    /** Id ke tiep = max(maxPersisted, maxLocal) + 1; nem neu tran short. */
    public static short nextId(short maxPersisted, short maxLocal) {
        int n = Math.max(maxPersisted, maxLocal) + 1;
        if (n > Short.MAX_VALUE) throw new IllegalStateException("symbol id tran short: " + n);
        return (short) n;
    }

    /**
     * Ke hoach sua id trung: MOI symbol cua MOI id trung nhan id MOI duy nhat (max+1, max+2, ... theo thu tu
     * (id cu, ten symbol) tang dan); id trung cu bi BO HAN (khong symbol nao giu) vi du lieu lich su khoa theo id do
     * da tron 2 symbol — khong the gan cho symbol nao ma dung. Symbol khac giu nguyen id.
     *
     * @return symbol -> id moi (chi cac symbol thay doi). Rong neu khong co id trung.
     */
    public static Map<String, Short> planRepair(Map<String, Short> symbolToId) {
        Map<Short, List<String>> d = duplicateIds(symbolToId);
        Map<String, Short> plan = new TreeMap<>();
        short next = maxId(symbolToId);
        for (Map.Entry<Short, List<String>> e : d.entrySet()) {
            for (String s : e.getValue()) {
                next = nextId(next, (short) 0);
                plan.put(s, next);
            }
        }
        return plan;
    }
}
