package com.binance.chuyennd.c3live.universe;

import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.SymbolMeta;
import com.binance.chuyennd.c3live.filters.SymbolRulesTest;
import org.junit.Test;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

import static org.junit.Assert.*;

/**
 * [V12 P0-U1..U4] Tren fixture tay (CHUA XAC MINH truong TradFi): TRADING/SETTLING/CLOSE/PENDING, quarterly, USDC quote,
 * TradFi (contractType / underlyingType / subType / danh sach), non-ASCII, delist &lt; 7 ngay, EXCLUDE POWR/MDT, thieu underlyingType.
 */
public class SymbolUniverseLiveTest {
    static final long NOW = SymbolRulesTest.FIXTURE_NOW;
    static final String CN = "币安人生USDT";
    final List<String> alerts = new ArrayList<>();

    static SymbolUniverseLive.Config cfg(String exclude, String allowNonAscii, String tradfiList) {
        Map<String, String> env = new HashMap<>();
        env.put("UNIVERSE_EXCLUDE", exclude);
        env.put("LIVE_C3_ALLOW_NONASCII", allowNonAscii);
        env.put("UNIVERSE_TRADFI_LIST", tradfiList);
        return SymbolUniverseLive.Config.fromEnv(env::get);
    }

    SymbolUniverseLive universe(SymbolUniverseLive.Config c) throws Exception {
        ExchangeInfo ei = SymbolRulesTest.fixture();
        return new SymbolUniverseLive(c, () -> ei, alerts::add);
    }

    static Set<String> set(String... s) { return new TreeSet<>(Arrays.asList(s)); }

    @Test
    public void fixtureClassification() throws Exception {
        SymbolUniverseLive u = universe(cfg("BTCDOMUSDT:intentional,USDCUSDT:intentional,POWRUSDT,MDTUSDT", "0", "KODEX200USDT"));
        UniverseDiff d = u.refresh(NOW);
        assertNotNull(d);
        assertEquals(22, d.getListed());
        assertEquals(19, d.getAlive());
        assertEquals(set("BTCUSDT", "ETHUSDT", "DOGEUSDT", "1000PEPEUSDT", CN, "DELISTUSDT", "SOONUSDT", "RELISTUSDT", "NOUTUSDT"),
                u.tradableSymbols());
        assertEquals(set("TSLAUSDT", "IBKRUSDT", "XAUUSDT", "KODEX200USDT"), d.getTradfiExcluded());
        assertEquals("contractType=TRADIFI_PERPETUAL", u.classification("TSLAUSDT").get().getRule());
        assertEquals("underlyingType=EQUITY", u.classification("IBKRUSDT").get().getRule());
        assertEquals("underlyingSubType=TradFi", u.classification("XAUUSDT").get().getRule());
        assertEquals("LIST", u.classification("KODEX200USDT").get().getRule());
        assertEquals(SymbolUniverseLive.Reason.NOT_PERPETUAL, u.notTradableReason("BTCUSDT_251226").get());
        assertEquals(SymbolUniverseLive.Reason.NOT_USDT, u.notTradableReason("BTCUSDC").get());
        assertEquals(SymbolUniverseLive.Reason.NOT_TRADING, u.notTradableReason("SETTLEDUSDT").get());
        assertEquals(SymbolUniverseLive.Reason.NOT_TRADING, u.notTradableReason("CLOSEDUSDT").get());
        assertEquals(SymbolUniverseLive.Reason.NOT_TRADING, u.notTradableReason("PENDUSDT").get());
        assertEquals(SymbolUniverseLive.Reason.EXCLUDED, u.notTradableReason("POWRUSDT").get());
        assertEquals(SymbolUniverseLive.Reason.NOT_LISTED, u.notTradableReason("NOPEUSDT").get());
        // canh bao EXCLUDE van TRADING: POWR, MDT (BTCDOM/USDC co :intentional -> khong canh bao)
        assertEquals(set("MDTUSDT", "POWRUSDT"), d.getExcludeStillTrading());
        assertEquals(1, alerts.size());
        assertTrue(alerts.get(0).contains("POWRUSDT") && alerts.get(0).contains("MDTUSDT"));
        // alive van true cho TradFi / EXCLUDE (de quan ly vi the cu)
        assertTrue(u.isAlive("TSLAUSDT"));
        assertTrue(u.isAlive("POWRUSDT"));
        assertFalse(u.isTradable("TSLAUSDT"));
        // NOUT thieu underlyingType -> trong U nhung danh dau chua xac minh
        assertEquals(set("NOUTUSDT"), d.getUnverified());
        assertFalse(u.classification("NOUTUSDT").get().isVerified());
    }

    @Test
    public void buyableRules() throws Exception {
        SymbolUniverseLive u = universe(cfg("BTCDOMUSDT:intentional,USDCUSDT:intentional,POWRUSDT,MDTUSDT", "0", "KODEX200USDT"));
        UniverseDiff d = u.refresh(NOW);
        assertTrue(u.isBuyable("BTCUSDT", NOW));
        assertTrue("delivery +8 ngay: van mua", u.isBuyable("SOONUSDT", NOW));
        assertFalse("delivery +3 ngay: khong mua", u.isBuyable("DELISTUSDT", NOW));
        assertTrue(u.whyNotBuyable("DELISTUSDT", NOW).get().startsWith("DELIVERY_SOON"));
        assertEquals(set("DELISTUSDT"), d.getDeliverySoon());
        assertTrue(u.isTradable(CN));
        assertFalse(u.isBuyable(CN, NOW));
        assertEquals("NON_ASCII", u.whyNotBuyable(CN, NOW).get());
        assertEquals(set(CN), d.getNonAsciiTradable());
        assertTrue(u.whyNotBuyable("XAUUSDT", NOW).get().startsWith("TRADFI"));
        assertEquals(7, d.getBuyable());
        // ngay sau: SOON (+8d) vao vung 7 ngay
        u.apply(SymbolRulesTest.fixture(), NOW + 86_400_000L + 1);
        assertEquals("DELIVERY_SOON deliveryDate=1762091200000", u.whyNotBuyable("SOONUSDT", NOW + 86_400_000L + 1).get());
        // snapshot cu > 60 phut -> khong mua (fail-closed)
        assertFalse(u.isBuyable("BTCUSDT", NOW + 86_400_000L + 1 + 61 * 60_000L));
        assertTrue(u.whyNotBuyable("BTCUSDT", NOW + 86_400_000L + 1 + 61 * 60_000L).get().startsWith("STALE"));
        assertTrue(u.isTradable("BTCUSDT"));
    }

    @Test
    public void marketIndexMembersExcludeTradFiAndNonAsciiByDefault() throws Exception {
        SymbolUniverseLive u = universe(cfg("BTCDOMUSDT:intentional,USDCUSDT:intentional", "0", ""));
        u.refresh(NOW);
        Set<String> m = u.marketIndexMembers();
        for (String t : new String[]{"TSLAUSDT", "IBKRUSDT", "XAUUSDT", "BTCDOMUSDT", "USDCUSDT", "BTCUSDT_251226", "BTCUSDC", "SETTLEDUSDT", CN}) {
            assertFalse(t, m.contains(t));
        }
        assertTrue(m.contains("POWRUSDT")); // DIED cu chan nham - nay vao U
        assertTrue(m.contains("MDTUSDT"));
        assertTrue(m.contains("KODEX200USDT")); // khong co nhan + khong trong danh sach -> lot (rui ro da ghi: can dump that)
        assertTrue(alerts.isEmpty());
        SymbolUniverseLive u2 = universe(cfg("", "1", ""));
        u2.refresh(NOW);
        assertTrue(u2.marketIndexMembers().contains(CN));
        assertTrue(u2.isBuyable(CN, NOW));
        assertTrue(u2.isTradable("BTCDOMUSDT")); // UNIVERSE_EXCLUDE="" -> khong loai gi
    }

    @Test
    public void diffAddedRemovedAndAlertDedupe() throws Exception {
        SymbolUniverseLive u = universe(cfg("POWRUSDT", "0", ""));
        u.refresh(NOW);
        assertEquals(1, alerts.size());
        ExchangeInfo base = SymbolRulesTest.fixture();
        List<SymbolMeta> syms = new ArrayList<>(base.getSymbols().values());
        syms.removeIf(s -> s.getSymbol().equals("RELISTUSDT"));
        syms.add(SymbolMeta.builder("NEWCOINUSDT").status("TRADING").contractType("PERPETUAL").quoteAsset("USDT").underlyingType("COIN")
                .deliveryDate(4133404800000L).stepSize(BigDecimal.ONE).tickSize(new BigDecimal("0.0001")).build());
        syms.add(SymbolMeta.builder("AAPLUSDT").status("TRADING").contractType("PERPETUAL").quoteAsset("USDT").underlyingType("EQUITY")
                .deliveryDate(4133404800000L).build());
        UniverseDiff d2 = u.apply(new ExchangeInfo(NOW + 900_000L, null, syms), NOW + 900_000L);
        assertEquals(set("NEWCOINUSDT"), d2.getAdded());
        assertEquals(set("RELISTUSDT"), d2.getRemoved());
        assertEquals(set("AAPLUSDT"), d2.getNewlyTradFi());
        assertTrue(d2.getTradfiExcluded().contains("TSLAUSDT"));
        assertEquals("canh bao EXCLUDE khong lap lai khi tap khong doi", 1, alerts.size());
        assertTrue(d2.summary().startsWith("[UNIVERSE] listed=23"));
        assertSame(d2, u.diff());
    }

    @Test
    public void refreshErrorKeepsSnapshotAndRefreshEvery15m() throws Exception {
        ExchangeInfo ei = SymbolRulesTest.fixture();
        final int[] calls = {0};
        final boolean[] fail = {false};
        SymbolUniverseLive u = new SymbolUniverseLive(cfg("", "0", ""), () -> {
            calls[0]++;
            if (fail[0]) throw new IllegalStateException("REST loi");
            return ei;
        }, alerts::add);
        assertFalse(u.isTradable("BTCUSDT"));
        assertEquals("NO_SNAPSHOT", u.whyNotBuyable("BTCUSDT", NOW).get());
        assertNotNull(u.refreshIfDue(NOW));
        assertNull(u.refreshIfDue(NOW + SymbolUniverseLive.REFRESH_MS - 1));
        assertEquals(1, calls[0]);
        fail[0] = true;
        assertNull(u.refreshIfDue(NOW + SymbolUniverseLive.REFRESH_MS));
        assertEquals(2, calls[0]);
        assertTrue(u.isTradable("BTCUSDT"));
        assertEquals(NOW, u.loadedAtMs());
    }

    @Test
    public void defaultsAndClassifierRules() {
        SymbolUniverseLive.Config d = SymbolUniverseLive.Config.defaults();
        assertEquals(Boolean.TRUE, d.getExclude().get("BTCDOMUSDT"));
        assertEquals(Boolean.TRUE, d.getExclude().get("USDCUSDT"));
        assertFalse(d.getExclude().containsKey("POWRUSDT"));
        assertFalse(d.isAllowNonAscii());
        TradFiClassifier c = TradFiClassifier.defaults();
        SymbolMeta rwa = SymbolMeta.builder("ONDOUSDT").contractType("PERPETUAL").underlyingType("COIN")
                .underlyingSubType(Collections.singletonList("RWA")).build();
        assertFalse("RWA la token crypto", c.classify(rwa).isTradFi());
        assertFalse(c.classify(SymbolMeta.builder("BTCDOMUSDT").contractType("PERPETUAL").underlyingType("INDEX").build()).isTradFi());
        assertTrue(c.classify(SymbolMeta.builder("EURUSDT").contractType("PERPETUAL").underlyingType("COIN")
                .underlyingSubType(Collections.singletonList("Forex")).build()).isTradFi());
        assertTrue(c.classify(SymbolMeta.builder("X").contractType("TradFi_Perpetual").underlyingType("COIN").build()).isTradFi());
        assertTrue(SymbolUniverseLive.isAsciiSymbol("1000PEPEUSDT"));
        assertFalse(SymbolUniverseLive.isAsciiSymbol(CN));
        assertFalse(SymbolUniverseLive.isAsciiSymbol("A B"));
        assertEquals(new HashSet<>(Arrays.asList("A", "B")), SymbolUniverseLive.Config.parseExclude(" A , B:intentional ,").keySet());
    }
}
