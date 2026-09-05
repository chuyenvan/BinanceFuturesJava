package com.binance.chuyennd.tradecore;

import org.junit.After;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * BUG B2 (docs/QUEUE.md muc BUGS, docs/T2B_FULLFLOW.md muc 1) — tong trong so DCA bi chia HAI LAN:
 * {@link TradeUtils#managerBudget} chia /dcaGridTotalWeight() VA {@link DcaUtils#gridLegWeightRatio}
 * chia them mot lan nua => margin(leg i) ~ w[i]/total^2.
 *
 * <p>Hai cau hoi test nay tra loi, dung nhu cong kiem da ghi truoc:
 * <ol>
 *   <li>Voi luoi 1,0,0,0 (total=1) ket qua PHAI KHONG DOI — day la ly do C2b khong bao gio thay bug.</li>
 *   <li>Voi luoi 1,1,3,8 leg-1 phai bang 1/13 cua mot-leg, KHONG phai 1/169.</li>
 * </ol>
 */
public class FixB2LadderDivisionTest {

    private final boolean fix0 = Configs.FIX_B2;
    private final boolean scalar0 = Configs.DCA_GRID_SCALAR;
    private final float[] w0 = Configs.DCA_GRID_WEIGHTS;
    private final float scale0 = Configs.DCA_GRID_SCALE;

    @After
    public void restore() {
        Configs.FIX_B2 = fix0;
        Configs.DCA_GRID_SCALAR = scalar0;
        Configs.DCA_GRID_WEIGHTS = w0;
        Configs.DCA_GRID_SCALE = scale0;
    }

    /** margin THUC TE cua leg dau = managerBudget(...) x gridLegWeightRatio(0), u=0 => throttle=1. */
    private static float leg1Margin(float[] weights, boolean fixB2) {
        Configs.DCA_GRID_SCALAR = false;
        Configs.DCA_GRID_WEIGHTS = weights;
        Configs.DCA_GRID_SCALE = 1.5f;
        Configs.FIX_B2 = fixB2;
        float budget = TradeUtils.managerBudget(700f, 0f, 35000f, null);
        return budget * DcaUtils.gridLegWeightRatio(0);
    }

    /** CONG HOI QUY o muc don vi: 1,0,0,0 => total=1 => sua hay khong sua deu RA CUNG MOT SO. */
    @Test
    public void singleLegGridIsUnchangedByFix() {
        float[] w = {1f, 0f, 0f, 0f};
        float now = leg1Margin(w, true);
        float old = leg1Margin(w, false);
        assertEquals("1,0,0,0: FIX_B2 khong duoc doi mot bit nao", old, now, 1e-4f);
        assertEquals("mot-leg @equity 35000 = 35000 x 0.03 x 1.5 = 1575", 1575f, now, 0.5f);
    }

    /** 1,1,3,8: leg-1 phai la 1/13 cua mot-leg. Truoc khi sua no la 1/169 (=13^2). */
    @Test
    public void ladderDividesTotalExactlyOnce() {
        float single = leg1Margin(new float[]{1f, 0f, 0f, 0f}, true);
        float fixed = leg1Margin(new float[]{1f, 1f, 3f, 8f}, true);
        float buggy = leg1Margin(new float[]{1f, 1f, 3f, 8f}, false);

        assertEquals("sau khi sua: leg-1 = 1/13 mot-leg", single / 13f, fixed, 1e-3f);
        assertEquals("truoc khi sua: leg-1 = 1/169 mot-leg", single / 169f, buggy, 1e-3f);
        assertEquals("he so danh cu dung bang total = 13", 13f, fixed / buggy, 1e-3f);
        assertTrue(fixed > buggy);
    }

    /** Tong ca ladder khi cham DAY = budget x SCALE = equity x F_BASE x SCALE (khong phinh exposure). */
    @Test
    public void fullLadderExposureEqualsOneSingleLeg() {
        Configs.DCA_GRID_SCALAR = false;
        Configs.DCA_GRID_WEIGHTS = new float[]{1f, 1f, 3f, 8f};
        Configs.DCA_GRID_SCALE = 1.5f;
        Configs.FIX_B2 = true;
        float budget = TradeUtils.managerBudget(700f, 0f, 35000f, null);
        float sum = 0f;
        for (int i = 0; i <= 3; i++) sum += budget * DcaUtils.gridLegWeightRatio(i);
        assertEquals("day ladder = 35000 x 0.03 x 1.5", 1575f, sum, 0.5f);
    }
}
