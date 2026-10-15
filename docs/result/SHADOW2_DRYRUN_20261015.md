# SHADOW2 vs SIM — dry-run 2026-10-15 (QUEUE_1015 P3)

Pre-reg thước/luật: `docs/prereg/PREREG_SHADOW2_PROMOTION.md`. Script: `research/shadow/compare_shadow2.py`.

## Trạng thái: **SCRIPT XONG, DRY-RUN BLOCKED** (lý do ở §3)

## 1. Đã làm
- `research/shadow/compare_shadow2.py` — so lệnh paper `shadow-c3b` (`~/shadow_c3b/ledger.csv`, CHỈ ĐỌC) với sim cùng cấu hình (K24 + `GATE_QUOTA_SKIP_WHEN_FULL=true`, chi phí vào OFF).
  - Chuẩn hoá symbol (bỏ hậu tố USDT/USDC/BUSD), thời gian shadow epoch-ms UTC → GMT+7 để khớp `start` của sim.
  - Khớp cùng symbol, phút vào lệch ≤ `--tol-min` (mặc định ±1′), greedy 1-1.
  - Loại cửa sổ KHÔNG đạt chuẩn `2026-10-12 09:06 → 2026-10-15 14:49` (mặc định `--drop-excluded true`).
  - Xuất: `n_shadow`, `n_sim`, `matched`, tỉ lệ khớp 2 phía, chênh giá vào (median/mean/maxabs), chênh PnL, **lệnh một-bên + lý do**.
- Smoke: parse đúng cả 2 định dạng — shadow ledger 18 lệnh; sim `printDone.csv` (gqsf-a1) 3 541 lệnh.

## 2. Số đo trên ledger hiện có (2026-10-15 ~12:15 +07)
`~/shadow_c3b/ledger.csv` chỉ có **18 lệnh**: **17 lệnh cùng phút `2026-10-08 22:20 +07`** (burst) + **1 lệnh `2026-10-13 22:24 +07`** (USUSDT). `legs.csv` 27 dòng; `open_positions.csv` 7 vị thế mở đều mở lúc `2026-10-08 22:20`.

## 3. Vì sao DRY-RUN (10-11 → 10-12 09:00) không chạy được — BLOCKED
1. **Shadow vắng lệnh trong cửa sổ dry-run:** lọc `--start 2026-10-11 --end 2026-10-12T09:00` ⇒ **0 lệnh shadow** (ledger chỉ có lệnh ở 10-08 22:20 và 10-13 22:24) ⇒ **không có gì để so**. Cửa sổ 10-08→10-09 (17 lệnh) nằm ngoài dry-run đã khai trước; muốn dùng phải có pre-reg riêng.
2. **Chưa có sim cùng kỳ:** sim K24+skipFull trên Vision cho 10-10→10-12 cần (a) bundle ticker dựng từ Vision (exporter `ho4p1-jar-exp` sha `99c5f040`, docs `HO4_P1.md` §S1) — **chưa dựng**, và (b) chạy 1 kernel Kaggle — nhưng template sim khai `sim-jar-nsel` (jar `b7c89f09`) **đã bị xoá khỏi Kaggle** (xem `docs/data/KAGGLE_REQUIRED.md` §P1-RESIDUAL) ⇒ kernel không chạy được tới khi khôi phục dataset.
3. **Tuần thật** (10-15 15:00 → 10-22) bắt đầu **sau** thời điểm này ⇒ báo cáo tuần chưa đến hạn.

## 4. Việc cần để mở khoá
- Đẩy lại `chuyendinh/sim-jar-nsel` (jar `b7c89f09`, có sẵn `~/src_wt_nsel/target/binance-java-sdk-1.2.4.jar`, sha trùng) — **chờ owner xác nhận** (owner vừa dọn Kaggle).
- Dựng bundle ticker Vision cho cửa sổ cần đo (10-10→10-22, lead-in) theo exporter HO4.
- Sau 10-22 (hoặc đủ ≥4 tuần theo pre-reg) chạy `compare_shadow2.py` và viết `docs/result/SHADOW2_WEEK_<n>.md`.
