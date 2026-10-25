import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.fill.FillAccounting;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.c3live.recon.OwnStopGuard;
import com.binance.chuyennd.c3live.recon.Reconciler;
import java.math.BigDecimal;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

/** [A1 2g] MIN-21: cum vua chot ma san THAT con vi the (stream bao sai/khop mot phan) + loi doc keo dai => sau 10' co len (A)? */
public class ProofB {
    static class G extends MockExchangeGateway {
        volatile boolean errPos = false, errAcct = false;
        @Override public synchronized List<PositionInfo> positions() {
            if (errPos) throw new GatewayException(ErrorKind.OTHER, "503 gia lap", false);
            return super.positions();
        }
        @Override public synchronized AccountSnapshot account() {
            if (errAcct) throw new GatewayException(ErrorKind.OTHER, "503 gia lap", false);
            return super.account();
        }
    }

    static void run(String title, boolean errPos, boolean errAcct) {
        AtomicLong now = new AtomicLong(1_793_000_000_000L);
        G gw = new G();
        LiveBookC3 book = new LiveBookC3(null, 1.0);
        String s = "XUSDT", cid = "c3-XUSDT-1-0", sc = "c3s-XUSDT-1-1";
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
        OwnStopGuard g = new OwnStopGuard(gw, book, null, m -> { }, () -> rec::onUnknownPosition, now::get);
        rec.setStopGuard(g); acct.setStopGuard(g); acct.setUnknownPositionSink(rec::onUnknownPosition);
        rec.startup();
        // stream bao cum dong (sai) trong khi san THAT con 100; doc loi bat dau dung luc nay
        gw.errPos = errPos; gw.errAcct = errAcct;
        acct.closedOnExchange(s, "TRAILING_STOP", now.get());
        StringBuilder tl = new StringBuilder();
        for (int m = 0; m <= 16; m++) {
            if (m > 0) for (int k = 0; k < 2; k++) { now.addAndGet(30_000L); rec.confirmPendingFlat(); }
            if (m % 2 == 0 || m == 11) {
                tl.append(" t=").append(m).append("':Y=").append(rec.allowsEntry("YUSDT") ? "OK" : "CHAN")
                  .append(",A=").append(rec.blocks().containsKey("UNKNOWN_POSITION") ? 1 : 0)
                  .append(",B=").append(rec.symbolBlocks().contains(s) ? 1 : 0);
            }
        }
        System.out.println("RESULT " + title + " | stop_con=" + gw.openStops(s).size() + " pos=" + gw.position(s) + " |" + tl);
    }

    public static void main(String[] a) {
        run("R5 san con vi the, doc OK", false, false);
        run("R6 san con vi the, positionRisk LOI keo dai", true, false);
        run("R7 san con vi the, account LOI keo dai", false, true);
        run("R8 san con vi the, ca hai LOI keo dai", true, true);
    }
}
