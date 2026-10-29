package com.binance.chuyennd.c3live.exec;

import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.OrderStatus;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.api.Ticker24h;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executor;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.LongSupplier;

/**
 * [V12 C3] Gui leg MUA c3_live idempotent — goi gateway TRUC TIEP (khong rpush Redis), tren executor rieng.
 *
 * <p>Quy tac:
 * <ol>
 *   <li>{@link LiveBookC3#markSending} (persist) TRUOC moi lan gui => restart giua chung thi biet "co the da gui".</li>
 *   <li>Loi chac chan KHONG khop ({@link GatewayException#isDefinitelyNotExecuted()}) => huy giu cho.</li>
 *   <li>Timeout / trang thai khong ro => UNKNOWN => cho het cua so an toan ({@code safeRetryMs} >= recvWindow: request
 *       cu den san tre hon se bi san tu choi) roi {@code queryOrder(cid)}: co => ap ket qua; KHONG co => moi duoc gui
 *       lai CUNG cid (toi da {@code maxAttempts}); tra loi => giu UNKNOWN (khong bao gio gui lai mu), luong dinh ky tra lai.</li>
 *   <li>Sau restart: leg PENDING (chua tung gui) => huy; SENDING/UNKNOWN => tra san; KHONG BAO GIO gui lai (quyet dinh cu
 *       da het han).</li>
 *   <li>[3j R1/R2/R4] Ket qua san co {@code executedQty > 0} => LUON ghi qty vao so (gia that neu co; khong co gia thi
 *       giai theo thu tu stream/queryOrder/userTrades, het ngan sach 3 s => ghi gia TAM = mark, co {@code pxProvisional}).
 *       KHONG BAO GIO suy ra "khong khop" tu gia thieu/0. {@code FILLED} ma executedQty = 0 => UNKNOWN + tra lai san;
 *       chi huy giu cho khi san noi CANCELED/EXPIRED/REJECTED voi executedQty = 0.</li>
 * </ol>
 * Fill that => {@link FillObserver#onFill} (C2 truot co dau, ref = close nen 1m quyet dinh). Moi call REST =>
 * {@link ApiObserver#onApiResult} (C3 dem loi lien tiep).
 */
public final class C3LiveOrderExecutor {

    private static final Logger LOG = LoggerFactory.getLogger(C3LiveOrderExecutor.class);

    public static final long DEFAULT_SAFE_RETRY_MS = 10_000L;
    public static final int DEFAULT_MAX_ATTEMPTS = 3;
    /** [3j R2] nhip toi thieu giua 2 lan thu hieu chinh gia TAM (0 call khi khong co leg provisional). */
    public static final long PROVISIONAL_RECHECK_MS = 5_000L;

    public enum Resolve { FOUND, ABSENT, ERROR, WAIT }

    public interface ApiObserver {
        void onApiResult(String api, boolean ok);
    }

    public interface FillObserver {
        void onFill(String symbol, boolean isBuy, double fillPx, double refPx);
    }

    /** [3j] su kien gia de ghi nhat ky (canary journal / log production): PX_RESOLVED | PX_PROVISIONAL | PX_CORRECTED. */
    public interface PriceObserver {
        void onPrice(String type, String symbol, String cid, double px, String source);
    }

    public interface Sleeper {
        void sleepMs(long ms) throws InterruptedException;
    }

    private final ExchangeGateway gw;
    private final LiveBookC3 book;
    private final ApiObserver api;
    private final FillObserver fill;
    private final LongSupplier clock;
    private final Sleeper sleeper;
    private final long safeRetryMs;
    private final int maxAttempts;
    private final Executor exec;
    private final Set<String> inFlight = ConcurrentHashMap.newKeySet();
    private final AtomicLong nSend = new AtomicLong();
    private final AtomicLong nConfirmed = new AtomicLong();
    private final AtomicLong nCancelled = new AtomicLong();
    private final AtomicLong nUnknown = new AtomicLong();
    private final AtomicLong nResend = new AtomicLong();
    private final AtomicLong nProvisional = new AtomicLong();
    private volatile FillPriceResolver prices;
    private volatile PriceObserver priceObs = (t, s, c, p, src) -> { };
    private volatile long lastProvisionalCheckMs = Long.MIN_VALUE / 2;

    public C3LiveOrderExecutor(ExchangeGateway gw, LiveBookC3 book, ApiObserver api, FillObserver fill, LongSupplier clock,
                               Sleeper sleeper, long safeRetryMs, int maxAttempts, Executor exec) {
        this.gw = gw;
        this.book = book;
        this.api = api == null ? (a, ok) -> { } : api;
        this.fill = fill == null ? (s, b, f, r) -> { } : fill;
        this.clock = clock;
        this.sleeper = sleeper;
        this.safeRetryMs = Math.max(0L, safeRetryMs);
        this.maxAttempts = Math.max(1, maxAttempts);
        this.exec = exec;
        this.prices = new FillPriceResolver(clock, sleeper, this.api);
    }

    /**
     * [3j] dung CHUNG 1 FillPriceResolver voi FillAccounting (user stream) — bat buoc trong production/canary de nguon (a)
     * stream co tac dung. Goi truoc khi su dung; null = giu resolver rieng (chi con (b)/(c)).
     */
    public void setPriceResolver(FillPriceResolver r) {
        if (r != null) this.prices = r;
    }

    public FillPriceResolver priceResolver() {
        return prices;
    }

    public void setPriceObserver(PriceObserver o) {
        this.priceObs = o == null ? (t, s, c, p, src) -> { } : o;
    }

    /** Dua leg da giu cho (PENDING) vao luong gui. Khong chan luong goi. */
    public void submit(String cid) {
        inFlight.add(cid);
        try {
            exec.execute(() -> {
                try {
                    place(cid);
                } catch (Throwable t) {
                    LOG.error("[C3-LIVE-EXEC] loi khong mong doi cid={}: {}", cid, t.toString());
                } finally {
                    inFlight.remove(cid);
                }
            });
        } catch (RejectedExecutionException e) {
            inFlight.remove(cid);
            book.cancel(cid, "executor_rejected", clock.getAsLong());
            LOG.error("[C3-LIVE-EXEC] executor tu choi cid={} => huy giu cho", cid);
        }
    }

    public boolean isInFlight(String cid) {
        return inFlight.contains(cid);
    }

    void place(String cid) {
        Optional<LiveBookC3.LegView> lv0 = book.leg(cid);
        if (!lv0.isPresent() || lv0.get().state != LiveBookC3.LegState.PENDING) return;
        String sym = lv0.get().symbol;
        BigDecimal qty = lv0.get().reqQty;
        while (true) {
            if (!book.markSending(cid, clock.getAsLong())) return;
            if (!book.healthy()) {
                // khong persist duoc SENDING => KHONG gui (restart se coi la chua gui)
                book.cancel(cid, "persist_fail_before_send", clock.getAsLong());
                nCancelled.incrementAndGet();
                LOG.error("[C3-LIVE-EXEC] {} {} so khong ghi duoc truoc khi gui => KHONG gui, huy giu cho", sym, cid);
                return;
            }
            nSend.incrementAndGet();
            try {
                OrderInfo o = gw.newMarketOrder(sym, Side.BUY, qty, cid, false);
                api.onApiResult("newMarketOrder", true);
                apply(cid, o, true, true);
                return;
            } catch (GatewayException e) {
                api.onApiResult("newMarketOrder", false);
                if (e.isDefinitelyNotExecuted()) {
                    book.cancel(cid, "not_executed:" + e.getKind() + ":" + e.getExchangeCode(), clock.getAsLong());
                    nCancelled.incrementAndGet();
                    LOG.warn("[C3-LIVE-EXEC] {} {} KHONG khop ({} {}) => huy giu cho", sym, cid, e.getKind(),
                            e.getExchangeCode());
                    return;
                }
                book.markUnknown(cid, "send:" + e.getKind(), clock.getAsLong());
            } catch (RuntimeException e) {
                api.onApiResult("newMarketOrder", false);
                book.markUnknown(cid, "send:" + e.getClass().getSimpleName(), clock.getAsLong());
            }
            nUnknown.incrementAndGet();
            Resolve r = resolve(cid, true);
            if (r != Resolve.ABSENT) return;
            Optional<LiveBookC3.LegView> cur = book.leg(cid);
            if (!cur.isPresent() || !cur.get().state.unresolved()) return;
            if (cur.get().attempts >= maxAttempts) {
                book.cancel(cid, "absent_after_" + cur.get().attempts, clock.getAsLong());
                nCancelled.incrementAndGet();
                LOG.warn("[C3-LIVE-EXEC] {} {} khong co tren san sau {} lan gui => huy giu cho", sym, cid,
                        cur.get().attempts);
                return;
            }
            nResend.incrementAndGet();
            LOG.warn("[C3-LIVE-EXEC] {} {} queryOrder xac nhan KHONG co sau cua so an toan => gui lai CUNG cid (lan {})",
                    sym, cid, cur.get().attempts + 1);
        }
    }

    /**
     * Tra san theo cid. {@code mayWait}: cho het cua so an toan; false => chua het cua so thi tra WAIT (khong chan).
     */
    Resolve resolve(String cid, boolean mayWait) {
        Optional<LiveBookC3.LegView> lv = book.leg(cid);
        if (!lv.isPresent() || !lv.get().state.unresolved()) return Resolve.FOUND;
        long wait = lv.get().lastSendMs + safeRetryMs - clock.getAsLong();
        if (wait > 0) {
            if (!mayWait) return Resolve.WAIT;
            try {
                sleeper.sleepMs(wait);
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                return Resolve.ERROR;
            }
        }
        try {
            Optional<OrderInfo> q = gw.queryOrder(lv.get().symbol, cid);
            api.onApiResult("queryOrder", true);
            if (q.isPresent()) {
                // [3j] 1 lan doc da xong: KHONG mo them ngan sach giai gia (stream/query sau se bo sung), khong tra lai san.
                apply(cid, q.get(), false, false);
                return Resolve.FOUND;
            }
            return Resolve.ABSENT;
        } catch (GatewayException e) {
            if (e.getKind() == ErrorKind.UNKNOWN_ORDER) {
                api.onApiResult("queryOrder", true);
                return Resolve.ABSENT;
            }
            api.onApiResult("queryOrder", false);
            book.markUnknown(cid, "query:" + e.getKind(), clock.getAsLong());
            return Resolve.ERROR;
        } catch (RuntimeException e) {
            api.onApiResult("queryOrder", false);
            return Resolve.ERROR;
        }
    }

    void apply(String cid, OrderInfo o) {
        apply(cid, o, true, true);
    }

    /**
     * Ap ket qua san vao so.
     *
     * @param resolvePrice [3j R2] duoc phep giai gia (stream/query/userTrades, <= 3 s) khi executedQty > 0 ma thieu avgPrice
     * @param requery      [3j R4] duoc phep tra san 1 lan khi FILLED/khong chac chan ma executedQty = 0
     */
    private void apply(String cid, OrderInfo o, boolean resolvePrice, boolean requery) {
        Optional<LiveBookC3.LegView> lv = book.leg(cid);
        if (!lv.isPresent()) return;
        long now = clock.getAsLong();
        OrderStatus st = o.getStatus() == null ? OrderStatus.UNKNOWN : o.getStatus();
        BigDecimal ex = o.getExecutedQty() == null ? BigDecimal.ZERO : o.getExecutedQty();
        BigDecimal avg = o.getAvgPrice();
        if (st == OrderStatus.FILLED || (st.isFinal() && ex.signum() > 0)) {
            if (ex.signum() <= 0) {
                // [3j R4] FILLED ma executedQty = 0: KHONG duoc huy giu cho (co the san bao nham / doc-sau-ghi tre).
                book.markUnknown(cid, "filled_exec0", now);
                LOG.warn("[C3-LIVE-EXEC] {} {} {} nhung executedQty=0 => UNKNOWN, tra lai san (KHONG huy)", lv.get().symbol, cid, st);
                requeryIfPossible(cid, lv.get().symbol, requery);
                return;
            }
            double px = avg == null ? 0d : avg.doubleValue();
            BigDecimal qty = ex;
            if (px <= 0d && !resolvePrice) {
                // [3j R2(a)] da doc 1 lan qua queryOrder: van uu tien gia tu stream neu da co (0 call REST)
                FillPriceResolver.Source cached = prices.cached(cid, o.getOrderId());
                if (cached != FillPriceResolver.Source.NONE) {
                    px = prices.cachedPx(cid, o.getOrderId());
                    priceObs.onPrice("PX_RESOLVED", lv.get().symbol, cid, px, cached.name());
                }
            }
            if (px <= 0d && resolvePrice) {
                FillPriceResolver.Resolved r = prices.resolve(gw, lv.get().symbol, cid, o.getOrderId());
                if (r.qty != null && r.qty.signum() > qty.signum()) qty = r.qty;
                if (r.hasPrice()) {
                    px = r.px;
                    priceObs.onPrice("PX_RESOLVED", lv.get().symbol, cid, px, r.source.name());
                    LOG.info("[C3-LIVE-EXEC] {} {} ACK thieu avgPrice => gia {} tu {} sau {} ms", lv.get().symbol, cid, px,
                            r.source, r.ms);
                }
            }
            if (px <= 0d) {
                // [3j R2] khong co gia that trong ngan sach => ghi qty voi gia TAM = mark (R1: qty KHONG duoc mat).
                double prov = markPrice(lv.get().symbol, lv.get().refPx);
                if (prov > 0d && book.confirmProvisional(cid, qty, prov, o.getOrderId(), clock.getAsLong())) {
                    nConfirmed.incrementAndGet();
                    nProvisional.incrementAndGet();
                    LOG.warn("[C3-LIVE-EXEC] {} {} PX_PROVISIONAL qty={} gia tam={} (mark; cho gia that)", lv.get().symbol, cid,
                            qty.toPlainString(), prov);
                    priceObs.onPrice("PX_PROVISIONAL", lv.get().symbol, cid, prov, "MARK");
                } else if (prov <= 0d) {
                    book.markUnknown(cid, "no_price", clock.getAsLong());
                    LOG.error("[C3-LIVE-EXEC] {} {} executedQty={} nhung KHONG co ca gia tam => giu UNKNOWN (R1: khong huy)",
                            lv.get().symbol, cid, qty.toPlainString());
                }
                return;
            }
            if (book.confirm(cid, qty, px, o.getOrderId(), clock.getAsLong())) {
                nConfirmed.incrementAndGet();
                LOG.info("[C3-LIVE-EXEC] FILL {} {} qty={} avg={} ref={} slip={}", lv.get().symbol, cid, qty.toPlainString(),
                        px, lv.get().refPx, lv.get().refPx > 0 ? String.format("%.5f", px / lv.get().refPx - 1d) : "NA");
                fill.onFill(lv.get().symbol, true, px, lv.get().refPx);
            } else if (book.correctPrice(cid, px, clock.getAsLong())) {
                // leg da duoc stream xac nhan TRUOC (CONFIRMED) voi gia tam => hieu chinh lai bang gia that
                LOG.info("[C3-LIVE-EXEC] {} {} PX_CORRECTED -> {} (leg da CONFIRMED)", lv.get().symbol, cid, px);
                priceObs.onPrice("PX_CORRECTED", lv.get().symbol, cid, px, "EXEC");
            }
            return;
        }
        if (st == OrderStatus.CANCELED || st == OrderStatus.REJECTED || st == OrderStatus.EXPIRED
                || st == OrderStatus.EXPIRED_IN_MATCH) {
            if (ex.signum() <= 0) {
                if (book.cancel(cid, "final_" + st, now)) nCancelled.incrementAndGet();
            } else {
                // co mot phan da khop => khong huy; ghi nhu FILLED (xu ly o nhanh tren o lan doc sau)
                book.markUnknown(cid, "final_" + st + "_exec_gt0", now);
                LOG.warn("[C3-LIVE-EXEC] {} {} {} nhung executedQty={} => UNKNOWN, tra lai san", lv.get().symbol, cid, st,
                        ex.toPlainString());
                requeryIfPossible(cid, lv.get().symbol, requery);
            }
            return;
        }
        if (st.isFinal()) {
            // TRIGGERED/FINISHED (trang thai algo) hoac khong xac dinh: khong ket luan da huy
            book.markUnknown(cid, "final_unknown_" + st, now);
            LOG.warn("[C3-LIVE-EXEC] {} {} trang thai {} khong ket luan => UNKNOWN", lv.get().symbol, cid, st);
            requeryIfPossible(cid, lv.get().symbol, requery);
            return;
        }
        book.noteOpen(cid, o.getOrderId(), now);
    }

    /** [3j R4] tra san 1 lan (khong ngu) khi trang thai/executedQty khong ket luan duoc. */
    private void requeryIfPossible(String cid, String symbol, boolean requery) {
        if (!requery) return;
        try {
            Optional<OrderInfo> q = gw.queryOrder(symbol, cid);
            api.onApiResult("queryOrder", true);
            if (q.isPresent()) {
                LOG.warn("[C3-LIVE-EXEC] {} {} tra lai san sau trang thai khong ro: status={} execQty={}", symbol, cid,
                        q.get().getStatus(), q.get().getExecutedQty());
                apply(cid, q.get(), false, false);
            }
        } catch (GatewayException e) {
            api.onApiResult("queryOrder", false);
        } catch (RuntimeException e) {
            api.onApiResult("queryOrder", false);
        }
    }

    /**
     * [3j R2] Hieu chinh gia TAM cua cac leg da CONFIRMED: stream (cache) truoc, roi queryOrder, roi userTrades.
     * Throttle {@link #PROVISIONAL_RECHECK_MS}; khong co leg provisional => 0 call.
     *
     * @return so leg duoc sua trong lan nay
     */
    public int correctProvisional() {
        List<LiveBookC3.LegView> prov = book.provisionalLegs();
        if (prov.isEmpty()) return 0;
        long now = clock.getAsLong();
        if (now - lastProvisionalCheckMs < PROVISIONAL_RECHECK_MS) return 0;
        lastProvisionalCheckMs = now;
        int n = 0;
        for (LiveBookC3.LegView lv : prov) {
            FillPriceResolver.Resolved r = prices.resolve(gw, lv.symbol, lv.cid, lv.orderId, 0L);
            if (!r.hasPrice()) continue;
            if (book.correctPrice(lv.cid, r.px, clock.getAsLong())) {
                n++;
                LOG.info("[C3-LIVE-EXEC] {} {} PX_CORRECTED {} -> {} (tu {})", lv.symbol, lv.cid, lv.avgPx, r.px, r.source);
                priceObs.onPrice("PX_CORRECTED", lv.symbol, lv.cid, r.px, r.source.name());
            }
        }
        return n;
    }

    /** [3j R2] gia danh dau hien tai (positionRisk mark; khong co vi the => gia khop cuoi); 0 = khong doc duoc. */
    private double markPrice(String sym, double refPx) {
        try {
            for (PositionInfo p : gw.positions()) {
                if (sym.equals(p.getSymbol()) && p.getMarkPrice() != null && p.getMarkPrice().signum() > 0) {
                    return p.getMarkPrice().doubleValue();
                }
            }
        } catch (RuntimeException e) {
            LOG.warn("[3j] {} khong doc duoc mark tu positions: {}", sym, e.toString());
        }
        try {
            for (Ticker24h t : gw.tickers24h(sym)) {
                if (sym.equals(t.getSymbol()) && t.getLastPrice() != null && t.getLastPrice().signum() > 0) {
                    return t.getLastPrice().doubleValue();
                }
            }
        } catch (RuntimeException e) {
            LOG.warn("[3j] {} khong doc duoc gia cuoi (tickers24h): {}", sym, e.toString());
        }
        if (refPx > 0d) {
            LOG.warn("[3j] {} khong doc duoc gia thi truong => gia TAM = ref {}", sym, refPx);
            return refPx;
        }
        return 0d;
    }

    /**
     * Giai quyet leg treo (khong gui lai). {@code startup=true} (sau restart): leg PENDING = chua tung gui => huy.
     * Leg SENDING/UNKNOWN khong con trong luong gui: het cua so an toan thi tra san; KHONG co => huy; loi => giu.
     *
     * @return so leg con treo sau luot
     */
    public int resolveUnresolved(boolean startup) {
        List<LiveBookC3.LegView> legs = book.unresolvedLegs();
        for (LiveBookC3.LegView lv : legs) {
            if (inFlight.contains(lv.cid)) continue;
            long now = clock.getAsLong();
            if (lv.state == LiveBookC3.LegState.PENDING) {
                if (startup || now - lv.tsCreated > 2 * safeRetryMs) {
                    book.cancel(lv.cid, startup ? "restart_unsent" : "stale_unsent", now);
                    nCancelled.incrementAndGet();
                    LOG.warn("[C3-LIVE-EXEC] {} {} PENDING chua tung gui ({}) => huy giu cho", lv.symbol, lv.cid,
                            startup ? "restart" : "stale");
                }
                continue;
            }
            Resolve r = resolve(lv.cid, false);
            if (r == Resolve.ABSENT) {
                book.cancel(lv.cid, startup ? "restart_absent" : "stale_absent", clock.getAsLong());
                nCancelled.incrementAndGet();
                LOG.warn("[C3-LIVE-EXEC] {} {} {} khong co tren san => huy giu cho (khong gui lai)", lv.symbol, lv.cid,
                        lv.state);
            }
        }
        correctProvisional();
        return book.unresolvedLegs().size();
    }

    public String stats() {
        return "send=" + nSend.get() + " confirmed=" + nConfirmed.get() + " cancelled=" + nCancelled.get() + " unknown="
                + nUnknown.get() + " resend=" + nResend.get() + " provisional=" + nProvisional.get() + " inflight="
                + inFlight.size();
    }
}
