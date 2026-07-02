# TASK-118: Exit booking clamp về min(priceSL, bar.open) — fix đã duyệt, chưa áp

- **status:** doing (CCD từ 2026-07-03 sáng — 113 đã xong)
- **depends_on:** TASK-113 phần code (tree không tranh chấp) · GATE xếp lịch Oracle sau GATE-113
- **touches_live_process:** không

## Bối cảnh (đã đo trước đây)
Trailing stop fill trên gap được book tại giá stop thay vì giá thực thi được — ΔPnL ~4,271 (~6% tâng).
Fix đã duyệt: clamp giá book về `min(priceSL, bar.open)` (haircut thực tế ngày crash) — chuẩn hơn bản
`min(priceSL, ticker.maxPrice)` từng nêu. GATE ở đây KHÔNG phải khớp-số (fix ĐỔI số có chủ đích) mà là:
(a) hướng Δ đúng (PnL giảm), (b) độ lớn cùng bậc với đo cũ ~4,271 trên cùng range đo cũ, (c) chỉ các lệnh
exit-trên-gap đổi số, lệnh thường giữ nguyên (log đếm).

## Việc làm
1. Grep điểm book exit trailing trong simulator; áp clamp; SLF4J log đếm số lệnh bị clamp.
2. Unit nhỏ: case gap (open < priceSL) → book tại open; case thường (open ≥ priceSL) → book tại priceSL.
3. Chạy đo trên range đo cũ (local hoặc Oracle SAU khi jobstore rảnh) → ghi Δ vào Kết quả.

## Output: log đo `/d/claudedata/task118_clamp.log` + Kết quả (Δ, số lệnh clamp, commit sha).

## Kết quả
<CCD điền>
