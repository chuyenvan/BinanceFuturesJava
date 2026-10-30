package com.binance.chuyennd.websocket;

import com.binance.chuyennd.utils.BinanceRestGuard;
import com.binance.chuyennd.utils.A1Qf2Access;
import com.binance.chuyennd.utils.RestBudget;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/** A1 re-audit QF2 (A1_QF2_REPORT, a1_wt2 — tich hop chinh thuc o QF3, giu nguyen kich ban). */
public class A1Qf2AdversarialTest {
    @Before
    public void setUp() {
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
    }

    @After
    public void tearDown() {
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
    }

    /**
     * A1-T6: IP bi ban (418 Retry-After 300 s) => Rest-Price-Loop dung dung (awaitIfBanned) => tuoi gia > 90 s.
     * Watchdog tuoi gia KHONG duoc restart JVM luc nay: BinanceRestGuard chi giu ban trong RAM, JVM moi se goi fapi ngay giua ban.
     */
    @Test
    public void t6_priceAgeWatchdogMustNotRestartDuringBan() {
        long now = System.currentTimeMillis();
        BinanceRestGuard.BANNED_UNTIL_MS.set(now + 300_000L);
        assertTrue(BinanceRestGuard.isBanned());
        int d = BinanceDataIngestor.decidePriceAge(130_000L, 3_600_000L, 0L, now);
        System.out.println("A1-T6 decidePriceAge(age=130s, dang ban)=" + d);
        assertNotEquals("watchdog restart JVM giua luc ban (mat trang thai ban, goi lai ngay)", 2, d);
    }

    /**
     * A1-T8: lane LOW 40 weight/60 s: repair khoi dong (klines limit 500, w=5, nghi 300 ms/call) vs premiumIndex (w=10 moi 30 s,
     * cho toi 30 s). Mo phong thoi gian ao 10 phut, thu tu luan phien cong bang. Dem premiumIndex bi tu choi.
     */
    @Test
    public void t8_repairStarvesFundingInLowLane() {
        AtomicLong clk = new AtomicLong(1_760_000_000_000L);
        RestBudget b = RestBudget.create(300, 1600, 2000, 150, clk::get);
        long t0 = clk.get(), nextRepair = t0, premDue = t0, premDeadline = -1;
        int repairOk = 0, premOk = 0, premDenied = 0;
        boolean repairFirst = true;
        for (long t = t0; t < t0 + 600_000L; t += 50) {
            clk.set(t);
            for (int k = 0; k < 2; k++) {
                boolean doRepair = (k == 0) == repairFirst;
                if (doRepair) {
                    if (t >= nextRepair && A1Qf2Access.tryAcquire(b, 5, RestBudget.Lane.LOW) == 0) {
                        repairOk++;
                        nextRepair = t + 300 + 100;   // sleep 300 + ~100 ms HTTP
                    }
                } else if (t >= premDue) {
                    if (premDeadline < 0) premDeadline = t + 30_000L;
                    if (A1Qf2Access.tryAcquire(b, 10, RestBudget.Lane.LOW) == 0) {
                        premOk++;
                        premDue = t + 30_000L;
                        premDeadline = -1;
                    } else if (t >= premDeadline) {
                        premDenied++;
                        premDue = t + 30_000L;
                        premDeadline = -1;
                    }
                }
            }
            repairFirst = !repairFirst;
        }
        System.out.println("A1-T8 repair_ok=" + repairOk + " (" + repairOk * 5 / 10 + " w/phut) premiumIndex_ok=" + premOk + " denied=" + premDenied);
        assertEquals("premiumIndex (funding) bi bo doi trong luc repair chay", 0, premDenied);
    }
}
