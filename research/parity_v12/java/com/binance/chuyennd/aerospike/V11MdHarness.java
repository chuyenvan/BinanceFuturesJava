package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.ai_ml.features.export.MarketDataInlineGenerator;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.lang.reflect.Field;
import java.util.*;
import java.util.zip.GZIPOutputStream;

/**
 * AUDIT-ONLY (V11 §6): MarketDataObject theo phut tu ticker 242 (CHI DOC) bang 2 cach:
 * JAVA = MarketDataInlineGenerator (calMarketData float32, loc died + isTickerAvailable, buffer lien tuc);
 * PY = mo phong md_inline.py (khong loc isTickerAvailable, float64). args: fromMinute toMinute out.csv.gz
 */
public class V11MdHarness {
    private static final Logger LOG = LoggerFactory.getLogger(V11MdHarness.class);
    static final long MIN = 60_000L;

    public static void main(String[] a) throws Exception {
        Field g = Live242WriteGuard.class.getDeclaredField("decided");
        g.setAccessible(true);
        g.set(null, Boolean.FALSE);
        OfflineGuard.install();
        TreeMap<Long, Map<String, KlineObjectSimple>> off = null;
        if (OfflineGuard.enabled()) {   // HARNESS_OFFLINE=1: kline tu cache file (HARNESS_CACHE_FILE), khong Aerospike
            try (java.io.ObjectInputStream in = new java.io.ObjectInputStream(new java.util.zip.GZIPInputStream(
                    new java.io.FileInputStream(System.getenv("HARNESS_CACHE_FILE"))))) {
                @SuppressWarnings("unchecked") TreeMap<Long, Map<String, KlineObjectSimple>> x =
                        (TreeMap<Long, Map<String, KlineObjectSimple>>) in.readObject();
                off = x;
            }
            LOG.info("offline cache minutes={}", off.size());
        }
        long from = Long.parseLong(a[0]), to = Long.parseLong(a[1]);
        MarketDataInlineGenerator gen = new MarketDataInlineGenerator();
        Map<String, Deque<double[]>> pyBuf = new HashMap<>();
        long n = 0, nMiss = 0;
        try (PrintWriter w = new PrintWriter(new OutputStreamWriter(new GZIPOutputStream(new FileOutputStream(a[2]))))) {
            w.println("ts,nsym,j_down,j_up,j_down15,p_down,p_up,p_down15");
            for (long t = from; t <= to; t += 240 * MIN) {
                int cnt = (int) Math.min(240, (to - t) / MIN + 1);
                TreeMap<Long, Map<String, KlineObjectSimple>> r = off != null
                        ? new TreeMap<>(off.subMap(t, true, t + (cnt - 1) * MIN, true))
                        : DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(t, cnt);
                for (long m = t; m < t + cnt * MIN; m += MIN) {
                    Map<String, KlineObjectSimple> snap = r.get(m);
                    if (snap == null || snap.isEmpty()) {
                        nMiss++;
                        continue;
                    }
                    MarketDataObject j = gen.update(snap);
                    double[] p = py(snap, pyBuf);
                    w.println(m + "," + snap.size() + "," + (j == null ? ",," : j.rateDownAvg + "," + j.rateUpAvg + "," + j.rateDown15MAvg)
                            + "," + (p == null ? ",," : p[0] + "," + p[1] + "," + p[2]));
                    n++;
                }
            }
        }
        OfflineGuard.finish();
        LOG.info("MD done minutes={} miss={}", n, nMiss);
        System.exit(0);
    }

    /** md_inline.py (InlineMD.update + cal_market_data), float64, KHONG loc isTickerAvailable. */
    static double[] py(Map<String, KlineObjectSimple> snap, Map<String, Deque<double[]>> buf) {
        Map<String, Double> mx = new HashMap<>(), mn = new HashMap<>();
        int valid = 0, warm = 0;
        for (Map.Entry<String, KlineObjectSimple> e : snap.entrySet()) {
            if (Constants.diedSymbol.contains(e.getKey())) continue;
            KlineObjectSimple k = e.getValue();
            Deque<double[]> b = buf.computeIfAbsent(e.getKey(), s -> new ArrayDeque<>());
            b.addLast(new double[]{k.maxPrice, k.minPrice});
            if (b.size() > 15) b.removeFirst();
            valid++;
            if (b.size() >= 15) warm++;
            double h = -Double.MAX_VALUE, l = Double.MAX_VALUE;
            for (double[] x : b) {
                h = Math.max(h, x[0]);
                l = Math.min(l, x[1]);
            }
            mx.put(e.getKey(), h);
            mn.put(e.getKey(), l);
        }
        if (valid < 50 || !snap.containsKey("BTCUSDT") || warm < 50) return null;
        KlineObjectSimple btc = snap.get("BTCUSDT");
        double rb = ((double) btc.priceClose - btc.priceOpen) / btc.priceOpen;
        TreeMap<Double, String> rd = new TreeMap<>(), ru = new TreeMap<>(), rm = new TreeMap<>();
        for (Map.Entry<String, KlineObjectSimple> e : snap.entrySet()) {
            String s = e.getKey();
            if (Constants.diedSymbol.contains(s)) continue;
            KlineObjectSimple k = e.getValue();
            double o = k.priceOpen, c = k.priceClose;
            double rc = o != 0 ? (c - o) / o : 0.0;
            if (rb > -0.004 && rc < -0.15) continue;
            if (rc > 0.3) continue;
            rd.put(rc, s);
            ru.put(-rc, s);
            Double h = mx.get(s);
            if (h != null && h != 0) rm.put((c - h) / h, s);
        }
        return new double[]{avg(rd), -avg(ru), avg(rm)};
    }

    static double avg(TreeMap<Double, String> m) {
        if (m.isEmpty()) return 0.0;
        int period = 100, n = m.size();
        if (period > n * 4 / 5) period = n * 4 / 5;
        double tot = 0;
        int c = 0;
        for (Double k : m.keySet()) {
            c++;
            tot += k;
            if (c >= period) break;
        }
        return c == 0 ? 0.0 : tot / c;
    }
}
