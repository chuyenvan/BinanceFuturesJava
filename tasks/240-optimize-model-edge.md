---
id: 240
status: TODO
depends_on: [230]
touches_live_process: false
writes_242_data: false
resource: kaggle
checkpoint: true
max_retry: 2
report: docs/reports/240.md
require_review: true
---

# TASK-240 [WS5] — Tối ưu model cho edge tốt nhất (SAU cổng quyết định B6)

## ⛔ GATE người: CHỈ chạy khi Uni chốt B6 ĐẠT
Theo `VALIDATION_TEST_ROADMAP.md §7`: chỉ tối ưu NẾU head-to-head (task 230) cho thấy maxFav3@4h **thật sự đạt ngưỡng pre-register**. B6 KHÔNG đạt → KHÔNG mở task này; quay lại `SOLUTION_FRAMEWORK §6` (điểm dừng / đổi nhánh). Supervisor KHÔNG auto (require_review + chờ người).

## Mục tiêu (1 câu)
Từ maxFav3@4h đã xác nhận có edge, tối ưu (HPO/feature/target) để edge tốt nhất — KHÔNG overfit.

## Scope
**Trong:** HPO trên WFO leak-free (RunHpoMaster_Distributed / Kaggle master-worker); thử feature/target/label quanh maxFav3@4h; đo edge bằng WFO bậc thang, KHÔNG in-sample.
**Ngoài:** bật tiền thật; đổi kiến trúc long-only.

## Acceptance (kiểm-được-bằng-máy)
- [ ] Edge cải thiện ĐO ĐƯỢC so baseline maxFav3@4h trên WFO (WFE/%OOS-dương/Calmar), pre-register trước.
- [ ] Mỗi model tối ưu mang provenance (E1-E3): commit + data hash + cutoffs.
- [ ] CONFIG_VERSION bump khi đổi thứ ngoài genome.

## (Code điền) Kết quả / Phát hiện / Quyết định
