# TSX_V2_SIM — bảng (median [min; max] 8 seed; Δ = biến thể − X14 cùng seed)

## 1. Headline DEV

| Chỉ số | CTL |
|---|---|
| X14 CAGR22 % | 39,28 [39,28; 39,28] |
| Biến thể CAGR22 % | 39,28 [39,28; 39,28] |
| ΔCAGR22 pp | +0,00 [+0,00; +0,00] |
| ΔΣPnL USD | +0 [+0; +0] |
| X14 DD22 % | -22,20 [-22,20; -22,20] |
| Biến thể DD22 % | -22,20 [-22,20; -22,20] |
| ΔDD22 pp | +0,00 [+0,00; +0,00] |
| ΔDD toàn kỳ pp | +0,00 [+0,00; +0,00] |
| ΔCalmar22 | +0,000 [+0,000; +0,000] |
| ΔUW22 ngày | +0,0 [+0,0; +0,0] |
| DD22 seed tệ nhất X14 → biến thể | -22,20 → -22,20 |
| seed ΔCAGR22>0 / ΔCalmar22≥0 | 0/8 / 1/8 |

## 2. Hoạt động DEV (2021-07..2025-12): X14 / biến thể / Δ (median)

| Chỉ số | CTL |
|---|---|
| Số cụm | 3 468 / 3 468 / +0 [+0; +0] |
| Số đợt vào | 772 / 772 / +0 [+0; +0] |
| Số leg | 3 531 / 3 531 / +0 [+0; +0] |
| Notional vào (Σ q·entry) USD | 3 331 481 / 3 331 481 / +0 [+0; +0] |
| Phơi nhiễm TB % | 5,75 / 5,75 / +0,00 [+0,00; +0,00] |
| Phơi nhiễm max % | 60,2 / 60,2 / +0,0 [+0,0; +0,0] |
| Giữ TB h | 51,0 / 51,0 / +0,0 [+0,0; +0,0] |
| Cụm cắt time-stop | 509 / 509 / +0 [+0; +0] |
| Δ số đợt vào TB % (C5) | +0.00 |

## 3. Cụm hoãn và vốn giam (X14 → biến thể, median)

| Chỉ số | CTL |
|---|---|
| Cụm hoãn/seed | 174 → 174 [174; 174] |
| ΣPnL cụm hoãn | -23 113 → -23 113 [-23 113; -23 113] |
| Giữ thêm TB h | 179 → 179 [179; 179] |
| Vốn giam TB giờ ON % equity | 7,7 → 7,7 [7,7; 7,7] |
| Vốn giam đỉnh % equity | 54,9 → 54,9 [54,9; 54,9] |
| Phơi nhiễm TB giờ ON % | 16,0 → 16,0 [16,0; 16,0] |
| Giờ ON | 5 112 → 5 112 [5 112; 5 112] |
| V4 cụm hoãn = Java | 1/1 |
| Thoát (gộp 8 seed) | cut_flag_off 85, arm_trail 25, cut_cap 64, sl_other 0 |

## 4. Crash-buy lỡ so X14 (khoá sym+anchor; median/seed: số chỉ-X14 (PnL) | số chỉ-biến-thể (PnL))

| Phạm vi | CTL |
|---|---|
| Toàn DEV | 0 (+0) \| 0 (+0); net +0 |
| LUNA (2022-04-27..2022-07-06, cửa sổ +15d) | 0 (+0) \| 0 (+0); Δcụm mới +0 |
| FTX (2022-11-10..2022-12-23, cửa sổ +15d) | 0 (+0) \| 0 (+0); Δcụm mới +0 |
| 04/2024 (2024-04-13..2024-05-24, cửa sổ +15d) | 0 (+0) \| 0 (+0); Δcụm mới +0 |
| 06/2024 (2024-06-18..2024-07-26, cửa sổ +15d) | 0 (+0) \| 0 (+0); Δcụm mới +0 |
| 03/2025 (2024-12-19..2025-03-24, cửa sổ +15d) | 0 (+0) \| 0 (+0); Δcụm mới +0 |
| 10-12/2025 (2025-10-11..2025-12-31, cửa sổ +15d) | 0 (+0) \| 0 (+0); Δcụm mới +0 |

## 5. Phân rã ΔΣPnL = direct (replay) + phần còn lại (slot/lãi kép/lệnh khác)

| | CTL |
|---|---|
| ΔΣPnL sim | +0 [+0; +0] |
| direct (replay) | +0 [+0; +0] |
| phần còn lại | +0 [+0; +0] |
| seed ΔΣPnL>0 | 0/8 |
| kiểm direct = phaseB (max\|Δ\|) | 0.0e+00 |

## 6. ΔPnL thực hiện theo kỳ đóng (median [min; max])

| Kỳ | CTL |
|---|---|
| 2021H2 | +0 [+0; +0] |
| 2022 | +0 [+0; +0] |
| 2023 | +0 [+0; +0] |
| 2024 | +0 [+0; +0] |
| 2025 | +0 [+0; +0] |
| ΔDD MTM phút trong năm (2022) pp | +0,00 [+0,00; +0,00] |

## 7. Theo đợt (TB 8 seed): direct (replay) | Δ đoạn (sim) — chỉ đợt có |giá trị| ≥ 50

| Đợt | CTL |
|---|---|
| **Tổng** | +0 \| +0 |
| Bỏ đợt lớn nhất (C4) | +0 (2021-07) \| +0 (2021-07) |

## 8. Luật ứng viên v1.2

| | CTL |
|---|---|
| C1 | ✘ |
| C2 | ✘ |
| C3 | ✔ |
| C4 | ✘ |
| C5 | ✔ |
| candidate | ✘ |

Ứng viên: [] → chọn None

