import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.ErrorKind;
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
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

/** [A1 delta 2f] 3 cum chot cung luc (stream pa=0), REST tre 60 s, 24 leg moi den: symbol khac co vao duoc khong? */
public class ProofCrash {
    static class Lag extends MockExchangeGateway {
        AtomicLong clk; long frozenUntil = Long.MIN_VALUE; List<PositionInfo> fp; AccountSnapshot fa; boolean readErr;
        @Override public synchronized List<PositionInfo> positions() {
            if (readErr) throw new GatewayException(ErrorKind.OTHER, "503 gia lap", false);
            return clk.get() < frozenUntil ? fp : super.positions();
        }
        @Override public synchronized AccountSnapshot account() { return clk.get() < frozenUntil ? fa : super.account(); }
        void freeze(long ms) { fp = new ArrayList<>(super.positions()); fa = super.account(); frozenUntil = clk.get() + ms; }
    }
    static String[] CL = {"AUSDT", "BUSDT", "CUSDT"};

    static void run(String title, boolean extraOrphanStop, boolean readErr, boolean restart) {
        AtomicLong now = new AtomicLong(1_793_000_000_000L);
        Lag gw = new Lag(); gw.clk = now;
        LiveBookC3 book = new LiveBookC3(null, 1.0);
        int k = 0;
        for (String s : CL) {
            gw.setPrice(s, new BigDecimal("1.00"));
            String cid = "c3-" + s + "-2988" + (k++) + "-0";
            book.reserve(s, cid, 0, 29_880L + k, "BIG_DOWN", 1.0, new BigDecimal("100"), 100.0, now.get());
            book.markSending(cid, now.get());
            OrderInfo o = gw.newMarketOrder(s, Side.BUY, new BigDecimal("100"), cid, false);
            book.confirm(cid, o.getExecutedQty(), o.getAvgPrice().doubleValue(), o.getOrderId(), now.get());
            book.setTrail(s, 0.08f, 1.05f, now.get());
            String sc = "c3s-" + s + "-1-1";
            gw.newStopMarket(s, Side.SELL, new BigDecimal("1.05"), sc, true);
            book.setStop(s, 1.05, sc, now.get());
        }
        List<String> alerts = new ArrayList<>();
        FillAccounting acct = new FillAccounting(book, gw, OrderAuditLog.dry(), null, alerts::add, null, now::get, null);
        Reconciler rec = new Reconciler(gw, book, acct, () -> null, alerts::add, null, now::get, 0.01, 2, null, null);
        OwnStopGuard g = new OwnStopGuard(gw, book, null, alerts::add, () -> rec::onUnknownPosition, now::get);
        rec.setStopGuard(g); acct.setStopGuard(g); acct.setUnknownPositionSink(rec::onUnknownPosition);
        rec.startup();
        if (extraOrphanStop) for (String s : CL) gw.newStopMarket(s, Side.SELL, new BigDecimal("0.90"), "c3s-" + s + "-1-0", true);   // stop cu chua kip huy (sau startup)
        // san: 3 stop kich (vi the ve 0), REST tre 60 s
        gw.freeze(60_000L);
        for (String s : CL) gw.triggerStops(s, new BigDecimal("1.04"));
        gw.readErr = readErr;
        now.addAndGet(1_000L);
        for (String s : CL) acct.closedOnExchange(s, "TRAILING_STOP", now.get());   // = xu ly ACCOUNT_UPDATE pa=0
        gw.readErr = false;
        System.out.println("   DBG sau closedOnExchange: open=" + gw.openStops(null).size() + " kept=" + g.keptStops() + " stale_pos=" + gw.positions().size() + " frozenUntil-now=" + (gw.frozenUntil - now.get()));
        Reconciler use = rec;
        if (restart) {   // restart trong 10': mat moc removeCluster (RAM)
            LiveBookC3 b2 = new LiveBookC3(null, 1.0);
            FillAccounting a2 = new FillAccounting(b2, gw, OrderAuditLog.dry(), null, alerts::add, null, now::get, null);
            use = new Reconciler(gw, b2, a2, () -> null, alerts::add, null, now::get, 0.01, 2, null, null);
            use.startup();
        }
        now.addAndGet(5_000L);
        use.confirmPendingFlat(); use.checkPositions();   // nhip ops + hourly/fallback trong luc REST tre
        int ok = 0; List<String> no = new ArrayList<>();
        for (int i = 0; i < 24; i++) { String y = "Y" + i + "USDT"; if (use.allowsEntry(y)) ok++; else no.add(y); }
        int okCl = 0; for (String s : CL) if (use.allowsEntry(s)) okCl++;
        System.out.println("RESULT " + title + ": 24 leg symbol khac vao duoc=" + ok + "/24, 3 symbol vua chot vao duoc=" + okCl + "/3, blocks="
                + use.blocks().keySet() + " symBlocks=" + use.symbolBlocks() + " stop_con=" + (gw.openStops(null).size()));
        // REST bat kip + 2 lan doc cach 31 s
        for (int i = 0; i < 4; i++) { now.addAndGet(31_000L); use.confirmPendingFlat(); use.checkPositions(); }
        ok = 0; for (int i = 0; i < 24; i++) if (use.allowsEntry("Y" + i + "USDT")) ok++;
        okCl = 0; for (String s : CL) if (use.allowsEntry(s)) okCl++;
        System.out.println("   sau ~2' (REST het tre): 24 leg=" + ok + "/24, 3 symbol chot=" + okCl + "/3, blocks=" + use.blocks().keySet()
                + " symBlocks=" + use.symbolBlocks() + " stop_con=" + gw.openStops(null).size());
    }

    public static void main(String[] a) {
        run("R1 duong thuong (chi stop vua kich)", false, false, false);
        run("R2 moi cum con 1 stop c3s- cu chua huy", true, false, false);
        run("R3 = R2 + REST loi doc luc chot", true, true, false);
        run("R4 = R2 + restart trong 10'", true, false, true);
    }
}
