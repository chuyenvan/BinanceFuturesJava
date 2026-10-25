import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.fill.FillAccounting;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.c3live.recon.Reconciler;
import java.math.BigDecimal;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

/** [A1 delta 2c] MAJ-2 du: mat stream + positionRisk RONG gia 2 lan cach >= 5 s => FlatConfirm (iii) co xac nhan phang khong? */
public class ProofFlat {
    static class GlitchGw extends MockExchangeGateway {
        volatile boolean glitch = false;
        @Override public synchronized List<PositionInfo> positions() {
            List<PositionInfo> real = super.positions();
            return glitch ? Collections.<PositionInfo>emptyList() : real;
        }
    }

    public static void main(String[] a) throws Exception {
        GlitchGw gw = new GlitchGw();
        AtomicLong now = new AtomicLong(1_793_000_000_000L);
        LiveBookC3 book = new LiveBookC3(null, 1.0);
        String sym = "XRPUSDT";
        BigDecimal qty = new BigDecimal("100");
        gw.setPrice(sym, new BigDecimal("1.00"));
        String cid = "c3-XRPUSDT-29883333-0";
        book.reserve(sym, cid, 0, 29_883_333L, "BIG_DOWN", 1.0, qty, 100.0, now.get());
        book.markSending(cid, now.get());
        OrderInfo o = gw.newMarketOrder(sym, Side.BUY, qty, cid, false);
        book.confirm(cid, o.getExecutedQty(), o.getAvgPrice().doubleValue(), o.getOrderId(), now.get());
        book.setTrail(sym, 0.08f, 1.05f, now.get());
        String scid = "c3s-XRPUSDT-29883400-1";
        gw.newStopMarket(sym, Side.SELL, new BigDecimal("1.05"), scid, true);
        book.setStop(sym, 1.05, scid, now.get());
        // vi the LA (khong thuoc so) de xem block UNKNOWN
        gw.setPosition("DOGEUSDT", new BigDecimal("50"), new BigDecimal("0.1"));
        FillAccounting acct = new FillAccounting(book, gw, OrderAuditLog.dry(), null, m -> System.out.println("  ALERT " + m), null, now::get, null);
        Reconciler rec = new Reconciler(gw, book, acct, () -> null, m -> System.out.println("  ALERT " + m.substring(0, Math.min(160, m.length()))),
                null, now::get, 0.01, 2, null);
        acct.setUnknownPositionSink(rec::onUnknownPosition);
        System.out.println("allowsEntry truoc startup = " + rec.allowsEntry("BTCUSDT"));
        Reconciler.Report r0 = rec.startup();
        System.out.println("startup ok=" + r0.ok + " blocks=" + rec.blocks().keySet() + " pos XRP=" + gw.position(sym) + " cum=" + book.cluster(sym).isPresent());
        // glitch: positionRisk 200 nhung rong
        gw.glitch = true;
        now.addAndGet(10_000L);
        Reconciler.Report r1 = rec.checkPositions();
        System.out.println("doc 1 (rong): flatPending=" + r1.flatPending + " closed=" + r1.closedWhileDown + " blocks=" + rec.blocks().keySet()
                + " allowsEntry(BTC)=" + rec.allowsEntry("BTCUSDT"));
        System.out.println("  openStops(XRP) truoc doc 2 = " + gw.openStops(sym).size() + " (stop c3s- van NEW tren san)");
        now.addAndGet(10_000L);
        Reconciler.Report r2 = rec.checkPositions();
        System.out.println("doc 2 (rong, +10 s): closed=" + r2.closedWhileDown + " cum_con=" + book.cluster(sym).isPresent()
                + " stop_con_tren_san=" + gw.openStops(sym).size() + " VI THE THAT XRP=" + gw.position(sym));
        gw.glitch = false;
        now.addAndGet(10_000L);
        Reconciler.Report r3 = rec.checkPositions();
        System.out.println("doc 3 (het glitch): unknown=" + r3.unknownPositions + " blocks=" + rec.blocks().keySet());
    }
}
