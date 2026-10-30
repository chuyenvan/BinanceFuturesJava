package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.onnx.entry.GateRatioTestSupport;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.trading.GatePreFilter;
import org.junit.After;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.util.*;
import java.util.function.Predicate;

import static org.junit.Assert.*;

/**
 * [V12 R4j A1 MIN-4] Duong PRODUCTION cua loc truoc gate: CUNG vong {@link GatePreFilter#runSelector} ma
 * DetectEntrySignal2TradeNormal goi, {@link GatePreFilter#heldPredicate} nhanh C3_LIVE_BOOK doc LiveBookC3 THAT (rig tai khoan
 * chinh), gate THAT ({@link AIRejectFilter#entryGate} -> LiveGateRollingRatio nap r). Coin dang giu dem hang nhung KHONG nap r;
 * LEGACY dem hang + nap r (giu cho); A1 loai khong dem hang.
 */
public class GateSelectorProductionR4jTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    @After
    public void tearDown() {
        GatePreFilter.setC3OwnedSourceForTest(null);
        GateRatioTestSupport.reset();
    }

    @Test
    public void c3LiveBook_heldSkipsGate_legacyGated_topKHolds() throws Exception {
        MainAccountRig r = new MainAccountRig(tmp.getRoot());
        String held = C3LiveFixtures.sym(0);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(held, 1.0f, false).outcome);
        assertTrue(r.book.isHolding(held));
        GatePreFilter.setC3OwnedSourceForTest(() -> r.book.ownedSymbols());
        Predicate<String> heldPre = GatePreFilter.heldPredicate(GatePreFilter.HeldSource.C3_LIVE_BOOK, null);
        assertTrue("nhanh C3_LIVE_BOOK doc so c3 that", heldPre.test(held));

        String tf = "TFXUSDT", legacy = "LEGUSDT", a = "AAAUSDT", b = "BBBUSDT", c = "CCCUSDT";
        TreeMap<Float, String> pool = new TreeMap<>();
        pool.put(0.05f, tf);
        pool.put(0.10f, held);
        pool.put(0.11f, legacy);
        pool.put(0.12f, a);
        pool.put(0.13f, b);
        pool.put(0.14f, c);
        Map<String, Object> tickers = new HashMap<>();
        for (String s : pool.values()) tickers.put(s, new Object());

        GateRatioTestSupport.configure(0.5f, 90);
        int b0 = GateRatioTestSupport.size();
        AIRejectFilter gate = new AIRejectFilter();
        long ts = 1_793_400_000_000L;
        List<String> counted = new ArrayList<>();
        List<String> gated = new ArrayList<>();
        GatePreFilter.Result res = GatePreFilter.runSelector(pool.entrySet(), 4, s -> s.equals(tf), s -> s.equals(legacy), heldPre,
                tickers::get, (s, k) -> k, new GatePreFilter.SelectorSink<Object>() {
                    @Override
                    public void beforeCap(String symbol, int nextRank) {
                    }

                    @Override
                    public void counted(String symbol, Float key, Float symbolPred, int rank) {
                        counted.add(rank + ":" + symbol);
                    }

                    @Override
                    public void gate(String symbol, Object ticker, Float symbolPred) {
                        gated.add(symbol);
                        gate.entryGate(new AiPredictionData(ts, 0.02f, 0f), symbolPred, true, false);
                    }
                });
        assertEquals(Arrays.asList("1:" + held, "2:" + legacy, "3:" + a, "4:" + b), counted);
        assertEquals("coin dang giu KHONG qua gate", Arrays.asList(legacy, a, b), gated);
        assertEquals(1, res.held);
        assertEquals(1, res.legacy);
        assertEquals(1, res.a1);
        assertEquals("LEGACY giu cho: hang 5 (CCC) KHONG the vao", 4, res.rank);
        assertEquals("chi 3 r nap (khong co coin dang giu)", b0 + 3, GateRatioTestSupport.size());
    }
}
