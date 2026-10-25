import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.fill.FillAccounting;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.c3live.recon.Reconciler;
import java.math.BigDecimal;
import java.util.concurrent.atomic.AtomicLong;

/** [A1 2e] ghostClear: vi the != 0 => REFUSED, stop giu; vi the = 0 => OK. */
public class ProofGhost {
    public static void main(String[] a) {
        AtomicLong now = new AtomicLong(1_793_000_000_000L);
        MockExchangeGateway gw = new MockExchangeGateway();
        LiveBookC3 book = new LiveBookC3(null, 1.0);
        String s = "XRPUSDT", cid = "c3-XRPUSDT-1-0", sc = "c3s-XRPUSDT-1-1";
        gw.setPrice(s, new BigDecimal("1"));
        book.reserve(s, cid, 0, 1L, "BIG_DOWN", 1.0, new BigDecimal("100"), 100.0, now.get());
        book.markSending(cid, now.get());
        OrderInfo o = gw.newMarketOrder(s, Side.BUY, new BigDecimal("100"), cid, false);
        book.confirm(cid, o.getExecutedQty(), o.getAvgPrice().doubleValue(), o.getOrderId(), now.get());
        book.setTrail(s, 0.08f, 1.05f, now.get());
        gw.newStopMarket(s, Side.SELL, new BigDecimal("0.95"), sc, true);
        book.setStop(s, 0.95, sc, now.get());
        FillAccounting acct = new FillAccounting(book, gw, OrderAuditLog.dry(), null, m -> { }, null, now::get, null);
        Reconciler rec = new Reconciler(gw, book, acct, () -> null, m -> { }, null, now::get, 0.01, 2, null, null);
        rec.startup();
        System.out.println("RESULT G1 vi the 100: " + rec.ghostClear(s) + " | stop=" + gw.openStops(s).size() + " cum=" + book.isHolding(s));
        System.out.println("RESULT G2 symbol sai: " + rec.ghostClear("XRP;rm"));
        gw.setPosition(s, BigDecimal.ZERO, new BigDecimal("1"));   // owner dong tay => cum ma
        System.out.println("RESULT G3 vi the 0: " + rec.ghostClear(s) + " | stop=" + gw.openStops(s).size() + " cum=" + book.isHolding(s));
    }
}
