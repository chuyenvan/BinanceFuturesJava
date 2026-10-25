package com.binance.chuyennd.c3live.book;

import com.binance.chuyennd.tradecore.selector.LiveDcaGridC3;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * [V12 C1] So vi the THAT cua c3_live (tai khoan con). Cum theo symbol: legs (cid, legIdx, qty, gia, margin, trang thai),
 * tsFirstLeg, legCount, peak/armed/stopPrice/stopClientAlgoId (cho trailing C6 vong 2b), closeCid.
 *
 * <p>Giu cho margin DONG BO truoc khi gui lenh: {@link #reserve} ghi leg PENDING (margin du kien = notional/leverage)
 * va persist TRUOC khi lenh roi khoi JVM => U = {@link #marginUsed()} / equity tinh ca pending => 24 ung vien cung tick
 * thay nhau. Xac nhan ({@link #confirm}) / huy ({@link #cancel}) theo ket qua san.
 *
 * <p>Trang thai leg: PENDING (chua gui) -> SENDING (da gui >= 1 lan; ghi TRUOC khi gui) -> CONFIRMED | CANCELLED;
 * UNKNOWN = gui roi nhung khong biet san da nhan chua (timeout) — chi duoc gui lai SAU KHI queryOrder xac nhan khong co.
 * Ca 3 trang thai chua giai quyet deu tinh margin (bao thu) va khoa symbol (khoa xu ly persist qua restart).
 *
 * <p>Persist JSON {@code run/c3live_book.json}, ghi atomic (tmp + ATOMIC_MOVE) sau MOI thay doi. File hong => sao luu
 * {@code .corrupt_<ms>} + {@link #healthy()} = false (fail-closed: chan mo moi). Ghi loi => healthy=false toi khi ghi lai duoc.
 * Thread-safe (moi ham synchronized).
 */
public final class LiveBookC3 {

    private static final Logger LOG = LoggerFactory.getLogger(LiveBookC3.class);
    public static final String DEFAULT_FILE = "run/c3live_book.json";
    public static final int VERSION = 1;

    public enum LegState {
        PENDING, SENDING, UNKNOWN, CONFIRMED, CANCELLED;

        public boolean unresolved() {
            return this == PENDING || this == SENDING || this == UNKNOWN;
        }
    }

    /** Ban sao bat bien cua 1 leg. */
    public static final class LegView {
        public final String symbol;
        public final String cid;
        public final int legIdx;
        public final long barMin;
        public final String level;
        public final double refPx;
        public final BigDecimal reqQty;
        public final double reservedMargin;
        public final LegState state;
        public final BigDecimal execQty;
        public final double avgPx;
        public final long orderId;
        public final long tsCreated;
        public final long lastSendMs;
        public final int attempts;
        public final String note;

        LegView(String symbol, Leg l) {
            this.symbol = symbol;
            this.cid = l.cid;
            this.legIdx = l.legIdx;
            this.barMin = l.barMin;
            this.level = l.level;
            this.refPx = l.refPx;
            this.reqQty = l.reqQty;
            this.reservedMargin = l.reservedMargin;
            this.state = l.state;
            this.execQty = l.execQty;
            this.avgPx = l.avgPx;
            this.orderId = l.orderId;
            this.tsCreated = l.tsCreated;
            this.lastSendMs = l.lastSendMs;
            this.attempts = l.attempts;
            this.note = l.note;
        }

        @Override
        public String toString() {
            return symbol + "/" + cid + "/" + state + "/qty=" + reqQty + "/exec=" + execQty;
        }
    }

    /** Ban sao bat bien cua 1 cum. */
    public static final class ClusterView {
        public final String symbol;
        public final long tsFirstLeg;
        public final int legCount;
        public final BigDecimal confirmedQty;
        public final double avgPrice;
        public final double confirmedMargin;
        public final double pendingMargin;
        public final double firstEntryPrice;
        public final double peak;
        public final boolean armed;
        public final double stopPrice;
        public final String stopClientAlgoId;
        public final String closeCid;
        public final String closeReason;
        public final int closeAttempts;
        public final long closeSentMs;
        public final boolean hasUnresolved;
        public final List<LegView> legs;

        ClusterView(Cluster c, double leverage) {
            this.symbol = c.symbol;
            this.tsFirstLeg = c.tsFirstLeg;
            this.legCount = c.legCount();
            this.confirmedQty = c.confirmedQty();
            this.avgPrice = c.avgPrice();
            this.confirmedMargin = c.confirmedMargin(leverage);
            this.pendingMargin = c.pendingMargin();
            this.firstEntryPrice = c.firstEntryPrice();
            this.peak = c.peak;
            this.armed = c.armed;
            this.stopPrice = c.stopPrice;
            this.stopClientAlgoId = c.stopClientAlgoId;
            this.closeCid = c.closeCid;
            this.closeReason = c.closeReason;
            this.closeAttempts = c.closeAttempts;
            this.closeSentMs = c.closeSentMs;
            this.hasUnresolved = c.hasUnresolved();
            List<LegView> ls = new ArrayList<>();
            for (Leg l : c.legs) ls.add(new LegView(c.symbol, l));
            this.legs = Collections.unmodifiableList(ls);
        }
    }

    // ------------------------------------------------------------------ trang thai noi bo
    static final class Leg {
        String cid;
        int legIdx;
        long barMin;
        String level;
        double refPx;
        BigDecimal reqQty;
        double reservedMargin;
        LegState state;
        BigDecimal execQty = BigDecimal.ZERO;
        double avgPx;
        long orderId;
        long tsCreated;
        long tsUpdated;
        long lastSendMs;
        int attempts;
        String note = "";
    }

    static final class Cluster {
        String symbol;
        long tsFirstLeg;
        final List<Leg> legs = new ArrayList<>();
        double peak;
        boolean armed;
        double stopPrice;
        String stopClientAlgoId;
        String closeCid;
        String closeReason;
        long closeSinceMs;
        long closeSentMs;
        int closeAttempts;

        int legCount() {
            int n = 0;
            for (Leg l : legs) if (l.state != LegState.CANCELLED) n++;
            return n;
        }

        boolean hasUnresolved() {
            for (Leg l : legs) if (l.state.unresolved()) return true;
            return false;
        }

        BigDecimal confirmedQty() {
            BigDecimal q = BigDecimal.ZERO;
            for (Leg l : legs) if (l.state == LegState.CONFIRMED) q = q.add(l.execQty);
            return q;
        }

        double avgPrice() {
            double qty = 0d, notional = 0d;
            for (Leg l : legs) {
                if (l.state != LegState.CONFIRMED) continue;
                double q = l.execQty.doubleValue();
                qty += q;
                notional += q * l.avgPx;
            }
            return qty > 0d ? notional / qty : 0d;
        }

        double confirmedMargin(double leverage) {
            double m = 0d;
            for (Leg l : legs) if (l.state == LegState.CONFIRMED) m += l.execQty.doubleValue() * l.avgPx / leverage;
            return m;
        }

        double pendingMargin() {
            double m = 0d;
            for (Leg l : legs) if (l.state.unresolved()) m += l.reservedMargin;
            return m;
        }

        /** Gia leg dau (khong tinh leg huy): gia khop neu da xac nhan, gia ref neu con treo. */
        double firstEntryPrice() {
            for (Leg l : legs) {
                if (l.state == LegState.CANCELLED) continue;
                return l.state == LegState.CONFIRMED && l.avgPx > 0d ? l.avgPx : l.refPx;
            }
            return 0d;
        }
    }

    private final File file;
    private final double leverage;
    private final Map<String, Cluster> clusters = new TreeMap<>();
    private final Map<String, String> cidToSymbol = new LinkedHashMap<>();
    private boolean loadOk = true;
    private boolean persistOk = true;
    private String unhealthyReason = "";

    /**
     * @param file     file persist (null = chi RAM, dung cho test)
     * @param leverage don bay (c3_live = 1, owner chot CROSS 1x)
     */
    public LiveBookC3(File file, double leverage) {
        if (!(leverage > 0d)) throw new IllegalArgumentException("leverage phai > 0");
        this.file = file;
        this.leverage = leverage;
        load();
    }

    // ------------------------------------------------------------------ doc
    public synchronized boolean healthy() {
        return loadOk && persistOk;
    }

    public synchronized String unhealthyReason() {
        return healthy() ? "" : unhealthyReason;
    }

    public double leverage() {
        return leverage;
    }

    public File file() {
        return file;
    }

    /** Margin dang dung = confirmed (qty*gia khop / leverage) + giu cho cua leg chua giai quyet. */
    public synchronized double marginUsed() {
        double m = 0d;
        for (Cluster c : clusters.values()) m += c.confirmedMargin(leverage) + c.pendingMargin();
        return m;
    }

    public synchronized double pendingMargin() {
        double m = 0d;
        for (Cluster c : clusters.values()) m += c.pendingMargin();
        return m;
    }

    /** Co cum (pending hoac confirmed hoac dang dong) — guard trung coin. */
    public synchronized boolean isHolding(String symbol) {
        return clusters.containsKey(symbol);
    }

    public synchronized boolean hasUnresolved(String symbol) {
        Cluster c = clusters.get(symbol);
        return c != null && c.hasUnresolved();
    }

    public synchronized boolean isClosing(String symbol) {
        Cluster c = clusters.get(symbol);
        return c != null && c.closeReason != null;
    }

    /** So leg khong bi huy (= bac grid tiep theo, nhu sim legCount). */
    public synchronized int legCount(String symbol) {
        Cluster c = clusters.get(symbol);
        return c == null ? 0 : c.legCount();
    }

    public synchronized int openCount() {
        return clusters.size();
    }

    public synchronized Set<String> ownedSymbols() {
        return new TreeSet<>(clusters.keySet());
    }

    public synchronized Optional<ClusterView> cluster(String symbol) {
        Cluster c = clusters.get(symbol);
        return c == null ? Optional.empty() : Optional.of(new ClusterView(c, leverage));
    }

    public synchronized List<ClusterView> clusters() {
        List<ClusterView> out = new ArrayList<>();
        for (Cluster c : clusters.values()) out.add(new ClusterView(c, leverage));
        return out;
    }

    public synchronized Optional<LegView> leg(String cid) {
        String s = cid == null ? null : cidToSymbol.get(cid);
        if (s == null) return Optional.empty();
        Cluster c = clusters.get(s);
        Leg l = c == null ? null : find(c, cid);
        return l == null ? Optional.empty() : Optional.of(new LegView(s, l));
    }

    /** Moi leg chua giai quyet (PENDING/SENDING/UNKNOWN). */
    public synchronized List<LegView> unresolvedLegs() {
        List<LegView> out = new ArrayList<>();
        for (Cluster c : clusters.values()) {
            for (Leg l : c.legs) if (l.state.unresolved()) out.add(new LegView(c.symbol, l));
        }
        return out;
    }

    /**
     * Trang thai grid cho DCA (port {@code ShadowBookC3.gridStates}) tu vi the THAT: chi cum co qty xac nhan > 0,
     * khong con leg treo va khong dang dong. legCount = so leg khong huy.
     */
    public synchronized List<LiveDcaGridC3.GridState> gridStates() {
        List<LiveDcaGridC3.GridState> out = new ArrayList<>();
        for (Cluster c : clusters.values()) {
            if (c.closeReason != null || c.hasUnresolved()) continue;
            if (c.confirmedQty().signum() <= 0) continue;
            out.add(new LiveDcaGridC3.GridState(c.symbol, (float) c.firstEntryPrice(), c.legCount()));
        }
        return out;
    }

    // ------------------------------------------------------------------ ghi
    /**
     * Giu cho margin cho 1 leg MUA truoc khi gui. false (khong doi gi) khi: so khong lanh, cid da ton tai (idempotent),
     * hoac cum dang dong.
     */
    public synchronized boolean reserve(String symbol, String cid, int legIdx, long barMin, String level, double refPx,
                                        BigDecimal qty, double margin, long nowMs) {
        if (!healthy()) return false;
        if (symbol == null || cid == null || qty == null || qty.signum() <= 0 || !(margin > 0d)) return false;
        if (cidToSymbol.containsKey(cid)) return false;
        Cluster c = clusters.get(symbol);
        if (c != null && c.closeReason != null) return false;
        if (c == null) {
            c = new Cluster();
            c.symbol = symbol;
            c.tsFirstLeg = nowMs;
            clusters.put(symbol, c);
        }
        Leg l = new Leg();
        l.cid = cid;
        l.legIdx = legIdx;
        l.barMin = barMin;
        l.level = level == null ? "" : level;
        l.refPx = refPx;
        l.reqQty = qty;
        l.reservedMargin = margin;
        l.state = LegState.PENDING;
        l.tsCreated = nowMs;
        l.tsUpdated = nowMs;
        c.legs.add(l);
        cidToSymbol.put(cid, symbol);
        persist(nowMs);
        return true;
    }

    /** Ghi TRUOC khi gui: SENDING, attempts++, lastSendMs. false neu leg khong ton tai hoac da ket thuc. */
    public synchronized boolean markSending(String cid, long nowMs) {
        Leg l = legOf(cid);
        if (l == null || !l.state.unresolved()) return false;
        l.state = LegState.SENDING;
        l.attempts++;
        l.lastSendMs = nowMs;
        l.tsUpdated = nowMs;
        persist(nowMs);
        return true;
    }

    public synchronized void markUnknown(String cid, String note, long nowMs) {
        Leg l = legOf(cid);
        if (l == null || !l.state.unresolved()) return;
        l.state = LegState.UNKNOWN;
        l.note = note == null ? "" : note;
        l.tsUpdated = nowMs;
        persist(nowMs);
    }

    /** Ghi orderId cua lenh chua ket thuc (NEW/PARTIALLY_FILLED) — giu trang thai cho lan tra sau. */
    public synchronized void noteOpen(String cid, long orderId, long nowMs) {
        Leg l = legOf(cid);
        if (l == null || !l.state.unresolved()) return;
        l.orderId = orderId;
        l.note = "open";
        l.tsUpdated = nowMs;
        persist(nowMs);
    }

    /** Xac nhan khop (execQty > 0); execQty <= 0 => huy. Idempotent: leg da ket thuc => false. */
    public synchronized boolean confirm(String cid, BigDecimal execQty, double avgPx, long orderId, long nowMs) {
        Leg l = legOf(cid);
        if (l == null || !l.state.unresolved()) return false;
        if (execQty == null || execQty.signum() <= 0 || !(avgPx > 0d)) {
            return cancel(cid, "exec=0", nowMs);
        }
        l.state = LegState.CONFIRMED;
        l.execQty = execQty;
        l.avgPx = avgPx;
        l.orderId = orderId;
        l.tsUpdated = nowMs;
        Cluster c = clusters.get(cidToSymbol.get(cid));
        if (c != null && avgPx > c.peak) c.peak = avgPx;
        persist(nowMs);
        return true;
    }

    /** Huy giu cho. Cum khong con leg song => xoa cum. Idempotent. */
    public synchronized boolean cancel(String cid, String reason, long nowMs) {
        Leg l = legOf(cid);
        if (l == null || !l.state.unresolved()) return false;
        l.state = LegState.CANCELLED;
        l.note = reason == null ? "" : reason;
        l.tsUpdated = nowMs;
        String sym = cidToSymbol.get(cid);
        Cluster c = clusters.get(sym);
        if (c != null && c.legCount() == 0) {
            clusters.remove(sym);
            for (Leg x : c.legs) cidToSymbol.remove(x.cid);
        }
        persist(nowMs);
        return true;
    }

    /** Danh dau cum dang dong (FLATTEN/time-stop/X14) voi cid lenh dong. */
    public synchronized boolean markClosing(String symbol, String closeCid, String reason, long nowMs) {
        Cluster c = clusters.get(symbol);
        if (c == null) return false;
        if (c.closeReason == null) c.closeSinceMs = nowMs;
        c.closeReason = reason == null ? "CLOSE" : reason;
        c.closeCid = closeCid;
        if (closeCid != null) {
            c.closeAttempts++;
            c.closeSentMs = nowMs;
        }
        persist(nowMs);
        return true;
    }

    /** Bo cid lenh dong (lenh chac chan khong khop) de lan sau gui lai — giu co dang dong. */
    public synchronized void clearCloseCid(String symbol, long nowMs) {
        Cluster c = clusters.get(symbol);
        if (c == null || c.closeCid == null) return;
        c.closeCid = null;
        persist(nowMs);
    }

    /** Cum da dong het tren san => xoa khoi so. */
    public synchronized boolean removeCluster(String symbol, String reason, long nowMs) {
        Cluster c = clusters.remove(symbol);
        if (c == null) return false;
        for (Leg x : c.legs) cidToSymbol.remove(x.cid);
        LOG.info("[C3-LIVE-BOOK] dong cum {} ly do={} legs={} qty={}", symbol, reason, c.legCount(), c.confirmedQty());
        persist(nowMs);
        return true;
    }

    /** (vong 2b trailing) ghi stop dang dat tren san cho cum. */
    public synchronized void setStop(String symbol, double stopPrice, String clientAlgoId, long nowMs) {
        Cluster c = clusters.get(symbol);
        if (c == null) return;
        c.stopPrice = stopPrice;
        c.stopClientAlgoId = clientAlgoId;
        c.armed = c.armed || clientAlgoId != null;
        persist(nowMs);
    }

    public synchronized void clearStop(String symbol, long nowMs) {
        Cluster c = clusters.get(symbol);
        if (c == null || c.stopClientAlgoId == null) return;
        c.stopClientAlgoId = null;
        persist(nowMs);
    }

    /** (vong 2b) cap nhat dinh gia cua cum. */
    public synchronized void updatePeak(String symbol, double px, long nowMs) {
        Cluster c = clusters.get(symbol);
        if (c == null || !(px > c.peak)) return;
        c.peak = px;
        persist(nowMs);
    }

    // ------------------------------------------------------------------ noi bo
    private Leg legOf(String cid) {
        String s = cid == null ? null : cidToSymbol.get(cid);
        if (s == null) return null;
        Cluster c = clusters.get(s);
        return c == null ? null : find(c, cid);
    }

    private static Leg find(Cluster c, String cid) {
        for (Leg l : c.legs) if (l.cid.equals(cid)) return l;
        return null;
    }

    // ------------------------------------------------------------------ persist
    private void persist(long nowMs) {
        if (file == null) return;
        JsonObject root = new JsonObject();
        root.addProperty("version", VERSION);
        root.addProperty("saved_ms", nowMs);
        root.addProperty("leverage", leverage);
        JsonArray arr = new JsonArray();
        for (Cluster c : clusters.values()) {
            JsonObject o = new JsonObject();
            o.addProperty("symbol", c.symbol);
            o.addProperty("ts_first_leg", c.tsFirstLeg);
            o.addProperty("peak", c.peak);
            o.addProperty("armed", c.armed);
            o.addProperty("stop_price", c.stopPrice);
            if (c.stopClientAlgoId != null) o.addProperty("stop_cid", c.stopClientAlgoId);
            if (c.closeCid != null) o.addProperty("close_cid", c.closeCid);
            if (c.closeReason != null) o.addProperty("close_reason", c.closeReason);
            o.addProperty("close_since_ms", c.closeSinceMs);
            o.addProperty("close_attempts", c.closeAttempts);
            o.addProperty("close_sent_ms", c.closeSentMs);
            JsonArray legs = new JsonArray();
            for (Leg l : c.legs) {
                JsonObject j = new JsonObject();
                j.addProperty("cid", l.cid);
                j.addProperty("leg_idx", l.legIdx);
                j.addProperty("bar_min", l.barMin);
                j.addProperty("level", l.level);
                j.addProperty("ref_px", l.refPx);
                j.addProperty("req_qty", l.reqQty.toPlainString());
                j.addProperty("reserved_margin", l.reservedMargin);
                j.addProperty("state", l.state.name());
                j.addProperty("exec_qty", l.execQty.toPlainString());
                j.addProperty("avg_px", l.avgPx);
                j.addProperty("order_id", l.orderId);
                j.addProperty("ts_created", l.tsCreated);
                j.addProperty("ts_updated", l.tsUpdated);
                j.addProperty("last_send_ms", l.lastSendMs);
                j.addProperty("attempts", l.attempts);
                j.addProperty("note", l.note);
                legs.add(j);
            }
            o.add("legs", legs);
            arr.add(o);
        }
        root.add("clusters", arr);
        try {
            File abs = file.getAbsoluteFile();
            File parent = abs.getParentFile();
            if (parent != null && !parent.exists() && !parent.mkdirs()) {
                throw new IOException("khong tao duoc thu muc " + parent);
            }
            File tmp = new File(abs.getPath() + ".tmp");
            Files.write(tmp.toPath(), root.toString().getBytes(StandardCharsets.UTF_8));
            Files.move(tmp.toPath(), abs.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
            if (!persistOk) LOG.warn("[C3-LIVE-BOOK] ghi lai duoc {} => het fail-closed persist", abs.getPath());
            persistOk = true;
        } catch (Exception e) {
            if (persistOk) {
                LOG.error("[C3-LIVE-BOOK] KHONG GHI DUOC {}: {} => FAIL-CLOSED (chan mo moi toi khi ghi lai duoc)",
                        file.getPath(), e.toString());
            }
            persistOk = false;
            unhealthyReason = "persist: " + e;
        }
    }

    private void load() {
        if (file == null || !file.exists()) {
            LOG.info("[C3-LIVE-BOOK] chua co file {} => so rong", file == null ? "-" : file.getPath());
            return;
        }
        try {
            String s = new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8);
            JsonObject root = JsonParser.parseString(s).getAsJsonObject();
            int v = root.get("version").getAsInt();
            if (v != VERSION) throw new IllegalStateException("version " + v + " != " + VERSION);
            Map<String, Cluster> tmp = new TreeMap<>();
            Map<String, String> tmpCid = new LinkedHashMap<>();
            for (JsonElement e : root.getAsJsonArray("clusters")) {
                JsonObject o = e.getAsJsonObject();
                Cluster c = new Cluster();
                c.symbol = o.get("symbol").getAsString();
                c.tsFirstLeg = o.get("ts_first_leg").getAsLong();
                c.peak = o.get("peak").getAsDouble();
                c.armed = o.get("armed").getAsBoolean();
                c.stopPrice = o.get("stop_price").getAsDouble();
                c.stopClientAlgoId = o.has("stop_cid") ? o.get("stop_cid").getAsString() : null;
                c.closeCid = o.has("close_cid") ? o.get("close_cid").getAsString() : null;
                c.closeReason = o.has("close_reason") ? o.get("close_reason").getAsString() : null;
                c.closeSinceMs = o.get("close_since_ms").getAsLong();
                c.closeAttempts = o.get("close_attempts").getAsInt();
                c.closeSentMs = o.get("close_sent_ms").getAsLong();
                for (JsonElement le : o.getAsJsonArray("legs")) {
                    JsonObject j = le.getAsJsonObject();
                    Leg l = new Leg();
                    l.cid = j.get("cid").getAsString();
                    l.legIdx = j.get("leg_idx").getAsInt();
                    l.barMin = j.get("bar_min").getAsLong();
                    l.level = j.get("level").getAsString();
                    l.refPx = j.get("ref_px").getAsDouble();
                    l.reqQty = new BigDecimal(j.get("req_qty").getAsString());
                    l.reservedMargin = j.get("reserved_margin").getAsDouble();
                    l.state = LegState.valueOf(j.get("state").getAsString());
                    l.execQty = new BigDecimal(j.get("exec_qty").getAsString());
                    l.avgPx = j.get("avg_px").getAsDouble();
                    l.orderId = j.get("order_id").getAsLong();
                    l.tsCreated = j.get("ts_created").getAsLong();
                    l.tsUpdated = j.get("ts_updated").getAsLong();
                    l.lastSendMs = j.get("last_send_ms").getAsLong();
                    l.attempts = j.get("attempts").getAsInt();
                    l.note = j.get("note").getAsString();
                    if (tmpCid.containsKey(l.cid)) throw new IllegalStateException("cid trung " + l.cid);
                    c.legs.add(l);
                    tmpCid.put(l.cid, c.symbol);
                }
                if (tmp.containsKey(c.symbol)) throw new IllegalStateException("symbol trung " + c.symbol);
                tmp.put(c.symbol, c);
            }
            clusters.putAll(tmp);
            cidToSymbol.putAll(tmpCid);
            int unresolved = 0;
            for (Cluster c : clusters.values()) for (Leg l : c.legs) if (l.state.unresolved()) unresolved++;
            LOG.warn("[C3-LIVE-BOOK] nap {} cum ({} leg chua giai quyet) tu {}", clusters.size(), unresolved, file.getPath());
        } catch (Exception e) {
            loadOk = false;
            unhealthyReason = "load: " + e;
            File bak = new File(file.getPath() + ".corrupt_" + System.currentTimeMillis());
            try {
                Files.copy(file.toPath(), bak.toPath(), StandardCopyOption.REPLACE_EXISTING);
            } catch (Exception ignore) {
                // sao luu loi khong doi ket luan fail-closed
            }
            LOG.error("[C3-LIVE-BOOK] FILE SO HONG {} ({}) => FAIL-CLOSED: chan mo moi; sao luu {}. Can reconcile/owner.",
                    file.getPath(), e.toString(), bak.getPath());
        }
    }
}
