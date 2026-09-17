package com.binance.chuyennd.research;

import com.binance.chuyennd.object.sw.KlineObjectSimple;

import java.io.*;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.zip.GZIPInputStream;

/**
 * [2026-09-17] DOC-ONLY tool phu vu PREREG_PUMPDUMP_OHLCV (descriptive, KHONG sua logic trading).
 * Doc OHLCV 1m (ticker_*.bin.gz) + OI 5m (oi_percoin_full.bin) cho CHI cac lenh can thiet
 * (manifest sinh boi pumpdump_ohlcv.py), convert ra CSV de Python doc. KHONG convert het du lieu.
 *
 * Args: <manifest.csv> <outDir> <tickerDir> <oiFile>
 *   manifest.csv: tid,sym,oi_symId,entry_ts_ms,group  (khong header? -> CO header)
 * Output: outDir/ohlcv_1m.csv (tid,ts_ms,o,h,l,c,v) ; outDir/oi_5m.csv (tid,ts_ms,oi_delta24h,oi_z)
 * Cua so causal: bar co startTime < entry (da dong), trong [entry-30h, entry).
 */
public class PumpDumpOhlcvExtract {

    static final long MIN_MS = 60_000L;
    static final long HOUR = 3_600_000L;
    static final long DAY = 24 * HOUR;
    static final long LOOKBACK = 30 * HOUR;

    static final class Trade {
        int tid;
        String sym;      // full "BTCUSDT"
        int oiSymId;
        long entry;      // epoch ms UTC
    }

    static final class Win {
        long t0, t1;
        int tid;
        Win(long t0, long t1, int tid) { this.t0 = t0; this.t1 = t1; this.tid = tid; }
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 4) {
            System.err.println("Args: <manifest.csv> <outDir> <tickerDir> <oiFile>");
            System.exit(2);
        }
        String manifest = args[0];
        String outDir = args[1];
        String tickerDir = args[2];
        String oiFile = args[3];
        if (!tickerDir.endsWith("/")) tickerDir += "/";
        if (!outDir.endsWith("/")) outDir += "/";
        new File(outDir).mkdirs();

        List<Trade> trades = new ArrayList<>();
        try (BufferedReader br = new BufferedReader(new FileReader(manifest))) {
            String line = br.readLine(); // header
            while ((line = br.readLine()) != null) {
                if (line.trim().isEmpty()) continue;
                String[] p = line.split(",");
                Trade t = new Trade();
                t.tid = Integer.parseInt(p[0].trim());
                t.sym = p[1].trim();
                t.oiSymId = Integer.parseInt(p[2].trim());
                t.entry = Long.parseLong(p[3].trim());
                trades.add(t);
            }
        }
        System.err.println("manifest trades=" + trades.size());

        // ===== OI: stream once, filter by (symId, window) =====
        Map<Integer, List<Win>> oiNeed = new HashMap<>();
        for (Trade t : trades) {
            oiNeed.computeIfAbsent(t.oiSymId, k -> new ArrayList<>())
                    .add(new Win(t.entry - LOOKBACK, t.entry, t.tid));
        }
        long oiRec = 0, oiHit = 0;
        try (DataInputStream dis = new DataInputStream(
                new BufferedInputStream(new FileInputStream(oiFile), 1 << 20));
             BufferedWriter oiOut = new BufferedWriter(new FileWriter(outDir + "oi_5m.csv"), 1 << 20)) {
            oiOut.write("tid,ts_ms,oi_delta24h,oi_z\n");
            while (true) {
                long ts;
                short sid;
                try {
                    ts = dis.readLong();
                } catch (EOFException eof) {
                    break;
                }
                sid = dis.readShort();
                float oid = dis.readFloat();
                float z = dis.readFloat();
                dis.readFloat(); // lsGlobal
                dis.readFloat(); // lsToptrader
                dis.readFloat(); // takerBuy
                oiRec++;
                List<Win> wins = oiNeed.get((int) sid);
                if (wins != null) {
                    for (Win w : wins) {
                        if (ts >= w.t0 && ts <= w.t1) {
                            oiOut.write(w.tid + "," + ts + ","
                                    + (Float.isNaN(oid) ? "" : oid) + ","
                                    + (Float.isNaN(z) ? "" : z) + "\n");
                            oiHit++;
                        }
                    }
                }
            }
            System.err.println("OI records scanned=" + oiRec + " written=" + oiHit);
        }

        // ===== Ticker: per-trade, load only needed day files =====
        List<Trade> sorted = new ArrayList<>(trades);
        sorted.sort(Comparator.comparingLong(t -> t.entry));

        SimpleDateFormat sdfDay = new SimpleDateFormat("yyyyMMdd");
        sdfDay.setTimeZone(TimeZone.getTimeZone("UTC"));

        Map<String, TreeMap<Long, Map<String, KlineObjectSimple>>> cache = new HashMap<>();
        long barsOut = 0;
        int daysLoaded = 0, daysCacheHit = 0;
        try (BufferedWriter oOut = new BufferedWriter(new FileWriter(outDir + "ohlcv_1m.csv"), 1 << 20)) {
            oOut.write("tid,ts_ms,o,h,l,c,v\n");
            for (Trade t : sorted) {
                long lo = t.entry - LOOKBACK;
                long startDayMs = Math.floorDiv(lo, DAY) * DAY;
                long endDayMs = Math.floorDiv(t.entry - 1, DAY) * DAY;
                long startDayNum = Long.parseLong(sdfDay.format(new Date(startDayMs)));

                // evict cache days no longer needed (day string compares numerically)
                cache.keySet().removeIf(ds -> Long.parseLong(ds) < startDayNum);

                List<KlineObjectSimple> bars = new ArrayList<>();
                for (long d = startDayMs; d <= endDayMs; d += DAY) {
                    String ds = sdfDay.format(new Date(d));
                    TreeMap<Long, Map<String, KlineObjectSimple>> day = cache.get(ds);
                    if (day == null) {
                        day = loadDay(tickerDir, ds);
                        if (day != null) {
                            cache.put(ds, day);
                            daysLoaded++;
                        }
                    } else {
                        daysCacheHit++;
                    }
                    if (day == null) continue;
                    // collect bars for this coin in [lo, entry)
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : day.entrySet()) {
                        long ts = e.getKey();
                        if (ts < lo || ts >= t.entry) continue;
                        KlineObjectSimple k = e.getValue().get(t.sym);
                        if (k == null || k.startTime == null) continue;
                        bars.add(k);
                    }
                }
                bars.sort(Comparator.comparingLong(b -> b.startTime));
                for (KlineObjectSimple k : bars) {
                    oOut.write(t.tid + "," + k.startTime + ","
                            + k.priceOpen + "," + k.maxPrice + "," + k.minPrice + ","
                            + k.priceClose + "," + k.totalUsdt + "\n");
                    barsOut++;
                }
            }
            System.err.println("ticker bars written=" + barsOut + " daysLoaded=" + daysLoaded
                    + " cacheHit=" + daysCacheHit);
        }
        System.out.println("DONE_PUMPDUMP_EXTRACT ohlcv_bars=" + barsOut + " oi_rows=" + oiHit
                + " oi_scanned=" + oiRec);
    }

    @SuppressWarnings("unchecked")
    static TreeMap<Long, Map<String, KlineObjectSimple>> loadDay(String dir, String dayStr) {
        File gz = new File(dir + "ticker_" + dayStr + ".bin.gz");
        if (!gz.exists()) return null;
        try (ObjectInputStream ois = new ObjectInputStream(
                new BufferedInputStream(new GZIPInputStream(new FileInputStream(gz)), 1 << 20))) {
            return (TreeMap<Long, Map<String, KlineObjectSimple>>) ois.readObject();
        } catch (Exception e) {
            System.err.println("loadDay fail " + dayStr + ": " + e);
            return null;
        }
    }
}
