package com.binance.chuyennd.c3live.entry;

import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.exec.C3LiveCids;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.filters.SymbolRules;
import com.binance.chuyennd.c3live.guard.AccountModeGuard;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.universe.SymbolUniverseLive;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.util.EnumMap;
import java.util.Map;
import java.util.Optional;
import java.util.function.BiConsumer;
import java.util.function.BooleanSupplier;
import java.util.function.Predicate;
import java.util.function.Supplier;

/**
 * [V12 C1/C3/C4/C5/C8] Duong vao lenh THAT cua c3_live cho 1 leg da qua cong quyet dinh (gate/AI) cua
 * {@code DetectEntrySignal2TradeNormal.createOrderBuyRequest}.
 *
 * <p>Thu tu kiem (MASTER 10-25): {@code killSwitchArmed} && {@code allowNewEntry(sym)} && {@code isBuyable(sym, now)}
 * (da loai TradFi/non-ASCII/delist<7d/EXCLUDE) && [so that: LEGACY / trung coin / DCA grid] &&
 * {@code AccountModeGuard.checkSymbol(sym)} OK => sizing = managerBudget(U = margin(pending+confirmed)/von, U_MAX)
 * x ratio grid, tran 4,5 % von, x tier => {@link SymbolRules#sizeMarketBuy} (khong dat => BO leg + dong SKIP) =>
 * {@link LiveBookC3#reserve} (PENDING, dong bo) => {@link C3LiveOrderExecutor#submit} (luong rieng).
 * Von = min(pilot, totalMarginBalance) (Q1b). Khong bao gio nem ra ngoai.
 */
public final class C3LiveEntry {

    private static final Logger LOG = LoggerFactory.getLogger(C3LiveEntry.class);
    private static final long WARN_EVERY_MS = 600_000L;

    public enum Outcome {
        DISABLED, PUSH_OFF, KS_NOT_ARMED, KS_BLOCKED, NOT_BUYABLE, BOOK_UNHEALTHY, LEGACY, HOLDING, DCA_OFF,
        DCA_NOT_HOLDING, DCA_PENDING, DCA_NOT_DUE, TIER3_DCA, MODE_GUARD, NO_RULES, NO_EQUITY, U_MAX, BUDGET_SMALL,
        SIZING, RESERVE_FAIL, BAD_INPUT, ERROR, SUBMITTED, RECON_BLOCKED
    }

    public interface KillSwitchView {
        boolean armed();

        boolean allowNewEntry(String symbol);

        /** [V12 2b] DCA cum dang co: C4 (cong suat) KHONG chan DCA; latch van chan. Mac dinh = allowNewEntry. */
        default boolean allowDca(String symbol) {
            return allowNewEntry(symbol);
        }
    }

    public interface CapitalSource {
        Double capital();
    }

    /** = {@code TradeUtils.managerBudget(null, marginUsed, capital, level)} (null = U >= U_MAX). */
    public interface BudgetFn {
        Float budget(float marginUsed, float capital);
    }

    /** = {@code LiveGridSizing.legBudget}. */
    public interface LegBudgetFn {
        Float apply(Float budget, int legIdx);
    }

    /** = {@code DcaUtils.shouldDcaGrid}. */
    public interface GridDue {
        boolean due(float firstEntryPrice, float lastPrice, int legCount);
    }

    public static final class LegInput {
        public final String symbol;
        public final String level;
        public final boolean dca;
        public final long barStartMs;
        public final double refPx;
        public final double sizingPx;
        public final float tierMultiplier;
        public final boolean tier3;
        /** [V12 2b] symbolPred / rank cua leg (nhu so giay) => metadata cum (trailing dung symbolPred). */
        public final Float symbolPred;
        public final int rank;

        public LegInput(String symbol, String level, boolean dca, long barStartMs, double refPx, double sizingPx,
                        float tierMultiplier, boolean tier3) {
            this(symbol, level, dca, barStartMs, refPx, sizingPx, tierMultiplier, tier3, null, -1);
        }

        public LegInput(String symbol, String level, boolean dca, long barStartMs, double refPx, double sizingPx,
                        float tierMultiplier, boolean tier3, Float symbolPred, int rank) {
            this.symbolPred = symbolPred;
            this.rank = rank;
            this.symbol = symbol;
            this.level = level;
            this.dca = dca;
            this.barStartMs = barStartMs;
            this.refPx = refPx;
            this.sizingPx = sizingPx;
            this.tierMultiplier = tierMultiplier;
            this.tier3 = tier3;
        }
    }

    public static final class Result {
        public final Outcome outcome;
        public final String cid;
        public final BigDecimal qty;
        public final double budget;
        public final double marginBefore;
        public final double capital;
        public final String detail;

        Result(Outcome outcome, String cid, BigDecimal qty, double budget, double marginBefore, double capital,
               String detail) {
            this.outcome = outcome;
            this.cid = cid;
            this.qty = qty;
            this.budget = budget;
            this.marginBefore = marginBefore;
            this.capital = capital;
            this.detail = detail;
        }

        static Result of(Outcome o, String detail) {
            return new Result(o, null, null, Double.NaN, Double.NaN, Double.NaN, detail);
        }

        @Override
        public String toString() {
            return outcome + (cid == null ? "" : " cid=" + cid) + (qty == null ? "" : " qty=" + qty.toPlainString())
                    + (Double.isNaN(budget) ? "" : " budget=" + budget) + " " + detail;
        }
    }

    private final LiveBookC3 book;
    private final KillSwitchView ks;
    private final SymbolUniverseLive universe;
    private final AccountModeGuard modeGuard;
    private final Supplier<SymbolRules> rules;
    private final CapitalSource capital;
    private final Predicate<String> legacy;
    private final BudgetFn budgetFn;
    private final LegBudgetFn legBudgetFn;
    private final GridDue gridDue;
    private final C3LiveOrderExecutor exec;
    private final OrderAuditLog audit;
    private final BiConsumer<String, Double> refSink;
    private final BooleanSupplier pushAllowed;
    private final boolean dcaGridEnabled;
    private final float sizeCapOfEquity;
    private final double minBudget;
    private final Predicate<String> reconAllows;
    private final Map<Outcome, Long> counts = new EnumMap<>(Outcome.class);
    private final Map<Outcome, Long> lastWarn = new EnumMap<>(Outcome.class);

    private C3LiveEntry(Builder b) {
        this.book = b.book;
        this.ks = b.ks;
        this.universe = b.universe;
        this.modeGuard = b.modeGuard;
        this.rules = b.rules;
        this.capital = b.capital;
        this.legacy = b.legacy == null ? s -> false : b.legacy;
        this.budgetFn = b.budgetFn;
        this.legBudgetFn = b.legBudgetFn == null ? (x, i) -> x : b.legBudgetFn;
        this.gridDue = b.gridDue;
        this.exec = b.exec;
        this.audit = b.audit;
        this.refSink = b.refSink == null ? (s, p) -> { } : b.refSink;
        this.pushAllowed = b.pushAllowed == null ? () -> true : b.pushAllowed;
        this.dcaGridEnabled = b.dcaGridEnabled;
        this.sizeCapOfEquity = b.sizeCapOfEquity;
        this.minBudget = b.minBudget;
        this.reconAllows = b.reconAllows == null ? s -> true : b.reconAllows;
    }

    public static Builder builder() {
        return new Builder();
    }

    public LiveBookC3 book() {
        return book;
    }

    /** Xu ly 1 leg (tuan tu hoa tren instance). Khong nem. */
    public Result onLeg(LegInput in, long nowMs) {
        Result r;
        try {
            // tuan tu hoa: kiem trung coin + doc U + giu cho la MOT buoc (tick selector/market co the chay song song)
            synchronized (this) {
                r = decide(in, nowMs);
            }
        } catch (Throwable t) {
            r = Result.of(Outcome.ERROR, t.toString());
            LOG.error("[C3-LIVE] loi leg {}: {}", in == null ? "-" : in.symbol, t.toString());
        }
        synchronized (counts) {
            counts.merge(r.outcome, 1L, Long::sum);
        }
        log(in, r, nowMs);
        return r;
    }

    private Result decide(LegInput in, long nowMs) {
        if (in == null || in.symbol == null || !(in.refPx > 0d) || !(in.sizingPx > 0d)) {
            return Result.of(Outcome.BAD_INPUT, "input");
        }
        String sym = in.symbol;
        if (!pushAllowed.getAsBoolean()) return Result.of(Outcome.PUSH_OFF, "push dong (SHADOW_NO_PUSH/LIVE_ENTRY/KILL file)");
        // (1) kill-switch phai o mode act (c3_live) — khong thi tu choi push
        if (!ks.armed()) return Result.of(Outcome.KS_NOT_ARMED, "kill-switch khong o mode act");
        // (2) latch NO_NEW_ENTRY/FLATTEN chan ca entry lan DCA
        // [V12 2b] DCA: chi latch chan (C4 cong suat khong chan DCA); mo cum moi: latch + C4 cong suat
        if (in.dca ? !ks.allowDca(sym) : !ks.allowNewEntry(sym)) {
            return Result.of(Outcome.KS_BLOCKED, in.dca ? "latch" : "latch/C4 cong suat");
        }
        // (3) universe: TradFi / non-ASCII / delist < 7d / EXCLUDE / snapshot cu
        if (!universe.isBuyable(sym, nowMs)) {
            Optional<String> why = universe.whyNotBuyable(sym, nowMs);
            return Result.of(Outcome.NOT_BUYABLE, why.orElse("?"));
        }
        if (!book.healthy()) return Result.of(Outcome.BOOK_UNHEALTHY, book.unhealthyReason());
        // [V12 2b C9] reconcile chan (vi the la / lech equity > 1 % / reconcile khoi dong loi)
        if (!reconAllows.test(sym)) return Result.of(Outcome.RECON_BLOCKED, "reconcile chan mo moi");
        if (legacy.test(sym)) return Result.of(Outcome.LEGACY, "vi the LEGACY");
        // (so THAT) trung coin / DCA grid
        int legIdx;
        if (in.dca) {
            if (!dcaGridEnabled) return Result.of(Outcome.DCA_OFF, "LIVE_DCA_GRID tat");
            Optional<LiveBookC3.ClusterView> c = book.cluster(sym);
            if (!c.isPresent()) return Result.of(Outcome.DCA_NOT_HOLDING, "khong giu");
            if (c.get().hasUnresolved || c.get().closeReason != null || c.get().confirmedQty.signum() <= 0) {
                return Result.of(Outcome.DCA_PENDING, "cum con leg treo/dang dong");
            }
            if (!gridDue.due((float) c.get().firstEntryPrice, (float) in.refPx, c.get().legCount)) {
                return Result.of(Outcome.DCA_NOT_DUE, "first=" + c.get().firstEntryPrice + " px=" + in.refPx + " legs="
                        + c.get().legCount);
            }
            legIdx = c.get().legCount;
            if (in.tier3) return Result.of(Outcome.TIER3_DCA, "TIER_3 chan DCA");
        } else {
            if (book.isHolding(sym)) return Result.of(Outcome.HOLDING, "dang giu");
            legIdx = 0;
        }
        // (4) che do tai khoan / symbol (one-way, CROSSED, leverage 1, multiAssets)
        AccountModeGuard.Result mg = modeGuard.checkSymbol(sym);
        if (mg == null || !mg.isOk()) return Result.of(Outcome.MODE_GUARD, String.valueOf(mg));
        SymbolRules sr = rules.get();
        if (sr == null) return Result.of(Outcome.NO_RULES, "chua nap exchangeInfo");
        // sizing
        Double cap = capital.capital();
        if (cap == null || !(cap > 0d)) return Result.of(Outcome.NO_EQUITY, "equity null");
        double used = book.marginUsed();
        Float b = budgetFn.budget((float) used, cap.floatValue());
        if (b == null) {
            return new Result(Outcome.U_MAX, null, null, Double.NaN, used, cap, "U=" + (used / cap) + " >= U_MAX");
        }
        b = legBudgetFn.apply(b, legIdx);
        if (b == null) return new Result(Outcome.U_MAX, null, null, Double.NaN, used, cap, "legBudget null");
        float capAmt = sizeCapOfEquity * cap.floatValue();
        if (b > capAmt) b = capAmt;
        if (b < minBudget) {
            return new Result(Outcome.BUDGET_SMALL, null, null, b, used, cap, "budget<" + minBudget);
        }
        b = b * in.tierMultiplier;
        double notionalBudget = b.doubleValue() * book.leverage();
        SymbolRules.Sizing sz = sr.sizeMarketBuy(sym, BigDecimal.valueOf(notionalBudget), BigDecimal.valueOf(in.sizingPx));
        if (sz == null || !sz.isOk()) {
            String reason = sz == null ? "null" : sz.getReason() + " " + sz.getDetail();
            audit.record(OrderAuditLog.Entry.of(nowMs).symbol(sym).side("BUY").type("MARKET").status("SKIP")
                    .price(BigDecimal.valueOf(in.sizingPx)).reason("sizing:" + reason));
            return new Result(Outcome.SIZING, null, null, b, used, cap, reason);
        }
        String cid = C3LiveCids.entry(sym, C3LiveCids.barMin(in.barStartMs), legIdx);
        double margin = sz.getNotional().doubleValue() / book.leverage();
        if (!book.reserve(sym, cid, legIdx, C3LiveCids.barMin(in.barStartMs), in.level, in.refPx, sz.getQty(), margin,
                nowMs)) {
            return new Result(Outcome.RESERVE_FAIL, cid, sz.getQty(), b, used, cap, "reserve false (cid trung/dong/so hong)");
        }
        book.setMeta(sym, in.symbolPred, in.rank, nowMs);   // [V12 2b] symbolPred/rank leg dau co gia tri (nhu so giay)
        refSink.accept(sym, in.refPx);
        exec.submit(cid);
        return new Result(Outcome.SUBMITTED, cid, sz.getQty(), b, used, cap,
                "legIdx=" + legIdx + " notional=" + sz.getNotional().toPlainString() + " U_before=" + (used / cap));
    }

    private void log(LegInput in, Result r, long nowMs) {
        String sym = in == null ? "-" : in.symbol;
        String lvl = in == null ? "-" : in.level;
        switch (r.outcome) {
            case SUBMITTED:
                LOG.info("[C3-LIVE] SUBMIT {} {} {}", sym, lvl, r);
                return;
            case LEGACY:
            case DCA_NOT_HOLDING:
            case DCA_NOT_DUE:
            case DCA_OFF:
                LOG.debug("[C3-LIVE] skip {} {} {}", sym, lvl, r);
                return;
            case DISABLED:
            case PUSH_OFF:
            case KS_NOT_ARMED:
            case BOOK_UNHEALTHY:
            case NO_RULES:
            case NO_EQUITY:
            case ERROR: {
                Long last;
                synchronized (lastWarn) {
                    last = lastWarn.get(r.outcome);
                    if (last != null && nowMs - last < WARN_EVERY_MS) return;
                    lastWarn.put(r.outcome, nowMs);
                }
                LOG.warn("[C3-LIVE] KHONG vao lenh {} {} {}", sym, lvl, r);
                return;
            }
            default:
                LOG.info("[C3-LIVE] skip {} {} {}", sym, lvl, r);
        }
    }

    public Map<Outcome, Long> counts() {
        synchronized (counts) {
            return new EnumMap<>(counts);
        }
    }

    public static final class Builder {
        private LiveBookC3 book;
        private KillSwitchView ks;
        private SymbolUniverseLive universe;
        private AccountModeGuard modeGuard;
        private Supplier<SymbolRules> rules;
        private CapitalSource capital;
        private Predicate<String> legacy;
        private BudgetFn budgetFn;
        private LegBudgetFn legBudgetFn;
        private GridDue gridDue;
        private C3LiveOrderExecutor exec;
        private OrderAuditLog audit;
        private BiConsumer<String, Double> refSink;
        private BooleanSupplier pushAllowed;
        private boolean dcaGridEnabled;
        private float sizeCapOfEquity = 0.045f;
        private double minBudget = 5d;
        private Predicate<String> reconAllows;

        public Builder book(LiveBookC3 v) { book = v; return this; }
        public Builder killSwitch(KillSwitchView v) { ks = v; return this; }
        public Builder universe(SymbolUniverseLive v) { universe = v; return this; }
        public Builder modeGuard(AccountModeGuard v) { modeGuard = v; return this; }
        public Builder rules(Supplier<SymbolRules> v) { rules = v; return this; }
        public Builder capital(CapitalSource v) { capital = v; return this; }
        public Builder legacy(Predicate<String> v) { legacy = v; return this; }
        public Builder budgetFn(BudgetFn v) { budgetFn = v; return this; }
        public Builder legBudgetFn(LegBudgetFn v) { legBudgetFn = v; return this; }
        public Builder gridDue(GridDue v) { gridDue = v; return this; }
        public Builder executor(C3LiveOrderExecutor v) { exec = v; return this; }
        public Builder audit(OrderAuditLog v) { audit = v; return this; }
        public Builder refSink(BiConsumer<String, Double> v) { refSink = v; return this; }
        public Builder pushAllowed(BooleanSupplier v) { pushAllowed = v; return this; }
        public Builder dcaGridEnabled(boolean v) { dcaGridEnabled = v; return this; }
        public Builder sizeCapOfEquity(float v) { sizeCapOfEquity = v; return this; }
        public Builder minBudget(double v) { minBudget = v; return this; }
        public Builder reconAllows(Predicate<String> v) { reconAllows = v; return this; }

        public C3LiveEntry build() {
            if (book == null || ks == null || universe == null || modeGuard == null || rules == null || capital == null
                    || budgetFn == null || gridDue == null || exec == null || audit == null) {
                throw new IllegalStateException("C3LiveEntry thieu thanh phan");
            }
            return new C3LiveEntry(this);
        }
    }
}
