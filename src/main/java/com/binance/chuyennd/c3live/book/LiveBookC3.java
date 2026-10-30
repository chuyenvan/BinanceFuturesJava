package com.binance.chuyennd.c3live.book;

import com.binance.chuyennd.tradecore.selector.LiveDcaGridC3;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
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
 * tsFirstLeg, legCount, peak/armed/stopPrice/stopClientAlgoId (trailing C6), closeCid.
 *
 * <p>Giu cho margin DONG BO truoc khi gui lenh: {@link #reserve} ghi leg PENDING (margin du kien = notional/leverage)
 * va persist TRUOC khi lenh roi khoi JVM => U = {@link #marginUsed()} / equity tinh ca pending => 24 ung vien cung tick
 * thay nhau. Xac nhan ({@link #confirm}) / huy ({@link #cancel}) theo ket qua san.
 *
 * <p>Trang thai leg: PENDING (chua gui) -> SENDING (da gui >= 1 lan; ghi TRUOC khi gui) -> CONFIRMED | CANCELLED;
 * UNKNOWN = gui roi nhung khong biet san da nhan chua (timeout) — chi duoc gui lai SAU KHI queryOrder xac nhan khong co.
 * Ca 3 trang thai chua giai quyet deu tinh margin (bao thu) va khoa symbol (khoa xu ly persist qua restart).
 *
 * <p>[V12 vong 2b] them: trang thai trailing GIONG so giay ({@code peakRate} so voi VWAP entry, {@code priceSL} logic,
 * symbolPred/rank cua leg dau co gia tri — {@code ShadowBookC3.Cluster}); stop tren san (active / pending / mo coi);
 * phi + realizedPnl + fill dong (C7); "san thang" qty/gia (C9); moc doi chieu equity (anchor + tong da chot/phi/funding/
 * chuyen tien ke tu moc). Dong cum => 1 dong {@code c3live_ledger.csv} canh file so.
 *
 * <p>Persist JSON {@code run/c3live_book.json}, ghi atomic (tmp + ATOMIC_MOVE) sau MOI thay doi. File hong => sao luu
 * {@code .corrupt_<ms>} + {@link #healthy()} = false (fail-closed: chan mo moi). Ghi loi => healthy=false toi khi ghi lai duoc.
 * Truong moi cua vong 2b doc bang {@code has()} (file vong 2a van nap duoc). Thread-safe (moi ham synchronized).
 */
public final class LiveBookC3 {

    private static final Logger LOG = LoggerFactory.getLogger(LiveBookC3.class);
    public static final String DEFAULT_FILE = "run/c3live_book.json";
    public static final String LEDGER_NAME = "c3live_ledger.csv";
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
        /** [3j R2] true = avgPx la gia TAM (mark) vi ACK/stream/query/userTrades chua co gia that. */
        public final boolean pxProvisional;
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
            this.pxProvisional = l.pxProvisional;
            this.orderId = l.orderId;
            this.tsCreated = l.tsCreated;
            this.lastSendMs = l.lastSendMs;
            this.attempts = l.attempts;
            this.note = l.note;
        }

        @Override
        public String toString() {
            return symbol + "/" + cid + "/" + state + "/qty=" + reqQty + "/exec=" + execQty
                    + (pxProvisional ? "/px=tam" : "");
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
        /** [3j R2] con leg nao dang giu gia TAM (avgPx = mark) — moi tinh toan lo/stop phai dung gia XAU nhat. */
        public final boolean hasProvisional;
        public final BigDecimal provisionalQty;
        public final List<LegView> legs;
        // ---- vong 2b
        /** VWAP entry kieu FLOAT y het {@code ShadowBookC3.Cluster.avgEntry()} (dau vao trailing). */
        public final float avgEntryF;
        /** dinh lai (ty le so VWAP) — ratchet bam dinh nhu so giay; reset 0 khi DCA. */
        public final float peakRate;
        /** stop LOGIC (giong {@code priceSL} so giay); NaN = chua arm. */
        public final float priceSL;
        public final Float symbolPred;
        public final int rank;
        public final int stopSeq;
        public final String pendingStopCid;
        public final double pendingStopPrice;
        public final long pendingStopSentMs;
        public final boolean pendingStopQtyMode;
        public final boolean stopQtyMode;
        public final List<String> orphanStops;
        public final double commission;
        public final double realizedPnl;
        public final BigDecimal exitQty;
        public final double exitAvgPx;
        public final boolean exchangeOverride;

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
            BigDecimal pq = BigDecimal.ZERO;
            boolean prov = false;
            List<LegView> ls = new ArrayList<>();
            for (Leg l : c.legs) {
                LegView v = new LegView(c.symbol, l);
                ls.add(v);
                if (l.state == LegState.CONFIRMED && l.pxProvisional) {
                    prov = true;
                    pq = pq.add(l.execQty);
                }
            }
            this.legs = Collections.unmodifiableList(ls);
            this.hasProvisional = prov;
            this.provisionalQty = pq;
            this.avgEntryF = c.avgEntryF();
            this.peakRate = c.peakRate;
            this.priceSL = c.priceSL;
            this.symbolPred = c.symbolPred;
            this.rank = c.rank;
            this.stopSeq = c.stopSeq;
            this.pendingStopCid = c.pendingStopCid;
            this.pendingStopPrice = c.pendingStopPrice;
            this.pendingStopSentMs = c.pendingStopSentMs;
            this.pendingStopQtyMode = c.pendingStopQtyMode;
            this.stopQtyMode = c.stopQtyMode;
            this.orphanStops = Collections.unmodifiableList(new ArrayList<>(c.orphanStops));
            this.commission = c.commission;
            this.realizedPnl = c.realizedPnl;
            this.exitQty = c.exitQty;
            this.exitAvgPx = c.exitQty.signum() > 0 ? c.exitNotional / c.exitQty.doubleValue() : 0d;
            this.exchangeOverride = c.adjQty != null;
        }

        /** Da arm trailing (stop logic co gia tri). */
        public boolean trailArmed() {
            return !Float.isNaN(priceSL);
        }
    }

    /** Moc doi chieu equity (C9 hang gio). */
    public static final class AccountView {
        public final double anchorEquity;
        public final long anchorMs;
        public final double realized;
        public final double commission;
        public final double funding;
        public final double transfers;

        AccountView(LiveBookC3 b) {
            this.anchorEquity = b.anchorEquity;
            this.anchorMs = b.anchorMs;
            this.realized = b.realizedSinceAnchor;
            this.commission = b.commissionSinceAnchor;
            this.funding = b.fundingSinceAnchor;
            this.transfers = b.transferSinceAnchor;
        }

        public boolean anchored() {
            return !Double.isNaN(anchorEquity);
        }

        /** Equity so (chua tinh lai chua chot) = moc + da chot - phi + funding + chuyen tien. */
        public double bookEquityExUnrealized() {
            return anchorEquity + realized - commission + funding + transfers;
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
        boolean pxProvisional;
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
        // ---- vong 2b
        float peakRate = 0f;
        float priceSL = Float.NaN;
        Float symbolPred;
        int rank = -1;
        int stopSeq;
        String pendingStopCid;
        double pendingStopPrice;
        long pendingStopSentMs;
        boolean pendingStopQtyMode;
        boolean stopQtyMode;
        final List<String> orphanStops = new ArrayList<>();
        /** [V12 R4f MAJOR-L1] tradeId da ghi vao cum (stream "t" / userTrades "id") — chong ghi trung; persist. */
        final java.util.LinkedHashSet<Long> tradeIds = new java.util.LinkedHashSet<>();
        double commission;
        double realizedPnl;
        BigDecimal exitQty = BigDecimal.ZERO;
        double exitNotional;
        /** "San thang" (C9): qty/gia vi the tren san khi lech so; null = theo legs. */
        BigDecimal adjQty;
        double adjAvg;

        int legCount() {
            int n = 0;
            for (Leg l : legs) if (l.state != LegState.CANCELLED) n++;
            return n;
        }

        boolean hasUnresolved() {
            for (Leg l : legs) if (l.state.unresolved()) return true;
            return false;
        }

        BigDecimal legsQty() {
            BigDecimal q = BigDecimal.ZERO;
            for (Leg l : legs) if (l.state == LegState.CONFIRMED) q = q.add(l.execQty);
            return q;
        }

        BigDecimal confirmedQty() {
            return adjQty != null ? adjQty : legsQty();
        }

        double avgPrice() {
            if (adjQty != null) return adjAvg;
            double qty = 0d, notional = 0d;
            for (Leg l : legs) {
                if (l.state != LegState.CONFIRMED) continue;
                double q = l.execQty.doubleValue();
                qty += q;
                notional += q * l.avgPx;
            }
            return qty > 0d ? notional / qty : 0d;
        }

        /**
         * VWAP kieu so giay: sumEntryQty (double) += (double)entry_f * qty_f; qty (float) += qty_f; avg = (float)(sum/qty).
         * Cung thu tu cong leg => cung bit voi {@code ShadowBookC3.Cluster.avgEntry()} khi cung gia/qty.
         */
        float avgEntryF() {
            if (adjQty != null) return (float) adjAvg;
            double sum = 0d;
            float q = 0f;
            for (Leg l : legs) {
                if (l.state != LegState.CONFIRMED) continue;
                float e = (float) l.avgPx;
                float qq = l.execQty.floatValue();
                sum += (double) e * qq;
                q += qq;
            }
            return q > 0f ? (float) (sum / q) : 0f;
        }

        double confirmedMargin(double leverage) {
            if (adjQty != null) return adjQty.doubleValue() * adjAvg / leverage;
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
    // ---- vong 2b: doi chieu equity
    private double anchorEquity = Double.NaN;
    private long anchorMs;
    private double realizedSinceAnchor;
    private double commissionSinceAnchor;
    private double fundingSinceAnchor;
    private double transferSinceAnchor;

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

    /** [3j R2] Cac leg da CONFIRMED nhung con giu gia TAM (cho hieu chinh bang gia that). */
    public synchronized List<LegView> provisionalLegs() {
        List<LegView> out = new ArrayList<>();
        for (Cluster c : clusters.values()) {
            for (Leg l : c.legs) if (l.state == LegState.CONFIRMED && l.pxProvisional) out.add(new LegView(c.symbol, l));
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

    /** Tap clientAlgoId stop ma so dang tham chieu (active + pending + mo coi cho huy). */
    public synchronized Set<String> referencedStopCids() {
        Set<String> s = new TreeSet<>();
        for (Cluster c : clusters.values()) {
            if (c.stopClientAlgoId != null) s.add(c.stopClientAlgoId);
            if (c.pendingStopCid != null) s.add(c.pendingStopCid);
            s.addAll(c.orphanStops);
        }
        return s;
    }

    public synchronized AccountView account() {
        return new AccountView(this);
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

    /**
     * Xac nhan khop (execQty > 0, gia that > 0); execQty <= 0 => huy. Idempotent: leg da ket thuc => false.
     * [3j R1] execQty > 0 ma avgPx <= 0 KHONG duoc coi la "khong khop": giu leg chua giai quyet (return false) de nguoi goi
     * giai gia (stream/queryOrder/userTrades) hoac ghi gia TAM qua {@link #confirmProvisional}. Bug 10-28 (K4): ACK MARKET
     * {@code status=FILLED} khong co {@code avgPrice} => ban cu huy giu cho va xoa cum du vi the san CO THAT, khong stop.
     * [2b] leg DCA (legIdx > 0) khop => RESET trailing (peakRate=0, priceSL=NaN, armed=false) y het
     * {@code ShadowBookC3.Cluster.addLeg} (sim mergeOrder tao cum REQUEST moi); stop cu (neu co) do TrailingStopManager huy.
     */
    public synchronized boolean confirm(String cid, BigDecimal execQty, double avgPx, long orderId, long nowMs) {
        Leg l = legOf(cid);
        if (l == null || !l.state.unresolved()) return false;
        if (execQty == null || execQty.signum() <= 0) {
            return cancel(cid, "exec=0", nowMs);
        }
        if (!(avgPx > 0d)) {
            LOG.error("[C3-LIVE-BOOK] R1: {} execQty={} nhung avgPx={} => KHONG huy giu cho, giu leg cho gia that/gia tam",
                    cid, execQty.toPlainString(), avgPx);
            return false;
        }
        applyConfirmed(l, execQty, avgPx, orderId, false, nowMs);
        persist(nowMs);
        return true;
    }

    /**
     * [3j R2] Xac nhan khop khi CHUA co gia that: ghi DU qty voi gia TAM {@code provPx} (current mark) va co
     * {@code pxProvisional}. Dung lai khi co gia that qua {@link #correctPrice}. Chi nhan qty > 0 va gia tam > 0.
     */
    public synchronized boolean confirmProvisional(String cid, BigDecimal execQty, double provPx, long orderId, long nowMs) {
        Leg l = legOf(cid);
        if (l == null || !l.state.unresolved()) return false;
        if (execQty == null || execQty.signum() <= 0 || !(provPx > 0d)) return false;
        applyConfirmed(l, execQty, provPx, orderId, true, nowMs);
        persist(nowMs);
        return true;
    }

    private void applyConfirmed(Leg l, BigDecimal execQty, double px, long orderId, boolean prov, long nowMs) {
        l.state = LegState.CONFIRMED;
        l.execQty = execQty;
        l.avgPx = px;
        l.pxProvisional = prov;
        l.orderId = orderId;
        l.tsUpdated = nowMs;
        Cluster c = clusters.get(cidToSymbol.get(l.cid));
        if (c != null && px > c.peak) c.peak = px;
        if (c != null && l.legIdx > 0) {
            c.peakRate = 0f;
            c.priceSL = Float.NaN;
            c.armed = false;
            if (c.adjQty != null) {   // da "san thang": cong leg moi vao qty/gia san
                double q0 = c.adjQty.doubleValue();
                double q1 = execQty.doubleValue();
                c.adjAvg = (q0 * c.adjAvg + q1 * px) / (q0 + q1);
                c.adjQty = c.adjQty.add(execQty);
            }
        }
    }

    /**
     * [3j R2] Gia THAT den sau khi da ghi gia TAM: thay avgPx, bo co provisional. Moi gia tri dan xuat (VWAP cum, notional
     * vao, khoang cach stop, dong ledger luc dong cum) tinh lai tu avgPx nay. true = co sua (idempotent: da co gia that => false).
     */
    public synchronized boolean correctPrice(String cid, double realPx, long nowMs) {
        Leg l = legOf(cid);
        if (l == null || l.state != LegState.CONFIRMED || !l.pxProvisional) return false;
        if (!(realPx > 0d)) return false;
        double old = l.avgPx;
        l.avgPx = realPx;
        l.pxProvisional = false;
        l.tsUpdated = nowMs;
        Cluster c = clusters.get(cidToSymbol.get(cid));
        if (c != null) {
            if (realPx > c.peak) c.peak = realPx;
            if (c.adjQty != null) {
                double q0 = c.adjQty.doubleValue();
                double q = l.execQty.doubleValue();
                if (q0 > 0d && q > 0d && q0 >= q) c.adjAvg = (q0 * c.adjAvg - q * old + q * realPx) / q0;
            }
        }
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

    /**
     * [2f] Moc so XOA cum symbol gan nhat trong JVM nay (chi trong bo nho; restart => quen). Long.MIN_VALUE neu chua tung.
     * Reconciler/OwnStopGuard dung de phan biet vi the "so DA BIET vua chot" (chan rieng symbol) voi vi the la (chan toan he).
     */
    public synchronized long lastRemovedMs(String symbol) {
        Long t = removedAtMs.get(symbol);
        return t == null ? Long.MIN_VALUE : t;
    }

    private final Map<String, Long> removedAtMs = new TreeMap<>();
    /** [V12 R4f MAJOR-L1] "SYM:tradeId" cua cum DA DONG (khop toi muon khong ghi lai); toi da RECENT_TRADES_MAX, persist. */
    private final java.util.LinkedHashSet<String> recentTrades = new java.util.LinkedHashSet<>();
    static final int RECENT_TRADES_MAX = 5000;

    /** Cum da dong het tren san => xoa khoi so (+ 1 dong ledger). */
    public synchronized boolean removeCluster(String symbol, String reason, long nowMs) {
        Cluster c = clusters.remove(symbol);
        if (c == null) return false;
        removedAtMs.put(symbol, nowMs);
        for (Long t : c.tradeIds) rememberTrade(symbol, t);   // [V12 R4f]
        for (Leg x : c.legs) cidToSymbol.remove(x.cid);
        LOG.info("[C3-LIVE-BOOK] dong cum {} ly do={} legs={} qty={} avg={} exitQty={} exitAvg={} realized={} phi={}",
                symbol, reason, c.legCount(), c.confirmedQty(), c.avgPrice(), c.exitQty,
                c.exitQty.signum() > 0 ? c.exitNotional / c.exitQty.doubleValue() : 0d, c.realizedPnl, c.commission);
        appendLedger(c, reason, nowMs);
        persist(nowMs);
        return true;
    }

    /** (trailing) ghi stop dang dat tren san cho cum. */
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

    /** cap nhat dinh gia cua cum. */
    public synchronized void updatePeak(String symbol, double px, long nowMs) {
        Cluster c = clusters.get(symbol);
        if (c == null || !(px > c.peak)) return;
        c.peak = px;
        persist(nowMs);
    }

    // ------------------------------------------------------------------ [2b] trailing / stop
    /** symbolPred / rank cua leg CO GIA TRI dau tien (giong so giay). true neu doi. */
    public synchronized boolean setMeta(String symbol, Float symbolPred, int rank, long nowMs) {
        Cluster c = clusters.get(symbol);
        if (c == null) return false;
        boolean ch = false;
        if (c.symbolPred == null && symbolPred != null) {
            c.symbolPred = symbolPred;
            ch = true;
        }
        if (c.rank < 0 && rank >= 0) {
            c.rank = rank;
            ch = true;
        }
        if (ch) persist(nowMs);
        return ch;
    }

    /**
     * Trang thai trailing (peakRate, priceSL logic; NaN = chua arm). Chi persist khi doi. priceSL co gia tri => armed.
     */
    public synchronized void setTrail(String symbol, float peakRate, float priceSL, long nowMs) {
        Cluster c = clusters.get(symbol);
        if (c == null) return;
        boolean same = Float.floatToIntBits(c.peakRate) == Float.floatToIntBits(peakRate)
                && Float.floatToIntBits(c.priceSL) == Float.floatToIntBits(priceSL);
        if (same) return;
        c.peakRate = peakRate;
        c.priceSL = priceSL;
        c.armed = !Float.isNaN(priceSL);
        persist(nowMs);
    }

    /** Cap so thu tu stop moi (stopSeq++ persist TRUOC khi gui). -1 neu khong co cum. */
    public synchronized int nextStopSeq(String symbol, long nowMs) {
        Cluster c = clusters.get(symbol);
        if (c == null) return -1;
        c.stopSeq++;
        persist(nowMs);
        return c.stopSeq;
    }

    /** Ghi stop SAP gui (persist TRUOC khi gui => restart biet de tra). */
    public synchronized boolean setPendingStop(String symbol, String cid, double price, boolean qtyMode, long nowMs) {
        Cluster c = clusters.get(symbol);
        if (c == null) return false;
        c.pendingStopCid = cid;
        c.pendingStopPrice = price;
        c.pendingStopSentMs = nowMs;
        c.pendingStopQtyMode = qtyMode;
        persist(nowMs);
        return true;
    }

    public synchronized void clearPendingStop(String symbol, long nowMs) {
        Cluster c = clusters.get(symbol);
        if (c == null || c.pendingStopCid == null) return;
        c.pendingStopCid = null;
        c.pendingStopPrice = 0d;
        c.pendingStopSentMs = 0L;
        c.pendingStopQtyMode = false;
        persist(nowMs);
    }

    /**
     * Stop pending da len san => thanh stop active. Stop active cu (neu co) chuyen sang danh sach MO COI (cho huy).
     * @return cid stop cu (null neu khong co)
     */
    public synchronized String promotePendingStop(String symbol, long nowMs) {
        Cluster c = clusters.get(symbol);
        if (c == null || c.pendingStopCid == null) return null;
        String old = c.stopClientAlgoId;
        if (old != null && !old.equals(c.pendingStopCid) && !c.orphanStops.contains(old)) c.orphanStops.add(old);
        c.stopClientAlgoId = c.pendingStopCid;
        c.stopPrice = c.pendingStopPrice;
        c.stopQtyMode = c.pendingStopQtyMode;
        c.pendingStopCid = null;
        c.pendingStopPrice = 0d;
        c.pendingStopSentMs = 0L;
        c.pendingStopQtyMode = false;
        persist(nowMs);
        return old;
    }

    /** Huy stop active khoi so (vd DCA reset arm): chuyen sang mo coi cho huy tren san. */
    public synchronized String retireActiveStop(String symbol, long nowMs) {
        Cluster c = clusters.get(symbol);
        if (c == null || c.stopClientAlgoId == null) return null;
        String old = c.stopClientAlgoId;
        if (!c.orphanStops.contains(old)) c.orphanStops.add(old);
        c.stopClientAlgoId = null;
        c.stopPrice = 0d;
        c.stopQtyMode = false;
        persist(nowMs);
        return old;
    }

    public synchronized void removeOrphanStop(String symbol, String cid, long nowMs) {
        Cluster c = clusters.get(symbol);
        if (c == null || !c.orphanStops.remove(cid)) return;
        persist(nowMs);
    }

    // ------------------------------------------------------------------ [V12 R4f MAJOR-L1] chong ghi trung khop
    private boolean tradeSeen(String sym, long tid) {
        Cluster c = clusters.get(sym);
        return (c != null && c.tradeIds.contains(tid)) || recentTrades.contains(sym + ":" + tid);
    }

    private void rememberTrade(String sym, long tid) {
        recentTrades.add(sym + ":" + tid);
        java.util.Iterator<String> it = recentTrades.iterator();
        while (recentTrades.size() > RECENT_TRADES_MAX && it.hasNext()) {
            it.next();
            it.remove();
        }
    }

    public synchronized boolean tradeSeenForTest(String sym, long tid) {
        return tradeSeen(sym, tid);
    }

    /**
     * Phi + realized cua 1 khop STREAM co tradeId. Da ghi (vd khoi phuc REST toi truoc) => false, KHONG ghi lai. Cum KHONG con:
     * khop moi (tradeId chua thay) van vao tong ke tu moc (khop that toi muon); tradeId &lt;= 0 ma cum khong con => chi phi,
     * KHONG realized (khong dedup duoc). true = khop moi da ghi.
     */
    public synchronized boolean addFillCosts(String symbol, long tradeId, double commissionUsd, double realizedPnl, long nowMs) {
        if (symbol != null && tradeId > 0) {
            if (tradeSeen(symbol, tradeId)) return false;
            Cluster c = clusters.get(symbol);
            if (c != null) c.tradeIds.add(tradeId);
            else rememberTrade(symbol, tradeId);
            persist(nowMs);
        } else if (symbol == null || !clusters.containsKey(symbol)) {
            realizedPnl = 0d;
        }
        addFillCosts(symbol, commissionUsd, realizedPnl, nowMs);
        return true;
    }

    /**
     * [V12 R4f MAJOR-L1] Khop THOAT khoi phuc qua REST (userTrades) — goi duoi khoa FillAccounting (cung khoa stream). Cum khong
     * con / tradeId da ghi / khong co tradeId => false, KHONG ghi gi (khong PnL trung). true = da ghi exit + phi + realized.
     */
    public synchronized boolean addRecoveredExit(String symbol, long tradeId, BigDecimal qty, double px, double commissionUsd,
                                                 double realizedPnl, long nowMs) {
        Cluster c = clusters.get(symbol);
        if (c == null || tradeId <= 0 || qty == null || qty.signum() <= 0 || !(px > 0d)) return false;
        if (tradeSeen(symbol, tradeId)) return false;
        c.tradeIds.add(tradeId);
        c.exitQty = c.exitQty.add(qty);
        c.exitNotional += qty.doubleValue() * px;
        if (Double.isFinite(commissionUsd)) {
            c.commission += commissionUsd;
            commissionSinceAnchor += commissionUsd;
        }
        if (Double.isFinite(realizedPnl)) {
            c.realizedPnl += realizedPnl;
            realizedSinceAnchor += realizedPnl;
        }
        persist(nowMs);
        return true;
    }

    // ------------------------------------------------------------------ [2b] ke toan fill (C7)
    /** Phi (USD, duong = mat) + realizedPnl cua 1 fill; cum khong con => van cong vao tong ke tu moc. */
    public synchronized void addFillCosts(String symbol, double commissionUsd, double realizedPnl, long nowMs) {
        if (!(Double.isFinite(commissionUsd)) || !(Double.isFinite(realizedPnl))) return;
        if (commissionUsd == 0d && realizedPnl == 0d) return;
        Cluster c = symbol == null ? null : clusters.get(symbol);
        if (c != null) {
            c.commission += commissionUsd;
            c.realizedPnl += realizedPnl;
        }
        commissionSinceAnchor += commissionUsd;
        realizedSinceAnchor += realizedPnl;
        persist(nowMs);
    }

    /** 1 fill BAN (dong) cua cum. */
    public synchronized void addExitFill(String symbol, BigDecimal qty, double px, long nowMs) {
        Cluster c = clusters.get(symbol);
        if (c == null || qty == null || qty.signum() <= 0 || !(px > 0d)) return;
        c.exitQty = c.exitQty.add(qty);
        c.exitNotional += qty.doubleValue() * px;
        persist(nowMs);
    }

    /** C9 "san thang": dat qty/gia vi the theo san (qty <= 0 khong hop le => bo qua). */
    public synchronized boolean overrideFromExchange(String symbol, BigDecimal qty, double entryPx, long nowMs) {
        Cluster c = clusters.get(symbol);
        if (c == null || qty == null || qty.signum() <= 0 || !(entryPx > 0d)) return false;
        c.adjQty = qty;
        c.adjAvg = entryPx;
        // [3j] gia vao theo SAN la gia THAT => leg nao con co "gia TAM" thi bo co (khong hieu chinh lung tung nua)
        for (Leg l : c.legs) l.pxProvisional = false;
        persist(nowMs);
        return true;
    }

    public synchronized void addFunding(double usd, long nowMs) {
        if (!Double.isFinite(usd) || usd == 0d) return;
        fundingSinceAnchor += usd;
        persist(nowMs);
    }

    public synchronized void addTransfer(double usd, long nowMs) {
        if (!Double.isFinite(usd) || usd == 0d) return;
        transferSinceAnchor += usd;
        persist(nowMs);
    }

    /** Dat moc doi chieu equity moi (reset tong ke tu moc). */
    public synchronized void anchor(double equityExUnrealized, long nowMs) {
        anchorEquity = equityExUnrealized;
        anchorMs = nowMs;
        realizedSinceAnchor = 0d;
        commissionSinceAnchor = 0d;
        fundingSinceAnchor = 0d;
        transferSinceAnchor = 0d;
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

    private void appendLedger(Cluster c, String reason, long nowMs) {
        if (file == null) return;
        File f = new File(file.getAbsoluteFile().getParentFile(), LEDGER_NAME);
        boolean header = !f.exists();
        try (PrintWriter w = new PrintWriter(new FileWriter(f, true))) {
            if (header) {
                w.println("sym,ts_first_leg,legs,qty,avg_entry,exit_qty,exit_avg,realized_pnl,commission,reason,ts_close,"
                        + "symbol_pred,rank,armed,price_sl");
            }
            double exitAvg = c.exitQty.signum() > 0 ? c.exitNotional / c.exitQty.doubleValue() : 0d;
            w.printf("%s,%d,%d,%s,%s,%s,%s,%s,%s,%s,%d,%s,%d,%s,%s%n", c.symbol, c.tsFirstLeg, c.legCount(),
                    c.confirmedQty().toPlainString(), Double.toString(c.avgPrice()), c.exitQty.toPlainString(),
                    Double.toString(exitAvg), Double.toString(c.realizedPnl), Double.toString(c.commission),
                    reason == null ? "" : reason.replace(',', ';'), nowMs,
                    c.symbolPred == null ? "" : Float.toString(c.symbolPred), c.rank, c.armed,
                    Float.isNaN(c.priceSL) ? "" : Float.toString(c.priceSL));
        } catch (IOException e) {
            LOG.error("[C3-LIVE-BOOK] khong ghi duoc ledger {}: {}", f.getPath(), e.toString());
        }
    }

    // ------------------------------------------------------------------ persist
    private void persist(long nowMs) {
        if (file == null) return;
        JsonObject root = new JsonObject();
        root.addProperty("version", VERSION);
        root.addProperty("saved_ms", nowMs);
        root.addProperty("leverage", leverage);
        JsonObject acct = new JsonObject();
        if (!Double.isNaN(anchorEquity)) acct.addProperty("anchor_equity", anchorEquity);
        acct.addProperty("anchor_ms", anchorMs);
        acct.addProperty("realized", realizedSinceAnchor);
        acct.addProperty("commission", commissionSinceAnchor);
        acct.addProperty("funding", fundingSinceAnchor);
        acct.addProperty("transfers", transferSinceAnchor);
        root.add("account", acct);
        JsonArray rtr = new JsonArray();   // [V12 R4f]
        for (String x : recentTrades) rtr.add(x);
        root.add("recent_trade_ids", rtr);
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
            // ---- 2b (float luu bang bit de khoi phuc 100 %)
            o.addProperty("peak_rate_bits", Float.floatToIntBits(c.peakRate));
            o.addProperty("price_sl_bits", Float.floatToIntBits(c.priceSL));
            if (c.symbolPred != null) o.addProperty("symbol_pred_bits", Float.floatToIntBits(c.symbolPred));
            o.addProperty("rank", c.rank);
            o.addProperty("stop_seq", c.stopSeq);
            o.addProperty("stop_qty_mode", c.stopQtyMode);
            if (c.pendingStopCid != null) {
                o.addProperty("pending_stop_cid", c.pendingStopCid);
                o.addProperty("pending_stop_price", c.pendingStopPrice);
                o.addProperty("pending_stop_sent_ms", c.pendingStopSentMs);
                o.addProperty("pending_stop_qty_mode", c.pendingStopQtyMode);
            }
            JsonArray orph = new JsonArray();
            for (String s : c.orphanStops) orph.add(s);
            o.add("orphan_stops", orph);
            JsonArray tids = new JsonArray();   // [V12 R4f]
            for (Long t : c.tradeIds) tids.add(t);
            o.add("trade_ids", tids);
            o.addProperty("commission", c.commission);
            o.addProperty("realized_pnl", c.realizedPnl);
            o.addProperty("exit_qty", c.exitQty.toPlainString());
            o.addProperty("exit_notional", c.exitNotional);
            if (c.adjQty != null) {
                o.addProperty("adj_qty", c.adjQty.toPlainString());
                o.addProperty("adj_avg", c.adjAvg);
            }
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
                j.addProperty("px_provisional", l.pxProvisional);
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
                if (o.has("peak_rate_bits")) c.peakRate = Float.intBitsToFloat(o.get("peak_rate_bits").getAsInt());
                if (o.has("price_sl_bits")) c.priceSL = Float.intBitsToFloat(o.get("price_sl_bits").getAsInt());
                if (o.has("symbol_pred_bits")) c.symbolPred = Float.intBitsToFloat(o.get("symbol_pred_bits").getAsInt());
                if (o.has("rank")) c.rank = o.get("rank").getAsInt();
                if (o.has("stop_seq")) c.stopSeq = o.get("stop_seq").getAsInt();
                if (o.has("stop_qty_mode")) c.stopQtyMode = o.get("stop_qty_mode").getAsBoolean();
                if (o.has("pending_stop_cid")) {
                    c.pendingStopCid = o.get("pending_stop_cid").getAsString();
                    c.pendingStopPrice = o.get("pending_stop_price").getAsDouble();
                    c.pendingStopSentMs = o.get("pending_stop_sent_ms").getAsLong();
                    c.pendingStopQtyMode = o.has("pending_stop_qty_mode") && o.get("pending_stop_qty_mode").getAsBoolean();
                }
                if (o.has("orphan_stops")) for (JsonElement x : o.getAsJsonArray("orphan_stops")) c.orphanStops.add(x.getAsString());
                if (o.has("trade_ids")) for (JsonElement x : o.getAsJsonArray("trade_ids")) c.tradeIds.add(x.getAsLong());
                if (o.has("commission")) c.commission = o.get("commission").getAsDouble();
                if (o.has("realized_pnl")) c.realizedPnl = o.get("realized_pnl").getAsDouble();
                if (o.has("exit_qty")) c.exitQty = new BigDecimal(o.get("exit_qty").getAsString());
                if (o.has("exit_notional")) c.exitNotional = o.get("exit_notional").getAsDouble();
                if (o.has("adj_qty")) {
                    c.adjQty = new BigDecimal(o.get("adj_qty").getAsString());
                    c.adjAvg = o.get("adj_avg").getAsDouble();
                }
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
                    l.pxProvisional = j.has("px_provisional") && j.get("px_provisional").getAsBoolean();
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
            double aEq = Double.NaN;
            long aMs = 0L;
            double r = 0d, cm = 0d, fu = 0d, tr = 0d;
            if (root.has("recent_trade_ids")) {
                for (JsonElement x : root.getAsJsonArray("recent_trade_ids")) recentTrades.add(x.getAsString());
            }
            if (root.has("account")) {
                JsonObject a = root.getAsJsonObject("account");
                if (a.has("anchor_equity")) aEq = a.get("anchor_equity").getAsDouble();
                if (a.has("anchor_ms")) aMs = a.get("anchor_ms").getAsLong();
                if (a.has("realized")) r = a.get("realized").getAsDouble();
                if (a.has("commission")) cm = a.get("commission").getAsDouble();
                if (a.has("funding")) fu = a.get("funding").getAsDouble();
                if (a.has("transfers")) tr = a.get("transfers").getAsDouble();
            }
            clusters.putAll(tmp);
            cidToSymbol.putAll(tmpCid);
            anchorEquity = aEq;
            anchorMs = aMs;
            realizedSinceAnchor = r;
            commissionSinceAnchor = cm;
            fundingSinceAnchor = fu;
            transferSinceAnchor = tr;
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
