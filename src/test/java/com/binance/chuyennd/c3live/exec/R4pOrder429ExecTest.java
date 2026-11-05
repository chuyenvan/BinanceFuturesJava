package com.binance.chuyennd.c3live.exec;

import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.ops.KillSwitchEngine;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/**
 * [V12 R4p Bug3 — E2E F2b] Duong PRODUCTION: executor nhan 429 tren newMarketOrder (6 lan lien tiep), xen call doc OK
 * (positions) => KillSwitchEngine (ACT) latch C3 NO_NEW_ENTRY; leg 429 van huy giu cho, khong gui lai cung cid.
 */
public class R4pOrder429ExecTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    @Test
    public void f2bExecutorOrder429WithOkReadsLatchesC3() {
        AtomicLong now = new AtomicLong(1_792_900_000_000L);
        KillSwitchEngine.Params p = new KillSwitchEngine.Params();
        p.latchFile = new File(tmp.getRoot(), "run/killsw_latch.json");
        p.resetFile = new File(tmp.getRoot(), "run/killsw_reset.req");
        KillSwitchEngine ks = new KillSwitchEngine(KillSwitchEngine.Mode.ACT, "act", new KillSwitchEngine.Sink() {
            public void info(String m) { }
            public void warn(String m) { }
        }, null, () -> 10000d, () -> 0.60f, now.get(), p);
        C3LiveOrderExecutor.ApiObserver api = new C3LiveOrderExecutor.ApiObserver() {
            @Override
            public void onApiResult(String a, boolean ok) {
                ks.onApiResult(now.get(), a, ok);
            }

            @Override
            public void onOrderResult(String a, boolean ok, boolean rl) {
                ks.onOrderResult(now.get(), a, ok, rl);
            }
        };
        MockExchangeGateway gw = new MockExchangeGateway();
        LiveBookC3 book = new LiveBookC3(null, 1.0);
        C3LiveOrderExecutor ex = new C3LiveOrderExecutor(gw, book, api, null, now::get, ms -> now.addAndGet(ms), 10_000L, 3,
                Runnable::run);
        for (int i = 0; i < 6; i++) gw.failNext("newMarketOrder",
                new GatewayException(ErrorKind.RATE_LIMIT, 429, -1003, "Too many requests (gia lap)", true, 0L, null));
        for (int i = 0; i < 6; i++) {
            String sym = "S" + i + "USDT";
            String cid = "c3-" + sym + "-100-0";
            gw.setPrice(sym, BigDecimal.ONE);
            assertTrue(book.reserve(sym, cid, 0, 100, "BIG_DOWN", 1.0, BigDecimal.TEN, 1.0, now.get()));
            gw.positions();
            api.onApiResult("positions", true);   // call doc OK xen giua (truoc fix: reset bo dem C3)
            ex.place(cid);
            assertFalse("429 => huy giu cho", book.leg(cid).isPresent());
            now.addAndGet(1_000L);
        }
        assertEquals("1 lan gui / leg, khong gui lai", 6, gw.calls("newMarketOrder"));
        assertTrue("C3 phai latch: " + ks.latchCodes(), ks.latchCodes().contains("C3"));
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, ks.requiredAction());
    }
}
