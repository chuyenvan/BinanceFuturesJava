package com.binance.chuyennd.ai_ml.validation.preflight;

/**
 * Danh mục 19 loại lỗi / 6 nhóm của Data Preflight Gate.
 *
 * <p>Nguồn canonical: {@code docs/DATA_VALIDATION_FRAMEWORK.md} §2. Mỗi hằng số ở đây tương ứng
 * MỘT loại lỗi và (theo thiết kế) MỘT class {@link DataValidator}. Trường {@link #defaultSeverity}
 * và {@link #expensive} bám bảng §2/§3 nhưng là ĐỀ XUẤT — Uni chốt cuối (§4). KHÔNG hard-code
 * verdict theo enum này; ngưỡng số thật nằm ở từng validator + {@code ExpectedRanges}.</p>
 *
 * <p>Nhóm: A=Coverage, B=Leakage, C=Values, D=Time, E=Provenance, F=Config.</p>
 */
public enum CheckId {
    // A. COVERAGE — thiếu/lệch dữ liệu (full-scan, rẻ)
    A1("A", "Pred thiếu cả giai đoạn (gate trống 2021-2022)", Severity.BLOCK, false),
    A2("A", "Lệch range giữa các nguồn (market vs pred)", Severity.BLOCK, false),
    A3("A", "Coin trong pred không có ticker (ghost USDCUSDT)", Severity.BLOCK, false),
    A4("A", "Fold WFO thiếu (16 vs 17)", Severity.BLOCK, false),
    A5("A", "Survivorship: coin delist/dead thiếu trong universe lịch sử (chỉ thấy survivor)", Severity.BLOCK, false),
    A6("A", "Cadence-mismatch: số record/loại < mật độ kỳ vọng (bug funding 15m thay vì per-minute)", Severity.BLOCK, false),

    // B. LEAKAGE — rò rỉ tương lai (sample, đắt) — đảo verdict
    B1("B", "Label tính từ giá vùng OOS", Severity.BLOCK, true),
    B2("B", "Feature dùng dữ liệu tương lai (shuffle-test)", Severity.WARN, true),
    B3("B", "Purge/embargo buffer < max holding", Severity.BLOCK, true),
    B4("B", "Cross-sectional/population leak (basket warmup, z-score toàn kỳ, OI merge tương lai)", Severity.BLOCK, true),

    // C. GIÁ TRỊ — data bẩn (full-scan cho C1-C3 rẻ; C4 sample)
    C1("C", "NaN/Inf trong feature/pred", Severity.BLOCK, false),
    C2("C", "Giá phi lý (0, âm, nhảy x1000 — bug USDC-margin)", Severity.BLOCK, false),
    C3("C", "Trùng lặp (ts, symbol)", Severity.BLOCK, false),
    C4("C", "Scale sai (0.03 vs 3%)", Severity.WARN, true),

    // D. THỜI GIAN (sample/scan nhẹ)
    D1("D", "Timezone lệch (GMT+7 vs UTC) ở settlement funding", Severity.WARN, true),
    D2("D", "Gap thời gian (ngày < 1440 phút)", Severity.WARN, true),
    D3("D", "Off-by-one nến (dùng close chưa chốt)", Severity.BLOCK, true),

    // E. PROVENANCE — nguồn gốc model/dataset (rẻ)
    E1("E", "Model không khớp code/data (mất source)", Severity.BLOCK, false),
    E2("E", "md5 mismatch (copy pred.bin quên sửa manifest)", Severity.BLOCK, false),
    E3("E", "Cutoff config im lặng (train range không khai báo)", Severity.BLOCK, false),

    // F. CẤU HÌNH
    F1("F", "Env thiếu → fallback im lặng (WFO_SMART_CACHE, pred dir rỗng)", Severity.BLOCK, false),
    F2("F", "Config version drift (CONFIG_VERSION) — cache HPO trả điểm cũ = run vô nghĩa", Severity.BLOCK, false);

    private final String group;
    private final String description;
    private final Severity defaultSeverity;
    private final boolean expensive;

    CheckId(String group, String description, Severity defaultSeverity, boolean expensive) {
        this.group = group;
        this.description = description;
        this.defaultSeverity = defaultSeverity;
        this.expensive = expensive;
    }

    /** @return nhóm lỗi: A/B/C/D/E/F. */
    public String group() {
        return group;
    }

    /** @return mô tả người-đọc của loại lỗi. */
    public String description() {
        return description;
    }

    /** @return mức nghiêm trọng mặc định (đề xuất; validator có thể override khi Uni chốt khác). */
    public Severity defaultSeverity() {
        return defaultSeverity;
    }

    /**
     * @return true nếu check ĐẮT (cần random-sample phân tầng theo §3), false nếu FULL-SCAN rẻ.
     *         {@code PreflightGate} chạy hết check rẻ trước rồi mới tới check đắt.
     */
    public boolean expensive() {
        return expensive;
    }
}
