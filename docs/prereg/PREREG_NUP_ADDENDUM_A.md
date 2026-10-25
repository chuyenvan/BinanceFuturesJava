# PREREG_NUP — ADDENDUM A (A6 calibration) — 2026-10-26

Trạng thái: viết **trước khi chạy bất kỳ arm nào** (mới chỉ có 2 run cổng B0 và 1 run A7-off;
chưa có số arm). Không đổi §1/§3/§4. Chỉ làm rõ §1.1: chọn `SIM_F_BASE` sao cho **notional leg0
= 0,67 × B0** chứ không phải `SIM_F_BASE` = 0,67 × B0 (vì throttle `1−U/U_MAX` thay đổi khi U giảm).

## A.1 Vì sao cần hiệu chuẩn

`budget = equity × SIM_F_BASE × (1−U/U_MAX) / ladder` (`TradeUtils.java:142`). Nếu chỉ nhân
`SIM_F_BASE` với 0,67 thì U giảm theo, throttle tăng, nên notional thực tế **không** giảm đúng 0,67.
Trên B0 (seed S7), phân bố U tại t0 của leg0 có median 0,144; hệ quả notional ratio của cách
`F_BASE=0.01005` là **0,740** (ước lượng từ printDone + equity MTM, chưa chạy A6) — ngoài band §1.1.
Vì vậy phải hiệu chuẩn `SIM_F_BASE`.

## A.2 Công thức CHỐT (chạy sau khi có A4 seed a1,s7; không dùng PnL)

Với mỗi cụm (leg0) của A4:
- `U = Σ margin các leg đang mở tại t0 / equity(t0)` (equity MTM phút, cùng pipeline GOLIVE).
- `f(rF, U) = rF × (1 − rF·U/U_MAX) / (1 − U/U_MAX)`, `U_MAX=0.60`.
- Giải `rF` bằng bisection trên [0,1] sao cho `median_U f(rF,U) = 0.67`.
- `SIM_F_BASE(A6) = 0.015 × rF`, làm tròn 6 chữ số thập phân.
- Chỉ dùng A4 seeds `a1, s7`; áp cùng F cho 4 seed Pha 1 và 4 seed Pha 2.

Sau khi chạy A6: median `notional leg0(A6)/notional leg0(A4)` trên 4 seed phải ∈ [0,64; 0,70]
(§1.1). Ngoài band ⇒ **dừng A6**, báo, không tự đổi F lần hai.

## A.3 Ghi chú

- Đây là hiệu chuẩn **size**, không dùng bất kỳ PnL/DD nào để chọn; không đổi luật G1–G4.
- `SIM_F_BASE` là key duy nhất tuyến tính với notional leg0; `U_MAX`, `DCA_GRID_SCALE`,
  `DCA_GRID_WEIGHTS`, tier multiplier giữ nguyên.
- File F đã chốt: `research/nup/a6_fbase.json` (ghi rF, F, T median, seeds, hash printDone A4 dùng).
