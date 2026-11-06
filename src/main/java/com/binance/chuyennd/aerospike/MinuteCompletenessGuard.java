package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayDeque;
import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Consumer;
import java.util.function.LongSupplier;

/**
 * [V12 R4r/R4s] Guard DO DU cua phut vua chot — CHI duong live ({@code DetectEntrySignal2TradeNormal}); sim/backtest khong co.
 *
 * <p>Su co 11-04 23:46Z: WS ingestor rot, nen chot chi 627/752 symbol; v_t_m quyet dinh luc :06 tren du lieu thieu.
 * <ul>
 *   <li>Nguong: phut {@code M} DU &lt;=&gt; so symbol co nen M trong cache &gt;= ceil(99 % x trung vi so symbol cua 60 phut DU gan nhat).
 *       [R4s A1 MIN-3] Tham chieu CHI gom phut da qua guard (phut MI khong vao) va KHONG het han theo thoi gian =&gt; su co keo dai
 *       (30', 2 h...) khong tu ha nguong. Mam ban dau (khi &lt; 30 phut DU) lay tu cache 60' truoc; &lt; 30 phut =&gt; khong kiem.</li>
 *   <li>Thieu =&gt; doc lai record phut M moi {@link #POLL_MS} toi khi du hoac toi giay +20 sau khi phut dong
 *       ({@code M + 60 s + 20 s}); khong bao gio cho qua moc nay.</li>
 *   <li>Van thieu =&gt; fail-closed phut do: KHONG mo lenh moi (vao/DCA, so giay + that), quan ly vi the/trailing/stop giu nguyen;
 *       log {@code [MINUTE-INCOMPLETE]} + dem.</li>
 *   <li>[R4s A1 MIN-2] MI lien tiep &gt;= {@link #ALERT_CONSEC} phut hoac &gt;= {@link #ALERT_N60} phut trong 60' =&gt; KHAN Telegram,
 *       chong spam: toi da 1 tin / {@link #ALERT_COOLDOWN_MIN} phut.</li>
 *   <li>Du ngay tu dau =&gt; khong doc them, khong doi gi (byte-identical r4q).</li>
 * </ul>
 * Tat khan cap: env {@code LIVE_MINUTE_GUARD=0}. Han che da biet: universe giam &gt; 1 % mot lan (delist hang loat) =&gt; moi phut MI +
 * KHAN toi khi restart (mam lai tu cache) hoac {@code LIVE_MINUTE_GUARD=0}.
 */
public final class MinuteCompletenessGuard {

    private static final Logger LOG = LoggerFactory.getLogger(MinuteCompletenessGuard.class);

    /** Nguong co dinh 99 % (so nguyen: need = ceil(99 * median / 100)). */
    public static final int RATIO_PCT = 99;
    public static final int LOOKBACK_MIN = 60;
    public static final int MIN_HISTORY = 30;
    /** Han cho: giay +20 sau khi phut dong. */
    public static final long DEADLINE_AFTER_CLOSE_MS = 20_000L;
    public static final long POLL_MS = 2_000L;
    /** [R4s MIN-2] KHAN khi MI lien tiep >= 3 hoac >= 5 phut MI trong 60'; toi da 1 tin / 30'. */
    public static final int ALERT_CONSEC = 3;
    public static final int ALERT_N60 = 5;
    public static final int ALERT_COOLDOWN_MIN = 30;

    public static final AtomicLong N_INCOMPLETE = new AtomicLong();
    public static final AtomicLong N_WAITED = new AtomicLong();
    public static final AtomicLong N_RECOVERED = new AtomicLong();
    public static final AtomicLong N_BLOCKED_LEGS = new AtomicLong();
    public static final AtomicLong N_ALERTS = new AtomicLong();

    /** Trang thai live (1 luong quyet dinh). Telegram tren thread daemon rieng, khong chan tick. */
    static final State LIVE = new State(m -> {
        Thread t = new Thread(() -> {
            try {
                Utils.sendSms2Telegram(m);
            } catch (Throwable e) {
                LOG.warn("[MINUTE-GUARD] gui Telegram loi: {}", e.getClass().getSimpleName());
            }
        }, "MINUTE-GUARD-ALERT");
        t.setDaemon(true);
        t.start();
    });

    private MinuteCompletenessGuard() {
    }

    public static boolean enabled() {
        String v = System.getenv("LIVE_MINUTE_GUARD");
        return v == null || !"0".equals(v.trim());
    }

    /** Tham chieu (phut DU) + dem MI de canh bao. */
    static final class State {
        /** phut -> so symbol, CHI phut DU; giu {@link #LOOKBACK_MIN} phut DU gan nhat, khong het han theo thoi gian. */
        final TreeMap<Long, Integer> good = new TreeMap<>();
        final ArrayDeque<Long> miMinutes = new ArrayDeque<>();
        int consecutive = 0;
        long lastAlertMinute = Long.MIN_VALUE;
        final Consumer<String> alertSink;

        State(Consumer<String> alertSink) {
            this.alertSink = alertSink;
        }

        void addGood(long minute, int have) {
            if (have <= 0) return;
            good.put(minute, have);
            while (good.size() > LOOKBACK_MIN) good.pollFirstEntry();
        }

        int median2() {
            int n = good.size();
            if (n < MIN_HISTORY) return -1;
            int[] v = good.values().stream().mapToInt(Integer::intValue).sorted().toArray();
            return (n % 2 == 1) ? 2 * v[n / 2] : v[n / 2 - 1] + v[n / 2];
        }

        /** Mam tu cache khi chua du phut DU (khoi dong): cac phut co nen trong 60' truoc. */
        void seed(LiveTickerWindow w, long endMinute) {
            long from = endMinute - LOOKBACK_MIN * Utils.TIME_MINUTE;
            int[] c = w.countsRange(from, LOOKBACK_MIN);
            for (int i = 0; i < c.length; i++) {
                long m = from + i * Utils.TIME_MINUTE;
                if (c[i] > 0 && !good.containsKey(m)) addGood(m, c[i]);
            }
        }

        void onComplete() {
            consecutive = 0;
        }

        void onIncomplete(Verdict v) {
            consecutive++;
            miMinutes.addLast(v.minute);
            while (!miMinutes.isEmpty() && miMinutes.peekFirst() <= v.minute - LOOKBACK_MIN * Utils.TIME_MINUTE) miMinutes.pollFirst();
            int n60 = miMinutes.size();
            if (consecutive < ALERT_CONSEC && n60 < ALERT_N60) return;
            if (lastAlertMinute != Long.MIN_VALUE && v.minute - lastAlertMinute < ALERT_COOLDOWN_MIN * Utils.TIME_MINUTE) return;
            lastAlertMinute = v.minute;
            long na = N_ALERTS.incrementAndGet();
            String msg = "[MINUTE-GUARD] KHAN: du lieu nen 1m THIEU — " + consecutive + " phut lien tiep, " + n60
                    + " phut/60' fail-closed (KHONG mo lenh moi; vi the/trailing/stop giu nguyen). " + v.line()
                    + ". Kiem ingestor collectData/WS. (toi da 1 tin/" + ALERT_COOLDOWN_MIN + "', tin thu " + na + ")";
            LOG.warn("{}", msg);
            try {
                alertSink.accept(msg);
            } catch (Throwable t) {
                LOG.warn("[MINUTE-GUARD] khong gui duoc canh bao: {}", t.getClass().getSimpleName());
            }
        }
    }

    /** Ket qua kiem 1 phut. */
    public static final class Verdict {
        public final long minute;
        public final boolean complete;
        public final boolean waited;
        public final int have;
        /** 2 x trung vi (giu nua don vi); -1 = khong du lich su. */
        public final int median2;
        public final int need;
        public final int polls;
        public final long waitedMs;

        Verdict(long minute, boolean complete, boolean waited, int have, int median2, int need, int polls, long waitedMs) {
            this.minute = minute;
            this.complete = complete;
            this.waited = waited;
            this.have = have;
            this.median2 = median2;
            this.need = need;
            this.polls = polls;
            this.waitedMs = waitedMs;
        }

        public double median() {
            return median2 < 0 ? Double.NaN : median2 / 2.0;
        }

        public String line() {
            return "phut=" + Utils.normalizeDateYYYYMMDDHHmm(minute) + " co=" + have + " can=" + need + " trung_vi60du="
                    + (median2 < 0 ? "NA" : (median2 % 2 == 0 ? String.valueOf(median2 / 2) : (median2 / 2) + ".5"))
                    + " cho=" + waitedMs + "ms doc_lai=" + polls;
        }
    }

    /** need = ceil(RATIO_PCT/100 x median) tinh bang so nguyen tren 2 x median. */
    static int need(int median2) {
        return (RATIO_PCT * median2 + 199) / 200;
    }

    public static Verdict check(LiveTickerWindow w, long endMinute) {
        return check(LIVE, w, endMinute, System::currentTimeMillis, Thread::sleep);
    }

    static Verdict check(State s, LiveTickerWindow w, long endMinute, LongSupplier clock, LiveTickerWindow.Sleeper sleeper) {
        if (s.good.size() < MIN_HISTORY) s.seed(w, endMinute);
        int m2 = s.median2();
        int have = w.countAt(endMinute);
        if (m2 < 0) {   // chua du lich su => khong kiem (dem vao tham chieu)
            s.addGood(endMinute, have);
            s.onComplete();
            return new Verdict(endMinute, true, false, have, -1, 0, 0, 0L);
        }
        int need = need(m2);
        if (have >= need) {   // du: 0 doc them
            s.addGood(endMinute, have);
            s.onComplete();
            return new Verdict(endMinute, true, false, have, m2, need, 0, 0L);
        }
        long deadline = endMinute + Utils.TIME_MINUTE + DEADLINE_AFTER_CLOSE_MS;
        long timeout = deadline - clock.getAsLong();
        long[] r = timeout > 0
                ? w.awaitMinuteComplete(endMinute, need, timeout, POLL_MS, sleeper, clock)
                : new long[]{have, 0L, 0L};
        boolean ok = r[0] >= need;
        boolean waited = r[1] > 0;
        Verdict v = new Verdict(endMinute, ok, waited, (int) r[0], m2, need, (int) r[1], r[2]);
        if (waited) N_WAITED.incrementAndGet();
        if (ok) {
            N_RECOVERED.incrementAndGet();
            s.addGood(endMinute, (int) r[0]);
            s.onComplete();
            LOG.warn("[MINUTE-WAIT] {} => DU sau khi cho (tong cho={} du={} thieu={})", v.line(), N_WAITED.get(), N_RECOVERED.get(),
                    N_INCOMPLETE.get());
        } else {
            long n = N_INCOMPLETE.incrementAndGet();
            LOG.warn("[MINUTE-INCOMPLETE] {} => KHONG mo lenh moi phut nay (quan ly vi the/trailing/stop giu nguyen) | tong_thieu={}"
                    + " tong_cho={} tong_du_sau_cho={} lien_tiep={}", v.line(), n, N_WAITED.get(), N_RECOVERED.get(), s.consecutive + 1);
            s.onIncomplete(v);
        }
        return v;
    }
}
