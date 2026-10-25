package com.binance.chuyennd.c3live.api;

import java.util.Locale;

/** [V12 C13] 1 muc exchangeInfo.rateLimits: {rateLimitType, interval, intervalNum, limit}. */
public final class RateLimitSpec {
    private final String rateLimitType;
    private final String interval;
    private final int intervalNum;
    private final int limit;

    public RateLimitSpec(String rateLimitType, String interval, int intervalNum, int limit) {
        this.rateLimitType = rateLimitType == null ? "" : rateLimitType.toUpperCase(Locale.ROOT);
        this.interval = interval == null ? "" : interval.toUpperCase(Locale.ROOT);
        this.intervalNum = intervalNum;
        this.limit = limit;
    }

    public String getRateLimitType() { return rateLimitType; }
    public String getInterval() { return interval; }
    public int getIntervalNum() { return intervalNum; }
    public int getLimit() { return limit; }

    /** Do dai cua so (ms); 0 neu khong nhan ra don vi. */
    public long windowMs() {
        long unit;
        switch (interval) {
            case "SECOND": unit = 1000L; break;
            case "MINUTE": unit = 60_000L; break;
            case "HOUR": unit = 3_600_000L; break;
            case "DAY": unit = 86_400_000L; break;
            default: return 0L;
        }
        return unit * Math.max(1, intervalNum);
    }

    @Override
    public String toString() { return rateLimitType + "/" + intervalNum + interval + "=" + limit; }
}
