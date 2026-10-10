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

    private final class Conn extends WebSocketListener {
        final List<String> symbols;
        volatile WebSocket ws;
        volatile long lastMsgMs;
        volatile boolean alive;
        volatile long nextRetryMs;
        volatile long backoffMs = 5_000L;

        Conn(List<String> symbols) {
            this.symbols = symbols;
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
            ws = http.newWebSocket(new Request.Builder().url(url()).build(), this);
            reconnects++;
        }

        void kill(String why) {
            alive = false;
            WebSocket w = ws;
            if (w != null) w.cancel();
            nextRetryMs = System.currentTimeMillis() + backoffMs;
            backoffMs = Math.min(60_000L, backoffMs * 2);
            LOG.warn("[KLINE-WS] dong ket noi {} symbol ({}), mo lai sau {} ms", symbols.size(), why, nextRetryMs - System.currentTimeMillis());
        }

        @Override
        public void onOpen(WebSocket webSocket, Response response) {
            backoffMs = 5_000L;
            LOG.info("[KLINE-WS] mo ket noi {} stream", symbols.size());
        }

        @Override
        public void onMessage(WebSocket webSocket, String text) {
            lastMsgMs = System.currentTimeMillis();
            KlineEvent ev = parse(text);
            if (ev == null) return;
            if (ev.closed) core.onWsFinal(ev.symbol, ev.openTime, ev.k);
            else if (openSink != null) openSink.onOpenUpdate(ev.symbol, ev.openTime, ev.k);
        }

        @Override
        public void onClosing(WebSocket webSocket, int code, String reason) {
            webSocket.close(1000, null);
            if (webSocket == ws && alive) kill("closing " + code + " " + reason);
        }

        @Override
        public void onFailure(WebSocket webSocket, Throwable t, Response response) {
            if (webSocket == ws && alive) kill("failure " + t);
        }

        @Override
        public void onClosed(WebSocket webSocket, int code, String reason) {
            if (webSocket == ws && alive) kill("closed " + code + " " + reason);
        }
    }

    private final KlineIngestCore core;
    private final OpenUpdateSink openSink;
    private final int streamsPerConn;
    private final long staleMs;
    private final OkHttpClient http;
    private final List<Conn> conns = new CopyOnWriteArrayList<>();
    private volatile long reconnects = 0;

    public KlineWsClient(KlineIngestCore core, OpenUpdateSink openSink, int streamsPerConn, long staleMs) {
        this.core = core;
        this.openSink = openSink;
        this.streamsPerConn = Math.max(1, Math.min(200, streamsPerConn));
        this.staleMs = staleMs;
        this.http = new OkHttpClient.Builder().pingInterval(20, TimeUnit.SECONDS)
                .readTimeout(0, TimeUnit.MILLISECONDS).connectTimeout(10, TimeUnit.SECONDS).build();
    }

    /** Chia symbol thành nhóm ≤ streamsPerConn (thứ tự sort cố định) — thuần, test được. */
    static List<List<String>> chunk(Collection<String> symbols, int size) {
        List<String> s = new ArrayList<>(symbols);
        java.util.Collections.sort(s);
        List<List<String>> out = new ArrayList<>();
        for (int i = 0; i < s.size(); i += size) out.add(new ArrayList<>(s.subList(i, Math.min(i + size, s.size()))));
        return out;
    }

    /** Mở kết nối cho symbol hiện có + luồng watchdog (10 s) mở lại kết nối chết và thêm symbol mới. */
    public void start(Supplier<Collection<String>> symbols) {
        for (List<String> c : chunk(symbols.get(), streamsPerConn)) {
            Conn cn = new Conn(c);
            conns.add(cn);
            cn.open();
        }
        Thread t = new Thread(() -> {
            while (true) {
                try {
                    Thread.sleep(10_000L);
                    watchdog(symbols.get());
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    return;
                } catch (Exception e) {
                    LOG.warn("[KLINE-WS] watchdog loi: {}", e.toString());
                }
            }
        }, "Kline-WS-Watchdog");
        t.setDaemon(true);
        t.start();
    }

    void watchdog(Collection<String> desired) {
        long now = System.currentTimeMillis();
        Set<String> covered = new HashSet<>();
        for (Conn c : conns) {
            covered.addAll(c.symbols);
            if (c.alive && now - c.lastMsgMs > staleMs) c.kill("im lang " + (now - c.lastMsgMs) + " ms");
            if (!c.alive && now >= c.nextRetryMs) c.open();
        }
        List<String> added = new ArrayList<>();
        for (String s : desired) if (!covered.contains(s)) added.add(s);
        if (!added.isEmpty()) {
            for (List<String> c : chunk(added, streamsPerConn)) {
                Conn cn = new Conn(c);
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
}
