package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.api.TradeFill;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.exec.C3LiveCids;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.function.Consumer;

import static org.junit.Assert.*;

/**
 * [V12 R4f] MAJOR-L1: khoi phuc khop qua REST (recoverC3Exit) va stream toi MUON/SOM — CA HAI thu tu cho CUNG ket qua equity
 * (khong ghi trung realized/phi). MINOR-1: phi userTrades (USDT tru; BNB quy theo gia; khong gia => than trong + canh bao);
 * userTrades loi mot phan => KHAN, khong ghi ket qua mot phan.
 */
public class C3MainAccountR4fTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final String S = C3LiveFixtures.sym(0);

    private static MainAccountRig armed(File root) {
        MainAccountRig r = new MainAccountRig(root);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(S, 1.0f, false).outcome);
        r.tick(S, "1.10");
        r.tick(S, "1.12");
        assertTrue(r.book.cluster(S).get().trailArmed());
        return r;
    }

    private static String[] ledger(File root) throws Exception {
        String[] last = null;
        for (String x : Files.readAllLines(new File(root, "run/" + LiveBookC3.LEDGER_NAME).toPath())) {
            if (x.startsWith(S + ",")) last = x.split(",", -1);
        }
        assertNotNull(last);
        return last;
    }

    /** stop mo coi kich; su kien stream GIU LAI (bo dem); anh chup cum CU nhu Reconciler lay truoc khi doc san. */
    private static Object[] race(MainAccountRig r) {
        r.book.retireActiveStop(S, r.now.get());
        LiveBookC3.ClusterView snap = r.book.cluster(S).get();
        Consumer<String> sink = r.mock.wsSink;
        List<String> buf = new ArrayList<>();
        r.mock.wsSink = buf::add;
        r.sync();
        r.mock.triggerStops(S, new BigDecimal("1.08"));
        r.mock.wsSink = sink;
        assertEquals(0, r.mock.position(S).signum());
        assertFalse(buf.isEmpty());
        return new Object[]{snap, sink, buf};
    }

    @SuppressWarnings("unchecked")
    private String[] run(boolean streamFirst, File root) throws Exception {
        MainAccountRig r = armed(root);
        r.mock.feeRate = new BigDecimal("0.0005");   // phi khop thoat > 0 (stream "n" = userTrades commission)
        Object[] x = race(r);
        LiveBookC3.ClusterView snap = (LiveBookC3.ClusterView) x[0];
        Consumer<String> sink = (Consumer<String>) x[1];
        List<String> buf = (List<String>) x[2];
        if (streamFirst) {
            for (String e : buf) sink.accept(e);                // stream dong cum + ghi khop
            assertFalse(r.book.isHolding(S));
            assertEquals("TRAILING_STOP", r.merged.recoverC3Exit(snap));   // REST toi SAU: cum da dong => KHONG ghi
        } else {
            assertEquals("TRAILING_STOP", r.merged.recoverC3Exit(snap));   // REST truoc: ghi khop (tradeId)
            assertTrue(r.book.isHolding(S));
            for (String e : buf) sink.accept(e);                // stream toi MUON: tradeId da ghi => bo, FILLED => dong
        }
        assertFalse(r.book.isHolding(S));
        r.now.addAndGet(60_000L);
        r.sync();
        r.rec.checkPositions();
        Double eq = r.eq.c3Equity();
        String[] l = ledger(root);
        return new String[]{l[5], l[6], l[7], l[8], l[9], String.valueOf(eq)};
    }

    @Test
    public void streamBeforeAndAfterRecovery_sameEquity_noDoubleCount() throws Exception {
        File a = tmp.newFolder("a");
        File b = tmp.newFolder("b");
        String[] ra = run(true, a);
        String[] rb = run(false, b);
        assertArrayEquals("2 thu tu => CUNG exit qty / exit avg / realized / phi / ly do / equity c3", ra, rb);
        BigDecimal qty = new BigDecimal(ra[0]);
        double exitAvg = Double.parseDouble(ra[1]);
        assertEquals("realized ghi DUNG 1 lan", (exitAvg - 1.0) * qty.doubleValue(), Double.parseDouble(ra[2]), 1e-9);
        assertTrue("phi khop ghi 1 lan (> 0)", Double.parseDouble(ra[3]) > 0d);
        assertEquals("TRAILING_STOP", ra[4]);
        assertNotEquals("null", ra[5]);
    }

    @Test
    public void recoveredFees_usdtDeducted_bnbConverted_unknownConservativeWithAlert() throws Exception {
        MainAccountRig r = armed(tmp.getRoot());
        BigDecimal q = r.book.cluster(S).get().confirmedQty;
        BigDecimal third = q.divide(new BigDecimal("3"), 8, java.math.RoundingMode.DOWN);
        BigDecimal rest = q.subtract(third).subtract(third);
        r.acct.setAssetUsdPrice(a -> "BNB".equals(a) ? 600d : Double.NaN);
        List<TradeFill> fills = new ArrayList<>();
        fills.add(new TradeFill(S, 1L, third, new BigDecimal("1.10"), r.now.get(), 501L, new BigDecimal("0.01"), "USDT", null));
        fills.add(new TradeFill(S, 1L, third, new BigDecimal("1.10"), r.now.get(), 502L, new BigDecimal("0.00002"), "BNB", null));
        fills.add(new TradeFill(S, 1L, rest, new BigDecimal("1.10"), r.now.get(), 503L, new BigDecimal("0.5"), "XYZ", null));
        fills.add(new TradeFill(S, 1L, rest, new BigDecimal("1.10"), r.now.get(), 503L, new BigDecimal("0.5"), "XYZ", null));   // trung
        assertEquals(3, r.acct.bookRecoveredExit(S, fills, false));
        assertEquals("ghi lai => 0", 0, r.acct.bookRecoveredExit(S, fills, false));
        r.acct.closedOnExchange(S, "TEST", r.now.get());
        String[] l = ledger(tmp.getRoot());
        double exp = 0.01 + 0.00002 * 600d + rest.doubleValue() * 1.10 * 0.0005;
        assertEquals("phi: USDT tru, BNB x gia BNBUSDT, XYZ than trong 0,05 % notional", exp, Double.parseDouble(l[8]), 1e-9);
        assertEquals(0, new BigDecimal(l[5]).compareTo(q));
        assertTrue(r.alerts.toString(), r.alerts.stream().anyMatch(m -> m.contains("KHONG co gia XYZUSDT")));
    }

    @Test
    public void partialUserTradesFailure_urgentAndNoPartialBooking() throws Exception {
        MainAccountRig r = armed(tmp.getRoot());
        BigDecimal c3 = r.scope.c3OpenQty(S);
        r.mock.wsSink = null;
        String cid = C3LiveCids.close(S, Math.floorDiv(r.now.get(), 60_000L), 1);
        r.book.markClosing(S, cid, "TEST_PARTIAL", r.now.get());
        r.sync();
        OrderInfo o = r.mock.newMarketOrder(S, Side.SELL, c3.divide(new BigDecimal("2")), cid, true);
        r.mock.userTradesFail.add(o.getOrderId());
        r.book.retireActiveStop(S, r.now.get());
        r.mock.triggerStops(S, new BigDecimal("1.08"));
        assertEquals(0, r.mock.position(S).signum());
        for (int i = 0; i < 6; i++) {
            r.now.addAndGet(35_000L);
            r.sync();
            r.rec.checkPositions();
        }
        assertFalse(r.book.isHolding(S));
        assertTrue(r.alerts.toString(), r.alerts.stream().anyMatch(m -> m.contains("KHAN") && m.contains("doc userTrades LOI mot phan")));
        assertEquals("KHONG ghi ket qua mot phan", 0, new BigDecimal(ledger(tmp.getRoot())[5]).signum());
    }
}
