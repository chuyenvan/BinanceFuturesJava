package com.binance.chuyennd.tradecore.selector;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

import static org.junit.Assert.*;

/**
 * [V12 R4q MIN-1] SHADOW_NO_PUSH=false (c3_live) KHONG duoc mo lai duong lenh THAT cua consumer queue LEGACY.
 * (1) quyet dinh: c3_live => chan tru khi LEGACY_QUEUE_LIVE_BLOCK=false; c3_shadow / tat => khong doi hanh vi cu.
 * (2) ma nguon: chot chan dung TRUOC forceNoPush/shadowHandle va TRUOC OrderHelper.newOrderMarket trong processOrderNewMarketNew;
 * producer DetectEntrySignal2TradeNormal: c3_live => shadowHandleOrder, KHONG rpush.
 */
public class LegacyQueueLiveBlockTest {

    @Test
    public void decision() {
        assertTrue(LiveProfileC3.decideLegacyQueueBlock(true, null));
        assertTrue(LiveProfileC3.decideLegacyQueueBlock(true, ""));
        assertTrue(LiveProfileC3.decideLegacyQueueBlock(true, "true"));
        assertTrue("gia tri la => chan", LiveProfileC3.decideLegacyQueueBlock(true, "0"));
        assertFalse(LiveProfileC3.decideLegacyQueueBlock(true, " FALSE "));
        assertFalse("c3_shadow/tat: giu duong cu", LiveProfileC3.decideLegacyQueueBlock(false, null));
    }

    private static String src(String rel) throws Exception {
        return new String(Files.readAllBytes(Paths.get("src/main/java/com/binance/chuyennd/" + rel)), StandardCharsets.UTF_8);
    }

    @Test
    public void consumerGuardBeforeRealOrder() throws Exception {
        String s = src("trading/BinanceOrderTradingManager.java");
        int m = s.indexOf("private void processOrderNewMarketNew(");
        assertTrue(m > 0);
        int end = s.indexOf("static void shadowHandleOrder(", m);
        String body = s.substring(m, end);
        int g = body.indexOf("LiveProfileC3.legacyQueueNewOrderBlocked()");
        int fnp = body.indexOf("LiveProfileC3.forceNoPush()");
        int real = body.indexOf("OrderHelper.newOrderMarket(");
        assertTrue("co chot", g > 0);
        assertTrue("chot truoc forceNoPush/shadowHandle", g < fnp);
        assertTrue("chot truoc lenh that", g < real);
        assertTrue("chot return", body.substring(g, fnp).contains("return;"));
    }

    @Test
    public void producerNeverRpushOnC3Live() throws Exception {
        String s = src("trading/DetectEntrySignal2TradeNormal.java");
        int r = s.indexOf("rpush(RedisConst.REDIS_KEY_BINANCE_TD_ORDER_MANAGER_QUEUE");
        assertTrue(r > 0);
        String before = s.substring(Math.max(0, r - 2500), r);
        int iL = before.lastIndexOf("LiveProfileC3.isLive()");
        int sh = before.lastIndexOf("BinanceOrderTradingManager.shadowHandleOrder(orderTrade)");
        int el = before.lastIndexOf("} else {");
        assertTrue("isLive => nhanh shadowHandle, rpush chi o else", iL > 0 && sh > iL && el > sh);
    }
}
