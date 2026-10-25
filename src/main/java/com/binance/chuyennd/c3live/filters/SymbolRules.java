package com.binance.chuyennd.c3live.filters;

import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.SymbolMeta;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.function.Supplier;

/**
 * [V12 C4] Lam tron qty / gia theo filter san cho c3_live. Thay the Utils.calQuantity / ClientSingleton.normalizeQuantity
 * (LEGACY: dung minQty lam buoc, bo MARKET_LOT_SIZE, noi budget +1..+9, ep BTC 0.002) - lop nay KHONG noi budget:
 * khong dat filter -> {@link Sizing#skip} co ly do (bo leg).
 * <ul>
 *   <li>MARKET: buoc MARKET_LOT_SIZE.stepSize (fallback LOT_SIZE), min/max MARKET_LOT_SIZE (fallback LOT_SIZE).</li>
 *   <li>STOP / LIMIT: LOT_SIZE.</li>
 *   <li>qty = floor(budget / refPrice, step); qty*refPrice &lt;= budget luon dung; &lt; minNotional -> bo (tru reduceOnly).</li>
 *   <li>Gia stop ban cua long: lam tron XUONG theo tickSize.</li>
 *   <li>Nap lai exchangeInfo moi 6 h ({@link #refreshIfDue}); loi nap -> giu ban cu + WARN.</li>
 * </ul>
 */
public final class SymbolRules {
    private static final Logger LOG = LoggerFactory.getLogger(SymbolRules.class);
    public static final long REFRESH_MS = 6L * 3_600_000L;
    private static final int DIV_SCALE = 24;

    public enum SkipReason {
        UNKNOWN_SYMBOL, NOT_TRADING, NO_FILTER, BAD_INPUT, QTY_ZERO, BELOW_MIN_QTY, ABOVE_MAX_QTY, BELOW_MIN_NOTIONAL, OVER_BUDGET
    }

    /** Ket qua tinh size: ok -> qty (da lam tron, scale theo step); !ok -> reason + detail (bo leg, khong gui). */
    public static final class Sizing {
        private final boolean ok;
        private final BigDecimal qty;
        private final BigDecimal notional;
        private final SkipReason reason;
        private final String detail;

        private Sizing(boolean ok, BigDecimal qty, BigDecimal notional, SkipReason reason, String detail) {
            this.ok = ok;
            this.qty = qty;
            this.notional = notional;
            this.reason = reason;
            this.detail = detail;
        }

        static Sizing ok(BigDecimal qty, BigDecimal notional) { return new Sizing(true, qty, notional, null, null); }

        static Sizing skip(SkipReason r, String detail, BigDecimal qty, BigDecimal notional) {
            return new Sizing(false, qty, notional, r, detail);
        }

        public boolean isOk() { return ok; }
        public BigDecimal getQty() { return qty; }
        /** qty * refPrice. */
        public BigDecimal getNotional() { return notional; }
        public SkipReason getReason() { return reason; }
        public String getDetail() { return detail; }

        @Override
        public String toString() {
            return ok ? "Sizing{ok qty=" + qty.toPlainString() + " notional=" + notional.toPlainString() + "}"
                    : "Sizing{SKIP " + reason + " " + detail + "}";
        }
    }

    private volatile Map<String, SymbolMeta> metas = Collections.emptyMap();
    private volatile long loadedAtMs;
    private final BigDecimal minNotionalMargin;

    /** minNotionalMargin = 1 (khong dem). */
    public SymbolRules(ExchangeInfo ei, long nowMs) {
        this(ei, nowMs, BigDecimal.ONE);
    }

    /** minNotionalMargin &gt;= 1: yeu cau notional &gt;= minNotional * margin (vd 1.02 de phong ref lech gia khop). */
    public SymbolRules(ExchangeInfo ei, long nowMs, BigDecimal minNotionalMargin) {
        this.minNotionalMargin = minNotionalMargin == null || minNotionalMargin.compareTo(BigDecimal.ONE) < 0 ? BigDecimal.ONE : minNotionalMargin;
        load(ei, nowMs);
    }

    public synchronized void load(ExchangeInfo ei, long nowMs) {
        if (ei == null || ei.getSymbols().isEmpty()) throw new IllegalArgumentException("exchangeInfo rong");
        this.metas = Collections.unmodifiableMap(new HashMap<>(ei.getSymbols()));
        this.loadedAtMs = nowMs;
        LOG.info("[C3-RULES] nap filter {} symbol", metas.size());
    }

    /** Nap lai khi da qua 6 h. Tra true neu da nap moi. Loi -> giu ban cu, WARN, false. */
    public synchronized boolean refreshIfDue(long nowMs, Supplier<ExchangeInfo> source) {
        if (nowMs - loadedAtMs < REFRESH_MS) return false;
        try {
            load(source.get(), nowMs);
            return true;
        } catch (RuntimeException e) {
            LOG.warn("[C3-RULES] nap lai exchangeInfo loi ({}), giu ban cu tu {}", e.toString(), loadedAtMs);
            return false;
        }
    }

    public long loadedAtMs() { return loadedAtMs; }

    public Optional<SymbolMeta> meta(String symbol) { return Optional.ofNullable(metas.get(symbol)); }

    public BigDecimal tickSize(String symbol) {
        SymbolMeta m = metas.get(symbol);
        return m == null ? null : m.getTickSize();
    }

    /** Tinh qty MARKET BUY tu budget (USDT) va gia tham chieu. KHONG noi budget. */
    public Sizing sizeMarketBuy(String symbol, BigDecimal budgetUsdt, BigDecimal refPrice) {
        SymbolMeta m = metas.get(symbol);
        if (m == null) return Sizing.skip(SkipReason.UNKNOWN_SYMBOL, symbol, null, null);
        if (!"TRADING".equals(m.getStatus())) return Sizing.skip(SkipReason.NOT_TRADING, "status=" + m.getStatus(), null, null);
        if (budgetUsdt == null || refPrice == null || budgetUsdt.signum() <= 0 || refPrice.signum() <= 0) {
            return Sizing.skip(SkipReason.BAD_INPUT, "budget=" + budgetUsdt + " price=" + refPrice, null, null);
        }
        BigDecimal raw = budgetUsdt.divide(refPrice, DIV_SCALE, RoundingMode.DOWN);
        return check(m, raw, refPrice, true, false, budgetUsdt);
    }

    /**
     * Kiem / lam tron 1 qty cho truoc (vd DCA tinh san, dong vi the). reduceOnly -> mien MIN_NOTIONAL (luat san
     * "unless you choose reduce only"). market=false -> LOT_SIZE.
     */
    public Sizing checkQty(String symbol, BigDecimal qty, BigDecimal refPrice, boolean market, boolean reduceOnly) {
        SymbolMeta m = metas.get(symbol);
        if (m == null) return Sizing.skip(SkipReason.UNKNOWN_SYMBOL, symbol, null, null);
        if (!"TRADING".equals(m.getStatus())) return Sizing.skip(SkipReason.NOT_TRADING, "status=" + m.getStatus(), null, null);
        if (qty == null || refPrice == null || qty.signum() <= 0 || refPrice.signum() <= 0) {
            return Sizing.skip(SkipReason.BAD_INPUT, "qty=" + qty + " price=" + refPrice, null, null);
        }
        return check(m, qty, refPrice, market, reduceOnly, null);
    }

    private Sizing check(SymbolMeta m, BigDecimal rawQty, BigDecimal price, boolean market, boolean reduceOnly, BigDecimal budget) {
        BigDecimal step = market && pos(m.getMarketStepSize()) ? m.getMarketStepSize() : m.getStepSize();
        if (!pos(step)) return Sizing.skip(SkipReason.NO_FILTER, "thieu stepSize", null, null);
        BigDecimal minQ = market && m.getMarketMinQty() != null ? m.getMarketMinQty() : m.getMinQty();
        BigDecimal maxQ = market && m.getMarketMaxQty() != null ? m.getMarketMaxQty() : m.getMaxQty();
        BigDecimal qty = floorTo(rawQty, step);
        BigDecimal notional = qty.multiply(price);
        if (qty.signum() == 0) return Sizing.skip(SkipReason.QTY_ZERO, "raw=" + rawQty.stripTrailingZeros().toPlainString() + " step=" + step.toPlainString(), qty, notional);
        if (minQ != null && qty.compareTo(minQ) < 0) return Sizing.skip(SkipReason.BELOW_MIN_QTY, "qty=" + qty.toPlainString() + " < minQty=" + minQ.toPlainString(), qty, notional);
        if (maxQ != null && maxQ.signum() > 0 && qty.compareTo(maxQ) > 0) return Sizing.skip(SkipReason.ABOVE_MAX_QTY, "qty=" + qty.toPlainString() + " > maxQty=" + maxQ.toPlainString(), qty, notional);
        if (!reduceOnly && m.getMinNotional() != null && notional.compareTo(m.getMinNotional().multiply(minNotionalMargin)) < 0) {
            return Sizing.skip(SkipReason.BELOW_MIN_NOTIONAL, "notional=" + notional.stripTrailingZeros().toPlainString() + " < minNotional="
                    + m.getMinNotional().toPlainString() + (minNotionalMargin.compareTo(BigDecimal.ONE) > 0 ? "x" + minNotionalMargin : ""), qty, notional);
        }
        if (budget != null && notional.compareTo(budget) > 0) return Sizing.skip(SkipReason.OVER_BUDGET, "notional > budget", qty, notional);
        return Sizing.ok(qty, notional);
    }

    /** qty lam tron XUONG theo buoc (market=true: MARKET_LOT_SIZE). null neu khong co filter. */
    public BigDecimal roundQtyDown(String symbol, BigDecimal qty, boolean market) {
        SymbolMeta m = metas.get(symbol);
        if (m == null || qty == null) return null;
        BigDecimal step = market && pos(m.getMarketStepSize()) ? m.getMarketStepSize() : m.getStepSize();
        return pos(step) ? floorTo(qty, step) : null;
    }

    /** Gia lam tron theo tickSize voi mode (FLOOR/DOWN/CEILING/UP/HALF_*). null neu khong co filter. */
    public BigDecimal roundPrice(String symbol, BigDecimal price, RoundingMode mode) {
        SymbolMeta m = metas.get(symbol);
        if (m == null || price == null || !pos(m.getTickSize())) return null;
        BigDecimal tick = m.getTickSize();
        return price.divide(tick, 0, mode).multiply(tick).setScale(Math.max(0, tick.stripTrailingZeros().scale()), RoundingMode.UNNECESSARY);
    }

    /** Stop BAN bao ve vi the LONG: lam tron XUONG theo tick (khong bao gio cao hon muc tinh). */
    public BigDecimal roundStopPriceForLong(String symbol, BigDecimal stop) {
        return roundPrice(symbol, stop, RoundingMode.FLOOR);
    }

    /** Gia nam trong [minPrice, maxPrice] cua PRICE_FILTER (bien thieu = khong gioi han). */
    public boolean isPriceInRange(String symbol, BigDecimal price) {
        SymbolMeta m = metas.get(symbol);
        if (m == null || price == null) return false;
        if (m.getMinPrice() != null && m.getMinPrice().signum() > 0 && price.compareTo(m.getMinPrice()) < 0) return false;
        return m.getMaxPrice() == null || m.getMaxPrice().signum() <= 0 || price.compareTo(m.getMaxPrice()) <= 0;
    }

    static BigDecimal floorTo(BigDecimal v, BigDecimal step) {
        BigDecimal n = v.divide(step, 0, RoundingMode.FLOOR);
        return n.multiply(step).setScale(Math.max(0, step.stripTrailingZeros().scale()), RoundingMode.UNNECESSARY);
    }

    private static boolean pos(BigDecimal b) { return b != null && b.signum() > 0; }
}
