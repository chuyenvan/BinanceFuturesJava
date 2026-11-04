package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.util.*;
import java.util.zip.GZIPInputStream;
import java.util.zip.GZIPOutputStream;

/**
 * PARITY_V11_WINDOW §6 R2: so 2 cache phut (A = 242 da luu, B = Vision) tung o (phut, symbol, 5 truong) bit-level.
 * args: cacheA cacheB outPrefix  => outPrefix_cells.csv.gz (o lech), outPrefix_syms_A.txt / _B.txt, log tong.
 */
public class CacheDiff {
    private static final Logger LOG = LoggerFactory.getLogger(CacheDiff.class);

    @SuppressWarnings("unchecked")
    static TreeMap<Long, Map<String, KlineObjectSimple>> read(String f) throws Exception {
        try (ObjectInputStream in = new ObjectInputStream(new GZIPInputStream(new FileInputStream(f)))) {
            return (TreeMap<Long, Map<String, KlineObjectSimple>>) in.readObject();
        }
    }

    static boolean eq(float x, float y) {
        return Float.floatToIntBits(x) == Float.floatToIntBits(y);
    }

    public static void main(String[] a) throws Exception {
        TreeMap<Long, Map<String, KlineObjectSimple>> A = read(a[0]), B = read(a[1]);
        String inner = A.isEmpty() ? "-" : A.firstEntry().getValue().getClass().getName();
        LOG.info("A minutes={} {}..{} inner={} | B minutes={} {}..{}", A.size(), A.firstKey(), A.lastKey(), inner, B.size(),
                B.firstKey(), B.lastKey());
        Set<String> sa = new TreeSet<>(), sb = new TreeSet<>();
        for (Map<String, KlineObjectSimple> m : A.values()) sa.addAll(m.keySet());
        for (Map<String, KlineObjectSimple> m : B.values()) sb.addAll(m.keySet());
        try (PrintWriter w = new PrintWriter(a[2] + "_syms_A.txt")) { sa.forEach(w::println); }
        try (PrintWriter w = new PrintWriter(a[2] + "_syms_B.txt")) { sb.forEach(w::println); }
        long cells = 0, same = 0, onlyA = 0, onlyB = 0, minOnlyA = 0, minOnlyB = 0;
        long[] fd = new long[6];
        String[] fn = {"startTime", "open", "high", "low", "close", "totalUsdt"};
        Set<Long> badMin = new TreeSet<>();
        Map<String, Integer> badSym = new TreeMap<>();
        try (PrintWriter w = new PrintWriter(new OutputStreamWriter(new GZIPOutputStream(new FileOutputStream(a[2] + "_cells.csv.gz"))))) {
            w.println("ts,symbol,kind,a_open,a_high,a_low,a_close,a_qv,b_open,b_high,b_low,b_close,b_qv");
            long lo = Math.max(A.firstKey(), B.firstKey()), hi = Math.min(A.lastKey(), B.lastKey());
            for (long t : new TreeSet<>(A.subMap(lo, true, hi, true).keySet())) if (!B.containsKey(t)) minOnlyA++;
            for (long t : new TreeSet<>(B.subMap(lo, true, hi, true).keySet())) if (!A.containsKey(t)) minOnlyB++;
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : A.subMap(lo, true, hi, true).entrySet()) {
                long t = e.getKey();
                Map<String, KlineObjectSimple> ma = e.getValue(), mb = B.getOrDefault(t, Collections.emptyMap());
                Set<String> all = new TreeSet<>(ma.keySet());
                all.addAll(mb.keySet());
                for (String s : all) {
                    KlineObjectSimple x = ma.get(s), y = mb.get(s);
                    if (x == null || y == null) {
                        if (x == null) onlyB++; else onlyA++;
                        badMin.add(t);
                        badSym.merge(s, 1, Integer::sum);
                        KlineObjectSimple z = x == null ? y : x;
                        w.println(t + "," + s + "," + (x == null ? "onlyB" : "onlyA") + "," + (x == null ? ",,,," : row(z)) + ","
                                + (y == null ? ",,,," : row(z)));
                        continue;
                    }
                    cells++;
                    boolean ok = true;
                    if (x.startTime.longValue() != y.startTime.longValue()) { fd[0]++; ok = false; }
                    if (!eq(x.priceOpen, y.priceOpen)) { fd[1]++; ok = false; }
                    if (!eq(x.maxPrice, y.maxPrice)) { fd[2]++; ok = false; }
                    if (!eq(x.minPrice, y.minPrice)) { fd[3]++; ok = false; }
                    if (!eq(x.priceClose, y.priceClose)) { fd[4]++; ok = false; }
                    if (!eq(x.totalUsdt, y.totalUsdt)) { fd[5]++; ok = false; }
                    if (ok) same++;
                    else {
                        badMin.add(t);
                        badSym.merge(s, 1, Integer::sum);
                        w.println(t + "," + s + ",diff," + row(x) + "," + row(y));
                    }
                }
            }
        }
        StringBuilder sb2 = new StringBuilder();
        for (int i = 0; i < 6; i++) sb2.append(fn[i]).append('=').append(fd[i]).append(' ');
        List<Map.Entry<String, Integer>> top = new ArrayList<>(badSym.entrySet());
        top.sort((p, q) -> q.getValue() - p.getValue());
        LOG.info("R2 syms A={} B={} A-B={} B-A={}", sa.size(), sb.size(), minus(sa, sb), minus(sb, sa));
        LOG.info("R2 cells_both={} bit_exact={} ({}%) onlyA={} onlyB={} minutes_onlyA={} minutes_onlyB={} field_diff[{}] bad_minutes={} top_sym={}",
                cells, same, cells == 0 ? 0 : String.format("%.6f", 100.0 * same / cells), onlyA, onlyB, minOnlyA, minOnlyB,
                sb2.toString().trim(), badMin.size(), top.subList(0, Math.min(15, top.size())));
    }

    static String row(KlineObjectSimple k) {
        return k.priceOpen + "," + k.maxPrice + "," + k.minPrice + "," + k.priceClose + "," + k.totalUsdt;
    }

    static List<String> minus(Set<String> x, Set<String> y) {
        List<String> o = new ArrayList<>();
        for (String s : x) if (!y.contains(s)) o.add(s);
        return o.size() > 40 ? o.subList(0, 40) : o;
    }
}
