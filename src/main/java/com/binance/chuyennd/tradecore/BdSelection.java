package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * [BD-SEL 2026-09-16] docs/prereg/PREREG_SEL_BIGDOWN.md — doi cach chon 2 coin cua leg BIG_DOWN
 * theo drop 1-phut causal thay vi pNoPump (getTopSymbolArray GIU NGUYEN, khong sua).
 *
 * <p>drop_i(t) = {@code Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen)}
 * (am = dang rot) — cung cong thuc {@code MarketBigChangeDetector.calMarketData} dung cho
 * tung coin. Universe = {@code predict2Symbol} (TreeMap pNoPump tang), skip {@code symbolLocked},
 * {@code symbol2Ticker[id] != null} — GIONG HET bo loc cua {@code getTopSymbolArray}.
 *
 * <p>Mode:
 * <ul>
 *   <li>{@code drop}     — 2 coin co drop AM NHAT (rot sau nhat).</li>
 *   <li>{@code mix}      — 2 coin co tong hang nho nhat: rankP (pNoPump tang) + rankD (drop am truoc).</li>
 *   <li>{@code drop_top8}— shortlist pNoPump top-{@link #TOPK}, roi chon 2 coin rot sau nhat trong do.</li>
 *   <li>{@code off}      — {@link #ACTIVE}=false, khong dung (parity byte-identical).</li>
 * </ul>
 *
 * <p>Tie-break deterministic: moi phep sap xep dung khoa phu {@code symbolId} (tang) de pha hoa.
 * Chi doi thu tu xep hang TRONG universe, van chon toi da 2 coin/tick.
 */
public final class BdSelection {
    /** Che do da chuan hoa (off|drop|mix|drop_top8). */
    public static final String MODE = Configs.BD_SEL_MODE.trim().toLowerCase();
    /** true khi mode != off. */
    public static final boolean ACTIVE = !"off".equals(MODE);
    /** shortlist size cho drop_top8 (default 8). */
    public static final int TOPK = Configs.BD_SEL_TOPK > 0 ? Configs.BD_SEL_TOPK : 8;

    private BdSelection() {
    }

    private static final class Cand {
        final short id;
        final float pNoPump;
        final float drop;

        Cand(short id, float pNoPump, float drop) {
            this.id = id;
            this.pNoPump = pNoPump;
            this.drop = drop;
        }
    }

    private static final Comparator<Cand> BY_P = (a, b) -> {
        int c = Float.compare(a.pNoPump, b.pNoPump);
        return c != 0 ? c : Short.compare(a.id, b.id);
    };

    private static final Comparator<Cand> BY_DROP = (a, b) -> {
        int c = Float.compare(a.drop, b.drop);
        return c != 0 ? c : Short.compare(a.id, b.id);
    };

    /**
     * Chon toi da {@code period} coin cho leg BIG_DOWN theo mode. Tra RONG khi mode=off.
     *
     * @param period           {@code numberOrder} (= 2 cho BIG_DOWN).
     * @param symbol2Ticker    mang ticker theo symbolId tai phut t (causal).
     * @param symbolLocked     cac id dang co vi the (skip).
     * @param predict2Symbol   TreeMap pNoPump-&gt;symbolId (universe cua selector).
     */
    public static Set<Short> select(int period, KlineObjectSimple[] symbol2Ticker,
                                    Set<Short> symbolLocked, TreeMap<Float, Short> predict2Symbol) {
        Set<Short> out = new HashSet<>();
        if (!ACTIVE || period <= 0) return out;
        if (predict2Symbol == null || predict2Symbol.isEmpty()) return out;
        if (symbol2Ticker == null) return out;

        List<Cand> cands = new ArrayList<>(predict2Symbol.size());
        for (Map.Entry<Float, Short> e : predict2Symbol.entrySet()) {
            Short id = e.getValue();
            if (id == null) continue;
            if (symbolLocked != null && symbolLocked.contains(id)) continue;
            KlineObjectSimple t = symbol2Ticker[id];
            if (t == null) continue;
            cands.add(new Cand(id, e.getKey(), Utils.rateOf2Double(t.priceClose, t.priceOpen)));
        }
        if (cands.isEmpty()) return out;

        if ("drop".equals(MODE)) {
            cands.sort(BY_DROP);
        } else if ("mix".equals(MODE)) {
            List<Cand> byP = new ArrayList<>(cands);
            byP.sort(BY_P);
            Map<Short, Integer> rankP = new HashMap<>();
            for (int i = 0; i < byP.size(); i++) rankP.put(byP.get(i).id, i + 1);

            List<Cand> byD = new ArrayList<>(cands);
            byD.sort(BY_DROP);
            Map<Short, Integer> rankD = new HashMap<>();
            for (int i = 0; i < byD.size(); i++) rankD.put(byD.get(i).id, i + 1);

            cands.sort((a, b) -> {
                int c = Integer.compare(rankP.get(a.id) + rankD.get(a.id),
                        rankP.get(b.id) + rankD.get(b.id));
                return c != 0 ? c : Short.compare(a.id, b.id);
            });
        } else if ("drop_top8".equals(MODE)) {
            List<Cand> byP = new ArrayList<>(cands);
            byP.sort(BY_P);
            int k = Math.min(TOPK, byP.size());
            List<Cand> shortlist = new ArrayList<>(byP.subList(0, k));
            shortlist.sort(BY_DROP);
            cands = shortlist;
        } else {
            // mode khong biet -> khong doi (an toan, khong duoc xay ra voi cac mode da chot).
            return out;
        }

        for (int i = 0; i < cands.size() && out.size() < period; i++) {
            out.add(cands.get(i).id);
        }
        return out;
    }
}
