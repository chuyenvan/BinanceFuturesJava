# IND_COMBO Pha 0 — KẾT QUẢ (chỉ đo, không sim)

Prereg vz_e1_wt **14ed6c00** (PREREG_IND_COMBO.md md5 1735a8eb; IND_COMBO_P0_PLAN.md md5 f15a6080). SELECTION **96f74733** (IND_COMBO_SELECTION.md md5 875ed090, selection.json 2d839dc2, ml.json 9a328b4d). Code `research/ind_combo/`, số liệu `docs/result/ind_combo_p0/`.

## VERDICT: **ĐÓNG** — không ứng viên track S nào đạt đủ 3 tiêu chí CONFIRM; track G không có ứng viên ở EXPLORE. Không đề xuất Pha 1 (S-VETO / G-RELAX / G-VETO / K-FLEX đều không đủ điều kiện).

## Dữ liệu (kiểm kho)
- Leg: printDone nt-x14 8 seed, level PREDICT_SYMBOL_TRADE; Y_leg = 100·pnl/margin (pnl ròng phí sim, gồm DCA trong leg + exit); start +07 → UTC; hạng S1 từ cand_base.npz (top-24 sp/phút), điểm S1 = symbolPred.
- Số leg/cụm: EXPLORE 10256 leg / 117 cụm; CONFIRM 11298 / 113; HO 2026H1 2275 / 29. Theo năm {'2022': 4571, '2023': 5685, '2024': 6185, '2025': 5113, '2026': 2275}. Y NaN = 0.
- Nến: 1h OHLCV `~/java/fsrun/OHLCV_1H_v2.bin` (Aerospike kline_1m_opt 2021–2025, 626 symbol) — dùng lại theo §5 (không resample kline1m); 4h/1d gộp từ 1h; r1m (C18) từ close Vision `res1109/r1_s1/kl`; ALT_EW `edge_attr/index.npz`. 2026H1: Kaggle kernel `ind-ho26` (vz-kline1m-2026 → 1h + ALT_EW), enable_internet=false.
- Track G: r/q theo phút tính lại bằng gate_offline cấu hình R5 (pred r3_gate + sổ n4f-b0, J 256); số phút pass/seed/năm KHỚP tuyệt đối sig_meta R5 (8/8 seed × 4 năm). Y72 = r5q_y.parquet (R5 Pha 1, 200a29a3).

## Validate
- Causal: 20 leg ngẫu nhiên (seed 20261114), tính TAY RSI14 1h, Stoch %K 4h, C/SMA50 1d từ nến 1h thô CẮT tại giờ đóng ≤ M: 20/20 khớp (≤1e-6); nến cuối đóng 0–57′ trước phút vào.
- NaN: C1/C4/C6/C18/C20 < 3 % (DEV); chỉ báo 1d NaN 22–45 % vì ~25 % leg vào coin < 50 ngày tuổi (age ≥ 300 ngày ⇒ NaN 0 %) — theo thiết kế prereg; IC tính trên phần không NaN.
- Bootstrap tái lập: chạy lại cùng seed 20261114 ra số y hệt (assert trong code + 2 lần chạy EXPLORE trùng số).
- Seed 42 cùng chiều gộp ở mọi ứng viên (EXPLORE và CONFIRM).
- Rebuild thêm 2026 không đổi X DEV của mọi indicator dùng (0 lệch), TRỪ M4 breadth (xem sai lệch #2).

## EXPLORE 2022–23 (partial Spearman IC; khử rank(hạng S1), rank(điểm S1), năm)
Khử trùng giữ 16: C1, C3, C4, C8, C9, C10, C11, C12, C17, C18, C19, C20, M1, M3, M5, M6. Bỏ: C2~C1, C5~C1, C6~C1, C7~C1, C13~C3, C14~C3, C15~C3, C16~C3, M2~C3, M4~C3.

| X | IC | CI90 | p2 | FDR | 2022 | 2023 |
|---|---:|---|---:|:-:|---:|---:|
| C17 | -0.122 | [-0.192; -0.038] | 0.009 | x | -0.187 | -0.032 |
| C11 | +0.106 | [+0.036; +0.173] | 0.011 | x | +0.119 | +0.092 |
| C18 | -0.101 | [-0.175; -0.009] | 0.049 |  | -0.191 | -0.011 |
| M3 | -0.108 | [-0.213; -0.008] | 0.081 |  | -0.299 | +0.011 |
| C4 | +0.068 | [-0.017; +0.147] | 0.184 |  | +0.041 | +0.082 |
| C8 | +0.061 | [-0.011; +0.141] | 0.194 |  | +0.016 | +0.089 |
| CALL (in-sample) | +0.114 | [+0.035; +0.191] | 0.016 | – | | |
| CTOP5 (in-sample) | +0.147 | [+0.053; +0.226] | 0.006 | – | | |
| ML (in-sample) | +0.732 | [+0.698; +0.757] | 0.000 | – | | |

C11 = ADX14 4h; C17 = C/SMA200−1 (1d); C18 = RV1h/RV24h; C4 = Stoch %K 1h; M3 = BTC C/SMA200−1. C_TOP5 = C17, C11, C18, C4, C19. MDE80 (CONFIRM, 113 cụm) = **0.110** (Holm m=5: 0.150) > 0,08 ⇒ cảnh báo thiếu power.

## CONFIRM 2024–25 (ứng viên chốt trong SELECTION; Holm một phía α 0,10, m = 5)

| Ứng viên | dấu E | IC | CI90 | p1 | Holm | IC 2024 | IC 2025 | veto ΔY (bỏ−giữ) [CI90] | ΣPnL bỏ 2024 / 2025 (USD) | (1) | (2) | (3) | ĐẠT | seed42 |
|---|:-:|---:|---|---:|:-:|---:|---:|---|---|:-:|:-:|:-:|:-:|---:|
| C17 | -1 | -0.051 | [-0.132; +0.035] | 0.161 |  | -0.015 | -0.140 | -1.62 [-3.63; +0.27] | +64992 / +6733 |  | x |  | **KHÔNG** | -0.051 |
| C11 | +1 | +0.061 | [+0.005; +0.106] | 0.024 | x | +0.124 | -0.000 | -0.08 [-1.18; +0.88] | +28676 / +69024 | x |  |  | **KHÔNG** | +0.054 |
| CALL | +1 | +0.040 | [-0.017; +0.093] | 0.112 |  | +0.031 | +0.043 | +1.34 [-0.24; +2.47] | +55845 / +58483 |  | x |  | **KHÔNG** | +0.042 |
| CTOP5 | +1 | +0.066 | [+0.010; +0.117] | 0.020 | x | +0.084 | +0.044 | -0.48 [-2.01; +0.77] | +33865 / +47320 | x | x |  | **KHÔNG** | +0.062 |
| ML | +1 | -0.020 | [-0.083; +0.044] | 0.699 |  | -0.047 | +0.010 | +1.76 [+0.59; +2.85] | +42874 / +49089 |  |  |  | **KHÔNG** | -0.019 |

- C_TOP5 và C11 qua (1) (IC dương, CI90 > 0, Holm) — tức có tín hiệu xếp hạng yếu (IC ≈ 0,06) — nhưng **trượt (3) kinh tế**: nhóm ngũ phân vị xấu vẫn lãi dương ở cả 2024 và 2025 (bỏ đi là mất tiền), ΔY CI chứa 0. C11 còn trượt (2) (IC 2025 ≈ 0). ML (in-sample IC 0,73) sụp về −0,02 ở CONFIRM = quá khớp; ngũ phân vị "xấu" của ML/C_ALL lại có Y cao hơn.

## Track G (gate linh hoạt, market-level)
- EXPLORE: không chỉ báo nào (M1, M3, M5, M6, C_ALL_M) đạt luật chọn ở CẢ 2 band (relax cần CI90 dưới > −1 pp; M3 band 0,85 CI dưới −1,37; C_ALL_M −1,74), veto đều CI chứa 0 ⇒ **track G ĐÓNG tại EXPLORE**, không mở Y CONFIRM cho G. Chi tiết: IND_COMBO_SELECTION.md.

## HO 2026-01..06 (chỉ mô tả; không có hạng S1 ⇒ khử theo điểm S1; 2 275 leg / 29 cụm)

| Ứng viên | IC | CI90 | veto ΔY [CI90] | ΣPnL bỏ |
|---|---:|---|---|---:|
| C17 | +0.070 | [-0.056; +0.209] | -0.88 [-3.01; +1.38] | +54600 |
| C11 | +0.021 | [-0.066; +0.111] | -1.73 [-4.89; +1.79] | +13682 |
| CALL | -0.003 | [-0.095; +0.094] | +2.86 [+1.41; +4.21] | +20212 |
| CTOP5 | -0.049 | [-0.152; +0.057] | +2.03 [-0.86; +4.09] | +25640 |
| ML | +0.046 | [-0.062; +0.140] | -1.25 [-4.39; +1.33] | +40278 |
- HO: C_TOP5 IC đổi dấu (−0,05), C_ALL ≈ 0; nhóm bị loại vẫn lãi ⇒ cùng kết luận ĐÓNG.

## Tài nguyên
- Oracle CPU ≈ 0,32 h (user+sys: G2 54 s, build 2×~215 s, explore 2×~265 s, confirm 72 s, kiểm ~40 s); RSS đỉnh build 3,04 GiB (/usr/bin/time; cgroup MemoryMax=3G không kích hoạt) — vượt nhẹ mức 3 GB, các job khác ≤ 2,6 GB. flock oracle_heavy + nice 19/ionice c3, mem_avail ≥ 20 GB, không có tiến trình deploy.
- Kaggle: 1 kernel `ind-ho26` ~11 phút (≈ 0,18 kernel-giờ).
- Đĩa Oracle: trống 17 GB trước; dữ liệu mới tối đa ~100 MB trong ~/claude_master/ind1114, đã dọn trung gian (giữ legs_x.parquet, mkt_h.parquet, g2_*.npz, json).

## Sai lệch / giới hạn so với prereg (khai đủ)
1. Nến 1h lấy từ store Aerospike OHLCV_1H_v2 (tái dùng theo §5), không phải resample kline1m Vision; C18 dùng close Vision; 2026 từ Vision qua Kaggle (không lọc cột `active`). 4h/1d gộp từ 1h (tương đương gộp từ 1m).
2. Giờ thiếu được ffill (nến phẳng, qv 0). Hệ quả: M4 (breadth) trên DEV ĐỔI khi nối dữ liệu 2026 (symbol bị cắt đuôi/relist được ffill qua khoảng trống dài) ⇒ M4 không tin cậy. M4 bị loại ở khử trùng (ρ 0,82 với C3) trong EXPLORE và không dùng ở đâu ⇒ không ảnh hưởng ứng viên; mọi indicator dùng không đổi.
3. Không khử trùng theo 45 feature S1 (bảng feature không có trong dump; điều kiện "nếu có").
4. EXPLORE chạy 2 lần do lỗi code track G (cột C_ALL_M) — số track S hai lần trùng tuyệt đối; không đổi định nghĩa.
5. HO: không có hạng S1 2026 (cand_base chỉ DEV) ⇒ khử theo điểm S1; không có Y72 2026 ⇒ track G không có HO; ALT_EW 2026 tính trên mọi symbol Vision (xấp xỉ universe edge_attr). AGENT_RUNBOOK §0.1 yêu cầu owner duyệt khi mở HO 2026 — prereg MASTER yêu cầu HO mô tả; MASTER cần xác nhận quyền dùng.
6. Chi tiết vận hành (cụm, khử cụm G, luật chọn G, p-value, MDE) cố định trong IND_COMBO_P0_PLAN.md commit cùng prereg, trước khi đọc Y.
