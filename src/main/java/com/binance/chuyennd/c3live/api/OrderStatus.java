package com.binance.chuyennd.c3live.api;

import java.util.Locale;

/**
 * [V12] Trang thai lenh thuong (/fapi/v1/order) va lenh algo (/fapi/v1/algoOrder: algoStatus).
 * Gia tri la (khong nhan ra) -> UNKNOWN, KHONG nem loi.
 */
public enum OrderStatus {
    NEW, PARTIALLY_FILLED, FILLED, CANCELED, REJECTED, EXPIRED, EXPIRED_IN_MATCH,
    /** algo */ TRIGGERING,
    /** algo */ TRIGGERED,
    /** algo */ FINISHED,
    UNKNOWN;

    public static OrderStatus parse(String s) {
        if (s == null) return UNKNOWN;
        try {
            return OrderStatus.valueOf(s.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            return UNKNOWN;
        }
    }

    /** Lenh khong con song tren so lenh cho cua san. */
    public boolean isFinal() {
        switch (this) {
            case FILLED: case CANCELED: case REJECTED: case EXPIRED: case EXPIRED_IN_MATCH:
            case TRIGGERED: case FINISHED:
                return true;
            default:
                return false;
        }
    }
}
