package com.binance.chuyennd.trading;

import com.binance.chuyennd.tradecore.Configs;
import org.junit.Test;

import java.util.ArrayDeque;
import java.util.Deque;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * [CADENCE-SPLIT-V2 2026-09-28] docs/plan/PLAN_CADENCE_SPLIT_V2.md — bang chung LOGIC cho cong tac
 * uu tien + hang doi CO CHAN khi pool = 1 thread:
 * (i)   key {@code MARKET_SCAN_PRIORITY} TAT (=0/khong khai) =&gt; luon nop nhu cu =&gt; y nguyen;
 * (ii)  BAT (=1) =&gt; tick MARKET-LEVEL chi nop khi RANH, dang ban =&gt; BO QUA (khong xep hang =&gt; khong phinh);
 * (iii) BAT =&gt; tick SELECTOR LUON duoc nhan (toi da 1 dang cho) =&gt; luon fire dung moc 15'.
 * Chi goi ham THUAN (TickGate / shouldSubmit), khong cham mang/ONNX/live.
 */
public class CadencePriorityTest {

    /** Thoi gian 1 luot checkMarketLevelChange2Trade (do duoc tren shadow 2026-09-27 = ~2m48s). */
    private static final long RUN_SEC = 168L;

    // ---- (i) key TAT => y nguyen (khong cong tac) ----

    @Test
    public void tat_thiLuonNop_yNguyen() {
        DetectEntrySignal2TradeNormal.TickGate g = new DetectEntrySignal2TradeNormal.TickGate();
        assertTrue(DetectEntrySignal2TradeNormal.shouldSubmit(0, g, true));
        assertTrue(DetectEntrySignal2TradeNormal.shouldSubmit(0, g, false));
        // saturate gates den muc toi da (1 chay + 1 cho) => TAT van phai luon nop.
        g.acceptSelector();
        g.acceptMarket();
        assertTrue(DetectEntrySignal2TradeNormal.shouldSubmit(-1, g, false));
        assertTrue(DetectEntrySignal2TradeNormal.shouldSubmit(0, g, true));
    }

    // ---- (ii) BAT: MARKET khong bao gio xep hang khi ban ----

    @Test
    public void bat_marketKhongBaoGioXepHangKhiBan() {
        DetectEntrySignal2TradeNormal.TickGate g = new DetectEntrySignal2TradeNormal.TickGate();
        assertTrue(DetectEntrySignal2TradeNormal.shouldSubmit(1, g, false)); // ranh => nhan
        assertEquals(1, g.pending());
        for (int i = 0; i < 5; i++) {
            assertFalse("dang ban => BO QUA", DetectEntrySignal2TradeNormal.shouldSubmit(1, g, false));
            assertEquals("pending KHONG duoc tang", 1, g.pending());
        }
        g.done(false);
        assertEquals(0, g.pending());
        assertTrue(DetectEntrySignal2TradeNormal.shouldSubmit(1, g, false)); // ranh lai => nhan
        g.done(false);
    }

    // ---- (iii) BAT: SELECTOR luon duoc nhan, toi da 1 dang cho ----

    @Test
    public void bat_selectorLuonDuocNhan_toiDa1Cho() {
        DetectEntrySignal2TradeNormal.TickGate g = new DetectEntrySignal2TradeNormal.TickGate();
        for (int round = 0; round < 4; round++) {
            assertTrue(DetectEntrySignal2TradeNormal.shouldSubmit(1, g, true));
            assertEquals(1, g.pending());
            g.done(true);
            assertEquals(0, g.pending());
        }
        assertTrue(DetectEntrySignal2TradeNormal.shouldSubmit(1, g, true));
        assertFalse("da co 1 selector cho => khong nhan slot thu 2 (khong phinh)",
                DetectEntrySignal2TradeNormal.shouldSubmit(1, g, true));
        assertEquals(1, g.pending());
        assertTrue("MARKET van bi bo khi co selector cho", !DetectEntrySignal2TradeNormal.shouldSubmit(1, g, false));
        g.done(true);
    }

    // ---- Mo phong 1 gio voi pool 1 thread: selector fire 4 moc; hang doi khong phinh ----

    @Test
    public void moPhong1Gio_selectorFire4Moc_hangDoiKhongPhinh() {
        DetectEntrySignal2TradeNormal.TickGate g = new DetectEntrySignal2TradeNormal.TickGate();
        int priority = 1;
        Deque<Boolean> queue = new ArrayDeque<>();
        boolean running = false, runningSel = false;
        long finishAt = -1;
        int selTicks = 0, selEnq = 0, mktEnq = 0, maxPending = 0, maxQueue = 0;

        for (long t = 0; t < 3600; t++) {
            // 1) task xong => tra slot
            if (running && t == finishAt) {
                g.done(runningSel);
                running = false;
            }
            // 2) worker ranh => lay task dang cho ra chay (pool 1 thread)
            if (!running && !queue.isEmpty()) {
                runningSel = queue.poll();
                running = true;
                finishAt = t + RUN_SEC;
            }
            // 3) tick: moi phut; phut chia het 15 => SELECTOR, con lai => MARKET-LEVEL
            if (t % 60 == 0) {
                boolean sel = (t / 60) % 15 == 0;
                if (DetectEntrySignal2TradeNormal.shouldSubmit(priority, g, sel)) {
                    queue.add(sel);
                    if (sel) {
                        selTicks++;
                        selEnq++;
                    } else {
                        mktEnq++;
                    }
                } else if (sel) {
                    selTicks++; // selector bi bo => KHONG duoc phep
                }
                maxPending = Math.max(maxPending, g.pending());
                maxQueue = Math.max(maxQueue, queue.size());
            }
        }
        assertEquals("SELECTOR phai gap dung 4 moc/gio", 4, selTicks);
        assertEquals("SELECTOR khong duoc bo lan nao", 4, selEnq);
        assertTrue("pending toi da 2 (= 1 dang chay + 1 selector cho)", maxPending <= 2);
        assertTrue("hang doi toi da 1 => KHONG phinh", maxQueue <= 1);
        assertTrue("market best-effort co chay", mktEnq >= 1);
        assertTrue("market < 60/nen (co skip-if-busy)", mktEnq < 60);
        System.out.println("[CADENCE-V2-SIM] 1 gio, RUN_SEC=" + RUN_SEC + ": SELECTOR enq=" + selEnq
                + " MKT enq=" + mktEnq + " maxPending=" + maxPending + " maxQueue=" + maxQueue);
    }

    @Test
    public void keyMacDinh_tat_vaKhongChamThamSoKhac() {
        assertEquals("MARKET_SCAN_PRIORITY mac dinh phai la 0 (TAT)", 0, Configs.MARKET_SCAN_PRIORITY);
    }
}
