package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.exec.C3LiveCids;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.c3live.recon.Reconciler;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

import static org.junit.Assert.*;

/** [V12 R4b] Sua A1 R4: MAJOR-1 (san &lt; so c3), MINOR-1/2/3, quyet dinh §4 moi. */
public class C3MainAccountR4bTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final String S = C3LiveFixtures.sym(0);

    private static MainAccountRig armed(MainAccountRig r) {
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(S, 1.0f, false).outcome);
        r.tick(S, "1.10");
        r.tick(S, "1.12");
        assertTrue(r.book.cluster(S).get().trailArmed());
        assertNotNull(r.book.cluster(S).get().stopClientAlgoId);
        return r;
    }

    private static int c3Sells(MainAccountRig r) {
        int n = 0;
        for (String l : r.mock.callLog()) if (l.startsWith("newMarketOrder:") && l.contains(":c3x-")) n++;
        return n;
    }

    // ------------------------------------------------------------------ MAJOR-1
    @Test
    public void major1_deficitWithC3EvidenceIsNotMerged() throws Exception {
        MainAccountRig r = armed(new MainAccountRig(tmp.getRoot()));
        BigDecimal c3 = r.scope.c3OpenQty(S);
        // c3 tu dong 1 phan (lenh c3x- that tren san) khi mat stream => co bang chung c3 => KHONG MERGED
        r.mock.wsSink = null;
        BigDecimal part = c3.divide(new BigDecimal("2"));
        String cid = C3LiveCids.close(S, Math.floorDiv(r.now.get(), 60_000L), 1);
        r.book.markClosing(S, cid, "TEST_PARTIAL", r.now.get());
        r.mock.newMarketOrder(S, Side.SELL, part, cid, true);
        r.book.clearCloseCid(S, r.now.get());
        r.book.markClosing(S, cid, "TEST_PARTIAL", r.now.get());
        assertTrue(r.refresher.refreshNow());
        r.now.addAndGet(5_000L);
        r.merged.poll();
        assertFalse("thieu hut duoc giai thich boi c3x- => khong MERGED", r.scope.isMerged(S));
    }

    @Test
    public void major1_hourlyQtySkipsMergedAndStartupNeverLowersBook() throws Exception {
        MainAccountRig r = armed(new MainAccountRig(tmp.getRoot()));
        BigDecimal c3 = r.scope.c3OpenQty(S);
        r.mock.wsSink = null;
        r.legacyTrade(S, Side.SELL, c3.divide(new BigDecimal("4")));
        r.now.addAndGet(60_000L);
        r.boot();
        assertTrue("khoi dong: san < so c3 khong bang chung => MERGED ngay", r.scope.isMerged(S));
        assertEquals("so c3 KHONG bi ha", 0, c3.compareTo(r.scope.c3OpenQty(S)));
        r.now.addAndGet(3_600_000L);
        r.rec.hourly();
        assertFalse(r.rec.blocks().toString(), r.rec.blocks().containsKey(Reconciler.BLOCK_EQUITY));
        assertEquals("MERGED + san < c3: KHONG dong", 0, c3Sells(r));
        // stop qty = qty c3 (khong closePosition)
        OrderInfo st = r.mock.openStops(S).get(0);
        assertFalse(st.isClosePosition());
    }

    // ------------------------------------------------------------------ §4 moi
    @Test
    public void decision4_mergedLegacyAlsoLongStopLostClosesExactlyC3Qty() throws Exception {
        MainAccountRig r = armed(new MainAccountRig(tmp.getRoot()));
        BigDecimal c3 = r.scope.c3OpenQty(S);
        r.legacyTrade(S, Side.BUY, new BigDecimal("500"));
        assertTrue(r.scope.isMerged(S));
        String cid = r.book.cluster(S).get().stopClientAlgoId;
        r.mock.rejectAllStops = true;
        r.mock.exchangeEndStop(cid, "EXPIRED");
        r.protector.check();
        assertEquals(0, c3Sells(r));
        r.now.addAndGet(62_000L);
        r.sync();
        r.protector.check();
        assertEquals("dong DUNG qty c3", 1, c3Sells(r));
        assertEquals("LEGACY 500 nguyen ven", 0, new BigDecimal("500").compareTo(r.mock.position(S)));
        assertFalse(r.book.isHolding(S));
        assertTrue(r.alerts.toString(), r.alerts.toString().contains("trung tinh voi LEGACY"));
        assertTrue(c3.signum() > 0);
    }

    @Test
    public void decision4_mergedDeficitStopLostDoesNotClose() throws Exception {
        MainAccountRig r = armed(new MainAccountRig(tmp.getRoot()));
        BigDecimal c3 = r.scope.c3OpenQty(S);
        r.legacyTrade(S, Side.SELL, c3.divide(new BigDecimal("2")));
        assertTrue("lenh khong-c3 khop tren symbol c3 => MERGED", r.scope.isMerged(S));
        String cid = r.book.cluster(S).get().stopClientAlgoId;
        r.mock.rejectAllStops = true;
        r.mock.exchangeEndStop(cid, "EXPIRED");
        r.protector.check();
        r.now.addAndGet(62_000L);
        r.sync();
        r.protector.check();
        assertEquals("san < qty c3: KHONG dong", 0, c3Sells(r));
        assertTrue(r.alerts.toString(), r.alerts.toString().contains("KHONG dong"));
    }

    // ------------------------------------------------------------------ MINOR-1
    @Test
    public void minor1_c3StopFillWithoutC3CidConfirmedByQueryStop() throws Exception {
        MockExchangeGateway m = new MockExchangeGateway();
        m.triggeredFillCidPrefix = "exch-";
        m.algoUpdateAfterFill = true;   // ai den SAU khop => phai xac nhan bang queryStop
        MainAccountRig r = armed(new MainAccountRig(tmp.getRoot(), m, 10_000d));
        double sp = r.mock.openStops(S).get(0).getStopPrice().doubleValue();
        r.tick(S, String.format(Locale.ROOT, "%.4f", sp * 0.999));
        assertFalse("khop stop c3 (cid san) duoc nhan => cum dong", r.book.isHolding(S));
        assertFalse(r.scope.isMerged(S));
    }

    @Test
    public void minor1_legacyStopFillOnC3SymbolIsForeignAndMerged() throws Exception {
        MainAccountRig r = armed(new MainAccountRig(tmp.getRoot()));
        double sp = r.mock.openStops(S).get(0).getStopPrice().doubleValue();
        BigDecimal c3 = r.scope.c3OpenQty(S);
        r.mock.setPosition(S, c3.add(new BigDecimal("40")), new BigDecimal("1.0"));   // LEGACY long 40 (khong qua stream)
        r.mock.addRestingStop(S, "legacy_sl_S", new BigDecimal("40"), new BigDecimal(String.format(Locale.ROOT, "%.4f", sp * 1.05)));
        r.sync();
        r.mock.triggerStops(S, new BigDecimal(String.format(Locale.ROOT, "%.4f", sp * 1.03)));
        assertTrue("khop stop LEGACY (ot STOP_MARKET, khong ai c3) => khop la => MERGED", r.scope.isMerged(S));
        assertTrue("so c3 KHONG tinh khop LEGACY la thoat c3", r.book.isHolding(S));
        assertEquals(0, c3.compareTo(r.scope.c3OpenQty(S)));
    }

    // ------------------------------------------------------------------ MINOR-2
    @Test
    public void minor2_scopeRefusalIsNotCountedAsApiError() throws Exception {
        MainAccountRig r = new MainAccountRig(tmp.getRoot());
        List<String> api = new ArrayList<>();
        C3LiveOrderExecutor ex = new C3LiveOrderExecutor(r.sgw, r.book, (a, ok) -> api.add(a + ":" + ok), null, r.now::get,
                ms -> r.now.addAndGet(ms), 10_000L, 3, Runnable::run);
        String lg = MainAccountRig.legacySym(3);
        String cid = C3LiveCids.entry(lg, C3LiveCids.barMin(r.now.get()), 0);
        assertTrue(r.book.reserve(lg, cid, 0, C3LiveCids.barMin(r.now.get()), "BIG_DOWN", 1.0, BigDecimal.TEN, 10d, r.now.get()));
        ex.submit(cid);
        assertFalse(r.book.isHolding(lg));
        assertFalse("tu choi phia client khong phai loi API: " + api, api.contains("newMarketOrder:false"));
        assertEquals(0, r.mock.calls("newMarketOrder"));
    }

    // ------------------------------------------------------------------ MINOR-3
    @Test
    public void minor3_mergedRealizedUsesC3BookAvgNotBlendedRp() throws Exception {
        MainAccountRig r = armed(new MainAccountRig(tmp.getRoot()));
        BigDecimal c3 = r.scope.c3OpenQty(S);
        double avg = r.book.cluster(S).get().avgPrice;
        r.mock.setPrice(S, new BigDecimal("1.30"));
        r.legacyTrade(S, Side.BUY, new BigDecimal("500"));   // LEGACY vao gia 1.30 => gia vao san bi tron
        assertTrue(r.scope.isMerged(S));
        OrderInfo st = r.mock.openStops(S).get(0);
        assertFalse(st.isClosePosition());
        double sp = st.getStopPrice().doubleValue();
        r.tick(S, String.format(Locale.ROOT, "%.4f", sp));
        assertFalse(r.book.isHolding(S));
        List<String> l = Files.readAllLines(new File(tmp.getRoot(), "run/" + LiveBookC3.LEDGER_NAME).toPath());
        String[] t = l.get(l.size() - 1).split(",");
        double realized = Double.parseDouble(t[7]);
        assertEquals("realized c3 = (gia khop - gia vao so c3) x qty c3", (sp - avg) * c3.doubleValue(), realized, 1e-6);
        assertEquals("LEGACY 500 nguyen ven", 0, new BigDecimal("500").compareTo(r.mock.position(S)));
    }
}
