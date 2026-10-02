# RESULT_SHORT_V2_P0A — State map (Pha 0A, PROGRAM_SHORT_V2)

**Kết luận (kill-criterion 0A): FAIL — KILL.** Không ứng viên nào (LIQ/BTCF/BLEED/FLAT/BLEED′) đạt đồng thời cover ≥3% +
`netproxy_7d` > +0,5% ở ≥3/4 năm + CI block-7d ngoài 0 — kể cả với CI RAW (không cần đến inflate). Gần nhất: LIQ (3/4 năm, CI raw
[−0,18;+2,30]) và BTCF (CI raw [+0,05;+2,00] nhưng chỉ 2/4 năm). Gate trạng thái KHÔNG tách khỏi rổ alt: excess_7d mọi trạng thái
∈ [−0,28%; +0,28%], BLEED +0,05% (tệ hơn ALL một chút).

Pre-reg: `docs/prereg/PREREG_SHORT_V2_P0A.md` @ 07d9e335 (commit TRƯỚC khi đo). Script: `research/analysis/short_v2_p0a_statemap.py`.
JSON: `docs/result/RESULT_SHORT_V2_P0A.json`. Dữ liệu: CLOSES_1H.bin (daily close + đường 1h), Aerospike `kline_1m_opt`
(quoteVol ngày UTC, cache ngoài repo `~/claude_master/1002/p0a_cache/qv/`), `/tmp/fund_cache.npz` (funding exact).
Chạy 2 lần (lần 2 chỉ thêm sanity) → bảng giống hệt byte-by-byte.

## 0. Sanity (chạy trước bảng chính)
- **S-a**: 339 409 coin-ngày DEV hợp lệ (624 coin, loại BTC + 5 stable). NA (đang listed nhưng thiếu warm-up 61/90 ngày): 2 037 / 7 534 /
  8 571 / 31 317 (2022→2025). Tỷ lệ trạng thái theo năm (LIQ/BTCF/BLEED/FLAT): 2022 13,4/26,1/41,3/19,2 · 2023 23,4/19,9/27,0/29,8 ·
  2024 22,9/20,3/36,1/20,7 · 2025 12,9/24,7/45,2/17,2 (%). Lệnh: T3 338 976, T7 338 375, T14 337 327; path cụt (delist/gap,
  dùng close cuối) 428/506/639; 100% lệnh có funding.
- **S-b causal**: thay toàn bộ close/quoteVol SAU 2022-06-15, 2023-09-01, 2025-03-10 bằng số ngẫu nhiên → state, run_up, age_hi,
  dd_hi, tsh_z, beta60, tier, bull của mọi ngày ≤ ngày cắt GIỐNG HỆT (assert pass 3/3).
- **S-c**: CFXUSDT (pre-reg) chỉ có dữ liệu từ 2023-02-20 trong CLOSES_1H ⇒ toàn NA trong cửa sổ (không đủ warm-up) — không kiểm
  được. Bổ sung TRBUSDT 2023-10-01→11-29 (chỉ kiểm tay, không ảnh hưởng số): LIQ trong pha pump (run_up 5→9,5, age_hi 0–10),
  nhưng ngay khi age_hi ≥ 11 coin rơi vào **BTCF** (tier LỚN do volume pump, beta60 1,2–2,7 do vol riêng) thay vì BLEED, kể cả khi
  dd_hi −45% và tsh_z −1,9. ⇒ BTCF (ưu tiên 2) hút các coin "rác" vừa pump; BLEED tier LỚN chỉ 3 335 lệnh T7. Đây là đặc điểm của
  định nghĩa cố định, không sửa (xem §Đề xuất amend).
- **S-d**: close 1m phút cuối vs daily close CLOSES_1H: 388 868 cặp, lệch 0 (median/p99). Σ tsh = 1 (±4e-16). 0 ngày thiếu phút.
  SL ⇔ maxFav ≥ 10%: lệch 1 lệnh (biên float). Funding 7d p0,1 = −6,6%, 549 lệnh < −5% (squeeze funding âm thật).

## A. Trạng thái × T (toàn DEV 2022–2025; % ; maxFav trên 1h closes = cận dưới)

| nhóm | T | n | cover | bleed mean | bleed med | excess | pSQ10 | pSQ20 | P(ret≤−10%) | funding | netproxy | CI raw | CI inflate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LIQ | 3 | 59637 | 17.6 | -0.05 | -1.13 | -0.00 | 28.2 | 10.1 | 17.7 | +0.010 | **+0.59** | [-0.16;+1.36] | [-0.27;+1.48] |
| LIQ | 7 | 59548 | 17.6 | -0.16 | -2.64 | -0.09 | 43.9 | 21.4 | 29.6 | +0.039 | **+1.07** | [-0.18;+2.30] | [-0.37;+2.49] |
| LIQ | 14 | 59480 | 17.6 | -0.72 | -4.99 | -0.16 | 54.6 | 32.3 | 38.8 | +0.072 | **+1.44** | [-0.12;+3.03] | [-0.36;+3.28] |
| BTCF | 3 | 77364 | 22.8 | -0.39 | -0.74 | -0.16 | 20.4 | 5.3 | 13.0 | -0.001 | **+0.53** | [-0.02;+1.12] | [-0.10;+1.21] |
| BTCF | 7 | 77263 | 22.8 | -0.89 | -1.97 | -0.28 | 36.6 | 14.1 | 24.3 | -0.007 | **+1.00** | [+0.05;+2.00] | [-0.10;+2.16] |
| BTCF | 14 | 77060 | 22.8 | -1.68 | -4.34 | -0.52 | 49.7 | 25.7 | 36.0 | -0.027 | **+1.46** | [+0.18;+2.73] | [-0.02;+2.93] |
| BLEED | 3 | 131893 | 38.9 | -0.23 | -0.42 | +0.05 | 17.7 | 4.0 | 11.2 | +0.036 | **+0.41** | [-0.21;+1.07] | [-0.31;+1.17] |
| BLEED | 7 | 131659 | 38.9 | -0.74 | -1.38 | +0.05 | 34.3 | 12.0 | 22.1 | +0.064 | **+0.95** | [-0.10;+2.09] | [-0.26;+2.27] |
| BLEED | 14 | 131092 | 38.9 | -1.50 | -3.73 | -0.00 | 48.1 | 24.4 | 33.9 | +0.088 | **+1.62** | [+0.16;+3.08] | [-0.06;+3.31] |
| BLEED' | 3 | 75861 | 22.4 | -0.06 | -0.28 | +0.06 | 17.2 | 3.7 | 10.0 | +0.016 | **+0.15** | [-0.58;+0.86] | [-0.69;+0.97] |
| BLEED' | 7 | 75862 | 22.4 | -0.62 | -1.04 | +0.07 | 33.8 | 11.1 | 19.8 | +0.026 | **+0.48** | [-0.82;+1.81] | [-1.03;+2.02] |
| BLEED' | 14 | 75862 | 22.4 | -1.69 | -3.23 | +0.07 | 47.8 | 23.0 | 32.0 | +0.025 | **+1.07** | [-0.60;+2.82] | [-0.86;+3.09] |
| FLAT | 3 | 70082 | 20.7 | +0.17 | -0.21 | +0.09 | 17.8 | 4.7 | 10.0 | +0.051 | **+0.16** | [-0.38;+0.75] | [-0.47;+0.84] |
| FLAT | 7 | 69905 | 20.7 | +0.63 | -0.55 | +0.28 | 34.7 | 13.6 | 19.1 | +0.094 | **+0.21** | [-0.70;+1.17] | [-0.84;+1.32] |
| FLAT | 14 | 69695 | 20.7 | +1.64 | -1.68 | +0.71 | 49.1 | 26.7 | 28.6 | +0.132 | **+0.41** | [-0.76;+1.62] | [-0.94;+1.81] |
| ALL | 3 | 338976 | 100.0 | -0.15 | -0.54 | +0.00 | 20.2 | 5.5 | 12.5 | +0.026 | **+0.42** | [-0.10;+0.95] | [-0.18;+1.03] |
| ALL | 7 | 338375 | 100.0 | -0.39 | -1.49 | +0.00 | 36.6 | 14.5 | 23.3 | +0.050 | **+0.83** | [-0.06;+1.75] | [-0.20;+1.89] |
| ALL | 14 | 337327 | 100.0 | -0.76 | -3.61 | -0.00 | 49.8 | 26.5 | 34.1 | +0.068 | **+1.30** | [+0.13;+2.44] | [-0.05;+2.61] |

## B. Theo năm (netproxy % ; bleed mean % ; pSQ10 %)

| nhóm | T | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| LIQ | 3 | np +2.13 · bl -1.94 · sq 21.9 · n 6411 | np -0.75 · bl +1.07 · sq 26.3 · n 14189 | np +0.51 · bl +0.40 · sq 31.4 · n 21163 | np +1.21 · bl -0.79 · sq 28.3 · n 17874 |
| LIQ | 7 | np +3.72 · bl -4.37 · sq 34.0 · n 6412 · CI [+1.42;+5.87] | np -1.22 · bl +2.26 · sq 44.9 · n 14189 · CI [-2.75;+0.56] | np +1.18 · bl +0.79 · sq 47.9 · n 21163 · CI [-1.89;+4.26] | np +1.80 · bl -1.69 · sq 41.9 · n 17784 · CI [+0.43;+3.08] |
| LIQ | 14 | np +4.90 · bl -7.25 · sq 43.4 · n 6412 | np -1.77 · bl +4.02 · sq 59.6 · n 14189 | np +1.93 · bl +0.30 · sq 56.9 · n 21163 | np +2.18 · bl -3.38 · sq 51.8 · n 17716 |
| BTCF | 3 | np +0.88 · bl -0.97 · sq 19.0 · n 12483 | np -0.29 · bl +0.52 · sq 14.6 · n 12075 | np +0.10 · bl +0.37 · sq 23.1 · n 18702 | np +0.93 · bl -0.91 · sq 21.5 · n 34104 |
| BTCF | 7 | np +1.59 · bl -2.10 · sq 34.6 · n 12483 · CI [-0.34;+3.73] | np -0.23 · bl +1.13 · sq 30.7 · n 12075 · CI [-1.93;+1.49] | np +0.01 · bl +1.09 · sq 41.7 · n 18702 · CI [-1.95;+2.02] | np +1.77 · bl -2.24 · sq 36.6 · n 34003 · CI [+0.15;+3.51] |
| BTCF | 14 | np +2.46 · bl -3.72 · sq 47.6 · n 12483 | np -0.21 · bl +2.03 · sq 44.5 · n 12075 | np -0.32 · bl +1.90 · sq 57.1 · n 18702 | np +2.67 · bl -4.23 · sq 48.2 · n 33800 |
| BLEED | 3 | np +0.54 · bl -0.72 · sq 19.0 · n 19732 | np -0.38 · bl +0.44 · sq 11.8 · n 16399 | np -0.16 · bl +0.48 · sq 18.7 · n 33347 | np +0.88 · bl -0.64 · sq 18.2 · n 62415 |
| BLEED | 7 | np +0.97 · bl -1.45 · sq 35.7 · n 19733 · CI [-1.16;+3.13] | np -0.48 · bl +0.90 · sq 27.9 · n 16399 · CI [-2.12;+1.37] | np -0.18 · bl +1.00 · sq 38.0 · n 33347 · CI [-2.38;+2.06] | np +1.92 · bl -1.89 · sq 33.5 · n 62180 · CI [+0.14;+3.71] |
| BLEED | 14 | np +1.63 · bl -2.25 · sq 49.3 · n 19733 | np -0.59 · bl +1.55 · sq 43.6 · n 16399 | np -0.23 · bl +1.75 · sq 54.2 · n 33347 | np +3.22 · bl -3.83 · sq 45.6 · n 61613 |
| BLEED' | 3 | np +0.47 · bl -0.69 · sq 18.4 · n 16712 | np +0.16 · bl -0.14 · sq 9.6 · n 7540 | np -1.02 · bl +1.32 · sq 18.2 · n 15775 | np +0.52 · bl -0.36 · sq 17.9 · n 35834 |
| BLEED' | 7 | np +1.12 · bl -1.76 · sq 34.4 · n 16713 · CI [-1.20;+3.62] | np -0.01 · bl +0.43 · sq 25.5 · n 7540 · CI [-2.76;+3.13] | np -2.11 · bl +2.85 · sq 39.9 · n 15775 · CI [-4.66;+0.32] | np +1.44 · bl -1.84 · sq 32.5 · n 35834 · CI [-0.69;+3.60] |
| BLEED' | 14 | np +1.84 · bl -2.64 · sq 48.0 · n 16713 | np +0.33 · bl +0.25 · sq 40.1 · n 7540 | np -3.55 · bl +4.62 · sq 58.4 · n 15775 | np +2.89 · bl -4.44 · sq 44.7 · n 35834 |
| FLAT | 3 | np +0.86 · bl -0.90 · sq 18.6 · n 9153 | np -0.97 · bl +1.17 · sq 14.7 · n 18099 | np -0.15 · bl +0.62 · sq 20.4 · n 19099 | np +0.99 · bl -0.53 · sq 17.6 · n 23731 |
| FLAT | 7 | np +1.65 · bl -2.33 · sq 33.6 · n 9154 · CI [-0.37;+3.88] | np -1.65 · bl +2.71 · sq 35.0 · n 18099 · CI [-3.22;+0.10] | np -0.56 · bl +2.14 · sq 39.0 · n 19099 · CI [-2.37;+1.40] | np +1.70 · bl -1.06 · sq 31.3 · n 23553 · CI [+0.12;+3.28] |
| FLAT | 14 | np +2.73 · bl -5.08 · sq 46.2 · n 9154 | np -2.15 · bl +5.18 · sq 52.6 · n 18099 | np -0.80 · bl +5.44 · sq 55.0 · n 19099 | np +2.49 · bl -1.59 · sq 42.9 · n 23343 |
| ALL | 3 | np +0.91 · bl -0.98 · sq 19.3 · n 47779 | np -0.62 · bl +0.82 · sq 16.6 · n 60762 | np +0.05 · bl +0.47 · sq 22.9 · n 92311 | np +0.96 · bl -0.71 · sq 20.3 · n 138124 |
| ALL | 7 | np +1.63 · bl -2.18 · sq 34.8 · n 47782 · CI [-0.26;+3.60] | np -0.95 · bl +1.80 · sq 34.6 · n 60762 · CI [-2.35;+0.49] | np +0.09 · bl +1.21 · sq 41.2 · n 92311 · CI [-1.77;+2.02] | np +1.83 · bl -1.81 · sq 35.0 · n 137520 · CI [+0.32;+3.41] |
| ALL | 14 | np +2.50 · bl -3.85 · sq 47.4 · n 47782 | np -1.26 · bl +3.30 · sq 50.2 · n 60762 | np +0.13 · bl +2.21 · sq 55.6 · n 92311 | np +2.82 · bl -3.49 · sq 46.6 · n 136472 |

## C. Độ dài run (ngày lịch; run bắt đầu trong DEV)

| trạng thái | tier | n | p25 | p50 | p75 | mean | kiểm duyệt |
|---|---|---|---|---|---|---|---|
| LIQ | ALL | 11034 | 1.0 | 2.0 | 5.0 | 5.4 | 17 |
| LIQ | LON | 3272 | 1.0 | 2.0 | 9.0 | 6.1 | 5 |
| LIQ | VUA | 4054 | 1.0 | 2.0 | 5.0 | 5.4 | 5 |
| LIQ | NHO | 3708 | 1.0 | 1.0 | 3.0 | 4.8 | 7 |
| BLEED | ALL | 19299 | 1.0 | 4.0 | 8.0 | 6.8 | 62 |
| BLEED | LON | 737 | 1.0 | 3.0 | 7.0 | 5.5 | 4 |
| BLEED | VUA | 9834 | 2.0 | 4.0 | 9.0 | 7.6 | 39 |
| BLEED | NHO | 8728 | 1.0 | 3.0 | 8.0 | 6.1 | 19 |

## D. Chuyển trạng thái P(s_{d+1} | s_d)

| từ \ sang | LIQ | BTCF | BLEED | FLAT | n |
|---|---|---|---|---|---|
| LIQ | 0.816 | 0.056 | 0.023 | 0.105 | 59621 |
| BTCF | 0.035 | 0.946 | 0.014 | 0.006 | 77291 |
| BLEED | 0.021 | 0.003 | 0.855 | 0.120 | 131837 |
| FLAT | 0.079 | 0.005 | 0.238 | 0.678 | 70052 |

## E. BLEED T=7 theo tier / regime

| lát | n | bleed mean | excess | pSQ10 | funding | netproxy | CI raw | CI inflate |
|---|---|---|---|---|---|---|---|---|
| tier_LON | 3335 | -0.86 | -0.91 | 34.3 | +0.072 | **+1.10** | [-0.41;+2.90] | [-0.65;+3.19] |
| tier_VUA | 65924 | -0.96 | -0.11 | 35.0 | +0.049 | **+1.11** | [+0.02;+2.26] | [-0.15;+2.44] |
| tier_NHO | 62400 | -0.50 | +0.28 | 33.5 | +0.080 | **+0.77** | [-0.27;+1.94] | [-0.43;+2.12] |
| bull | 55003 | -0.96 | +0.02 | 35.0 | +0.118 | **+1.63** | [-0.18;+3.61] | [-0.46;+3.92] |
| notbull(=BLEED') | 75862 | -0.62 | +0.07 | 33.8 | +0.026 | **+0.48** | [-0.82;+1.81] | [-1.03;+2.02] |

## F. Kill-criterion 0A (T=7)

| ứng viên | cover | C1 cover≥3% | năm >+0,5% | C2 ≥3/4 | netproxy_7d | C3 raw | C3 inflate | PASS raw | PASS inflate |
|---|---|---|---|---|---|---|---|---|---|
| LIQ | 17.6% | True | 3/4 | True | +1.07 | False | False | False | False |
| BTCF | 22.8% | True | 2/4 | False | +1.00 | True | False | False | False |
| BLEED | 38.9% | True | 2/4 | False | +0.95 | False | False | False | False |
| FLAT | 20.7% | True | 2/4 | False | +0.21 | False | False | False | False |
| BLEED' | 22.4% | True | 2/4 | False | +0.48 | False | False | False | False |

**VERDICT: FAIL**

## G. Phân rã netproxy_7d (đồng nhất đại số với công thức §1)
`netproxy = −bleed_mean + pSQ10·(E[ret|SL] − 0,102) + funding − 0,112%` (đơn vị %):

| nhóm | −bleed | SL-convexity | funding | phí | = netproxy | E[ret_T thô \| SL] |
|---|---|---|---|---|---|---|
| LIQ | +0,16 | +0,98 | +0,04 | −0,11 | +1,07 | +12,4 |
| BTCF | +0,89 | +0,23 | −0,01 | −0,11 | +1,00 | +10,8 |
| BLEED | +0,74 | +0,25 | +0,06 | −0,11 | +0,95 | +10,9 |
| BLEED′ | +0,62 | −0,05 | +0,03 | −0,11 | +0,48 | +10,1 |
| FLAT | −0,63 | +0,85 | +0,09 | −0,11 | +0,21 | +12,7 |
| ALL | +0,39 | +0,50 | +0,05 | −0,11 | +0,83 | +11,6 |

"SL-convexity" = phần lợi do SL cắt ở +10,2% thay vì giữ tới T. Với LIQ ~92% netproxy đến từ đây — phần này phụ thuộc giả định
SL khớp đúng +10,2% và chỉ kích hoạt theo 1h close (bỏ qua wick trong giờ ⇒ SL thật kích hoạt NHIỀU hơn, kể cả trên path quay đầu
thành lãi) ⇒ lạc quan, chưa lượng hoá được ở pha này.

## H. Quan sát (chỉ mô tả số, không thêm ngưỡng)
1. **Gate không tách khỏi beta rổ alt.** excess_7d: LIQ −0,09, BTCF −0,28, BLEED +0,05, FLAT +0,28 (%). pSQ10_7d BLEED 34,3% vs ALL
   36,6% (−6% tương đối); LIQ cao nhất 43,9%. Dấu netproxy theo năm do regime: mọi nhóm dương 2022 & 2025, âm/≈0 2023–2024 (ALL
   +1,63/−0,95/+0,09/+1,83).
2. **Regime đi NGƯỢC giả thuyết**: BLEED∧bull +1,63% (bleed −0,96, funding +0,118) > BLEED′ = BLEED∧¬bull +0,48%; BLEED′ 2024 −2,11%.
3. **Chu kỳ ngắn — xác nhận theo run trạng thái**: LIQ median 2 ngày (p75 5; LỚN p75 9), BLEED median 4 ngày (p75 8); P(ở lại) LIQ
   0,816, BLEED 0,855, FLAT→BLEED 0,238. Run bị phân mảnh do điều kiện ngày nhấp nháy (tsh_z quanh 0, dd_hi quanh −15%) ⇒ đây là
   cận dưới độ dài "pha" thật (ZigZag 25% trước đó: up-leg median 18d).
4. pSQ10 tăng mạnh theo T (BLEED 17,7 → 34,3 → 48,1% ở 3/7/14d) — đuôi phải không giảm khi giữ lâu; netproxy tăng theo T chủ yếu
   nhờ bleed rổ + SL-convexity.

## Giới hạn
- maxFav/SL trên 1h closes = cận dưới squeeze; SL giả định khớp đúng +10,2% (không slippage/gap/liquidation) ⇒ netproxy lạc quan.
- Lệnh coin-ngày chồng lấn (T > 1 ngày): CI block-7d cluster theo thời gian; với T=14 cửa sổ vượt khối ⇒ CI T14 có thể hẹp.
- Coin mới list (< 61/90 ngày dữ liệu) bị loại (NA: 31 317 coin-ngày 2025) — đúng nhóm pump/dump mạnh nhất không được đo.
- Universe = symbol có trong Aerospike `kline_1m_opt` (590 cuối 2025); funding từ cache scan Aerospike (phủ 100% lệnh).
- S-c pre-reg (CFX) không kiểm được do thiếu warm-up; thay bằng TRB (kiểm tay).

## Đề xuất amend cho pha sau (KHÔNG chạy)
- BTCF thiếu điều kiện "theo BTC" thật (tương quan/R²): coin vừa pump có beta60 > 1,5 do vol riêng và tier LỚN do volume pump ⇒
  bị gán BTCF thay vì BLEED (TRB). Ứng viên: BTCF yêu cầu corr60 ≥ ngưỡng, hoặc đặt BLEED trước BTCF, hoặc tier dùng quoteVol 90d.
- Đo SL/pSQ bằng 1m high (sim first-hit) trước khi tin phần SL-convexity — chính là phần lớn netproxy của LIQ.
- Hysteresis cho đo độ dài run (tránh nhấp nháy quanh ngưỡng).
- Theo chương trình: FAIL 0A ⇒ dừng; quyết định có mở lại với amend hay không thuộc MASTER/owner.
