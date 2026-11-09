package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.object.MarketLevelChange;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.function.Predicate;

/**
 * [V12 R4u BIG_DOWN-SEL 2026-11-09] Chon coin cho leg market-signal (BIG_DOWN / SMALL_*) cua c3 THEO DUNG quy uoc sim:
 * {@code SimulatorMarketLevelTicker1MStopLoss:368-380} = {@code MarketBigChangeDetector.getTopSymbolArray(n, tickers,
 * locked, extractPredict2Symbol(bins S1-map))}.
 *
 * <ul>
 *   <li>Thu tu = symbolPred = 1 - P(win) da quantile-map theo hang S1 (THAP = tot) — o live la
 *       {@code LiveBuildMap.Assigned.symbolPred} (cung gia tri GV-I cua vong selector).</li>
 *   <li>Bo coin dang giu ({@code locked}), coin khong co ticker khong duoc them nhung VAN tinh vao luot dung
 *       (chep NGUYEN cau truc vong lap sim: kiem {@code size >= n} sau moi phan tu duoc xet, ke ca {@code n <= 0}).</li>
 *   <li>KHONG loc maxThres (sim khong loc; truoc R4u live loc {@code tier1Score > maxThres} qua sortedCandidates).</li>
 *   <li>null/NaN bi bo (sim: bins bo NaN khi nap).</li>
 *   <li>KHAC sim co chu y: sim dung {@code TreeMap<Float, Short>} => 2 coin TRUNG symbolPred thi mat 1 (phu thuoc thu
 *       tu record bins). Live giu ca hai, xep (symbolPred, symbol) tang dan (tat dinh).</li>
 * </ul>
 */
public final class BigDownSelect {

    private BigDownSelect() {
    }

    /** Thu tu (symbolPred tang, symbol tang); bo null/NaN. */
    public static List<String> order(Map<String, Float> mapPred) {
        List<Map.Entry<String, Float>> es = new ArrayList<>();
        if (mapPred != null) {
            for (Map.Entry<String, Float> e : mapPred.entrySet()) {
                if (e.getKey() != null && e.getValue() != null && !e.getValue().isNaN()) es.add(e);
            }
        }
        es.sort((a, b) -> {
            int c = Float.compare(a.getValue(), b.getValue());
            return c != 0 ? c : a.getKey().compareTo(b.getKey());
        });
        List<String> out = new ArrayList<>(es.size());
        for (Map.Entry<String, Float> e : es) out.add(e.getKey());
        return out;
    }

    /** Ban String cua {@code MarketBigChangeDetector.getTopSymbolArray} tren {@link #order}. */
    public static List<String> select(Map<String, Float> mapPred, int n, Predicate<String> locked,
                                      Predicate<String> hasTicker) {
        List<String> symbols = new ArrayList<>();
        for (String s : order(mapPred)) {
            if (locked != null && locked.test(s)) continue;
            if (hasTicker == null || hasTicker.test(s)) symbols.add(s);
            if (symbols.size() >= n) break;
        }
        return symbols;
    }

    /**
     * [V12 R4u BIG_DOWN-GATE] sim KHONG goi entryGate cho leg BIG_DOWN (chi BIG_DOWN; SMALL_UP/SMALL_DOWN_15M van qua gate
     * nguong co so nhu cu). Live: bo gate chi khi profile c3 BAT.
     */
    public static boolean bypassGate(boolean profileC3On, MarketLevelChange level) {
        return profileC3On && level == MarketLevelChange.BIG_DOWN;
    }

    /** Guard van hanh con giu cho leg BIG_DOWN khi bo gate: seed buffer gate hong => REJECT (ly do); null = qua. */
    public static String bigDownGuard(boolean seedBlocked) {
        return seedBlocked ? "GATE-SEED HONG: chan vao lenh moi (van quan ly vi the/stop)" : null;
    }

    /** "SYM=0.123456,SYM2=..." cho dong log [BIG_DOWN-SEL]. */
    public static String describe(List<String> sel, Map<String, Float> mapPred) {
        StringBuilder sb = new StringBuilder();
        for (String s : sel) {
            if (sb.length() > 0) sb.append(',');
            Float v = mapPred == null ? null : mapPred.get(s);
            sb.append(s).append('=').append(v == null ? "null" : String.format(Locale.US, "%.6f", v));
        }
        return sb.length() == 0 ? "-" : sb.toString();
    }
}
