package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.TradeUtils;
import org.junit.Test;

import java.io.File;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

import static org.junit.Assert.*;

/**
 * CONG HOI QUY cua L3 — co lap LEGACY tren 242.
 *
 * <p>De bai: MOT JVM chay ca hai duong — (i) 66 vi the THAT cu tiep tuc dong THAT theo luat
 * HEAD, (ii) so giay C3 chay song song. Cac test duoi khang dinh:
 * <ol>
 *   <li>cung {@code LIVE_PROFILE=c3_shadow}: symbol LEGACY -> arm/ratchet/time-stop = HEAD,
 *       symbol cua so giay -> C3 (0.07 / dead-zone 1.0 / time-stop 168h);</li>
 *   <li>LEGACY = (vi the that) \ (so giay), tu thu hep khi vi the that dong, song sot restart;</li>
 *   <li>legacy KHONG chiem slot top-K cua so giay;</li>
 *   <li>hai duong khong dung chung {@code BUDGET_PER_ORDER} / {@code balanceBasic}.</li>
 * </ol>
 * Khong doi duoc env trong JVM dang chay nen nhanh "profile BAT" duoc kiem qua cac ham thuan
 * tinh toan {@code decideArmRate/decideDeadzone/decideTimeStop} — chinh la ham ma
 * {@code armRateFor/ratchetDeadzoneMultFor/timeStopApplies} goi vao.
 */
public class LegacyIsolationTest {

    private static final float HEAD_ARM = 0.05f;        // env 242: SIM_RATE_PROFIT_STOP_MARKET
    private static final float HEAD_DEADZONE = 5.21847f; // LIVE_RATCHET_DEADZONE_MULT cua HEAD

    /** (1a) Profile BAT + symbol LEGACY => nguong arm giu DUNG gia tri HEAD. */
    @Test
    public void armRateLegacyStaysHeadWhenProfileOn() {
        assertEquals(HEAD_ARM, LiveProfileC3.decideArmRate(true, true, HEAD_ARM), 0f);
        assertEquals(0.01f, LiveProfileC3.decideArmRate(true, true, 0.01f), 0f);
    }

    /** (1b) Profile BAT + symbol cua SO GIAY => nguong arm C3 0.07. */
    @Test
    public void armRatePaperUsesC3WhenProfileOn() {
        assertEquals(LiveProfileC3.ARM_RATE, LiveProfileC3.decideArmRate(true, false, HEAD_ARM), 0f);
        assertEquals(0.07f, LiveProfileC3.decideArmRate(true, false, HEAD_ARM), 0f);
    }

    /** (1c) Profile TAT: ca hai loai symbol deu HEAD (khong co khai niem legacy). */
    @Test
    public void armRateHeadWhenProfileOff() {
        assertEquals(HEAD_ARM, LiveProfileC3.decideArmRate(false, false, HEAD_ARM), 0f);
        assertEquals(HEAD_ARM, LiveProfileC3.decideArmRate(false, true, HEAD_ARM), 0f);
        assertEquals(HEAD_ARM, LiveProfileC3.armRateFor("BTCUSDT", HEAD_ARM), 0f);
        assertEquals(Configs.RATE_PROFIT_STOP_MARKET,
                TradeUtils.calRateMinWithPredReturn15MForTradingStop(0.0123f, "BTCUSDT"), 0f);
    }

    /** (1d) dead-zone ratchet: legacy giu x5.21847 ke ca khi profile BAT; giay -> 1.0. */
    @Test
    public void ratchetDeadzoneSplitByLegacy() {
        assertEquals(HEAD_DEADZONE, LiveProfileC3.decideDeadzone(true, true, HEAD_DEADZONE), 0f);
        assertEquals(1.0f, LiveProfileC3.decideDeadzone(true, false, HEAD_DEADZONE), 0f);
        assertEquals(HEAD_DEADZONE, LiveProfileC3.decideDeadzone(false, false, HEAD_DEADZONE), 0f);
        assertEquals(HEAD_DEADZONE, LiveProfileC3.ratchetDeadzoneMultFor("BTCUSDT", HEAD_DEADZONE), 0f);
    }

    /**
     * (1e) Diem RATCHET that su cua duong dong THAT = dead-zone x arm. Legacy phai giu
     * 5.21847 x 0.05 = 26.1% nhu HEAD; so giay ratchet LIEN TUC (1.0 x 0.07).
     */
    @Test
    public void ratchetTriggerPointLegacyIdenticalToHead() {
        float legacy = LiveProfileC3.decideDeadzone(true, true, HEAD_DEADZONE)
                * LiveProfileC3.decideArmRate(true, true, HEAD_ARM);
        float head = HEAD_DEADZONE * HEAD_ARM;
        assertEquals("legacy phai byte-identical HEAD", head, legacy, 0f);
        float paper = LiveProfileC3.decideDeadzone(true, false, HEAD_DEADZONE)
                * LiveProfileC3.decideArmRate(true, false, HEAD_ARM);
        assertEquals(0.07f, paper, 1e-7f);
        assertTrue("C3 phai ratchet som hon HEAD rat nhieu", paper < legacy / 3f);
    }

    /** (1f) time-stop 168h: CHI cho so giay, khong bao gio cham symbol legacy. */
    @Test
    public void timeStopNeverAppliesToLegacy() {
        assertFalse(LiveProfileC3.decideTimeStop(true, true));
        assertTrue(LiveProfileC3.decideTimeStop(true, false));
        assertFalse(LiveProfileC3.decideTimeStop(false, false));
        assertFalse("profile TAT => khong co time-stop o dau ca",
                LiveProfileC3.timeStopApplies("BTCUSDT"));
    }

    /** (2a) LEGACY = vi the THAT \ so GIAY. */
    @Test
    public void legacyIsRealMinusPaper() {
        Set<String> real = new HashSet<>(Arrays.asList("AAAUSDT", "BBBUSDT", "CCCUSDT"));
        Set<String> paper = new HashSet<>(Arrays.asList("CCCUSDT", "DDDUSDT"));
        assertEquals(new TreeSet<>(Arrays.asList("AAAUSDT", "BBBUSDT")),
                LegacySymbols.compute(real, paper));
    }

    /** (2b) Tap tu THU HEP khi vi the that dong (khong con trong danh sach doc ve tu Binance). */
    @Test
    public void legacyShrinksWhenRealPositionCloses() {
        Set<String> paper = new HashSet<>();
        TreeSet<String> t0 = LegacySymbols.compute(
                new HashSet<>(Arrays.asList("AAAUSDT", "BBBUSDT")), paper);
        assertEquals(2, t0.size());
        TreeSet<String> t1 = LegacySymbols.compute(
                new HashSet<>(Arrays.asList("AAAUSDT")), paper);
        assertEquals(new TreeSet<>(Arrays.asList("AAAUSDT")), t1);
        assertTrue(LegacySymbols.compute(new HashSet<String>(), paper).isEmpty());
    }

    /** (2c) Reconcile ghi dia va nap lai duoc sau restart (JVM tu restart moi 4h). */
    @Test
    public void legacySurvivesRestart() {
        String p = "/tmp/l3_legacy_test/legacy_symbols.csv";
        new File(p).delete();
        LegacySymbols.resetForTest(p);
        LegacySymbols a = LegacySymbols.getInstance();
        a.reconcile(new HashSet<>(Arrays.asList("AAAUSDT", "BBBUSDT", "CCCUSDT")),
                new HashSet<>(Arrays.asList("CCCUSDT")));
        assertEquals(2, a.size());
        assertTrue(new File(p).exists());
        LegacySymbols.resetForTest(p);                       // gia lap restart JVM
        assertEquals(new TreeSet<>(Arrays.asList("AAAUSDT", "BBBUSDT")),
                LegacySymbols.getInstance().all());
        LegacySymbols.getInstance().reconcile(new HashSet<>(Arrays.asList("AAAUSDT")),
                new HashSet<String>());
        LegacySymbols.resetForTest(p);
        assertEquals(new TreeSet<>(Arrays.asList("AAAUSDT")), LegacySymbols.getInstance().all());
    }

    /** (2d) Profile TAT: khong co symbol nao la legacy va KHONG cham dia. */
    @Test
    public void noLegacyWhenProfileOff() {
        assertFalse(LiveProfileC3.on());
        assertFalse(LegacySymbols.isLegacySymbol("AAAUSDT"));
        assertFalse(LegacySymbols.isLegacySymbol(null));
    }

    /** (3) Legacy KHONG chiem slot top-K cua so giay (mo hinh vong chon sau patch L3). */
    @Test
    public void legacyDoesNotConsumePaperSlot() {
        List<String> pool = Arrays.asList("L1", "P1", "L2", "P2", "P3", "P4", "P5",
                "P6", "P7", "P8", "P9");
        Set<String> legacy = new HashSet<>(Arrays.asList("L1", "L2"));
        List<String> got = LegacySymbols.paperCandidates(pool, legacy, 8);
        assertEquals(8, got.size());
        assertEquals(Arrays.asList("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"), got);
        assertFalse(got.contains("L1"));
        // khong co legacy thi ket qua y het cach dem cu (top-K dau pool)
        assertEquals(Arrays.asList("L1", "P1", "L2", "P2", "P3", "P4", "P5", "P6"),
                LegacySymbols.paperCandidates(pool, new HashSet<String>(), 8));
    }

    /**
     * (4a) Sizing so GIAY khong the an theo {@code BudgetManager.BUDGET_PER_ORDER}: tham so
     * {@code budget} truyen vao {@code managerBudget} KHONG tham gia phep tinh (chi equity +
     * margin). Doi doi so nay bao nhieu cung ra cung mot ket qua.
     */
    @Test
    public void paperSizingIgnoresLiveBudgetPerOrder() {
        Float a = TradeUtils.managerBudget(0f, 1000f, 35000f, null);
        Float b = TradeUtils.managerBudget(123456f, 1000f, 35000f, null);
        assertNotNull(a);
        assertEquals(a, b);
    }

    /**
     * (4b) Von cua so GIAY chi den tu {@code PAPER_EQUITY} — khong bao gio roi ve
     * {@code CAPITAL_START}/{@code balanceBasic} cua tai khoan that. Profile TAT => 0.
     */
    @Test
    public void paperEquityIsolatedFromLiveCapital() {
        assertEquals(0f, LiveProfileC3.paperEquity(), 0f);
    }

    /** (5) Nhanh giay mac dinh KHONG day lenh qua Redis queue cua bot. */
    @Test
    public void shadowDoesNotUseBotRedisQueueByDefault() {
        assertFalse(LiveProfileC3.shadowUseRedisQueue());
    }

    /** (6) SHADOW_NO_PUSH bi hardcode true khi profile bat (khong doc env). */
    @Test
    public void forceNoPushHardcodedWithProfile() {
        assertEquals(LiveProfileC3.on(), LiveProfileC3.forceNoPush());
        assertFalse(LiveProfileC3.forceNoPush());
    }
}
