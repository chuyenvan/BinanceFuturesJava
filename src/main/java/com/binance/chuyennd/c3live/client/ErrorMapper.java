package com.binance.chuyennd.c3live.client;

import com.binance.chuyennd.c3live.api.ErrorKind;

/**
 * [V12 C2] Map (HTTP status, ma loi Binance) -> ErrorKind. Dung chung Live / Dry / Mock.
 * Bang ma: Binance USDT-M error codes (CHUA XAC MINH lai voi tai lieu tai thoi diem code cho cac ma it gap).
 */
public final class ErrorMapper {
    private ErrorMapper() { }

    public static ErrorKind kindFor(int httpStatus, int code) {
        if (httpStatus == 429 || httpStatus == 418) return ErrorKind.RATE_LIMIT;
        switch (code) {
            case -2015: case -2014: case -1022: case -1002: case -2008:
                return ErrorKind.AUTH;
            case -1003: case -1015:
                return ErrorKind.RATE_LIMIT;
            case -2019: case -2018:
                return ErrorKind.INSUFFICIENT_MARGIN;
            case -1013: case -1111: case -4164: case -4003: case -4004: case -4005: case -4013: case -4014:
            case -4023: case -4024: case -4131: case -2027: case -1112:
                return ErrorKind.FILTER;
            case -2011: case -2013:
                return ErrorKind.UNKNOWN_ORDER;
            case -1007: case -1006:
                return ErrorKind.TIMEOUT_UNKNOWN_STATE;
            default:
                break;
        }
        if (httpStatus == 401) return ErrorKind.AUTH;
        if (httpStatus >= 500 && code != -1008) return ErrorKind.TIMEOUT_UNKNOWN_STATE;
        return ErrorKind.OTHER;
    }

    /** true = san chac chan khong thuc thi request (an toan gui lai cung clientOrderId sau khi xu ly nguyen nhan). */
    public static boolean definitelyNotExecuted(ErrorKind kind) {
        return kind != ErrorKind.TIMEOUT_UNKNOWN_STATE;
    }
}
