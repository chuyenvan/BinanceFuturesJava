package com.binance.chuyennd.c3live.entry;

import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.SymbolMeta;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Fixture exchangeInfo tong hop cho test c3_live (KHONG phai dump that — truong TradFi theo fixture tay v12lib). */
public final class C3LiveFixtures {

    private C3LiveFixtures() {
    }

    public static SymbolMeta crypto(String sym) {
        return SymbolMeta.builder(sym).pair(sym).status("TRADING").contractType("PERPETUAL").baseAsset(sym.replace("USDT", ""))
                .quoteAsset("USDT").marginAsset("USDT").underlyingType("COIN").underlyingSubType(Collections.emptyList())
                .onboardDate(1_600_000_000_000L).deliveryDate(4_133_404_800_000L).tickSize(new BigDecimal("0.0001"))
                .minPrice(new BigDecimal("0.0001")).maxPrice(new BigDecimal("100000")).stepSize(new BigDecimal("0.1"))
                .minQty(new BigDecimal("0.1")).maxQty(new BigDecimal("10000000")).marketStepSize(new BigDecimal("0.1"))
                .marketMinQty(new BigDecimal("0.1")).marketMaxQty(new BigDecimal("1000000")).minNotional(new BigDecimal("5"))
                .build();
    }

    public static SymbolMeta tradfi(String sym) {
        return SymbolMeta.builder(sym).pair(sym).status("TRADING").contractType("TRADIFI_PERPETUAL")
                .baseAsset(sym.replace("USDT", "")).quoteAsset("USDT").marginAsset("USDT").underlyingType("EQUITY")
                .underlyingSubType(Collections.singletonList("TradFi")).onboardDate(1_600_000_000_000L)
                .deliveryDate(4_133_404_800_000L).tickSize(new BigDecimal("0.01")).minPrice(new BigDecimal("0.01"))
                .maxPrice(new BigDecimal("100000")).stepSize(new BigDecimal("0.01")).minQty(new BigDecimal("0.01"))
                .maxQty(new BigDecimal("100000")).marketStepSize(new BigDecimal("0.01")).marketMinQty(new BigDecimal("0.01"))
                .marketMaxQty(new BigDecimal("10000")).minNotional(new BigDecimal("5")).build();
    }

    /** n symbol crypto C00USDT..C(n-1)USDT + TSLAUSDT (TradFi). */
    public static ExchangeInfo info(int n) {
        List<SymbolMeta> l = new ArrayList<>();
        for (int i = 0; i < n; i++) l.add(crypto(sym(i)));
        l.add(tradfi("TSLAUSDT"));
        return new ExchangeInfo(0L, Collections.emptyList(), l);
    }

    public static String sym(int i) {
        return String.format("C%02dUSDT", i);
    }
}
