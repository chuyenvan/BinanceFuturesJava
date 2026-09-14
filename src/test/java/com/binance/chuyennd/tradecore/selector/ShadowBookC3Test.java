package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.tradecore.Configs;
import org.junit.Test;

import java.util.HashMap;
import java.util.Map;

import static org.junit.Assert.*;

/**
 * Unit test duong exit C3 trong {@link ShadowBookC3}: arm 0.07 (a), time-stop 168h (b),
 * ratchet LIEN TUC + cap 0.08/0.03 ban le 0.29 (c), ke toan equity giay (d), gop cum DCA (e).
 *
 * <p>Khong phu thuoc env: goi thang cac ham thuan tinh toan / so vi the trong bo nho.
 */
public class ShadowBookC3Test {

    private static Map<String, Float> px(String s, float v) {
        Map<String, Float> m = new HashMap<>();
        m.put(s, v);
        return m;
    }

    /** So SACH: xoa ca state tren dia (getInstance nap lai state cua test truoc). */
    private ShadowBookC3 fresh() {
        ShadowBookC3.resetForTest();
        stateFile().delete();
        Configs.properties.putIfAbsent("CAPITAL_START", "35000");
        return ShadowBookC3.getInstance();
    }

    private static java.io.File stateFile() {
        return new java.io.File(System.getProperty("user.dir"), "open_positions.csv");
    }

    /** (a) chua vuot 0.07 thi KHONG arm; vuot roi thi arm va SL nam TREN entry. */
    @Test
    public void armOnlyAboveC3Threshold() {
        ShadowBookC3 b = fresh();
        b.openPos("AAAUSDT", 0L, 100f, 1f, 1, 0.10f);
        assertEquals(1, b.openCount());
        b.tick(px("AAAUSDT", 106f), 1000L);      // +6% < 7% -> chua arm, chua dong
        assertEquals(1, b.openCount());
        b.tick(px("AAAUSDT", 110f), 2000L);      // +10% -> arm, SL = entry*(1+0.05)
        assertEquals(1, b.openCount());
        b.tick(px("AAAUSDT", 104f), 3000L);      // rot duoi SL 105 -> dong
        assertEquals(0, b.openCount());
    }

    /** (c) ratchet LIEN TUC: dinh len thi SL len theo, khong cho toi dead-zone 26.1% cua live. */
    @Test
    public void ratchetIsContinuous() {
        ShadowBookC3 b = fresh();
        b.openPos("BBBUSDT", 0L, 100f, 1f, 2, 0.10f);
        b.tick(px("BBBUSDT", 108f), 1000L);      // arm o peak 8% -> SL = 104
        b.tick(px("BBBUSDT", 120f), 2000L);      // peak 20% -> gap min(0.10,0.08)=0.08 -> SL = 112
        assertEquals(1, b.openCount());
        b.tick(px("BBBUSDT", 111f), 3000L);      // duoi 112 -> dong (live voi dead-zone se KHONG doi SL)
        assertEquals(0, b.openCount());
    }

    /** (b) cum CHUA arm qua 168h -> dong bang time-stop; da arm thi KHONG. */
    @Test
    public void timeStop168hOnlyWhenNotArmed() {
        long h = 3600_000L;
        ShadowBookC3 b = fresh();
        b.openPos("CCCUSDT", 0L, 100f, 1f, 3, 0.10f);
        b.tick(px("CCCUSDT", 99f), 167 * h);     // chua toi 168h
        assertEquals(1, b.openCount());
        b.tick(px("CCCUSDT", 99f), 169 * h);     // qua 168h, chua arm -> dong
        assertEquals(0, b.openCount());

        ShadowBookC3 b2 = fresh();
        b2.openPos("DDDUSDT", 0L, 100f, 1f, 4, 0.10f);
        b2.tick(px("DDDUSDT", 110f), 1000L);     // arm
        b2.tick(px("DDDUSDT", 106f), 400 * h);   // da arm -> time-stop KHONG ap
        assertEquals(1, b2.openCount());
    }

    /** (d) equity giay = PAPER_EQUITY + realized + mark-to-market; margin = notional/leverage. */
    @Test
    public void paperEquityAccounting() {
        ShadowBookC3 b = fresh();
        float eq0 = b.equityNow(new HashMap<>());
        b.openPos("EEEUSDT", 0L, 100f, 2f, 1, 0.10f);
        assertEquals(100f * 2f / Configs.LEVERAGE_ORDER, b.marginRunning(), 1e-4f);
        assertEquals(eq0 + 20f, b.equityNow(px("EEEUSDT", 110f)), 1e-3f);   // MTM +10 x 2
        b.tick(px("EEEUSDT", 110f), 1000L);                                 // arm, SL 105
        b.tick(px("EEEUSDT", 104f), 2000L);                                 // dong tai 105
        assertEquals(0, b.openCount());
        assertEquals(eq0 + 10f, b.equityNow(new HashMap<>()), 1e-3f);       // realized (105-100)x2
    }

    /** State song qua restart: mo -> reset instance (gia lap restart 4h) -> van con vi the. */
    @Test
    public void stateSurvivesRestart() {
        ShadowBookC3 b = fresh();
        b.openPos("GGGUSDT", 12345L, 100f, 3f, 5, 0.2f);
        b.tick(px("GGGUSDT", 110f), 1000L);          // arm -> SL 105
        ShadowBookC3.resetForTest();                 // = ThreadAutoRestartProgram restart JVM
        ShadowBookC3 b2 = ShadowBookC3.getInstance();
        assertTrue("vi the phai song qua restart", b2.isHolding("GGGUSDT"));
        assertEquals(1, b2.openCount());
        b2.tick(px("GGGUSDT", 104f), 2000L);          // SL 105 phai duoc nap lai -> dong
        assertEquals(0, b2.openCount());
        stateFile().delete();
    }

    /**
     * (e) [BOOKFIX] DCA/BIG_DOWN cung coin: leg2 KHONG bi vut ma GOP vao cum — VWAP/legCount/qty/
     * firstEntryPrice/pnl khop mo hinh vi the cua sim ({@code mergeOrder}: entry=&Sigma;(e*q)/&Sigma;q).
     */
    @Test
    public void multiLegClusterMatchesSimModel() {
        ShadowBookC3 b = fresh();
        float eq0 = b.equityNow(new HashMap<>());
        b.openPos("HHHUSDT", 0L, 100f, 2f, 3, 0.20f);   // leg1 (mo cum): rank/pred THAT
        b.tick(px("HHHUSDT", 110f), 500L);              // leg1 don le: rate 0.10 > 0.07 -> arm
        assertNotNull("leg1 da arm", b.cluster("HHHUSDT").priceSL);
        b.openPos("HHHUSDT", 5L, 60f, 2f, -1, null);    // leg2 DCA: gia thap, khong rank/pred

        assertEquals("1 cum / coin", 1, b.openCount());
        ShadowBookC3.Cluster c = b.cluster("HHHUSDT");
        assertEquals("legCount = so leg", 2, c.legCount);
        assertEquals("tong qty", 4f, c.qty, 1e-6f);
        assertEquals("VWAP = (100*2+60*2)/4", 80f, c.avgEntry(), 1e-4f);
        assertEquals("firstEntryPrice bat bien leg dau", 100f, c.firstEntryPrice, 1e-6f);
        assertEquals("time-stop neo leg dau", 0L, c.tsFirstLeg);
        assertEquals("clusterSelRank: leg KHONG-null dau", 3, c.rank);
        assertEquals("clusterSymbolPred: leg KHONG-null dau", 0.20f, c.symbolPred, 1e-6f);
        assertNull("DCA re-arm nhu sim tao cum REQUEST moi", c.priceSL);
        assertEquals("DCA reset peak", 0f, c.peakRate, 1e-9f);

        // margin cum = notional/lev = (100*2+60*2)/lev
        assertEquals(320f / Configs.LEVERAGE_ORDER, b.marginRunning(), 1e-3f);
        // MTM tren VWAP: (90-80)*4 = 40
        assertEquals(eq0 + 40f, b.equityNow(px("HHHUSDT", 90f)), 1e-2f);

        // exit tren cum: arm o rate 0.25 (>0.07) roi dong duoi SL -> pnl tren TONG qty
        b.tick(px("HHHUSDT", 100f), 1000L);             // (100-80)/80 = 0.25 -> arm
        float expSL = 80f * (1f + ShadowBookC3.trailRate(0.25f, 0.20f));
        b.tick(px("HHHUSDT", expSL - 0.5f), 2000L);     // duoi SL -> dong ca cum
        assertEquals(0, b.openCount());
        double expPnl = (expSL - 80f) * 4f;             // pnl = (exit - VWAP) * tong qty
        assertEquals(eq0 + expPnl, b.equityNow(new HashMap<>()), 1e-2f);
    }

    /** (e2) [BOOKFIX] Cum DCA phai song qua restart voi VWAP/legCount/qty nguyen ven. */
    @Test
    public void clusterStateSurvivesRestart() {
        ShadowBookC3 b = fresh();
        b.openPos("IIIUSDT", 100L, 100f, 2f, 7, 0.2f);
        b.openPos("IIIUSDT", 200L, 60f, 2f, -1, null);   // DCA -> VWAP 80, qty 4, legCount 2
        ShadowBookC3.resetForTest();                     // gia lap restart JVM
        ShadowBookC3 b2 = ShadowBookC3.getInstance();
        ShadowBookC3.Cluster c = b2.cluster("IIIUSDT");
        assertNotNull("cum phai song qua restart", c);
        assertEquals(2, c.legCount);
        assertEquals(4f, c.qty, 1e-6f);
        assertEquals(80f, c.avgEntry(), 1e-4f);
        assertEquals(100f, c.firstEntryPrice, 1e-6f);
        assertEquals(100L, c.tsFirstLeg);
        assertEquals(320f / Configs.LEVERAGE_ORDER, b2.marginRunning(), 1e-3f);
        stateFile().delete();
    }
}
