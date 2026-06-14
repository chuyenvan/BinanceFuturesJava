package com.binance.chuyennd.research.oibackfill;

/**
 * TASK-013 — Khai báo CHUNG 5 set metrics OI/LS/taker (history backfill + forward 007-C/035 dùng chung
 * để feature extractor 018 chỉ thấy MỘT schema, không phân biệt nguồn). Granularity 5m UTC, mỗi metric
 * 1 set, Snappy {@code Map<Long,Float>} per symbol (key = symbol UPPER), dedup theo ts.
 *
 * <p>Nguồn cột: file daily {@code data.binance.vision/data/futures/um/daily/metrics/<SYM>/<SYM>-metrics-YYYY-MM-DD.zip},
 * header 8 cột (xác nhận B1):
 * <pre>
 *   0 create_time              5 sum_toptrader_long_short_ratio
 *   1 symbol                   6 count_long_short_ratio
 *   2 sum_open_interest        7 sum_taker_long_short_vol_ratio
 *   3 sum_open_interest_value
 *   4 count_toptrader_long_short_ratio
 * </pre>
 *
 * <p>Queue/done set (Aerospike 226) là checkpoint phân tán (xem {@link BackfillOiMaster}/{@link BackfillOiWorker}).
 */
public final class OiMetricSets {

    private OiMetricSets() {
    }

    /** Bước thời gian metrics (5 phút) tính bằng ms. */
    public static final long STEP_MS = 5 * 60_000L;

    /** Set queue task PENDING/RUNNING (mỗi key = 1 symbol). Worker scanAll → luôn nhỏ. */
    public static final String QUEUE_SET = "oi_backfill_queue";
    /** Set đánh dấu symbol DONE (point-get, KHÔNG scan) → rerun skip = checkpoint idempotent. */
    public static final String DONE_SET = "oi_backfill_done";

    /** 1 metric = (set Aerospike, bin Snappy, chỉ số cột CSV). */
    public static final class Metric {
        public final String set;
        public final String bin;
        public final int col;

        Metric(String set, String bin, int col) {
            this.set = set;
            this.bin = bin;
            this.col = col;
        }
    }

    // OI value dùng set+bin Y HỆT 007-C forward ({@code open_interest}/{@code oi_data}) → history + forward
    // ghi CÙNG chỗ, không bậc thang. 4 metric LS/taker mới dùng bin chung "m_data".
    public static final Metric OI = new Metric("open_interest", "oi_data", 3);
    public static final Metric LS_TOPTRADER_ACC = new Metric("oi_ls_toptrader_acc", "m_data", 4);
    public static final Metric LS_TOPTRADER_POS = new Metric("oi_ls_toptrader_pos", "m_data", 5);
    public static final Metric LS_GLOBAL_ACC = new Metric("oi_ls_global_acc", "m_data", 6);
    public static final Metric TAKER_VOL = new Metric("oi_taker_vol", "m_data", 7);

    /** Cả 5 metric cần ghi cho mỗi symbol. */
    public static final Metric[] ALL = {OI, LS_TOPTRADER_ACC, LS_TOPTRADER_POS, LS_GLOBAL_ACC, TAKER_VOL};

    /** Chuẩn hoá 1 mốc thời gian về lưới 5m gần nhất (chống lệch giây + boundary file cũ). */
    public static long normalize5m(long tsMs) {
        return Math.round(tsMs / (double) STEP_MS) * STEP_MS;
    }
}
