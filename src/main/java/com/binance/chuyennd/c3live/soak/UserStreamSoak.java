package com.binance.chuyennd.c3live.soak;

import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.client.C3LiveClient;
import com.binance.chuyennd.c3live.client.C3LiveClientConfig;
import com.binance.chuyennd.c3live.fill.UserStream;
import com.binance.chuyennd.c3live.fill.UserStreamEvents;
import com.binance.chuyennd.c3live.rate.RateGuard;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.TimeZone;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.LongSupplier;

/**
 * [V12 R4h] SOAK user-data stream tai khoan chinh — CHI DOC, KHONG dat/huy lenh, KHONG BAO GIO DELETE listenKey.
 *
 * <p>Muc dich: production chua tung chay user-data stream qua 12 h (restart 12h che). Mo stream &gt;= 26 h bang CHINH may trang
 * thai {@link UserStream} cua c3_live (keepAlive 30', backoff 1-60 s, xoay URL), ghi: keepAlive listenKey (ok/loi), luc bi cat
 * (ky vong ~24 h ket noi), ket noi lai, khe ho. Su kien tai khoan (lenh LEGACY...) chi DEM theo loai, khong ghi noi dung.
 *
 * <p>An toan (ROUND4H §3): gateway boc {@link SoakGuard#readOnly} — chi POST/PUT listenKey; {@code UserStream.stop()} (DELETE)
 * KHONG bao gio duoc goi; ket thuc = {@code System.exit} (socket dong, listenKey tu het han &lt;= 60'). LEGACY v1.1 khong dung
 * user-data stream (kiem code + log + socket 242, ROUND4H §3).
 *
 * <p>[V12 R4l] {@code SOAK_FORCE_CLOSE_MIN} (trong/0 = tat): bai thu KET NOI LAI CUONG BUC (docs/c3live/SOAK_ADDENDUM_R4L_FORCE_RECONNECT.md)
 * — {@link ForceCloseConnector} boc Connector production, client dong socket hien tai moi N phut, {@link #FORCE_CLOSE_N} lan;
 * UserStream (KHONG sua) tu ket noi lai qua duong onClosed. KET_QUA theo {@link #forcePass}.
 *
 * <p>Env: {@code SOAK_HOURS} (mac dinh 26, 1..72), {@code SOAK_FORCE_CLOSE_MIN}, {@code LIVE_C3_WS_URLS}, {@code LIVE_C3_WS_PING_MS}
 * (mac dinh 60000), {@code LIVE_C3_KEYS_FILE} (C3LiveClientConfig).
 */
public final class UserStreamSoak {

    private static final Logger LOG = LoggerFactory.getLogger(UserStreamSoak.class);
    /** [V12 R4l] so lan dong cuong buc. */
    static final int FORCE_CLOSE_N = 6;
    /** [V12 R4l] tran thoi gian ket noi lai (p100) cua tieu chi DAT. */
    static final long FORCE_RECONNECT_MAX_MS = 10_000L;

    private UserStreamSoak() {
    }

    static double hours(String raw) {
        try {
            double h = raw == null || raw.trim().isEmpty() ? 26d : Double.parseDouble(raw.trim());
            return h >= 1d && h <= 72d ? h : 26d;
        } catch (NumberFormatException e) {
            return 26d;
        }
    }

    /** [V12 R4l] trong / 0 = tat (soak thuong); 1..60 = so phut giua 2 lan dong; gia tri khac = 10. */
    static int forceCloseMin(String raw) {
        if (raw == null || raw.trim().isEmpty()) return 0;
        try {
            int m = Integer.parseInt(raw.trim());
            if (m == 0) return 0;
            return m >= 1 && m <= 60 ? m : 10;
        } catch (NumberFormatException e) {
            return 10;
        }
    }

    /** [V12 R4l] tieu chi DAT (ADDENDUM R4l muc 1-5 + ket thuc dang ket noi). */
    static boolean forcePass(long forced, List<Long> reconnectMs, int nGaps, long maxGapMs, long kaFail, long lkFail, long blocked,
                             boolean connected) {
        if (forced != FORCE_CLOSE_N || reconnectMs == null || reconnectMs.size() != FORCE_CLOSE_N) return false;
        long p100 = maxOf(reconnectMs);
        return p100 >= 0 && p100 <= FORCE_RECONNECT_MAX_MS && nGaps <= FORCE_CLOSE_N
                && maxGapMs <= Math.min(FORCE_RECONNECT_MAX_MS, p100 + 1_000L)
                && kaFail == 0 && lkFail == 0 && blocked == 0 && connected;
    }

    static long maxOf(List<Long> xs) {
        long m = -1L;
        for (Long x : xs) if (x != null && x > m) m = x;
        return m;
    }

    /**
     * [V12 R4l] Boc {@link UserStream.Connector} production: nho socket moi nhat; {@link #forceClose()} dong socket do (client
     * close) — san tra close frame => Listener.onClosed => UserStream.closed => markDown => ket noi lai (code production, KHONG
     * sua). Thoi gian ket noi lai = tu luc dong den onOpen cua socket ke tiep. Khong goi REST nao.
     */
    static final class ForceCloseConnector implements UserStream.Connector {
        private final UserStream.Connector inner;
        private final LongSupplier clock;
        private volatile UserStream.Socket last;
        private volatile long closeAtMs = -1L;
        private final List<Long> reconnectMs = new CopyOnWriteArrayList<>();
        private final AtomicLong forced = new AtomicLong();

        ForceCloseConnector(UserStream.Connector inner, LongSupplier clock) {
            this.inner = inner;
            this.clock = clock;
        }

        @Override
        public UserStream.Socket open(String url, UserStream.Listener l) {
            UserStream.Socket s = inner.open(url, new UserStream.Listener() {
                @Override
                public void onOpen() {
                    long c = closeAtMs;
                    if (c >= 0) {
                        long d = clock.getAsLong() - c;
                        reconnectMs.add(d);
                        closeAtMs = -1L;
                        LOG.warn("[WS-SOAK] KET NOI LAI sau dong cuong buc #{} = {} s", forced.get(), d / 1000d);
                    }
                    l.onOpen();
                }

                @Override
                public void onText(String text) {
                    l.onText(text);
                }

                @Override
                public void onClosed(String why) {
                    l.onClosed(why);
                }
            });
            last = s;
            return s;
        }

        /** @return false neu chua co socket hoac lan dong truoc chua ket noi lai. */
        synchronized boolean forceClose() {
            UserStream.Socket s = last;
            if (s == null || closeAtMs >= 0) return false;
            closeAtMs = clock.getAsLong();
            long n = forced.incrementAndGet();
            LOG.warn("[WS-SOAK] DONG CUONG BUC #{} luc {} (client dong socket; UserStream tu ket noi lai)", n, fmt(closeAtMs));
            s.close();
            return true;
        }

        long forced() {
            return forced.get();
        }

        List<Long> reconnectMs() {
            return new ArrayList<>(reconnectMs);
        }

        boolean pending() {
            return closeAtMs >= 0;
        }
    }

    static String fmt(long ms) {
        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        f.setTimeZone(TimeZone.getTimeZone("Asia/Ho_Chi_Minh"));
        return f.format(new Date(ms)) + "+07";
    }

    public static void main(String[] args) throws Exception {
        double h = hours(System.getenv("SOAK_HOURS"));
        int fcMin = forceCloseMin(System.getenv("SOAK_FORCE_CLOSE_MIN"));
        long ping = 60_000L;
        try {
            String p = System.getenv("LIVE_C3_WS_PING_MS");
            if (p != null && !p.trim().isEmpty()) ping = Math.max(0L, Long.parseLong(p.trim()));
        } catch (NumberFormatException ignore) {
            ping = 60_000L;
        }
        String urls = System.getenv("LIVE_C3_WS_URLS");
        RateGuard rg = RateGuard.defaults();
        C3LiveClient client = C3LiveClient.create(C3LiveClientConfig.fromEnv(), rg);
        ExchangeGateway gw = SoakGuard.readOnly(client);
        final Map<String, AtomicLong> evCount = new ConcurrentHashMap<>();
        final AtomicLong kaOk = new AtomicLong(), kaFail = new AtomicLong(), lkOk = new AtomicLong(), lkFail = new AtomicLong();
        UserStream.Connector conn = UserStream.okHttp(ping);
        final ForceCloseConnector fc = fcMin > 0 ? new ForceCloseConnector(conn, System::currentTimeMillis) : null;
        UserStream us = UserStream.forSink(gw, fc != null ? fc : conn,
                UserStream.parseUrls(urls == null || urls.trim().isEmpty() ? UserStream.DEFAULT_URLS : urls),
                (UserStreamEvents.Event e) -> evCount.computeIfAbsent(e == null ? "null" : e.type, k -> new AtomicLong()).incrementAndGet(),
                m -> LOG.warn("[WS-SOAK] canh bao stream: {}", m),
                (api, ok) -> {
                    long now = System.currentTimeMillis();
                    if ("keepAliveUserStream".equals(api)) {
                        (ok ? kaOk : kaFail).incrementAndGet();
                        LOG.info("[WS-SOAK] KEEPALIVE {} luc {} (ok={} loi={})", ok ? "OK" : "LOI", fmt(now), kaOk.get(), kaFail.get());
                    } else if ("startUserStream".equals(api)) {
                        (ok ? lkOk : lkFail).incrementAndGet();
                        LOG.info("[WS-SOAK] LISTENKEY POST {} luc {}", ok ? "OK" : "LOI", fmt(now));
                    }
                },
                System::currentTimeMillis, 15_000L, 60_000L);
        long t0 = System.currentTimeMillis();
        long end = t0 + (long) (h * 3_600_000d);
        LOG.warn("*** [WS-SOAK] BAT DAU {} — {} h, CHI DOC (khong lenh, khong DELETE listenKey), ping={} ms{} ***", fmt(t0), h, ping,
                fc != null ? " | DONG CUONG BUC moi " + fcMin + "' x " + FORCE_CLOSE_N + " lan (ADDENDUM R4l)" : "");
        us.start();
        SoakGapMonitor mon = new SoakGapMonitor();
        long nextStat = t0 + 600_000L;
        long nextForce = fc != null ? t0 + fcMin * 60_000L : Long.MAX_VALUE;
        while (System.currentTimeMillis() < end) {
            long now = System.currentTimeMillis();
            SoakGapMonitor.Gap g = mon.sample(now, us.isConnected());
            if (g != null) {
                LOG.warn("[WS-SOAK] KHE HO #{}: mat {} -> co lai {} = {} s; truoc do ket noi lien {} h{}", mon.gaps().size(),
                        fmt(g.downAtMs), fmt(g.upAtMs), g.gapMs() / 1000d, String.format("%.2f", g.connectedForMs / 3_600_000d),
                        g.is24hCut() ? " => CAT 24h" : "");
            }
            if (fc != null && fc.forced() < FORCE_CLOSE_N && now >= nextForce && us.isConnected() && fc.forceClose()) {
                nextForce = now + fcMin * 60_000L;
            }
            if (now >= nextStat) {
                nextStat = now + 600_000L;
                LOG.info("[WS-SOAK] t+{}h {} | keepAlive ok={} loi={} | listenKey POST ok={} loi={} | khe_ho={} max_khe_ho_s={}"
                                + " | max_ket_noi_lien_h={} | su_kien={} | chan={}{}",
                        String.format("%.2f", (now - t0) / 3_600_000d), us.stats(), kaOk.get(), kaFail.get(), lkOk.get(), lkFail.get(),
                        mon.gaps().size(), mon.maxGapMs() / 1000d, String.format("%.2f", mon.maxConnectedMs() / 3_600_000d), evCount,
                        SoakGuard.blockedCount(), fc == null ? "" : " | dong_cuong_buc=" + fc.forced() + " ket_noi_lai_ms=" + fc.reconnectMs());
            }
            Thread.sleep(1_000L);
        }
        boolean pass;
        String need;
        String extra = "";
        if (fc != null) {
            List<Long> rec = fc.reconnectMs();
            pass = forcePass(fc.forced(), rec, mon.gaps().size(), mon.maxGapMs(), kaFail.get(), lkFail.get(), SoakGuard.blockedCount(),
                    us.isConnected());
            need = "can: dong 6 + ket noi lai 6/6, p100<=10s, khe_ho<=6 va max<=min(10s,p100+1s), keepAlive/POST loi=0, 0 goi bi chan";
            extra = " | dong_cuong_buc=" + fc.forced() + " ket_noi_lai=" + rec.size() + " p100_s=" + maxOf(rec) / 1000d
                    + " ket_noi_lai_ms=" + rec + " dang_cho=" + fc.pending() + " | listenKey POST ok=" + lkOk.get() + " loi=" + lkFail.get()
                    + " | chan=" + SoakGuard.blockedCount();
        } else {
            pass = mon.cut24hSeen() && us.isConnected() && SoakGuard.blockedCount() == 0;
            need = "can: thay cat ~24h + ket noi lai + 0 goi bi chan";
        }
        LOG.warn("*** [WS-SOAK] KET THUC {} | {} | KET_QUA={} ({}) | keepAlive ok={} loi={}"
                        + " | khe_ho={} max_s={} | max_ket_noi_lien_h={} | su_kien={}{} ***", fmt(System.currentTimeMillis()), us.stats(),
                pass ? "DAT" : "CHUA_DAT", need, kaOk.get(), kaFail.get(), mon.gaps().size(), mon.maxGapMs() / 1000d,
                String.format("%.2f", mon.maxConnectedMs() / 3_600_000d), evCount, extra);
        for (SoakGapMonitor.Gap g : mon.gaps()) {
            LOG.warn("[WS-SOAK] khe_ho mat={} lai={} s={} ket_noi_truoc_h={}", fmt(g.downAtMs), fmt(g.upAtMs), g.gapMs() / 1000d,
                    String.format("%.2f", g.connectedForMs / 3_600_000d));
        }
        // KHONG goi us.stop() (DELETE listenKey) — thoat JVM: socket dong, listenKey tu het han.
        System.exit(pass ? 0 : 3);
    }
}
