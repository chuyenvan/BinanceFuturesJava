package com.binance.chuyennd.c3live.risk;

import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.OrderStatus;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.exec.C3LiveCids;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.recon.FlatConfirm;
import com.binance.chuyennd.c3live.recon.OwnStopGuard;
import com.binance.chuyennd.ops.KillSwitchEngine;
import com.binance.chuyennd.c3live.rate.RateGuard;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Consumer;
import java.util.function.LongSupplier;
import java.util.function.Supplier;

/**
 * [V12 C8/C6] Dong cum c3_live bang MARKET reduce-only, idempotent (cid {@code c3x-<sym>-<min>-<n>}), chia lo
 * <= {@code maxOrders} lenh / {@code windowMs} (mac dinh 5 / 10 s; lenh con lai sang luot sau), huy stop sau khi dong.
 *
 * <ul>
 *   <li>{@link #step()}: {@code requiredAction()==FLATTEN} => dong TOAN BO cum (bo qua cum con leg mua treo toi khi
 *       giai quyet), Telegram luc bat dau + khi xong. Chan mo moi do latch FLATTEN cua kill-switch.</li>
 *   <li>{@link #closeCluster(String, String)}: dong 1 cum (time-stop / X14 / chu dong — vong 2b goi).</li>
 * </ul>
 * Qty dong = |positionAmt| tren san (nguon su that); khong doc duoc => qty xac nhan trong so. Lenh dong cu chua ro
 * (timeout) => queryOrder truoc; khong co + het cua so an toan => moi gui lai cid moi. Dong xong => huy stop
 * ({@code stopClientAlgoId} + moi stop mo cua symbol) roi xoa cum khoi so.
 */
public final class C3LiveFlattener {

    private static final Logger LOG = LoggerFactory.getLogger(C3LiveFlattener.class);
    public static final int DEFAULT_MAX_ORDERS = 5;
    public static final long DEFAULT_WINDOW_MS = 10_000L;

    private final ExchangeGateway gw;
    private final LiveBookC3 book;
    private final Supplier<KillSwitchEngine.Action> action;
    private final Consumer<String> alert;
    private final C3LiveOrderExecutor.ApiObserver api;
    private final LongSupplier clock;
    private final int maxOrders;
    private final long windowMs;
    private final long safeRetryMs;
    private final ArrayDeque<Long> sends = new ArrayDeque<>();
    private final FlatConfirm flat;
    private OwnStopGuard guard;
    private boolean announced;
    private boolean doneAnnounced;
    private long nCloseOrders;

    public C3LiveFlattener(ExchangeGateway gw, LiveBookC3 book, Supplier<KillSwitchEngine.Action> action,
                           Consumer<String> alert, C3LiveOrderExecutor.ApiObserver api, LongSupplier clock, int maxOrders,
                           long windowMs, long safeRetryMs) {
        this(gw, book, action, alert, api, clock, maxOrders, windowMs, safeRetryMs, null);
    }

    /** [2c] {@code flat} dung chung voi Reconciler (null => tao rieng, khoang cach 5 s). */
    public C3LiveFlattener(ExchangeGateway gw, LiveBookC3 book, Supplier<KillSwitchEngine.Action> action,
                           Consumer<String> alert, C3LiveOrderExecutor.ApiObserver api, LongSupplier clock, int maxOrders,
                           long windowMs, long safeRetryMs, FlatConfirm flat) {
        this.flat = flat != null ? flat
                : new FlatConfirm(gw, api, alert, FlatConfirm.DEFAULT_MIN_GAP_MS, FlatConfirm.DEFAULT_MIN_READS);
        this.gw = gw;
        this.book = book;
        this.action = action;
        this.alert = alert == null ? m -> { } : alert;
        this.api = api == null ? (a, ok) -> { } : api;
        this.clock = clock;
        this.maxOrders = Math.max(1, maxOrders);
        this.windowMs = Math.max(1L, windowMs);
        this.safeRetryMs = Math.max(0L, safeRetryMs);
        this.guard = new OwnStopGuard(gw, book, this.api, this.alert, null, clock);
    }

    /** Mot luot FLATTEN. @return so lenh dong da gui trong luot. */
    public synchronized int step() {
        long now = clock.getAsLong();
        KillSwitchEngine.Action a = action.get();
        if (a != KillSwitchEngine.Action.FLATTEN) {
            announced = false;
            doneAnnounced = false;
            return 0;
        }
        try (RateGuard.Lane lane = RateGuard.emergencyLane()) {   // [3f] FLATTEN kill-switch: khong bao gio bi rate guard rieng chan
            return flattenStep(now);
        }
    }

    private int flattenStep(long now) {
        if (!announced) {
            announced = true;
            doneAnnounced = false;
            String m = "[C3-LIVE] FLATTEN: dong " + book.openCount() + " cum reduce-only (<= " + maxOrders + " lenh/"
                    + windowMs / 1000 + "s), huy stop, DUNG mo moi";
            LOG.warn("{}", m);
            fire(m);
        }
        if (book.openCount() == 0) {
            if (!doneAnnounced) {
                doneAnnounced = true;
                String m = "[C3-LIVE] FLATTEN xong: 0 cum mo (lenh dong da gui=" + nCloseOrders + ")";
                LOG.warn("{}", m);
                fire(m);
            }
            return 0;
        }
        Map<String, BigDecimal> pos = positions();
        int sent = 0;
        for (LiveBookC3.ClusterView c : book.clusters()) {
            if (c.hasUnresolved) continue;
            if (pacerFull(now)) break;
            sent += closeOne(c, pos, "FLATTEN", now);
        }
        return sent;
    }

    /** Dong 1 cum (time-stop / X14 / chu dong). @return so lenh gui (0/1). */
    public synchronized int closeCluster(String symbol, String reason) {
        Optional<LiveBookC3.ClusterView> c = book.cluster(symbol);
        if (!c.isPresent() || c.get().hasUnresolved) return 0;
        long now = clock.getAsLong();
        if (pacerFull(now)) return 0;
        try (RateGuard.Lane lane = RateGuard.emergencyLane()) {   // [3f] dong cum: lan khan cap
            return closeOne(c.get(), positions(), reason, now);
        }
    }

    private int closeOne(LiveBookC3.ClusterView c, Map<String, BigDecimal> pos, String reason, long now) {
        String sym = c.symbol;
        if (c.closeCid != null) {
            int st = checkPrevClose(c, pos, now);
            if (st <= 0) return 0;   // dang cho / da xu ly
        }
        BigDecimal qty;
        if (pos != null) {
            BigDecimal p = pos.get(sym);
            qty = p == null ? BigDecimal.ZERO : p.max(BigDecimal.ZERO);
            // [3f §ADD-4] KHONG bao gio dong qua phan cua c3 (tai khoan chinh: cung symbol co the co vi the khac)
            BigDecimal mine = c.confirmedQty.subtract(c.exitQty == null ? BigDecimal.ZERO : c.exitQty).max(BigDecimal.ZERO);
            qty = qty.min(mine);   // [3g MIN-6] phan c3 = 0 => KHONG dong gi (khong bao gio lay confirmedQty)
        } else {
            qty = c.confirmedQty;
        }
        if (qty.signum() <= 0) {
            // [2c MAJ-2] vang/0 trong positionRisk CHUA phai bang chung phang => chi xoa cum + huy stop khi FlatConfirm
            // xac nhan (2 lan doc cach >= 5 s + 0 lenh mo); chua du => giu cum + stop, thu lai luot sau
            if (flat.observeFlat(sym, now, "close " + reason)) finalizeClosed(sym, reason + ":flat_on_exchange", now);
            return 0;
        }
        flat.clear(sym);
        int attempt = c.closeAttempts + 1;
        String cid = C3LiveCids.close(sym, Math.floorDiv(now, 60_000L), attempt);
        book.markClosing(sym, cid, reason, now);   // persist TRUOC khi gui
        sends.addLast(now);
        nCloseOrders++;
        try {
            OrderInfo o = gw.newMarketOrder(sym, Side.SELL, qty, cid, true);
            api.onApiResult("newMarketOrder", true);
            api.onOrderResult("newMarketOrder", true, false);   // [V12 R4p Bug3]
            onCloseResult(sym, o, qty, reason, now);
        } catch (GatewayException e) {
            if (!(e instanceof com.binance.chuyennd.c3live.api.ClientSideRefusal)) {
                api.onApiResult("newMarketOrder", false);   // [R4b MINOR-2]
                api.onOrderResult("newMarketOrder", false, C3LiveOrderExecutor.ApiObserver.rateLimited(e));   // [V12 R4p Bug3]
            }
            if (e.isDefinitelyNotExecuted()) {
                book.clearCloseCid(sym, now);
                LOG.warn("[C3-LIVE-CLOSE] {} {} khong khop ({} {}) => thu lai luot sau", sym, cid, e.getKind(),
                        e.getExchangeCode());
            } else {
                LOG.warn("[C3-LIVE-CLOSE] {} {} trang thai khong ro ({}) => tra san luot sau", sym, cid, e.getKind());
            }
        } catch (RuntimeException e) {
            api.onApiResult("newMarketOrder", false);
            LOG.warn("[C3-LIVE-CLOSE] {} {} loi {} => tra san luot sau", sym, cid, e.toString());
        }
        return 1;
    }

    /** @return 1 = duoc phep gui lenh dong moi; 0 = cho / da xu ly xong. */
    private int checkPrevClose(LiveBookC3.ClusterView c, Map<String, BigDecimal> pos, long now) {
        String sym = c.symbol;
        Optional<OrderInfo> q;
        try {
            q = gw.queryOrder(sym, c.closeCid);
            api.onApiResult("queryOrder", true);
        } catch (GatewayException e) {
            if (e.getKind() != ErrorKind.UNKNOWN_ORDER) {
                api.onApiResult("queryOrder", false);
                return 0;
            }
            api.onApiResult("queryOrder", true);
            q = Optional.empty();
        } catch (RuntimeException e) {
            api.onApiResult("queryOrder", false);
            return 0;
        }
        if (q.isPresent()) {
            OrderInfo o = q.get();
            if (!o.getStatus().isFinal()) return 0;
            BigDecimal exq = o.getExecutedQty();
            if (o.getStatus() == OrderStatus.FILLED && exq != null && exq.compareTo(c.confirmedQty) >= 0) {
                finalizeClosed(sym, c.closeReason, now);   // bang chung (ii): lenh dong cua bot khop het
                return 0;
            }
            BigDecimal rest = pos == null ? null : pos.getOrDefault(sym, BigDecimal.ZERO);
            if (rest != null && rest.signum() <= 0) {
                if (flat.observeFlat(sym, now, "close-check " + c.closeReason)) finalizeClosed(sym, c.closeReason, now);
                return 0;   // chua du bang chung: giu cum + stop + closeCid, luot sau tra lai
            }
            flat.clear(sym);
            book.clearCloseCid(sym, now);   // khop mot phan / huy => gui phan con lai
            return pos == null ? 0 : 1;
        }
        if (now - c.closeSentMs < safeRetryMs) return 0;
        book.clearCloseCid(sym, now);
        return 1;
    }

    private void onCloseResult(String sym, OrderInfo o, BigDecimal qty, String reason, long now) {
        OrderStatus st = o.getStatus() == null ? OrderStatus.UNKNOWN : o.getStatus();
        BigDecimal ex = o.getExecutedQty() == null ? BigDecimal.ZERO : o.getExecutedQty();
        if (st == OrderStatus.FILLED && ex.compareTo(qty) >= 0) {
            finalizeClosed(sym, reason, now);
        } else if (st.isFinal()) {
            book.clearCloseCid(sym, now);
        }
        // NEW / PARTIALLY_FILLED: giu closeCid, luot sau tra
    }

    /** Cum da phang tren san: huy stop (cid trong so + moi stop mo cua symbol) roi xoa cum. */
    private void finalizeClosed(String sym, String reason, long now) {
        Optional<LiveBookC3.ClusterView> c = book.cluster(sym);
        java.util.Set<String> cids = new java.util.LinkedHashSet<>();
        if (c.isPresent()) {
            if (c.get().stopClientAlgoId != null) cids.add(c.get().stopClientAlgoId);
            if (c.get().pendingStopCid != null) cids.add(c.get().pendingStopCid);
            cids.addAll(c.get().orphanStops);
        }
        try {
            List<OrderInfo> open = gw.openStops(sym);
            api.onApiResult("openStops", true);
            for (OrderInfo s : open) {
                if (OwnStopGuard.isOwn(s.getClientOrderId())) cids.add(s.getClientOrderId());   // [2e] KHONG dung stop ngoai bot
            }
        } catch (RuntimeException e) {
            api.onApiResult("openStops", false);
            LOG.warn("[C3-LIVE-CLOSE] {} khong doc duoc stop mo ({}) => reconcile se don stop mo coi", sym, e.toString());
        }
        // [2e MAJ-3] xoa cum TRUOC roi huy stop c3s- qua guard (chi khi positionRisk + account deu phang)
        book.removeCluster(sym, reason, now);
        int kept = 0;
        for (String id : cids) {
            OwnStopGuard.Result gr = guard.cancelOwnStopGuarded(sym, id, "dong cum (" + reason + ")");
            if (gr == OwnStopGuard.Result.KEPT_POSITION || gr == OwnStopGuard.Result.KEPT_READ_ERROR) kept++;
        }
        LOG.warn("[C3-LIVE-CLOSE] {} DA DONG ({}); stop c3s-: {} xu ly, {} GIU (vi the san chua phang / doc loi)", sym, reason,
                cids.size(), kept);
    }

    /** [2e MAJ-3] guard huy stop c3s- dung chung (runtime). */
    public synchronized void setStopGuard(OwnStopGuard g) {
        if (g != null) this.guard = g;
    }

    private Map<String, BigDecimal> positions() {
        try {
            List<PositionInfo> ps = gw.positions();
            api.onApiResult("positions", true);
            Map<String, BigDecimal> m = new HashMap<>();
            for (PositionInfo p : ps) {
                if (p.getPositionAmt() == null) continue;
                m.merge(p.getSymbol(), p.getPositionAmt(), BigDecimal::add);
            }
            return m;
        } catch (RuntimeException e) {
            api.onApiResult("positions", false);
            LOG.warn("[C3-LIVE-CLOSE] positions() loi {} => dung qty trong so", e.toString());
            return null;
        }
    }

    private boolean pacerFull(long now) {
        while (!sends.isEmpty() && sends.peekFirst() <= now - windowMs) sends.pollFirst();
        return sends.size() >= maxOrders;
    }

    /** Cho test: so lenh trong cua so hien tai. */
    synchronized int sendsInWindow(long now) {
        pacerFull(now);
        return sends.size();
    }

    private void fire(String m) {
        try {
            alert.accept(m);
        } catch (Throwable ignore) {
            // alert khong duoc lam hong luong dong
        }
    }
}
