package com.binance.chuyennd.c3live.e2e.replay;
import java.io.*; import java.util.*; import java.util.zip.GZIPInputStream;
/** LUOT6: in khoa phut dau/cuoi cua file ticker sim + startTime cua 1 kline o moi khoa (khong in gia). */
public final class Add24TkPeek {
    @SuppressWarnings("unchecked")
    public static void main(String[] a) throws Exception {
        for (String fn : a) {
            TreeMap<Long, Map<String, Object>> m;
            try (ObjectInputStream ois = new ObjectInputStream(new BufferedInputStream(new GZIPInputStream(new FileInputStream(fn)), 1 << 20))) { m = (TreeMap<Long, Map<String, Object>>) ois.readObject(); }
            for (Long key : new long[0].length == 0 ? Arrays.asList(m.firstKey(), m.lastKey()) : null) {
                long st = -1; int n = 0, eq = 0;
                for (Object o : m.get(key).values()) { if (o == null) continue; long s = ((com.binance.chuyennd.object.sw.KlineObjectSimple) o).startTime; if (st < 0) st = s; n++; if (s == key) eq++; }
                System.out.println(fn.replaceAll(".*/", "") + " key=" + key + " kline.startTime=" + st + " n=" + n + " eqKey=" + eq);
            }
        }
    }
}
