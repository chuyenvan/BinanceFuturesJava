package com.binance.chuyennd.c3live.exec;

import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.TradeFill;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.LongSupplier;

/**
 * [V12 3j R2] Giai quyet GIA KHOP cho 1 lenh khi ACK khong co avgPrice (Binance MARKET ACK co the thieu), theo dung thu tu
 * va trong TONG ngan sach <= {@link #DEFAULT_BUDGET_MS} 3 s:
 * <ol>
 *   <li><b>(a) stream</b> {@code ORDER_TRADE_UPDATE}: {@code ap} (avg) hoac {@code L} (last) cua chinh cid/orderId — cache
 *       duoc {@link #observe} tu FillAccounting (moi JVM chi co 1 user stream); doi toi da {@link #DEFAULT_STREAM_WAIT_MS};</li>
 *   <li><b>(b) queryOrder</b> avgPrice, kem lui doc-sau-ghi kieu 3e ({@link #QUERY_BACKOFF_MS}) — dung khi stream cham/tre;</li>
 *   <li><b>(c) userTrades</b> theo orderId — gia binh quan gia quyen sum(qty*price)/sum(qty).</li>
 * </ol>
 * Khong nguon nao co gia (hoac het ngan sach) => {@link Source#NONE}; nguoi goi ghi qty voi gia TAM (R2: PX_PROVISIONAL)
 * chu KHONG duoc coi la "khong khop" (R1). Moi call REST bao {@link C3LiveOrderExecutor.ApiObserver}.
 *
 * <p>Thread-safe: cache la ConcurrentHashMap; {@link #resolve} khong giu khoa khi ngu.
 */
public final class FillPriceResolver {

    private static final Logger LOG = LoggerFactory.getLogger(FillPriceResolver.class);

    /** Tong ngan sach (ms) cho ca (a)+(b)+(c) — R2: <= 3 s. */
    public static final long DEFAULT_BUDGET_MS = 3_000L;
    /** Cho toi da (a) stream truoc khi tra san (K4 that: ap den sau ACK ~30-480 ms). */
    public static final long DEFAULT_STREAM_WAIT_MS = 600L;
    /** Buoc ngu giua 2 lan doc cache khi cho stream. */
    static final long STREAM_POLL_MS = 50L;
    /** [3e] lui doc-sau-ghi khi queryOrder chua co / chua co gia (tong <= ngan sach). */
    static final long[] QUERY_BACKOFF_MS = {250L, 500L, 1_000L, 1_250L};
    /** Chua lai phan ngan sach cho (c) userTrades khi (b) da dung het gio. */
    static final long TRADES_RESERVE_MS = 500L;

    public enum Source {
        /** (a) ORDER_TRADE_UPDATE ap. */
        STREAM_AP,
        /** (a) ORDER_TRADE_UPDATE L (gia khop tung phan). */
        STREAM_LAST,
        /** (b) queryOrder avgPrice. */
        QUERY,
        /** (c) userTrades binh quan gia quyen. */
        TRADES,
        /** Khong nguon nao — nguoi goi phai dung gia TAM (mark) va danh dau provisional. */
        NONE
    }

    /** Ket qua: px > 0 => gia that; px <= 0 => {@link Source#NONE}. qty > 0 khi nguon doc duoc executedQty lon hon. */
    public static final class Resolved {
        public final double px;
        public final Source source;
        public final BigDecimal qty;
        public final long ms;

        Resolved(double px, Source source, BigDecimal qty, long ms) {
            this.px = px;
            this.source = source;
            this.qty = qty;
            this.ms = ms;
        }

        public boolean hasPrice() {
            return px > 0d && source != Source.NONE;
        }

        @Override
        public String toString() {
            return source + "@" + px + "/q=" + qty + "/" + ms + "ms";
        }
    }

    private final LongSupplier clock;
    private final C3LiveOrderExecutor.Sleeper sleeper;
    private final C3LiveOrderExecutor.ApiObserver api;
    private final long budgetMs;
    private final long streamWaitMs;

    /** ap uu tien hon L (ap la gia binh quan that cua lenh). */
    private final Map<String, Double> apByCid = new ConcurrentHashMap<>();
    private final Map<String, Double> lastByCid = new ConcurrentHashMap<>();
    private final Map<Long, Double> apByOrder = new ConcurrentHashMap<>();
    private final Map<Long, Double> lastByOrder = new ConcurrentHashMap<>();

    public FillPriceResolver(LongSupplier clock, C3LiveOrderExecutor.Sleeper sleeper, C3LiveOrderExecutor.ApiObserver api) {
        this(clock, sleeper, api, DEFAULT_BUDGET_MS, DEFAULT_STREAM_WAIT_MS);
    }

    FillPriceResolver(LongSupplier clock, C3LiveOrderExecutor.Sleeper sleeper, C3LiveOrderExecutor.ApiObserver api,
                      long budgetMs, long streamWaitMs) {
        this.clock = clock;
        this.sleeper = sleeper == null ? ms -> { } : sleeper;
        this.api = api == null ? (a, ok) -> { } : api;
        this.budgetMs = Math.max(0L, budgetMs);
        this.streamWaitMs = Math.max(0L, streamWaitMs);
    }

    /**
     * [3j] ghi gia tu user stream. {@code avg} = truong {@code ap}; {@code last} = truong {@code L}. Chi nhan gia > 0
     * (ap = "0" cua su kien NEW khong ghi de gia that da co).
     */
    public void observe(String cid, long orderId, BigDecimal avg, BigDecimal last) {
        if (avg != null && avg.signum() > 0) {
            if (cid != null) apByCid.put(cid, avg.doubleValue());
            if (orderId > 0L) apByOrder.put(orderId, avg.doubleValue());
        }
        if (last != null && last.signum() > 0) {
            if (cid != null) lastByCid.putIfAbsent(cid, last.doubleValue());
            if (orderId > 0L) lastByOrder.putIfAbsent(orderId, last.doubleValue());
        }
    }

    /** Gia tu cache stream (a): ap truoc, roi L; null = chua co. */
    public Source cached(String cid, long orderId) {
        if (cid != null && apByCid.containsKey(cid)) return Source.STREAM_AP;
        if (orderId > 0L && apByOrder.containsKey(orderId)) return Source.STREAM_AP;
        if (cid != null && lastByCid.containsKey(cid)) return Source.STREAM_LAST;
        if (orderId > 0L && lastByOrder.containsKey(orderId)) return Source.STREAM_LAST;
        return Source.NONE;
    }

    double cachedPx(String cid, long orderId) {
        Double v = cid == null ? null : apByCid.get(cid);
        if (v == null && orderId > 0L) v = apByOrder.get(orderId);
        if (v == null && cid != null) v = lastByCid.get(cid);
        if (v == null && orderId > 0L) v = lastByOrder.get(orderId);
        return v == null ? 0d : v;
    }

    /**
     * (a) doi stream toi da {@code streamWaitMs} (trong ngan sach), (b) queryOrder kem lui doc-sau-ghi, (c) userTrades.
     * Khong bao gio nem: loi doc = nguon do khong dung duoc.
     */
    public Resolved resolve(ExchangeGateway gw, String symbol, String cid, long orderId) {
        return resolve(gw, symbol, cid, orderId, streamWaitMs);
    }

    /**
     * Nhu {@link #resolve(ExchangeGateway, String, String, long)} nhung gioi han cho stream (0 = khong cho stream, dung cho
     * luong dinh ky hieu chinh gia TAM).
     */
    public Resolved resolve(ExchangeGateway gw, String symbol, String cid, long orderId, long streamWaitMaxMs) {
        long t0 = clock.getAsLong();
        long deadline = t0 + budgetMs;
        long streamWait = Math.max(0L, Math.min(streamWaitMaxMs, streamWaitMs));
        // (a) stream
        while (true) {
            Source s = cached(cid, orderId);
            if (s != Source.NONE) return new Resolved(cachedPx(cid, orderId), s, BigDecimal.ZERO, clock.getAsLong() - t0);
            long left = t0 + streamWait - clock.getAsLong();
            if (left <= 0L) break;
            if (!sleep(Math.min(STREAM_POLL_MS, left))) break;
        }
        // (b) queryOrder (doc-sau-ghi) — chua lai TRADES_RESERVE_MS cho (c)
        BigDecimal qty = BigDecimal.ZERO;
        long queryDeadline = orderId > 0L ? Math.max(t0, deadline - TRADES_RESERVE_MS) : deadline;
        for (int i = 0; ; i++) {
            Optional<OrderInfo> q = Optional.empty();
            try {
                q = gw.queryOrder(symbol, cid);
                api.onApiResult("queryOrder", true);
            } catch (GatewayException e) {
                api.onApiResult("queryOrder", false);
                if (e.getKind() == ErrorKind.UNKNOWN_ORDER) {
                    q = Optional.empty();
                }
            } catch (RuntimeException e) {
                api.onApiResult("queryOrder", false);
            }
            if (q.isPresent()) {
                OrderInfo o = q.get();
                if (o.getExecutedQty() != null && o.getExecutedQty().signum() > 0) qty = o.getExecutedQty();
                if (o.getAvgPrice() != null && o.getAvgPrice().signum() > 0) {
                    return new Resolved(o.getAvgPrice().doubleValue(), Source.QUERY, qty, clock.getAsLong() - t0);
                }
            }
            if (i >= QUERY_BACKOFF_MS.length || clock.getAsLong() >= queryDeadline) break;
            if (!sleep(Math.min(QUERY_BACKOFF_MS[i], Math.max(0L, queryDeadline - clock.getAsLong())))) break;
        }
        // (c) userTrades
        if (orderId > 0L && clock.getAsLong() < deadline) {
            try {
                List<TradeFill> tr = gw.userTrades(symbol, orderId);
                api.onApiResult("userTrades", true);
                double px = weightedAvg(tr);
                if (px > 0d) {
                    BigDecimal q = BigDecimal.ZERO;
                    for (TradeFill t : tr) if (t.getQty() != null) q = q.add(t.getQty());
                    return new Resolved(px, Source.TRADES, q.signum() > 0 ? q : qty, clock.getAsLong() - t0);
                }
            } catch (GatewayException e) {
                api.onApiResult("userTrades", false);
            } catch (RuntimeException e) {
                api.onApiResult("userTrades", false);
            }
        }
        return new Resolved(0d, Source.NONE, qty, clock.getAsLong() - t0);
    }

    /** Gia binh quan gia quyen cua cac khop (0 = khong co). */
    static double weightedAvg(List<TradeFill> trades) {
        if (trades == null || trades.isEmpty()) return 0d;
        double q = 0d;
        double n = 0d;
        for (TradeFill t : trades) {
            if (t.getQty() == null || t.getPrice() == null) continue;
            double tq = t.getQty().doubleValue();
            double tp = t.getPrice().doubleValue();
            if (!(tq > 0d) || !(tp > 0d)) continue;
            q += tq;
            n += tq * tp;
        }
        return q > 0d ? n / q : 0d;
    }

    /** Ngu ngan sach; InterruptedException => interrupt + dung. true = con tiep. */
    private boolean sleep(long ms) {
        if (ms <= 0L) return true;
        try {
            sleeper.sleepMs(ms);
            return true;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            LOG.warn("[3j] FillPriceResolver bi ngat khi cho gia — dung");
            return false;
        }
    }
}
