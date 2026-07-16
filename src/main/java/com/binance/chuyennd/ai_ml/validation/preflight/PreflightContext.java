package com.binance.chuyennd.ai_ml.validation.preflight;

import com.aerospike.client.AerospikeClient;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Ngữ cảnh chạy truyền cho mọi {@link DataValidator} — tách validator khỏi cách lấy handle
 * (Aerospike client, đường dẫn dataset, env, expected ranges), để mỗi validator KHÔNG tự
 * new client / đọc config riêng (tránh lệch nguồn).
 *
 * <p>Các validator chạm dữ liệu 242 phải dùng client 226 (CORE: mọi thứ chạm 242 qua SSH 226).
 * Field nào chưa cần thì để null; validator tự kiểm null và trả FAIL/NEEDS_HUMAN thay vì NPE câm.</p>
 */
public final class PreflightContext {

    private final AerospikeClient client;
    private final String wfoDataDir;
    private final String fundingPredDir;
    private final int sampleSizePerCell;
    private final Map<String, String> env;
    private final ExpectedRanges expected;

    private PreflightContext(Builder b) {
        this.client = b.client;
        this.wfoDataDir = b.wfoDataDir;
        this.fundingPredDir = b.fundingPredDir;
        this.sampleSizePerCell = b.sampleSizePerCell;
        this.env = b.env;
        this.expected = b.expected;
    }

    /** @return Aerospike client (226) — có thể null nếu chạy check chỉ trên file bin. */
    public AerospikeClient client() {
        return client;
    }

    /** @return thư mục WFO dataset file bin (WFO_DATA_DIR), có thể null. */
    public String wfoDataDir() {
        return wfoDataDir;
    }

    /** @return thư mục selector predict_wf_*.bin (WFO_FUNDING_PRED_DIR), có thể null. */
    public String fundingPredDir() {
        return fundingPredDir;
    }

    /** @return số mẫu tối thiểu mỗi (tháng × tier) cho check đắt (§3, đề xuất ≥100 — chờ Uni chốt). */
    public int sampleSizePerCell() {
        return sampleSizePerCell;
    }

    /**
     * @param key tên biến môi trường
     * @return giá trị env đã nạp (null nếu thiếu — validator F1 dùng để bắt fallback im lặng)
     */
    public String env(String key) {
        return env.get(key);
    }

    /** @return khai báo range/ngưỡng pre-register cho từng nguồn (§1.4). */
    public ExpectedRanges expected() {
        return expected;
    }

    /** Builder cho {@link PreflightContext}. */
    public static final class Builder {
        private AerospikeClient client;
        private String wfoDataDir;
        private String fundingPredDir;
        private int sampleSizePerCell = 100;
        private Map<String, String> env = new LinkedHashMap<>();
        private ExpectedRanges expected = new ExpectedRanges();

        public Builder client(AerospikeClient v) { this.client = v; return this; }
        public Builder wfoDataDir(String v) { this.wfoDataDir = v; return this; }
        public Builder fundingPredDir(String v) { this.fundingPredDir = v; return this; }
        public Builder sampleSizePerCell(int v) { this.sampleSizePerCell = v; return this; }
        public Builder env(Map<String, String> v) { if (v != null) this.env = new LinkedHashMap<>(v); return this; }
        public Builder expected(ExpectedRanges v) { if (v != null) this.expected = v; return this; }

        /** @return context bất biến. */
        public PreflightContext build() {
            return new PreflightContext(this);
        }
    }
}
