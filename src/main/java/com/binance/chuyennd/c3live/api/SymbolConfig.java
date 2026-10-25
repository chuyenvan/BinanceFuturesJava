package com.binance.chuyennd.c3live.api;

import java.util.Locale;

/** [V12 C5] Cau hinh symbol tren tai khoan (GET /fapi/v1/symbolConfig): marginType CROSSED|ISOLATED, leverage. */
public final class SymbolConfig {
    public static final String CROSSED = "CROSSED";
    public static final String ISOLATED = "ISOLATED";

    private final String symbol;
    private final String marginType;
    private final int leverage;

    public SymbolConfig(String symbol, String marginType, int leverage) {
        this.symbol = symbol;
        this.marginType = normalizeMarginType(marginType);
        this.leverage = leverage;
    }

    /** "cross"/"CROSSED" -> CROSSED; "isolated"/"ISOLATED" -> ISOLATED; khac giu nguyen (upper). */
    public static String normalizeMarginType(String m) {
        if (m == null) return null;
        String u = m.trim().toUpperCase(Locale.ROOT);
        if ("CROSS".equals(u) || CROSSED.equals(u)) return CROSSED;
        return u;
    }

    public String getSymbol() { return symbol; }
    public String getMarginType() { return marginType; }
    public int getLeverage() { return leverage; }
    public boolean isCrossed() { return CROSSED.equals(marginType); }

    @Override
    public String toString() { return "SymbolConfig{" + symbol + " " + marginType + " x" + leverage + "}"; }
}
