# Độ phủ lệnh & lợi nhuận/rủi ro: M2 vs baseline (DEV 2022–2025)

2026-10-09. Phân tích khách quan, KHÔNG luật, KHÔNG vòng GO. Script `research/analysis/coverage_m2_base.py`, JSON `docs/audit/COVERAGE_M2_BASE_20261009.json`. Chỉ run DEV có sẵn (sim_end 2025-12-31); KHÔNG mở `ho26-*`; 0 sim / 0 Kaggle / 0 Java / 0 chạm 242.

- Baseline = K24 + skipFull (`nsel-nen-s*`, 8 seed); M2 = K24 + skipFull + NSEL M2 (`nsel-m2-s*`, 8 seed); bản stress in-sim 1,675% là chính. Phụ phí gốc: `gqsf-*` / `nsel-m2b-*`.
- Số = mean [min..max] qua seed 42, 7, 13, 21, 99, 123, 777, 2024.

## Định nghĩa / phương pháp

- Nguồn: printDone.csv + result.json của run + nến 1m ticker (`/home/ubuntu/kaggle_data_hpo`, jbin). Không đọc `ho26-*`.
- Equity MTM phút = thước `nsel_score_b`: pnl realized ghi tại phút `end` + unrealized q·(close1m − entry), q = margin/entry; cửa sổ 2022-01-01 00:00 → 2025-12-31 23:59 (+07); CAGR22 = (E_cuối/E_đầu)^(1/4) − 1 (1461 ngày / 365,25).
- Return ngày = equity MTM 23:59 +07 / ngày trước − 1; Sharpe = mean/sd·√365, Sortino = mean/√mean(min(r,0)²)·√365, rf = 0; vol = sd·√365; skew/kurtosis dư (scipy) trên 1461 return ngày.
- Tuần = tuần ISO đủ 7 ngày (+07) 2022-01-03 → 2025-12-28 (208 tuần), năm của tuần = năm của thứ Hai; tháng = 48 tháng dương lịch. Tuần 'bằng 0' = |ΔE tuần| < 1e-6·E0 (không có vị thế cả tuần).
- maxDD = equity MTM phút, đỉnh reset đầu cửa sổ; UW dài nhất = chuỗi phút equity < đỉnh trước dài nhất (ngày); hồi DD lớn nhất = từ đáy (và từ đỉnh) tới phút đầu tiên equity ≥ đỉnh trước DD.
- Lệnh vào = dòng printDone có start trong cửa sổ (mọi loại chân); leg0 = chân đầu cụm (sym, end) (= nsel_p0_data.load).
- Có vị thế = ≥ 1 chân mở (start ≤ phút < end). Vị thế đồng thời = số cụm (sym, end) đang mở. U = Σ notional chân mở (quantity·entry, 1x) / equity MTM phút.
- Khoảng trống = chuỗi ngày (+07) liên tiếp không có lệnh vào (mọi chân). Đợt = cụm ngày có lệnh, tách khi ≥ 3 ngày liền không lệnh vào; PnL đợt = Σ pnl realized của lệnh vào trong đợt; % top-3 đợt chia cho Σ pnl lệnh vào trong cửa sổ.
- Tập trung ngày: % của ΣΔequity MTM ngày (net cả cửa sổ) đến từ top-k ngày; Gini trên max(ΔE ngày, 0) qua 1461 ngày.
- Đặc tính lệnh = dòng printDone có end trong cửa sổ (mọi chân); % = pnl/margin; expectancy = mean pnl/margin; time-stop = giữ ≥ 168h; lỗ đơn lệnh % vốn = pnl / equity MTM phút trước lúc vào; MAE = min(low 1m, phút s+1..e−1)/entry − 1 (entry stress đã gồm phạt), chỉ lệnh vào và đóng trong cửa sổ.
- Benchmark: close 1m BTCUSDT/ETHUSDT cùng nguồn ticker, ffill; 50/50 = 50% BTC + 50% tiền mặt, rebalance 00:00 +07 ngày 1 mỗi tháng; không phí, không funding.
- Tương quan = Pearson return ngày (+07) strategy vs BTC, toàn kỳ và chỉ các ngày BTC < −5%.
- Stress = phạt giá vào 1,675% khi nến 1m quyết định ≤ −1% (in-sim, nsel-nen/nsel-m2); phí gốc = phạt 0 (gqsf / nsel-m2b).
- Số trình bày = mean [min..max] qua seed. Không bootstrap, không inflate, không luật; đây là mô tả, không phải đo lever.

## 1. Lợi nhuận / rủi ro (stress; cửa sổ 2022-01-01 → 2025-12-31 +07)

| chỉ số | Baseline | M2 | BTC B&H | ETH B&H | 50% BTC + 50% cash |
|---|---|---|---|---|---|
| CAGR22 % | 27,63 [25,67..29,72] | 30,63 [29,19..33,02] | 16,53 | -5,62 | 12,19 |
| maxDD MTM phút % | -22,86 [-24,69..-21,59] | -27,99 [-28,88..-27,28] | -67,80 | -77,27 | -39,85 |
| Calmar | 1,212 [1,060..1,377] | 1,095 [1,027..1,210] | 0,244 | -0,073 | 0,306 |
| Sharpe ngày (×√365) | 1,80 [1,69..1,90] | 1,49 [1,41..1,60] | 0,56 | 0,25 | 0,59 |
| Sortino ngày (×√365) | 2,90 [2,62..3,15] | 2,16 [2,02..2,34] | 0,82 | 0,35 | 0,88 |
| Vol năm hoá % | 14,1 [13,7..14,4] | 19,2 [18,7..19,6] | 49,4 | 66,2 | 24,5 |
| Ngày tệ nhất % | -10,02 [-10,96..-8,76] | -12,93 [-13,46..-12,04] | -16,18 | -24,07 | -8,09 |
| Tuần ISO tệ nhất % | -10,85 [-13,28..-8,65] | -12,19 [-12,70..-11,51] | -30,11 | -30,12 | -14,00 |
| Tháng tệ nhất % | -11,06 [-13,28..-5,57] | -9,73 [-10,73..-8,52] | -40,50 | -47,60 | -20,25 |
| UW dài nhất (ngày) | 138 [117..187] | 230 [219..246] | 654 | 792 | 615 |
| Hồi DD lớn nhất: đáy → đỉnh cũ (ngày) | 102 [2..180] | 88 [63..130] | 416 | 627 | 377 |
| Hồi DD lớn nhất: đỉnh → hồi (ngày) | 115 [59..187] | 194 [108..241] | 654 | 792 | 615 |
| Skew return ngày | 0,78 [-0,03..1,55] | -1,30 [-1,47..-0,97] | 0,16 | -0,06 | 0,22 |
| Kurtosis dư return ngày | 90,0 [85,0..96,5] | 55,5 [51,5..58,5] | 4,8 | 4,2 | 4,4 |
| % tuần dương | 47,0 [44,7..49,5] | 51,7 [50,0..52,9] | 51,0 | 48,1 | 51,0 |
| % tháng dương | 69,8 [66,7..72,9] | 69,5 [66,7..75,0] | 56,2 | 45,8 | 56,2 |
| ROI 2022 % | 4,3 [-0,3..16,2] | -3,0 [-6,2..1,4] | -65,1 | -67,9 | -37,1 |
| ROI 2023 % | 54,3 [49,9..60,2] | 84,9 [79,2..90,0] | 156,9 | 91,8 | 65,7 |
| ROI 2024 % | 33,6 [30,0..36,9] | 37,0 [30,8..41,2] | 122,5 | 47,8 | 55,4 |
| ROI 2025 % | 23,6 [19,0..27,7] | 18,7 [10,0..25,6] | -7,6 | -12,7 | -2,2 |

DD lớn nhất chưa hồi tới cuối cửa sổ: baseline không; M2 không; benchmark không.

## 2. Độ phủ lệnh (stress)

| chỉ số | Baseline | M2 |
|---|---|---|
| Lệnh vào/năm (mọi chân) | 739 [728..758] | 1587 [1511..1676] |
| Leg0/năm | 724 [715..744] | 1324 [1272..1384] |
| % ngày có ≥1 lệnh vào (mọi chân) | 10,0 [9,8..10,3] | 15,5 [14,9..16,0] |
| % ngày có ≥1 leg0 | 9,9 [9,7..10,3] | 15,0 [14,4..15,5] |
| % tuần có ≥1 lệnh vào | 44,1 [42,3..46,2] | 58,1 [56,7..60,1] |
| % tuần có ≥1 leg0 | 44,1 [42,3..46,2] | 57,5 [56,2..59,1] |
| % tháng có ≥1 lệnh vào | 88,8 [87,5..91,7] | 97,1 [93,8..100,0] |
| % thời gian (phút) có vị thế | 37,1 [35,8..38,9] | 50,9 [49,1..52,0] |
| % ngày có vị thế mở | 41,6 [40,3..43,7] | 56,5 [55,0..57,8] |
| Vị thế (cụm) đồng thời TB, mọi phút | 3,75 [3,65..3,87] | 7,99 [7,67..8,49] |
| Vị thế đồng thời TB khi có vị thế | 10,13 [9,51..10,47] | 15,71 [15,15..16,34] |
| Vị thế đồng thời p95 khi có vị thế | 30 [29..31] | 45 [44..47] |
| Vị thế đồng thời max | 70 [69..74] | 103 [102..105] |
| Chân mở đồng thời max | 80 [74..83] | 140 [137..150] |
| U TB khi có vị thế (% equity) | 13,1 [12,4..13,4] | 18,1 [17,5..18,7] |
| U p95 khi có vị thế % | 36,0 [35,4..36,7] | 47,4 [46,1..48,4] |
| U max % | 62,1 [60,6..63,7] | 68,3 [67,1..69,7] |
| Khoảng trống dài nhất không lệnh vào (ngày) | 67 [65..69] | 43 [37..49] |
| Khoảng trống p50 (ngày) | 7,2 [7,0..8,0] | 5,0 [5,0..5,0] |
| Khoảng trống p90 (ngày) | 26,2 [25,7..27,3] | 21,6 [18,6..22,8] |
| Số khoảng trống | 113 [108..116] | 156 [153..158] |
| Đợt/năm (tách ≥ 3 ngày yên) | 21,4 [20,5..22,8] | 26,6 [26,2..27,2] |
| Lệnh/đợt TB | 34,6 [32,3..36,0] | 59,6 [57,6..61,5] |
| Độ dài đợt TB (ngày) | 2,1 [2,0..2,2] | 2,8 [2,7..2,8] |
| Lệnh/tuần p25 | 0 [0..0] | 0 [0..0] |
| Lệnh/tuần p50 | 0 [0..0] | 3 [2..4] |
| Lệnh/tuần p75 | 24 [24..24] | 48 [44..54] |
| Lệnh/tuần max | 297 [292..303] | 399 [385..406] |
| % tuần PnL MTM dương | 47,0 [44,7..49,5] | 51,7 [50,0..52,9] |
| % tuần âm | 15,5 [14,4..17,3] | 25,3 [24,0..27,9] |
| % tuần bằng 0 | 37,5 [34,6..39,9] | 23,0 [22,1..24,5] |
| % tháng dương | 69,8 [66,7..72,9] | 69,5 [66,7..75,0] |
| % ΣPnL MTM từ top-5 ngày | 31,0 [29,0..32,4] | 30,0 [27,6..32,6] |
| % ΣPnL MTM từ top-10 ngày | 47,3 [44,3..49,7] | 49,2 [45,4..53,0] |
| % ΣPnL MTM từ top-20 ngày | 71,7 [66,2..75,4] | 76,7 [70,9..81,8] |
| % ΣPnL realized từ top-3 đợt | 30,2 [28,5..32,1] | 34,0 [31,6..38,3] |
| Gini lãi ngày (max(ΔE,0)) | 0,909 [0,907..0,911] | 0,876 [0,871..0,881] |

### 2b. Theo năm (mean qua seed: Baseline / M2)

| chỉ số | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|
| Lệnh vào | 618 / 1367 | 763 / 1483 | 839 / 1952 | 737 / 1548 |
| % ngày có lệnh vào | 8,0 / 13,1 | 12,2 / 16,1 | 12,0 / 17,2 | 7,8 / 15,7 |
| % ngày có leg0 | 8,0 / 13,1 | 12,2 / 16,1 | 12,0 / 17,2 | 7,3 / 13,6 |
| % tuần có lệnh vào | 34,6 / 44,0 | 57,2 / 66,1 | 42,5 / 57,5 | 41,9 / 65,0 |
| % thời gian có vị thế | 21,8 / 37,9 | 52,4 / 59,6 | 41,8 / 53,8 | 32,2 / 52,3 |
| % ngày có vị thế | 25,5 / 42,5 | 58,6 / 66,4 | 46,2 / 58,7 | 36,2 / 58,6 |
| Khoảng trống dài nhất (ngày) | 66 / 33 | 25 / 24 | 53 / 40 | 54 / 39 |
| Số đợt | 16,2 / 20,9 | 28,9 / 34,2 | 19,0 / 23,4 | 21,4 / 28,0 |
| Lệnh/tuần p50 | 0,0 / 0,0 | 2,2 / 22,4 | 0,0 / 5,5 | 0,0 / 3,2 |
| % tuần dương | 33,4 / 38,7 | 65,1 / 66,3 | 49,3 / 52,4 | 40,0 / 49,3 |
| ROI năm % | 4,3 / -3,0 | 54,3 / 84,9 | 33,6 / 37,0 | 23,6 / 18,7 |
| ROI BTC B&H % | -65,1 | 156,9 | 122,5 | -7,6 |

## 3. Tương quan với BTC (return ngày +07)

| chỉ số | Baseline | M2 | ETH B&H | 50/50 |
|---|---|---|---|---|
| Tương quan ngày vs BTC (toàn kỳ) | 0,221 [0,207..0,233] | 0,319 [0,306..0,331] | 0,821 | 0,998 |
| Tương quan ngày vs ETH | 0,244 [0,232..0,254] | 0,345 [0,332..0,357] | 1,000 | 0,815 |
| Số ngày BTC < −5% | 35 [35..35] | 35 [35..35] | 35 | 35 |
| Tương quan, chỉ ngày BTC < −5% | 0,480 [0,437..0,539] | 0,524 [0,456..0,559] | 0,861 | 0,980 |
| Return TB những ngày BTC < −5% (%) | -0,26 [-0,32..-0,19] | -0,94 [-1,07..-0,81] | -8,01 | -3,43 |
| BTC TB những ngày đó (%) | -7,10 [-7,10..-7,10] | -7,10 [-7,10..-7,10] | -7,10 | -7,10 |

## 4. Đặc tính lệnh (stress; lệnh đóng trong cửa sổ, mọi chân)

| chỉ số | Baseline | M2 |
|---|---|---|
| Lệnh đóng/năm | 739 [728..758] | 1587 [1511..1676] |
| Win rate % | 82,9 [82,5..83,3] | 79,8 [79,3..80,3] |
| Avg win % margin | 8,09 [8,02..8,13] | 7,62 [7,59..7,66] |
| Avg loss % margin | -17,95 [-18,60..-17,13] | -17,22 [-17,45..-17,04] |
| Avg win USD | 58 [55..62] | 44 [42..45] |
| Avg loss USD | -153 [-169..-145] | -117 [-121..-109] |
| Payoff (avg win / avg loss tuyệt đối, USD) | 0,38 [0,37..0,39] | 0,37 [0,36..0,39] |
| Expectancy %/lệnh (margin) | 3,645 [3,382..3,913] | 2,599 [2,470..2,789] |
| Expectancy USD/lệnh | 22,0 [20,1..23,7] | 11,2 [10,0..12,5] |
| Giữ p50 (giờ) | 12,8 [12,5..13,4] | 17,5 [16,6..18,1] |
| Giữ p90 (giờ) | 168,0 [168,0..168,0] | 168,0 [168,0..168,0] |
| % chân giữ ≥ 168h (time-stop) | 16,5 [16,2..16,9] | 17,9 [17,5..18,1] |
| % leg0 giữ ≥ 168h | 16,9 [16,5..17,3] | 20,3 [19,8..20,7] |
| Lỗ đơn lệnh tệ nhất % vốn | -1,71 [-2,03..-1,21] | -2,03 [-2,03..-2,03] |
| Lỗ đơn lệnh tệ nhất % margin | -89,7 [-100,1..-69,5] | -100,1 [-100,1..-100,1] |
| MAE p10 % | -27,16 [-27,87..-26,58] | -27,71 [-28,32..-27,30] |
| MAE p50 % | -6,20 [-6,54..-5,97] | -5,90 [-6,10..-5,72] |
| MAE tệ nhất % | -95,0 [-100,0..-88,1] | -100,0 [-100,0..-100,0] |

## 5. M2 − Baseline ghép cặp theo seed (stress)

| chỉ số | Δ mean | Δ [min..max] | seed M2 tốt hơn |
|---|---|---|---|
| CAGR22 % | 3,00 | [-0,33..6,84] | 7/8 |
| maxDD MTM phút % | -5,13 | [-6,66..-2,59] | 0/8 |
| Calmar | -0,117 | [-0,336..0,150] | 2/8 |
| Sharpe ngày (×√365) | -0,31 | [-0,48..-0,09] | 0/8 |
| Sortino ngày (×√365) | -0,74 | [-1,02..-0,28] | 0/8 |
| Vol năm hoá % | 5,0 | [4,6..5,7] | 0/8 |
| Ngày tệ nhất % | -2,91 | [-4,71..-1,72] | 0/8 |
| Tuần ISO tệ nhất % | -1,34 | [-4,06..1,43] | 1/8 |
| Tháng tệ nhất % | 1,33 | [-5,11..3,55] | 6/8 |
| UW dài nhất (ngày) | 92 | [32..129] | 0/8 |
| % tuần PnL MTM dương | 4,7 | [2,4..8,2] | 8/8 |
| % tháng dương | -0,3 | [-6,2..6,2] | 2/8 |
| Lệnh vào/năm (mọi chân) | 848 | [782..944] | trung tính (Δ>0: 8/8) |
| % ngày có ≥1 lệnh vào (mọi chân) | 5,5 | [4,8..6,2] | 8/8 |
| % ngày có ≥1 leg0 | 5,1 | [4,5..5,7] | 8/8 |
| % tuần có ≥1 lệnh vào | 14,1 | [12,0..16,3] | 8/8 |
| % tháng có ≥1 lệnh vào | 8,3 | [4,2..12,5] | 8/8 |
| % thời gian (phút) có vị thế | 13,8 | [11,9..15,5] | trung tính (Δ>0: 8/8) |
| U TB khi có vị thế (% equity) | 5,0 | [4,3..5,7] | trung tính (Δ>0: 8/8) |
| Khoảng trống dài nhất không lệnh vào (ngày) | -24 | [-29..-16] | 8/8 |
| Đợt/năm (tách ≥ 3 ngày yên) | 5,2 | [4,2..5,8] | trung tính (Δ>0: 8/8) |
| Lệnh/tuần p50 | 3 | [2..4] | 8/8 |
| % tuần bằng 0 | -14,5 | [-16,8..-11,1] | 8/8 |
| % ΣPnL MTM từ top-10 ngày | 1,9 | [-4,0..7,3] | 3/8 |
| Gini lãi ngày (max(ΔE,0)) | -0,034 | [-0,038..-0,029] | 8/8 |
| Win rate % | -3,2 | [-3,8..-2,4] | 0/8 |
| Payoff (avg win / avg loss tuyệt đối, USD) | -0,01 | [-0,03..0,01] | 3/8 |
| Expectancy %/lệnh (margin) | -1,046 | [-1,337..-0,694] | 0/8 |
| Lỗ đơn lệnh tệ nhất % vốn | -0,32 | [-0,82..0,00] | 1/8 |
| MAE p10 % | -0,55 | [-1,39..0,06] | 2/8 |
| Tương quan ngày vs BTC (toàn kỳ) | 0,098 | [0,079..0,115] | 0/8 |
| Return TB những ngày BTC < −5% (%) | -0,68 | [-0,80..-0,53] | 0/8 |

## 6. Phụ: bản phí gốc (phạt 0)

- Baseline gqsf (8 seed): CAGR 36,95 [35,58..39,31]; maxDD -22,55 [-24,67..-20,05]; Calmar 1,647 [1,453..1,961]; Sharpe 2,28 [2,17..2,43]; % ngày có lệnh 9,8 [9,5..10,1]; % thời gian có vị thế 35,9 [34,7..37,5]; % tuần dương 47,1 [45,7..49,0].
- M2 nsel-m2b (3 seed): CAGR 43,22 [42,10..44,26]; maxDD -26,97 [-27,24..-26,78]; Calmar 1,603 [1,546..1,653]; Sharpe 1,97 [1,91..2,03]; % ngày có lệnh 15,4 [14,9..15,7]; % thời gian có vị thế 50,9 [50,0..51,6]; % tuần dương 54,5 [53,4..55,8].
- M2 − Baseline phí gốc ghép cặp seed [42, 7, 21]: ΔCAGR 7,11, ΔmaxDD -3,76, ΔCalmar 0,043, Δ% ngày có lệnh 5,7, ΔSharpe -0,28.

## 7. Tự kiểm

- Thước MTM phút vs scorer B (`docs/result/NSEL_RESULT_B.json`): 16 run, max |ΔCAGR22| = 0,000000 pp, max |ΔmaxDD22| = 0,000000 pp.
- Equity MTM cuối cửa sổ vs result.json equity_final: max |lệch| = 0,0008% (chân mở qua cuối cửa sổ).
- Phút-chân thiếu giá (ffill/entry): 0,0065%; ngày thiếu file ticker: 0; phút thiếu giá BTC/ETH (trước ffill): {'BTC': 940, 'ETH': 1440}.
- Parity scorer A (`docs/result/NSEL_RESULT_A.json`) cho run dùng: 26/27 PASS (khác: nsel-m2b-s21 THIEU_LUC_CHAM_A (queue PASS)).
- Dòng printDone bị bỏ (thiếu số): 0.
