package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.recon.Reconciler;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.util.List;

import static org.junit.Assert.*;

/** [V12 R4c] A: san = 0 khong bang chung c3 => LOST_FOREIGN (journal + KHAN + chan 24 h + realized 0). B: vi the khong-c3 tren symbol vua chot => KHAN 1 lan. */
public class C3MainAccountR4cTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final String S = C3LiveFixtures.sym(0);

    private static MainAccountRig armed(MainAccountRig r) {
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(S, 1.0f, false).outcome);
        r.tick(S, "1.10");
        r.tick(S, "1.12");
        assertTrue(r.book.cluster(S).get().trailArmed());
        return r;
    }

    /** cum CHUA arm trailing: khong co stop c3s- tren san (dung pham vi muc A cua A1). */
    private static MainAccountRig unarmed(MainAccountRig r) {
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(S, 1.0f, false).outcome);
        r.tick(S, "1.00");
        assertFalse(r.book.cluster(S).get().trailArmed());
        assertNull(r.book.cluster(S).get().stopClientAlgoId);
        return r;
    }

    private static int c3Sells(MainAccountRig r) {
        int n = 0;
        for (String l : r.mock.callLog()) if (l.startsWith("newMarketOrder:") && l.contains(":c3x-")) n++;
        return n;
    }

    private static int count(List<String> l, String a, String b) {
        int n = 0;
        for (String x : l) if (x.contains(a) && x.contains(b)) n++;
        return n;
    }

    /** du nhip REST (moi 40 s 1 lan doc vi the) cho FlatConfirm (3 lan doc cach >= 30 s). */
    private static void settle(MainAccountRig r, int rounds) {
        for (int i = 0; i < rounds; i++) {
            for (int k = 0; k < 4; k++) r.tick(MainAccountRig.legacySym(2), "1");
            r.rec.checkPositions();
        }
    }

    private static String[] ledgerLast(File root, String sym) throws Exception {
        List<String> l = Files.readAllLines(new File(root, "run/" + LiveBookC3.LEDGER_NAME).toPath());
        String[] last = null;
        for (String x : l) if (x.startsWith(sym + ",")) last = x.split(",", -1);
        assertNotNull("ledger co dong " + sym, last);
        return last;
    }

    private void assertLost(MainAccountRig r, BigDecimal c3Qty, int sells0) throws Exception {
        assertFalse("cum da dong (LOST_FOREIGN)", r.book.isHolding(S));
        String[] led = ledgerLast(tmp.getRoot(), S);
        assertEquals(Reconciler.REASON_LOST_FOREIGN, led[9]);
        assertEquals("realized c3 = 0 (khong PnL ao)", 0d, Double.parseDouble(led[7]), 0d);
        assertEquals("khong co khop thoat c3", 0, new BigDecimal(led[5]).signum());
        assertEquals(1, count(r.journal, "LOST_FOREIGN", S));
        assertEquals("KHAN dung 1 lan", 1, count(r.alerts, "KHAN", S + " LOST_FOREIGN"));
        assertTrue(r.alerts.stream().anyMatch(a -> a.contains("LOST_FOREIGN") && a.contains("qty=" + c3Qty.toPlainString())));
        assertEquals("c3 khong gui lenh ban nao", 0, c3Sells(r) - sells0);
        assertEquals("LEGACY khong bi dung", 0, r.mock.position(S).signum());
        assertTrue(r.scope.entryBlocked(S, r.now.get()));
        String why = r.scope.entryBlockReason(S, r.now.get());
        assertTrue(why, why.startsWith("LOST_FOREIGN"));
        assertTrue("chi chan symbol do", r.rec.allowsEntry(C3LiveFixtures.sym(5)));
    }

    // ------------------------------------------------------------------ A
    @Test
    public void a_gapLegacySellsExactC3Qty_isLostForeignBlocked24h() throws Exception {
        MainAccountRig r = unarmed(new MainAccountRig(tmp.getRoot()));
        BigDecimal c3Qty = r.scope.c3OpenQty(S);
        int sells0 = c3Sells(r);
        r.mock.wsSink = null;
        r.legacyTrade(S, Side.SELL, c3Qty);
        settle(r, 6);
        assertLost(r, c3Qty, sells0);

        // trong 24 h: entry bi chan (LEGACY), ke ca sau restart (persist c3live_lost.txt)
        int c3Orders0 = r.mock.callLog().size();
        assertEquals(C3LiveEntry.Outcome.LEGACY, r.buy(S, 1.0f, false).outcome);
        r.now.addAndGet(6 * 3_600_000L);
        r.boot();
        assertTrue(new File(tmp.getRoot(), "run/c3live_lost.txt").exists());
        assertTrue(r.scope.entryBlockReason(S, r.now.get()).startsWith("LOST_FOREIGN"));
        assertEquals(C3LiveEntry.Outcome.LEGACY, r.buy(S, 1.0f, false).outcome);
        for (String l : r.mock.callLog().subList(c3Orders0, r.mock.callLog().size())) {
            assertFalse("khong lenh c3 nao tren " + S + ": " + l, l.contains(":" + S + ":c3"));
        }
        // het 24 h => go chan (ca khi nap lai file sau restart)
        r.now.addAndGet(18 * 3_600_000L + 1_000L);
        assertTrue(r.refresher.refreshNow());
        assertFalse(r.scope.entryBlocked(S, r.now.get()));
        r.boot();
        assertFalse(r.scope.isLostBlocked(S, r.now.get()));
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(S, 1.0f, false).outcome);
    }

    @Test
    public void a_streamOnLegacySellsExactC3Qty_isLostForeignNotExternal() throws Exception {
        MainAccountRig r = unarmed(new MainAccountRig(tmp.getRoot()));
        BigDecimal c3Qty = r.scope.c3OpenQty(S);
        int sells0 = c3Sells(r);
        r.legacyTrade(S, Side.SELL, c3Qty);   // stream: fill khong-c3 + ACCOUNT_UPDATE pa=0
        assertTrue("ACCOUNT_UPDATE pa=0 khong dong cum ngay (khong EXTERNAL)", r.book.isHolding(S));
        settle(r, 6);
        assertLost(r, c3Qty, sells0);
        assertFalse(r.alerts.toString(), r.alerts.stream().anyMatch(a -> a.contains("DA DONG tren san (EXTERNAL)")));
    }

    @Test
    public void a_accountUpdateBeforeOrderUpdate_doesNotCloseCluster() throws Exception {
        MainAccountRig r = unarmed(new MainAccountRig(tmp.getRoot()));
        r.mock.emitRaw("{\"e\":\"ACCOUNT_UPDATE\",\"E\":" + r.now.get() + ",\"T\":" + r.now.get()
                + ",\"a\":{\"m\":\"ORDER\",\"B\":[],\"P\":[{\"s\":\"" + S + "\",\"pa\":\"0\",\"ep\":\"0\",\"up\":\"0\",\"mt\":\"cross\",\"ps\":\"BOTH\"}]}}");
        assertTrue("pa=0 qua stream khong phai bang chung c3 => giu cum", r.book.isHolding(S));
        settle(r, 4);
        assertTrue("san con vi the c3 => van giu", r.book.isHolding(S));
        assertFalse(r.scope.entryBlockReason(S, r.now.get()) + "", r.scope.isLostBlocked(S, r.now.get()));
    }

    @Test
    public void a_c3StopCloseIsStillTrailingNotLost() throws Exception {
        MainAccountRig r = armed(new MainAccountRig(tmp.getRoot()));
        r.tick(S, "1.05");
        settle(r, 2);
        assertFalse(r.book.isHolding(S));
        assertEquals("TRAILING_STOP", ledgerLast(tmp.getRoot(), S)[9]);
        assertFalse(r.scope.isLostBlocked(S, r.now.get()));
        assertEquals(0, count(r.alerts, "LOST_FOREIGN", S));
    }

    @Test
    public void a_gapC3StopFiredIsTrailingNotLost() throws Exception {
        MainAccountRig r = armed(new MainAccountRig(tmp.getRoot()));
        r.mock.wsSink = null;
        r.tick(S, "1.05");   // stop c3s- khop khi mat stream => bang chung c3 (FINISHED)
        settle(r, 4);
        assertFalse(r.book.isHolding(S));
        assertNotEquals(Reconciler.REASON_LOST_FOREIGN, ledgerLast(tmp.getRoot(), S)[9]);
        assertFalse(r.scope.isLostBlocked(S, r.now.get()));
        assertEquals(0, count(r.alerts, "LOST_FOREIGN", S));
    }

    // ------------------------------------------------------------------ B
    @Test
    public void b_foreignPositionAfterC3Close_urgentExactlyOnceWithQty() throws Exception {
        MainAccountRig r = armed(new MainAccountRig(tmp.getRoot()));
        r.tick(S, "1.05");
        assertFalse(r.book.isHolding(S));
        r.legacyTrade(S, Side.BUY, new BigDecimal("50"));
        for (int i = 0; i < 30; i++) r.tick(MainAccountRig.legacySym(2), "1");   // 300 s (< 15 phut)
        assertEquals(r.alerts.toString(), 1, count(r.alerts, "KHAN: " + S + " co vi the KHONG-c3", "qty=50"));
        for (int i = 0; i < 90; i++) r.tick(MainAccountRig.legacySym(2), "1");   // them 900 s
        assertTrue(r.refresher.refreshNow());
        assertEquals("dung 1 lan", 1, count(r.alerts, "KHAN: " + S + " co vi the KHONG-c3", "qty="));
        assertEquals("khong lenh ghi c3 nao ngoai S", 0, r.c3WritesOutside(java.util.Collections.singleton(S)).size());
    }

    @Test
    public void b_gapForeignPositionAfterC3Close_urgentOnce() throws Exception {
        MainAccountRig r = armed(new MainAccountRig(tmp.getRoot()));
        r.tick(S, "1.05");
        assertFalse(r.book.isHolding(S));
        r.mock.wsSink = null;
        r.legacyTrade(S, Side.BUY, new BigDecimal("37"));
        for (int i = 0; i < 60; i++) r.tick(MainAccountRig.legacySym(2), "1");
        assertEquals(r.alerts.toString(), 1, count(r.alerts, "KHAN: " + S + " co vi the KHONG-c3", "qty=37"));
    }

    @Test
    public void b_foreignPositionLongAfterClose_noUrgent() throws Exception {
        MainAccountRig r = armed(new MainAccountRig(tmp.getRoot()));
        r.tick(S, "1.05");
        r.now.addAndGet(16 * MainAccountRig.MIN);
        r.legacyTrade(S, Side.BUY, new BigDecimal("50"));
        for (int i = 0; i < 20; i++) r.tick(MainAccountRig.legacySym(2), "1");
        assertEquals(0, count(r.alerts, "KHAN: " + S + " co vi the KHONG-c3", "qty="));
    }
}
