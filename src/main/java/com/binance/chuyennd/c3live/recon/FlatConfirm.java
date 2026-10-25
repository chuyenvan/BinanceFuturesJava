package com.binance.chuyennd.c3live.recon;

import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * [V12 2c MAJ-2] "Symbol vang (hoac 0) trong positionRisk" KHONG dong nghia "da phang". Chi ket luan phang khi co BANG
 * CHUNG DUONG:
 * <ol>
 *   <li>user stream {@code ACCOUNT_UPDATE pa=0} cho symbol (FillAccounting tu xu ly — khong qua lop nay);</li>
 *   <li>lenh dong / stop cua bot da khop het (caller kiem: lenh dong FILLED + executedQty khop, stop FINISHED/FILLED);</li>
 *   <li>(lop nay) 2 lan doc positionRisk LIEN TIEP cach nhau &gt;= {@code minGapMs} (mac dinh 5 s) deu thay phang VA
 *       khong co lenh thuong nao dang mo cho symbol ({@code openOrders(sym)} rong).</li>
 * </ol>
 * Chua du => caller GIU cum + GIU stop, WARN, thu lai luot sau. Bat ky lan doc nao thay vi the &gt; 0 => xoa moc.
 * Thread-safe; dung chung giua Reconciler va C3LiveFlattener.
 */
public final class FlatConfirm {

    private static final Logger LOG = LoggerFactory.getLogger(FlatConfirm.class);
    public static final long DEFAULT_MIN_GAP_MS = 5_000L;

    private final ExchangeGateway gw;
    private final C3LiveOrderExecutor.ApiObserver api;
    private final long minGapMs;
    private final Map<String, Long> firstFlatMs = new TreeMap<>();

    public FlatConfirm(ExchangeGateway gw, C3LiveOrderExecutor.ApiObserver api, long minGapMs) {
        this.gw = gw;
        this.api = api == null ? (a, ok) -> { } : api;
        this.minGapMs = Math.max(0L, minGapMs);
    }

    /**
     * 1 lan doc positionRisk (thanh cong) thay {@code sym} phang (vang / 0). @return true = du bang chung (iii):
     * lan doc truoc cach &gt;= minGapMs cung phang VA khong co lenh thuong mo. false = giu cum + stop, thu lai sau.
     */
    public synchronized boolean observeFlat(String sym, long now, String who) {
        Long first = firstFlatMs.get(sym);
        if (first == null) {
            firstFlatMs.put(sym, now);
            LOG.warn("[C3-LIVE-FLAT] {} {}: positionRisk khong co/0 lan dau => CHUA ket luan phang, GIU cum + stop; xac nhan"
                    + " lai sau >= {} ms", who, sym, minGapMs);
            return false;
        }
        if (now - first < minGapMs) return false;
        List<OrderInfo> open;
        try {
            open = gw.openOrders(sym);
            api.onApiResult("openOrders", true);
        } catch (RuntimeException e) {
            api.onApiResult("openOrders", false);
            LOG.warn("[C3-LIVE-FLAT] {} {}: khong doc duoc lenh mo ({}) => chua ket luan phang", who, sym, e.toString());
            return false;
        }
        if (open != null && !open.isEmpty()) {
            LOG.warn("[C3-LIVE-FLAT] {} {}: van con {} lenh thuong mo => chua ket luan phang", who, sym, open.size());
            return false;
        }
        firstFlatMs.remove(sym);
        LOG.warn("[C3-LIVE-FLAT] {} {}: 2 lan doc cach {} ms deu phang + 0 lenh mo => XAC NHAN phang", who, sym, now - first);
        return true;
    }

    /** Lan doc thay vi the &gt; 0 (hoac cum da xu ly bang bang chung khac) => xoa moc. */
    public synchronized void clear(String sym) {
        firstFlatMs.remove(sym);
    }

    /** Chi giu moc cua symbol con trong so. */
    public synchronized void retainOnly(Set<String> owned) {
        firstFlatMs.keySet().retainAll(owned);
    }

    public synchronized boolean isPending(String sym) {
        return firstFlatMs.containsKey(sym);
    }

    /** Co moc nao da du cach (can doc xac nhan lai). */
    public synchronized boolean anyDue(long now) {
        for (long t : firstFlatMs.values()) if (now - t >= minGapMs) return true;
        return false;
    }

    public synchronized Set<String> pending() {
        return Collections.unmodifiableSet(new TreeSet<>(firstFlatMs.keySet()));
    }
}
