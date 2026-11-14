# IND_COMBO Pha 0 — SELECTION (khoá TRƯỚC khi đọc Y CONFIRM 2024–25)

Prereg vz_e1_wt 14ed6c00 (PREREG_IND_COMBO.md md5 1735a8eb, IND_COMBO_P0_PLAN.md md5 f15a6080). Sinh tự động từ explore.json/selection.json.

## Mẫu EXPLORE (2022–23, +07)
- Leg nt-x14 PREDICT 8 seed: 10256 leg, 117 cụm đợt (≤ 60′, hợp 8 seed); theo năm {'2022': 4571, '2023': 5685}. Số cụm CONFIRM (chỉ đếm, không Y): 113 (leg 11298).
- Khử trùng (|ρ Spearman| > 0,80 với indicator đứng trước còn giữ; bảng 45 feature S1 không có trong dump): giữ 16 = C1, C3, C4, C8, C9, C10, C11, C12, C17, C18, C19, C20, M1, M3, M5, M6.
- Bỏ: C2 (~C1 ρ 0.831); C5 (~C1 ρ 0.868); C6 (~C1 ρ 0.881); C7 (~C1 ρ 0.89); C13 (~C3 ρ 0.943); C14 (~C3 ρ 0.824); C15 (~C3 ρ 0.809); C16 (~C3 ρ 0.94); M2 (~C3 ρ 0.803); M4 (~C3 ρ 0.817)

## Track S — EXPLORE (partial Spearman IC, khử rank(hạng S1), rank(điểm S1), dummy năm; CI90 bootstrap cụm 2 000, seed 20261114)

| X | IC | CI90 | p2 | FDR q0,10 | IC 2022 | IC 2023 | n |
|---|---:|---|---:|:-:|---:|---:|---:|
| C17 | -0.1217 | [-0.1922; -0.0382] | 0.0092 | x | -0.1866 | -0.0319 | 6923 |
| C11 | +0.1064 | [+0.0361; +0.1731] | 0.0107 | x | 0.1191 | 0.0923 | 9693 |
| C18 | -0.1008 | [-0.1755; -0.0095] | 0.0489 |  | -0.1908 | -0.0113 | 10209 |
| M3 | -0.1084 | [-0.2130; -0.0081] | 0.0811 |  | -0.2986 | 0.0109 | 10256 |
| C4 | +0.0681 | [-0.0172; +0.1472] | 0.1839 |  | 0.0409 | 0.0818 | 10209 |
| C8 | +0.0607 | [-0.0107; +0.1405] | 0.1938 |  | 0.0163 | 0.0895 | 7730 |
| C19 | -0.0659 | [-0.1404; +0.0307] | 0.2075 |  | -0.2228 | 0.0672 | 9961 |
| C3 | -0.0528 | [-0.1331; +0.0322] | 0.2919 |  | -0.1629 | 0.0797 | 8690 |
| M1 | -0.0606 | [-0.1555; +0.0523] | 0.3419 |  | -0.0323 | -0.018 | 10256 |
| M6 | -0.0501 | [-0.1467; +0.0612] | 0.4230 |  | -0.1588 | 0.048 | 10256 |
| C20 | -0.0216 | [-0.0921; +0.0438] | 0.6013 |  | 0.0097 | -0.0549 | 10244 |
| C9 | +0.0254 | [-0.0629; +0.1166] | 0.6483 |  | -0.0229 | 0.0493 | 10027 |
| C1 | +0.0196 | [-0.0501; +0.0942] | 0.6567 |  | -0.0666 | 0.0906 | 10158 |
| C12 | +0.0211 | [-0.0567; +0.1085] | 0.6775 |  | 0.03 | 0.0129 | 8387 |
| C10 | +0.0029 | [-0.0983; +0.1134] | 0.9650 |  | -0.005 | 0.058 | 9540 |
| M5 | -0.0015 | [-0.0846; +0.0814] | 0.9756 |  | -0.0193 | 0.0559 | 10256 |
| CALL | +0.1143 | [+0.0352; +0.1910] | 0.0162 | in-sample |  |  | 10244 |
| CTOP5 | +0.1466 | [+0.0526; +0.2260] | 0.0060 | in-sample |  |  | 10209 |
| ML | +0.7324 | [+0.6975; +0.7569] | 0.0000 | in-sample |  |  | 10256 |

- C_ALL = TB phân vị có dấu (ECDF EXPLORE) của 12 indicator coin-level giữ lại; C_TOP5 = C17, C11, C18, C4, C19; ML = xgboost depth 3/200 cây/lr 0,05/subsample 0,8/seed 20261114, mục tiêu = residual rank(Y) theo rank(hạng S1)+năm, feature = C1, C3, C4, C8, C9, C10, C11, C12, C17, C18, C19, C20, M1, M3, M5, M6, rank, symbolPred (model `ml.json` lưu, KHÔNG train lại).
- ML IC EXPLORE là in-sample (quá khớp, chỉ báo).

## ỨNG VIÊN CONFIRM (≤ 6) — chốt
- C17: dấu EXPLORE -1; cutpoint ngũ phân vị XẤU (EXPLORE) ≥ 0.361705; seed 42 IC EXPLORE -0.1196
- C11: dấu EXPLORE +1; cutpoint ngũ phân vị XẤU (EXPLORE) ≤ 24.352; seed 42 IC EXPLORE 0.109
- CALL: dấu EXPLORE +1; cutpoint ngũ phân vị XẤU (EXPLORE) ≤ -0.119879; seed 42 IC EXPLORE 0.1091
- CTOP5: dấu EXPLORE +1; cutpoint ngũ phân vị XẤU (EXPLORE) ≤ -0.140159; seed 42 IC EXPLORE 0.1467
- ML: dấu EXPLORE +1; cutpoint ngũ phân vị XẤU (EXPLORE) ≤ -1045.72; seed 42 IC EXPLORE 0.7298
- Holm một phía α 0,10 trên m = 5 ứng viên.

## MDE80 (trước khi đọc Y CONFIRM)
- se_E trung vị 0.0510; se_C = se_E × √(n_cụm_E/n_cụm_C) = 0.0519; MDE80 không chỉnh (α 0,10 một phía) = **0.110**; Holm m=5: 0.150.
- ⚠️ MDE > 0,08 ⇒ **khả năng không có power** (vẫn chạy theo prereg).

## Track G — EXPLORE (Y72 pp, khử cụm R5, Δ so với phút pass B0)
- Phút EXPLORE (seed × phút): {'nm70': 15185, 'pass': 2428}; cụm bootstrap (toàn DEV) 449. Market giữ sau khử trùng: M1, M3, M5, M6 + C_ALL_M.

| M | dấu | relax 0,85 Δ [CI90] / Y72 nm∩thuận | relax 0,70 Δ [CI90] / Y72 nm∩thuận | veto Δ [CI90] |
|---|:-:|---|---|---|
| M1 | +1 | Δ +0.83 [-2.41; +3.82] / +3.79 (n 169) | Δ +0.07 [-2.73; +2.97] / +3.02 (n 245) | Δ +0.19 [-6.44; +7.09] (n 221) |
| M3 | -1 | Δ +4.30 [-1.37; +11.00] / +7.25 (n 140) | Δ +4.82 [+0.07; +9.70] / +7.77 (n 242) | Δ +0.17 [-3.77; +4.11] (n 132) |
| M5 | -1 | Δ -4.19 [-10.65; +3.63] / -1.23 (n 168) | Δ -1.52 [-8.30; +5.88] / +1.43 (n 235) | Δ +1.16 [-2.60; +5.07] (n 163) |
| M6 | -1 | Δ +0.96 [-2.85; +4.58] / +3.91 (n 117) | Δ +1.39 [-1.80; +4.51] / +4.35 (n 230) | Δ +2.46 [-3.37; +8.90] (n 247) |
| CALLM | +1 | Δ +2.12 [-1.74; +6.08] / +5.07 (n 120) | Δ +2.77 [-0.62; +6.28] / +5.72 (n 241) | Δ -1.77 [-6.46; +3.24] (n 180) |

- Y72 phút pass B0 (khử cụm) = +2.95 pp.
- **Không ứng viên G nào đạt luật chọn EXPLORE ⇒ track G ĐÓNG tại EXPLORE (không mở Y CONFIRM cho G).**
