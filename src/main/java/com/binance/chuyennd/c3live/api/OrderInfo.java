package com.binance.chuyennd.c3live.api;

import java.math.BigDecimal;
import java.util.Objects;

/**
 * [V12] Anh chup bat bien cua 1 lenh (thuong hoac algo). Truong khong co tu san = null (BigDecimal) / 0 (long).
 */
public final class OrderInfo {
    private final OrderKind kind;
    private final String symbol;
    private final long orderId;
    private final String clientOrderId;
    private final Side side;
    private final String type;
    private final OrderStatus status;
    private final String rawStatus;
    private final BigDecimal origQty;
    private final BigDecimal executedQty;
    private final BigDecimal avgPrice;
    private final BigDecimal stopPrice;
    private final boolean reduceOnly;
    private final boolean closePosition;
    private final long updateTimeMs;
    /** [3g] algo: actualOrderId (lenh thuong sinh ra khi stop kich); null = khong co / khong phai algo. */
    private final String actualOrderId;

    private OrderInfo(Builder b) {
        this.kind = b.kind == null ? OrderKind.REGULAR : b.kind;
        this.symbol = b.symbol;
        this.orderId = b.orderId;
        this.clientOrderId = b.clientOrderId;
        this.side = b.side;
        this.type = b.type;
        this.status = b.status == null ? OrderStatus.UNKNOWN : b.status;
        this.rawStatus = b.rawStatus;
        this.origQty = b.origQty;
        this.executedQty = b.executedQty;
        this.avgPrice = b.avgPrice;
        this.stopPrice = b.stopPrice;
        this.reduceOnly = b.reduceOnly;
        this.closePosition = b.closePosition;
        this.updateTimeMs = b.updateTimeMs;
        this.actualOrderId = b.actualOrderId;
    }

    public static Builder builder() { return new Builder(); }

    public Builder toBuilder() {
        return new Builder().kind(kind).symbol(symbol).orderId(orderId).clientOrderId(clientOrderId).side(side)
                .type(type).status(status).rawStatus(rawStatus).origQty(origQty).executedQty(executedQty)
                .avgPrice(avgPrice).stopPrice(stopPrice).reduceOnly(reduceOnly).closePosition(closePosition)
                .updateTimeMs(updateTimeMs).actualOrderId(actualOrderId);
    }

    public OrderKind getKind() { return kind; }
    public String getSymbol() { return symbol; }
    /** orderId (REGULAR) hoac algoId (ALGO). */
    public long getOrderId() { return orderId; }
    /** clientOrderId (REGULAR) hoac clientAlgoId (ALGO). */
    public String getClientOrderId() { return clientOrderId; }
    public Side getSide() { return side; }
    /** MARKET / STOP_MARKET ... (algo: orderType). */
    public String getType() { return type; }
    public OrderStatus getStatus() { return status; }
    public String getRawStatus() { return rawStatus; }
    public BigDecimal getOrigQty() { return origQty; }
    public BigDecimal getExecutedQty() { return executedQty; }
    public BigDecimal getAvgPrice() { return avgPrice; }
    /** stopPrice (REGULAR) hoac triggerPrice (ALGO). */
    public BigDecimal getStopPrice() { return stopPrice; }
    public boolean isReduceOnly() { return reduceOnly; }
    public boolean isClosePosition() { return closePosition; }
    public long getUpdateTimeMs() { return updateTimeMs; }
    public String getActualOrderId() { return actualOrderId; }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof OrderInfo)) return false;
        OrderInfo x = (OrderInfo) o;
        return orderId == x.orderId && reduceOnly == x.reduceOnly && closePosition == x.closePosition
                && updateTimeMs == x.updateTimeMs && kind == x.kind && Objects.equals(symbol, x.symbol)
                && Objects.equals(clientOrderId, x.clientOrderId) && side == x.side && Objects.equals(type, x.type)
                && status == x.status && Objects.equals(rawStatus, x.rawStatus) && Objects.equals(origQty, x.origQty)
                && Objects.equals(executedQty, x.executedQty) && Objects.equals(avgPrice, x.avgPrice)
                && Objects.equals(stopPrice, x.stopPrice);
    }

    @Override
    public int hashCode() { return Objects.hash(kind, symbol, orderId, clientOrderId, status, updateTimeMs); }

    @Override
    public String toString() {
        return "OrderInfo{" + kind + " " + symbol + " id=" + orderId + " cid=" + clientOrderId + " " + side + " " + type
                + " " + status + " q=" + origQty + " exQ=" + executedQty + " avg=" + avgPrice + " stop=" + stopPrice
                + " ro=" + reduceOnly + " cp=" + closePosition + " t=" + updateTimeMs + "}";
    }

    public static final class Builder {
        private OrderKind kind;
        private String symbol;
        private long orderId;
        private String clientOrderId;
        private Side side;
        private String type;
        private OrderStatus status;
        private String rawStatus;
        private BigDecimal origQty;
        private BigDecimal executedQty;
        private BigDecimal avgPrice;
        private BigDecimal stopPrice;
        private boolean reduceOnly;
        private boolean closePosition;
        private long updateTimeMs;
        private String actualOrderId;

        public Builder kind(OrderKind v) { this.kind = v; return this; }
        public Builder symbol(String v) { this.symbol = v; return this; }
        public Builder orderId(long v) { this.orderId = v; return this; }
        public Builder clientOrderId(String v) { this.clientOrderId = v; return this; }
        public Builder side(Side v) { this.side = v; return this; }
        public Builder type(String v) { this.type = v; return this; }
        public Builder status(OrderStatus v) { this.status = v; return this; }
        public Builder rawStatus(String v) { this.rawStatus = v; return this; }
        public Builder origQty(BigDecimal v) { this.origQty = v; return this; }
        public Builder executedQty(BigDecimal v) { this.executedQty = v; return this; }
        public Builder avgPrice(BigDecimal v) { this.avgPrice = v; return this; }
        public Builder stopPrice(BigDecimal v) { this.stopPrice = v; return this; }
        public Builder reduceOnly(boolean v) { this.reduceOnly = v; return this; }
        public Builder closePosition(boolean v) { this.closePosition = v; return this; }
        public Builder updateTimeMs(long v) { this.updateTimeMs = v; return this; }
        public Builder actualOrderId(String v) { this.actualOrderId = v; return this; }
        public OrderInfo build() { return new OrderInfo(this); }
    }
}
