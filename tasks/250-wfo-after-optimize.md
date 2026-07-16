---
id: 250
status: TODO
depends_on: [240]
touches_live_process: false
writes_242_data: false
resource: heavy_226
checkpoint: true
max_retry: 2
report: docs/reports/250.md
require_review: true
---

# TASK-250 [WS5] — WFO lại với model đã tối ưu

## Mục tiêu (1 câu)
Chạy WFO model tối ưu (task 240) leak-free → số cuối cùng để Uni quyết bật tiền thật hay không.

## Scope
**Trong:** model tối ưu = artifact MỚI → **trigger re-validate FULL** (preflight SLOW: provenance E1-E3 + leak B1-B4) + đóng stamp mới TRƯỚC khi WFO; WFO trên data sạch cùng khuôn 230; so với maxFav3@4h baseline.
**Ngoài:** deploy/restart 2 process live (người tay).

## Acceptance (kiểm-được-bằng-máy)
- [ ] Preflight FULL PASS cho model mới (stamp mới) TRƯỚC khi WFO — chống overfit lọt lưới.
- [ ] WFO ra WFE/%OOS-dương/maxDD; bảng so baseline.
- [ ] Verdict do Uni quyết (Claude chỉ trình số).

## (Code điền) Kết quả / Phát hiện / Quyết định
