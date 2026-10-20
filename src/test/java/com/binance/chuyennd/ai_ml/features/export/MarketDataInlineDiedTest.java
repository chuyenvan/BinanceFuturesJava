package com.binance.chuyennd.ai_ml.features.export;

import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.junit.Test;

import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import static org.junit.Assert.*;

/** [V11 §6] MarketDataInlineGenerator voi tap died tuong minh (khop nguon sim) — mac dinh van Constants.diedSymbol. */
public class MarketDataInlineDiedTest {
    static final long MIN = 60_000L;

    static Map<String, KlineObjectSimple> snap(long t, boolean crashS0) {
        Map<String, KlineObjectSimple> m = new HashMap<>();
        for (int i = 0; i < 60; i++) {
            KlineObjectSimple k = new KlineObjectSimple();
            k.startTime = t;
            k.priceOpen = 100f;
            k.priceClose = (i == 0 && crashS0) ? 90f : 100f + (i % 7) * 0.1f - 0.3f;
            k.maxPrice = Math.max(k.priceOpen, k.priceClose) + 0.05f;
            k.minPrice = Math.min(k.priceOpen, k.priceClose) - 0.05f;
            k.totalUsdt = 1000f + i;
            m.put(i == 59 ? "BTCUSDT" : "S" + i + "USDT", k);
        }
        return m;
    }

    @Test
    public void explicitDiedSetChangesOnlyDiedCoins() {
        Set<String> none = Collections.emptySet();
        Set<String> s0 = new HashSet<>(Collections.singletonList("S0USDT"));
        MarketDataInlineGenerator a = new MarketDataInlineGenerator(none);
        MarketDataInlineGenerator b = new MarketDataInlineGenerator(s0);
        MarketDataObject ra = null, rb = null;
        for (int t = 0; t < 16; t++) {
            ra = a.update(snap(t * MIN, t == 15));
            rb = b.update(snap(t * MIN, t == 15));
        }
        assertNotNull(ra);
        assertNotNull(rb);
        assertTrue(ra.rateDownAvg < rb.rateDownAvg);   // S0 sap -10 % chi vao trung binh khi KHONG la died
        // phut khong co coin died bat thuong: hai ban bang nhau
        MarketDataInlineGenerator c = new MarketDataInlineGenerator(none);
        MarketDataInlineGenerator d = new MarketDataInlineGenerator(new HashSet<>(Collections.singletonList("NOTEXISTUSDT")));
        MarketDataObject rc = null, rd = null;
        for (int t = 0; t < 16; t++) {
            rc = c.update(snap(t * MIN, false));
            rd = d.update(snap(t * MIN, false));
        }
        assertEquals(Float.floatToIntBits(rc.rateDownAvg), Float.floatToIntBits(rd.rateDownAvg));
        assertEquals(Float.floatToIntBits(rc.rateDown15MAvg), Float.floatToIntBits(rd.rateDown15MAvg));
    }

    @Test
    public void parseDiedLikeConstants() throws Exception {
        Class<?> c = Class.forName("com.binance.chuyennd.ai_ml.features.export.entry.LiveFeaturePipeline");
        java.lang.reflect.Method m = c.getDeclaredMethod("parseDied", String.class);
        m.setAccessible(true);
        @SuppressWarnings("unchecked")
        Set<String> s = (Set<String>) m.invoke(null, "BTCDOM, USDC,ETHUSDT,");
        assertEquals(new HashSet<>(java.util.Arrays.asList("BTCDOMUSDT", "USDCUSDT", "ETHUSDT")), s);
    }
}
