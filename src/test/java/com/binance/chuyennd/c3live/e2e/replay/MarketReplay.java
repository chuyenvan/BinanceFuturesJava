package com.binance.chuyennd.c3live.e2e.replay;

import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;

import java.util.TreeMap;

/**
 * [E2E_V12 ERRATA1 E1/N6] Dieu kien thi truong cua phut quyet dinh b cho DCA grid (BIG_DOWN / isDcaAlt), tinh tu nen 1m
 * MOI symbol cua fixture (mkt.csv.gz) theo DUNG vong live DetectEntrySignal2TradeNormal:280-356 (vong main KHONG chay
 * trong replay => harness lap lai vong do) va goi HAM PRODUCTION cua jar: Constants.diedSymbol, Utils.isTickerAvailable,
 * Utils.rateOf2Double, Configs.NUMBER_TICKER_CAL_RATE_CHANGE, MarketBigChangeDetector.calRateChangeAvg / getMarketStatus1M /
 * isDcaAlt. Universe = universe A1 cua rig (UniverseA1Filter.filter o live). REF tinh RIENG theo cong thuc sim (ref_v12.py ?R8).
 * Gioi han (ghi SPEC): symbol khong co nen o b bi bo (live dung ban ghi cuoi cua cua so); cua so 15 nen = 15 ban ghi co mat gan
 * nhat; khong ap SimpleSymbolMapper.isQuarantined; LIVE_MD_SOURCE (inline) khong dat o 242 => duong mac dinh.
 */
final class MarketReplay {

    static final double DIP = 0.98d;

    static final class State {
        final float down, up, down15;
        final MarketLevelChange level;
        final boolean dcaAlt;
        final int n, n15;

        State(float down, float up, float down15, MarketLevelChange level, boolean dcaAlt, int n, int n15) {
            this.down = down;
            this.up = up;
            this.down15 = down15;
            this.level = level;
            this.dcaAlt = dcaAlt;
            this.n = n;
            this.n15 = n15;
        }
    }

    interface Excl {
        boolean test(String sym, long b);
    }

    interface Fct {
        double of(String sym, long t);
    }

    private MarketReplay() {
    }

    /** Nen {o,h,l,c,qv} cua symbol i o phut t sau bien doi S-DCA (he so gia cum ep; dip: c'=o*0.98, l'=min(l,c') neu KHA DUNG). */
    static float[] bar(ReplayData d, int i, long t, Fct fct, boolean dip) {
        float[] x = d.mkt(i, t);
        if (x == null) return null;
        boolean av = x[1] != x[2] || x[4] != 0f;   // = Utils.isTickerAvailable tren nen GOC
        double f = fct.of(d.mSym[i], t);
        if (f != 1d) {
            for (int k = 0; k < 4; k++) x[k] = (float) (x[k] * f);
        }
        if (dip && av) {
            float c2 = (float) (x[0] * DIP);
            x[3] = c2;
            x[2] = Math.min(x[2], c2);
        }
        return x;
    }

    static KlineObjectSimple k(long b, float[] x) {
        KlineObjectSimple k = new KlineObjectSimple();
        k.startTime = b;
        k.priceOpen = x[0];
        k.maxPrice = x[1];
        k.minPrice = x[2];
        k.priceClose = x[3];
        k.totalUsdt = x[4];
        return k;
    }

    /** null = khong co BTC o b (live: BO vong entry phut nay => khong DCA). */
    static State at(ReplayData d, long b, Excl a1x, Fct fct, boolean dip) {
        Integer bi = d.mIdx.get(Constants.SYMBOL_PAIR_BTC);
        float[] bx = bi == null ? null : bar(d, bi, b, fct, dip);
        if (bx == null) return null;
        KlineObjectSimple btc = k(b, bx);
        Float btcRate = Utils.rateOf2Double(btc.priceClose, btc.priceOpen);
        TreeMap<Float, String> dn = new TreeMap<>(), up = new TreeMap<>(), d15 = new TreeMap<>();
        int n = 0, n15 = 0;
        for (int i = 0; i < d.mSym.length; i++) {
            String s = d.mSym[i];
            if (Constants.diedSymbol.contains(s)) continue;
            if (a1x.test(s, b)) continue;
            float[] x = bar(d, i, b, fct, dip);
            if (x == null) continue;
            KlineObjectSimple t = k(b, x);
            if (!Utils.isTickerAvailable(t)) continue;
            Float rate = Utils.rateOf2Double(t.priceClose, t.priceOpen);
            if (btcRate > -0.004 && rate < -0.15) continue;
            if (rate > 0.3) continue;
            dn.put(rate, s);
            up.put(-rate, s);
            n++;
            Float pmax = null;
            int cnt = 0;
            for (long tt = b; cnt < Configs.NUMBER_TICKER_CAL_RATE_CHANGE && tt >= d.mT0; tt -= ReplayData.MIN) {
                float[] y = bar(d, i, tt, fct, dip && tt == b);
                if (y == null) continue;
                cnt++;
                if (pmax == null || pmax < y[1]) pmax = y[1];
            }
            d15.put(Utils.rateOf2Double(t.priceClose, pmax), s);
            n15++;
        }
        Float da = MarketBigChangeDetector.calRateChangeAvg(dn, 100);
        Float ua = -MarketBigChangeDetector.calRateChangeAvg(up, 100);
        Float d15a = MarketBigChangeDetector.calRateChangeAvg(d15, 100);
        MarketLevelChange lv = MarketBigChangeDetector.getMarketStatus1M(da, ua, d15a);
        boolean alt = MarketBigChangeDetector.isDcaAlt(d15a, da, ua);
        return new State(da, ua, d15a, lv, alt, n, n15);
    }
}
