package com.binance.chuyennd.c3live.e2e.replay;

import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.CoinRankManager;
import java.io.*;
import java.lang.reflect.Field;
import java.util.*;
import java.util.zip.GZIPInputStream;

/** ADD24 LUOT6 1a (DEV-B): TIER LUOI cua sim tai lap bang CHINH code a8690d46 (CoinRankManager + HistoryManager + SimpleSymbolMapper
 *  bien dich tu git show a8690d46 vao simcls/, dat TRUOC jar stub tren classpath). Mapper = ov_idtostr.tsv cua HO5 (nap qua reflection,
 *  khong Aerospike); symbol chua co id -> cap id max+1.. theo thu tu A-Z (sim cap theo thu tu gap; id < 1000 nen chi doi ten, khong doi hang).
 *  Nuoi HistoryManager.updateHistoryArray moi phut tu ticker sim; CHI goi getCoinTier o cac moc cap nhat cua sim (args) => checkAndUpdate.
 *  EB24: assert moi ts <= 2026-09-30 23:59:59 +07 truoc khi xu ly. args: tsv files(csv path list) moments(csv ms) out.csv
 *  out: moment,symbol,id,tier (getCoinTier, UNKNOWN->T3) cho moi symbol trong mapper + cot ranked (co trong symbolTiers). */
public final class Add24SimTierCode {
    static final long TS_MAX = 1790787599999L;
    @SuppressWarnings("unchecked")
    public static void main(String[] a) throws Exception {
        SimpleSymbolMapper mp = SimpleSymbolMapper.getInstance();
        Map<String, Short> s2i = (Map<String, Short>) get(mp, "strToId");
        Map<Short, String> i2s = (Map<Short, String>) get(mp, "idToStr");
        short mx = 0;
        try (BufferedReader br = new BufferedReader(new InputStreamReader(new FileInputStream(a[0]), "UTF-8"))) {
            String ln;
            while ((ln = br.readLine()) != null) {
                String[] p = ln.split("\t");
                if (p.length == 2 && p[0].matches("\\d+")) { short id = Short.parseShort(p[0]); s2i.put(p[1], id); i2s.put(id, p[1]); mx = (short) Math.max(mx, id); }
            }
        }
        set(mp, "counter", mx); set(mp, "isInitialized", true);
        String[] files = a[1].split(",");
        TreeSet<Long> mom = new TreeSet<>();
        for (String x : a[2].split(",")) mom.add(Long.parseLong(x));
        long last = mom.last();
        TreeSet<String> unseen = new TreeSet<>();
        Map<Long, Map<String, KlineObjectSimple>> all = new TreeMap<>();
        List<String> added = new ArrayList<>();
        try (PrintWriter pw = new PrintWriter(new FileWriter(a[3]))) {
            pw.println("moment,symbol,id,tier,ranked");
            for (String fn : files) {
                TreeMap<Long, Map<String, Object>> m;
                try (ObjectInputStream ois = new ObjectInputStream(new BufferedInputStream(new GZIPInputStream(new FileInputStream(fn)), 1 << 20))) {
                    m = (TreeMap<Long, Map<String, Object>>) ois.readObject();
                }
                for (Map.Entry<Long, Map<String, Object>> e : m.entrySet()) {
                    long t = e.getKey();
                    if (t > TS_MAX) throw new IllegalStateException("EB24 ts>" + TS_MAX);
                    if (t > last) break;
                    TreeMap<String, KlineObjectSimple> snap = new TreeMap<>();
                    for (Map.Entry<String, Object> se : e.getValue().entrySet()) {
                        if (se.getValue() == null) continue;
                        String s = se.getKey().endsWith("USDT") ? se.getKey() : se.getKey() + "USDT";
                        snap.put(s, (KlineObjectSimple) se.getValue());
                    }
                    for (String s : snap.keySet()) if (!s2i.containsKey(s)) unseen.add(s);
                    for (String s : unseen) if (!s2i.containsKey(s)) { mx++; s2i.put(s, mx); i2s.put(mx, s); added.add(s + "=" + mx); }
                    KlineObjectSimple[] arr = new KlineObjectSimple[Math.max(mx + 1, 1000)];
                    for (Map.Entry<String, KlineObjectSimple> se : snap.entrySet()) arr[s2i.get(se.getKey())] = se.getValue();
                    HistoryManager.getInstance().updateHistoryArray(arr);
                    if (mom.contains(t)) {
                        CoinRankManager crm = CoinRankManager.getInstance();
                        crm.getCoinTier((short) 1, t);
                        Map<String, CoinRankManager.CoinTier> st = (Map<String, CoinRankManager.CoinTier>) get(crm, "symbolTiers");
                        for (Map.Entry<String, Short> x : new TreeMap<>(s2i).entrySet()) {
                            CoinRankManager.CoinTier ti = crm.getCoinTier(x.getValue(), t);
                            pw.println(t + "," + x.getKey() + "," + x.getValue() + "," + ti + "," + (st.containsKey(x.getKey()) ? 1 : 0));
                        }
                        System.out.println("moment " + t + " ranked=" + st.size());
                    }
                }
                System.out.println("file " + fn + " ticks=" + m.size());
            }
        }
        System.out.println("added_ids " + added);
    }
    static Object get(Object o, String f) throws Exception { Field x = o.getClass().getDeclaredField(f); x.setAccessible(true); return x.get(o); }
    static void set(Object o, String f, Object v) throws Exception { Field x = o.getClass().getDeclaredField(f); x.setAccessible(true); x.set(o, v); }
}
