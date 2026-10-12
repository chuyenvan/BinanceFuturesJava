package com.binance.chuyennd.aerospike.tools;

import com.binance.chuyennd.ai_ml.data.SymbolIdRules;
import org.junit.Test;

import java.util.HashMap;
import java.util.Map;

import static org.junit.Assert.*;

/** [LIVEFIX2] rollback mapper: toJson -> parseBackupMap; restorePlan dao nguoc planRepair, giu symbol moi. */
public class SymbolMapperRepairToolTest {

    private static Map<String, Short> withDups() {
        Map<String, Short> m = new HashMap<>();
        for (int i = 1; i <= 842; i++) m.put("S" + i + "USDT", (short) i);
        for (int i = 0; i < 8; i++) {
            m.put("A" + i + "USDT", (short) (843 + i));
            m.put("B" + i + "USDT", (short) (843 + i));
        }
        for (int i = 851; i <= 933; i++) m.put("S" + i + "USDT", (short) i);
        return m;
    }

    @Test
    public void backupJsonRoundTrip() {
        Map<String, Short> m = withDups();
        m.put("Q\"X\\USDT", (short) 7000);
        assertEquals(m, SymbolMapperRepairTool.parseBackupMap(SymbolMapperRepairTool.toJson(m, 1284)));
    }

    @Test
    public void restorePlan_revertsRepair_keepsNewSymbols() {
        Map<String, Short> orig = withDups();
        Map<String, Short> fixed = new HashMap<>(orig);
        fixed.putAll(SymbolIdRules.planRepair(orig));
        fixed.put("NEWAFTERUSDT", (short) 950);            // niem yet moi sau repair
        Map<String, Short> plan = SymbolMapperRepairTool.restorePlan(fixed, orig);
        assertEquals(16, plan.size());
        Map<String, Short> restored = new HashMap<>(fixed);
        restored.putAll(plan);
        Map<String, Short> expect = new HashMap<>(orig);
        expect.put("NEWAFTERUSDT", (short) 950);
        assertEquals(expect, restored);
        assertEquals(8, SymbolIdRules.duplicateIds(restored).size());
        assertTrue(SymbolMapperRepairTool.restorePlan(orig, orig).isEmpty());
    }

    @Test(expected = IllegalStateException.class)
    public void restorePlan_refusesCollisionWithNewSymbol() {
        Map<String, Short> backup = new HashMap<>();
        backup.put("AUSDT", (short) 5);
        Map<String, Short> current = new HashMap<>();
        current.put("AUSDT", (short) 9);
        current.put("NEWUSDT", (short) 5);
        SymbolMapperRepairTool.restorePlan(current, backup);
    }
}
