# FUNDNEG_T1 — long khi funding âm cực đoan: KẾT QUẢ

Prereg: `docs/prereg/PREREG_FUNDNEG_T1.md`, commit `66862db3`, sha256 `8985f26fa41079b0ce5e5c542a80f24123b4e6f6657abcf13e5b1b55eb1702dc` (commit TRƯỚC khi tính bất kỳ return nào). Code: `research/fundneg_t1/` (hash trong `docs/result/fundneg_t1/code_sha.txt`). Agent: fundnegT1, 2026-10-23.

## VERDICT: **NO-GO cả 4 biến thể** (theo tiêu chí prereg, tập NON-OVERLAP)

- F1 trượt ở CẢ 4 biến thể: mean net kỳ KIỂM dương (+0,22 … +1,08 %/lệnh) nhưng CI 95 % bootstrap theo ngày luôn chứa 0 (cận dưới −0,27 … −1,27 %).
- F4 trượt ở CẢ 4: kỳ KIỂM mean net < p95 control (lệnh ngẫu nhiên cùng giờ, cùng tercile vol) ở mọi biến thể. Control p50 dương ở 7/8 ô (biến thể × kỳ) ⇒ một phần đáng kể "edge" là thời điểm thị trường, không riêng coin bị short-crowding.
- F2, F3 đạt cả 4; F5 đạt 3/4 (trượt thr−0,05 %/H24).
- Không có ỨNG VIÊN (cần F1 đạt).

Đọc rủi ro (post-hoc, mô tả — không đổi verdict):
1. **Không có alpha HƯỚNG ở kỳ KIỂM.** Thành phần giá (gross − phí) kỳ KIỂM ÂM ở cả 4 biến thể (−0,23 … −1,06 %/lệnh); mean net dương chỉ nhờ funding nhận được (+0,45 … +2,14 %/lệnh) ⇒ thực chất là carry (hướng đã đóng), không phải squeeze.
2. **Mean do vài lệnh đuôi quyết định.** Median kỳ KIỂM âm (−0,68 … −2,10 %), hit 42–44 %. Cắt 1 % hai đuôi ⇒ mean KIỂM âm ở cả 4 biến thể. Lệnh lớn nhất: MYXUSDT 2025-08-04 +1150 % (giá ×7,6 trong 72h; funding tới −2 %/1h, Σrate −79 % qua 72 lần settle, notional theo giá ⇒ +490 % funding) — không thể tái lập ở quy mô, coin 1h-interval mới niêm yết.
3. **Không ổn định theo năm.** NON 2024 âm ở cả 4 biến thể (−0,12 … −2,30 %), 2025 dương; 2025 chiếm 75–83 % lệnh KIỂM (bùng nổ coin funding 4h/1h).
4. Theo interval: coin 8h kỳ KIỂM net âm ở cả 4 biến thể (−0,48 … −4,13 %); 4h ≈ 0; phần dương chủ yếu từ coin 1h (n nhỏ, đuôi cực lớn).

## Bảng 1 — Tiêu chí (tập NON-OVERLAP)

| biến thể | KIỂM n | KIỂM mean net | CI95 ngày | KIỂM net2 (×2 phí) | ctrl p95 KIỂM | KHÁM PHÁ n | KHÁM PHÁ mean | ctrl p95 KP | n 2024 / 2025 | F1 | F2 | F3 | F4 | F5 | VERDICT |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| thr-0.05_H24 | 3998 | +0.22% | [-0.27%, +0.78%] | -0.08% | +0.39% | 2316 | +0.45% | +0.42% | 859 / 3139 | trượt | ĐẠT | ĐẠT | trượt | trượt | **NO-GO** |
| thr-0.05_H72 | 2041 | +0.74% | [-0.68%, +2.45%] | +0.44% | +1.01% | 1388 | +0.87% | +1.09% | 505 / 1536 | trượt | ĐẠT | ĐẠT | trượt | ĐẠT | **NO-GO** |
| thr-0.10_H24 | 2066 | +0.38% | [-0.35%, +1.27%] | +0.08% | +0.48% | 855 | +0.39% | +0.46% | 351 / 1715 | trượt | ĐẠT | ĐẠT | trượt | ĐẠT | **NO-GO** |
| thr-0.10_H72 | 1050 | +1.08% | [-1.27%, +4.23%] | +0.78% | +1.92% | 537 | +1.37% | +1.13% | 211 / 839 | trượt | ĐẠT | ĐẠT | trượt | ĐẠT | **NO-GO** |

## Bảng 2 — Chi tiết theo tập × kỳ (net = sau phí 0,30 %/vòng + funding thật)

| biến thể | tập/kỳ | n | ngày | mean net | median | hit | mean gross | mean funding | settle/lệnh | net2 | CI95 ngày | ctrl p50 | ctrl p95 | MFE med | MAE med |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| thr-0.05_H24 | NON_DISC | 2316 | 603 | +0.45% | -0.03% | 49.5% | +0.51% | +0.24% | 3.1 | +0.15% | [+0.02%, +0.90%] | +0.29% | +0.42% | +3.40% | -3.17% |
| thr-0.05_H24 | NON_TEST | 3998 | 589 | +0.22% | -0.68% | 44.4% | +0.07% | +0.45% | 7.5 | -0.08% | [-0.27%, +0.78%] | +0.19% | +0.39% | +3.89% | -4.10% |
| thr-0.05_H24 | ALL_DISC | 3256 | 686 | +0.15% | -0.08% | 49.3% | +0.20% | +0.25% | 3.1 | -0.15% | [-0.85%, +1.13%] | +0.01% | +0.14% | +3.77% | -3.69% |
| thr-0.05_H24 | ALL_TEST | 4660 | 661 | +0.13% | -0.75% | 44.2% | -0.02% | +0.45% | 7.5 | -0.17% | [-0.35%, +0.64%] | +0.01% | +0.22% | +4.04% | -4.40% |
| thr-0.05_H72 | NON_DISC | 1388 | 515 | +0.87% | -0.06% | 49.7% | +0.73% | +0.44% | 9.1 | +0.57% | [-0.07%, +1.84%] | +0.82% | +1.09% | +5.85% | -5.55% |
| thr-0.05_H72 | NON_TEST | 2041 | 538 | +0.74% | -1.50% | 44.2% | -0.18% | +1.21% | 20.7 | +0.44% | [-0.68%, +2.45%] | -0.07% | +1.01% | +6.58% | -7.43% |
| thr-0.05_H72 | ALL_DISC | 1958 | 594 | +0.62% | -0.23% | 48.8% | +0.47% | +0.45% | 9.1 | +0.32% | [-0.64%, +1.89%] | +0.51% | +0.77% | +6.45% | -6.24% |
| thr-0.05_H72 | ALL_TEST | 2454 | 606 | +0.93% | -1.12% | 45.5% | +0.11% | +1.13% | 20.6 | +0.63% | [-0.51%, +2.60%] | +0.37% | +1.25% | +6.87% | -7.58% |
| thr-0.10_H24 | NON_DISC | 855 | 425 | +0.39% | -0.16% | 48.8% | +0.23% | +0.46% | 3.1 | +0.09% | [-0.17%, +0.98%] | +0.26% | +0.46% | +3.54% | -3.69% |
| thr-0.10_H24 | NON_TEST | 2066 | 516 | +0.38% | -0.85% | 43.9% | -0.10% | +0.78% | 9.0 | +0.08% | [-0.35%, +1.27%] | +0.18% | +0.48% | +4.24% | -4.63% |
| thr-0.10_H24 | ALL_DISC | 1235 | 508 | -0.14% | -0.33% | 47.9% | -0.31% | +0.48% | 3.2 | -0.44% | [-1.75%, +1.39%] | -0.08% | +0.16% | +4.06% | -4.18% |
| thr-0.10_H24 | ALL_TEST | 2411 | 581 | +0.32% | -0.89% | 43.8% | -0.15% | +0.77% | 8.8 | +0.02% | [-0.37%, +1.11%] | +0.03% | +0.33% | +4.45% | -4.92% |
| thr-0.10_H72 | NON_DISC | 537 | 323 | +1.37% | -0.43% | 46.2% | +0.84% | +0.83% | 9.3 | +1.07% | [+0.00%, +2.74%] | +0.64% | +1.13% | +6.27% | -6.22% |
| thr-0.10_H72 | NON_TEST | 1050 | 432 | +1.08% | -2.10% | 41.9% | -0.76% | +2.14% | 24.5 | +0.78% | [-1.27%, +4.23%] | +0.14% | +1.92% | +6.81% | -8.32% |
| thr-0.10_H72 | ALL_DISC | 785 | 395 | +0.66% | -0.75% | 44.8% | +0.12% | +0.85% | 9.3 | +0.36% | [-1.08%, +2.43%] | +0.46% | +0.87% | +6.51% | -7.09% |
| thr-0.10_H72 | ALL_TEST | 1283 | 496 | +1.88% | -1.48% | 44.8% | +0.19% | +1.99% | 24.2 | +1.58% | [-0.54%, +4.71%] | +0.93% | +2.45% | +7.31% | -8.33% |

## Bảng 3 — Số sự kiện/năm và mean net theo năm

| biến thể | sự kiện thô mọi symbol | sự kiện thô trong universe | ALL (sau 1-vị-thế) | NON | mean net NON theo năm |
|---|---|---|---|---|---|
| thr-0.05_H24 | 2022:6539 / 2023:4699 / 2024:7886 / 2025:73098 | 2022:4024 / 2023:1974 / 2024:2434 / 2025:16989 | 2022:2236 / 2023:1020 / 2024:1014 / 2025:3646 | 2022:1503 / 2023:813 / 2024:859 / 2025:3139 | 2022:+0.23% / 2023:+0.87% / 2024:-0.22% / 2025:+0.34% |
| thr-0.05_H72 | 2022:6539 / 2023:4699 / 2024:7886 / 2025:73098 | 2022:4024 / 2023:1974 / 2024:2434 / 2025:16989 | 2022:1344 / 2023:614 / 2024:613 / 2025:1841 | 2022:911 / 2023:477 / 2024:505 / 2025:1536 | 2022:+0.45% / 2023:+1.67% / 2024:-0.12% / 2025:+1.02% |
| thr-0.10_H24 | 2022:2530 / 2023:2654 / 2024:4014 / 2025:44126 | 2022:1421 / 2023:883 / 2024:998 / 2025:10524 | 2022:792 / 2023:443 / 2024:429 / 2025:1982 | 2022:503 / 2023:352 / 2024:351 / 2025:1715 | 2022:+0.26% / 2023:+0.58% / 2024:-1.32% / 2025:+0.73% |
| thr-0.10_H72 | 2022:2530 / 2023:2654 / 2024:4014 / 2025:44126 | 2022:1421 / 2023:883 / 2024:998 / 2025:10524 | 2022:509 / 2023:276 / 2024:272 / 2025:1011 | 2022:321 / 2023:216 / 2024:211 / 2025:839 | 2022:+0.50% / 2023:+2.65% / 2024:-2.30% / 2025:+1.93% |

Đếm loại: 
- thr-0.05_H24: ngoài dữ liệu (exit > 2025-12-31) 107; thiếu nến vào 23; thiếu nến ra 0; bỏ do 1-vị-thế/coin 17375; lệnh ALL 7916; OVERLAP 1602 (cờ a sym±24h 654, cờ b ngày sập 1254); control pool = cả universe (coin không có vol30) 35; pool median 32 coin; NON sau 2025-11-21 (X14 dừng): KIỂM 482.
- thr-0.05_H72: ngoài dữ liệu (exit > 2025-12-31) 310; thiếu nến vào 23; thiếu nến ra 0; bỏ do 1-vị-thế/coin 20676; lệnh ALL 4412; OVERLAP 983 (cờ a sym±24h 362, cờ b ngày sập 799); control pool = cả universe (coin không có vol30) 21; pool median 32 coin; NON sau 2025-11-21 (X14 dừng): KIỂM 227.
- thr-0.10_H24: ngoài dữ liệu (exit > 2025-12-31) 83; thiếu nến vào 3; thiếu nến ra 0; bỏ do 1-vị-thế/coin 10094; lệnh ALL 3646; OVERLAP 725 (cờ a sym±24h 320, cờ b ngày sập 553); control pool = cả universe (coin không có vol30) 19; pool median 32 coin; NON sau 2025-11-21 (X14 dừng): KIỂM 295.
- thr-0.10_H72: ngoài dữ liệu (exit > 2025-12-31) 242; thiếu nến vào 3; thiếu nến ra 0; bỏ do 1-vị-thế/coin 11513; lệnh ALL 2068; OVERLAP 481 (cờ a sym±24h 197, cờ b ngày sập 381); control pool = cả universe (coin không có vol30) 14; pool median 32 coin; NON sau 2025-11-21 (X14 dừng): KIỂM 124.

## Bảng 4 — Tập trung theo coin (NON)

| biến thể | kỳ | số coin | top-5 coin (số lệnh, Σnet) | top-5 tỷ trọng lệnh | top-5 tỷ trọng Σnet | mean net bỏ top-5 |
|---|---|---|---|---|---|---|
| thr-0.05_H24 | NON_DISC | 164 | AXSUSDT(216, +0.39), APEUSDT(103, +0.90), WAVESUSDT(83, +0.07), RLCUSDT(65, +0.34), KAVAUSDT(62, +0.19) | 22.8% | 18.1% | +0.48% |
| thr-0.05_H24 | NON_TEST | 264 | ENAUSDT(167, -0.99), MOVEUSDT(152, -0.26), TIAUSDT(131, +1.20), BERAUSDT(120, -1.02), OMUSDT(117, +0.92) | 17.2% | -1.7% | +0.27% |
| thr-0.05_H72 | NON_DISC | 162 | AXSUSDT(103, -0.19), APEUSDT(44, +0.47), WAVESUSDT(38, +0.10), RLCUSDT(36, +0.48), TRXUSDT(36, +0.49) | 18.5% | 11.1% | +0.95% |
| thr-0.05_H72 | NON_TEST | 260 | ENAUSDT(79, -1.06), TIAUSDT(69, +0.56), MOVEUSDT(57, -0.65), OMUSDT(55, +0.61), BERAUSDT(51, -1.22) | 15.2% | -11.7% | +0.97% |
| thr-0.10_H24 | NON_DISC | 113 | AXSUSDT(54, +0.22), WAVESUSDT(44, -0.38), APEUSDT(43, +0.35), FOOTBALLUSDT(33, +0.02), RSRUSDT(31, +0.59) | 24.0% | 24.0% | +0.39% |
| thr-0.10_H24 | NON_TEST | 199 | MOVEUSDT(106, -0.19), ENAUSDT(76, -0.19), OMUSDT(69, +0.08), SOONUSDT(59, -0.45), TIAUSDT(56, +0.33) | 17.7% | -5.2% | +0.49% |
| thr-0.10_H72 | NON_DISC | 112 | AXSUSDT(39, -0.11), APEUSDT(22, +0.67), WAVESUSDT(21, -0.34), RSRUSDT(19, +1.31), OCEANUSDT(19, +0.51) | 22.3% | 28.0% | +1.27% |
| thr-0.10_H72 | NON_TEST | 197 | ENAUSDT(44, -0.53), MOVEUSDT(43, -0.23), OMUSDT(37, -0.30), IPUSDT(27, -1.33), BERAUSDT(27, -0.59) | 17.0% | -26.4% | +1.64% |

## Bảng 5 — Sleeve 2 % vốn/lệnh (compounding, equity thực hiện)

| biến thể | tập/kỳ | equity cuối | CAGR | maxDD | max đồng thời |
|---|---|---|---|---|---|
| thr-0.05_H24 | NON_DISC | 1.2254 | +10.70% | -4.77% | 21 |
| thr-0.05_H24 | NON_TEST | 1.1647 | +7.92% | -13.96% | 30 |
| thr-0.05_H24 | ALL_DISC | 1.0425 | +2.10% | -22.17% | 69 |
| thr-0.05_H24 | ALL_TEST | 1.0837 | +4.10% | -16.92% | 55 |
| thr-0.05_H72 | NON_DISC | 1.2568 | +12.11% | -6.58% | 25 |
| thr-0.05_H72 | NON_TEST | 1.2623 | +12.35% | -15.21% | 31 |
| thr-0.05_H72 | ALL_DISC | 1.2361 | +11.18% | -22.77% | 73 |
| thr-0.05_H72 | ALL_TEST | 1.4370 | +19.88% | -18.00% | 60 |
| thr-0.10_H24 | NON_DISC | 1.0676 | +3.33% | -4.40% | 10 |
| thr-0.10_H24 | NON_TEST | 1.1529 | +7.37% | -13.35% | 17 |
| thr-0.10_H24 | ALL_DISC | 0.9472 | -2.67% | -15.65% | 37 |
| thr-0.10_H24 | ALL_TEST | 1.1407 | +6.80% | -14.01% | 46 |
| thr-0.10_H72 | NON_DISC | 1.1542 | +7.43% | -4.34% | 13 |
| thr-0.10_H72 | NON_TEST | 1.2001 | +9.55% | -13.79% | 17 |
| thr-0.10_H72 | ALL_DISC | 1.1018 | +4.97% | -9.86% | 41 |
| thr-0.10_H72 | ALL_TEST | 1.5151 | +23.09% | -14.62% | 48 |

## Bảng 6 — Tương quan với BTC trend (NON)

| biến thể | kỳ | ρ Pearson net~BTC 7d trước | ρ Spearman | ρ Pearson net~BTC trong lúc giữ | tỷ lệ lệnh BTC7d<0 | mean net khi BTC7d<0 | khi ≥0 |
|---|---|---|---|---|---|---|---|
| thr-0.05_H24 | NON_DISC | -0.035 | -0.068 | 0.467 | 58.4% | +0.69% | +0.12% |
| thr-0.05_H24 | NON_TEST | -0.034 | -0.048 | 0.176 | 53.0% | +0.54% | -0.13% |
| thr-0.05_H72 | NON_DISC | -0.056 | -0.111 | 0.477 | 59.2% | +1.12% | +0.52% |
| thr-0.05_H72 | NON_TEST | -0.026 | -0.055 | 0.163 | 52.5% | +1.35% | +0.06% |
| thr-0.10_H24 | NON_DISC | -0.023 | -0.016 | 0.347 | 52.2% | +0.71% | +0.04% |
| thr-0.10_H24 | NON_TEST | -0.040 | -0.054 | 0.107 | 51.5% | +0.87% | -0.14% |
| thr-0.10_H72 | NON_DISC | -0.033 | -0.057 | 0.363 | 52.0% | +2.04% | +0.64% |
| thr-0.10_H72 | NON_TEST | -0.020 | -0.035 | 0.115 | 49.5% | +1.95% | +0.23% |

## Bảng 7 — POST-HOC mô tả (KHÔNG vào tiêu chí): đuôi, thành phần giá vs funding, theo interval (NON)

| biến thể | kỳ | n | min | p1 | p50 | p99 | max | mean cắt 1 % hai đuôi | mean chỉ giá (gross−0,30 %) | mean funding | funding>0 | theo interval_h [n, net, gross, fund] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| thr-0.05_H24 | DISC | 2316 | -30.57% | -13.96% | -0.03% | +24.82% | +79.69% | +0.28% | +0.21% | +0.24% | 89% | 4h:[48, +3.71%, +2.94%, +1.07%]; 8h:[2268, +0.38%, +0.46%, +0.22%] |
| thr-0.05_H24 | TEST | 3998 | -54.97% | -22.63% | -0.68% | +29.24% | +605.07% | -0.22% | -0.23% | +0.45% | 89% | 1h:[421, +1.91%, +0.64%, +1.56%]; 4h:[3045, +0.11%, +0.08%, +0.34%]; 8h:[532, -0.48%, -0.41%, +0.24%] |
| thr-0.05_H72 | DISC | 1388 | -73.46% | -23.64% | -0.06% | +50.61% | +124.13% | +0.47% | +0.43% | +0.44% | 84% | 4h:[21, +8.19%, +6.07%, +2.42%]; 8h:[1367, +0.76%, +0.65%, +0.41%] |
| thr-0.05_H72 | TEST | 2041 | -69.80% | -31.88% | -1.50% | +48.94% | +1150.12% | -0.51% | -0.48% | +1.21% | 83% | 1h:[153, +12.27%, +5.25%, +7.32%]; 4h:[1562, -0.01%, -0.49%, +0.77%]; 8h:[326, -1.09%, -1.22%, +0.44%] |
| thr-0.10_H24 | DISC | 855 | -30.57% | -15.51% | -0.16% | +31.56% | +79.69% | +0.18% | -0.07% | +0.46% | 91% | 4h:[40, +3.45%, +2.47%, +1.29%]; 8h:[815, +0.24%, +0.12%, +0.42%] |
| thr-0.10_H24 | TEST | 2066 | -54.97% | -31.11% | -0.85% | +37.00% | +544.70% | -0.27% | -0.40% | +0.78% | 94% | 1h:[363, +2.24%, +0.75%, +1.80%]; 4h:[1531, +0.12%, -0.16%, +0.57%]; 8h:[172, -1.21%, -1.43%, +0.52%] |
| thr-0.10_H72 | DISC | 537 | -39.26% | -27.38% | -0.43% | +55.82% | +124.13% | +0.84% | +0.54% | +0.83% | 88% | 4h:[17, +14.05%, +11.54%, +2.81%]; 8h:[520, +0.95%, +0.49%, +0.76%] |
| thr-0.10_H72 | TEST | 1050 | -69.80% | -35.61% | -2.10% | +59.19% | +1150.12% | -1.02% | -1.06% | +2.14% | 90% | 1h:[140, +13.16%, +5.50%, +7.96%]; 4h:[801, -0.33%, -1.32%, +1.29%]; 8h:[109, -4.13%, -4.72%, +0.89%] |

Top-3 lệnh NON KIỂM theo net (thr-0.10_H72): MYXUSDT +1150.12%; MYXUSDT +660.79%; AIAUSDT +236.71%

## Validation

| mã | kiểm | kết quả |
|---|---|---|
| V1 | offset `ts` (calc_time) so với tròn giờ, mọi dòng 2022–25 | max 31 ms (< 60 s: True) |
| V1 | CSV Vision gốc tải lại BTCUSDT 2024-03 (header calc_time,funding_interval_hours,last_funding_rate) vs parquet | 93/93 dòng khớp, max|Δrate| = 0, interval lệch 0, calc_time offset max 4 ms |
| V1 | CSV Vision gốc tải lại 1000000BOBUSDT 2025-06 (header calc_time,funding_interval_hours,last_funding_rate) vs parquet | 154/154 dòng khớp, max|Δrate| = 0, interval lệch 0, calc_time offset max 20 ms |
| V1 | CSV Vision gốc tải lại ETHUSDT 2022-06 (header calc_time,funding_interval_hours,last_funding_rate) vs parquet | 90/90 dòng khớp, max|Δrate| = 0, interval lệch 0, calc_time offset max 25 ms |
| V1 | t_in > τ mọi lệnh (assert trong run + checks) | True |
| V2 | dtype ts funding / panel hr / tau,t_in,t_out lệnh | int64 / int64 / int64 |
| V2 | trùng (sym, τ) funding / lệnh | 0 / 0 |
| V3 | tái lập độc lập thr-0.10_H24 KIỂM — ALL | pipeline n=2411 mean=0.003164290804984; độc lập n=2411 mean=0.003164290804984; Δ=-1.30e-17 |
| V3 | tái lập độc lập thr-0.10_H24 KIỂM — NON | pipeline n=2066 mean=0.003803061530877; độc lập n=2066 mean=0.003803061530877; Δ=-1.30e-17 |
| V4 | 10 lệnh ngẫu nhiên (seed 7) đọc lại nến 1m thô + dòng funding, tính tay | khớp cả 10: True (chi tiết `checks.json`) |
| V5 | dấu funding qua `accrue()`: rate âm ×3 (τ loại, τ+H nhận) / rate dương / hỗn hợp + thiếu giá | [0.002999999999999957, 0.003] / [-0.001, -0.001] / [0.0027500000000000007, 0.00275] → PASS |

ADDENDUM 1 — trước/sau sửa: max |Δ| (mean net, net2, ctrl p95, mọi biến thể/tập/kỳ) = 1.86e-10; số lệnh và F1–F5 không đổi.

## Lệch thiết kế (đã ghi trong prereg trước khi chạy)
1. Seed thứ 8 = `tsx-x14-a1` (glob `tsx-x14-s*` chỉ có 7 seed) — theo quy ước LIQ_PROXY.
2. "Close nến 1m τ+1′" = nến có open time τ+1′ (đóng τ+2′) — trễ thêm 1 phút, bảo thủ.
3. Overlap (a) = khoảng giữ leg X14 giao [τ−24h, τ+24h] (rộng hơn "leg bắt đầu trong ±24h").
4. F3 = MỖI năm kiểm ≥ 50 (chặt hơn trung bình) — đạt ở mọi biến thể nên không ảnh hưởng verdict.
5. Funding cashflow = −rate × P(τ')/P0 (notional theo giá, qty cố định) thay vì notional cố định — đúng cơ chế, nhưng khuếch đại đuôi khi giá tăng mạnh (MYX).

## ADDENDUM 1 (sau khi thấy kết quả — bug số học, không phải logic)
V3 lần đầu: Δ mean = 9,1e-12 (đạt < 1e-9) nhưng sai lệch TỪNG lệnh tới 1,6e-8. Nguyên nhân: `accrue()` dùng cumsum TOÀN CỤC của rate×P qua mọi symbol (độ lớn ~1e4–1e5) rồi lấy hiệu, chia P0 của coin giá thấp ⇒ mất chính xác. Sửa: cumsum theo TỪNG symbol (`core.Funding.build_cs`, `accrue`). Sau sửa: Δ mean V3 = 1,3e-17, max sai lệch từng lệnh 1,2e-15. Trước/sau: max |Δ| mọi mean net / net2 / ctrl p95 = 1,9e-10; số lệnh và F1–F5 không đổi (`results_pre_addendum1.json` lưu ở thư mục làm việc, không commit).

## Điểm nghi ngờ / rủi ro của chính agent
- **Vi phạm ngân sách RAM**: `build_panel.py` (1m → panel giờ/ngày, từng tháng) đạt max RSS **7,68 GB** (> trần 5 GB của brief) ở các tháng 2025 (~23 triệu dòng 1m/tháng, pandas groupby). Không bị watchdog kill, không ảnh hưởng kết quả, nhưng là vi phạm luật cứng — lần sau phải xử lý theo row-group/symbol. Các bước sau: run 3,1 GB, V3 3,8 GB, checks 0,7 GB.
- X14 printDone dừng 2025-11-21 ⇒ 124–482 lệnh NON kỳ KIỂM sau mốc này không thể bị gắn cờ overlap (có thể là lệnh "ngày sập" thật, vd. sập đầu 12/2025 nếu có).
- Overlap chỉ dựa trên X14 sim (8 seed), không dựa trên lệnh live.
- Exit fallback: delist 0–3 lệnh/tập, gap 0–5 — không đáng kể. 3–23 sự kiện thiếu nến vào (giờ niêm yết) bị bỏ.
- f_8h nhân 8 lần rate 1h: coin 1h với rate −0,0125 %/h đã thành −0,10 % ⇒ 2025 có rất nhiều sự kiện từ coin 1h/4h mới niêm yết; tính thanh khoản/khả năng khớp lệnh 2 % vốn ở các coin này CHƯA kiểm.
- Control rút từ universe top-100 cùng tercile vol nhưng không khớp interval funding ⇒ control có thể nhận ít funding hơn (nhiều coin 8h) — so sánh F4 vì vậy hơi THIÊN VỀ phía sự kiện; dù vậy F4 vẫn trượt.
- HO 2026: không chạy (không cần cho verdict; brief chỉ cho mô tả).

## Artefact (`docs/result/fundneg_t1/`)
`results.json` (mọi số trên), `posthoc_desc.json` (Bảng 7), `checks.json` (V1/V2/V4/V5), `v3_independent_summary.json`, `universe.json` (48 tháng × 100 coin), `code_sha.txt`. `trades_*.parquet` (lệnh từng biến thể, có cờ overlap, P0/P1/funding/MFE/MAE). Ma trận control (`ctrl_*.npy`, 100 seed) không commit — tái tạo bằng `run.py` (seed cố định). Bảng trong file này sinh tự động bởi `research/fundneg_t1/gen_tables.py` từ JSON.
