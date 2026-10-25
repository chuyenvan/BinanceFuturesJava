# GOLIVE_QUARTERLY — gói go-live v1.1 (crash-buy K24 + skipFull + TS_MKT_EXT X14) theo QUÝ — 2026-10-25

**CHỈ MÔ TẢ.** Không chọn, không tune, không chạy lại sim. Chỉ dùng artefact đã có: chuỗi printDone của sim Java X14, 8 seed.
Code: `research/golive_quarterly/` (`mtm_dev.py`, `mtm_ho.py`, `quarterly.py`, `handcheck.py`). Số liệu: `docs/result/golive_quarterly/`
(`quarterly_x14.csv` = median/min/max qua 8 seed; `quarterly_x14_by_seed.csv` = từng seed; `validate.json`, `handcheck.json`, `summary.json`, `tables.md`).

## Tóm tắt, rủi ro trước
- **DEV 2022–25 (median 8 seed):** ΣPnL 113 410 USD [108 245 … 129 889], CAGR 39,0 %, maxDD MTM −22,83 % [−24,66 … −20,05], Calmar 1,71.
  Có 660 đợt vào, 2 878 cụm, 2 938 leg.
  **HO 2026-01→09 (W9):** ΣPnL 18 106 [12 894 … 22 674], ROI 12,68 % (quy năm 17,3 %), maxDD −5,62 % [−6,67 … −5,14].
- **Quý âm** (median): 2022Q2 (LUNA, −3,7 %, 7/8 seed âm), 2022Q4 (FTX, −2,0 %, 8/8 seed âm), 2025Q3 (−0,1 %, 5/8 seed âm),
  2026Q3 HO (−1,2 % realized nhưng MTM +0,27 %, 6/8 seed âm).
- **DD quý lớn:** 2022Q2 −22,8 % (chính là DD toàn kỳ), 2025Q4 −17,2 %, 2022Q4 −14,6 %, 2021Q3 −14,2 %, 2021Q4 −13,6 %, 2024Q2 −12,1 %.
  DD lớn trùng với quý có nhiều đợt vào: hệ mua lúc sập nên DD đến đúng lúc vào lệnh. Ví dụ 2025Q4 có 150 đợt, DD −17,2 % nhưng cuối quý vẫn +12,6 %.
- **Tập trung PnL:** top-3 quý chiếm **46,3 %** ΣPnL DEV 2022–25 (median; khoảng [42,8 … 47,8 %], 16 quý).
  Cả 8 seed đều có cùng top-3 là 2024Q4, 2025Q1, 2025Q4, chỉ khác thứ tự. Riêng top-1 chiếm ~15–18 %. Năm 2022 chỉ +4,6k (ROI 11,1 %) và khoảng seed rất rộng [2,7k … 12,3k].
- **Lệnh thưa:** DEV 2022–25 có 832/1 461 ngày (57 %) không có vị thế nào, và 1 318/1 461 ngày (90 %) không vào lệnh mới.
  Phơi nhiễm trung bình 5,3 % vốn, tối đa 62 %, tối đa 69 vị thế cùng lúc.
- **Phát hiện ngoài phạm vi (đã xử lý trong bảng): MTM legacy `gvz_mtm` / `reset_rule_score.run_mtm` BỎ SÓT PnL của leg đóng đúng 00:00 UTC
  trong suốt ngày UTC đó.** `_work_vision` lọc `m1 > base`, nên leg có `m1 == base` không vào `sp`; còn `prefix` chỉ cộng các leg có `te_day < day`.
  Mỗi seed có ~100 leg như vậy, ~85–95 cụm trong đó là cụm X14 bị cắt khi cờ tắt (00:00 UTC), tổng −10k … −15k USD. Hệ quả: equity bị
  thổi cao tới 4,2–5,6k USD trong ngày đó. Kiểm "lúc phẳng vị thế, equity phải bằng số dư thực hiện" FAIL với bản legacy (lệch 3,5–4,1k USD
  ở 6 858–9 738 phút/seed) và PASS sau khi sửa (lệch ≤ 0,016 USD). **Tác động lên DD/ret theo quý và DD22 = 0 tuyệt đối** (max |Δ| = 0 trên mọi quý, mọi seed),
  nên số đã công bố (DD22 −22,83 median) vẫn đúng. Tuy vậy, các chỉ số trong báo cáo trước có chia cho equity phút trong ngày
  (U(t), "vốn giam", phơi nhiễm, đều lấy từ `deep_cache/eq_dev.npz` hoặc cùng đường `run_mtm`) có thể lệch trong ~16–20 ngày/seed bị ảnh hưởng.
  Phần này CHƯA đo lại. Chưa sửa `gvz_mtm.py` vì ngoài phạm vi; MASTER quyết.

## Nguồn và đối chiếu
| | DEV | HO |
|---|---|---|
| Run | `~/kaggle_sim/out/tsx-x14-{a1,s7,s13,s21,s99,s123,s777,s2024}` (= X14 của c1ab8eda, TSX_V3_JAVA b31d44d1) | `tsx-ho-x14-s{42,7,13,21,99,123,777,2024}` (46ebc1ee, a69a6a95) |
| Jar | `cc0f9d11…1b1dfe` (TS_MKT_EXT), profile `r4_kg0_k16_f015_g155`, TOPK 24, `GATE_QUOTA_SKIP_WHEN_FULL=true`, X14 = `SIM_LOSER_TS_EXT_HOURS=336` + 214 ngày cờ (`tsx/flags.json`) | cùng jar; cờ 2026 = 15 ngày / 4 khoảng (`tsx/ho/ho_flags.json`); bundle pred `sim-ho26a` |
| Vốn / phí / funding | `CAPITAL_START=35000`, `SIM_RATE_FEE=0.000982`; phí ngầm = q(tp−e) − funding − pnl = **0,1116 % notional vào** (median, khớp FEE_IN); `SIM_APPLY_FUNDING=true` | như DEV |
| Lãi kép | Có. Size theo số dư (xem TSX_V3_JAVA §"lãi kép"); equity 35k → ~150k cuối 2025 | Run HO chạy từ 2021-07 → 2026-09-30; equity đầu 2026 ≈ 140k là đường đi riêng của run HO (KHÔNG nối tiếp run DEV) |
| MTM | `gvz_mtm` import TRƯỚC `reset_rule_score`, chạy lại 8 run, `missing = 0` (assert), khớp `mtm_vision.json` và `deep_cache/eq_dev.npz` (Δ = 0); sửa lỗi 00:00 UTC như trên | `ecm_mtm_h`/`ho4_score_a.build` trên cache giá 1m Vision `ecm_px` ĐÃ CÓ; fetch bị khoá offline; `miss = 0`, `nofile = 0`, khớp `ho_mtm.json` và `eq_ho.npz` (Δ = 0). Không tải kline 2026, không chạy kernel Kaggle |

**Đối chiếu số đã công bố.** Tính lại qua `n700.arm_metrics`, khớp tuyệt đối với `tsx_v3_java/dev_rows.csv`:
- CAGR22: mean **39,490**, median 39,06. Brief ghi "≈ 39,5" = mean.
- DD22 MTM: mean −22,547, **median −22,833**. Brief ghi "≈ −22,9" ≈ median −22,83.
- Cụm: median **3 472** (3 471,5). Đợt vào: **768**. Leg: 3 531.
- Ba số đếm trên là toàn kỳ DEV **2021-07 → 2025-12**, gồm cả 2021H2: 586 cụm, 110 đợt. Riêng 2022–25 có 2 878 cụm và 660 đợt.
- Từng seed: n_cl, n_batch, n_leg, ΣPnL đều khớp tuyệt đối. DD lũy kế cuối 2025Q4 = dd22 công bố (Δ = 0).

## Quy ước
- **Quý theo giờ +07** (= giờ printDone = cửa sổ W9 HO = PER_DEV của DEEP). Trục MTM là UTC = giờ +07 − 7h. Đã kiểm bằng phép "phẳng vị thế ⇒ equity = số dư":
  trục đúng lệch ≤ 0,016 USD; trục sai (không trừ 7h) lệch 3,8–5,5k USD.
- Leg và cụm (cụm = các leg DCA cùng `sym` đóng cùng phút) được gán quý theo **giờ ĐÓNG**. **Đợt vào** = phút anchor t0 (leg đầu của cụm) nằm trong quý.
- **ROI quý** = ΣPnL thực hiện / số dư thực hiện đầu quý. **CAGR quy năm** = (1+ROI)^4 − 1. Với năm/tổng: quy theo số ngày.
  **ret MTM** = equity MTM cuối quý / cuối quý trước − 1. ret MTM khác ROI khi có vị thế vắt qua ranh giới quý, ví dụ 2026Q2/Q3.
- **maxDD quý**: MTM phút, đỉnh tính từ đầu quý. **DD lũy kế**: đỉnh tính từ đầu giai đoạn (DEV 2022-01-01, riêng các quý 2021 tính từ 2021-07-01; HO 2026-01-01), xét tới cuối quý.
  **Calmar quý** = CAGR quy năm / |maxDD quý|.
- **Phơi nhiễm** = notional leg đang mở / equity MTM, lấy theo từng phút (TB, max). **Vị thế đồng thời** = số cụm đang mở.
- **Thoát**: X14 gia hạn = cụm bị HOÃN (tuổi > 168h+1′, mốc 168h rơi vào ngày cờ, trừ cụm đã arm trailing trước 168h theo P0 `gqsf-*`/`ho4-k24-b-*`;
  khớp đếm `[TSX]` của Java 16/16 run). Time-stop 168h = STOP_LOSS ở tuổi 168h ±2′. Trailing = STOP_MARKET. Khác = phần còn lại.
- **Ngày không vị thế**: ngày +07 không có cụm nào mở. **Ngày không vào lệnh**: không có leg mới. **Ngày cờ X14**: theo nhãn ngày (UTC) của cờ.
- Median, min, max lấy qua 8 seed cho TỪNG chỉ số độc lập: median của các cột KHÔNG cộng dồn được.

## Bảng theo quý (median 8 seed [min … max]; tự sinh `tables.md`)

### A. Hiệu quả
| Quý | Đợt vào | Cụm | Leg | Win % cụm | PnL/cụm | ΣPnL USD | ROI % | CAGR quy năm % | maxDD quý % | DD lũy kế % | Calmar | DD quý legacy % | DD lũy kế legacy % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021Q3 | 68 | 386 | 386 | 81,7 | 12,2 | 4 720 [4 265 … 4 930] | 13,48 [12,19 … 14,08] | 65,9 | -14,15 [-14,17 … -13,93] | -14,15 | 4,67 | -14,15 | -14,15 |
| 2021Q4 | 42 | 203 | 203 | 77,5 | 9,2 | 1 860 [1 541 … 2 177] | 4,68 [3,91 … 5,47] | 20,1 | -13,61 [-13,81 … -13,59] | -14,15 | 1,46 | -13,61 | -14,15 |
| 2022Q1 | 20 | 100 | 100 | 88,5 | 27,2 | 2 734 [2 226 … 3 193] | 6,62 [5,35 … 7,61] | 29,2 | -7,71 [-8,59 … -7,22] | -7,71 | 3,79 | -7,71 | -7,71 |
| 2022Q2 | 105 | 270 | 294 | 83,9 | -6,1 | -1 663 [-2 712 … 5 228] | -3,72 [-6,06 … 11,93] | -14,0 | -22,83 [-24,66 … -18,25] | -22,83 | -0,62 | -22,83 | -22,83 |
| 2022Q3 | 12 | 91 | 91 | 95,8 | 49,7 | 4 432 [3 796 … 5 473] | 10,57 [8,91 … 12,05] | 49,5 | -1,84 [-2,23 … -1,84] | -22,83 | 26,87 | -1,84 | -22,83 |
| 2022Q4 | 36 | 114 | 122 | 77,5 | -8,0 | -955 [-1 705 … -408] | -2,03 [-3,52 … -0,88] | -7,9 | -14,60 [-16,06 … -13,99] | -22,83 | -0,54 | -14,60 | -22,83 |
| 2023Q1 | 14 | 152 | 152 | 88,6 | 35,9 | 5 586 [4 918 … 6 312] | 12,34 [10,22 … 13,52] | 59,3 | -5,48 [-5,59 … -3,96] | -22,83 | 10,92 | -5,48 | -22,83 |
| 2023Q2 | 30 | 184 | 184 | 75,7 | 46,1 | 8 594 [7 339 … 9 792] | 16,09 [14,24 … 18,47] | 81,7 | -6,24 [-7,69 … -4,75] | -22,83 | 13,68 | -6,24 | -22,83 |
| 2023Q3 | 17 | 131 | 131 | 88,0 | 46,6 | 6 240 [5 642 … 7 085] | 10,03 [9,10 … 11,89] | 46,6 | -3,61 [-3,65 … -3,17] | -22,83 | 14,37 | -3,61 | -22,83 |
| 2023Q4 | 62 | 284 | 284 | 86,6 | 40,6 | 11 495 [11 114 … 11 985] | 17,22 [16,23 … 18,42] | 88,8 | -3,50 [-3,77 … -3,34] | -22,83 | 25,35 | -3,50 | -22,83 |
| 2024Q1 | 54 | 256 | 256 | 87,8 | 45,9 | 12 010 [9 581 … 15 399] | 14,98 [12,59 … 17,94] | 74,8 | -7,88 [-7,93 … -7,73] | -22,83 | 9,45 | -7,88 | -22,83 |
| 2024Q2 | 29 | 189 | 190 | 83,9 | 15,0 | 3 033 [1 669 … 5 146] | 3,44 [1,91 … 5,08] | 14,5 | -12,10 [-12,38 … -11,97] | -22,83 | 1,19 | -12,10 | -22,83 |
| 2024Q3 | 28 | 138 | 138 | 88,5 | 46,1 | 6 260 [4 536 … 7 090] | 6,81 [4,77 … 7,50] | 30,2 | -7,64 [-7,82 … -7,63] | -22,83 | 3,95 | -7,64 | -22,83 |
| 2024Q4 | 44 | 262 | 262 | 90,4 | 66,9 | 17 175 [14 838 … 19 078] | 16,88 [15,62 … 18,80] | 86,6 | -6,51 [-7,08 … -6,32] | -22,83 | 13,18 | -6,51 | -22,83 |
| 2025Q1 | 44 | 236 | 236 | 91,8 | 79,1 | 17 669 [16 209 … 19 062] | 14,84 [14,09 … 17,36] | 73,9 | -9,33 [-9,76 … -9,32] | -22,83 | 7,93 | -9,33 | -22,83 |
| 2025Q2 | 6 | 36 | 36 | 91,0 | 121,6 | 4 593 [3 954 … 5 247] | 3,35 [3,07 … 3,81] | 14,1 | -1,32 [-1,79 … -0,82] | -22,83 | 10,60 | -1,32 | -22,83 |
| 2025Q3 | 10 | 81 | 81 | 75,7 | -2,4 | -184 [-2 600 … 434] | -0,14 [-1,67 … 0,32] | -0,5 | -3,05 [-4,56 … -2,74] | -22,83 | -0,18 | -3,05 | -22,83 |
| 2025Q4 | 150 | 360 | 386 | 90,2 | 49,4 | 17 653 [16 226 … 21 909] | 12,58 [11,70 … 15,32] | 60,7 | -17,19 [-17,62 … -16,97] | -22,83 | 3,55 | -17,19 | -22,83 |
| 2021H2 | 110 | 586 | 586 | 80,3 | 11,1 | 6 593 [5 947 … 6 951] | 18,84 [16,99 … 19,86] | 40,9 | -14,15 [-14,17 … -13,93] | -14,15 | 2,91 | -14,15 | -14,15 |
| 2022 | 170 | 572 | 605 | 85,3 | 8,2 | 4 640 [2 707 … 12 348] | 11,10 [6,45 … 30,09] | 11,1 | -22,83 [-24,66 … -18,25] | -22,83 | 0,49 | -22,83 | -22,83 |
| 2023 | 124 | 758 | 758 | 84,6 | 41,4 | 32 014 [29 935 … 34 002] | 68,33 [60,75 … 73,65] | 68,4 | -6,24 [-7,69 … -4,97] | -22,83 | 11,09 | -6,24 | -22,83 |
| 2024 | 155 | 840 | 840 | 88,1 | 45,5 | 37 817 [33 285 … 46 508] | 48,59 [43,49 … 54,19] | 48,5 | -12,10 [-12,38 … -11,97] | -22,83 | 3,97 | -12,10 | -22,83 |
| 2025 | 209 | 710 | 736 | 89,1 | 56,1 | 39 737 [37 426 … 44 881] | 35,20 [29,17 … 37,38] | 35,2 | -17,84 [-20,05 … -16,97] | -22,83 | 2,00 | -17,84 | -22,83 |
| DEV_2022_25 | 660 | 2 878 | 2 938 | 87,0 | 39,5 | 113 410 [108 245 … 129 889] | 273,60 [260,22 … 316,49] | 39,0 | -22,83 [-24,66 … -20,05] | -22,83 | 1,71 | -22,83 | -22,83 |
| DEV_ALL_2021H2_25 | 768 | 3 472 | 3 531 | 85,9 | 34,7 | 119 857 [114 817 … 135 929] | 342,45 [328,05 … 388,37] | 39,1 | -22,83 [-24,66 … -20,05] | -22,83 | 1,72 | -22,83 | -22,83 |
| 2026Q1 | 24 | 131 | 132 | 88,7 | 71,2 | 9 536 [6 935 … 12 024] | 6,53 [4,59 … 8,12] | 28,8 | -5,62 [-6,01 … -5,14] | -5,62 | 5,34 | — | — |
| 2026Q2 | 31 | 146 | 148 | 86,1 | 71,9 | 10 858 [8 370 … 12 555] | 6,86 [5,38 … 8,36] | 30,4 | -3,24 [-3,83 … -3,07] | -5,62 | 9,75 | — | — |
| 2026Q3 | 32 | 158 | 163 | 79,9 | -12,9 | -2 000 [-8 537 … 5 118] | -1,22 [-4,88 … 3,04] | -4,8 | -3,79 [-6,28 … -2,49] | -5,62 | -1,21 | — | — |
| HO_2026_W9 | 88 | 441 | 452 | 84,1 | 41,2 | 18 106 [12 894 … 22 674] | 12,68 [8,41 … 15,01] | 17,3 | -5,62 [-6,67 … -5,14] | -5,62 | 3,24 | — | — |

### B. Phơi nhiễm / thoát / chi phí
| Quý | Phơi nhiễm TB % | max % | Vị thế đồng thời max | Giữ trung vị h | Trailing | Time-stop 168h | X14 gia hạn | Khác | Phí USD | Funding USD | Ngày không vị thế | Ngày không vào lệnh | Ngày cờ X14 | ret MTM % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021Q3 | 10,46 | 56,5 [56,3 … 56,5] | 54 | 17,4 | 319 | 68 | 0 | 0 | 178 | 59 | 34 / 92 | 76 | 4 | 13,15 |
| 2021Q4 | 6,19 | 59,9 [59,8 … 60,0] | 54 | 17,5 | 156 | 23 | 25 | 0 | 111 | 10 | 53 / 92 | 86 | 10 | 4,99 |
| 2022Q1 | 4,75 | 43,3 [41,8 … 45,7] | 37 | 16,4 | 78 | 6 | 15 | 0 | 62 | -35 | 65 / 90 | 85 | 14 | 6,62 |
| 2022Q2 | 12,78 | 62,0 [58,0 … 63,5] | 56 | 7,2 | 218 | 8 | 43 | 3 | 115 | -226 | 46 / 91 | 77 | 44 | -3,72 |
| 2022Q3 | 2,05 | 45,1 [45,1 … 48,1] | 37 | 17,7 | 84 | 6 | 0 | 0 | 66 | -44 | 68 / 92 | 87 | 0 | 10,57 |
| 2022Q4 | 9,80 | 54,2 [52,3 … 54,7] | 60 | 13,9 | 82 | 0 | 33 | 0 | 53 | -572 | 64 / 92 | 86 | 20 | -2,03 |
| 2023Q1 | 5,55 | 41,0 [36,5 … 41,3] | 32 | 17,8 | 131 | 13 | 11 | 0 | 124 | 38 | 44 / 90 | 80 | 3 | 12,34 |
| 2023Q2 | 7,01 | 47,9 [45,8 … 48,8] | 44 | 18,9 | 134 | 51 | 0 | 0 | 163 | -77 | 41 / 91 | 80 | 1 | 17,37 |
| 2023Q3 | 5,03 | 44,5 [44,3 … 44,5] | 36 | 20,5 | 108 | 24 | 0 | 0 | 136 | -281 | 39 / 92 | 85 | 0 | 9,31 |
| 2023Q4 | 6,34 | 54,0 [51,7 … 54,6] | 64 | 10,7 | 242 | 42 | 0 | 0 | 283 | -6 | 28 / 92 | 76 | 0 | 16,94 |
| 2024Q1 | 4,92 | 43,3 [42,9 … 43,3] | 34 | 4,6 | 226 | 30 | 0 | 1 | 325 | 354 | 37 / 91 | 75 | 0 | 15,26 |
| 2024Q2 | 7,25 | 54,5 [54,3 … 54,7] | 47 | 13,0 | 157 | 17 | 18 | 0 | 237 | -0 | 47 / 91 | 82 | 28 | 2,69 |
| 2024Q3 | 3,76 | 53,9 [49,5 … 55,4] | 56 | 29,2 | 115 | 12 | 8 | 1 | 156 | -8 | 66 / 92 | 88 | 14 | 7,38 |
| 2024Q4 | 4,45 | 50,8 [50,7 … 51,2] | 46 | 7,4 | 236 | 26 | 0 | 0 | 384 | 201 | 45 / 92 | 79 | 9 | 16,88 |
| 2025Q1 | 3,78 | 45,4 [45,4 … 46,6] | 37 | 6,1 | 214 | 9 | 6 | 0 | 425 | -382 | 54 / 90 | 81 | 40 | 14,84 |
| 2025Q2 | 1,00 | 36,4 [36,2 … 36,5] | 24 | 7,6 | 32 | 4 | 0 | 0 | 88 | -333 | 73 / 91 | 88 | 7 | 3,35 |
| 2025Q3 | 2,95 | 38,6 [38,5 … 38,6] | 26 | 14,0 | 62 | 20 | 0 | 0 | 186 | 52 | 54 / 92 | 87 | 0 | -0,14 |
| 2025Q4 | 3,96 | 60,0 [59,9 … 60,3] | 69 | 1,5 | 338 | 10 | 13 | 0 | 553 | -375 | 56 / 92 | 82 | 20 | 12,58 |
| 2021H2 | 8,31 | 59,9 [59,8 … 60,0] | 54 | 17,8 | 471 | 90 | 25 | 0 | 287 | 67 | 87 / 184 | 162 | 14 | 18,84 |
| 2022 | 7,29 | 62,0 [58,0 … 63,5] | 60 | 13,0 | 463 | 20 | 92 | 3 | 294 | -873 | 243 / 365 | 334 | 78 | 11,10 |
| 2023 | 5,99 | 54,0 [51,7 … 54,6] | 64 | 14,8 | 620 | 130 | 11 | 0 | 712 | -333 | 155 / 365 | 322 | 4 | 67,93 |
| 2024 | 5,10 | 54,7 [54,3 … 55,4] | 56 | 9,2 | 730 | 81 | 26 | 2 | 1 096 | 504 | 194 / 366 | 324 | 51 | 48,96 |
| 2025 | 2,88 | 60,0 [59,9 … 60,3] | 69 | 4,3 | 644 | 43 | 19 | 0 | 1 252 | -834 | 238 / 365 | 338 | 67 | 35,20 |
| DEV_2022_25 | 5,31 | 62,0 [60,1 … 63,5] | 69 | 10,1 | 2 454 | 274 | 148 | 4 | 3 343 | -1 562 | 832 / 1 461 | 1 318 | 200 | 273,60 |
| DEV_ALL_2021H2_25 | 5,64 | 62,0 [60,1 … 63,5] | 69 | 11,3 | 2 929 | 366 | 172 | 4 | 3 628 | -1 486 | 916 / 1 645 | 1 480 | 214 | 342,45 |
| 2026Q1 | 3,47 | 47,6 [45,4 … 48,3] | 42 | 8,9 | 113 | 4 | 9 | 4 | 273 | -370 | 63 / 90 | 84 | 14 | 6,53 |
| 2026Q2 | 3,16 | 43,3 [42,6 … 43,7] | 41 | 7,7 | 126 | 16 | 5 | 0 | 310 | -733 | 67 / 91 | 80 | 1 | 5,31 |
| 2026Q3 | 4,86 | 39,3 [36,3 … 40,5] | 28 | 9,1 | 128 | 34 | 0 | 0 | 433 | -693 | 42 / 92 | 79 | 0 | 0,27 |
| HO_2026_W9 | 4,03 | 47,6 [45,4 … 48,3] | 42 | 8,6 | 370 | 53 | 14 | 4 | 1 087 | -1 786 | 168 / 273 | 243 | 15 | 12,68 |

## Ghi chú đọc bảng
- 2021Q3, 2021Q4 và 2021H2 chỉ để đối chiếu tổng với số công bố (ngoài phạm vi 2022Q1 → 2026Q3). Dòng `DEV_ALL_2021H2_25` = toàn kỳ DEV đã công bố.
- Dòng DEV (2022–25) và dòng HO (2026) là **các run khác nhau**. HO dùng bundle pred khác; bộ seed có 42 thay cho A1; equity đầu 2026 ≈ 140k là của chính run HO.
  Vì vậy PnL USD của DEV và HO không cộng nối được; nên so bằng ROI.
- PnL USD tăng dần theo thời gian một phần do lãi kép (size theo số dư). Khi so các quý, dùng ROI/ret.
- Phí là phí ngầm (≈ 0,1116 % notional vào). Funding âm = long NHẬN funding: DEV 2022–25 nhận ròng ~1,6k, HO ~1,8k.

## Nhận xét regime (mô tả)
- **Quý âm** đều rơi vào đợt sập kéo dài hoặc nhiều nhịp: LUNA/3AC (2022Q2: 105 đợt vào, 44 ngày cờ, 43 cụm X14), FTX (2022Q4: 33 cụm X14, 8/8 seed âm).
  Ngoài ra có hai quý ít hoạt động mà win thấp: 2025Q3 (10 đợt, win 75,7 %) và 2026Q3 HO (32 đợt, win 79,9 %, 34 time-stop).
  Không quý nào âm quá −6,1 % ROI ở bất kỳ seed nào. Seed tệ nhất là 2022Q2 −6,06 %; HO 2026Q3 seed tệ nhất −4,88 %.
- **2022Q2 quyết định DD toàn kỳ ở 7/8 seed** (−22,83 % median; DD lũy kế chạm mức cuối kỳ ngay trong 2022Q2).
  Ngoại lệ S777: 2022Q2 dương +11,9 % (DD quý −18,25 %), còn DD toàn kỳ −20,05 % lại rơi vào **2025Q4**
  (sập thanh lý 10/2025; DD quý −17,6 %, đỉnh nằm ở quý trước). 2025Q4 là rủi ro DD gần nhất, đứng thứ 2 (−17,2 % median), xảy ra ngay trước go-live.
- Quý mạnh nhất là quý "sập rồi hồi nhanh": 2024Q4, 2025Q1, 2025Q4 (ROI 12,6–16,9 %); 2023Q2, 2023Q4 (16–17 %).
  Năm 2023 có ROI cao nhất (68 %) dù chỉ 4 ngày cờ: phần lớn PnL không đến từ X14.
- **HO 2026**: Q1 (đợt sập T2, 14/15 ngày cờ) và Q2 dương ~6,5–6,9 %; Q3 âm realized nhưng ret MTM +0,27 %, vì lỗ của các vị thế vắt từ Q2 đã được trừ MTM vào cuối Q2.
  maxDD W9 −5,62 % nhỏ hơn hẳn các quý sập của DEV. HO chỉ có MỘT đợt sập, nên chưa kiểm được đuôi kiểu 2022Q2.

## Validate (`validate.json`, `handcheck.json`) — ALL_OK = True
1. **Σ PnL các quý = tổng giai đoạn**, max |Δ| = 3e-11 USD trên mọi seed: 16 quý 2022–25 = DEV_2022_25; 4 năm = DEV_2022_25; 18 quý = Σ printDone; 3 quý HO = W9.
   Σ đợt và Σ cụm theo quý = tổng (Δ = 0). Σ log(1+ret MTM) các quý = log tổng (Δ ≤ 7e-16).
2. **Đếm khớp số công bố** (`tsx_v3_java/dev_rows.csv`): n_cl, n_batch, n_leg, ΣPnL khớp tuyệt đối 8/8. Median 3 472 / 768 / 3 531.
   CAGR22 mean 39,490 và DD22 mean −22,547 / median −22,833 tái lập đúng. Cụm hoãn X14 = đếm `[TSX]` Java 16/16 run.
3. **MTM missing = 0**: assert trong `mtm_dev.py` (gvz_mtm import trước R, `R._work is MT._work_vision`) và trong `mtm_ho.py` (`miss = nofile = fetch.fail = fetch.ok = 0`).
   Bản chạy lại khớp cache `eq_dev.npz`/`eq_ho.npz` với Δ = 0, khớp `mtm_vision.json`/`ho_mtm.json` với Δ = 0.
4. **HO từng quý vs scorer HO4 (`ho_mtm.json` Q1/Q2/Q3/W9)**: ΣPnL lệch tối đa 4e-12; ret lệch ≤ 0,0005 pp (do mốc đầu quý lấy phút trước, không phải phút đầu); DD lệch 0.
5. **Trục thời gian**: lúc phẳng vị thế, equity = số dư thực hiện, lệch ≤ 0,016 USD (DEV đã sửa, HO). Bản legacy và trục không trừ 7h đều FAIL (xem trên).
6. **Kiểm tay độc lập** (`handcheck.py`, chỉ dùng `csv`/`datetime`, không pandas, không import pipeline): DEV S7 2022Q2 (ΣPnL −2 189,52; 287 leg; 259 cụm; 101 đợt; win 82,24 %)
   và HO s42 2026Q1 (9 620,00; 109; 109; 23; 90,83 %). Khớp bảng với Δ = 0.

## Giới hạn / chưa đo được
- Sim **không mô hình trượt giá** (đặc biệt coin mới niêm yết / thanh khoản mỏng lúc sập). Fill ở giá sim, phí ngầm cố định 0,1116 % notional vào.
  DD/ret ở đây là **cận lạc quan**.
- MTM dùng **giá close 1m** (Vision): không bắt được râu nến trong phút. DD trong phút bị đánh giá thấp.
- **HO chỉ có 1 đợt sập** (T2/2026). HO4 đã bị nhìn nhiều lần (không sạch). 8 seed chỉ là nhiễu mô hình, không phải đường đi thị trường:
  khoảng [min … max] KHÔNG phải khoảng tin cậy.
- DEV là **in-sample** với X14: ngưỡng cờ được chọn trên 2021–25.
- Không đo: Sharpe/Sortino theo quý; tail kiểu sập > 3 tuần (giữ loser tới 21 ngày); năng lực (capacity); trễ publish ALT_EW (Vision) cho cờ live; khác biệt live 242 so với sim.
- Funding 2026 lấy từ bundle sim (`sim-ho26a`), chưa đối chiếu funding thực.
- Lỗi MTM legacy 00:00 UTC (xem trên): chưa sửa ở nguồn `gvz_mtm.py`; ảnh hưởng tới chỉ số phút-trong-ngày ở các báo cáo trước CHƯA đo lại.
