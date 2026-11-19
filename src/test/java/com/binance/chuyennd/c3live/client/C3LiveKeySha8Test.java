package com.binance.chuyennd.c3live.client;

import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.rate.RateGuard;
import org.junit.Test;

import static org.junit.Assert.*;

/** [W3A muc 2] sha8 = 8 hex dau sha256(API KEY); khong lo key/secret. */
public class C3LiveKeySha8Test {

    @Test
    public void sha8_vectorChuan() {
        // sha256("abc") = ba7816bf 8f01cfea ...
        assertEquals("ba7816bf", C3LiveKeys.sha8("abc"));
        C3LiveKeys k = C3LiveKeys.ofForTest("abc", "secret_w3a");
        assertEquals("ba7816bf", k.apiKeySha8());
        assertFalse(k.toString().contains("abc"));
    }

    @Test
    public void client_keySha8_khongPhaiKey() {
        String key = "W3AKEYabcdefghijklmnopqrstuvwxyz0123456789";
        C3LiveClientConfig cfg = C3LiveClientConfig.builder().baseUrl("http://127.0.0.1:9").connectTimeoutMs(100L)
                .rateMaxWaitMs(0L).build();
        C3LiveClient c = new C3LiveClient(cfg, C3LiveKeys.ofForTest(key, "s3cr3t_w3a"), RateGuard.defaults(),
                new OrderAuditLog(OrderAuditLog.LIVE_TAG, l -> { }));
        String s = c.keySha8();
        assertEquals(C3LiveKeys.sha8(key), s);
        assertEquals(8, s.length());
        assertFalse(key.contains(s));
    }
}
