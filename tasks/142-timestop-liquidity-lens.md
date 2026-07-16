---
id: 142
status: DONE
depends_on: []
touches_live_process: false
writes_242_data: false
resource: oracle
checkpoint: false
max_retry: 1
report: docs/reports/142.md
require_review: true
---

# TASK-142: Time-stop dưới lăng kính THANH KHOẢN (không phải PnL tối đa)

## Mục tiêu (1 câu)
Đo đánh đổi "mất bao nhiêu PnL để KHÔNG vị thế nào kẹt vốn > ~1 năm" — vì Uni đã chốt thanh khoản là
mục tiêu, nên time-stop (trước bị loại chỉ theo PnL) cần đánh giá lại theo thước mới.

## Scope
**Trong scope:**
- Sim full-history (wfo_dataset_v4, giveback 1.0) với `TIME_STOP_HOURS` ∈ {đủ dài: 6480=270 ngày,
  8640=360 ngày}. So với không time-stop.
- Đo: (a) PnL mất bao nhiêu so với không time-stop; (b) số vị thế bị cắt vì quá hạn; (c) thời gian giữ
  lệnh lâu nhất (max holding) trước vs sau — xác nhận time-stop thật sự chặn được kẹt >1 năm.

**Ngoài scope:** KHÔNG kết luận time-stop "tốt/xấu" — trình đánh đổi cho Uni quyết ngưỡng.

## Pre-register
- Time-stop 270/360 ngày "chấp nhận được" nếu PnL mất < 15% tổng VÀ chặn được mọi vị thế >1 năm.

## HÀNG RÀO
- `TIME_STOP_HOURS` đo từ leg ĐẦU cụm DCA (clusterFirstLegTime) — đã implement. Verify không bị DCA reset.
- pgrep rỗng trước jar. setsid nohup. Trả config về bak2.

## Acceptance criteria
- [ ] Report 142.md: bảng {no-stop, 270d, 360d} × {PnL, maxHolding, #cắt-quá-hạn}.
- [ ] Xác nhận time-stop chặn được kẹt >1 năm (maxHolding sau ≤ ngưỡng).

---
## (Code điền) Kết quả
## (Code điền) Phát hiện ngoài scope
## (Code điền) Quyết định phát sinh
