package com.binance.chuyennd.websocket;

import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;

/**
 * [KFIX 2026-10-10] Websocket {@code <sym>@kline_1m} (combined stream, ≤ {@code streamsPerConn} stream/kết nối) —
 * chỉ đẩy sự kiện {@code k.x == true} (nến đã đóng, bản cuối của sàn) vào {@link KlineIngestCore#onWsFinal};
 * sự kiện {@code x=false} chuyển cho {@code onOpenUpdate} (nến phút đang mở, tuỳ chọn).
 * Watchdog: kết nối im lặng &gt; {@code staleMs} hoặc đã đóng/lỗi ⇒ mở lại (backoff ≥ 5 s);
 * symbol mới (không nằm trong kết nối nào) ⇒ mở thêm kết nối. Lỗi WS KHÔNG làm mất nến: symbol thiếu WS final
 * được REST sớm + pass settle phủ (KlineIngestCore).
 */
public final class KlineWsClient {
    private static final Logger LOG = LoggerFactory.getLogger(KlineWsClient.class);
    /** [KFIX] Binance da tach stream thi truong sang /market (duong cu /stream, /ws: KET NOI DUOC NHUNG IM LANG —
     *  do 2026-10-10 tu Oracle: /stream 0 msg/8s, /market/stream 33 msg/8s). Doi duoc qua env KLINE_WS_BASE. */
    static final String BASE = com.binance.chuyennd.tradecore.Cfg.getOr("KLINE_WS_BASE",
            "wss://fstream.binance.com/market/stream?streams=");

    /** Sự kiện kline đã parse. */
    public static final class KlineEvent {
        public final String symbol;
        public final long openTime;
        public final boolean closed;
        public final KlineObjectOptimized k;

        KlineEvent(String symbol, long openTime, boolean closed, KlineObjectOptimized k) {
            this.symbol = symbol;
            this.openTime = openTime;
            this.closed = closed;
            this.k = k;
        }
    }

    public interface OpenUpdateSink {
        void onOpenUpdate(String fullSym, long openTime, KlineObjectOptimized k);
    }

    /** Parse message combined stream ({@code {"stream":..,"data":{"e":"kline","k":{..}}}}) hoặc raw; null nếu không phải kline. */
    public static KlineEvent parse(String msg) {
        try {
            JSONObject root = new JSONObject(msg);
            JSONObject d = root.has("data") ? root.getJSONObject("data") : root;
            if (!"kline".equals(d.optString("e")) || !d.has("k")) return null;
            JSONObject k = d.getJSONObject("k");
            if (!"1m".equals(k.optString("i", "1m"))) return null;
            KlineObjectOptimized c = KlineObjectOptimized.newBuilder()
                    .setPriceOpen(Float.parseFloat(k.getString("o")))
                    .setMaxPrice(Float.parseFloat(k.getString("h")))
                    .setMinPrice(Float.parseFloat(k.getString("l")))
                    .setPriceClose(Float.parseFloat(k.getString("c")))
                    .setTotalUsdt(Float.parseFloat(k.getString("q"))).build();
            return new KlineEvent(k.getString("s").toUpperCase(Locale.ROOT), k.getLong("t"), k.getBoolean("x"), c);
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * [INGEST-QF2] Mốc xoay CHỦ ĐỘNG của kết nối thứ {@code idx} (tính từ lúc mở): 20h + (idx mod 8)×25′ ⇒ 6 kết nối mở cùng lúc
     * xoay ở 20h00, 20h25, …, 22h05 — lệch nhau 25′, đều trước mốc 24h sàn tự cắt; không bao giờ rơi cùng lúc vì mốc 24h.
     */
    static long rotateAfterMs(int idx) {
        return ROTATE_BASE_MS + (long) Math.floorMod(idx, 8) * ROTATE_STEP_MS;
    }

    static final long ROTATE_BASE_MS = 20L * 3_600_000L;
    static final long ROTATE_STEP_MS = 25L * 60_000L;

    private final class Conn extends WebSocketListener {
        final List<String> symbols;
        final int idx;
        volatile WebSocket ws;
        /** [INGEST-QF2] kết nối thay thế đang mở trong lúc xoay (cũ vẫn chạy tới khi bản mới có message đầu tiên). */
        volatile WebSocket pending;
        volatile long lastMsgMs;
        volatile boolean alive;
        volatile long nextRetryMs;
        volatile long backoffMs = 5_000L;
        volatile long rotateAtMs;

        Conn(List<String> symbols, int idx) {
            this.symbols = symbols;
            this.idx = idx;
        }

        /** Xoay chủ động: mở bản thay thế; swap khi bản mới nhận message đầu tiên (không hở dữ liệu). */
        void rotate() {
            WebSocket p = pending;
            if (p != null) {   // ban thay the qua 2' chua co message => huy, mo ban khac
                pending = null;
                p.cancel();
                LOG.warn("[KLINE-WS] ban thay the #{} khong co du lieu sau 2', huy va thu lai", idx);
            }
            LOG.info("[KLINE-WS] xoay chu dong ket noi #{} ({} symbol) truoc moc 24h", idx, symbols.size());
            rotateAtMs = System.currentTimeMillis() + 120_000L;   // neu ban moi khong len trong 2' => thu lai
            pending = http.newWebSocket(new Request.Builder().url(url()).build(), this);
            rotations++;
        }

        String url() {
            StringBuilder sb = new StringBuilder(BASE);
            for (int i = 0; i < symbols.size(); i++) {
                if (i > 0) sb.append('/');
                sb.append(symbols.get(i).toLowerCase(Locale.ROOT)).append("@kline_1m");
            }
            return sb.toString();
        }

        void open() {
            lastMsgMs = System.currentTimeMillis();
            alive = true;
            rotateAtMs = lastMsgMs + rotateAfterMs(idx);   // [INGEST-QF2] moc xoay lech nhau theo idx
            ws = http.newWebSocket(new Request.Builder().url(url()).build(), this);
            reconnects++;
        }

        void kill(String why) {
            alive = false;
            WebSocket w = ws;
            if (w != null) w.cancel();
            WebSocket p = pending;
            pending = null;
            if (p != null) p.cancel();
            nextRetryMs = System.currentTimeMillis() + backoffMs;
            backoffMs = Math.min(60_000L, backoffMs * 2);
            LOG.warn("[KLINE-WS] dong ket noi #{} {} symbol ({}), mo lai sau {} ms", idx, symbols.size(), why, nextRetryMs - System.currentTimeMillis());
        }

        @Override
        public void onOpen(WebSocket webSocket, Response response) {
            if (webSocket == ws) backoffMs = 5_000L;
            LOG.info("[KLINE-WS] mo ket noi {} stream{}", symbols.size(), webSocket == pending ? " (ban thay the khi xoay)" : "");
        }

        @Override
        public void onMessage(WebSocket webSocket, String text) {
            if (webSocket == pending) {   // [INGEST-QF2] ban thay the da co du lieu => swap, dong ban cu (trung su kien vo hai)
                WebSocket old = ws;
                ws = webSocket;
                pending = null;
                rotateAtMs = System.currentTimeMillis() + rotateAfterMs(idx);
                if (old != null) old.close(1000, "rotate");
                LOG.info("[KLINE-WS] xoay xong ket noi #{}; moc xoay ke tiep sau {} phut", idx, rotateAfterMs(idx) / 60_000L);
            } else if (webSocket != ws) {
                return;   // ban cu da thay
            }
            lastMsgMs = System.currentTimeMillis();
            KlineEvent ev = parse(text);
            if (ev == null) return;
            if (ev.closed) core.onWsFinal(ev.symbol, ev.openTime, ev.k);
            else if (openSink != null) openSink.onOpenUpdate(ev.symbol, ev.openTime, ev.k);
        }

        private void pendingFailed(WebSocket webSocket, String why) {
            if (webSocket == pending) {
                pending = null;
                rotateAtMs = System.currentTimeMillis() + 120_000L;
                LOG.warn("[KLINE-WS] ban thay the #{} loi ({}), giu ban cu, thu xoay lai sau 2'", idx, why);
            }
        }

        @Override
        public void onClosing(WebSocket webSocket, int code, String reason) {
            webSocket.close(1000, null);
            pendingFailed(webSocket, "closing " + code);
            if (webSocket == ws && alive) kill("closing " + code + " " + reason);
        }

        @Override
        public void onFailure(WebSocket webSocket, Throwable t, Response response) {
            pendingFailed(webSocket, "failure " + t);
            if (webSocket == ws && alive) kill("failure " + t);
        }

        @Override
        public void onClosed(WebSocket webSocket, int code, String reason) {
            pendingFailed(webSocket, "closed " + code);
            if (webSocket == ws && alive) kill("closed " + code + " " + reason);
        }
    }

    private final KlineIngestCore core;
    private final OpenUpdateSink openSink;
    private final int streamsPerConn;
    private final long staleMs;
    private final long watchdogMs;
    private final OkHttpClient http;
    private final List<Conn> conns = new CopyOnWriteArrayList<>();
    private volatile long reconnects = 0;
    private volatile long rotations = 0;

    /** [INGEST-QF2] staleMs + watchdogMs = thời gian tối đa phát hiện kết nối im lặng (prereg Q10: ≤ 15 s). */
    public KlineWsClient(KlineIngestCore core, OpenUpdateSink openSink, int streamsPerConn, long staleMs, long watchdogMs) {
        this.core = core;
        this.openSink = openSink;
        this.streamsPerConn = Math.max(1, Math.min(200, streamsPerConn));
        this.staleMs = staleMs;
        this.watchdogMs = Math.max(1_000L, watchdogMs);
        this.http = new OkHttpClient.Builder().pingInterval(20, TimeUnit.SECONDS)
                .readTimeout(0, TimeUnit.MILLISECONDS).connectTimeout(10, TimeUnit.SECONDS).build();
    }

    /** Thời gian phát hiện im lặng tối đa (ms). */
    long maxDetectMs() {
        return staleMs + watchdogMs;
    }

    /**
     * Chia symbol thành ⌈N/size⌉ nhóm ĐỀU NHAU (mỗi nhóm ≤ size, thứ tự sort cố định) — thuần, test được.
     * [QF3, A1_QF2 MIN-B] trước đây 752 = 5×150 + 2 ⇒ kết nối thứ 6 chỉ 2 symbol ít giao dịch, dễ bị coi "im lặng"; nay 6 × 125–126.
     */
    static List<List<String>> chunk(Collection<String> symbols, int size) {
        List<String> s = new ArrayList<>(symbols);
        java.util.Collections.sort(s);
        List<List<String>> out = new ArrayList<>();
        if (s.isEmpty()) return out;
        int groups = (s.size() + size - 1) / size;
        int base = s.size() / groups, extra = s.size() % groups, i = 0;
        for (int g = 0; g < groups; g++) {
            int n = base + (g < extra ? 1 : 0);
            out.add(new ArrayList<>(s.subList(i, i + n)));
            i += n;
        }
        return out;
    }

    /** Kết nối ít symbol (&lt; {@link #SMALL_CONN}) = symbol mới niêm yết, có thể vài chục giây không trade ⇒ ngưỡng im lặng dài,
     *  dựa thêm vào ping 20 s của OkHttp để phát hiện kết nối chết (ADD2). Kết nối thường: staleMs (≤15 s cùng watchdog). */
    static final int SMALL_CONN = 20;
    static final long SMALL_CONN_STALE_MS = 90_000L;

    long staleFor(int nSymbols) {
        return nSymbols < SMALL_CONN ? Math.max(staleMs, SMALL_CONN_STALE_MS) : staleMs;
    }

    /** Mở kết nối cho symbol hiện có + luồng watchdog (mỗi watchdogMs) mở lại kết nối chết, xoay chủ động, thêm symbol mới. */
    public void start(Supplier<Collection<String>> symbols) {
        for (List<String> c : chunk(symbols.get(), streamsPerConn)) {
            Conn cn = new Conn(c, conns.size());
            conns.add(cn);
            cn.open();
        }
        Thread t = new Thread(com.binance.chuyennd.utils.LoopSupervisor.wrap("Kline-WS-Watchdog", () -> {
            while (true) {
                try {
                    Thread.sleep(watchdogMs);
                    watchdog(symbols.get());
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    return;
                } catch (Exception e) {
                    LOG.warn("[KLINE-WS] watchdog loi: {}", e.toString());
                }
            }
        }), "Kline-WS-Watchdog");
        t.setDaemon(true);
        t.start();
    }

    void watchdog(Collection<String> desired) {
        long now = System.currentTimeMillis();
        Set<String> covered = new HashSet<>();
        for (Conn c : conns) {
            covered.addAll(c.symbols);
            if (c.alive && now - c.lastMsgMs > staleFor(c.symbols.size())) c.kill("im lang " + (now - c.lastMsgMs) + " ms");
            if (!c.alive && now >= c.nextRetryMs) c.open();
            if (c.alive && now >= c.rotateAtMs) c.rotate();
        }
        List<String> added = new ArrayList<>();
        for (String s : desired) if (!covered.contains(s)) added.add(s);
        if (!added.isEmpty()) {
            for (List<String> c : chunk(added, streamsPerConn)) {
                Conn cn = new Conn(c, conns.size());
                conns.add(cn);
                cn.open();
            }
            LOG.info("[KLINE-WS] them {} symbol moi vao WS", added.size());
        }
    }

    public int aliveConnections() {
        int n = 0;
        for (Conn c : conns) if (c.alive) n++;
        return n;
    }

    public int connections() {
        return conns.size();
    }

    public long reconnects() {
        return reconnects;
    }

    public long rotations() {
        return rotations;
    }
}
