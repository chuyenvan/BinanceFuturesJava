package com.binance.chuyennd.tradecore.selector;

import org.junit.Test;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import static org.junit.Assert.*;

/**
 * [TS-MKT-EXT v1.1] ALT_EW phut + co ngay — doi chieu luat sim (edge_attr_build.py logret/build_index,
 * tsx_flags.py) tren du lieu mau tinh tay.
 */
public class AltEwIndexTest {

    private static final long MIN = AltEwIndex.MIN;
    private static final long DAY = AltEwIndex.DAY;
    private static final long T0 = LocalDate.of(2026, 2, 10).toEpochDay() * DAY;

    private static double clip(double r) {
        return Math.max(-0.5, Math.min(0.5, r));
    }

    /** EW = TB deu cac log-return (cat ±0,5), bo BTC/ETH, bo qv=0, bo nen khong lien ke. */
    @Test
    public void minuteEwMatchesHandComputed() {
        AltEwIndex a = new AltEwIndex();
        int A = a.id("AAAUSDT"), B = a.id("BBBUSDT"), C = a.id("CCCUSDT"), BTC = a.id("BTCUSDT"), E = a.id("ETHUSDT");
        int[] ids = {A, B, C, BTC, E};
        assertTrue(Double.isNaN(a.feed(T0, ids, new double[]{100, 10, 1, 50000, 3000}, new double[]{1, 1, 1, 1, 1}, 5)));
        // phut 2: A +1 %, B x2 (ln2=0.693 -> cat 0.5), C qv=0 (bo), BTC/ETH bo
        double ew = a.feed(T0 + MIN, ids, new double[]{101, 20, 2, 60000, 1000}, new double[]{1, 1, 0, 1, 1}, 5);
        double exp = (clip(Math.log(101) - Math.log(100)) + clip(Math.log(20) - Math.log(10))) / 2.0;
        assertEquals(exp, ew, 1e-15);
        assertEquals(0.5, clip(Math.log(2)), 0d);
        // phut 3: C co qv>0 nhung nen truoc qv=0 -> van bo; A nhay coc (thieu phut 4) xem phut 5
        double ew3 = a.feed(T0 + 2 * MIN, new int[]{A, C}, new double[]{99, 3}, new double[]{1, 1}, 2);
        assertEquals(clip(Math.log(99) - Math.log(101)), ew3, 1e-15);
        // phut 5: A khong co nen phut 4 => khong co return; C co return (phut 3 qv>0 -> khong, phut 4 vang)
        assertTrue(Double.isNaN(a.feed(T0 + 4 * MIN, new int[]{A, C}, new double[]{98, 3}, new double[]{1, 1}, 2)));
        // gia 0 / am -> ln khong huu han -> bo
        double ew6 = a.feed(T0 + 5 * MIN, new int[]{A, C}, new double[]{0, 3.3}, new double[]{1, 1}, 2);
        assertEquals(clip(Math.log(3.3) - Math.log(3)), ew6, 1e-15);
        TreeMap<Long, AltEwIndex.DayStat> d = a.finish();
        assertEquals(1, d.size());
        assertEquals(3, d.get(T0 / DAY).n);
        assertEquals(ew + ew3 + ew6, d.get(T0 / DAY).sum, 1e-15);
    }

    /** S9: phut 00:00 UTC ngay 1 thang KHONG co return (sim logret theo thang); doi ngay giua thang thi co. */
    @Test
    public void monthBoundaryHasNoReturnButDayBoundaryHas() {
        long m = LocalDate.of(2026, 3, 1).toEpochDay() * DAY;
        AltEwIndex a = new AltEwIndex();
        int A = a.id("AAAUSDT");
        a.feed(m - MIN, new int[]{A}, new double[]{100}, new double[]{1}, 1);
        assertTrue(Double.isNaN(a.feed(m, new int[]{A}, new double[]{110}, new double[]{1}, 1)));
        assertFalse(Double.isNaN(a.feed(m + MIN, new int[]{A}, new double[]{111}, new double[]{1}, 1)));
        long d2 = LocalDate.of(2026, 3, 2).toEpochDay() * DAY;
        a.feed(d2 - MIN, new int[]{A}, new double[]{100}, new double[]{1}, 1);
        assertEquals(Math.log(105) - Math.log(100), a.feed(d2, new int[]{A}, new double[]{105}, new double[]{1}, 1), 1e-15);
        assertEquals(1439, AltEwIndex.expectedMinutes(m / DAY));
        assertEquals(1440, AltEwIndex.expectedMinutes(d2 / DAY));
    }

    /** Co(D) = eod − rolling(31).max() cua sim (tham chieu cai lai tung chu trong test), tren chuoi 120 ngay. */
    @Test
    public void flagMatchesSimRollingFormula() {
        int nd = 120;
        long d0 = T0 / DAY;
        Map<Long, AltEwIndex.DayStat> days = new HashMap<>();
        double[] s = new double[nd];
        java.util.Random rnd = new java.util.Random(42);
        for (int i = 0; i < nd; i++) {
            double drift = (i >= 40 && i < 60) ? -0.03 : (i >= 60 && i < 70 ? 0.02 : 0.0);
            s[i] = drift + 0.02 * rnd.nextGaussian();
            days.put(d0 + i, new AltEwIndex.DayStat(d0 + i, s[i], 1440));
        }
        double[] L = new double[nd];
        double c = 0;
        for (int i = 0; i < nd; i++) {
            c += s[i];
            L[i] = c;
        }
        int on = 0;
        for (int i = 30; i < nd; i++) {          // co ngay d0+i+1 dua tren eod(d0+i); can du 31 hang
            double mx = Double.NEGATIVE_INFINITY;
            for (int k = i - 30; k <= i; k++) mx = Math.max(mx, L[k]);
            double ddRef = Math.exp(L[i] - mx) - 1;
            AltEwIndex.FlagResult r = AltEwIndex.flagFor(d0 + i + 1, days);
            assertEquals(ddRef, r.dd, 1e-12);
            assertEquals(ddRef <= -0.30 ? AltEwIndex.State.ON : AltEwIndex.State.OFF, r.state);
            if (r.state == AltEwIndex.State.ON) on++;
        }
        assertTrue("chuoi mau phai co ngay co", on > 0);
        assertTrue("chuoi mau phai co ngay khong co", on < nd - 30);
    }

    /** Nguong dung −0,30 (≤), thieu ngay / ngay mong ⇒ NA. */
    @Test
    public void thresholdAndMissingData() {
        long d0 = T0 / DAY;
        Map<Long, AltEwIndex.DayStat> days = new HashMap<>();
        for (int i = 0; i < 30; i++) days.put(d0 + i, new AltEwIndex.DayStat(d0 + i, 0d, 1440));
        days.put(d0 + 29, new AltEwIndex.DayStat(d0 + 29, Math.log(0.70) - 1e-12, 1440));
        assertEquals(AltEwIndex.State.ON, AltEwIndex.flagFor(d0 + 30, days).state);
        days.put(d0 + 29, new AltEwIndex.DayStat(d0 + 29, Math.log(0.70) + 1e-9, 1440));
        assertEquals(AltEwIndex.State.OFF, AltEwIndex.flagFor(d0 + 30, days).state);
        days.put(d0 + 3, new AltEwIndex.DayStat(d0 + 3, 0d, AltEwIndex.MIN_MINUTES_PER_DAY - 1));
        assertEquals(AltEwIndex.State.NA, AltEwIndex.flagFor(d0 + 30, days).state);
        days.put(d0 + 3, new AltEwIndex.DayStat(d0 + 3, 0d, AltEwIndex.MIN_MINUTES_PER_DAY));
        assertNotEquals(AltEwIndex.State.NA, AltEwIndex.flagFor(d0 + 30, days).state);
        days.remove(d0);
        assertEquals(AltEwIndex.State.NA, AltEwIndex.flagFor(d0 + 30, days).state);
        // ngay d0 chi la moc P=0 (k = D−31) nen khong can cho co(d0+31)
        days.put(d0 + 30, new AltEwIndex.DayStat(d0 + 30, 0d, 1440));
        assertNotEquals(AltEwIndex.State.NA, AltEwIndex.flagFor(d0 + 31, days).state);
    }

    /** Adapter Map (record Aerospike float32) cho cung ket qua voi duong mang khi gia la float. */
    @Test
    public void mapAdapterEqualsArrayPath() {
        AltEwIndex a = new AltEwIndex();
        AltEwIndex b = new AltEwIndex();
        String[] syms = {"AAAUSDT", "BBBUSDT", "BTCUSDT"};
        List<Double> ea = new ArrayList<>(), eb = new ArrayList<>();
        for (int t = 0; t < 50; t++) {
            Map<String, com.binance.chuyennd.object.sw.KlineObjectSimple> m = new HashMap<>();
            int[] ids = new int[3];
            double[] cl = new double[3], qv = new double[3];
            for (int i = 0; i < 3; i++) {
                com.binance.chuyennd.object.sw.KlineObjectSimple k = new com.binance.chuyennd.object.sw.KlineObjectSimple();
                k.startTime = T0 + t * MIN;
                k.priceClose = (float) (10 + i + Math.sin(t * 0.3 + i));
                k.totalUsdt = (t % 7 == 0 && i == 1) ? 0f : 100f;
                m.put(syms[i], k);
                ids[i] = b.id(syms[i]);
                cl[i] = k.priceClose;
                qv[i] = k.totalUsdt;
            }
            ea.add(a.feed(T0 + t * MIN, m));
            eb.add(b.feed(T0 + t * MIN, ids, cl, qv, 3));
        }
        for (int i = 0; i < ea.size(); i++) {
            if (Double.isNaN(eb.get(i))) assertTrue(Double.isNaN(ea.get(i)));
            else assertEquals(eb.get(i), ea.get(i), 1e-15);
        }
    }
}
