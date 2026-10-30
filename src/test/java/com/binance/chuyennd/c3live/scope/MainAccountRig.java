package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.AssetBalance;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.exit.C3StopProtector;
import com.binance.chuyennd.c3live.exit.TrailingStopManager;
import com.binance.chuyennd.c3live.fill.FillAccounting;
import com.binance.chuyennd.c3live.fill.UserStreamEvents;
import com.binance.chuyennd.c3live.filters.SymbolRules;
import com.binance.chuyennd.c3live.guard.AccountModeGuard;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.c3live.recon.OwnStopGuard;
import com.binance.chuyennd.c3live.recon.Reconciler;
import com.binance.chuyennd.c3live.risk.C3LiveFlattener;
import com.binance.chuyennd.c3live.risk.C3MainEquity;
import com.binance.chuyennd.c3live.universe.SymbolUniverseLive;
import com.binance.chuyennd.ops.KillSwitchEngine;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.TradeUtils;

import java.io.File;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicLong;

/**
 * [V12 R4] Gian thu TAI KHOAN CHINH (mock offline): 44 vi the LEGACY (C30..C73) + lenh/algo LEGACY + bot LEGACY mo/dong ngau
 * nhien; lop c3 production THAT (C3Scope, C3ScopedGateway, C3StreamScope, C3MergedGuard, C3LegacyRefresher, C3StopProtector,
 * C3MainEquity, Reconciler qty, KillSwitchEngine ACT). Moi lop c3 chi di qua {@link #sgw}; bot LEGACY goi THANG mock.
 */
final class MainAccountRig {

    static final long T0 = 1_792_900_020_000L;
    static final long MIN = 60_000L;
    static final int LEGACY_N = 44;

    static String legacySym(int i) {
        return C3LiveFixtures.sym(30 + i);
    }

    final File root;
    final AtomicLong now = new AtomicLong(T0);
    final MockExchangeGateway mock;
    final ExchangeInfo ei = C3LiveFixtures.info(80);
    final List<String> alerts = new CopyOnWriteArrayList<>();
    final List<String> journal = new CopyOnWriteArrayList<>();
    final List<String> ksLines = new CopyOnWriteArrayList<>();
    final Map<String, BigDecimal> legacyExpected = new TreeMap<>();
    final Random rnd = new Random(42);
    int legacySeq;
    int legacyOps;
    double capital = 10_000d;
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
    int bar;

    MainAccountRig(File root) {
        this(root, new MockExchangeGateway(), 10_000d);
    }

    MainAccountRig(File root, MockExchangeGateway m, double capital) {
        this.root = root;
        this.mock = m;
        this.capital = capital;
        mock.exchangeInfo = ei;
        mock.now = T0;
        for (int i = 0; i < 80; i++) mock.setPrice(C3LiveFixtures.sym(i), new BigDecimal("1"));
        setAccount("500000", "200000");
        for (int i = 0; i < LEGACY_N; i++) {
            String s = legacySym(i);
            BigDecimal q = new BigDecimal(100 + i);
            mock.setPosition(s, q, BigDecimal.ONE);
            legacyExpected.put(s, q);
        }
        mock.addRestingOrder(legacySym(0), "web_lim_1", Side.BUY, new BigDecimal("50"));
        mock.addRestingStop(legacySym(1), "legacy_sl_1", new BigDecimal("101"), new BigDecimal("0.5"));
        KillSwitchEngine.Params p = new KillSwitchEngine.Params();
        p.c2Signed = true;
        p.latchFile = new File(root, "run/killsw_latch.json");
        p.resetFile = new File(root, "run/killsw_reset.req");
        p.autoReleaseMs = 30 * MIN;
        p.c4Capacity = true;
        p.c6OwnPeak = true;
        p.peakTag = "mock_c3eq";
        ks = new KillSwitchEngine(KillSwitchEngine.Mode.ACT, "act", new KillSwitchEngine.Sink() {
            public void info(String x) { ksLines.add(x); }
            public void warn(String x) { ksLines.add(x); }
        }, new File(root, "run/c3live_killsw_peak"), null, () -> Configs.U_MAX, T0, p);
        ks.setAlert(alerts::add);
        boot();
    }

    /** Tai khoan chinh: tmb (gom LEGACY) + availableBalance. */
    void setAccount(String tmb, String avail) {
        BigDecimal t = new BigDecimal(tmb);
        mock.accountSnapshot = new AccountSnapshot(t, t, new BigDecimal(avail), BigDecimal.ZERO,
                Collections.singletonList(new AssetBalance("USDT", t, t, new BigDecimal(avail), BigDecimal.ZERO)), 0L);
    }

    /** (Re)khoi dong cac thanh phan JVM tren CUNG file (restart). */
    void boot() {
        C3LiveOrderExecutor.ApiObserver api = (a, ok) -> ks.onApiResult(now.get(), a, ok);
        book = new LiveBookC3(new File(root, "run/c3live_book.json"), 1.0);
        scope = new C3Scope(book, now::get, new File(root, "run/c3live_merged.txt"));
        sgw = new C3ScopedGateway(mock, scope, now::get, null);
        sgw.setBook(book);
        sgw.setGuardSleep(ms -> {
            now.addAndGet(ms);
            mock.now = now.get();
        });
        C3LiveOrderExecutor.FillObserver fill = (s, b, f, r) -> ks.onFill(now.get(), s, b, f, r);
        audit = new OrderAuditLog(OrderAuditLog.LIVE_TAG, journal::add);
        acct = new FillAccounting(book, sgw, audit, fill, alerts::add, api, now::get, null);
        rec = new Reconciler(sgw, book, acct, () -> new SymbolRules(ei, T0), alerts::add, api, now::get, 0.01, 2, null);
        rec.setQtyReconcile(true);
        acct.setUnknownPositionSink(rec::onUnknownPosition);
        ex = new C3LiveOrderExecutor(sgw, book, api, fill, now::get, ms -> now.addAndGet(ms), 10_000L, 3, Runnable::run);
        eq = new C3MainEquity(sgw, book, scope, capital, new File(root, "run/c3live_equity_c3.json"), "mock", 0L, now::get, api,
                alerts::add);
        ks.attachEquitySource(eq);
        SymbolUniverseLive uni = new SymbolUniverseLive(SymbolUniverseLive.Config.defaults(), () -> ei, x -> { });
        uni.apply(ei, now.get());
        flat = new C3LiveFlattener(sgw, book, ks::requiredAction, alerts::add, api, now::get, 5, 10_000L, 10_000L);
        mgr = TrailingStopManager.builder().gateway(sgw).book(book).rules(() -> new SymbolRules(ei, T0))
                .closer(flat::closeCluster).defer((s, t, n) -> false).armHook((s, t, n) -> { })
                .action(ks::requiredAction).api(api).clock(now::get).safeRetryMs(10_000L).sleeper(ms -> { })
                .qtyModeFor(scope::isMerged).build();
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
        sgw.setSuspectSink(merged::suspect);
        protector = new C3StopProtector(book, mgr, flat::closeCluster, scope::isMerged, alerts::add, now::get);
        protector.setMergedCloseCheck(merged::exchangeCoversC3);   // [R4b §4] nhu runtime
        rec.setMergedPredicate(scope::isMerged);                   // [R4b MAJOR-1] nhu runtime
        stream = new C3StreamScope(scope, book, now::get);
        stream.setGateway(sgw);                                    // [R4b MINOR-1] nhu runtime
        stream.setSleeper(ms -> { });
        stream.setForeignFillSink(merged::onForeignFill);
        stream.setSuspectSink(merged::suspect);
        stream.setStopTerminalSink(protector::onStopTerminal);
        refresher = new C3LegacyRefresher(sgw, scope, merged, api, alerts::add, now::get);
        final FillAccounting a0 = acct;
        final C3StreamScope st = stream;
        mock.wsSink = txt -> {
            String f = st.filter(txt);
            if (f != null) a0.dispatch(UserStreamEvents.parse(f));
        };
        entry = C3LiveEntry.builder().book(book)
                .killSwitch(new C3LiveEntry.KillSwitchView() {
                    public boolean armed() { return true; }
                    public boolean allowNewEntry(String s) { return ks.allowNewEntry(s); }
                    public boolean allowDca(String s) { return ks.allowDca(s); }
                })
                .universe(uni).modeGuard(new AccountModeGuard(sgw, x -> { }).globalPolicy(false, false))
                .rules(() -> new SymbolRules(ei, T0)).capital(eq::capital).legacy(s -> scope.entryBlocked(s, now.get()))
                .budgetFn((m, c) -> TradeUtils.managerBudget(null, m, c, null)).legBudgetFn((b, i) -> b)
                .gridDue((f, px, n) -> n == 1 && px <= f * 0.5f).executor(ex)
                .audit(audit).pushAllowed(() -> true).dcaGridEnabled(true)
                .sizeCapOfEquity(0.045f).reconAllows(rec::allowsEntry).build();
        ex.resolveUnresolved(true);
        if (!refresher.refreshNow()) throw new IllegalStateException("refresh LEGACY loi");
        rec.startup();
    }

    void sync() {
        mock.now = now.get();
    }

    C3LiveEntry.Result buy(String sym, float ref, boolean dca) {
        bar++;
        sync();
        return entry.onLeg(new C3LiveEntry.LegInput(sym, dca ? "DCA_LEVEL1" : "BIG_DOWN", dca, T0 + bar * MIN, ref, ref, 1f,
                false, 0.5f, 1), now.get());
    }

    /** 1 nhip: san kich stop o gia => nhip exit (Urgent nhu runtime) => FLATTEN => bao ve => MERGED => LEGACY-busy. */
    void tick(String sym, String px) {
        now.addAndGet(10_000L);
        sync();
        BigDecimal p = new BigDecimal(px);
        mock.triggerStops(sym, p);
        Map<String, Float> m = new HashMap<>();
        for (String s : book.ownedSymbols()) {
            BigDecimal x = mock.price(s);
            if (x != null) m.put(s, x.floatValue());
        }
        m.put(sym, p.floatValue());
        try (com.binance.chuyennd.c3live.rate.RateGuard.Urgent u =
                     com.binance.chuyennd.c3live.rate.RateGuard.urgent(now.get() + C3StopProtector.DEADLINE_MS)) {
            mgr.step(m);
        }
        flat.step();
        protector.check();
        merged.poll();
        refresher.tick();
        rec.confirmPendingFlat();
        Double e = eq.c3Equity();
        if (e != null) ks.onPaper(now.get(), book.openCount(), (float) book.marginUsed(), e.floatValue());
    }

    /** Bot LEGACY: lenh MARKET cid khong-c3 tren symbol LEGACY / tu do (KHONG BAO GIO symbol trong {@code avoid}). */
    void legacyBot(int nOps, Set<String> avoid) {
        sync();
        List<String> pool = new ArrayList<>();
        for (int i = 0; i < LEGACY_N; i++) pool.add(legacySym(i));
        for (int i = 74; i < 80; i++) pool.add(C3LiveFixtures.sym(i));
        pool.removeAll(avoid);
        for (int k = 0; k < nOps; k++) {
            String s = pool.get(rnd.nextInt(pool.size()));
            BigDecimal cur = mock.position(s);
            boolean sell = cur.signum() > 0 && rnd.nextBoolean();
            BigDecimal q = new BigDecimal(1 + rnd.nextInt(20));
            if (sell) q = q.min(cur);
            legacyTrade(s, sell ? Side.SELL : Side.BUY, q);
        }
    }

    void legacyTrade(String s, Side side, BigDecimal q) {
        sync();
        mock.newMarketOrder(s, side, q, "legacy-" + (++legacySeq), side == Side.SELL);
        legacyOps++;
        BigDecimal cur = legacyExpected.getOrDefault(s, BigDecimal.ZERO);
        legacyExpected.put(s, side == Side.BUY ? cur.add(q) : cur.subtract(q));
    }

    /** Moi lenh GHI cid c3 tren mock: chi tren symbol cho phep; khong lenh ghi nao cua c3 mang cid khong-c3. */
    List<String> c3WritesOutside(Set<String> allowed) {
        List<String> bad = new ArrayList<>();
        for (String l : mock.callLog()) {
            String[] t = l.split(":", 3);
            if (t.length < 3) continue;
            String cid = t[2];
            if (C3Scope.isC3Cid(cid)) {
                if (!allowed.contains(t[1])) bad.add(l);
            } else if (!cid.startsWith("legacy-")) {
                bad.add(l);
            }
        }
        return bad;
    }
}
