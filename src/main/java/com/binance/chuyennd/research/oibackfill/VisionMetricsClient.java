package com.binance.chuyennd.research.oibackfill;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TimeZone;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * TASK-013 — Đọc-only client cho {@code data.binance.vision} metrics daily (OI/LS/taker 5m).
 * Bắt chước cơ chế tải/zip của {@code SurvivorshipBac0} (HttpURLConnection thuần + ZipInputStream),
 * KHÔNG đụng Aerospike/Configs/Redis ⇒ chạy được cả trên dev/226/Kaggle.
 *
 * <p>Cung cấp: liệt kê universe symbol có metrics; liệt kê đúng ngày-file của 1 symbol (tránh 404-storm
 * khi quét mù 2020→nay); tải + parse + dedup + chuẩn-mốc-5m → 5 {@code TreeMap<Long,Float>} cho 1 symbol.
 */
public class VisionMetricsClient {

    private static final Logger LOG = LoggerFactory.getLogger(VisionMetricsClient.class);

    private static final String S3_LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision";
    private static final String FILE_BASE = "https://data.binance.vision";
    private static final String METRICS_PREFIX = "data/futures/um/daily/metrics/";

    private static final Pattern CP = Pattern.compile("<CommonPrefixes><Prefix>(.*?)</Prefix></CommonPrefixes>");
    private static final Pattern KEY = Pattern.compile("<Key>(.*?)</Key>");
    private static final Pattern NEXT = Pattern.compile("<NextMarker>(.*?)</NextMarker>");
    private static final Pattern DATE_IN_NAME = Pattern.compile("-metrics-(\\d{4}-\\d{2}-\\d{2})\\.zip$");

    /** SimpleDateFormat KHÔNG thread-safe → ThreadLocal (download song song nhiều luồng). */
    private static final ThreadLocal<SimpleDateFormat> SDF_UTC = ThreadLocal.withInitial(() -> {
        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        f.setTimeZone(TimeZone.getTimeZone("UTC"));
        return f;
    });

    /** Kết quả backfill 1 symbol: 5 map metric (theo {@link OiMetricSets#ALL}, cùng thứ tự). */
    public static class SymbolMetrics {
        public final String symbol;
        public final TreeMap<Long, Float>[] maps;   // index khớp OiMetricSets.ALL
        public int filesOk;
        public int filesEmpty;
        public int rawRows;     // tổng dòng dữ liệu (trước dedup)

        @SuppressWarnings("unchecked")
        SymbolMetrics(String symbol) {
            this.symbol = symbol;
            this.maps = new TreeMap[OiMetricSets.ALL.length];
            for (int i = 0; i < maps.length; i++) maps[i] = new TreeMap<>();
        }
    }

    /** Liệt kê toàn bộ symbol có thư mục metrics (paginated S3-XML, CommonPrefixes). */
    public TreeSet<String> listSymbols() throws IOException {
        TreeSet<String> out = new TreeSet<>();
        String marker = "";
        int pages = 0;
        while (true) {
            String url = S3_LIST + "?delimiter=/&prefix=" + METRICS_PREFIX;
            if (!marker.isEmpty()) url += "&marker=" + URLEncoder.encode(marker, "UTF-8");
            String xml = httpText(url);
            pages++;
            Matcher m = CP.matcher(xml);
            String lastSeg = null;
            while (m.find()) {
                String p = m.group(1);                       // .../metrics/BTCUSDT/
                lastSeg = p;
                String seg = p.replaceAll("/+$", "");
                seg = seg.substring(seg.lastIndexOf('/') + 1);
                if (!seg.isEmpty()) out.add(seg.toUpperCase());
            }
            if (!xml.contains("<IsTruncated>true</IsTruncated>")) break;
            Matcher nm = NEXT.matcher(xml);
            if (nm.find() && !nm.group(1).isEmpty()) marker = nm.group(1);
            else if (lastSeg != null) marker = lastSeg;
            else break;
            if (pages > 80) {
                LOG.warn("⚠️ >80 trang listing universe — dừng phòng loop.");
                break;
            }
        }
        return out;
    }

    /** Liệt kê đúng các ngày (yyyy-MM-dd) có file metrics của 1 symbol (paginated, bỏ .CHECKSUM). */
    public List<String> listFileDates(String symbol) throws IOException {
        TreeSet<String> dates = new TreeSet<>();
        String prefix = METRICS_PREFIX + symbol.toUpperCase() + "/";
        String marker = "";
        int pages = 0;
        while (true) {
            String url = S3_LIST + "?prefix=" + prefix;
            if (!marker.isEmpty()) url += "&marker=" + URLEncoder.encode(marker, "UTF-8");
            String xml = httpText(url);
            pages++;
            Matcher m = KEY.matcher(xml);
            String lastKey = null;
            while (m.find()) {
                String k = m.group(1);
                lastKey = k;
                if (k.endsWith(".CHECKSUM")) continue;
                Matcher dm = DATE_IN_NAME.matcher(k);
                if (dm.find()) dates.add(dm.group(1));
            }
            if (!xml.contains("<IsTruncated>true</IsTruncated>")) break;
            Matcher nm = NEXT.matcher(xml);
            if (nm.find() && !nm.group(1).isEmpty()) marker = nm.group(1);
            else if (lastKey != null) marker = lastKey;
            else break;
            if (pages > 200) {
                LOG.warn("⚠️ {} >200 trang listing file — dừng phòng loop.", symbol);
                break;
            }
        }
        return new ArrayList<>(dates);
    }

    /**
     * Tải + parse + dedup + chuẩn-mốc-5m toàn bộ metrics của 1 symbol. Tải song song nhiều ngày (threads),
     * merge tuần tự vào 5 TreeMap (dedup tự nhiên theo ts đã chuẩn-hoá).
     *
     * @param symbol  symbol (UPPER).
     * @param threads số luồng tải song song.
     */
    public SymbolMetrics fetchSymbol(String symbol, int threads) throws Exception {
        SymbolMetrics res = new SymbolMetrics(symbol);
        List<String> dates = listFileDates(symbol);
        if (dates.isEmpty()) {
            LOG.warn("⚠️ {} không có file metrics nào (S3 listing rỗng).", symbol);
            return res;
        }

        ExecutorService pool = Executors.newFixedThreadPool(Math.max(1, threads));
        try {
            List<Future<List<long[]>>> futures = new ArrayList<>();
            // Mỗi ngày → 1 task tải+parse, trả list dòng dạng [ts, bitsCol3, bitsCol4, ... ] dùng Float.floatToIntBits.
            for (String d : dates) {
                final String date = d;
                futures.add(pool.submit((Callable<List<long[]>>) () -> parseDay(symbol, date)));
            }
            for (int i = 0; i < futures.size(); i++) {
                List<long[]> rows;
                try {
                    rows = futures.get(i).get();
                } catch (Exception e) {
                    LOG.warn("⚠️ {} ngày {} lỗi tải/parse: {}", symbol, dates.get(i), e.getMessage());
                    continue;
                }
                if (rows == null) {
                    res.filesEmpty++;
                    continue;
                }
                res.filesOk++;
                for (long[] row : rows) {
                    res.rawRows++;
                    long ts = row[0];
                    for (int mIdx = 0; mIdx < OiMetricSets.ALL.length; mIdx++) {
                        long bits = row[1 + mIdx];
                        if (bits == Long.MIN_VALUE) continue;          // metric thiếu ở dòng này
                        float v = Float.intBitsToFloat((int) bits);
                        if (Float.isNaN(v) || Float.isInfinite(v)) continue;
                        res.maps[mIdx].put(ts, v);                     // dedup: ts trùng = ghi đè (giá trị giống nhau)
                    }
                }
            }
        } finally {
            pool.shutdownNow();
        }
        return res;
    }

    /**
     * Tải + parse 1 file daily, trả map ts5m → giá trị của ĐÚNG 1 metric (theo col CSV). Dùng cho VERIFY
     * recompute value-fidelity (so giá trị thô CSV vs giá trị đã lưu Aerospike). null nếu 404/rỗng.
     */
    public TreeMap<Long, Float> parseDayMetric(String symbol, String date, int col) throws IOException {
        List<long[]> rows = parseDay(symbol, date);
        if (rows == null) return null;
        // xác định index trong row tương ứng col CSV.
        int mIdx = -1;
        for (int i = 0; i < OiMetricSets.ALL.length; i++) if (OiMetricSets.ALL[i].col == col) mIdx = i;
        if (mIdx < 0) return null;
        TreeMap<Long, Float> out = new TreeMap<>();
        for (long[] row : rows) {
            long bits = row[1 + mIdx];
            if (bits == Long.MIN_VALUE) continue;
            out.put(row[0], Float.intBitsToFloat((int) bits));
        }
        return out;
    }

    /** Tải + parse 1 file daily. Trả null nếu 404/rỗng. Mỗi phần tử = [ts5m, bits(col3), bits(col4), col5, col6, col7]. */
    private List<long[]> parseDay(String symbol, String date) throws IOException {
        String url = String.format("%s/%s%s/%s-metrics-%s.zip", FILE_BASE, METRICS_PREFIX, symbol.toUpperCase(),
                symbol.toUpperCase(), date);
        byte[] zip = httpBytes(url);
        if (zip == null) return null;
        List<String> lines = unzipCsv(zip);
        if (lines.isEmpty()) return null;

        List<long[]> out = new ArrayList<>(lines.size());
        for (String line : lines) {
            String[] p = line.split(",");
            if (p.length < 8) continue;
            long ts = parseCreateTime(p[0]);
            if (ts <= 0) continue;                                  // header / parse fail
            ts = OiMetricSets.normalize5m(ts);

            long[] row = new long[1 + OiMetricSets.ALL.length];
            row[0] = ts;
            for (int mIdx = 0; mIdx < OiMetricSets.ALL.length; mIdx++) {
                int col = OiMetricSets.ALL[mIdx].col;
                row[1 + mIdx] = parseFloatBits(col < p.length ? p[col] : "");
            }
            out.add(row);
        }
        return out;
    }

    /** Parse cột số → intBits của Float; Long.MIN_VALUE nếu trống/không-parse-được. */
    private static long parseFloatBits(String s) {
        if (s == null) return Long.MIN_VALUE;
        s = s.trim();
        if (s.isEmpty()) return Long.MIN_VALUE;
        try {
            return Float.floatToIntBits(Float.parseFloat(s));
        } catch (NumberFormatException e) {
            return Long.MIN_VALUE;
        }
    }

    /** Parse create_time: epoch (ms/sec) hoặc "yyyy-MM-dd HH:mm:ss" UTC → ms. -1 nếu hỏng (vd header). */
    static long parseCreateTime(String s) {
        if (s == null) return -1;
        s = s.trim();
        if (s.isEmpty()) return -1;
        if (s.matches("\\d{10,}")) {
            try {
                long v = Long.parseLong(s);
                if (s.length() <= 11) v *= 1000L;                   // giây → ms
                return v;
            } catch (NumberFormatException e) {
                return -1;
            }
        }
        try {
            return SDF_UTC.get().parse(s).getTime();
        } catch (Exception e) {
            return -1;                                              // header "create_time" rơi vào đây
        }
    }

    private static String httpText(String url) throws IOException {
        byte[] b = httpBytes(url);
        return b == null ? "" : new String(b, StandardCharsets.UTF_8);
    }

    /** GET bytes (retry nhẹ). null nếu 404. */
    static byte[] httpBytes(String url) throws IOException {
        IOException last = null;
        for (int attempt = 0; attempt < 3; attempt++) {
            try {
                HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
                c.setRequestProperty("User-Agent", "oi-backfill/1.0");
                c.setConnectTimeout(20000);
                c.setReadTimeout(120000);
                int code = c.getResponseCode();
                if (code == 404) return null;
                if (code != 200) throw new IOException("HTTP " + code);
                try (InputStream in = c.getInputStream(); ByteArrayOutputStream bo = new ByteArrayOutputStream()) {
                    byte[] buf = new byte[65536];
                    int n;
                    while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
                    return bo.toByteArray();
                }
            } catch (IOException e) {
                last = e;
                try {
                    Thread.sleep(500L * (attempt + 1));
                } catch (InterruptedException ignored) {
                    Thread.currentThread().interrupt();
                }
            }
        }
        throw last != null ? last : new IOException("tải thất bại: " + url);
    }

    private static List<String> unzipCsv(byte[] zip) throws IOException {
        List<String> lines = new ArrayList<>();
        try (ZipInputStream zis = new ZipInputStream(new ByteArrayInputStream(zip))) {
            ZipEntry e = zis.getNextEntry();
            if (e == null) return lines;
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            byte[] buf = new byte[65536];
            int n;
            while ((n = zis.read(buf)) > 0) bo.write(buf, 0, n);
            for (String l : bo.toString("UTF-8").split("\n")) {
                l = l.trim();
                if (!l.isEmpty()) lines.add(l);
            }
        }
        return lines;
    }

    /** Tiện ích: tổng số record (qua mọi metric, không trùng-lặp metric) cho 1 symbol — đếm theo OI (đại diện). */
    public static int totalTs(SymbolMetrics m) {
        TreeSet<Long> all = new TreeSet<>();
        for (Map<Long, Float> map : m.maps) all.addAll(map.keySet());
        return all.size();
    }
}
