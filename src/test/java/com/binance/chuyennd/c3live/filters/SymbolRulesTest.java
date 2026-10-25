package com.binance.chuyennd.c3live.filters;

import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.ExchangeInfoParser;
import com.binance.chuyennd.c3live.api.SymbolMeta;
import org.junit.Assume;
import org.junit.Test;

import java.io.File;
import java.io.InputStream;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Random;

import static org.junit.Assert.*;

/**
 * [V12 C4] Tren fixture tay (CHUA XAC MINH gia tri filter) + tuy chon dump that ~/claude_master/v12/fixtures/exchangeInfo_*.json.gz.
 * Kiem bat bien DOC LAP (remainder / so sanh truc tiep, khong goi lai ham lam tron cua lop).
 */
public class SymbolRulesTest {
    public static final long FIXTURE_NOW = 1_761_400_000_000L;

    public static ExchangeInfo fixture() throws Exception {
        try (InputStream in = SymbolRulesTest.class.getResourceAsStream("/c3live/exchangeInfo_fixture_manual.json")) {
            assertNotNull("thieu fixture", in);
            return ExchangeInfoParser.parse(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        }
    }

    static BigDecimal d(String s) { return new BigDecimal(s); }

    @Test
    public void marketBuySizingRoundsDownAndNeverExceedsBudget() throws Exception {
        SymbolRules r = new SymbolRules(fixture(), FIXTURE_NOW);
        SymbolRules.Sizing s = r.sizeMarketBuy("BTCUSDT", d("300"), d("64010.5"));
        assertTrue(s.toString(), s.isOk());
        assertEquals("0.004", s.getQty().toPlainString());
        assertEquals(0, d("256.042").compareTo(s.getNotional()));
        SymbolRules.Sizing doge = r.sizeMarketBuy("DOGEUSDT", d("100"), d("0.15234"));
        assertEquals("656", doge.getQty().toPlainString());
        assertTrue(doge.getNotional().compareTo(d("100")) <= 0);
    }

    @Test
    public void notEnoughBudgetIsSkippedNotInflated() throws Exception {
        SymbolRules r = new SymbolRules(fixture(), FIXTURE_NOW);
        // LEGACY se noi budget / ep BTC 0.002; c3_live: bo leg
        SymbolRules.Sizing z = r.sizeMarketBuy("BTCUSDT", d("50"), d("64010.5"));
        assertFalse(z.isOk());
        assertEquals(SymbolRules.SkipReason.QTY_ZERO, z.getReason());
        SymbolRules.Sizing n = r.sizeMarketBuy("BTCUSDT", d("120"), d("64010.5"));
        assertEquals(SymbolRules.SkipReason.BELOW_MIN_NOTIONAL, n.getReason());
        assertEquals("0.001", n.getQty().toPlainString());
        SymbolRules.Sizing mx = r.sizeMarketBuy("BTCUSDT", d("10000000"), d("64010.5"));
        assertEquals(SymbolRules.SkipReason.ABOVE_MAX_QTY, mx.getReason()); // MARKET_LOT_SIZE.maxQty 120 (khong phai LOT 1000)
        assertEquals(SymbolRules.SkipReason.NOT_TRADING, r.sizeMarketBuy("SETTLEDUSDT", d("100"), d("1")).getReason());
        assertEquals(SymbolRules.SkipReason.UNKNOWN_SYMBOL, r.sizeMarketBuy("NOPEUSDT", d("100"), d("1")).getReason());
        assertEquals(SymbolRules.SkipReason.BAD_INPUT, r.sizeMarketBuy("BTCUSDT", d("100"), d("0")).getReason());
        // dem minNotional 2 %: 5.05 USDT DOGE -> bi bo khi margin 1.02
        SymbolRules r2 = new SymbolRules(fixture(), FIXTURE_NOW, d("1.02"));
        assertTrue(r.sizeMarketBuy("DOGEUSDT", d("5.2"), d("0.10")).isOk());
        assertEquals(SymbolRules.SkipReason.BELOW_MIN_NOTIONAL, r2.sizeMarketBuy("DOGEUSDT", d("5.09"), d("0.10")).getReason());
    }

    @Test
    public void reduceOnlyExemptFromMinNotionalAndUsesStep() throws Exception {
        SymbolRules r = new SymbolRules(fixture(), FIXTURE_NOW);
        SymbolRules.Sizing a = r.checkQty("BTCUSDT", d("0.0019"), d("64010.5"), true, true);
        assertTrue(a.isOk());
        assertEquals("0.001", a.getQty().toPlainString());
        assertEquals(SymbolRules.SkipReason.BELOW_MIN_NOTIONAL, r.checkQty("BTCUSDT", d("0.0019"), d("64010.5"), true, false).getReason());
        assertEquals(SymbolRules.SkipReason.QTY_ZERO, r.checkQty("BTCUSDT", d("0.0005"), d("64010.5"), true, true).getReason());
        // STOP dung LOT_SIZE.maxQty (1000) thay vi MARKET (120)
        assertTrue(r.checkQty("BTCUSDT", d("500"), d("64010.5"), false, true).isOk());
        assertFalse(r.checkQty("BTCUSDT", d("500"), d("64010.5"), true, true).isOk());
        assertEquals("0.25", r.roundQtyDown("ETHUSDT", d("0.2509"), false).stripTrailingZeros().toPlainString());
    }

    @Test
    public void stopPriceForLongRoundsDownToTick() throws Exception {
        SymbolRules r = new SymbolRules(fixture(), FIXTURE_NOW);
        assertEquals("64010.5", r.roundStopPriceForLong("BTCUSDT", d("64010.59")).toPlainString());
        assertEquals("64010.5", r.roundStopPriceForLong("BTCUSDT", d("64010.5")).toPlainString());
        assertEquals("0.15234", r.roundStopPriceForLong("DOGEUSDT", d("0.152349")).toPlainString());
        assertEquals("0.0000123", r.roundStopPriceForLong("1000PEPEUSDT", d("0.00001239")).toPlainString());
        assertEquals("2412.38", r.roundPrice("ETHUSDT", d("2412.371"), RoundingMode.CEILING).toPlainString());
        assertTrue(r.isPriceInRange("BTCUSDT", d("300")));
        assertFalse(r.isPriceInRange("BTCUSDT", d("200")));
        assertNull(r.roundStopPriceForLong("NOPEUSDT", d("1")));
    }

    @Test
    public void refreshEvery6hKeepsOldOnError() throws Exception {
        ExchangeInfo ei = fixture();
        SymbolRules r = new SymbolRules(ei, FIXTURE_NOW);
        assertFalse(r.refreshIfDue(FIXTURE_NOW + SymbolRules.REFRESH_MS - 1, () -> { throw new AssertionError("chua toi han"); }));
        assertFalse(r.refreshIfDue(FIXTURE_NOW + SymbolRules.REFRESH_MS, () -> { throw new IllegalStateException("mang loi"); }));
        assertTrue(r.meta("BTCUSDT").isPresent());
        ExchangeInfo small = new ExchangeInfo(0L, null, Arrays.asList(SymbolMeta.builder("NEWUSDT").status("TRADING")
                .stepSize(d("1")).minQty(d("1")).tickSize(d("0.001")).minNotional(d("5")).build()));
        assertTrue(r.refreshIfDue(FIXTURE_NOW + SymbolRules.REFRESH_MS, () -> small));
        assertTrue(r.meta("NEWUSDT").isPresent());
        assertFalse(r.meta("BTCUSDT").isPresent());
        assertTrue(r.sizeMarketBuy("NEWUSDT", d("10"), d("1")).isOk()); // khong co MARKET_LOT_SIZE -> fallback LOT_SIZE
    }

    /** Bat bien cho MOI symbol TRADING cua 1 exchangeInfo, gia/budget ngau nhien (seed co dinh). */
    static int checkInvariants(ExchangeInfo ei, long seed) {
        SymbolRules r = new SymbolRules(ei, FIXTURE_NOW);
        Random rnd = new Random(seed);
        int n = 0;
        for (SymbolMeta m : ei.getSymbols().values()) {
            if (!"TRADING".equals(m.getStatus()) || m.getTickSize() == null || m.getTickSize().signum() <= 0) continue;
            for (int k = 0; k < 40; k++) {
                BigDecimal price = BigDecimal.valueOf(Math.pow(10, -6 + rnd.nextDouble() * 11)).setScale(12, RoundingMode.DOWN);
                price = price.divide(m.getTickSize(), 0, RoundingMode.DOWN).multiply(m.getTickSize());
                if (price.signum() <= 0) price = m.getTickSize();
                BigDecimal budget = BigDecimal.valueOf(5 + rnd.nextDouble() * 1995).setScale(2, RoundingMode.DOWN);
                SymbolRules.Sizing s = r.sizeMarketBuy(m.getSymbol(), budget, price);
                n++;
                if (!s.isOk()) { assertNotNull(s.getReason()); continue; }
                BigDecimal step = m.getMarketStepSize() != null && m.getMarketStepSize().signum() > 0 ? m.getMarketStepSize() : m.getStepSize();
                BigDecimal minQ = m.getMarketMinQty() != null ? m.getMarketMinQty() : m.getMinQty();
                BigDecimal maxQ = m.getMarketMaxQty() != null ? m.getMarketMaxQty() : m.getMaxQty();
                String ctx = m.getSymbol() + " budget=" + budget + " price=" + price + " qty=" + s.getQty();
                assertEquals(ctx, 0, s.getQty().remainder(step).signum());
                BigDecimal notional = s.getQty().multiply(price);
                assertTrue(ctx, notional.compareTo(budget) <= 0);
                assertTrue(ctx, budget.subtract(notional).compareTo(step.multiply(price)) < 0); // lam tron xuong DUNG 1 buoc
                if (m.getMinNotional() != null) assertTrue(ctx, notional.compareTo(m.getMinNotional()) >= 0);
                if (minQ != null) assertTrue(ctx, s.getQty().compareTo(minQ) >= 0);
                if (maxQ != null && maxQ.signum() > 0) assertTrue(ctx, s.getQty().compareTo(maxQ) <= 0);
            }
        }
        return n;
    }

    @Test
    public void invariantsOnManualFixture() throws Exception {
        assertTrue(checkInvariants(fixture(), 42L) > 500);
    }

    /** Dump that do owner chay deploy/dump_exchangeinfo.sh; chua co -> bo qua (Assume). */
    @Test
    public void invariantsOnRealDumpIfPresent() throws Exception {
        String dir = System.getProperty("c3live.fixtures", System.getProperty("user.home") + "/claude_master/v12/fixtures");
        File[] fs = new File(dir).listFiles((d, n) -> n.startsWith("exchangeInfo_") && n.endsWith(".json.gz"));
        Assume.assumeTrue("chua co dump exchangeInfo that trong " + dir, fs != null && fs.length > 0);
        Arrays.sort(fs);
        ExchangeInfo ei = ExchangeInfoParser.parseFile(fs[fs.length - 1].toPath());
        assertTrue(ei.getSymbols().size() > 100);
        assertTrue(checkInvariants(ei, 7L) > 1000);
    }
}
