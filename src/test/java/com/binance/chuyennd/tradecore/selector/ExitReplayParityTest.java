package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.tradecore.Configs;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Random;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * [V12 C6 tieu chi GOLIVE §2] Replay TONG HOP (CI): so giay {@link ShadowBookC3} va duong THAT
 * ({@code LiveBookC3 + TrailingStopManager + MockExchangeGateway}) tren CUNG chuoi gia phut 20 ngay, 8 symbol (len->arm->
 * trailing, di ngang->time-stop, di ngang->X14 hoan->cat, sap->DCA->re-arm->trailing, 4 random walk) => moi quyet dinh
 * arm/doi SL (bit float)/time-stop/X14 hoan TRUNG 100 %; thoat trailing: cung co, phut that >= phut giay.
 * Replay du lieu DEV that (3 dot) chay ngoai CI bang {@code ExitReplayDevMain}.
 */
public class ExitReplayParityTest {

    private static final Logger LOG = LoggerFactory.getLogger(ExitReplayParityTest.class);

    static final long DAY = 86_400_000L;
    static final long MIN = 60_000L;
    static final long T0 = LocalDate.of(2025, 2, 3).toEpochDay() * DAY;
    private final Map<String, Boolean> existed = new LinkedHashMap<>();
    private static final String[] FILES = {"ledger.csv", "open_positions.csv", "legs.csv"};

    @Before
    public void setUp() {
        for (String f : FILES) existed.put(f, new File(System.getProperty("user.dir"), f).exists());
        new File(System.getProperty("user.dir"), "open_positions.csv").delete();
        Configs.properties.putIfAbsent("CAPITAL_START", "35000");
        TsMktExt.enabledForTest = true;
        TsMktExt.legacyCheck = s -> false;
        TsMktExt x = new TsMktExt(null, null, 0L, 0L);
        long d0 = T0 / DAY;
        for (int i = 0; i < 25; i++) x.setFlagForTest(d0 + i, (i == 7 || i == 8) ? AltEwIndex.State.ON : AltEwIndex.State.OFF);
        TsMktExt.setInstanceForTest(x);
    }

    @After
    public void tearDown() {
        TsMktExt.enabledForTest = null;
        TsMktExt.legacyCheck = LegacySymbols::isLegacySymbol;
        TsMktExt.setInstanceForTest(null);
        ShadowBookC3.resetForTest();
        for (String f : FILES) if (!existed.get(f)) new File(System.getProperty("user.dir"), f).delete();
    }

    static float path(int k, long m, Random[] rnd, float[] walk) {
        double d = m / 1440.0;   // ngay
        switch (k) {
            case 0:   // len 20 % trong 2 ngay -> xuong
                if (d < 2) return (float) (1.0 + 0.10 * d);
                if (d < 3) return (float) (1.20 - 0.30 * (d - 2));
                return 0.90f;
            case 1:   // di ngang +-2 %
            case 2:
                return (float) (1.0 + 0.02 * Math.sin(m / 90.0 + k));
            case 3:   // sap -> DCA -> hoi phuc -> trailing
                if (d < 1) return (float) (1.0 - 0.56 * d);
                if (d < 3) return (float) (0.44 + 0.255 * (d - 1));
                if (d < 4) return (float) (0.95 - 0.20 * (d - 3));
                return 0.75f;
            default: {   // random walk buoc 0,3 %
                Random r = rnd[k];
                float w = walk[k];
                w = (float) (w * (1.0 + (r.nextBoolean() ? 0.003 : -0.003) + 0.0004));
                walk[k] = w;
                return w;
            }
        }
    }

    @Test
    public void syntheticTwentyDaysPaperVsLive100pct() {
        ExchangeInfo ei = C3LiveFixtures.info(8);
        ExitParityEngine e = new ExitParityEngine(ei, T0, TsMktExt::deferTimeStop);
        Random[] rnd = new Random[8];
        float[] walk = new float[8];
        for (int k = 0; k < 8; k++) {
            rnd[k] = new Random(1000 + k);
            walk[k] = 1f;
        }
        long minutes = 20 * 1440;
        for (long m = 0; m < minutes; m++) {
            long ts = T0 + m * MIN;
            Map<String, Float> px = new LinkedHashMap<>();
            for (int k = 0; k < 8; k++) px.put(C3LiveFixtures.sym(k), path(k, m, rnd, walk));
            if (m == 0) {
                for (int k = 0; k < 8; k++) {
                    if (k == 1) continue;
                    e.leg(C3LiveFixtures.sym(k), ts, px.get(C3LiveFixtures.sym(k)), 100f, k, k % 2 == 0 ? 0.10f : 0.50f);
                }
            }
            if (m == 3 * 1440) e.leg(C3LiveFixtures.sym(1), ts, px.get(C3LiveFixtures.sym(1)), 100f, 1, 0.50f);
            ShadowBookC3.Cluster c3 = e.paperCluster(C3LiveFixtures.sym(3));
            if (c3 != null && c3.legCount == 1 && px.get(C3LiveFixtures.sym(3)) <= c3.firstEntryPrice * 0.5f) {
                e.leg(C3LiveFixtures.sym(3), ts, px.get(C3LiveFixtures.sym(3)), 100f, 3, 0.10f);
            }
            e.minute(ts, px);
        }
        ExitParityEngine.Compare c = e.compare();
        LOG.warn("[EXIT-PARITY synthetic] {}", c);
        for (String s : c.mismatches) LOG.warn("  mismatch {}", s);
        assertEquals(c.mismatches.toString(), 0, c.decisionMismatch);
        assertEquals(c.mismatches.toString(), 0, c.trailExitOnlyPaper + c.trailExitOnlyLive);
        assertTrue("phai co arm", c.arms >= 3);
        assertTrue("phai co time-stop (C01)", c.timeStops >= 1);
        assertTrue("phai co X14 hoan (C02 ngay 7-8)", c.defers >= 1);
        assertTrue("phai co doi SL", c.slMoves >= 10);
        assertTrue("phai co thoat trailing", c.trailExitBoth >= 2);
    }
}
