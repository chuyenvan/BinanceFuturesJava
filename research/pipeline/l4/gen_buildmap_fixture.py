#!/usr/bin/env python3
"""Sinh FIXTURE VANG cho LiveBuildMapTest bang CHINH pandas (thuat toan y het build_map.py).

Co Y tao THE (score trung, p trung) de kiem tie-break `rank(method="first")` = thu tu dong.
"""
import numpy as np, pandas as pd, sys

rng = np.random.RandomState(7)
N = 40
score = np.round(rng.randn(N).astype(np.float32), 3)
p = np.round(rng.rand(N).astype(np.float32), 4)
score[5] = score[11] = score[23]          # 3 dong trung score
p[2] = p[17]                              # 2 dong trung p
p[30] = p[31] = p[32]                     # 3 dong trung p
df = pd.DataFrame({"ts": 1, "score": score.astype(np.float64), "p": p.astype(np.float64)})
# ---- Y HET build_map.py ----
df["r_score"] = df.groupby("ts").score.rank(method="first")
df["p_sorted"] = df.groupby("ts").p.rank(method="first", ascending=False)
key = df.set_index(["ts", "p_sorted"]).p
df["p_new"] = key.reindex(list(zip(df.ts, df.r_score))).values
assert np.allclose(np.sort(df.p_new.values), np.sort(df.p.values)), "multiset doi"
pred = (np.float32(1.0) - df.p_new.to_numpy(np.float32))


def arr(name, v, fmt):
    return "    private static final %s = {%s};\n" % (name, ", ".join(fmt % x for x in v))


with open(sys.argv[1], "w") as f:
    f.write("""package com.binance.chuyennd.tradecore.selector;

import org.junit.Test;

import java.util.*;

import static org.junit.Assert.*;

/**
 * CONG PORT {@code build_map.py} -> {@link LiveBuildMap}.
 *
 * <p>FIXTURE VANG duoi day do CHINH pandas sinh ra (script
 * {@code research/pipeline/l4/gen_buildmap_fixture.py} chay dung 4 dong thuat toan cua
 * {@code research/pipeline/build_map.py}), CO Y cai 3 dong trung {@code score} va 5 dong trung
 * {@code p} de kiem tie-break {@code rank(method="first")} = THU TU DONG.
 * Sua fixture bang tay = pha cong; muon doi thi chay lai script.
 */
public class LiveBuildMapTest {

""")
    f.write(arr("float[] SCORE", score, "%.9gf"))
    f.write(arr("float[] P", p, "%.9gf"))
    f.write(arr("float[] GOLD_PNEW", df.p_new.to_numpy(np.float32), "%.9gf"))
    f.write(arr("float[] GOLD_PRED", pred, "%.9gf"))
    f.write(arr("int[] GOLD_RANK", df.r_score.to_numpy(np.int32), "%d"))
    f.write("""
    private static LiveBuildMap.Assigned run() {
        List<String> order = new ArrayList<>();
        Map<String, Float> sc = new HashMap<>(), pw = new HashMap<>();
        for (int i = 0; i < SCORE.length; i++) {
            String k = "S" + i;
            order.add(k);
            sc.put(k, SCORE[i]);
            pw.put(k, P[i]);
        }
        return LiveBuildMap.assign(order, sc, pw);
    }

    /** Java == pandas TUNG GIA TRI (ke ca o cac dong co the). */
    @Test
    public void matchesPythonBuildMapValueByValue() {
        LiveBuildMap.Assigned a = run();
        assertNotNull(a);
        for (int i = 0; i < SCORE.length; i++) {
            String k = "S" + i;
            assertEquals("p_new dong " + i, GOLD_PNEW[i], a.pwinMapped.get(k), 0f);
            assertEquals("symbolPred dong " + i, GOLD_PRED[i], a.symbolPred.get(k), 0f);
            assertEquals("rank dong " + i, GOLD_RANK[i], (int) a.rank.get(k));
        }
    }

    /** symbolPred = 1 - p_new, DAO DAU y het WfoDataset.buildFundingFromWfFiles:248. */
    @Test
    public void symbolPredIsOneMinusPwin() {
        LiveBuildMap.Assigned a = run();
        for (String k : a.symbolPred.keySet()) {
            assertEquals(1.0f - a.pwinMapped.get(k), a.symbolPred.get(k), 0f);
        }
    }

    /** Multiset P(win) cua tick KHONG doi — dieu kien song cua quantile-map. */
    @Test
    public void multisetPreserved() {
        LiveBuildMap.Assigned a = run();
        float[] in = P.clone();
        float[] out = new float[a.size()];
        int i = 0;
        for (float v : a.pwinMapped.values()) out[i++] = v;
        Arrays.sort(in);
        Arrays.sort(out);
        assertArrayEquals(in, out, 0f);
    }

    /** Coin rank 1 (score THAP nhat) nhan P(win) LON nhat => symbolPred THAP nhat. */
    @Test
    public void bestRankGetsHighestPwin() {
        LiveBuildMap.Assigned a = run();
        String best = null;
        for (Map.Entry<String, Integer> e : a.rank.entrySet()) if (e.getValue() == 1) best = e.getKey();
        assertNotNull(best);
        float maxP = Float.NEGATIVE_INFINITY, minPred = Float.POSITIVE_INFINITY;
        for (float v : a.pwinMapped.values()) maxP = Math.max(maxP, v);
        for (float v : a.symbolPred.values()) minPred = Math.min(minPred, v);
        assertEquals(maxP, a.pwinMapped.get(best), 0f);
        assertEquals(minPred, a.symbolPred.get(best), 0f);
    }

    /** rank(method="first"): the pha theo THU TU DONG, khong co rank trung. */
    @Test
    public void rankFirstBreaksTiesByRowOrder() {
        int[] r = LiveBuildMap.rankFirst(new double[]{5, 1, 5, 1}, true);
        assertArrayEquals(new int[]{3, 1, 4, 2}, r);
        int[] d = LiveBuildMap.rankFirst(new double[]{5, 1, 5, 1}, false);
        assertArrayEquals(new int[]{1, 3, 2, 4}, d);
        Set<Integer> uniq = new HashSet<>();
        for (int x : LiveBuildMap.rankFirst(new double[]{1, 1, 1, 1}, true)) uniq.add(x);
        assertEquals(4, uniq.size());
    }

    /** Doi THU TU DONG => ket qua doi o dung cac dong co THE (bang chung tie-break song). */
    @Test
    public void rowOrderMattersOnlyForTies() {
        LiveBuildMap.Assigned a = run();
        List<String> rev = new ArrayList<>();
        Map<String, Float> sc = new HashMap<>(), pw = new HashMap<>();
        for (int i = SCORE.length - 1; i >= 0; i--) {
            String k = "S" + i;
            rev.add(k);
            sc.put(k, SCORE[i]);
            pw.put(k, P[i]);
        }
        LiveBuildMap.Assigned b = LiveBuildMap.assign(rev, sc, pw);
        assertNotNull(b);
        int diff = 0;
        for (String k : a.symbolPred.keySet()) {
            if (!a.symbolPred.get(k).equals(b.symbolPred.get(k))) diff++;
        }
        assertTrue("phai co dong doi vi fixture co the", diff > 0);
        assertTrue("chi cac dong co the duoc doi", diff <= 8);
    }

    /** Thieu khoa / NaN => null, caller giu duong cu (KHONG doan gia tri). */
    @Test
    public void returnsNullOnMissingOrNaN() {
        List<String> order = Arrays.asList("A", "B");
        Map<String, Float> sc = new HashMap<>(), pw = new HashMap<>();
        sc.put("A", 1f);
        pw.put("A", 0.5f);
        assertNull(LiveBuildMap.assign(order, sc, pw));
        sc.put("B", Float.NaN);
        pw.put("B", 0.4f);
        assertNull(LiveBuildMap.assign(order, sc, pw));
        assertNull(LiveBuildMap.assign(null, sc, pw));
        assertNull(LiveBuildMap.assign(new ArrayList<String>(), sc, pw));
    }

    /** Thu tu dong LIVE la tat dinh (ten symbol tang dan), khong theo HashMap. */
    @Test
    public void liveRowOrderIsDeterministic() {
        List<String> l = LiveBuildMap.liveRowOrder(new HashSet<>(Arrays.asList("ZZZ", "AAA", "MMM")));
        assertEquals(Arrays.asList("AAA", "MMM", "ZZZ"), l);
    }
}
""")
print("FIXTURE_OK")
