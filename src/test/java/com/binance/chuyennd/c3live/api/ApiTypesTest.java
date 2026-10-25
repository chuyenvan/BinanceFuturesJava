package com.binance.chuyennd.c3live.api;

import org.junit.Test;

import java.math.BigDecimal;

import static org.junit.Assert.*;

/** [V12] DTO / parser / clientOrderId. */
public class ApiTypesTest {

    static final String JSON = "{\"serverTime\":1761400000000,\"rateLimits\":["
            + "{\"rateLimitType\":\"REQUEST_WEIGHT\",\"interval\":\"MINUTE\",\"intervalNum\":1,\"limit\":2400},"
            + "{\"rateLimitType\":\"ORDERS\",\"interval\":\"MINUTE\",\"intervalNum\":1,\"limit\":1200},"
            + "{\"rateLimitType\":\"ORDERS\",\"interval\":\"SECOND\",\"intervalNum\":10,\"limit\":300}],"
            + "\"symbols\":[{\"symbol\":\"BTCUSDT\",\"pair\":\"BTCUSDT\",\"contractType\":\"PERPETUAL\",\"status\":\"TRADING\","
            + "\"baseAsset\":\"BTC\",\"quoteAsset\":\"USDT\",\"marginAsset\":\"USDT\",\"underlyingType\":\"COIN\","
            + "\"underlyingSubType\":[\"PoW\"],\"onboardDate\":1569398400000,\"deliveryDate\":4133404800000,"
            + "\"filters\":[{\"filterType\":\"PRICE_FILTER\",\"minPrice\":\"261.10\",\"maxPrice\":\"809484\",\"tickSize\":\"0.10\"},"
            + "{\"filterType\":\"LOT_SIZE\",\"stepSize\":\"0.001\",\"maxQty\":\"1000\",\"minQty\":\"0.001\"},"
            + "{\"filterType\":\"MARKET_LOT_SIZE\",\"stepSize\":\"0.001\",\"maxQty\":\"120\",\"minQty\":\"0.001\"},"
            + "{\"filterType\":\"MAX_NUM_ORDERS\",\"limit\":200},{\"filterType\":\"MIN_NOTIONAL\",\"notional\":\"100\"}]},"
            + "{\"symbol\":\"OLDUSDT\",\"status\":\"TRADING\",\"filters\":[[{\"filterType\":\"PRICE_FILTER\",\"tickSize\":\"0.0010\"}]]}]}";

    @Test
    public void parsesExchangeInfo() {
        ExchangeInfo ei = ExchangeInfoParser.parse(JSON);
        assertEquals(1761400000000L, ei.getServerTime());
        assertEquals(3, ei.getRateLimits().size());
        assertEquals(2400, ei.rateLimit("REQUEST_WEIGHT", 60_000L).get().getLimit());
        assertEquals(300, ei.rateLimit("ORDERS", 10_000L).get().getLimit());
        SymbolMeta b = ei.symbol("BTCUSDT").get();
        assertEquals(0, new BigDecimal("0.1").compareTo(b.getTickSize()));
        assertEquals(0, new BigDecimal("0.001").compareTo(b.getStepSize()));
        assertEquals(0, new BigDecimal("120").compareTo(b.getMarketMaxQty()));
        assertEquals(0, new BigDecimal("100").compareTo(b.getMinNotional()));
        assertEquals("COIN", b.getUnderlyingType());
        assertEquals(4133404800000L, b.getDeliveryDate());
        assertEquals(1, b.getUnderlyingSubType().size());
        // file pin cu: filters long nhau van doc duoc
        assertEquals(0, new BigDecimal("0.001").compareTo(ei.symbol("OLDUSDT").get().getTickSize()));
        assertNull(ei.symbol("OLDUSDT").get().getContractType());
    }

    @Test
    public void clientOrderIdRules() {
        assertTrue(ClientOrderIds.isValid("c3-BTCUSDT-29123456-1"));
        assertFalse(ClientOrderIds.isValid(""));
        assertFalse(ClientOrderIds.isValid(null));
        assertFalse(ClientOrderIds.isValid("a b"));
        assertFalse(ClientOrderIds.isValid("0123456789012345678901234567890123456"));
        assertTrue(ClientOrderIds.isValid("012345678901234567890123456789012345"));
        String nonAscii = "币安人生USDT";
        assertFalse(ClientOrderIds.isValid("c3-" + nonAscii));
        String tok = ClientOrderIds.symbolToken(nonAscii);
        assertTrue(tok.startsWith("x"));
        assertEquals(11, tok.length());
        assertEquals(tok, ClientOrderIds.symbolToken(nonAscii));
        assertTrue(ClientOrderIds.isValid("c3-" + tok + "-29123456-1"));
        assertEquals("BTCUSDT", ClientOrderIds.symbolToken("BTCUSDT"));
    }

    @Test
    public void enumsParseSafely() {
        assertEquals(OrderStatus.UNKNOWN, OrderStatus.parse("WEIRD"));
        assertEquals(OrderStatus.FILLED, OrderStatus.parse("filled"));
        assertTrue(OrderStatus.FINISHED.isFinal());
        assertFalse(OrderStatus.NEW.isFinal());
        assertEquals(Side.SELL, Side.BUY.opposite());
        assertEquals(SymbolConfig.CROSSED, SymbolConfig.normalizeMarginType("cross"));
        assertEquals(60_000L, new RateLimitSpec("ORDERS", "MINUTE", 1, 1200).windowMs());
    }
}
