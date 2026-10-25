package com.binance.chuyennd.ai_ml.features.export.entry;

import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.junit.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import static org.junit.Assert.*;

/**
 * [V12 SAFE C11] LIVE_SEED_EXCLUDE_DECISION_MIN: race seed/tick dau sau restart (10-21 07:54:10: seed nuoi toi phut
 * quyet dinh dau => minute <= lastFed => mat tick). Co 1: tick dau co feature, trang thai sau tick dau = co 0 (khi
 * khong race); co 0 (mac dinh) = hanh vi cu.
 */
public class LiveFeaturePipelineSeedExclTest {
    static final long MIN = LiveFeaturePipelineTest.MIN;
    static final long E0 = LiveFeaturePipelineTest.E0;

    private static LiveFeaturePipelineTest.FakeSrc src() {
        LiveFeaturePipelineTest.FakeSrc s = new LiveFeaturePipelineTest.FakeSrc();
        for (long m = E0 - 20 * MIN; m <= E0 + 5 * MIN; m += MIN) s.nsym.put(m, 10 + (int) ((m - E0) / MIN + 20));
        return s;
    }

    private static final class Run {
        final LiveFeaturePipelineTest.FakeSink sink = new LiveFeaturePipelineTest.FakeSink();
        final LiveFeaturePipelineTest.FakeMd md = new LiveFeaturePipelineTest.FakeMd();
        final LiveFeaturePipelineTest.FakeSrc src = src();
        final LiveFeaturePipeline p = new LiveFeaturePipeline(sink, md, true, 3);
        final List<LiveFeaturePipeline.Result> res = new ArrayList<>();

        Run(boolean excl, long seedTo) {
            p.setSeedExcludeDecisionMin(excl);
            p.seed(LiveFeaturePipelineTest.seedData(src, E0 - 10 * MIN, seedTo, 31_000L));
        }

        void ticks(long from, long to) {
            for (long m = from; m <= to; m += MIN) res.add(p.onTick(src, m, new MarketDataObject(9f, 9f, 9f)));
        }
    }

    /** Race (seed gom phut quyet dinh dau E0): co 0 mat tick E0; co 1 co feature E0; tick sau giong nhau. */
    @Test
    public void raceFirstTickLostWithFlagOffRecoveredWithFlagOn() {
        Run off = new Run(false, E0);
        Run on = new Run(true, E0);
        assertEquals(E0, off.p.lastFed());
        assertEquals(E0 - MIN, on.p.lastFed());           // phut cuoi giu lai
        off.ticks(E0, E0 + 3 * MIN);
        on.ticks(E0, E0 + 3 * MIN);
        assertNull(off.res.get(0));                        // hanh vi cu: mat tick dau
        assertNotNull(on.res.get(0));
        assertNotNull(on.res.get(0).features);
        assertEquals(E0, on.res.get(0).minute);
        assertEquals(Arrays.asList(E0 + MIN, E0 + 2 * MIN, E0 + 3 * MIN), off.sink.extracted);
        assertEquals(Arrays.asList(E0, E0 + MIN, E0 + 2 * MIN, E0 + 3 * MIN), on.sink.extracted);
        // so lan md.update/kich thuoc: phut E0 qua seed (co 0) == qua extract (co 1) => cung chuoi md
        assertEquals(off.md.calls, on.md.calls);
        // tick sau tick dau: ket qua giong nhau
        for (int i = 1; i < 4; i++) {
            assertEquals(off.res.get(i).minute, on.res.get(i).minute);
            assertEquals(off.res.get(i).nSym, on.res.get(i).nSym);
            assertEquals(off.res.get(i).featRate.rateDownAvg, on.res.get(i).featRate.rateDownAvg, 0f);
            assertEquals(off.res.get(i).partial, on.res.get(i).partial);
        }
        assertEquals(off.src.awaited.subList(0, 3), on.src.awaited.subList(1, 4));
        assertEquals(1L, on.p.nSeedHeldDropped);
        assertEquals(0L, on.p.nSeedHeldFed);
    }

    /** Khong race (seed toi E0-1, tick dau E0): co 1 == co 0 tung buoc (phut giu lai duoc nuoi o tick dau). */
    @Test
    public void noRaceFlagOnIdenticalToFlagOff() {
        Run off = new Run(false, E0 - MIN);
        Run on = new Run(true, E0 - MIN);
        off.ticks(E0, E0 + 3 * MIN);
        on.ticks(E0, E0 + 3 * MIN);
        assertEquals(off.sink.fed, on.sink.fed);
        assertEquals(off.sink.extracted, on.sink.extracted);
        assertEquals(off.sink.sizes, on.sink.sizes);
        assertEquals(off.md.calls, on.md.calls);
        assertEquals(off.src.awaited, on.src.awaited);
        for (int i = 0; i < 4; i++) {
            assertEquals(off.res.get(i).minute, on.res.get(i).minute);
            assertEquals(off.res.get(i).partial, on.res.get(i).partial);
            assertEquals(off.res.get(i).featRate.rateDownAvg, on.res.get(i).featRate.rateDownAvg, 0f);
        }
        assertEquals(1L, on.p.nSeedHeldFed);
    }

    /** Tick dau tre nhieu phut: phut giu lai duoc nuoi, phut lo duoc catch-up tu cua so nhu cu. */
    @Test
    public void lateFirstTickCatchesUpLikeBefore() {
        Run off = new Run(false, E0);
        Run on = new Run(true, E0);
        off.ticks(E0 + 3 * MIN, E0 + 4 * MIN);
        on.ticks(E0 + 3 * MIN, E0 + 4 * MIN);
        assertEquals(off.sink.fed, on.sink.fed);
        assertEquals(off.sink.extracted, on.sink.extracted);
        assertEquals(off.md.calls, on.md.calls);
    }

    /** Cua so tre hon seed (tick dau < phut giu lai): bo phut giu lai, phan con lai nhu cu (khong nuoi trung). */
    @Test
    public void windowBehindSeedDropsHeldMinute() {
        Run on = new Run(true, E0);
        on.ticks(E0 - MIN, E0 - MIN);
        assertNull(on.res.get(0));                        // E0-1 <= lastFed (E0-1): nhu cu, giu ket qua cu
        assertEquals(1L, on.p.nSeedHeldDropped);
        on.ticks(E0, E0);
        assertNotNull(on.res.get(1));
        assertEquals(Arrays.asList(E0), on.sink.extracted);
    }

    @Test
    public void defaultIsOff() {
        assertFalse(LiveFeaturePipeline.seedExcludeCfg());
        LiveFeaturePipelineTest.FakeSink sink = new LiveFeaturePipelineTest.FakeSink();
        LiveFeaturePipeline p = new LiveFeaturePipeline(sink, new LiveFeaturePipelineTest.FakeMd(), true, 3);
        TreeMap<Long, Map<String, KlineObjectSimple>> seed = LiveFeaturePipelineTest.seedData(src(), E0 - 3 * MIN, E0, 0L);
        p.seed(seed);
        assertEquals(E0, p.lastFed());
        assertEquals(4, sink.fed.size());
    }
}
