package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Arrays;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.LongSupplier;

/**
 * [V12 R4r] Guard DO DU cua phut vua chot — CHI duong live ({@code DetectEntrySignal2TradeNormal}); sim/backtest khong co.
 *
 * <p>Su co 11-04 23:46Z: WS ingestor rot, nen chot chi 627/752 symbol; v_t_m quyet dinh luc :06 tren du lieu thieu.
 * <ul>
 *   <li>Nguong co dinh: phut {@code M} DU &lt;=&gt; so symbol co nen M trong cache &gt;= ceil(99 % x trung vi so symbol 60 phut truoc)
 *       (trung vi tinh tren phut co du lieu; &lt; 30 phut lich su =&gt; khong kiem).</li>
 *   <li>Thieu =&gt; doc lai record phut M moi {@link #POLL_MS} toi khi du hoac toi giay +20 sau khi phut dong
 *       ({@code M + 60 s + 20 s}); khong bao gio cho qua moc nay.</li>
 *   <li>Van thieu =&gt; fail-closed phut do: KHONG mo lenh moi (vao/DCA, so giay + that), quan ly vi the/trailing/stop giu nguyen;
 *       log {@code [MINUTE-INCOMPLETE]} + dem.</li>
 *   <li>Du ngay tu dau =&gt; khong doc them, khong doi gi (byte-identical r4q).</li>
 * </ul>
 * Tat khan cap: env {@code LIVE_MINUTE_GUARD=0}.
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

    public static final AtomicLong N_INCOMPLETE = new AtomicLong();
    public static final AtomicLong N_WAITED = new AtomicLong();
    public static final AtomicLong N_RECOVERED = new AtomicLong();
    public static final AtomicLong N_BLOCKED_LEGS = new AtomicLong();

    private MinuteCompletenessGuard() {
    }

    public static boolean enabled() {
        String v = System.getenv("LIVE_MINUTE_GUARD");
        return v == null || !"0".equals(v.trim());
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
            return "phut=" + Utils.normalizeDateYYYYMMDDHHmm(minute) + " co=" + have + " can=" + need + " trung_vi60="
                    + (median2 < 0 ? "NA" : (median2 % 2 == 0 ? String.valueOf(median2 / 2) : (median2 / 2) + ".5"))
                    + " cho=" + waitedMs + "ms doc_lai=" + polls;
        }
    }

    /** 2 x trung vi cac phan tu &gt; 0; -1 neu &lt; {@link #MIN_HISTORY} phan tu. */
    static int median2(int[] counts) {
        int[] v = Arrays.stream(counts).filter(c -> c > 0).sorted().toArray();
        if (v.length < MIN_HISTORY) return -1;
        int n = v.length;
        return (n % 2 == 1) ? 2 * v[n / 2] : v[n / 2 - 1] + v[n / 2];
    }

    /** need = ceil(RATIO_PCT/100 x median) tinh bang so nguyen tren 2 x median. */
    static int need(int median2) {
        return (RATIO_PCT * median2 + 199) / 200;
    }

    public static Verdict check(LiveTickerWindow w, long endMinute) {
        return check(w, endMinute, System::currentTimeMillis, Thread::sleep);
    }

    static Verdict check(LiveTickerWindow w, long endMinute, LongSupplier clock, LiveTickerWindow.Sleeper sleeper) {
        int[] hist = w.countsRange(endMinute - LOOKBACK_MIN * Utils.TIME_MINUTE, LOOKBACK_MIN);
        int m2 = median2(hist);
        int have = w.countAt(endMinute);
        if (m2 < 0) return new Verdict(endMinute, true, false, have, -1, 0, 0, 0L);
        int need = need(m2);
        if (have >= need) return new Verdict(endMinute, true, false, have, m2, need, 0, 0L);   // du: 0 doc them
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
            LOG.warn("[MINUTE-WAIT] {} => DU sau khi cho (tong cho={} du={} thieu={})", v.line(), N_WAITED.get(), N_RECOVERED.get(),
                    N_INCOMPLETE.get());
        } else {
            long n = N_INCOMPLETE.incrementAndGet();
            LOG.warn("[MINUTE-INCOMPLETE] {} => KHONG mo lenh moi phut nay (quan ly vi the/trailing/stop giu nguyen) | tong_thieu={}"
                    + " tong_cho={} tong_du_sau_cho={}", v.line(), n, N_WAITED.get(), N_RECOVERED.get());
        }
        return v;
    }
}
