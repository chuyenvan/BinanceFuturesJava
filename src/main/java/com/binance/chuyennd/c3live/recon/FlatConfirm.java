package com.binance.chuyennd.c3live.recon;

import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.OrderStatus;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.exec.C3LiveCids;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.function.Consumer;

/**
 * [V12 2c MAJ-2 / 2d MAJ-2b] "Symbol vang (hoac 0) trong positionRisk" KHONG dong nghia "da phang". Chi ket luan phang
 * khi co BANG CHUNG DUONG:
 * <ol>
 *   <li>(i) user stream {@code ACCOUNT_UPDATE pa=0} cho symbol (FillAccounting tu xu ly — khong qua lop nay);</li>
 *   <li>(ii) lenh dong / stop cua bot da khop het (caller kiem: lenh dong FILLED + executedQty khop, stop FINISHED/FILLED);</li>
 *   <li>(iii) (lop nay) DU CA 3 dieu kien:
 *     <ol type="a">
 *       <li>&gt;= {@code minReads} (3) lan doc positionRisk LIEN TIEP, cach nhau &gt;= {@code minGapMs} (30 s), deu vang/0;</li>
 *       <li>{@code account().positions} (/fapi/v3/account) cung vang symbol hoac positionAmt = 0 (mang null = khong biet
 *           =&gt; KHONG du);</li>
 *       <li>0 algo order {@code c3s-} con mo (NEW/chua final) cho symbol. Con stop c3s- NEW ma positionRisk rong =&gt;
 *           KHONG ket luan phang; Telegram WARN 1 lan, cho (i)/(ii) hoac owner (de stop song khi vi the da phang la vo hai:
 *           closePosition reduce-only).</li>
 *     </ol>
 *     Them: khong co lenh THUONG nao dang mo cho symbol.</li>
 * </ol>
 * Chua du => caller GIU cum + GIU stop, WARN, thu lai luot sau. Lan doc nao thay vi the &gt; 0 => xoa moc.
 * Thread-safe; dung chung giua Reconciler va C3LiveFlattener.
 */
public final class FlatConfirm {

    private static final Logger LOG = LoggerFactory.getLogger(FlatConfirm.class);
    /** [2d MAJ-2b] khoang cach toi thieu giua 2 lan doc positionRisk duoc tinh. */
    public static final long DEFAULT_MIN_GAP_MS = 30_000L;
    /** [2d MAJ-2b] so lan doc positionRisk lien tiep phai vang. */
    public static final int DEFAULT_MIN_READS = 3;

    private static final class St {
        int reads;
        long firstMs;
        long lastCountedMs;
        boolean stopWarned;
        long lastLogMs = Long.MIN_VALUE / 2;
    }

    private final ExchangeGateway gw;
    private final C3LiveOrderExecutor.ApiObserver api;
    private final Consumer<String> alert;
    private final long minGapMs;
    private final int minReads;
    private final Map<String, St> st = new TreeMap<>();

    public FlatConfirm(ExchangeGateway gw, C3LiveOrderExecutor.ApiObserver api, long minGapMs) {
        this(gw, api, null, minGapMs, DEFAULT_MIN_READS);
    }

    public FlatConfirm(ExchangeGateway gw, C3LiveOrderExecutor.ApiObserver api, Consumer<String> alert, long minGapMs,
                       int minReads) {
        this.gw = gw;
        this.api = api == null ? (a, ok) -> { } : api;
        this.alert = alert == null ? m -> { } : alert;
        this.minGapMs = Math.max(0L, minGapMs);
        this.minReads = Math.max(2, minReads);
    }

    /**
     * 1 lan doc positionRisk (thanh cong) thay {@code sym} phang (vang / 0). @return true = du bang chung (iii) (a)+(b)+(c);
     * false = giu cum + stop, thu lai sau.
     */
    public synchronized boolean observeFlat(String sym, long now, String who) {
        St s = st.get(sym);
        if (s == null) {
            s = new St();
            s.reads = 1;
            s.firstMs = now;
            s.lastCountedMs = now;
            st.put(sym, s);
            LOG.warn("[C3-LIVE-FLAT] {} {}: positionRisk khong co/0 lan 1/{} => CHUA ket luan phang, GIU cum + stop", who, sym,
                    minReads);
            return false;
        }
        if (now - s.lastCountedMs >= minGapMs) {
            s.reads++;
            s.lastCountedMs = now;
            LOG.warn("[C3-LIVE-FLAT] {} {}: positionRisk khong co/0 lan {}/{} (cach lan dau {} ms)", who, sym, s.reads, minReads,
                    now - s.firstMs);
        }
        if (s.reads < minReads) return false;
        // (b) /fapi/v3/account positions cung phai vang/0
        AccountSnapshot a;
        try {
            a = gw.account();
            api.onApiResult("account", true);
        } catch (RuntimeException e) {
            api.onApiResult("account", false);
            logHold(s, now, who, sym, "khong doc duoc account (" + e + ")");
            return false;
        }
        List<PositionInfo> ap = a == null ? null : a.getPositions();
        if (ap == null) {
            logHold(s, now, who, sym, "account() khong co mang positions (khong doi chung duoc)");
            return false;
        }
        for (PositionInfo p : ap) {
            if (sym.equals(p.getSymbol()) && p.getPositionAmt() != null && p.getPositionAmt().signum() != 0) {
                logHold(s, now, who, sym, "account().positions VAN co vi the " + p.getPositionAmt().toPlainString()
                        + " (positionRisk sai)");
                return false;
            }
        }
        // (c) 0 stop c3s- con mo
        List<OrderInfo> stops;
        try {
            stops = gw.openStops(sym);
            api.onApiResult("openStops", true);
        } catch (RuntimeException e) {
            api.onApiResult("openStops", false);
            logHold(s, now, who, sym, "khong doc duoc openStops (" + e + ")");
            return false;
        }
        int ownOpen = 0;
        for (OrderInfo o : stops == null ? Collections.<OrderInfo>emptyList() : stops) {
            String cid = o.getClientOrderId();
            OrderStatus os = o.getStatus();
            if (cid != null && cid.startsWith(C3LiveCids.STOP_PREFIX) && (os == null || !os.isFinal())) ownOpen++;
        }
        if (ownOpen > 0) {
            if (!s.stopWarned) {
                s.stopWarned = true;
                String m = "[C3-LIVE-FLAT] " + sym + ": positionRisk + account deu bao phang nhung VAN con " + ownOpen
                        + " stop c3s- NEW tren san => KHONG ket luan phang, GIU cum + stop; cho stream pa=0 / lenh dong FILLED"
                        + " hoac owner kiem tay";
                LOG.warn("{}", m);
                try {
                    alert.accept(m);
                } catch (Throwable ignore) {
                    // alert khong duoc lam hong doi chieu
                }
            }
            return false;
        }
        // lenh thuong con mo => co the con khop
        List<OrderInfo> open;
        try {
            open = gw.openOrders(sym);
            api.onApiResult("openOrders", true);
        } catch (RuntimeException e) {
            api.onApiResult("openOrders", false);
            logHold(s, now, who, sym, "khong doc duoc openOrders (" + e + ")");
            return false;
        }
        if (open != null && !open.isEmpty()) {
            logHold(s, now, who, sym, "van con " + open.size() + " lenh thuong mo");
            return false;
        }
        st.remove(sym);
        LOG.warn("[C3-LIVE-FLAT] {} {}: {} lan doc positionRisk (cach >= {} ms, tong {} ms) + account().positions deu phang +"
                + " 0 stop c3s- + 0 lenh mo => XAC NHAN phang", who, sym, s.reads, minGapMs, now - s.firstMs);
        return true;
    }

    private void logHold(St s, long now, String who, String sym, String why) {
        if (now - s.lastLogMs < 600_000L) return;
        s.lastLogMs = now;
        LOG.warn("[C3-LIVE-FLAT] {} {}: {} => CHUA ket luan phang, GIU cum + stop", who, sym, why);
    }

    /** Lan doc thay vi the &gt; 0 (hoac cum da xu ly bang bang chung khac) => xoa moc. */
    public synchronized void clear(String sym) {
        st.remove(sym);
    }

    /** Chi giu moc cua symbol con trong so. */
    public synchronized void retainOnly(Set<String> owned) {
        st.keySet().retainAll(owned);
    }

    public synchronized boolean isPending(String sym) {
        return st.containsKey(sym);
    }

    /** Co moc nao da du cach (can doc xac nhan lai). */
    public synchronized boolean anyDue(long now) {
        for (St s : st.values()) if (now - s.lastCountedMs >= minGapMs) return true;
        return false;
    }

    public synchronized Set<String> pending() {
        return Collections.unmodifiableSet(new TreeSet<>(st.keySet()));
    }

    public long minGapMs() {
        return minGapMs;
    }
}
