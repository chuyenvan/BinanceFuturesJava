package com.binance.chuyennd.c3live.api;

/**
 * [V12 C2] Loi duy nhat ma ExchangeGateway nem ra. Message KHONG bao gio chua key / secret / signature / query ky.
 */
public class GatewayException extends RuntimeException {
    private static final long serialVersionUID = 1L;

    private final ErrorKind kind;
    private final int httpStatus;
    private final int exchangeCode;
    private final boolean definitelyNotExecuted;
    private final long retryAfterMs;

    public GatewayException(ErrorKind kind, int httpStatus, int exchangeCode, String message,
                            boolean definitelyNotExecuted, long retryAfterMs, Throwable cause) {
        super(message, cause);
        this.kind = kind == null ? ErrorKind.OTHER : kind;
        this.httpStatus = httpStatus;
        this.exchangeCode = exchangeCode;
        this.definitelyNotExecuted = definitelyNotExecuted;
        this.retryAfterMs = Math.max(0L, retryAfterMs);
    }

    public GatewayException(ErrorKind kind, String message, boolean definitelyNotExecuted) {
        this(kind, 0, 0, message, definitelyNotExecuted, 0L, null);
    }

    public ErrorKind getKind() { return kind; }

    /** 0 neu khong co HTTP response (timeout, chan noi bo). */
    public int getHttpStatus() { return httpStatus; }

    /** Ma loi Binance (vd -2019); 0 neu khong co. */
    public int getExchangeCode() { return exchangeCode; }

    /**
     * true = san tu choi ro rang hoac request chua tung duoc gui (an toan de gui lai voi CUNG clientOrderId sau khi sua nguyen nhan).
     * false = trang thai khong chac chan (TIMEOUT_UNKNOWN_STATE) -> bat buoc queryOrder truoc.
     */
    public boolean isDefinitelyNotExecuted() { return definitelyNotExecuted; }

    /** Goi y cho: so ms nen doi truoc call tiep theo (429/418 Retry-After), 0 neu khong co. */
    public long getRetryAfterMs() { return retryAfterMs; }

    @Override
    public String toString() {
        return "GatewayException{" + kind + ", http=" + httpStatus + ", code=" + exchangeCode
                + ", notExecuted=" + definitelyNotExecuted + ", msg=" + getMessage() + "}";
    }
}
