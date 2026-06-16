---
id: 037
status: TODO
depends_on: [036]
touches_live_process: false
writes_242_data: false
resource: kaggle
checkpoint: false
max_retry: 2
report: docs/reports/037.md
require_review: true
---

# TASK-037: Funding F3 — export feature funding KHÔNG cần OI (per-coin sâu + volume + cấu trúc giá + cross-sectional)

- **status:** TODO. `depends_on: [036]` (tên feature sạch + đường export đúng trước khi thêm). **Độc lập 013** (KHÔNG dùng OI) → chạy song song nhánh gate.
- **Nền:** ADR-0011 §5.3 (THÊM, phần không-OI) + cross-sectional.

## Feature THÊM (từ `funding_data` + kline/ticker đã có — KHÔNG OI)
- **Funding sâu per-coin:** percentile/z-score theo lịch sử CHÍNH coin (bất thường tương đối); **độ bền** (số kỳ liên tiếp cùng dấu, tổng funding N kỳ — bắt "nuôi shorter"); `|funding|` + dấu.
- **Volume per-coin:** volume-z (cur/avgN — `getSumVolume`/`getAverageVolume` đã có), volume-trend, taker-buy ratio (nếu có ở ticker).
- **Cấu trúc giá:** distFromHigh (đối xứng `distFromLow24H` đã có), vị trí trong range, nén biên độ (range/ATR co — pre-breakout), relative-strength vs BTC/basket.
- **Cross-sectional:** rank/z của funding/volume/momentum trong số coin CÙNG mốc (selector so coin-với-coin).
- **GIỮ market-context cũ** (btcMom, breadth, basket) — tỉa sau bằng importance, KHÔNG bỏ tay (user §5.3).

## Cách làm
- Mở rộng export feature funding (đường THẬT xác định ở 036), thêm nhóm trên. Per-coin, ghi `.bin.gz`/CSV như cũ, từ 2021, warmup, extractor stateful liên tục (không reset).
- Chuẩn hoá cross-sectional tại mỗi mốc. KHÔNG dùng OI/LS (để 038). Chạy Kaggle (đọc 226).

## Validate (require_review)
- Recompute vài feature vài mốc khớp; **không look-ahead** (percentile/z expanding, không dùng tương lai); cross-sectional đúng số coin/mốc; #dòng/coverage hợp lý (so lifecycle 010).

## (Code / Kết quả điền)
