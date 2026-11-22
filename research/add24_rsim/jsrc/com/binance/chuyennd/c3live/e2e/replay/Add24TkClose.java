package com.binance.chuyennd.c3live.e2e.replay;
import java.io.*; import java.util.*; import java.util.zip.GZIPInputStream;
/** LUOT7 (DEV-B): gia close ticker SIM (tk26) cho cac cap (symbol, phut) trong pairs.csv -> out.csv (symbol,t,close,startTime). EB24 assert. */
public final class Add24TkClose {
    @SuppressWarnings("unchecked")
    public static void main(String[] a) throws Exception {
        Map<Long, Set<String>> want = new HashMap<>();
        try (BufferedReader br = new BufferedReader(new FileReader(a[0]))) { String ln = br.readLine();
            while ((ln = br.readLine()) != null) { String[] p = ln.split(","); want.computeIfAbsent(Long.parseLong(p[1]), z -> new HashSet<>()).add(p[0]); } }
        try (PrintWriter pw = new PrintWriter(new FileWriter(a[1]))) {
            pw.println("symbol,t,close,found");
            for (int i = 2; i < a.length; i++) {
                TreeMap<Long, Map<String, Object>> m;
                try (ObjectInputStream ois = new ObjectInputStream(new BufferedInputStream(new GZIPInputStream(new FileInputStream(a[i])), 1 << 20))) { m = (TreeMap<Long, Map<String, Object>>) ois.readObject(); }
                for (Map.Entry<Long, Map<String, Object>> e : m.entrySet()) {
                    if (e.getKey() > 1790787599999L) throw new IllegalStateException("EB24");
                    Set<String> w = want.get(e.getKey()); if (w == null) continue;
                    for (String s : w) {
                        Object o = e.getValue().get(s); if (o == null) o = e.getValue().get(s.replaceAll("USDT$", ""));
                        pw.println(s + "," + e.getKey() + "," + (o == null ? "" : ((com.binance.chuyennd.object.sw.KlineObjectSimple) o).priceClose) + "," + (o != null));
                    }
                }
            }
        }
    }
}
