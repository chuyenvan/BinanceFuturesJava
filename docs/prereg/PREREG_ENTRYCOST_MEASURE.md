# PREREG_ENTRYCOST_MEASURE — đo kỳ vọng hiệu năng K24+skipFull với chi phí vào THỰC (bucket) — chỉ ĐO, không chọn

MASTER 2026-10-13. Commit trước kernel đầu tiên.

## Mục đích
Số cho quyết định release v1 (khẩu vị rủi ro pilot 10k / DD 40% của owner): ROI/maxDD/Calmar kỳ vọng khi chi phí vào = mô hình EXEC (2c812222) thay vì phí gốc (thiếu chi phí) hay penalty 1,675% (thừa ~20×). KHÔNG chọn/tune gì từ kết quả; cấu hình hệ giữ nguyên.

## Cấu hình
- Nền: `PARITY["ho4p1-c2"]` (K24 + skipFull, phí gốc SIM_RATE_FEE/SLIPPAGE như ho4p1-c2), jar module 7caa968b+ (key ENTRY_COST; parity off md5 ad26fd55 đã PASS ở sim-ec-p-s42).
- Biến thể duy nhất: `SIM_ENTRY_COST_MODE=bucket`, NC 0.0007, C1 0.0018, C2 0.0019, C4 0.0032 (bản thực = CI_trên EXEC), CRASH_ENTRY_PENALTY không khai.
- Seed: 42, 7, 13, 21, 99, 123, 777, 2024.
- Cửa sổ: (D) DEV đến SIM_END 20251231 như ho4p1-c2; (H) HO4 W9 2026-01→09 (bundle Vision HO4 như golive_1009) — HO4 đã dùng làm holdout; ở đây CHỈ ĐO lại cùng cấu hình, không tune.
- Nền so sánh dùng kết quả đã có (không chạy lại): phí gốc 8 seed và stress 8 seed của cùng cửa sổ (ghi nguồn + md5).

## Thước báo (không có luật GO — chỉ đo)
- Mỗi cửa sổ: mean ± sd qua 8 seed và min/max: ΣPnL, ROI trên 35 000, CAGR (D), maxDD MTM, Calmar MTM, n chân, phân bố chân theo bucket + chi phí USD; Δ ghép cặp seed vs phí gốc và vs stress.
- Theo năm (D) và theo quý (H). E0 trên H: mean ΣPnL > 0 và ≥ 6/8 seed > 0 (báo, không quyết).
- Kiểm hợp lệ: log `[ENTRY-COST] SUMMARY mode=bucket` có ở mọi kernel; 12/12 check sim true; jar sha giống nhau; seed 42 (D) n = 3529 & md5 d1d804be (tái lập smoke sim-ec-s-s42).
