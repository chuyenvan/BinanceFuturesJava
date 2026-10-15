package com.binance.chuyennd.tradecore;

import org.junit.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * QUEUE_1015 P5: kill-switch theo equity. Kiem bac WARN/PAUSE/STOP theo DD va UW (ngay khong lap dinh),
 * "tam dung" chan mo lenh MOI nhung khong dung han, config vang => inert, va khong goi notifier khi TAT.
 */
public class KillSwitchTest {

    private static final long DAY = 86_400_000L;
    private static final double EQ = 100_000.0;

    private static KillSwitch mk(boolean notify) {
        // enabled, notify, ddWarn, ddPause, ddStop, ddResume, uwWarn, uwPause
        return new KillSwitch(true, notify, 0.05f, 0.10f, 0.20f, 0.03f, 10f, 20f);
    }

    @Test
    public void defaultFromConfigIsDisabledWhenNoKeys() {
        // Trong moi truong test khong dat KILL_SWITCH_* => mac dinh TAT.
        KillSwitch ks = new KillSwitch();
        assertFalse("mac dinh phai TAT", ks.enabled());
        assertEquals(KillSwitch.State.DISABLED, ks.state());
        assertFalse(ks.blocksNewEntries());
        assertEquals(KillSwitch.State.DISABLED, ks.onEquity(EQ, 0L));
    }

    @Test
    public void noThresholdsMeansInertButEnabled() {
        // Bat nhung KHONG khai nguong nao => khong bao gio ha bac.
        KillSwitch ks = new KillSwitch(true, false, Float.NaN, Float.NaN, Float.NaN,
                Float.NaN, Float.NaN, Float.NaN);
        assertEquals(KillSwitch.State.NORMAL, ks.onEquity(EQ, 0L));
        assertEquals(KillSwitch.State.NORMAL, ks.onEquity(EQ * 0.1, 30 * DAY));
        assertFalse(ks.blocksNewEntries());
    }

    @Test
    public void drawdownRungs() {
        KillSwitch ks = mk(false);
        assertEquals(KillSwitch.State.NORMAL, ks.onEquity(EQ, 0L));
        // -5% => WARN (canh bao, khong chan)
        assertEquals(KillSwitch.State.WARN, ks.onEquity(EQ * 0.95, DAY));
        assertFalse(ks.blocksNewEntries());
        // -10% => PAUSE (chan lenh moi, KHONG dung han)
        assertEquals(KillSwitch.State.PAUSE, ks.onEquity(EQ * 0.90, 2 * DAY));
        assertTrue(ks.blocksNewEntries());
        assertFalse(ks.halted());
        // -20% => STOP (dung han)
        assertEquals(KillSwitch.State.STOP, ks.onEquity(EQ * 0.80, 3 * DAY));
        assertTrue(ks.halted());
    }

    @Test
    public void underWaterDaysRung() {
        KillSwitch ks = mk(false);
        assertEquals(KillSwitch.State.NORMAL, ks.onEquity(EQ, 0L));
        // equity chi giam nhe, nhung 10 ngay khong lap dinh => WARN
        assertEquals(KillSwitch.State.WARN, ks.onEquity(EQ * 0.99, 10 * DAY));
        // 20 ngay => PAUSE
        assertEquals(KillSwitch.State.PAUSE, ks.onEquity(EQ * 0.99, 20 * DAY));
    }

    @Test
    public void pauseKeepsManagingAndRecoversToNormal() {
        KillSwitch ks = mk(false);
        ks.onEquity(EQ, 0L);
        assertEquals(KillSwitch.State.PAUSE, ks.onEquity(EQ * 0.90, DAY));
        // hoi phuc: DD < DD_RESUME (0.03) va UW < UW_WARN (10 ngay)
        assertEquals(KillSwitch.State.NORMAL, ks.onEquity(EQ * 0.98, 2 * DAY));
        assertFalse(ks.blocksNewEntries());
    }

    @Test
    public void newPeakResetsUnderWater() {
        KillSwitch ks = mk(false);
        ks.onEquity(EQ, 0L);
        ks.onEquity(EQ * 0.99, 25 * DAY);            // UW >= 20 ngay => PAUSE
        assertEquals(KillSwitch.State.PAUSE, ks.state());
        assertEquals(KillSwitch.State.NORMAL, ks.onEquity(EQ * 1.01, 26 * DAY)); // dinh moi
        assertEquals(EQ * 1.01, ks.peakEquity(), 1e-6);
    }

    @Test
    public void notifierOnlyFiresOnTransitionWhenNotifyOn() {
        List<String> msgs = new ArrayList<>();
        KillSwitch ks = mk(true);
        ks.setNotifier((s, m) -> msgs.add(s + "|" + m));
        ks.onEquity(EQ, 0L);                          // NORMAL (khong doi tu NORMAL => khong gui)
        ks.onEquity(EQ * 0.95, DAY);                  // -> WARN (gui)
        ks.onEquity(EQ * 0.94, 2 * DAY);              // van WARN (khong gui)
        ks.onEquity(EQ * 0.90, 3 * DAY);              // -> PAUSE (gui)
        assertEquals(2, msgs.size());
        assertTrue(msgs.get(0).startsWith("WARN|"));
        assertTrue(msgs.get(1).startsWith("PAUSE|"));
    }

    @Test
    public void nonPositiveEquityIsIgnored() {
        KillSwitch ks = mk(true);
        ks.onEquity(EQ, 0L);
        assertEquals(KillSwitch.State.NORMAL, ks.onEquity(0.0, DAY));
        assertEquals(KillSwitch.State.NORMAL, ks.onEquity(-5.0, 2 * DAY));
    }
}
