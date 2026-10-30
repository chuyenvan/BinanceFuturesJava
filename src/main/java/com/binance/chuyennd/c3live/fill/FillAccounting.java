package com.binance.chuyennd.c3live.fill;

import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.exec.C3LiveCids;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.exec.FillPriceResolver;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.recon.OwnStopGuard;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Consumer;
import java.util.function.LongSupplier;

/**
 * [V12 C7] Ke toan fill THAT vao {@link LiveBookC3} tu user-data stream (hoac adapter dry phat su kien cung dang).
 * <ul>
 *   <li>Leg MUA {@code c3-...}: FILLED (hoac ket thuc voi z&gt;0) => {@link LiveBookC3#confirm} (qty/avgPrice/orderId that);
 *       chi lan xac nhan DAU TIEN (stream hoac executor REST) moi goi {@code FillObserver.onFill} (C2 co dau, ref = close nen
 *       1m quyet dinh) => khong dem trung. Ket thuc z=0 => huy giu cho.</li>
 *   <li>Moi fill (x=TRADE): phi {@code n} (quy USD neu tai san on dinh USDT/USDC/BFUSD/FDUSD; khac => WARN, khong cong)
 *       + realizedPnl {@code rp} => so (cum + tong ke tu moc doi chieu equity).</li>
 *   <li>Fill BAN cua cum dang giu: cong qty/gia dong; ly do suy tu clientOrderId: {@code c3x-} = lenh dong cua bot,
 *       {@code c3s-}/stop dang dat/ot=STOP_MARKET = TRAILING_STOP, {@code autoclose-} = LIQUIDATION, {@code adl_autoclose}
 *       = ADL, {@code settlement_autoclose} = DELIST_SETTLE, con lai = EXTERNAL.</li>
 *   <li>{@code ACCOUNT_UPDATE}: vi the cua cum dang giu ve 0 => {@link #closedOnExchange} (huy stop con lai, xoa cum,
 *       Telegram neu khong phai stop/lenh dong cua bot); vi the khac 0 KHONG co trong so => bao Reconciler (chan mo moi);
 *       FUNDING_FEE => funding; DEPOSIT/WITHDRAW/... => chuyen tien (doi chieu equity).</li>
 * </ul>
 * Thread-safe (synchronized). Khong bao gio nem ra ngoai.
 */
public final class FillAccounting {

    private static final Logger LOG = LoggerFactory.getLogger(FillAccounting.class);
    public static final String REASON_TRAILING = "TRAILING_STOP";
    public static final String REASON_LIQ = "LIQUIDATION";
    public static final String REASON_ADL = "ADL";
    public static final String REASON_SETTLE = "DELIST_SETTLE";
    public static final String REASON_EXTERNAL = "EXTERNAL";
    public static final String REASON_BOT_CLOSE = "BOT_CLOSE";
    static final Set<String> STABLE = new HashSet<>(Arrays.asList("USDT", "USDC", "BFUSD", "FDUSD"));
    static final BigDecimal QTY_EPS = new BigDecimal("1e-12");

    /** Cum vua dong (nhat ky X14 onClosed — noi o runtime qua TrailingStopManager). */
    public interface ClosedHook {
        void onClosed(String symbol, long tsFirstLeg, String reason, long now);
    }

    private final LiveBookC3 book;
    private final ExchangeGateway gw;
    private final OrderAuditLog audit;
    private final C3LiveOrderExecutor.FillObserver fill;
    private final Consumer<String> alert;
    private final C3LiveOrderExecutor.ApiObserver api;
    private final LongSupplier clock;
    private final ClosedHook closedHook;
    private volatile Consumer<String> unknownPosition = s -> { };
    private volatile OwnStopGuard stopGuard;
    private final Map<String, String> lastExitReason = new ConcurrentHashMap<>();
    private final Set<String> warnedAssets = ConcurrentHashMap.newKeySet();
    private volatile FillPriceResolver prices;
    private final AtomicLong nOrder = new AtomicLong();
    private final AtomicLong nConfirm = new AtomicLong();
    private final AtomicLong nExitFill = new AtomicLong();
    private final AtomicLong nClosedExchange = new AtomicLong();
    private final AtomicLong nAccount = new AtomicLong();

    public FillAccounting(LiveBookC3 book, ExchangeGateway gw, OrderAuditLog audit, C3LiveOrderExecutor.FillObserver fill,
                          Consumer<String> alert, C3LiveOrderExecutor.ApiObserver api, LongSupplier clock,
                          ClosedHook closedHook) {
        this.book = book;
        this.gw = gw;
        this.audit = audit;
        this.fill = fill == null ? (s, b, f, r) -> { } : fill;
        this.alert = alert == null ? m -> { } : alert;
        this.api = api == null ? (a, ok) -> { } : api;
        this.clock = clock == null ? System::currentTimeMillis : clock;
        this.closedHook = closedHook == null ? (s, t, r, n) -> { } : closedHook;
    }

    /** Noi Reconciler: vi the khac 0 khong co trong so. */
    public void setUnknownPositionSink(Consumer<String> sink) {
        this.unknownPosition = sink == null ? s -> { } : sink;
    }

    /**
     * [3j R2] cache gia tu stream dung CHUNG voi C3LiveOrderExecutor (nguon (a) cua FillPriceResolver). Phai tro cung 1
     * object voi executor (production/canary); null = khong chia se.
     */
    public void setPriceResolver(FillPriceResolver r) {
        this.prices = r;
    }

    public void dispatch(UserStreamEvents.Event e) {
        try {
            if (e instanceof UserStreamEvents.OrderUpdate) {
                onOrderUpdate((UserStreamEvents.OrderUpdate) e);
            } else if (e instanceof UserStreamEvents.AccountUpdate) {
                onAccountUpdate((UserStreamEvents.AccountUpdate) e);
            } else if (e instanceof UserStreamEvents.AlgoUpdate) {
                onAlgoUpdate((UserStreamEvents.AlgoUpdate) e);
            }
        } catch (Throwable t) {
            LOG.error("[C3-LIVE-FILL] loi xu ly su kien {}: {}", e == null ? "-" : e.type, t.toString());
        }
    }

    public synchronized void onOrderUpdate(UserStreamEvents.OrderUpdate u) {
        long now = clock.getAsLong();
        nOrder.incrementAndGet();
        String sym = u.symbol;
        String cid = u.clientOrderId;
        FillPriceResolver pr = prices;
        if (pr != null) pr.observe(cid, u.orderId, u.avgPrice, u.lastPrice);   // [3j R2(a)] cache gia cho executor
        if (sym == null) return;
        boolean fresh = true;
        if (u.isTrade()) {
            double nt = u.lastQty == null || u.lastPrice == null ? 0d : u.lastQty.doubleValue() * u.lastPrice.doubleValue();
            double comm = commissionUsd(u.commission, u.commissionAsset, nt);
            double rp = u.realizedPnl == null ? 0d : u.realizedPnl.doubleValue();
            fresh = book.addFillCosts(sym, u.tradeId, comm, rp, now);   // [V12 R4f] chong ghi trung theo tradeId
            if (!fresh) LOG.info("[C3-LIVE-FILL] {} khop t={} DA GHI (khoi phuc REST toi truoc) => bo qua ghi lai", sym, u.tradeId);
            audit.record(OrderAuditLog.Entry.of(now).clientOrderId(cid).orderId(u.orderId).symbol(sym).side(u.side)
                    .type(u.origType == null ? u.orderType : u.origType).qty(u.lastQty).price(u.lastPrice)
                    .status("FILL").latencyMs(Math.max(0L, now - u.tradeTimeMs)).errCode("")
                    .reason("stream X=" + u.status + " z=" + plain(u.cumQty) + " n=" + plain(u.commission) + " "
                            + (u.commissionAsset == null ? "" : u.commissionAsset) + " rp=" + plain(u.realizedPnl)));
        }
        if (u.isBuy()) {
            onBuy(u, now);
        } else {
            onSell(u, now, fresh);
        }
    }

    private void onBuy(UserStreamEvents.OrderUpdate u, long now) {
        String cid = u.clientOrderId;
        Optional<LiveBookC3.LegView> lv = cid == null ? Optional.<LiveBookC3.LegView>empty() : book.leg(cid);
        if (!lv.isPresent()) {
            if (cid != null && cid.startsWith(C3LiveCids.ENTRY_PREFIX)) return;   // leg da ket thuc / da xoa: bo qua
            if (u.isTrade()) {
                String m = "[C3-LIVE] FILL MUA KHONG thuoc so c3_live: " + u.symbol + " cid=" + cid + " qty=" + plain(u.lastQty)
                        + " => Reconciler se chan mo moi neu con vi the la";
                LOG.warn("{}", m);
                alert.accept(m);
            }
            return;
        }
        BigDecimal z = u.cumQty == null ? BigDecimal.ZERO : u.cumQty;
        if ("FILLED".equals(u.status) || (u.isFinal() && z.signum() > 0)) {
            // [3j R1/R2] gia that: ap (binh quan) truoc, roi L (gia khop tung phan). KHONG BAO GIO coi thieu gia la "khong khop".
            double px = u.avgPrice != null && u.avgPrice.signum() > 0 ? u.avgPrice.doubleValue()
                    : (u.lastPrice != null && u.lastPrice.signum() > 0 ? u.lastPrice.doubleValue() : 0d);
            Optional<LiveBookC3.LegView> cur = book.leg(cid);
            if (cur.isPresent() && cur.get().state == LiveBookC3.LegState.CONFIRMED && cur.get().pxProvisional) {
                // da ghi qty voi gia TAM (ACK thieu avgPrice) => hieu chinh bang gia that cua stream
                if (px > 0d && book.correctPrice(cid, px, now)) {
                    LOG.info("[C3-LIVE-FILL] {} {} PX_CORRECTED {} -> {} (stream)", u.symbol, cid, cur.get().avgPx, px);
                }
                return;
            }
            if (z.signum() <= 0) {
                LOG.warn("[C3-LIVE-FILL] {} {} {} nhung z=0 => giu leg cho executor tra san (khong huy)", u.symbol, cid, u.status);
                return;
            }
            if (px <= 0d) {
                // [3j R1] co qty ma chua co gia: executor dang giai gia (stream/query/userTrades) => KHONG huy giu cho
                LOG.warn("[C3-LIVE-FILL] {} {} FILLED z={} nhung thieu ca ap/L => giu leg unresolved, cho executor giai gia",
                        u.symbol, cid, z.toPlainString());
                return;
            }
            if (book.confirm(cid, z, px, u.orderId, now)) {
                nConfirm.incrementAndGet();
                LOG.info("[C3-LIVE-FILL] xac nhan qua stream {} {} qty={} avg={} ref={}", u.symbol, cid, z.toPlainString(), px,
                        lv.get().refPx);
                fill.onFill(u.symbol, true, px, lv.get().refPx);
            }
        } else if (u.isFinal()) {
            // [3j R4] chi huy khi san noi CHAC CHAN khong khop
            if ("CANCELED".equals(u.status) || "EXPIRED".equals(u.status) || "REJECTED".equals(u.status)
                    || "EXPIRED_IN_MATCH".equals(u.status)) {
                if (book.cancel(cid, "stream_" + u.status, now)) {
                    LOG.warn("[C3-LIVE-FILL] leg {} {} ket thuc {} khong khop => huy giu cho", u.symbol, cid, u.status);
                }
            } else {
                LOG.warn("[C3-LIVE-FILL] leg {} {} trang thai {} khong ket luan => giu leg", u.symbol, cid, u.status);
            }
        } else if (u.orderId > 0) {
            book.noteOpen(cid, u.orderId, now);
        }
    }

    private void onSell(UserStreamEvents.OrderUpdate u, long now, boolean fresh) {
        String sym = u.symbol;
        Optional<LiveBookC3.ClusterView> c = book.cluster(sym);
        if (!c.isPresent()) return;
        String reason = exitReason(u.clientOrderId, u.origType, c.get().stopClientAlgoId);
        if (REASON_BOT_CLOSE.equals(reason) && c.get().closeReason != null) reason = c.get().closeReason;
        lastExitReason.put(sym, reason);
        if (fresh && u.isTrade() && u.lastQty != null && u.lastQty.signum() > 0) {
            nExitFill.incrementAndGet();
            double px = u.lastPrice == null ? 0d : u.lastPrice.doubleValue();
            book.addExitFill(sym, u.lastQty, px, now);
            if (REASON_TRAILING.equals(reason) && c.get().stopPrice > 0d && px > 0d) {
                LOG.info("[C3-LIVE-FILL] {} stop khop {}@{} (stop={} truot={})", sym, plain(u.lastQty), px, c.get().stopPrice,
                        String.format(Locale.ROOT, "%.5f", 1d - px / c.get().stopPrice));
            }
        }
        if ("FILLED".equals(u.status)) {
            Optional<LiveBookC3.ClusterView> c2 = book.cluster(sym);
            if (c2.isPresent() && !c2.get().hasUnresolved
                    && c2.get().exitQty.add(QTY_EPS).compareTo(c2.get().confirmedQty) >= 0) {
                closedOnExchange(sym, reason, now);
            }
        }
    }

    public synchronized void onAccountUpdate(UserStreamEvents.AccountUpdate a) {
        long now = clock.getAsLong();
        nAccount.incrementAndGet();
        String m = a.reason == null ? "" : a.reason;
        double stableBc = 0d;
        for (UserStreamEvents.Balance b : a.balances) {
            if (b.asset == null || b.balanceChange == null || b.balanceChange.signum() == 0) continue;
            if (STABLE.contains(b.asset)) {
                stableBc += b.balanceChange.doubleValue();
            } else if (warnedAssets.add(b.asset + "|" + m)) {
                LOG.warn("[C3-LIVE-FILL] ACCOUNT_UPDATE {} doi so du tai san KHONG on dinh {} bc={} => khong quy USD (doi chieu "
                        + "equity co the lech)", m, b.asset, b.balanceChange.toPlainString());
            }
        }
        if (stableBc != 0d) {
            if ("FUNDING_FEE".equals(m)) {
                book.addFunding(stableBc, now);
            } else if (!"ORDER".equals(m)) {
                book.addTransfer(stableBc, now);
                LOG.warn("[C3-LIVE-FILL] ACCOUNT_UPDATE ly do={} doi so du on dinh {} => ghi 'chuyen tien' cho doi chieu equity",
                        m, stableBc);
            }
        }
        for (UserStreamEvents.Position p : a.positions) {
            if (p.symbol == null || p.positionAmt == null) continue;
            boolean flat = p.positionAmt.abs().compareTo(QTY_EPS) <= 0;
            Optional<LiveBookC3.ClusterView> c = book.cluster(p.symbol);
            if (c.isPresent()) {
                if (flat) {
                    if (c.get().confirmedQty.signum() > 0 && !c.get().hasUnresolved) {
                        String r = lastExitReason.getOrDefault(p.symbol, "ORDER".equals(m) ? REASON_EXTERNAL : m);
                        closedOnExchange(p.symbol, r, now);
                    }
                } else if (p.positionAmt.signum() < 0) {
                    String msg = "[C3-LIVE] vi the AM (short) " + p.symbol + " pa=" + p.positionAmt.toPlainString()
                            + " tren tai khoan c3_live — KHONG tu dong; Reconciler chan mo moi";
                    LOG.error("{}", msg);
                    alert.accept(msg);
                    unknownPosition.accept(p.symbol);
                }
            } else if (!flat) {
                unknownPosition.accept(p.symbol);
            }
        }
    }

    public synchronized void onAlgoUpdate(UserStreamEvents.AlgoUpdate a) {
        if (a.clientAlgoId == null) return;
        LOG.info("[C3-LIVE-FILL] ALGO_UPDATE {} caid={} X={} ai={}", a.symbol, a.clientAlgoId, a.status, a.actualOrderId);
        boolean terminal = "CANCELED".equals(a.status) || "EXPIRED".equals(a.status);
        Optional<LiveBookC3.ClusterView> c = a.symbol == null ? Optional.<LiveBookC3.ClusterView>empty() : book.cluster(a.symbol);
        if (terminal && c.isPresent()) {
            // [3k R1] San tu ket thuc stop (CANCELED/EXPIRED). Vi the ve 0 => binh thuong (closedOnExchange lo). CON vi the
            // (uoc luong tu so: confirmedQty - exitQty, hoac con leg chua ro) => MAT STOP: bo stop active NGAY de
            // TrailingStopManager dat lai o nhip exit ke tiep (<= 10 s), khong cho Reconciler hang gio.
            onStopTerminal(a, c.get(), terminalPosOpen(c.get()), clock.getAsLong());
        } else if (terminal && a.symbol != null) {
            LOG.info("[C3-LIVE-FILL] {} stop {} ket thuc {} nhung so khong giu cum (da dong) => bo qua", a.symbol,
                    a.clientAlgoId, a.status);
        }
        if (a.symbol != null && ("TRIGGERED".equals(a.status) || "FINISHED".equals(a.status) || "TRIGGERING".equals(a.status))) {
            if (c.isPresent() && a.clientAlgoId.equals(c.get().stopClientAlgoId)) lastExitReason.put(a.symbol, REASON_TRAILING);
        }
    }

    /** [3k R1] Vi the (theo so) con mo? confirmedQty - exitQty > 0, hoac con leg chua ro (khong du tin hieu phang). */
    private static boolean terminalPosOpen(LiveBookC3.ClusterView c) {
        BigDecimal pos = c.confirmedQty.subtract(c.exitQty == null ? BigDecimal.ZERO : c.exitQty);
        return pos.signum() > 0 || c.hasUnresolved;
    }

    /**
     * [3k R1] Stop cua cum bi san ket thuc khi vi the con: (a) stop ACTIVE => go khoi so NGAY (khong dua vao orphanStops vi
     * tren san stop da chet) de trailing dat lai; (b) stop PENDING (chua kip promote) => bo pending de dat lai. Ghi log +
     * Telegram (mat bao ve la su co, phai thay). Vi the da phang => khong lam gi (closedOnExchange huy stop con lai).
     */
    private void onStopTerminal(UserStreamEvents.AlgoUpdate a, LiveBookC3.ClusterView c, boolean posOpen, long now) {
        if (!posOpen) {
            LOG.info("[C3-LIVE-FILL] {} stop {} {} khi vi the da phang => binh thuong", a.symbol, a.clientAlgoId, a.status);
            return;
        }
        String m;
        if (a.clientAlgoId.equals(c.stopClientAlgoId)) {
            String old = book.retireActiveStop(a.symbol, now);
            if (old != null) book.removeOrphanStop(a.symbol, old, now);   // da chet tren san: guard khong huy lai
            m = "[C3-LIVE] " + a.symbol + " STOP MAT: san ket thuc " + a.clientAlgoId + " X=" + a.status
                    + " khi vi the con mo (qty so=" + c.confirmedQty.toPlainString() + " da dong=" + c.exitQty.toPlainString()
                    + ") => bo stop khoi so, trailing DAT LAI nhip ke tiep; kiem ngay neu vi the lon";
        } else if (a.clientAlgoId.equals(c.pendingStopCid)) {
            book.clearPendingStop(a.symbol, now);
            m = "[C3-LIVE] " + a.symbol + " stop PENDING " + a.clientAlgoId + " bi san ket thuc X=" + a.status
                    + " khi vi the con mo => bo pending, trailing dat lai nhip ke tiep";
        } else {
            return;
        }
        LOG.warn("{}", m);
        try {
            alert.accept(m);
        } catch (Throwable ignore) {
            // alert khong duoc lam hong ke toan fill
        }
    }

    /**
     * Vi the cua cum da phang tren san (stop khop / thanh ly / ADL / delist / lenh dong cua bot / tay): huy MOI stop con lai
     * cua symbol, xoa cum (ghi ledger), Telegram neu KHONG phai stop/lenh dong cua bot. Idempotent.
     */
    public synchronized void closedOnExchange(String sym, String reason, long now) {
        Optional<LiveBookC3.ClusterView> c = book.cluster(sym);
        if (!c.isPresent()) return;
        if (c.get().hasUnresolved) {
            LOG.warn("[C3-LIVE-FILL] {} vi the san = 0 nhung con leg mua treo => cho executor giai quyet", sym);
            return;
        }
        Set<String> cids = new HashSet<>();
        if (c.get().stopClientAlgoId != null) cids.add(c.get().stopClientAlgoId);
        if (c.get().pendingStopCid != null) cids.add(c.get().pendingStopCid);
        cids.addAll(c.get().orphanStops);
        try {
            List<OrderInfo> open = gw.openStops(sym);
            api.onApiResult("openStops", true);
            for (OrderInfo o : open) {
                String id = o.getClientOrderId();
                if (id != null && id.startsWith(C3LiveCids.STOP_PREFIX)) cids.add(id);
            }
        } catch (RuntimeException e) {
            api.onApiResult("openStops", false);
            LOG.warn("[C3-LIVE-FILL] {} khong doc duoc stop mo ({}) => Reconciler se don stop mo coi", sym, e.toString());
        }
        String r = reason == null ? REASON_EXTERNAL : reason;
        // [2e MAJ-3] xoa cum TRUOC, roi huy stop qua guard: chi huy khi positionRisk + account deu phang; con vi the / doc loi
        // => GIU stop + symbol vao UNKNOWN_POSITION + Telegram (Reconciler doc lai moi 30 s de tu go neu that su phang)
        book.removeCluster(sym, r, now);
        int kept = 0;
        for (String id : cids) {
            OwnStopGuard.Result gr = guard().cancelOwnStopGuarded(sym, id, "cum dong (" + r + ")");
            if (gr == OwnStopGuard.Result.KEPT_POSITION || gr == OwnStopGuard.Result.KEPT_READ_ERROR) kept++;
        }
        if (kept > 0) LOG.warn("[C3-LIVE-FILL] {} cum da dong ({}) nhung GIU {} stop c3s- (vi the san chua phang / doc loi)", sym, r, kept);
        nClosedExchange.incrementAndGet();
        lastExitReason.remove(sym);
        try {
            closedHook.onClosed(sym, c.get().tsFirstLeg, r, now);
        } catch (Throwable ignore) {
            // chi log
        }
        boolean normal = REASON_TRAILING.equals(r) || isBotCloseReason(r);
        String m = "[C3-LIVE] cum " + sym + " DA DONG tren san (" + r + ") qty=" + c.get().confirmedQty.toPlainString()
                + " avg=" + c.get().avgPrice + " => da cap nhat so, xu ly " + cids.size() + " stop"
                + (kept > 0 ? " (GIU " + kept + " stop c3s- vi san chua xac nhan phang)" : "");
        if (normal) {
            LOG.info("{}", m);
        } else {
            LOG.warn("{}", m);
            alert.accept(m);
        }
    }

    private static boolean isBotCloseReason(String r) {
        return r != null && (r.startsWith("TIME_STOP") || r.startsWith("FLATTEN") || r.startsWith("X14")
                || r.startsWith("TRAILING_IMMEDIATE") || REASON_BOT_CLOSE.equals(r));
    }

    private OwnStopGuard guard() {
        OwnStopGuard g = stopGuard;
        if (g == null) {
            g = new OwnStopGuard(gw, book, api, alert, () -> unknownPosition, clock);
            stopGuard = g;
        }
        return g;
    }

    /** [2e MAJ-3] guard huy stop c3s- dung chung (runtime). */
    public void setStopGuard(OwnStopGuard g) {
        if (g != null) stopGuard = g;
    }

    /** Ly do dong suy tu clientOrderId / loai lenh goc. */
    public static String exitReason(String cid, String origType, String activeStopCid) {
        if (cid != null) {
            if (cid.startsWith(C3LiveCids.CLOSE_PREFIX)) return REASON_BOT_CLOSE;
            if (cid.startsWith(C3LiveCids.STOP_PREFIX) || cid.equals(activeStopCid)) return REASON_TRAILING;
            if (cid.startsWith("autoclose-")) return REASON_LIQ;
            if (cid.startsWith("adl_autoclose")) return REASON_ADL;
            if (cid.startsWith("settlement_autoclose")) return REASON_SETTLE;
        }
        if ("STOP_MARKET".equalsIgnoreCase(origType) || "STOP".equalsIgnoreCase(origType)) return REASON_TRAILING;
        return REASON_EXTERNAL;
    }

    /** [V12 R4f MINOR-1] gia &lt;ASSET&gt;USDT de quy phi ngoai stable (vd BNB); NaN = khong co. Runtime noi (gia realtime 242). */
    private volatile java.util.function.ToDoubleFunction<String> assetUsdPx = a -> Double.NaN;
    /** Khong co gia: ghi phi THAN TRONG = notional x 0,05 % (taker khong giam, &gt;= phi that) + canh bao. */
    static final double FEE_FALLBACK_RATE = 0.0005d;

    public void setAssetUsdPrice(java.util.function.ToDoubleFunction<String> f) {
        if (f != null) this.assetUsdPx = f;
    }

    double commissionUsd(BigDecimal n, String asset, double notionalUsd) {
        if (n == null || n.signum() == 0) return 0d;
        if (asset == null || STABLE.contains(asset.toUpperCase(Locale.ROOT))) return n.doubleValue();
        String a = asset.toUpperCase(Locale.ROOT);
        double px;
        try {
            px = assetUsdPx.applyAsDouble(a);
        } catch (RuntimeException e) {
            px = Double.NaN;
        }
        if (Double.isFinite(px) && px > 0d) return n.doubleValue() * px;   // [3g MIN-4] quy theo gia <ASSET>USDT
        double fb = Math.abs(notionalUsd) * FEE_FALLBACK_RATE;
        if (warnedAssets.add("fee|" + a)) {
            String m = "[C3-LIVE] phi tra bang " + a + " KHONG co gia " + a + "USDT => ghi THAN TRONG " + FEE_FALLBACK_RATE * 100
                    + " % notional (>= phi that); doi chieu equity c3 co the lech nhe — KIEM";
            LOG.warn("{}", m);
            alert.accept(m);
        }
        return fb;
    }

    /**
     * [V12 R4f MAJOR-L1] Ghi khop THOAT khoi phuc qua REST (userTrades) DUOI CUNG khoa voi stream (FillAccounting): doc lai cum SONG;
     * cum da dong (stream toi truoc) => KHONG ghi; moi khop theo tradeId (da ghi => bo). realized = (gia - gia vao c3) x qty (KHONG
     * dung rp san: sai khi MERGED; khong MERGED chi doi chieu); phi tru (USDT) / quy theo gia (khac). Tra so khop da ghi.
     */
    public synchronized int bookRecoveredExit(String sym, java.util.List<com.binance.chuyennd.c3live.api.TradeFill> fills, boolean merged) {
        long now = clock.getAsLong();
        Optional<LiveBookC3.ClusterView> c = book.cluster(sym);
        if (!c.isPresent()) {
            LOG.info("[C3-LIVE-FILL] {} cum da dong (stream toi truoc) => KHONG ghi khop khoi phuc", sym);
            return 0;
        }
        double avg = c.get().avgPrice;
        int n = 0;
        for (com.binance.chuyennd.c3live.api.TradeFill f : fills) {
            if (f.getQty() == null || f.getPrice() == null) continue;
            if (f.getTradeId() <= 0) {
                String m = "[C3-LIVE] " + sym + " khop khoi phuc orderId " + f.getOrderId() + " KHONG co tradeId => KHONG ghi (khong chong trung"
                        + " duoc); realized c3 co the THIEU — KIEM";
                LOG.error("{}", m);
                alert.accept(m);
                continue;
            }
            double q = f.getQty().doubleValue();
            double px = f.getPrice().doubleValue();
            double comm = commissionUsd(f.getCommission(), f.getCommissionAsset(), q * px);
            double rp = f.getPrice().subtract(BigDecimal.valueOf(avg)).multiply(f.getQty()).doubleValue();   // so hoc nhu stream (BigDecimal)
            if (!merged && f.getRealizedPnl() != null
                    && Math.abs(f.getRealizedPnl().doubleValue() - rp) > Math.max(0.01d, 1e-4d * q * px)) {
                LOG.warn("[C3-LIVE-FILL] {} khop {}: rp san {} khac rp c3 {} (gia vao c3 {}) — doi chieu", sym, f.getTradeId(),
                        f.getRealizedPnl().toPlainString(), rp, avg);
            }
            if (book.addRecoveredExit(sym, f.getTradeId(), f.getQty(), px, comm, rp, now)) {
                n++;
                nExitFill.incrementAndGet();
            }
        }
        return n;
    }

    private static String plain(BigDecimal v) {
        return v == null ? "" : v.stripTrailingZeros().toPlainString();
    }

    public String stats() {
        return "orders=" + nOrder.get() + " confirm=" + nConfirm.get() + " exitFill=" + nExitFill.get() + " closedOnExchange="
                + nClosedExchange.get() + " account=" + nAccount.get();
    }
}
