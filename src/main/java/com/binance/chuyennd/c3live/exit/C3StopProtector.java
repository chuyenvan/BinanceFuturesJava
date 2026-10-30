package com.binance.chuyennd.c3live.exit;

import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.rate.RateGuard;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.util.HashSet;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;
import java.util.function.Consumer;
import java.util.function.LongSupplier;
import java.util.function.Predicate;

/**
 * [V12 R4 R6] Bao ve NGAY cho c3_live production: cum DA arm (thiet ke c3 KHONG co stop truoc arm; DCA reset arm) con qty
 * ma KHONG co stop tren san => dat lai TRONG {@link RateGuard.Urgent} (khong ngu burst, moi lan cho guard phai xong truoc
 * han) theo priceSL da persist (gia nhu cu) qua {@link TrailingStopManager#ensureStop}.
 * <ul>
 *   <li>Stop bi SAN ket thuc khi con vi the (ALGO_UPDATE CANCELED/EXPIRED, {@link #onStopTerminal}): han = moc su kien +
 *       {@link #DEADLINE_MS} (61 s); qua han van khong co stop => dong qty c3 qua lan KHAN CAP
 *       ({@code C3LiveFlattener.closeCluster}) + Telegram. Symbol MERGED: KHONG dong (R2), chi Telegram KHAN + thu tiep.</li>
 *   <li>Truong hop khac (vua arm, Reconciler bo stop vang, restart): dat trong Urgent; qua han chi Telegram + thu tiep moi nhip
 *       (khong dong).</li>
 * </ul>
 */
public final class C3StopProtector {

    private static final Logger LOG = LoggerFactory.getLogger(C3StopProtector.class);
    public static final long DEADLINE_MS = 61_000L;
    public static final String REASON_STOP_LOST = "STOP_LOST_61S";
    /** moc su kien giu toi thieu (stream bao truoc khi FillAccounting go stop khoi so). */
    static final long EVENT_KEEP_MS = 10_000L;

    private final LiveBookC3 book;
    private final TrailingStopManager trailing;
    private final TrailingStopManager.Closer closer;
    private final Predicate<String> merged;
    private final Consumer<String> alert;
    private final LongSupplier clock;
    private final Map<String, Long> since = new TreeMap<>();
    private final Set<String> terminal = new HashSet<>();
    private final Set<String> alerted = new HashSet<>();
    /** [V12 R4b §4] MERGED: true = san &gt;= qty c3 (LEGACY cung long) => dong DUNG qty c3 la trung tinh. Mac dinh: khong dong. */
    private volatile Predicate<String> mergedMayClose = s -> false;

    public void setMergedCloseCheck(Predicate<String> p) {
        this.mergedMayClose = p == null ? s -> false : p;
    }

    public C3StopProtector(LiveBookC3 book, TrailingStopManager trailing, TrailingStopManager.Closer closer,
                           Predicate<String> merged, Consumer<String> alert, LongSupplier clock) {
        this.book = book;
        this.trailing = trailing;
        this.closer = closer;
        this.merged = merged == null ? s -> false : merged;
        this.alert = alert == null ? m -> { } : alert;
        this.clock = clock == null ? System::currentTimeMillis : clock;
    }

    /** Stream: stop c3s- cua symbol bi san ket thuc (CANCELED/EXPIRED). */
    public synchronized void onStopTerminal(String sym, long now) {
        if (sym == null) return;
        Long s = since.get(sym);
        if (s == null || now < s) since.put(sym, now);
        terminal.add(sym);
    }

    private static boolean needsStop(LiveBookC3.ClusterView c) {
        BigDecimal open = c.confirmedQty.subtract(c.exitQty == null ? BigDecimal.ZERO : c.exitQty);
        return c.trailArmed() && open.signum() > 0 && !c.hasUnresolved && c.closeReason == null
                && c.stopClientAlgoId == null && c.pendingStopCid == null;
    }

    private void place(String sym, long deadline) {
        try (RateGuard.Urgent u = RateGuard.urgent(deadline)) {
            trailing.ensureStop(sym, null);
        } catch (RuntimeException e) {
            LOG.warn("[C3-LIVE-PROTECT] {} dat lai stop loi: {}", sym, e.toString());
        }
    }

    /** Kiem moi cum (ops 5 s + ngay khi co su kien). @return so cum con khong co stop sau luot. */
    public synchronized int check() {
        long now = clock.getAsLong();
        int unprotected = 0;
        Set<String> seen = new HashSet<>();
        for (LiveBookC3.ClusterView c : book.clusters()) {
            String sym = c.symbol;
            if (!needsStop(c)) continue;
            seen.add(sym);
            long s0 = since.computeIfAbsent(sym, k -> now);
            long dl = s0 + DEADLINE_MS;
            if (now <= dl) {
                place(sym, dl);
                Optional<LiveBookC3.ClusterView> c2 = book.cluster(sym);
                if (!c2.isPresent() || !needsStop(c2.get())) {
                    LOG.warn("[C3-LIVE-PROTECT] {} co stop lai sau {} ms", sym, clock.getAsLong() - s0);
                    since.remove(sym);
                    terminal.remove(sym);
                    alerted.remove(sym);
                    seen.remove(sym);
                    continue;
                }
                unprotected++;
                continue;
            }
            unprotected++;
            if (!terminal.contains(sym)) {
                if (alerted.add(sym)) {
                    String m = "[C3-LIVE] " + sym + " da arm nhung KHONG co stop tren san > " + DEADLINE_MS / 1000
                            + " s — van thu lai moi nhip (Urgent); kiem rate/san";
                    LOG.error("{}", m);
                    alert.accept(m);
                }
                place(sym, now + DEADLINE_MS);
                continue;
            }
            if (merged.test(sym)) {
                boolean canClose;
                try {
                    canClose = mergedMayClose.test(sym);
                } catch (RuntimeException e) {
                    canClose = false;
                }
                if (canClose) {
                    String m = "[C3-LIVE] KHAN: " + sym + " MERGED, san >= qty c3 (LEGACY cung long), stop bi san ket thuc > "
                            + DEADLINE_MS / 1000 + " s => DONG DUNG qty c3 (c3x- reduceOnly, lan khan cap) — trung tinh voi LEGACY";
                    LOG.error("{}", m);
                    alert.accept(m);
                    try {
                        closer.closeCluster(sym, REASON_STOP_LOST);
                    } catch (RuntimeException e) {
                        LOG.error("[C3-LIVE-PROTECT] {} dong khan cap loi: {}", sym, e.toString());
                    }
                    continue;
                }
                if (alerted.add(sym)) {
                    String m = "[C3-LIVE] KHAN: " + sym + " MERGED mat stop > " + DEADLINE_MS / 1000 + " s — KHONG dong (san < qty c3 / am:"
                            + " LEGACY ban vao long c3); trailing tiep tuc dat stop qty; owner KIEM NGAY";
                    LOG.error("{}", m);
                    alert.accept(m);
                }
                place(sym, now + DEADLINE_MS);
                continue;
            }
            String m = "[C3-LIVE] KHAN: " + sym + " stop bi san ket thuc, dat lai KHONG duoc trong " + DEADLINE_MS / 1000
                    + " s => DONG qty c3 qua lan khan cap (R6)";
            LOG.error("{}", m);
            alert.accept(m);
            try {
                closer.closeCluster(sym, REASON_STOP_LOST);
            } catch (RuntimeException e) {
                LOG.error("[C3-LIVE-PROTECT] {} dong khan cap loi: {}", sym, e.toString());
            }
        }
        since.entrySet().removeIf(e -> !seen.contains(e.getKey()) && now - e.getValue() > EVENT_KEEP_MS);
        terminal.retainAll(since.keySet());
        alerted.retainAll(seen);
        return unprotected;
    }

    public synchronized String status() {
        return "unprotected=" + since.keySet() + " terminal=" + terminal;
    }
}
