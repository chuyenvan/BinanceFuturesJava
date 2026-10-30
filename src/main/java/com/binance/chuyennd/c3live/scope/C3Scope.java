package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.exec.C3LiveCids;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.LongSupplier;
import java.util.function.Supplier;

/**
 * [V12 R4 R1/R2/R3] PHAM VI c3_live tren TAI KHOAN CHINH (44 vi the LEGACY + bot LEGACY cung IP).
 * <ul>
 *   <li>c3 chi thay / ghi cua CHINH no: cid {@code c3-}/{@code c3x-}/{@code c3s-} va cum trong so c3.</li>
 *   <li>symbol "lien quan c3" = cum dang giu (ke ca leg treo) / vua chot &lt; 15' (khong co hoat dong LEGACY sau khi chot) /
 *       Reconciler dang theo doi (A)(B) / con stop c3s- bi giu / MERGED. Vi the cua symbol KHONG lien quan = LEGACY: bi an
 *       khoi lop c3 (khong bao gio la chan (A), khong bao gio bi cham).</li>
 *   <li>LEGACY-busy = symbol co vi the / lenh / algo KHONG phai c3 (lam moi moi chu ky; anh chup cu &gt; 3' => fail-closed:
 *       chan MO MOI moi symbol).</li>
 *   <li>MERGED (one-way da cong don LEGACY vao symbol c3 dang giu): view tra PHAN c3 = min(san, can tren so c3); trang thai
 *       persist (song qua restart).</li>
 * </ul>
 * Thread-safe; khong goi ra ngoai khi giu khoa (chi doc so / snapshot volatile).
 */
public final class C3Scope {

    private static final Logger LOG = LoggerFactory.getLogger(C3Scope.class);
    /** anh chup LEGACY cu hon muc nay => chan MO MOI moi symbol (fail-closed). */
    public static final long LEGACY_MAX_AGE_MS = 180_000L;
    /** symbol vua chot van "lien quan c3" trong cua so nay (> OwnStopGuard.KNOWN_CLOSE_WINDOW_MS 10'). */
    public static final long RELATED_AFTER_CLOSE_MS = 15L * 60_000L;
    public static final BigDecimal EPS = new BigDecimal("1e-9");
    /** [V12 R4b MINOR-5] vi the khong-c3 tren symbol c3 vua chot chi bi coi la LEGACY sau khoang nay (REST tre sau khi dong). */
    public static final long TOUCH_AFTER_CLOSE_MS = 60_000L;

    private final LiveBookC3 book;
    private final LongSupplier clock;
    private final File mergedFile;
    private volatile Supplier<Set<String>> extraRelated = Collections::emptySet;
    private final Map<String, Long> legacyTouched = new ConcurrentHashMap<>();
    private final Map<String, String> merged = new ConcurrentHashMap<>();
    private final Map<String, BigDecimal> lastRawAmt = new ConcurrentHashMap<>();
    private final Map<String, String> busyMarks = new ConcurrentHashMap<>();
    private volatile Map<String, String> legacyBusy = Collections.emptyMap();
    private volatile long legacyAtMs = Long.MIN_VALUE;
    private volatile int legacyPositionCount = -1;
    /** [V12 R4c A] symbol LOST_FOREIGN: chan mo lai toi moc (ms) — persist canh file MERGED. */
    private final Map<String, Long> lostUntil = new ConcurrentHashMap<>();
    private final Map<String, String> lostWhy = new ConcurrentHashMap<>();
    /** [V12 R4c B] da canh bao vi the khong-c3 tren symbol vua chot (sym -> moc chot da canh bao). */
    private final Map<String, Long> foreignAfterCloseAlerted = new ConcurrentHashMap<>();
    private final java.util.concurrent.ConcurrentLinkedQueue<String> foreignAfterCloseQ = new java.util.concurrent.ConcurrentLinkedQueue<>();
    public static final long LOST_BLOCK_MS = 24L * 3_600_000L;

    public C3Scope(LiveBookC3 book, LongSupplier clock, File mergedFile) {
        this.book = book;
        this.clock = clock == null ? System::currentTimeMillis : clock;
        this.mergedFile = mergedFile;
        loadMerged();
        loadLost();
    }

    // ------------------------------------------------------------------ cid
    public static boolean isC3OrderCid(String cid) {
        return cid != null && (cid.startsWith(C3LiveCids.ENTRY_PREFIX) || cid.startsWith(C3LiveCids.CLOSE_PREFIX));
    }

    public static boolean isC3AlgoCid(String cid) {
        return cid != null && cid.startsWith(C3LiveCids.STOP_PREFIX);
    }

    public static boolean isC3Cid(String cid) {
        return isC3OrderCid(cid) || isC3AlgoCid(cid);
    }

    /** Lenh do SAN tu sinh dong vi the (thanh ly / ADL / delist): dong ca phan c3. */
    public static boolean isExchangeCloseCid(String cid) {
        return cid != null && (cid.startsWith("autoclose-") || cid.startsWith("adl_autoclose")
                || cid.startsWith("settlement_autoclose"));
    }

    // ------------------------------------------------------------------ so c3
    /** Noi them symbol "lien quan" (Reconciler dang theo doi, stop c3s- bi giu). Supplier KHONG duoc lay khoa. */
    public void setExtraRelated(Supplier<Set<String>> s) {
        this.extraRelated = s == null ? Collections::emptySet : s;
    }

    public boolean held(String sym) {
        return sym != null && book.cluster(sym).isPresent();
    }

    /** Qty c3 dang mo theo so = confirmed - da dong (>= 0). */
    public BigDecimal c3OpenQty(String sym) {
        Optional<LiveBookC3.ClusterView> c = sym == null ? Optional.<LiveBookC3.ClusterView>empty() : book.cluster(sym);
        if (!c.isPresent()) return BigDecimal.ZERO;
        BigDecimal ex = c.get().exitQty == null ? BigDecimal.ZERO : c.get().exitQty;
        BigDecimal q = c.get().confirmedQty.subtract(ex);
        return q.signum() > 0 ? q : BigDecimal.ZERO;
    }

    /** Can tren qty c3 = dang mo + qty yeu cau cua leg chua ro (PENDING/SENDING/UNKNOWN). */
    public BigDecimal c3UpperQty(String sym) {
        Optional<LiveBookC3.ClusterView> c = sym == null ? Optional.<LiveBookC3.ClusterView>empty() : book.cluster(sym);
        if (!c.isPresent()) return BigDecimal.ZERO;
        BigDecimal q = c3OpenQty(sym);
        for (LiveBookC3.LegView l : c.get().legs) {
            if (l.state != null && l.state.unresolved() && l.reqQty != null) q = q.add(l.reqQty);
        }
        return q;
    }

    private boolean recentlyClosedNoLegacy(String sym, long now) {
        long t = book.lastRemovedMs(sym);
        if (t == Long.MIN_VALUE || now - t < 0L || now - t >= RELATED_AFTER_CLOSE_MS) return false;
        Long lt = legacyTouched.get(sym);
        return lt == null || lt < t;
    }

    private boolean legacyTouchedAfterClose(String sym) {
        long t = book.lastRemovedMs(sym);
        Long lt = legacyTouched.get(sym);
        return t != Long.MIN_VALUE && lt != null && lt >= t;
    }

    /** symbol thuoc pham vi c3 (vi the hien ra o lop c3). */
    public boolean related(String sym) {
        if (sym == null) return false;
        if (held(sym) || merged.containsKey(sym)) return true;
        long now = clock.getAsLong();
        if (recentlyClosedNoLegacy(sym, now)) return true;
        Set<String> ex;
        try {
            ex = extraRelated.get();
        } catch (RuntimeException e) {
            ex = Collections.emptySet();
        }
        // LEGACY da vao symbol SAU khi c3 chot => vi the la cua LEGACY, khong theo doi nua (R3)
        return ex != null && ex.contains(sym) && !legacyTouchedAfterClose(sym);
    }

    // ------------------------------------------------------------------ view
    /** View vi the cua lop c3: bo symbol LEGACY; symbol MERGED => phan c3. */
    public List<PositionInfo> view(List<PositionInfo> raw) {
        List<PositionInfo> out = new ArrayList<>();
        if (raw == null) return out;
        for (PositionInfo p : raw) {
            String s = p.getSymbol();
            if (s == null || !related(s)) continue;
            if (merged.containsKey(s) && p.getPositionAmt() != null) {
                out.add(share(p));
            } else {
                out.add(p);
            }
        }
        return out;
    }

    private PositionInfo share(PositionInfo p) {
        String s = p.getSymbol();
        BigDecimal amt = p.getPositionAmt();
        BigDecimal upper = c3UpperQty(s);
        BigDecimal q = amt.signum() < 0 ? c3OpenQty(s) : amt.min(upper);
        if (q.signum() < 0) q = BigDecimal.ZERO;
        Optional<LiveBookC3.ClusterView> c = book.cluster(s);
        BigDecimal ep = c.isPresent() && c.get().avgPrice > 0d ? BigDecimal.valueOf(c.get().avgPrice) : p.getEntryPrice();
        BigDecimal mark = p.getMarkPrice();
        BigDecimal upl = mark == null || ep == null ? null : mark.subtract(ep).multiply(q);
        BigDecimal notional = mark == null ? null : mark.multiply(q);
        return new PositionInfo(s, p.getPositionSide(), q, ep, mark, upl, notional, p.getUpdateTimeMs());
    }

    /** View lenh / algo: CHI cid c3. */
    public static List<OrderInfo> c3Only(List<OrderInfo> raw) {
        List<OrderInfo> out = new ArrayList<>();
        if (raw == null) return out;
        for (OrderInfo o : raw) if (isC3Cid(o.getClientOrderId())) out.add(o);
        return out;
    }

    // ------------------------------------------------------------------ LEGACY-busy
    /**
     * Lam moi tap LEGACY-busy tu doc TOAN tai khoan (chi doc): symbol co lenh/algo khong-c3, hoac vi the khong thuoc c3
     * (khong giu trong so, am, hoac lon hon can tren so c3).
     */
    public void refreshLegacy(List<PositionInfo> positions, List<OrderInfo> orders, List<OrderInfo> algos, long now) {
        Map<String, String> busy = new TreeMap<>();
        int legacyPos = 0;
        for (PositionInfo p : positions) {
            String s = p.getSymbol();
            BigDecimal amt = p.getPositionAmt();
            if (s == null || amt == null) continue;
            lastRawAmt.put(s, amt);
            if (amt.signum() == 0) continue;
            if (!held(s)) {
                legacyPos++;
                busy.put(s, "vi the " + amt.toPlainString());
                long rm = book.lastRemovedMs(s);
                if (rm == Long.MIN_VALUE || now - rm >= TOUCH_AFTER_CLOSE_MS) touchLegacy(s, now);   // [R4b MINOR-5]
                if (rm != Long.MIN_VALUE && now - rm >= TOUCH_AFTER_CLOSE_MS && now - rm < RELATED_AFTER_CLOSE_MS) {
                    Long done = foreignAfterCloseAlerted.get(s);
                    if (done == null || done != rm) {   // [V12 R4c B] KHAN dung 1 lan / lan chot
                        foreignAfterCloseAlerted.put(s, rm);
                        foreignAfterCloseQ.add("[C3-LIVE] KHAN: " + s + " co vi the KHONG-c3 qty=" + amt.toPlainString()
                                + " tren symbol c3 vua chot " + (now - rm) / 1000 + " s truoc => coi la LEGACY (an khoi lop c3, LEGACY-busy);"
                                + " neu KHONG phai LEGACY (phan du c3 / so sai) owner KIEM NGAY");
                    }
                }
            } else if (amt.signum() < 0 || amt.compareTo(c3UpperQty(s).add(EPS)) > 0) {
                busy.put(s, "vi the san " + amt.toPlainString() + " > c3 " + c3UpperQty(s).toPlainString());
            }
        }
        for (OrderInfo o : orders) {
            if (o.getSymbol() != null && !isC3OrderCid(o.getClientOrderId())) busy.putIfAbsent(o.getSymbol(), "lenh " + o.getClientOrderId());
        }
        for (OrderInfo o : algos) {
            if (o.getSymbol() != null && !isC3AlgoCid(o.getClientOrderId())) busy.putIfAbsent(o.getSymbol(), "algo " + o.getClientOrderId());
        }
        legacyBusy = Collections.unmodifiableMap(busy);
        legacyPositionCount = legacyPos;
        legacyAtMs = now;
        busyMarks.clear();
    }

    /** Danh dau busy ngay (kiem truoc ghi / stream thay hoat dong LEGACY) — toi lan lam moi ke tiep. */
    public void markBusy(String sym, String why) {
        if (sym == null) return;
        if (busyMarks.put(sym, why == null ? "-" : why) == null) LOG.info("[C3-LIVE-SCOPE] {} LEGACY-busy: {}", sym, why);
    }

    /** Hoat dong LEGACY (lenh/khop khong-c3) tren symbol. */
    public void touchLegacy(String sym, long now) {
        if (sym != null) legacyTouched.put(sym, now);
    }

    /** [V12 R4c B] canh bao cho gui (moi lan chot 1 lan). */
    public java.util.List<String> drainForeignAfterClose() {
        java.util.List<String> out = new ArrayList<>();
        String m;
        while ((m = foreignAfterCloseQ.poll()) != null) out.add(m);
        return out;
    }

    /** [V12 R4c A] chan mo lai symbol toi {@code untilMs} (LOST_FOREIGN); persist. */
    public void blockLost(String sym, long untilMs, String why) {
        if (sym == null) return;
        lostUntil.put(sym, untilMs);
        lostWhy.put(sym, why == null ? "-" : why);
        persistLost();
    }

    public boolean isLostBlocked(String sym, long now) {
        Long u = sym == null ? null : lostUntil.get(sym);
        return u != null && now < u;
    }

    private File lostFile() {
        return mergedFile == null ? null : new File(mergedFile.getAbsoluteFile().getParentFile(), "c3live_lost.txt");
    }

    private void loadLost() {
        File f = lostFile();
        if (f == null || !f.exists()) return;
        try {
            for (String line : Files.readAllLines(f.toPath(), StandardCharsets.UTF_8)) {
                String[] t = line.trim().split(" ", 3);
                if (t.length < 2 || !t[0].matches("[A-Z0-9]{2,40}")) continue;
                lostUntil.put(t[0], Long.parseLong(t[1]));
                lostWhy.put(t[0], t.length > 2 ? t[2] : "persist");
            }
            if (!lostUntil.isEmpty()) LOG.warn("[C3-LIVE-SCOPE] nap LOST_FOREIGN tu {}: {}", f.getPath(), lostUntil);
        } catch (Exception e) {
            LOG.error("[C3-LIVE-SCOPE] khong doc duoc {}: {}", f.getPath(), e.toString());
        }
    }

    private synchronized void persistLost() {
        File f = lostFile();
        if (f == null) return;
        try {
            File abs = f.getAbsoluteFile();
            if (abs.getParentFile() != null) abs.getParentFile().mkdirs();
            File tmp = new File(abs.getParentFile(), abs.getName() + ".tmp");
            StringBuilder sb = new StringBuilder();
            for (Map.Entry<String, Long> e : new TreeMap<>(lostUntil).entrySet()) {
                sb.append(e.getKey()).append(' ').append(e.getValue()).append(' ')
                        .append(lostWhy.getOrDefault(e.getKey(), "-").replace('\n', ' ')).append('\n');
            }
            Files.write(tmp.toPath(), sb.toString().getBytes(StandardCharsets.UTF_8));
            Files.move(tmp.toPath(), abs.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (Exception e) {
            LOG.error("[C3-LIVE-SCOPE] khong ghi duoc {}: {}", f.getPath(), e.toString());
        }
    }

    public boolean legacyFresh(long now) {
        return legacyAtMs != Long.MIN_VALUE && now - legacyAtMs <= LEGACY_MAX_AGE_MS;
    }

    /** Ly do CHAN mo lenh (entry lan DCA) tren symbol; null = khong chan. */
    public String entryBlockReason(String sym, long now) {
        if (!legacyFresh(now)) return "anh chup LEGACY cu/chua co (fail-closed)";
        if (isLostBlocked(sym, now)) return "LOST_FOREIGN (chan toi " + lostUntil.get(sym) + ") " + lostWhy.get(sym);
        String m = sym == null ? null : merged.get(sym);
        if (m != null) return "MERGED " + m;
        String b = sym == null ? null : legacyBusy.get(sym);
        if (b != null) return "LEGACY-busy " + b;
        b = sym == null ? null : busyMarks.get(sym);
        if (b != null) return "LEGACY-busy " + b;
        return null;
    }

    public boolean entryBlocked(String sym, long now) {
        return entryBlockReason(sym, now) != null;
    }

    public Set<String> legacyBusySymbols() {
        Set<String> s = new TreeSet<>(legacyBusy.keySet());
        s.addAll(busyMarks.keySet());
        return s;
    }

    public int legacyPositionCount() {
        return legacyPositionCount;
    }

    public long legacyAtMs() {
        return legacyAtMs;
    }

    public BigDecimal lastRawAmt(String sym) {
        return sym == null ? null : lastRawAmt.get(sym);
    }

    public void noteRawAmt(String sym, BigDecimal amt) {
        if (sym != null && amt != null) lastRawAmt.put(sym, amt);
    }

    // ------------------------------------------------------------------ MERGED
    public boolean isMerged(String sym) {
        return sym != null && merged.containsKey(sym);
    }

    public Map<String, String> merged() {
        return new TreeMap<>(merged);
    }

    /** @return true neu MOI vao trang thai MERGED. */
    public boolean setMerged(String sym, String why) {
        if (sym == null) return false;
        boolean fresh = merged.putIfAbsent(sym, why == null ? "-" : why) == null;
        if (fresh) persistMerged();
        return fresh;
    }

    public boolean clearMerged(String sym) {
        boolean was = sym != null && merged.remove(sym) != null;
        if (was) persistMerged();
        return was;
    }

    private void loadMerged() {
        if (mergedFile == null || !mergedFile.exists()) return;
        try {
            for (String line : Files.readAllLines(mergedFile.toPath(), StandardCharsets.UTF_8)) {
                String t = line.trim();
                if (t.isEmpty()) continue;
                int sp = t.indexOf(' ');
                String s = sp < 0 ? t : t.substring(0, sp);
                if (s.matches("[A-Z0-9]{2,40}")) merged.put(s, sp < 0 ? "persist" : t.substring(sp + 1));
            }
            if (!merged.isEmpty()) LOG.warn("[C3-LIVE-SCOPE] nap MERGED tu {}: {}", mergedFile.getPath(), merged.keySet());
        } catch (Exception e) {
            LOG.error("[C3-LIVE-SCOPE] khong doc duoc file MERGED {}: {}", mergedFile.getPath(), e.toString());
        }
    }

    private synchronized void persistMerged() {
        if (mergedFile == null) return;
        try {
            File abs = mergedFile.getAbsoluteFile();
            if (abs.getParentFile() != null) abs.getParentFile().mkdirs();
            File tmp = new File(abs.getParentFile(), abs.getName() + ".tmp");
            StringBuilder sb = new StringBuilder();
            for (Map.Entry<String, String> e : new TreeMap<>(merged).entrySet()) {
                sb.append(e.getKey()).append(' ').append(e.getValue().replace('\n', ' ')).append('\n');
            }
            Files.write(tmp.toPath(), sb.toString().getBytes(StandardCharsets.UTF_8));
            Files.move(tmp.toPath(), abs.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (Exception e) {
            LOG.error("[C3-LIVE-SCOPE] khong ghi duoc file MERGED {}: {}", mergedFile.getPath(), e.toString());
        }
    }

    public String status() {
        long now = clock.getAsLong();
        return "legacyPos=" + legacyPositionCount + " legacyBusy=" + legacyBusySymbols().size() + " fresh=" + legacyFresh(now)
                + " merged=" + merged.keySet();
    }
}
