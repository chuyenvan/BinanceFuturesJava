package com.binance.chuyennd.c3live.client;

/**
 * [V12 C2] Key file c3_live thieu / sai quyen / sai owner / sai noi dung -> KHONG tao client, c3_live tu choi bat push.
 * Message chi chua duong dan, quyen, owner, ten bien thieu - KHONG BAO GIO chua gia tri key/secret.
 */
public class C3LiveKeyException extends Exception {
    private static final long serialVersionUID = 1L;

    public C3LiveKeyException(String message) {
        super(message);
    }

    public C3LiveKeyException(String message, Throwable cause) {
        super(message, cause);
    }
}
