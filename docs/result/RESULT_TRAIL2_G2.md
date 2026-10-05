# RESULT — TRAIL2_G2 (trailing vòng 2: tách tỉ lệ vs phẳng, chọn luật đơn)

Pre-reg: `docs/prereg/PREREG_TRAIL2_G2.md` (md5 `9f791a25c0d764d9cb78a5a3b4665002`, commit `3969bc84`, chốt TRƯỚC khi có số).
Nền G2 arm 7% (gate GDV2 ratio W90, phí base). Chỉ đổi 3 key: `TS_GIVEBACK_RATIO`, `SIM_TS_MAX_GAP`, `SIM_TS_MAX_GAP_WEAK` (Configs.java dòng 894-895 đọc qua Cfg.get). Jar tái dùng `sim-jar-gdv2` (7368be46…, xác nhận trong result.json cả 5 arm), sim Kaggle, 0 build, 0 sim Oracle. DEV ≤ 2025-12-30; không đụng 242/shadow/2026.
Runner `research/analysis/trail2_g2_run.py` · chấm `research/analysis/trail2_g2_driver.py` (cùng hàm bootstrap/T1 như vòng 1) · thô `docs/result/trail2_g2.json`.

## Kết luận (theo luật pre-reg §3)

**Cổng T0: PASS.** Chạy lại với 3 key khai tường minh (0.5 / 0.08 / 0.03): md5 `853aaa08…` byte-identical G2, n 2509, eq 131 374.
Cả 5 arm PASS T1 §9. Mọi CI95 ΔCalmar_MTM (block-72h inflate 1.665 và episode-cluster) chứa 0 ⇒ theo luật: **không pure form nào tệ hơn G2 có ý nghĩa; đề xuất luật ĐƠN GIẢN NHẤT không kém điểm = FLAT3** (pure phẳng, gap = 3% khi lãi > 3%, bỏ min() + weak/strong; 1 tham số). Lý do chọn: Calmar_MTM điểm cao nhất trong nhóm pure (1.940 vs PROP30 1.895 / FLAT5 1.869 / PROP50 1.837) và cũng cao hơn T0 (1.900) nhẹ; nhóm FLAT có 1 tham số.

**Đọc đúng mức (rủi ro):** đây là "không có bằng chứng kém hơn", KHÔNG phải chứng minh tương đương. FLAT3 hơn T0 +0.04 Calmar_MTM (+2.1%), CAGR +0.12pp, ΣPnL ~~+469~~ **+534** USDT [sửa 2026-10-03, nguồn: `REAUDIT_FLAT3_20261003` 69b3cf07 — artifact: 96 909 − 96 375 = Δequity] — nằm gọn trong nhiễu. CI rất rộng (xem dưới) nên không loại được mức kém hơn vài điểm Calmar. Lợi ích có thể tin hơn là ĐƠN GIẢN HOÁ (bỏ 3 tham số + phân nhánh pNoPump) chứ không phải hiệu năng.

## Rủi ro / giới hạn

1. Phương pháp bootstrap giữ y hệt vòng 1 (đã nêu ở RESULT_TRAIL_G2): PRIMARY paired block-72h (lưới `blk2`, NREP 2000, seed 20260905, Calmar trên equity đóng, inflate 1.665); SENSITIVITY `boot_pair` episode-cluster NREP 2000 seed 20260905. Điểm ΔCalmar_MTM dùng Calmar_MTM = CAGR/|maxDD MTM-phút| (khác thang với Calmar trong bootstrap). Bản block-72h có CI ±25…±55 (tỉ số Calmar không ổn định); bản episode ±3…±5.5 — cả hai chứa 0 mọi arm.
2. **Pre-reg nói 355 pre-arm loser "GIỐNG HỆT mọi arm" — thực tế không hoàn toàn:** 355 (T0) / 359 / 361 / 360 / 359 (PROP50/PROP30/FLAT3/FLAT5). Trailing không đổi entry nhưng đổi ngân sách vốn/thời điểm giải phóng vị thế nên tập lệnh xê dịch nhẹ (n từ 2488 đến 2517, |Δn| ≤ 0.84% < 5%). Vì vậy so sánh vẫn gần "sạch" nhưng không tuyệt đối; nhóm loser lỗ TB −14.0…−14.6%, ΣPnL nhóm −53.7k…−56.7k.
3. Chỉ số "% lãi giữ lại so đỉnh" (pre-reg §4) KHÔNG đo được: printDone không có cột peak-profit. Cần chạy lại với `SIM_TRAIL_TRACE` (ghi `trailTrace.csv`) nếu MASTER muốn — chưa làm (ngoài phạm vi pre-reg về key). Thay bằng phân phối profit lúc thoát của 2154 lệnh armed.
4. `max` armed là 1 lệnh đơn lẻ (PROP50 295%, PROP30 176%, FLAT3 207%, FLAT5 205%, T0 207%) — rất nhiễu, không dùng làm bằng chứng; p95 đáng tin hơn.
5. UW 87 ngày (FLAT3, PROP30) vs 129 (T0) vs 138–139 (PROP50/FLAT5): quan sát mô tả, không kiểm định, không phải tiêu chí. Thêm một lần test trên cùng DEV; không tune sau khi thấy số.

## Bảng 5 arm

| arm | ratio / cap / cap_weak | n (Δ vs T0) | equity | CAGR % | maxDD MTM-phút % | UW (ngày) | quý xấu nhất ROI % | Calmar_MTM | T1 | ΔCalmar_MTM | CI95 block72 (infl) | CI95 episode (sens.) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T0 (=G2) | 0.5 / 0.08 / 0.03 | 2509 | 131 374 | 34.18 | −17.99 | 129 | −0.47 | 1.900 | PASS | — | — | — | baseline (parity PASS) |
| PROP50 | 0.5 / 1.0 / 1.0 | 2488 (−0.8%) | 131 839 | 34.29 | −18.66 | 138 | −1.35 | 1.837 | PASS | −0.06 | [−26.4, +23.6] chứa 0 | [−5.4, +4.1] chứa 0 | ≈ G2 |
| PROP30 | 0.3 / 1.0 / 1.0 | 2503 (−0.2%) | 127 524 | 33.30 | −17.57 | 87 | −1.34 | 1.895 | PASS | −0.01 | [−53.9, +33.6] chứa 0 | [−5.0, +5.1] chứa 0 | ≈ G2 |
| **FLAT3** | 1.0 / 0.03 / 0.03 | 2517 (+0.3%) | 131 908 | 34.31 | −17.68 | 87 | −0.77 | **1.940** | PASS | +0.04 | [−52.8, +39.5] chứa 0 | [−5.0, +4.7] chứa 0 | ≈ G2; **luật đề xuất** |
| FLAT5 | 1.0 / 0.05 / 0.05 | 2491 (−0.7%) | 129 372 | 33.73 | −18.04 | 139 | −1.71 | 1.869 | PASS | −0.03 | [−36.5, +21.8] chứa 0 | [−5.6, +2.9] chứa 0 | ≈ G2 |

Phụ: conc_max 4.0–4.1% mọi arm; 0 năm âm; maxDD MTM-phút theo năm tệ nhất −17.6…−18.7% (2022 mọi arm). CAGR theo năm 2021/22/23/24/25 (%): T0 18.4/10.3/51.7/43.5/32.1 · PROP50 23.5/10.9/46.6/39.2/34.8 · PROP30 18.5/10.7/51.1/41.8/29.7 · FLAT3 18.5/11.1/54.1/43.4/29.5 · FLAT5 17.9/9.3/55.6/41.7/30.2. ΔCAGR CI95 (block72, infl) chứa 0 mọi arm.

## Chẩn đoán mô tả

### Phân phối lệnh armed (STOP_MARKET_DONE, profit % lúc thoát)

| arm | n armed | median | p25 | p75 | p95 | max |
|---|---|---|---|---|---|---|
| T0 | 2154 | 5.5 | 4.0 | 7.5 | 18.5 | 207.0 |
| PROP50 | 2129 | 5.0 | 4.0 | 7.5 | 19.0 | 295.0 |
| PROP30 | 2142 | 6.0 | 5.49 | 7.5 | 14.0 | 176.2 |
| FLAT3 | 2157 | 6.0 | 4.99 | 8.49 | 14.5 | 207.0 |
| FLAT5 | 2132 | 5.5 | 3.5 | 9.48 | 19.0 | 205.0 |

Pre-arm loser (STOP_LOSS_DONE): T0 355 (lỗ TB −14.00%, −53 698 USDT) · PROP50 359 (−14.18%, −56 617) · PROP30 361 (−14.61%, −55 336) · FLAT3 360 (−14.27%, −56 736) · FLAT5 359 (−14.62%, −54 959).

### PROP vs FLAT ở đuôi phải — cơ chế nào giữ runner tốt hơn

- **Đuôi phải (p95) do mức nới quyết định, không do dạng tỉ lệ/phẳng:** nới rộng thì giữ runner (PROP50 gap = 50% đỉnh: p95 19.0; FLAT5 gap 5%: p95 19.0; T0: 18.5), siết chặt thì cắt runner (PROP30: 14.0; FLAT3: 14.5). PROP và FLAT cùng độ chặt cho p95 gần như trùng nhau (PROP30 14.0 ≈ FLAT3 14.5; PROP50 19.0 ≈ FLAT5 19.0). Giữ đuôi tốt nhất là PROP50 (p95 19.0, max 295 nhưng max là 1 lệnh).
- **Thân phân phối khác nhau rõ hơn:** FLAT khoá một cục cố định nên thân phân phối dịch theo mức gap (FLAT3 p25 4.99, p75 8.49; FLAT5 p25 3.5, p75 9.48 — FLAT5 thoát sớm nhiều lệnh ở ~3.5% rồi bù bằng thân phải). PROP siết theo tỉ lệ: PROP30 nâng sàn (p25 5.49) nhưng trần p75 vẫn 7.5.
- **Hiệu quả rủi ro-lợi nhuận:** điểm tốt nhất là FLAT3 (Calmar_MTM 1.940, UW 87) dù p95 thấp hơn T0 4pp: nó bù đuôi bị cắt bằng thân cao hơn (median 6.0 vs 5.5, p25 5.0 vs 4.0). Chênh lệch nhỏ và trong nhiễu.
- Tóm lại: về giữ runner, PROP50 ≈ FLAT5 ≥ T0 > FLAT3 ≈ PROP30; về Calmar/UW điểm, FLAT3 > T0 ≈ PROP30 > FLAT5 > PROP50 — trade-off runner đối lại sàn, không cơ chế nào thắng rõ.

## Bảng quý + năm (qstat_r4.py) — T0 và FLAT3 (pure tốt nhất theo Calmar_MTM điểm)

### T0 (= G2)
TAG trail2-g2-t0 n_total 2509 days 1644 eq_first 20210701 eq_last 20251230 131374.0
| quy | n | sel | BD | DCA | win% | TSloss% | meanP% | mP|SM% | mP|SL% | PnL USDT | funding | margin TB | ROI% | equity cuoi | maxDD% (ngay) | UW (ngay) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021Q3 | 285 | 271 | 14 | 0 | 86.32 | 14.04 | 4.098 | 6.68 | -11.74 | 5212.8 | 33.1 | 490 | 14.46 | 40060 | -5.34 | 17 |
| 2021Q4 | 150 | 132 | 18 | 0 | 80.00 | 20.67 | 1.951 | 6.50 | -15.51 | 1213.0 | -8.2 | 574 | 3.41 | 41425 | -3.17 | 27 |
| 2022Q1 | 64 | 64 | 0 | 0 | 87.50 | 14.06 | 3.599 | 6.16 | -12.05 | 1605.7 | -16.0 | 672 | 3.88 | 43031 | -2.05 | 33 |
| 2022Q2 | 200 | 173 | 8 | 19 | 81.00 | 22.00 | 2.351 | 7.09 | -14.44 | -203.1 | -105.4 | 473 | -0.47 | 42828 | -10.41 | 56 |
| 2022Q3 | 56 | 48 | 8 | 0 | 91.07 | 10.71 | 6.746 | 7.93 | -3.14 | 2806.5 | -16.9 | 722 | 6.55 | 45634 | -0.21 | 28 |
| 2022Q4 | 103 | 92 | 4 | 7 | 72.82 | 25.24 | 1.523 | 8.41 | -18.87 | 40.1 | -555.4 | 487 | 0.09 | 45675 | -9.39 | 53 |
| 2023Q1 | 109 | 103 | 6 | 0 | 89.91 | 13.76 | 4.441 | 6.84 | -10.62 | 3586.4 | 29.8 | 790 | 7.85 | 49261 | -2.08 | 20 |
| 2023Q2 | 122 | 106 | 16 | 0 | 77.87 | 24.59 | 6.288 | 11.33 | -9.17 | 6740.7 | -62.6 | 867 | 12.66 | 55495 | -2.03 | 45 |
| 2023Q3 | 103 | 85 | 18 | 0 | 87.38 | 18.45 | 5.837 | 8.10 | -4.17 | 5508.5 | -266.0 | 960 | 10.84 | 61510 | -0.70 | 24 |
| 2023Q4 | 194 | 185 | 9 | 0 | 87.11 | 13.40 | 4.442 | 6.78 | -10.66 | 7906.8 | -19.0 | 938 | 12.66 | 69298 | -2.42 | 16 |
| 2024Q1 | 183 | 158 | 25 | 0 | 90.16 | 9.84 | 4.603 | 6.84 | -15.87 | 8890.1 | 221.6 | 1146 | 13.00 | 78307 | -1.54 | 34 |
| 2024Q2 | 143 | 116 | 26 | 1 | 81.12 | 19.58 | 1.932 | 6.93 | -18.60 | 1178.8 | -1.1 | 1115 | 1.51 | 79486 | -5.51 | 80 |
| 2024Q3 | 102 | 96 | 6 | 0 | 90.20 | 12.75 | 6.481 | 8.10 | -4.57 | 5994.2 | -27.1 | 1047 | 7.54 | 85480 | -1.26 | 30 |
| 2024Q4 | 164 | 150 | 14 | 0 | 94.51 | 5.49 | 6.558 | 7.64 | -12.11 | 13975.1 | 65.5 | 1401 | 16.35 | 99455 | -0.45 | 17 |
| 2025Q1 | 173 | 165 | 8 | 0 | 93.06 | 6.36 | 5.425 | 7.64 | -27.16 | 14826.3 | -136.1 | 1649 | 14.91 | 114281 | -1.88 | 28 |
| 2025Q2 | 26 | 26 | 0 | 0 | 88.46 | 11.54 | 4.764 | 7.74 | -18.04 | 2544.0 | -286.5 | 2090 | 2.23 | 116825 | -0.72 | 15 |
| 2025Q3 | 53 | 49 | 4 | 0 | 75.47 | 22.64 | -0.059 | 5.98 | -20.69 | -306.6 | 120.3 | 1994 | -0.26 | 116519 | -1.59 | 40 |
| 2025Q4 | 279 | 197 | 64 | 18 | 86.38 | 5.38 | 6.711 | 8.60 | -26.53 | 14855.4 | -299.7 | 1342 | 12.75 | 131374 | -1.31 | 52 |

| nam | n | sel | BD | DCA | win% | TSloss% | meanP% | mP|SM% | mP|SL% | PnL USDT | funding | margin TB | ROI% | equity cuoi | maxDD% (ngay) | UW (ngay) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 435 | 403 | 32 | 0 | 84.14 | 16.32 | 3.358 | 6.62 | -13.39 | 6425.8 | 24.9 | 519 | 18.36 | 41425 | -5.34 | 33 |
| 2022 | 423 | 377 | 20 | 26 | 81.32 | 20.09 | 2.920 | 7.36 | -14.74 | 4249.2 | -693.6 | 539 | 10.26 | 45675 | -10.55 | 137 |
| 2023 | 528 | 479 | 49 | 0 | 85.61 | 17.05 | 5.140 | 8.00 | -8.79 | 23742.4 | -317.7 | 895 | 51.72 | 69298 | -2.42 | 45 |
| 2024 | 592 | 520 | 71 | 1 | 89.19 | 11.49 | 4.823 | 7.31 | -14.34 | 30038.2 | 259.0 | 1192 | 43.52 | 99455 | -5.51 | 86 |
| 2025 | 531 | 437 | 76 | 18 | 87.57 | 7.72 | 5.521 | 8.02 | -24.37 | 31919.2 | -602.1 | 1544 | 32.09 | 131374 | -1.88 | 60 |

TOTAL n=2509 win=85.89 TSloss=14.15 meanP=4.463 PnL=96374.8 equity=131374 maxDD_day=-10.55 UW=137 negQ=2

### FLAT3
TAG trail2-g2-flat3 n_total 2517 days 1644 eq_first 20210701 eq_last 20251230 131908.0
| quy | n | sel | BD | DCA | win% | TSloss% | meanP% | mP|SM% | mP|SL% | PnL USDT | funding | margin TB | ROI% | equity cuoi | maxDD% (ngay) | UW (ngay) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021Q3 | 283 | 269 | 14 | 0 | 85.87 | 14.49 | 4.101 | 6.84 | -12.07 | 5019.3 | 27.1 | 490 | 13.91 | 39868 | -5.27 | 17 |
| 2021Q4 | 151 | 133 | 18 | 0 | 80.13 | 20.53 | 2.238 | 6.83 | -15.55 | 1467.2 | -5.6 | 574 | 4.06 | 41486 | -3.05 | 27 |
| 2022Q1 | 63 | 63 | 0 | 0 | 85.71 | 15.87 | 4.116 | 7.25 | -12.50 | 1838.8 | -21.1 | 675 | 4.43 | 43325 | -2.16 | 33 |
| 2022Q2 | 200 | 173 | 8 | 19 | 81.00 | 22.00 | 2.258 | 6.99 | -14.51 | -333.9 | -104.5 | 469 | -0.77 | 42991 | -10.02 | 56 |
| 2022Q3 | 56 | 48 | 8 | 0 | 91.07 | 10.71 | 7.004 | 8.22 | -3.14 | 2907.7 | -16.7 | 725 | 6.76 | 45899 | -0.12 | 19 |
| 2022Q4 | 104 | 93 | 4 | 7 | 73.08 | 25.00 | 1.955 | 8.89 | -18.86 | 196.3 | -548.6 | 490 | 0.43 | 46095 | -9.37 | 10 |
| 2023Q1 | 109 | 103 | 6 | 0 | 89.91 | 13.76 | 4.707 | 7.15 | -10.62 | 3868.4 | 30.9 | 800 | 8.39 | 49963 | -2.12 | 20 |
| 2023Q2 | 121 | 105 | 16 | 0 | 77.69 | 24.79 | 6.807 | 12.08 | -9.17 | 7366.3 | -61.8 | 886 | 13.42 | 56666 | -2.00 | 45 |
| 2023Q3 | 103 | 85 | 18 | 0 | 87.38 | 18.45 | 5.414 | 7.58 | -4.17 | 5392.7 | -254.1 | 983 | 10.69 | 62722 | -0.68 | 24 |
| 2023Q4 | 193 | 184 | 9 | 0 | 87.05 | 13.47 | 4.599 | 7.04 | -11.09 | 8449.4 | -24.3 | 966 | 13.28 | 71051 | -2.24 | 16 |
| 2024Q1 | 189 | 164 | 25 | 0 | 90.48 | 9.52 | 4.909 | 7.10 | -15.87 | 10337.8 | 217.6 | 1188 | 14.72 | 81509 | -1.48 | 34 |
| 2024Q2 | 143 | 116 | 26 | 1 | 81.12 | 19.58 | 2.057 | 7.09 | -18.60 | 1081.1 | -3.8 | 1163 | 1.33 | 82591 | -5.39 | 80 |
| 2024Q3 | 102 | 96 | 6 | 0 | 90.20 | 12.75 | 5.756 | 7.26 | -4.57 | 5819.0 | -24.8 | 1085 | 7.05 | 88410 | -1.01 | 26 |
| 2024Q4 | 166 | 152 | 14 | 0 | 94.58 | 5.42 | 5.935 | 6.97 | -12.11 | 13445.1 | 73.2 | 1441 | 15.21 | 101855 | -0.22 | 17 |
| 2025Q1 | 174 | 166 | 8 | 0 | 93.10 | 6.32 | 4.908 | 7.07 | -27.16 | 13782.2 | -143.3 | 1693 | 13.53 | 115637 | -1.87 | 28 |
| 2025Q2 | 25 | 25 | 0 | 0 | 88.00 | 12.00 | 5.337 | 8.52 | -18.04 | 2880.6 | -291.6 | 2122 | 2.49 | 118517 | -0.57 | 15 |
| 2025Q3 | 53 | 49 | 4 | 0 | 75.47 | 22.64 | -0.072 | 5.96 | -20.69 | -279.7 | 120.7 | 2020 | -0.24 | 118238 | -1.30 | 40 |
| 2025Q4 | 282 | 199 | 64 | 19 | 85.46 | 6.38 | 6.749 | 9.14 | -28.27 | 13670.6 | -390.0 | 1341 | 11.56 | 131908 | -1.54 | 52 |

| nam | n | sel | BD | DCA | win% | TSloss% | meanP% | mP|SM% | mP|SL% | PnL USDT | funding | margin TB | ROI% | equity cuoi | maxDD% (ngay) | UW (ngay) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 434 | 402 | 32 | 0 | 83.87 | 16.59 | 3.453 | 6.84 | -13.57 | 6486.5 | 21.5 | 519 | 18.53 | 41486 | -5.27 | 33 |
| 2022 | 423 | 377 | 20 | 26 | 81.09 | 20.33 | 3.089 | 7.65 | -14.80 | 4608.9 | -690.8 | 539 | 11.11 | 46095 | -10.02 | 69 |
| 2023 | 526 | 477 | 49 | 0 | 85.55 | 17.11 | 5.289 | 8.22 | -8.91 | 25076.7 | -309.3 | 917 | 54.14 | 71051 | -2.24 | 45 |
| 2024 | 600 | 528 | 71 | 1 | 89.33 | 11.33 | 4.657 | 7.09 | -14.34 | 30682.9 | 262.2 | 1235 | 43.35 | 101855 | -5.39 | 86 |
| 2025 | 534 | 439 | 76 | 19 | 87.08 | 8.24 | 5.406 | 8.16 | -25.23 | 30053.8 | -704.1 | 1560 | 29.51 | 131908 | -1.87 | 60 |

TOTAL n=2517 win=85.74 TSloss=14.30 meanP=4.477 PnL=96908.9 equity=131908 maxDD_day=-10.02 UW=86 negQ=2

(Các arm khác: `~/claude_master/0929/qstat2_{prop50,prop30,flat5}.txt`; diag đầy đủ `diag2_*.txt` trên Oracle.)

## Artifact để audit

Kaggle kernels `chuyendinh/sim-trail2-g2-{t0,prop50,prop30,flat3,flat5}` (secs 1084/1184/2639/1641/2099); output `~/kaggle_sim/out/trail2-g2-*` (printDone md5: t0 `853aaa08…`, prop50 `0f685f7f…`, prop30 `3fd38fb9…`, flat3 `650c386f…`, flat5 `e252d50c…`); log chấm `~/claude_master/0929/trail2_g2_score.log`; cache MTM `/tmp/trail2_g2_mtm.json`.
