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
import java.util.Date;
import java.util.Map;
import java.util.TimeZone;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

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
 * <p>Env: {@code SOAK_HOURS} (mac dinh 26, 1..72), {@code LIVE_C3_WS_URLS}, {@code LIVE_C3_WS_PING_MS} (mac dinh 60000),
 * {@code LIVE_C3_KEYS_FILE} (C3LiveClientConfig).
 */
public final class UserStreamSoak {

    private static final Logger LOG = LoggerFactory.getLogger(UserStreamSoak.class);

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

    static String fmt(long ms) {
        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        f.setTimeZone(TimeZone.getTimeZone("Asia/Ho_Chi_Minh"));
        return f.format(new Date(ms)) + "+07";
    }

    public static void main(String[] args) throws Exception {
        double h = hours(System.getenv("SOAK_HOURS"));
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
        UserStream us = UserStream.forSink(gw, UserStream.okHttp(ping),
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
        LOG.warn("*** [WS-SOAK] BAT DAU {} — {} h, CHI DOC (khong lenh, khong DELETE listenKey), ping={} ms ***", fmt(t0), h, ping);
        us.start();
        SoakGapMonitor mon = new SoakGapMonitor();
        long nextStat = t0 + 600_000L;
        while (System.currentTimeMillis() < end) {
            long now = System.currentTimeMillis();
            SoakGapMonitor.Gap g = mon.sample(now, us.isConnected());
            if (g != null) {
                LOG.warn("[WS-SOAK] KHE HO #{}: mat {} -> co lai {} = {} s; truoc do ket noi lien {} h{}", mon.gaps().size(),
                        fmt(g.downAtMs), fmt(g.upAtMs), g.gapMs() / 1000d, String.format("%.2f", g.connectedForMs / 3_600_000d),
                        g.is24hCut() ? " => CAT 24h" : "");
            }
            if (now >= nextStat) {
                nextStat = now + 600_000L;
                LOG.info("[WS-SOAK] t+{}h {} | keepAlive ok={} loi={} | listenKey POST ok={} loi={} | khe_ho={} max_khe_ho_s={}"
                                + " | max_ket_noi_lien_h={} | su_kien={} | chan={}",
                        String.format("%.2f", (now - t0) / 3_600_000d), us.stats(), kaOk.get(), kaFail.get(), lkOk.get(), lkFail.get(),
                        mon.gaps().size(), mon.maxGapMs() / 1000d, String.format("%.2f", mon.maxConnectedMs() / 3_600_000d), evCount,
                        SoakGuard.blockedCount());
            }
            Thread.sleep(1_000L);
        }
        boolean pass = mon.cut24hSeen() && us.isConnected() && SoakGuard.blockedCount() == 0;
        LOG.warn("*** [WS-SOAK] KET THUC {} | {} | KET_QUA={} (can: thay cat ~24h + ket noi lai + 0 goi bi chan) | keepAlive ok={} loi={}"
                        + " | khe_ho={} max_s={} | max_ket_noi_lien_h={} | su_kien={} ***", fmt(System.currentTimeMillis()), us.stats(),
                pass ? "DAT" : "CHUA_DAT", kaOk.get(), kaFail.get(), mon.gaps().size(), mon.maxGapMs() / 1000d,
                String.format("%.2f", mon.maxConnectedMs() / 3_600_000d), evCount);
        for (SoakGapMonitor.Gap g : mon.gaps()) {
            LOG.warn("[WS-SOAK] khe_ho mat={} lai={} s={} ket_noi_truoc_h={}", fmt(g.downAtMs), fmt(g.upAtMs), g.gapMs() / 1000d,
                    String.format("%.2f", g.connectedForMs / 3_600_000d));
        }
        // KHONG goi us.stop() (DELETE listenKey) — thoat JVM: socket dong, listenKey tu het han.
        System.exit(pass ? 0 : 3);
    }
}
