package com.binance.chuyennd.c3live.api;

/** [V12] Chieu lenh (one-way mode, khong dung positionSide). */
public enum Side {
    BUY, SELL;

    public Side opposite() { return this == BUY ? SELL : BUY; }

    public static Side parse(String s) {
        if (s == null) return null;
        String u = s.trim().toUpperCase(java.util.Locale.ROOT);
        if ("BUY".equals(u)) return BUY;
        if ("SELL".equals(u)) return SELL;
        return null;
    }
}
