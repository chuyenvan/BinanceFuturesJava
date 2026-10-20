package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.tradecore.Cfg;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * [V11 2026-10-20] docs/plan/V11_COLLECTOR_SETTLE.md — pool xep hang TAT DINH, KHONG mat coin trung score.
 *
 * <p>Truoc: {@code TreeMap<Float,String>.put(score, sym)} => coin trung score de nhau (S1 mat median 9 coin/phut),
 * coin con lai phu thuoc thu tu HashMap. Nay (cong {@code LIVE_RANK_TIEBREAK=symbol}, mac dinh {@code legacy}):
 * thu tu = (score tang, symbol tang) — CUNG quy uoc rank("first") tren danh sach symbol da sort cua
 * {@code build_map.py}/{@code s1_off.py}. Giu kieu {@code TreeMap<Float,String>} cho code phia sau: khoa trung duoc day
 * len {@link Math#nextUp(float)} cua khoa truoc (lech vai ulp, thu tu tang ngat).
 */
public final class TieSafeRank {

    public static final String KEY = "LIVE_RANK_TIEBREAK";

    private TieSafeRank() {
    }

    public static boolean on() {
        return "symbol".equalsIgnoreCase(Cfg.getOr(KEY, "legacy").trim());
    }

    /** Pool (score tang, symbol tang); bo null/NaN; khoa tang ngat. */
    public static TreeMap<Float, String> build(Map<String, Float> scores) {
        List<Map.Entry<String, Float>> l = new ArrayList<>();
        if (scores != null) {
            for (Map.Entry<String, Float> e : scores.entrySet()) {
                Float v = e.getValue();
                if (e.getKey() != null && v != null && !v.isNaN()) l.add(e);
            }
        }
        l.sort((a, b) -> {
            int c = Float.compare(a.getValue(), b.getValue());
            return c != 0 ? c : a.getKey().compareTo(b.getKey());
        });
        TreeMap<Float, String> out = new TreeMap<>();
        boolean first = true;
        float prev = 0f;
        for (Map.Entry<String, Float> e : l) {
            float k = e.getValue();
            if (!first && Float.compare(k, prev) <= 0) k = Math.nextUp(prev);
            out.put(k, e.getKey());
            prev = k;
            first = false;
        }
        return out;
    }

    /** So coin ma duong legacy (TreeMap theo score) se lam mat (= tong so diem trung - so gia tri phan biet). */
    public static int lostInLegacy(Map<String, Float> scores) {
        if (scores == null) return 0;
        Set<Float> seen = new HashSet<>();
        int n = 0;
        for (Float v : scores.values()) {
            if (v == null || v.isNaN()) continue;
            n++;
            seen.add(v);
        }
        return n - seen.size();
    }
}
