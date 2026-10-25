package com.binance.chuyennd.c3live.api;

/**
 * [V12 C2] Phan loai loi chung cho moi ban cai ExchangeGateway (Live / Dry / Mock).
 * Ma goc cua san van giu trong {@link GatewayException#getExchangeCode()}.
 */
public enum ErrorKind {
    /** HTTP 429 / 418, -1003, -1015, hoac RateGuard noi bo het ngan sach. */
    RATE_LIMIT,
    /** -2019 (margin), -2018 (balance). */
    INSUFFICIENT_MARGIN,
    /** -1013, -1111, -4164, -4003, -4005, -4131 ... (filter / precision / notional). */
    FILTER,
    /** -2011 (cancel), -2013 (query) : lenh khong ton tai tren san. */
    UNKNOWN_ORDER,
    /** Timeout / 5xx / -1007: san CO THE da nhan lenh. Phai tra theo clientOrderId truoc khi gui lai. */
    TIMEOUT_UNKNOWN_STATE,
    /** -2015, -2014, -1022, -1002, HTTP 401: key / IP / quyen / chu ky. */
    AUTH,
    /** Moi loi con lai (gom -1021 timestamp: san tu choi chac chan, client tu dong bo lai gio). */
    OTHER
}
