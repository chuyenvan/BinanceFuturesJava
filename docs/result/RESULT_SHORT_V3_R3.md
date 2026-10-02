# RESULT_SHORT_V3_R3 — Breakdown momentum (cascade xả)

**Kết luận GO-R3: NO-GO — 0/5 điều kiện đạt ở cả T=3 và T=7.** Phá đáy 30d + volume ≥2× + rơi ≥5% KHÔNG phải cascade tiếp diễn
mà là điểm **hồi** (mean-reversion): bleed_7d trung bình **+2,03%** (giá TĂNG sau entry), +4,51% sau 3 ngày; netproxy_7d **−1,66%**
(CI raw [−4,50;+1,75]); pSQ10_7d 52,2% = 1,42× ALL. Không tách khỏi ALL cùng ngày: excess_short_7d **−0,15%** (BRK hồi mạnh
hơn rổ một chút; pSQ10 rổ cùng ngày 52,4% ≈ BRK 52,2%) — BRK chỉ là đại diện cho NGÀY sập toàn thị trường, sau đó cả rổ hồi.

Pre-reg: `docs/prereg/PREREG_SHORT_V3_R3.md` @ 8b3e6202 (commit TRƯỚC khi đo). Chương trình: `PROGRAM_SHORT_V3.md` @ a8eff3fb §R3.
Script: `research/analysis/short_v3_r3_breakdown.py` (import hàm P0A `short_v2_p0a_statemap.py`, không sửa). JSON:
`docs/result/RESULT_SHORT_V3_R3.json`. Dữ liệu: CLOSES_1H.bin (daily close + đường 1h), cache quoteVol P0A (chỉ đọc),
`/tmp/fund_cache.npz` (funding exact). Chạy 1 lần, 15 s, RSS 1,3 GB. Không ngưỡng/lát nào thêm sau khi thấy số.

## 0. Sanity (in trước bảng chính)
- **S-a**: coin-ngày hợp lệ E (DEV) 354 241 (2022 48 672 · 2023 63 819 · 2024 95 609 · 2025 146 141). BRK raw → sau cooldown:
  554→352 · 357→275 · 608→513 · 1 285→1 038 (tổng 2 178; lệnh T3 2 177, T7 2 175). BNV raw → cooldown 3 141→1 583 · 1 613→933 ·
  3 807→2 092 · 9 535→5 113. cover BRK 0,61% (raw 0,79%), BNV 2,74%. **Cụm theo ngày**: BRK rơi vào chỉ 58/48/75/181 ngày lịch;
  max 78/82/178/362 BRK trong 1 ngày (2025: 1 ngày chiếm ~35% BRK năm) ⇒ cỡ mẫu hiệu dụng nhỏ, CI rộng. n_trunc BRK 1/5 (T3/T7);
  100% lệnh có funding; tier NA 0.
- **S-b causal**: thay close/quoteVol SAU 2022-06-15, 2023-09-01, 2025-03-10 bằng số ngẫu nhiên → lo30, r1, mqv, E, raw BRK/BNV,
  entry sau cooldown của mọi ngày ≤ ngày cắt GIỐNG HỆT (3/3); đối chứng: sau ngày cắt raw_BNV khác (test có lực).
- **S-c** 10 BRK mẫu (T=7), kiểm tay điều kiện đúng cả 10 (close ≤ lo30, r1 ≤ −5%, qv ≥ 2× median):
  AXS 2022-01-05 r1 −13,6% qv 2,9× ret7 −2,6% · CELR 2022-11-08 −17,6% 3,1× −17,1% · OGN 2023-06-10 −18,0% 2,7× +8,1% SL ·
  MEME 2024-04-13 −23,7% 2,1× +16,1% SL · DEFI 2024-08-05 −8,9% 7,7× +13,2% SL · SCRT 2025-01-19 −15,5% 2,3× −5,8% ·
  D 2025-06-05 −6,5% 5,4× +2,2% SL · AVAAI 2025-10-10 −46,8% 3,4× +28,9% SL · SONIC 2025-10-10 −27,7% 4,2× +2,7% SL ·
  CLO 2025-12-19 −14,5% 2,1× +37,9% SL.
- **S-d**: BRK ⊆ BNV (assert); không 2 entry cùng coin cách ≤ 7 ngày (assert); SL ⇔ maxFav ≥ 10% lệch 1 lệnh (biên float).
- Ghi chú: ALL ở đây = mọi coin-ngày E (cần 31 ngày lịch sử) ⇒ rộng hơn ALL P0A (cần 61/90 ngày): n_7d 353 182 vs 338 375;
  netproxy_7d ALL +0,86% vs +0,83% P0A (nhất quán).

## A. [BRK, BNV, ALL] × T (toàn DEV; %; maxFav/SL trên 1h closes = cận dưới squeeze)

| nhóm | T | n | cover | bleed mean | bleed med | excess_short | excess pnl | pSQ10 | pSQ20 | P(ret≤−10%) | funding | SL% | netproxy | CI raw | CI infl ×1,18 | netproxy noSL | CI raw noSL | năm >0 | năm >0,5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BRK | 3 | 2177 | 0.61 | +4.51 | +2.98 | -0.02 | +0.34 | 43.5 | 17.3 | 12.6 | -0.096 | 43.5 | **-2.42** | [-5.09;+0.79] | [-5.57;+1.36] | -4.77 | [-10.51;+1.05] | 1/4 | 1/4 |
| BRK | 7 | 2175 | 0.61 | +2.03 | +0.59 | -0.15 | +0.60 | 52.2 | 25.4 | 20.8 | -0.130 | 52.2 | **-1.66** | [-4.50;+1.75] | [-5.01;+2.36] | -2.42 | [-5.97;+1.63] | 2/4 | 2/4 |
| BNV | 3 | 9715 | 2.74 | +0.60 | +0.33 | +0.10 | +0.11 | 26.1 | 7.3 | 13.5 | -0.027 | 26.1 | **-0.21** | [-1.43;+1.03] | [-1.65;+1.25] | -0.77 | [-2.80;+0.99] | 3/4 | 3/4 |
| BNV | 7 | 9711 | 2.74 | -1.01 | -1.57 | +0.27 | +0.22 | 41.0 | 15.3 | 24.1 | -0.038 | 41.0 | **+0.27** | [-1.14;+1.76] | [-1.40;+2.03] | +0.79 | [-1.07;+2.77] | 2/4 | 2/4 |
| ALL | 3 | 353799 | 100.00 | -0.16 | -0.56 | +0.00 | -0.00 | 20.5 | 5.7 | 12.8 | +0.026 | 20.5 | **+0.44** | [-0.07;+0.97] | [-0.17;+1.07] | +0.05 | [-0.58;+0.67] | 3/4 | 2/4 |
| ALL | 7 | 353182 | 100.00 | -0.40 | -1.55 | -0.00 | +0.00 | 36.9 | 14.8 | 23.7 | +0.049 | 36.9 | **+0.86** | [-0.03;+1.77] | [-0.19;+1.93] | +0.29 | [-0.97;+1.58] | 3/4 | 2/4 |

## B. Theo năm (np = netproxy; nS = netproxy noSL; bl = bleed mean; ex = excess_short; sq = pSQ10; %)

| nhóm | T | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| BRK | 3 | np +0.62 · nS +4.08 · bl -4.54 · ex +0.02 · sq 37.5 · n 352 | np -1.22 · nS -1.40 · bl +1.25 · ex +0.30 · sq 9.5 · n 275 | np -4.29 · nS -6.65 · bl +6.51 · ex -0.34 · sq 55.4 · n 513 | np -2.85 · nS -7.75 · bl +7.47 · ex +0.04 · sq 48.8 · n 1037 |
| BRK | 7 | np +0.51 · nS +4.17 · bl -4.98 · ex +0.58 · sq 45.7 · n 352 · CI [-3.54;+5.03] | np +1.16 · nS +0.62 · bl -0.77 · ex +0.67 · sq 17.8 · n 275 · CI [-3.31;+8.89] | np -5.03 · nS -9.37 · bl +9.25 · ex -0.94 · sq 65.1 · n 513 · CI [-8.02;+1.51] | np -1.47 · nS -2.01 · bl +1.57 · ex -0.22 · sq 57.2 · n 1035 · CI [-5.55;+4.11] |
| BNV | 3 | np +1.66 · nS +2.83 · bl -3.09 · ex +0.32 · sq 24.1 · n 1583 | np +1.55 · nS +1.31 · bl -1.42 · ex +0.09 · sq 8.8 · n 933 | np +0.90 · nS +0.34 · bl -0.43 · ex -0.13 · sq 23.4 · n 2092 | np -1.57 · nS -2.72 · bl +2.54 · ex +0.13 · sq 30.9 · n 5107 |
| BNV | 7 | np +1.97 · nS +3.11 · bl -3.51 · ex +0.42 · sq 35.8 · n 1583 · CI [-1.50;+5.12] | np +2.32 · nS +2.03 · bl -2.11 · ex +0.25 · sq 26.2 · n 933 · CI [-2.99;+6.57] | np -0.53 · nS -1.78 · bl +1.74 · ex +0.03 · sq 39.0 · n 2092 · CI [-3.70;+2.66] | np -0.30 · nS +0.89 · bl -1.16 · ex +0.32 · sq 46.1 · n 5103 · CI [-2.36;+1.85] |
| ALL | 3 | np +0.93 · nS +0.84 · bl -0.99 · ex -0.00 · sq 19.4 · n 48669 | np -0.57 · nS -0.85 · bl +0.78 · ex -0.00 · sq 16.6 · n 63819 | np +0.05 · nS -0.50 · bl +0.48 · ex +0.00 · sq 23.2 · n 95605 | np +0.98 · nS +0.53 · bl -0.71 · ex -0.00 · sq 20.9 · n 145706 |
| ALL | 7 | np +1.67 · nS +2.00 · bl -2.22 · ex +0.00 · sq 34.9 · n 48672 · CI [-0.23;+3.66] | np -0.85 · nS -1.71 · bl +1.70 · ex -0.00 · sq 34.4 · n 63819 · CI [-2.26;+0.61] | np +0.08 · nS -1.12 · bl +1.23 · ex -0.00 · sq 41.6 · n 95605 · CI [-1.78;+2.00] | np +1.85 · nS +1.53 · bl -1.80 · ex -0.00 · sq 35.6 · n 145086 · CI [+0.35;+3.40] |

## C. BRK theo tier / regime (CHỈ báo cáo)

| T | lát | n | bleed mean | excess_short | pSQ10 | funding | netproxy | CI raw | netproxy noSL |
|---|---|---|---|---|---|---|---|---|---|
| 3 | tier_LON | 528 | +4.42 | -0.07 | 49.1 | -0.230 | **-2.85** | [-5.15;+0.23] | -4.87 |
| 3 | tier_VUA | 810 | +4.74 | +0.26 | 44.1 | -0.093 | **-2.18** | [-5.15;+1.39] | -4.97 |
| 3 | tier_NHO | 839 | +4.36 | -0.26 | 39.6 | -0.014 | **-2.38** | [-5.15;+0.73] | -4.52 |
| 3 | bull | 403 | -1.07 | +0.82 | 20.3 | -0.068 | **+1.12** | [-0.85;+3.29] | +0.84 |
| 3 | notbull | 1765 | +5.80 | -0.22 | 48.8 | -0.103 | **-3.22** | [-6.04;+0.66] | -6.07 |
| 7 | tier_LON | 527 | +1.79 | +0.60 | 56.9 | -0.292 | **-2.16** | [-4.65;+1.22] | -2.40 |
| 7 | tier_VUA | 810 | +2.38 | -0.14 | 52.3 | -0.155 | **-1.46** | [-4.47;+2.25] | -2.78 |
| 7 | tier_NHO | 838 | +1.84 | -0.63 | 49.2 | -0.005 | **-1.53** | [-4.53;+1.94] | -2.07 |
| 7 | bull | 403 | -2.98 | +1.68 | 30.3 | -0.116 | **+2.78** | [-0.25;+4.96] | +2.72 |
| 7 | notbull | 1765 | +3.17 | -0.57 | 57.2 | -0.134 | **-2.67** | [-5.53;+1.42] | -3.59 |

## D. Phân rã netproxy = −bleed + SL-convexity + funding − phí (%)

| nhóm | T | −bleed | SL-convexity | funding | phí | = netproxy | netproxy noSL |
|---|---|---|---|---|---|---|---|
| BRK | 3 | -4.51 | +2.30 | -0.096 | -0.112 | -2.42 | -4.77 |
| BRK | 7 | -2.03 | +0.61 | -0.130 | -0.112 | -1.66 | -2.42 |
| BNV | 3 | -0.60 | +0.53 | -0.027 | -0.112 | -0.21 | -0.77 |
| BNV | 7 | +1.01 | -0.59 | -0.038 | -0.112 | +0.27 | +0.79 |
| ALL | 3 | +0.16 | +0.37 | +0.026 | -0.112 | +0.44 | +0.05 |
| ALL | 7 | +0.40 | +0.52 | +0.049 | -0.112 | +0.86 | +0.29 |

## E. Luật GO-R3

| ô | netproxy | G1 >+0,5% | CI raw | CI infl | G2 lo>0 | năm>0 | G3 ≥3/4 | excess_short | G4 >+0,3% | pSQ10 | pSQ10 ALL | tỉ lệ | G5 ≤0,8 | PASS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BRK T3 | -2.42 | False | [-5.09;+0.79] | [-5.57;+1.36] | False | 1/4 | False | -0.02 | False | 43.5 | 20.5 | 2.12 | False | **False** |
| BRK T7 | -1.66 | False | [-4.50;+1.75] | [-5.01;+2.36] | False | 2/4 | False | -0.15 | False | 52.2 | 36.9 | 1.42 | False | **False** |

**VERDICT: NO-GO**

## F. Verdict từng điều kiện (BRK; T=3 / T=7)
- G1 netproxy > +0,5%: **FAIL / FAIL** (−2,42% / −1,66%).
- G2 CI raw & inflate cận dưới > 0: **FAIL / FAIL** (raw [−5,09;+0,79] / [−4,50;+1,75]; infl [−5,57;+1,36] / [−5,01;+2,36]).
- G3 ≥ 3/4 năm dương: **FAIL / FAIL** (1/4; 2/4 — dương 2022 +0,51, 2023 +1,16; âm 2024 −5,03, 2025 −1,47 ở T=7).
- G4 excess_short > +0,3%: **FAIL / FAIL** (−0,02% / −0,15%).
- G5 pSQ10 ≤ 0,8×ALL: **FAIL / FAIL** (43,5 vs 20,5 → 2,12×; 52,2 vs 36,9 → 1,42×). pSQ10 rổ ALL khớp ngày (chỉ báo cáo)
  42,4% / 52,4% ≈ BRK ⇒ squeeze là của NGÀY, không của coin.
**VERDICT: NO-GO.** Đối chứng BNV (không volume) cũng không qua: netproxy_7d +0,27% (CI [−1,14;+1,76]), 2/4 năm.

## G. Quan sát (chỉ mô tả số, không thêm ngưỡng)
1. **Volume làm tệ hơn, không tốt hơn.** BNV_7d bleed −1,01% (rơi tiếp nhẹ), BRK_7d +2,03% (hồi); T=3 BNV +0,60% vs BRK +4,51%.
   Volume ≥2× ngày phá đáy = capitulation/đáy xả, không phải đầu cascade. Hồi mạnh nhất 3 ngày đầu (bleed T3 > T7).
2. **Gate vẫn không tách khỏi beta ngày** — đúng điểm P0A fail, R3 không sửa được: excess_short BRK ≈ 0 (−0,02/−0,15%); BRK tập
   trung ở vài ngày sập toàn thị trường (2025: 1 ngày 362 lệnh), pSQ10 BRK = pSQ10 rổ cùng ngày. Lát bull (n 403, netproxy_7d
   +2,78%, CI raw [−0,25;+4,96]) vs ¬bull (n 1 765, −2,67%) — chỉ báo cáo; dấu theo regime như P0A, không chọn.
3. **SL-convexity**: netproxy_7d BRK −1,66% đã gồm +0,61% từ SL 1h (lạc quan); netproxy KHÔNG SL (giữ hết T) −2,42% (T3 −4,77%).
   Bleed thuần âm cho short ⇒ kết luận NO-GO không phụ thuộc giả định SL. Funding BRK âm (−0,13%/7d: short TRẢ funding sau sập).

## Giới hạn
- maxFav/SL trên 1h closes = cận dưới squeeze; SL khớp đúng +10,2% (không slippage/gap) ⇒ netproxy lạc quan (vẫn âm).
- n BRK 2 175 nhưng chỉ ~362 ngày phân biệt, cụm mạnh ⇒ CI block-7d rộng (±3%); NO-GO đến từ điểm ước lượng ÂM, không do CI.
- Daily close UTC 23:59; entry tại close ngày phá đáy (không intraday) — cascade nội ngày có thể đã xong trước entry (R1 đo nhịp giờ).
- quoteVol từ cache Aerospike 1m (P0A); universe theo cache; coin < 31 ngày lịch sử không đo.

## Đề xuất amend cho pha sau (KHÔNG chạy)
- Hướng ngược (LONG sau BRK, giữ ≤3d) có bleed +4,5%/3d nhưng excess ≈ 0 ⇒ chỉ là beta hồi thị trường sau ngày sập; nếu mở phải
  pre-reg riêng với đối chứng long-ALL cùng ngày. Không thuộc phạm vi short.
- BRK∧bull (n 403) là lát dương duy nhất — n nhỏ, chọn sau khi thấy ⇒ chỉ có thể là pre-reg mới trên dữ liệu khác (2026 niêm phong).
- Theo PROGRAM_SHORT_V3: R3 NO-GO ⇒ không ghép làm gate cho R1.
