package com.binance.chuyennd.tradecore;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.function.BiConsumer;

/**
 * [QUEUE_1015 P5 2026-10-15] KILL-SWITCH theo equity — <b>MAC DINH TAT, CHUA DEPLOY</b>.
 *
 * <p>Theo doi equity paper/live va tu dong ha bac khi drawdown (DD tu dinh) hoac so ngay
 * khong lap dinh (UW = under-water days) vuot nguong.
 *
 * <p><b>Ba bac:</b>
 * <ul>
 *   <li>{@link State#WARN} — canh bao (Telegram), KHONG doi hanh vi giao dich.</li>
 *   <li>{@link State#PAUSE} — <i>khong mo lenh MOI</i> nhung VAN quan ly vi the dang co
 *       (trailing/SL/time-stop chay binh thuong).</li>
 *   <li>{@link State#STOP} — dung han: khong mo lenh moi (owner quyet viec con quan ly hay khong).</li>
 * </ul>
 *
 * <p><b>Tham so DOC TU CONFIG, KHONG dat gia tri o day</b> (owner chot khau vi). Key nao VANG
 * thi bac tuong ung KHONG bao gio kich hoat (inert). Cac key:
 * <pre>
 *   KILL_SWITCH_ENABLED        (bool, mac dinh false)
 *   KILL_SWITCH_DD_WARN        (phan so, vd 0.10 = -10% tu dinh)
 *   KILL_SWITCH_DD_PAUSE
 *   KILL_SWITCH_DD_STOP
 *   KILL_SWITCH_UW_DAYS_WARN   (so ngay ke tu dinh)
 *   KILL_SWITCH_UW_DAYS_PAUSE
 *   KILL_SWITCH_DD_RESUME      (phuc hoi: DD nho hon muc nay va UW ngan => ve NORMAL)
 *   KILL_SWITCH_NOTIFY         (bool, mac dinh false; gui Telegram qua kenh healthcheck)
 * </pre>
 *
 * <p><b>Parity sim:</b> lop nay KHONG duoc tham chieu tu {@code SimulatorMarketLevelTicker1MStopLoss}
 * hay bat ky duong sim nao => ai khong goi thi khong co tac dung phu; moi key mac dinh TAT.
 */
public final class KillSwitch {

    private static final Logger LOG = LoggerFactory.getLogger(KillSwitch.class);

    public enum State {DISABLED, NORMAL, WARN, PAUSE, STOP}

    private static final long DAY_MS = 86_400_000L;

    private final boolean enabled;
    private final boolean notify;
    private final float ddWarn;
    private final float ddPause;
    private final float ddStop;
    private final float ddResume;
    private final float uwWarn;
    private final float uwPause;

    private double peakEquity = Double.NaN;
    private long peakTs = Long.MIN_VALUE;
    private State state;

    /** Doc tham so tu config. Mac dinh: TAT. */
    public KillSwitch() {
        this(boolKey("KILL_SWITCH_ENABLED", false), boolKey("KILL_SWITCH_NOTIFY", false),
                floatKey("KILL_SWITCH_DD_WARN"), floatKey("KILL_SWITCH_DD_PAUSE"),
                floatKey("KILL_SWITCH_DD_STOP"), floatKey("KILL_SWITCH_DD_RESUME"),
                floatKey("KILL_SWITCH_UW_DAYS_WARN"), floatKey("KILL_SWITCH_UW_DAYS_PAUSE"));
    }

    /** Constructor day du (dung cho test va cho owner cam tham so tu config tuy y). */
    public KillSwitch(boolean enabled, boolean notify, float ddWarn, float ddPause, float ddStop,
                      float ddResume, float uwWarn, float uwPause) {
        this.enabled = enabled;
        this.notify = notify;
        this.ddWarn = ddWarn;
        this.ddPause = ddPause;
        this.ddStop = ddStop;
        this.ddResume = ddResume;
        this.uwWarn = uwWarn;
        this.uwPause = uwPause;
        this.state = enabled ? State.NORMAL : State.DISABLED;
    }

    /** Hook gui canh bao (mac dinh no-op; production noi vao kenh Telegram healthcheck). */
    private BiConsumer<State, String> notifier = (s, m) -> {
    };

    public boolean enabled() {
        return enabled;
    }

    public State state() {
        return state;
    }

    /** True = KHONG duoc mo lenh moi (PAUSE hoac STOP). Quan ly vi the dang co KHONG bi chan. */
    public boolean blocksNewEntries() {
        return state == State.PAUSE || state == State.STOP;
    }

    /** True = dung han (khong mo lenh moi; owner quyet co quan ly vi the hay khong). */
    public boolean halted() {
        return state == State.STOP;
    }

    public double peakEquity() {
        return peakEquity;
    }

    public long peakTs() {
        return peakTs;
    }

    public void setNotifier(BiConsumer<State, String> n) {
        if (n != null) {
            this.notifier = n;
        }
    }

    /**
     * Cap nhat equity (paper hoac live). Tra ve trang thai moi. Ham thuan; chi goi notifier khi
     * NOTIFY bat VA trang thai DOI (khong spam).
     *
     * @param equity equity hien tai (phai &gt; 0; neu khong thi bo qua)
     * @param tsMs   moc thoi gian (ms)
     */
    public State onEquity(double equity, long tsMs) {
        if (!enabled) {
            return State.DISABLED;
        }
        if (!(equity > 0)) {
            return state;
        }
        if (Double.isNaN(peakEquity) || equity > peakEquity) {
            peakEquity = equity;
            peakTs = tsMs;
        }
        double dd = peakEquity > 0 ? (peakEquity - equity) / peakEquity : 0.0;
        double uwDays = (peakTs == Long.MIN_VALUE) ? 0.0 : (tsMs - peakTs) / (double) DAY_MS;

        State next = nextState(dd, uwDays, state);
        if (next != state) {
            String msg = String.format(
                    "KILL-SWITCH %s -> %s (equity=%.2f peak=%.2f DD=%.2f%% UW=%.1f ngay)",
                    state, next, equity, peakEquity, dd * 100.0, uwDays);
            LOG.warn("[KILL-SWITCH] {}", msg);
            state = next;
            if (notify) {
                try {
                    notifier.accept(next, msg);
                } catch (RuntimeException e) {
                    LOG.error("[KILL-SWITCH] gui canh bao loi", e);
                }
            }
        }
        return state;
    }

    private State nextState(double dd, double uwDays, State cur) {
        // STOP > PAUSE > WARN, xet ca DD va UW (lay muc nang nhat). Key vang => inert.
        // EPS: nguong la float, dd la double => so sanh co dung sai 1e-9 de tranh truot bien (vd 0.95).
        boolean stop = ge(dd, ddStop);
        boolean pause = ge(dd, ddPause) || ge(uwDays, uwPause);
        boolean warn = ge(dd, ddWarn) || ge(uwDays, uwWarn);

        if (stop) {
            return State.STOP;
        }
        if (pause) {
            return State.PAUSE;
        }
        if (warn) {
            return State.WARN;
        }
        // phuc hoi: tu WARN/PAUSE ve NORMAL khi DD < nguong resume (neu khai) va UW ngan.
        if (cur == State.WARN || cur == State.PAUSE) {
            boolean okDd = Float.isNaN(ddResume) || (float) dd < ddResume;
            boolean okUw = Float.isNaN(uwWarn) || (float) uwDays < uwWarn;
            if (okDd && okUw) {
                return State.NORMAL;
            }
            return cur;
        }
        return State.NORMAL;
    }

    private static boolean ge(double v, float thr) {
        // Nguong doc tu config la float => so sanh trong khong gian float (tranh lech 0.10f > 0.1 double).
        return !Float.isNaN(thr) && (float) v >= thr;
    }

    // --- helpers doc config ---
    private static boolean boolKey(String k, boolean dflt) {
        String v = Cfg.getOr(k, "").trim();
        if (v.isEmpty()) {
            return dflt;
        }
        return "1".equals(v) || "true".equalsIgnoreCase(v);
    }

    private static float floatKey(String k) {
        String v = Cfg.getOr(k, "").trim();
        if (v.isEmpty()) {
            return Float.NaN;
        }
        try {
            return Float.parseFloat(v);
        } catch (NumberFormatException e) {
            return Float.NaN;
        }
    }
}
