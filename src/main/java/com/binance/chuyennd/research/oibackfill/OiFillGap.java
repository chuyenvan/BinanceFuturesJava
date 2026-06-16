package com.binance.chuyennd.research.oibackfill;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
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
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * TASK-035 - FILL-GAP mot lan: lap khoang trong 5 metric OI/LS/taker tu moc cuoi history (T-1, backfill 013)
 * den luc forward moi bat dau chay lien tuc. Voi moi (symbol song x metric): doc lastKey hien co tren target
 * -> keo REST /futures/data/* (period=5m, limit=500, phan trang startTime) tu sau lastKey toi hien tai ->
 * ghi chunk-thang (writeMetricMap, merge-guard, idempotent).
 *
 * <p>Chay SAU khi deploy ingest moi (de biet forward da chay tu dau). Idempotent: chong lan voi forward vo hai.
 *
 * <p>Args: [226|242 (mac dinh 242)] [run] [SYMBOL...]. Khong co "run" -> DRY-RUN (chi in). Khong liet ke symbol
 * -> lay toan bo coin song tu Redis. Chay tren noi co Binance-out + Aerospike target (live server cho 242).
 */
public class OiFillGap {
    private static final Logger LOG = LoggerFactory.getLogger(OiFillGap.class);
    private static final String BASE = "https://fapi.binance.com/futures/data/";
    private static final long THROTTLE_MS = 250;
    private static final int PAGE_LIMIT = 500;          // max Binance /futures/data/*
    private static final int MAX_PAGES = 30;            // ~30 x 41h, du cho gap rat dai
    private static final long FIVE_MIN = 5 * 60_000L;
    private static final long DEFAULT_BACKFILL_MS = 3 * 24 * 60 * 60_000L; // neu chua co data: fill 3 ngay

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
        String target = "242";
        boolean run = false;
        List<String> explicit = new ArrayList<>();
        for (String a : args) {
            if ("226".equals(a) || "242".equals(a)) target = a;
            else if ("run".equalsIgnoreCase(a)) run = true;
            else if (a.toUpperCase().matches("^[A-Z0-9]+USDT$")) explicit.add(a.toUpperCase());
        }
        new OiFillGap().run(target, run, explicit);
        System.exit(0);
    }

    private void run(String target, boolean doRun, List<String> explicit) {
        boolean is226 = "226".equals(target);
        List<String> symbols = explicit.isEmpty() ? collectSymbols() : explicit;
        LOG.info("===== [TASK-035] FILL-GAP target={} mode={} symbols={} =====",
                target, doRun ? "RUN" : "DRY-RUN", symbols.size());
        long now = System.currentTimeMillis();
        long totalFilled = 0;
        int touched = 0;
        boolean banned = false;
        for (String symbol : symbols) {
            if (banned) break;
            for (Ep ep : Ep.values()) {
                try {
                    if (BinanceRestGuard.awaitIfBanned(60_000L)) { banned = true; break; }
                    TreeMap<Long, Float> existing = getMetric(is226, ep, symbol);
                    long startTime = existing.isEmpty() ? now - DEFAULT_BACKFILL_MS : existing.lastKey() + 1;
                    if (startTime >= now - FIVE_MIN) continue; // khong gap dang ke

                    TreeMap<Long, Float> gap = new TreeMap<>();
                    int pages = 0;
                    while (startTime < now - FIVE_MIN && pages < MAX_PAGES) {
                        String url = BASE + ep.path + "?symbol=" + symbol + "&period=5m&limit=" + PAGE_LIMIT + "&startTime=" + startTime;
                        String resp = HttpRequest.getContentFromUrl(url, 8000);
                        BinanceRestGuard.reportBan(resp);
                        if (BinanceRestGuard.isBanned()) { banned = true; break; }
                        Map<Long, Float> batch = parseAll(resp, ep.field);
                        if (batch.isEmpty()) break;
                        gap.putAll(batch);
                        long maxTs = Collections.max(batch.keySet());
                        if (maxTs < startTime) break;       // khong tien -> dung
                        startTime = maxTs + 1;
                        pages++;
                        Thread.sleep(THROTTLE_MS);
                    }
                    if (gap.isEmpty()) continue;

                    if (doRun) {
                        int err = writeMetric(is226, ep, symbol, gap);
                        if (err == 0) { totalFilled += gap.size(); touched++; }
                        LOG.info("{} {}: fill {} diem [{}..{}] err={}", symbol, ep.m.set, gap.size(), gap.firstKey(), gap.lastKey(), err);
                    } else {
                        LOG.info("[DRY] {} {}: se fill {} diem [{}..{}]", symbol, ep.m.set, gap.size(), gap.firstKey(), gap.lastKey());
                    }
                    Thread.sleep(THROTTLE_MS);
                } catch (Exception e) {
                    LOG.warn("fill-gap bo qua {}/{}: {}", symbol, ep.path, e.getMessage());
                }
            }
        }
        LOG.info("===== FILL-GAP xong: {} (symbol x metric) co data, tong {} diem (mode={}) =====",
                touched, totalFilled, doRun ? "RUN" : "DRY-RUN");
    }

    private TreeMap<Long, Float> getMetric(boolean is226, Ep ep, String symbol) {
        return is226 ? DataManagerAerospikeFloatSim.getMetricMap226(ep.m.set, ep.m.bin, symbol)
                     : DataManagerAerospikeFloatSim.getMetricMap242(ep.m.set, ep.m.bin, symbol);
    }

    private int writeMetric(boolean is226, Ep ep, String symbol, Map<Long, Float> map) {
        return is226 ? DataManagerAerospikeFloatSim.writeMetricMap226(ep.m.set, ep.m.bin, symbol, map)
                     : DataManagerAerospikeFloatSim.writeMetricMap242(ep.m.set, ep.m.bin, symbol, map);
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

    private Map<Long, Float> parseAll(String resp, String field) {
        Map<Long, Float> out = new HashMap<>();
        if (StringUtils.isBlank(resp) || !resp.trim().startsWith("[")) return out;
        JSONArray arr = new JSONArray(resp);
        for (int i = 0; i < arr.length(); i++) {
            JSONObject o = arr.getJSONObject(i);
            out.put(o.getLong("timestamp"), (float) o.getDouble(field));
        }
        return out;
    }
}
