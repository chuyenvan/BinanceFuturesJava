package com.binance.chuyennd.research;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.client.model.enums.OrderSide;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * ENTRY-short FUNCTION-TEST (DRAFT 2026-07-18). HAM THUAN — khong Aerospike/backtest I/O.
 *
 * <p>Ly do khong goi truc tiep {@code SimulatorMarketLevelTicker1MStopLoss.createOrderSELL}: ham do
 * di qua {@code SimpleSymbolMapper.getSymbol} + {@code CoinRankManager.getCoinTier} -> deu cham Aerospike
 * (khong the chay tren may dev thuan). Thay vao do, test DUNG LAI dung shape order ma createOrderSELL
 * emit (side=SELL, priceEntry=gia close, cung constructor) roi cho di qua LIFECYCLE thuc (updateStatusShort
 * + calTp) — do la phan quyet dinh vao/ra that su. symbol=null de bo qua getId (khong dung Aerospike),
 * giong pattern {@link ShortOrderMechanismTest}.
 *
 * <p>3 kich ban theo spec (in SO):
 * <ul>
 *   <li>(a) tin hieu selector -> lenh tao ra la SELL, priceEntry = gia close.</li>
 *   <li>(b) gia GIAM 8% roi toi TIME-STOP -> PnL DUONG ~ +8%*qty - phi.</li>
 *   <li>(c) gia TANG vuot SHORT_SL_PCT -> cat tai -SL (STOP_LOSS_DONE, PnL ~ -SL).</li>
 * </ul>
 */
public class ShortEntryLifecycleTest {

    private static final float EPS = 1e-3f;

    /**
     * Nhan ban dung cach createOrderSELL dung order: status=REQUEST, priceEntry=ticker.priceClose,
     * side=SELL, symbol=null (bo qua Aerospike). timeStart = thoi diem vao.
     */
    private static OrderTargetInfoTest entrySellFromTicker(KlineObjectSimple ticker, float qty) {
        Float entry = ticker.priceClose; // createOrderSELL: Float entry = ticker.priceClose;
        OrderTargetInfoTest o = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, null, qty,
                Configs.LEVERAGE_ORDER, null, ticker.startTime, ticker.startTime, OrderSide.SELL);
        o.minPrice = entry;
        o.maeLow = entry;
        o.lastEntry = entry;
        o.lastPrice = entry;
        return o;
    }

    private static KlineObjectSimple kline(long ts, float open, float high, float low, float close) {
        KlineObjectSimple k = new KlineObjectSimple();
        k.startTime = ts;
        k.priceOpen = open;
        k.maxPrice = high;
        k.minPrice = low;
        k.priceClose = close;
        return k;
    }

    private static float expectedFeeSlip(float entry, float qty) {
        float fee = qty * entry * Configs.RATE_FEE;
        float slip = Configs.APPLY_SLIPPAGE ? qty * entry * Configs.SLIPPAGE_RATE * 2f : 0f;
        return fee + slip;
    }

    /** (a) Tin hieu selector -> lenh la SELL, priceEntry = gia close. */
    @Test
    public void entrySignalCreatesSellOrder() {
        long t0 = 1_000_000L;
        KlineObjectSimple entryK = kline(t0, 99f, 101f, 98f, 100f); // close=100 -> gia vao
        OrderTargetInfoTest o = entrySellFromTicker(entryK, 1f);

        System.out.println("[a] side=" + o.side + " priceEntry=" + o.priceEntry);
        assertEquals("ENTRY short phai la SELL", OrderSide.SELL, o.side);
        assertEquals("priceEntry = gia close cua kline vao", 100f, o.priceEntry, EPS);
    }

    /** (b) Short + gia giam 8% roi TIME-STOP -> PnL DUONG ~ +8%*qty - phi. */
    @Test
    public void shortProfitOnDropThenTimeStop() {
        Configs.SHORT_SL_PCT = 0.25f;         // co dinh cho test (khong phu thuoc env)
        Configs.SHORT_TIME_STOP_HOURS = 24;

        float entry = 100f, qty = 1f;
        long t0 = 1_000_000L;
        OrderTargetInfoTest o = entrySellFromTicker(kline(t0, 99f, 101f, 98f, entry), qty);

        // Gia giam 8% -> ~92. Chua cham hard-SL (high 93 < slTrigger 125). Da qua 24h -> time-stop fire.
        long afterTimeStop = t0 + Configs.SHORT_TIME_STOP_HOURS * 3600_000L + 60_000L;
        KlineObjectSimple k = kline(afterTimeStop, 92f, 93f, 91f, 92f);
        o.updateStatusShort(k);

        float pnl = o.calTp();
        float expected = qty * (entry - o.priceTP) - expectedFeeSlip(entry, qty);
        System.out.println("[b] status=" + o.status + " exitTP=" + o.priceTP
                + " pnl=" + pnl + " expected=" + expected);

        assertEquals("time-stop -> STOP_LOSS_DONE", OrderTargetStatus.STOP_LOSS_DONE, o.status);
        assertEquals("thoat time-stop = max(open,close) = 92", 92f, o.priceTP, EPS);
        assertTrue("PnL phai DUONG khi gia giam 8% (got=" + pnl + ")", pnl > 0f);
        assertEquals("PnL = qty*(entry-exit) - phi", expected, pnl, EPS);
    }

    /** (c) Short + gia tang vuot SHORT_SL_PCT -> cat tai -SL. */
    @Test
    public void shortStopLossOnRise() {
        Configs.SHORT_SL_PCT = 0.25f;
        Configs.SHORT_TIME_STOP_HOURS = 24;

        float entry = 100f, qty = 1f;
        long t0 = 1_000_000L;
        OrderTargetInfoTest o = entrySellFromTicker(kline(t0, 99f, 101f, 98f, entry), qty);

        float slTrigger = entry * (1f + Configs.SHORT_SL_PCT); // 125
        // Gia tang manh trong phut ke tiep (chua toi time-stop). open<=SL -> fill dung nguong.
        KlineObjectSimple k = kline(t0 + 60_000L, 105f, slTrigger + 5f, 104f, slTrigger + 3f);
        o.updateStatusShort(k);

        float pnl = o.calTp();
        float expected = qty * (entry - slTrigger) - expectedFeeSlip(entry, qty);
        float rawLossRate = (entry - slTrigger) / entry;
        System.out.println("[c] status=" + o.status + " exitTP=" + o.priceTP
                + " pnl=" + pnl + " expected=" + expected + " rawLossRate=" + rawLossRate);

        assertEquals("gia tang vuot SL -> STOP_LOSS_DONE", OrderTargetStatus.STOP_LOSS_DONE, o.status);
        assertEquals("chot tai nguong SL (open<=SL)", slTrigger, o.priceTP, EPS);
        assertTrue("cat SL phai LO (got=" + pnl + ")", pnl < 0f);
        assertEquals("PnL = qty*(entry-slTrigger) - phi", expected, pnl, EPS);
        assertEquals("raw loss rate ~ -SHORT_SL_PCT", -Configs.SHORT_SL_PCT, rawLossRate, EPS);
    }
}
