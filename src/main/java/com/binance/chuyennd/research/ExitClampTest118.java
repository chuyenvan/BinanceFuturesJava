package com.binance.chuyennd.research;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Unit test TASK-118 — xác nhận clamp exit price về min(priceSL, bar.open).
 *
 * <p>Case 1 (gap): bar.open &lt; priceSL → priceTP = bar.open (haircut thực tế).
 * Case 2 (thường): bar.open ≥ priceSL → priceTP = priceSL (fill đúng stop).
 *
 * <p>Chạy standalone: {@code mvn compile exec:java -Dexec.mainClass=com.binance.chuyennd.research.ExitClampTest118}
 */
public class ExitClampTest118 {
    private static final Logger LOG = LoggerFactory.getLogger(ExitClampTest118.class);

    public static void main(String[] args) {
        int pass = 0, fail = 0;

        // ── Case 1: GAP — open < priceSL ──────────────────────────────────────
        // Nến trigger: minPrice (85) < priceSL (100). Bar mở GAP xuống 88 < 100.
        // Expected: priceTP = min(100, 88) = 88.0
        {
            float priceSL = 100f;
            float priceEntry = 90f;    // priceSL > priceEntry → STOP_MARKET_DONE
            float minPrice = 85f;      // đã chạm dưới SL → trigger exit
            float priceOpen = 88f;     // gap-down: open thấp hơn SL
            float maxPrice = 92f;      // max nội nến (cao hơn open do hồi nhẹ)
            float expected = 88f;      // min(100, 88)

            OrderTargetInfoTest order = buildOrder(priceSL, priceEntry, minPrice);
            KlineObjectSimple ticker = buildTicker(priceOpen, maxPrice, minPrice);

            order.updateStatusNew(null, ticker);

            boolean ok = Math.abs(order.priceTP - expected) < 0.001f
                    && order.status == OrderTargetStatus.STOP_MARKET_DONE;
            LOG.info("[CASE1 GAP ] priceSL={} open={} max={} → priceTP={} (expected={}) {}",
                    priceSL, priceOpen, maxPrice, order.priceTP, expected, ok ? "PASS" : "FAIL");
            if (ok) pass++; else { fail++; LOG.error("CASE1 FAIL: priceTP={} status={}", order.priceTP, order.status); }
        }

        // ── Case 2: THƯỜNG — open >= priceSL ──────────────────────────────────
        // Nến trigger: minPrice (97) < priceSL (100). Bar mở bình thường 105 > 100.
        // Expected: priceTP = min(100, 105) = 100.0
        {
            float priceSL = 100f;
            float priceEntry = 90f;    // priceSL > priceEntry → STOP_MARKET_DONE
            float minPrice = 97f;      // đã chạm dưới SL → trigger exit
            float priceOpen = 105f;    // open cao hơn SL (không gap)
            float maxPrice = 110f;
            float expected = 100f;     // min(100, 105) = 100

            OrderTargetInfoTest order = buildOrder(priceSL, priceEntry, minPrice);
            KlineObjectSimple ticker = buildTicker(priceOpen, maxPrice, minPrice);

            order.updateStatusNew(null, ticker);

            boolean ok = Math.abs(order.priceTP - expected) < 0.001f
                    && order.status == OrderTargetStatus.STOP_MARKET_DONE;
            LOG.info("[CASE2 NORM] priceSL={} open={} max={} → priceTP={} (expected={}) {}",
                    priceSL, priceOpen, maxPrice, order.priceTP, expected, ok ? "PASS" : "FAIL");
            if (ok) pass++; else { fail++; LOG.error("CASE2 FAIL: priceTP={} status={}", order.priceTP, order.status); }
        }

        LOG.info("=== ExitClampTest118: {}/{} PASS ===", pass, pass + fail);
        System.exit(fail > 0 ? 1 : 0);
    }

    private static OrderTargetInfoTest buildOrder(float priceSL, float priceEntry, float minPrice) {
        OrderTargetInfoTest o = new OrderTargetInfoTest(
                OrderTargetStatus.POSITION_RUNNING, priceEntry,
                null, 1f, 10, null, 0L, 0L, OrderSide.BUY);
        o.priceSL = priceSL;
        o.minPrice = minPrice;
        o.lastPrice = minPrice;
        return o;
    }

    private static KlineObjectSimple buildTicker(float priceOpen, float maxPrice, float minPrice) {
        KlineObjectSimple k = new KlineObjectSimple();
        k.startTime = System.currentTimeMillis();
        k.priceOpen = priceOpen;
        k.maxPrice = maxPrice;
        k.minPrice = minPrice;
        k.priceClose = (priceOpen + minPrice) / 2f;
        return k;
    }
}
