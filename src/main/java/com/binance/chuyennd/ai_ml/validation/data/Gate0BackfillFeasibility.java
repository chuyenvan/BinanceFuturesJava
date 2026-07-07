package com.binance.chuyennd.ai_ml.validation.data;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * GATE 0 — feasibility backfill coin delist. QUYẾT ĐỊNH TẤT CẢ.
 *
 * <p>Kiểm 3 nguồn dữ liệu cho coin delist (LUNA/FTT/ANC) + 1 coin sống (BTC đối chứng), tại mốc
 * QUANH LÚC SẬP (LUNA 2022-05, FTT 2022-11):
 *   1. KLINE 1m       — data.binance.vision monthly/klines  (giá — nền ticker)
 *   2. METRICS (OI)   — data.binance.vision daily/metrics    (open interest — cho ExportFundingOiPerCoin)
 *   3. FUNDING RATE   — fapi/v1/fundingRate API              (funding — cho funding-selector)
 *
 * <p>Thuần HTTP read-only, KHÔNG đụng Aerospike/242/226. In rõ nguồn nào CÓ/THIẾU cho từng coin.
 * ĐỌC KẾT QUẢ:
 *   - Cả 3 nguồn CÓ cho coin delist → backfill KHẢ THI đầy đủ → đi tiếp.
 *   - Thiếu funding/OI của coin delist → funding-selector/feature vẫn mù → backfill KHÔNG trọn vẹn → CÂN NHẮC.
 *   - Thiếu cả kline → DỪNG (không dựng lại được gì).
 */
public class Gate0BackfillFeasibility {
    private static final Logger LOG = LoggerFactory.getLogger(Gate0BackfillFeasibility.class);
    private static final String FILE_BASE = "https://data.binance.vision";
    private static final String KLINE_PREFIX = "data/futures/um/monthly/klines/";
    private static final String METRICS_PREFIX = "data/futures/um/daily/metrics/";
    // funding: thử cả API fapi lẫn vision (nếu có)
    private static final String FAPI = "https://fapi.binance.com/fapi/v1/fundingRate";

    public static void main(String[] args) {
        // coin | mốc kiểm kline (yyyy,MM) | mốc metrics (yyyy-MM-dd) | funding window quanh sập (startMs,endMs)
        String[][] cases = {
            // LUNA sập 2022-05
            {"LUNAUSDT", "2022", "05", "2022-05-11", "1652140800000", "1652486400000"},
            // FTT sập 2022-11
            {"FTTUSDT", "2022", "11", "2022-11-09", "1667952000000", "1668211200000"},
            // ANC sập
            {"ANCUSDT", "2022", "05", "2022-05-11", "1652140800000", "1652486400000"},
            // BTC đối chứng (coin sống)
            {"BTCUSDT", "2022", "05", "2022-05-11", "1652140800000", "1652486400000"},
        };

        LOG.info("========== GATE 0 — FEASIBILITY BACKFILL COIN DELIST ==========");
        LOG.info(String.format("%-10s %-14s %-14s %-14s", "coin", "KLINE-1m", "METRICS-OI", "FUNDING-RATE"));
        int fullOk = 0;
        for (String[] c : cases) {
            String coin = c[0];
            boolean kline = checkKline(coin, c[1], c[2]);
            boolean metrics = checkMetrics(coin, c[3]);
            boolean funding = checkFunding(coin, Long.parseLong(c[4]), Long.parseLong(c[5]));
            LOG.info(String.format("%-10s %-14s %-14s %-14s", coin,
                    kline ? "CÓ" : "THIẾU", metrics ? "CÓ" : "THIẾU", funding ? "CÓ" : "THIẾU"));
            if (coin.startsWith("LUNA") || coin.startsWith("FTT") || coin.startsWith("ANC")) {
                if (kline && metrics && funding) fullOk++;
            }
        }
        LOG.info("========== KẾT LUẬN GATE 0 ==========");
        LOG.info("Coin delist có ĐỦ 3 nguồn: {}/3", fullOk);
        if (fullOk == 3) LOG.info("=> KHẢ THI ĐẦY ĐỦ: backfill được cả giá+OI+funding cho coin delist. ĐI TIẾP.");
        else if (fullOk >= 1) LOG.info("=> KHẢ THI MỘT PHẦN: một số coin/nguồn thiếu. Xem chi tiết dòng trên trước khi quyết.");
        else LOG.info("=> KHÔNG KHẢ THI hoặc thiếu nặng: cân nhắc DỪNG hoặc đổi nguồn.");
        System.exit(0);
    }

    /** KLINE monthly zip tồn tại? */
    private static boolean checkKline(String sym, String y, String mo) {
        String url = String.format("%s/%s%s/1m/%s-1m-%s-%s.zip", FILE_BASE, KLINE_PREFIX, sym, sym, y, mo);
        try {
            byte[] zip = httpBytes(url);
            if (zip == null) return false;
            int rows = countCsvRows(zip);
            LOG.info("   [{}] kline {}-{}: {} dòng", sym, y, mo, rows);
            return rows > 100;
        } catch (Exception e) { LOG.warn("   [{}] kline lỗi: {}", sym, e.getMessage()); return false; }
    }

    /** METRICS daily zip (OI) tồn tại? */
    private static boolean checkMetrics(String sym, String date) {
        String url = String.format("%s/%s%s/%s-metrics-%s.zip", FILE_BASE, METRICS_PREFIX, sym, sym, date);
        try {
            byte[] zip = httpBytes(url);
            if (zip == null) return false;
            int rows = countCsvRows(zip);
            LOG.info("   [{}] metrics {}: {} dòng (OI/LS/taker 5m)", sym, date, rows);
            return rows > 10;
        } catch (Exception e) { LOG.warn("   [{}] metrics lỗi: {}", sym, e.getMessage()); return false; }
    }

    /** FUNDING RATE qua fapi API trong window quanh sập? */
    private static boolean checkFunding(String sym, long startMs, long endMs) {
        String url = String.format("%s?symbol=%s&startTime=%d&endTime=%d&limit=1000", FAPI, sym, startMs, endMs);
        try {
            byte[] body = httpBytes(url);
            if (body == null) return false;
            String json = new String(body, StandardCharsets.UTF_8);
            // đếm số bản ghi funding (mỗi bản ghi có "fundingRate")
            int cnt = 0, idx = 0;
            while ((idx = json.indexOf("fundingRate", idx)) >= 0) { cnt++; idx += 11; }
            LOG.info("   [{}] funding API quanh sập: {} bản ghi", sym, cnt);
            return cnt > 0;
        } catch (Exception e) { LOG.warn("   [{}] funding lỗi: {}", sym, e.getMessage()); return false; }
    }

    private static int countCsvRows(byte[] zip) throws IOException {
        try (ZipInputStream zis = new ZipInputStream(new ByteArrayInputStream(zip))) {
            ZipEntry e = zis.getNextEntry();
            if (e == null) return 0;
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            byte[] buf = new byte[65536]; int n;
            while ((n = zis.read(buf)) > 0) bo.write(buf, 0, n);
            int rows = 0;
            for (String l : bo.toString("UTF-8").split("\n")) if (!l.trim().isEmpty()) rows++;
            return rows;
        }
    }

    private static byte[] httpBytes(String url) throws IOException {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setRequestProperty("User-Agent", "gate0-feasibility/1.0");
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
}
