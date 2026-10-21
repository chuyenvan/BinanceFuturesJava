package com.binance.chuyennd.ops;

import com.binance.chuyennd.tradecore.Cfg;
import com.binance.chuyennd.tradecore.EntryCost;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.management.ManagementFactory;
import java.lang.management.ThreadMXBean;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

/**
 * [EXEC-PROBE 2026-10-21] Do chi phi THUC THI tren shadow — <b>CHI LOG, khong doi quyet dinh</b>. Co
 * {@code LIVE_EXEC_PROBE} (mac dinh 0 = TAT: moi hook tra ve sau MOT phep doc boolean, khong cap phat, khong thread).
 *
 * <p>Bat (=1): tai moi leg GIAY vao lenh (entry leg 0 / DCA leg &gt;= 1, sau khi {@code ShadowBookC3.openPos} da ghi) va
 * moi lan so giay dong cum (trailing / time-stop), hook CHI chep cac so nguyen thuy vao mot hang doi co gioi han
 * ({@code offer} khong chan; day => bo + dem). Mot thread daemon {@code ExecProbe} gom su kien trong
 * {@link #KEY_BATCH_MS} ms, mo MOT ket noi websocket PUBLIC (khong API key, khong REST) toi combined stream
 * {@code <sym>@depth<N>@100ms} cho &lt;= {@link #KEY_MAX_STREAMS} symbol, lay message dau tien moi symbol, DONG ket noi,
 * roi ghi moi su kien 1 dong {@code [EXEC-PROBE] ...} (CSV, header {@link #HEADER}). Gioi han ket noi
 * {@link #KEY_MAX_CONN_5M}/5 phut (vuot => {@code status=rate_capped}, khong mo). Moi 60 phut 1 dong
 * {@code [EXEC-PROBE-STAT]} (dem, CPU thread, heap).
 *
 * <p>Cot chinh (bps, duong = bat loi cho ta): {@code slip_bps} = VWAP walk-the-book so voi gia sim dung (close nen
 * quyet dinh cho leg vao; SL/price_realtime cho exit), {@code drift_bps} = mid so voi gia sim (troi gia tu luc dong nen
 * toi luc chup), {@code impact_bps} = VWAP so voi mid (nua spread + an sau). Khong tinh phi taker (giong nhau sim/live).
 *
 * <p>Khong ghi Aerospike/Redis, khong goi Binance REST, khong dat lenh. Moi loi bi nuot (log WARN toi da 1 lan/10').
 * Thiet ke: {@code docs/plan/GOLIVE_GAP_C3LIVE.md} muc B; pre-reg {@code docs/prereg/PREREG_EXEC_PROBE.md}.
 */
public final class ExecProbe {

    private static final Logger LOG = LoggerFactory.getLogger(ExecProbe.class);

    public static final String KEY = "LIVE_EXEC_PROBE";
    /** ws (mac dinh) | mock (so gia lap tat dinh quanh gia sim — CHI harness/test, khong mang). */
    public static final String KEY_SOURCE = "EXEC_PROBE_SOURCE";
    /** Danh sach base URL (phay); xoay vong khi 2 lo lien tiep khong nhan duoc message nao. */
    public static final String KEY_WS_BASES = "EXEC_PROBE_WS_BASES";
    public static final String KEY_DEPTH = "EXEC_PROBE_DEPTH";
    public static final String KEY_MAX_STREAMS = "EXEC_PROBE_MAX_STREAMS";
    public static final String KEY_TIMEOUT_MS = "EXEC_PROBE_TIMEOUT_MS";
    public static final String KEY_BATCH_MS = "EXEC_PROBE_BATCH_MS";
    public static final String KEY_MAX_CONN_5M = "EXEC_PROBE_MAX_CONN_5M";

    public static final String DEFAULT_WS_BASES =
            "wss://fstream.binance.com/public/stream?streams=,wss://fstream.binance.com/market/stream?streams=";
    public static final int DEFAULT_DEPTH = 20;
    public static final int DEFAULT_MAX_STREAMS = 20;
    public static final long DEFAULT_TIMEOUT_MS = 3000L;
    public static final long DEFAULT_BATCH_MS = 500L;
    public static final int DEFAULT_MAX_CONN_5M = 30;
    static final int QUEUE_CAP = 512;
    static final long STAT_EVERY_MS = 3_600_000L;
    static final long FIVE_MIN_MS = 300_000L;

    public static final String TAG = "[EXEC-PROBE]";
    public static final String VERSION = "1";
    public static final String HEADER = "v,ev,sym,side,lvl,leg,reason,qty,notional,sim_px,bar_open,bar_ret,bucket,"
            + "t_bar_close,t_dec,t_snap,lat_dec_ms,lat_snap_ms,ex_lag_ms,bid,ask,mid,spread_bps,l1_bid_ntl,l1_ask_ntl,"
            + "n_lvl,side_ntl,walk_vwap,fill_frac,walk_lvls,slip_bps,drift_bps,impact_bps,slip_x025,slip_x4,trig_px,status,src";

    public static final String EV_ENTRY = "ENTRY";
    public static final String EV_DCA = "DCA";
    public static final String EV_EXIT = "EXIT";

    /** Co env (doc MOT lan). */
    private static final boolean ENV_ON = OpsConfig.parseOn(Cfg.get(KEY));
    /** Hieu dung (= ENV_ON; chi unit test moi doi qua {@link #installForTest}). */
    private static volatile boolean active = ENV_ON;
    private static volatile Engine engine;
    private static volatile long lastErrMs = Long.MIN_VALUE / 2;

    private ExecProbe() {
    }

    /** Call site goi ham nay TRUOC moi hook: TAT => false va khong lam gi khac. */
    public static boolean on() {
        return active;
    }

    // ------------------------------------------------------------------------------------------- su kien

    /** Mot su kien (chi so nguyen thuy, bat bien). */
    public static final class Event {
        final String ev;
        final String sym;
        final boolean buy;
        final String lvl;
        final int leg;
        final String reason;
        final double qty;
        final double simPx;
        final double barOpen;
        /** start nen quyet dinh (ms), -1 = khong co (exit). */
        final long barStartMs;
        final long tDec;
        /** Gia kich hoat (exit: price_realtime cua nhip); NaN neu khong co. */
        final double trigPx;

        Event(String ev, String sym, boolean buy, String lvl, int leg, String reason, double qty, double simPx,
              double barOpen, long barStartMs, long tDec, double trigPx) {
            this.ev = ev;
            this.sym = sym;
            this.buy = buy;
            this.lvl = lvl;
            this.leg = leg;
            this.reason = reason;
            this.qty = qty;
            this.simPx = simPx;
            this.barOpen = barOpen;
            this.barStartMs = barStartMs;
            this.tDec = tDec;
            this.trigPx = trigPx;
        }
    }

    // ------------------------------------------------------------------------------------------- hook (call site)

    /**
     * Leg GIAY vua duoc so ghi ({@code legIdx} 0 = mo cum, &gt;= 1 = DCA). {@code legIdx < 0} (so khong ghi: LEGACY,
     * gia/qty hong) => bo qua. Chi xep hang; KHONG nem.
     */
    public static void onPaperLeg(String symbol, String level, int legIdx, float qty, float simPx, float barOpen,
                                  Long barStartMs) {
        if (!active) return;
        try {
            if (symbol == null || legIdx < 0 || !(qty > 0f) || !(simPx > 0f)) return;
            Engine e = engine();
            if (e == null) return;
            e.offer(new Event(legIdx == 0 ? EV_ENTRY : EV_DCA, symbol, true, level, legIdx, "", qty, simPx, barOpen,
                    barStartMs == null ? -1L : barStartMs, System.currentTimeMillis(), Double.NaN));
        } catch (Throwable t) {
            err("onPaperLeg", t);
        }
    }

    /** So giay vua quyet dinh dong cum ({@code simPx} = gia sim ghi vao ledger; {@code trigPx} = gia nhip). */
    public static void onPaperExit(String symbol, String reason, float qty, float simPx, float trigPx, int legCount,
                                   long nowMs) {
        if (!active) return;
        try {
            if (symbol == null || !(qty > 0f) || !(simPx > 0f)) return;
            Engine e = engine();
            if (e == null) return;
            e.offer(new Event(EV_EXIT, symbol, false, "", legCount, reason, qty, simPx, Double.NaN, -1L, nowMs, trigPx));
        } catch (Throwable t) {
            err("onPaperExit", t);
        }
    }

    /** CHI harness/test: cho thread xu ly het hang doi (toi da {@code ms}). True neu da rong. */
    public static boolean awaitIdle(long ms) {
        Engine e = engine;
        if (e == null) return true;
        long end = System.currentTimeMillis() + ms;
        while (System.currentTimeMillis() < end) {
            if (e.idle()) return true;
            try {
                Thread.sleep(20L);
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                return e.idle();
            }
        }
        return e.idle();
    }

    private static Engine engine() {
        Engine e = engine;
        if (e != null) return e;
        synchronized (ExecProbe.class) {
            if (engine == null && active) {
                Engine ne = new Engine(Settings.fromCfg(), null, null);
                ne.startThread();
                engine = ne;
            }
            return engine;
        }
    }

    /** CHI unit test: dat engine (khong thread) + bat/tat hieu dung. {@code null} => tro ve trang thai env. */
    static synchronized void installForTest(Engine e) {
        engine = e;
        active = e != null || ENV_ON;
    }

    static void err(String where, Throwable e) {
        long now = System.currentTimeMillis();
        if (now - lastErrMs < 600_000L) return;
        lastErrMs = now;
        LOG.warn("{} loi {} (bo qua, khong anh huong giao dich): {}", TAG, where, e.toString());
    }

    // ------------------------------------------------------------------------------------------- cau hinh

    static final class Settings {
        final String source;
        final List<String> bases;
        final int depth;
        final int maxStreams;
        final long timeoutMs;
        final long batchMs;
        final int maxConn5m;

        Settings(String source, List<String> bases, int depth, int maxStreams, long timeoutMs, long batchMs, int maxConn5m) {
            this.source = source;
            this.bases = bases;
            this.depth = depth;
            this.maxStreams = maxStreams;
            this.timeoutMs = timeoutMs;
            this.batchMs = batchMs;
            this.maxConn5m = maxConn5m;
        }

        static Settings fromCfg() {
            return parse(Cfg.get(KEY_SOURCE), Cfg.get(KEY_WS_BASES), Cfg.get(KEY_DEPTH), Cfg.get(KEY_MAX_STREAMS),
                    Cfg.get(KEY_TIMEOUT_MS), Cfg.get(KEY_BATCH_MS), Cfg.get(KEY_MAX_CONN_5M));
        }

        /** Thuan: gia tri sai/ngoai mien => mac dinh. depth chi 5|10|20; streams 1..50; timeout 500..10000; batch 0..2000; conn 1..120. */
        static Settings parse(String src, String bases, String depth, String streams, String timeout, String batch, String conn) {
            String s = src == null ? "ws" : src.trim().toLowerCase(Locale.ROOT);
            if (!"mock".equals(s)) s = "ws";
            List<String> bl = new ArrayList<>();
            for (String b : (bases == null || bases.trim().isEmpty() ? DEFAULT_WS_BASES : bases).split(",")) {
                String t = b.trim();
                if (t.startsWith("wss://")) bl.add(t);
            }
            if (bl.isEmpty()) for (String b : DEFAULT_WS_BASES.split(",")) bl.add(b.trim());
            int d = (int) bounded(depth, DEFAULT_DEPTH, 5, 20);
            if (d != 5 && d != 10 && d != 20) d = DEFAULT_DEPTH;
            return new Settings(s, Collections.unmodifiableList(bl), d,
                    (int) bounded(streams, DEFAULT_MAX_STREAMS, 1, 50),
                    bounded(timeout, DEFAULT_TIMEOUT_MS, 500, 10_000),
                    bounded(batch, DEFAULT_BATCH_MS, 0, 2_000),
                    (int) bounded(conn, DEFAULT_MAX_CONN_5M, 1, 120));
        }

        private static long bounded(String raw, long def, long lo, long hi) {
            if (raw == null || raw.trim().isEmpty()) return def;
            try {
                long v = Long.parseLong(raw.trim());
                return (v < lo || v > hi) ? def : v;
            } catch (NumberFormatException e) {
                return def;
            }
        }

        String describe() {
            return "source=" + source + " depth=" + depth + " maxStreams=" + maxStreams + " timeoutMs=" + timeoutMs
                    + " batchMs=" + batchMs + " maxConn5m=" + maxConn5m + " bases=" + bases;
        }
    }

    // ------------------------------------------------------------------------------------------- nguon so

    /** Nguon anh chup so. KHONG nem; thieu symbol = khong nhan duoc trong timeout. */
    public interface BookSource {
        Map<String, ExecProbeBook.Book> snapshot(List<String> symbols, Map<String, Double> refPx, long timeoutMs);

        String name();

        /** So lan mo ket noi that (mock = 0). */
        long connects();
    }

    /** So gia lap TAT DINH (khong mang): mid = gia sim, spread 2 bps, moi muc 1 bp va 1 000 USDT. CHI harness/test. */
    static final class MockSource implements BookSource {
        private final int depth;

        MockSource(int depth) {
            this.depth = depth;
        }

        @Override
        public Map<String, ExecProbeBook.Book> snapshot(List<String> symbols, Map<String, Double> refPx, long timeoutMs) {
            Map<String, ExecProbeBook.Book> out = new HashMap<>();
            long now = System.currentTimeMillis();
            for (String s : symbols) {
                Double r = refPx.get(s);
                if (r == null || !(r > 0d)) continue;
                double[] bp = new double[depth], bq = new double[depth], ap = new double[depth], aq = new double[depth];
                for (int i = 0; i < depth; i++) {
                    bp[i] = r * (1d - (1d + i) * 1e-4);
                    ap[i] = r * (1d + (1d + i) * 1e-4);
                    bq[i] = 1000d / bp[i];
                    aq[i] = 1000d / ap[i];
                }
                out.put(s, new ExecProbeBook.Book(s, bp, bq, ap, aq, now, now));
            }
            return out;
        }

        @Override
        public String name() {
            return "mock";
        }

        @Override
        public long connects() {
            return 0L;
        }
    }

    // ------------------------------------------------------------------------------------------- engine

    /** Hang doi + vong xu ly. Tach khoi static de unit test chay dong bo ({@link #runOnce}). */
    static final class Engine {
        final Settings cfg;
        final BookSource source;
        final LineSink sink;
        final BlockingQueue<Event> q = new ArrayBlockingQueue<>(QUEUE_CAP);
        final ArrayDeque<Event> carry = new ArrayDeque<>();
        final ArrayDeque<Long> connTimes = new ArrayDeque<>();
        final AtomicLong offered = new AtomicLong(), dropped = new AtomicLong(), lines = new AtomicLong(),
                noBook = new AtomicLong(), rateCapped = new AtomicLong(), batches = new AtomicLong(), snapMsSum = new AtomicLong();
        volatile boolean busy = false;
        volatile Thread thread;
        volatile boolean headerDone = false;
        long lastStatMs;

        Engine(Settings cfg, BookSource src, LineSink sink) {
            this.cfg = cfg;
            this.source = src != null ? src : ("mock".equals(cfg.source) ? new MockSource(cfg.depth)
                    : new ExecProbeWsSource(cfg.bases, cfg.depth));
            this.sink = sink != null ? sink : line -> LOG.info("{}", line);
            this.lastStatMs = System.currentTimeMillis();
        }

        void offer(Event e) {
            offered.incrementAndGet();
            if (!q.offer(e)) dropped.incrementAndGet();
        }

        boolean idle() {
            return q.isEmpty() && carry.isEmpty() && !busy;
        }

        void startThread() {
            LOG.info("{} BAT (CHI LOG, khong doi quyet dinh) {} => {}", TAG, cfg.describe(), source.name());
            if ("mock".equals(source.name())) {
                LOG.warn("{} EXEC_PROBE_SOURCE=mock: so GIA LAP (chi harness/test) — khong phai du lieu thi truong", TAG);
            }
            Thread t = new Thread(() -> {
                while (true) {
                    try {
                        runOnce(1_000L);
                        maybeStat(System.currentTimeMillis());
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        return;
                    } catch (Throwable e) {
                        busy = false;
                        err("worker", e);
                    }
                }
            }, "ExecProbe");
            t.setDaemon(true);
            thread = t;
            t.start();
        }

        /** Xu ly toi da MOT lo. Tra so dong da ghi. */
        int runOnce(long pollMs) throws InterruptedException {
            List<Event> batch = new ArrayList<>();
            while (!carry.isEmpty()) batch.add(carry.poll());
            if (batch.isEmpty()) {
                Event first = q.poll(pollMs, TimeUnit.MILLISECONDS);
                if (first == null) return 0;
                batch.add(first);
            }
            busy = true;
            try {
                long end = System.currentTimeMillis() + cfg.batchMs;
                while (batch.size() < QUEUE_CAP) {
                    long wait = end - System.currentTimeMillis();
                    Event e = wait > 0 ? q.poll(wait, TimeUnit.MILLISECONDS) : q.poll();
                    if (e == null) break;
                    batch.add(e);
                }
                // symbol rieng biet theo thu tu den, <= maxStreams; su kien cua symbol vuot tran => lo sau
                LinkedHashMap<String, Double> ref = new LinkedHashMap<>();
                List<Event> now = new ArrayList<>();
                for (Event e : batch) {
                    if (ref.containsKey(e.sym) || ref.size() < cfg.maxStreams) {
                        ref.putIfAbsent(e.sym, e.simPx);
                        now.add(e);
                    } else {
                        carry.add(e);
                    }
                }
                long t0 = System.currentTimeMillis();
                Map<String, ExecProbeBook.Book> books;
                String capStatus = null;
                if (!allowConnect(t0)) {
                    books = Collections.emptyMap();
                    capStatus = "rate_capped";
                } else {
                    books = source.snapshot(new ArrayList<>(ref.keySet()), ref, cfg.timeoutMs);
                    if (books == null) books = Collections.emptyMap();
                }
                batches.incrementAndGet();
                snapMsSum.addAndGet(System.currentTimeMillis() - t0);
                if (!headerDone) {
                    sink.line(TAG + " #hdr," + HEADER);
                    headerDone = true;
                }
                int n = 0;
                for (Event e : now) {
                    ExecProbeBook.Book b = books.get(e.sym);
                    String st = capStatus;
                    if (st == null && b == null) st = "no_book";
                    if ("no_book".equals(st)) noBook.incrementAndGet();
                    if ("rate_capped".equals(st)) rateCapped.incrementAndGet();
                    sink.line(TAG + " " + format(e, b, st, source.name()));
                    lines.incrementAndGet();
                    n++;
                }
                return n;
            } finally {
                busy = false;
            }
        }

        /** Tran ket noi / 5 phut (mock khong tinh). */
        boolean allowConnect(long now) {
            if ("mock".equals(source.name())) return true;
            while (!connTimes.isEmpty() && now - connTimes.peekFirst() >= FIVE_MIN_MS) connTimes.pollFirst();
            if (connTimes.size() >= cfg.maxConn5m) return false;
            connTimes.addLast(now);
            return true;
        }

        void maybeStat(long now) {
            if (now - lastStatMs < STAT_EVERY_MS) return;
            lastStatMs = now;
            LOG.info("{}", statLine());
        }

        String statLine() {
            long cpuMs = -1L;
            try {
                ThreadMXBean mx = ManagementFactory.getThreadMXBean();
                Thread t = thread;
                if (t != null && mx.isThreadCpuTimeSupported()) cpuMs = mx.getThreadCpuTime(t.getId()) / 1_000_000L;
            } catch (Throwable ignore) {
                cpuMs = -1L;
            }
            Runtime rt = Runtime.getRuntime();
            long b = batches.get();
            return "[EXEC-PROBE-STAT] offered=" + offered.get() + " lines=" + lines.get() + " dropped=" + dropped.get()
                    + " batches=" + b + " connects=" + source.connects() + " no_book=" + noBook.get()
                    + " rate_capped=" + rateCapped.get() + " avg_snap_ms=" + (b == 0 ? 0 : snapMsSum.get() / b)
                    + " worker_cpu_ms=" + cpuMs + " heap_used_mb=" + ((rt.totalMemory() - rt.freeMemory()) >> 20)
                    + " queue=" + q.size() + " src=" + source.name();
        }
    }

    /** Dau ra dong (SLF4J o runtime; list o test). */
    interface LineSink {
        void line(String s);
    }

    /** Dinh dang 1 dong CSV theo {@link #HEADER} (khong co tien to TAG). Thuan. */
    static String format(Event e, ExecProbeBook.Book b, String status, String src) {
        double notional = e.qty * e.simPx;
        double barRet = (e.barOpen > 0d) ? (e.simPx - e.barOpen) / e.barOpen : Double.NaN;
        String bucket = (e.barOpen > 0d) ? EntryCost.NAMES[EntryCost.bucketOf((float) e.simPx, (float) e.barOpen)] : "";
        long tBarClose = e.barStartMs > 0 ? e.barStartMs + 60_000L : -1L;
        double bid = Double.NaN, ask = Double.NaN, mid = Double.NaN, spread = Double.NaN, l1b = Double.NaN, l1a = Double.NaN;
        double vwap = Double.NaN, fill = Double.NaN, slip = Double.NaN, drift = Double.NaN, impact = Double.NaN, sideNtl = Double.NaN;
        double slip025 = Double.NaN, slip4 = Double.NaN;
        int nLvl = -1, walkLvls = -1;
        long tSnap = -1L, exLag = Long.MIN_VALUE;
        String st = status;
        if (b != null) {
            bid = b.bestBid();
            ask = b.bestAsk();
            mid = b.mid();
            spread = (mid > 0d) ? (ask - bid) / mid * 1e4 : Double.NaN;
            l1b = b.bidPx.length > 0 ? b.bidPx[0] * b.bidQty[0] : Double.NaN;
            l1a = b.askPx.length > 0 ? b.askPx[0] * b.askQty[0] : Double.NaN;
            nLvl = b.levels();
            ExecProbeBook.Walk w = e.buy ? ExecProbeBook.walk(b.askPx, b.askQty, e.qty)
                    : ExecProbeBook.walk(b.bidPx, b.bidQty, e.qty);
            vwap = w.vwap;
            fill = w.fillFrac;
            walkLvls = w.levels;
            sideNtl = w.sideNotional;
            slip = ExecProbeBook.costBps(e.buy, vwap, e.simPx);
            drift = ExecProbeBook.costBps(e.buy, mid, e.simPx);
            impact = ExecProbeBook.costBps(e.buy, vwap, mid);
            // cung so, qty x0.25 / x4 (pilot 10k ~ 0.29 x so giay 35k; x4 = du phong quy mo) — doi chieu do sau
            double[] sp = e.buy ? b.askPx : b.bidPx, sq = e.buy ? b.askQty : b.bidQty;
            slip025 = ExecProbeBook.costBps(e.buy, ExecProbeBook.walk(sp, sq, e.qty * 0.25d).vwap, e.simPx);
            slip4 = ExecProbeBook.costBps(e.buy, ExecProbeBook.walk(sp, sq, e.qty * 4d).vwap, e.simPx);
            tSnap = b.recvMs;
            if (b.exchMs > 0) exLag = b.recvMs - b.exchMs;
            if (st == null) st = Double.isNaN(vwap) ? "empty_book" : (w.shortBook() ? "short" : "ok");
        }
        StringBuilder sb = new StringBuilder(320);
        sb.append(VERSION).append(',').append(e.ev).append(',').append(ExecProbeBook.txt(e.sym)).append(',')
                .append(e.buy ? "BUY" : "SELL").append(',').append(ExecProbeBook.txt(e.lvl)).append(',').append(e.leg).append(',')
                .append(ExecProbeBook.txt(e.reason)).append(',').append(ExecProbeBook.px(e.qty)).append(',')
                .append(ExecProbeBook.num(notional, 2)).append(',').append(ExecProbeBook.px(e.simPx)).append(',')
                .append(ExecProbeBook.px(e.barOpen)).append(',').append(ExecProbeBook.num(barRet, 6)).append(',')
                .append(bucket).append(',').append(tBarClose > 0 ? Long.toString(tBarClose) : "").append(',')
                .append(e.tDec).append(',').append(tSnap > 0 ? Long.toString(tSnap) : "").append(',')
                .append(tBarClose > 0 ? Long.toString(e.tDec - tBarClose) : "").append(',')
                .append(tSnap > 0 ? Long.toString(tSnap - e.tDec) : "").append(',')
                .append(exLag != Long.MIN_VALUE ? Long.toString(exLag) : "").append(',')
                .append(ExecProbeBook.px(bid)).append(',').append(ExecProbeBook.px(ask)).append(',').append(ExecProbeBook.px(mid)).append(',')
                .append(ExecProbeBook.num(spread, 3)).append(',').append(ExecProbeBook.num(l1b, 2)).append(',')
                .append(ExecProbeBook.num(l1a, 2)).append(',').append(nLvl >= 0 ? Integer.toString(nLvl) : "").append(',')
                .append(ExecProbeBook.num(sideNtl, 2)).append(',').append(ExecProbeBook.px(vwap)).append(',')
                .append(ExecProbeBook.num(fill, 4)).append(',').append(walkLvls >= 0 ? Integer.toString(walkLvls) : "").append(',')
                .append(ExecProbeBook.num(slip, 3)).append(',').append(ExecProbeBook.num(drift, 3)).append(',')
                .append(ExecProbeBook.num(impact, 3)).append(',').append(ExecProbeBook.num(slip025, 3)).append(',')
                .append(ExecProbeBook.num(slip4, 3)).append(',').append(ExecProbeBook.px(e.trigPx)).append(',')
                .append(st == null ? "" : st).append(',').append(ExecProbeBook.txt(src));
        return sb.toString();
    }
}
