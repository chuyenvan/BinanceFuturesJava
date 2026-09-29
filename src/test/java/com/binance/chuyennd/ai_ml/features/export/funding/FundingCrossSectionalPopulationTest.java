package com.binance.chuyennd.ai_ml.features.export.funding;

import org.junit.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.assertNotEquals;

/**
 * [B5-PARITY 2026-09-29] Bang chung cho HO LUC parity cua market-only skip (B4): PASS-2
 * cross-sectional rank (#33..#35) tinh TREN CHINH list truyen vao. Neu tick market-only truyen
 * chi symbol DANG GIU (tap con) => percentile rank cua held coin LECH so voi full population
 * (csPop) => pNoPump lech => LATEST_SEL_PNOPUMP/trailing/DCA lech. => B5 bo market-only skip,
 * luon predict full universe (PREREG_PASS_SPEED_V2 §2.2).
 */
public class FundingCrossSectionalPopulationTest {

    /** Full population: 4 coin, coinFundingRate phan bo 0.0 .. 0.3. Held = chi 2 coin. */
    private static FundingMarketFeatures feat(String sym, float funding) {
        FundingMarketFeatures f = new FundingMarketFeatures();
        f.symbol = sym;
        f.coinFundingRate = funding;
        f.volumeZCoin = funding * 10f;
        f.momentum24H = funding * 2f;
        return f;
    }

    @Test
    public void rankTrenTapCon_khac_fullPopulation() {
        List<FundingMarketFeatures> full = new ArrayList<>();
        full.add(feat("A", 0.0f));
        full.add(feat("B", 0.1f));
        full.add(feat("C", 0.2f));
        full.add(feat("D", 0.3f));
        FundingCrossSectional.apply(full);
        float rankBFull = full.get(1).fundingRankCS;

        // Held-only: chi giu B va C => apply tren tap con => rank B phai KHAC (vi population chi 2)
        List<FundingMarketFeatures> held = new ArrayList<>();
        FundingMarketFeatures b = feat("B", 0.1f);
        FundingMarketFeatures c = feat("C", 0.2f);
        held.add(b);
        held.add(c);
        FundingCrossSectional.apply(held);
        float rankBHeld = held.get(0).fundingRankCS;

        assertNotEquals("rank cua held coin tren tap con PHAI khac full population (day la loi B4)",
                rankBFull, rankBHeld, 0.0f);
    }

    @Test
    public void rankFullPopulation_onDinh_giuaHaiLanApply() {
        List<FundingMarketFeatures> full = new ArrayList<>();
        full.add(feat("A", 0.0f));
        full.add(feat("B", 0.1f));
        full.add(feat("C", 0.2f));
        full.add(feat("D", 0.3f));
        FundingCrossSectional.apply(full);
        float r1 = full.get(2).momentumRankCS;
        FundingCrossSectional.apply(full);
        float r2 = full.get(2).momentumRankCS;
        org.junit.Assert.assertEquals("apply 2 lan cung population => deterministic", r1, r2, 0.0f);
    }
}
