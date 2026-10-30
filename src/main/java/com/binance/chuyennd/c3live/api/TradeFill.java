package com.binance.chuyennd.c3live.api;

import java.math.BigDecimal;
import java.util.Objects;

/**
 * [V12 3j] 1 khop THAT cua lenh thuong (GET /fapi/v1/userTrades). Dung lam nguon gia thu 3 khi ACK MARKET
 * khong co avgPrice va queryOrder chua tra gia (R2(c) round 3j): gia binh quan gia quyen = sum(qty*price)/sum(qty).
 *
 * <p>Bat bien. San khong tra truong nao => null (khong bao gio nem).
 */
public final class TradeFill {

    private final String symbol;
    private final long orderId;
    private final BigDecimal qty;
    private final BigDecimal price;
    private final long timeMs;
    /** [V12 R4f] id khop (userTrades "id" = stream "t") de chong ghi trung; &lt;= 0 = khong co. */
    private final long tradeId;
    private final BigDecimal commission;
    private final String commissionAsset;
    /** realizedPnl cua san (CHI doi chieu; sai khi MERGED). */
    private final BigDecimal realizedPnl;

    public TradeFill(String symbol, long orderId, BigDecimal qty, BigDecimal price, long timeMs) {
        this(symbol, orderId, qty, price, timeMs, -1L, null, null, null);
    }

    public TradeFill(String symbol, long orderId, BigDecimal qty, BigDecimal price, long timeMs, long tradeId,
                     BigDecimal commission, String commissionAsset, BigDecimal realizedPnl) {
        this.symbol = symbol;
        this.orderId = orderId;
        this.qty = qty;
        this.price = price;
        this.timeMs = timeMs;
        this.tradeId = tradeId;
        this.commission = commission;
        this.commissionAsset = commissionAsset;
        this.realizedPnl = realizedPnl;
    }

    public long getTradeId() { return tradeId; }
    public BigDecimal getCommission() { return commission; }
    public String getCommissionAsset() { return commissionAsset; }
    public BigDecimal getRealizedPnl() { return realizedPnl; }

    public String getSymbol() {
        return symbol;
    }

    public long getOrderId() {
        return orderId;
    }

    public BigDecimal getQty() {
        return qty;
    }

    public BigDecimal getPrice() {
        return price;
    }

    public long getTimeMs() {
        return timeMs;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof TradeFill)) return false;
        TradeFill x = (TradeFill) o;
        return orderId == x.orderId && timeMs == x.timeMs && Objects.equals(symbol, x.symbol)
                && Objects.equals(qty, x.qty) && Objects.equals(price, x.price);
    }

    @Override
    public int hashCode() {
        return Objects.hash(symbol, orderId, qty, price, timeMs);
    }

    @Override
    public String toString() {
        return symbol + "/" + orderId + "/" + qty + "@" + price + "/" + timeMs;
    }
}
