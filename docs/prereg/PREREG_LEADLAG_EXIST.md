# PREREG_LEADLAG_EXIST — test TỒN TẠI lead-lag BTC→alt (giá-only, DEV, không sim)

MASTER 2026-10-13. Commit TRƯỚC khi viết/chạy scorer. Không dùng dữ liệu 2026 (HO4 đã dùng), không mở kho backcast ở vòng này.

## 0. Bối cảnh
- Chưa từng đo lead-lag giờ/phút. Đã có: beta_decomp T170 (61a7fc7e, β 0,049, chủ yếu alpha), FEATGRP G1 rs_btc NULL (rank-IC âm), ALT_REGIME_WAVES, HEDGE_OVERLAY NULL.
- Mục tiêu: quyết định rẻ có nên làm feature lead-lag (S1/gate) hay ĐÓNG hướng.

## 1. Dữ liệu
- `/home/ubuntu/java/fsrun/CLOSES_1H.bin` (14 B BE: ts i8 close-time, sym i2, close f4; map `/home/ubuntu/selector_pred_out/symbol_map.csv`). Cửa sổ 2022-01-01 00:00 → 2025-12-31 23:00 UTC. BTC = id 1.
- Universe mỗi giờ t: alt (loại BTCUSDT, ETHUSDT, BTCDOMUSDT, stable USDC/FDUSD/TUSD/BUSD) có close ở t−73h…t+4h đủ (không thiếu giờ) và ≥ 30 ngày lịch sử.
- Chân vào lệnh (H2): ledger chân K24+skipFull stress mà EXEC dùng (docs/result/EXEC_RESULT.md, 23 654 chân DEV 2022–25); thời điểm vào = t_dec nến M.

## 2. Định nghĩa (causal, chỉ dùng dữ liệu ≤ t)
- r_x(a,b] = log(close_b/close_a).
- β_i(t): OLS r_i 1h ~ r_BTC 1h trên 30 ngày [t−30d, t−k]; cần ≥ 500 điểm.
- Gap: g_i,k(t) = β_i(t)·r_BTC(t−k, t] − r_i(t−k, t], chuẩn hoá chia σ_i 1h 7 ngày. k ∈ {1h, 3h}.
- Đích: idio fwd y_i,h(t) = r_i(t, t+h] − β_i(t)·r_BTC(t, t+h], h ∈ {1h, 4h}.
- Đối chứng reversal: rev_i,k(t) = −r_i(t−k, t]/σ_i. Gap "thuần" g⊥ = phần dư hồi quy cắt ngang g trên rev tại mỗi t.

## 3. Giả thuyết + thước
- H1 (toàn thị trường): IC_t = Spearman cắt ngang(g⊥_i,k(t), y_i,h(t)) mỗi giờ có ≥ 30 coin. Thống kê = mean IC; CI95 bằng block bootstrap theo ngày, block 10 ngày, NREP 2000, seed 20261013. 4 biến thể (k × h) ⇒ CI nở √(2 ln 4) = 1,665 quanh mean.
- H2 (sự kiện của hệ): tại mỗi chân, g_k=3h (giờ đóng gần nhất ≤ t_dec), chia tercile theo năm; Δ = mean ret_4h(top) − mean ret_4h(bottom), ret_4h = log(close(t_dec+4h)/close_M) tính bằng CLOSES_1H giờ đóng gần nhất ≥ t_dec+4h. CI95 block bootstrap theo ngày (như trên). Báo kèm h=1h, k=1h (không dùng để quyết).

## 4. Luật quyết định (chốt trước)
- GO (sang vòng feature + pre-reg sim): H1 biến thể chính (k=3h, h=4h) mean IC > 0 với CI nở dưới > 0, VÀ ≥ 3/4 năm mean IC > 0, VÀ H2 Δ > +0,30% với CI95 dưới > 0.
- Ngược lại: ĐÓNG hướng lead-lag giờ (ghi research_1012 + docs/result). Không chạy lại với k/h khác.
- Báo đầy đủ mọi biến thể, theo năm, số giờ/coin/chân dùng.

## 5. Kiểm hợp lệ trước khi báo
- V1: tái tạo 3 giá trị β_i, g, y bằng tay cho 3 (coin, t) ngẫu nhiên (seed cố định) — khớp 1e-6.
- V2: kiểm causal — xáo r_BTC theo thời gian (placebo) ⇒ mean IC H1 phải |·| < 1/3 mean IC thật hoặc CI chứa 0.
- V3: số chân H2 ghép được ≥ 95% của 23 654; báo phần thiếu.
- Scorer + output (json) commit; md5 output ghi trong docs/result/RESULT_LEADLAG_EXIST.md.
