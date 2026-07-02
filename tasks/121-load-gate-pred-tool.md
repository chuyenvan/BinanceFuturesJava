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

## Kết quả (CCD opus — code + unit local, KHÔNG chạy thật)

### 1. SCHEMA đã xác định (đọc reader hiện hành — KHÔNG đoán)
Reader mà `WfoDataset.export` dùng khi `WFO_SET_PRED=ai_pred_market_gate_wfo`:
`DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospikeSet(setName)` (L1817) — `scanAll` bin
`"data"` → `Snappy.uncompress` → `gson`→`AiPredictionData` → key TreeMap = `data.timestamp`.
Writer đối xứng: `saveMarketAiPredictionsBatchToSet(setName, map)` (L1792).

| Thành phần | Giá trị |
|---|---|
| Client/box | `getClient226()` (trên Oracle = Aerospike local theo config box) |
| Namespace | `Configs.AEROSPIKE_NAMESPACE` (config.properties = `ticker`) |
| Set | `ai_pred_market_gate_wfo` (override arg[1] / env `WFO_SET_PRED`) |
| Key | **per-tick / per-phút** `yyyyMMdd-HHmm` từ epoch-ms — formatter **pin GMT+7** (`AerospikeConfigs.keyFormat`); **KHÔNG chunk-tháng**. Mỗi phút = 1 record |
| Bin | đúng **1 bin** tên `"data"` = `Snappy.compress(gson.toJson(AiPredictionData) UTF-8)` |
| WritePolicy | `recordExistsAction=UPDATE, sendKey=true` → put đè cùng key ⇒ **idempotent** (chạy lại KHÔNG nhân đôi) |

`AiPredictionData` JSON = `{timestamp:long, predReturn15M:float, predRisk4H:float}`.
CSV nguồn (`WFOGateRunner` L113): header **`timestamp,predReturn15M,predRisk4H`**, mỗi dòng `<epochMs>,<float>,<float>`;
`timestamp`=epoch-ms → gán thẳng `AiPredictionData.timestamp` (reader lấy làm key).

> Quyết định thiết kế: tool **TÁI DÙNG** `saveMarketAiPredictionsBatchToSet` làm writer (nguồn sự thật duy nhất
> về key/bin/encoding/policy) thay vì tự dựng lại → 0 rủi ro lệch format.

### 2. Code
- `export/gate/LoadWfoGatePredTool.java` — main(csvPath, [setName]); stream CSV, validate header khớp tuyệt đối
  + preflight 5 dòng đầu, gom ≤4900 key/batch → flush qua `BatchSink` (production = Aerospike), log mỗi 100k dòng,
  exception → exit 1. Sink tách rời để test không cần Aerospike.
- `export/gate/LoadWfoGatePredToolTest.java` — self-test main-based (repo không dùng JUnit).

### 3. Unit — PASS 13/13 (exit 0), Aerospike STUB (RecordingSink), KHÔNG kết nối
`javac -encoding UTF-8` OK; test: validateHeader (đúng/sai/BOM), parseLine (đúng/thiếu cột/ts≤0/số sai),
chunk 10 dòng×chunk=4 → batch **[4,4,2]** total=10, dedup (3 dòng cùng-ts → ghi 2 record), bỏ dòng trống, dòng hỏng→ném.

### 4. Cách chạy (master trên Oracle — validate small 1 chunk → so đọc-lại → full; CCD KHÔNG chạy)
```
java -cp binance-java-sdk.jar \
  com.binance.chuyennd.ai_ml.features.export.gate.LoadWfoGatePredTool \
  ~/claudedata/wfo_gate_pred.csv [ai_pred_market_gate_wfo]
# đọc-lại verify: WFO_SET_PRED=ai_pred_market_gate_wfo ... WfoDataset.export
```
arg[0]=CSV (bắt buộc); arg[1]=set (mặc định env `WFO_SET_PRED` hoặc `ai_pred_market_gate_wfo`).
