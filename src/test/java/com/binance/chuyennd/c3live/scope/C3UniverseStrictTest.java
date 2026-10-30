package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.SymbolMeta;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.universe.SymbolUniverseLive;
import org.junit.Test;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Optional;

import static org.junit.Assert.*;

/**
 * [V12 R4 R7] (g) universe c3_live chat: TRADING + PERPETUAL + USDT + underlyingType COIN; loai TradFi (contractType TRADIFI /
 * underlyingType EQUITY...), INDEX, PREMARKET, chua phan loai (underlyingType thieu); nguon exchangeInfo tho thieu truong /
 * &lt; 200 TradFi => fail-fast (khong nhan snapshot).
 */
public class C3UniverseStrictTest {

    static final long NOW = 1_792_900_020_000L;

    static SymbolMeta with(String sym, String contractType, String underlyingType) {
        SymbolMeta b = C3LiveFixtures.crypto(sym);
        return SymbolMeta.builder(sym).pair(sym).status("TRADING").contractType(contractType).baseAsset(sym.replace("USDT", ""))
                .quoteAsset("USDT").marginAsset("USDT").underlyingType(underlyingType).underlyingSubType(Collections.emptyList())
                .onboardDate(b.getOnboardDate()).deliveryDate(b.getDeliveryDate()).tickSize(b.getTickSize())
                .minPrice(new BigDecimal("0.0001")).maxPrice(new BigDecimal("100000")).stepSize(new BigDecimal("0.1"))
                .minQty(new BigDecimal("0.1")).maxQty(new BigDecimal("10000000")).marketStepSize(new BigDecimal("0.1"))
                .marketMinQty(new BigDecimal("0.1")).marketMaxQty(new BigDecimal("1000000")).minNotional(new BigDecimal("5"))
                .build();
    }

    static ExchangeInfo source(int tradfi, boolean dropUnderlying) {
        List<SymbolMeta> l = new ArrayList<>();
        for (int i = 0; i < 20; i++) {
            l.add(dropUnderlying ? with(C3LiveFixtures.sym(i), "PERPETUAL", null) : C3LiveFixtures.crypto(C3LiveFixtures.sym(i)));
        }
        for (int i = 0; i < tradfi; i++) l.add(C3LiveFixtures.tradfi(String.format("TF%03dUSDT", i)));
        if (!dropUnderlying) {
            l.add(with("ALLUSDT", "PERPETUAL", "INDEX"));
            l.add(with("PREDICTUSDT", "PERPETUAL", "PREMARKET"));
            l.add(with("NEWCOINUSDT", "PERPETUAL", null));
            l.add(with("GOLDUSDT", "PERPETUAL", "COMMODITY"));
            l.add(with("NVDAUSDT", "TRADIFI_PERPETUAL", "COIN"));
        }
        return new ExchangeInfo(0L, Collections.emptyList(), l);
    }

    static SymbolUniverseLive strict(List<String> alerts) {
        return new SymbolUniverseLive(SymbolUniverseLive.Config.defaults().strictCoin(), () -> null, alerts::add);
    }

    @Test
    public void strictUniverseOnlyCoinPerpetualUsdt() {
        List<String> alerts = new ArrayList<>();
        SymbolUniverseLive u = strict(alerts);
        assertNotNull(u.apply(source(210, false), NOW));
        assertTrue(u.isBuyable(C3LiveFixtures.sym(3), NOW));
        assertFalse("TradFi contractType", u.isBuyable("TF001USDT", NOW));
        assertFalse("TradFi contractType du underlyingType COIN", u.isBuyable("NVDAUSDT", NOW));
        assertFalse("COMMODITY", u.isBuyable("GOLDUSDT", NOW));
        assertEquals(Optional.of(SymbolUniverseLive.Reason.INDEX), u.notTradableReason("ALLUSDT"));
        assertEquals(Optional.of(SymbolUniverseLive.Reason.NOT_COIN), u.notTradableReason("PREDICTUSDT"));
        assertEquals("chua phan loai => loai (fail-closed)", Optional.of(SymbolUniverseLive.Reason.UNCLASSIFIED),
                u.notTradableReason("NEWCOINUSDT"));
        assertEquals(20, u.tradableSymbols().size());
        assertFalse(u.marketIndexMembers().contains("PREDICTUSDT"));
        assertNull(u.lastSourceError());
        // khong chat (canary / mac dinh cu): PREMARKET + chua phan loai van tradable (hanh vi cu giu nguyen)
        SymbolUniverseLive old = new SymbolUniverseLive(SymbolUniverseLive.Config.defaults(), () -> null, x -> { });
        old.apply(source(210, false), NOW);
        assertTrue(old.isTradable("PREDICTUSDT"));
        assertTrue(old.isTradable("NEWCOINUSDT"));
    }

    @Test
    public void rawSourceWithoutFieldsOrTooFewTradFiFailsFast() {
        List<String> alerts = new ArrayList<>();
        SymbolUniverseLive u = strict(alerts);
        assertNull("thieu truong underlyingType => tu choi", u.apply(source(0, true), NOW));
        assertFalse(u.hasSnapshot());
        assertTrue(u.lastSourceError(), u.lastSourceError().contains("underlyingType"));
        assertFalse(u.isBuyable(C3LiveFixtures.sym(1), NOW));
        assertTrue(alerts.toString(), alerts.toString().contains("fail-fast"));
        assertNull("< 200 TradFi => khong phai exchangeInfo tho day du", u.apply(source(150, false), NOW));
        assertFalse(u.hasSnapshot());
        // nguon tot => nhan; sau do nguon xau => giu snapshot cu (het han maxStale => khong mua)
        assertNotNull(u.apply(source(200, false), NOW));
        assertTrue(u.isBuyable(C3LiveFixtures.sym(1), NOW));
        assertNull(u.apply(source(10, false), NOW + 60_000L));
        assertTrue(u.isBuyable(C3LiveFixtures.sym(1), NOW + 60_000L));
        assertFalse("snapshot cu > 60' => STALE", u.isBuyable(C3LiveFixtures.sym(1), NOW + 61L * 60_000L));
        assertEquals(15L * 60_000L, SymbolUniverseLive.REFRESH_MS);
    }
}
