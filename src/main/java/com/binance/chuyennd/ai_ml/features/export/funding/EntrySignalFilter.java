package com.binance.chuyennd.ai_ml.features.export.funding;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.HashSet;

/**
 * ENTRY SIGNAL FILTER — HAM LOC TIN HIEU VAO LENH, DUNG CHUNG cho TAT CA:
 *   train (export feature), backtest, hpo, wfo, live.
 *
 * <p><b>QUAN TRONG — 1 NGUON CHAN LY DUY NHAT.</b> Moi noi quyet dinh "co xet coin nay
 * tai moc t khong" PHAI goi {@link #selectCoins}. KHONG hardcode logic loc o cho khac.
 * Doi tham so ben duoi = PHAI re-export toan bo + retrain toan bo model (train/backtest/live
 * se lech phan bo neu khong dong bo). Da do da-giai-doan (TASK filter, 2026-06-18):
 *   - top-10% cross-sectional |rate30m|: %giu on dinh ~6-10% moi regime (crash/bull/sideway),
 *     nguong tu co gian (P90 dao dong 0.83%-2.48% qua cac giai doan) -> dung adaptive.
 *   - vol-avg-30m >= 2000 USDT: chi de gat coin rac thanh khoan thap truoc khi xep hang.
 *
 * <p><b>Cach hoat dong (cross-sectional tai MOI moc t):</b>
 * <ol>
 *   <li>Tang 1 (volume): chi giu coin co volume trung binh 30m >= {@link #VOL_AVG_MIN_USDT}.</li>
 *   <li>Tang 2 (bien dong top-pct): xep cac coin con lai theo |rate(WINDOW)m| (2 chieu: tang+roi),
 *       giu top {@link #TOP_PCT} bien dong manh nhat.</li>
 * </ol>
 * Tie-break on dinh theo symId tang dan (train/backtest/live cho CUNG ket qua khi bang diem).
 */
public final class EntrySignalFilter {

    private EntrySignalFilter() {}

    // ====================== THAM SO KHOA CUNG ======================
    // ⚠️ Doi bat ky gia tri nao = PHAI re-export + retrain TOAN BO. Da validate da-giai-doan.
    /** Volume trung binh 30m toi thieu (USDT) — gat coin rac thanh khoan thap. */
    public static final double VOL_AVG_MIN_USDT = 2000.0;
    /** So phut tinh return de do bien dong (2 chieu). */
    public static final int RATE_WINDOW_MIN = 30;
    /** So phut tinh volume trung binh. */
    public static final int VOL_AVG_WINDOW_MIN = 30;
    /** Ty le coin giu lai (top bien dong manh nhat) — cross-sectional moi moc. */
    public static final double TOP_PCT = 0.10;
    // ===============================================================

    /**
     * Chon coin qua filter tai 1 moc thoi gian.
     *
     * @param snapshot toan bo ticker tai moc t (key = symbol UPPER). Phai la SNAPSHOT DAY DU
     *                 cua thi truong tai t de tinh cross-sectional dung (thieu coin = rank lech).
     * @param history  HistoryManager DA duoc updateHistory(snapshot) tai moc t (de getReturn dung).
     * @return Set symbol qua filter (top-pct bien dong trong so coin du volume). Rong neu warmup.
     */
    public static Set<String> selectCoins(Map<String, KlineObjectSimple> snapshot, HistoryManager history) {
        Set<String> result = new HashSet<>();
        if (snapshot == null || snapshot.isEmpty() || history == null) return result;

        // Tang 1 + tinh |rate|: gom (symbol, symId, |rate30m|) cho coin du volume.
        List<Cand> cands = new ArrayList<>(snapshot.size());
        for (Map.Entry<String, KlineObjectSimple> e : snapshot.entrySet()) {
            String symbol = e.getKey();
            KlineObjectSimple k = e.getValue();
            if (k == null || !Utils.isTickerAvailable(k)) continue;

            short symId = com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper.getInstance().getId(symbol);
            if (symId < 0) continue;

            // vol-avg-30m: trung binh totalUsdt cua WINDOW nen gan nhat. getAverageVolume tra 0
            // khi chua du `periods` nen -> fallback ve totalUsdt nen hien tai (warmup).
            float volAvg = history.getAverageVolume(symId, VOL_AVG_WINDOW_MIN);
            if (volAvg <= 0f) volAvg = k.totalUsdt;
            if (volAvg < VOL_AVG_MIN_USDT) continue;

            float rate = history.getReturn(symbol, RATE_WINDOW_MIN);
            // getReturn tra 0.0 khi thieu history (warmup) -> |rate|=0 -> khong vao top, tu loai.
            float absRate = Math.abs(rate);
            if (absRate <= 0f) continue; // bo coin chua co bien dong / chua du history

            cands.add(new Cand(symbol, symId, absRate));
        }
        if (cands.isEmpty()) return result;

        // Tang 2: xep theo |rate| GIAM dan; tie-break symId TANG dan (on dinh, deterministic).
        cands.sort((a, b) -> {
            int c = Float.compare(b.absRate, a.absRate);
            if (c != 0) return c;
            return Short.compare(a.symId, b.symId);
        });

        // Giu top TOP_PCT (lam tron len >=1 de luon co it nhat 1 coin neu co candidate).
        int keep = (int) Math.ceil(cands.size() * TOP_PCT);
        if (keep < 1) keep = 1;
        if (keep > cands.size()) keep = cands.size();
        for (int i = 0; i < keep; i++) result.add(cands.get(i).symbol);
        return result;
    }

    /** Ung vien xep hang cross-sectional. */
    private static final class Cand {
        final String symbol;
        final short symId;
        final float absRate;
        Cand(String symbol, short symId, float absRate) {
            this.symbol = symbol;
            this.symId = symId;
            this.absRate = absRate;
        }
    }
}
