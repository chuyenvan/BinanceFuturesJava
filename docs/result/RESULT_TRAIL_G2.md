# RESULT — TRAIL_G2 (sweep trailing trên nền G2)

Pre-reg: `docs/prereg/PREREG_TRAIL_G2.md` (md5 `5fc4c48555cb8a680d201c1f6f1548a5`, commit `4659b457`, chốt TRƯỚC khi có số).
Nền = G2 (GDV2 ratio W90, nhịp 1', phí base). Chỉ đổi khối exit. Jar tái dùng `sim-jar-gdv2` (sha256 `7368be46…`, xác nhận trong result.json cả 5 arm). Sim trên Kaggle, 0 sim Oracle, 0 build. DEV ≤ 2025-12-30; không đụng 242/shadow-c3/2026.
Runner: `research/analysis/trail_g2_run.py` · Chấm: `research/analysis/trail_g2_driver.py` · Số liệu thô: `docs/result/trail_g2.json`.

## Kết luận (theo luật pre-reg §5)

**Không arm nào thắng G2. Trailing hiện tại KHÔNG tệ rõ rệt trên DEV; khác biệt trong nhiễu.**
- Cổng parity T0 = G2: PASS (md5 `853aaa08…` byte-identical, n 2509, eq 131 374).
- Cả 5 arm PASS Tầng 1 rủi ro §9 (maxDD MTM-phút ≤ 40%/năm, UW ≤ 250, quý xấu ≥ −20%, 0 năm âm, conc ≤ 15%) — T1 không phân biệt được arm nào; biên rất rộng (maxDD ~−17%, conc ~4%).
- Không arm nào có CI95 ΔCalmar_MTM (inflate k=4 = 1.665) loại được 0. LAD/GV3 cao hơn T0 về điểm (Calmar_MTM 1.949/1.907 vs 1.900, tức +2.6%/+0.4%) nhưng nằm hoàn toàn trong nhiễu. A5 và A5LAD kém hơn T0 về điểm (CAGR −5.2pp / −4.4pp, Σ PnL ≈ −21.6k / −18.3k USDT).

## Rủi ro / giới hạn của lần chạy này (đọc trước)

1. **Phương pháp bootstrap ΔCalmar là diễn giải của tôi, chưa có hàm sẵn.** Không script nào trong repo bootstrap ΔCalmar_MTM theo block-72h: `ci_pair` (reset_rule_score) chỉ làm RATE_KEYS; `boot_pair` (GDV2_P3) làm ΔCalmar nhưng theo episode-cluster, 5000 rep, seed 20260928. Tôi làm: (PRIMARY) paired block-72h trên lưới khối chung `blk2` của reset_rule_score (khối theo ts vào lệnh, cộng PnL đóng theo khối), NREP 2000, seed 20260905, Calmar/CAGR/maxDD tính trên equity đóng theo thứ tự khối rút (đúng công thức `boot_pair`), percentile 2.5/97.5 rồi inflate quanh tâm ×1.6651; (SENSITIVITY) gọi nguyên `boot_pair` của reset_rule_gdv2_p3 với NREP 2000 + seed 20260905. Điểm ΔCalmar_MTM quan sát dùng Calmar_MTM = CAGR/|maxDD MTM-phút| (run_mtm), khác thang với Calmar trong bootstrap (equity đóng). MASTER cần audit/đồng ý cách đọc này.
2. **CI block-72h rất rộng (±60…±100 điểm Calmar)** vì maxDD của path resample có thứ tự ngẫu nhiên nhỏ và không ổn định làm tỉ số nổ. Bản episode-cluster hẹp hơn nhiều (±5…±18) nhưng cũng chứa 0 cho cả 4 arm ⇒ kết luận không phụ thuộc vào biến thể bootstrap. Bootstrap trung bình ΔCalmar cũng không cùng dấu với điểm quan sát ở vài arm (ví dụ A5LAD block72 mean +2.36 vs điểm −0.12) — thêm bằng chứng đây là nhiễu, không tín hiệu.
3. n xê dịch nhẹ qua ngân sách vốn (không đổi entry): max |Δn| = +2.95% (A5LAD) < ngưỡng 5% ⇒ không cần cờ cảnh báo §1.
4. Đây là thêm một lần test trên cùng DEV (GDV2_P3 đã đếm ~27 lần trước đó); k=4 inflate đã tính. Không tune thêm sau khi thấy số.
5. UW cải thiện điểm ở GV3 (87 vs 129 ngày) và LAD (101) là quan sát mô tả, KHÔNG có kiểm định, không phải tiêu chí thắng.
6. Cột profit trong `traildiag.py` là % (5.5 = +5.5%); histogram bucket cuối của traildiag dùng thang phân số nên sai nhãn — bỏ qua histogram đó, các số med/p25/p75/p95 đúng.

## Bảng 5 arm

| arm | cấu hình exit | n (Δ vs T0) | equity | CAGR % | maxDD MTM-phút % | UW (ngày) | quý xấu nhất ROI % | Calmar_MTM | T1 | ΔCalmar_MTM (điểm) | CI95 block72 (inflate) | CI95 episode (sens.) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T0 (=G2) | arm 7%, GB 0.5 | 2509 | 131 374 | 34.18 | −17.99 | 129 | −0.47 | 1.900 | PASS | — | — | — | baseline (parity PASS) |
| A5 | arm 5%, GB 0.5 | 2564 (+2.2%) | 109 825 | 28.95 | −17.18 | 129 | −2.64 | 1.685 | PASS | −0.22 | [−99.1, +77.4] chứa 0 | [−12.0, +18.3] chứa 0 | ≈ G2 (điểm kém hơn) |
| GV3 | arm 7%, GB 0.3 | 2501 (−0.3%) | 127 836 | 33.37 | −17.50 | 87 | −1.25 | 1.907 | PASS | +0.01 | [−57.9, +33.1] chứa 0 | [−5.5, +4.3] chứa 0 | ≈ G2 |
| LAD | arm 7%, ladder LO .05/.10/.20 GAPS .02/.04/.08 | 2494 (−0.6%) | 130 177 | 33.91 | −17.40 | 101 | −0.40 | 1.949 | PASS | +0.05 | [−60.8, +60.5] chứa 0 | [−7.2, +11.4] chứa 0 | ≈ G2 |
| A5LAD | arm 5% + ladder | 2583 (+2.9%) | 113 074 | 29.78 | −16.74 | 106 | −2.19 | 1.779 | PASS | −0.12 | [−83.2, +126.2] chứa 0 | [−11.5, +18.4] chứa 0 | ≈ G2 (điểm kém hơn) |

Phụ: conc_max 4.1–4.2% mọi arm; 0 năm âm mọi arm; maxDD MTM-phút theo năm tệ nhất −16.7…−18.0% (cả 5 arm đều rơi vào năm 2022; chi tiết JSON `mtm_dd_year`); ΔCAGR CI95 (block72, inflate) chứa 0 cho cả 4 arm (GV3 [−31.9,+11.0]; LAD [−29.8,+22.0]; A5 [−124.8,+5.1]; A5LAD [−117.3,+14.7]). CAGR theo năm 2021/22/23/24/25 (%): T0 18.4/10.3/51.7/43.5/32.1 · A5 14.9/7.1/43.4/36.3/30.5 · GV3 18.3/10.4/53.8/41.0/28.9 · LAD 19.0/11.5/51.8/40.9/30.9 · A5LAD 16.3/8.9/43.6/35.5/31.1.

## Chẩn đoán mô tả (giá trị chính)

### Pre-arm loser (STOP_LOSS_DONE — chết trước khi arm)

| arm | số lệnh | % n | lỗ TB / lệnh (%) | Σ PnL nhóm (USDT) |
|---|---|---|---|---|
| T0 | 355 | 14.1% | −14.00 | −53 698 |
| A5 | 218 | 8.5% | −16.39 | −31 898 |
| GV3 | 361 | 14.4% | −14.61 | −55 627 |
| LAD | 356 | 14.3% | −14.08 | −54 071 |
| A5LAD | 218 | 8.4% | −16.09 | −31 474 |

**Arm 5% có cứu pre-arm loser: CÓ về số lượng (355 → 218, −137 lệnh; TSloss 14.1% → 8.5%; nhóm loser lỗ ít hơn ~21.8k USDT), nhưng KHÔNG có lợi ròng.** Lệnh được cứu chuyển thành winner nhỏ (armed thoát ở sàn ~3%), đồng thời kéo mọi winner armed xuống thấp hơn: median armed 5.5% → 3.5%, mP|SM 7.5% → 5.5%. Loser còn lại là nhóm xấu hơn (lỗ TB −16.4% vs −14.0%). Ròng: Σ PnL −21.6k, CAGR −5.2pp, Calmar_MTM −0.22. H1 (arm sớm cứu loser) đúng về cơ chế nhưng chi phí (thoát sớm winner) lớn hơn lợi ⇒ không ủng hộ. GV3/LAD gần như không đổi nhóm loser (như dự kiến, không đổi arm).

### Phân phối lệnh armed (STOP_MARKET_DONE, profit %)

| arm | n armed | median | p25 | p75 | p95 | max | min |
|---|---|---|---|---|---|---|---|
| T0 | 2154 | 5.5 | 4.0 | 7.5 | 18.5 | 207.0 | −58.6 |
| A5 | 2346 | 3.5 | 3.0 | 5.5 | 15.0 | 207.0 | −58.6 |
| GV3 | 2140 | 6.0 | 5.49 | 7.5 | 14.0 | 207.0 | −58.6 |
| LAD | 2138 | 6.5 | 5.5 | 7.5 | 13.0 | 204.5 | −58.6 |
| A5LAD | 2365 | 4.5 | 3.5 | 6.0 | 9.5 | 204.5 | −58.6 |

Đọc: GV3/LAD nâng sàn và median (+0.5/+1.0pp) và cắt đuôi phải (p95 18.5 → 14/13) — khoá chặt vùng thấp nhưng trả lại đúng phần đuôi mà T0 giữ; ròng ≈ 0 (H2 không được ủng hộ trên DEV). Cường độ đuôi cực trị (max ~207%) vẫn được giữ ở mọi arm. (min −58.6% trong nhóm STOP_MARKET giống hệt ở mọi arm; chưa điều tra nguyên nhân.) Số lệnh/n thay đổi được ghi ở bảng chính.

## Bảng quý + năm (qstat_r4.py) — T0 và arm điểm tốt nhất (LAD, Calmar_MTM cao nhất nhưng KHÔNG thắng theo luật)

### T0 (= G2)
TAG trail-g2-t0 n_total 2509 days 1644 eq_first 20210701 eq_last 20251230 131374.0
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

### LAD
TAG trail-g2-lad n_total 2494 days 1644 eq_first 20210701 eq_last 20251230 130177.0
| quy | n | sel | BD | DCA | win% | TSloss% | meanP% | mP|SM% | mP|SL% | PnL USDT | funding | margin TB | ROI% | equity cuoi | maxDD% (ngay) | UW (ngay) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021Q3 | 283 | 269 | 14 | 0 | 85.87 | 14.49 | 4.214 | 6.97 | -12.07 | 5137.7 | 24.5 | 491 | 14.24 | 39985 | -5.27 | 17 |
| 2021Q4 | 151 | 133 | 18 | 0 | 80.13 | 20.53 | 2.244 | 6.84 | -15.56 | 1519.2 | -6.0 | 577 | 4.18 | 41656 | -3.04 | 27 |
| 2022Q1 | 63 | 63 | 0 | 0 | 85.71 | 15.87 | 3.644 | 6.69 | -12.50 | 1638.9 | -21.2 | 678 | 3.93 | 43295 | -2.07 | 33 |
| 2022Q2 | 202 | 175 | 8 | 19 | 81.19 | 21.78 | 2.366 | 7.07 | -14.51 | -174.5 | -105.4 | 470 | -0.40 | 43121 | -9.74 | 54 |
| 2022Q3 | 55 | 47 | 8 | 0 | 90.91 | 10.91 | 7.392 | 8.68 | -3.14 | 3008.4 | -16.0 | 726 | 6.98 | 46129 | -0.12 | 18 |
| 2022Q4 | 104 | 93 | 4 | 7 | 73.08 | 25.00 | 1.933 | 8.86 | -18.86 | 327.6 | -549.9 | 492 | 0.71 | 46457 | -9.62 | 8 |
| 2023Q1 | 109 | 103 | 6 | 0 | 89.91 | 13.76 | 4.714 | 7.16 | -10.62 | 3915.6 | 30.7 | 807 | 8.43 | 50372 | -2.15 | 19 |
| 2023Q2 | 128 | 111 | 17 | 0 | 78.91 | 23.44 | 6.636 | 11.48 | -9.17 | 7536.3 | -55.0 | 885 | 13.32 | 57084 | -1.98 | 45 |
| 2023Q3 | 98 | 81 | 17 | 0 | 86.73 | 19.39 | 4.762 | 6.91 | -4.17 | 4581.8 | -255.8 | 989 | 9.47 | 62490 | -0.66 | 24 |
| 2023Q4 | 195 | 186 | 9 | 0 | 87.18 | 13.33 | 4.532 | 6.93 | -11.06 | 8168.2 | -27.5 | 951 | 12.88 | 70538 | -2.22 | 16 |
| 2024Q1 | 177 | 152 | 25 | 0 | 90.40 | 9.60 | 4.944 | 7.09 | -15.26 | 9678.7 | 198.6 | 1179 | 13.89 | 80337 | -1.32 | 34 |
| 2024Q2 | 133 | 106 | 26 | 1 | 80.45 | 20.30 | 1.741 | 6.90 | -18.52 | 389.3 | -13.7 | 1139 | 0.49 | 80727 | -5.45 | 80 |
| 2024Q3 | 101 | 95 | 6 | 0 | 90.10 | 12.87 | 5.610 | 7.11 | -4.57 | 5502.5 | -25.4 | 1068 | 6.82 | 86229 | -1.05 | 30 |
| 2024Q4 | 166 | 152 | 14 | 0 | 94.58 | 5.42 | 5.905 | 6.94 | -12.11 | 13184.9 | 67.2 | 1410 | 15.29 | 99414 | -0.19 | 17 |
| 2025Q1 | 172 | 164 | 8 | 0 | 93.02 | 6.40 | 5.022 | 7.22 | -27.16 | 13467.9 | -135.0 | 1644 | 13.55 | 112882 | -1.83 | 25 |
| 2025Q2 | 23 | 23 | 0 | 0 | 91.30 | 8.70 | 6.115 | 8.08 | -14.51 | 2698.9 | -91.6 | 2074 | 2.39 | 115581 | -0.57 | 4 |
| 2025Q3 | 52 | 48 | 4 | 0 | 76.92 | 21.15 | 1.066 | 6.19 | -18.03 | 1238.0 | 115.2 | 1973 | 1.07 | 116819 | -0.98 | 21 |
| 2025Q4 | 282 | 199 | 64 | 19 | 85.82 | 6.38 | 6.750 | 9.13 | -28.18 | 13358.3 | -356.4 | 1330 | 11.43 | 130177 | -1.53 | 52 |

| nam | n | sel | BD | DCA | win% | TSloss% | meanP% | mP|SM% | mP|SL% | PnL USDT | funding | margin TB | ROI% | equity cuoi | maxDD% (ngay) | UW (ngay) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 434 | 402 | 32 | 0 | 83.87 | 16.59 | 3.529 | 6.93 | -13.58 | 6656.9 | 18.5 | 521 | 19.02 | 41656 | -5.27 | 33 |
| 2022 | 424 | 378 | 20 | 26 | 81.13 | 20.28 | 3.102 | 7.66 | -14.80 | 4800.3 | -692.6 | 539 | 11.53 | 46457 | -9.74 | 67 |
| 2023 | 530 | 481 | 49 | 0 | 85.66 | 16.98 | 5.120 | 7.99 | -8.90 | 24201.9 | -307.7 | 913 | 51.84 | 70538 | -2.22 | 45 |
| 2024 | 577 | 505 | 71 | 1 | 89.25 | 11.44 | 4.599 | 7.01 | -14.06 | 28755.5 | 226.7 | 1217 | 40.94 | 99414 | -5.45 | 86 |
| 2025 | 529 | 434 | 76 | 19 | 87.52 | 7.94 | 5.602 | 8.21 | -24.60 | 30763.0 | -467.8 | 1527 | 30.94 | 130177 | -1.83 | 52 |

TOTAL n=2494 win=85.81 TSloss=14.27 meanP=4.482 PnL=95177.5 equity=130177 maxDD_day=-9.74 UW=86 negQ=1

(Bảng quý/năm của A5, GV3, A5LAD: `~/kaggle_sim/out/trail-g2-*` + `~/claude_master/0929/qstat_{a5,gv3,a5lad}.txt` trên Oracle; diag đầy đủ `diag_*.txt`.)

## Artifact để audit

Kaggle kernels `chuyendinh/sim-trail-g2-{t0,a5,gv3,lad,a5lad}`; output `~/kaggle_sim/out/trail-g2-*` (printDone md5: t0 `853aaa08…`, a5 `655dd46b…`, gv3 `c2b4691e…`, lad `adfebe0c…`, a5lad `e4083e29…`); log chấm `~/claude_master/0929/trail_g2_score.log`; cache MTM `/tmp/trail_g2_mtm.json`.
