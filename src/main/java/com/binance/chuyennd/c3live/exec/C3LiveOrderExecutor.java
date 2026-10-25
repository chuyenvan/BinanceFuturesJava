package com.binance.chuyennd.c3live.exec;

import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.OrderStatus;
import com.binance.chuyennd.c3live.api.Side;
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
 * </ol>
 * Fill that => {@link FillObserver#onFill} (C2 truot co dau, ref = close nen 1m quyet dinh). Moi call REST =>
 * {@link ApiObserver#onApiResult} (C3 dem loi lien tiep).
 */
public final class C3LiveOrderExecutor {

    private static final Logger LOG = LoggerFactory.getLogger(C3LiveOrderExecutor.class);

    public static final long DEFAULT_SAFE_RETRY_MS = 10_000L;
    public static final int DEFAULT_MAX_ATTEMPTS = 3;

    public enum Resolve { FOUND, ABSENT, ERROR, WAIT }

    public interface ApiObserver {
        void onApiResult(String api, boolean ok);
    }

    public interface FillObserver {
        void onFill(String symbol, boolean isBuy, double fillPx, double refPx);
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
                apply(cid, o);
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
                apply(cid, q.get());
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
        Optional<LiveBookC3.LegView> lv = book.leg(cid);
        if (!lv.isPresent()) return;
        long now = clock.getAsLong();
        OrderStatus st = o.getStatus() == null ? OrderStatus.UNKNOWN : o.getStatus();
        BigDecimal ex = o.getExecutedQty() == null ? BigDecimal.ZERO : o.getExecutedQty();
        BigDecimal avg = o.getAvgPrice();
        if (st == OrderStatus.FILLED || (st.isFinal() && ex.signum() > 0)) {
            double px = avg == null ? 0d : avg.doubleValue();
            if (book.confirm(cid, ex, px, o.getOrderId(), now)) {
                nConfirmed.incrementAndGet();
                LOG.info("[C3-LIVE-EXEC] FILL {} {} qty={} avg={} ref={} slip={}", lv.get().symbol, cid, ex.toPlainString(),
                        px, lv.get().refPx, lv.get().refPx > 0 ? String.format("%.5f", px / lv.get().refPx - 1d) : "NA");
                if (px > 0d) fill.onFill(lv.get().symbol, true, px, lv.get().refPx);
            }
        } else if (st.isFinal()) {
            if (book.cancel(cid, "final_" + st, now)) nCancelled.incrementAndGet();
        } else {
            book.noteOpen(cid, o.getOrderId(), now);
        }
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
        return book.unresolvedLegs().size();
    }

    public String stats() {
        return "send=" + nSend.get() + " confirmed=" + nConfirmed.get() + " cancelled=" + nCancelled.get() + " unknown="
                + nUnknown.get() + " resend=" + nResend.get() + " inflight=" + inFlight.size();
    }
}
