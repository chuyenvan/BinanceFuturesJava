package com.binance.chuyennd.tradecore.selector;

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

    private static final float[] SCORE = {1.69099998f, -0.465999991f, 0.0329999998f, 0.407999992f, -0.788999975f, 2.02900004f, -0.00100000005f, -1.755f, 1.01800001f, 0.600000024f, -0.625f, 2.02900004f, 0.504999995f, -0.261000007f, -0.243000001f, -1.45299995f, 0.555000007f, 0.123999998f, 0.273999989f, -1.52699995f, 1.65100002f, 0.153999999f, -0.386999995f, 2.02900004f, -0.0450000018f, -1.45099998f, -0.405000001f, -2.28800011f, 1.04900002f, -0.416000009f, -0.742999971f, 1.07200003f, -1.65100002f, 0.535000026f, -2.06399989f, -0.662f, -1.204f, 1.46200001f, 1.76600003f, -0.328999996f};
    private static final float[] P = {0.412999988f, 0.906400025f, 0.308899999f, 0.741100013f, 0.422399998f, 0.426499993f, 0.63440001f, 0.522899985f, 0.414900005f, 0.00139999995f, 0.0922999978f, 0.709399998f, 0.524299979f, 0.696200013f, 0.955500007f, 0.682900012f, 0.0531000011f, 0.308899999f, 0.592599988f, 0.235100001f, 0.964999974f, 0.944999993f, 0.848399997f, 0.472299993f, 0.841499984f, 0.131099999f, 0.308699995f, 0.463f, 0.74180001f, 0.485799998f, 0.324400008f, 0.324400008f, 0.324400008f, 0.300399989f, 0.1655f, 0.414900005f, 0.448100001f, 0.774900019f, 0.796400011f, 0.522400022f};
    private static final float[] GOLD_PNEW = {0.1655f, 0.682900012f, 0.448100001f, 0.414900005f, 0.74180001f, 0.0922999978f, 0.463f, 0.944999993f, 0.308899999f, 0.324400008f, 0.696200013f, 0.0531000011f, 0.412999988f, 0.522400022f, 0.485799998f, 0.841499984f, 0.324400008f, 0.426499993f, 0.414900005f, 0.848399997f, 0.235100001f, 0.422399998f, 0.524299979f, 0.00139999995f, 0.472299993f, 0.796400011f, 0.592599988f, 0.964999974f, 0.308899999f, 0.63440001f, 0.741100013f, 0.308699995f, 0.906400025f, 0.324400008f, 0.955500007f, 0.709399998f, 0.774900019f, 0.300399989f, 0.131099999f, 0.522899985f};
    private static final float[] GOLD_PRED = {0.834500015f, 0.317099988f, 0.551900029f, 0.585099995f, 0.25819999f, 0.907700002f, 0.537f, 0.0550000072f, 0.691100001f, 0.675599992f, 0.303799987f, 0.94690001f, 0.587000012f, 0.477599978f, 0.514199972f, 0.158500016f, 0.675599992f, 0.573500037f, 0.585099995f, 0.151600003f, 0.764899969f, 0.577600002f, 0.475700021f, 0.998600006f, 0.527700007f, 0.203599989f, 0.407400012f, 0.0350000262f, 0.691100001f, 0.36559999f, 0.258899987f, 0.691300035f, 0.0935999751f, 0.675599992f, 0.0444999933f, 0.290600002f, 0.225099981f, 0.699599981f, 0.868900001f, 0.477100015f};
    private static final int[] GOLD_RANK = {36, 13, 22, 26, 9, 38, 21, 3, 31, 30, 12, 39, 27, 18, 19, 6, 29, 23, 25, 5, 35, 24, 16, 40, 20, 7, 15, 1, 32, 14, 10, 33, 4, 28, 2, 11, 8, 34, 37, 17};

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
