package com.binance.chuyennd.c3live.e2e.replay;

import java.io.*;
import java.util.*;
import java.util.zip.GZIPInputStream;

/** ADD24 B5 (DEV-B): tai lap TIER cua sim (CoinRankManager.updateRanking + HistoryManager a8690d46) tu CHINH ticker sim (ho4p1-tk26):
 *  universe = symbol co nen o tick cap nhat; tong totalUsdt 720 ban ghi gan nhat (ring); sort giam dan, hoa -> A-Z; bottom 20 % = TIER_3;
 *  cap nhat khi phut % 60 == 0. In: tier/rank FIGHT, SPACE moi gio + co mat nen FIGHT tai cac phut chi dinh. Khong PnL. */
public final class Add24TierProbe {
    public static void main(String[] a) throws Exception {
        File dir = new File(a[0]);
        String[] watch = a[1].split(",");
        Set<Long> probeMin = new HashSet<>();
        for (String x : a[2].split(",")) probeMin.add(Long.parseLong(x));
        File[] fs = dir.listFiles((d, n) -> n.startsWith("ticker_") && n.endsWith(".bin.gz"));
        Arrays.sort(fs);
        Map<String, float[]> ring = new HashMap<>();
        Map<String, Integer> head = new HashMap<>();
        Map<String, Long> lastT = new HashMap<>();
        for (File f : fs) {
            TreeMap<Long, Map<String, Object>> m;
            try (ObjectInputStream ois = new ObjectInputStream(new BufferedInputStream(new GZIPInputStream(new FileInputStream(f)), 1 << 20))) {
                @SuppressWarnings("unchecked") TreeMap<Long, Map<String, Object>> mm = (TreeMap<Long, Map<String, Object>>) ois.readObject();
                m = mm;
            }
            for (Map.Entry<Long, Map<String, Object>> e : m.entrySet()) {
                long t = e.getKey();
                Set<String> present = new HashSet<>();
                for (Map.Entry<String, Object> se : e.getValue().entrySet()) {
                    String s = se.getKey().endsWith("USDT") ? se.getKey() : se.getKey() + "USDT";
                    com.binance.chuyennd.object.sw.KlineObjectSimple k = (com.binance.chuyennd.object.sw.KlineObjectSimple) se.getValue();
                    if (k == null) continue;
                    present.add(s);
                    float[] r = ring.computeIfAbsent(s, z -> new float[720]);
                    int h = head.getOrDefault(s, 0);
                    Long lt = lastT.get(s);
                    if (lt != null && lt == k.startTime.longValue()) h--;   // ghi de cung startTime
                    r[((h % 720) + 720) % 720] = k.totalUsdt;
                    head.put(s, h + 1);
                    lastT.put(s, k.startTime);
                    if (probeMin.contains(t)) {
                        for (String w : watch) if (w.equals(s)) System.out.println("BAR t=" + t + " " + s + " o=" + k.priceOpen + " h=" + k.maxPrice + " l=" + k.minPrice + " c=" + k.priceClose + " qv=" + k.totalUsdt);
                    }
                }
                if (probeMin.contains(t)) for (String w : watch) if (!present.contains(w)) System.out.println("BAR t=" + t + " " + w + " MISSING");
                if ((t / 60000L) % 60 == 0) {
                    TreeMap<Float, List<String>> vm = new TreeMap<>(Collections.reverseOrder());
                    for (String s : present) {
                        int h = head.get(s);
                        int n = Math.min(h, 720);
                        float sum = 0f;
                        for (int i = 1; i <= n; i++) sum += ring.get(s)[(((h - i) % 720) + 720) % 720];
                        vm.computeIfAbsent(sum, z -> new ArrayList<>()).add(s);
                    }
                    List<String> order = new ArrayList<>();
                    for (List<String> l : vm.values()) { Collections.sort(l); order.addAll(l); }
                    int n = order.size(), b20 = (int) (n * 0.80);
                    StringBuilder sb = new StringBuilder("TIER t=" + t + " n=" + n);
                    for (String w : watch) {
                        int i = order.indexOf(w);
                        sb.append(" ").append(w).append("=").append(i).append(i < 0 ? "(absent)" : (i >= b20 ? "(T3)" : (i < (int) (n * 0.2) ? "(T1)" : "(T2)")));
                        sb.append(" hist=").append(Math.min(head.getOrDefault(w, 0), 720));
                    }
                    System.out.println(sb);
                }
            }
        }
    }
}
