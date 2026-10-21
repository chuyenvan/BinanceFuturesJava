package com.binance.chuyennd.ops;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

/**
 * [EXEC-PROBE 2026-10-21] Nguon so qua websocket PUBLIC Binance USD-M (khong API key, khong REST). Moi lo: MOT ket noi
 * combined stream {@code <sym>@depth<N>@100ms} cho &lt;= maxStreams symbol, giu message DAU TIEN moi symbol, dong ket
 * noi ngay khi du (hoac het timeout). Khong co ket noi thuong truc. Base URL xoay vong khi 2 lo lien tiep khong nhan
 * duoc message nao (vd Binance doi duong /public vs /market — KlineWsClient 2026-10-10).
 */
final class ExecProbeWsSource implements ExecProbe.BookSource {

    private static final Logger LOG = LoggerFactory.getLogger(ExecProbeWsSource.class);

    private final List<String> bases;
    private final int depth;
    private final OkHttpClient http;
    private final AtomicLong connects = new AtomicLong();
    private final AtomicLong failures = new AtomicLong();
    private volatile int baseIdx = 0;
    private int emptyStreak = 0;

    ExecProbeWsSource(List<String> bases, int depth) {
        this.bases = bases;
        this.depth = depth;
        this.http = new OkHttpClient.Builder().connectTimeout(5, TimeUnit.SECONDS)
                .readTimeout(0, TimeUnit.MILLISECONDS).retryOnConnectionFailure(false).build();
    }

    /** URL combined stream (thuan, test duoc). */
    static String url(String base, List<String> symbols, int depth) {
        StringBuilder sb = new StringBuilder(base);
        for (int i = 0; i < symbols.size(); i++) {
            if (i > 0) sb.append('/');
            sb.append(symbols.get(i).toLowerCase(Locale.ROOT)).append("@depth").append(depth).append("@100ms");
        }
        return sb.toString();
    }

    /**
     * Gom message theo symbol cho MOT lo (tach rieng de unit test bang message gia — khong can mang).
     * Giu message dau tien hop le cua moi symbol mong doi; loi ket noi => mo khoa ngay.
     */
    static final class Collector {
        final Set<String> want;
        final Map<String, ExecProbeBook.Book> got = new ConcurrentHashMap<>();
        final CountDownLatch latch;
        volatile String failure;

        Collector(List<String> symbols) {
            this.want = new HashSet<>();
            for (String s : symbols) want.add(s.toUpperCase(Locale.ROOT));
            this.latch = new CountDownLatch(want.size());
        }

        void onText(String text, long recvMs) {
            ExecProbeBook.Book b = ExecProbeBook.parseDepth(text, recvMs);
            if (b == null || !want.contains(b.symbol)) return;
            if (got.putIfAbsent(b.symbol, b) == null) latch.countDown();
        }

        void onFail(String why) {
            failure = why;
            while (latch.getCount() > 0) latch.countDown();
        }

        boolean await(long ms) throws InterruptedException {
            return latch.await(ms, TimeUnit.MILLISECONDS);
        }
    }

    @Override
    public Map<String, ExecProbeBook.Book> snapshot(List<String> symbols, Map<String, Double> refPx, long timeoutMs) {
        if (symbols == null || symbols.isEmpty()) return new HashMap<>();
        final Collector c = new Collector(symbols);
        String base = bases.get(Math.floorMod(baseIdx, bases.size()));
        WebSocket ws = null;
        Map<String, ExecProbeBook.Book> out = null;
        String fail = null;
        try {
            connects.incrementAndGet();
            ws = http.newWebSocket(new Request.Builder().url(url(base, symbols, depth)).build(), new WebSocketListener() {
                @Override
                public void onMessage(WebSocket webSocket, String text) {
                    c.onText(text, System.currentTimeMillis());
                }

                @Override
                public void onFailure(WebSocket webSocket, Throwable t, Response response) {
                    c.onFail(t.getClass().getSimpleName() + (response == null ? "" : " http=" + response.code()));
                }

                @Override
                public void onClosing(WebSocket webSocket, int code, String reason) {
                    c.onFail("closing " + code);
                }
            });
            c.await(timeoutMs);
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
        } catch (Throwable t) {
            c.onFail(t.getClass().getSimpleName());
        } finally {
            // chot ket qua TRUOC khi dong (onFailure do cancel() ben duoi khong duoc tinh la loi)
            out = new HashMap<>(c.got);
            fail = c.failure;
            if (ws != null) {
                boolean graceful = false;
                try {
                    graceful = ws.close(1000, "probe-done");   // okhttp tu cancel neu san khong tra close sau 60 s
                } catch (Throwable t) {
                    graceful = false;
                }
                if (!graceful) ws.cancel();
            }
        }
        if (fail != null) failures.incrementAndGet();
        rotateIfDead(out.isEmpty(), base, fail, symbols.size());
        return out;
    }

    private void rotateIfDead(boolean empty, String base, String failure, int n) {
        if (!empty) {
            emptyStreak = 0;
            return;
        }
        emptyStreak++;
        LOG.warn("{} lo {} symbol KHONG nhan duoc so (base={} loi={}) streak={}", ExecProbe.TAG, n, base,
                failure == null ? "timeout" : failure, emptyStreak);
        if (emptyStreak >= 2 && bases.size() > 1) {
            baseIdx = Math.floorMod(baseIdx + 1, bases.size());
            emptyStreak = 0;
            LOG.warn("{} doi base websocket -> {}", ExecProbe.TAG, bases.get(baseIdx));
        }
    }

    @Override
    public String name() {
        return "ws";
    }

    @Override
    public long connects() {
        return connects.get();
    }

    long failures() {
        return failures.get();
    }

    int baseIdx() {
        return baseIdx;
    }
}
