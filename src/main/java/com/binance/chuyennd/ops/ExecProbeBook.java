package com.binance.chuyennd.ops;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Arrays;
import java.util.Locale;

/**
 * [EXEC-PROBE 2026-10-21] Phan THUAN cua do chi phi thuc thi (khong I/O, khong thread, khong log): anh chup so lenh,
 * parse message partial-depth websocket public Binance, walk-the-book, dinh dang dong CSV {@code [EXEC-PROBE]}.
 * Unit test o {@code ExecProbeBookTest}.
 */
public final class ExecProbeBook {

    private ExecProbeBook() {
    }

    /** Anh chup so lenh (bid giam dan, ask tang dan; chi muc qty &gt; 0). */
    public static final class Book {
        public final String symbol;
        public final double[] bidPx;
        public final double[] bidQty;
        public final double[] askPx;
        public final double[] askQty;
        /** Moc nhan message tai JVM (ms). */
        public final long recvMs;
        /** Truong {@code E} (event time cua san, ms); -1 neu thieu. */
        public final long exchMs;

        public Book(String symbol, double[] bidPx, double[] bidQty, double[] askPx, double[] askQty, long recvMs, long exchMs) {
            this.symbol = symbol;
            this.bidPx = bidPx;
            this.bidQty = bidQty;
            this.askPx = askPx;
            this.askQty = askQty;
            this.recvMs = recvMs;
            this.exchMs = exchMs;
        }

        public double bestBid() {
            return bidPx.length > 0 ? bidPx[0] : Double.NaN;
        }

        public double bestAsk() {
            return askPx.length > 0 ? askPx[0] : Double.NaN;
        }

        public double mid() {
            double b = bestBid(), a = bestAsk();
            return (b > 0 && a > 0) ? (a + b) / 2d : Double.NaN;
        }

        public int levels() {
            return Math.min(bidPx.length, askPx.length);
        }
    }

    /** Ket qua walk-the-book mot phia. */
    public static final class Walk {
        /** VWAP bao thu: phan vuot do sau nhin thay tinh o muc XAU nhat nhin thay. NaN neu so trong / qty &lt;= 0. */
        public final double vwap;
        /** Phan qty khop duoc trong cac muc nhin thay (0..1). */
        public final double fillFrac;
        /** So muc da an. */
        public final int levels;
        /** Tong notional cac muc nhin thay cua phia nay. */
        public final double sideNotional;

        Walk(double vwap, double fillFrac, int levels, double sideNotional) {
            this.vwap = vwap;
            this.fillFrac = fillFrac;
            this.levels = levels;
            this.sideNotional = sideNotional;
        }

        public boolean shortBook() {
            return fillFrac < 1d;
        }
    }

    /**
     * Walk mot phia so ({@code px} theo thu tu uu tien khop). {@code qty <= 0} hoac so trong => vwap NaN, fillFrac 0.
     */
    public static Walk walk(double[] px, double[] qty, double q) {
        double sideNtl = 0d;
        int n = (px == null || qty == null) ? 0 : Math.min(px.length, qty.length);
        for (int i = 0; i < n; i++) sideNtl += px[i] * qty[i];
        if (!(q > 0d) || n == 0) return new Walk(Double.NaN, 0d, 0, sideNtl);
        double rem = q, cost = 0d;
        int used = 0;
        for (int i = 0; i < n && rem > 0d; i++) {
            double take = Math.min(rem, qty[i]);
            cost += take * px[i];
            rem -= take;
            used++;
        }
        double filled = q - rem;
        if (rem > 0d) cost += rem * px[n - 1];   // bao thu: phan thieu tinh o muc xau nhat nhin thay
        return new Walk(cost / q, filled / q, used, sideNtl);
    }

    /**
     * Parse message partial depth ({@code <sym>@depth<N>@100ms}) dang combined stream
     * ({@code {"stream":"btcusdt@depth20@100ms","data":{"e":"depthUpdate","E":..,"s":"BTCUSDT","b":[[p,q]..],"a":[..]}}})
     * hoac raw. Tra null neu khong phai depth / hong. KHONG nem.
     */
    public static Book parseDepth(String msg, long recvMs) {
        try {
            JSONObject root = new JSONObject(msg);
            JSONObject d = root.has("data") ? root.getJSONObject("data") : root;
            JSONArray b = d.has("b") ? d.optJSONArray("b") : d.optJSONArray("bids");
            JSONArray a = d.has("a") ? d.optJSONArray("a") : d.optJSONArray("asks");
            if (b == null || a == null) return null;
            String sym = d.optString("s", "");
            if (sym.isEmpty()) {
                String st = root.optString("stream", "");
                int at = st.indexOf('@');
                if (at <= 0) return null;
                sym = st.substring(0, at);
            }
            sym = sym.toUpperCase(Locale.ROOT);
            double[][] bb = side(b, true);
            double[][] aa = side(a, false);
            return new Book(sym, bb[0], bb[1], aa[0], aa[1], recvMs, d.optLong("E", -1L));
        } catch (Exception e) {
            return null;
        }
    }

    private static double[][] side(JSONArray arr, boolean desc) {
        int n = arr.length();
        double[][] lv = new double[n][];
        int k = 0;
        for (int i = 0; i < n; i++) {
            JSONArray l = arr.getJSONArray(i);
            double p = Double.parseDouble(l.getString(0));
            double q = Double.parseDouble(l.getString(1));
            if (p > 0d && q > 0d) lv[k++] = new double[]{p, q};
        }
        double[][] used = Arrays.copyOf(lv, k);
        Arrays.sort(used, (x, y) -> desc ? Double.compare(y[0], x[0]) : Double.compare(x[0], y[0]));
        double[] px = new double[k], qt = new double[k];
        for (int i = 0; i < k; i++) {
            px[i] = used[i][0];
            qt[i] = used[i][1];
        }
        return new double[][]{px, qt};
    }

    /** Chi phi bps cho lenh {@code side}: BUY = (x/ref-1)*1e4; SELL = (1-x/ref)*1e4 (duong = bat loi). */
    public static double costBps(boolean buy, double x, double ref) {
        if (!(x > 0d) || !(ref > 0d)) return Double.NaN;
        return (buy ? (x / ref - 1d) : (1d - x / ref)) * 1e4;
    }

    /** Dinh dang so cho CSV: NaN/vo cuc => rong; khong dau phay (Locale.ROOT). */
    public static String num(double v, int dp) {
        if (Double.isNaN(v) || Double.isInfinite(v)) return "";
        return String.format(Locale.ROOT, "%." + dp + "f", v);
    }

    /** Gia: giu do chinh xac (toi da 10 so le, bo 0 thua). */
    public static String px(double v) {
        if (Double.isNaN(v) || Double.isInfinite(v) || v <= 0d) return "";
        String s = String.format(Locale.ROOT, "%.10f", v);
        int e = s.length();
        while (e > 0 && s.charAt(e - 1) == '0') e--;
        if (e > 0 && s.charAt(e - 1) == '.') e--;
        return s.substring(0, e);
    }

    /** Truong text an toan CSV: null => rong; dau phay/xuong dong => '_'. */
    public static String txt(String s) {
        if (s == null) return "";
        return s.replace(',', '_').replace('\n', '_').replace('\r', '_');
    }
}
