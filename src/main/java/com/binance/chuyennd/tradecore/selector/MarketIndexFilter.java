package com.binance.chuyennd.tradecore.selector;

import java.util.function.Predicate;

/**
 * [V12 c3_live P0-U3] Bo loc thanh vien chi so thi truong (ALT_EW cua TS_MKT_EXT X14) — chi c3_live dat (loai TradFi,
 * {@code SymbolUniverseLive.marketIndexMembers()}). Mac dinh null = KHONG loc => c3_shadow / sim y nguyen.
 * Tach rieng de duong khac khong tham chieu {@code TsMktExt} (TsMktExtTest.realPositionPathDoesNotReferenceTsExt).
 */
public final class MarketIndexFilter {

    private static volatile Predicate<String> filter = null;

    private MarketIndexFilter() {
    }

    public static void set(Predicate<String> f) {
        filter = f;
    }

    public static Predicate<String> get() {
        return filter;
    }
}
