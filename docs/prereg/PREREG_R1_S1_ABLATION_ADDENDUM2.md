# PREREG_R1_S1_ABLATION — ADDENDUM 2 (2026-11-10, TRƯỚC khi chạy bất kỳ kernel nào, chưa nhìn số)

**Lý do.** Lần build A3 đầu (sha 0d6e3781…) có G-FULL=False. Hai fold không đạt điều kiện (b) của ADDENDUM 1 ("≥ 99,9 % dòng pool cũ ghép được"):

| fold | ghép được / pool | tỉ lệ |
|---|---|---|
| 20250701 | 972 929 / 974 118 | 99,878 % |
| 20251001 | 3 480 757 / 3 499 202 | 99,473 % |

Các fold khác đạt. Trên mọi fold, max|Δ| = 0 và coverage ≥ 99,95 %.

**Chẩn đoán** (`research/r1_s1/r1_diag.py`):
- 100 % số dòng không ghép được (1 189 và 18 445) là các key (ts, coin) có trong `pred_s1a2x1` nhưng **không có trong bin net015 ở tick đó**.
- Không có dòng nào thiếu vì NaN p, NaN điểm ref, trùng key, hay thiếu cả tick.
- Coin đó vẫn có mặt trong bin ở các tick khác.

Vì sim chỉ xếp hạng các key có trong bin, những key này không bao giờ vào sim, ở A0 lẫn A3. Do đó chúng không ảnh hưởng gì đến phép đo.

**Sửa định nghĩa (chỉ đổi mẫu số).** G-FULL(b) mới:

  matched ≥ 99,9 % × (số dòng pool cũ trong khoảng fold − số key pool vắng mặt trong bin)

kèm max|Δ| ≤ 1e-6 như cũ. Các điều kiện (a) và (c) giữ nguyên.

Báo cáo vẫn ghi cả cờ cũ `G_FULL_ADD1_raw` (= False) cho minh bạch. Không đổi cách chấm điểm S1, không đổi bin, không đổi tiêu chí C1/C2/C-LIVE, seed, metric.

**Tái lập.** Build lại bằng code đã sửa (chỉ thay phần báo cáo) phải cho ra đúng sha bin 0d6e3781… Kết quả ghi trong `a3_report.json`.
