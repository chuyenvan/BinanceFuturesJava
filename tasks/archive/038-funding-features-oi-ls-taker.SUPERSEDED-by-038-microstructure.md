---
id: 038
status: TODO
depends_on: [013, 037]
touches_live_process: false
writes_242_data: false
resource: kaggle
checkpoint: false
max_retry: 2
report: docs/reports/038.md
require_review: true
---

# TASK-038: Funding F4 — feature OI/LS/taker per-coin (sau 013)

- **status:** TODO. `depends_on: [013]` (OI history 226 chunk-tháng) + `[037]` (ghép cùng khung feature). Chờ 013 backfill 226 xong.
- **Nền:** ADR-0011 §5.3 (OI/LS/taker per-coin — chân thiếu nghiêm trọng nhất).

## Feature THÊM (từ 5 set OI 226 do 013)
- **OI:** level, ΔOI, **OI/price divergence** (giá ngang + OI tăng = tích vị thế → squeeze setup), OI×funding (crowdedness).
- **Long/short:** top-trader account & vị thế, global account ratio.
- **Taker:** buy/sell vol ratio.
- Chuẩn hoá per-coin (z/percentile lịch sử coin) + cross-sectional (so coin cùng mốc).

## Cách làm
- Đọc 5 set OI 226 (chunk-tháng `SYMBOL_yyyyMM`, reader khớp `OiMetricSets`/DataManager của 013). Ghép vào khung feature funding (037), **align mốc 5m**. Kaggle (đọc 226).

## Validate (require_review)
- Recompute OI feature vài mốc; ΔOI/divergence đúng; align với 037 không lệch thời gian; coverage per-coin (delist có OI tới ngày chết — LS/taker dừng sớm hơn OI là data thật, xem report 013).

## (Code / Kết quả điền)
