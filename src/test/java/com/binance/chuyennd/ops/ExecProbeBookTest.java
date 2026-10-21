package com.binance.chuyennd.ops;

import org.junit.Test;

import static org.junit.Assert.*;

/** Ham thuan cua {@link ExecProbeBook}: walk-the-book, parse depth, bps, dinh dang. */
public class ExecProbeBookTest {

    private static final double EPS = 1e-9;

    @Test
    public void walkWithinFirstLevel() {
        ExecProbeBook.Walk w = ExecProbeBook.walk(new double[]{100, 101}, new double[]{5, 5}, 2);
        assertEquals(100d, w.vwap, EPS);
        assertEquals(1d, w.fillFrac, EPS);
        assertEquals(1, w.levels);
        assertEquals(1005d, w.sideNotional, EPS);
        assertFalse(w.shortBook());
    }

    @Test
    public void walkAcrossLevels() {
        // 5@100 + 3@101 = 803 / 8
        ExecProbeBook.Walk w = ExecProbeBook.walk(new double[]{100, 101, 102}, new double[]{5, 5, 5}, 8);
        assertEquals(803d / 8d, w.vwap, EPS);
        assertEquals(2, w.levels);
        assertEquals(1d, w.fillFrac, EPS);
    }

    @Test
    public void walkShortBookIsConservative() {
        // so chi co 4; can 10 => 6 con lai tinh o muc xau nhat (101)
        ExecProbeBook.Walk w = ExecProbeBook.walk(new double[]{100, 101}, new double[]{2, 2}, 10);
        assertEquals((200d + 202d + 6 * 101d) / 10d, w.vwap, EPS);
        assertEquals(0.4d, w.fillFrac, EPS);
        assertTrue(w.shortBook());
    }

    @Test
    public void walkEmptyOrZeroQty() {
        assertTrue(Double.isNaN(ExecProbeBook.walk(new double[0], new double[0], 1).vwap));
        assertTrue(Double.isNaN(ExecProbeBook.walk(new double[]{1}, new double[]{1}, 0).vwap));
        assertTrue(Double.isNaN(ExecProbeBook.walk(null, null, 1).vwap));
    }

    @Test
    public void costBpsSign() {
        assertEquals(10d, ExecProbeBook.costBps(true, 100.1, 100), 1e-6);    // mua dat hon => +10
        assertEquals(10d, ExecProbeBook.costBps(false, 99.9, 100), 1e-6);    // ban re hon => +10
        assertEquals(-10d, ExecProbeBook.costBps(true, 99.9, 100), 1e-6);
        assertTrue(Double.isNaN(ExecProbeBook.costBps(true, Double.NaN, 100)));
    }

    @Test
    public void parseCombinedDepth() {
        String m = "{\"stream\":\"ethusdt@depth5@100ms\",\"data\":{\"e\":\"depthUpdate\",\"E\":1700000000123,"
                + "\"T\":1700000000120,\"s\":\"ETHUSDT\",\"U\":1,\"u\":2,\"pu\":0,"
                + "\"b\":[[\"1999.5\",\"3\"],[\"2000.0\",\"1.5\"],[\"1999.0\",\"0\"]],"
                + "\"a\":[[\"2000.6\",\"2\"],[\"2000.5\",\"1\"]]}}";
        ExecProbeBook.Book b = ExecProbeBook.parseDepth(m, 1700000000200L);
        assertNotNull(b);
        assertEquals("ETHUSDT", b.symbol);
        assertEquals(2000.0d, b.bestBid(), EPS);          // sap giam dan
        assertEquals(2000.5d, b.bestAsk(), EPS);          // sap tang dan
        assertEquals(2, b.bidPx.length);                  // muc qty 0 bi bo
        assertEquals(1700000000123L, b.exchMs);
        assertEquals(2000.25d, b.mid(), EPS);
    }

    @Test
    public void parseRawAndSymbolFromStream() {
        String raw = "{\"stream\":\"btcusdt@depth5@100ms\",\"data\":{\"b\":[[\"10\",\"1\"]],\"a\":[[\"11\",\"1\"]]}}";
        ExecProbeBook.Book b = ExecProbeBook.parseDepth(raw, 5L);
        assertNotNull(b);
        assertEquals("BTCUSDT", b.symbol);
        assertEquals(-1L, b.exchMs);
        assertNull(ExecProbeBook.parseDepth("{\"e\":\"kline\"}", 0L));
        assertNull(ExecProbeBook.parseDepth("not json", 0L));
        assertNull(ExecProbeBook.parseDepth("{\"result\":null,\"id\":1}", 0L));
    }

    @Test
    public void formatting() {
        assertEquals("", ExecProbeBook.num(Double.NaN, 2));
        assertEquals("1.50", ExecProbeBook.num(1.5, 2));
        assertEquals("0.00012345", ExecProbeBook.px(0.00012345));
        assertEquals("100", ExecProbeBook.px(100.0));
        assertEquals("", ExecProbeBook.px(0d));
        assertEquals("a_b", ExecProbeBook.txt("a,b"));
        assertEquals("", ExecProbeBook.txt(null));
    }
}
