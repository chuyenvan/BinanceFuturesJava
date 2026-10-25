package com.binance.chuyennd.c3live.recon;

import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.exec.C3LiveCids;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;
import java.util.function.LongSupplier;
import java.util.function.Supplier;

/**
 * [V12 2e MAJ-3] DIEM DUY NHAT huy stop {@code c3s-} cua bot. Stop c3s- khong co trong so ("mo coi") hoac stop con lai sau khi
 * cum duoc coi la da dong CHI bi huy khi:
 * <ul>
 *   <li>stop do khong con mo tren san (=> coi nhu da het, khong goi huy), HOAC</li>
 *   <li>so dang giu cum symbol do voi stop ACTIVE khac va stop active do DANG MO tren san (stop cu bi thay — van co bao ve), HOAC</li>
 *   <li>CA positionRisk LAN {@code account().positions} cung bao symbol phang (vang / amt = 0).</li>
 * </ul>
 * Mot trong hai nguon con vi the != 0, hoac doc loi / account khong co mang positions => GIU stop, dua symbol vao
 * UNKNOWN_POSITION (neu so khong giu symbol; [2f] tru cum so VUA chot va vi the doc duoc => chi chan rieng symbol), ghi
 * vao danh sach "dang giu" (Reconciler thu lai) va Telegram (lan dau ngay, nhac lai moi 6 h/symbol).
 * Hai duong KHONG qua guard (co chu dich, caller tu dam bao): {@link #cancelReplaced} (stop moi cua cum da len san va thanh
 * active) va {@link #cancelRetired} (cum dang giu bi go arm do DCA nhu so giay).
 */
public final class OwnStopGuard {

    private static final Logger LOG = LoggerFactory.getLogger(OwnStopGuard.class);
    /** Telegram GIU stop: lan dau ngay, nhac lai moi 6 h/symbol (cung nhip nhac cum ma). */
    static final long ALERT_EVERY_MS = FlatConfirm.GHOST_REMIND_MS;

    public enum Result { CANCELLED, GONE, KEPT_POSITION, KEPT_READ_ERROR, CANCEL_ERROR }

    /** cid -> symbol cua stop c3s- dang bi GIU (Reconciler thu huy lai moi lan doc vi the; con giu => khong go UNKNOWN). */
    private final Map<String, String> kept = new ConcurrentHashMap<>();

    private final ExchangeGateway gw;
    private final LiveBookC3 book;
    private final C3LiveOrderExecutor.ApiObserver api;
    private final Consumer<String> alert;
    private final Supplier<Consumer<String>> unknownSink;
    private final LongSupplier clock;
    private final Map<String, Long> lastAlertMs = new ConcurrentHashMap<>();

    public OwnStopGuard(ExchangeGateway gw, LiveBookC3 book, C3LiveOrderExecutor.ApiObserver api, Consumer<String> alert,
                        Supplier<Consumer<String>> unknownSink, LongSupplier clock) {
        this.gw = gw;
        this.book = book;
        this.api = api == null ? (a, ok) -> { } : api;
        this.alert = alert == null ? m -> { } : alert;
        this.unknownSink = unknownSink == null ? () -> s -> { } : unknownSink;
        this.clock = clock == null ? System::currentTimeMillis : clock;
    }

    /** Huy stop c3s- KHONG co stop thay the da xac nhan: chi khi ca 2 nguon vi the deu phang (xem lop). */
    public synchronized Result cancelOwnStopGuarded(String sym, String cid, String why) {
        if (sym == null || cid == null) return Result.GONE;
        List<OrderInfo> open;
        try {
            open = gw.openStops(sym);
            api.onApiResult("openStops", true);
        } catch (RuntimeException e) {
            api.onApiResult("openStops", false);
            return keep(sym, cid, why, Result.KEPT_READ_ERROR, "khong doc duoc openStops (" + e + ")");
        }
        boolean isOpen = false;
        for (OrderInfo o : open) if (cid.equals(o.getClientOrderId()) && !o.getStatus().isFinal()) isOpen = true;
        if (!isOpen) {
            kept.remove(cid);
            return Result.GONE;
        }
        // stop cu cua cum dang giu, da co stop active khac DANG MO tren san => van co bao ve, huy duoc
        Optional<LiveBookC3.ClusterView> c = book == null ? Optional.<LiveBookC3.ClusterView>empty() : book.cluster(sym);
        if (c.isPresent() && c.get().stopClientAlgoId != null && !cid.equals(c.get().stopClientAlgoId)) {
            String act = c.get().stopClientAlgoId;
            for (OrderInfo o : open) {
                if (act.equals(o.getClientOrderId()) && !o.getStatus().isFinal()) return doCancel(sym, cid, why + " (thay boi " + act + ")");
            }
        }
        // con lai: CA positionRisk LAN account().positions phai phang
        BigDecimal pr;
        try {
            List<PositionInfo> ps = gw.positions();
            api.onApiResult("positions", true);
            pr = amt(ps, sym);
        } catch (RuntimeException e) {
            api.onApiResult("positions", false);
            return keep(sym, cid, why, Result.KEPT_READ_ERROR, "khong doc duoc positionRisk (" + e + ")", true);
        }
        BigDecimal ac;
        try {
            AccountSnapshot a = gw.account();
            api.onApiResult("account", true);
            if (a == null || a.getPositions() == null) {
                return keep(sym, cid, why, Result.KEPT_READ_ERROR, "account() khong co mang positions", true);
            }
            ac = amt(a.getPositions(), sym);
        } catch (RuntimeException e) {
            api.onApiResult("account", false);
            return keep(sym, cid, why, Result.KEPT_READ_ERROR, "khong doc duoc account (" + e + ")", true);
        }
        if (pr.signum() != 0 || ac.signum() != 0) {
            return keep(sym, cid, why, Result.KEPT_POSITION, "vi the != 0 (positionRisk=" + pr.toPlainString() + " account="
                    + ac.toPlainString() + ")");
        }
        return doCancel(sym, cid, why + " (positionRisk + account deu phang)");
    }

    /** Stop cu bi thay: caller VUA dat stop moi va stop moi da la active trong so (san xac nhan) => huy truc tiep. */
    public Result cancelReplaced(String sym, String cid, String why) {
        return doCancel(sym, cid, why);
    }

    /** Cum dang giu bi go arm (DCA reset nhu so giay) => huy truc tiep, co chu dich. */
    public Result cancelRetired(String sym, String cid, String why) {
        return doCancel(sym, cid, why);
    }

    private Result doCancel(String sym, String cid, String why) {
        try {
            gw.cancelStop(sym, cid);
            api.onApiResult("cancelStop", true);
            kept.remove(cid);
            LOG.info("[C3-LIVE-STOPGUARD] huy stop {} {} — {}", sym, cid, why);
            return Result.CANCELLED;
        } catch (GatewayException e) {
            boolean gone = e.getKind() == ErrorKind.UNKNOWN_ORDER;
            api.onApiResult("cancelStop", gone);
            if (gone) {
                kept.remove(cid);
                return Result.GONE;
            }
            LOG.warn("[C3-LIVE-STOPGUARD] {} huy stop {} loi {} => thu lai sau", sym, cid, e.getKind());
            return Result.CANCEL_ERROR;
        } catch (RuntimeException e) {
            api.onApiResult("cancelStop", false);
            return Result.CANCEL_ERROR;
        }
    }

    /** Ban sao cid -> symbol cac stop c3s- dang bi giu. */
    public Map<String, String> keptStops() {
        return new java.util.TreeMap<>(kept);
    }

    /** [2f] tap symbol con stop c3s- dang bi giu. */
    public java.util.Set<String> keptSymbols() {
        return new java.util.TreeSet<>(kept.values());
    }

    /** true neu con stop c3s- cua symbol dang bi giu. */
    public boolean hasKept(String sym) {
        return sym != null && kept.containsValue(sym);
    }

    /** Bo theo doi (vd stop da duoc so nhan lai lam stop cua cum). */
    public void forget(String cid) {
        if (cid != null) kept.remove(cid);
    }

    /**
     * [2f] Symbol so DA BIET: cum vua bi so xoa (chot) trong {@link #KNOWN_CLOSE_WINDOW_MS} gan day (cung JVM). Vi the con
     * thay tren san cua symbol nay = san tre/chua cap nhat => lop chan (B) CHI symbol do; qua cua so => coi la vi the la (A).
     */
    public static boolean recentlyClosed(LiveBookC3 book, String sym, long now) {
        if (book == null || sym == null) return false;
        long t = book.lastRemovedMs(sym);
        return t != Long.MIN_VALUE && now - t >= 0L && now - t < KNOWN_CLOSE_WINDOW_MS;
    }

    /** [2f] cua so "so da biet vua chot" (B); qua cua so ma vi the con => leo thang UNKNOWN toan he (A). */
    public static final long KNOWN_CLOSE_WINDOW_MS = 600_000L;

    private Result keep(String sym, String cid, String why, Result r, String detail) {
        return keep(sym, cid, why, r, detail, false);
    }

    /**
     * Giu stop. Lop chan: so dang giu cum => khong chan them; cum so vua chot (B) => Reconciler chi chan symbol nay (qua
     * {@link #hasKept}); con lai (vi the la, so mat, qua cua so) hoac KHONG doc duoc vi the (positionRisk/account) => (A)
     * UNKNOWN_POSITION toan he.
     */
    private Result keep(String sym, String cid, String why, Result r, String detail, boolean positionsUnreadable) {
        kept.put(cid, sym);
        long now = clock.getAsLong();
        boolean held = book != null && book.isHolding(sym);
        boolean global = !held && (positionsUnreadable || !recentlyClosed(book, sym, now));
        if (global) {
            try {
                unknownSink.get().accept(sym);
            } catch (Throwable ignore) {
                // khong lam hong guard
            }
        }
        Long last = lastAlertMs.get(sym);
        String m = "[C3-LIVE-STOPGUARD] GIU stop " + sym + " " + cid + " (" + why + "): " + detail
                + (held ? "" : global ? " => symbol vao UNKNOWN_POSITION (chan mo moi TOAN HE)"
                : " => cum so vua chot: CHI chan mo moi " + sym + " toi khi xac nhan phang") + "; owner kiem tay neu keo dai";
        if (last == null || now - last >= ALERT_EVERY_MS) {
            lastAlertMs.put(sym, now);
            LOG.warn("{}", m);
            try {
                alert.accept(m);
            } catch (Throwable ignore) {
                // alert khong duoc lam hong guard
            }
        } else {
            LOG.info("{}", m);
        }
        return r;
    }

    private static BigDecimal amt(List<PositionInfo> ps, String sym) {
        BigDecimal s = BigDecimal.ZERO;
        if (ps == null) return s;
        for (PositionInfo p : ps) {
            // tong |amt|: hedge mode LONG + SHORT bu tru nhau KHONG duoc coi la phang
            if (sym.equals(p.getSymbol()) && p.getPositionAmt() != null) s = s.add(p.getPositionAmt().abs());
        }
        return s;
    }

    /** true neu cid la stop cua bot. */
    public static boolean isOwn(String cid) {
        return cid != null && cid.startsWith(C3LiveCids.STOP_PREFIX);
    }
}
