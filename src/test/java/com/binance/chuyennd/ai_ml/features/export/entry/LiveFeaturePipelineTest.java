package com.binance.chuyennd.ai_ml.features.export.entry;

import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.junit.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import static org.junit.Assert.*;

/** [V11] LiveFeaturePipeline: thu tu nuoi, phut lo tick, goi lai cung phut, settle partial, md null (khong Aerospike). */
public class LiveFeaturePipelineTest {
    static final long MIN = 60_000L;
    static final long E0 = 1_760_000_000_000L / MIN * MIN;

    static final class FakeSink implements LiveFeaturePipeline.Sink {
        final List<Long> fed = new ArrayList<>();
        final List<Long> extracted = new ArrayList<>();
        final List<MarketDataObject> mdUsed = new ArrayList<>();
        final List<Integer> sizes = new ArrayList<>();

        public void feed(long minute, Map<String, KlineObjectSimple> snap) {
            fed.add(minute);
        }

        public MarketFeatures extract(long minute, Map<String, KlineObjectSimple> snap, MarketDataObject md) {
            extracted.add(minute);
            mdUsed.add(md);
            sizes.add(snap.size());
            MarketFeatures f = new MarketFeatures();
            f.timestamp = minute;
            return f;
        }
    }

    static final class FakeMd implements LiveFeaturePipeline.MdGen {
        final List<Integer> calls = new ArrayList<>();
        boolean returnNull = false;

        public MarketDataObject update(Map<String, KlineObjectSimple> snap) {
            calls.add(snap.size());
            return returnNull ? null : new MarketDataObject(0.01f * snap.size(), 0f, 0f);
        }
    }

    static final class FakeSrc implements LiveFeaturePipeline.MinuteSource {
        final Map<Long, Integer> nsym = new HashMap<>();
        final Map<Long, Integer> afterWait = new HashMap<>();
        final List<Long> awaited = new ArrayList<>();

        public Map<String, KlineObjectSimple> snapshot(long minute) {
            Integer n = nsym.get(minute);
            Map<String, KlineObjectSimple> o = new HashMap<>();
            for (int i = 0; n != null && i < n; i++) {
                KlineObjectSimple k = new KlineObjectSimple();
                k.startTime = minute;
                o.put("S" + i + "USDT", k);
            }
            return o;
        }

        public LiveFeaturePipeline.SettleInfo await(long minute, int expected) {
            awaited.add(minute);
            Integer w = afterWait.get(minute);
            if (w != null) nsym.put(minute, w);
            int have = nsym.getOrDefault(minute, 0);
            return new LiveFeaturePipeline.SettleInfo(have, expected, have < expected ? 3000L : 0L, have < expected ? 12 : 0);
        }
    }

    static TreeMap<Long, Map<String, KlineObjectSimple>> seedData(FakeSrc src, long from, long to, long msOffset) {
        TreeMap<Long, Map<String, KlineObjectSimple>> t = new TreeMap<>();
        for (long m = from; m <= to; m += MIN) {
            Map<String, KlineObjectSimple> s = src.snapshot(m);
            for (KlineObjectSimple k : s.values()) k.startTime = m + msOffset;
            t.put(m + msOffset, s);
        }
        return t;
    }

    @Test
    public void seedAlignsAndFeedsInOrderThenCatchesUpMissedMinutes() {
        FakeSink sink = new FakeSink();
        FakeMd md = new FakeMd();
        FakeSrc src = new FakeSrc();
        for (long m = E0 - 10 * MIN; m <= E0 + 5 * MIN; m += MIN) src.nsym.put(m, 10);
        LiveFeaturePipeline p = new LiveFeaturePipeline(sink, md, true, 3);
        TreeMap<Long, Map<String, KlineObjectSimple>> seed = seedData(src, E0 - 10 * MIN, E0 - MIN, 5_874L);
        p.seed(seed);
        assertEquals(E0 - MIN, p.lastFed());
        for (Map<String, KlineObjectSimple> s : seed.values()) for (KlineObjectSimple k : s.values()) assertEquals(0L, k.startTime % MIN);
        assertEquals(10, sink.fed.size());
        // tick lo phut E0, E0+1 -> tick E0+2 phai nuoi E0, E0+1 roi trich E0+2
        LiveFeaturePipeline.Result r = p.onTick(src, E0 + 2 * MIN, new MarketDataObject(9f, 9f, 9f));
        assertEquals(Arrays.asList(E0, E0 + MIN), sink.fed.subList(10, 12));
        assertEquals(Arrays.asList(E0 + 2 * MIN), sink.extracted);
        assertEquals(13, md.calls.size());          // md nuoi MOI phut 1 lan (10 seed + 2 catchup + 1)
        assertNotNull(r.features);
        assertEquals(0.1f, r.featRate.rateDownAvg, 1e-6f);   // inline (10 symbol * 0.01)
        assertFalse(r.partial);
        // goi lai cung phut: khong nuoi/trich lai
        LiveFeaturePipeline.Result r2 = p.onTick(src, E0 + 2 * MIN, null);
        assertSame(r, r2);
        assertEquals(13, md.calls.size());
        assertEquals(1, sink.extracted.size());
        assertEquals(2, p.nCatchup);
    }

    @Test
    public void settlePartialIsFlaggedAndCounted() {
        FakeSink sink = new FakeSink();
        FakeMd md = new FakeMd();
        FakeSrc src = new FakeSrc();
        for (long m = E0 - 3 * MIN; m < E0; m += MIN) src.nsym.put(m, 738);
        src.nsym.put(E0, 300);          // phut quyet dinh thieu, cho cung khong du
        LiveFeaturePipeline p = new LiveFeaturePipeline(sink, md, true, 3);
        p.seed(seedData(src, E0 - 3 * MIN, E0 - MIN, 0L));
        LiveFeaturePipeline.Result r = p.onTick(src, E0, null);
        assertTrue(r.partial);
        assertEquals(1, p.nPartial);
        assertEquals(300, r.nSym);
        assertEquals(Arrays.asList(E0), src.awaited);
        // phut sau: cho xong thi du (afterWait) -> khong partial; expected = 300-3 (theo phut truoc)
        src.nsym.put(E0 + MIN, 200);
        src.afterWait.put(E0 + MIN, 738);
        LiveFeaturePipeline.Result r3 = p.onTick(src, E0 + MIN, null);
        assertFalse(r3.partial);
        assertEquals(738, r3.nSym);
    }

    @Test
    public void mdNullFallsBackToLegacyRateAndNoSnapshotSkipsTick() {
        FakeSink sink = new FakeSink();
        FakeMd md = new FakeMd();
        md.returnNull = true;
        FakeSrc src = new FakeSrc();
        src.nsym.put(E0 - MIN, 5);
        src.nsym.put(E0, 5);
        LiveFeaturePipeline p = new LiveFeaturePipeline(sink, md, true, 0);
        p.seed(seedData(src, E0 - MIN, E0 - MIN, 0L));
        MarketDataObject legacy = new MarketDataObject(7f, 7f, 7f);
        LiveFeaturePipeline.Result r = p.onTick(src, E0, legacy);
        assertSame(legacy, r.featRate);
        assertNull(r.inlineRate);
        assertEquals(1, p.nMdNull);
        LiveFeaturePipeline.Result r2 = p.onTick(src, E0 + MIN, legacy);   // khong co snapshot
        assertNull(r2.features);
        assertEquals(1, p.nNoSnap);
    }

    @Test
    public void featMdLegacyUsesLegacyRate() {
        FakeSink sink = new FakeSink();
        FakeMd md = new FakeMd();
        FakeSrc src = new FakeSrc();
        src.nsym.put(E0, 4);
        LiveFeaturePipeline p = new LiveFeaturePipeline(sink, md, false, 3);
        MarketDataObject legacy = new MarketDataObject(5f, 5f, 5f);
        LiveFeaturePipeline.Result r = p.onTick(src, E0, legacy);   // khong seed: expected=0 -> khong cho
        assertSame(legacy, r.featRate);
        assertNotNull(r.inlineRate);
        assertTrue(src.awaited.isEmpty());
    }
}
