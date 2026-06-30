package com.binance.chuyennd.ai_ml.wfo.framework;

/**
 * WFO FRAMEWORK — 1 ĐƠN VỊ CÔNG VIỆC (job) với STATE MACHINE rõ ràng (Uni chốt: không queue thuần,
 * phải phân biệt chưa-chạy / đang-chạy / xong / chết-giữa-chừng + lease/TTL).
 *
 * <pre>
 * PENDING ──claim(owner,lease)──► RUNNING ──report(result)──► DONE
 *    ▲                              │
 *    └──lease hết hạn (worker chết)─┘   (worker khác steal khi quá hạn)
 *                                   │
 *                                   └──fail quá maxRetry──► FAILED (chờ người)
 * </pre>
 *
 * <p>1 job = 1 đơn vị WFO (vd 1 cửa sổ strategy / 1 fold model). type cho biết task nào xử lý.
 * payload = tham số job (JSON phẳng). result = kết quả khi DONE (JSON). Idempotent: chạy lại cho cùng
 * kết quả (seed cố định) → steal an toàn.
 */
public class WfoJob {

    public enum State { PENDING, RUNNING, DONE, FAILED }

    public String id;            // vd "strat-w03"
    public String type;          // "strategy_window" | "model_fold" ...
    public State state = State.PENDING;
    public String payload = "";  // JSON tham số job (do task định nghĩa)
    public String result = "";   // JSON kết quả (khi DONE)
    public String owner = "";    // worker đang giữ (host/pid)
    public long leaseUntil = 0;  // epoch ms; RUNNING hết hạn mà chưa gia hạn → coi worker chết
    public int retryCount = 0;
    public int maxRetry = 2;
    public long createdAt = 0;
    public long updatedAt = 0;
    public String lastError = "";

    public WfoJob() {}

    public WfoJob(String id, String type, String payload) {
        this.id = id;
        this.type = type;
        this.payload = payload;
        this.createdAt = System.currentTimeMillis();
        this.updatedAt = this.createdAt;
    }

    public boolean leaseExpired(long now) {
        return state == State.RUNNING && now > leaseUntil;
    }

    @Override
    public String toString() {
        return String.format("Job[%s type=%s state=%s owner=%s lease=%d retry=%d/%d]",
                id, type, state, owner, leaseUntil, retryCount, maxRetry);
    }
}
