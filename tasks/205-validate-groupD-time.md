---
id: 205
status: TODO
depends_on: [200]
touches_live_process: false
writes_242_data: false
resource: oracle
checkpoint: false
max_retry: 2
report: docs/reports/205.md
require_review: true
---

# TASK-205 [WS1-D] — Validator nhóm D: Thời gian (D1-D3)

## Mục tiêu (1 câu)
Bắt lệch timezone, gap thời gian, off-by-one nến — nguồn "SKIP lặng" và look-ahead nội nến.

## Scope
**Trong:** `D1FundingTzValidator` (settlement funding đúng 00/08/16h UTC), `D2TimeGapValidator` (WRAP `CheckGapMarketObject/CheckGapTicker`: đếm phút/ngày=1440, log ngày thiếu), `D3IntrabarLookaheadValidator` (VERIFY `Configs.BLOCK_INTRABAR_LOOKAHEAD=true`).
**Ngoài:** lấp gap (WS3).

## Acceptance (kiểm-được-bằng-máy)
- [ ] D2 metrics số ngày <1440 phút + danh sách; khớp `CheckGap*` hiện có.
- [ ] D3 FAIL nếu flag look-ahead tắt.
- [ ] Log SLF4J.

## (Code điền) Kết quả / Phát hiện / Quyết định
