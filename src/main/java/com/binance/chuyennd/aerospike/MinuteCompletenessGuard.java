package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayDeque;
import java.util.HashSet;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Consumer;
import java.util.function.LongSupplier;
import java.util.function.Predicate;
import java.util.function.Supplier;

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
 * [R4t A1 MAJ-S] So ky vong = min(trung vi 60 phut DU, |symbol da thay o phut DU ∩ TRADING theo exchangeInfo hien hanh|):
 * delist hang loat =&gt; symbol roi TRADING =&gt; ky vong giam theo (khong ket fail-closed; tre toi lan lam moi exchangeInfo ke tiep);
 * WS rot =&gt; symbol van TRADING =&gt; van bat. Universe tang =&gt; khong anh huong (min). exchangeInfo khong co / ky vong &lt; nua trung vi
 * (nguon nghi sai) =&gt; chi dung trung vi. Tat khan cap: env {@code LIVE_MINUTE_GUARD=0}.
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

    /** Trang thai live (1 luong quyet dinh). Telegram tren thread daemon rieng, khong chan tick. Ky vong exchangeInfo = A1 snapshot. */
    static final State LIVE = new State(com.binance.chuyennd.tradecore.selector.UniverseA1Filter::tradingSymbols, m -> {
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
        /** [R4t MAJ-S] symbol TRADING theo exchangeInfo hien hanh (null = khong co nguon => chi dung trung vi). */
        final Supplier<Set<String>> trading;
        /** [R4t] symbol da thay o phut DU (+ mam tu cache), dinh — WS rot keo dai khong lam mat symbol khoi tap nay. */
        final Set<String> knownSyms = new HashSet<>();
        long lastSanityWarnMinute = Long.MIN_VALUE;
        /** [FIN] da thay bin fin (ingestor moi) trong JVM nay; FIN_NOBIN_RESET phut lien tiep khong co bin =&gt; false. */
        boolean finSeen = false;
        int finNoBinStreak = 0;
        long lastNoBinWarnMinute = Long.MIN_VALUE;

        State(Consumer<String> alertSink) {
            this(() -> null, alertSink);
        }

        State(Supplier<Set<String>> trading, Consumer<String> alertSink) {
            this.trading = trading;
            this.alertSink = alertSink;
        }

        /**
         * So symbol ky vong theo exchangeInfo = |knownSyms ∩ TRADING|; -1 khi khong co nguon. Delist that => symbol roi TRADING =>
         * ky vong giam theo; WS rot => symbol van TRADING => ky vong giu.
         */
        int expectedEx() {
            Set<String> t;
            try {
                t = trading.get();
            } catch (RuntimeException e) {
                t = null;
            }
            if (t == null || t.isEmpty()) return -1;
            int n = 0;
            for (String s : knownSyms) if (t.contains(s)) n++;
            return n;
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
            knownSyms.addAll(w.symbolsIn(from, LOOKBACK_MIN));
        }

        void onComplete() {
            consecutive = 0;
        }

        /** Phut DU: vao tham chieu + tap symbol da biet, reset dem lien tiep. */
        void markGood(LiveTickerWindow w, long minute, int have) {
            addGood(minute, have);
            knownSyms.addAll(w.symbolsIn(minute, 1));
            onComplete();
        }

        void onIncomplete(Verdict v) {
            onIncomplete(v.minute, v.line());
        }

        /** [FIN] dung chung cho MI dem va MI fin: dem lien tiep / 60' + KHAN Telegram (chong spam). */
        void onIncomplete(long minute, String line) {
            consecutive++;
            miMinutes.addLast(minute);
            while (!miMinutes.isEmpty() && miMinutes.peekFirst() <= minute - LOOKBACK_MIN * Utils.TIME_MINUTE) miMinutes.pollFirst();
            int n60 = miMinutes.size();
            if (consecutive < ALERT_CONSEC && n60 < ALERT_N60) return;
            if (lastAlertMinute != Long.MIN_VALUE && minute - lastAlertMinute < ALERT_COOLDOWN_MIN * Utils.TIME_MINUTE) return;
            lastAlertMinute = minute;
            long na = N_ALERTS.incrementAndGet();
            String msg = "[MINUTE-GUARD] KHAN: du lieu nen 1m THIEU — " + consecutive + " phut lien tiep, " + n60
                    + " phut/60' fail-closed (KHONG mo lenh moi; vi the/trailing/stop giu nguyen). " + line
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
        /** [R4t] so symbol ky vong theo exchangeInfo (|knownSyms ∩ TRADING|); -1 = khong co nguon / bo qua. */
        public final int expected;

        Verdict(long minute, boolean complete, boolean waited, int have, int median2, int need, int polls, long waitedMs) {
            this(minute, complete, waited, have, median2, need, polls, waitedMs, -1);
        }

        Verdict(long minute, boolean complete, boolean waited, int have, int median2, int need, int polls, long waitedMs, int expected) {
            this.minute = minute;
            this.complete = complete;
            this.waited = waited;
            this.have = have;
            this.median2 = median2;
            this.need = need;
            this.polls = polls;
            this.waitedMs = waitedMs;
            this.expected = expected;
        }

        public double median() {
            return median2 < 0 ? Double.NaN : median2 / 2.0;
        }

        public String line() {
            return "phut=" + Utils.normalizeDateYYYYMMDDHHmm(minute) + " co=" + have + " can=" + need + " trung_vi60du="
                    + (median2 < 0 ? "NA" : (median2 % 2 == 0 ? String.valueOf(median2 / 2) : (median2 / 2) + ".5"))
                    + " ky_vong_ex=" + (expected < 0 ? "NA" : String.valueOf(expected))
                    + " cho=" + waitedMs + "ms doc_lai=" + polls;
        }
    }

    /** need = ceil(RATIO_PCT/100 x median) tinh bang so nguyen tren 2 x median. */
    static int need(int median2) {
        return (RATIO_PCT * median2 + 199) / 200;
    }

    // ===================== [FIN 2026-11-14, phuong an A] guard theo bin "fin" cua ingestor =====================
    /**
     * Co rollback (Cfg.get, doc 1 lan/JVM): "0"/"false" =&gt; TAT kiem fin (hanh vi r4u3: chi dem so symbol co nen).
     * Vang/khac =&gt; BAT. Chi dung khi buoc phai chay jar nay voi ingestor CU (khong ghi bin fin).
     */
    public static final String KEY_FIN = "LIVE_FIN_GUARD";
    /** Nguong = khai niem guard dem: phut DA CHOT khi so symbol (fin giao U) &gt;= ceil(99 % x |U|); U = universe dang dung. */
    public static final int FIN_RATIO_PCT = RATIO_PCT;
    /** Han doc lai fin: giay +45 sau khi phut dong (WS final tre ve +4..+30 s; REST settle tu +20..+30 s). */
    public static final long FIN_DEADLINE_AFTER_CLOSE_MS = 45_000L;
    /** So phut lien tiep record khong co bin fin =&gt; coi ingestor la CU: khong cho doc lai nua (fail-closed ngay). */
    public static final int FIN_NOBIN_RESET = 3;
    public static final AtomicLong N_FIN_INCOMPLETE = new AtomicLong();
    public static final AtomicLong N_FIN_NOBIN = new AtomicLong();
    public static final AtomicLong N_FIN_WAITED = new AtomicLong();
    public static final AtomicLong N_FIN_RECOVERED = new AtomicLong();
    /** [A1-M2] so phut DU co >= 1 coin universe chua chot (bi loai theo coin); tong so coin bi loai; so leg bi chan theo coin. */
    public static final AtomicLong N_FIN_EXCL_MINUTES = new AtomicLong();
    public static final AtomicLong N_FIN_EXCL_SYMS = new AtomicLong();
    public static final AtomicLong N_FIN_EXCL_LEGS = new AtomicLong();
    /** [A1-M2] so ten coin toi da in trong dong [MINUTE-FIN-EXCL] (so dem luon day du). */
    static final int EXCL_LOG_MAX = 30;
    private static volatile Boolean finOn = null;

    /** [A1-M5] co tat: "0"/"false"/"no"/"off" (khong phan biet hoa thuong, bo khoang trang) - KHOP script deploy/swap. */
    static boolean parseFinFlag(String v) {
        if (v == null) return true;
        String s = v.trim().toLowerCase(java.util.Locale.ROOT);
        return !("0".equals(s) || "false".equals(s) || "no".equals(s) || "off".equals(s));
    }

    public static boolean finEnabled() {
        Boolean b = finOn;
        if (b == null) {
            b = parseFinFlag(com.binance.chuyennd.tradecore.Cfg.get(KEY_FIN));
            finOn = b;
        }
        return b;
    }

    /** need = ceil(FIN_RATIO_PCT/100 x |U|). */
    static int finNeed(int universe) {
        return (FIN_RATIO_PCT * universe + 99) / 100;
    }

    /** Ket qua kiem fin 1 phut. reason: DU | DU_SAU_CHO | FIN_THIEU | FIN_KHONG_BIN. */
    public static final class FinVerdict {
        public final long minute;
        public final boolean complete, waited, changed, binPresent;
        public final int have, universe, need, polls;
        public final long waitedMs;
        public final String reason;
        /** [A1-M3] tre quyet dinh so voi luc phut dong (ms, = luc guard xong - (phut + 60 s)); binh thuong ~+6 s, cho toi ~+45 s. */
        public final long lateMs;
        /** [A1-M2] tap fin (ten day du) cua phut khi DU; null khi khong DU. Leg cua coin ngoai tap nay bi chan (finAllows). */
        public final java.util.Set<String> finSyms;
        /** [A1-M2] coin universe co nen phut nay nhung CHUA chot (sap xep); rong khi khong DU. */
        public final java.util.List<String> excluded;

        FinVerdict(long minute, boolean complete, boolean waited, boolean changed, boolean binPresent, int have, int universe,
                   int need, int polls, long waitedMs, String reason) {
            this(minute, complete, waited, changed, binPresent, have, universe, need, polls, waitedMs, reason, -1L, null,
                    java.util.Collections.<String>emptyList());
        }

        FinVerdict(long minute, boolean complete, boolean waited, boolean changed, boolean binPresent, int have, int universe,
                   int need, int polls, long waitedMs, String reason, long lateMs, java.util.Set<String> finSyms,
                   java.util.List<String> excluded) {
            this.minute = minute;
            this.complete = complete;
            this.waited = waited;
            this.changed = changed;
            this.binPresent = binPresent;
            this.have = have;
            this.universe = universe;
            this.need = need;
            this.polls = polls;
            this.waitedMs = waitedMs;
            this.reason = reason;
            this.lateMs = lateMs;
            this.finSyms = finSyms;
            this.excluded = excluded == null ? java.util.Collections.<String>emptyList() : excluded;
        }

        public String line() {
            return "phut=" + Utils.normalizeDateYYYYMMDDHHmm(minute) + " fin=" + have + "/" + universe + " can=" + need
                    + " bin_fin=" + (binPresent ? 1 : 0) + " cho=" + waitedMs + "ms doc_lai=" + polls
                    + " tre_sau_dong=" + lateMs + "ms loai_coin=" + excluded.size();
        }
    }

    /**
     * [A1-M2 2026-11-14] Fail-closed THEO COIN: coin khong nam trong bin fin o phut quyet dinh =&gt; khong vao/DCA coin do phut do.
     * {@code finSyms} null = guard fin khong chay (tat / LIVE_MINUTE_GUARD=0) =&gt; khong loc (y nguyen r4u3).
     */
    public static boolean finAllows(java.util.Set<String> finSyms, String symbol) {
        return finSyms == null || (symbol != null && finSyms.contains(symbol));
    }

    /** [A1-M2] coin universe co nen phut {@code m} trong cache nhung KHONG nam trong fin (sap xep tang dan). */
    static java.util.List<String> finMissing(LiveTickerWindow w, long m, java.util.Set<String> fin, Predicate<String> inUniverse) {
        java.util.List<String> out = new java.util.ArrayList<>();
        for (String sym : w.symbolsAt(m)) {
            if (inUniverse != null && !inUniverse.test(sym)) continue;
            if (fin == null || !fin.contains(sym)) out.add(sym);
        }
        java.util.Collections.sort(out);
        return out;
    }

    /** {co, |U|, bin_fin} - U = symbol co nen phut m trong cache (sau merge) va thuoc universe; co = |U giao fin|. */
    static int[] finCount(LiveTickerWindow w, long m, MinuteFin.Read r, Predicate<String> inUniverse) {
        java.util.Set<String> fin = r == null ? null : r.fin;
        int have = 0, u = 0;
        for (String sym : w.symbolsAt(m)) {
            if (inUniverse != null && !inUniverse.test(sym)) continue;
            u++;
            if (fin != null && fin.contains(sym)) have++;
        }
        return new int[]{have, u, fin != null ? 1 : 0};
    }

    public static FinVerdict checkFin(LiveTickerWindow w, long endMinute, Predicate<String> inUniverse) {
        return checkFin(LIVE, w, endMinute, inUniverse, System::currentTimeMillis, Thread::sleep);
    }

    /**
     * [FIN] Goi SAU guard dem (phut da DU theo dem). Doc nguyen tu data+fin phut {@code endMinute}, merge vao cache; du =&gt; tra ngay.
     * Thieu =&gt; doc lai moi {@link #POLL_MS} toi khi du hoac toi giay +{@link #FIN_DEADLINE_AFTER_CLOSE_MS}/1000 sau khi phut dong.
     * Van thieu =&gt; fail-closed (nhu MINUTE-INCOMPLETE). Record khong co bin fin va chua tung thay bin =&gt; fail-closed NGAY.
     */
    static FinVerdict checkFin(State s, LiveTickerWindow w, long endMinute, Predicate<String> inUniverse, LongSupplier clock,
                               LiveTickerWindow.Sleeper sleeper) {
        long t0 = clock.getAsLong();
        MinuteFin.Read r = w.readFinal(endMinute);
        boolean changed = r.overwritten > 0;
        int[] c = finCount(w, endMinute, r, inUniverse);
        if (c[2] == 1) s.finSeen = true;
        boolean noWait = c[2] == 0 && r.found && !s.finSeen;   // ingestor cu: tranh chan tick toi +45 s moi phut
        long deadline = endMinute + Utils.TIME_MINUTE + FIN_DEADLINE_AFTER_CLOSE_MS;
        int polls = 0;
        while (!noWait && !(c[2] == 1 && c[0] >= finNeed(c[1]))) {
            long now = clock.getAsLong();
            if (now >= deadline) break;
            try {
                sleeper.sleep(Math.max(1L, Math.min(POLL_MS, deadline - now)));
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                break;
            }
            r = w.readFinal(endMinute);
            polls++;
            if (r.overwritten > 0) changed = true;
            c = finCount(w, endMinute, r, inUniverse);
            if (c[2] == 1) s.finSeen = true;
        }
        boolean bin = c[2] == 1;
        boolean ok = bin && c[0] >= finNeed(c[1]);
        if (bin) {
            s.finNoBinStreak = 0;
        } else if (++s.finNoBinStreak >= FIN_NOBIN_RESET) {
            s.finSeen = false;
        }
        String reason = ok ? (polls > 0 ? "DU_SAU_CHO" : "DU") : (bin ? "FIN_THIEU" : "FIN_KHONG_BIN");
        long tEnd = clock.getAsLong();
        java.util.List<String> excl = ok ? finMissing(w, endMinute, r.fin, inUniverse) : java.util.Collections.<String>emptyList();
        java.util.Set<String> finSyms = ok ? java.util.Collections.unmodifiableSet(new HashSet<>(r.fin)) : null;
        FinVerdict v = new FinVerdict(endMinute, ok, polls > 0, changed, bin, c[0], c[1], finNeed(c[1]), polls,
                tEnd - t0, reason, tEnd - (endMinute + Utils.TIME_MINUTE), finSyms, excl);
        if (polls > 0) N_FIN_WAITED.incrementAndGet();
        if (ok) {
            if (polls > 0) {
                N_FIN_RECOVERED.incrementAndGet();
                // [A1-M3] dong nay co tre_sau_dong (ms sau khi phut dong) => addendum do K5 + do tre RIENG cho phut phai cho
                LOG.warn("[MINUTE-FIN-WAIT] {} => DU sau khi cho (tong_cho={} du_sau_cho={} thieu={})", v.line(), N_FIN_WAITED.get(),
                        N_FIN_RECOVERED.get(), N_FIN_INCOMPLETE.get());
            }
            if (!excl.isEmpty()) {
                long nm = N_FIN_EXCL_MINUTES.incrementAndGet();
                long ns = N_FIN_EXCL_SYMS.addAndGet(excl.size());
                String ds = excl.size() <= EXCL_LOG_MAX ? String.join(",", excl)
                        : String.join(",", excl.subList(0, EXCL_LOG_MAX)) + ",...(+" + (excl.size() - EXCL_LOG_MAX) + ")";
                LOG.warn("[MINUTE-FIN-EXCL] phut={} loai={} universe={} fin={} ds={} => KHONG vao/DCA cac coin nay phut nay (van tinh"
                                + " market/feature/p15) | tong_phut={} tong_coin={}", Utils.normalizeDateYYYYMMDDHHmm(endMinute),
                        excl.size(), c[1], c[0], ds, nm, ns);
            }
            return v;
        }
        long n = N_FIN_INCOMPLETE.incrementAndGet();
        if (!bin) N_FIN_NOBIN.incrementAndGet();
        LOG.warn("[MINUTE-INCOMPLETE] {} ly_do={} => KHONG mo lenh moi phut nay (quan ly vi the/trailing/stop giu nguyen)"
                + " | tong_fin_thieu={} tong_khong_bin={} lien_tiep={}", v.line(), reason, n, N_FIN_NOBIN.get(), s.consecutive + 1);
        if (!bin && (s.lastNoBinWarnMinute == Long.MIN_VALUE || endMinute - s.lastNoBinWarnMinute >= LOOKBACK_MIN * Utils.TIME_MINUTE)) {
            s.lastNoBinWarnMinute = endMinute;
            LOG.error("[MINUTE-FIN] record phut KHONG co bin fin (ingestor cu / KLINE_FIN_BIN=0?) => fail-closed moi phut. Deploy"
                    + " ingestor fin TRUOC; tam ve hanh vi cu: {}=0 (dong nay toi da 1 lan/{}')", KEY_FIN, LOOKBACK_MIN);
        }
        s.onIncomplete(endMinute, v.line() + " ly_do=" + reason);
        return v;
    }

    public static Verdict check(LiveTickerWindow w, long endMinute) {
        return check(LIVE, w, endMinute, System::currentTimeMillis, Thread::sleep);
    }

    static Verdict check(State s, LiveTickerWindow w, long endMinute, LongSupplier clock, LiveTickerWindow.Sleeper sleeper) {
        if (s.good.size() < MIN_HISTORY) s.seed(w, endMinute);
        int m2 = s.median2();
        int have = w.countAt(endMinute);
        if (m2 < 0) {   // chua du lich su => khong kiem (dem vao tham chieu)
            s.markGood(w, endMinute, have);
            return new Verdict(endMinute, true, false, have, -1, 0, 0, 0L);
        }
        // [R4t MAJ-S] ky vong = min(trung vi DU, |knownSyms ∩ TRADING exchangeInfo|): delist that => giam theo, WS rot => giu.
        int ex = s.expectedEx();
        int ref2 = m2;
        if (ex >= 0) {
            if (4L * ex >= m2) {   // ex >= nua trung vi: hop ly
                ref2 = Math.min(m2, 2 * ex);
            } else {
                if (s.lastSanityWarnMinute == Long.MIN_VALUE || endMinute - s.lastSanityWarnMinute >= LOOKBACK_MIN * Utils.TIME_MINUTE) {
                    s.lastSanityWarnMinute = endMinute;
                    LOG.warn("[MINUTE-GUARD] ky vong exchangeInfo {} < nua trung vi DU {} => BO QUA exchangeInfo (nguon nghi sai), dung trung vi",
                            ex, m2 / 2.0);
                }
                ex = -1;
            }
        }
        int need = need(ref2);
        if (have >= need) {   // du: 0 doc them
            s.markGood(w, endMinute, have);
            return new Verdict(endMinute, true, false, have, m2, need, 0, 0L, ex);
        }
        long deadline = endMinute + Utils.TIME_MINUTE + DEADLINE_AFTER_CLOSE_MS;
        long timeout = deadline - clock.getAsLong();
        long[] r = timeout > 0
                ? w.awaitMinuteComplete(endMinute, need, timeout, POLL_MS, sleeper, clock)
                : new long[]{have, 0L, 0L};
        boolean ok = r[0] >= need;
        boolean waited = r[1] > 0;
        Verdict v = new Verdict(endMinute, ok, waited, (int) r[0], m2, need, (int) r[1], r[2], ex);
        if (waited) N_WAITED.incrementAndGet();
        if (ok) {
            N_RECOVERED.incrementAndGet();
            s.markGood(w, endMinute, (int) r[0]);
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
