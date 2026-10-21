# TS_MKT_EXT — phân tích sâu (mô tả) P0 vs X14 — 2026-10-21

Chỉ MÔ TẢ trên run đã có (DEV 8 seed `gqsf-*` vs `tsx-x14-*`; HO W9 8 seed `ho4-k24-b-s*` vs `tsx-ho-x14-s*`). Không đổi luật, không tune ngưỡng, không chạy lại sim, 2020 không dùng, không đọc 242.
Script + dữ liệu: `docs/result/ts_mkt_ext/deep/` (`deep_mtm_dev.py`, `deep_mtm_ho.py`, `deep_analysis.py`, `deep_extra.py`, `deep_compact.py`; ra `deep.json`, `deep_tables.md` (bảng đủ min/max), `deep_extra.md`, `deferred_clusters.csv` (1 476 cụm hoãn, mọi seed), `altew_dd_daily.csv`). Cache equity phút (không commit): `~/claude_master/tsx/deep_cache/`.

## 1. Validate (PASS — dừng nếu không khớp)
| Mục | Doc | Tái lập | Sai lệch |
|---|---|---|---|
| DEV ΔPnL/seed (TB) | +12,2k | +12 185 | 0 (ΣPnL từng run khớp `ts_mkt_ext.json` 3e-11) |
| CAGR22 P0 / X14 (TB) | 36,98 / 39,49 | 36,984 / 39,490 | 0,000pp (cùng `n700.arm_metrics`) |
| DD22 MTM P0 / X14 (TB) | −22,55 / −22,55 | −22,546 / −22,547 (từ equity phút ghi lại) | 0,000pp |
| DD MTM theo năm UTC (16 run × 5 năm) | `mtm_vision.json` | equity phút mới | max \|Δ\| = 0 |
| HO ΔPnL W9/seed (TB) | +3 348 | +3 347,9 | 0 |
| HO ROI baseline / ΔROI / ΔmaxDD | 10,19 / +2,30pp / +0,04 | 10,187 / +2,302 / +0,038 | ≤ 3e-14 |
| Cờ DEV / HO | 214 ngày 42 khoảng (sha c79ef302) / 15 ngày 4 khoảng | tính lại từ index.npz + ew_2026.npz | chuỗi khoảng trùng 100 % |
| Cụm hoãn (deferClusters / cutAfterDefer Java) | 16 run | tái dựng từ printDone | **16/16 khớp tuyệt đối** |

MTM: `gvz_mtm` import trước, `R._work is MT._work_vision` assert, missing = 0 (DEV 16 run, HO 16 run qua `ecm_mtm_h`/`ho4_score_a`, miss 0).
Quy ước giá cắt @168h: DEV = min(open, close) nến 1m Vision tại phút tuổi 168h+1' — kiểm trên 561 leg P0 bị cắt time-stop: 100 % trùng `tp` (rel < 1e-4). HO: cache `ecm_px` chỉ có close ⇒ proxy min(close[m−1], close[m]); trên 62 leg P0 2026 khớp 74 % < 1e-4, p95 lệch 0,09 % (đủ cho thống kê cụm, không bit-exact).
Định nghĩa: **leg** = 1 dòng printDone; **cụm** = (sym, giờ đóng) — các leg DCA đóng cùng phút, anchor = leg đầu (= `clusterFirstLegTime`); **đợt vào** = số anchor phân biệt. Cụm hoãn = cụm X14 tuổi > 168h+1' có mốc 168h rơi vào ngày cờ (UTC), loại cụm đã arm trước 168h (P0 cùng sym+anchor giữ > 168h không bị SL; chỉ 1 ca S13). PnL@168h = PnL thực + q·(px168 − tp) + funding·(1 − tỉ lệ thời gian tới mốc) (fee chỉ trên notional vào: pnl = q(tp−e) − 0,001116·q·e − funding, fit resid ≤ 2e-4 USD; funding chia tỉ lệ thời gian là xấp xỉ).

## 2. Bảng theo kỳ (median 8 seed; P0 / X14 / Δ). Min/max đủ trong `deep_tables.md`
Kỳ giao dịch theo giờ ĐÓNG (+07); MTM (DD, Calmar, tháng tệ, phơi nhiễm) theo trục UTC (DEV, khớp `dd_year`) / +07 (HO W9, khớp ecm). ROI = PnL thực hiện / số dư thực hiện đầu kỳ. Calmar = lợi nhuận MTM năm hoá / |DD phút|. Phơi nhiễm = notional mở / equity MTM, mẫu theo giờ.

| Chỉ số (median 8 seed) P0 / X14 / Δ | 2021H2 | 2022 | 2023 | 2024 | 2025 | DEV | 2026W9 |
|---|---|---|---|---|---|---|---|
| Số cụm | 586 / 586 / +0 | 590 / 572 / -15 | 760 / 758 / -2 | 840 / 840 / -1 | 710 / 710 / +0 | 3494 / 3472 / -18 | 441 / 441 / +0 |
| Số đợt vào | 110 / 110 / +0 | 175 / 170 / -3 | 124 / 124 / +0 | 156 / 156 / +0 | 209 / 209 / +0 | 772 / 768 / -4 | 88 / 88 / +0 |
| Số leg | 586 / 586 / +0 | 620 / 605 / -14 | 761 / 758 / -2 | 842 / 840 / -1 | 736 / 736 / +0 | 3552 / 3531 / -18 | 452 / 452 / +0 |
| Win leg % | 80,4 / 80,4 / +0,0 | 79,8 / 83,6 / +3,8 | 84,7 / 84,7 / +0,0 | 87,8 / 88,1 / +0,3 | 87,1 / 87,3 / +0,3 | 84,4 / 85,2 / +0,8 | 82,6 / 83,4 / +0,7 |
| PnL USD | 6262 / 6593 / +325 | 2789 / 4640 / +1752 | 29511 / 32014 / +2281 | 34745 / 37817 / +3125 | 36129 / 39737 / +3862 | 108922 / 119857 / +11415 | 15350 / 18106 / +3416 |
| ROI % | 17,9 / 18,8 / +0,9 | 6,7 / 11,1 / +4,1 | 66,3 / 68,3 / +2,2 | 47,2 / 48,6 / +1,5 | 33,8 / 35,2 / +1,3 | 311,2 / 342,4 / +32,6 | 10,9 / 12,7 / +2,3 |
| maxDD MTM phút % | -14,15 / -14,15 / +0,00 | -22,83 / -22,83 / +0,00 | -6,24 / -6,24 / -0,00 | -12,10 / -12,10 / -0,00 | -17,84 / -17,84 / +0,00 | -22,83 / -22,83 / +0,00 | -5,66 / -5,62 / +0,00 |
| maxDD EOD % | -6,46 / -6,46 / +0,00 | -16,06 / -17,17 / -0,81 | -3,22 / -3,22 / -0,00 | -6,49 / -6,65 / -0,03 | -2,84 / -3,43 / -0,49 | -16,06 / -17,17 / -0,81 | -4,14 / -4,14 / -0,00 |
| Calmar | 2,88 / 3,04 / +0,16 | 0,30 / 0,49 / +0,18 | 10,60 / 10,99 / +0,22 | 3,93 / 4,01 / +0,12 | 2,14 / 2,23 / +0,08 | 1,66 / 1,77 / +0,11 | 2,65 / 3,24 / +0,58 |
| Tháng tệ nhất % | -3,97 / -3,21 / +0,76 | -11,70 / -10,98 / +0,92 | -1,29 / -1,29 / -0,00 | -0,79 / -0,48 / +0,29 | -1,29 / -1,08 / +0,13 | -11,70 / -10,98 / +0,75 | -2,76 / -2,76 / -0,00 |
| Giữ TB h | 54,2 / 55,0 / +0,8 | 47,1 / 92,4 / +45,7 | 50,7 / 51,6 / +1,0 | 37,7 / 40,7 / +2,9 | 25,7 / 27,2 / +1,6 | 42,2 / 50,9 / +8,8 | 41,1 / 44,9 / +3,7 |
| Giữ p90 h | 168 / 168 / +0 | 168 / 482 / +314 | 168 / 168 / +0 | 168 / 168 / +0 | 111 / 111 / +0 | 168 / 168 / +0 | 168 / 168 / +0 |
| Cụm chạm 168h | 116 / 116 / +0 | 110 / 112 / +0 | 142 / 142 / -0 | 109 / 109 / +0 | 62 / 62 / +0 | 540 / 538 / -0 | 68 / 68 / +0 |
| Cụm cắt time-stop | 116 / 116 / +0 | 110 / 96 / -14 | 142 / 141 / -0 | 108 / 102 / -6 | 62 / 60 / -2 | 536 / 516 / -22 | 68 / 64 / -3 |
| Phơi nhiễm TB % | 8,5 / 8,6 / +0,1 | 3,7 / 7,3 / +3,7 | 5,9 / 6,0 / +0,1 | 4,8 / 5,1 / +0,3 | 3,0 / 3,2 / +0,2 | 4,8 / 5,8 / +1,0 | 3,7 / 4,0 / +0,3 |
| Phơi nhiễm max % | 54,1 / 54,1 / +0,0 | 60,8 / 60,8 / -0,0 | 53,7 / 53,7 / -0,0 | 53,4 / 53,4 / +0,1 | 49,6 / 49,6 / +0,0 | 60,8 / 60,8 / -0,0 | 45,1 / 45,1 / +0,0 |
| DD đỉnh→đáy (mode) P0 \| X14 | 09-07→09-07 \| 09-07→09-07 | 05-05→05-12 \| 05-05→05-12 | 04-27→06-10 \| 03-03→06-10 | 04-10→04-13 \| 04-10→04-13 | 08-14→10-10 \| 08-14→10-10 | 05-05→05-12 \| 05-05→05-12 | 02-02→02-06 \| 02-02→02-06 |
| Tháng tệ nhất (mode) P0 \| X14 | 2021-12 \| 2021-12 | 2022-05 \| 2022-05 | 2023-05 \| 2023-05 | 2024-06 \| 2024-06 | 2025-03 \| 2025-08 | 2022-05 \| 2022-05 | 2026-07 \| 2026-07 |

ΔPnL seed × kỳ: **0/48 ô âm** (2021H2 +321…+343, 2022 +1,1k…+3,1k, 2023 +1,8k…+3,0k, 2024 +2,6k…+5,3k, 2025 +3,5k…+5,9k, W9 +1,8k…+4,3k).
Đọc nhanh: (i) maxDD MTM phút năm gần như KHÔNG đổi (đáy năm rơi vào phút sập; tại mốc cắt, giữ hay cắt cho cùng equity MTM); (ii) maxDD EOD xấu hơn 2022 (−0,81pp) và 2025 (−0,49pp) — vốn bị giam qua đêm; (iii) 2022 là năm hoạt động nặng nhất: giữ TB 47→92h, p90 168→482h, phơi nhiễm TB 3,7→7,3 %, −15 cụm/−3 đợt vào.

## 3. ALT_EW và các đợt cờ
Ngày cờ ON theo năm: 2021 14 · 2022 78 · 2023 4 · 2024 51 · 2025 67 · 2026 (HO) 15. 42 đợt DEV + 4 đợt HO; chỉ **12/42 đợt DEV** và 2/4 đợt HO có cụm hoãn (các đợt còn lại không có cụm chưa arm nào chạm 168h trong ngày ON — ví dụ 2025-01-28→02-22, 26 ngày, dd −49 %, 0 cụm hoãn ⇒ luật vô hiệu ở đó).

Đợt có cụm hoãn (DEV; Δ direct = Σ(PnL thực − PnL@168h) cụm hoãn của đợt; median [min; max] 8 seed). Bảng đủ 42 đợt + "Δ đoạn" trong `deep_tables.md`.
| Đợt (UTC) | ngày ON | dd min | Sự kiện (gợi ý, chưa kiểm nguồn) | cụm hoãn/seed | Δ direct |
|---|---|---|---|---|---|
| 2021-12-10→12-11 | 2 | −33,6 | dư chấn flash crash 04/12/2021 | 25 | +326 [+321; +343] |
| 2022-01-22→02-04 | 14 | −43,9 | bán tháo 01/2022 | 15 | +777 [+705; +825] |
| 2022-05-08→06-08 | 32 | −62,0 | LUNA/UST | 43 | **+1 626** [+984; +1 863] |
| 2022-06-17→06-19 | 3 | −34,9 | Celsius/3AC | 0 (max 1) | +0 [+0; +94] |
| 2022-11-13→11-30 | 18 | −36,7 | FTX | 33 | +632 [+556; +837] |
| 2023-03-10→03-12 | 3 | −32,5 | SVB/USDC depeg | 11 | +692 [+563; +818] |
| 2024-04-14→04-20 | 7 | −38,4 | alt sập 04/2024 | 16 | **+1 456** [+1 387; +1 622] |
| 2024-06-19→07-10 | 22 | −45,4 | alt bleed 06/2024 + Mt.Gox | 7 | **−522** [−1 403; −129] |
| 2024-07-12 | 1 | −30,8 | (như trên) | 2 | +176 [+143; +258] |
| 2025-01-14 | 1 | −31,1 | điều chỉnh 01/2025 | 0 (max 1) | +0 [+0; +39] |
| 2025-03-10→03-14 | 5 | −35,5 | bán tháo 03/2025 | 6 | **+897** [+812; +1 963] |
| 2025-10-17→10-19 | 3 | −33,6 | dư chấn 10–11/10/2025 | 13 | +405 [+371; +580] |
| HO 2026-02-05→02-14 | 10 | −40,2 | (chưa xác minh) | 9 | **+2 987** [+1 485; +3 966] |
| HO 2026-06-11 | 1 | −30,2 | (chưa xác minh) | 5 | +228 [+94; +251] |

## 4. Cụm được hoãn
| | DEV (8 seed) | HO W9 (8 seed) |
|---|---|---|
| Cụm hoãn/seed | 172,5 [162; 179] (gộp 1 364) | 14 [12; 16] (gộp 112) |
| % được cứu (PnL thực > PnL@168h) | 77,4 [75,9; 80,9] | 71,4 [66,7; 75,0] |
| ΣΔ direct/seed | +6 493 [+5 714; +8 693] | +3 163 [+1 722; +4 217] |
| PnL thực vs @168h (Σ/seed) | −23,2k vs −30,0k | −4,1k vs −7,4k |
| Δ TB / median mỗi cụm | +37,7 / +24,4 | +234 / +85 |
| Giữ thêm TB (h) | 177 | 114 |
| Đuôi xấu nhất (gộp) | −643 (ARK 2024-06-18, cắt 504h); p5 −80 | −628 (PLAY 2026-02-01, cắt khi cờ tắt); p5 −576 |

Theo cách thoát (gộp 8 seed):
| Phạm vi | Thoát | n | % cứu | Δ TB | ΣΔ | giữ thêm TB h |
|---|---|---|---|---|---|---|
| DEV | cắt khi cờ tắt (00:00 UTC ngày OFF) | 711 | 90 | +48 | +34 293 | 77 |
| DEV | arm → trailing thắng | 181 | 99 | +120 | +21 766 | 132 |
| DEV | cắt ở 504h | 472 | **51** | **−4,5** | **−2 132** | 336 |
| HO | arm → trailing thắng | 27 | 100 | +899 | +24 283 | 93 |
| HO | cắt khi cờ tắt | 85 | 62 | +16 | +1 343 | 119 |
Không có cụm hoãn còn mở cuối kỳ. Direct theo năm đóng (DEV): 2021 +326 · 2022 +3 058 · 2023 +692 · 2024 +1 110 · 2025 +1 293.

## 5. ΔPnL đến từ đâu, phụ thuộc bao nhiêu đợt
Tách ΔPnL (median): DEV tổng +11 415 = direct +6 493 (54 % [49; 70]) + sizing ước tính +8 239 (lãi kép: size theo số dư lớn hơn, giả định size ∝ số dư thực hiện) + phần dư −3 229 (ít cụm/slot hơn, chọn lệnh khác). HO: tổng +3 416 = direct +3 163 (95 %) + sizing +146 + dư −55.
- "Δ đoạn" (ΔPnL thực hiện từ đầu đợt k tới đầu đợt k+1) gộp cả lãi kép ⇒ đợt không có cụm hoãn vẫn có Δ đoạn dương lớn (2023-05-12: +1 970, 0 cụm hoãn = lãi kép cả năm 05/2023→04/2024). Dùng direct để quy cho đợt.
- **DEV**: top-1 đợt (LUNA) = 25 % direct, top-3 (LUNA, 04/2024, 03/2025) = 61 %. Bỏ từng đợt: direct còn > 0 ở mọi đợt, 8/8 seed; bỏ top-3 vẫn +2 580 [+1 508; +3 441] (8/8). Theo Δ đoạn: bỏ top-1 còn +9 271 (8/8), bỏ top-3 +6 871 (8/8). Quy đổi thô có lãi kép (Δ tổng × (1 − tỉ trọng direct)) bỏ top-3 ≈ +4,5k. Chỉ 1 đợt âm: 2024-06-19→07-10 (−522/seed).
- **HO**: 1 sự kiện (02/2026) = 94 % direct / 95 % Δ đoạn; bỏ nó còn +228 / +191 mỗi seed (8/8 > 0, nhỏ). Và trong đợt đó gần như toàn bộ đến từ **3 cụm/seed arm → trailing** (SPACE, FIGHT, CLO; +2,9k/seed).
- Seed × năm: 0/48 ô âm (seed là nhiễu mô hình, corr cao — không phải đường thị trường độc lập).

## 6. Rủi ro
| | DEV P0 | DEV X14 | HO P0 | HO X14 |
|---|---|---|---|---|
| Phơi nhiễm TB trong giờ cờ ON (%) | 8,3 | 15,7 (+7,4pp) | 5,1 | 11,3 (+6,1pp) |
| Vốn giam bởi cụm hoãn / equity: TB giờ ON / max | – | 7,7 % / **52,9 %** [41; 56] | – | 6,1 % / 11,7 % |
| Phơi nhiễm max toàn kỳ (%) | 60,8 | 60,8 | 45,1 | 45,1 |
| Phơi nhiễm ngoài giờ ON (%) | 4,28 | 4,28 | 3,58 | 3,58 |

DD trong cửa sổ [đầu sự kiện, cuối + 15 ngày] (MTM phút, reset đầu cửa sổ), Δ X14−P0 median: 12/2021 **−2,2pp** (−2,4 → −4,6); 03/2023 −0,8pp; 04/2024 −0,3pp; 06–07/2024 −0,35pp (và ret −0,56pp); 10–12/2025 −0,4pp; LUNA 0,0 (đáy −22,8 % ngày 05-12 như nhau: tại mốc cắt, giữ hay cắt cho cùng equity MTM — khác biệt chỉ xuất hiện sau đó); HO 02/2026 0,0.
Lỡ crash-buy: chỉ thấy ở LUNA (04-27→07-04/2022): cụm vào mới P0 281,5 vs X14 269,5 (−15,5/seed, tệ nhất −27); lệnh chỉ P0 có 38/seed (PnL +1 275) vs chỉ X14 có 23,5 (+541) ⇒ mất cơ hội ≈ −0,7k/seed. Các sự kiện khác 0 (06/2024 −1). HO: 0 (tệ nhất −2).
Đuôi: đợt dài > 3 tuần (06/2024, 22 ngày ON) là đợt duy nhất âm — 39 cụm (gộp) cắt ở 504h đều thua so với cắt 168h (−7 259 gộp, 0 % cứu), chỉ bù một phần bởi 16 cụm arm (+3 301). Kênh 504h nhìn chung không có edge (51 % cứu); dương ở LUNA (245 cụm, +2 738, 57 %) và FTX (188, +2 390, 54 %) nhờ hồi kịp trước 21 ngày. Đợt LUNA (32 ngày ON liên tục) dương chủ yếu nhờ arm → trailing (85 cụm, +9 298 gộp).

## 7. Độ gần ngưỡng (dd ALT_EW trong [−0,33; −0,27])
| | DEV | HO 2026 |
|---|---|---|
| Ngày ON "sát ngưỡng" (dd ∈ [−0,33; −0,30]) / tổng ON | 96 / 214 (45 %) | 7 / 15 |
| Ngày OFF sát ngưỡng (dd ∈ (−0,30; −0,27]) | 115 | 15 |
| Cụm hoãn có ngày bắt đầu hoãn sát ngưỡng: n / Δ direct | 63,5 / +1 902 [+148; +3 960] (29 % direct) | 5 / +228 |
| Cụm hoãn chạm ≥ 1 ngày sát ngưỡng: n / Δ direct | 87,5 / +3 863 [+2 675; +5 776] (59 %) | 12 / +1 479 (47 %) |
| Cụm X14 bị cắt 168h trong ngày OFF sát ngưỡng: n / PnL / notional | 61,5 / −7,2k / 56k | 0 |
Theo năm (ON sát / OFF sát): 2021 10/11 · 2022 22/24 · 2023 4/8 · 2024 30/20 · 2025 30/52 · 2026 7/15. ⇒ Kết quả nhạy với ngưỡng: ~½ ngày ON ở sát −30 %; ~30–60 % direct gắn với ngày có thể lật bởi sai số ±3pp của ALT_EW (ví dụ khác universe/độ trễ dữ liệu live).

## 8. Kết luận ngắn
1. **Edge đến từ đâu**: ~54 % ΔPnL DEV là hiệu ứng trực tiếp của việc không cắt đáy 168h (cụm hoãn: 77 % được cứu, chủ yếu qua *cắt khi cờ tắt* (+34k gộp, 90 % cứu) và *arm → trailing* (+22k, 99 % cứu)); phần còn lại là lãi kép từ số dư lớn hơn trừ hao hụt slot/vốn. Kênh "giữ tới 504h" không có edge (−2,1k gộp). HO: ~95 % là direct, tập trung 3 cụm/seed arm thắng.
2. **Phụ thuộc đợt**: DEV — chỉ 12/42 đợt có tác dụng; top-3 đợt = 61 % direct nhưng bỏ top-3 vẫn dương 8/8 ⇒ không phụ thuộc 1 đợt. HO — gần như 1 sự kiện (02/2026), không chứng minh độ bền ngoài mẫu qua nhiều đợt.
3. **Rủi ro**: DD phút năm không đổi, nhưng DD EOD xấu hơn 2022/2025, DD cục bộ trong sự kiện xấu hơn tới −2,2pp (12/2021); vốn giam trung bình +7pp equity trong ngày ON, đỉnh ~53 %; lỡ crash-buy chỉ ở LUNA (~−0,7k/seed). Đuôi: sập kéo dài > 3 tuần (06/2024) là kịch bản thua duy nhất quan sát được; nhạy ngưỡng cao (45 % ngày ON sát −30 %).
4. Không có gì trong phân tích này đổi kết luận GO/CONFIRM đã chốt; đây là mô tả, không phải kiểm định mới.

## Bất thường / giới hạn
- HO px168 dùng proxy close (không có open 2026 trên Oracle) — Δ HO từng cụm sai số ~0,1 %.
- PnL@168h dùng funding chia tỉ lệ thời gian (xấp xỉ); giả định size ∝ số dư trong tách "sizing" là ước tính, phần dư hấp thụ sai số.
- Nhãn sự kiện là gợi ý theo ngày, chưa kiểm nguồn; 2026 không xác minh.
- "Δ đoạn" và LOO là phân rã mô tả trên 1 đường đi; không phải phản thực (không chạy lại sim bỏ đợt).
