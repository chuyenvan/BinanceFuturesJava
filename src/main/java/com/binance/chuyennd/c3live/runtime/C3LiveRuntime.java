package com.binance.chuyennd.c3live.runtime;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.c3live.adapter.DryGateway;
import com.binance.chuyennd.c3live.adapter.GatewayFactory;
import com.binance.chuyennd.c3live.alert.C3LiveAlerts;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.exit.TrailingStopManager;
import com.binance.chuyennd.c3live.fill.FillAccounting;
import com.binance.chuyennd.c3live.fill.UserStream;
import com.binance.chuyennd.c3live.fill.UserStreamEvents;
import com.binance.chuyennd.c3live.filters.SymbolRules;
import com.binance.chuyennd.c3live.guard.AccountModeGuard;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.rate.RateGuard;
import com.binance.chuyennd.c3live.recon.Reconciler;
import com.binance.chuyennd.c3live.risk.C3LiveEquity;
import com.binance.chuyennd.c3live.risk.C3LiveFlattener;
import com.binance.chuyennd.c3live.universe.SymbolUniverseLive;
import com.binance.chuyennd.c3live.universe.TradFiClassifier;
import com.binance.chuyennd.ops.OpsHooks;
import com.binance.chuyennd.tradecore.Cfg;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.DcaUtils;
import com.binance.chuyennd.tradecore.TradeUtils;
import com.binance.chuyennd.tradecore.selector.LegacySymbols;
import com.binance.chuyennd.tradecore.selector.LiveDcaGridC3;
import com.binance.chuyennd.tradecore.selector.LiveGridSizing;
import com.binance.chuyennd.tradecore.selector.LiveProfileC3;
import com.binance.chuyennd.tradecore.selector.MarketIndexFilter;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.math.BigDecimal;
import java.util.Collections;
import java.util.HashSet;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.function.Predicate;

/**
 * [V12 c3_live] Noi day production (chi tao khi {@code LIVE_PROFILE=c3_live} + {@code LIVE_ADAPTER=dry|live}):
 * gateway (Dry/C3LiveClient), LiveBookC3 (persist), equity (EquitySource cho A40), universe, AccountModeGuard,
 * SymbolRules (nap lai 6h), executor lenh (thread {@code C3LIVE-EXEC}), FLATTEN, Telegram (OpsHooks.setAlert), va
 * thread dinh ky {@code C3LIVE-OPS} (5 s): refresh universe/rules, giai quyet leg treo (30 s), FLATTEN, onBook (15 s).
 * [2b] + C6 {@link TrailingStopManager} (10 s, gia price_realtime nhu nhip exit so giay), C7 {@link UserStream} +
 * {@link FillAccounting} (live; dry => DryGateway phat su kien cung dang), C9 {@link Reconciler} (khoi dong + hang gio +
 * fallback REST khi mat stream). Tao loi (vd key sai) => null => c3_live TU CHOI push (WARN + Telegram), JVM chay tiep.
 */
public final class C3LiveRuntime {

    private static final Logger LOG = LoggerFactory.getLogger(C3LiveRuntime.class);
    private static final long OPS_PERIOD_MS = 5_000L;
    private static final long RESOLVE_EVERY_MS = 30_000L;
    private static final long BOOK_EVERY_MS = 15_000L;
    private static final long EXIT_EVERY_MS = 10_000L;
    private static final long RECON_EVERY_MS = 3_600_000L;
    private static final long STATS_EVERY_MS = 3_600_000L;
    public static final String KEY_STOP_MODE = "LIVE_C3_STOP_MODE";
    public static final String KEY_WS_URLS = "LIVE_C3_WS_URLS";
    public static final String KEY_REANCHOR_FILE = "LIVE_C3_REANCHOR_FILE";
    public static final String KEY_EQUITY_TOL = "LIVE_C3_EQUITY_TOL";

    private static volatile C3LiveRuntime INSTANCE;
    private static volatile boolean initTried;

    final GatewayFactory.Mode mode;
    final ExchangeGateway gw;
    final RateGuard rateGuard;
    final OrderAuditLog audit;
    final LiveBookC3 book;
    final C3LiveEquity equity;
    final SymbolUniverseLive universe;
    final AccountModeGuard modeGuard;
    final C3LiveOrderExecutor executor;
    final C3LiveEntry entry;
    final C3LiveFlattener flattener;
    final C3LiveAlerts alerts;
    final ConcurrentHashMap<String, BigDecimal> refs;
    final FillAccounting acct;
    final Reconciler reconciler;
    final TrailingStopManager trailing;
    final UserStream userStream;
    final File reanchorFile;
    private volatile SymbolRules rules;

    /** null = c3_live tat / tao loi (khong push). */
    public static C3LiveRuntime get() {
        C3LiveRuntime r = INSTANCE;
        if (r != null || initTried) return r;
        synchronized (C3LiveRuntime.class) {
            if (!initTried) {
                initTried = true;
                try {
                    INSTANCE = create();
                } catch (Throwable t) {
                    LOG.error("[C3-LIVE] KHONG khoi tao duoc runtime ({}) => TU CHOI push c3_live", t.toString());
                }
            }
            return INSTANCE;
        }
    }

    private static C3LiveRuntime create() {
        if (!LiveProfileC3.isLive()) return null;
        GatewayFactory.Mode mode = GatewayFactory.Mode.parse(Cfg.get(GatewayFactory.KEY_ADAPTER));
        if (mode == GatewayFactory.Mode.OFF) return null;
        C3LiveAlerts alerts = new C3LiveAlerts(Utils::sendSms2Telegram);
        OpsHooks.setAlert(alerts::send);
        double pilot = parseD(Cfg.get("LIVE_C3_PILOT_CAPITAL"), C3LiveEquity.DEFAULT_PILOT_CAPITAL);
        OrderAuditLog audit = mode == GatewayFactory.Mode.DRY ? OrderAuditLog.dry() : OrderAuditLog.live();
        ConcurrentHashMap<String, BigDecimal> refs = new ConcurrentHashMap<>();
        GatewayFactory.Result gr = GatewayFactory.create(mode, Cfg::get, refs::get,
                BigDecimal.valueOf(parseD(Cfg.get("LIVE_C3_DRY_EQUITY"), pilot)), System::currentTimeMillis, audit);
        if (gr.gateway == null) {
            String m = "[C3-LIVE] LIVE_ADAPTER=" + mode + " KHONG tao duoc gateway (" + gr.reason
                    + ") => TU CHOI push c3_live (JVM chay tiep, so giay van chay)";
            LOG.warn("{}", m);
            alerts.send(m);
            return null;
        }
        if (Math.abs(Configs.LEVERAGE_ORDER - 1f) > 1e-6) {
            LOG.warn("[C3-LIVE] Configs.LEVERAGE_ORDER={} != 1 — c3_live tinh margin = notional (CROSS 1x owner chot)",
                    Configs.LEVERAGE_ORDER);
        }
        C3LiveRuntime rt = new C3LiveRuntime(mode, gr.gateway, gr.rateGuard, audit, refs, alerts, pilot);
        rt.start();
        return rt;
    }

    private C3LiveRuntime(GatewayFactory.Mode mode, ExchangeGateway gw, RateGuard rateGuard, OrderAuditLog audit,
                          ConcurrentHashMap<String, BigDecimal> refsIn, C3LiveAlerts alerts, double pilot) {
        this.mode = mode;
        this.gw = gw;
        this.rateGuard = rateGuard;
        this.audit = audit;
        this.alerts = alerts;
        // refs dung CHUNG (cung object) voi DryGateway (gia ref close 1m)
        this.refs = refsIn;
        this.book = new LiveBookC3(new File(Cfg.getOr("LIVE_C3_BOOK_FILE", LiveBookC3.DEFAULT_FILE)), 1.0d);
        C3LiveOrderExecutor.ApiObserver api = OpsHooks::onApiResult;
        this.equity = new C3LiveEquity(gw, pilot, (long) parseD(Cfg.get("LIVE_C3_EQUITY_TTL_MS"), 60_000d),
                System::currentTimeMillis, api);
        OpsHooks.attachEquitySource(equity);
        this.universe = new SymbolUniverseLive(SymbolUniverseLive.Config.fromEnv(Cfg::get), gw::exchangeInfo, alerts::send);
        this.modeGuard = new AccountModeGuard(gw, alerts::send);
        long safe = (long) parseD(Cfg.get("LIVE_C3_RESEND_SAFE_MS"), C3LiveOrderExecutor.DEFAULT_SAFE_RETRY_MS);
        ExecutorService ex = Executors.newSingleThreadExecutor(r -> {
            Thread t = new Thread(r, "C3LIVE-EXEC");
            t.setDaemon(true);
            return t;
        });
        C3LiveOrderExecutor.FillObserver fillObs = (s, isBuy, f, ref) -> OpsHooks.onFill(s, isBuy, f, ref);
        this.executor = new C3LiveOrderExecutor(gw, book, api, fillObs, System::currentTimeMillis, Thread::sleep, safe,
                (int) parseD(Cfg.get("LIVE_C3_ORDER_MAX_ATTEMPTS"), C3LiveOrderExecutor.DEFAULT_MAX_ATTEMPTS), ex);
        // [2b C7/C9] ke toan fill + doi chieu
        this.acct = new FillAccounting(book, gw, audit, fillObs, alerts::send, api, System::currentTimeMillis,
                TrailingStopManager::tsExtOnClosed);
        this.reanchorFile = new File(Cfg.getOr(KEY_REANCHOR_FILE, Reconciler.DEFAULT_REANCHOR_FILE));
        this.reconciler = new Reconciler(gw, book, acct, () -> rules, alerts::send, api, System::currentTimeMillis,
                parseD(Cfg.get(KEY_EQUITY_TOL), Reconciler.DEFAULT_EQUITY_TOL), Reconciler.DEFAULT_MATCH_TO_RELEASE,
                reanchorFile);
        acct.setUnknownPositionSink(reconciler::onUnknownPosition);
        final boolean dry = mode == GatewayFactory.Mode.DRY;
        final Reconciler rec = reconciler;
        this.entry = C3LiveEntry.builder()
                .book(book)
                .killSwitch(new C3LiveEntry.KillSwitchView() {
                    public boolean armed() { return OpsHooks.killSwitchArmed(); }
                    public boolean allowNewEntry(String s) { return OpsHooks.allowNewEntry(s); }
                    public boolean allowDca(String s) { return OpsHooks.allowDca(s); }
                })
                .universe(universe)
                .modeGuard(modeGuard)
                .rules(() -> rules)
                .capital(equity::capital)
                .legacy(LegacySymbols::isLegacySymbol)
                .budgetFn((m, c) -> TradeUtils.managerBudget(null, m, c, null))
                .legBudgetFn(LiveGridSizing::legBudget)
                .gridDue((f, p, n) -> DcaUtils.shouldDcaGrid(f, p, n))
                .executor(executor)
                .audit(audit)
                .refSink((s, p) -> refs.put(s, BigDecimal.valueOf(p)))
                .pushAllowed(dry ? () -> true : () -> !LiveProfileC3.forceNoPush())
                .dcaGridEnabled(LiveDcaGridC3.active())
                .sizeCapOfEquity(LiveProfileC3.SIZE_CAP_OF_EQUITY)
                .reconAllows(rec::allowsEntry)
                .build();
        this.flattener = new C3LiveFlattener(gw, book, OpsHooks::requiredAction, alerts::send, api,
                System::currentTimeMillis, (int) parseD(Cfg.get("LIVE_C3_FLATTEN_MAX_ORDERS"), 5d),
                (long) parseD(Cfg.get("LIVE_C3_FLATTEN_WINDOW_MS"), 10_000d), safe);
        this.trailing = TrailingStopManager.builder()
                .gateway(gw)
                .book(book)
                .rules(() -> rules)
                .closer(flattener::closeCluster)
                .action(OpsHooks::requiredAction)
                .api(api)
                .alert(alerts::send)
                .safeRetryMs(safe)
                .stopMode("reduce_only_qty".equalsIgnoreCase(Cfg.getOr(KEY_STOP_MODE, "close_position").trim())
                        ? TrailingStopManager.StopMode.REDUCE_ONLY_QTY : TrailingStopManager.StopMode.CLOSE_POSITION)
                .build();
        if (dry && gw instanceof DryGateway) {
            ((DryGateway) gw).setEventSink(txt -> acct.dispatch(UserStreamEvents.parse(txt)));
            this.userStream = null;
        } else {
            this.userStream = new UserStream(gw, UserStream.okHttp((long) parseD(Cfg.get("LIVE_C3_WS_PING_MS"), 60_000d)),
                    UserStream.parseUrls(Cfg.getOr(KEY_WS_URLS, UserStream.DEFAULT_URLS)), acct, this::fallbackRest,
                    alerts::send, api, System::currentTimeMillis, 15_000L, 10_000L, 60_000L, 300_000L);
        }
        // ALT_EW (X14) cua c3_live tinh tren marketIndexMembers
        MarketIndexFilter.set(s -> {
            Set<String> m = marketIndexOrNull();
            return m == null || m.contains(s);
        });
    }

    private void start() {
        String m = "[C3-LIVE] khoi dong adapter=" + mode + " gateway=" + gw.name() + " book=" + book.file().getPath()
                + " cum=" + book.openCount() + " leg_treo=" + book.unresolvedLegs().size() + " pilot="
                + equity.pilotCapital() + " killSwitchArmed=" + OpsHooks.killSwitchArmed() + " X14=" + TrailingStopManager.tsExtEnabled()
                + " stream=" + (userStream == null ? "dry-events" : "ws");
        LOG.warn("{}", m);
        alerts.send(m);
        if (!OpsHooks.killSwitchArmed()) {
            alerts.send("[C3-LIVE] kill-switch KHONG o mode act => moi leg c3_live bi TU CHOI (dat LIVE_KILLSW_MODE=act)");
        }
        if (!TrailingStopManager.tsExtEnabled()) {
            LOG.warn("[C3-LIVE] TS_MKT_EXT (X14) TAT o c3_live (LIVE_TS_MKT_EXT!=1) => time-stop 168h KHONG gia han");
        }
        TrailingStopManager.startTsExtIfEnabled();
        if (userStream != null) userStream.start();
        Thread t = new Thread(this::opsLoop, "C3LIVE-OPS");
        t.setDaemon(true);
        t.start();
    }

    /** Fallback REST khi mat user stream (thread C3LIVE-STREAM). */
    private void fallbackRest() {
        executor.resolveUnresolved(false);
        reconciler.checkPositions();
    }

    private void opsLoop() {
        long lastResolve = Long.MIN_VALUE / 2, lastBook = Long.MIN_VALUE / 2, lastStats = System.currentTimeMillis();
        long lastExit = Long.MIN_VALUE / 2, lastRecon = System.currentTimeMillis();
        boolean first = true;
        while (true) {
            long now = System.currentTimeMillis();
            try {
                refreshRefData(now);
                if (first) {
                    first = false;
                    modeGuard.checkGlobal();
                    int left = executor.resolveUnresolved(true);
                    LOG.warn("[C3-LIVE] khoi phuc sau restart: con {} leg treo", left);
                    Reconciler.Report r = reconciler.startup();
                    LOG.warn("[C3-LIVE] reconcile khoi dong {}", r.ok ? "XONG" : "LOI (chan mo moi)");
                    if (r.ok) reconciler.hourly();   // dat moc equity / doi chieu ngay
                    lastResolve = now;
                    lastRecon = now;
                } else if (now - lastResolve >= RESOLVE_EVERY_MS) {
                    executor.resolveUnresolved(false);
                    lastResolve = now;
                    if (reconciler.blocks().containsKey(Reconciler.BLOCK_STARTUP)) {   // lan dau loi doc san => thu lai
                        Reconciler.Report r2 = reconciler.startup();
                        if (r2.ok) reconciler.hourly();
                    }
                }
                flattener.step();
                if (now - lastExit >= EXIT_EVERY_MS) {
                    lastExit = now;
                    exitTick();
                }
                if (now - lastRecon >= RECON_EVERY_MS || reanchorFile.exists()) {
                    lastRecon = now;
                    reconciler.hourly();   // file yeu cau dat lai moc (owner) => chay ngay
                }
                if (now - lastBook >= BOOK_EVERY_MS) {
                    Double tmb = equity.totalMarginBalance();
                    if (tmb != null) OpsHooks.onBook(book.openCount(), (float) book.marginUsed(), tmb.floatValue());
                    lastBook = now;
                }
                if (now - lastStats >= STATS_EVERY_MS) {
                    LOG.info("[C3-LIVE] HOURLY cum={} margin={} pending={} exec[{}] entry{} trail[{}] fill[{}] stream[{}] recon[{}]",
                            book.openCount(), String.format("%.2f", book.marginUsed()), String.format("%.2f", book.pendingMargin()),
                            executor.stats(), entry.counts(), trailing.stats(), acct.stats(),
                            userStream == null ? "dry" : userStream.stats(), reconciler.status());
                    lastStats = now;
                }
            } catch (Throwable e) {
                LOG.error("[C3-LIVE] loi vong ops: {}", e.toString());
            }
            try {
                Thread.sleep(OPS_PERIOD_MS);
            } catch (InterruptedException ie) {
                return;
            }
        }
    }

    /** Nhip exit: gia price_realtime cua cum dang giu (cung nguon nhip exit so giay); dry => kich stop gia lap truoc. */
    private void exitTick() {
        Set<String> syms = book.ownedSymbols();
        if (syms.isEmpty()) return;
        Map<String, Float> px;
        try {
            px = DataManagerAerospikeFloatSim.getAllPriceRealtimeLegacy(new HashSet<>(syms));
        } catch (Throwable e) {
            LOG.warn("[C3-LIVE] khong doc duoc gia realtime ({}) => nhip exit khong gia (stop san van con)", e.toString());
            px = Collections.emptyMap();
        }
        if (gw instanceof DryGateway && px != null) ((DryGateway) gw).onPrices(px);
        trailing.step(px);
    }

    private void refreshRefData(long now) {
        try {
            universe.refreshIfDue(now);
        } catch (Throwable e) {
            LOG.warn("[C3-LIVE] refresh universe loi: {}", e.toString());
        }
        try {
            SymbolRules r = rules;
            if (r == null) {
                ExchangeInfo ei = gw.exchangeInfo();
                if (ei != null) {
                    rules = new SymbolRules(ei, now);
                    if (rateGuard != null) rateGuard.updateLimits(RateGuard.Limits.fromExchangeInfo(ei));
                    LOG.info("[C3-LIVE] nap SymbolRules {} symbol", ei.getSymbols().size());
                }
            } else {
                r.refreshIfDue(now, gw::exchangeInfo);
            }
        } catch (Throwable e) {
            LOG.warn("[C3-LIVE] nap exchangeInfo/SymbolRules loi: {}", e.toString());
        }
    }

    // ------------------------------------------------------------------ truy cap cho hook
    public C3LiveEntry entry() {
        return entry;
    }

    public LiveBookC3 book() {
        return book;
    }

    /** Thanh vien chi so thi truong (da loai TradFi) — null neu chua co snapshot. */
    public Set<String> marketIndexOrNull() {
        if (!universe.hasSnapshot()) return null;
        Set<String> m = universe.marketIndexMembers();
        return m == null || m.isEmpty() ? null : m;
    }

    /**
     * [2b] Predicate "la TradFi" theo phan loai universe (de loai khoi feature cat ngang/thi truong). Chua co snapshot =>
     * thu nap DONG BO 1 lan (khoi dong: seed feature truoc vong ops); van chua co => null (khong loc + WARN o hook).
     */
    public Predicate<String> tradFiOrNull() {
        if (!universe.hasSnapshot()) {
            try {
                universe.refresh(System.currentTimeMillis());
            } catch (Throwable e) {
                LOG.warn("[C3-LIVE] nap universe dong bo loi: {}", e.toString());
            }
        }
        if (!universe.hasSnapshot()) return null;
        final SymbolUniverseLive u = universe;
        return s -> {
            Optional<TradFiClassifier.Verdict> v = u.classification(s);
            return v.isPresent() && v.get().isTradFi();
        };
    }

    public void putRef(String symbol, double px) {
        if (symbol != null && px > 0d) refs.put(symbol, BigDecimal.valueOf(px));
    }

    static double parseD(String raw, double def) {
        if (raw == null || raw.trim().isEmpty()) return def;
        try {
            double v = Double.parseDouble(raw.trim());
            return Double.isFinite(v) && v > 0d ? v : def;
        } catch (NumberFormatException e) {
            return def;
        }
    }
}
