package com.binance.chuyennd.c3live.e2e.replay;

import java.io.*;
import java.util.*;
import java.util.zip.GZIPInputStream;
import java.util.zip.GZIPOutputStream;

/** ADD24 LUOT5 (DEV-B): xep hang tier MOI GIO (logic CoinRankManager.updateRanking/HistoryManager a8690d46) tu ticker sim tk26,
 *  doc tuan tu cac file ticker_YYYYMMDD.bin.gz khi co marker .done (downloader), XOA file sau khi doc.
 *  Out: tier_hourly.csv.gz (hourMs,symbol,rank,n) cho MOI symbol co mat; closes.csv.gz (symbol,t,o,c,l,h) cho (symbol, khoang) trong watch.csv. */
public final class Add24TierAll {
    public static void main(String[] a) throws Exception {
        File dir = new File(a[0]);
        String[] days = a[1].split(",");
        Map<String, List<long[]>> watch = new HashMap<>();
        try (BufferedReader br = new BufferedReader(new FileReader(a[2]))) {
            String ln;
            while ((ln = br.readLine()) != null) {
                String[] p = ln.split(",");
                watch.computeIfAbsent(p[0], z -> new ArrayList<>()).add(new long[]{Long.parseLong(p[1]), Long.parseLong(p[2])});
            }
        }
        Map<String, float[]> ring = new HashMap<>();
        Map<String, Integer> head = new HashMap<>();
        Map<String, Long> lastT = new HashMap<>();
        try (PrintWriter tw = new PrintWriter(new OutputStreamWriter(new GZIPOutputStream(new FileOutputStream(new File(a[3], "tier_hourly.csv.gz")))));
             PrintWriter cw = new PrintWriter(new OutputStreamWriter(new GZIPOutputStream(new FileOutputStream(new File(a[3], "closes.csv.gz")))))) {
            for (String d : days) {
                File f = new File(dir, "ticker_" + d + ".bin.gz"), done = new File(dir, "ticker_" + d + ".done");
                long w0 = System.currentTimeMillis();
                while (!done.exists()) {
                    if (System.currentTimeMillis() - w0 > 1800_000L) throw new IOException("timeout cho " + f);
                    Thread.sleep(2000L);
                }
                TreeMap<Long, Map<String, Object>> m;
                try (ObjectInputStream ois = new ObjectInputStream(new BufferedInputStream(new GZIPInputStream(new FileInputStream(f)), 1 << 20))) {
                    @SuppressWarnings("unchecked") TreeMap<Long, Map<String, Object>> mm = (TreeMap<Long, Map<String, Object>>) ois.readObject();
                    m = mm;
                }
                f.delete();
                for (Map.Entry<Long, Map<String, Object>> e : m.entrySet()) {
                    long t = e.getKey();
                    if (t > 1790787599999L) break;   // EB24 (ERRATA4): khong nap ts > 2026-09-30 23:59:59 +07
                    List<String> present = new ArrayList<>();
                    for (Map.Entry<String, Object> se : e.getValue().entrySet()) {
                        String s = se.getKey().endsWith("USDT") ? se.getKey() : se.getKey() + "USDT";
                        com.binance.chuyennd.object.sw.KlineObjectSimple k = (com.binance.chuyennd.object.sw.KlineObjectSimple) se.getValue();
                        if (k == null) continue;
                        present.add(s);
                        float[] r = ring.computeIfAbsent(s, z -> new float[720]);
                        int h = head.getOrDefault(s, 0);
                        Long lt = lastT.get(s);
                        if (lt != null && lt == k.startTime.longValue()) h--;
                        r[((h % 720) + 720) % 720] = k.totalUsdt;
                        head.put(s, h + 1);
                        lastT.put(s, k.startTime);
                        List<long[]> iv = watch.get(s);
                        if (iv != null) for (long[] x : iv) if (t >= x[0] && t <= x[1]) {
                            cw.println(s + "," + t + "," + k.priceOpen + "," + k.priceClose + "," + k.minPrice + "," + k.maxPrice);
                            break;
                        }
                    }
                    if ((t / 60000L) % 60 == 0) {
                        TreeMap<Float, List<String>> vm = new TreeMap<>(Collections.reverseOrder());
                        for (String s : present) {
                            int h = head.get(s), n = Math.min(h, 720);
                            float sum = 0f;
                            for (int i = 1; i <= n; i++) sum += ring.get(s)[(((h - i) % 720) + 720) % 720];
                            vm.computeIfAbsent(sum, z -> new ArrayList<>()).add(s);
                        }
                        int rk = 0, n = present.size();
                        for (List<String> l : vm.values()) {
                            Collections.sort(l);
                            for (String s : l) tw.println(t + "," + s + "," + (rk++) + "," + n);
                        }
                    }
                }
                System.out.println("done " + d + " ticks=" + m.size());
                System.out.flush();
            }
        }
    }
}
