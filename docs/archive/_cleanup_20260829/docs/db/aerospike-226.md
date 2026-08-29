# db/aerospike-226 — REPLICATE + COMPUTE (open internet)

> Đọc cùng [db/index](index.md). 226 = bản replicate market (on-demand) + kho tính toán/huấn luyện. Kaggle/dev tới được.

## Set COMPUTE (chỉ ở 226, KHÔNG ghi 242)
- `ai_pred_market` / predict · `predictionSymbol`
- `marketobject` (MarketDataObject dẫn xuất) · `symbol_lifecycle`
- `gate_return` (label) · `gate_features` (A/B) · `funding_label`
- `distributed_task` (AerospikeTaskCoordinator), kết quả wfo/hpo · `hpo_queue_<CONFIG_VERSION>` / `hpo_results_<CONFIG_VERSION>`

## Vai trò
- **Replicate-theo-setname (on-demand):** trước khi train/backtest, dùng `ReplicateSet242To226` (TASK-034, chạy TRÊN 226, đọc-only 242 → ghi 226) copy đúng set MARKET cần (vì Kaggle/dev chỉ đọc 226). Vừa phục vụ train vừa làm backup repl=1.
- **Compute:** train/backtest/wfo/hpo đọc MARKET (đã replicate) + COMPUTE từ 226, ghi COMPUTE vào 226.
- Market historical (kline_1m 2020+) hiện đang có sẵn ở 226 (cào cũ) → job train/Kaggle chạy bình thường, không gián đoạn.

## Lưu ý
- **TASK-112:** tool/job đọc qua `getReadClient` (ticker/mapper/funding_data) cần `config.properties` của box có `AEROSPIKE_READ_CLUSTER=226`; chạy sim/backtest cần thêm `TICKER_SOURCE=aerospike`. Thiếu/sai key → fail-fast `IllegalStateException` ngay tại điểm dùng (không còn flag IS_KAGGLE_MODE/IS_HPO_MODE cũ).
- Open internet → tải `data.binance.vision` trực tiếp được. Tài nguyên YẾU → job nặng chạy tuần tự (xem [run-226](../rules/run-226.md)).
- `marketobject` = COMPUTE → 226 (TASK-032 xác nhận chỉ sống ở 226).
