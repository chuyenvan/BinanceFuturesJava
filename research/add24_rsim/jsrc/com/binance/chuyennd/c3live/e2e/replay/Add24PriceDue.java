package com.binance.chuyennd.c3live.e2e.replay;
import com.binance.chuyennd.tradecore.DcaUtils;
import java.io.*; import java.util.*; import java.util.zip.GZIPInputStream;
/** LUOT7 (EB25): phut ma gia close (sim, closes.csv.gz) cua cum sim cham bac grid (DcaUtils.shouldDcaGrid jar, lc=1..4) - KHONG xet thi truong / gate.
 *  Dung de chon NGAY can mkt toan san cho nhanh DCA cua rig. args: cums.csv closes.csv.gz lo_ms hi_ms out.csv (cid,t,mask) */
public final class Add24PriceDue {
    public static void main(String[] a) throws Exception {
        long lo = Long.parseLong(a[2]), hi = Long.parseLong(a[3]);
        HashMap<String, TreeMap<Long, Float>> cl = new HashMap<>();
        try (BufferedReader br = new BufferedReader(new InputStreamReader(new GZIPInputStream(new FileInputStream(a[1]))))) {
            String ln; while ((ln = br.readLine()) != null) { String[] p = ln.split(","); long t = Long.parseLong(p[1]); if (t > 1790787599999L) throw new IllegalStateException("EB24"); cl.computeIfAbsent(p[0], z -> new TreeMap<>()).put(t, Float.parseFloat(p[3])); } }
        int n = 0;
        try (BufferedReader br = new BufferedReader(new FileReader(a[0])); PrintWriter pw = new PrintWriter(new FileWriter(a[4]))) {
            pw.println("cid,t,mask"); String ln = br.readLine();
            while ((ln = br.readLine()) != null) {
                String[] p = ln.split(","); float first = Float.parseFloat(p[2]); long t0 = Long.parseLong(p[3]), te = Long.parseLong(p[4]);
                TreeMap<Long, Float> c = cl.get(p[1]); long f0 = Math.max(t0 + 60000L, lo), f1 = Math.min(te, hi); if (c == null || f0 >= f1) continue;
                for (Map.Entry<Long, Float> e : c.subMap(f0, true, f1, false).entrySet()) {
                    int mask = 0; for (int lc = 1; lc <= 4; lc++) if (DcaUtils.shouldDcaGrid(first, e.getValue(), lc)) mask |= 1 << (lc - 1);
                    if (mask != 0) { pw.println(p[0] + "," + e.getKey() + "," + mask); n++; }
                }
            }
        }
        System.out.println("ADD24PRICEDUE rows=" + n);
    }
}
