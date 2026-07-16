---
id: 220
status: TODO
depends_on: [206]
touches_live_process: false
writes_242_data: true
resource: heavy_226
checkpoint: true
max_retry: 2
report: docs/reports/220.md
require_review: true
---

# TASK-220 [WS3] — Re-export dữ liệu thiếu/sai cho đủ WFO (theo report gate)

## Mục tiêu (1 câu)
Lấp đúng chỗ thiếu/sai mà preflight (WS1) chỉ ra → export lại dataset WFO đạt ExpectedRanges.

## Scope
**Trong:** đọc report A1/A2/D2 → xác định nguồn×tháng thiếu → re-export (feature/pred/funding) đúng phần đó; regen `wfo_dataset` file bin + manifest md5. Chạy trên 226 (ghi 242 qua SSH 226). Checkpoint theo tháng, resume-skip-done.
**Ngoài:** train lại model (WS4); đổi feature set.

## Bối cảnh
- ⚠️ `writes_242_data=true` → BẮT BUỘC qua SSH 226 (AGENT_WORKFLOW §1). Chạy trên máy bạn/226 — Cowork sandbox KHÔNG tới được.
- Lệnh export tham chiếu: `WFO_DATAFLOW §4` (ExportWfoDataset).

## Acceptance (kiểm-được-bằng-máy)
- [ ] Sau export: records/tháng mỗi nguồn ≥ ngưỡng ExpectedRanges.
- [ ] Preflight A1/A2/D2 PASS lại (gate xanh).
- [ ] manifest md5 khớp; 0 NaN.

## (Code điền) Kết quả / Phát hiện / Quyết định
