package com.binance.chuyennd.ai_ml.data;

import org.junit.Assume;
import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.junit.Assert.*;

/**
 * [LIVEFIX2 2026-10-11] Mo phong deploy tren BAN SAO mapper that cua 242 (khong ghi 242):
 * jar moi + mapper HIEN TAI => init fail-fast (dung thiet ke); mapper SAU planRepair => init PASS, id cu giu nguyen.
 * Chay khi co env MAPPER_SNAPSHOT_JSON (JSON {"SYM": id, ...} — research/analysis/mapaud_dump.py); khong co => skip.
 * Ngoai ra luon chay 1 ca tong hop (khong can file).
 */
public class SymbolMapperSnapshotRepairTest {

    static Map<String, Short> parse(String json) {
        Map<String, Short> m = new HashMap<>();
        Matcher mt = Pattern.compile("\"([^\"]+)\"\\s*:\\s*(\\d+)").matcher(json);
        while (mt.find()) m.put(mt.group(1), Short.parseShort(mt.group(2)));
        return m;
    }

    @Test
    public void realSnapshot242_failFastThenPassAfterRepair() throws Exception {
        String path = System.getenv("MAPPER_SNAPSHOT_JSON");
        Assume.assumeTrue("MAPPER_SNAPSHOT_JSON khong dat — skip", path != null && !path.isEmpty());
        Map<String, Short> m = parse(new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8));
        String report = simulate(m);
        System.out.println(report);
    }

    @Test
    public void synthetic_failFastThenPassAfterRepair() {
        Map<String, Short> m = new HashMap<>();
        for (int i = 1; i <= 842; i++) m.put("S" + i + "USDT", (short) i);
        for (int i = 0; i < 8; i++) {
            m.put("A" + i + "USDT", (short) (843 + i));
            m.put("B" + i + "USDT", (short) (843 + i));
        }
        for (int i = 851; i <= 933; i++) m.put("S" + i + "USDT", (short) i);
        String r = simulate(m);
        assertTrue(r, r.contains("plan=16 ids=934..949"));
    }

    /** Mo phong 4 buoc: (1) check (2) init FAIL fail-fast, WARN chay (3) plan (4) ap plan len BAN SAO => init PASS. */
    static String simulate(Map<String, Short> m) {
        StringBuilder sb = new StringBuilder();
        Map<Short, List<String>> dups = SymbolIdRules.duplicateIds(m);
        short max = SymbolIdRules.maxId(m);
        sb.append("[SNAP] n=").append(m.size()).append(" maxId=").append(max).append(" idTrung=").append(dups.size())
          .append(' ').append(new TreeMap<>(dups)).append('\n');

        SymbolMapperIdTest.FakeStore cur = new SymbolMapperIdTest.FakeStore();
        cur.data.putAll(m);
        boolean failed = false;
        try {
            new SimpleSymbolMapper(cur, "FAIL").init();
        } catch (RuntimeException e) {
            failed = true;
            sb.append("[SNAP] jar moi + mapper hien tai: init FAIL-FAST (dung) — ").append(e.getClass().getSimpleName()).append('\n');
        }
        if (!dups.isEmpty()) assertTrue("mapper co id trung phai fail-fast", failed);
        SimpleSymbolMapper warn = new SimpleSymbolMapper(cur, "WARN");
        warn.init();
        assertEquals(m.size(), warn.getAllMappings().size());

        Map<String, Short> plan = SymbolIdRules.planRepair(m);
        TreeMap<Short, String> byId = new TreeMap<>();
        for (Map.Entry<String, Short> e : plan.entrySet()) byId.put(e.getValue(), e.getKey());
        int nDupSyms = 0;
        for (List<String> l : dups.values()) nDupSyms += l.size();
        assertEquals(nDupSyms, plan.size());
        if (!plan.isEmpty()) {
            assertEquals(max + 1, (int) byId.firstKey());
            assertEquals(max + plan.size(), (int) byId.lastKey());
            sb.append("[SNAP] plan=").append(plan.size()).append(" ids=").append(byId.firstKey()).append("..")
              .append(byId.lastKey()).append(' ').append(byId).append('\n');
        }

        Map<String, Short> fixed = new HashMap<>(m);
        fixed.putAll(plan);
        SymbolIdRules.assertUniqueIds(fixed, "snapshot-after-repair");
        SymbolMapperIdTest.FakeStore after = new SymbolMapperIdTest.FakeStore();
        after.data.putAll(fixed);
        SimpleSymbolMapper ok = new SimpleSymbolMapper(after, "FAIL");
        ok.init();   // PASS (khong nem)
        assertEquals(m.size(), ok.getAllMappings().size());
        int unchanged = 0;
        for (Map.Entry<String, Short> e : m.entrySet()) {
            if (plan.containsKey(e.getKey())) continue;
            assertEquals(e.getValue(), (Short) ok.getId(e.getKey()));
            unchanged++;
        }
        short next = ok.getId("LIVEFIX2NEWUSDT");
        assertEquals(max + plan.size() + 1, next);
        for (short id : fixed.values()) assertTrue("id " + id + " < CAPACITY", SymbolIdLimits.inRange(id));
        sb.append("[SNAP] mapper sau repair: init PASS n=").append(ok.getAllMappings().size() - 1)
          .append(" id_khong_doi=").append(unchanged).append(" id_moi_ke_tiep=").append(next)
          .append(" maxId<CAPACITY(").append(SymbolIdLimits.CAPACITY).append(")=true");
        return sb.toString();
    }
}
