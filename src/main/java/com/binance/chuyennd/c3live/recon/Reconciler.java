package com.binance.chuyennd.c3live.recon;

import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.OrderStatus;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.exec.C3LiveCids;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.fill.FillAccounting;
import com.binance.chuyennd.c3live.filters.SymbolRules;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.function.Consumer;
import java.util.function.LongSupplier;
import java.util.function.Supplier;

/**
 * [V12 C9] Doi chieu so THAT c3_live voi san (tai khoan con).
 * <ul>
 *   <li><b>Khoi dong</b> ({@link #startup}): {@code positions()} + {@code openStops()} + so persist =>
 *     <ul>
 *       <li>cum co qty xac nhan nhung san = 0 => da dong khi bot chet: stop cua cum o trang thai da kich => TRAILING_STOP,
 *           khong thi EXTERNAL (Telegram) — {@link FillAccounting#closedOnExchange} (huy stop con lai, xoa cum);</li>
 *       <li>qty/gia san khac so => SAN THANG ({@link LiveBookC3#overrideFromExchange}) + WARN/Telegram;</li>
 *       <li>stop pending/active cua so: co tren san => giu (pending => nhan); KHONG co ma cum da arm => bo tham chieu,
 *           {@code TrailingStopManager} dat lai o nhip ke (round-down priceSL logic da persist);</li>
 *       <li>stop {@code c3s-} tren san khong duoc so tham chieu => MO COI => huy; stop khac (khong phai cua bot) => chi WARN;</li>
 *       <li>vi the san KHONG co trong so (hoac vi the am) => CHAN mo moi + Telegram, KHONG tu dong.</li>
 *     </ul></li>
 *   <li><b>Hang gio</b> ({@link #hourly}): |equity so - totalMarginBalance| / totalMarginBalance &gt; 1 % => Telegram +
 *       NO_NEW_ENTRY (chi duong c3_live), tu go khi KHOP lai 2 lan lien tiep. Equity so = moc + da chot - phi + funding +
 *       chuyen tien (tu C7) + lai chua chot tren qty/gia SO voi markPrice san. Chua co moc (lan dau) hoac so trong
 *       (0 cum, 0 leg treo) => dat lai moc = totalMarginBalance - lai chua chot (khong ket luan). File yeu cau
 *       {@code run/c3live_reanchor.req} (script owner) => dat lai moc.</li>
 *   <li><b>Fallback</b> ({@link #checkPositions}): khi mat user stream — cum co qty ma san = 0 => cap nhat so (nhu khoi dong).</li>
 * </ul>
 * {@link #allowsEntry} = khong co ly do chan nao. Thread-safe. Khong bao gio nem ra ngoai.
 */
public final class Reconciler {

    private static final Logger LOG = LoggerFactory.getLogger(Reconciler.class);
    public static final double DEFAULT_EQUITY_TOL = 0.01d;
    public static final int DEFAULT_MATCH_TO_RELEASE = 2;
    public static final String BLOCK_UNKNOWN = "UNKNOWN_POSITION";
    public static final String BLOCK_EQUITY = "EQUITY_MISMATCH";
    public static final String BLOCK_STARTUP = "STARTUP_RECON";
    public static final String DEFAULT_REANCHOR_FILE = "run/c3live_reanchor.req";
    static final BigDecimal REL_QTY_TOL = new BigDecimal("1e-9");

    /** Ket qua 1 luot (cho log/test). */
    public static final class Report {
        public final List<String> closedWhileDown = new ArrayList<>();
        public final List<String> overridden = new ArrayList<>();
        public final List<String> stopsDropped = new ArrayList<>();
        public final List<String> pendingPromoted = new ArrayList<>();
        public final List<String> orphanCancelled = new ArrayList<>();
        public final List<String> foreignStops = new ArrayList<>();
        public final List<String> unknownPositions = new ArrayList<>();
        /** [2c MAJ-2] cum co qty ma positionRisk vang/0, CHUA du bang chung phang => giu cum + stop. */
        public final List<String> flatPending = new ArrayList<>();
        /** [2e MAJ-3] stop c3s- "mo coi" nhung GIU vi vi the con / doc loi (OwnStopGuard). */
        public final List<String> orphanKept = new ArrayList<>();
        public boolean ok = true;
        public String error = "";

        @Override
        public String toString() {
            return "ok=" + ok + (error.isEmpty() ? "" : " err=" + error) + " closedWhileDown=" + closedWhileDown + " overridden="
                    + overridden + " stopsDropped=" + stopsDropped + " pendingPromoted=" + pendingPromoted + " orphanCancelled="
                    + orphanCancelled + " foreignStops=" + foreignStops + " unknownPositions=" + unknownPositions
                    + " flatPending=" + flatPending + " orphanKept=" + orphanKept;
        }
    }

    private final ExchangeGateway gw;
    private final LiveBookC3 book;
    private final FillAccounting acct;
    private final Supplier<SymbolRules> rules;
    private final Consumer<String> alert;
    private final C3LiveOrderExecutor.ApiObserver api;
    private final LongSupplier clock;
    private final double equityTol;
    private final int matchToRelease;
    private final File reanchorFile;
    private final FlatConfirm flat;
    private OwnStopGuard guard;
    /** [2e] moc lan doc positionRisk gan nhat (de doc lai moi 30 s khi dang chan UNKNOWN). */
    private long lastPosCheckMs = Long.MIN_VALUE / 2;
    private long lastKeptRetryMs = Long.MIN_VALUE / 2;
    /** [2c MAJ-1] khoi tao SAN co BLOCK_STARTUP: chi go khi {@link #startup()} doc san va doi chieu XONG. */
    private final Map<String, String> blocks = new TreeMap<>();
    private final Set<String> unknownSyms = new TreeSet<>();
    private final java.util.concurrent.ConcurrentLinkedQueue<String> unknownQ = new java.util.concurrent.ConcurrentLinkedQueue<>();
    /** [2d MIN-18] vi the la: moc lan doc dau tien thay vang. */
    private final Map<String, Long> unknownGoneSince = new TreeMap<>();
    private int matchStreak;
    private double lastDiff = Double.NaN;
    private double lastBookEq = Double.NaN;
    private double lastTmb = Double.NaN;
    private long lastBlockLogMs = Long.MIN_VALUE / 2;

    public Reconciler(ExchangeGateway gw, LiveBookC3 book, FillAccounting acct, Supplier<SymbolRules> rules,
                      Consumer<String> alert, C3LiveOrderExecutor.ApiObserver api, LongSupplier clock, double equityTol,
                      int matchToRelease, File reanchorFile) {
        this(gw, book, acct, rules, alert, api, clock, equityTol, matchToRelease, reanchorFile, null);
    }

    /** [2c] {@code flat} dung chung voi C3LiveFlattener (null => tao rieng, khoang cach 5 s). */
    public Reconciler(ExchangeGateway gw, LiveBookC3 book, FillAccounting acct, Supplier<SymbolRules> rules,
                      Consumer<String> alert, C3LiveOrderExecutor.ApiObserver api, LongSupplier clock, double equityTol,
                      int matchToRelease, File reanchorFile, FlatConfirm flat) {
        this.blocks.put(BLOCK_STARTUP, "chua doi chieu khoi dong");
        this.flat = flat != null ? flat
                : new FlatConfirm(gw, api, alert, FlatConfirm.DEFAULT_MIN_GAP_MS, FlatConfirm.DEFAULT_MIN_READS);
        this.gw = gw;
        this.book = book;
        this.acct = acct;
        this.rules = rules;
        this.alert = alert == null ? m -> { } : alert;
        this.api = api == null ? (a, ok) -> { } : api;
        this.clock = clock == null ? System::currentTimeMillis : clock;
        this.equityTol = equityTol > 0d ? equityTol : DEFAULT_EQUITY_TOL;
        this.matchToRelease = Math.max(1, matchToRelease);
        this.reanchorFile = reanchorFile;
        this.guard = new OwnStopGuard(gw, book, this.api, this.alert, () -> this::onUnknownPosition, this.clock);
    }

    /** [2e MAJ-3] guard huy stop c3s- dung chung (runtime); mac dinh guard rieng (unknown -> chinh Reconciler nay). */
    public synchronized void setStopGuard(OwnStopGuard g) {
        if (g != null) this.guard = g;
    }

    public synchronized OwnStopGuard stopGuard() {
        return guard;
    }

    // ------------------------------------------------------------------ cong vao lenh
    /** Khong co ly do chan (vi the la / lech equity / reconcile khoi dong chua xong). */
    public synchronized boolean allowsEntry(String symbol) {
        drainUnknown();
        if (blocks.isEmpty() && (symbol == null || !flat.isPending(symbol))) return true;
        long now = clock.getAsLong();
        if (now - lastBlockLogMs > 600_000L) {
            lastBlockLogMs = now;
            LOG.warn("[C3-LIVE-RECON] CHAN vao lenh ({}): {}{}", symbol, blocks,
                    blocks.isEmpty() ? " (symbol dang cho xac nhan phang)" : "");
        }
        return false;
    }

    public synchronized Map<String, String> blocks() {
        drainUnknown();
        return new LinkedHashMap<>(blocks);
    }

    /**
     * Vi the khac 0 khong thuoc so (tu C7 / OwnStopGuard / luot reconcile). [2e] KHONG lay khoa Reconciler (tranh dao thu tu
     * khoa voi FillAccounting): xep hang, ap dung o lan goi dong bo ke tiep (allowsEntry/blocks/checkPositions... luon xa
     * hang truoc) => chan vao lenh co hieu luc ngay o cong vao lenh.
     */
    public void onUnknownPosition(String symbol) {
        if (symbol == null) return;
        unknownQ.add(symbol);
        if (Thread.holdsLock(this)) drainUnknown();
    }

    private void drainUnknown() {
        String s;
        while ((s = unknownQ.poll()) != null) markUnknown(s);
    }

    private void markUnknown(String symbol) {
        if (unknownSyms.add(symbol)) {
            String m = "[C3-LIVE-RECON] vi the LA tren tai khoan c3_live: " + symbol
                    + " (khong co trong so) => CHAN mo moi, KHONG tu dong; owner kiem tra/dong tay";
            LOG.error("{}", m);
            alert.accept(m);
        }
        blocks.put(BLOCK_UNKNOWN, String.join(",", unknownSyms));
    }

    // ------------------------------------------------------------------ khoi dong
    /** Luot doi chieu luc khoi dong (sau khi executor giai quyet leg treo). Loi doc san => CHAN mo moi toi luot sau. */
    public synchronized Report startup() {
        long now = clock.getAsLong();
        drainUnknown();
        lastPosCheckMs = now;
        Report r = new Report();
        Map<String, PositionInfo> pos;
        List<OrderInfo> stops;
        // chup so TRUOC khi doc san: cum xac nhan SAU moc chup van "con leg treo" trong ban chup => bo qua (khong dong nham)
        List<LiveBookC3.ClusterView> snap = book.clusters();
        try {
            pos = positionsBySymbol();
            stops = gw.openStops(null);
            api.onApiResult("openStops", true);
        } catch (RuntimeException e) {
            api.onApiResult("openStops", false);
            r.ok = false;
            r.error = e.toString();
            blocks.put(BLOCK_STARTUP, "khong doc duoc san: " + e.getClass().getSimpleName());
            LOG.error("[C3-LIVE-RECON] khoi dong: khong doc duoc san ({}) => CHAN mo moi toi khi doi chieu duoc", e.toString());
            return r;
        }
        Map<String, OrderInfo> stopByCid = new HashMap<>();
        for (OrderInfo s : stops) if (s.getClientOrderId() != null) stopByCid.put(s.getClientOrderId(), s);
        reconcileClusters(snap, pos, stopByCid, r, now, true);
        // stop mo coi
        Set<String> refd = book.referencedStopCids();
        // [2c MIN-6] stop c3s- cao nhat cua cum DA arm ma so khong co stop (vd so khong ghi duoc luc dat) => NHAN lai
        // (san la nguon su that), con lai moi huy
        List<OrderInfo> sorted = new ArrayList<>(stops);
        sorted.sort((a, b) -> {
            BigDecimal pa = a.getStopPrice() == null ? BigDecimal.ZERO : a.getStopPrice();
            BigDecimal pb = b.getStopPrice() == null ? BigDecimal.ZERO : b.getStopPrice();
            return pb.compareTo(pa);
        });
        for (OrderInfo s : sorted) {
            String cid = s.getClientOrderId();
            if (cid == null || refd.contains(cid)) continue;
            if (cid.startsWith(C3LiveCids.STOP_PREFIX)) {
                Optional<LiveBookC3.ClusterView> cv = book.cluster(s.getSymbol());
                if (cv.isPresent() && cv.get().trailArmed() && cv.get().stopClientAlgoId == null
                        && cv.get().pendingStopCid == null && s.getStopPrice() != null && s.getStopPrice().signum() > 0
                        && !r.flatPending.contains(s.getSymbol())) {
                    book.setPendingStop(s.getSymbol(), cid, s.getStopPrice().doubleValue(), !s.isClosePosition(), now);
                    book.promotePendingStop(s.getSymbol(), now);
                    r.pendingPromoted.add(s.getSymbol() + "/" + cid + "(nhan lai)");
                    continue;
                }
                // [2e MAJ-3] chi huy khi positionRisk + account deu phang; con vi the / doc loi => GIU + UNKNOWN + Telegram
                OwnStopGuard.Result gr = guard.cancelOwnStopGuarded(s.getSymbol(), cid, "stop mo coi luc khoi dong");
                if (gr == OwnStopGuard.Result.CANCELLED || gr == OwnStopGuard.Result.GONE) {
                    r.orphanCancelled.add(s.getSymbol() + "/" + cid);
                } else {
                    r.orphanKept.add(s.getSymbol() + "/" + cid + ":" + gr);
                }
            } else {
                r.foreignStops.add(s.getSymbol() + "/" + cid);
            }
        }
        unknownCheck(pos, r);
        flat.retainOnly(book.ownedSymbols());
        blocks.remove(BLOCK_STARTUP);
        String m = "[C3-LIVE-RECON] khoi dong: " + r;
        if (!r.closedWhileDown.isEmpty() || !r.overridden.isEmpty() || !r.unknownPositions.isEmpty()
                || !r.foreignStops.isEmpty() || !r.flatPending.isEmpty() || !r.orphanKept.isEmpty()) {
            LOG.warn("{}", m);
            alert.accept(m);
        } else {
            LOG.info("{}", m);
        }
        return r;
    }

    private void reconcileClusters(List<LiveBookC3.ClusterView> snap, Map<String, PositionInfo> pos,
                                   Map<String, OrderInfo> stopByCid, Report r, long now, boolean startup) {
        for (LiveBookC3.ClusterView c : snap) {
            String sym = c.symbol;
            if (c.hasUnresolved) continue;   // executor tra san leg treo truoc
            PositionInfo p = pos.get(sym);
            BigDecimal ex = p == null || p.getPositionAmt() == null ? BigDecimal.ZERO : p.getPositionAmt();
            if (ex.signum() <= 0) {
                if (c.confirmedQty.signum() > 0) {
                    // [2c MAJ-2] vang/0 trong positionRisk CHUA phai bang chung phang: can stop/lenh dong cua bot da khop
                    // het, hoac 2 lan doc cach >= 5 s + 0 lenh mo (FlatConfirm). Chua du => GIU cum + stop, thu lai.
                    OrderStatus st = activeStopStatus(c);
                    boolean stopFired = st == OrderStatus.TRIGGERED || st == OrderStatus.FINISHED || st == OrderStatus.FILLED
                            || st == OrderStatus.TRIGGERING;
                    boolean positive = st == OrderStatus.FINISHED || st == OrderStatus.FILLED || closeOrderFilled(c);
                    String who = startup ? "reconcile khoi dong" : "reconcile";
                    if (!positive && !flat.observeFlat(sym, now, who)) {
                        r.flatPending.add(sym);
                        continue;
                    }
                    flat.clear(sym);
                    String reason = stopFired ? FillAccounting.REASON_TRAILING
                            : (c.closeReason != null ? c.closeReason : FillAccounting.REASON_EXTERNAL);
                    acct.closedOnExchange(sym, reason, now);
                    r.closedWhileDown.add(sym + ":" + reason);
                }
                continue;
            }
            flat.clear(sym);
            if (!startup) continue;
            // san thang qty/gia
            double ep = p.getEntryPrice() == null ? 0d : p.getEntryPrice().doubleValue();
            boolean qtyDiff = ex.subtract(c.confirmedQty).abs().compareTo(ex.abs().multiply(REL_QTY_TOL)) > 0;
            boolean pxDiff = ep > 0d && Math.abs(ep / c.avgPrice - 1d) > 1e-6;
            if (qtyDiff || pxDiff) {
                book.overrideFromExchange(sym, ex, ep > 0d ? ep : c.avgPrice, now);
                r.overridden.add(sym + " qty " + c.confirmedQty.toPlainString() + "->" + ex.toPlainString() + " avg "
                        + c.avgPrice + "->" + ep);
            }
            // stop pending / active
            if (c.pendingStopCid != null) {
                if (stopByCid.containsKey(c.pendingStopCid)) {
                    String old = book.promotePendingStop(sym, now);
                    r.pendingPromoted.add(sym + "/" + c.pendingStopCid);
                    if (old != null && !stopByCid.containsKey(old)) book.removeOrphanStop(sym, old, now);
                } else {
                    book.clearPendingStop(sym, now);
                }
            }
            Optional<LiveBookC3.ClusterView> cur = book.cluster(sym);
            if (cur.isPresent() && cur.get().stopClientAlgoId != null && !stopByCid.containsKey(cur.get().stopClientAlgoId)) {
                book.retireActiveStop(sym, now);
                book.removeOrphanStop(sym, cur.get().stopClientAlgoId, now);
                r.stopsDropped.add(sym + "/" + cur.get().stopClientAlgoId);
            }
            if (cur.isPresent()) {
                for (String oc : cur.get().orphanStops) {
                    if (!stopByCid.containsKey(oc)) book.removeOrphanStop(sym, oc, now);   // da het tren san
                }
            }
        }
    }

    /** Trang thai stop active cua cum tren san (truy van theo clientAlgoId); null = khong co / khong doc duoc. */
    private OrderStatus activeStopStatus(LiveBookC3.ClusterView c) {
        String cid = c.stopClientAlgoId;
        if (cid == null) return null;
        try {
            Optional<OrderInfo> q = gw.queryStop(c.symbol, cid);
            api.onApiResult("queryStop", true);
            return q.isPresent() ? q.get().getStatus() : null;
        } catch (GatewayException e) {
            api.onApiResult("queryStop", e.getKind() == ErrorKind.UNKNOWN_ORDER);
            return null;
        } catch (RuntimeException e) {
            api.onApiResult("queryStop", false);
            return null;
        }
    }

    /** [2c MAJ-2] bang chung (ii): lenh dong cua bot (closeCid) FILLED va executedQty >= qty xac nhan trong so. */
    private boolean closeOrderFilled(LiveBookC3.ClusterView c) {
        if (c.closeCid == null) return false;
        try {
            Optional<OrderInfo> q = gw.queryOrder(c.symbol, c.closeCid);
            api.onApiResult("queryOrder", true);
            if (!q.isPresent() || q.get().getStatus() != OrderStatus.FILLED) return false;
            BigDecimal exq = q.get().getExecutedQty();
            return exq != null && exq.compareTo(c.confirmedQty) >= 0;
        } catch (GatewayException e) {
            api.onApiResult("queryOrder", e.getKind() == ErrorKind.UNKNOWN_ORDER);
            return false;
        } catch (RuntimeException e) {
            api.onApiResult("queryOrder", false);
            return false;
        }
    }

    /**
     * [2c MAJ-2] Goi moi nhip ops (5 s): co symbol dang "nghi phang" da du khoang cach => doc lai positionRisk de xac nhan
     * (hoac xoa nghi ngo neu vi the con). null = khong co gi phai lam.
     */
    public synchronized Report confirmPendingFlat() {
        drainUnknown();
        long t = clock.getAsLong();
        boolean unknownDue = false;
        for (long g : unknownGoneSince.values()) if (t - g >= flat.minGapMs()) unknownDue = true;
        // [2e] dang chan UNKNOWN (vd guard GIU stop vi positionRisk tre sau khi dong) => doc lai moi 30 s de tu go som
        if (!unknownSyms.isEmpty() && t - lastPosCheckMs >= flat.minGapMs()) unknownDue = true;
        if (!flat.anyDue(t) && !unknownDue) return null;
        return checkPositions();
    }

    /** Symbol dang cho xac nhan phang (giu cum + stop). */
    public Set<String> flatPending() {
        return flat.pending();
    }

    private void unknownCheck(Map<String, PositionInfo> pos, Report r) {
        Set<String> owned = book.ownedSymbols();
        Set<String> now = new TreeSet<>();
        for (Map.Entry<String, PositionInfo> e : pos.entrySet()) {
            BigDecimal amt = e.getValue().getPositionAmt();
            if (amt == null || amt.signum() == 0) continue;
            if (!owned.contains(e.getKey()) || amt.signum() < 0) now.add(e.getKey());
        }
        r.unknownPositions.addAll(now);
        // [2d MIN-18] vi the la cu chi duoc coi la "het" khi >= 2 lan doc nhat quan cach >= minGap (30 s) deu vang
        // (1 lan doc rong/glitch KHONG go chan)
        long t = clock.getAsLong();
        for (String s : new ArrayList<>(unknownSyms)) {
            if (now.contains(s)) {
                unknownGoneSince.remove(s);
                continue;
            }
            if (guard.hasKept(s)) {
                // [2e MAJ-3] con stop c3s- bi GIU cho symbol nay (chua huy duoc) => CHUA go chan
                unknownGoneSince.remove(s);
                continue;
            }
            Long g = unknownGoneSince.get(s);
            if (g == null) {
                unknownGoneSince.put(s, t);
                LOG.warn("[C3-LIVE-RECON] vi the la {} vang o lan doc nay => CHUA go chan (can lan doc xac nhan sau >= {} ms)",
                        s, flat.minGapMs());
            } else if (t - g >= flat.minGapMs()) {
                unknownSyms.remove(s);
                unknownGoneSince.remove(s);
            }
        }
        unknownGoneSince.keySet().retainAll(unknownSyms);
        for (String s : now) onUnknownPosition(s);
        if (!unknownSyms.isEmpty()) blocks.put(BLOCK_UNKNOWN, String.join(",", unknownSyms));
        if (unknownSyms.isEmpty() && blocks.remove(BLOCK_UNKNOWN) != null) {
            String m = "[C3-LIVE-RECON] het vi the la => GO chan mo moi (UNKNOWN_POSITION)";
            LOG.warn("{}", m);
            alert.accept(m);
        }
    }

    // ------------------------------------------------------------------ fallback (mat stream)
    /** Khi mat user stream: cum co qty ma san = 0 => cap nhat so; vi the la => chan. */
    public synchronized Report checkPositions() {
        long now = clock.getAsLong();
        lastPosCheckMs = now;
        drainUnknown();
        Report r = new Report();
        try {
            List<LiveBookC3.ClusterView> snap = book.clusters();   // chup TRUOC khi doc san
            Map<String, PositionInfo> pos = positionsBySymbol();
            reconcileClusters(snap, pos, Collections.<String, OrderInfo>emptyMap(), r, now, false);
            retryKeptStops(r, now);
            unknownCheck(pos, r);
            flat.retainOnly(book.ownedSymbols());
        } catch (RuntimeException e) {
            r.ok = false;
            r.error = e.toString();
        }
        if (!r.closedWhileDown.isEmpty()) LOG.warn("[C3-LIVE-RECON] fallback REST: {}", r);
        return r;
    }

    // ------------------------------------------------------------------ hang gio
    /** Doi chieu equity + vi the + stop mo coi. */
    public synchronized Report hourly() {
        long now = clock.getAsLong();
        Report r = checkPositions();
        if (!r.ok) {
            LOG.warn("[C3-LIVE-RECON] hang gio: khong doc duoc positions ({}) => bo luot", r.error);
            return r;
        }
        sweepOrphanStops(r);
        try {
            AccountSnapshot a = gw.account();
            api.onApiResult("account", true);
            Map<String, PositionInfo> pos = positionsBySymbol();
            double upl = unrealizedOnBook(pos);
            double tmb = a.getTotalMarginBalance() == null ? Double.NaN : a.getTotalMarginBalance().doubleValue();
            if (!(tmb > 0d)) {
                r.ok = false;
                r.error = "totalMarginBalance=" + tmb;
                return r;
            }
            boolean reReq = reanchorRequested(now);
            LiveBookC3.AccountView av = book.account();
            boolean bookFlat = book.openCount() == 0 && book.unresolvedLegs().isEmpty();
            if (!av.anchored() || reReq || bookFlat) {
                book.anchor(tmb - upl, now);
                String m = "[C3-LIVE-RECON] dat moc doi chieu equity = " + fmt(tmb - upl) + " (tmb=" + fmt(tmb) + " upl=" + fmt(upl)
                        + (reReq ? ", yeu cau owner" : (bookFlat ? ", so trong" : ", lan dau")) + ")";
                if (reReq || !av.anchored()) {
                    LOG.warn("{}", m);
                } else {
                    LOG.info("{}", m);
                }
                if (reReq) alert.accept(m);
                if (blocks.containsKey(BLOCK_EQUITY) && (reReq || bookFlat)) {
                    blocks.remove(BLOCK_EQUITY);
                    alert.accept("[C3-LIVE-RECON] GO chan mo moi (EQUITY_MISMATCH) sau khi dat lai moc");
                }
                matchStreak = 0;
                lastDiff = 0d;
                return r;
            }
            double bookEq = av.bookEquityExUnrealized() + upl;
            double diff = Math.abs(bookEq - tmb) / tmb;
            lastDiff = diff;
            lastBookEq = bookEq;
            lastTmb = tmb;
            String line = "equity_so=" + fmt(bookEq) + " tmb=" + fmt(tmb) + " lech=" + String.format(Locale.ROOT, "%.4f%%", diff * 100)
                    + " (moc=" + fmt(av.anchorEquity) + " chot=" + fmt(av.realized) + " phi=" + fmt(av.commission) + " funding="
                    + fmt(av.funding) + " chuyen=" + fmt(av.transfers) + " upl_so=" + fmt(upl) + ")";
            if (diff > equityTol) {
                matchStreak = 0;
                if (!blocks.containsKey(BLOCK_EQUITY)) {
                    blocks.put(BLOCK_EQUITY, line);
                    String m = "[C3-LIVE-RECON] LECH EQUITY > " + String.format(Locale.ROOT, "%.1f%%", equityTol * 100)
                            + " => CHAN mo moi (tu go khi khop " + matchToRelease + " lan lien tiep): " + line;
                    LOG.error("{}", m);
                    alert.accept(m);
                } else {
                    blocks.put(BLOCK_EQUITY, line);
                    LOG.warn("[C3-LIVE-RECON] van lech equity: {}", line);
                }
            } else {
                matchStreak++;
                LOG.info("[C3-LIVE-RECON] HOURLY khop: {} streak={}", line, matchStreak);
                if (blocks.containsKey(BLOCK_EQUITY) && matchStreak >= matchToRelease) {
                    blocks.remove(BLOCK_EQUITY);
                    String m = "[C3-LIVE-RECON] equity khop lai " + matchStreak + " lan lien tiep => GO chan mo moi: " + line;
                    LOG.warn("{}", m);
                    alert.accept(m);
                }
            }
        } catch (RuntimeException e) {
            api.onApiResult("account", false);
            r.ok = false;
            r.error = e.toString();
            LOG.warn("[C3-LIVE-RECON] hang gio loi {}", e.toString());
        }
        return r;
    }

    /** Lai chua chot tren qty/gia SO voi markPrice san (lech qty/gia so se lo ra o day). */
    private double unrealizedOnBook(Map<String, PositionInfo> pos) {
        double upl = 0d;
        for (LiveBookC3.ClusterView c : book.clusters()) {
            if (c.confirmedQty.signum() <= 0) continue;
            PositionInfo p = pos.get(c.symbol);
            if (p == null || p.getMarkPrice() == null || p.getMarkPrice().signum() <= 0) continue;
            upl += c.confirmedQty.doubleValue() * (p.getMarkPrice().doubleValue() - c.avgPrice);
        }
        return upl;
    }

    /**
     * [2e MAJ-3] Thu huy lai (qua guard) cac stop c3s- dang bi GIU khong con thuoc so — vd positionRisk tre sau khi stream bao
     * dong: vai giay sau ca 2 nguon phang => huy, symbol moi duoc go UNKNOWN. Thua toi thieu minGap (30 s).
     */
    private void retryKeptStops(Report r, long now) {
        Map<String, String> k = guard.keptStops();
        if (k.isEmpty() || now - lastKeptRetryMs < flat.minGapMs()) return;
        lastKeptRetryMs = now;
        Set<String> refd = book.referencedStopCids();
        for (Map.Entry<String, String> e : k.entrySet()) {
            if (refd.contains(e.getKey())) continue;   // so dang tham chieu (trailing tu xu ly)
            OwnStopGuard.Result gr = guard.cancelOwnStopGuarded(e.getValue(), e.getKey(), "thu lai stop dang giu");
            if (gr == OwnStopGuard.Result.CANCELLED || gr == OwnStopGuard.Result.GONE) {
                r.orphanCancelled.add(e.getValue() + "/" + e.getKey());
            } else {
                r.orphanKept.add(e.getValue() + "/" + e.getKey() + ":" + gr);
            }
        }
        if (!r.orphanCancelled.isEmpty()) LOG.warn("[C3-LIVE-RECON] huy stop dang giu (nay da phang): {}", r.orphanCancelled);
    }

    private void sweepOrphanStops(Report r) {
        try {
            List<OrderInfo> stops = gw.openStops(null);
            api.onApiResult("openStops", true);
            Set<String> refd = book.referencedStopCids();
            for (OrderInfo s : stops) {
                String cid = s.getClientOrderId();
                if (cid == null || refd.contains(cid) || !cid.startsWith(C3LiveCids.STOP_PREFIX)) continue;
                if (book.isHolding(s.getSymbol())) {
                    Optional<LiveBookC3.ClusterView> c = book.cluster(s.getSymbol());
                    if (c.isPresent() && c.get().pendingStopCid != null) continue;   // dang dat do: de nhip sau
                }
                OwnStopGuard.Result gr = guard.cancelOwnStopGuarded(s.getSymbol(), cid, "stop mo coi (quet hang gio)");
                if (gr == OwnStopGuard.Result.CANCELLED || gr == OwnStopGuard.Result.GONE) {
                    r.orphanCancelled.add(s.getSymbol() + "/" + cid);
                } else {
                    r.orphanKept.add(s.getSymbol() + "/" + cid + ":" + gr);
                }
            }
        } catch (RuntimeException e) {
            api.onApiResult("openStops", false);
        }
        if (!r.orphanKept.isEmpty()) LOG.warn("[C3-LIVE-RECON] GIU stop c3s- (vi the con / doc loi): {}", r.orphanKept);
        if (!r.orphanCancelled.isEmpty()) LOG.warn("[C3-LIVE-RECON] huy stop mo coi: {}", r.orphanCancelled);
    }

    private boolean reanchorRequested(long now) {
        if (reanchorFile == null || !reanchorFile.exists()) return false;
        try {
            Files.move(reanchorFile.toPath(), new File(reanchorFile.getPath() + ".done_" + now).toPath(),
                    StandardCopyOption.REPLACE_EXISTING);
        } catch (Exception e) {
            try {
                Files.deleteIfExists(reanchorFile.toPath());
            } catch (Exception ignore) {
                // lan sau ap dung lai
            }
        }
        return true;
    }

    private Map<String, PositionInfo> positionsBySymbol() {
        List<PositionInfo> ps;
        try {
            ps = gw.positions();
            api.onApiResult("positions", true);
        } catch (RuntimeException e) {
            api.onApiResult("positions", false);
            throw e;
        }
        Map<String, PositionInfo> m = new HashMap<>();
        for (PositionInfo p : ps) {
            if (p.getSymbol() == null || p.getPositionAmt() == null) continue;
            PositionInfo prev = m.get(p.getSymbol());
            if (prev == null || prev.getPositionAmt().signum() == 0) m.put(p.getSymbol(), p);
        }
        return m;
    }

    /**
     * [2e] Lenh owner go "cum ma" ({@code ops/c3live/c3live_ghost_clear.sh SYMBOL} => file yeu cau, runtime goi ham nay):
     * CHI khi CA positionRisk LAN account().positions bao symbol phang (doc loi / account khong co mang => TU CHOI) thi huy
     * moi stop c3s- con mo cua symbol (qua OwnStopGuard) roi xoa cum khoi so (ly do GHOST_CLEAR_OWNER). @return dong ket qua
     * "OK ..." hoac "REFUSED ...".
     */
    public synchronized String ghostClear(String sym) {
        long now = clock.getAsLong();
        drainUnknown();
        if (sym == null || !sym.matches("[A-Z0-9]{2,30}")) return "REFUSED symbol khong hop le: " + sym;
        if (!book.isHolding(sym)) return "REFUSED " + sym + ": so KHONG giu cum symbol nay";
        BigDecimal pr = BigDecimal.ZERO;
        BigDecimal ac = BigDecimal.ZERO;
        try {
            for (PositionInfo p : gw.positions()) {
                if (sym.equals(p.getSymbol()) && p.getPositionAmt() != null) pr = pr.add(p.getPositionAmt().abs());
            }
            api.onApiResult("positions", true);
            AccountSnapshot a = gw.account();
            api.onApiResult("account", true);
            if (a == null || a.getPositions() == null) return "REFUSED " + sym + ": account() khong co mang positions";
            for (PositionInfo p : a.getPositions()) {
                if (sym.equals(p.getSymbol()) && p.getPositionAmt() != null) ac = ac.add(p.getPositionAmt().abs());
            }
        } catch (RuntimeException e) {
            return "REFUSED " + sym + ": doc san loi (" + e.getClass().getSimpleName() + ")";
        }
        if (pr.signum() != 0 || ac.signum() != 0) {
            return "REFUSED " + sym + ": vi the != 0 (positionRisk=" + pr.toPlainString() + " account=" + ac.toPlainString()
                    + ") — KHONG phai cum ma; giu nguyen";
        }
        List<String> done = new ArrayList<>();
        List<String> kept = new ArrayList<>();
        try {
            for (OrderInfo s : gw.openStops(sym)) {
                if (!OwnStopGuard.isOwn(s.getClientOrderId())) continue;
                OwnStopGuard.Result gr = guard.cancelOwnStopGuarded(sym, s.getClientOrderId(), "owner go cum ma");
                (gr == OwnStopGuard.Result.CANCELLED || gr == OwnStopGuard.Result.GONE ? done : kept).add(s.getClientOrderId());
            }
            api.onApiResult("openStops", true);
        } catch (RuntimeException e) {
            api.onApiResult("openStops", false);
            return "REFUSED " + sym + ": khong doc duoc stop mo (" + e.getClass().getSimpleName() + ")";
        }
        if (!kept.isEmpty()) return "REFUSED " + sym + ": khong huy duoc stop " + kept + " (giu cum)";
        book.removeCluster(sym, "GHOST_CLEAR_OWNER", now);
        flat.clear(sym);
        String m = "[C3-LIVE-RECON] owner GO cum ma " + sym + ": positionRisk + account = 0, huy stop " + done + ", xoa cum";
        LOG.warn("{}", m);
        alert.accept(m);
        return "OK " + sym + ": huy stop " + done + ", xoa cum khoi so";
    }

    public synchronized double lastEquityDiff() {
        return lastDiff;
    }

    public synchronized String status() {
        return "blocks=" + blocks + " lastDiff=" + (Double.isNaN(lastDiff) ? "NA" : String.format(Locale.ROOT, "%.5f", lastDiff))
                + " bookEq=" + fmt(lastBookEq) + " tmb=" + fmt(lastTmb) + " streak=" + matchStreak;
    }

    private static String fmt(double v) {
        return Double.isNaN(v) ? "NA" : String.format(Locale.ROOT, "%.2f", v);
    }
}
