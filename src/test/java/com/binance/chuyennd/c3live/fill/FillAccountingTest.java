package com.binance.chuyennd.c3live.fill;

import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/** [V12 C7] Ke toan fill: xac nhan leg 1 lan, phi/realizedPnl, stop khop/thanh ly/ADL => cap nhat so + huy stop, funding/chuyen tien. */
public class FillAccountingTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    AtomicLong now = new AtomicLong(1_792_900_000_000L);
    MockExchangeGateway gw;
    LiveBookC3 book;
    FillAccounting acct;
    List<String> fills;
    List<String> alerts;
    List<String> unknown;
    List<String> closed;
    List<String> auditLines;

    @Before
    public void setUp() {
        gw = new MockExchangeGateway();
        book = new LiveBookC3(new File(tmp.getRoot(), "run/c3live_book.json"), 1.0);
        fills = new ArrayList<>();
        alerts = new ArrayList<>();
        unknown = new ArrayList<>();
        closed = new ArrayList<>();
        auditLines = new ArrayList<>();
        acct = new FillAccounting(book, gw, new OrderAuditLog(OrderAuditLog.LIVE_TAG, auditLines::add),
                (s, b, f, r) -> fills.add(s + ":" + b + ":" + f + ":" + r), alerts::add, null, now::get,
                (s, t, r, n) -> closed.add(s + ":" + r));
        acct.setUnknownPositionSink(unknown::add);
        gw.wsSink = txt -> acct.dispatch(UserStreamEvents.parse(txt));
        gw.feeRate = new BigDecimal("0.0005");
    }

    /** Mo cum qua san gia lap; executor REST + stream cung xac nhan => onFill dung 1 lan. */
    private void open(String sym, String px, String qty) {
        String cid = "c3-" + sym + "-100-0";
        assertTrue(book.reserve(sym, cid, 0, 100, "BIG_DOWN", Double.parseDouble(px), new BigDecimal(qty), 1.0, now.get()));
        book.markSending(cid, now.get());
        gw.setPrice(sym, new BigDecimal(px));
        OrderInfo o = gw.newMarketOrder(sym, Side.BUY, new BigDecimal(qty), cid, false);   // stream xac nhan truoc
        C3LiveOrderExecutor.FillObserver obs = (s, b, f, r) -> fills.add(s + ":" + b + ":" + f + ":" + r);
        // REST response den sau: confirm tra false => khong goi onFill lan 2
        if (book.confirm(cid, o.getExecutedQty(), o.getAvgPrice().doubleValue(), o.getOrderId(), now.get())) {
            obs.onFill(sym, true, o.getAvgPrice().doubleValue(), Double.parseDouble(px));
        }
    }

    @Test
    public void buyConfirmedOnceWithCommission() {
        open("AUSDT", "2", "100");
        assertEquals(1, fills.size());
        LiveBookC3.ClusterView c = book.cluster("AUSDT").get();
        assertEquals(0, new BigDecimal("100").compareTo(c.confirmedQty));
        assertEquals(0.1, c.commission, 1e-12);   // 100*2*0.0005
        assertEquals(0.1, book.account().commission, 1e-12);
        assertTrue(auditLines.stream().anyMatch(l -> l.contains("FILL") && l.contains("c3-AUSDT-100-0")));
    }

    @Test
    public void stopFillClosesClusterCancelsOtherStopsNoTelegram() throws Exception {
        open("AUSDT", "2", "100");
        gw.newStopMarket("AUSDT", Side.SELL, new BigDecimal("2.2"), "c3s-AUSDT-1-1", true);
        book.setPendingStop("AUSDT", "c3s-AUSDT-1-1", 2.2, false, now.get());
        book.promotePendingStop("AUSDT", now.get());
        gw.newStopMarket("AUSDT", Side.SELL, new BigDecimal("2.1"), "c3s-AUSDT-1-0", true);   // stop cu chua huy
        gw.setPrice("AUSDT", new BigDecimal("2.5"));
        assertEquals(2, gw.triggerStops("AUSDT", new BigDecimal("2.19")) + 1);   // 1 stop kich (2.2), stop 2.1 chua
        assertFalse("cum da dong", book.isHolding("AUSDT"));
        assertTrue("stop con lai (2.1) bi huy", gw.openStops("AUSDT").isEmpty());
        assertEquals(1, closed.size());
        assertEquals("AUSDT:" + FillAccounting.REASON_TRAILING, closed.get(0));
        assertTrue("stop khop la binh thuong => khong Telegram", alerts.isEmpty());
        assertEquals(19.0, book.account().realized, 1e-9);   // (2.19-2)*100
        List<String> ledger = Files.readAllLines(new File(tmp.getRoot(), "run/" + LiveBookC3.LEDGER_NAME).toPath());
        assertEquals(2, ledger.size());
        assertTrue(ledger.get(1), ledger.get(1).contains(FillAccounting.REASON_TRAILING));
        assertTrue(ledger.get(1), ledger.get(1).startsWith("AUSDT,"));
        assertEquals("C2 chi cho lenh MUA", 1, fills.size());
    }

    @Test
    public void liquidationAdlDelistUpdateBookAndAlert() {
        open("AUSDT", "2", "100");
        open("BUSDT", "1", "10");
        open("CUSDT", "1", "10");
        gw.forceClose("AUSDT", "autoclose-", new BigDecimal("1"));
        gw.forceClose("BUSDT", "adl_autoclose-", new BigDecimal("1.5"));
        gw.forceClose("CUSDT", "settlement_autoclose-", new BigDecimal("0.9"));
        assertEquals(0, book.openCount());
        assertEquals("AUSDT:" + FillAccounting.REASON_LIQ, closed.get(0));
        assertEquals("BUSDT:" + FillAccounting.REASON_ADL, closed.get(1));
        assertEquals("CUSDT:" + FillAccounting.REASON_SETTLE, closed.get(2));
        assertEquals(3, alerts.size());
    }

    @Test
    public void unknownPositionFundingTransfers() {
        gw.setPosition("ZZUSDT", new BigDecimal("5"), BigDecimal.ONE);
        gw.emitRaw("{\"e\":\"ACCOUNT_UPDATE\",\"E\":1,\"a\":{\"m\":\"ORDER\",\"B\":[],\"P\":[{\"s\":\"ZZUSDT\",\"pa\":\"5\",\"ep\":\"1\",\"ps\":\"BOTH\"}]}}");
        assertEquals(1, unknown.size());
        gw.emitRaw("{\"e\":\"ACCOUNT_UPDATE\",\"E\":1,\"a\":{\"m\":\"FUNDING_FEE\",\"B\":[{\"a\":\"USDT\",\"wb\":\"1\",\"cw\":\"1\",\"bc\":\"-0.75\"}],\"P\":[]}}");
        gw.emitRaw("{\"e\":\"ACCOUNT_UPDATE\",\"E\":1,\"a\":{\"m\":\"DEPOSIT\",\"B\":[{\"a\":\"BFUSD\",\"wb\":\"1\",\"cw\":\"1\",\"bc\":\"500\"}],\"P\":[]}}");
        gw.emitRaw("{\"e\":\"ACCOUNT_UPDATE\",\"E\":1,\"a\":{\"m\":\"DEPOSIT\",\"B\":[{\"a\":\"BTC\",\"wb\":\"1\",\"cw\":\"1\",\"bc\":\"0.1\"}],\"P\":[]}}");
        assertEquals(-0.75, book.account().funding, 1e-12);
        assertEquals("tai san khong on dinh khong quy USD", 500.0, book.account().transfers, 1e-12);
    }

    @Test
    public void parserToleratesGarbageAndCombinedStream() {
        assertEquals("PARSE_ERROR", UserStreamEvents.parse("{khong phai json").type);
        UserStreamEvents.Event e = UserStreamEvents.parse("{\"stream\":\"x\",\"data\":{\"e\":\"ALGO_UPDATE\",\"E\":5,"
                + "\"o\":{\"caid\":\"c3s-AUSDT-1-1\",\"aid\":9,\"s\":\"AUSDT\",\"X\":\"TRIGGERED\",\"ai\":\"123\"}}}");
        assertTrue(e instanceof UserStreamEvents.AlgoUpdate);
        assertEquals("c3s-AUSDT-1-1", ((UserStreamEvents.AlgoUpdate) e).clientAlgoId);
        acct.dispatch(e);   // khong co cum: khong nem
        assertEquals(FillAccounting.REASON_EXTERNAL, FillAccounting.exitReason("web_123", "MARKET", null));
        assertEquals(FillAccounting.REASON_TRAILING, FillAccounting.exitReason("x", "STOP_MARKET", null));
        assertEquals(FillAccounting.REASON_BOT_CLOSE, FillAccounting.exitReason("c3x-AUSDT-1-1", "MARKET", null));
    }
}
