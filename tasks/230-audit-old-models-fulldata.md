---
id: 230
status: TODO
depends_on: [206, 220]
touches_live_process: false
writes_242_data: false
resource: heavy_226
checkpoint: true
max_retry: 2
report: docs/reports/230.md
require_review: true
---

# TASK-230 [WS4] — Rà toàn bộ model cũ với data FULL + validate chặt

## Mục tiêu (1 câu)
So sánh công bằng mọi model cũ (đã sửa data) với ứng viên đang tốt maxFav3@4h — trên cùng data sạch, leak-free.

## Scope
**Trong:** với mỗi model cũ: kiểm provenance E1-E3 (có manifest/source? nếu mất → chỉ dùng benchmark, train lại theo CORE); chạy WFO leak-free trên `wfo_dataset` mới (WS3); bảng WFE/%OOS-dương/maxDD so maxFav3@4h.
**Ngoài:** tối ưu HPO mới (làm sau khi có verdict); bật tiền thật.

## Bối cảnh
- Chạy sim/WFO trên 226 (Cowork sandbox không chạy được). maxFav3@4h baseline: `tasks/155-baseline-model-maxfav3.md`.
- CORE: model lệch khỏi Java export hiện tại → TRAIN LẠI, không revert artifact cũ.

## Acceptance (kiểm-được-bằng-máy)
- [ ] Mỗi model: preflight PASS + WFO rerun ra số (KHÔNG tự kết verdict — trình Uni).
- [ ] Bảng so sánh model cũ vs maxFav3@4h trên cùng cửa sổ.
- [ ] Model mất provenance được đánh dấu benchmark-only.

## (Code điền) Kết quả / Phát hiện / Quyết định
