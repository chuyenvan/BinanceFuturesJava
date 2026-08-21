package com.binance.chuyennd.websocket;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.research.oibackfill.OiMetricSets;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.BinanceRestGuard;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.client.constant.Constants;
import org.apache.commons.lang.StringUtils;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * TASK-035 - Forward ingest 5 metric OI/LS/taker (chunk-thang, dong schema voi history 013) -> 242.
 *
 * 5 metric (deu /futures/data/*, public, PER-SYMBOL vi KHONG co WebSocket/endpoint all-symbol):
 * OI (sumOpenInterestValue), top-trader account ratio, top-trader position ratio, global account ratio,
 * taker buy/sell ratio. Granularity goc 5m.
 *
 * Chu ky 30 phut (5 endpoint x ~554 symbol x throttle 250ms ~ 11-12 phut/sweep). Goi TUAN TU + throttle
 * + qua BinanceRestGuard (dung chung cooldown ban voi ticker/funding). Ghi chunk-thang SYMBOL_yyyyMM qua
 * writeMetricMap242 (merge-guard, KHONG de history).
 *
 * Canh giay: giay 0-12 da ban (TickerIngestor burst kline + entry/DCA giay 5-10) -> phan GHI Aerospike chi
 * chay tu giay 13 tro di (awaitWriteWindow). REST sweep khong dung Aerospike nen khong chan.
 *
 * Test: main("test") chay 1 vong cho vai symbol (mac dinh BTC/ETH/DOGE), in forward vs history de soi
 * BAC THANG don vi, ghi thu 226 (KHONG 242), verify. KHONG loop, KHONG dung live.
 */
public class OpenInterestIngestor2AerospikeNew {
    private static final Logger LOG = LoggerFactory.getLogger(OpenInterestIngestor2AerospikeNew.class);

    private static final String BASE = "https://fapi.binance.com/futures/data/";
    private static final long THROTTLE_MS = 250;
    private static final long FORWARD_INTERVAL_MS = 30 * 60 * 1000; // 30 phut
    private static final int WRITE_START_SEC = 13;                  // ne giay 0-12
    private static final int SWEEP_LIMIT = 8;                       // limit/call: phu >30 phut (6 diem 5m) + bien

    /** Anh xa metric -> endpoint -> field JSON (khop cot history 013 trong VisionMetricsClient). */
    private enum Ep {
        OI(OiMetricSets.OI, "openInterestHist", "sumOpenInterestValue"),
        LS_ACC(OiMetricSets.LS_TOPTRADER_ACC, "topLongShortAccountRatio", "longShortRatio"),
        LS_POS(OiMetricSets.LS_TOPTRADER_POS, "topLongShortPositionRatio", "longShortRatio"),
        LS_GLOBAL(OiMetricSets.LS_GLOBAL_ACC, "globalLongShortAccountRatio", "longShortRatio"),
        TAKER(OiMetricSets.TAKER_VOL, "takerlongshortRatio", "buySellRatio");
        final OiMetricSets.Metric m;
        final String path, field;
        Ep(OiMetricSets.Metric m, String path, String field) { this.m = m; this.path = path; this.field = field; }
    }

    public static void main(String[] args) {
        if (args.length > 0 && "test".equalsIgnoreCase(args[0])) {
            new OpenInterestIngestor2AerospikeNew().runTest(args);
            return;
        }
        new OpenInterestIngestor2AerospikeNew().start();
    }

    public void start() {
        LOG.info("===== [TASK-035] OI/LS/taker forward ingest | 5 endpoint (OI+LS+taker) | chunk-thang 242 | chu ky {}' | limit {} | ghi tu giay {} | qua BinanceRestGuard =====",
                FORWARD_INTERVAL_MS / 60000, SWEEP_LIMIT, WRITE_START_SEC);
        startForwardLoop();
        startOiFeatComputeLoop();
    }

    /**
     * [OI-FEAT] Tính oi_feat_* (5 feature selector: oiDelta24h, oiZ, lsGlobal, lsToptrader, takerBuy) NGAY TRÊN 242
     * mỗi {@link #FORWARD_INTERVAL_MS} (30'), đọc 226-full ∪ 242-fresh (242→226:3222 open) → giữ oi_feat_* tươi cho
     * {@code LiveOiFeatProvider} (bỏ phụ thuộc job Oracle thủ công). Logic EXACT = {@code ComputeOiFeat2Live242.runOnce}
     * (per-coin 1 lúc → không OOM box live). Rolling push {@code OI_FEAT_ROLL_DAYS} ngày (default 2, đủ tươi cho tol 2h).
     * Delay đầu {@code OI_FEAT_INIT_DELAY_MS} (default 5') để forward sweep ghi raw OI trước.
     */
    private void startOiFeatComputeLoop() {
        final int rollDays = envInt("OI_FEAT_ROLL_DAYS", 2);
        final long initDelay = envLong("OI_FEAT_INIT_DELAY_MS", 5 * 60_000L);
        // Cadence 60' (đo dry-run: ~29'/881 coin đọc 226-full). 60' << tol 2h của LiveOiFeatProvider → luôn tươi,
        // giảm nửa tải mạng 242→226 so với 30'. Tune qua env OI_FEAT_INTERVAL_MS nếu cần.
        final long intervalMs = envLong("OI_FEAT_INTERVAL_MS", 60 * 60_000L);
        new Thread(() -> {
            Thread.currentThread().setName("OI-Feat-Compute-Loop");
            LOG.info("===== [OI-FEAT] compute oi_feat_* tren 242 | chu ky {}' | rolling {}d | delay dau {}s =====",
                    intervalMs / 60000, rollDays, initDelay / 1000);
            try { Thread.sleep(initDelay); } catch (InterruptedException ignored) { }
            while (true) {
                long t0 = System.currentTimeMillis();
                try {
                    com.binance.chuyennd.research.oibackfill.ComputeOiFeat2Live242.runOnce(rollDays, false);
                    LOG.info("[OI-FEAT] compute xong trong {}ms", System.currentTimeMillis() - t0);
                } catch (Throwable e) {
                    LOG.error("[OI-FEAT] compute loi (bo qua vong nay): {}", e.getMessage(), e);
                }
                long sleep = intervalMs - (System.currentTimeMillis() - t0);
                if (sleep < 60_000L) sleep = 60_000L;
                try { Thread.sleep(sleep); } catch (InterruptedException ignored) { }
            }
        }).start();
    }

    private static int envInt(String k, int d) {
        String v = System.getenv(k);
        try { return v == null ? d : Integer.parseInt(v.trim()); } catch (Exception e) { return d; }
    }

    private static long envLong(String k, long d) {
        String v = System.getenv(k);
        try { return v == null ? d : Long.parseLong(v.trim()); } catch (Exception e) { return d; }
    }

    private List<String> collectSymbols() {
        List<String> symbols = new ArrayList<>();
        Set<String> redisData = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
        for (String s : redisData) {
            String up = s.toUpperCase();
            if (!Constants.diedSymbol.contains(up) && up.endsWith("USDT") && up.matches("^[A-Z0-9]+$")) {
                symbols.add(up);
            }
        }
        return symbols;
    }

    private void startForwardLoop() {
        new Thread(() -> {
            Thread.currentThread().setName("OI-Metrics-Forward-Loop");
            int idle = 0;
            while (true) {
                long sweepStart = System.currentTimeMillis();
                try {
                    List<String> symbols = collectSymbols();
                    Map<OiMetricSets.Metric, Map<String, Map<Long, Float>>> buffer = new LinkedHashMap<>();
                    boolean banned = false;
                    for (String symbol : symbols) {
                        if (banned) break;
                        for (Ep ep : Ep.values()) {
                            try {
                                if (BinanceRestGuard.awaitIfBanned(60_000L)) { banned = true; break; }
                                String url = BASE + ep.path + "?symbol=" + symbol + "&period=5m&limit=" + SWEEP_LIMIT;
                                String resp = HttpRequest.getContentFromUrl(url, 5000);
                                BinanceRestGuard.reportBan(resp);
                                if (BinanceRestGuard.isBanned()) { banned = true; break; }
                                Map<Long, Float> pts = parseAll(resp, ep.field);
                                if (!pts.isEmpty()) {
                                    buffer.computeIfAbsent(ep.m, k -> new LinkedHashMap<>())
                                          .computeIfAbsent(symbol, k -> new HashMap<>())
                                          .putAll(pts);
                                }
                                Thread.sleep(THROTTLE_MS);
                            } catch (Exception e) {
                                LOG.warn("forward bo qua {}/{} (loi tam): {}", symbol, ep.path, e.getMessage());
                            }
                        }
                    }
                    int written = flush(buffer);
                    if (written > 0) { idle = 0; LOG.info("OI/LS/taker forward: ghi {} (symbol x metric) / {} symbol.", written, symbols.size()); }
                    else if (++idle % 4 == 0) LOG.info("OI/LS/taker forward song (chua ghi gi, idle={}).", idle);
                } catch (Exception e) {
                    LOG.error("OI/LS/taker sweep loi: {}", e.getMessage(), e);
                }
                long sleep = FORWARD_INTERVAL_MS - (System.currentTimeMillis() - sweepStart);
                if (sleep < 1000) sleep = 1000;
                try { Thread.sleep(sleep); } catch (InterruptedException ignored) { }
            }
        }).start();
    }

    /** Flush buffer ra 242, CANH GIAY tranh khung entry/DCA. */
    private int flush(Map<OiMetricSets.Metric, Map<String, Map<Long, Float>>> buffer) {
        int written = 0;
        for (Map.Entry<OiMetricSets.Metric, Map<String, Map<Long, Float>>> me : buffer.entrySet()) {
            OiMetricSets.Metric m = me.getKey();
            for (Map.Entry<String, Map<Long, Float>> se : me.getValue().entrySet()) {
                try {
                    awaitWriteWindow();
                    int err = DataManagerAerospikeFloatSim.writeMetricMap242(m.set, m.bin, se.getKey(), se.getValue());
                    if (err == 0) written++;
                    else LOG.warn("ghi chunk-thang loi {} chunk: {} {}", err, m.set, se.getKey());
                } catch (Exception e) {
                    LOG.warn("flush loi {} {}: {}", m.set, se.getKey(), e.getMessage());
                }
            }
        }
        return written;
    }

    /** Ne giay 0-12: chi cho ghi tu giay 13 tro di moi phut. */
    private void awaitWriteWindow() throws InterruptedException {
        int sec = (int) ((System.currentTimeMillis() % 60_000L) / 1000L);
        if (sec < WRITE_START_SEC) Thread.sleep((WRITE_START_SEC - sec) * 1000L + 50L);
    }

    /** Parse TAT CA diem trong mang (giu du do phan giai 5m). */
    private Map<Long, Float> parseAll(String resp, String field) {
        Map<Long, Float> out = new HashMap<>();
        if (StringUtils.isBlank(resp) || !resp.trim().startsWith("[")) return out;
        JSONArray arr = new JSONArray(resp);
        for (int i = 0; i < arr.length(); i++) {
            JSONObject o = arr.getJSONObject(i);
            float v = (float) o.getDouble(field);
            // Bo diem rac: symbol thanh khoan thap (short≈0) -> longShortRatio = Infinity/NaN,
            // Aerospike reject "Infinity is not a valid double" lam hong CA writeMonthChunk.
            // Skip diem loi de phan con lai cua chunk van ghi duoc (gap nho hon la mat ca chunk).
            if (Float.isNaN(v) || Float.isInfinite(v)) continue;
            out.put(o.getLong("timestamp"), v);
        }
        return out;
    }

    // ===================== TEST MODE (khong loop, ghi 226) =====================
    private void runTest(String[] args) {
        List<String> syms = args.length > 1 ? Arrays.asList(Arrays.copyOfRange(args, 1, args.length))
                                            : Arrays.asList("BTCUSDT", "ETHUSDT", "DOGEUSDT");
        LOG.info("TEST forward 5 metric cho {} (poll Binance, so history 226, ghi thu 226, KHONG 242).", syms);
        for (String symbol : syms) {
            for (Ep ep : Ep.values()) {
                try {
                    String url = BASE + ep.path + "?symbol=" + symbol + "&period=5m&limit=" + SWEEP_LIMIT;
                    String resp = HttpRequest.getContentFromUrl(url, 5000);
                    TreeMap<Long, Float> pts = new TreeMap<>(parseAll(resp, ep.field));
                    if (pts.isEmpty()) { LOG.warn("  {} {}: KHONG parse duoc resp", symbol, ep.m.set); continue; }
                    Map.Entry<Long, Float> fwd = pts.lastEntry();
                    TreeMap<Long, Float> hist = DataManagerAerospikeFloatSim.getMetricMap226(ep.m.set, ep.m.bin, symbol);
                    String cmp;
                    if (hist.isEmpty()) {
                        cmp = "history RONG";
                    } else {
                        float hv = hist.lastEntry().getValue();
                        double ratio = hv == 0 ? -1 : fwd.getValue() / hv;
                        boolean step = ratio > 0 && (ratio > 10 || ratio < 0.1);
                        cmp = String.format("history_last(ts=%d val=%.6f) ratio=%.3f %s",
                                hist.lastKey(), hv, ratio, step ? "LECH CO (nghi bac thang!)" : "ok co");
                    }
                    LOG.info("  {} {}: forward {} diem, newest(ts={} val={}) | {}", symbol, ep.m.set, pts.size(), fwd.getKey(), fwd.getValue(), cmp);
                    int err = DataManagerAerospikeFloatSim.writeMetricMap226(ep.m.set, ep.m.bin, symbol, pts);
                    Float back = DataManagerAerospikeFloatSim.getMetricMap226(ep.m.set, ep.m.bin, symbol).get(fwd.getKey());
                    LOG.info("     ghi226 err={} verify={}", err, (back != null && Math.abs(back - fwd.getValue()) < 1e-6) ? "OK" : "FAIL");
                    Thread.sleep(THROTTLE_MS);
                } catch (Exception e) {
                    LOG.warn("  {} {}: loi {}", symbol, ep.m.set, e.getMessage());
                }
            }
        }
        LOG.info("TEST xong.");
    }
}
