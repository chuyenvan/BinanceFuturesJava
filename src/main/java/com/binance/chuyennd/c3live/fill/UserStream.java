package com.binance.chuyennd.c3live.fill;

import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Consumer;
import java.util.function.LongSupplier;

/**
 * [V12 C7] User-data stream cua TAI KHOAN CON (listenKey qua {@link ExchangeGateway#startUserStream}), websocket
 * (okhttp — thu vien san co, nhu {@code ops.ExecProbeWsSource}). Su kien => {@link FillAccounting}.
 * <ul>
 *   <li>keepAlive listenKey moi 30' (loi => ket noi lai voi listenKey moi);</li>
 *   <li>mat ket noi / {@code listenKeyExpired} / qua han ket noi => WARN + ket noi lai voi backoff 1 s .. 60 s; URL xoay vong
 *       qua danh sach mau ({@code {key}} = listenKey) khi ket noi that bai (URL private CHUA XAC MINH — canary);</li>
 *   <li>khi KHONG ket noi (sau 2 s): fallback REST ({@code fallback}: tra lenh treo + positions) moi {@code fallbackEveryMs},
 *       Telegram 1 lan khi mat lau hon {@code alertDownMs}; ket noi lai (sau khi da tung ket noi) => fallback 1 lan
 *       (bu su kien bi lo trong luc mat).</li>
 * </ul>
 * Khong log listenKey (chi 4 ky tu dau). {@link #tick(long)} la may trang thai (test duoc khong can thread rieng);
 * {@link #start()} chay thread {@code C3LIVE-STREAM} goi tick moi giay.
 */
public final class UserStream {

    private static final Logger LOG = LoggerFactory.getLogger(UserStream.class);
    public static final String DEFAULT_URLS = "wss://fstream.binance.com/private/ws/{key},wss://fstream.binance.com/ws/{key}";
    public static final long KEEPALIVE_MS = 30L * 60_000L;

    /** Ket noi websocket (prod: okhttp). */
    public interface Connector {
        Socket open(String url, Listener listener);
    }

    public interface Socket {
        void close();
    }

    public interface Listener {
        void onOpen();

        void onText(String text);

        void onClosed(String why);
    }

    public enum State { DISCONNECTED, CONNECTING, CONNECTED }

    private final ExchangeGateway gw;
    private final Connector connector;
    private final List<String> urls;
    /** [V12 R4h] dich su kien (prod: FillAccounting::dispatch; soak: chi dem). */
    private final java.util.function.Consumer<UserStreamEvents.Event> sink;
    private final Runnable fallback;
    private final Consumer<String> alert;
    private final C3LiveOrderExecutor.ApiObserver api;
    private final LongSupplier clock;
    private final long connectTimeoutMs;
    private final long fallbackEveryMs;
    private final long maxBackoffMs;
    private final long alertDownMs;

    private volatile State state = State.DISCONNECTED;
    private int gen;
    private Socket socket;
    private String listenKey;
    private int urlIdx;
    private long nextAttemptMs;
    private long backoffMs = 1_000L;
    private long connectStartMs;
    private long connectedSinceMs;
    private long lastKeepAliveMs;
    /** -1 = dang ket noi; khac = moc bat dau mat (hoac moc khoi dong). */
    private long downSinceMs = -1L;
    private boolean everConnected;
    private long lastFallbackMs = Long.MIN_VALUE / 2;
    private long lastDownWarnMs = Long.MIN_VALUE / 2;
    private boolean downAlerted;
    private boolean needCatchUp;
    private volatile long lastMsgMs;
    private final AtomicLong nMsg = new AtomicLong();
    private final AtomicLong nConnect = new AtomicLong();
    private final AtomicLong nDown = new AtomicLong();
    private final AtomicLong nFallback = new AtomicLong();
    private final AtomicLong nKeepAlive = new AtomicLong();
    private final AtomicLong nCatchUp = new AtomicLong();
    private Thread thread;

    public UserStream(ExchangeGateway gw, Connector connector, List<String> urlTemplates, FillAccounting acct, Runnable fallback,
                      Consumer<String> alert, C3LiveOrderExecutor.ApiObserver api, LongSupplier clock,
                      long connectTimeoutMs, long fallbackEveryMs, long maxBackoffMs, long alertDownMs) {
        this.gw = gw;
        this.connector = connector;
        this.urls = urlTemplates == null || urlTemplates.isEmpty() ? parseUrls(DEFAULT_URLS) : new ArrayList<>(urlTemplates);
        this.sink = acct == null ? e -> { } : acct::dispatch;
        this.fallback = fallback == null ? () -> { } : fallback;
        this.alert = alert == null ? m -> { } : alert;
        this.api = api == null ? (a, ok) -> { } : api;
        this.clock = clock == null ? System::currentTimeMillis : clock;
        this.connectTimeoutMs = Math.max(1_000L, connectTimeoutMs);
        this.fallbackEveryMs = Math.max(1_000L, fallbackEveryMs);
        this.maxBackoffMs = Math.max(1_000L, maxBackoffMs);
        this.alertDownMs = Math.max(0L, alertDownMs);
    }

    /** [V12 R4h] cho cong cu soak CHI DOC: su kien vao {@code sink} (khong FillAccounting). */
    public static UserStream forSink(ExchangeGateway gw, Connector connector, List<String> urlTemplates,
                                     java.util.function.Consumer<UserStreamEvents.Event> sink, Consumer<String> alert,
                                     C3LiveOrderExecutor.ApiObserver api, LongSupplier clock, long connectTimeoutMs,
                                     long maxBackoffMs) {
        UserStream u = new UserStream(gw, connector, urlTemplates, null, () -> { }, alert, api, clock, connectTimeoutMs,
                3_600_000L, maxBackoffMs, Long.MAX_VALUE / 4);
        u.sinkOverride = sink;
        return u;
    }

    private volatile java.util.function.Consumer<UserStreamEvents.Event> sinkOverride;

    public static List<String> parseUrls(String raw) {
        List<String> out = new ArrayList<>();
        if (raw == null) return out;
        for (String s : raw.split(",")) {
            String t = s.trim();
            if (t.isEmpty()) continue;
            out.add(t.contains("{key}") ? t : (t.endsWith("/") ? t + "{key}" : t + "/{key}"));
        }
        return Collections.unmodifiableList(out);
    }

    /** Thread rieng goi {@link #tick} moi giay. */
    public synchronized void start() {
        if (thread != null) return;
        thread = new Thread(() -> {
            while (!Thread.currentThread().isInterrupted()) {
                try {
                    tick(clock.getAsLong());
                } catch (Throwable t) {
                    LOG.error("[C3-LIVE-STREAM] loi vong: {}", t.toString());
                }
                try {
                    Thread.sleep(1_000L);
                } catch (InterruptedException ie) {
                    return;
                }
            }
        }, "C3LIVE-STREAM");
        thread.setDaemon(true);
        thread.start();
    }

    public synchronized void stop() {
        if (thread != null) thread.interrupt();
        thread = null;
        gen++;
        closeSocket();
        state = State.DISCONNECTED;
        if (listenKey != null) {
            try {
                gw.closeUserStream(listenKey);
            } catch (RuntimeException ignore) {
                // het han tu nhien
            }
        }
    }

    public boolean isConnected() {
        return state == State.CONNECTED;
    }

    public State state() {
        return state;
    }

    /** May trang thai: ket noi / keepAlive / fallback REST. */
    public void tick(long now) {
        boolean runFallback = false;
        synchronized (this) {
            if (state != State.CONNECTED && downSinceMs < 0) downSinceMs = now;
            switch (state) {
                case DISCONNECTED:
                    if (now >= nextAttemptMs) connect(now);
                    break;
                case CONNECTING:
                    if (now - connectStartMs > connectTimeoutMs) {
                        markDown(now, "ket noi qua han " + connectTimeoutMs + " ms", true);
                    }
                    break;
                case CONNECTED:
                    if (connectedSinceMs > 0 && now - connectedSinceMs > 60_000L) backoffMs = 1_000L;
                    if (now - lastKeepAliveMs >= KEEPALIVE_MS) {
                        lastKeepAliveMs = now;
                        try {
                            gw.keepAliveUserStream(listenKey);
                            api.onApiResult("keepAliveUserStream", true);
                            nKeepAlive.incrementAndGet();
                        } catch (RuntimeException e) {
                            api.onApiResult("keepAliveUserStream", false);
                            listenKey = null;
                            markDown(now, "keepAlive loi " + e.getClass().getSimpleName(), false);
                        }
                    }
                    if (needCatchUp) {
                        needCatchUp = false;
                        runFallback = true;
                        nCatchUp.incrementAndGet();
                    }
                    break;
                default:
                    break;
            }
            if (state != State.CONNECTED && downSinceMs >= 0 && now - downSinceMs >= 2_000L
                    && now - lastFallbackMs >= fallbackEveryMs) {
                lastFallbackMs = now;
                runFallback = true;
                if (now - lastDownWarnMs >= 300_000L) {
                    lastDownWarnMs = now;
                    LOG.warn("[C3-LIVE-STREAM] MAT user stream {}s => fallback REST (tra lenh treo + positions) moi {}s",
                            (now - downSinceMs) / 1000L, fallbackEveryMs / 1000L);
                }
                if (!downAlerted && now - downSinceMs >= alertDownMs) {
                    downAlerted = true;
                    alert.accept("[C3-LIVE-STREAM] mat user stream " + (now - downSinceMs) / 1000L
                            + "s => dang dung fallback REST, dang ket noi lai");
                }
            }
        }
        if (runFallback) {
            nFallback.incrementAndGet();
            try {
                fallback.run();
            } catch (Throwable t) {
                LOG.warn("[C3-LIVE-STREAM] fallback REST loi: {}", t.toString());
            }
        }
    }

    private void connect(long now) {
        try {
            if (listenKey == null) {
                listenKey = gw.startUserStream();
                api.onApiResult("startUserStream", true);
                lastKeepAliveMs = now;
            }
        } catch (RuntimeException e) {
            api.onApiResult("startUserStream", false);
            markDown(now, "khong lay duoc listenKey: " + e.getClass().getSimpleName(), false);
            return;
        }
        String tpl = urls.get(Math.floorMod(urlIdx, urls.size()));
        String url = tpl.replace("{key}", listenKey);
        final int g = ++gen;
        state = State.CONNECTING;
        connectStartMs = now;
        nConnect.incrementAndGet();
        LOG.info("[C3-LIVE-STREAM] ket noi #{} url_mau={} key={}..", nConnect.get(), tpl,
                listenKey.length() > 4 ? listenKey.substring(0, 4) : "?");
        try {
            socket = connector.open(url, new Listener() {
                @Override
                public void onOpen() {
                    opened(g);
                }

                @Override
                public void onText(String text) {
                    message(g, text);
                }

                @Override
                public void onClosed(String why) {
                    closed(g, why);
                }
            });
        } catch (RuntimeException e) {
            markDown(now, "mo websocket loi " + e.getClass().getSimpleName(), true);
        }
    }

    private synchronized void opened(int g) {
        if (g != gen) return;
        long now = clock.getAsLong();
        state = State.CONNECTED;
        connectedSinceMs = now;
        if (everConnected) {
            LOG.warn("[C3-LIVE-STREAM] ket noi LAI sau {}s => bu su kien bang REST 1 lan",
                    downSinceMs >= 0 ? Math.max(0L, now - downSinceMs) / 1000L : 0L);
            if (downAlerted) alert.accept("[C3-LIVE-STREAM] user stream da ket noi lai");
            needCatchUp = true;
        } else {
            LOG.info("[C3-LIVE-STREAM] da ket noi");
        }
        everConnected = true;
        downSinceMs = -1L;
        downAlerted = false;
    }

    private void message(int g, String text) {
        synchronized (this) {
            if (g != gen) return;
        }
        lastMsgMs = clock.getAsLong();
        nMsg.incrementAndGet();
        UserStreamEvents.Event e = UserStreamEvents.parse(text);
        if (e instanceof UserStreamEvents.ListenKeyExpired) {
            synchronized (this) {
                if (g != gen) return;
                listenKey = null;
                markDown(clock.getAsLong(), "listenKeyExpired", false);
            }
            return;
        }
        java.util.function.Consumer<UserStreamEvents.Event> so = sinkOverride;
        (so != null ? so : sink).accept(e);
    }

    private synchronized void closed(int g, String why) {
        if (g != gen) return;
        markDown(clock.getAsLong(), why == null ? "dong" : why, state == State.CONNECTING);
    }

    private void markDown(long now, String why, boolean rotate) {
        closeSocket();
        gen++;
        state = State.DISCONNECTED;
        nDown.incrementAndGet();
        if (downSinceMs < 0) downSinceMs = now;
        if (rotate) urlIdx++;
        nextAttemptMs = now + backoffMs;
        LOG.warn("[C3-LIVE-STREAM] mat ket noi ({}) => thu lai sau {} ms{}", why, backoffMs, rotate ? " (doi URL)" : "");
        backoffMs = Math.min(maxBackoffMs, backoffMs * 2);
    }

    private void closeSocket() {
        Socket s = socket;
        socket = null;
        if (s != null) {
            try {
                s.close();
            } catch (RuntimeException ignore) {
                // da dong
            }
        }
    }

    public long fallbackCount() {
        return nFallback.get();
    }

    /** So lan bu REST sau khi ket noi lai. */
    public long catchUpCount() {
        return nCatchUp.get();
    }

    public long connectCount() {
        return nConnect.get();
    }

    public String stats() {
        return "state=" + state + " msg=" + nMsg.get() + " connect=" + nConnect.get() + " down=" + nDown.get() + " fallback="
                + nFallback.get() + " keepAlive=" + nKeepAlive.get() + " lastMsgAgoS="
                + (lastMsgMs == 0 ? -1 : (clock.getAsLong() - lastMsgMs) / 1000L);
    }

    /** Ket noi prod bang okhttp (ping dinh ky phat hien ket noi chet; 0 = tat). */
    public static Connector okHttp(long pingMs) {
        final OkHttpClient http = new OkHttpClient.Builder().connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(0, TimeUnit.MILLISECONDS).pingInterval(Math.max(0L, pingMs), TimeUnit.MILLISECONDS)
                .retryOnConnectionFailure(false).build();
        return (url, l) -> {
            final WebSocket ws = http.newWebSocket(new Request.Builder().url(url).build(), new WebSocketListener() {
                @Override
                public void onOpen(WebSocket webSocket, Response response) {
                    l.onOpen();
                }

                @Override
                public void onMessage(WebSocket webSocket, String text) {
                    l.onText(text);
                }

                @Override
                public void onClosing(WebSocket webSocket, int code, String reason) {
                    webSocket.close(1000, null);
                    l.onClosed("closing " + code);
                }

                @Override
                public void onClosed(WebSocket webSocket, int code, String reason) {
                    l.onClosed("closed " + code);
                }

                @Override
                public void onFailure(WebSocket webSocket, Throwable t, Response response) {
                    l.onClosed("failure " + t.getClass().getSimpleName() + (response == null ? "" : " http=" + response.code()));
                }
            });
            return () -> {
                if (!ws.close(1000, "bye")) ws.cancel();
            };
        };
    }
}
