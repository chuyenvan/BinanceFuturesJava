---
id: 202
status: TODO
depends_on: [200]
touches_live_process: false
writes_242_data: false
resource: oracle
checkpoint: false
max_retry: 2
report: docs/reports/202.md
require_review: true
---

# TASK-202 [WS1-C] — Validator nhóm C: Values / data bẩn (C1-C4)

## Mục tiêu (1 câu)
4 validator bắt NaN/Inf, giá phi lý, trùng lặp, scale sai — bọc từ tool phân tích feature hiện có.

## Scope
**Trong:** `C1NanInfValidator` (đếm NaN/Inf mỗi cột = 0), `C2PriceSanityValidator` (giá>0; |Δ1phút|<50%; OHLC hợp lệ — bắt bug USDC-margin), `C3DuplicateValidator` (không cặp (ts,symId) lặp), `C4ScaleValidator` (min/max/median trong ExpectedRanges — WARN). WRAP `FeatureQualityAnalyzer`, `ValidateMarketObjectConsistency`, `ProductionFeatureStabilityChecker`.
**Ngoài:** vá bug `DataManagerAerospikeFloatSim:940` (ghi phát hiện, KHÔNG tự sửa).

## Acceptance (kiểm-được-bằng-máy)
- [ ] C1 metrics NaN=0/Inf=0 mỗi cột; C3 dup=0; số khớp tool cũ.
- [ ] C2 bắt được giá≤0 và bước nhảy >50% trên tập test giả.
- [ ] Log SLF4J.

## (Code điền) Kết quả / Phát hiện / Quyết định
