package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.*;
import java.util.zip.GZIPOutputStream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * PARITY_V11_WINDOW §2.1: dung cache phut `cache_<from>_<to>.ser.gz` (TreeMap&lt;Long, Map&lt;String, KlineObjectSimple&gt;&gt;, dung
 * dinh dang V11FeatHarness.load doc) tu zip Vision UM 1m daily. Ep float32 bang Float.valueOf(String) nhu
 * KlineObjectSimple.convertString2Kline (cot 1/2/3/4/7). Chi symbol trong universe. Khong mang, khong Aerospike.
 * args: universe.txt visionRoot from to outFile [holes.csv]
 */
public class VisionCacheBuilder {
    private static final Logger LOG = LoggerFactory.getLogger(VisionCacheBuilder.class);
    static final long MIN = 60_000L;

    public static void main(String[] a) throws Exception {
        List<String> uni = new ArrayList<>();
        try (BufferedReader r = new BufferedReader(new FileReader(a[0]))) {
            String s;
            while ((s = r.readLine()) != null) if (!s.trim().isEmpty() && !s.startsWith("#")) uni.add(s.trim());
        }
        Collections.sort(uni);
        String root = a[1];
        long from = Long.parseLong(a[2]), to = Long.parseLong(a[3]);
        TreeMap<Long, Map<String, KlineObjectSimple>> data = new TreeMap<>();
        LocalDate d0 = Instant.ofEpochMilli(from).atZone(ZoneOffset.UTC).toLocalDate();
        LocalDate d1 = Instant.ofEpochMilli(to).atZone(ZoneOffset.UTC).toLocalDate();
        Map<String, Integer> missFile = new TreeMap<>();
        long cells = 0;
        for (LocalDate d = d0; !d.isAfter(d1); d = d.plusDays(1)) {
            File dir = new File(root, d.toString());
            if (!dir.isDirectory()) throw new IllegalStateException("thieu thu muc Vision " + dir);
            int nf = 0;
            for (String s : uni) {
                File z = new File(dir, s + ".zip");
                if (!z.exists()) {
                    missFile.merge(d.toString(), 1, Integer::sum);
                    continue;
                }
                nf++;
                try (ZipInputStream zin = new ZipInputStream(new BufferedInputStream(new FileInputStream(z)))) {
                    ZipEntry e = zin.getNextEntry();
                    if (e == null) throw new IllegalStateException("zip rong " + z);
                    BufferedReader r = new BufferedReader(new InputStreamReader(zin, StandardCharsets.UTF_8));
                    String ln;
                    while ((ln = r.readLine()) != null) {
                        if (ln.isEmpty() || !Character.isDigit(ln.charAt(0))) continue;   // header
                        String[] p = ln.split(",");
                        long ts = Long.parseLong(p[0]);
                        if (ts < from || ts > to) continue;
                        if (ts % MIN != 0) throw new IllegalStateException("open_time khong tron phut " + ln + " " + z);
                        KlineObjectSimple k = new KlineObjectSimple();
                        k.startTime = ts;
                        k.priceOpen = Float.valueOf(p[1]);
                        k.maxPrice = Float.valueOf(p[2]);
                        k.minPrice = Float.valueOf(p[3]);
                        k.priceClose = Float.valueOf(p[4]);
                        k.totalUsdt = Float.valueOf(p[7]);
                        if (data.computeIfAbsent(ts, x -> new HashMap<>()).put(s, k) != null)
                            throw new IllegalStateException("trung (sym,ts) " + s + " " + ts);
                        cells++;
                    }
                }
            }
            LOG.info("day {} files={} missing={}", d, nf, missFile.getOrDefault(d.toString(), 0));
        }
        // lo Vision: symbol co nen truoc VA sau phut m nhung thieu o m (PREREG §5 K2a)
        int holes = 0;
        PrintWriter hw = a.length > 5 ? new PrintWriter(new FileWriter(a[5])) : null;
        if (hw != null) hw.println("ts,symbol");
        Map<String, Long> firstTs = new HashMap<>(), lastTs = new HashMap<>();
        for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : data.entrySet())
            for (String s : e.getValue().keySet()) {
                firstTs.putIfAbsent(s, e.getKey());
                lastTs.put(s, e.getKey());
            }
        for (long t = data.firstKey(); t <= data.lastKey(); t += MIN) {
            Map<String, KlineObjectSimple> m = data.get(t);
            for (String s : firstTs.keySet()) {
                if (firstTs.get(s) < t && lastTs.get(s) > t && (m == null || !m.containsKey(s))) {
                    holes++;
                    if (hw != null) hw.println(t + "," + s);
                }
            }
        }
        if (hw != null) hw.close();
        try (ObjectOutputStream o = new ObjectOutputStream(new GZIPOutputStream(new FileOutputStream(a[4])))) {
            o.writeObject(data);
        }
        LOG.info("cache {} minutes={} cells={} syms={} first={} last={} holes={} missing_files={}", a[4], data.size(), cells,
                firstTs.size(), data.firstKey(), data.lastKey(), holes, missFile);
    }
}
