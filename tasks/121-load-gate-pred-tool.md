# TASK-121: LoadWfoGatePredTool — nạp wfo_gate_pred.csv → Aerospike set `ai_pred_market_gate_wfo` (GĐ2 mắt xích 1)

- **status:** doing (CCD opus code local; master chạy trên Oracle sau)
- **touches_live_process:** không (code + unit local; KHÔNG SSH)

## Bối cảnh
Gate/market predictions leak-free đang nằm ở `wfo_gate_pred.csv` (Oracle, sinh bởi WFOGateRunner per-fold).
Cần nạp vào Aerospike Oracle-local (ns theo config box) đúng FORMAT mà `WfoDataset.export` đọc từ set pred
(xem cách nó scan `ai_pred_market_full_basket_v2` — bắt buộc đọc code reader trước, mirror đúng bin/key/encoding).
Sau khi nạp: export dataset v3 = `WfoDataset.export` với env `WFO_SET_PRED=ai_pred_market_gate_wfo` (đã hỗ trợ).

## Việc làm
1. Đọc reader hiện hành (WfoDataset.export + DataManagerAerospikeFloatSim phần pred) → xác định key schema
   (chunk-month? per-tick?), bin, encoding. Ghi tóm tắt schema vào đầu tool (javadoc).
2. Viết `LoadWfoGatePredTool` (package export/gate): đọc csv (arg đường dẫn), validate header + N dòng đầu,
   ghi Aerospike theo config box (getClient226 — trên Oracle sẽ là local), chunk ≤ 4900 keys/batch,
   idempotent (chạy lại không nhân đôi), đếm + log SLF4J từng mốc 100k dòng, exception → exit 1.
3. Unit: csv mẫu nhỏ tự sinh trong test → mock/skip Aerospike nếu không có (test parse + chunk logic).
4. KHÔNG chạy thật — master chạy trên Oracle (validate small: 1 chunk trước, so đọc-lại, rồi full).

## Output: commit code + unit; Kết quả ghi schema đã xác định + cách chạy (lệnh mẫu). Marker /d/claudedata/CCD121_DONE.

## Kết quả
<CCD điền>
