package com.binance.chuyennd.research.oibackfill;

/**
 * Khai báo CHUNG 5 set Aerospike chứa OI FEATURE ĐÃ TÍNH SẴN cho live selector (#41..#45).
 *
 * <p>Khác {@link OiMetricSets} (chứa OI/LS/taker RAW): đây là 5 feature ĐÃ tính exact trên Oracle
 * (oiDelta24h, oiZ expanding, lsGlobal, lsToptrader, takerBuy) bởi {@code ComputeOiFeat2Live242},
 * push rolling-recent sang 242. Live chỉ {@code LiveOiFeatProvider.lookup} (merge_asof backward 2h),
 * KHÔNG tính → không đụng RAM/full-history trên bot.
 *
 * <p>Schema: mỗi set = 1 bin Snappy {@code Map<Long,Float>} per symbol (key = symbol UPPER), value =
 * ts(5m UTC) → feature. 5 set có CÙNG tập ts (kể cả NaN) để lookup 1 mốc ref là nhất quán cả 5.
 * ~vài nghìn record (per-coin) → index RAM không đáng kể (namespace ticker memory-size 1G).
 */
public final class OiFeatLiveSets {

    private OiFeatLiveSets() {}

    /** Bin dùng chung cho 5 set. */
    public static final String BIN = "f_data";

    public static final String OI_DELTA24H = "oi_feat_delta24h";
    public static final String OI_Z = "oi_feat_z";
    public static final String LS_GLOBAL = "oi_feat_lsg";
    public static final String LS_TOPTRADER = "oi_feat_lst";
    public static final String TAKER_BUY = "oi_feat_takerbuy";

    /** merge_asof BACKWARD tolerance 2h — KHỚP ExportFundingOiPerCoin/SelectorOiProvider. */
    public static final long MERGE_TOL_MS = 2L * 60L * 60_000L;
}
