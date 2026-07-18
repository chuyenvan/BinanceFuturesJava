package com.binance.chuyennd.research;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.client.model.enums.OrderSide;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * FUNCTION-TEST co che SHORT (DRAFT 2026-07-18). HAM THUAN — khong Aerospike/backtest I/O:
 * dung symbol=null de tranh SimpleSymbolMapper.getId (Aerospike), set field truc tiep, dung
 * kline TAY. Kiem 3 kich ban theo spec bang SO:
 *   (a) short + gia GIAM 10%  -> PnL DUONG ~ +10%*qty - phi.
 *   (b) short + gia TANG vuot hard-SL -> STOP_LOSS_DONE, chot tai -SHORT_SL_PCT.
 *   (c) funding DUONG -> short BI TRU (mo hinh chi phi bao thu, dung spec task).
 * KHONG chay full WFO. ENABLE_SHORT khong can bat: test goi truc tiep updateStatusShort/calTp.
 */
public class ShortOrderMechanismTest {

    private static final float EPS = 1e-3f;

    private static OrderTargetInfoTest newShort(float entry, Float tp, float qty) {
        // symbol=null -> constructor bo qua getId (khong dung Aerospike). side=SELL.
        OrderTargetInfoTest o = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, tp, qty,
                1, null, 1000L, 1000L, OrderSide.SELL);
        o.lastPrice = entry;
        o.minPrice = entry;
        return o;
    }

    private static float expectedFeeSlip(float entry, float qty) {
        float fee = qty * entry * Configs.RATE_FEE;
        float slip = Configs.APPLY_SLIPPAGE ? qty * entry * Configs.SLIPPAGE_RATE * 2f : 0f;
        return fee + slip;
    }

    /** (a) SHORT + gia giam 10% -> PnL duong dung ~ +10%*qty - phi. */
    @Test
    public void shortProfitWhenPriceDrops() {
        float entry = 100f, qty = 1f, exit = 90f; // giam 10%
        OrderTargetInfoTest o = newShort(entry, exit, qty);

        float pnl = o.calTp();
        float expected = qty * (entry - exit) - expectedFeeSlip(entry, qty);

        assertTrue("short PnL phai DUONG khi gia giam (got=" + pnl + ")", pnl > 0f);
        assertEquals("short PnL = qty*(entry-exit) - phi", expected, pnl, EPS);
    }

    /** (b) SHORT + gia tang vuot hard-SL -> STOP_LOSS_DONE, chot tai entry*(1+SHORT_SL_PCT), PnL ~ -SHORT_SL_PCT. */
    @Test
    public void shortHardStopLossWhenPriceRises() {
        float entry = 100f, qty = 1f;
        float slTrigger = entry * (1f + Configs.SHORT_SL_PCT);
        OrderTargetInfoTest o = newShort(entry, null, qty);
        o.timeStart = 1000L;

        // kline TAY: gia tang manh, high vuot nguong SL, open <= nguong (khong gap) -> fill dung nguong.
        KlineObjectSimple k = new KlineObjectSimple();
        k.startTime = 1000L + 60_000L; // 1 phut sau, chua cham time-stop
        k.priceOpen = entry + 5f;      // 105 <= 125
        k.maxPrice = slTrigger + 5f;   // 130 >= 125 -> trigger
        k.minPrice = entry;
        k.priceClose = slTrigger + 3f;

        o.updateStatusShort(k);

        assertEquals("phai STOP_LOSS_DONE khi gia tang vuot SL",
                OrderTargetStatus.STOP_LOSS_DONE, o.status);
        assertEquals("chot tai nguong SL (open<=SL)", slTrigger, o.priceTP, EPS);

        float pnl = o.calTp();
        float expected = qty * (entry - slTrigger) - expectedFeeSlip(entry, qty);
        assertTrue("short cat SL phai LO (got=" + pnl + ")", pnl < 0f);
        assertEquals("short SL PnL = qty*(entry-slTrigger) - phi", expected, pnl, EPS);
        // do lo ~ -SHORT_SL_PCT * notional (truoc phi)
        float rawLossRate = (entry - slTrigger) / entry;
        assertEquals("raw loss rate ~ -SHORT_SL_PCT", -Configs.SHORT_SL_PCT, rawLossRate, EPS);
    }

    /** (c) funding DUONG -> short BI TRU (calTp giam dung so tien funding). */
    @Test
    public void shortChargedWhenFundingPositive() {
        float entry = 100f, qty = 1f, exit = 90f;
        float fundingPositive = 2.0f; // rate>0 * notional -> phi duong

        OrderTargetInfoTest noFunding = newShort(entry, exit, qty);
        float pnlNoFunding = noFunding.calTp();

        OrderTargetInfoTest withFunding = newShort(entry, exit, qty);
        withFunding.time2FundingFee.put(2000L, fundingPositive); // funding duong
        float pnlWithFunding = withFunding.calTp();

        assertTrue("funding duong phai LAM GIAM PnL short", pnlWithFunding < pnlNoFunding);
        assertEquals("short bi tru dung so tien funding",
                pnlNoFunding - fundingPositive, pnlWithFunding, EPS);
    }
}
