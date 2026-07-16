---
id: 141
status: DONE
depends_on: []
touches_live_process: false
writes_242_data: false
resource: oracle
checkpoint: false
max_retry: 1
report: docs/reports/141.md
require_review: true
---

# TASK-141: Xác nhận Java — CAGR thật của cấu hình khuyến nghị (ret2 + giveback 1.0)

## Mục tiêu (1 câu)
Trả lời thẳng "cấu hình khuyến nghị có đạt ≥20%/năm không" bằng sim full-history engine Java, con số
tích hợp mà cả phiên chưa có (mới chỉ đo từng thành phần rời).

## Scope
**Trong scope:**
- Chạy `SimulatorMarketLevelTicker1MStopLoss` full-history trên `wfo_dataset_v4` (funding ret2) với
  `TS_GIVEBACK_RATIO=1.0`, `SIM_END_DATE=20260601`, `WRITE_SIM_STORAGE=true`.
- Chạy `TraceData2Test` → PnL theo năm/level. Tính CAGR (balance đầu→cuối), maxDD, phân bố năm.
- Nếu job b5d0aw99s (`final_config_result.md`) đã xong từ phiên trước → đọc lại, KHÔNG chạy lại.

**Ngoài scope:** KHÔNG sweep thêm tham số; KHÔNG đổi label. Chỉ đo đúng 1 cấu hình.

## Pre-register
- Đạt: CAGR ≥ 20%/năm VÀ maxDD ≤ 40% VÀ không năm nào âm.
- Báo thẳng CAGR thực dù thấp (baseline cũ chỉ ~2.4%/năm — nếu vẫn thấp, đó là bằng chứng long-only-pump
  một mình không đủ, KHÔNG che).

## HÀNG RÀO
- `pgrep 'WfoWorker|SimulatorMarketLevel'` rỗng trước khi đụng jar. Không ghi đè jar khi có job chạy.
- `setsid nohup`. Trả `config.properties` về `config.properties.bak2` sau khi xong (WRITE_SIM_STORAGE=false).

## Acceptance criteria
- [ ] Report 141.md: CAGR, maxDD, bảng balance theo năm, PnL theo level (DCA vs PST).
- [ ] So với baseline giveback mặc định (sim_final_result.md) để thấy delta.
- [ ] Verdict pre-register: đạt/không đạt 20%/năm.

---
## (Code điền) Kết quả
## (Code điền) Phát hiện ngoài scope
## (Code điền) Quyết định phát sinh
