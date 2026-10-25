import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.fill.FillAccounting;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.c3live.recon.FlatConfirm;
import com.binance.chuyennd.c3live.recon.Reconciler;
import com.binance.chuyennd.c3live.risk.C3LiveFlattener;
import com.binance.chuyennd.ops.KillSwitchEngine;
import java.math.BigDecimal;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

/** [A1 delta 2d] MAJ-2b hoi quy + tim duong khac huy stop c3s- cua vi the THAT. */
public class ProofFlat2 {
    static class G extends MockExchangeGateway {
        volatile boolean gPos = false, gAcct = false;
        @Override public synchronized List<PositionInfo> positions() {
            return gPos ? Collections.<PositionInfo>emptyList() : super.positions();
        }
        @Override public synchronized AccountSnapshot account() {
            AccountSnapshot a = super.account();
            if (!gAcct) return a;
            return new AccountSnapshot(a.getTotalMarginBalance(), a.getTotalWalletBalance(), a.getAvailableBalance(),
                    a.getTotalUnrealizedProfit(), a.getAssets(), a.getTimeMs(), Collections.<PositionInfo>emptyList());
        }
    }
    static final String SYM = "XRPUSDT", SCID = "c3s-XRPUSDT-29883400-1";

    static LiveBookC3 setup(G gw, AtomicLong now, boolean bookKnows) {
        LiveBookC3 book = new LiveBookC3(null, 1.0);
        BigDecimal qty = new BigDecimal("100");
        gw.setPrice(SYM, new BigDecimal("1.00"));
        String cid = "c3-XRPUSDT-29883333-0";
        if (bookKnows) {
            book.reserve(SYM, cid, 0, 29_883_333L, "BIG_DOWN", 1.0, qty, 100.0, now.get());
            book.markSending(cid, now.get());
        }
        OrderInfo o = gw.newMarketOrder(SYM, Side.BUY, qty, cid, false);
        if (bookKnows) {
            book.confirm(cid, o.getExecutedQty(), o.getAvgPrice().doubleValue(), o.getOrderId(), now.get());
            book.setTrail(SYM, 0.08f, 1.05f, now.get());
        }
        gw.newStopMarket(SYM, Side.SELL, new BigDecimal("0.95"), SCID, true);
        if (bookKnows) book.setStop(SYM, 0.95, SCID, now.get());
        return book;
    }

    static String st(G gw, LiveBookC3 book) {
        return "cum=" + book.cluster(SYM).isPresent() + " stop_san=" + gw.openStops(SYM).size() + " VI_THE_THAT=" + gw.position(SYM);
    }

    public static void main(String[] a) {
        AtomicLong now = new AtomicLong(1_793_000_000_000L);
        // ---- A/B/C: Reconciler fallback
        G gw = new G();
        LiveBookC3 book = setup(gw, now, true);
        FlatConfirm fc = new FlatConfirm(gw, null, m -> System.out.println("  ALERT " + m), FlatConfirm.DEFAULT_MIN_GAP_MS, FlatConfirm.DEFAULT_MIN_READS);
        FillAccounting acct = new FillAccounting(book, gw, OrderAuditLog.dry(), null, m -> System.out.println("  ALERT " + m), null, now::get, null);
        Reconciler rec = new Reconciler(gw, book, acct, () -> null, m -> { }, null, now::get, 0.01, 2, null, fc);
        rec.startup();
        gw.gPos = true;
        for (int i = 1; i <= 6; i++) { now.addAndGet(31_000L); rec.checkPositions(); }
        System.out.println("RESULT A (positionRisk rong x6, account con vi the): " + st(gw, book));
        gw.gAcct = true;
        for (int i = 1; i <= 6; i++) { now.addAndGet(31_000L); rec.checkPositions(); }
        System.out.println("RESULT B (positionRisk + account rong x6, stop NEW con): " + st(gw, book) + " allowsEntry(XRP)=" + rec.allowsEntry(SYM)
                + " allowsEntry(BTC)=" + rec.allowsEntry("BTCUSDT"));
        // ---- F: time-stop closeCluster trong glitch
        C3LiveFlattener fl = new C3LiveFlattener(gw, book, () -> KillSwitchEngine.Action.NONE, m -> { }, null, now::get, 5, 10_000L, 10_000L, fc);
        for (int i = 1; i <= 6; i++) { now.addAndGet(31_000L); fl.closeCluster(SYM, "TIME_STOP_168H"); }
        System.out.println("RESULT F (closeCluster TIME_STOP trong glitch x6): " + st(gw, book));
        System.out.println("  FLATTEN step trong glitch:");
        C3LiveFlattener fl2 = new C3LiveFlattener(gw, book, () -> KillSwitchEngine.Action.FLATTEN, m -> { }, null, now::get, 5, 10_000L, 10_000L, fc);
        for (int i = 1; i <= 6; i++) { now.addAndGet(31_000L); fl2.step(); }
        System.out.println("RESULT F2 (FLATTEN step x6 trong glitch): " + st(gw, book));
        // ---- C: owner huy stop tay => xac nhan phang (dung y)
        gw.cancelStop(SYM, SCID);
        for (int i = 1; i <= 2; i++) { now.addAndGet(31_000L); rec.checkPositions(); }
        System.out.println("RESULT C (sau khi stop bi huy, glitch con): " + st(gw, book));
        // ---- D: so MAT/doi ten (rollback) + vi the THAT con stop c3s- => startup
        G gw2 = new G();
        AtomicLong now2 = new AtomicLong(1_793_100_000_000L);
        setup(gw2, now2, false);
        LiveBookC3 empty = new LiveBookC3(null, 1.0);
        FillAccounting acct2 = new FillAccounting(empty, gw2, OrderAuditLog.dry(), null, m -> { }, null, now2::get, null);
        Reconciler rec2 = new Reconciler(gw2, empty, acct2, () -> null, m -> System.out.println("  ALERT " + m.substring(0, Math.min(140, m.length()))),
                null, now2::get, 0.01, 2, null, null);
        Reconciler.Report r = rec2.startup();
        System.out.println("RESULT D (so rong + vi the that co stop c3s-, startup): orphanCancelled=" + r.orphanCancelled + " unknown=" + r.unknownPositions
                + " | " + st(gw2, empty));
        // ---- E: hourly sweep voi vi the la co stop c3s-
        G gw3 = new G();
        AtomicLong now3 = new AtomicLong(1_793_200_000_000L);
        LiveBookC3 b3 = setup(gw3, now3, true);
        FillAccounting acct3 = new FillAccounting(b3, gw3, OrderAuditLog.dry(), null, m -> { }, null, now3::get, null);
        Reconciler rec3 = new Reconciler(gw3, b3, acct3, () -> null, m -> { }, null, now3::get, 0.01, 2, null, null);
        rec3.startup();
        String ocid = "c3s-DOGEUSDT-29883500-1";
        gw3.setPrice("DOGEUSDT", new BigDecimal("0.10"));
        gw3.newMarketOrder("DOGEUSDT", Side.BUY, new BigDecimal("50"), "manual-1", false);
        gw3.newStopMarket("DOGEUSDT", Side.SELL, new BigDecimal("0.09"), ocid, true);
        now3.addAndGet(3_600_000L);
        Reconciler.Report r3 = rec3.hourly();
        System.out.println("RESULT E (hourly, vi the la DOGE co stop c3s-): orphanCancelled=" + r3.orphanCancelled + " DOGE_pos=" + gw3.position("DOGEUSDT")
                + " DOGE_stop_san=" + gw3.openStops("DOGEUSDT").size());
    }
}
