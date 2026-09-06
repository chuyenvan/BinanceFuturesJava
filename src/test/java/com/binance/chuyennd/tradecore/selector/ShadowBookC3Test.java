package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.tradecore.Configs;
import org.junit.Test;

import java.util.HashMap;
import java.util.Map;

import static org.junit.Assert.*;

/**
 * Unit test duong exit C3 trong {@link ShadowBookC3}: arm 0.07 (a), time-stop 168h (b),
 * ratchet LIEN TUC + cap 0.08/0.03 ban le 0.29 (c), ke toan equity giay (d).
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

    /** Khong mo trung coin dang giu. */
    @Test
    public void noDuplicateOpen() {
        ShadowBookC3 b = fresh();
        b.openPos("FFFUSDT", 0L, 100f, 1f, 1, 0.1f);
        b.openPos("FFFUSDT", 5L, 200f, 9f, 2, 0.2f);
        assertEquals(1, b.openCount());
        assertTrue(b.isHolding("FFFUSDT"));
    }
}
