# PRE-REG — Vol-target sizing trên nền G2+FLAT3 (sim-tier, owner 09-30 mục 2)
Chốt TRƯỚC số. Baseline B0 = G2+FLAT3 (profiles/g2_flat3.properties, sim md5 650c386f, n2517). Jar sim-jar-gdv2 (key-driven, KHÔNG build).
LÝ DO chọn vol-target (không phải breadth): breadth/regime đã NULL 9 vòng với cơ chế rõ (gate đổi phơi nhiễm, không đổi edge; lệnh breadth-thấp lãi ngang breadth-cao) — KHÔNG re-run.
Vol-target là lever sim-tier DUY NHẤT chưa test sạch (TASK5 2026-09-20 "NULL/1 lỗi thiết kế"). Nền G2 (margin nhỏ, nhiều lệnh) tạo dư địa cho sizing động.

## BẮT BUỘC đọc trước: docs/prereg/PREREG_VOL_TARGET.md + RESULT TASK5 (lỗi thiết kế cũ là gì) + code SIZE_VOL_TARGET (Configs + Simulator).
Xác định ĐỦ tham số VT (target vol level, lookback, cap) — nếu TASK5 lỗi ở tham số/định nghĩa, sửa cho đúng và GHI RÕ khác gì bản cũ (amendment).

## Arm (k=3 ⇒ inflate sqrt(2 ln 3)=1.482). Nền G2+FLAT3, chỉ thêm key sizing:
| arm | SIZE_VOL_TARGET_MODE | ghi chú |
|---|---|---|
| B0 | OFF (=g2_flat3) | parity md5 650c386f BẮT BUỘC |
| VT_COIN | COIN | size mỗi lệnh nghịch biến vol coin (target vol/coin) |
| VT_PORT | PORTFOLIO | scale toàn danh mục theo vol thị trường |
(+ tham số VT giữ như PREREG_VOL_TARGET nếu hợp lệ; nếu phải sửa lỗi TASK5, khai amendment TRƯỚC khi xem số.)

## Luật §9 (đọc: trailing không đổi n; VT ĐỔI size → đổi maxDD/CAGR, có thể đổi n qua ngân sách)
- Cổng: B0 md5 650c386f. |n_arm − 2517| >10% ⇒ ghi rõ.
- T1 rủi ro tuyệt đối §9 mỗi arm (maxDD MTM ≤40%/năm, UW ≤250, quý xấu ≥−20%, 0 năm âm, conc ≤15%). VT KỲ VỌNG cải thiện maxDD/UW.
- VT thắng B0 ⇔ ĐẠT T1 VÀ Calmar_MTM > B0 VÀ bootstrap CI ΔCalmar_MTM (block-72h + episode, NREP 2000, seed 20260905, inflate 1.482) không chứa 0.
- Báo mọi arm: Calmar_MTM, CAGR, maxDD phút, UW, quý xấu, bảng quý+năm (qstat_r4.py), phân bổ ROI (roidist.py). So VT có mua được maxDD/UW bằng cách hy sinh CAGR bao nhiêu.
- Không tune sau số. KHÔNG chạm 242/shadow/holdout 2026. DEV ≤2025-12-31. Kaggle. Python logging.
Kết quả: docs/result/RESULT_VOLTARGET_G2.md + json. Commit + push.
