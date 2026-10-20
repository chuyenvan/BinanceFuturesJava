package tsxoff;

import com.binance.chuyennd.tradecore.selector.AltEwIndex;
import com.binance.chuyennd.tradecore.selector.TsMktExt;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedOutputStream;
import java.io.DataOutputStream;
import java.io.FileOutputStream;
import java.io.PrintWriter;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.MappedByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Harness OFFLINE (khong thuoc jar live): chay DUNG lop live AltEwIndex / TsMktExt.decide tren kline Vision
 * (bin do tsx_prep.py viet tu parquet Kaggle vz-kline1m-*). Khong Aerospike, khong mang.
 * Modes: ew &lt;bin&gt; &lt;syms&gt; &lt;outPrefix&gt; | flags &lt;out.csv&gt; &lt;fromDay&gt; &lt;toDay&gt; &lt;days.csv...&gt; |
 * replay &lt;flags.csv&gt; &lt;trades.csv&gt; &lt;out.csv&gt;
 */
public final class TsxLiveOffline {
    private static final Logger LOG = LoggerFactory.getLogger(TsxLiveOffline.class);

    public static void main(String[] a) throws Exception {
        switch (a[0]) {
            case "ew":
                ew(a[1], a[2], a[3]);
                break;
            case "flags":
                flags(a);
                break;
            case "replay":
                replay(a[1], a[2], a[3]);
                break;
            case "cache":
                cache(a[1], a[2]);
                break;
            default:
                throw new IllegalArgumentException(a[0]);
        }
    }

    private static MappedByteBuffer map(FileChannel ch, long off, long len) throws Exception {
        MappedByteBuffer b = ch.map(FileChannel.MapMode.READ_ONLY, off, len);
        b.order(ByteOrder.LITTLE_ENDIAN);
        return b;
    }

    static void ew(String bin, String symsPath, String out) throws Exception {
        List<String> syms = Files.readAllLines(Paths.get(symsPath));
        AltEwIndex a64 = new AltEwIndex();
        AltEwIndex a32 = new AltEwIndex();
        int[] m64 = new int[syms.size()];
        int[] m32 = new int[syms.size()];
        for (int i = 0; i < syms.size(); i++) {
            m64[i] = a64.id(syms.get(i).trim());
            m32[i] = a32.id(syms.get(i).trim());
        }
        long nEw = 0, nMin = 0;
        try (RandomAccessFile raf = new RandomAccessFile(bin, "r"); FileChannel ch = raf.getChannel();
             DataOutputStream o64 = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(out + "_ew64.bin"), 1 << 20));
             DataOutputStream o32 = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(out + "_ew32.bin"), 1 << 20))) {
            ByteBuffer hb = ByteBuffer.allocate(8).order(ByteOrder.LITTLE_ENDIAN);
            ch.read(hb, 0);
            long n = hb.getLong(0);
            MappedByteBuffer ts = map(ch, 8, 8 * n);
            MappedByteBuffer id = map(ch, 8 + 8 * n, 4 * n);
            MappedByteBuffer cl = map(ch, 8 + 12 * n, 8 * n);
            MappedByteBuffer qv = map(ch, 8 + 20 * n, 8 * n);
            int cap = 4096;
            int[] i64 = new int[cap], i32 = new int[cap];
            double[] c = new double[cap], q = new double[cap], c32 = new double[cap], q32 = new double[cap];
            long i = 0;
            while (i < n) {
                long t = ts.getLong((int) (8 * i));
                int k = 0;
                while (i < n && ts.getLong((int) (8 * i)) == t) {
                    int sid = id.getInt((int) (4 * i));
                    double cc = cl.getDouble((int) (8 * i));
                    double qq = qv.getDouble((int) (8 * i));
                    i64[k] = m64[sid];
                    i32[k] = m32[sid];
                    c[k] = cc;
                    q[k] = qq;
                    c32[k] = (double) (float) cc;     // mo phong store Aerospike float32
                    q32[k] = (double) (float) qq;
                    k++;
                    i++;
                }
                nMin++;
                double e64 = a64.feed(t, i64, c, q, k);
                double e32 = a32.feed(t, i32, c32, q32, k);
                if (!Double.isNaN(e64)) {
                    o64.writeLong(t);
                    o64.writeDouble(e64);
                    nEw++;
                }
                if (!Double.isNaN(e32)) {
                    o32.writeLong(t);
                    o32.writeDouble(e32);
                }
            }
            LOG.info("ew {} rows={} minutes={} ew={}", bin, n, nMin, nEw);
        }
        writeDays(a64.finish(), out + "_days64.csv");
        writeDays(a32.finish(), out + "_days32.csv");
        String ex = System.getenv("TSX_EXCL");
        if (ex != null && !ex.isEmpty()) {
            String[] files = ex.split(":");
            for (int k = 0; k < files.length; k++) excl(bin, syms, files[k], out + "_daysX" + k + ".csv");
        }
    }

    /** Nhu ew (float32 = dang store live) nhung BO cac symbol trong file loai tru — do do nhay universe. */
    static void excl(String bin, List<String> syms, String exFile, String outCsv) throws Exception {
        java.util.Set<String> ex = new java.util.HashSet<>();
        for (String l : Files.readAllLines(Paths.get(exFile))) if (!l.trim().isEmpty()) ex.add(l.trim());
        AltEwIndex acc = new AltEwIndex();
        int[] mp = new int[syms.size()];
        boolean[] drop = new boolean[syms.size()];
        for (int i = 0; i < syms.size(); i++) {
            mp[i] = acc.id(syms.get(i).trim());
            drop[i] = ex.contains(syms.get(i).trim());
        }
        try (RandomAccessFile raf = new RandomAccessFile(bin, "r"); FileChannel ch = raf.getChannel()) {
            ByteBuffer hb = ByteBuffer.allocate(8).order(ByteOrder.LITTLE_ENDIAN);
            ch.read(hb, 0);
            long n = hb.getLong(0);
            MappedByteBuffer ts = map(ch, 8, 8 * n);
            MappedByteBuffer id = map(ch, 8 + 8 * n, 4 * n);
            MappedByteBuffer cl = map(ch, 8 + 12 * n, 8 * n);
            MappedByteBuffer qv = map(ch, 8 + 20 * n, 8 * n);
            int cap = 4096;
            int[] ii = new int[cap];
            double[] c = new double[cap], q = new double[cap];
            long i = 0;
            while (i < n) {
                long t = ts.getLong((int) (8 * i));
                int k = 0;
                while (i < n && ts.getLong((int) (8 * i)) == t) {
                    int sid = id.getInt((int) (4 * i));
                    if (!drop[sid]) {
                        ii[k] = mp[sid];
                        c[k] = (double) (float) cl.getDouble((int) (8 * i));
                        q[k] = (double) (float) qv.getDouble((int) (8 * i));
                        k++;
                    }
                    i++;
                }
                acc.feed(t, ii, c, q, k);
            }
        }
        writeDays(acc.finish(), outCsv);
        LOG.info("excl {} drop={} -> {}", exFile, ex.size(), outCsv);
    }

    private static void writeDays(TreeMap<Long, AltEwIndex.DayStat> d, String path) throws Exception {
        try (PrintWriter w = new PrintWriter(path)) {
            w.println("epoch_day,date,sum_ew,n_min");
            for (AltEwIndex.DayStat s : d.values()) {
                w.println(s.day + "," + LocalDate.ofEpochDay(s.day) + "," + Double.toString(s.sum) + "," + s.n);
            }
        }
    }

    static void flags(String[] a) throws Exception {
        String out = a[1];
        long from = LocalDate.parse(a[2]).toEpochDay();
        long to = LocalDate.parse(a[3]).toEpochDay();
        Map<Long, AltEwIndex.DayStat> days = new HashMap<>();
        for (int i = 4; i < a.length; i++) {
            for (String ln : Files.readAllLines(Paths.get(a[i]))) {
                if (ln.startsWith("epoch_day")) continue;
                String[] p = ln.split(",");
                long d = Long.parseLong(p[0]);
                days.put(d, new AltEwIndex.DayStat(d, Double.parseDouble(p[2]), Integer.parseInt(p[3])));
            }
        }
        int on = 0;
        try (PrintWriter w = new PrintWriter(out)) {
            w.println("flag_day,date,state,dd,p,max_p,max_day,min_n,reason");
            for (long d = from; d <= to; d++) {
                AltEwIndex.FlagResult r = AltEwIndex.flagFor(d, days);
                if (r.state == AltEwIndex.State.ON) on++;
                w.println(d + "," + LocalDate.ofEpochDay(d) + "," + r.state + "," + Double.toString(r.dd) + ","
                        + Double.toString(r.p) + "," + Double.toString(r.maxP) + "," + r.maxDay + "," + r.minN + ","
                        + r.reason);
            }
        }
        LOG.info("flags {} {}..{} on={}", out, a[2], a[3], on);
    }

    /** Cache .ser.gz (record phut kline_1m_opt dang live, float32) -> duong adapter Map cua AltEwIndex. */
    @SuppressWarnings("unchecked")
    static void cache(String ser, String out) throws Exception {
        TreeMap<Long, Map<String, com.binance.chuyennd.object.sw.KlineObjectSimple>> d;
        try (java.io.ObjectInputStream in = new java.io.ObjectInputStream(new java.util.zip.GZIPInputStream(
                new java.io.FileInputStream(ser)))) {
            d = (TreeMap<Long, Map<String, com.binance.chuyennd.object.sw.KlineObjectSimple>>) in.readObject();
        }
        AltEwIndex acc = new AltEwIndex();
        java.util.TreeSet<String> all = new java.util.TreeSet<>();
        try (PrintWriter w = new PrintWriter(out + "_min.csv")) {
            w.println("ts,nsym,ew");
            for (Map.Entry<Long, Map<String, com.binance.chuyennd.object.sw.KlineObjectSimple>> e : d.entrySet()) {
                double ew = acc.feed(e.getKey(), e.getValue());
                w.println(e.getKey() + "," + e.getValue().size() + "," + Double.toString(ew));
                all.addAll(e.getValue().keySet());
            }
        }
        writeDays(acc.finish(), out + "_days.csv");
        Files.write(Paths.get(out + "_syms.txt"), all);
        LOG.info("cache {} minutes={} syms={}", ser, d.size(), all.size());
    }

    /** trades.csv: sym,anchor_ms,exit_ms,status. Phut (ms) dau tien decide = CUT tinh tu anchor+168h+1m. */
    static void replay(String flagsCsv, String trades, String out) throws Exception {
        Map<Long, TsMktExt.Flag> fl = new HashMap<>();
        for (String ln : Files.readAllLines(Paths.get(flagsCsv))) {
            if (ln.startsWith("flag_day")) continue;
            String[] p = ln.split(",");
            fl.put(Long.parseLong(p[0]), "ON".equals(p[2]) ? TsMktExt.Flag.ON : TsMktExt.Flag.OFF);
        }
        long min = 60_000L;
        try (PrintWriter w = new PrintWriter(out)) {
            w.println("sym,anchor_ms,exit_ms,status,first_due_ms,first_dec,cut_ms");
            for (String ln : Files.readAllLines(Paths.get(trades))) {
                if (ln.startsWith("sym")) continue;
                String[] p = ln.split(",");
                long anchor = Long.parseLong(p[1]);
                long due = anchor + TsMktExt.BASE_HOURS * TsMktExt.HOUR + min;
                TsMktExt.Decision first = null;
                long cut = -1;
                for (long m = due; m <= anchor + 600 * TsMktExt.HOUR; m += min) {
                    TsMktExt.Flag f = fl.getOrDefault(Math.floorDiv(m, AltEwIndex.DAY), TsMktExt.Flag.OFF);
                    TsMktExt.Decision d = TsMktExt.decide(true, false, m - anchor, f);
                    if (first == null) first = d;
                    if (d == TsMktExt.Decision.CUT) {
                        cut = m;
                        break;
                    }
                }
                w.println(p[0] + "," + anchor + "," + p[2] + "," + p[3] + "," + due + "," + first + "," + cut);
            }
        }
        LOG.info("replay {} -> {}", trades, out);
    }
}
