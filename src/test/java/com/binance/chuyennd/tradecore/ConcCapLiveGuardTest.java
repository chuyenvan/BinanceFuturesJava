package com.binance.chuyennd.tradecore;

import org.junit.After;
import org.junit.Test;

import java.util.HashSet;
import java.util.Set;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * FUNCTION-TEST cho 2 guard safety-net ban LIVE ({@link ConcCapLiveGuard}).
 * Ham thuan — khong Redis, khong Binance client, khong backtest I/O.
 *
 * <p>Ba cau hoi phai tra loi:
 * <ol>
 *   <li><b>Default OFF thi co thuc su khong lam gi khong</b> — neu sai, day la code cham tien that.</li>
 *   <li><b>Bat len thi co chan DUNG nguong khong</b> (duoi nguong cho qua, vuot nguong chan).</li>
 *   <li><b>Cua so 60 phut co TU TROI khong</b> — ban sim reset theo run, ban live phai troi theo
 *       dong ho that; sai cho nay thi guard 2 chan vinh vien sau dot burst dau tien.</li>
 * </ol>
 *
 * <p>Configs.CONC_CAP_* KHONG final nen test gan lai truc tiep duoc; {@link #restore()} tra ve default.
 */
public class ConcCapLiveGuardTest {

    private static final float EPS = 1e-5f;

    private final boolean agg0 = Configs.CONC_CAP_AGG_DCA_ENABLED;
    private final float pct0 = Configs.CONC_CAP_AGG_DCA_PCT;
    private final boolean bd0 = Configs.CONC_CAP_BD_RATE_ENABLED;
    private final int perHour0 = Configs.CONC_CAP_BD_PER_HOUR;

    @After
    public void restore() {
        Configs.CONC_CAP_AGG_DCA_ENABLED = agg0;
        Configs.CONC_CAP_AGG_DCA_PCT = pct0;
        Configs.CONC_CAP_BD_RATE_ENABLED = bd0;
        Configs.CONC_CAP_BD_PER_HOUR = perHour0;
    }

    private static Set<String> setOf(String... xs) {
        Set<String> s = new HashSet<>();
        for (String x : xs) s.add(x);
        return s;
    }

    // ---------------------------------------------------------------- default OFF

    @Test
    public void defaultOff_khongChanGiCa() {
        Configs.CONC_CAP_AGG_DCA_ENABLED = false;
        Configs.CONC_CAP_BD_RATE_ENABLED = false;
        ConcCapLiveGuard g = new ConcCapLiveGuard();
        // nap trang thai "cuc doan" hon moi nguong
        for (int i = 0; i < 500; i++) g.recordBigDownLeg(1_000_000L + i);
        g.recordDcaLeg("AAAUSDT", 9_999_999f);
        assertFalse("flag OFF => guard 1 KHONG duoc chan", g.blockDcaLeg(9_999_999f, 1f));
        assertFalse("flag OFF => guard 2 KHONG duoc chan", g.blockBigDownLeg(1_000_500L));
    }

    // ---------------------------------------------------------------- guard 1

    @Test
    public void guard1_duoiNguongThiChoQua_vuotNguongThiChan() {
        Configs.CONC_CAP_AGG_DCA_ENABLED = true;
        Configs.CONC_CAP_AGG_DCA_PCT = 0.45f;
        ConcCapLiveGuard g = new ConcCapLiveGuard();
        float equity = 100_000f;

        // so sach: leg 40,000 => 0.40 <= 0.45 => CHO QUA
        assertFalse(g.blockDcaLeg(40_000f, equity));
        assertEquals(0.40f, g.ratioIfAdd(40_000f, equity), EPS);

        // da co 40,000 trong cac leg DCA; them 4,000 => 0.44 <= 0.45 => CHO QUA
        g.recordDcaLeg("AAAUSDT", 25_000f);
        g.recordDcaLeg("BBBUSDT", 15_000f);
        assertEquals(40_000f, g.aggDcaLegMargin(), EPS);
        assertFalse(g.blockDcaLeg(4_000f, equity));

        // them 6,000 => 0.46 > 0.45 => CHAN
        assertTrue(g.blockDcaLeg(6_000f, equity));
        assertEquals(0.46f, g.ratioIfAdd(6_000f, equity), EPS);
    }

    @Test
    public void guard1_dungBangNguongThiKHONGChan_chiVUOTmoiChan() {
        Configs.CONC_CAP_AGG_DCA_ENABLED = true;
        Configs.CONC_CAP_AGG_DCA_PCT = 0.45f;
        ConcCapLiveGuard g = new ConcCapLiveGuard();
        // spec dung dau ">" chu khong phai ">=" (PREREG muc 2)
        assertFalse("dung bang nguong => cho qua", g.blockDcaLeg(45_000f, 100_000f));
    }

    @Test
    public void guard1_failOpenKhiChuaCoEquity() {
        Configs.CONC_CAP_AGG_DCA_ENABLED = true;
        Configs.CONC_CAP_AGG_DCA_PCT = 0.45f;
        ConcCapLiveGuard g = new ConcCapLiveGuard();
        g.recordDcaLeg("AAAUSDT", 1_000_000f);
        assertFalse("equity chua doc duoc => FAIL-OPEN, khong chan", g.blockDcaLeg(1f, 0f));
        assertFalse(g.blockDcaLeg(1f, -1f));
    }

    @Test
    public void guard1_coDcaTier_suyTuStructure_khongDungSymbol2Level() {
        ConcCapLiveGuard g = new ConcCapLiveGuard();
        assertFalse(g.isInDcaTier("AAAUSDT"));
        g.recordDcaLeg("AAAUSDT", 10f);
        assertTrue(g.isInDcaTier("AAAUSDT"));
        assertFalse(g.isInDcaTier("BBBUSDT"));
    }

    @Test
    public void guard1_retainSymbols_bo_cum_da_dong() {
        Configs.CONC_CAP_AGG_DCA_ENABLED = true;
        Configs.CONC_CAP_AGG_DCA_PCT = 0.45f;
        ConcCapLiveGuard g = new ConcCapLiveGuard();
        g.recordDcaLeg("AAAUSDT", 30_000f);
        g.recordDcaLeg("BBBUSDT", 20_000f);
        assertEquals(50_000f, g.aggDcaLegMargin(), EPS);
        assertTrue(g.blockDcaLeg(1f, 100_000f));

        // BBB dong vi the => phai bien mat khoi aggregate, khong duoc phinh mai
        g.retainSymbols(setOf("AAAUSDT"));
        assertEquals(30_000f, g.aggDcaLegMargin(), EPS);
        assertFalse(g.isInDcaTier("BBBUSDT"));
        assertFalse(g.blockDcaLeg(1f, 100_000f));

        // null => khong doi gi (phong thu)
        g.retainSymbols(null);
        assertEquals(30_000f, g.aggDcaLegMargin(), EPS);
    }

    @Test
    public void guard1_nhieuLegCungMotSymbolDeuDuocCong() {
        ConcCapLiveGuard g = new ConcCapLiveGuard();
        g.recordDcaLeg("AAAUSDT", 1_000f);
        g.recordDcaLeg("AAAUSDT", 3_000f);
        g.recordDcaLeg("AAAUSDT", 8_000f);
        assertEquals(12_000f, g.aggDcaLegMargin(), EPS);
        assertEquals(3, g.trackedDcaLegCount());
    }

    // ---------------------------------------------------------------- guard 2

    @Test
    public void guard2_chanKhiDuNguong_vaCuaSoTuTroiTheoThoiGianThat() {
        Configs.CONC_CAP_BD_RATE_ENABLED = true;
        Configs.CONC_CAP_BD_PER_HOUR = 3;
        ConcCapLiveGuard g = new ConcCapLiveGuard();
        long t0 = 1_700_000_000_000L;

        assertFalse(g.blockBigDownLeg(t0));
        g.recordBigDownLeg(t0);
        g.recordBigDownLeg(t0 + 1_000L);
        assertEquals(2, g.bdCountLastHour(t0 + 2_000L));
        assertFalse("moi 2 leg, cap 3 => cho qua", g.blockBigDownLeg(t0 + 2_000L));

        g.recordBigDownLeg(t0 + 2_000L);
        assertTrue("du 3 leg, cap 3 => CHAN (spec dung >=)", g.blockBigDownLeg(t0 + 3_000L));

        // 61 phut sau: ca 3 moc da roi khoi cua so => tu troi, KHONG chan nua
        long later = t0 + 61L * 60L * 1000L;
        assertEquals(0, g.bdCountLastHour(later));
        assertFalse("cua so 60 phut phai TU TROI theo dong ho that", g.blockBigDownLeg(later));
    }

    @Test
    public void guard2_chiDemLegTrongDungCuaSo60Phut() {
        Configs.CONC_CAP_BD_RATE_ENABLED = true;
        Configs.CONC_CAP_BD_PER_HOUR = 75;
        ConcCapLiveGuard g = new ConcCapLiveGuard();
        long t0 = 1_700_000_000_000L;
        g.recordBigDownLeg(t0);                          // se het han
        g.recordBigDownLeg(t0 + 30L * 60L * 1000L);      // con han
        long now = t0 + 61L * 60L * 1000L;
        assertEquals("chi con leg trong 60 phut gan nhat", 1, g.bdCountLastHour(now));
    }
}
