package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.exec.C3LiveCids;
import com.binance.chuyennd.c3live.exit.TrailingStopManager;
import com.binance.chuyennd.c3live.fill.FillAccounting;
import com.binance.chuyennd.c3live.fill.UserStreamEvents;
import com.binance.chuyennd.c3live.filters.SymbolRules;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * [V12 C6 test] Chay SONG SONG so giay {@link ShadowBookC3} (singleton that) va duong THAT c3_live
 * ({@link LiveBookC3} + {@link TrailingStopManager} + {@link MockExchangeGateway} kich stop + {@link FillAccounting}) tren
 * CUNG chuoi gia phut, ghi su kien de so: arm (phut + priceSL), moi lan doi priceSL (bit float), time-stop, X14 hoan,
 * dong trailing (phut, gia khop). Gia khop that = gia phut stop kich tren san gia lap (stop round-down tick, doi khi
 * &gt;= 1 tick va &gt;= 0,1 %) — khac gia so giay (priceSL) la "chenh gia khop" duoc phep.
 */
public final class ExitParityEngine {

    /** Su kien 1 phia. */
    public static final class Ev {
        public final String type;
        public final long ts;
        public final float value;

        Ev(String type, long ts, float value) {
            this.type = type;
            this.ts = ts;
            this.value = value;
        }

        @Override
        public String toString() {
            return type + "@" + ts + "=" + value;
        }
    }

    public final MockExchangeGateway gw = new MockExchangeGateway();
    public final LiveBookC3 book = new LiveBookC3(null, 1.0);
    public final ShadowBookC3 paper;
    public final TrailingStopManager mgr;
    public final FillAccounting acct;
    public final AtomicLong now = new AtomicLong();
    public final Map<String, List<Ev>> paperEv = new TreeMap<>();
    public final Map<String, List<Ev>> liveEv = new TreeMap<>();
    public final Map<String, Float> liveExitPx = new LinkedHashMap<>();
    public final Map<String, Float> paperExitPx = new LinkedHashMap<>();
    public final List<String> closerCalls = new ArrayList<>();
    private final Map<String, Float> lastPaperSL = new LinkedHashMap<>();
    private final ExchangeInfo ei;
    private final SymbolRules rules;
    private int legSeq;

    public ExitParityEngine(ExchangeInfo ei, long t0, TrailingStopManager.TimeStopDefer defer) {
        this.ei = ei;
        this.now.set(t0);
        this.rules = new SymbolRules(ei, t0);
        gw.exchangeInfo = ei;
        ShadowBookC3.resetForTest();
        this.paper = ShadowBookC3.getInstance();
        this.acct = new FillAccounting(book, gw, new OrderAuditLog(OrderAuditLog.DRY_TAG, s -> { }), null, null, null,
                now::get, null);
        gw.wsSink = txt -> acct.dispatch(UserStreamEvents.parse(txt));
        this.mgr = TrailingStopManager.builder().gateway(gw).book(book).rules(() -> rules)
                .closer((s, r) -> closeLive(s, r))
                .defer(defer).armHook((s, t, n) -> { }).clock(now::get).safeRetryMs(0L)
                .events((type, sym, n, v, d) -> {
                    if ("ARM".equals(type) || "SL".equals(type) || "TIME_STOP".equals(type) || "DEFER".equals(type)) {
                        liveEv.computeIfAbsent(sym, k -> new ArrayList<>()).add(new Ev(type, n, (float) v));
                    }
                }).build();
    }

    /** Dong cum that (time-stop / immediate) = MARKET reduce-only tren san gia lap (qty = vi the san). */
    private int closeLive(String sym, String reason) {
        closerCalls.add(sym + ":" + reason);
        BigDecimal pos = gw.position(sym);
        if (pos.signum() <= 0) return 0;
        String cid = C3LiveCids.close(sym, Math.floorDiv(now.get(), 60_000L), closerCalls.size());
        book.markClosing(sym, cid, reason, now.get());
        gw.newMarketOrder(sym, Side.SELL, pos, cid, true);
        return 1;
    }

    /** 1 leg (mo cum hoac DCA) vao CA HAI so, cung gia/qty/ts. */
    public void leg(String sym, long ts, float px, float qty, int rank, Float pred) {
        now.set(ts);
        paper.openPos(sym, ts, px, qty, rank, pred);
        int legIdx = book.legCount(sym);
        String cid = C3LiveCids.entry(sym, Math.floorDiv(ts, 60_000L), legIdx) + (legSeq++ == 0 ? "" : "");
        BigDecimal q = new BigDecimal(Float.toString(qty));
        BigDecimal p = new BigDecimal(Float.toString(px));
        if (!book.reserve(sym, cid, legIdx, Math.floorDiv(ts, 60_000L), "TEST", px, q, q.doubleValue() * px, ts)) {
            throw new IllegalStateException("reserve that bai " + sym + " " + cid);
        }
        book.markSending(cid, ts);
        gw.setPrice(sym, p);
        OrderInfo o = gw.newMarketOrder(sym, Side.BUY, q, cid, false);
        book.confirm(cid, o.getExecutedQty(), o.getAvgPrice().doubleValue(), o.getOrderId(), ts);
        book.setMeta(sym, pred, rank, ts);
        lastPaperSL.remove(sym);
    }

    /** 1 phut: san kich stop (stop cua phut truoc) -> so giay tick -> nhip exit that. */
    public void minute(long ts, Map<String, Float> px) {
        now.set(ts);
        for (Map.Entry<String, Float> e : px.entrySet()) {
            BigDecimal p = new BigDecimal(Float.toString(e.getValue()));
            if (book.isHolding(e.getKey())) {
                boolean had = book.isHolding(e.getKey());
                gw.triggerStops(e.getKey(), p);
                if (had && !book.isHolding(e.getKey())) {
                    liveEv.computeIfAbsent(e.getKey(), k -> new ArrayList<>()).add(new Ev("TRAIL_EXIT", ts, e.getValue()));
                    liveExitPx.put(e.getKey(), e.getValue());
                }
            } else {
                gw.setPrice(e.getKey(), p);
            }
        }
        // so giay
        Map<String, ShadowBookC3.Cluster> before = new LinkedHashMap<>();
        for (String s : paper.openSymbols()) {
            ShadowBookC3.Cluster c = paper.cluster(s);
            if (c != null) before.put(s, c);
        }
        Map<String, Float> slBefore = new LinkedHashMap<>();
        for (Map.Entry<String, ShadowBookC3.Cluster> e : before.entrySet()) slBefore.put(e.getKey(), e.getValue().priceSL);
        paper.tick(px, ts);
        for (Map.Entry<String, ShadowBookC3.Cluster> e : before.entrySet()) {
            String s = e.getKey();
            ShadowBookC3.Cluster c = paper.cluster(s);
            List<Ev> l = paperEv.computeIfAbsent(s, k -> new ArrayList<>());
            Float prevSL = slBefore.get(s);
            if (c == null) {
                if (prevSL == null) {
                    l.add(new Ev("TIME_STOP", ts, px.get(s)));
                } else {
                    // ratchet trong cung nhip truoc khi cat: ghi SL cuoi
                    Float slAtClose = e.getValue().priceSL;
                    if (slAtClose != null && !slAtClose.equals(prevSL)) l.add(new Ev("SL", ts, slAtClose));
                    l.add(new Ev("TRAIL_EXIT", ts, slAtClose == null ? Float.NaN : slAtClose));
                    paperExitPx.put(s, slAtClose);
                }
                continue;
            }
            if (prevSL == null && c.priceSL != null) {
                l.add(new Ev("ARM", ts, c.priceSL));
            } else if (prevSL != null && c.priceSL != null && !prevSL.equals(c.priceSL)) {
                l.add(new Ev("SL", ts, c.priceSL));
            } else if (c.priceSL == null && ts - c.tsFirstLeg > LiveProfileC3.TIME_STOP_HOURS * 3_600_000L) {
                l.add(new Ev("DEFER", ts, px.get(s)));
            }
        }
        // that
        Map<String, Float> livePx = new LinkedHashMap<>();
        for (String s : book.ownedSymbols()) if (px.containsKey(s)) livePx.put(s, px.get(s));
        mgr.step(livePx);
    }

    /** Cum giay con mo (de leg DCA dung legCount giay). */
    public ShadowBookC3.Cluster paperCluster(String sym) {
        return paper.cluster(sym);
    }

    /**
     * So 2 phia. Quyet dinh = moi su kien ARM/SL/TIME_STOP/DEFER (loai, phut, gia tri float bit) TRUNG; TRAIL_EXIT:
     * cung co/khong, phut that >= phut giay (stop san tre <= 1 nguong doi). @return dong bao cao; mismatch dem rieng.
     */
    public static final class Compare {
        public int symbols, decisionEvents, decisionMismatch, trailExitBoth, trailExitSameMinute, trailExitLater,
                trailExitOnlyPaper, trailExitOnlyLive, timeStops, defers, arms, slMoves;
        public final List<String> mismatches = new ArrayList<>();
        public double sumExitPxDiffRel;

        @Override
        public String toString() {
            return "symbols=" + symbols + " decisionEvents=" + decisionEvents + " decisionMismatch=" + decisionMismatch
                    + " arms=" + arms + " slMoves=" + slMoves + " timeStops=" + timeStops + " defers=" + defers
                    + " trailExit(both=" + trailExitBoth + " sameMinute=" + trailExitSameMinute + " later=" + trailExitLater
                    + " onlyPaper=" + trailExitOnlyPaper + " onlyLive=" + trailExitOnlyLive + ") meanExitPxDiffRel="
                    + (trailExitBoth == 0 ? 0 : sumExitPxDiffRel / trailExitBoth);
        }
    }

    public Compare compare() {
        Compare cmp = new Compare();
        java.util.Set<String> syms = new java.util.TreeSet<>(paperEv.keySet());
        syms.addAll(liveEv.keySet());
        for (String s : syms) {
            cmp.symbols++;
            List<Ev> p = dec(paperEv.get(s));
            List<Ev> l = dec(liveEv.get(s));
            cmp.decisionEvents += p.size();
            for (Ev e : p) {
                if ("ARM".equals(e.type)) cmp.arms++;
                if ("SL".equals(e.type)) cmp.slMoves++;
                if ("TIME_STOP".equals(e.type)) cmp.timeStops++;
                if ("DEFER".equals(e.type)) cmp.defers++;
            }
            if (!sameEvents(p, l)) {
                cmp.decisionMismatch++;
                cmp.mismatches.add(s + " paper=" + head(p) + " live=" + head(l));
            }
            Ev pe = exit(paperEv.get(s));
            Ev le = exit(liveEv.get(s));
            if (pe != null && le != null) {
                cmp.trailExitBoth++;
                if (pe.ts == le.ts) cmp.trailExitSameMinute++;
                else if (le.ts > pe.ts) cmp.trailExitLater++;
                else cmp.mismatches.add(s + " live thoat TRUOC giay " + le + " vs " + pe);
                if (pe.value > 0f) cmp.sumExitPxDiffRel += (le.value - pe.value) / pe.value;
            } else if (pe != null) {
                cmp.trailExitOnlyPaper++;
                cmp.mismatches.add(s + " chi giay thoat trailing " + pe);
            } else if (le != null) {
                cmp.trailExitOnlyLive++;
                cmp.mismatches.add(s + " chi that thoat trailing " + le);
            }
        }
        return cmp;
    }

    private static List<Ev> dec(List<Ev> l) {
        List<Ev> out = new ArrayList<>();
        if (l == null) return out;
        for (Ev e : l) if (!"TRAIL_EXIT".equals(e.type)) out.add(e);
        return out;
    }

    private static Ev exit(List<Ev> l) {
        if (l == null) return null;
        for (Ev e : l) if ("TRAIL_EXIT".equals(e.type)) return e;
        return null;
    }

    private static boolean sameEvents(List<Ev> a, List<Ev> b) {
        if (a.size() != b.size()) return false;
        for (int i = 0; i < a.size(); i++) {
            Ev x = a.get(i), y = b.get(i);
            if (!x.type.equals(y.type) || x.ts != y.ts) return false;
            if (!"DEFER".equals(x.type) && !"TIME_STOP".equals(x.type)
                    && Float.floatToIntBits(x.value) != Float.floatToIntBits(y.value)) return false;
        }
        return true;
    }

    private static String head(List<Ev> l) {
        return l.size() <= 6 ? l.toString() : l.subList(0, 6) + "...(" + l.size() + ")";
    }
}
