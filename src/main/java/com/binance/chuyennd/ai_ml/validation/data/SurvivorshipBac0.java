package com.binance.chuyennd.ai_ml.validation.data;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * TASK-001 — Bậc-0: chốt bằng số mức survivorship-do-THIẾU-SYMBOL.
 *
 * Java thuần (java.net + zip), KHÔNG đụng Aerospike/Configs/engine. Đọc coverage THẬT (TASK-002) trừ
 * universe data.vision → tập symbol USDT-perp TỪNG tồn tại mà dataset THIẾU HOÀN TOÀN. Cổng quyết:
 *   - rỗng/nhỏ & không coin nào thanh khoản đáng kể → KẾT LUẬN không cần full backfill.
 *   - đáng kể → tải klines monthly 1m từng symbol thiếu, đo sập, xuất CSV + summary.
 *
 * Lọc (cả universe lẫn coverage): đuôi USDT, KHÔNG '_', KHÔNG chứa 'USDC', KHÔNG 'BTCDOMUSDT'.
 * Chạy trên 226 (đọc outputs/aerospike_coverage.csv cùng máy + có internet). Log SLF4J, không System.out.
 */
public class SurvivorshipBac0 {

    private static final Logger LOG = LoggerFactory.getLogger(SurvivorshipBac0.class);

    private static final String S3_LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision";
    private static final String FILE_BASE = "https://data.binance.vision";
    private static final String PREFIX = "data/futures/um/monthly/klines/";
    private static final String COVERAGE_CSV = "outputs/aerospike_coverage.csv";
    private static final String OUT_CSV = "outputs/survivorship_missing_symbols.csv";
    private static final int START_YEAR = 2021, START_MONTH = 1;
    // Ngưỡng "thanh khoản đáng kể" để cổng quyết (avg quote-volume/phút, USDT). Coin thiếu mà QV dưới mức
    // này coi như rác (không trade được) → không kéo vào survivorship.
    private static final double LIQUID_QV = 50_000.0;

    private static final Pattern CP = Pattern.compile("<CommonPrefixes><Prefix>(.*?)</Prefix></CommonPrefixes>");
    private static final Pattern NEXT = Pattern.compile("<NextMarker>(.*?)</NextMarker>");

    public static void main(String[] args) {
        try { new SurvivorshipBac0().run(); }
        catch (Exception e) { LOG.error("❌ SurvivorshipBac0 lỗi", e); }
        System.exit(0);
    }

    private static boolean keep(String s) {
        return s != null && s.endsWith("USDT") && !s.contains("_") && !s.contains("USDC") && !s.equals("BTCDOMUSDT");
    }

    public void run() throws Exception {
        // 1. coverage (THẬT, từ TASK-002)
        File cov = new File(COVERAGE_CSV);
        if (!cov.exists()) {
            LOG.error("⛔ Không thấy {} (cần TASK-002 chạy cùng máy/đường dẫn). DỪNG, KHÔNG bịa.", cov.getAbsolutePath());
            return;
        }
        Set<String> coverage = new TreeSet<>();
        int covRaw = 0;
        try (BufferedReader br = new BufferedReader(new InputStreamReader(new FileInputStream(cov), StandardCharsets.UTF_8))) {
            String line = br.readLine(); // header
            while ((line = br.readLine()) != null) {
                if (line.isEmpty()) continue;
                covRaw++;
                String sym = line.split(",", 2)[0].trim();
                if (keep(sym)) coverage.add(sym);
            }
        }
        LOG.info("📄 coverage.csv: {} dòng → {} symbol USDT-perp (sau lọc USDC/BTCDOM/_)", covRaw, coverage.size());

        // 2. universe data.vision (paginated S3-XML)
        Set<String> universe = listUniverse();
        LOG.info("🌐 universe data.vision: {} symbol USDT-perp (sau lọc)", universe.size());

        // 3. tập thiếu hoàn toàn = universe − coverage
        List<String> missing = new ArrayList<>();
        for (String s : universe) if (!coverage.contains(s)) missing.add(s);
        Collections.sort(missing);
        LOG.info("🎯 TẬP THIẾU HOÀN TOÀN (universe − coverage) = {} symbol", missing.size());
        if (!missing.isEmpty()) LOG.info("    {}", String.join(", ", missing));
        // tham khảo chiều ngược: coverage có mà universe-monthly không (đổi tên / ngoài um-monthly)
        int covOnly = 0;
        for (String s : coverage) if (!universe.contains(s)) covOnly++;
        LOG.info("    (tham khảo: coverage-only, không có trong universe-monthly = {})", covOnly);

        // 4. CỔNG QUYẾT
        if (missing.isEmpty()) {
            LOG.info("✅ KẾT LUẬN: tập thiếu RỖNG → survivorship-do-thiếu-symbol = 0. KHÔNG cần full backfill (bỏ TASK-003/004).");
            return;
        }

        // tập thiếu KHÔNG rỗng → tải klines + đo, để quyết bằng số (thường ít symbol → nhẹ)
        LOG.info("⬇️ Tập thiếu {} symbol → tải klines monthly 1m phân tích...", missing.size());
        new File(OUT_CSV).getParentFile().mkdirs();
        List<Map<String, Object>> rows = new ArrayList<>();
        for (int i = 0; i < missing.size(); i++) {
            Map<String, Object> r = analyze(missing.get(i));
            if (r != null) rows.add(r);
            LOG.info("    [{}/{}] {} {}", i + 1, missing.size(), missing.get(i), r == null ? "(không có klines)" : "ok");
        }

        // xuất CSV
        String[] cols = {"symbol", "firstDate", "lastDate", "daysAlive", "firstOpen", "maxClose",
                "minClose", "lastClose", "drawdownToBottom", "diedNearZero", "avgQuoteVolume"};
        try (BufferedWriter w = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(OUT_CSV), StandardCharsets.UTF_8))) {
            w.write(String.join(",", cols)); w.newLine();
            for (Map<String, Object> r : rows) {
                StringBuilder sb = new StringBuilder();
                for (int c = 0; c < cols.length; c++) { if (c > 0) sb.append(","); sb.append(r.get(cols[c])); }
                w.write(sb.toString()); w.newLine();
            }
        }

        // summary + kết luận bằng số
        int died = 0, liquid = 0;
        double sumDd = 0;
        List<Map<String, Object>> liquidDied = new ArrayList<>();
        for (Map<String, Object> r : rows) {
            if ((boolean) r.get("diedNearZero")) died++;
            double qv = (double) r.get("avgQuoteVolume");
            if (qv >= LIQUID_QV) { liquid++; if ((boolean) r.get("diedNearZero")) liquidDied.add(r); }
            sumDd += (double) r.get("drawdownToBottom");
        }
        rows.sort((a, b) -> Double.compare((double) a.get("drawdownToBottom"), (double) b.get("drawdownToBottom")));
        LOG.info("📊 SUMMARY tập thiếu: có klines={} | diedNearZero={} | thanh-khoản≥{}USDT/phút={} | drawdown TB={}%",
                rows.size(), died, (long) LIQUID_QV, liquid, rows.isEmpty() ? "-" : String.format(Locale.US, "%.1f", sumDd / rows.size() * 100));
        LOG.info("   10 coin thiếu sập nặng nhất:");
        for (int i = 0; i < Math.min(10, rows.size()); i++) {
            Map<String, Object> r = rows.get(i);
            LOG.info("     {} dd={}% died={} avgQV={} alive={}d",
                    r.get("symbol"), String.format(Locale.US, "%.1f", (double) r.get("drawdownToBottom") * 100),
                    r.get("diedNearZero"), String.format(Locale.US, "%.0f", (double) r.get("avgQuoteVolume")), r.get("daysAlive"));
        }
        if (liquid == 0) {
            LOG.info("✅ KẾT LUẬN: tập thiếu {} symbol nhưng KHÔNG coin nào thanh khoản đáng kể (≥{}USDT/phút) → bot không trade được chúng → survivorship NHẸ, KHÔNG cần full backfill.",
                    missing.size(), (long) LIQUID_QV);
        } else {
            LOG.info("⚠️ KẾT LUẬN: có {} coin thiếu CÓ thanh khoản (trong đó {} sập-gần-0) → survivorship CÓ THỂ ĐÁNG KỂ → cân nhắc TASK-003/004 backfill. Xem {}.",
                    liquid, liquidDied.size(), OUT_CSV);
        }
    }

    /** Parse listing S3-XML có phân trang → mọi symbol USDT-perp (đã lọc). */
    private Set<String> listUniverse() throws IOException {
        Set<String> out = new TreeSet<>();
        String marker = "";
        int pages = 0;
        while (true) {
            String url = S3_LIST + "?delimiter=/&prefix=" + PREFIX;
            if (!marker.isEmpty()) url += "&marker=" + URLEncoder.encode(marker, "UTF-8");
            String xml = httpText(url);
            pages++;
            String lastSeg = null;
            Matcher m = CP.matcher(xml);
            while (m.find()) {
                String p = m.group(1);
                String seg = p.replaceAll("/+$", "");
                seg = seg.substring(seg.lastIndexOf('/') + 1);
                lastSeg = p;
                if (keep(seg)) out.add(seg);
            }
            if (!xml.contains("<IsTruncated>true</IsTruncated>")) break;
            Matcher nm = NEXT.matcher(xml);
            if (nm.find() && !nm.group(1).isEmpty()) marker = nm.group(1);
            else if (lastSeg != null) marker = lastSeg;
            else break;
            if (pages > 50) { LOG.warn("⚠️ >50 trang listing — dừng phòng loop."); break; }
        }
        return out;
    }

    /** Tải klines monthly 1m 2021→nay cho 1 symbol, gom chỉ số O(1). null nếu không có klines nào. */
    private Map<String, Object> analyze(String sym) {
        Calendar now = Calendar.getInstance();
        int endY = now.get(Calendar.YEAR), endM = now.get(Calendar.MONTH) + 1;
        Long firstT = null, lastT = null;
        double firstOpen = 0, lastClose = 0, maxClose = Double.NEGATIVE_INFINITY, minClose = Double.POSITIVE_INFINITY;
        double qvSum = 0; long qvCnt = 0;
        boolean got = false;
        int y = START_YEAR, mo = START_MONTH;
        while (y < endY || (y == endY && mo <= endM)) {
            String url = String.format("%s/%s%s/1m/%s-1m-%04d-%02d.zip", FILE_BASE, PREFIX, sym, sym, y, mo);
            byte[] zip;
            try { zip = httpBytes(url); }
            catch (Exception e) { LOG.warn("    {} {}-{}: lỗi tải {}", sym, y, mo, e.getMessage()); zip = null; }
            if (zip != null) {
                try {
                    for (String line : unzipCsv(zip)) {
                        String[] p = line.split(",");
                        if (p.length < 8) continue;
                        long ot; double o, c, qv;
                        try { ot = (long) Double.parseDouble(p[0]); o = Double.parseDouble(p[1]); c = Double.parseDouble(p[4]); qv = Double.parseDouble(p[7]); }
                        catch (NumberFormatException nf) { continue; } // header
                        got = true;
                        if (firstT == null || ot < firstT) { firstT = ot; firstOpen = o; }
                        if (lastT == null || ot > lastT) { lastT = ot; lastClose = c; }
                        if (c > maxClose) maxClose = c;
                        if (c < minClose) minClose = c;
                        qvSum += qv; qvCnt++;
                    }
                } catch (Exception e) { LOG.warn("    {} {}-{}: unzip lỗi {}", sym, y, mo, e.getMessage()); }
            }
            mo++; if (mo > 12) { mo = 1; y++; }
        }
        if (!got) return null;
        Map<String, Object> r = new HashMap<>();
        r.put("symbol", sym);
        r.put("firstDate", dateOf(firstT));
        r.put("lastDate", dateOf(lastT));
        r.put("daysAlive", Math.max(1, (int) ((lastT - firstT) / 86400000L) + 1));
        r.put("firstOpen", firstOpen);
        r.put("maxClose", maxClose);
        r.put("minClose", minClose);
        r.put("lastClose", lastClose);
        r.put("drawdownToBottom", firstOpen != 0 ? (minClose / firstOpen - 1.0) : 0.0);
        r.put("diedNearZero", maxClose > 0 && lastClose / maxClose < 0.1);
        r.put("avgQuoteVolume", qvCnt > 0 ? qvSum / qvCnt : 0.0);
        return r;
    }

    private static String dateOf(long ms) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(ms);
        return String.format(Locale.US, "%04d-%02d-%02d", c.get(Calendar.YEAR), c.get(Calendar.MONTH) + 1, c.get(Calendar.DAY_OF_MONTH));
    }

    private static String httpText(String url) throws IOException {
        byte[] b = httpBytes(url);
        return b == null ? "" : new String(b, StandardCharsets.UTF_8);
    }

    /** GET bytes. null nếu 404 (klines chưa sinh/đã chết). */
    private static byte[] httpBytes(String url) throws IOException {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setRequestProperty("User-Agent", "survivorship-bac0/1.0");
        c.setConnectTimeout(20000); c.setReadTimeout(120000);
        int code = c.getResponseCode();
        if (code == 404) return null;
        if (code != 200) throw new IOException("HTTP " + code);
        try (InputStream in = c.getInputStream(); ByteArrayOutputStream bo = new ByteArrayOutputStream()) {
            byte[] buf = new byte[65536]; int n;
            while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
            return bo.toByteArray();
        }
    }

    private static List<String> unzipCsv(byte[] zip) throws IOException {
        List<String> lines = new ArrayList<>();
        try (ZipInputStream zis = new ZipInputStream(new ByteArrayInputStream(zip))) {
            ZipEntry e = zis.getNextEntry();
            if (e == null) return lines;
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            byte[] buf = new byte[65536]; int n;
            while ((n = zis.read(buf)) > 0) bo.write(buf, 0, n);
            for (String l : bo.toString("UTF-8").split("\n")) {
                l = l.trim();
                if (!l.isEmpty()) lines.add(l);
            }
        }
        return lines;
    }
}
