package com.binance.chuyennd.c3live.alert;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;

/**
 * [V12] Canh bao c3_live qua Telegram bang co che SAN CO cua repo ({@code Utils.sendSms2Telegram}, khong them token,
 * khong log token). Gui BAT DONG BO (1 thread daemon, hang doi 100, day thi bo) de khong chan tick/luong lenh.
 * Moi canh bao cung ghi WARN {@code [C3-LIVE-ALERT]}. Escape HTML (parse_mode=HTML).
 */
public final class C3LiveAlerts {

    private static final Logger LOG = LoggerFactory.getLogger(C3LiveAlerts.class);

    private final Consumer<String> sender;
    private final ThreadPoolExecutor ex;

    public C3LiveAlerts(Consumer<String> sender) {
        this.sender = sender;
        this.ex = new ThreadPoolExecutor(1, 1, 0L, TimeUnit.MILLISECONDS, new ArrayBlockingQueue<>(100), r -> {
            Thread t = new Thread(r, "C3LIVE-ALERT");
            t.setDaemon(true);
            return t;
        }, new ThreadPoolExecutor.DiscardPolicy());
    }

    public void send(String msg) {
        String m = msg == null ? "" : msg;
        LOG.warn("[C3-LIVE-ALERT] {}", m);
        String body = escapeHtml(m.startsWith("[C3-LIVE]") || m.startsWith("[KILLSW]") ? m : "[C3-LIVE] " + m);
        try {
            ex.execute(() -> {
                try {
                    sender.accept(body);
                } catch (Throwable t) {
                    LOG.warn("[C3-LIVE-ALERT] gui Telegram loi: {}", t.getClass().getSimpleName());
                }
            });
        } catch (Throwable t) {
            LOG.warn("[C3-LIVE-ALERT] khong xep hang duoc canh bao: {}", t.getClass().getSimpleName());
        }
    }

    static String escapeHtml(String s) {
        StringBuilder b = new StringBuilder(s.length() + 16);
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '&': b.append("&amp;"); break;
                case '<': b.append("&lt;"); break;
                case '>': b.append("&gt;"); break;
                default: b.append(c);
            }
        }
        return b.toString();
    }
}
