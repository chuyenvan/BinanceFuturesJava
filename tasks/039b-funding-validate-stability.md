---
id: 039b
status: CANCELLED
owner: headless
depends_on: []
touches_live_process: false
writes_242_data: false
resource: kaggle
kaggle_slots: 3
checkpoint: false
max_retry: 2
report: docs/reports/039b.md
require_review: true
---

# TASK-039b: Validate tính ỔN ĐỊNH của funding selector

## Mục tiêu
Trả lời 2 câu trước khi tin model để generate/triển khai:
1. **Ổn định theo thời gian (regime):** LIFT/rankIC có sống sót qua bull/bear không, hay chỉ đẹp nhờ vài giai đoạn? (đo per-quý trên test).
2. **Lặp lại (ổn định code+data):** đổi seed có ra cùng kết luận không? (variance nhỏ → đáng đóng version).

Đây là điều kiện để bước generate (039c) đáng bỏ tài nguyên.

## Bối cảnh
- Train code đã có `REPORT_QUARTERS=1` (đo LIFT/rankIC từng quý trên test) và `SEED` (commit c0c4d11).
- Đã chạy nền 2 kernel `funding-val-s42`, `funding-val-s7` (HORIZON=4h, REPORT_QUARTERS=1). Kiểm trạng thái trước, dùng lại nếu xong.

## Việc cần làm

### Bước 1 — Hoàn tất ma trận validate
Chạy `REPORT_QUARTERS=1` cho **horizon {4h, 12h} × seed {42, 7, 123}** (2×3 = 6 run; 4h-42 và 4h-7 đã có thì chỉ chạy bổ sung).
- 4h và 12h là 2 horizon đáng giá nhất (base thấp, room LIFT lớn). 24h/72h base cao → bỏ qua ở validate (LIFT đã sát baseline).
- Mỗi kernel: header HORIZON=<H>, SEED=<S>, REPORT_QUARTERS=1, resolve path đệ quy. id `chuyendinh/funding-val-<H>-s<S>`.

### Bước 2 — Monitor (bắt lỗi) + tải metrics
Poll until complete/error mỗi kernel. Tải `metrics_<H>.json` (có field `per_quarter` + `seed`).

### Bước 3 — Tổng hợp + đánh giá
Lập 2 bảng trong report:
- **Bảng A (ổn định regime):** hàng = quý (2024Q4..2026Q2), cột = LIFT & rankIC & base & N. Đặc biệt soi quý bear/sập.
- **Bảng B (lặp lại seed):** hàng = (horizon), cột = LIFT mỗi seed + độ lệch (max-min).

## OUTPUT FILE (rõ ràng)
| File | Nơi | Nội dung |
|---|---|---|
| `metrics_<H>_s<S>.json` ×6 | Kaggle → `/d/claudedata/k039/val/` | metrics + per_quarter + seed |
| `docs/reports/039b.md` | repo | Bảng A (per-quý) + Bảng B (per-seed) + verdict ổn định |

## TIẾN TRÌNH theo dõi (ghi report)
1. Trạng thái 6 kernel (slug, status, thời gian).
2. per_quarter LIFT từng run.
3. Tổng hợp 2 bảng.

## NGHIỆM THU (pass/fail — tiêu chí ĐO, không cảm tính)
- [ ] **Ổn định regime:** LIFT > 1.20 ở ≥ 75% số quý test (cho 4h). Nếu LIFT < 1.0 (tệ hơn ngẫu nhiên) ở bất kỳ quý nào → ghi rõ là cờ đỏ.
- [ ] **Lặp lại:** LIFT giữa 3 seed lệch (max−min) < 0.10 cho mỗi horizon → code+data ổn định. Lệch lớn → FAIL, báo người.
- [ ] Report có đủ 2 bảng + verdict thẳng (ổn / không ổn / chỉ ổn ở regime nào).
- KHÔNG tự kết luận "dùng được" — báo người quyết generate hay không.

## Kiểm soát tài nguyên
- Tối đa 3 slot Kaggle đồng thời (kaggle_slots=3). Phối hợp với 039a (nếu 039a đang chạy, validate chờ slot hoặc giảm batch).
- Read-only Kaggle dataset, không đụng 226/live.
