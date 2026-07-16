---
id: 201
status: TODO
depends_on: [200]
touches_live_process: false
writes_242_data: false
resource: oracle
checkpoint: false
max_retry: 2
report: docs/reports/201.md
require_review: true
---

# TASK-201 [WS1-A] — Validator nhóm A: Coverage (A1-A5)

## Mục tiêu (1 câu)
5 class `DataValidator` cho A1-A5, trả metrics; A1 tái phát hiện lỗi gate trống 2021-2022 (regression task 156).

## Scope
**Trong:** `A1PredCoverageValidator` (đếm records/tháng mỗi nguồn, cảnh báo < X% median), `A2RangeConsistencyValidator` (giao thời gian market∩gate∩selector∩funding phủ mọi cửa sổ), `A3GhostTickerValidator` (mọi symId trong pred có ticker), `A4FoldCountValidator` (số fold = ExpectedRanges.expectedFolds), `A5SurvivorshipValidator` (coin DEAD trong `symbol_lifecycle` phải CÓ mặt trong universe trước ngày delist — chống backtest chỉ thấy survivor). WRAP tool cũ (`CheckGapPredict*`, `CleanTickerGhostAndTail`, `SurvivorshipBac0`/`SurvivorshipFeatureCheck`).
**Ngoài:** sửa dữ liệu (đó là WS3); ngưỡng BLOCK/WARN cuối (chờ Uni §6).

## Bối cảnh
- Nguồn tái dùng: roadmap §2 hàng A1-A4. Gốc lỗi A1: `docs/reports/156.md`.

## Acceptance (kiểm-được-bằng-máy)
- [ ] 4 validator implement `DataValidator`, đăng ký chạy qua `PreflightGate`.
- [ ] A1 chạy trên data hiện tại → metrics ghi records/tháng; phát hiện gate 2021-2022 thiếu.
- [ ] Số A3 khớp scan ghost hiện có (WFO_DATAFLOW §9).
- [ ] Log SLF4J; không đọc/ghi ổ C.

## (Code điền) Kết quả / Phát hiện / Quyết định
