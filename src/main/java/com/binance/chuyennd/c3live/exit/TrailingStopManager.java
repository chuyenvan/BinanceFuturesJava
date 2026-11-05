package com.binance.chuyennd.c3live.exit;

import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.OrderStatus;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.exec.C3LiveCids;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.filters.SymbolRules;
import com.binance.chuyennd.c3live.recon.OwnStopGuard;
import com.binance.chuyennd.ops.KillSwitchEngine;
import com.binance.chuyennd.tradecore.selector.C3TrailRate;
import com.binance.chuyennd.tradecore.selector.TsMktExt;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Consumer;
import java.util.function.LongSupplier;
import java.util.function.Supplier;

/**
 * [V12 C6 vong 2b] Thoat THAT cua c3_live — CUNG luat voi so giay {@code ShadowBookC3.tick}, chay tren cum THAT
 * ({@link LiveBookC3}):
 * <ol>
 *   <li>peakRate = max(peakRate, (px - VWAP)/VWAP) (VWAP kieu float y het so giay, {@code ClusterView.avgEntryF});</li>
 *   <li>chua arm: rate &gt; 0,07 ({@code LiveProfileC3.ARM_RATE}) => priceSL = VWAP·(1 + trailRate(peak, symbolPred));
 *       neu khong va tuoi &gt; 168h => {@link TsMktExt#deferTimeStop} (X14) — hoan thi giu, khong thi dong MARKET
 *       reduce-only qua {@link Closer} (= {@code C3LiveFlattener.closeCluster}, idempotent C3);</li>
 *   <li>da arm: ratchet LIEN TUC priceSL = max(priceSL, VWAP·(1 + trailRate(peak)));
 *       trailRate = {@link C3TrailRate#trailRate} (= {@code ShadowBookC3.trailRate} =>
 *       {@code TradeUtils.calRateLossDynamicBuyPNoPump}) — KHONG viet lai cong thuc;</li>
 *   <li>stop TREN SAN: STOP_MARKET SELL, mac dinh closePosition=true (workingType theo client, mac dinh MARK_PRICE),
 *       gia = round-down(priceSL, tick); DOI chi khi muc moi &gt;= muc cu + 1 tick VA &gt;= muc cu·(1 + 0,1 %);
 *       doi = DAT stop moi (clientAlgoId {@code c3s-...-seq}, persist TRUOC khi gui) roi HUY stop cu (khong khoang trong).
 *       San tu choi vi da co stop closePosition cung chieu (-4130, CHUA XAC MINH voi Algo API) => dat stop moi kieu
 *       qty + reduceOnly (khong khoang trong). San tu choi vi "would immediately trigger" (-2021) => dong ngay MARKET;</li>
 *   <li>DCA khop (LiveBookC3.confirm legIdx&gt;0) reset arm nhu so giay => stop dang co bi huy.</li>
 * </ol>
 * Stop khop / san dong vi the: biet qua C7 (user stream) hoac C9 (reconcile REST) => cap nhat so + huy stop con lai
 * (khong o lop nay). Kill-switch FLATTEN => khong lam gi (flattener lo). Khong bao gio nem ra ngoai.
 */
public final class TrailingStopManager {

    private static final Logger LOG = LoggerFactory.getLogger(TrailingStopManager.class);
    public static final String REASON_TIME_STOP = "TIME_STOP_168H";
    public static final String REASON_TRAIL_IMMEDIATE = "TRAILING_IMMEDIATE";
    public static final double DEFAULT_MIN_MOVE_FRAC = 0.001d;
    static final int CODE_CLOSE_POSITION_EXISTS = -4130;
    static final int CODE_WOULD_TRIGGER = -2021;

    public enum StopMode { CLOSE_POSITION, REDUCE_ONLY_QTY }

    /** = {@link C3TrailRate#trailRate}. */
    public interface TrailFn {
        float trailRate(float peakRate, Float symbolPred, String symbol);
    }

    /** = {@link TsMktExt#deferTimeStop}. */
    public interface TimeStopDefer {
        boolean defer(String symbol, long tsFirstLeg, long now);
    }

    /** = {@link TsMktExt#onArmed} (chi log). */
    public interface ArmHook {
        void onArmed(String symbol, long tsFirstLeg, long now);
    }

    /** = {@code C3LiveFlattener.closeCluster} (MARKET reduce-only idempotent). */
    public interface Closer {
        int closeCluster(String symbol, String reason);
    }

    /** Su kien (de test/replay so voi so giay). type: ARM, SL, STOP_PLACED, STOP_CANCEL, TIME_STOP, DEFER, IMMEDIATE. */
    public interface EventSink {
        void event(String type, String symbol, long now, double value, String detail);
    }

    private final ExchangeGateway gw;
    private final LiveBookC3 book;
    private final Supplier<SymbolRules> rules;
    private final Closer closer;
    private final TrailFn trail;
    private final TimeStopDefer defer;
    private final ArmHook armHook;
    private final Supplier<KillSwitchEngine.Action> action;
    private final C3LiveOrderExecutor.ApiObserver api;
    private final Consumer<String> alert;
    private final LongSupplier clock;
    private final float armRate;
    private final long timeStopMs;
    private final BigDecimal minMoveMult;
    private final long safeRetryMs;
    private final StopMode stopMode;
    private final EventSink events;
    private volatile boolean closePositionConflictSeen;
    private OwnStopGuard guard;
    private long lastNoRulesWarnMs = Long.MIN_VALUE / 2;
    private long lastBookErrMs = Long.MIN_VALUE / 2;
    private final AtomicLong nArm = new AtomicLong();
    private final AtomicLong nPlace = new AtomicLong();
    private final AtomicLong nMove = new AtomicLong();
    private final AtomicLong nCancel = new AtomicLong();
    private final AtomicLong nTimeStop = new AtomicLong();
    private final AtomicLong nDefer = new AtomicLong();
    private final AtomicLong nImmediate = new AtomicLong();
    private final AtomicLong nFallbackQty = new AtomicLong();
    private final AtomicLong nUnconfirmed = new AtomicLong();
    /** [2g MIN-20] cho giua 2 lan kiem stop moi (test thay bang ham ghi nhan). */
    private final java.util.function.LongConsumer sleeper;
    /** [V12 R4 R2] symbol bat buoc stop qty reduceOnly = qty c3 con mo (MERGED). Mac dinh: khong symbol nao. */
    private final java.util.function.Predicate<String> forceQty;

    private TrailingStopManager(Builder b) {
        this.gw = b.gw;
        this.book = b.book;
        this.rules = b.rules;
        this.closer = b.closer;
        this.trail = b.trail == null ? C3TrailRate::trailRate : b.trail;
        this.defer = b.defer == null ? TsMktExt::deferTimeStop : b.defer;
        this.armHook = b.armHook == null ? TsMktExt::onArmed : b.armHook;
        this.action = b.action == null ? () -> KillSwitchEngine.Action.NONE : b.action;
        this.api = b.api == null ? (a, ok) -> { } : b.api;
        this.alert = b.alert == null ? m -> { } : b.alert;
        this.clock = b.clock == null ? System::currentTimeMillis : b.clock;
        this.armRate = b.armRate;
        this.timeStopMs = b.timeStopHours * 3_600_000L;
        this.minMoveMult = BigDecimal.ONE.add(BigDecimal.valueOf(b.minMoveFrac));
        this.safeRetryMs = Math.max(0L, b.safeRetryMs);
        this.stopMode = b.stopMode == null ? StopMode.CLOSE_POSITION : b.stopMode;
        this.events = b.events == null ? (t, s, n, v, d) -> { } : b.events;
        this.sleeper = b.sleeper == null ? TrailingStopManager::sleepQuiet : b.sleeper;
        this.forceQty = b.forceQty == null ? s -> false : b.forceQty;
        this.guard = new OwnStopGuard(gw, book, this.api, this.alert, null, this.clock);
    }

    public static Builder builder() {
        return new Builder();
    }

    /** Khoi dong X14 (idempotent; tat => khong lam gi). */
    public static void startTsExtIfEnabled() {
        TsMktExt.startIfEnabled();
    }

    /**
     * Mot nhip exit cho moi cum that. {@code prices} = gia hien tai theo symbol (cung nguon gia nhip exit so giay:
     * price_realtime). @return so thao tac san (dat/huy/dong) da lam.
     */
    public synchronized int step(Map<String, Float> prices) {
        long now = clock.getAsLong();
        if (action.get() == KillSwitchEngine.Action.FLATTEN) return 0;
        int ops = 0;
        for (LiveBookC3.ClusterView c : book.clusters()) {
            try {
                ops += stepOne(c, prices, now);
            } catch (Throwable t) {
                LOG.error("[C3-LIVE-TRAIL] loi nhip {}: {}", c.symbol, t.toString());
            }
        }
        return ops;
    }

    private int stepOne(LiveBookC3.ClusterView c0, Map<String, Float> prices, long now) {
        String sym = c0.symbol;
        int ops = 0;
        for (String oc : c0.orphanStops) ops += cancelOrphan(sym, oc, now, GUARDED);
        if (c0.closeReason != null) {   // dang dong (time-stop/X14/immediate): day tiep lenh dong (idempotent)
            ops += closer.closeCluster(sym, c0.closeReason);
            return ops;
        }
        if (c0.hasUnresolved || c0.confirmedQty.signum() <= 0) return ops;
        LiveBookC3.ClusterView c = c0;
        boolean pendingBlocks = false;
        if (c.pendingStopCid != null) {
            ops += resolvePending(c, now);
            Optional<LiveBookC3.ClusterView> re = book.cluster(sym);
            if (!re.isPresent()) return ops;
            c = re.get();
            pendingBlocks = c.pendingStopCid != null;
        }
        Float pxO = prices == null ? null : prices.get(sym);
        if (pxO == null || !(pxO > 0f)) {
            // khong co gia (feed loi / vua restart): cum DA arm ma chua co stop tren san => dat lai theo priceSL da persist
            if (!pendingBlocks && c.trailArmed() && c.stopClientAlgoId == null) ops += syncStop(c, c.priceSL, now);
            if (!c.trailArmed() && c.stopClientAlgoId != null) {   // DCA reset arm: huy stop cu ke ca khi chua co gia
                String old = book.retireActiveStop(sym, now);
                if (old != null) ops += cancelOrphan(sym, old, now, RETIRED);
            }
            return ops;
        }
        float px = pxO;
        float entry = c.avgEntryF;
        if (!(entry > 0f)) return ops;
        // ---- CUNG thu tu phep tinh voi ShadowBookC3.tick
        float rate = (px - entry) / entry;
        float peak = c.peakRate;
        if (rate > peak) peak = rate;
        float sl = c.priceSL;
        if (Float.isNaN(sl)) {
            if (rate > armRate) {
                sl = entry * (1f + trail.trailRate(peak, c.symbolPred, sym));
                nArm.incrementAndGet();
                LOG.info("[C3-LIVE-TRAIL] arm {} entry={} px={} peak={} SL={}", sym, entry, px, peak, sl);
                events.event("ARM", sym, now, sl, "peak=" + peak);
                try {
                    armHook.onArmed(sym, c.tsFirstLeg, now);
                } catch (Throwable ignore) {
                    // chi log
                }
            } else if (now - c.tsFirstLeg > timeStopMs) {
                book.setTrail(sym, peak, Float.NaN, now);
                if (defer.defer(sym, c.tsFirstLeg, now)) {
                    nDefer.incrementAndGet();
                    events.event("DEFER", sym, now, px, "age_h=" + (now - c.tsFirstLeg) / 3_600_000L);
                    return ops;
                }
                nTimeStop.incrementAndGet();
                LOG.warn("[C3-LIVE-TRAIL] TIME-STOP {} entry={} px={} gio_giu={} => dong MARKET reduce-only", sym, entry, px,
                        (now - c.tsFirstLeg) / 3_600_000L);
                events.event("TIME_STOP", sym, now, px, "");
                ops += closer.closeCluster(sym, REASON_TIME_STOP);
                return ops;
            }
        }
        if (!Float.isNaN(sl)) {
            float nsl = entry * (1f + trail.trailRate(peak, c.symbolPred, sym));
            if (nsl > sl) {
                sl = nsl;
                events.event("SL", sym, now, sl, "peak=" + peak);
            }
        }
        book.setTrail(sym, peak, sl, now);
        if (Float.isNaN(sl)) {
            if (c.stopClientAlgoId != null) {   // vd DCA reset arm => stop cu khong con hop le
                String old = book.retireActiveStop(sym, now);
                LOG.info("[C3-LIVE-TRAIL] {} khong con arm (DCA reset) => huy stop {}", sym, old);
                if (old != null) ops += cancelOrphan(sym, old, now, RETIRED);
            }
            return ops;
        }
        if (pendingBlocks) return ops;
        Optional<LiveBookC3.ClusterView> cur = book.cluster(sym);
        if (!cur.isPresent()) return ops;
        ops += syncStop(cur.get(), sl, now);
        return ops;
    }

    /** Dat / doi stop tren san theo priceSL logic (round-down tick, nguong 1 tick + 0,1 %). */
    private int syncStop(LiveBookC3.ClusterView c, float sl, long now) {
        String sym = c.symbol;
        SymbolRules r = rules == null ? null : rules.get();
        if (r == null) {
            if (now - lastNoRulesWarnMs > 600_000L) {
                lastNoRulesWarnMs = now;
                LOG.warn("[C3-LIVE-TRAIL] chua co SymbolRules => CHUA dat duoc stop tren san (vd {})", sym);
            }
            return 0;
        }
        BigDecimal desired;
        try {
            desired = r.roundStopPriceForLong(sym, new BigDecimal(Float.toString(sl)));
        } catch (RuntimeException e) {
            desired = null;
        }
        if (desired == null || desired.signum() <= 0) return 0;
        if (c.stopClientAlgoId == null) return place(c, desired, now, "ARM");
        BigDecimal curPx = BigDecimal.valueOf(c.stopPrice);
        BigDecimal tick = r.tickSize(sym);
        boolean tickOk = tick == null || tick.signum() <= 0 ? desired.compareTo(curPx) > 0
                : desired.compareTo(curPx.add(tick)) >= 0;
        boolean pctOk = desired.compareTo(curPx.multiply(minMoveMult)) >= 0;
        if (tickOk && pctOk) return place(c, desired, now, "MOVE");
        return 0;
    }

    private int place(LiveBookC3.ClusterView c, BigDecimal price, long now, String why) {
        boolean qty = stopMode == StopMode.REDUCE_ONLY_QTY || forceQty.test(c.symbol)
                || (c.stopClientAlgoId != null && !c.stopQtyMode && closePositionConflictSeen);
        return send(c, price, qty, now, why, true);
    }

    private int send(LiveBookC3.ClusterView c, BigDecimal price, boolean qtyMode, long now, String why,
                     boolean allowFallback) {
        String sym = c.symbol;
        BigDecimal stopQty = c.confirmedQty;
        if (qtyMode && forceQty.test(sym)) {   // [V12 R4 R2] MERGED: qty = PHAN c3 con mo (khong bao gio dong phan LEGACY)
            stopQty = c.confirmedQty.subtract(c.exitQty == null ? BigDecimal.ZERO : c.exitQty);
            if (stopQty.signum() <= 0) return 0;
        }
        int seq = book.nextStopSeq(sym, now);
        if (seq < 0) return 0;
        String cid = C3LiveCids.stop(sym, Math.floorDiv(now, 60_000L), seq);
        book.setPendingStop(sym, cid, price.doubleValue(), qtyMode, now);
        if (!book.healthy()) {
            // [2c MIN-6] san la nguon su that: so khong ghi duoc VAN dat/doi stop (trang thai giu trong RAM; restart =>
            // Reconciler nhan lai stop c3s- cao nhat cua cum da arm thay vi huy) + ERROR + Telegram (thua 10')
            if (now - lastBookErrMs > 600_000L) {
                lastBookErrMs = now;
                String m = "[C3-LIVE-TRAIL] " + sym + " SO KHONG GHI DUOC (dia day/loi IO) => VAN dat stop " + cid
                        + " tren san (bao ve vi the); kiem dia/so NGAY";
                LOG.error("{}", m);
                try {
                    if (alert != null) alert.accept(m);
                } catch (Throwable ignore) {
                    // alert khong duoc chan dat stop
                }
            } else {
                LOG.error("[C3-LIVE-TRAIL] {} so khong ghi duoc => van dat stop {} tren san", sym, cid);
            }
        }
        try {
            OrderInfo resp;
            if (qtyMode) {
                resp = gw.newStopMarket(sym, Side.SELL, stopQty, price, cid, true);
            } else {
                resp = gw.newStopMarket(sym, Side.SELL, price, cid, true);
            }
            api.onApiResult("newStopMarket", true);
            api.onOrderResult("newStopMarket", true, false);   // [V12 R4p Bug3]
            String old = book.promotePendingStop(sym, now);
            nPlace.incrementAndGet();
            if ("MOVE".equals(why)) nMove.incrementAndGet();
            LOG.info("[C3-LIVE-TRAIL] {} {} stop={} cid={} mode={} (cu={} {})", sym, why, price.toPlainString(), cid,
                    qtyMode ? "qty+reduceOnly" : "closePosition", old, c.stopPrice);
            events.event("STOP_PLACED", sym, now, price.doubleValue(), why + " cid=" + cid + (qtyMode ? " qty" : ""));
            int ops = 1;
            if (old != null) ops += cancelReplacedIfConfirmed(sym, cid, resp, old, now);
            return ops;
        } catch (GatewayException e) {
            int code = e.getExchangeCode();
            boolean business = code == CODE_CLOSE_POSITION_EXISTS || code == CODE_WOULD_TRIGGER;
            if (!(e instanceof com.binance.chuyennd.c3live.api.ClientSideRefusal)) {
                api.onApiResult("newStopMarket", business);   // [R4b MINOR-2]
                api.onOrderResult("newStopMarket", business, C3LiveOrderExecutor.ApiObserver.rateLimited(e));   // [V12 R4p Bug3]
            }
            if (code == CODE_CLOSE_POSITION_EXISTS && !qtyMode && allowFallback) {
                closePositionConflictSeen = true;
                nFallbackQty.incrementAndGet();
                book.clearPendingStop(sym, now);
                LOG.warn("[C3-LIVE-TRAIL] {} san tu choi stop closePosition thu 2 (-4130) => dat stop qty+reduceOnly roi huy"
                        + " stop cu (khong khoang trong)", sym);
                return 1 + send(c, price, true, now, why, false);
            }
            if (code == CODE_WOULD_TRIGGER) {
                book.clearPendingStop(sym, now);
                nImmediate.incrementAndGet();
                LOG.warn("[C3-LIVE-TRAIL] {} stop {} se kich ngay (-2021: gia da duoi stop) => dong MARKET reduce-only", sym,
                        price.toPlainString());
                events.event("IMMEDIATE", sym, now, price.doubleValue(), "");
                return 1 + closer.closeCluster(sym, REASON_TRAIL_IMMEDIATE);
            }
            if (e.isDefinitelyNotExecuted()) {
                book.clearPendingStop(sym, now);
                LOG.warn("[C3-LIVE-TRAIL] {} dat stop {} loi {} {} => thu lai nhip sau", sym, cid, e.getKind(), code);
            } else {
                LOG.warn("[C3-LIVE-TRAIL] {} dat stop {} trang thai khong ro ({}) => tra san sau {} ms", sym, cid, e.getKind(),
                        safeRetryMs);
            }
            return 1;
        } catch (RuntimeException e) {
            api.onApiResult("newStopMarket", false);
            LOG.warn("[C3-LIVE-TRAIL] {} dat stop {} loi {} => tra san sau", sym, cid, e.toString());
            return 1;
        }
    }

    /** Stop pending chua ro (timeout/restart): tra san theo clientAlgoId sau cua so an toan. */
    private int resolvePending(LiveBookC3.ClusterView c, long now) {
        String sym = c.symbol;
        if (now - c.pendingStopSentMs < safeRetryMs) return 0;
        Optional<OrderInfo> q;
        try {
            q = gw.queryStop(sym, c.pendingStopCid);
            api.onApiResult("queryStop", true);
        } catch (GatewayException e) {
            if (e.getKind() == ErrorKind.UNKNOWN_ORDER) {
                api.onApiResult("queryStop", true);
                q = Optional.empty();
            } else {
                api.onApiResult("queryStop", false);
                return 1;
            }
        } catch (RuntimeException e) {
            api.onApiResult("queryStop", false);
            return 1;
        }
        if (q.isPresent()) {
            OrderStatus st = q.get().getStatus() == null ? OrderStatus.UNKNOWN : q.get().getStatus();
            if (st == OrderStatus.CANCELED || st == OrderStatus.EXPIRED || st == OrderStatus.REJECTED) {
                book.clearPendingStop(sym, now);
                LOG.warn("[C3-LIVE-TRAIL] {} stop pending {} tren san = {} => bo, dat lai nhip sau", sym, c.pendingStopCid, st);
                return 1;
            }
            String newCid = c.pendingStopCid;
            String old = book.promotePendingStop(sym, now);
            LOG.warn("[C3-LIVE-TRAIL] {} stop pending {} CO tren san ({}) => nhan lam stop active", sym, newCid, st);
            int ops = 1;
            if (old != null) ops += cancelReplacedIfConfirmed(sym, newCid, q.get(), old, now);
            return ops;
        }
        book.clearPendingStop(sym, now);
        LOG.warn("[C3-LIVE-TRAIL] {} stop pending {} KHONG co tren san => bo, dat lai nhip sau", sym, c.pendingStopCid);
        return 1;
    }

    /**
     * [2g MIN-20] Chi huy stop cu (REPLACED) khi stop MOI da xac nhan NEW: response co algoStatus NEW, hoac thay cid moi
     * (chua final) trong openStops — kiem toi da 2 lan cach {@link #CONFIRM_GAP_MS}. Khong xac nhan duoc => GIU CA HAI stop
     * (vo hai: closePosition/reduce-only), WARN; stop cu nam trong orphanStops, nhip sau di qua OwnStopGuard (chi huy khi
     * stop active moi DANG MO tren san, hoac vi the phang).
     */
    private int cancelReplacedIfConfirmed(String sym, String newCid, OrderInfo resp, String old, long now) {
        if (newStopConfirmed(sym, newCid, resp)) return cancelOrphan(sym, old, now, REPLACED);
        nUnconfirmed.incrementAndGet();
        LOG.warn("[C3-LIVE-TRAIL] {} stop moi {} CHUA xac nhan NEW (status={}, khong thay trong openStops sau 2 lan) => GIU ca"
                + " stop cu {}; nhip sau huy qua guard", sym, newCid, resp == null ? null : resp.getStatus(), old);
        return 0;
    }

    static final long CONFIRM_GAP_MS = 1_000L;

    private static void sleepQuiet(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private boolean newStopConfirmed(String sym, String newCid, OrderInfo resp) {
        if (resp != null && resp.getStatus() == OrderStatus.NEW) return true;
        for (int i = 0; i < 2; i++) {
            if (i > 0) sleeper.accept(CONFIRM_GAP_MS);
            try {
                List<OrderInfo> open = gw.openStops(sym);
                api.onApiResult("openStops", true);
                for (OrderInfo o : open) {
                    if (newCid.equals(o.getClientOrderId()) && o.getStatus() == OrderStatus.NEW) return true;
                }
            } catch (RuntimeException e) {
                api.onApiResult("openStops", false);
            }
        }
        return false;
    }

    /** [2e MAJ-3] cach huy: GUARDED = qua OwnStopGuard; REPLACED = stop cu vua bi thay; RETIRED = cum bi go arm (DCA). */
    private static final int GUARDED = 0;
    private static final int REPLACED = 1;
    private static final int RETIRED = 2;

    /** Huy stop cu/mo coi qua OwnStopGuard (diem huy c3s- duy nhat); da het cung coi la xong. */
    private int cancelOrphan(String sym, String cid, long now, int mode) {
        OwnStopGuard.Result r;
        if (mode == REPLACED) {
            r = guard.cancelReplaced(sym, cid, "stop cu bi thay (trailing)");
        } else if (mode == RETIRED) {
            r = guard.cancelRetired(sym, cid, "cum bi go arm (DCA reset nhu so giay)");
        } else {
            r = guard.cancelOwnStopGuarded(sym, cid, "stop mo coi cua cum (trailing)");
        }
        if (r == OwnStopGuard.Result.CANCELLED || r == OwnStopGuard.Result.GONE) {
            book.removeOrphanStop(sym, cid, now);
            if (r == OwnStopGuard.Result.CANCELLED) {
                nCancel.incrementAndGet();
                events.event("STOP_CANCEL", sym, now, 0d, cid);
            }
        } else if (r == OwnStopGuard.Result.CANCEL_ERROR) {
            LOG.warn("[C3-LIVE-TRAIL] {} huy stop {} loi => thu lai nhip sau", sym, cid);
        }
        return 1;
    }

    /**
     * [V12 R4 R6] 1 nhip CHI cho 1 symbol (stop bi san ket thuc => dat lai trong pham vi RateGuard.Urgent cua nguoi goi).
     * prices null => dat lai theo priceSL da persist (gia nhu cu). @return so thao tac san.
     */
    public synchronized int ensureStop(String symbol, Map<String, Float> prices) {
        if (symbol == null || action.get() == KillSwitchEngine.Action.FLATTEN) return 0;
        Optional<LiveBookC3.ClusterView> c = book.cluster(symbol);
        if (!c.isPresent()) return 0;
        try {
            return stepOne(c.get(), prices, clock.getAsLong());
        } catch (Throwable t) {
            LOG.error("[C3-LIVE-TRAIL] loi ensureStop {}: {}", symbol, t.toString());
            return 0;
        }
    }

    /**
     * [V12 R4 R2] MERGED: thay stop closePosition dang co bang stop qty reduceOnly = qty c3 con mo, CUNG gia (dat moi truoc, huy
     * cu sau khi moi xac nhan — khong khoang trong). Khong co stop / da la qty / dang pending => 0.
     */
    public synchronized int replaceStopAsQty(String symbol) {
        Optional<LiveBookC3.ClusterView> co = symbol == null ? Optional.<LiveBookC3.ClusterView>empty() : book.cluster(symbol);
        if (!co.isPresent()) return 0;
        LiveBookC3.ClusterView c = co.get();
        if (c.stopClientAlgoId == null || c.stopQtyMode || c.pendingStopCid != null || !(c.stopPrice > 0d)) return 0;
        BigDecimal px = BigDecimal.valueOf(c.stopPrice);
        SymbolRules r = rules == null ? null : rules.get();
        if (r != null) {
            try {
                BigDecimal rr = r.roundStopPriceForLong(symbol, px);
                if (rr != null && rr.signum() > 0) px = rr;
            } catch (RuntimeException ignore) {
                // giu gia so
            }
        }
        LOG.warn("[C3-LIVE-TRAIL] {} MERGED: thay stop closePosition {} bang stop qty reduceOnly (gia {})", symbol,
                c.stopClientAlgoId, px.toPlainString());
        return send(c, px, true, clock.getAsLong(), "MERGED", false);
    }

    /** [2e MAJ-3] guard huy stop c3s- dung chung (runtime). */
    public synchronized void setStopGuard(OwnStopGuard g) {
        if (g != null) this.guard = g;
    }

    /** X14 dang bat (c3_live: LIVE_TS_MKT_EXT=1). */
    public static boolean tsExtEnabled() {
        return TsMktExt.enabled();
    }

    /** Cum THAT vua dong (bat ky ly do) — log cua X14. */
    public static void tsExtOnClosed(String symbol, long tsFirstLeg, String reason, long now) {
        TsMktExt.onClosed(symbol, tsFirstLeg, reason, now);
    }

    public String stats() {
        return "arm=" + nArm.get() + " place=" + nPlace.get() + " move=" + nMove.get() + " cancel=" + nCancel.get()
                + " timeStop=" + nTimeStop.get() + " defer=" + nDefer.get() + " immediate=" + nImmediate.get()
                + " fallbackQty=" + nFallbackQty.get() + " unconfirmed=" + nUnconfirmed.get();
    }

    public static final class Builder {
        private ExchangeGateway gw;
        private LiveBookC3 book;
        private Supplier<SymbolRules> rules;
        private Closer closer;
        private TrailFn trail;
        private TimeStopDefer defer;
        private ArmHook armHook;
        private Supplier<KillSwitchEngine.Action> action;
        private C3LiveOrderExecutor.ApiObserver api;
        private Consumer<String> alert;
        private LongSupplier clock;
        private float armRate = C3TrailRate.armRate();
        private int timeStopHours = C3TrailRate.timeStopHours();
        private double minMoveFrac = DEFAULT_MIN_MOVE_FRAC;
        private long safeRetryMs = 10_000L;
        private StopMode stopMode = StopMode.CLOSE_POSITION;
        private EventSink events;
        private java.util.function.LongConsumer sleeper;
        private java.util.function.Predicate<String> forceQty;

        public Builder sleeper(java.util.function.LongConsumer v) { sleeper = v; return this; }
        public Builder gateway(ExchangeGateway v) { gw = v; return this; }
        public Builder book(LiveBookC3 v) { book = v; return this; }
        public Builder rules(Supplier<SymbolRules> v) { rules = v; return this; }
        public Builder closer(Closer v) { closer = v; return this; }
        public Builder trail(TrailFn v) { trail = v; return this; }
        public Builder defer(TimeStopDefer v) { defer = v; return this; }
        public Builder armHook(ArmHook v) { armHook = v; return this; }
        public Builder action(Supplier<KillSwitchEngine.Action> v) { action = v; return this; }
        public Builder api(C3LiveOrderExecutor.ApiObserver v) { api = v; return this; }
        public Builder alert(Consumer<String> v) { alert = v; return this; }
        public Builder clock(LongSupplier v) { clock = v; return this; }
        public Builder armRate(float v) { armRate = v; return this; }
        public Builder timeStopHours(int v) { timeStopHours = v; return this; }
        public Builder minMoveFrac(double v) { minMoveFrac = v; return this; }
        public Builder safeRetryMs(long v) { safeRetryMs = v; return this; }
        public Builder stopMode(StopMode v) { stopMode = v; return this; }
        public Builder events(EventSink v) { events = v; return this; }
        /** [V12 R4 R2] symbol bat buoc stop qty reduceOnly = qty c3 (MERGED). */
        public Builder qtyModeFor(java.util.function.Predicate<String> v) { forceQty = v; return this; }

        public TrailingStopManager build() {
            if (gw == null || book == null || closer == null) throw new IllegalStateException("TrailingStopManager thieu thanh phan");
            return new TrailingStopManager(this);
        }
    }
}
