package com.binance.chuyennd.c3live.exit;

import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.filters.SymbolRules;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.ops.KillSwitchEngine;
import com.binance.chuyennd.tradecore.selector.C3TrailRate;
import org.junit.Before;
import org.junit.Test;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.Assert.*;

/** [V12 C6] TrailingStopManager: arm 0,07, ratchet = cong thuc so giay, stop san dat-roi-huy, nguong doi, -4130, -2021, time-stop/X14. */
public class TrailingStopManagerTest {

    static final long T0 = 1_792_900_000_000L;
    static final String S = "C00USDT";
    AtomicLong now;
    MockExchangeGateway gw;
    LiveBookC3 book;
    ExchangeInfo ei;
    List<String> closes;
    AtomicBoolean deferFlag;
    AtomicReference<KillSwitchEngine.Action> action;

    @Before
    public void setUp() {
        now = new AtomicLong(T0);
        gw = new MockExchangeGateway();
        ei = C3LiveFixtures.info(4);
        gw.exchangeInfo = ei;
        book = new LiveBookC3(null, 1.0);
        closes = new ArrayList<>();
        deferFlag = new AtomicBoolean(false);
        action = new AtomicReference<>(KillSwitchEngine.Action.NONE);
    }

    private void open(String sym, int legIdx, String px, String qty, Float pred) {
        String cid = "c3-" + sym + "-" + (1000 + legIdx) + "-" + legIdx;
        assertTrue(book.reserve(sym, cid, legIdx, 1000 + legIdx, "BIG_DOWN", Double.parseDouble(px), new BigDecimal(qty),
                Double.parseDouble(px) * Double.parseDouble(qty), now.get()));
        book.markSending(cid, now.get());
        gw.setPrice(sym, new BigDecimal(px));
        OrderInfo o = gw.newMarketOrder(sym, Side.BUY, new BigDecimal(qty), cid, false);
        assertTrue(book.confirm(cid, o.getExecutedQty(), o.getAvgPrice().doubleValue(), o.getOrderId(), now.get()));
        book.setMeta(sym, pred, 0, now.get());
    }

    private TrailingStopManager mgr() {
        return TrailingStopManager.builder().gateway(gw).book(book).rules(() -> new SymbolRules(ei, T0))
                .closer((s, r) -> {
                    closes.add(s + ":" + r);
                    return 1;
                })
                .defer((s, t, n) -> deferFlag.get()).armHook((s, t, n) -> { }).action(action::get).clock(now::get)
                .safeRetryMs(10_000L).build();
    }

    private static Map<String, Float> px(String s, float v) {
        Map<String, Float> m = new HashMap<>();
        m.put(s, v);
        return m;
    }

    private LiveBookC3.ClusterView c() {
        return book.cluster(S).get();
    }

    @Test
    public void armAtSevenPctAndRatchetIsPaperFormula() {
        open(S, 0, "1.0", "100", 0.5f);
        TrailingStopManager m = mgr();
        m.step(px(S, 1.05f));
        assertFalse("chua arm o +5 %", c().trailArmed());
        assertEquals(0, gw.calls("newStopMarket"));
        m.step(px(S, 1.08f));
        float entry = 1.0f;
        float rate = (1.08f - entry) / entry;
        float sl = entry * (1f + C3TrailRate.trailRate(rate, 0.5f, S));
        assertTrue(c().trailArmed());
        assertEquals(Float.floatToIntBits(sl), Float.floatToIntBits(c().priceSL));
        assertEquals(1, gw.calls("newStopMarket"));
        List<OrderInfo> st = gw.openStops(S);
        assertEquals(1, st.size());
        assertTrue("closePosition=true", st.get(0).isClosePosition());
        BigDecimal want = new BigDecimal(Float.toString(sl)).setScale(4, RoundingMode.DOWN);
        assertEquals(0, want.compareTo(st.get(0).getStopPrice()));
        assertEquals(c().stopClientAlgoId, st.get(0).getClientOrderId());
        assertTrue(c().stopClientAlgoId.startsWith("c3s-"));
        // ratchet lien tuc (giong so giay) nhung san chi doi khi >= 1 tick va >= 0,1 %
        m.step(px(S, 1.0805f));
        float sl2 = entry * (1f + C3TrailRate.trailRate((1.0805f - entry) / entry, 0.5f, S));
        assertEquals(Float.floatToIntBits(Math.max(sl, sl2)), Float.floatToIntBits(c().priceSL));
        assertEquals("muc moi < cu*1.001 => KHONG doi tren san", 1, gw.calls("newStopMarket"));
        m.step(px(S, 1.20f));
        assertEquals(2, gw.calls("newStopMarket"));
        List<String> log = gw.callLog();
        int iNew = -1, iCancel = -1;
        for (int i = 0; i < log.size(); i++) {
            if (log.get(i).startsWith("newStopMarket")) iNew = i;
            if (log.get(i).startsWith("cancelStop")) iCancel = i;
        }
        assertTrue("dat stop MOI truoc roi moi huy stop CU", iNew >= 0 && iCancel > iNew);
        assertEquals("con dung 1 stop mo", 1, gw.openStops(S).size());
        assertTrue(c().orphanStops.isEmpty());
        // gia xuong: priceSL khong giam
        float slHigh = c().priceSL;
        m.step(px(S, 1.10f));
        assertEquals(Float.floatToIntBits(slHigh), Float.floatToIntBits(c().priceSL));
        assertEquals(2, gw.calls("newStopMarket"));
    }

    @Test
    public void tickRuleOnLowPricedSymbol() {
        // gia 0.05, tick 0.0001: 0,1 % = 0.00005 < 1 tick => can >= 1 tick
        open(S, 0, "0.05", "1000", 0.5f);
        TrailingStopManager m = mgr();
        m.step(px(S, 0.0540f));
        assertEquals(1, gw.calls("newStopMarket"));
        BigDecimal first = gw.openStops(S).get(0).getStopPrice();
        // tang nho: SL logic tang nhung chua du 1 tick sau round-down
        m.step(px(S, 0.05402f));
        BigDecimal cur = gw.openStops(S).get(0).getStopPrice();
        assertTrue(cur.subtract(first).compareTo(new BigDecimal("0.0001")) < 0 || gw.calls("newStopMarket") == 2);
        if (gw.calls("newStopMarket") == 2) assertTrue(cur.subtract(first).compareTo(new BigDecimal("0.0001")) >= 0);
    }

    @Test
    public void secondClosePositionRejectedFallsBackToQtyWithoutGap() {
        gw.rejectSecondClosePosition = true;
        open(S, 0, "1.0", "100", 0.5f);
        TrailingStopManager m = mgr();
        m.step(px(S, 1.08f));
        String first = c().stopClientAlgoId;
        m.step(px(S, 1.30f));
        assertEquals("1 lan closePosition bi -4130 + 1 lan qty", 3, gw.calls("newStopMarket"));
        List<OrderInfo> st = gw.openStops(S);
        assertEquals(1, st.size());
        assertFalse(st.get(0).isClosePosition());
        assertEquals(0, new BigDecimal("100").compareTo(st.get(0).getOrigQty()));
        assertTrue(st.get(0).isReduceOnly());
        assertTrue(c().stopQtyMode);
        assertNotEquals(first, c().stopClientAlgoId);
        List<String> log = gw.callLog();
        assertTrue(log.indexOf("cancelStop:" + S + ":" + first) > log.lastIndexOf("newStopMarket:" + S + ":" + c().stopClientAlgoId));
        // lan doi tiep: stop active la qty => closePosition moi hop le
        m.step(px(S, 1.60f));
        assertEquals(1, gw.openStops(S).size());
    }

    @Test
    public void wouldImmediatelyTriggerClosesMarket() {
        gw.rejectWouldTrigger = true;
        open(S, 0, "1.0", "100", 0.5f);
        gw.setPrice(S, new BigDecimal("1.00"));   // mark san da thap hon stop moi
        TrailingStopManager m = mgr();
        m.step(px(S, 1.10f));
        assertEquals(Collections.singletonList(S + ":" + TrailingStopManager.REASON_TRAIL_IMMEDIATE), closes);
        assertNull(c().pendingStopCid);
        assertTrue(gw.openStops(S).isEmpty());
    }

    @Test
    public void timeStop168hWithX14Defer() {
        open(S, 0, "1.0", "100", 0.5f);
        TrailingStopManager m = mgr();
        now.set(T0 + 168 * 3_600_000L);
        m.step(px(S, 1.01f));
        assertTrue("dung 168h: chua toi", closes.isEmpty());
        now.addAndGet(60_000L);
        deferFlag.set(true);
        m.step(px(S, 1.01f));
        assertTrue("X14 hoan => khong cat", closes.isEmpty());
        deferFlag.set(false);
        now.addAndGet(60_000L);
        m.step(px(S, 1.01f));
        assertEquals(Collections.singletonList(S + ":" + TrailingStopManager.REASON_TIME_STOP), closes);
    }

    @Test
    public void armedClusterNeverTimeStops() {
        open(S, 0, "1.0", "100", 0.5f);
        TrailingStopManager m = mgr();
        m.step(px(S, 1.10f));
        now.set(T0 + 400 * 3_600_000L);
        m.step(px(S, 1.09f));
        assertTrue(closes.isEmpty());
    }

    @Test
    public void dcaResetsArmAndCancelsStop() {
        open(S, 0, "1.0", "100", 0.5f);
        TrailingStopManager m = mgr();
        m.step(px(S, 1.10f));
        String stop = c().stopClientAlgoId;
        assertNotNull(stop);
        open(S, 1, "1.05", "100", null);   // DCA khop => reset arm nhu so giay
        assertFalse(c().trailArmed());
        assertEquals(0f, c().peakRate, 0f);
        m.step(px(S, 1.06f));
        assertNull(c().stopClientAlgoId);
        assertTrue(gw.openStops(S).isEmpty());
        assertTrue(gw.callLog().contains("cancelStop:" + S + ":" + stop));
    }

    @Test
    public void unknownStopPlacementResolvedByQueryNoDuplicate() {
        open(S, 0, "1.0", "100", 0.5f);
        MockExchangeGateway g2 = new MockExchangeGateway() {
            boolean once = true;

            @Override
            public synchronized OrderInfo newStopMarket(String symbol, Side side, BigDecimal qty, BigDecimal stopPrice,
                                                        String cid, boolean ro) {
                OrderInfo o = super.newStopMarket(symbol, side, qty, stopPrice, cid, ro);
                if (once) {
                    once = false;
                    throw new GatewayException(ErrorKind.TIMEOUT_UNKNOWN_STATE, 0, 0, "read timeout", false, 0L, null);
                }
                return o;
            }
        };
        g2.exchangeInfo = ei;
        g2.setPosition(S, new BigDecimal("100"), BigDecimal.ONE);
        TrailingStopManager m = TrailingStopManager.builder().gateway(g2).book(book).rules(() -> new SymbolRules(ei, T0))
                .closer((s, r) -> 0).defer((s, t, n) -> false).armHook((s, t, n) -> { }).clock(now::get)
                .safeRetryMs(10_000L).build();
        m.step(px(S, 1.10f));
        assertNotNull("pending giu lai khi khong ro", c().pendingStopCid);
        assertNull(c().stopClientAlgoId);
        now.addAndGet(5_000L);
        m.step(px(S, 1.10f));
        assertEquals("trong cua so an toan: khong tra, khong gui lai", 1, g2.calls("newStopMarket"));
        now.addAndGet(6_000L);
        m.step(px(S, 1.10f));
        assertEquals(1, g2.calls("queryStop"));
        assertNull(c().pendingStopCid);
        assertNotNull(c().stopClientAlgoId);
        assertEquals("KHONG dat trung", 1, g2.calls("newStopMarket"));
        assertEquals(1, g2.openStops(S).size());
    }

    @Test
    public void noPriceStillRestoresMissingStopForArmedCluster() {
        open(S, 0, "1.0", "100", 0.5f);
        book.setTrail(S, 0.10f, 1.05f, now.get());   // vd sau restart: da arm, stop bi bo (reconcile)
        TrailingStopManager m = mgr();
        m.step(Collections.<String, Float>emptyMap());
        assertEquals(1, gw.calls("newStopMarket"));
        assertEquals(0, new BigDecimal("1.05").compareTo(gw.openStops(S).get(0).getStopPrice()));
    }

    @Test
    public void flattenActionDoesNothing() {
        open(S, 0, "1.0", "100", 0.5f);
        action.set(KillSwitchEngine.Action.FLATTEN);
        assertEquals(0, mgr().step(px(S, 1.2f)));
        assertEquals(0, gw.calls("newStopMarket"));
    }
}
