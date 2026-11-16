package com.binance.chuyennd.c3live.e2e.replay;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.onnx.entry.E2eGateSupport;
import com.binance.chuyennd.c3live.adapter.DryGateway;
import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.IncomeRecord;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.exec.FillPriceResolver;
import com.binance.chuyennd.c3live.exit.C3StopProtector;
import com.binance.chuyennd.c3live.exit.TrailingStopManager;
import com.binance.chuyennd.c3live.fill.FillAccounting;
import com.binance.chuyennd.c3live.fill.UserStream;
import com.binance.chuyennd.c3live.fill.UserStreamEvents;
import com.binance.chuyennd.c3live.filters.SymbolRules;
import com.binance.chuyennd.c3live.guard.AccountModeGuard;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.rate.ProductionRatePolicy;
import com.binance.chuyennd.c3live.rate.RateGuard;
import com.binance.chuyennd.c3live.recon.OwnStopGuard;
import com.binance.chuyennd.c3live.recon.Reconciler;
import com.binance.chuyennd.c3live.risk.C3LiveFlattener;
import com.binance.chuyennd.c3live.risk.C3MainEquity;
import com.binance.chuyennd.c3live.scope.C3LegacyRefresher;
import com.binance.chuyennd.c3live.scope.C3MergedGuard;
import com.binance.chuyennd.c3live.scope.C3Scope;
import com.binance.chuyennd.c3live.scope.C3ScopedGateway;
import com.binance.chuyennd.c3live.scope.C3StreamScope;
import com.binance.chuyennd.c3live.universe.SymbolUniverseLive;
import com.binance.chuyennd.c3live.universe.TradFiClassifier;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.ops.KillSwitchEngine;
import com.binance.chuyennd.ops.OpsConfig;
import com.binance.chuyennd.tradecore.Cfg;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.DcaUtils;
import com.binance.chuyennd.tradecore.EntryGate;
import com.binance.chuyennd.tradecore.TradeUtils;
import com.binance.chuyennd.tradecore.selector.LegacySymbols;
import com.binance.chuyennd.tradecore.selector.LiveDcaGridC3;
import com.binance.chuyennd.tradecore.selector.LiveGridSizing;
import com.binance.chuyennd.tradecore.selector.LiveProfileC3;
import com.binance.chuyennd.trading.GatePreFilter;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Predicate;
import java.util.zip.GZIPOutputStream;

/**
 * [E2E_REPLAY] Gian replay NGAY SAP (docs/c3live/E2E_REPLAY.md): tang quyet dinh production (GatePreFilter.runSelector ->
 * AIRejectFilter.entryGate -> LiveGateRollingRatio) + lop thuc thi c3_live production noi day y C3LiveRuntime (pham vi tai
 * khoan chinh R4) tren san gia {@link FakeExchange1m} hoac {@link DryGateway}; dong ho gia; ghi trace + kiem tieu chi.
 */
final class CrashDayRig {

    private static final Logger LOG = LoggerFactory.getLogger(CrashDayRig.class);
    static final long MIN = 60_000L;
    static final long H = 3_600_000L;
    // [E2E_V12] KHONG gan cung tham so chien luoc: moi gia tri doc qua Cfg/env (dat bang env 242 danh sach trang + override
    //   khai truoc trong tools/e2e/run_lane.sh). Rig cu gan cung PCT/DAYS/GS/MOM15/CAPITAL/dcaGridEnabled(true) => da xoa.
    static final int TOPK = Integer.parseInt(Cfg.getOr("SELECTOR_RANK_TOPK", "-1").trim());
    static final double CAPITAL = parseD(Cfg.get("C3_CAPITAL"), parseD(Cfg.get("LIVE_C3_PILOT_CAPITAL"), 10_000d));
    static final long GRACE_MS = 61_000L;
    // S-DCA: he so gia tong hop theo pha 10' (bac grid -0,50/-0,75/-0,90 tinh tren gia vao leg dau)
    static final double[] SDCA_FACTORS = {0.40d, 0.20d, 0.07d};
    static final long SDCA_PHASE_MS = 10 * 60_000L;
    // [ERRATA1 E5] S-DCA tong hop dieu kien thi truong + p15 (= ref_v12.py SDCA_DIP_OFFS / SDCA_P15_ZERO_OFF; SPEC ?R7b)
    static final long[] SDCA_DIP_OFFS = {2L, 3L, 12L, 22L};
    static final long SDCA_P15_ZERO_OFF = 2L;
    static final long SDCA_MKT_WIN = 30L;

    static double parseD(String v, double def) {
        if (v == null || v.trim().isEmpty()) return def;
        return Double.parseDouble(v.trim());
    }

    enum Venue { FAKE, DRY }

    enum HeldMode { NONE_V11, SHADOW_R4H, OWN_BOOK }

    static final class Opts {
        String name;
        Venue venue = Venue.FAKE;
        HeldMode held = HeldMode.OWN_BOOK;
        boolean a1 = true;
        boolean exec = true;
        long end = ReplayData.END;
        long wsDownFrom = -1, wsDownTo = -1;            // F1
        long rlAt = -1;                                  // F2: tu moc nay, n lenh MARKET ke tiep + m stop ke tiep => 429
        int rlOrders = 0, rlStops = 0;
        boolean ackNoAvg = false;                        // F3
        long expireDelayMs = 0L;                         // F4
        final Set<String> legacy = new TreeSet<>();      // F5: LEGACY giu tu truoc START
        String mergeSymbol = null;                       // F5: bot LEGACY mua symbol c3 dang giu
        long mergeAt = -1;
        long ddAt = -1;                                  // F6a
        double ddUsd = 0d;
        long c1From = -1, c1To = -1;                     // F6b
        long sDcaAt = -1;                                // S-DCA: moc chon cum (xem SDCA_FACTORS)
        int sDcaN = 2;                                   // S-DCA: so cum ep gia (>= 2 theo prereg D1)
        long finInjAt = -1;                              // FIN-INJ: leg PREDICT PASS dau tien o phut >= moc nay bi bo khoi tap fin
    }

    final Opts o;
    final ReplayData d;
    final File out;
    final AtomicLong now = new AtomicLong(ReplayData.START);
    final List<String> alerts = new CopyOnWriteArrayList<>();
    final List<String> ksLines = new CopyOnWriteArrayList<>();
    final List<String> journal = new CopyOnWriteArrayList<>();
    final List<String> errors = new ArrayList<>();
    final List<String> traceRows = new ArrayList<>();
    final List<String> outcomeRows = new ArrayList<>();
    final List<String> eventRows = new ArrayList<>();
    final Map<String, Object> res = new LinkedHashMap<>();
    final Map<String, Boolean> crit = new LinkedHashMap<>();
    final Map<String, List<String>> viol = new LinkedHashMap<>();
    final Map<String, Float> lastPx = new HashMap<>();
    final Map<String, BigDecimal> lastPxBd = new HashMap<>();
    final Map<String, BigDecimal> legacyQty = new TreeMap<>();
    final Map<String, double[]> truth = new TreeMap<>();          // symbol -> [rp, fee] cac khop c3 (su that san)
    final Map<String, double[]> c3Vwap = new TreeMap<>();         // [r4p Bug4] symbol -> [qty, cost, rp theo VWAP c3] tu khop san
    final Set<String> everMerged = new TreeSet<>();               // [r4p Bug4] symbol tung MERGED trong lan chay
    final Map<String, Integer> buyCidCount = new HashMap<>();
    final Map<Long, Float> qByHour = new TreeMap<>();

    FakeExchange1m fake;
    DryGateway dry;
    ExchangeGateway raw;
    CountingGateway cnt;
    KillSwitchEngine ks;
    LiveBookC3 book;
    C3Scope scope;
    C3ScopedGateway sgw;
    FillAccounting acct;
    Reconciler rec;
    C3LiveOrderExecutor ex;
    C3LiveEntry entry;
    C3LiveFlattener flat;
    TrailingStopManager mgr;
    C3MergedGuard merged;
    C3StreamScope stream;
    C3StopProtector protector;
    C3LegacyRefresher refresher;
    C3MainEquity eq;
    OwnStopGuard guard;
    OrderAuditLog audit;
    SymbolUniverseLive uni;
    SymbolRules rules;
    AIRejectFilter gate;
    UserStream us;
    volatile UserStream.Listener wsListener;
    volatile boolean wsUp = true;
    final Map<String, BigDecimal> refs = new HashMap<>();
    String persist;
    long lastResolve = Long.MIN_VALUE / 2, lastHourly, lastBook = Long.MIN_VALUE / 2, lastPeriodic = Long.MIN_VALUE / 2;
    long lastUni = Long.MIN_VALUE / 2;
    /** [ERRATA3 E11] nhip production C3LiveRuntime:75-78: vong ops 5 s, exitTick (mgr.step) 10 s, onBook (equity) 15 s.
     *  Gia DAU VAO chi co 4 moc/phut (+0/+15/+30/+45 s = O, cuc 1, cuc 2, C cua nen 1m) - do phan giai du lieu, KHONG phai nhip exit. */
    static final long OPS_MS = 5_000L, EXIT_MS = 10_000L, PX_MS = 15_000L;
    long lastExit = Long.MIN_VALUE / 2;
    Set<String> lastLatch = new TreeSet<>();
    long latchFlattenAt = -1;
    int rlOrdersLeft, rlStopsLeft;
    boolean rlArmed, merged0, dd0, sdca0, finInj0;
    final Map<String, Long> sdcaStart = new LinkedHashMap<>();     // S-DCA: symbol -> phut bat dau ep gia
    long sdcaSt = -1;                                              // S-DCA: moc chon cum (tm)
    final List<String> marketRows = new ArrayList<>();             // [ERRATA1 N6] dieu kien thi truong moi phut quyet dinh
    int nMktBig, nMktAlt, nMktNull;
    String curDcaTag = "";
    final Map<String, Long> firstLegBar = new HashMap<>();         // symbol -> phut quyet dinh leg dau cum dang mo (harness)
    String finInjSym;
    long finInjBar = -1;
    int nFinExcl;
    final List<String> fillRows = new ArrayList<>();                // khop c3 (su that san): ms,symbol,side,qty,price,cid
    final List<String> finRows = new ArrayList<>();
    final Map<String, Long> gapSince = new HashMap<>();
    final Map<String, Long> orphanPosSince = new HashMap<>();
    final Map<String, Long> orphanStopSince = new HashMap<>();
    final Map<String, double[]> lastStop = new HashMap<>();       // sym -> [stopPrice, tsFirstLeg, legCount]
    final Map<String, Long> armedAt = new HashMap<>();
    final Map<String, Long> firstStopAt = new HashMap<>();
    int nArm, nStopMoves, nDcaDue, nDcaSubmitted, maxOpen, maxStopsSeen;
    final List<String> submittedCids = new ArrayList<>();
    final Map<String, Long> submitTime = new HashMap<>();
    final Map<String, String> cidSym = new HashMap<>();
    final Map<String, Long> confirmAt = new HashMap<>();
    long flatDoneAt = -1;
    LogCapture logCap;

    CrashDayRig(Opts o, ReplayData d, File outRoot) {
        this.o = o;
        this.d = d;
        this.out = new File(outRoot, o.name);
    }

    // ------------------------------------------------------------------ dong ho
    long t() {
        return now.get();
    }

    void setTime(long t) {
        long v = now.updateAndGet(x -> Math.max(x, t));
        if (fake != null) fake.now = v;
    }

    void advance(long ms) {
        long v = now.addAndGet(Math.max(0L, ms));
        if (fake != null) fake.now = v;
    }

    // ------------------------------------------------------------------ khoi tao
    void init() throws Exception {
        out.mkdirs();
        File run = new File(out, "run");
        deleteTree(run);
        run.mkdirs();
        logCap = LogCapture.attach();
        // [E2E_V12] KHONG gan EntryGate.GATE_DYN_SCALE / Configs.MIN_MOMENTUM_15M: gia tri = Configs/EntryGate nap tu env
        //   (ghi vao result.json "cfg_effective" de C1 doi chieu).
        // buffer gate: ban ghi live ts < START
        List<Long> ts0 = new ArrayList<>();
        List<Float> r0 = new ArrayList<>();
        for (int i = 0; i < d.bufTs.length; i++) {
            if (d.bufTs[i] < ReplayData.START) {
                ts0.add(d.bufTs[i]);
                r0.add(d.bufR[i]);
            }
        }
        long[] a = new long[ts0.size()];
        float[] b = new float[r0.size()];
        for (int i = 0; i < a.length; i++) {
            a[i] = ts0.get(i);
            b[i] = r0.get(i);
        }
        persist = new File(run, "gate_ratio_live.bin").getPath();
        Object[] g0 = E2eGateSupport.startProduction(persist, a, b);   // LiveGateRollingRatio.init() THAT (env)
        res.put("gate_ratio_on", g0[0]);
        res.put("gate_ratio_file_env", g0[1]);
        res.put("buffer_init_records", a.length);
        res.put("buffer_after_load", E2eGateSupport.size());
        if (!Boolean.TRUE.equals(g0[0])) throw new IllegalStateException("[E2E_V12] GATE-RATIO live TAT theo env => tu choi");
        gate = new AIRejectFilter();
        uni = new SymbolUniverseLive(SymbolUniverseLive.Config.fromEnv(Cfg::get).strictCoin()
                .withClassifier(TradFiClassifier.universeA1()), () -> d.exInfo, alerts::add);
        uni.apply(d.exInfo, t());
        lastUni = t();
        rules = new SymbolRules(d.exInfo, t());
        if (!o.exec) return;

        KillSwitchEngine.Params p = OpsConfig.killSwitchParams(true);
        p.latchFile = new File(run, "killsw_latch.json");
        p.resetFile = new File(run, "killsw_reset.req");
        p.c6OwnPeak = true;
        p.peakTag = (o.venue == Venue.DRY ? "dry" : "live") + "_c3eq";
        ks = new KillSwitchEngine(KillSwitchEngine.Mode.ACT, "act", new KillSwitchEngine.Sink() {
            public void info(String x) { ksLines.add(fmt(t()) + " " + x); }
            public void warn(String x) { ksLines.add(fmt(t()) + " " + x); }
        }, new File(run, "c3live_killsw_peak"), null, () -> Configs.U_MAX, t(), p);
        ks.setAlert(alerts::add);

        audit = new OrderAuditLog(OrderAuditLog.LIVE_TAG, journal::add);
        if (o.venue == Venue.FAKE) {
            fake = new FakeExchange1m();
            fake.exchangeInfo = d.exInfo;
            fake.now = t();
            fake.startEquity = new BigDecimal("200000");
            fake.expireDelayMs = o.expireDelayMs;
            fake.ackWithoutAvgPrice = o.ackNoAvg;
            fake.rejectWouldTrigger = true;   // nhu Binance -2021 (sua san gia 11-05 sau lan chay 1: thieu => stop nam tren gia)
            fake.tap = this::onTruthEvent;
            raw = fake;
        } else {
            dry = new DryGateway(() -> d.exInfo, refs::get, BigDecimal.valueOf(CAPITAL), audit, now::get, null,
                    DryGateway.DEFAULT_FEE_RATE);
            raw = dry;
        }
        // gia mo dau: open phut START
        applyPrices(ReplayData.START, 0, false);
        // LEGACY (F5) giu tu truoc START
        for (String s : o.legacy) {
            BigDecimal px = lastPxBd.get(s);
            if (px == null) throw new IllegalStateException("LEGACY " + s + " khong co gia");
            BigDecimal q = new BigDecimal("50").divide(px, 0, java.math.RoundingMode.DOWN).max(BigDecimal.ONE);
            fake.setPosition(s, q, px);
            legacyQty.put(s, q);
        }
        cnt = new CountingGateway(raw, now::get);
        boot();
    }

    void boot() {
        File run = new File(out, "run");
        // [r4p] = C3LiveRuntime: onOrderResult (bo dem 429 rieng duong dat lenh, Bug3)
        C3LiveOrderExecutor.ApiObserver api = new C3LiveOrderExecutor.ApiObserver() {
            @Override
            public void onApiResult(String x, boolean ok) {
                ks.onApiResult(t(), x, ok);
            }

            @Override
            public void onOrderResult(String x, boolean ok, boolean rl) {
                ks.onOrderResult(t(), x, ok, rl);
            }
        };
        book = new LiveBookC3(new File(run, "c3live_book.json"), 1.0);
        scope = new C3Scope(book, now::get, new File(run, "c3live_merged.txt"));
        sgw = new C3ScopedGateway(cnt, scope, now::get, ProductionRatePolicy.policy(Cfg::get));
        sgw.setBook(book);
        sgw.setGuardSleep(this::advance);
        FillPriceResolver pr = new FillPriceResolver(now::get, this::advance, api);
        C3LiveOrderExecutor.FillObserver fill = (s, isBuy, f, r) -> ks.onFill(t(), s, isBuy, f, r);
        acct = new FillAccounting(book, sgw, audit, fill, alerts::add, api, now::get, null);
        acct.setPriceResolver(pr);
        rec = new Reconciler(sgw, book, acct, () -> rules, alerts::add, api, now::get, Reconciler.DEFAULT_EQUITY_TOL,
                Reconciler.DEFAULT_MATCH_TO_RELEASE, null);
        rec.setQtyReconcile(true);
        acct.setUnknownPositionSink(rec::onUnknownPosition);
        ex = new C3LiveOrderExecutor(sgw, book, api, fill, now::get, this::advance, C3LiveOrderExecutor.DEFAULT_SAFE_RETRY_MS,
                C3LiveOrderExecutor.DEFAULT_MAX_ATTEMPTS, Runnable::run);
        ex.setPriceResolver(pr);
        ex.setCostRecovery(acct);   // [r4p] = C3LiveRuntime (Bug2: bu phi khi stream rot)
        eq = new C3MainEquity(sgw, book, scope, CAPITAL, new File(run, "c3live_equity_c3.json"),
                o.venue == Venue.DRY ? "dry" : "live", 60_000L, now::get, api, alerts::add);
        ks.attachEquitySource(eq);
        flat = new C3LiveFlattener(sgw, book, ks::requiredAction, alerts::add, api, now::get, 5, 10_000L,
                C3LiveOrderExecutor.DEFAULT_SAFE_RETRY_MS);
        mgr = TrailingStopManager.builder().gateway(sgw).book(book).rules(() -> rules).closer(flat::closeCluster)
                .defer((s, t0, n) -> false).armHook((s, t0, n) -> { }).action(ks::requiredAction).api(api)
                .alert(alerts::add).clock(now::get).safeRetryMs(C3LiveOrderExecutor.DEFAULT_SAFE_RETRY_MS)
                .sleeper(this::advance).stopMode(TrailingStopManager.StopMode.CLOSE_POSITION)
                .qtyModeFor(scope::isMerged)   // = C3LiveRuntime (sua harness 11-05: ban dau THIEU => F5 gia)
                .events((type, sym, n, v, det) -> onTrailEvent(type, sym, n, v, det)).build();
        guard = new OwnStopGuard(sgw, book, api, alerts::add, () -> rec::onUnknownPosition, now::get);
        rec.setStopGuard(guard);
        acct.setStopGuard(guard);
        flat.setStopGuard(guard);
        mgr.setStopGuard(guard);
        final OwnStopGuard g = guard;
        final Reconciler r0 = rec;
        scope.setExtraRelated(() -> {
            Set<String> s = new HashSet<>(r0.watchedSymbols());
            s.addAll(g.keptSymbols());
            return s;
        });
        merged = new C3MergedGuard(scope, sgw, book, alerts::add, audit, now::get);
        merged.setTrailing(mgr);
        merged.setActExecutor(Runnable::run);
        sgw.setSuspectSink(merged::suspect);
        protector = new C3StopProtector(book, mgr, flat::closeCluster, scope::isMerged, alerts::add, now::get);
        protector.setMergedCloseCheck(merged::exchangeCoversC3);
        rec.setMergedPredicate(scope::isMerged);
        rec.setLostForeignSink(merged::onLostForeign);
        rec.setExitRecovery(merged::recoverC3Exit);
        merged.setExitBooker(acct::bookRecoveredExit);
        stream = new C3StreamScope(scope, book, now::get);
        stream.setGateway(sgw);
        stream.setSleeper(this::advance);
        stream.setForeignFillSink(merged::onForeignFill);
        stream.setSuspectSink(merged::suspect);
        stream.setStopTerminalSink(protector::onStopTerminal);
        refresher = new C3LegacyRefresher(sgw, scope, merged, api, alerts::add, now::get);
        final C3StreamScope ss = stream;
        final FillAccounting a0 = acct;
        java.util.function.Consumer<String> direct = txt -> {
            String f = ss.filter(txt);
            if (f != null) a0.dispatch(UserStreamEvents.parse(f));
        };
        if (o.wsDownFrom >= 0) {
            us = new UserStream(sgw, (url, l) -> {
                if (wsUp) {
                    wsListener = l;
                    l.onOpen();
                } else {
                    l.onClosed("e2e: mat ket noi (gia lap F1)");
                }
                return () -> {
                    if (wsListener == l) wsListener = null;
                };
            }, UserStream.parseUrls("wss://e2e/{key}"), acct, () -> {
                ex.resolveUnresolved(false);
                rec.checkPositions();
            }, alerts::add, api, now::get, 15_000L, 10_000L, 60_000L, 300_000L);
            java.util.function.Consumer<String> viaWs = txt -> {
                UserStream.Listener l = wsListener;
                if (!wsUp || l == null) return;
                String f = ss.filter(txt);
                if (f != null) l.onText(f);
            };
            setDownstream(viaWs);
        } else {
            setDownstream(direct);
        }
        uni.apply(d.exInfo, t());
        AccountModeGuard mg = new AccountModeGuard(sgw, alerts::add).globalPolicy(false, false);
        GatePreFilter.setC3OwnedSourceForTest(book::ownedSymbols);
        entry = C3LiveEntry.builder().book(book)
                .killSwitch(new C3LiveEntry.KillSwitchView() {
                    public boolean armed() { return true; }
                    public boolean allowNewEntry(String s) { return ks.allowNewEntry(s); }
                    public boolean allowDca(String s) { return ks.allowDca(s); }
                })
                .universe(uni).modeGuard(mg).rules(() -> rules).capital(eq::capital)
                // [E2E_V12] = C3LiveRuntime.buildEntry:417-427 (dong-cho-dong). legacy = LegacySymbols.blocksC3 (env
                //   C3_EXCLUDE_LEGACY_HELD) || scope; F5 cu giu them o.legacy. dcaGridEnabled = LiveDcaGridC3.active() (env
                //   LIVE_DCA_GRID_ENABLED); legBudgetFn = LiveGridSizing::legBudget (APPLY doc env LIVE_APPLY_GRID_RATIO).
                //   pushAllowed: adapter=dry => () -> true (nhu production nhanh dry).
                .legacy(s -> LegacySymbols.blocksC3(s) || o.legacy.contains(s) || scope.entryBlocked(s, t()))
                .budgetFn((m, c) -> TradeUtils.managerBudget(null, m, c, null))
                .legBudgetFn(LiveGridSizing::legBudget)
                .gridDue((f, px, n) -> DcaUtils.shouldDcaGrid(f, px, n)).executor(ex).audit(audit)
                .refSink((s, px) -> refs.put(s, BigDecimal.valueOf(px))).pushAllowed(() -> true)
                .dcaGridEnabled(LiveDcaGridC3.active())
                .sizeCapOfEquity(LiveProfileC3.SIZE_CAP_OF_EQUITY).reconAllows(rec::allowsEntry).build();
        mg.checkGlobal();
        ex.resolveUnresolved(true);
        if (!refresher.refreshNow()) errors.add("refreshNow LEGACY loi luc khoi dong");
        Reconciler.Report r = rec.startup();
        if (!r.ok) errors.add("reconcile khoi dong LOI");
        lastHourly = t();
    }

    void setDownstream(java.util.function.Consumer<String> c) {
        if (fake != null) {
            fake.downstream = c;
        } else {
            dry.setEventSink(txt -> {
                onTruthEvent(txt);
                c.accept(txt);
            });
        }
    }

    // ------------------------------------------------------------------ vong chinh
    void run() throws Exception {
        init();
        for (long tm = ReplayData.START; tm < o.end; tm += MIN) {
            setTime(tm);
            if (o.sDcaAt >= 0 && !sdca0 && tm >= o.sDcaAt && o.exec) chooseSdca(tm);
            applyPrices(tm, 0, true);
            if (o.exec) ops();
            setTime(tm + OPS_MS);
            if (o.exec) ops();
            setTime(tm + 6_000L);
            long b = tm - MIN;
            boolean stall = o.c1From >= 0 && b >= o.c1From && b < o.c1To;
            if (b >= ReplayData.START && !stall) decide(b);
            // [ERRATA3 E11] ops moi 5 s (+10..+55 s); moc gia dau vao doi o +15/+30/+45 s (truoc ops cung thoi diem)
            for (long off = 2 * OPS_MS; off < MIN; off += OPS_MS) {
                setTime(tm + off);
                if (off % PX_MS == 0) applyPrices(tm, (int) (off / PX_MS), true);
                if (o.exec) ops();
            }
        }
        if (o.exec) {   // lang 3 phut sau END (gia dung yen) de leg/stop/flatten don xong
            for (int i = 0; i < 36; i++) {
                setTime(t() + OPS_MS);
                ops();
            }
        }
        finish();
    }

    /** Moc gia DAU VAO k (0..3, +15k s) cua nen phut tm: O, cuc 1, cuc 2, C (nen giam: O,H,L,C; nen tang: O,L,H,C).
     *  [ERRATA3 E11] day la do phan giai dau vao (nen 1m), nhip exit = 10 s (EXIT_MS) doc gia moc gan nhat. */
    void applyPrices(long tm, int k, boolean trigger) {
        Map<String, Float> m = new HashMap<>();
        for (String s0 : d.bars.keySet()) {
            ReplayData.Bar br = d.bar(s0, tm);   // [S-TS] sau END: gia phang neu flatExt
            if (br == null) continue;
            int i;
            boolean down = br.c < br.o;
            switch (k) {
                case 0: i = 0; break;
                case 1: i = down ? 1 : 2; break;
                case 2: i = down ? 2 : 1; break;
                default: i = 3;
            }
            BigDecimal px = br.bd(i);
            String s = s0;
            double fct = sdcaFactor(s, tm);
            if (fct != 1d) px = px.multiply(BigDecimal.valueOf(fct));   // S-DCA: gia ep (nhan he so pha)
            lastPxBd.put(s, px);
            lastPx.put(s, px.floatValue());
            m.put(s, px.floatValue());
            if (fake != null && trigger) {
                fake.tickPrice(s, px);
            } else if (fake != null) {
                fake.setPrice(s, px);
            }
        }
        if (dry != null && trigger && !m.isEmpty()) dry.onPrices(m);
        if (fake != null) fake.deliverDue(t());
    }

    void ops() {
        long n = t();
        try {
            injectScheduled(n);
            if (n - lastUni >= 15 * MIN) {
                uni.apply(d.exInfo, n);
                lastUni = n;
            }
            if (us != null) {
                boolean down = n >= o.wsDownFrom && n < o.wsDownTo;
                if (down && wsUp) {
                    wsUp = false;
                    UserStream.Listener l = wsListener;
                    wsListener = null;
                    if (l != null) l.onClosed("e2e: rot ket noi (F1)");
                    event("WS_DOWN", "-", "");
                } else if (!down && !wsUp) {
                    wsUp = true;
                    event("WS_UP_ALLOWED", "-", "");
                }
                us.tick(n);
            }
            if (n - lastResolve >= 30_000L) {
                ex.resolveUnresolved(false);
                ex.correctProvisional();
                lastResolve = n;
            }
            ex.tickCosts(n);   // [r4p] = C3LiveRuntime vong ops
            flat.step();
            refresher.tick();
            merged.poll();
            everMerged.addAll(scope.merged().keySet());
            protector.check();
            eq.pollFunding(n);
            rec.confirmPendingFlat();
            Map<String, Float> px = new HashMap<>();
            for (String s : book.ownedSymbols()) {
                Float v = lastPx.get(s);
                if (v != null) px.put(s, v);
            }
            if (n - lastExit >= EXIT_MS) {   // [ERRATA3 E11] = C3LiveRuntime:511 exitTick moi EXIT_EVERY_MS 10 s
                lastExit = n;
                try (RateGuard.Urgent u = RateGuard.urgent(t() + C3StopProtector.DEADLINE_MS)) {
                    mgr.step(px);
                }
            }
            if (n - lastHourly >= H) {
                rec.hourly();
                lastHourly = n;
                checkQtyParity("hourly", false);
            }
            if (n - lastBook >= 15_000L) {
                Double e = eq.c3Equity();
                if (e != null) ks.onPaper(t(), book.openCount(), (float) book.marginUsed(), e.floatValue());
                lastBook = n;
            }
            if (n - lastPeriodic >= MIN) {
                ks.periodic(t());
                lastPeriodic = n;
            }
            if (fake != null) fake.deliverDue(t());
        } catch (Throwable e) {
            errors.add(fmt(n) + " ops: " + e);
            LOG.error("[E2E] loi ops {}: {}", fmt(n), e.toString());
        }
        latchWatch();
        checks();
    }

    void injectScheduled(long n) {
        if (o.rlAt >= 0 && !rlArmed && n >= o.rlAt && fake != null) {
            rlArmed = true;
            rlOrdersLeft = o.rlOrders;
            rlStopsLeft = o.rlStops;
            for (int i = 0; i < o.rlOrders; i++) fake.failNext("newMarketOrder", rl429());
            for (int i = 0; i < o.rlStops; i++) fake.failNext("newStopMarket", rl429());
            event("INJECT_429", "-", "orders=" + o.rlOrders + " stops=" + o.rlStops);
        }
        if (o.mergeSymbol != null && !merged0 && n >= o.mergeAt && fake != null) {
            merged0 = true;
            BigDecimal px = lastPxBd.get(o.mergeSymbol);
            BigDecimal q = new BigDecimal("50").divide(px, 0, java.math.RoundingMode.DOWN).max(BigDecimal.ONE);
            boolean c3Held = book.isHolding(o.mergeSymbol);
            fake.legacyOrder(o.mergeSymbol, Side.BUY, q, "legacy-e2e-merge-1");
            legacyQty.merge(o.mergeSymbol, q, BigDecimal::add);
            event("INJECT_MERGE", o.mergeSymbol, "qty=" + q.toPlainString() + " c3_dang_giu=" + c3Held);
        }
        if (o.ddAt >= 0 && !dd0 && n >= o.ddAt && fake != null) {
            String s = book.ownedSymbols().isEmpty() ? null : book.ownedSymbols().iterator().next();
            if (s != null) {
                dd0 = true;
                fake.incomes.add(new IncomeRecord(s, "FUNDING_FEE", BigDecimal.valueOf(-o.ddUsd), "USDT", n, "e2e-dd-1"));
                event("INJECT_DD", s, "FUNDING_FEE -" + o.ddUsd);
            }
        }
    }

    /**
     * [E2E_V12 S-DCA] Luat (khai truoc, REF ap cung luat tren so cua REF): tai phut tm dau tien &gt;= sDcaAt, chon toi da
     * sDcaN cum dang mo, da khop (confirmedQty &gt; 0), CHUA arm, legCount == 1, khong dang dong; sap theo (phut quyet dinh
     * leg dau, symbol). Tu nen tm: moi gia (O/H/L/C, ref, DCA due) cua symbol do nhan SDCA_FACTORS[pha] voi pha =
     * (t - tm) / 10'. Khong du cum => thu lai o phut sau.
     */
    void chooseSdca(long tm) {
        List<LiveBookC3.ClusterView> cand = new ArrayList<>();
        for (LiveBookC3.ClusterView c : book.clusters()) {
            if (c.confirmedQty.signum() > 0 && !c.trailArmed() && c.legCount == 1 && c.closeReason == null
                    && !c.hasUnresolved && firstLegBar.containsKey(c.symbol)) cand.add(c);
        }
        if (cand.size() < o.sDcaN) return;
        cand.sort((x, y) -> {
            int k = Long.compare(firstLegBar.get(x.symbol), firstLegBar.get(y.symbol));
            return k != 0 ? k : x.symbol.compareTo(y.symbol);
        });
        for (int i = 0; i < o.sDcaN; i++) {
            sdcaStart.put(cand.get(i).symbol, tm);
            event("INJECT_SDCA", cand.get(i).symbol, "pha " + Arrays.toString(SDCA_FACTORS) + " tu " + fmt(tm)
                    + " first=" + cand.get(i).firstEntryPrice);
        }
        sdca0 = true;
        sdcaSt = tm;
    }

    double sdcaFactor(String s, long barTs) {
        Long st = sdcaStart.get(s);
        if (st == null || barTs < st) return 1d;
        int ph = (int) Math.min(SDCA_FACTORS.length - 1, (barTs - st) / SDCA_PHASE_MS);
        return SDCA_FACTORS[ph];
    }

    /** [E2E_V12 F1] tap fin cua phut b = symbol co nen 1m CHOT trong Vision o phut b (fixture) — tru symbol bi tiem. */
    boolean finAllows(long b, String sym, String level, boolean predictPass) {
        boolean on = com.binance.chuyennd.aerospike.MinuteCompletenessGuard.enabled()
                && com.binance.chuyennd.aerospike.MinuteCompletenessGuard.finEnabled();
        if (!on) return com.binance.chuyennd.aerospike.MinuteCompletenessGuard.finAllows(null, sym);
        // tap fin day du = moi symbol co nen chot o phut b; finAllows chi hoi thanh vien cua sym => du dung {sym} khi co nen
        Set<String> fin = new HashSet<>();
        if (d.bar(sym, b) != null) fin.add(sym);
        if (o.finInjAt >= 0 && predictPass && !finInj0 && b >= o.finInjAt) {
            finInj0 = true;
            finInjSym = sym;
            finInjBar = b;
            event("INJECT_FIN", sym, "bo khoi tap fin phut " + fmt(b));
        }
        if (finInjBar == b && sym.equals(finInjSym)) fin.remove(sym);
        boolean ok = com.binance.chuyennd.aerospike.MinuteCompletenessGuard.finAllows(fin, sym);
        if (!ok) {
            nFinExcl++;
            // = dong log production DetectEntrySignal2TradeNormal:1352 (in boi harness, vong main khong chay)
            LOG.warn("[MINUTE-FIN-EXCL] chan leg {} {} (phut {} nen CHUA chot) | tong_chan_leg={} [harness]", level, sym, fmt(b),
                    nFinExcl);
            finRows.add(b + "," + sym + "," + level);
        }
        return ok;
    }

    static GatewayException rl429() {
        return new GatewayException(ErrorKind.RATE_LIMIT, 429, -1003, "Too many requests (e2e gia lap 429)", true, 0L, null);
    }

    // ------------------------------------------------------------------ tang quyet dinh
    void decide(long b) {
        long n = t();
        List<ReplayData.SelRow> rows = d.selAt(b);
        Map<String, List<KlineObjectSimple>> win = new HashMap<>();
        for (String s0 : d.bars.keySet()) {
            ReplayData.Bar br = d.bar(s0, b);
            if (br == null) continue;
            win.put(s0, Collections.singletonList(kline(b, br)));
        }
        if (o.exec) {
            ks.onTickStart(n);
            ks.onMarketData(n, win);
        }
        if (rows.isEmpty()) return;
        // [ERRATA1 E5] S-DCA tong hop dieu kien thi truong + p15 (moc sdcaSt = phut chon cum; offset tinh tren nen quyet dinh b)
        long off = sdcaSt >= 0 && b >= sdcaSt ? (b - sdcaSt) / MIN : -1;
        boolean dip = false;
        for (long x : SDCA_DIP_OFFS) if (off == x) dip = true;
        final float p15 = off == SDCA_P15_ZERO_OFF ? 0f : rows.get(0).p15;
        // [ERRATA1 N6] dieu kien thi truong cua phut = vong live DetectEntrySignal2TradeNormal:280-356 (ham production)
        long synthSt = off >= 0 && off < SDCA_MKT_WIN ? sdcaSt : -1L;
        MarketReplay.State mk = MarketReplay.at(d, b, (s, bb) -> o.a1 && a1Excluded(s, bb), this::sdcaFactor, dip, synthSt);
        if (mk == null) nMktNull++;
        else {
            if (mk.level != null) nMktBig++;
            if (mk.dcaAlt) nMktAlt++;
        }
        marketRows.add(b + "," + p15 + "," + (dip ? 1 : 0) + "," + (mk == null ? ",,,,,,," : mk.down + "," + mk.down15 + ","
                + mk.up + "," + (mk.level == null ? "" : mk.level.name()) + "," + (mk.level != null ? 1 : 0) + ","
                + (mk.dcaAlt ? 1 : 0) + "," + mk.n + "," + mk.n15));
        if (o.exec) {
            // [ERRATA1] thu tu = production (DetectEntrySignal2TradeNormal:433-516): BIG_DOWN -> DCA "level" -> DCA "dcaAlt" -> selector
            // 1. nhanh BIG_DOWN (shadow log)
            for (ReplayData.BigDownLeg bd : d.bigDown) {
                if (bd.ts != b) continue;
                if (o.a1 && a1Excluded(bd.symbol, b)) {
                    outcome(b, bd.symbol, "BIG_DOWN", "A1_EXCLUDED", "", "");
                    continue;
                }
                // [E2E_V12] = createOrderBuyRequest0 r4u (BIG_DOWN-GATE 11-10): profile c3 => bo gate p15, chi guard seed
                AIRejectFilter.FilterResult fr;
                if (com.binance.chuyennd.tradecore.selector.BigDownSelect.bypassGate(LiveProfileC3.on(),
                        com.binance.chuyennd.object.MarketLevelChange.BIG_DOWN)) {
                    String g0 = com.binance.chuyennd.tradecore.selector.BigDownSelect.bigDownGuard(
                            com.binance.chuyennd.ai_ml.onnx.entry.LiveGateRollingRatio.isSeedBlocked());
                    fr = g0 != null ? new AIRejectFilter.FilterResult(AIRejectFilter.FilterDecision.REJECT, g0)
                            : new AIRejectFilter.FilterResult(AIRejectFilter.FilterDecision.PASS, "BIG_DOWN bypass");
                } else {
                    fr = gate.entryGate(new AiPredictionData(b, p15, 0f), null, false, false);
                }
                if (fr.decision != AIRejectFilter.FilterDecision.PASS) {
                    outcome(b, bd.symbol, "BIG_DOWN", "GATE_REJECT", fr.reason, "");
                    continue;
                }
                if (!finAllows(b, bd.symbol, "BIG_DOWN", false)) {
                    outcome(b, bd.symbol, "BIG_DOWN", "FIN_EXCL", "", "");
                    continue;
                }
                leg(bd.symbol, "BIG_DOWN", false, b, null, -1);
            }
            // 2-3. DCA grid CHI o phut co dieu kien thi truong (N6): paperDcaGrid("level") neu BIG_DOWN, ("dcaAlt") neu isDcaAlt
            if (mk != null && mk.level != null) dcaPass(b, p15, "level");
            if (mk != null && mk.dcaAlt) dcaPass(b, p15, "dcaAlt");
        }
        // 4. selector PREDICT
        final Map<String, ReplayData.SelRow> bySym = new HashMap<>();
        TreeMap<Float, String> pool = new TreeMap<>();
        for (ReplayData.SelRow r : rows) {
            bySym.put(r.symbol, r);
            pool.put(r.key, r.symbol);
        }
        final Set<String> a1x = new HashSet<>(), heldX = new HashSet<>(), counted = new HashSet<>();
        final Map<String, Integer> rankOf = new HashMap<>();
        Predicate<String> a1 = s -> {
            boolean x = o.a1 && a1Excluded(s, b);
            if (x) a1x.add(s);
            return x;
        };
        Predicate<String> heldBase = heldPredicate(b);
        Predicate<String> held = s -> {
            boolean x = heldBase.test(s);
            if (x) heldX.add(s);
            return x;
        };
        Predicate<String> legacy = s -> o.legacy.contains(s) || LegacySymbols.blocksC3(s);
        final List<String[]> gatedRows = new ArrayList<>();
        GatePreFilter.runSelector(pool.entrySet(), TOPK, a1, legacy, held, s -> d.bar(s, b),
                (s, k) -> bySym.get(s).gv, new GatePreFilter.SelectorSink<ReplayData.Bar>() {
                    @Override
                    public void beforeCap(String symbol, int nextRank) {
                    }

                    @Override
                    public void counted(String symbol, Float key, Float sp, int rank) {
                        counted.add(symbol);
                        rankOf.put(symbol, rank);
                    }

                    @Override
                    public void gate(String symbol, ReplayData.Bar tk, Float sp) {
                        boolean full = o.exec && bookFull();
                        float q = E2eGateSupport.qPeek(b, p15, sp);
                        qByHour.putIfAbsent(b / H * H, q);
                        AIRejectFilter.FilterResult fr = gate.entryGate(new AiPredictionData(b, p15, 0f), sp, true, full);
                        boolean pass = fr.decision == AIRejectFilter.FilterDecision.PASS;
                        String outc = "-";
                        if (pass && o.exec) {
                            if (legacy.test(symbol)) {
                                outc = "SKIP_LEGACY_AFTER_GATE";
                            } else if (!finAllows(b, symbol, "PREDICT_SYMBOL_TRADE", true)) {
                                outc = "FIN_EXCL";   // = createOrderBuyRequest0:1349 (sau gate + LEGACY, truoc hook)
                                outcome(b, symbol, "PREDICT_SYMBOL_TRADE", "FIN_EXCL", "", "");
                            } else {
                                outc = leg(symbol, "PREDICT_SYMBOL_TRADE", false, b, sp, rankOf.get(symbol));
                            }
                        }
                        gatedRows.add(new String[]{symbol, full ? "1" : "0", Integer.toString(Float.floatToRawIntBits(q)),
                                pass ? "1" : "0", outc});
                    }
                });
        Map<String, String[]> g = new HashMap<>();
        for (String[] x : gatedRows) g.put(x[0], x);
        for (ReplayData.SelRow r : rows) {
            String[] x = g.get(r.symbol);
            float fac = Math.max(EntryGate.DYN_MIN, (r.gv / EntryGate.SCORE_BASE) * EntryGate.DYN_MULT);
            float rr = p15 / (fac * EntryGate.GATE_DYN_SCALE);
            traceRows.add(b + "," + r.symbol + "," + Float.floatToRawIntBits(r.key) + "," + r.rank + ","
                    + (rankOf.containsKey(r.symbol) ? rankOf.get(r.symbol) : -1) + "," + (a1x.contains(r.symbol) ? 1 : 0) + ","
                    + (o.legacy.contains(r.symbol) ? 1 : 0) + "," + (heldX.contains(r.symbol) ? 1 : 0) + ","
                    + (x != null ? 1 : 0) + "," + (x != null ? x[1] : "0") + "," + Float.floatToRawIntBits(rr) + ","
                    + Float.floatToRawIntBits(r.gv) + "," + Float.floatToRawIntBits(p15) + "," + (x != null ? x[2] : "")
                    + "," + (x != null ? x[3] : "0") + "," + (x != null ? x[4] : "-"));
        }
        if (!o.exec) return;
        if (fake != null) fake.deliverDue(t());
        latchWatch();
    }

    /** DCA grid (= C3LiveHook.dcaDue tren so that), 1 nhanh (level / dcaAlt) - cong p15 phang MIN_MOMENTUM_15M (sp null). */
    void dcaPass(long b, float p15, String tag) {
        curDcaTag = tag;
        for (LiveDcaGridC3.GridState gs : book.gridStates()) {
            ReplayData.Bar br = d.bar(gs.symbol, b);
            if (br == null) continue;
            float close = (float) (br.c * sdcaFactor(gs.symbol, b));
            if (!DcaUtils.shouldDcaGrid(gs.firstEntryPrice, close, gs.legCount)) continue;
            nDcaDue++;
            AIRejectFilter.FilterResult fr = gate.entryGate(new AiPredictionData(b, p15, 0f), null, false, false);
            if (fr.decision != AIRejectFilter.FilterDecision.PASS) {
                outcome(b, gs.symbol, "DCA_LEVEL1", "GATE_REJECT", fr.reason + " tag=" + tag, "");
                continue;
            }
            if (!finAllows(b, gs.symbol, "DCA_LEVEL1", false)) {
                outcome(b, gs.symbol, "DCA_LEVEL1", "FIN_EXCL", "tag=" + tag, "");
                continue;
            }
            String oc = leg(gs.symbol, "DCA_LEVEL1", true, b, null, -1);
            if ("SUBMITTED".equals(oc)) nDcaSubmitted++;
        }
        curDcaTag = "";
    }

    /** [ERRATA1 N4] E (equity c3) ma C3MainEquity.capital() vua dung (cache ttl) + thoi diem tinh - doc field (test, chi doc). */
    double[] eqSnap() {
        try {
            java.lang.reflect.Field a = C3MainEquity.class.getDeclaredField("eqCached");
            java.lang.reflect.Field at = C3MainEquity.class.getDeclaredField("eqAtMs");
            a.setAccessible(true);
            at.setAccessible(true);
            Object v = a.get(eq);
            return new double[]{v == null ? Double.NaN : ((Number) v).doubleValue(), ((Number) at.get(eq)).doubleValue()};
        } catch (Exception e) {
            return new double[]{Double.NaN, -1d};
        }
    }

    Predicate<String> heldPredicate(long b) {
        switch (o.held) {
            case NONE_V11:
                return s -> false;
            case SHADOW_R4H: {
                long b0 = 1_793_305_800_000L, w1 = 1_793_332_800_000L;   // 10-30 03:30 .. 11:00 +07
                return s -> b >= b0 && b < w1 && d.shadowHeld(s, b);
            }
            default:
                return GatePreFilter.heldPredicate(GatePreFilter.HeldSource.C3_LIVE_BOOK, null);
        }
    }

    boolean a1Excluded(String s, long b) {
        Optional<TradFiClassifier.Verdict> v = uni.classification(s);
        if (!v.isPresent()) return b > d.exInfo.getServerTime();   // fail-closed nhu UniverseA1Filter.excludedIn
        // [4q] = UniverseA1Filter production: loai TRADFI + INDEX + PREMARKET (PREMARKET-b). Ban dau chi TradFi.
        com.binance.chuyennd.c3live.api.SymbolMeta m = d.exInfo.getSymbols().get(s);
        return v.get().isTradFi() || (m != null && com.binance.chuyennd.tradecore.selector.UniverseA1Classifier.excluded(
                com.binance.chuyennd.tradecore.selector.UniverseA1Classifier.classify(m.getContractType(), m.getUnderlyingType())));
    }

    boolean bookFull() {
        Double cap = eq.capital();
        if (cap == null || !(cap > 0d)) return false;
        return TradeUtils.managerBudget(null, (float) book.marginUsed(), cap.floatValue(), null) == null;
    }

    String leg(String sym, String level, boolean dca, long b, Float sp, Integer rank) {
        ReplayData.Bar br = d.bar(sym, b);
        Float cur = lastPx.get(sym);
        if (br == null || cur == null) {
            outcome(b, sym, level, "NO_BAR", "", "");
            return "NO_BAR";
        }
        // ref = close nen quyet dinh (C3LiveHook.onLeg) x he so S-DCA
        double fct = sdcaFactor(sym, b);
        double ref = fct == 1d ? (double) br.c : (double) br.c * fct;
        boolean hadCluster = book.cluster(sym).isPresent();
        // sizing = gia nhip hien tai (~ price_realtime tuoi = open nen b+1 x he so S-DCA); tierMul = 1, tier3 = false (gioi han)
        C3LiveEntry.Result r = entry.onLeg(new C3LiveEntry.LegInput(sym, level, dca, b, ref, cur.doubleValue(), 1f, false, sp,
                rank == null ? -1 : rank), t());
        double[] es = eqSnap();
        if (r.outcome == C3LiveEntry.Outcome.SUBMITTED) {
            submittedCids.add(r.cid);
            submitTime.put(r.cid, t());
            cidSym.put(r.cid, sym);
            if (!hadCluster) firstLegBar.put(sym, b);
        }
        outcome(b, sym, level, r.outcome.name(), r.detail, r.cid == null ? "" : r.cid);
        legRows.add(b + "," + t() + "," + sym + "," + level + "," + r.outcome.name() + "," + (r.cid == null ? "" : r.cid) + ","
                + (r.qty == null ? "" : r.qty.toPlainString()) + "," + (Double.isNaN(r.budget) ? "" : Double.toString(r.budget))
                + "," + (Double.isNaN(r.marginBefore) ? "" : Double.toString(r.marginBefore)) + ","
                + (Double.isNaN(r.capital) ? "" : Double.toString(r.capital)) + "," + ref + "," + cur + "," + legIdxOf(r.detail) + ","
                + (rules.tickSize(sym) == null ? "" : rules.tickSize(sym).toPlainString()) + ","
                + (r.detail == null ? "" : r.detail.replace(',', ';')) + "," + (Double.isNaN(es[0]) ? "" : Double.toString(es[0]))
                + "," + (long) es[1] + "," + (dca ? curDcaTag : ""));
        if (fake != null) fake.drain();
        return r.outcome.name();
    }

    final List<String> legRows = new ArrayList<>();

    static String legIdxOf(String detail) {
        if (detail == null) return "";
        int i = detail.indexOf("legIdx=");
        if (i < 0) return "";
        int j = i + 7, k = j;
        while (k < detail.length() && (Character.isDigit(detail.charAt(k)) || detail.charAt(k) == '-')) k++;
        return detail.substring(j, k);
    }

    static KlineObjectSimple kline(long b, ReplayData.Bar br) {
        KlineObjectSimple k = new KlineObjectSimple();
        k.startTime = b;
        k.priceOpen = br.o;
        k.maxPrice = br.h;
        k.minPrice = br.l;
        k.priceClose = br.c;
        return k;
    }

    // ------------------------------------------------------------------ su kien / kiem
    void onTruthEvent(String txt) {
        try {
            JsonObject j = JsonParser.parseString(txt).getAsJsonObject();
            if (!"ORDER_TRADE_UPDATE".equals(j.get("e").getAsString())) return;
            JsonObject x = j.getAsJsonObject("o");
            if (!"TRADE".equals(x.get("x").getAsString())) return;
            String cid = x.get("c").getAsString();
            if (!C3Scope.isC3Cid(cid)) return;
            String s = x.get("s").getAsString();
            double[] a = truth.computeIfAbsent(s, k -> new double[2]);
            a[0] += x.has("rp") ? x.get("rp").getAsDouble() : 0d;
            a[1] += x.has("n") ? x.get("n").getAsDouble() : 0d;
            double lq = x.get("l").getAsDouble(), lp = x.get("L").getAsDouble();
            fillRows.add(t() + "," + s + "," + x.get("S").getAsString() + "," + x.get("l").getAsString() + ","
                    + x.get("L").getAsString() + "," + cid + "," + (x.has("rp") ? x.get("rp").getAsString() : "") + ","
                    + (x.has("n") ? x.get("n").getAsString() : ""));
            double[] v = c3Vwap.computeIfAbsent(s, k -> new double[3]);
            if ("BUY".equals(x.get("S").getAsString())) {
                v[0] += lq;
                v[1] += lq * lp;
            } else if (v[0] > 0d) {
                double avg = v[1] / v[0], qq = Math.min(lq, v[0]);
                v[2] += (lp - avg) * qq;
                v[1] -= avg * qq;
                v[0] -= qq;
                if (v[0] <= 1e-12) {
                    v[0] = 0d;
                    v[1] = 0d;
                }
            }
            if ("BUY".equals(x.get("S").getAsString()) && cid.startsWith("c3-")) buyCidCount.merge(cid, 1, Integer::sum);
        } catch (RuntimeException e) {
            errors.add("truth parse: " + e);
        }
    }

    void onTrailEvent(String type, String sym, long n, double v, String det) {
        eventRows.add(n + "," + fmt(n) + ",TRAIL_" + type + "," + sym + "," + v + "," + det.replace(',', ';'));
        if ("ARM".equals(type)) {
            nArm++;
            armedAt.put(sym, n);
            firstStopAt.remove(sym);
        }
    }

    void event(String type, String sym, String det) {
        eventRows.add(t() + "," + fmt(t()) + "," + type + "," + sym + ",," + det.replace(',', ';'));
    }

    void outcome(long b, String sym, String level, String oc, String det, String cid) {
        outcomeRows.add(b + "," + fmt(b) + "," + t() + "," + sym + "," + level + "," + oc + "," + cid + ","
                + (det == null ? "" : det.replace(',', ';')));
    }

    void latchWatch() {
        if (ks == null) return;
        Set<String> cur = new TreeSet<>(ks.latchCodes());
        if (!cur.equals(lastLatch)) {
            event("KS_LATCH", "-", cur + " action=" + ks.requiredAction());
            lastLatch = cur;
        }
        if (latchFlattenAt < 0 && ks.requiredAction() == KillSwitchEngine.Action.FLATTEN) latchFlattenAt = t();
    }

    void violation(String c, String msg) {
        List<String> l = viol.computeIfAbsent(c, k -> new ArrayList<>());
        if (l.size() < 50) l.add(fmt(t()) + " " + msg);
    }

    /** X3/X4/X5 moi nhip (doc san tho, khong dem weight). */
    void checks() {
        long n = t();
        Map<String, BigDecimal> pos = c3Positions();
        Map<String, List<OrderInfo>> stops = new HashMap<>();
        for (OrderInfo st : raw.openStops(null)) {
            if (st.getClientOrderId() != null && st.getClientOrderId().startsWith("c3s-")) {
                stops.computeIfAbsent(st.getSymbol(), k -> new ArrayList<>()).add(st);
            }
        }
        maxOpen = Math.max(maxOpen, book.openCount());
        for (String cid : submittedCids) {
            if (confirmAt.containsKey(cid)) continue;
            Optional<LiveBookC3.LegView> lv = book.leg(cid);
            if (!lv.isPresent() || !lv.get().state.unresolved()) confirmAt.put(cid, n);
        }
        if (latchFlattenAt >= 0 && flatDoneAt < 0 && book.openCount() == 0) flatDoneAt = n;
        for (LiveBookC3.ClusterView c : book.clusters()) {
            BigDecimal ex0 = pos.getOrDefault(c.symbol, BigDecimal.ZERO);
            List<OrderInfo> sl = stops.getOrDefault(c.symbol, Collections.<OrderInfo>emptyList());
            maxStopsSeen = Math.max(maxStopsSeen, sl.size());
            if (c.trailArmed() && ex0.signum() > 0 && c.closeReason == null) {
                if (sl.isEmpty()) {
                    Long since = gapSince.putIfAbsent(c.symbol, n);
                    if (since != null && n - since > GRACE_MS) violation("X3", c.symbol + " cum ARM khong co stop " + (n - since) / 1000 + "s");
                } else {
                    gapSince.remove(c.symbol);
                    firstStopAt.putIfAbsent(c.symbol, n);
                    if (sl.size() > 2) violation("X3", c.symbol + " " + sl.size() + " stop c3 mo");
                    for (OrderInfo st : sl) {
                        if (!st.isClosePosition() && !scope.isMerged(c.symbol)) violation("X3", c.symbol + " stop khong closePosition " + st.getClientOrderId());
                        Float cur = lastPx.get(c.symbol);
                        if (cur != null && st.getStopPrice() != null && st.getStopPrice().floatValue() > cur * 1.0000001f
                                && sl.size() == 1) {
                            // gia vuot xuong duoi stop ma chua kich: chi co the khi chua co nhip (khong ky vong) => ghi
                            violation("X3", c.symbol + " stopPrice " + st.getStopPrice() + " > gia " + cur);
                        }
                    }
                }
                double[] ls = lastStop.get(c.symbol);
                if (c.stopClientAlgoId != null && c.stopPrice > 0) {
                    if (ls != null && ls[1] == c.tsFirstLeg && ls[2] == c.legCount && c.stopPrice != ls[0]) {
                        nStopMoves++;
                        BigDecimal tick = rules.tickSize(c.symbol);
                        if (c.stopPrice < ls[0]) violation("X4", c.symbol + " stop giam " + ls[0] + " -> " + c.stopPrice);
                        else if ((tick != null && c.stopPrice - ls[0] < tick.doubleValue() - 1e-12) || c.stopPrice < ls[0] * 1.001 - 1e-12) {
                            violation("X4", c.symbol + " doi qua nho " + ls[0] + " -> " + c.stopPrice + " tick=" + tick);
                        }
                    }
                    lastStop.put(c.symbol, new double[]{c.stopPrice, c.tsFirstLeg, c.legCount});
                }
            } else {
                gapSince.remove(c.symbol);
            }
        }
        // X5: vi the c3 tren san <=> cum mo trong so; stop c3 chi o symbol co vi the
        Set<String> bookSyms = new HashSet<>();
        for (LiveBookC3.ClusterView c : book.clusters()) bookSyms.add(c.symbol);
        for (Map.Entry<String, BigDecimal> e : pos.entrySet()) {
            if (e.getValue().signum() == 0) continue;
            if (!bookSyms.contains(e.getKey())) {
                Long since = orphanPosSince.putIfAbsent(e.getKey(), n);
                if (since != null && n - since > GRACE_MS) violation("X5", e.getKey() + " vi the c3 tren san khong co cum " + e.getValue());
            } else {
                orphanPosSince.remove(e.getKey());
            }
        }
        orphanPosSince.keySet().removeIf(s -> pos.getOrDefault(s, BigDecimal.ZERO).signum() == 0 || bookSyms.contains(s));
        for (Map.Entry<String, List<OrderInfo>> e : stops.entrySet()) {
            if (pos.getOrDefault(e.getKey(), BigDecimal.ZERO).signum() <= 0) {
                Long since = orphanStopSince.putIfAbsent(e.getKey(), n);
                if (since != null && n - since > GRACE_MS) violation("X5", e.getKey() + " stop c3 mo tren symbol phang " + e.getValue().size());
            } else {
                orphanStopSince.remove(e.getKey());
            }
        }
        orphanStopSince.keySet().removeIf(s -> !stops.containsKey(s));
    }

    /** Vi the CUA c3 tren san = vi the tong - qty LEGACY. */
    Map<String, BigDecimal> c3Positions() {
        Map<String, BigDecimal> m = new HashMap<>();
        for (PositionInfo p : raw.positions()) {
            BigDecimal q = p.getPositionAmt().subtract(legacyQty.getOrDefault(p.getSymbol(), BigDecimal.ZERO));
            m.put(p.getSymbol(), q);
        }
        for (Map.Entry<String, BigDecimal> e : legacyQty.entrySet()) m.putIfAbsent(e.getKey(), e.getValue().negate());
        return m;
    }

    int checkQtyParity(String tag, boolean strict) {
        Map<String, BigDecimal> pos = c3Positions();
        int bad = 0;
        Set<String> syms = new TreeSet<>(pos.keySet());
        for (LiveBookC3.ClusterView c : book.clusters()) syms.add(c.symbol);
        for (String s : syms) {
            Optional<LiveBookC3.ClusterView> c = book.cluster(s);
            BigDecimal b = c.isPresent() ? c.get().confirmedQty : BigDecimal.ZERO;
            BigDecimal e = pos.getOrDefault(s, BigDecimal.ZERO);
            if (b.compareTo(e) != 0) {
                if (!strict && c.isPresent() && (c.get().hasUnresolved || c.get().closeReason != null)) continue;
                bad++;
                violation("X6", tag + " " + s + " so=" + b.toPlainString() + " san_c3=" + e.toPlainString());
            }
        }
        return bad;
    }

    // ------------------------------------------------------------------ ket thuc + tieu chi
    void finish() throws Exception {
        res.put("run", o.name);
        res.put("venue", o.venue.name());
        res.put("held_mode", o.held.name());
        res.put("a1", o.a1);
        res.put("window", fmt(ReplayData.START) + " .. " + fmt(o.end));
        Object[] all = E2eGateSupport.flushAndLoad(persist);
        long[] ats = (long[]) all[0];
        float[] ar = (float[]) all[1];
        List<long[]> appended = new ArrayList<>();
        for (int i = 0; i < ats.length; i++) if (ats[i] >= ReplayData.START) appended.add(new long[]{ats[i], Float.floatToRawIntBits(ar[i])});
        res.put("appended_r", appended.size());
        Map<String, Object> qh = new LinkedHashMap<>();
        for (Map.Entry<Long, Float> e : qByHour.entrySet()) qh.put(fmt(e.getKey()), String.format(Locale.ROOT, "%.11f", e.getValue()));
        res.put("q_by_hour", qh);
        writeGz(new File(out, "trace_dec.csv.gz"), "ts,symbol,key_bits,rank_dump,rank_counted,a1,legacy,held,gated,bookfull,r_bits,gv_bits,"
                + "p15_bits,q_bits,pass,outcome", traceRows);
        writeGz(new File(out, "appended.csv.gz"), "ts,r_bits", toRows(appended));
        if (o.held == HeldMode.NONE_V11 && !o.a1) e2a(appended);
        if (o.held == HeldMode.SHADOW_R4H) e2b();
        if (o.exec) execCriteria();
        res.put("rig_checks_e2e1105", crit);   // kiem lop thuc thi kieu E2E_REPLAY 11-05 (bao cao); tieu chi V12 cham bang check_v12.py
        res.put("violations", viol);
        res.put("errors", errors);
        res.put("log_errors", logCap == null ? "n/a" : logCap.errors());
        res.put("log_capture", logCap == null ? "KHONG gan duoc appender" : logCap.kind());
        writeText(new File(out, "outcomes.csv"), "decision_ts,decision_t7,submit_ms,symbol,level,outcome,cid,detail", outcomeRows);
        writeText(new File(out, "events.csv"), "ms,t7,type,symbol,value,detail", eventRows);
        writeText(new File(out, "legs.csv"), "decision_ts,submit_ms,symbol,level,outcome,cid,qty,budget,margin_before,capital,"
                + "ref_px,sizing_px,leg_idx,tick,detail,eq,eq_at,dca_tag", legRows);
        writeText(new File(out, "market.csv"), "b,p15,dip,down,down15,up,level,big,alt,n,n15", marketRows);
        Map<String, Object> mkr = new LinkedHashMap<>();
        mkr.put("minutes", marketRows.size());
        mkr.put("big", nMktBig);
        mkr.put("dcaAlt", nMktAlt);
        mkr.put("no_btc", nMktNull);
        mkr.put("dca_due", nDcaDue);
        mkr.put("dca_submitted", nDcaSubmitted);
        mkr.put("died_symbols_jar", new TreeSet<>(com.binance.client.constant.Constants.diedSymbol));
        mkr.put("mkt_symbols", d.mSym.length);
        res.put("market", mkr);
        writeText(new File(out, "fills.csv"), "ms,symbol,side,qty,price,cid,rp,fee", fillRows);
        writeText(new File(out, "fin_excl.csv"), "decision_ts,symbol,level", finRows);
        Map<String, Object> inj = new LinkedHashMap<>();
        inj.put("sdca_at", o.sDcaAt);
        inj.put("sdca_n", o.sDcaN);
        inj.put("sdca_factors", SDCA_FACTORS);
        inj.put("sdca_phase_ms", SDCA_PHASE_MS);
        inj.put("sdca_start", sdcaStart);
        inj.put("sdca_st", sdcaSt);
        inj.put("sdca_dip_offs_min", SDCA_DIP_OFFS);
        inj.put("sdca_dip", MarketReplay.DIP);
        inj.put("sdca_p15_zero_off_min", SDCA_P15_ZERO_OFF);
        inj.put("sdca_mkt_win_min", SDCA_MKT_WIN);
        inj.put("flat_ext", d.flatExt);
        inj.put("fin_inj_at", o.finInjAt);
        inj.put("fin_inj_symbol", finInjSym);
        inj.put("fin_inj_bar", finInjBar);
        inj.put("fin_excl_legs", nFinExcl);
        res.put("injections", inj);
        res.put("cfg_effective", cfgEffective());
        writeText(new File(out, "ks_lines.txt"), "", ksLines);
        writeText(new File(out, "alerts.txt"), "", alerts);
        writeText(new File(out, "journal.txt"), "", journal);
        Gson gs = new GsonBuilder().setPrettyPrinting().serializeSpecialFloatingPointValues().create();
        Files.write(new File(out, "result.json").toPath(), gs.toJson(res).getBytes(StandardCharsets.UTF_8));
        if (logCap != null) logCap.detach();
        GatePreFilter.setC3OwnedSourceForTest(null);
    }

    /** Gia tri HIEU LUC (doc tu class production da nap env) — C1 doi chieu voi env 242 + override. */
    static Map<String, Object> cfgEffective() {
        Map<String, Object> m = new LinkedHashMap<>();
        for (String f : new String[]{"F_BASE", "U_MAX", "DCA_GRID_SCALE", "DCA_GRID_WEIGHTS", "DCA_GRID_LEVELS", "FIX_B1", "FIX_B2",
                "FIX_B3", "RATE_PROFIT_STOP_MARKET", "TS_GIVEBACK_RATIO", "TS_MAX_GAP", "TS_MAX_GAP_WEAK", "LOSER_TIME_STOP_HOURS",
                "MIN_MOMENTUM_15M", "PRE_ARM_SL", "TS_PEAK_MODE", "SELECTOR_RANK_TOPK", "GATE_QUOTA_SKIP_WHEN_FULL",
                "MS_DOWN_BIG_AVG", "MS_DOWN_BIG_AVG_DCA", "NUMBER_TICKER_CAL_RATE_CHANGE", "BD_FRACTION"}) {
            try {
                Object v = Configs.class.getField(f).get(null);
                m.put("Configs." + f, v instanceof float[] ? Arrays.toString((float[]) v) : String.valueOf(v));
            } catch (Throwable e) {
                m.put("Configs." + f, "n/a");
            }
        }
        m.put("EntryGate.GATE_DYN_SCALE", EntryGate.GATE_DYN_SCALE);
        m.put("EntryGate.GATE_REGIME_ADAPTIVE", EntryGate.GATE_REGIME_ADAPTIVE);
        m.put("LiveGridSizing.on", LiveGridSizing.on());
        m.put("LiveDcaGridC3.active", LiveDcaGridC3.active());
        m.put("LiveProfileC3.SIZE_CAP_OF_EQUITY", LiveProfileC3.SIZE_CAP_OF_EQUITY);
        m.put("LiveProfileC3.on", LiveProfileC3.on());
        m.put("LegacySymbols.excludeLegacyHeld", LegacySymbols.excludeLegacyHeld());
        m.put("MinuteGuard.enabled", com.binance.chuyennd.aerospike.MinuteCompletenessGuard.enabled());
        m.put("MinuteGuard.finEnabled", com.binance.chuyennd.aerospike.MinuteCompletenessGuard.finEnabled());
        m.put("TsMktExt.enabled", com.binance.chuyennd.tradecore.selector.TsMktExt.enabled());
        m.put("C3TrailRate.armRate", com.binance.chuyennd.tradecore.selector.C3TrailRate.armRate());
        m.put("C3TrailRate.timeStopHours", com.binance.chuyennd.tradecore.selector.C3TrailRate.timeStopHours());
        List<Float> ratio = new ArrayList<>();
        for (int i = 0; i < 5; i++) ratio.add(DcaUtils.gridLegWeightRatio(i));
        m.put("DcaUtils.gridLegWeightRatio[0..4]", ratio);
        m.put("rig.TOPK", TOPK);
        m.put("rig.CAPITAL", CAPITAL);
        m.put("Cfg.asked", Cfg.asked());
        // [ERRATA1 E5] key code DA HOI nhung env luot KHONG dat (242 khong dat + khong override) => mac dinh trong code JAR
        TreeSet<String> unset = new TreeSet<>();
        for (String k : Cfg.asked()) if (System.getenv(k) == null) unset.add(k);
        m.put("Cfg.asked_khong_dat_env_(mac_dinh_JAR)", unset);
        return m;
    }

    void e2a(List<long[]> appended) {
        List<long[]> live = d.bufferBetween(ReplayData.START, o.end);
        Map<String, Integer> ms = new HashMap<>();
        for (long[] x : live) ms.merge(x[0] + "|" + x[1], 1, Integer::sum);
        int match = 0;
        List<String> onlyHarness = new ArrayList<>();
        for (long[] x : appended) {
            String k = x[0] + "|" + x[1];
            Integer c = ms.get(k);
            if (c != null && c > 0) {
                ms.put(k, c - 1);
                match++;
            } else if (onlyHarness.size() < 30) {
                onlyHarness.add(fmt(x[0]) + " r=" + Float.intBitsToFloat((int) x[1]));
            }
        }
        List<String> onlyLive = new ArrayList<>();
        int nOnlyLive = 0;
        for (Map.Entry<String, Integer> e : ms.entrySet()) {
            nOnlyLive += e.getValue();
            if (e.getValue() > 0 && onlyLive.size() < 30) {
                String[] p = e.getKey().split("\\|");
                onlyLive.add(fmt(Long.parseLong(p[0])) + " r=" + Float.intBitsToFloat((int) Long.parseLong(p[1])) + " x" + e.getValue());
            }
        }
        double frac = (double) match / Math.max(1, Math.max(live.size(), appended.size()));
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("live_records", live.size());
        m.put("harness_records", appended.size());
        m.put("match", match);
        m.put("match_frac", frac);
        m.put("only_harness_n", appended.size() - match);
        m.put("only_live_n", nOnlyLive);
        m.put("only_harness_sample", onlyHarness);
        m.put("only_live_sample", onlyLive);
        res.put("E2a", m);
        crit.put("E2a", frac >= 0.999);
    }

    void e2b() {
        long h4 = 1_793_307_600_000L, w1 = 1_793_332_800_000L;
        Float q04 = qByHour.get(h4);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("q04", q04 == null ? null : String.format(Locale.ROOT, "%.11f", q04));
        boolean qOk = q04 != null && Math.abs(q04 - 0.00756445155f) <= Math.abs(0.00756445155f) * 1e-9;
        int pass = 0, passHourly = 0;
        TreeSet<String> newSyms = new TreeSet<>(), newHourly = new TreeSet<>();
        for (String row : traceRows) {
            String[] a = row.split(",", -1);
            long ts = Long.parseLong(a[0]);
            if (ts < h4 || ts >= w1) continue;
            if (Integer.parseInt(a[3]) > 24) continue;
            float r = Float.intBitsToFloat(Integer.parseInt(a[10]));
            String sym = a[1];
            if (q04 != null && r >= q04) {
                pass++;
                if (!d.shadowHeld(sym, ts)) newSyms.add(sym.replace("USDT", ""));
            }
            if ("1".equals(a[14])) {
                passHourly++;
                if (!d.shadowHeld(sym, ts)) newHourly.add(sym.replace("USDT", ""));
            }
        }
        m.put("wave2_pass_q04_frozen", pass);
        m.put("wave2_new_q04_frozen", newSyms);
        m.put("wave2_pass_production_hourly_q", passHourly);
        m.put("wave2_new_production_hourly_q", newHourly);
        res.put("E2b", m);
        crit.put("E2b", qOk && newSyms.equals(new TreeSet<>(Arrays.asList("CAP", "CT", "DOS", "IDOL", "IRYS", "NIL", "PARTI", "Q"))));
    }

    void execCriteria() {
        // X1: outcome
        Map<String, Integer> oc = new TreeMap<>();
        Set<String> bad = new TreeSet<>(Arrays.asList("ERROR", "BAD_INPUT", "NO_RULES", "MODE_GUARD", "RESERVE_FAIL", "NO_EQUITY",
                "BOOK_UNHEALTHY", "RECON_BLOCKED", "NOT_BUYABLE", "NO_BAR"));
        int nBad = 0;
        for (String r : outcomeRows) {
            String x = r.split(",", -1)[5];
            oc.merge(x, 1, Integer::sum);
            if (bad.contains(x)) {
                nBad++;
                violation("X1", r);
            }
        }
        res.put("outcomes", oc);
        crit.put("X1", nBad == 0);
        // X2: khop mot lan + qty/gia so = san
        int x2 = 0;
        for (String cid : submittedCids) {
            Integer c = buyCidCount.get(cid);
            if (c != null && c > 1) {
                x2++;
                violation("X2", cid + " khop " + c + " lan");
            }
            Optional<LiveBookC3.LegView> lv = book.leg(cid);
            String sym = cidSym.get(cid);
            Optional<OrderInfo> oi = sym == null ? Optional.<OrderInfo>empty() : raw.queryOrder(sym, cid);
            if (!oi.isPresent()) continue;   // 429/huy: khong co lenh tren san
            OrderInfo od = oi.get();
            if (od.getExecutedQty() == null || od.getExecutedQty().signum() <= 0) continue;
            if (!lv.isPresent()) {
                // cum da dong & bi xoa khoi so: kiem qua ledger (khong co o day) — chi dem
                continue;
            }
            LiveBookC3.LegView l = lv.get();
            if (l.execQty == null || l.execQty.compareTo(od.getExecutedQty()) != 0) {
                x2++;
                violation("X2", cid + " qty so=" + l.execQty + " san=" + od.getExecutedQty());
            }
            if (od.getAvgPrice() != null && Math.abs(l.avgPx - od.getAvgPrice().doubleValue()) > od.getAvgPrice().doubleValue() * 1e-9) {
                x2++;
                violation("X2", cid + " gia so=" + l.avgPx + " san=" + od.getAvgPrice());
            }
        }
        for (LiveBookC3.LegView l : book.unresolvedLegs()) {
            x2++;
            violation("X2", "leg treo cuoi cua so " + l.cid + " " + l.state);
        }
        long maxLat = 0;
        for (String cid : submittedCids) {
            Long c = confirmAt.get(cid);
            if (c == null) continue;
            long lat = c - submitTime.get(cid);
            maxLat = Math.max(maxLat, lat);
            if (lat > 60_000L) {
                x2++;
                violation("X2", cid + " xac nhan so sau " + lat / 1000 + "s");
            }
        }
        res.put("max_confirm_latency_ms", maxLat);
        crit.put("X2", x2 == 0);
        // X3/X4/X5
        crit.put("X3", !viol.containsKey("X3"));
        crit.put("X4", !viol.containsKey("X4"));
        crit.put("X5", !viol.containsKey("X5"));
        // X6 doi soat
        int q = checkQtyParity("cuoi", true);
        // AccountView da cong don phi/realized luc khop (ke ca cum con mo) — KHONG cong them ClusterView (sua harness 11-05:
        // ban dau cong ca 2 => phi so bi dem 2 lan phi vao cua cum mo)
        double bookR = book.account().realized, bookF = book.account().commission;
        double openF = 0d;
        for (LiveBookC3.ClusterView c : book.clusters()) openF += c.commission;
        // [r4p Bug4] realized: LOAI rp san cua symbol MERGED (san tinh tren gia von gop LEGACY+c3); phan MERGED cua so = rp VWAP c3
        // tinh doc lap tu khop san => so sanh (so - rpC3 MERGED) voi Σrp san non-MERGED. Phi: giu nguyen moi symbol.
        double exR = 0, exF = 0, exRMergedBlend = 0, c3RMerged = 0;
        for (Map.Entry<String, double[]> e : truth.entrySet()) {
            exF += e.getValue()[1];
            if (everMerged.contains(e.getKey())) {
                exRMergedBlend += e.getValue()[0];
                double[] v = c3Vwap.get(e.getKey());
                c3RMerged += v == null ? 0d : v[2];
            } else {
                exR += e.getValue()[0];
            }
        }
        Map<String, Object> x6 = new LinkedHashMap<>();
        x6.put("qty_mismatch_end", q);
        x6.put("realized_book", bookR);
        x6.put("realized_exchange(non_merged)", exR);
        x6.put("merged_symbols", new ArrayList<>(everMerged));
        x6.put("realized_merged_c3_vwap", c3RMerged);
        x6.put("realized_merged_exchange_blended(bo qua)", exRMergedBlend);
        x6.put("fee_book", bookF);
        x6.put("fee_exchange", exF);
        x6.put("fee_open_clusters(da gom trong fee_book)", openF);
        Map<String, String> tr = new TreeMap<>();
        for (Map.Entry<String, double[]> e : truth.entrySet()) tr.put(e.getKey(), e.getValue()[0] + "/" + e.getValue()[1]);
        x6.put("truth_rp_fee_by_symbol", tr);
        x6.put("recon_status", rec.status());
        res.put("X6", x6);
        boolean rOk = Math.abs(bookR - c3RMerged - exR) <= 1e-6 * Math.max(1d, Math.abs(exR));
        boolean fOk = Math.abs(bookF - exF) <= 1e-6 * Math.max(1d, Math.abs(exF));
        if (!rOk) violation("X6", "realized so=" + bookR + " (-MERGED c3 " + c3RMerged + ") san(non-MERGED)=" + exR);
        if (!fOk) violation("X6", "phi so=" + bookF + " san=" + exF);
        crit.put("X6", q == 0 && rOk && fOk && !viol.containsKey("X6"));
        // X7
        int le = logCap == null ? -1 : logCap.errorCount();
        crit.put("X7", errors.isEmpty() && le == 0);
        // X8
        res.put("ks_final_latch", new TreeSet<>(ks.latchCodes()));
        res.put("ks_action_final", ks.requiredAction().name());
        boolean anyLatch = false;
        for (String e : eventRows) if (e.contains(",KS_LATCH,") && !e.contains("[] action")) anyLatch = true;
        boolean noFault = o.wsDownFrom < 0 && o.rlAt < 0 && !o.ackNoAvg && o.expireDelayMs == 0 && o.legacy.isEmpty()
                && o.ddAt < 0 && o.c1From < 0 && o.sDcaAt < 0;
        if (noFault) crit.put("X8", !anyLatch);
        res.put("ks_any_latch", anyLatch);
        // X9
        Map<String, Object> x9 = new LinkedHashMap<>();
        x9.put("max_weight_per_min", cnt.maxWeightPerMin());
        x9.put("max_weight_minute", fmt(cnt.maxWeightMinute()));
        x9.put("max_orders_10s", cnt.maxOrders10s());
        x9.put("by_method", cnt.byMethod);
        res.put("X9", x9);
        crit.put("X9", cnt.maxWeightPerMin() <= 600 && cnt.maxOrders10s() <= 150);
        // X10
        Map<String, Object> x10 = new LinkedHashMap<>();
        x10.put("dca_due", nDcaDue);
        x10.put("dca_submitted", nDcaSubmitted);
        res.put("X10", x10);
        Map<String, Object> st = new LinkedHashMap<>();
        st.put("submitted", submittedCids.size());
        st.put("arm_events", nArm);
        st.put("stop_moves", nStopMoves);
        st.put("max_open_clusters", maxOpen);
        st.put("max_c3_stops_one_symbol", maxStopsSeen);
        st.put("open_clusters_end", book.openCount());
        st.put("trail", mgr.stats());
        st.put("exec", ex.stats());
        st.put("fill", acct.stats());
        st.put("scope", scope.status());
        st.put("merged", merged.status());
        st.put("protector", protector.status());
        st.put("equity", eq.status());
        st.put("refused_calls", sgw.refusedCalls());
        st.put("latch_flatten_at", latchFlattenAt < 0 ? "-" : fmt(latchFlattenAt));
        st.put("expired_by_exchange", fake == null ? -1 : fake.expiredCount);
        st.put("legacy_qty", legacyQty.toString());
        res.put("stats", st);
    }

    static String symOfCid(String cid) {
        // c3-<SYMBOL>-<barMin>-<leg>
        String[] p = cid.split("-");
        return p.length >= 2 ? p[1] : null;
    }

    // ------------------------------------------------------------------ tien ich
    static final SimpleDateFormat F7 = new SimpleDateFormat("MM-dd HH:mm:ss");

    static {
        F7.setTimeZone(TimeZone.getTimeZone("GMT+7"));
    }

    static synchronized String fmt(long ms) {
        return F7.format(new Date(ms));
    }

    static List<String> toRows(List<long[]> l) {
        List<String> o = new ArrayList<>();
        for (long[] x : l) o.add(x[0] + "," + x[1]);
        return o;
    }

    static void writeGz(File f, String header, List<String> rows) throws Exception {
        try (Writer w = new OutputStreamWriter(new GZIPOutputStream(new FileOutputStream(f)), StandardCharsets.UTF_8)) {
            w.write(header);
            w.write('\n');
            for (String r : rows) {
                w.write(r);
                w.write('\n');
            }
        }
    }

    static void writeText(File f, String header, List<String> rows) throws Exception {
        try (Writer w = new OutputStreamWriter(new FileOutputStream(f), StandardCharsets.UTF_8)) {
            if (!header.isEmpty()) {
                w.write(header);
                w.write('\n');
            }
            for (String r : rows) {
                w.write(r);
                w.write('\n');
            }
        }
    }

    static void deleteTree(File f) {
        File[] c = f.listFiles();
        if (c != null) for (File x : c) deleteTree(x);
        f.delete();
    }
}
