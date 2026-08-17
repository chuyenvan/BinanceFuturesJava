package com.binance.chuyennd.ai_ml.features.export.funding;

import java.util.Arrays;
import java.util.List;

/**
 * PASS-2 cross-sectional rank cho selector features #33..#35
 * (fundingRankCS, volumeZRankCS, momentumRankCS).
 *
 * <p><b>Vì sao tồn tại</b>: logic rank gốc nằm private trong
 * {@code ExportFeaturesForPythonTool.applyCrossSectional/percentileRanks} — CHỈ chạy ở pipeline
 * export/train. Live inference ({@code DetectEntrySignal2TradeNormal.predictAllCandidates}) trước
 * đây KHÔNG có PASS-2 nên 3 feature này luôn NaN ở live (reconcile 2026-08-17 phát hiện). Class này
 * COPY CHÍNH XÁC thuật toán để live tính khớp train. Population phải là {@link EntrySignalFilter}
 * (giống export) — caller chịu trách nhiệm truyền đúng tập coin.
 *
 * <p>Rank-percentile (midrank) ∈ [0,1] so với các phần tử KHÔNG-NaN cùng mảng; NaN giữ NaN;
 * &lt;2 giá trị hợp lệ → tất cả NaN. KHÔNG look-ahead (chỉ coin cùng mốc t).
 */
public final class FundingCrossSectional {

    private FundingCrossSectional() {}

    /**
     * Set fundingRankCS/volumeZRankCS/momentumRankCS cho từng feature trong list, rank giữa các
     * phần tử của CHÍNH list (phải là population EntrySignalFilter tại mốc t). Mutate tại chỗ.
     */
    public static void apply(List<FundingMarketFeatures> list) {
        int m = list.size();
        if (m == 0) return;
        float[] funding = new float[m];
        float[] volz = new float[m];
        float[] mom = new float[m];
        for (int i = 0; i < m; i++) {
            FundingMarketFeatures f = list.get(i);
            funding[i] = f.coinFundingRate; // luôn có giá trị (0 nếu thiếu funding) → rank toàn coin
            volz[i] = f.volumeZCoin;        // NaN khi warmup → loại khỏi rank
            mom[i] = f.momentum24H;
        }
        float[] fundingRank = percentileRanks(funding);
        float[] volzRank = percentileRanks(volz);
        float[] momRank = percentileRanks(mom);
        for (int i = 0; i < m; i++) {
            FundingMarketFeatures f = list.get(i);
            f.fundingRankCS = fundingRank[i];
            f.volumeZRankCS = volzRank[i];
            f.momentumRankCS = momRank[i];
        }
    }

    /**
     * Rank-percentile (midrank) ∈ [0,1] cho từng phần tử so với các phần tử KHÔNG-NaN cùng mảng.
     * NaN giữ nguyên NaN. Nếu &lt;2 giá trị hợp lệ → tất cả NaN (rank vô nghĩa).
     * COPY CHÍNH XÁC từ ExportFeaturesForPythonTool.percentileRanks (parity train↔live).
     */
    private static float[] percentileRanks(float[] vals) {
        int m = vals.length;
        float[] out = new float[m];
        int validCount = 0;
        for (float v : vals) if (!Float.isNaN(v)) validCount++;
        if (validCount <= 1) {
            Arrays.fill(out, Float.NaN);
            return out;
        }
        float[] sorted = new float[validCount];
        int k = 0;
        for (float v : vals) if (!Float.isNaN(v)) sorted[k++] = v;
        Arrays.sort(sorted);
        for (int i = 0; i < m; i++) {
            float v = vals[i];
            if (Float.isNaN(v)) {
                out[i] = Float.NaN;
                continue;
            }
            int less = lowerBound(sorted, v);
            int equal = upperBound(sorted, v) - less;
            out[i] = (float) ((less + 0.5 * equal) / validCount);
        }
        return out;
    }

    /** Số phần tử &lt; key trong mảng đã sort tăng dần. */
    private static int lowerBound(float[] a, float key) {
        int lo = 0, hi = a.length;
        while (lo < hi) {
            int mid = (lo + hi) >>> 1;
            if (a[mid] < key) lo = mid + 1;
            else hi = mid;
        }
        return lo;
    }

    /** Số phần tử ≤ key trong mảng đã sort tăng dần. */
    private static int upperBound(float[] a, float key) {
        int lo = 0, hi = a.length;
        while (lo < hi) {
            int mid = (lo + hi) >>> 1;
            if (a[mid] <= key) lo = mid + 1;
            else hi = mid;
        }
        return lo;
    }
}
