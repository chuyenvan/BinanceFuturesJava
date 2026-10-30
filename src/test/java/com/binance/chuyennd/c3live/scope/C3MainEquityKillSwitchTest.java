package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.IncomeRecord;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.exec.C3LiveCids;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.ops.KillSwitchEngine;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.math.BigDecimal;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.Assert.*;

/**
 * [V12 R4] (d) kill-switch C6/A40 do tren EQUITY c3 (LEGACY lo lon KHONG kich; c3 lo kich); (e) size tu equity c3 (khong tu
 * tmb); funding c3 theo symbol + khoang giu.
 */
public class C3MainEquityKillSwitchTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final String S = C3LiveFixtures.sym(0);

    static void periodicHealthy(KillSwitchEngine e, long t) {
        e.onTickStart(t);
        Map<String, List<KlineObjectSimple>> w = new HashMap<>();
        KlineObjectSimple k = new KlineObjectSimple();
        k.startTime = t - 60_000L;
        k.priceOpen = 1f;
        k.priceClose = 1f;
        k.maxPrice = 1f;
        k.minPrice = 1f;
        w.put("BTCUSDT", Collections.singletonList(k));
        e.onMarketData(t, w);
        e.periodic(t);
    }

    /** Cum c3 qty@px truc tiep vao so + san (khong qua sizing 4,5 %). */
    static void c3Position(MainAccountRig r, String sym, String qty, String px) {
        long now = r.now.get();
        String cid = C3LiveCids.entry(sym, C3LiveCids.barMin(now), 0);
        BigDecimal q = new BigDecimal(qty);
        double p = Double.parseDouble(px);
        assertTrue(r.book.reserve(sym, cid, 0, C3LiveCids.barMin(now), "BIG_DOWN", p, q, q.doubleValue() * p, now));
        assertTrue(r.book.confirm(cid, q, p, 1L, now));
        BigDecimal cur = r.mock.position(sym);
        r.mock.setPosition(sym, cur.add(q), new BigDecimal(px));
        r.mock.setPrice(sym, new BigDecimal(px));
    }

    @Test
    public void d_bigLegacyLossDoesNotTriggerC6A40ButC3LossDoes() throws Exception {
        MainAccountRig r = new MainAccountRig(tmp.getRoot(), new MockExchangeGateway(), 2_000d);
        r.setAccount("1000000", "600000");
        c3Position(r, S, "1800", "1.0");
        long t = r.now.addAndGet(60_000L);
        periodicHealthy(r.ks, t);
        r.tick(S, "1.0");
        assertEquals(2_000d, r.eq.c3Equity(), 1e-6);
        // LEGACY lo 60 % tmb tai khoan chinh (gia 44 symbol LEGACY sap) — equity c3 KHONG doi
        for (int i = 0; i < MainAccountRig.LEGACY_N; i++) r.mock.setPrice(MainAccountRig.legacySym(i), new BigDecimal("0.05"));
        r.setAccount("400000", "10000");
        for (int k = 0; k < 4; k++) {
            t = r.now.addAndGet(60_000L);
            r.tick(MainAccountRig.legacySym(0), "0.05");
            periodicHealthy(r.ks, t);
        }
        assertEquals(2_000d, r.eq.c3Equity(), 1e-6);
        assertTrue("LEGACY lo KHONG kich C6/A40: " + r.ks.latchCodes(), r.ks.latchCodes().isEmpty());
        assertEquals(KillSwitchEngine.Action.NONE, r.ks.requiredAction());
        // c3 lo: 1800 x (1.0 -> 0.55) = -810 => equity c3 1190 => DD -40,5 % => FLATTEN
        t = r.now.addAndGet(60_000L);
        r.mock.setPrice(S, new BigDecimal("0.55"));
        r.tick(S, "0.55");
        periodicHealthy(r.ks, t);
        assertEquals(2_000d - 810d, r.eq.c3Equity(), 1e-6);
        assertEquals(KillSwitchEngine.Action.FLATTEN, r.ks.requiredAction());
        assertTrue(r.ks.latchCodes().toString(), r.ks.latchCodes().contains("A40") || r.ks.latchCodes().contains("C6"));
    }

    @Test
    public void e_sizingFromC3EquityNotTmb() throws Exception {
        MainAccountRig r = new MainAccountRig(tmp.getRoot(), new MockExchangeGateway(), 10_000d);
        r.setAccount("1000000", "900000");   // tai khoan chinh lon (LEGACY) => KHONG duoc phinh size
        C3LiveEntry.Result a = r.buy(C3LiveFixtures.sym(2), 1.0f, false);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, a.outcome);
        assertEquals(10_000d, a.capital, 1e-6);
        assertTrue("notional <= 4,5 % x 10 000: " + a, a.qty.doubleValue() <= 450d + 1e-9);
        // c3 lo da chot 2 000 (cum dang mo) => von c3 = 8 000 du tmb khong doi
        r.book.addFillCosts(C3LiveFixtures.sym(2), 0d, -2_000d, r.now.get());
        C3LiveEntry.Result b = r.buy(C3LiveFixtures.sym(3), 1.0f, false);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, b.outcome);
        assertEquals(8_000d, b.capital, 1e-6);
        // availableBalance tai khoan chinh thap (LEGACY dung ky quy) => von c3 <= available + margin c3
        r.setAccount("1000000", "1");
        C3LiveEntry.Result c = r.buy(C3LiveFixtures.sym(4), 1.0f, false);
        double margin = c.marginBefore;
        assertTrue("a=" + a + " b=" + b + " c=" + c, margin > 1d);
        assertEquals(1d + margin, c.capital, 1e-6);
        // tmb tang manh (LEGACY lai) => von c3 KHONG tang
        r.setAccount("5000000", "4000000");
        C3LiveEntry.Result d = r.buy(C3LiveFixtures.sym(5), 1.0f, false);
        assertEquals(8_000d, d.capital, 1e-6);
        assertTrue(r.alerts.toString(), r.alerts.toString().contains("availableBalance"));
    }

    @Test
    public void fundingCountsOnlyC3SymbolsWhileHeld() throws Exception {
        MainAccountRig r = new MainAccountRig(tmp.getRoot(), new MockExchangeGateway(), 10_000d);
        long t0 = r.now.get();
        c3Position(r, S, "100", "1.0");
        long t1 = r.now.addAndGet(3_600_000L);
        r.mock.incomes.add(new IncomeRecord(S, "FUNDING_FEE", new BigDecimal("-1.5"), "USDT", t1 - 1000L, "11"));
        r.mock.incomes.add(new IncomeRecord(MainAccountRig.legacySym(0), "FUNDING_FEE", new BigDecimal("-50"), "USDT", t1 - 1000L, "12"));
        r.mock.incomes.add(new IncomeRecord(S, "FUNDING_FEE", new BigDecimal("-9"), "USDT", t0 - 3_600_000L, "10"));
        assertEquals(1, r.eq.pollFunding(t1));
        assertEquals(-1.5d, r.eq.fundingCum(), 1e-9);
        assertEquals(1, r.mock.calls("income"));
        assertEquals(0, r.eq.pollFunding(t1 + 1000L));   // throttle 10'
        assertEquals(0, r.eq.pollFunding(t1 + 600_000L)); // dong cu khong tinh lai
        assertEquals(-1.5d, r.eq.fundingCum(), 1e-9);
        assertEquals(10_000d - 1.5d, r.eq.c3Equity(), 1e-6);
        // restart: funding cong don persist
        r.boot();
        assertEquals(-1.5d, r.eq.fundingCum(), 1e-9);
        assertTrue(r.book.isHolding(S));
        LiveBookC3.ClusterView c = r.book.cluster(S).get();
        assertEquals(0, new BigDecimal("100").compareTo(c.confirmedQty));
    }
}
