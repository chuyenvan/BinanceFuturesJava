package com.binance.chuyennd.ai_ml.wfo.framework;

import org.junit.Test;

import java.util.NavigableSet;
import java.util.TreeMap;
import java.util.TreeSet;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

/**
 * BUG-FIX 2026-07-13: funding.bin phai forward-fill luoi 15m -> moi phut (khoi phuc thiet ke
 * gen_funding_wf_predictions.py). Test hanh vi thuan cua {@link WfoDataset#forwardFillToGrid}.
 */
public class WfoDatasetForwardFillTest {

    private static final long MIN = 60_000L;
    private static final long STEP15 = 15 * MIN;

    private static long[] arr(long v) { return new long[]{v}; }

    /** Luoi 15m deu, grid 1 phut -> moi phut trong [t0, t_last+15m) duoc fill; carry-forward dung moc. */
    @Test
    public void fillDayGridEveryMinute() {
        TreeMap<Long, long[]> src = new TreeMap<>();
        src.put(0L, arr(100));
        src.put(STEP15, arr(200));
        src.put(2 * STEP15, arr(300));   // moc 15m tai 0,15,30

        NavigableSet<Long> grid = new TreeSet<>();
        for (long t = 0; t <= 2 * STEP15; t += MIN) grid.add(t);  // 31 phut 0..30

        TreeMap<Long, long[]> out = WfoDataset.forwardFillToGrid(src, grid, STEP15);

        assertEquals("moi phut 0..30 deu duoc fill", 31, out.size());
        // phut 1..14 carry moc 0
        assertEquals(100, out.get(1 * MIN)[0]);
        assertEquals(100, out.get(14 * MIN)[0]);
        // dung moc 15m
        assertEquals(200, out.get(STEP15)[0]);
        assertEquals(200, out.get(STEP15 + 7 * MIN)[0]);
        assertEquals(300, out.get(2 * STEP15)[0]);
    }

    /** Reference-share: nhieu phut lien tiep tro CUNG 1 mang (tiet kiem RAM, khong nhan ban). */
    @Test
    public void consecutiveMinutesShareArrayReference() {
        TreeMap<Long, long[]> src = new TreeMap<>();
        src.put(0L, arr(100));
        src.put(STEP15, arr(200));
        NavigableSet<Long> grid = new TreeSet<>();
        for (long t = 0; t < STEP15; t += MIN) grid.add(t);

        TreeMap<Long, long[]> out = WfoDataset.forwardFillToGrid(src, grid, STEP15);
        assertSame("phut 1 va 5 cung tro mang moc 0", out.get(1 * MIN), out.get(5 * MIN));
        assertSame(src.get(0L), out.get(3 * MIN));
    }

    /** ts truoc moc selector dau tien -> KHONG fill (beforeFirst). */
    @Test
    public void beforeFirstSelectorNotFilled() {
        TreeMap<Long, long[]> src = new TreeMap<>();
        src.put(10 * MIN, arr(100));   // moc dau o phut 10
        NavigableSet<Long> grid = new TreeSet<>();
        for (long t = 0; t <= 12 * MIN; t += MIN) grid.add(t);

        TreeMap<Long, long[]> out = WfoDataset.forwardFillToGrid(src, grid, STEP15);
        assertNull("phut 0..9 truoc moc dau -> null", out.get(0L));
        assertNull(out.get(9 * MIN));
        assertEquals(100, out.get(10 * MIN)[0]);
        assertEquals(100, out.get(12 * MIN)[0]);
    }

    /** Gap > staleMs -> KHONG carry stale qua han (de trong, khong bia tin hieu cu). */
    @Test
    public void staleBeyondCapNotFilled() {
        TreeMap<Long, long[]> src = new TreeMap<>();
        src.put(0L, arr(100));
        src.put(3 * STEP15, arr(400));   // gap 45m (thieu moc 15m,30m)
        NavigableSet<Long> grid = new TreeSet<>();
        for (long t = 0; t <= 3 * STEP15; t += MIN) grid.add(t);

        TreeMap<Long, long[]> out = WfoDataset.forwardFillToGrid(src, grid, STEP15);
        // phut 0..15 (gap<=15m tinh tu moc 0) fill; phut 16..44 qua han -> null; moc 45m co gia tri moi
        assertEquals(100, out.get(15 * MIN)[0]);
        assertNull("phut 16 cach moc 0 la 16m > 15m -> null", out.get(16 * MIN));
        assertNull(out.get(30 * MIN));
        assertEquals(400, out.get(3 * STEP15)[0]);
        assertFalse(out.containsKey(20 * MIN));
    }
}
