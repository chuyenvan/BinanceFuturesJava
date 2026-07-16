---
id: 203
status: TODO
depends_on: [200]
touches_live_process: false
writes_242_data: false
resource: local
checkpoint: false
max_retry: 2
report: docs/reports/203.md
require_review: true
---

# TASK-203 [WS1-E+F] — Validator Provenance (E1-E3) + Config (F1-F2)

## Mục tiêu (1 câu)
Chặn model/dataset mất nguồn gốc + env fallback im lặng — 2 gốc bug lớn (ONNX mất source, WFO_SMART_CACHE).

## Scope
**Trong:** `E1ManifestValidator` (model/dataset có manifest: commit+data hash+cutoffs), `E2Md5Validator` (WRAP `WfoDataset.load()` md5 3 file), `E3CutoffValidator` (manifest ghi train range, khớp mong đợi), `F1RequiredEnvValidator` (fail-fast nếu thiếu env bắt buộc: WFO_DATA_DIR, WFO_FUNDING_PRED_DIR, WFO_SMART_CACHE — KHÔNG fallback lặng), `F2ConfigVersionValidator` (VERIFY khớp CONFIG_VERSION `RunHpoMaster_Distributed`).
**Ngoài:** thiết kế lại format manifest model (đề xuất riêng nếu thiếu).

## Acceptance (kiểm-được-bằng-máy)
- [ ] E2 md5 khớp/mismatch đúng trên file bin thật.
- [ ] F1 trả BLOCK-fail khi unset env bắt buộc; PASS khi đủ.
- [ ] Log SLF4J.

## (Code điền) Kết quả / Phát hiện / Quyết định
