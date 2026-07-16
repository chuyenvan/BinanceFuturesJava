---
id: 207
status: TODO
depends_on: [200]
touches_live_process: false
writes_242_data: false
resource: local
checkpoint: false
max_retry: 2
report: docs/reports/207.md
require_review: true
---

# TASK-207 [WS1] — Chạy validate song song Oracle+Kaggle: SKIP semantics + gộp stamp

## Mục tiêu (1 câu)
Cho phép mỗi môi trường (Oracle / 226 / Kaggle) chạy phần validator có INPUT của nó mà không báo lỗi giả, rồi gộp stamp nhiều env thành verdict tổng.

## Bối cảnh
`VALIDATION_TEST_ROADMAP.md §5b`: data-locality → validator chạy nơi data ở. Hiện validator thiếu input đều ném → gate coi là infra-error (NEEDS_HUMAN), nhầm với lỗi thật.

## Scope
**Trong:** thêm ngữ nghĩa SKIP (validator thiếu input hợp lệ ở env này → SKIPPED, không FAIL/không NEEDS_HUMAN); ValidationReport phân biệt SKIP vs infra-error; ValidationStamp ghi tập check đã chạy ở env đó; hàm gộp nhiều stamp (Oracle + Kaggle) → verdict "phủ đủ 21 loại + tất cả PASS".
**Ngoài:** đổi logic từng validator (chỉ đổi cơ chế gate + stamp).

## Acceptance (kiểm-được-bằng-máy)
- [ ] Unit-test: gate chạy với ctx chỉ có client (không wfoDataDir) → validator file-bin = SKIPPED, không làm verdict FAIL.
- [ ] Gộp 2 stamp (Oracle phủ nhóm A/C/D/F, Kaggle phủ B/E + A2) → "đủ 21, PASS".
- [ ] `mvn -o test` xanh.

## (Code điền) Kết quả / Phát hiện / Quyết định
