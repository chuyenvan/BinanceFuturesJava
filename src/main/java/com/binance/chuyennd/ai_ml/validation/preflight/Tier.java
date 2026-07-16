package com.binance.chuyennd.ai_ml.validation.preflight;

/**
 * Tầng chạy validate theo chi phí (Uni chốt 2026-07-11: "nhanh thì gắn vào cho chắc, lâu thì chạy ngoài").
 *
 * <ul>
 *   <li>{@link #FAST} — check FULL-SCAN rẻ ({@link CheckId#expensive()} == false). GẮN INLINE vào
 *       đầu WFO/HPO, luôn chạy, chặn tại chỗ.</li>
 *   <li>{@link #SLOW} — check random-sample ĐẮT ({@link CheckId#expensive()} == true). Chạy NGOÀI
 *       theo trigger (run đầu / data mới / đổi môi trường / gen mới), KHÔNG chạy mỗi lần WFO.
 *       Kết quả đóng dấu {@link ValidationStamp}.</li>
 *   <li>{@link #ALL} — chạy cả hai (dùng cho lần validate full ngoài).</li>
 * </ul>
 */
public enum Tier {
    FAST,
    SLOW,
    ALL
}
