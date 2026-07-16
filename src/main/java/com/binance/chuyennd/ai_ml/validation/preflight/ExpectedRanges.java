package com.binance.chuyennd.ai_ml.validation.preflight;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Khai báo PRE-REGISTER cho từng nguồn/feature — nền của nguyên tắc §1.4
 * ("mỗi nguồn khai báo trước range thời gian, records/tháng, min/max mỗi feature;
 * validate so khai báo, lệch = fail"). Chống "so với trí nhớ".
 *
 * <p>Skeleton: giữ container tối thiểu. Nội dung thật nạp từ
 * {@code /home/ubuntu/claudedata/validate_criteria.md} (hoặc file khai báo tương đương) —
 * việc nạp/parse là task riêng (WS1). KHÔNG hard-code magic number vào code.</p>
 */
public final class ExpectedRanges {

    /** Khai báo range thời gian mong đợi của một nguồn. */
    public static final class SourceRange {
        public final String source;
        public final long expectedStartMs;
        public final long expectedEndMs;
        public final long minRecordsPerMonth;

        public SourceRange(String source, long expectedStartMs, long expectedEndMs, long minRecordsPerMonth) {
            this.source = source;
            this.expectedStartMs = expectedStartMs;
            this.expectedEndMs = expectedEndMs;
            this.minRecordsPerMonth = minRecordsPerMonth;
        }
    }

    /** Khai báo min/max hợp lệ của một feature (dùng C4 scale-check). */
    public static final class FeatureBound {
        public final String feature;
        public final double min;
        public final double max;

        public FeatureBound(String feature, double min, double max) {
            this.feature = feature;
            this.min = min;
            this.max = max;
        }
    }

    private final Map<String, SourceRange> sourceRanges = new LinkedHashMap<>();
    private final Map<String, FeatureBound> featureBounds = new LinkedHashMap<>();
    private int expectedFolds = 17;
    private int expectedMinDeadCoins = 72;

    /** @param r khai báo range 1 nguồn. */
    public void putSource(SourceRange r) {
        sourceRanges.put(r.source, r);
    }

    /** @param b khai báo bound 1 feature. */
    public void putFeature(FeatureBound b) {
        featureBounds.put(b.feature, b);
    }

    /**
     * @param source tên nguồn
     * @return khai báo range (null nếu chưa khai báo → validator coi là NEEDS_HUMAN, KHÔNG đoán)
     */
    public SourceRange source(String source) {
        return sourceRanges.get(source);
    }

    /**
     * @param feature tên feature
     * @return bound khai báo (null nếu chưa khai báo)
     */
    public FeatureBound feature(String feature) {
        return featureBounds.get(feature);
    }

    /** @return số fold WFO mong đợi (A4). */
    public int expectedFolds() {
        return expectedFolds;
    }

    /** @param n số fold mong đợi. */
    public void expectedFolds(int n) {
        this.expectedFolds = n;
    }

    /**
     * @return số coin DEAD tối thiểu mong đợi trong universe (A5 survivorship). Mặc định 72
     *         (WFO_DATAFLOW: symbol_lifecycle 72 DEAD). Thấp hơn = nghi universe bị lọc còn survivor.
     */
    public int expectedMinDeadCoins() {
        return expectedMinDeadCoins;
    }

    /** @param n số coin DEAD tối thiểu mong đợi. */
    public void expectedMinDeadCoins(int n) {
        this.expectedMinDeadCoins = n;
    }
}
