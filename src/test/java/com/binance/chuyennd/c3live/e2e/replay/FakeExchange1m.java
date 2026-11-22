package com.binance.chuyennd.c3live.e2e.replay;

import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;

import java.math.BigDecimal;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import java.util.Optional;
import java.util.function.Consumer;

/**
 * [E2E_REPLAY §3] San gia lap theo gia phut (mo rong {@link MockExchangeGateway}, CHI test).
 * <ul>
 *   <li>Moi su kien user-stream di qua hang doi rieng: ghi "su that san" ({@link #tap}) roi giao xuong {@link #downstream}.</li>
 *   <li>Vi the ve 0 sau 1 lenh BAN (MARKET hoac stop kich) => san TU EXPIRE moi stop closePosition con mo cua symbol:
 *       trang thai EXPIRED ngay (bot huy sau se nhan -2011), su kien ALGO_UPDATE den sau su kien khop
 *       ({@link #expireDelayMs} = 0: cung lo; &gt; 0: giao o nhip sau khi het tre — F4 +4 ms).</li>
 * </ul>
 */
final class FakeExchange1m extends MockExchangeGateway {

    /** Su kien JSON user-stream sau khi san phat (ghi su that). */
    volatile Consumer<String> tap = s -> { };
    /** Duong giao xuong bot (stream scope -> FillAccounting) — null = mat ket noi. */
    volatile Consumer<String> downstream = null;
    volatile long expireDelayMs = 0L;
    /** [ADD24 L0-FOLLOW-lite] cid -> gia khop that (rong = tat). */
    final java.util.Map<String, BigDecimal> followPx = new java.util.HashMap<>();
    int followHits;
    int expiredCount;

    private final Deque<String> queue = new ArrayDeque<>();
    private final List<Object[]> delayed = new ArrayList<>();
    private boolean draining;

    FakeExchange1m() {
        super.wsSink = this::enqueue;
        feeRate = new BigDecimal("0.0005");
        dynamicAccount = true;
    }

    private void enqueue(String ev) {
        synchronized (queue) {
            queue.add(ev);
        }
    }

    /** Giao het hang doi (khong de quy: su kien sinh ra trong luc giao se duoc giao tiep sau). */
    void drain() {
        if (draining) return;
        draining = true;
        try {
            while (true) {
                String ev;
                synchronized (queue) {
                    ev = queue.poll();
                }
                if (ev == null) return;
                tap.accept(ev);
                Consumer<String> d = downstream;
                if (d != null) d.accept(ev);
            }
        } finally {
            draining = false;
        }
    }

    /** Giao cac su kien tre da toi han. */
    void deliverDue(long nowMs) {
        List<Object[]> due = new ArrayList<>();
        synchronized (delayed) {
            for (Object[] d : new ArrayList<>(delayed)) {
                if ((Long) d[0] <= nowMs) {
                    due.add(d);
                    delayed.remove(d);
                }
            }
        }
        for (Object[] d : due) enqueue((String) d[1]);
        drain();
    }

    private void afterSell(String symbol) {
        if (position(symbol).signum() != 0) return;
        for (OrderInfo st : new ArrayList<>(openStops0(symbol))) {
            if (!st.isClosePosition()) continue;
            expiredCount++;
            if (expireDelayMs <= 0L) {
                exchangeEndStop(st.getClientOrderId(), "EXPIRED");   // trang thai + su kien vao hang doi (sau su kien khop)
            } else {
                // trang thai EXPIRED NGAY, su kien den tre: tach bang cach giu su kien lai
                List<String> captured = new ArrayList<>();
                Consumer<String> keep = super.wsSink;
                super.wsSink = captured::add;
                try {
                    exchangeEndStop(st.getClientOrderId(), "EXPIRED");
                } finally {
                    super.wsSink = keep;
                }
                synchronized (delayed) {
                    for (String c : captured) delayed.add(new Object[]{now + expireDelayMs, c});
                }
            }
        }
    }

    private List<OrderInfo> openStops0(String symbol) {
        return super.openStops(symbol);
    }

    @Override
    public OrderInfo newMarketOrder(String symbol, Side side, BigDecimal qty, String cid, boolean reduceOnly) {
        // [ADD24 L0-FOLLOW-lite] lenh MUA co cid trung lenh that => khop tai gia khop that (avg log FILL), roi tra gia nen
        BigDecimal fp = side == Side.BUY && cid != null ? followPx.get(cid) : null;
        BigDecimal old = fp != null ? price(symbol) : null;
        if (fp != null) {
            setPrice(symbol, fp);
            followHits++;
        }
        OrderInfo o = super.newMarketOrder(symbol, side, qty, cid, reduceOnly);
        if (fp != null && old != null) setPrice(symbol, old);
        if (side == Side.SELL) afterSell(symbol);
        drain();
        return o;
    }

    @Override
    public OrderInfo newStopMarket(String symbol, Side side, BigDecimal qty, BigDecimal stopPrice, String cid,
                                   boolean reduceOnly) {
        OrderInfo o = super.newStopMarket(symbol, side, qty, stopPrice, cid, reduceOnly);
        drain();
        return o;
    }

    @Override
    public OrderInfo cancelStop(String symbol, String cid) {
        OrderInfo o = super.cancelStop(symbol, cid);
        drain();
        return o;
    }

    /** Gia nhip: dat gia + kich stop SELL (gia &lt;= stopPrice) cua symbol, roi giao su kien. */
    int tickPrice(String symbol, BigDecimal px) {
        int n = super.triggerStops(symbol, px);
        if (n > 0) afterSell(symbol);
        drain();
        return n;
    }

    @Override
    public void forceClose(String symbol, String cidPrefix, BigDecimal price) {
        super.forceClose(symbol, cidPrefix, price);
        afterSell(symbol);
        drain();
    }

    /** Lenh LEGACY (bot LEGACY cung tai khoan, cid khong-c3) — goi THANG san, khong qua lop c3. */
    OrderInfo legacyOrder(String symbol, Side side, BigDecimal qty, String cid) {
        OrderInfo o = super.newMarketOrder(symbol, side, qty, cid, side == Side.SELL);
        drain();
        return o;
    }

    Optional<OrderInfo> stopState(String symbol, String cid) {
        return super.queryStop(symbol, cid);
    }
}
