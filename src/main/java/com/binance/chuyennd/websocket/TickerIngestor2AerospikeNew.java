package com.binance.chuyennd.websocket;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.BinanceRestGuard;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.apache.commons.lang.StringUtils;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.*;

public class TickerIngestor2AerospikeNew {
    public static final Logger LOG = LoggerFactory.getLogger(TickerIngestor2AerospikeNew.class);
    // 🔒 Chống vòng-lặp-giữ-ban (TASK-007 A): cooldown GLOBAL theo IP nằm ở utils/BinanceRestGuard
    // (dùng chung với funding/OI ingester — ban theo IP nên KHÔNG để mỗi class một biến).

    private final ConcurrentHashMap<Long, ConcurrentHashMap<String, KlineObjectOptimized>> timeBuffer = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Float> priceBuffer = new ConcurrentHashMap<>();
    private final Set<String> globalSubscribedSymbols = Collections.newSetFromMap(new ConcurrentHashMap<>());

    private final ExecutorService restFetchService = Executors.newFixedThreadPool(15);
    private final ExecutorService repairService = Executors.newSingleThreadExecutor();
    // 🔧 #5: MỘT pool dùng chung cho fetch kline (trước đây new ForkJoinPool(30) MỖI batch → ~37 pool/phút,
    // lồng trong restFetchService(15) → đỉnh 15×30=450 luồng). Pool sống suốt vòng đời ingest (P1 long-running).
    private final java.util.concurrent.ForkJoinPool klineFetchPool = new java.util.concurrent.ForkJoinPool(30);

    // ===== [KFIX 2026-10-10] chot nen 1m = ban CUOI cua san (docs/runbooks/KLINE_FIX_242.md, audit KLINE_242_DIVERGENCE) =====
    // KLINE_INGEST_MODE: ws_settle (mac dinh: WS x=true + REST som cho symbol thieu + REST settle ghi de neu khac)
    //                    rest_settle (khong WS: REST som giay 2 cho moi symbol + REST settle)
    //                    legacy (V8.1 y nguyen — ROLLBACK khong can doi jar)
    static final String MODE_LEGACY = "legacy", MODE_REST = "rest_settle", MODE_WS = "ws_settle";
    static final String MODE = normMode(com.binance.chuyennd.tradecore.Cfg.getOr("KLINE_INGEST_MODE", MODE_WS));
    static final long WS_FLUSH_MS = cfgLong("KLINE_WS_FLUSH_MS", 1500);
    /** REST som cho symbol THIEU WS final. Do 2026-10-10 (/market, 30 sym x 8 phut): x=true toi p50 0,52 s nhung ~22% symbol
     *  (it giao dich) toi o ~3,04 s moi phut, 0 sau 3,5 s => ws_settle mac dinh 4 s (WS suy giam >50% thieu o giay 2 => REST ngay);
     *  rest_settle mac dinh 2 s (nhu V8.1). Ca hai xong truoc khi live doc o giay 6. */
    static final long EARLY_REST_SEC = cfgLong("KLINE_EARLY_REST_SEC", MODE_REST.equals(MODE) ? 2 : 4);
    static final long SETTLE_SEC = cfgLong("KLINE_SETTLE_SEC", 30);
    static final long SETTLE_MIN_AGE_SEC = cfgLong("KLINE_SETTLE_MIN_AGE_SEC", 20);
    static final int SETTLE_LIMIT = (int) cfgLong("KLINE_SETTLE_LIMIT", 3);
    /** Pass settle DAU TIEN sau khi start: limit lon (weight van 1 khi < 100) => lap lo phut trong luc dung/restart 12h. */
    static final int SETTLE_LIMIT_STARTUP = (int) cfgLong("KLINE_SETTLE_LIMIT_STARTUP", 30);
    static final int REST_RETRY = (int) cfgLong("KLINE_REST_RETRY", 2);
    static final int WS_STREAMS_PER_CONN = (int) cfgLong("KLINE_WS_STREAMS_PER_CONN", 150);
    static final long STATS_MIN = cfgLong("KLINE_STATS_MIN", 10);
    private final ExecutorService klineRestPool = Executors.newFixedThreadPool(30);
    private final KlineIngestCore core = new KlineIngestCore(new AerospikeMinuteStore(), this::restKlines, klineRestPool,
            REST_RETRY, 300L, SETTLE_MIN_AGE_SEC * 1000L, 15_000L);
    private volatile KlineWsClient wsClient;
    private volatile int lastRestCalls = 0;

    /** Store prod: doc record phut (key yyyyMMdd-HHmm, cung dinh dang writeMinuteBatch) + ghi merge theo symbol. */
    static final class AerospikeMinuteStore implements KlineIngestCore.MinuteStore {
        @Override
        public Map<String, KlineObjectOptimized> read(long minute) {
            String k = new java.text.SimpleDateFormat("yyyyMMdd-HHmm").format(new Date(minute));
            return DataManagerAerospikeFloatSim.getExistingTickersMap(new com.aerospike.client.Key(
                    Configs.AEROSPIKE_NAMESPACE, DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_TICKER, k));
        }

        @Override
        public void write(long minute, Map<String, KlineObjectOptimized> candles) {
            DataManagerAerospikeFloatSim.writeMinuteBatch(minute, candles);
        }
    }

    public void start() {
        LOG.info("🚀 TickerIngestor V8.1 (HYBRID REALTIME - KHẮC PHỤC TRỄ 1 PHÚT) Started! [KLINE-INGEST] mode={} "
                + "wsFlushMs={} earlyRestSec={} settleSec={} settleMinAgeSec={} settleLimit={} startupLimit={} retry={} streamsPerConn={}",
                MODE, WS_FLUSH_MS, EARLY_REST_SEC, SETTLE_SEC, SETTLE_MIN_AGE_SEC, SETTLE_LIMIT, SETTLE_LIMIT_STARTUP, REST_RETRY, WS_STREAMS_PER_CONN);

        List<String> symbols = collectSymbolsFromRedis();
        globalSubscribedSymbols.addAll(symbols);

        startDataRepair(30 * 60);
        if (MODE_LEGACY.equals(MODE)) {
            startIngestorLoops(true);          // V8.1 y nguyen (rollback: KLINE_INGEST_MODE=legacy)
        } else {
            startIngestorLoops(false);         // chi Rest-Price-Loop (nan nen phut dang mo)
            startFinalizerLoop();
            if (MODE_WS.equals(MODE)) {
                wsClient = new KlineWsClient(core, this::onOpenUpdate, WS_STREAMS_PER_CONN, 75_000L);
                wsClient.start(() -> new ArrayList<>(globalSubscribedSymbols));
            }
        }
    }

    private void startIngestorLoops(boolean legacyKlineLoop) {
        // --- LUỒNG 1: LẤY GIÁ & "HOẠT HÌNH" NẾN HIỆN TẠI (3s/lần) ---
        new Thread(() -> {
            Thread.currentThread().setName("Rest-Price-Loop");
            String endpoint = "https://fapi.binance.com/fapi/v1/ticker/price"; // Chỉ tốn 2 weight
            boolean wasBanned = false;

            while (true) {
                try {
                    // 🔒 GUARD ban: đang ban thì KHÔNG gọi endpoint (mọi call lúc ban đều GIA HẠN ban).
                    // Cap 60s/nhịp để thread không kẹt + cho phép tái kiểm khi hết hạn.
                    if (BinanceRestGuard.awaitIfBanned(60_000L)) {
                        wasBanned = true;
                        continue;
                    }
                    if (wasBanned) {
                        LOG.info("✅ Hết cooldown, resume REST");
                        wasBanned = false;
                    }

                    String response = HttpRequest.getContentFromUrl(endpoint, 5000);
                    List<String> newSymbolsToRepair = new ArrayList<>();
                    long curMin = Utils.getMinute(System.currentTimeMillis());

                    // Lấy hoặc tạo mới rổ chứa nến của phút HIỆN TẠI
                    ConcurrentHashMap<String, KlineObjectOptimized> currentMinuteCandles = timeBuffer.computeIfAbsent(curMin, k -> new ConcurrentHashMap<>());

                    if (StringUtils.isNotBlank(response) && response.trim().startsWith("[")) {
                        JSONArray tickers = new JSONArray(response);

                        for (int i = 0; i < tickers.length(); i++) {
                            JSONObject obj = tickers.getJSONObject(i);
                            String symbol = obj.getString("symbol").toUpperCase();

                            if (symbol.endsWith("USDT") && symbol.matches("^[A-Z0-9]+$") && !Constants.diedSymbol.contains(symbol)) {
                                float price = obj.getFloat("price");
                                priceBuffer.put(symbol, price);

                                // --- LOGIC NẶN NẾN REALTIME ---
                                String shortS = symbol.replace("USDT", "");
                                currentMinuteCandles.compute(shortS, (k, existingCandle) -> {
                                    if (existingCandle == null) {
                                        // Phút mới chưa có data -> Lấy giá hiện tại làm râu nến ban đầu
                                        return KlineObjectOptimized.newBuilder()
                                                .setPriceOpen(price).setPriceClose(price)
                                                .setMaxPrice(price).setMinPrice(price)
                                                .setTotalUsdt(0).build();
                                    } else {
                                        // Đã có data -> Cập nhật Close và nới râu High/Low theo giá Realtime
                                        return KlineObjectOptimized.newBuilder()
                                                .setPriceOpen(existingCandle.getPriceOpen())
                                                .setPriceClose(price)
                                                .setMaxPrice(Math.max(existingCandle.getMaxPrice(), price))
                                                .setMinPrice(Math.min(existingCandle.getMinPrice(), price))
                                                .setTotalUsdt(existingCandle.getTotalUsdt()).build();
                                    }
                                });

                                if (!globalSubscribedSymbols.contains(symbol)) {
                                    LOG.info("✨ Mã mới gia nhập cuộc chơi: {}", symbol);
                                    initNewSymbolConfig(symbol);
                                    globalSubscribedSymbols.add(symbol);
                                    newSymbolsToRepair.add(symbol);
                                }
                            }
                        }

                        // Ghi Giá Realtime cho Bot chạy
                        if (!priceBuffer.isEmpty()) {
                            DataManagerAerospikeFloatSim.writePriceRealtime(new HashMap<>(priceBuffer));
                        }

                        // 🔥 ĐIỂM SỬA QUAN TRỌNG: Ghi liên tục NẾN HIỆN TẠI xuống DB để Bot không bị trễ
                        if (!currentMinuteCandles.isEmpty()) {
                            writeOpenMinute(curMin, new HashMap<>(currentMinuteCandles));
                        }

                        // Repair mã mới
                        if (!newSymbolsToRepair.isEmpty()) {
                            final List<String> repairList = new ArrayList<>(newSymbolsToRepair);
                            repairService.execute(() -> repairBatchOptimized(repairList, Utils.getMinute(System.currentTimeMillis() - 30 * Utils.TIME_HOUR), 1800));
                        }

                    } else if (StringUtils.isNotBlank(response) && response.trim().startsWith("{")) {
                        LOG.warn("⚠️ API Price báo lỗi (Limit): {}", response);
                        BinanceRestGuard.reportBan(response); // -1003/banned until => đặt cooldown GLOBAL
                    }

                    Thread.sleep(3000);

                } catch (Exception e) {
                    LOG.error("❌ Rest-Price-Loop Error: {}", e.getMessage());
                    Utils.sleep(3000L);
                }
            }
        }).start();

        // --- LUỒNG 2: CHỐT NẾN CHUẨN (ĐÚNG 1 LẦN KHI SANG PHÚT MỚI) --- [KFIX] chi mode legacy
        if (legacyKlineLoop) new Thread(() -> {
            Thread.currentThread().setName("Rest-Kline-Loop");
            long lastProcessedMinute = 0;

            while (true) {
                try {
                    long now = System.currentTimeMillis();
                    long curMin = Utils.getMinute(now);
                    long second = (now / 1000) % 60;

                    // 🔒 GUARD ban: burst 554 req/phút là nguồn ban gốc → đang ban thì BỎ QUA cả phút.
                    if (BinanceRestGuard.isBanned()) {
                        Thread.sleep(1000);
                        continue;
                    }

                    // Chỉ kích hoạt lấy Klines vào đúng giây thứ 02 đến 10 của phút mới
                    if (second >= 2 && second <= 10 && curMin > lastProcessedMinute) {
                        List<String> currentSymbols = new ArrayList<>(globalSubscribedSymbols);
                        if (!currentSymbols.isEmpty()) {
                            List<List<String>> batches = subListBySize(currentSymbols, 15);
                            List<Future<?>> futures = new ArrayList<>();

                            for (List<String> batch : batches) {
                                futures.add(restFetchService.submit(() -> fetchKlinesForBatch(batch)));
                            }

                            for (Future<?> f : futures) {
                                f.get(20, TimeUnit.SECONDS);
                            }

                            flushKlinesToDatabase(curMin);
                            lastProcessedMinute = curMin;
                        }
                    }
                    Thread.sleep(1000);
                } catch (Exception e) {
                    LOG.error("❌ Rest-Kline-Loop Error: {}", e.getMessage());
                }
            }
        }).start();
    }

    // ============================ [KFIX 2026-10-10] ============================
    static String normMode(String m) {
        String x = m == null ? "" : m.trim().toLowerCase(java.util.Locale.ROOT);
        if (MODE_LEGACY.equals(x) || MODE_REST.equals(x) || MODE_WS.equals(x)) return x;
        LOG.error("[KLINE-INGEST] KLINE_INGEST_MODE='{}' khong hop le -> dung {}", m, MODE_WS);
        return MODE_WS;
    }

    static long cfgLong(String key, long def) {
        String v = com.binance.chuyennd.tradecore.Cfg.getOr(key, null);
        if (v == null) return def;
        try {
            return Long.parseLong(v.trim());
        } catch (NumberFormatException e) {
            LOG.error("[KLINE-INGEST] {}='{}' khong phai so nguyen -> mac dinh {}", key, v, def);
            return def;
        }
    }

    /** Ghi nen phut DANG MO (nan). Mode moi: qua core (CHAN neu phut da chot). Legacy: ghi thang nhu V8.1. */
    private void writeOpenMinute(long minute, Map<String, KlineObjectOptimized> candles) {
        if (MODE_LEGACY.equals(MODE)) DataManagerAerospikeFloatSim.writeMinuteBatch(minute, candles);
        else core.writeOpenMinute(minute, candles);
    }

    /** WS x=false: nen phut dang mo chinh xac (O/H/L/C/Q dang chay) lam goc cho bo nan. */
    private void onOpenUpdate(String fullSym, long openTime, KlineObjectOptimized k) {
        if (openTime != Utils.getMinute(System.currentTimeMillis())) return;
        timeBuffer.computeIfAbsent(openTime, m -> new ConcurrentHashMap<>()).put(KlineIngestCore.shortSym(fullSym), k);
    }

    /** REST klines 1m moi nhat; NEM exception khi ban / body loi (core retry + dem failed + log). */
    private List<KlineIngestCore.Bar> restKlines(String symbol, int limit) throws Exception {
        if (BinanceRestGuard.isBanned()) throw new IllegalStateException("banned (BinanceRestGuard)");
        String url = "https://fapi.binance.com/fapi/v1/klines?symbol=" + symbol + "&interval=1m&limit=" + limit;
        String response = HttpRequest.getContentFromUrl(url, 3000);
        BinanceRestGuard.reportBan(response);
        if (StringUtils.isBlank(response) || !response.trim().startsWith("[")) {
            throw new IllegalStateException("body khong phai mang: " + StringUtils.abbreviate(String.valueOf(response), 120));
        }
        return parseRestKlines(response);
    }

    /** Parse body klines (mang 12 cot) -> Bar float32 (Float.parseFloat — cung cach parse WS). */
    static List<KlineIngestCore.Bar> parseRestKlines(String body) {
        JSONArray arr = new JSONArray(body);
        List<KlineIngestCore.Bar> out = new ArrayList<>(arr.length());
        for (int i = 0; i < arr.length(); i++) {
            JSONArray k = arr.getJSONArray(i);
            out.add(new KlineIngestCore.Bar(k.getLong(0), KlineObjectOptimized.newBuilder()
                    .setPriceOpen(Float.parseFloat(k.getString(1))).setMaxPrice(Float.parseFloat(k.getString(2)))
                    .setMinPrice(Float.parseFloat(k.getString(3))).setPriceClose(Float.parseFloat(k.getString(4)))
                    .setTotalUsdt(Float.parseFloat(k.getString(7))).build()));
        }
        return out;
    }

    /**
     * Luong "Kline-Finalizer" (100 ms/nhip), M = phut vua dong:
     * (1) ws: giay >= WS_FLUSH_MS ghi WS final cua M; moi nhip ghi WS final toi muon;
     * (2) giay >= EARLY_REST_SEC: REST som (limit=2) cho symbol THIEU WS final (rest_settle: moi symbol) — ghi M kip truoc
     *     khi live doc (giay 6), seed nen phut dang mo; (3) giay >= SETTLE_SEC: REST limit=SETTLE_LIMIT, ghi de nen da dong
     *     >= SETTLE_MIN_AGE_SEC neu khac store (M va M-1); (4) [KLINE-INGEST] counter moi STATS_MIN phut.
     */
    private void startFinalizerLoop() {
        Thread t = new Thread(() -> {
            long lastWsFlush = 0, lastEarly = 0, lastSettle = 0, lastStats = 0;
            boolean firstSettle = true;
            int wsCount = 0, earlyCalls = 0;
            while (true) {
                try {
                    long now = System.currentTimeMillis();
                    long curMin = Utils.getMinute(now);
                    long m = curMin - Utils.TIME_MINUTE;
                    long inMin = now - curMin;
                    boolean ws = MODE_WS.equals(MODE);
                    if (ws) {
                        if (m > lastWsFlush && inMin >= WS_FLUSH_MS) {
                            wsCount = core.flushWsFinals(m);
                            lastWsFlush = m;
                        }
                        core.flushLateFinals();
                    }
                    boolean earlyDue = inMin >= EARLY_REST_SEC * 1000L;
                    if (ws && !earlyDue && m > lastEarly && m <= lastWsFlush && inMin >= 2000L) {
                        int nSym = globalSubscribedSymbols.size();     // WS suy giam: > 50% symbol chua co final o giay 2
                        earlyDue = nSym > 0 && core.missingFinals(m, new ArrayList<>(globalSubscribedSymbols)).size() * 2 > nSym;
                    }
                    if (m > lastEarly && earlyDue && (!ws || m <= lastWsFlush)) {
                        lastEarly = m;
                        if (inMin <= 50_000L) earlyCalls = earlyPass(m, curMin, ws, wsCount);
                    }
                    if (m > lastSettle && inMin >= SETTLE_SEC * 1000L) {
                        lastSettle = m;
                        if (!BinanceRestGuard.isBanned()) {
                            long t0 = System.currentTimeMillis();
                            int lim = firstSettle ? Math.max(SETTLE_LIMIT, SETTLE_LIMIT_STARTUP) : SETTLE_LIMIT;
                            firstSettle = false;
                            KlineIngestCore.SettleResult r = core.settle(System.currentTimeMillis(),
                                    new ArrayList<>(globalSubscribedSymbols), lim);
                            lastRestCalls = earlyCalls + r.fetched + r.failed;
                            if (r.rewrittenDiff > 0 || r.failed > 0 || r.filledMissing > 0) {
                                LOG.info("[KLINE-INGEST] settle phut {} (limit={}): fetched={} failed={} rewritten_diff={} filled_missing={} same={} diff_by_minute={} ({} ms)",
                                        Utils.normalizeDateYYYYMMDDHHmm(m), lim, r.fetched, r.failed, r.rewrittenDiff, r.filledMissing,
                                        r.same, r.diffByMinute.values(), System.currentTimeMillis() - t0);
                            }
                        }
                    }
                    if (STATS_MIN > 0 && (curMin / Utils.TIME_MINUTE) % STATS_MIN == 0 && curMin > lastStats && inMin >= 45_000L) {
                        lastStats = curMin;
                        KlineWsClient w = wsClient;
                        LOG.info("[KLINE-INGEST] mode={} {} | ws_conn={}/{} ws_reconnects={} symbols={} rest_klines_calls_last_min={} (weight ~ +60 price/funding, limit 2400/phut)",
                                MODE, core.statsLine(), w == null ? 0 : w.aliveConnections(), w == null ? 0 : w.connections(),
                                w == null ? 0 : w.reconnects(), globalSubscribedSymbols.size(), lastRestCalls);
                    }
                    core.gc(curMin - 10 * Utils.TIME_MINUTE);
                    for (Long k : new ArrayList<>(timeBuffer.keySet())) {
                        if (k < curMin - Utils.TIME_MINUTE) timeBuffer.remove(k);
                    }
                    Thread.sleep(100);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    return;
                } catch (Exception e) {
                    LOG.error("[KLINE-INGEST] Kline-Finalizer loi: {}", e.toString(), e);
                    Utils.sleep(1000L);
                }
            }
        }, "Kline-Finalizer");
        t.start();
    }

    /** REST som cho phut M; log 1 dong/phut (giu cum 'Chốt nến phút' cho health_242.sh). Tra so call REST. */
    private int earlyPass(long m, long curMin, boolean ws, int wsCount) {
        List<String> syms = new ArrayList<>(globalSubscribedSymbols);
        List<String> need = ws ? core.missingFinals(m, syms) : syms;
        int nClosed = 0, nFail = 0;
        if (!need.isEmpty() && !BinanceRestGuard.isBanned()) {
            KlineIngestCore.EarlyResult r = core.earlyRest(m, need);
            nClosed = r.closed.size();
            nFail = r.failed.size();
            if (!r.open.isEmpty()) {
                ConcurrentHashMap<String, KlineObjectOptimized> cur = timeBuffer.computeIfAbsent(curMin, k -> new ConcurrentHashMap<>());
                cur.putAll(r.open);
            }
        }
        int wsHave = ws ? syms.size() - need.size() : 0;   // WS final da co (ghi o giay 1,5 + toi muon)
        LOG.info("✅ [KLINE V9 {}] Chốt nến phút {} thành công. Total: {} symbols (ws_final={} ws_flush_1s5={} rest_som={} rest_loi={} thieu_ws={})",
                MODE, Utils.normalizeDateYYYYMMDDHHmm(m), wsHave + nClosed, wsHave, wsCount, nClosed, nFail, ws ? need.size() : 0);
        return need.size();
    }

    //    private void fetchKlinesForBatch(List<String> symbols) {
//        for (String symbol : symbols) {
//            try {
//                // limit=2 sẽ lấy cây nến ĐÃ ĐÓNG của phút trước, VÀ cây nến VỪA MỞ của phút hiện tại
//                String url = "https://fapi.binance.com/fapi/v1/klines?symbol=" + symbol + "&interval=1m&limit=2";
//                String response = HttpRequest.getContentFromUrl(url, 5000);
//
//                if (StringUtils.isNotBlank(response) && response.trim().startsWith("[")) {
//                    JSONArray klines = new JSONArray(response);
//
//                    for (int i = 0; i < klines.length(); i++) {
//                        JSONArray k = klines.getJSONArray(i);
//
//                        long startTime = k.getLong(0);
//                        float open = k.getFloat(1);
//                        float high = k.getFloat(2);
//                        float low = k.getFloat(3);
//                        float close = k.getFloat(4);
//                        float volume = k.getFloat(7);
//
//                        String shortS = symbol.replace("USDT", "");
//                        KlineObjectOptimized optP = KlineObjectOptimized.newBuilder()
//                                .setPriceOpen(open).setPriceClose(close)
//                                .setMaxPrice(high).setMinPrice(low)
//                                .setTotalUsdt(volume).build();
//
//                        // Nạp đè dữ liệu CHUẨN TỪ SÀN vào RAM (thay thế cho cây nến ta tự nặn lúc đầu)
//                        timeBuffer.computeIfAbsent(startTime, key -> new ConcurrentHashMap<>()).put(shortS, optP);
//                    }
//                }
//                Thread.sleep(10);
//            } catch (Exception e) {
//                // Ignore
//            }
//        }
//    }
    private void fetchKlinesForBatch(List<String> symbols) {
        // #5: dùng pool CHUNG klineFetchPool (không tạo/hủy mỗi batch) → chặn trần 30 luồng cho mọi batch song song.
        try {
            klineFetchPool.submit(() ->
                    symbols.parallelStream().forEach(symbol -> {
                        try {
                            // 🔒 GUARD ban: dính ban giữa chừng → short-circuit, không gọi tiếp coin nào.
                            if (BinanceRestGuard.isBanned()) return;

                            String url = "https://fapi.binance.com/fapi/v1/klines?symbol=" + symbol + "&interval=1m&limit=2";
                            // Giảm timeout xuống 3000ms để luồng không bị kẹt nếu mạng lag
                            String response = HttpRequest.getContentFromUrl(url, 3000);

                            // klines khi ban cũng trả body -1003 => phát hiện & đặt cooldown (trước đây nuốt lỗi).
                            BinanceRestGuard.reportBan(response);

                            if (org.apache.commons.lang.StringUtils.isNotBlank(response) && response.trim().startsWith("[")) {
                                org.json.JSONArray klines = new org.json.JSONArray(response);

                                for (int i = 0; i < klines.length(); i++) {
                                    org.json.JSONArray k = klines.getJSONArray(i);

                                    long startTime = k.getLong(0);
                                    float open = k.getFloat(1);
                                    float high = k.getFloat(2);
                                    float low = k.getFloat(3);
                                    float close = k.getFloat(4);
                                    float volume = k.getFloat(7);

                                    String shortS = symbol.replace("USDT", "");
                                    com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized optP =
                                            com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized.newBuilder()
                                                    .setPriceOpen(open).setPriceClose(close)
                                                    .setMaxPrice(high).setMinPrice(low)
                                                    .setTotalUsdt(volume).build();

                                    // Nạp đè dữ liệu CHUẨN TỪ SÀN vào RAM
                                    // timeBuffer là ConcurrentHashMap nên rất an toàn khi dùng đa luồng
                                    timeBuffer.computeIfAbsent(startTime, key -> new java.util.concurrent.ConcurrentHashMap<>()).put(shortS, optP);
                                }
                            }
                            // 🔥 ĐÃ XÓA THREAD.SLEEP(10)
                        } catch (Exception e) {
                            // Ignore lỗi của từng đồng coin để không ảnh hưởng các coin khác
                        }
                    })
            ).get(); // Đợi tất cả 554 đồng coin tải xong
        } catch (Exception e) {
            LOG.error("Lỗi khi fetch kline đa luồng: ", e);
        }
        // KHÔNG shutdown: pool dùng chung, sống suốt vòng đời ingest (#5).
    }

    private void flushKlinesToDatabase(long curMin) {
        long lastMin = curMin - 60000;

        try {
            // 1. Lưu cây nến hiện tại (Đã được cập nhật Open/Volume chuẩn)
            if (timeBuffer.containsKey(curMin)) {
                DataManagerAerospikeFloatSim.writeMinuteBatch(curMin, new HashMap<>(timeBuffer.get(curMin)));
            }

            // 2. Chốt lưu vĩnh viễn cây nến của phút trước
            if (timeBuffer.containsKey(lastMin)) {
                DataManagerAerospikeFloatSim.writeMinuteBatch(lastMin, new HashMap<>(timeBuffer.get(lastMin)));

                int finalSize = timeBuffer.get(lastMin).size();
                timeBuffer.remove(lastMin);
                LOG.info("✅ [KLINE V8.1] Chốt nến phút {} thành công. Total: {} symbols", Utils.normalizeDateYYYYMMDDHHmm(lastMin), finalSize);
            }

            // Dọn rác
            for (Long timeKey : new ArrayList<>(timeBuffer.keySet())) {
                if (timeKey < lastMin) timeBuffer.remove(timeKey);
            }
        } catch (Exception e) {
            LOG.error("❌ Flush Kline Error: {}", e.getMessage());
        }
    }

    private List<String> collectSymbolsFromRedis() {
        List<String> symbols = new ArrayList<>();
        Set<String> redisData = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
        String regex = "^[A-Z0-9]+$";

        for (String s : redisData) {
            String upperS = s.toUpperCase();
            if (!Constants.diedSymbol.contains(upperS) && StringUtils.endsWithIgnoreCase(upperS, "USDT") && upperS.matches(regex)) {
                symbols.add(upperS);
            }
        }
        return symbols;
    }

    private void startDataRepair(int totalMinutes) {
        repairService.execute(() -> {
            try {
                long now = System.currentTimeMillis();
                int step = 500;
                List<String> symbols = collectSymbolsFromRedis();

                for (int offset = totalMinutes; offset > 0; offset -= step) {
                    long batchStart = Utils.getMinute(now - (long) offset * Utils.TIME_MINUTE);
                    List<String> missing = new ArrayList<>();

                    for (String s : symbols) {
                        if (DataManagerAerospikeFloatSim.isSymbolMissingInPoints(s.replace("USDT", ""), batchStart, step)) {
                            missing.add(s);
                        }
                    }

                    if (!missing.isEmpty()) {
                        repairBatchOptimized(missing, batchStart, step);
                        Thread.sleep(5000);
                    }
                }
            } catch (Exception e) {
                LOG.error("Repair Task Error", e);
            }
        });
    }

    private void repairBatchOptimized(List<String> symbols, long batchStartTime, int limit) {
        for (String s : symbols) {
            try {
                // 🔒 GUARD ban: repair cũng gọi REST → đang ban thì dừng batch (không gia hạn ban).
                if (BinanceRestGuard.isBanned()) return;
                if (StringUtils.isBlank(s) || !s.matches("^[A-Z0-9]+$")) continue;

                List<KlineObjectSimple> candles = TickerFuturesHelper.getTickerSimpleWithStartTimeAndLimit(s, "1m", batchStartTime, limit);
                if (candles == null || candles.isEmpty()) continue;

                String shortS = s.replace("USDT", "");
                for (KlineObjectSimple c : candles) {
                    if (c == null || c.startTime == null) continue;
                    long ts = c.startTime.longValue();

                    if (ts >= batchStartTime && ts < batchStartTime + (long) limit * Utils.TIME_MINUTE) {
                        Map<String, KlineObjectOptimized> map = new HashMap<>();
                        map.put(shortS, convertToProto(c));
                        DataManagerAerospikeFloatSim.writeMinuteBatch(ts, map);
                    }
                }

                Thread.sleep(300);

            } catch (Exception e) {
                // bỏ qua 1 coin để tiếp coin khác — NHƯNG vẫn log (CLAUDE.md: không nuốt exception câm)
                LOG.warn("repair coin {} lỗi, bỏ qua tiếp coin khác: {}", s, e.toString());
            }
        }
    }

    private void initNewSymbolConfig(String symbol) {
        try {
            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS, symbol, symbol);
            ClientSingleton.getInstance().syncRequestClient.changeInitialLeverage(symbol, Configs.LEVERAGE_ORDER);
        } catch (Exception e) {
        }
    }

    private List<List<String>> subListBySize(List<String> list, int size) {
        List<List<String>> parts = new ArrayList<>();
        for (int i = 0; i < list.size(); i += size) parts.add(list.subList(i, Math.min(i + size, list.size())));
        return parts;
    }

    private KlineObjectOptimized convertToProto(KlineObjectSimple c) {
        return KlineObjectOptimized.newBuilder().setPriceOpen(c.priceOpen).setPriceClose(c.priceClose)
                .setMaxPrice(c.maxPrice).setMinPrice(c.minPrice).setTotalUsdt(c.totalUsdt).build();
    }
}