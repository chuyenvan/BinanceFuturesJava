package com.binance.chuyennd.c3live.canary;

import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.AssetBalance;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.OrderStatus;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.api.SymbolConfig;
import com.binance.chuyennd.c3live.api.Ticker24h;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.exec.C3LiveCids;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.exit.TrailingStopManager;
import com.binance.chuyennd.c3live.fill.FillAccounting;
import com.binance.chuyennd.c3live.fill.UserStream;
import com.binance.chuyennd.c3live.fill.UserStreamEvents;
import com.binance.chuyennd.c3live.filters.SymbolRules;
import com.binance.chuyennd.c3live.guard.AccountModeGuard;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.recon.FlatConfirm;
import com.binance.chuyennd.c3live.recon.OwnStopGuard;
import com.binance.chuyennd.c3live.recon.Reconciler;
import com.binance.chuyennd.c3live.risk.C3LiveFlattener;
import com.binance.chuyennd.ops.KillSwitchEngine;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.BooleanSupplier;
import java.util.function.Consumer;
import java.util.function.IntSupplier;
import java.util.function.LongSupplier;
import java.util.function.Predicate;

/**
 * [V12 3] Kich ban G-CANARY (prereg docs/prereg/GCANARY_PREREG.md, CHOT 10-25) chay tren CHINH cac lop c3_live da audit
 * (C3LiveOrderExecutor, LiveBookC3, FillAccounting, UserStream, TrailingStopManager, C3LiveFlattener, OwnStopGuard, Reconciler,
 * FlatConfirm, AccountModeGuard) voi so / trang thai rieng trong {@code run/canary/}, qua {@link CanaryGateway} (gioi han CUNG).
 * Moi lenh script = 1 JVM = 1 lenh cua lop nay; K6/K6b can 2 JVM (mo + kill / khoi dong lai).
 * Phu thuoc dong ho / ngu / websocket tiem duoc (test dung MockExchangeGateway + dong ho gia).
 */
public final class CanaryEngine {

    private static final Logger LOG = LoggerFactory.getLogger(CanaryEngine.class);
    public static final String BOOK_NAME = "c3live_book.json";
    public static final String DAT = "DAT";
    public static final String TRUOT = "TRUOT";
    public static final String TU_CHOI = "TU_CHOI";
    static final Set<String> STABLE = Collections.unmodifiableSet(new HashSet<>(java.util.Arrays.asList("USDT", "BFUSD", "USDC", "FDUSD")));

    /** Ngu (prod Thread.sleep; test: tang dong ho gia). */
    public interface Sleeper {
        void sleep(long ms);
    }

    /** Thoi gian kich ban (mac dinh = prereg). */
    public static final class Config {
        public long k0RunMs = 65L * 60_000L;
        public long k4WaitMs = 30L * 60_000L;
        public long k7CutMs = 330_000L;
        public long k7bInjectMs = 90_000L;
        public long safeRetryMs = 10_000L;
        public long streamWaitMs = 5_000L;
        public long fillEventWaitMs = 5_000L;
        public long closeWaitMs = 60_000L;
        public long orphanWaitMs = 60_000L;
        public double expectTmb = Double.NaN;
        public boolean injectTimeout;
    }

    /** Phu thuoc ngoai. */
    public static final class Deps {
        public ExchangeGateway raw;
        public File dir;
        public LongSupplier clock;
        public Sleeper sleeper;
        public UserStream.Connector connector;
        public List<String> wsUrls;
        public Consumer<String> alert;
        public Predicate<String> legacy;
        public IntSupplier usedWeight1m;
        public String journalName;
    }

    /** Ket qua 1 lenh. */
    public static final class Result {
        public final String command;
        public final String verdict;
        public final List<String> fails;
        public final Map<String, Object> data;

        Result(String command, String verdict, List<String> fails, Map<String, Object> data) {
            this.command = command;
            this.verdict = verdict;
            this.fails = fails;
            this.data = data;
        }

        public boolean ok() {
            return DAT.equals(verdict);
        }

        public String line() {
            return "RESULT " + command + " " + verdict + (fails.isEmpty() ? "" : " | " + String.join(" ; ", fails));
        }
    }

    /** Dung phien (tran lo / tu choi) — da flatten neu can. */
    static final class Abort extends RuntimeException {
        private static final long serialVersionUID = 1L;
        final String verdict;

        Abort(String verdict, String msg) {
            super(msg);
            this.verdict = verdict;
        }
    }

    /** Ghi ket qua 1 buoc. */
    final class Step {
        final String k;
        final long t0 = clock.getAsLong();
        final List<String> fails = new ArrayList<>();
        final Map<String, Object> data = new LinkedHashMap<>();

        Step(String k) {
            this.k = k;
        }

        boolean check(boolean ok, String failMsg) {
            if (!ok) fails.add(failMsg);
            return ok;
        }

        void put(String key, Object v) {
            data.put(key, v);
        }
    }

    private final Deps deps;
    private final Config cfg;
    private final LongSupplier clock;
    private final Sleeper sleeper;
    private final File dir;
    private final Object stateLock = new Object();
    private final CanaryState state;
    private final CanaryJournal journal;
    private final List<String> alerts = Collections.synchronizedList(new ArrayList<>());
    private final List<Map<String, Object>> streamEvents = Collections.synchronizedList(new ArrayList<>());
    private final Set<String> seenTrades = ConcurrentHashMap.newKeySet();
    private final Map<String, Float> trailTarget = new ConcurrentHashMap<>();

    // thanh phan c3_live (tao trong build)
    CanaryGateway gw;
    LiveBookC3 book;
    FillAccounting acct;
    FlatConfirm flat;
    Reconciler rec;
    OwnStopGuard guard;
    C3LiveFlattener flattener;
    TrailingStopManager trailing;
    C3LiveOrderExecutor executor;
    AccountModeGuard modeGuard;
    UserStream stream;
    StreamTap tap;
    volatile SymbolRules rules;
    private long lastLossCheckMs = Long.MIN_VALUE / 2;
    private long fallbackRuns;

    public CanaryEngine(Deps deps, Config cfg) throws IOException {
        this.deps = deps;
        this.cfg = cfg == null ? new Config() : cfg;
        this.clock = deps.clock;
        this.sleeper = deps.sleeper;
        this.dir = deps.dir;
        if (!dir.exists() && !dir.mkdirs()) throw new IOException("khong tao duoc " + dir);
        this.state = CanaryState.load(dir);
        String jn = deps.journalName == null ? "canary_" + clock.getAsLong() + ".jsonl" : deps.journalName;
        this.journal = new CanaryJournal(new File(dir, jn), clock);
    }

    public CanaryState state() {
        return state;
    }

    public CanaryJournal journal() {
        return journal;
    }

    public List<String> alerts() {
        synchronized (alerts) {
            return new ArrayList<>(alerts);
        }
    }

    public List<Map<String, Object>> streamEvents() {
        synchronized (streamEvents) {
            return new ArrayList<>(streamEvents);
        }
    }

    public CanaryGateway gateway() {
        return gw;
    }

    public LiveBookC3 book() {
        return book;
    }

    public Reconciler reconciler() {
        return rec;
    }

    public UserStream stream() {
        return stream;
    }

    public void close() {
        try {
            if (stream != null) stream.stop();
        } catch (RuntimeException ignore) {
            // dong
        }
        journal.close();
    }

    // ------------------------------------------------------------------ dung chung
    private void alert(String m) {
        String msg = m.startsWith("[CANARY]") ? m : "[CANARY] " + m;
        alerts.add(msg);
        journal.ev("ALERT", "msg", msg);
        try {
            if (deps.alert != null) deps.alert.accept(msg);
        } catch (Throwable ignore) {
            // Telegram loi khong anh huong kich ban
        }
    }

    private void saveState() {
        synchronized (stateLock) {
            try {
                state.save(dir);
            } catch (IOException e) {
                LOG.error("[CANARY] khong ghi duoc trang thai: {}", e.toString());
                journal.ev("STATE_SAVE_ERROR", "err", e.toString());
            }
        }
    }

    private Set<String> allowedSymbols() {
        Set<String> s = new LinkedHashSet<>();
        if (state.symMain != null) s.add(state.symMain);
        if (state.symAux != null) s.add(state.symAux);
        if (s.isEmpty()) s.add("__CANARY_NONE__");   // chua chon symbol => moi lenh ghi bi tu choi
        return s;
    }

    boolean lossCapHit() {
        return state.aborted != null || cachedLoss >= CanaryLimits.LOSS_CAP_USDT;
    }

    private volatile double cachedLoss;

    /** Lo hien tai = max(phi + lo da chot tu su kien stream, tmb0 - tmb). Khong doc duoc tmb => chi phan da chot. */
    double lossNow() {
        double realized;
        synchronized (stateLock) {
            realized = state.cumFeeStable - state.cumRealized - state.cumFunding;
        }
        double drop = Double.NaN;
        if (state.tmb0 != null && gw != null) {
            try {
                AccountSnapshot a = gw.account();
                if (a.getTotalMarginBalance() != null) drop = state.tmb0 - a.getTotalMarginBalance().doubleValue();
            } catch (RuntimeException e) {
                drop = Double.NaN;
            }
        }
        double l = Double.isNaN(drop) ? realized : Math.max(realized, drop);
        cachedLoss = l;
        return l;
    }

    /** Cham tran lo => flatten + dung phien (ghi vao trang thai: moi lenh sau TU CHOI tru flatten/report/cleanup). */
    void checkLoss(boolean force) {
        long now = clock.getAsLong();
        if (!force && now - lastLossCheckMs < 30_000L) return;
        lastLossCheckMs = now;
        double l = lossNow();
        if (l >= CanaryLimits.LOSS_CAP_USDT && state.aborted == null) {
            state.aborted = "LOSS_CAP lo=" + fmt(l) + " >= " + CanaryLimits.LOSS_CAP_USDT + " USDT luc " + now;
            saveState();
            alert("CHAM TRAN LO " + fmt(l) + " USDT => FLATTEN + DUNG PHIEN canary");
            journal.ev("ABORT", "why", state.aborted);
            flattenAll("LOSS_CAP");
            throw new Abort(TRUOT, "cham tran lo " + fmt(l) + " USDT (da flatten, phien dung)");
        }
    }

    static String fmt(double v) {
        return String.format(Locale.ROOT, "%.4f", v);
    }

    // ------------------------------------------------------------------ dung thanh phan
    /** Tao moi lop c3_live tren CanaryGateway (symbol hien tai trong trang thai). Khong goi san. */
    void build() {
        C3LiveOrderExecutor.ApiObserver api = (a, ok) -> { };
        Consumer<String> al = this::alert;
        gw = new CanaryGateway(deps.raw, allowedSymbols(), journal, deps.usedWeight1m, this::lossCapHit);
        gw.cidListener = (sym, cid) -> {
            long m = Math.floorDiv(clock.getAsLong(), 60_000L);
            synchronized (stateLock) {
                Long prev = state.lastCidMinute.get(sym);
                if (prev == null || prev < m) state.lastCidMinute.put(sym, m);
            }
        };
        book = new LiveBookC3(new File(dir, BOOK_NAME), 1.0d);
        acct = new FillAccounting(book, gw, OrderAuditLog.live(), null, al, api, clock, null);
        flat = new FlatConfirm(gw, api, al, FlatConfirm.DEFAULT_MIN_GAP_MS, FlatConfirm.DEFAULT_MIN_READS);
        rec = new Reconciler(gw, book, acct, () -> rules, al, api, clock, Reconciler.DEFAULT_EQUITY_TOL,
                Reconciler.DEFAULT_MATCH_TO_RELEASE, null, flat);
        acct.setUnknownPositionSink(rec::onUnknownPosition);
        final Reconciler r0 = rec;
        guard = new OwnStopGuard(gw, book, api, al, () -> r0::onUnknownPosition, clock);
        rec.setStopGuard(guard);
        acct.setStopGuard(guard);
        flattener = new C3LiveFlattener(gw, book, () -> KillSwitchEngine.Action.NONE, al, api, clock, 5, 10_000L, cfg.safeRetryMs, flat);
        flattener.setStopGuard(guard);
        trailing = TrailingStopManager.builder().gateway(gw).book(book).rules(() -> rules).closer(flattener::closeCluster)
                .trail((peak, pred, sym) -> trailTarget.getOrDefault(sym, -0.20f)).defer((s, t, n) -> false)
                .armHook((s, t, n) -> { }).action(() -> KillSwitchEngine.Action.NONE).api(api).alert(al).clock(clock)
                .armRate(-1f).timeStopHours(1_000_000).safeRetryMs(cfg.safeRetryMs).sleeper(sleeper::sleep)
                .events((type, s, n, v, d) -> journal.ev("TRAIL_EVENT", "event", type, "symbol", s, "value", v, "detail", d))
                .build();
        trailing.setStopGuard(guard);
        executor = new C3LiveOrderExecutor(gw, book, api, null, clock, sleeper::sleep, cfg.safeRetryMs, 3, Runnable::run);
        modeGuard = new AccountModeGuard(gw, CanaryLimits.LEVERAGE, al, clock, 60_000L);
        tap = new StreamTap(deps.connector);
        stream = new UserStream(gw, tap, deps.wsUrls, acct, this::fallbackRest, al, api, clock, 15_000L, 10_000L, 60_000L, 300_000L);
    }

    private void fallbackRest() {
        fallbackRuns++;
        journal.ev("FALLBACK_REST", "n", fallbackRuns);
        executor.resolveUnresolved(false);
        rec.checkPositions();
    }

    void loadRules() {
        ExchangeInfo ei = gw.exchangeInfo();
        rules = new SymbolRules(ei, clock.getAsLong());
    }

    // ------------------------------------------------------------------ websocket: ghi su kien + cat/noi lai (K7)
    /** Boc Connector: ghi su kien (che listenKey) + so cai doc lap, va cat ket noi phia client (K7). */
    final class StreamTap implements UserStream.Connector {
        private final UserStream.Connector real;
        volatile boolean cut;
        volatile UserStream.Socket cur;
        volatile UserStream.Listener curL;
        volatile String lastOpenUrl;
        volatile long lastOpenMs = -1L;
        volatile int opens;

        StreamTap(UserStream.Connector real) {
            this.real = real;
        }

        @Override
        public UserStream.Socket open(String url, UserStream.Listener l) {
            String masked = maskUrl(url);
            journal.ev("WS_OPEN_TRY", "url", masked);
            if (cut) throw new IllegalStateException("canary: ket noi dang bi CAT (K7)");
            UserStream.Listener w = new UserStream.Listener() {
                @Override
                public void onOpen() {
                    opens++;
                    lastOpenUrl = masked;
                    lastOpenMs = clock.getAsLong();
                    journal.ev("WS_OPEN", "url", masked);
                    l.onOpen();
                }

                @Override
                public void onText(String text) {
                    onStreamText(text);
                    synchronized (held) {
                        if (holding) {
                            held.add(() -> l.onText(text));
                            return;
                        }
                    }
                    l.onText(text);
                }

                @Override
                public void onClosed(String why) {
                    journal.ev("WS_CLOSED", "why", why);
                    l.onClosed(why);
                }
            };
            UserStream.Socket s = real.open(url, w);
            cur = s;
            curL = w;
            return () -> {
                if (s != null) s.close();
            };
        }

        void cut() {
            cut = true;
            UserStream.Listener l = curL;
            UserStream.Socket s = cur;
            cur = null;
            curL = null;
            journal.ev("WS_CUT");
            if (s != null) {
                try {
                    s.close();
                } catch (RuntimeException ignore) {
                    // da dong
                }
            }
            if (l != null) l.onClosed("canary cut");
        }

        void restore() {
            cut = false;
            journal.ev("WS_RESTORE");
        }

        private final List<Runnable> held = new ArrayList<>();
        private boolean holding;

        /** MO-5: giu (khong chuyen cho FillAccounting) su kien toi khi release => executor PHAI tra san bang queryOrder(cid). */
        void hold() {
            synchronized (held) {
                holding = true;
            }
            journal.ev("WS_HOLD");
        }

        void release() {
            List<Runnable> q;
            synchronized (held) {
                if (!holding && held.isEmpty()) return;
                holding = false;
                q = new ArrayList<>(held);
                held.clear();
            }
            journal.ev("WS_RELEASE", "n", q.size());
            for (Runnable r : q) r.run();
        }
    }

    static String maskUrl(String url) {
        if (url == null) return null;
        int i = url.lastIndexOf('/');
        return i < 0 ? "***" : url.substring(0, i + 1) + "***";
    }

    /** Su kien stream: nhat ky (raw da che) + so cai doc lap (rp, phi, funding). */
    void onStreamText(String text) {
        long now = clock.getAsLong();
        UserStreamEvents.Event e;
        try {
            e = UserStreamEvents.parse(text);
        } catch (RuntimeException ex) {
            journal.ev("WS_EVENT_PARSE_ERROR", "err", ex.toString());
            return;
        }
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("ts", now);
        m.put("e", e.type);
        if (e instanceof UserStreamEvents.OrderUpdate) {
            UserStreamEvents.OrderUpdate u = (UserStreamEvents.OrderUpdate) e;
            m.put("s", u.symbol);
            m.put("c", u.clientOrderId);
            m.put("X", u.status);
            m.put("x", u.execType);
            m.put("ot", u.origType);
            m.put("z", u.cumQty == null ? null : u.cumQty.toPlainString());
            m.put("ap", u.avgPrice == null ? null : u.avgPrice.toPlainString());
            if (u.isTrade()) {
                String key = u.orderId + ":" + u.tradeTimeMs + ":" + u.lastQty + ":" + u.cumQty;
                if (seenTrades.add(key)) {
                    double rp = u.realizedPnl == null ? 0d : u.realizedPnl.doubleValue();
                    double fee = u.commission == null ? 0d : u.commission.doubleValue();
                    String fa = u.commissionAsset == null ? "?" : u.commissionAsset;
                    synchronized (stateLock) {
                        state.cumRealized += rp;
                        state.fills++;
                        if (STABLE.contains(fa)) {
                            state.cumFeeStable += fee;
                        } else if (fee != 0d) {
                            state.feeOther.merge(fa, fee, Double::sum);
                        }
                    }
                    saveState();
                }
            }
        } else if (e instanceof UserStreamEvents.AlgoUpdate) {
            UserStreamEvents.AlgoUpdate a = (UserStreamEvents.AlgoUpdate) e;
            m.put("s", a.symbol);
            m.put("caid", a.clientAlgoId);
            m.put("X", a.status);
            m.put("ai", a.actualOrderId);
        } else if (e instanceof UserStreamEvents.AccountUpdate) {
            UserStreamEvents.AccountUpdate a = (UserStreamEvents.AccountUpdate) e;
            m.put("m", a.reason);
            List<String> ps = new ArrayList<>();
            for (UserStreamEvents.Position p : a.positions) ps.add(p.symbol + "=" + (p.positionAmt == null ? "?" : p.positionAmt.toPlainString()));
            m.put("P", ps);
            if ("FUNDING_FEE".equals(a.reason)) {
                double f = 0d;
                for (UserStreamEvents.Balance b : a.balances) {
                    if (b.asset != null && STABLE.contains(b.asset) && b.balanceChange != null) f += b.balanceChange.doubleValue();
                }
                synchronized (stateLock) {
                    state.cumFunding += f;
                }
                saveState();
            }
        }
        streamEvents.add(m);
        Map<String, Object> j = new LinkedHashMap<>(m);
        j.put("raw", text);
        journal.event("WS_EVENT", j);
    }

    // ------------------------------------------------------------------ cho / bom vong
    /** 1 nhip: stream (may trang thai) + xac nhan phang/UNKNOWN (nhu nhip ops runtime) + kiem tran lo moi 30 s. */
    void tick() {
        long now = clock.getAsLong();
        if (stream != null) stream.tick(now);
        if (rec != null) rec.confirmPendingFlat();
        checkLoss(false);
    }

    /** Bom vong trong ms (ngu tung 1 s). */
    void pump(long ms) {
        long end = clock.getAsLong() + ms;
        while (true) {
            tick();
            long left = end - clock.getAsLong();
            if (left <= 0) return;
            sleeper.sleep(Math.min(1_000L, left));
        }
    }

    /** Bom vong toi khi cond dung hoac het maxMs. @return ms da cho (>= 0) hoac -1 neu het gio. */
    long waitFor(BooleanSupplier cond, long maxMs) {
        long t0 = clock.getAsLong();
        while (true) {
            tick();
            if (cond.getAsBoolean()) return clock.getAsLong() - t0;
            long left = t0 + maxMs - clock.getAsLong();
            if (left <= 0) return -1L;
            sleeper.sleep(Math.min(1_000L, left));
        }
    }

    /** Mo stream, cho CONNECTED toi da streamWaitMs. @return ms ket noi hoac -1. */
    long ensureStream() {
        if (stream.isConnected()) return 0L;
        long t0 = clock.getAsLong();
        stream.tick(t0);
        return waitFor(stream::isConnected, cfg.streamWaitMs);
    }

    // ------------------------------------------------------------------ doc san
    BigDecimal lastPrice(String sym) {
        for (Ticker24h t : gw.tickers24h(sym)) {
            if (sym.equals(t.getSymbol()) && t.getLastPrice() != null && t.getLastPrice().signum() > 0) return t.getLastPrice();
        }
        throw new GatewayException(com.binance.chuyennd.c3live.api.ErrorKind.OTHER, "khong co gia " + sym, true);
    }

    /** positionAmt tren positionRisk (0 neu vang). */
    BigDecimal posAmt(String sym) {
        BigDecimal s = BigDecimal.ZERO;
        for (PositionInfo p : gw.positions()) {
            if (sym.equals(p.getSymbol()) && p.getPositionAmt() != null) s = s.add(p.getPositionAmt());
        }
        return s;
    }

    Optional<PositionInfo> pos(String sym) {
        for (PositionInfo p : gw.positions()) {
            if (sym.equals(p.getSymbol()) && p.getPositionAmt() != null && p.getPositionAmt().signum() != 0) return Optional.of(p);
        }
        return Optional.empty();
    }

    /** positionAmt tren account().positions (null = khong co mang). */
    BigDecimal acctAmt(String sym) {
        AccountSnapshot a = gw.account();
        if (a.getPositions() == null) return null;
        BigDecimal s = BigDecimal.ZERO;
        for (PositionInfo p : a.getPositions()) {
            if (sym.equals(p.getSymbol()) && p.getPositionAmt() != null) s = s.add(p.getPositionAmt());
        }
        return s;
    }

    /** Gia danh dau (positionRisk khi co vi the, khong thi gia khop cuoi). */
    BigDecimal mark(String sym) {
        Optional<PositionInfo> p = pos(sym);
        if (p.isPresent() && p.get().getMarkPrice() != null && p.get().getMarkPrice().signum() > 0) return p.get().getMarkPrice();
        return lastPrice(sym);
    }

    List<OrderInfo> ownStops(String sym) {
        List<OrderInfo> out = new ArrayList<>();
        for (OrderInfo o : gw.openStops(sym)) {
            if (OwnStopGuard.isOwn(o.getClientOrderId()) && o.getStatus() != null && !o.getStatus().isFinal()) out.add(o);
        }
        return out;
    }

    private Map<String, Float> px(String sym) {
        Map<String, Float> m = new HashMap<>();
        m.put(sym, mark(sym).floatValue());
        return m;
    }

    // ------------------------------------------------------------------ hanh dong (qua dung lop c3_live)
    /** Ket qua mo 1 leg. */
    static final class Leg {
        String cid;
        boolean confirmed;
        BigDecimal qty;
        double avg;
        double ref;
        long sendMs;
        long fillEventMs = -1L;
        String error;
    }

    /** Doi sang phut moi neu phut hien tai da dung cid cua symbol (cid c3-/c3x-/c3s- khong trung qua cac cum). */
    void waitNewMinute(String sym) {
        Long last;
        synchronized (stateLock) {
            last = state.lastCidMinute.get(sym);
        }
        if (last == null) return;
        long waited = waitFor(() -> Math.floorDiv(clock.getAsLong(), 60_000L) > last, 61_000L);
        if (waited < 0) throw new Abort(TRUOT, "khong sang duoc phut moi cho cid " + sym);
    }

    /** Mo 1 leg 20 USDT MARKET qua C3LiveOrderExecutor (duong production: reserve -> markSending -> RESULT/queryOrder). */
    Leg openLeg(String sym) {
        Leg l = new Leg();
        if (book.isHolding(sym)) throw new Abort(TRUOT, "so dang giu cum " + sym + " (khong mo chong)");
        AccountModeGuard.Result mg = modeGuard.checkSymbol(sym);
        if (!mg.isOk()) throw new Abort(TRUOT, "AccountModeGuard chan " + sym + ": " + mg.getProblems());
        waitNewMinute(sym);
        BigDecimal px = lastPrice(sym);
        SymbolRules.Sizing sz = rules.sizeMarketBuy(sym, CanaryLimits.ORDER_NOTIONAL_USDT, px);
        if (!sz.isOk()) throw new Abort(TRUOT, "khong tinh duoc qty " + sym + ": " + sz);
        long now = clock.getAsLong();
        long barMin = Math.floorDiv(now, 60_000L);
        l.cid = C3LiveCids.entry(sym, barMin, 0);
        l.qty = sz.getQty();
        l.ref = px.doubleValue();
        if (!book.reserve(sym, l.cid, 0, barMin, "CANARY", l.ref, l.qty, sz.getNotional().doubleValue(), now)) {
            throw new Abort(TRUOT, "so tu choi giu cho leg " + l.cid);
        }
        book.setMeta(sym, null, 0, now);
        journal.ev("LEG_SEND", "symbol", sym, "cid", l.cid, "qty", l.qty.toPlainString(), "ref", px.toPlainString());
        l.sendMs = clock.getAsLong();
        executor.submit(l.cid);   // executor dong bo (Runnable::run): gui + (timeout) cho cua so an toan + queryOrder
        tap.release();
        Optional<LiveBookC3.LegView> lv = book.leg(l.cid);
        l.confirmed = lv.isPresent() && lv.get().state == LiveBookC3.LegState.CONFIRMED;
        if (lv.isPresent()) {
            l.avg = lv.get().avgPx;
            if (!l.confirmed) l.error = "leg " + lv.get().state;
        } else {
            l.error = "leg bi huy (khong khop)";
        }
        final String cid = l.cid;
        long w = waitFor(() -> firstEventTs("ORDER_TRADE_UPDATE", cid, "FILLED") >= 0, cfg.fillEventWaitMs);
        l.fillEventMs = firstEventTs("ORDER_TRADE_UPDATE", cid, "FILLED");
        journal.ev("LEG_DONE", "symbol", sym, "cid", l.cid, "confirmed", l.confirmed, "avg", l.avg, "err", l.error,
                "streamLatMs", l.fillEventMs < 0 ? null : l.fillEventMs - l.sendMs, "waitMs", w);
        return l;
    }

    long firstEventTs(String type, String cid, String status) {
        synchronized (streamEvents) {
            for (Map<String, Object> e : streamEvents) {
                if (!type.equals(e.get("e"))) continue;
                Object c = "ALGO_UPDATE".equals(type) ? e.get("caid") : e.get("c");
                if (cid != null && !cid.equals(c)) continue;
                if (status != null && !status.equals(e.get("X"))) continue;
                return ((Number) e.get("ts")).longValue();
            }
        }
        return -1L;
    }

    /** Dung vi the cua cum dang giu; khong co thi mo leg moi. */
    Leg ensurePosition(String sym, Step st) {
        Optional<LiveBookC3.ClusterView> c = book.cluster(sym);
        if (c.isPresent() && c.get().confirmedQty.signum() > 0 && !c.get().hasUnresolved) {
            st.put("position", "dung cum co san qty=" + c.get().confirmedQty.toPlainString());
            return null;
        }
        Leg l = openLeg(sym);
        st.put("openLeg", legMap(l));
        if (!l.confirmed) throw new Abort(TRUOT, "mo leg " + sym + " khong khop: " + l.error);
        return l;
    }

    static Map<String, Object> legMap(Leg l) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("cid", l.cid);
        m.put("confirmed", l.confirmed);
        m.put("qty", l.qty == null ? null : l.qty.toPlainString());
        m.put("avg", l.avg);
        m.put("ref", l.ref);
        m.put("slip", l.ref > 0 && l.avg > 0 ? l.avg / l.ref - 1d : null);
        m.put("streamLatMs", l.fillEventMs < 0 ? null : l.fillEventMs - l.sendMs);
        m.put("error", l.error);
        return m;
    }

    /** Stop logic = mark*(1+offsetFromMark) quy ra ty le so VWAP cua cum; trailing dat/doi (ratchet chi tang). */
    void trailTo(String sym, double offsetFromMark) {
        LiveBookC3.ClusterView c = book.cluster(sym).orElseThrow(() -> new Abort(TRUOT, "khong co cum " + sym));
        double m = mark(sym).doubleValue();
        float rate = (float) (m * (1d + offsetFromMark) / c.avgEntryF - 1d);
        trailTarget.put(sym, rate);
        Map<String, Float> p = new HashMap<>();
        p.put(sym, (float) m);
        trailing.step(p);
    }

    /** Dat stop o ty le co dinh so VWAP (rate) qua trailing. */
    void trailRate(String sym, float rate) {
        trailTarget.put(sym, rate);
        trailing.step(px(sym));
    }

    /** Cho cum bi xoa khoi so (stream / REST / flattener). Goi lai closer moi 5 s neu cum dang dong. */
    long waitClusterGone(String sym, long maxMs) {
        long[] lastPoke = {clock.getAsLong()};
        return waitFor(() -> {
            if (!book.isHolding(sym)) return true;
            Optional<LiveBookC3.ClusterView> c = book.cluster(sym);
            if (c.isPresent() && c.get().closeReason != null && clock.getAsLong() - lastPoke[0] >= 5_000L) {
                lastPoke[0] = clock.getAsLong();
                flattener.closeCluster(sym, c.get().closeReason);
            }
            return !book.isHolding(sym);
        }, maxMs);
    }

    /** Dong 1 cum qua C3LiveFlattener (MARKET reduce-only c3x-, huy stop qua guard). */
    long closeCluster(String sym, String reason) {
        if (!book.isHolding(sym)) return 0L;
        waitNewMinuteForClose(sym);
        flattener.closeCluster(sym, reason);
        return waitClusterGone(sym, cfg.closeWaitMs);
    }

    /** cid dong c3x-<sym>-<phut>-<lan>: lan = closeAttempts+1 cua cum => tranh trung voi lenh dong cua cum truoc cung phut. */
    private void waitNewMinuteForClose(String sym) {
        Long last;
        synchronized (stateLock) {
            last = state.lastCloseMinute.get(sym);
        }
        long m = Math.floorDiv(clock.getAsLong(), 60_000L);
        if (last != null && last >= m) waitFor(() -> Math.floorDiv(clock.getAsLong(), 60_000L) > last, 61_000L);
        synchronized (stateLock) {
            state.lastCloseMinute.put(sym, Math.floorDiv(clock.getAsLong(), 60_000L));
        }
        saveState();
    }

    /** Cho 0 stop c3s- mo cua symbol (guard huy khi ca 2 nguon phang; Reconciler thu lai moi 30 s). */
    long waitNoOwnStops(String sym, long maxMs) {
        return waitFor(() -> ownStops(sym).isEmpty(), maxMs);
    }

    /**
     * Dong MOI vi the cua 2 symbol canary (khong cham symbol khac): cum trong so => C3LiveFlattener; vi the ngoai so (vd sau K6b)
     * => MARKET reduce-only c3x- truc tiep; roi huy stop c3s- qua guard (chi khi positionRisk + account deu phang).
     */
    Map<String, Object> flattenAll(String reason) {
        Map<String, Object> out = new LinkedHashMap<>();
        gw.failPositions = false;
        gw.failAccount = false;
        if (tap != null) tap.release();
        for (String sym : allowedSymbols()) {
            if (sym.startsWith("__")) continue;
            try {
                if (book.isHolding(sym)) {
                    long w = closeCluster(sym, "FLATTEN_" + reason);
                    out.put(sym + ".cluster", w >= 0 ? "dong" : "CHUA dong sau " + cfg.closeWaitMs + " ms");
                }
                BigDecimal amt = posAmt(sym);
                if (amt.signum() > 0) {
                    waitNewMinuteForClose(sym);
                    String cid = C3LiveCids.close(sym, Math.floorDiv(clock.getAsLong(), 60_000L), 9);
                    try {
                        OrderInfo o = gw.newMarketOrder(sym, Side.SELL, amt, cid, true);
                        out.put(sym + ".directClose", o.getStatus() + " " + o.getExecutedQty());
                    } catch (GatewayException e) {
                        out.put(sym + ".directClose", "LOI " + e.getKind() + ":" + e.getExchangeCode());
                    }
                }
                long w = waitFor(() -> {
                    try {
                        BigDecimal a = acctAmt(sym);
                        return posAmt(sym).signum() == 0 && a != null && a.signum() == 0;
                    } catch (RuntimeException e) {
                        return false;
                    }
                }, cfg.closeWaitMs);
                out.put(sym + ".flat", w >= 0);
                for (OrderInfo s : ownStops(sym)) {
                    OwnStopGuard.Result gr = guard.cancelOwnStopGuarded(sym, s.getClientOrderId(), "canary flatten (" + reason + ")");
                    out.put(sym + ".stop." + s.getClientOrderId(), gr.name());
                }
                out.put(sym + ".posAfter", posAmt(sym).toPlainString());
                out.put(sym + ".ownStopsAfter", ownStops(sym).size());
            } catch (RuntimeException e) {
                out.put(sym + ".error", e.toString());
            }
        }
        journal.event("FLATTEN", out);
        return out;
    }

    // ------------------------------------------------------------------ dieu kien chung truoc moi lenh
    /** Vi the / lenh / stop cua symbol NGOAI canary (khong bao gio cham; co => tu choi chay). */
    List<String> foreignExposure() {
        Set<String> allow = allowedSymbols();
        List<String> out = new ArrayList<>();
        for (PositionInfo p : gw.positions()) {
            if (p.getPositionAmt() != null && p.getPositionAmt().signum() != 0 && !allow.contains(p.getSymbol())) {
                out.add("vi the " + p.getSymbol() + "=" + p.getPositionAmt().toPlainString());
            }
        }
        for (OrderInfo o : gw.openOrders(null)) if (!allow.contains(o.getSymbol())) out.add("lenh mo " + o.getSymbol());
        for (OrderInfo o : gw.openStops(null)) if (!allow.contains(o.getSymbol())) out.add("algo mo " + o.getSymbol());
        return out;
    }

    /** Kiem lai 2 symbol trong trang thai van dung LUAT (khong xet hang) — chong sua tay file trang thai. */
    List<String> revalidateSymbols(ExchangeInfo ei) {
        List<String> out = new ArrayList<>();
        for (String s : new String[]{state.symMain, state.symAux}) {
            List<Ticker24h> t = gw.tickers24h(s);
            Optional<String> why = SymbolPicker.whyNot(s, ei, t, deps.legacy, clock.getAsLong(), true);
            if (why.isPresent()) out.add(s + " khong con dung luat: " + why.get());
        }
        return out;
    }

    /** Dieu kien chung cho moi buoc K (tru preflight/flatten/cleanup/status). */
    void begin(String k, boolean needStream) {
        if (state.aborted != null) throw new Abort(TU_CHOI, "phien da DUNG: " + state.aborted);
        if (!state.symbolsChosen()) throw new Abort(TU_CHOI, "chua chon symbol (chay canary_preflight truoc)");
        if (state.tmb0 == null) throw new Abort(TU_CHOI, "chua co moc tmb (K0 chua DAT)");
        build();
        List<String> f = foreignExposure();
        if (!f.isEmpty()) throw new Abort(TU_CHOI, "tai khoan co vi the/lenh ngoai canary: " + f);
        ExchangeInfo ei = gw.exchangeInfo();
        List<String> bad = revalidateSymbols(ei);
        if (!bad.isEmpty()) throw new Abort(TU_CHOI, String.join("; ", bad));
        rules = new SymbolRules(ei, clock.getAsLong());
        checkLoss(true);
        if (needStream) {
            long w = ensureStream();
            journal.ev("STREAM_READY", "k", k, "ms", w);
            if (w < 0) journal.ev("STREAM_NOT_READY", "k", k);
        }
    }

    // ------------------------------------------------------------------ K0 + chon symbol
    /** preflight = K0 chi doc (prereg §4) + chon 2 symbol theo LUAT + moc tmb. 0 lenh ghi. */
    public Result preflight() {
        Step st = new Step("K0");
        try {
            build();
            long mut0 = gw.mutatingCalls();
            ExchangeInfo ei = gw.exchangeInfo();
            List<Ticker24h> tk = gw.tickers24h(null);
            SymbolPicker.Pick p = SymbolPicker.pick(ei, tk, deps.legacy, clock.getAsLong());
            st.put("pick.scanned", p.scanned);
            st.put("pick.eligible", p.eligible);
            st.put("pick.rejects", p.rejectCounts);
            st.put("pick.top", p.topMaps());
            if (!st.check(p.main != null && p.aux != null, "khong du 2 symbol dung luat (eligible=" + p.eligible + ")")) {
                return finish(st);
            }
            if (state.symbolsChosen() && (!state.symMain.equals(p.main) || !state.symAux.equals(p.aux))) {
                st.put("pick.previous", state.symMain + "," + state.symAux);
                if (!state.steps.isEmpty() && hasTradeSteps()) {
                    st.check(false, "symbol theo luat da doi (" + p.main + "," + p.aux + ") sau khi da co buoc giao dich voi "
                            + state.symMain + "," + state.symAux + " => MASTER quyet (giu symbol cu)");
                    return finish(st);
                }
            }
            state.symMain = p.main;
            state.symAux = p.aux;
            state.pickedAtMs = clock.getAsLong();
            state.pickTop = p.topMaps();
            saveState();
            gw = null;
            build();   // gateway voi 2 symbol vua chon
            st.put("symMain", state.symMain);
            st.put("symAux", state.symAux);
            AccountSnapshot a = gw.account();
            double tmb = a.getTotalMarginBalance().doubleValue();
            st.put("tmb", tmb);
            st.put("twb", a.getTotalWalletBalance() == null ? null : a.getTotalWalletBalance().toPlainString());
            st.put("assets", assetMap(a));
            st.check(tmb > 0d, "tmb <= 0");
            if (Double.isNaN(cfg.expectTmb) || cfg.expectTmb <= 0d) {
                st.check(false, "thieu CANARY_EXPECT_TMB (so da nap) => khong do duoc tmb ~ so da nap");
            } else {
                double d = Math.abs(tmb - cfg.expectTmb) / cfg.expectTmb;
                st.put("tmbDiffFrac", d);
                st.check(d <= 0.01d, "tmb " + fmt(tmb) + " lech so da nap " + fmt(cfg.expectTmb) + " > 1%");
            }
            boolean multi = gw.multiAssetsMargin();
            boolean dual = gw.dualSidePosition();
            st.put("multiAssetsMargin", multi);
            st.put("dualSidePosition", dual);
            st.check(multi, "multiAssetsMargin=false");
            st.check(!dual, "dualSidePosition=true (hedge)");
            for (String s : new String[]{state.symMain, state.symAux}) {
                SymbolConfig sc = gw.symbolConfig(s);
                st.put("symbolConfig." + s, sc.getMarginType() + "/" + sc.getLeverage() + "x");
                st.check(sc.isCrossed() && sc.getLeverage() == CanaryLimits.LEVERAGE,
                        s + " " + sc.getMarginType() + "/" + sc.getLeverage() + "x (yeu cau CROSSED/1x — chay canary_step SETUP YES=1)");
            }
            try {
                st.put("symbolConfigsAll", gw.symbolConfigs().size());
            } catch (RuntimeException e) {
                st.put("symbolConfigsAll", "loi " + e.getClass().getSimpleName());
            }
            List<PositionInfo> pr = gw.positions();
            int nPos = 0;
            for (PositionInfo x : pr) if (x.getPositionAmt() != null && x.getPositionAmt().signum() != 0) nPos++;
            st.put("positionRisk.nonZero", nPos);
            st.put("positionRisk.rows", pr.size());
            st.check(nPos == 0, "positionRisk co " + nPos + " vi the");
            List<PositionInfo> ap = a.getPositions();
            st.put("account.positions", ap == null ? "null" : String.valueOf(ap.size()));
            int nAcc = 0;
            if (ap != null) for (PositionInfo x : ap) if (x.getPositionAmt() != null && x.getPositionAmt().signum() != 0) nAcc++;
            st.check(ap != null, "account() khong co mang positions");
            st.check(nAcc == 0, "account().positions co " + nAcc + " vi the");
            int no = gw.openOrders(null).size();
            int ns = gw.openStops(null).size();
            st.put("openOrders", no);
            st.put("openAlgo", ns);
            st.check(no == 0, no + " lenh mo");
            st.check(ns == 0, ns + " algo mo");
            // websocket: mo <= 5 s qua >= 1 URL; keepAlive 2 lan trong k0RunMs
            long t0 = clock.getAsLong();
            long w = ensureStream();
            st.put("ws.openMs", w);
            st.put("ws.url", tap.lastOpenUrl);
            st.check(w >= 0 && w <= 5_000L, "websocket khong mo trong 5 s");
            int ka0 = keepAliveOk();
            pump(Math.max(0L, cfg.k0RunMs - (clock.getAsLong() - t0)));
            int ka = keepAliveOk() - ka0;
            st.put("ws.keepAliveOk", ka);
            st.put("ws.state", stream.state().name());
            st.put("ws.stats", stream.stats());
            st.put("k0RunMin", (clock.getAsLong() - t0) / 60_000L);
            st.check(ka >= 2, "keepAlive OK " + ka + " lan (yeu cau >= 2 trong " + cfg.k0RunMs / 60_000L + "')");
            st.put("apiRestrictions", "KHONG doc bang client futures (sapi) — owner xac nhan quyen rut TAT + IP restrict khi tao key");
            st.check(gw.mutatingCalls() == 0 && mut0 == 0, "K0 da gui " + (gw.mutatingCalls() + mut0) + " lenh ghi (phai 0)");
            if (st.fails.isEmpty() && hasTradeSteps() && state.tmb0 != null) {
                st.put("tmb0", "GIU moc cu " + state.tmb0 + " (da co buoc giao dich; so cai K8 tinh tu moc nay)");
            } else if (st.fails.isEmpty()) {
                AccountSnapshot a2 = gw.account();
                state.tmb0 = a2.getTotalMarginBalance().doubleValue();
                state.tmb0Ms = clock.getAsLong();
                book.anchor(state.tmb0, clock.getAsLong());
                st.put("tmb0", state.tmb0);
            }
        } catch (Abort e) {
            st.check(false, e.getMessage());
        } catch (RuntimeException e) {
            st.check(false, "loi " + e);
        }
        return finish(st);
    }

    private boolean hasTradeSteps() {
        for (String k : state.steps.keySet()) if (!"K0".equals(k) && !"SETUP".equals(k)) return true;
        return false;
    }

    private int keepAliveOk() {
        int n = 0;
        for (Map<String, Object> e : journal.entries()) {
            if ("keepAliveUserStream".equals(e.get("api")) && Boolean.TRUE.equals(e.get("ok"))) n++;
        }
        return n;
    }

    static Map<String, String> assetMap(AccountSnapshot a) {
        Map<String, String> m = new LinkedHashMap<>();
        if (a.getAssets() != null) {
            for (AssetBalance b : a.getAssets()) {
                if (b.getWalletBalance() != null && (b.getWalletBalance().signum() != 0 || STABLE.contains(b.getAsset()))) {
                    m.put(b.getAsset(), b.getWalletBalance().toPlainString());
                }
            }
        }
        return m;
    }

    /** SETUP (ghi, chi 2 symbol canary): CROSSED + leverage 1 qua AccountModeGuard (duong production), one-way. */
    public Result setup() {
        Step st = new Step("SETUP");
        try {
            if (!state.symbolsChosen()) throw new Abort(TU_CHOI, "chua chon symbol (chay canary_preflight truoc)");
            if (state.aborted != null) throw new Abort(TU_CHOI, "phien da DUNG: " + state.aborted);
            build();
            List<String> f = foreignExposure();
            if (!f.isEmpty()) throw new Abort(TU_CHOI, "tai khoan co vi the/lenh ngoai canary: " + f);
            AccountModeGuard.Result g = modeGuard.checkGlobal();
            st.put("global", g.toString());
            st.check(g.isOk(), "GLOBAL: " + g.getProblems());
            for (String s : new String[]{state.symMain, state.symAux}) {
                AccountModeGuard.Result r = modeGuard.checkSymbol(s);
                st.put(s, r.toString());
                st.check(r.isOk(), s + ": " + r.getProblems());
            }
        } catch (Abort e) {
            return refused(st, e);
        } catch (RuntimeException e) {
            st.check(false, "loi " + e);
        }
        return finish(st);
    }

    // ------------------------------------------------------------------ K1..K8
    /** Chay 1 buoc. K6_OPEN / K6B_OPEN: chuan bi (JVM goi se bi kill ngay sau). */
    public Result step(String k) {
        String key = k == null ? "" : k.trim().toUpperCase(Locale.ROOT);
        Step st = new Step(key);
        try {
            switch (key) {
                case "K1": k1(st); break;
                case "K2": k2(st); break;
                case "K3": k3(st); break;
                case "K4": k4(st); break;
                case "K5": k5(st); break;
                case "K6_OPEN": k6Open(st, true); break;
                case "K6_RESTART": k6Restart(st); break;
                case "K6B_OPEN": k6Open(st, false); break;
                case "K6B_RESTART": k6bRestart(st); break;
                case "K7": k7(st); break;
                case "K7B": k7b(st); break;
                case "K8": k8(st); break;
                default:
                    throw new Abort(TU_CHOI, "buoc khong ho tro: " + k);
            }
            checkLoss(true);
        } catch (Abort e) {
            if (TU_CHOI.equals(e.verdict)) return refused(st, e);
            st.check(false, e.getMessage());
            safeFlatten(st, key);
        } catch (RuntimeException e) {
            LOG.error("[CANARY] {} loi: {}", key, e.toString());
            st.check(false, "loi " + e);
            safeFlatten(st, key);
        }
        if (!st.fails.isEmpty() && !key.endsWith("_OPEN") && !"K8".equals(key) && !"K6B_RESTART".equals(key)) {
            safeFlatten(st, key);   // prereg: mac dinh khi TRUOT => dong het
        }
        return finish(st);
    }

    private void safeFlatten(Step st, String k) {
        if (gw == null || book == null) return;
        try {
            st.put("autoFlatten", flattenAll("TRUOT_" + k));
        } catch (Abort e2) {
            st.put("autoFlatten", "dung: " + e2.getMessage());
        } catch (RuntimeException e2) {
            st.put("autoFlatten", "loi " + e2);
        }
    }

    /** K1: MARKET BUY 20 USDT qua executor; (tuy chon MO-5) mat response sau khi gui => queryOrder theo cid, 0 gui lai. */
    void k1(Step st) {
        begin("K1", true);
        String s = state.symMain;
        if (book.isHolding(s) || posAmt(s).signum() != 0 || !ownStops(s).isEmpty()) {
            throw new Abort(TU_CHOI, s + " chua phang (cum/vi the/stop con) — chay canary_flatten truoc K1");
        }
        st.put("balancesBefore", assetMap(gw.account()));
        boolean inject = cfg.injectTimeout;
        if (inject) {
            if (state.injectTimeoutUsed) throw new Abort(TU_CHOI, "MO-5: tiem timeout da dung 1 lan trong phien — tat CANARY_INJECT_TIMEOUT");
            state.injectTimeoutUsed = true;
            saveState();   // ghi TRUOC khi gui (khong bao gio tiem lan 2)
            gw.armTimeoutAfterNextOpen();
            tap.hold();   // su kien stream den truoc: giu lai de executor buoc phai queryOrder(cid)
        }
        st.put("injectTimeout", inject);
        Leg l = openLeg(s);
        st.put("leg", legMap(l));
        st.check(l.confirmed, "leg khong CONFIRMED: " + l.error);
        st.check(gw.sends(l.cid) == 1, "cid " + l.cid + " gui " + gw.sends(l.cid) + " lan (phai dung 1 — idempotency)");
        Map<String, Object> resp = lastCall("newMarketOrder:BUY", l.cid);
        st.put("response", resp);
        if (inject) {
            st.check(lastCall("queryOrder", l.cid) != null, "MO-5: khong thay queryOrder theo cid sau timeout");
            Map<String, Object> q = lastCall("queryOrder", l.cid);
            st.put("queryOrder", q);
            st.check(q != null && "FILLED".equals(q.get("status")), "MO-5: queryOrder khong FILLED");
        } else {
            st.check(resp != null && "FILLED".equals(resp.get("status")), "response khong FILLED");
            st.check(resp != null && l.qty.compareTo(new BigDecimal(String.valueOf(resp.get("executedQty")))) == 0,
                    "executedQty != qty gui");
        }
        String code = errCodeFor(l.cid);
        st.check(code == null || !(code.endsWith(":-2019") || code.endsWith(":-4164")), "TRUOT " + code + " => phuong an B (MO-2), MASTER");
        st.check(l.fillEventMs >= 0, "khong thay ORDER_TRADE_UPDATE FILLED cua " + l.cid);
        if (l.fillEventMs >= 0) st.check(l.fillEventMs - l.sendMs <= 2_000L, "stream tre " + (l.fillEventMs - l.sendMs) + " ms > 2 s");
        bookMatchesExchange(st, s);
        st.put("balancesAfter", assetMap(gw.account()));
    }

    /** Dong nhat ky ghi gan nhat cua api (+cid). */
    Map<String, Object> lastCall(String api, String cid) {
        List<Map<String, Object>> es = journal.entries();
        for (int i = es.size() - 1; i >= 0; i--) {
            Map<String, Object> e = es.get(i);
            if (!api.equals(e.get("api"))) continue;
            if (cid != null && !cid.equals(e.get("cid"))) continue;
            return e;
        }
        return null;
    }

    private String errCodeFor(String cid) {
        for (Map<String, Object> e : journal.entries()) {
            if (cid.equals(e.get("cid")) && Boolean.FALSE.equals(e.get("ok"))) return e.get("errKind") + ":" + e.get("errCode");
        }
        return null;
    }

    /** So = san: qty khop positionRisk; avg lech entryPrice <= 1 tick. */
    void bookMatchesExchange(Step st, String s) {
        Optional<LiveBookC3.ClusterView> c = book.cluster(s);
        Optional<PositionInfo> p = pos(s);
        st.check(c.isPresent() && p.isPresent(), "so/san khong cung co vi the " + s);
        if (!c.isPresent() || !p.isPresent()) return;
        st.put("book.qty", c.get().confirmedQty.toPlainString());
        st.put("ex.qty", p.get().getPositionAmt().toPlainString());
        st.put("book.avg", c.get().avgPrice);
        st.put("ex.entry", p.get().getEntryPrice() == null ? null : p.get().getEntryPrice().toPlainString());
        st.check(c.get().confirmedQty.compareTo(p.get().getPositionAmt()) == 0, "qty so " + c.get().confirmedQty + " != san "
                + p.get().getPositionAmt());
        BigDecimal tick = rules.tickSize(s);
        if (p.get().getEntryPrice() != null && tick != null) {
            double d = Math.abs(c.get().avgPrice - p.get().getEntryPrice().doubleValue());
            st.check(d <= tick.doubleValue() * 1.0001d, "avg so lech san " + d + " > 1 tick " + tick);
        }
    }

    /** Dem stop c3s- NEW cua symbol; ghi vao data; phai == expect. */
    void countStops(Step st, String s, String label, int expect) {
        List<OrderInfo> l = ownStops(s);
        List<String> ids = new ArrayList<>();
        for (OrderInfo o : l) ids.add(o.getClientOrderId() + "@" + o.getStopPrice() + (o.isClosePosition() ? "/cp" : "/qty"));
        st.put("stops." + label, ids);
        st.check(l.size() == expect, label + ": " + l.size() + " stop c3s- NEW (phai " + expect + ")");
    }

    /** K2: dat stop closePosition MARK -20 % (trailing ARM), doi len -19 % (MOVE), thu closePosition thu 2, doi -18 %. */
    void k2(Step st) {
        begin("K2", true);
        String s = state.symMain;
        ensurePosition(s, st);
        LiveBookC3.ClusterView c0 = book.cluster(s).get();
        st.check(c0.stopClientAlgoId == null || ownStops(s).size() == 1, "dau K2: stop trong so khong khop san");
        trailRate(s, -0.20f);
        String a = book.cluster(s).get().stopClientAlgoId;
        st.put("a.cid", a);
        st.check(a != null, "(a) khong dat duoc stop");
        countStops(st, s, "a", 1);
        stopStatus(st, s, a, "a");
        trailRate(s, -0.19f);
        String b = book.cluster(s).get().stopClientAlgoId;
        st.put("b.cid", b);
        st.put("b.qtyMode", book.cluster(s).get().stopQtyMode);
        st.check(b != null && !b.equals(a), "(b) stop khong doi");
        countStops(st, s, "b", 1);
        stopStatus(st, s, b, "b");
        st.check(ownStops(s).stream().noneMatch(o -> o.getClientOrderId().equals(a)), "(b) stop cu A van mo");
        // (c) closePosition thu 2 cung chieu khi B con: du lieu (-4130 hay chap nhan)
        long now = clock.getAsLong();
        String cc = C3LiveCids.stop(s, Math.floorDiv(now, 60_000L), book.nextStopSeq(s, now));
        BigDecimal pc = rules.roundStopPriceForLong(s, mark(s).multiply(new BigDecimal("0.75")));
        try {
            OrderInfo o = gw.newStopMarket(s, Side.SELL, null, pc, cc, true);
            st.put("c.result", "CHAP NHAN status=" + o.getRawStatus());
            OwnStopGuard.Result gr = guard.cancelOwnStopGuarded(s, cc, "K2(c) huy closePosition thu 2");
            st.put("c.cancel", gr.name());
            st.check(gr == OwnStopGuard.Result.CANCELLED || gr == OwnStopGuard.Result.GONE, "(c) khong huy duoc stop thu 2: " + gr);
        } catch (GatewayException e) {
            st.put("c.result", "TU CHOI " + e.getKind() + ":" + e.getExchangeCode() + " " + e.getMessage());
        }
        countStops(st, s, "c", 1);
        trailRate(s, -0.18f);
        String d = book.cluster(s).get().stopClientAlgoId;
        st.put("d.cid", d);
        st.put("d.qtyMode", book.cluster(s).get().stopQtyMode);
        st.check(d != null && !d.equals(b), "(d) stop khong doi");
        countStops(st, s, "d", 1);
        stopStatus(st, s, d, "d");
        st.put("trail.stats", trailing.stats());
    }

    /** queryStop theo clientAlgoId khop + algoStatus NEW trong response dat stop. */
    private void stopStatus(Step st, String s, String cid, String label) {
        if (cid == null) return;
        Optional<OrderInfo> q = gw.queryStop(s, cid);
        st.put(label + ".queryStop", q.map(o -> o.getRawStatus()).orElse("KHONG CO"));
        st.check(q.isPresent() && q.get().getStatus() == OrderStatus.NEW, label + ": queryStop " + cid + " khong NEW");
        String algoStatus = null;
        for (OrderInfo o : gw.stopResponses()) if (cid.equals(o.getClientOrderId())) algoStatus = o.getRawStatus();
        st.put(label + ".algoStatus", algoStatus);
        st.check("NEW".equals(algoStatus), label + ": response algoStatus=" + algoStatus + " (phai NEW)");
    }

    /** K3: stop SELL trigger CAO hon mark => -2021 => bot dong MARKET reduce-only (TRAILING_IMMEDIATE). */
    void k3(Step st) {
        begin("K3", true);
        String s = state.symMain;
        ensurePosition(s, st);
        int ref0 = gw.stopResponses().size();
        trailTo(s, +0.03d);
        Map<String, Object> err = null;
        for (Map<String, Object> e : journal.entries()) {
            Object api = e.get("api");
            if (api != null && api.toString().startsWith("newStopMarket") && Boolean.FALSE.equals(e.get("ok"))) err = e;
        }
        st.put("stopError", err);
        st.check(gw.stopResponses().size() == ref0, "san CHAP NHAN stop tren mark (khong -2021)");
        st.check(err != null && Integer.valueOf(-2021).equals(err.get("errCode")),
                "ma loi " + (err == null ? "khong co" : err.get("errCode")) + " (mong -2021) => A1 cap nhat ErrorMapper");
        long w = waitClusterGone(s, cfg.closeWaitMs);
        st.put("closeMs", w);
        st.check(w >= 0, "cum chua dong sau " + cfg.closeWaitMs + " ms");
        st.check(posAmt(s).signum() == 0, "vi the con " + posAmt(s));
        long ws = waitNoOwnStops(s, cfg.orphanWaitMs);
        st.check(ws >= 0, "con stop c3s- sau dong");
        String led = lastLedgerLine(s);
        st.put("ledger", led);
        st.check(led != null && led.contains(TrailingStopManager.REASON_TRAIL_IMMEDIATE), "ledger khong ghi TRAILING_IMMEDIATE");
    }

    String lastLedgerLine(String sym) {
        File f = new File(dir, LiveBookC3.LEDGER_NAME);
        if (!f.exists()) return null;
        try {
            List<String> ls = Files.readAllLines(f.toPath(), StandardCharsets.UTF_8);
            for (int i = ls.size() - 1; i >= 0; i--) if (ls.get(i).startsWith(sym + ",")) return ls.get(i);
        } catch (IOException e) {
            return null;
        }
        return null;
    }

    /** K4: stop o mark -0,15 % (ratchet theo mark), cho san kich that; so dong cum ly do TRAILING, 0 stop mo coi <= 30 s. */
    void k4(Step st) {
        begin("K4", true);
        String s = state.symMain;
        ensurePosition(s, st);
        trailTo(s, -0.0015d);
        String sid = book.cluster(s).map(c -> c.stopClientAlgoId).orElse(null);
        st.put("stop.first", sid);
        st.check(sid != null, "khong dat duoc stop");
        long t0 = clock.getAsLong();
        long[] lastMove = {t0};
        long w = waitFor(() -> {
            if (!book.isHolding(s)) return true;
            if (clock.getAsLong() - lastMove[0] >= 5_000L) {
                lastMove[0] = clock.getAsLong();
                try {
                    trailTo(s, -0.0015d);   // ratchet: chi doi len
                } catch (RuntimeException e) {
                    journal.ev("K4_MOVE_ERROR", "err", e.toString());
                }
            }
            return !book.isHolding(s);
        }, cfg.k4WaitMs);
        st.put("triggerWaitMs", w);
        if (!st.check(w >= 0, "stop KHONG kich trong " + cfg.k4WaitMs / 60_000L + "'")) return;
        String led = lastLedgerLine(s);
        st.put("ledger", led);
        if (led == null || !led.contains(FillAccounting.REASON_TRAILING)) {
            st.put("MIN_reason", "ly do dong khong phai TRAILING (" + led + ") => MIN cap nhat nhan dien (khong dung)");
        }
        long ws = waitNoOwnStops(s, 30_000L);
        st.put("orphanWaitMs", ws);
        st.check(ws >= 0, "stop c3s- mo coi > 30 s sau khi cum dong");
        st.check(posAmt(s).signum() == 0, "vi the con");
        st.put("events.algo", eventsFor("ALGO_UPDATE", s));
        st.put("events.order", eventsFor("ORDER_TRADE_UPDATE", s));
        st.put("events.account", eventsFor("ACCOUNT_UPDATE", null));
        st.put("openAlgoAfter", gw.openStops(s).size());
    }

    private List<Map<String, Object>> eventsFor(String type, String sym) {
        List<Map<String, Object>> out = new ArrayList<>();
        synchronized (streamEvents) {
            for (Map<String, Object> e : streamEvents) {
                if (!type.equals(e.get("e"))) continue;
                if (sym != null && e.get("s") != null && !sym.equals(e.get("s"))) continue;
                out.add(e);
            }
        }
        return out.size() > 20 ? out.subList(out.size() - 20, out.size()) : out;
    }

    /** K5: dong cum bang closeCluster(TIME_STOP_168H): c3x- reduce-only FILLED, guard huy stop (CANCELLED), 0 algo. */
    void k5(Step st) {
        begin("K5", true);
        String s = state.symMain;
        ensurePosition(s, st);
        if (book.cluster(s).get().stopClientAlgoId == null) trailRate(s, -0.20f);
        String sid = book.cluster(s).get().stopClientAlgoId;
        st.put("stop", sid);
        st.check(sid != null, "khong co stop truoc khi dong");
        long w = closeCluster(s, TrailingStopManager.REASON_TIME_STOP);
        st.put("closeMs", w);
        st.check(w >= 0, "cum chua dong");
        Map<String, Object> close = null;
        for (Map<String, Object> e : journal.entries()) {
            Object c = e.get("cid");
            if ("newMarketOrder:SELL:RO".equals(e.get("api")) && c != null && c.toString().startsWith(C3LiveCids.CLOSE_PREFIX)
                    && s.equals(e.get("symbol"))) close = e;
        }
        st.put("closeOrder", close);
        st.check(close != null && "FILLED".equals(close.get("status")), "lenh c3x- khong FILLED");
        long ws = waitNoOwnStops(s, cfg.orphanWaitMs);
        st.check(ws >= 0, "stop chua huy");
        Map<String, Object> cancel = lastCall("cancelStop", sid);
        st.put("guardCancel", cancel);
        st.check(cancel != null && Boolean.TRUE.equals(cancel.get("ok")), "guard khong huy stop " + sid + " (CANCELLED)");
        st.check(posAmt(s).signum() == 0, "vi the con");
        BigDecimal a = acctAmt(s);
        st.check(a != null && a.signum() == 0, "account().positions chua phang");
        st.check(gw.openStops(s).isEmpty(), "con algo mo");
    }

    /** 12 truong cum so voi anh chup (K6). */
    static Map<String, Object> snapshot(LiveBookC3.ClusterView c) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("tsFirstLeg", c.tsFirstLeg);
        m.put("legCount", c.legCount);
        m.put("confirmedQty", c.confirmedQty.toPlainString());
        m.put("avgEntryF", Float.floatToIntBits(c.avgEntryF));
        m.put("peakRate", Float.floatToIntBits(c.peakRate));
        m.put("priceSL", Float.floatToIntBits(c.priceSL));
        m.put("stopClientAlgoId", c.stopClientAlgoId);
        m.put("stopPrice", Double.doubleToLongBits(c.stopPrice));
        m.put("symbolPred", c.symbolPred == null ? null : Float.floatToIntBits(c.symbolPred));
        m.put("rank", c.rank);
        m.put("stopSeq", c.stopSeq);
        m.put("peak", Double.doubleToLongBits(c.peak));
        // luu dang CHUOI: JSON (Gson) doc so nguyen 64-bit thanh double => mat bit (doubleToLongBits ~ 4.6E18)
        m.replaceAll((k, v) -> v == null ? null : String.valueOf(v));
        return m;
    }

    /** K6_OPEN / K6B_OPEN: mo 20 USDT + stop da arm, chup cum; JVM goi se bi kill ngay sau (Runtime.halt). */
    void k6Open(Step st, boolean snapshotForK6) {
        begin(st.k, true);
        String s = state.symMain;
        ensurePosition(s, st);
        if (book.cluster(s).get().stopClientAlgoId == null) trailRate(s, -0.20f);
        LiveBookC3.ClusterView c = book.cluster(s).get();
        st.check(c.stopClientAlgoId != null, "khong arm duoc stop");
        countStops(st, s, "open", 1);
        if (snapshotForK6) {
            state.k6Snapshot = new LinkedHashMap<>(snapshot(c));
            state.k6SnapshotSymbol = s;
            saveState();
            st.put("snapshot", state.k6Snapshot);
        }
    }

    /** K6_RESTART: JVM moi doc so -> resolveUnresolved + reconcile khoi dong; 12 truong bit-identical; 0 lenh truoc reconcile; 0 stop trung. */
    void k6Restart(Step st) {
        begin("K6", true);
        String s = state.symMain;
        long mut0 = gw.mutatingCalls();
        int left = executor.resolveUnresolved(true);
        Reconciler.Report r = rec.startup();
        long mutDuring = gw.mutatingCalls() - mut0;
        st.put("legTreo", left);
        st.put("report", r.toString());
        st.put("mutatingBeforeReconcileDone", mutDuring);
        st.check(r.ok, "reconcile khoi dong LOI: " + r.error);
        st.check(mutDuring == 0, mutDuring + " lenh ghi truoc/trong reconcile khoi dong (phai 0)");
        st.check(r.overridden.isEmpty() && r.stopsDropped.isEmpty() && r.orphanCancelled.isEmpty() && r.unknownPositions.isEmpty()
                && r.closedWhileDown.isEmpty(), "reconcile khong sach: " + r);
        Optional<LiveBookC3.ClusterView> c = book.cluster(s);
        st.check(c.isPresent(), "so khong con cum " + s);
        if (c.isPresent()) {
            Map<String, Object> now = snapshot(c.get());
            Map<String, Object> was = state.k6Snapshot;
            st.put("snapshotNow", now);
            st.check(s.equals(state.k6SnapshotSymbol) && was != null && !was.isEmpty(), "khong co anh chup K6_OPEN");
            if (was != null) {
                for (Map.Entry<String, Object> e : now.entrySet()) {
                    Object w = was.get(e.getKey());
                    st.check(sameVal(w, e.getValue()), "truong " + e.getKey() + " khac: truoc=" + w + " sau=" + e.getValue());
                }
            }
        }
        countStops(st, s, "afterRestart", 1);
        int ns0 = (int) journal.entries().stream().filter(e -> String.valueOf(e.get("api")).startsWith("newStopMarket")).count();
        trailing.step(px(s));   // nhip trailing sau restart: KHONG dat stop trung
        int ns1 = (int) journal.entries().stream().filter(e -> String.valueOf(e.get("api")).startsWith("newStopMarket")).count();
        st.check(ns1 == ns0, "trailing dat them " + (ns1 - ns0) + " stop sau restart");
        countStops(st, s, "afterTrail", 1);
        bookMatchesExchange(st, s);
    }

    static boolean sameVal(Object a, Object b) {
        if (a == null || b == null) return a == b;
        if (a instanceof Number && b instanceof Number) {
            return new BigDecimal(a.toString()).compareTo(new BigDecimal(b.toString())) == 0;
        }
        return a.toString().equals(b.toString());
    }

    /** K6B_RESTART: so da bi doi ten (script) => startup: stop c3s- VAN CON, symbol vao UNKNOWN (A), Telegram, 0 huy stop. */
    void k6bRestart(Step st) {
        if (new File(dir, BOOK_NAME).exists()) throw new Abort(TU_CHOI, "K6b: so van con (script phai doi ten so truoc)");
        begin("K6b", true);
        String s = state.symMain;
        int cancels0 = countApi("cancelStop");
        Reconciler.Report r = rec.startup();
        st.put("report", r.toString());
        st.check(r.ok, "reconcile loi: " + r.error);
        st.check(!r.orphanKept.isEmpty(), "orphanKept rong (stop c3s- khong duoc GIU)");
        st.check(r.orphanCancelled.isEmpty(), "stop bi HUY khi so mat (MAJ-3 hoi quy) => DUNG TOAN BO lo trinh");
        st.check(r.unknownPositions.contains(s), "unknownPositions khong co " + s);
        st.check(rec.blocks().containsKey(Reconciler.BLOCK_UNKNOWN), "khong chan UNKNOWN_POSITION (A)");
        st.check(countApi("cancelStop") == cancels0, "co lenh huy stop");
        countStops(st, s, "afterRestart", 1);
        st.check(!alerts().isEmpty(), "khong co Telegram");
        st.put("alerts", alerts());
        st.put("next", "script tu chay canary_flatten (owner dong tay theo prereg)");
    }

    private int countApi(String api) {
        int n = 0;
        for (Map<String, Object> e : journal.entries()) if (api.equals(e.get("api"))) n++;
        return n;
    }

    /**
     * K7: co vi the + stop; CAT websocket phia client (dong socket + chan noi lai) trong k7CutMs: phat hien <= 15 s, fallback REST
     * moi 10 s, Telegram sau 5'; noi lai => bu REST; 0 cum/stop bi xoa sai; so = san. Cuoi buoc dong cum (phang).
     */
    void k7(Step st) {
        begin("K7", true);
        String s = state.symMain;
        ensurePosition(s, st);
        if (book.cluster(s).get().stopClientAlgoId == null) trailRate(s, -0.20f);
        String sid = book.cluster(s).get().stopClientAlgoId;
        BigDecimal qty0 = book.cluster(s).get().confirmedQty;
        st.check(stream.isConnected(), "stream chua ket noi truoc khi cat");
        long fb0 = stream.fallbackCount();
        long cu0 = stream.catchUpCount();
        int al0 = alerts().size();
        long tCut = clock.getAsLong();
        tap.cut();
        long det = waitFor(() -> !stream.isConnected(), 15_000L);
        st.put("detectMs", det);
        st.check(det >= 0 && det <= 15_000L, "khong phat hien mat stream trong 15 s");
        pump(Math.max(0L, cfg.k7CutMs - (clock.getAsLong() - tCut)));
        long fb = stream.fallbackCount() - fb0;
        long cutMs = clock.getAsLong() - tCut;
        st.put("cutMs", cutMs);
        st.put("fallbackRuns", fb);
        st.check(fb >= Math.max(1L, cutMs / 10_000L - 3L), "fallback REST chi " + fb + " lan trong " + cutMs / 1000 + " s (mong ~moi 10 s)");
        boolean tg = false;
        List<String> al = alerts();
        for (int i = al0; i < al.size(); i++) if (al.get(i).contains("mat user stream")) tg = true;
        st.put("telegramDown", tg);
        if (cutMs >= 300_000L) st.check(tg, "khong co Telegram mat stream sau 5'");
        st.check(book.isHolding(s), "cum bi xoa SAI trong luc mat stream");
        st.check(sid != null && sid.equals(book.cluster(s).map(c -> c.stopClientAlgoId).orElse(null)), "stop trong so bi doi/xoa");
        st.check(ownStops(s).stream().anyMatch(o -> o.getClientOrderId().equals(sid)), "stop tren san bi huy SAI");
        tap.restore();
        long rc = waitFor(stream::isConnected, 90_000L);
        st.put("reconnectMs", rc);
        st.check(rc >= 0, "khong noi lai duoc stream sau 90 s");
        long cu = waitFor(() -> stream.catchUpCount() > cu0, 15_000L);
        st.check(cu >= 0, "khong bu REST sau khi noi lai");
        st.check(qty0.compareTo(book.cluster(s).map(c -> c.confirmedQty).orElse(BigDecimal.ZERO)) == 0, "qty so doi sau mat stream");
        bookMatchesExchange(st, s);
        long w = closeCluster(s, "K7_END");
        st.check(w >= 0 && posAmt(s).signum() == 0, "khong dong duoc cum cuoi K7");
        st.check(waitNoOwnStops(s, cfg.orphanWaitMs) >= 0, "con stop sau dong K7");
    }

    /**
     * K7b: symbol chinh vua chot trong luc positionRisk LOI (tiem phia client) => lop (B) chi chan symbol chinh; symbol phu VAO
     * DUOC 1 leg that; (A) khong xuat hien neu &lt; 10'; go (B) sau 2 lan doc phang + account phang; dong symbol phu.
     */
    void k7b(Step st) {
        begin("K7b", true);
        String s1 = state.symMain;
        String s2 = state.symAux;
        if (book.isHolding(s2) || posAmt(s2).signum() != 0) throw new Abort(TU_CHOI, s2 + " chua phang truoc K7b");
        // nhu runtime chinh: reconcile khoi dong truoc (go chan STARTUP_RECON) — K7b do lop chan theo symbol, khong phai chan khoi dong
        Reconciler.Report r0 = rec.startup();
        st.put("startup", r0.toString());
        st.put("startup.blocks", rec.blocks().toString());
        if (!st.check(r0.ok && rec.blocks().isEmpty(), "reconcile khoi dong khong sach: " + r0 + " blocks=" + rec.blocks())) return;
        ensurePosition(s1, st);
        if (book.cluster(s1).get().stopClientAlgoId == null) trailRate(s1, -0.20f);
        waitNewMinuteForClose(s1);
        gw.failPositions = true;
        long tInj = clock.getAsLong();
        journal.ev("K7B_INJECT_ON", "what", "positionRisk loi phia client");
        flattener.closeCluster(s1, "K7B_CLOSE");
        long gone = waitFor(() -> !book.isHolding(s1), cfg.closeWaitMs);
        st.put("s1.closeMs", gone);
        st.check(gone >= 0, s1 + " khong dong duoc (trong luc tiem loi doc)");
        long tClose = clock.getAsLong();
        boolean b1 = !rec.allowsEntry(s1);
        boolean b2 = rec.allowsEntry(s2);
        st.put("afterClose.blocks", rec.blocks().toString());
        st.put("afterClose.symBlocks", rec.symbolBlocks().toString());
        st.check(b1, s1 + " KHONG bi chan (phai B) ngay sau khi chot");
        st.check(b2, s2 + " bi chan trong luc " + s1 + " o lop B (loi alpha)");
        st.check(!rec.blocks().containsKey(Reconciler.BLOCK_UNKNOWN), "chan TOAN HE (A) ngay khi chot");
        Leg l2 = null;
        if (b2) {
            l2 = openLeg(s2);
            st.put("s2.leg", legMap(l2));
            st.check(l2.confirmed, s2 + " vao lenh khong khop: " + l2.error);
        }
        List<String> timeline = new ArrayList<>();
        long[] aSeen = {-1L};
        long[] lastT = {Long.MIN_VALUE / 2};
        BooleanSupplier observe = () -> {
            long t = clock.getAsLong();
            boolean a = rec.blocks().containsKey(Reconciler.BLOCK_UNKNOWN);
            if (a && aSeen[0] < 0) aSeen[0] = t;
            if (t - lastT[0] >= 10_000L) {
                lastT[0] = t;
                timeline.add(((t - tClose) / 1000) + "s A=" + a + " B=" + rec.symbolBlocks());
            }
            return false;
        };
        long injLeft = Math.max(0L, cfg.k7bInjectMs - (clock.getAsLong() - tInj));
        waitFor(observe, injLeft);
        gw.failPositions = false;
        journal.ev("K7B_INJECT_OFF");
        long rel = waitFor(() -> {
            observe.getAsBoolean();
            return rec.allowsEntry(s1);
        }, OwnStopGuard.KNOWN_CLOSE_WINDOW_MS + 120_000L);
        long bMs = rel >= 0 ? clock.getAsLong() - tClose : -1L;
        st.put("timeline", timeline);
        st.put("s1.blockedMs", bMs);
        st.put("A.firstSeenAfterCloseMs", aSeen[0] < 0 ? null : aSeen[0] - tClose);
        if (aSeen[0] >= 0) {
            long aAfter = aSeen[0] - tClose;
            st.check(aAfter >= OwnStopGuard.KNOWN_CLOSE_WINDOW_MS, "chan TOAN HE (A) sau " + aAfter / 1000 + " s < 10'");
            boolean tg = false;
            for (String m : alerts()) if (m.contains("UNKNOWN_POSITION")) tg = true;
            st.check(tg, "len (A) nhung khong co Telegram");
        }
        st.check(rel >= 0, s1 + " khong duoc go chan");
        st.check(bMs < 0 || bMs < OwnStopGuard.KNOWN_CLOSE_WINDOW_MS || aSeen[0] >= 0, "(B) keo dai > 10' ma khong leo thang (A)");
        st.check(waitNoOwnStops(s1, cfg.orphanWaitMs + 60_000L) >= 0, s1 + " con stop c3s- sau khi go chan");
        if (l2 != null && l2.confirmed) {
            long w = closeCluster(s2, "K7B_END");
            st.check(w >= 0 && posAmt(s2).signum() == 0, "khong dong duoc " + s2);
            st.check(waitNoOwnStops(s2, cfg.orphanWaitMs) >= 0, s2 + " con stop");
        }
        st.check(posAmt(s1).signum() == 0, s1 + " con vi the");
    }

    /** K8: cuoi phien — 0 vi the / 0 algo / 0 lenh; equity so cai doc lap (tmb0 + rp - phi + funding) lech tmb <= 1 %. */
    void k8(Step st) {
        begin("K8", false);
        List<String> pos = new ArrayList<>();
        for (PositionInfo p : gw.positions()) {
            if (p.getPositionAmt() != null && p.getPositionAmt().signum() != 0) pos.add(p.getSymbol() + "=" + p.getPositionAmt());
        }
        AccountSnapshot a = gw.account();
        List<String> apos = new ArrayList<>();
        if (a.getPositions() != null) {
            for (PositionInfo p : a.getPositions()) {
                if (p.getPositionAmt() != null && p.getPositionAmt().signum() != 0) apos.add(p.getSymbol() + "=" + p.getPositionAmt());
            }
        }
        int no = gw.openOrders(null).size();
        int ns = gw.openStops(null).size();
        st.put("positionRisk", pos);
        st.put("accountPositions", a.getPositions() == null ? "null" : apos.toString());
        st.put("openOrders", no);
        st.put("openAlgo", ns);
        st.check(pos.isEmpty(), "con vi the " + pos);
        st.check(a.getPositions() != null && apos.isEmpty(), "account().positions khong phang");
        st.check(no == 0 && ns == 0, "con lenh/algo mo (" + no + "/" + ns + ")");
        st.check(book.openCount() == 0, "so canary con " + book.openCount() + " cum");
        double tmb = a.getTotalMarginBalance().doubleValue();
        double exp;
        synchronized (stateLock) {
            exp = state.tmb0 + state.cumRealized - state.cumFeeStable + state.cumFunding;
            st.put("ledger.tmb0", state.tmb0);
            st.put("ledger.realized", state.cumRealized);
            st.put("ledger.feeStable", state.cumFeeStable);
            st.put("ledger.funding", state.cumFunding);
            st.put("ledger.feeOther", state.feeOther);
            st.put("ledger.fills", state.fills);
        }
        double diff = Math.abs(exp - tmb);
        st.put("tmb", tmb);
        st.put("equityLedger", exp);
        st.put("diffUsd", diff);
        st.put("diffFrac", diff / tmb);
        st.put("balances", assetMap(a));
        st.put("cost", state.cumFeeStable - state.cumRealized - state.cumFunding);
        st.check(diff / tmb <= 0.01d, "equity so cai lech tmb " + fmt(diff / tmb * 100) + "% > 1%");
        st.check(state.cumFeeStable - state.cumRealized - state.cumFunding <= CanaryLimits.LOSS_CAP_USDT,
                "chi phi > " + CanaryLimits.LOSS_CAP_USDT + " USDT");
        st.check(state.feeOther.isEmpty(), "phi tra bang tai san ngoai stable " + state.feeOther + " (so cai khong quy doi duoc)");
        st.put("maxWeight1m", gw.maxWeight1m());
    }

    // ------------------------------------------------------------------ flatten / cleanup / status
    /** Khan cap: dong 2 symbol canary (khong cham symbol khac), huy stop c3s- qua guard. Chay ca khi phien da DUNG. */
    public Result flatten() {
        Step st = new Step("FLATTEN");
        try {
            if (!state.symbolsChosen()) throw new Abort(TU_CHOI, "chua chon symbol — khong co gi de dong");
            build();
            ExchangeInfo ei = gw.exchangeInfo();
            rules = new SymbolRules(ei, clock.getAsLong());
            List<String> f = foreignExposure();
            st.put("foreign_KHONG_CHAM", f);
            st.put("streamMs", ensureStream());
            Map<String, Object> out = flattenAll("OWNER");
            st.put("result", out);
            for (String s : new String[]{state.symMain, state.symAux}) {
                st.check(posAmt(s).signum() == 0, s + " con vi the " + posAmt(s));
                st.check(ownStops(s).isEmpty(), s + " con stop c3s-");
            }
        } catch (Abort e) {
            return refused(st, e);
        } catch (RuntimeException e) {
            st.check(false, "loi " + e);
        }
        return finish(st);
    }

    /** Ket thuc: 0 vi the / 0 algo / 0 lenh tren TOAN tai khoan (doc). */
    public Result cleanupCheck() {
        Step st = new Step("CLEANUP");
        try {
            build();
            int np = 0;
            for (PositionInfo p : gw.positions()) if (p.getPositionAmt() != null && p.getPositionAmt().signum() != 0) np++;
            int no = gw.openOrders(null).size();
            int ns = gw.openStops(null).size();
            st.put("positions", np);
            st.put("openOrders", no);
            st.put("openAlgo", ns);
            st.check(np == 0, np + " vi the");
            st.check(no == 0, no + " lenh mo");
            st.check(ns == 0, ns + " algo mo");
        } catch (RuntimeException e) {
            st.check(false, "loi " + e);
        }
        return finish(st);
    }

    /** Trang thai phien (khong goi san). */
    public String statusJson() {
        synchronized (stateLock) {
            return state.toJson();
        }
    }

    // ------------------------------------------------------------------ ket qua
    static String displayName(String k) {
        switch (k) {
            case "K6_RESTART": return "K6";
            case "K6B_RESTART": return "K6b";
            case "K6B_OPEN": return "K6b_OPEN";
            case "K7B": return "K7b";
            default: return k;
        }
    }

    private Result refused(Step st, Abort e) {
        st.fails.add(e.getMessage());
        journal.ev("STEP_REFUSED", "k", st.k, "why", e.getMessage());
        Result r = new Result(displayName(st.k), TU_CHOI, st.fails, st.data);
        LOG.warn("[CANARY] {}", r.line());
        return r;
    }

    private Result finish(Step st) {
        String verdict = st.fails.isEmpty() ? DAT : TRUOT;
        String name = displayName(st.k);
        st.put("ms", clock.getAsLong() - st.t0);
        if (gw != null) {
            st.put("maxWeight1m", gw.maxWeight1m());
            st.put("http429_418", gw.rateLimitedCount());
            st.put("guardRefused", gw.refusedCalls());
        }
        CanaryState.StepRecord rec0 = new CanaryState.StepRecord();
        rec0.result = verdict;
        rec0.ms = clock.getAsLong();
        rec0.fails = new ArrayList<>(st.fails);
        rec0.data = CanaryJournal.sanitize(st.data);
        synchronized (stateLock) {
            state.steps.put(name, rec0);
        }
        saveState();
        Map<String, Object> j = new LinkedHashMap<>();
        j.put("k", name);
        j.put("verdict", verdict);
        j.put("fails", st.fails);
        j.put("data", st.data);
        journal.event("STEP_RESULT", j);
        Result r = new Result(name, verdict, st.fails, st.data);
        LOG.warn("[CANARY] {}", r.line());
        return r;
    }
}
