package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.OrderStatus;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.exit.TrailingStopManager;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.rate.RateGuard;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.TreeMap;
import java.util.function.Consumer;
import java.util.function.LongSupplier;

/**
 * [V12 R4 R2] MERGED: one-way da cong don vi the LEGACY vao symbol c3 dang giu.
 * <ul>
 *   <li>Phat hien: (a) stream — lenh khong-c3 KHOP tren symbol c3 dang giu => NGAY; (b) REST — vi the san &gt; can tren so c3
 *       (hoac am) o 2 lan doc cach &gt;= 3 s.</li>
 *   <li>Xu ly: KHONG dong; stop c3 closePosition => thay bang stop qty reduceOnly = qty c3 (CUNG gia) roi huy stop cu (khong
 *       khoang trong); thay khong duoc => van HUY stop closePosition (no se dong ca phan LEGACY), trailing dat lai kieu qty;
 *       chan mo moi symbol (entry + DCA); Telegram KHAN; journal (OrderAuditLog status=MERGED).</li>
 *   <li>Go: san = qty c3 (+-eps) o 2 lan doc cach &gt;= 3 s va so khong con leg treo, hoac c3 da het vi the (cum da dong).</li>
 * </ul>
 */
public final class C3MergedGuard {

    private static final Logger LOG = LoggerFactory.getLogger(C3MergedGuard.class);
    public static final long CONFIRM_GAP_MS = 3_000L;
    public static final long ACT_DEADLINE_MS = 61_000L;
    static final long REMIND_MS = 3_600_000L;

    private final C3Scope scope;
    private final C3ScopedGateway gw;
    private final LiveBookC3 book;
    private final Consumer<String> alert;
    private final OrderAuditLog audit;
    private final LongSupplier clock;
    private volatile TrailingStopManager trailing;
    /** noi chay HANH DONG MERGED (thay/huy stop, co the cho guard toi 61 s). Mac dinh: ngay tren luong goi. Runtime: thread
     *  C3LIVE-PROTECT (khong chan luong websocket); co MERGED + chan mo moi luon dat DONG BO truoc. */
    private volatile java.util.concurrent.Executor actExec = Runnable::run;
    private final Map<String, Long> suspectSince = new TreeMap<>();
    private final Map<String, Long> releaseSince = new TreeMap<>();
    private final Map<String, Long> lastRemind = new TreeMap<>();

    public C3MergedGuard(C3Scope scope, C3ScopedGateway gw, LiveBookC3 book, Consumer<String> alert, OrderAuditLog audit,
                         LongSupplier clock) {
        this.scope = scope;
        this.gw = gw;
        this.book = book;
        this.alert = alert == null ? m -> { } : alert;
        this.audit = audit;
        this.clock = clock == null ? System::currentTimeMillis : clock;
    }

    public void setTrailing(TrailingStopManager t) {
        this.trailing = t;
    }

    public void setActExecutor(java.util.concurrent.Executor e) {
        this.actExec = e == null ? Runnable::run : e;
    }

    /** (a) stream: lenh khong-c3 khop tren symbol c3 dang giu => MERGED ngay. */
    public void onForeignFill(String sym, String detail) {
        if (sym == null || !scope.held(sym)) return;
        merge(sym, "stream: " + detail);
    }

    /** nghi van (kiem truoc ghi / stream vi the): doc xac nhan o lan poll ke tiep. */
    public synchronized void suspect(String sym) {
        if (sym == null || scope.isMerged(sym) || !scope.held(sym)) return;
        if (!suspectSince.containsKey(sym)) {
            suspectSince.put(sym, Long.MIN_VALUE);   // chua co lan doc tinh
            LOG.warn("[C3-LIVE-MERGED] {} nghi lan LEGACY => doc xac nhan (2 lan cach >= {} ms)", sym, CONFIRM_GAP_MS);
        }
    }

    /** Ops loop (5 s): co nghi van / dang MERGED => doc vi the THO toan tai khoan (1 call) va danh gia. */
    public void poll() {
        boolean need;
        synchronized (this) {
            need = !suspectSince.isEmpty() || !scope.merged().isEmpty();
        }
        if (!need) return;
        List<PositionInfo> raw;
        try {
            raw = gw.positionsAll();
        } catch (RuntimeException e) {
            LOG.warn("[C3-LIVE-MERGED] doc vi the loi ({}) => thu lai nhip sau", e.toString());
            return;
        }
        observe(raw, false);
    }

    /**
     * Danh gia tu 1 lan doc vi the THO. {@code startup}=true (khoi dong, sau khi executor giai quyet leg treo): san &gt; so c3
     * => MERGED NGAY (khong cho lan doc thu 2) — truoc khi Reconciler "san thang" ghi de so bang vi the da lan LEGACY.
     */
    public void observe(List<PositionInfo> raw, boolean startup) {
        long now = clock.getAsLong();
        Map<String, BigDecimal> amt = new TreeMap<>();
        for (PositionInfo p : raw) {
            if (p.getSymbol() == null || p.getPositionAmt() == null) continue;
            amt.merge(p.getSymbol(), p.getPositionAmt(), BigDecimal::add);
        }
        // [V12 R4b MAJOR-1] san != ledger c3 (ca 2 chieu). Ngoai khoa: thieu hut can doc BANG CHUNG thoat c3 tren san (REST).
        Map<String, String> reasons = new TreeMap<>();
        for (LiveBookC3.ClusterView c : book.clusters()) {
            String s = c.symbol;
            BigDecimal a = amt.getOrDefault(s, BigDecimal.ZERO);
            scope.noteRawAmt(s, a);
            if (scope.isMerged(s)) continue;
            BigDecimal upper = scope.c3UpperQty(s);
            if (a.signum() < 0 || a.compareTo(upper.add(C3Scope.EPS)) > 0) {
                reasons.put(s, "san " + a.toPlainString() + " > so c3 " + upper.toPlainString());
                continue;
            }
            BigDecimal open = scope.c3OpenQty(s);
            // san = 0: duong "phang" cua Reconciler/FlatConfirm (stop/thanh ly/ADL...) — khong phai MERGED
            if (c.hasUnresolved || a.signum() == 0 || a.add(C3Scope.EPS).compareTo(open) >= 0) continue;
            BigDecimal ev = evidencedExit(c);
            BigDecimal must = c.confirmedQty.subtract(ev);
            if (a.add(C3Scope.EPS).compareTo(must) >= 0) {
                LOG.info("[C3-LIVE-MERGED] {} san {} < so c3 {} nhung DUOC GIAI THICH boi bang chung thoat c3 tren san ({})", s,
                        a.toPlainString(), open.toPlainString(), ev.toPlainString());
                continue;
            }
            reasons.put(s, "san " + a.toPlainString() + " < so c3 " + open.toPlainString()
                    + " KHONG co bang chung thoat c3 (c3x-/c3s- da chung minh " + ev.toPlainString() + ")");
        }
        List<String> toMerge = new ArrayList<>();
        List<String> toAct = new ArrayList<>();
        synchronized (this) {
            for (LiveBookC3.ClusterView c : book.clusters()) {
                String s = c.symbol;
                if (scope.isMerged(s)) continue;
                String why = reasons.get(s);
                if (why == null) {
                    if (suspectSince.remove(s) != null) LOG.info("[C3-LIVE-MERGED] {} het nghi van (san = so c3 / co bang chung)", s);
                    continue;
                }
                Long since = suspectSince.get(s);
                if (startup) {
                    toMerge.add(s + "|khoi dong: " + why);
                } else if (since == null || since == Long.MIN_VALUE) {
                    suspectSince.put(s, now);
                } else if (now - since >= CONFIRM_GAP_MS) {
                    toMerge.add(s + "|REST 2 lan: " + why);
                }
            }
            suspectSince.keySet().removeIf(s -> !scope.held(s));
            for (String s : scope.merged().keySet()) {
                if (!scope.held(s)) {
                    releaseSince.remove(s);
                    scope.touchLegacy(s, now);   // phan con lai tren san = LEGACY (khong theo doi lop B / chan (A))
                    release(s, "c3 khong con vi the (cum da dong) — phan con lai la cua LEGACY");
                    continue;
                }
                BigDecimal a = amt.getOrDefault(s, BigDecimal.ZERO);
                boolean clean = !book.hasUnresolved(s) && a.subtract(scope.c3OpenQty(s)).abs().compareTo(C3Scope.EPS) <= 0;
                if (!clean) {
                    releaseSince.remove(s);
                    toAct.add(s);
                    continue;
                }
                Long rs = releaseSince.get(s);
                if (rs == null) {
                    releaseSince.put(s, now);
                } else if (now - rs >= CONFIRM_GAP_MS) {
                    releaseSince.remove(s);
                    release(s, "san = qty c3 " + a.toPlainString() + " (2 lan doc)");
                }
            }
        }
        for (String m : toMerge) {
            int i = m.indexOf('|');
            merge(m.substring(0, i), m.substring(i + 1));
        }
        for (String s : toAct) act(s, now);
    }

    private void merge(String sym, String why) {
        long now = clock.getAsLong();
        synchronized (this) {
            suspectSince.remove(sym);
            releaseSince.remove(sym);
        }
        if (scope.setMerged(sym, why)) {
            scope.markBusy(sym, "MERGED");
            String m = "[C3-LIVE] KHAN: " + sym + " MERGED (vi the LEGACY cong don vao vi the c3, one-way) — " + why + ". qty c3="
                    + scope.c3OpenQty(sym).toPlainString() + ". KHONG dong; stop closePosition => stop qty reduceOnly = qty c3;"
                    + " chan mo moi " + sym + "; owner KIEM NGAY (go tu dong khi san = qty c3)";
            LOG.error("{}", m);
            alert.accept(m);
            journal(sym, "MERGED", why, now);
            lastRemind.put(sym, now);
        }
        try {
            actExec.execute(() -> act(sym, clock.getAsLong()));
        } catch (RuntimeException e) {
            LOG.error("[C3-LIVE-MERGED] {} khong xep duoc hanh dong ({}) => chay ngay", sym, e.toString());
            act(sym, now);
        }
    }

    private void release(String sym, String why) {
        if (scope.clearMerged(sym)) {
            String m = "[C3-LIVE] " + sym + " het MERGED: " + why + " => go chan mo moi (symbol van theo LEGACY-busy)";
            LOG.warn("{}", m);
            alert.accept(m);
            journal(sym, "MERGED_RELEASED", why, clock.getAsLong());
            lastRemind.remove(sym);
        }
    }

    /**
     * [V12 R4b MAJOR-1] Qty thoat c3 CHUNG MINH tren san (dinh luong nhu canary 3h): lenh dong c3x- (executedQty) + stop c3s- da
     * kich (FINISHED/TRIGGERED => executedQty cua actualOrderId). Lay max voi exitQty cua so. Doc loi => khong tinh (fail-closed:
     * thieu hut khong giai thich => MERGED, khong dong, khong ghi de so).
     */
    BigDecimal evidencedExit(LiveBookC3.ClusterView c) {
        String sym = c.symbol;
        BigDecimal e = BigDecimal.ZERO;
        if (c.closeCid != null) {
            try {
                Optional<OrderInfo> q = gw.queryOrder(sym, c.closeCid);
                if (q.isPresent() && q.get().getExecutedQty() != null && q.get().getExecutedQty().signum() > 0) {
                    e = e.add(q.get().getExecutedQty());
                }
            } catch (RuntimeException ex) {
                LOG.warn("[C3-LIVE-MERGED] {} doc lenh dong {} loi {} => khong tinh bang chung", sym, c.closeCid, ex.toString());
            }
        }
        java.util.Set<String> cids = new java.util.LinkedHashSet<>();
        if (c.stopClientAlgoId != null) cids.add(c.stopClientAlgoId);
        if (c.pendingStopCid != null) cids.add(c.pendingStopCid);
        cids.addAll(c.orphanStops);
        for (String cid : cids) {
            try {
                Optional<OrderInfo> st = gw.queryStop(sym, cid);
                if (!st.isPresent()) continue;
                OrderStatus x = st.get().getStatus();
                String ai = st.get().getActualOrderId();
                if (!(x == OrderStatus.FINISHED || x == OrderStatus.TRIGGERED) || ai == null || ai.trim().isEmpty()) continue;
                Optional<OrderInfo> o = gw.queryOrderById(sym, Long.parseLong(ai.trim()));
                if (o.isPresent() && o.get().getExecutedQty() != null && o.get().getExecutedQty().signum() > 0) {
                    e = e.add(o.get().getExecutedQty());
                }
            } catch (RuntimeException ex) {
                LOG.warn("[C3-LIVE-MERGED] {} doc stop {} loi {} => khong tinh bang chung", sym, cid, ex.toString());
            }
        }
        BigDecimal bookExit = c.exitQty == null ? BigDecimal.ZERO : c.exitQty;
        return e.max(bookExit);
    }

    /**
     * [V12 R4e MINOR-1] San = 0: tim bang chung thoat c3 tren MOI lenh c3 (lenh dong c3x- + stop c3s- active/pending/MO COI);
     * co => nap khop THAT (userTrades theo orderId) con thieu vao so (realized c3 khong bi thieu khi mat stream) va tra ly do
     * (TRAILING_STOP neu tu stop, nguoc lai ly do dong). Khong co bang chung => null (Reconciler moi gan LOST_FOREIGN).
     */
    /** [V12 R4f MAJOR-L1] ghi khop khoi phuc DUOI khoa FillAccounting (runtime: FillAccounting::bookRecoveredExit). */
    public interface ExitBooker {
        int book(String sym, List<com.binance.chuyennd.c3live.api.TradeFill> fills, boolean merged);
    }

    private volatile ExitBooker booker;

    public void setExitBooker(ExitBooker b) {
        this.booker = b;
    }

    public String recoverC3Exit(LiveBookC3.ClusterView c) {
        String sym = c.symbol;
        long now = clock.getAsLong();
        java.util.Map<Long, String> orders = new java.util.LinkedHashMap<>();
        java.util.Set<String> cids = new java.util.LinkedHashSet<>();
        if (c.stopClientAlgoId != null) cids.add(c.stopClientAlgoId);
        if (c.pendingStopCid != null) cids.add(c.pendingStopCid);
        cids.addAll(c.orphanStops);
        for (String cid : cids) {
            try {
                Optional<OrderInfo> st = gw.queryStop(sym, cid);
                if (!st.isPresent()) continue;
                OrderStatus x = st.get().getStatus();
                String ai = st.get().getActualOrderId();
                if (!(x == OrderStatus.FINISHED || x == OrderStatus.TRIGGERED) || ai == null || ai.trim().isEmpty()) continue;
                long id = Long.parseLong(ai.trim());
                Optional<OrderInfo> o = gw.queryOrderById(sym, id);
                if (o.isPresent() && o.get().getExecutedQty() != null && o.get().getExecutedQty().signum() > 0) {
                    orders.put(id, com.binance.chuyennd.c3live.fill.FillAccounting.REASON_TRAILING);
                }
            } catch (RuntimeException ex) {
                LOG.warn("[C3-LIVE-MERGED] {} doc stop {} loi {} => khong tinh bang chung", sym, cid, ex.toString());
            }
        }
        if (c.closeCid != null) {
            try {
                Optional<OrderInfo> q = gw.queryOrder(sym, c.closeCid);
                if (q.isPresent() && q.get().getExecutedQty() != null && q.get().getExecutedQty().signum() > 0) {
                    orders.putIfAbsent(q.get().getOrderId(), c.closeReason != null ? c.closeReason
                            : com.binance.chuyennd.c3live.fill.FillAccounting.REASON_BOT_CLOSE);
                }
            } catch (RuntimeException ex) {
                LOG.warn("[C3-LIVE-MERGED] {} doc lenh dong {} loi {} => khong tinh bang chung", sym, c.closeCid, ex.toString());
            }
        }
        if (orders.isEmpty()) return null;
        BigDecimal q = BigDecimal.ZERO;
        double notional = 0d;
        boolean tradesOk = true;
        List<com.binance.chuyennd.c3live.api.TradeFill> fills = new ArrayList<>();
        for (Long id : orders.keySet()) {
            try {
                for (com.binance.chuyennd.c3live.api.TradeFill f : gw.userTrades(sym, id)) {
                    if (f.getQty() == null || f.getPrice() == null) continue;
                    fills.add(f);
                    q = q.add(f.getQty());
                    notional += f.getQty().doubleValue() * f.getPrice().doubleValue();
                }
            } catch (RuntimeException ex) {
                tradesOk = false;
                LOG.warn("[C3-LIVE-MERGED] {} doc userTrades orderId {} loi {}", sym, id, ex.toString());
            }
        }
        // [V12 R4f MAJOR-L1] KHONG tinh "thieu" tu anh chup c (cu): ghi DUOI khoa FillAccounting, doc lai cum song, chong trung tradeId
        ExitBooker bk = booker;
        if (!tradesOk && q.signum() > 0) {
            String m = "[C3-LIVE] KHAN: " + sym + " doc userTrades LOI mot phan (orderId " + orders.keySet() + ") => KHONG ghi ket qua mot"
                    + " phan; realized/phi c3 co the THIEU — owner KIEM";
            LOG.error("{}", m);
            alert.accept(m);
        } else if (q.signum() > 0 && bk != null) {
            int n = bk.book(sym, fills, scope.isMerged(sym));
            LOG.warn("[C3-LIVE-MERGED] {} khop thoat c3 qua REST (orderId {}): {} khop moi da ghi / {} (con lai da co tu stream);"
                    + " vwap {}", sym, orders.keySet(), n, fills.size(), notional / q.doubleValue());
        } else if (q.signum() > 0) {
            LOG.error("[C3-LIVE-MERGED] {} chua noi bo ghi khop (ExitBooker) => khong ghi", sym);
        } else if (!tradesOk || q.signum() == 0) {
            String m = "[C3-LIVE] " + sym + " co bang chung thoat c3 (orderId " + orders.keySet() + ") nhung KHONG doc duoc khop"
                    + " (userTrades) => realized c3 co the THIEU, owner KIEM";
            LOG.error("{}", m);
            alert.accept(m);
        }
        String reason = orders.containsValue(com.binance.chuyennd.c3live.fill.FillAccounting.REASON_TRAILING)
                ? com.binance.chuyennd.c3live.fill.FillAccounting.REASON_TRAILING : orders.values().iterator().next();
        LOG.info("[C3-LIVE-MERGED] {} san=0: bang chung thoat c3 orderId {} => ly do {} (KHONG phai LOST_FOREIGN)", sym, orders.keySet(),
                reason);
        return reason;
    }

    /**
     * [V12 R4b §4] MERGED ma san &gt;= qty c3 (LEGACY cung long): dong DUNG qty c3 (c3x- reduceOnly) la trung tinh voi LEGACY.
     * Doc vi the THO trong lan khan cap (khong bi guard rieng chan). Doc loi => false (khong dong).
     */
    public boolean exchangeCoversC3(String sym) {
        try (RateGuard.Lane lane = RateGuard.emergencyLane()) {
            BigDecimal a = BigDecimal.ZERO;
            for (PositionInfo p : gw.positionsAll()) {
                if (sym.equals(p.getSymbol()) && p.getPositionAmt() != null) a = a.add(p.getPositionAmt());
            }
            BigDecimal open = scope.c3OpenQty(sym);
            return open.signum() > 0 && a.signum() > 0 && a.add(C3Scope.EPS).compareTo(open) >= 0;
        } catch (RuntimeException e) {
            LOG.warn("[C3-LIVE-MERGED] {} doc vi the de quyet dinh dong loi {} => KHONG dong", sym, e.toString());
            return false;
        }
    }

    /**
     * [V12 R4c A] san = 0 ma so c3 con qty, KHONG co bang chung thoat c3: journal LOST_FOREIGN + Telegram KHAN + chan mo lai symbol
     * 24 h. Cum duoc Reconciler dong voi ly do LOST_FOREIGN; realized c3 CHI tu khop c3 (khong PnL ao).
     */
    public void onLostForeign(String sym, LiveBookC3.ClusterView c) {
        long now = clock.getAsLong();
        BigDecimal open = c.confirmedQty.subtract(c.exitQty == null ? BigDecimal.ZERO : c.exitQty);
        String why = "san=0, so c3 qty=" + open.toPlainString() + " khong bang chung thoat c3";
        scope.blockLost(sym, now + C3Scope.LOST_BLOCK_MS, why);
        String m = "[C3-LIVE] KHAN: " + sym + " LOST_FOREIGN: vi the san = 0 nhung so c3 con qty=" + open.toPlainString()
                + " KHONG co bang chung thoat c3 (stop c3s- / lenh c3x-) => vi the bi dong NGOAI (LEGACY ban dung qty c3 khi mat stream /"
                + " tay / thanh ly?). Ghi so: realized c3 = PnL khop c3 (khong PnL ao); CHAN mo lai " + sym + " 24 h; LEGACY co the dang tuong"
                + " minh short — owner KIEM NGAY";
        LOG.error("{}", m);
        alert.accept(m);
        if (audit != null) {
            try {
                audit.record(OrderAuditLog.Entry.of(now).symbol(sym).status("LOST_FOREIGN").reason(why).qty(open).errCode(""));
            } catch (RuntimeException e) {
                LOG.warn("[C3-LIVE-MERGED] journal loi: {}", e.toString());
            }
        }
    }

    /** Dam bao KHONG con stop closePosition cua c3 tren symbol MERGED (idempotent). */
    private void act(String sym, long now) {
        Optional<LiveBookC3.ClusterView> c = book.cluster(sym);
        if (!c.isPresent()) return;
        Long lr = lastRemind.get(sym);
        if (lr != null && now - lr >= REMIND_MS) {
            lastRemind.put(sym, now);
            alert.accept("[C3-LIVE] NHAC: " + sym + " VAN MERGED (qty c3=" + scope.c3OpenQty(sym).toPlainString() + ")");
        }
        if (c.get().stopClientAlgoId == null || c.get().stopQtyMode) return;
        String oldCid = c.get().stopClientAlgoId;
        TrailingStopManager t = trailing;
        if (t != null) {
            try (RateGuard.Urgent u = RateGuard.urgent(now + ACT_DEADLINE_MS)) {
                t.replaceStopAsQty(sym);
            } catch (RuntimeException e) {
                LOG.warn("[C3-LIVE-MERGED] {} thay stop qty loi: {}", sym, e.toString());
            }
        }
        Optional<LiveBookC3.ClusterView> c2 = book.cluster(sym);
        boolean stillCp = c2.isPresent() && oldCid.equals(c2.get().stopClientAlgoId) && !c2.get().stopQtyMode;
        boolean cpOpen = stillCp || stopOpen(sym, oldCid);
        if (!cpOpen) {
            journal(sym, "MERGED_STOP_QTY", "stop closePosition " + oldCid + " da thay bang stop qty", now);
            return;
        }
        // khong thay duoc (hoac stop cu chua huy duoc): HUY stop closePosition (no se dong ca phan LEGACY khi kich)
        try (RateGuard.Lane lane = RateGuard.emergencyLane()) {
            gw.cancelStop(sym, oldCid);
            if (stillCp) {
                String old = book.retireActiveStop(sym, now);
                if (old != null) book.removeOrphanStop(sym, old, now);
            } else {
                book.removeOrphanStop(sym, oldCid, now);
            }
            journal(sym, "MERGED_STOP_CANCEL", "huy stop closePosition " + oldCid + (stillCp ? " (chua dat duoc stop qty: trailing dat lai)" : ""), now);
            if (stillCp) {
                alert.accept("[C3-LIVE] KHAN: " + sym + " MERGED: huy stop closePosition " + oldCid
                        + " nhung CHUA dat duoc stop qty => vi the c3 TAM KHONG co stop; trailing dat lai kieu qty nhip sau");
            }
        } catch (RuntimeException e) {
            LOG.error("[C3-LIVE-MERGED] {} KHONG huy duoc stop closePosition {}: {} => thu lai nhip sau", sym, oldCid, e.toString());
        }
    }

    private boolean stopOpen(String sym, String cid) {
        try {
            for (OrderInfo o : gw.openStops(sym)) if (cid.equals(o.getClientOrderId()) && (o.getStatus() == null || !o.getStatus().isFinal())) return true;
            return false;
        } catch (RuntimeException e) {
            return true;   // khong biet => coi nhu con (huy lai: idempotent, UNKNOWN_ORDER vo hai)
        }
    }

    private void journal(String sym, String status, String why, long now) {
        if (audit == null) return;
        try {
            audit.record(OrderAuditLog.Entry.of(now).symbol(sym).status(status).reason(why)
                    .qty(scope.c3OpenQty(sym)).errCode(""));
        } catch (RuntimeException e) {
            LOG.warn("[C3-LIVE-MERGED] journal loi: {}", e.toString());
        }
    }

    public synchronized String status() {
        return "merged=" + scope.merged().keySet() + " suspect=" + suspectSince.keySet();
    }
}
