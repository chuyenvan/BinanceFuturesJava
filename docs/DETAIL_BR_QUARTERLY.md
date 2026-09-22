# DETAIL_BR_QUARTERLY.md - Chi tiet BR vs T170 theo QUY va NAM (doc-only, khong chay sim)

Nguon: `storage/printDone.csv` + `logs/sim.out` cua 4 tag (`X1_GS_T170_2021`=T170, `X1_C3_FULL_2021`=T100/gate-1.0, `X1_C3_FULL_2021_REGIME_BR`=BR, `X1_C3_FULL_2021_REGIME_BR0`=BR0), tai dung `equity()`/`trades()` cua `research/analysis/c3_rates.py` (KHONG sua file goc). not_up% tu `/home/ubuntu/regime_work/regime_daily_breadth.csv`. n_eff_total/ICC lay tu `research/analysis/out/breadth_gate_metrics.json` (da tinh san o TASK B2 Buoc 6, xem `docs/RESULT_BREADTH_GATE_SIM.md`).

Quy uoc: **n** = so lenh MO trong ky (theo cot `start`); **PnL** = tong `profit` (USDT) cua cac lenh do; **return ky (%)** = equity_cuoi/equity_dau - 1 (equity_dau cua ky dau tien = equity goc 35,000); **maxDD trong ky** va **UW dai nhat trong ky** tinh CUC BO (cummax reset tai dau ky, giong phuong phap `uw_by_year` da dung trong `breadth_gate_metrics.py`), KHONG phai maxDD/UW toan cuc cat lat; **ROI/lenh (%)** = trung binh(`profit`/`margin`*100) tren cac lenh mo trong ky (co the bi keo boi vai lenh margin rat nho -- xem ghi chu o cuoi); **%not_up** = ty le ngay trong ky co `regime=NOTUP` (gate chat 1.70) theo CSV breadth.

---

## 1. Theo QUY (2021Q3 .. 2025Q4) - BR canh T170

| Quy | n BR | n T170 | PnL BR | PnL T170 | Return% BR | Return% T170 | Eq dau BR | Eq dau T170 | Eq cuoi BR | Eq cuoi T170 | maxDD% BR | maxDD% T170 | UW(ngay) BR | UW(ngay) T170 | WinRate% BR | WinRate% T170 | ROI/lenh% BR | ROI/lenh% T170 | %notup BR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021Q3 | 97 | 80 | 419 | 410 | 7.54 | 7.44 | 35,000 | 35,000 | 37,640 | 37,603 | -3.21 | -2.14 | 23 | 37 | 91.8 | 95.0 | 0.836 | 0.775 | 71.7 |
| 2021Q4 | 121 | 69 | -105 | 241 | -3.11 | 4.44 | 37,640 | 37,603 | 36,471 | 39,272 | -8.29 | -2.46 | 46 | 22 | 70.2 | 89.9 | -0.034 | 0.501 | 54.8 |
| 2022Q1 | 37 | 37 | 164 | 164 | 4.61 | 4.61 | 36,471 | 39,272 | 38,151 | 41,081 | -1.15 | -1.15 | 33 | 33 | 91.9 | 91.9 | 0.369 | 0.342 | 100.0 |
| 2022Q2 | 86 | 86 | 323 | 323 | 5.34 | 5.33 | 38,151 | 41,081 | 40,188 | 43,272 | -3.99 | -3.99 | 45 | 45 | 83.7 | 83.7 | 0.510 | 0.475 | 100.0 |
| 2022Q3 | 22 | 22 | 171 | 171 | 5.47 | 5.47 | 40,188 | 43,272 | 42,386 | 45,638 | -0.24 | -0.24 | 28 | 28 | 95.5 | 95.5 | 0.578 | 0.537 | 100.0 |
| 2022Q4 | 53 | 53 | 107 | 107 | 2.90 | 2.90 | 42,386 | 45,638 | 43,614 | 46,960 | -11.84 | -11.84 | 49 | 49 | 73.6 | 73.6 | 0.318 | 0.295 | 100.0 |
| 2023Q1 | 38 | 6 | 151 | -1 | 3.82 | -0.37 | 43,614 | 46,960 | 45,280 | 46,787 | -2.95 | -1.51 | 27 | 27 | 92.1 | 83.3 | 0.285 | 0.008 | 58.2 |
| 2023Q2 | 46 | 36 | 465 | 484 | 15.10 | 16.18 | 45,280 | 46,787 | 52,118 | 54,357 | -3.15 | -2.73 | 63 | 63 | 76.1 | 80.6 | 0.649 | 0.826 | 70.7 |
| 2023Q3 | 30 | 30 | 225 | 225 | 5.92 | 5.92 | 52,118 | 54,357 | 55,202 | 57,573 | -1.06 | -1.07 | 41 | 41 | 86.7 | 86.7 | 0.547 | 0.525 | 100.0 |
| 2023Q4 | 82 | 54 | 507 | 309 | 16.15 | 10.08 | 55,202 | 57,573 | 64,116 | 63,378 | -1.22 | -0.62 | 11 | 9 | 95.1 | 94.4 | 0.323 | 0.281 | 35.5 |
| 2024Q1 | 184 | 88 | 785 | 428 | 15.75 | 11.31 | 64,116 | 63,378 | 74,215 | 70,548 | -2.78 | -0.96 | 33 | 45 | 88.6 | 94.3 | 0.267 | 0.260 | 0.0 |
| 2024Q2 | 120 | 73 | 87 | 120 | -5.55 | -0.92 | 74,215 | 70,548 | 70,098 | 69,900 | -11.36 | -6.60 | 82 | 82 | 77.5 | 80.8 | 0.307 | 0.214 | 71.7 |
| 2024Q3 | 55 | 55 | 410 | 410 | 7.78 | 7.78 | 70,098 | 69,900 | 75,550 | 75,337 | -1.20 | -1.20 | 26 | 26 | 90.9 | 90.9 | 0.618 | 0.620 | 100.0 |
| 2024Q4 | 193 | 65 | 997 | 382 | 23.20 | 11.09 | 75,550 | 75,337 | 93,076 | 83,695 | -3.08 | -0.58 | 17 | 17 | 90.7 | 93.8 | 0.274 | 0.245 | 48.4 |
| 2025Q1 | 157 | 116 | 533 | 541 | 12.06 | 14.62 | 93,076 | 83,695 | 104,305 | 95,934 | -2.97 | -2.37 | 28 | 28 | 86.6 | 91.4 | 0.163 | 0.198 | 62.6 |
| 2025Q2 | 10 | 10 | 56 | 56 | 1.57 | 1.57 | 104,305 | 95,934 | 105,943 | 97,440 | -0.99 | -0.99 | 4 | 4 | 90.0 | 90.0 | 0.185 | 0.201 | 100.0 |
| 2025Q3 | 46 | 20 | 23 | 59 | -0.36 | 1.27 | 105,943 | 97,440 | 105,566 | 98,676 | -3.46 | -1.14 | 46 | 5 | 80.4 | 85.0 | 0.020 | 0.105 | 38.7 |
| 2025Q4 | 205 | 189 | 1,546 | 1,282 | 8.38 | 12.56 | 105,566 | 98,676 | 114,410 | 111,070 | -4.24 | -4.23 | 52 | 52 | 83.9 | 85.2 | 1.027 | 0.664 | 89.2 |

---

## 2. Theo NAM (2021-2025) - BR canh T170

| Nam | n BR | n T170 | PnL BR | PnL T170 | Return% BR | Return% T170 | CAGR% BR | CAGR% T170 | Eq dau BR | Eq dau T170 | Eq cuoi BR | Eq cuoi T170 | maxDD% BR | maxDD% T170 | UW(ngay) BR | UW(ngay) T170 | quy-min% BR | quy-min% T170 | WinRate% BR | WinRate% T170 | ROI/lenh% BR | ROI/lenh% T170 | %notup BR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 218 | 149 | 314 | 651 | 4.20 | 12.21 | 8.56 | 25.84 | 35,000 | 35,000 | 36,471 | 39,272 | -8.29 | -2.46 | 46 | 37 | -3.11 | 4.44 | 79.8 | 92.6 | 0.353 | 0.648 | 63.0 |
| 2022 | 198 | 198 | 764 | 764 | 19.59 | 19.58 | 19.60 | 19.59 | 36,471 | 39,272 | 43,614 | 46,960 | -11.84 | -11.84 | 72 | 72 | -3.11 | 2.90 | 83.8 | 83.8 | 0.440 | 0.409 | 100.0 |
| 2023 | 196 | 126 | 1,349 | 1,017 | 47.01 | 34.96 | 47.05 | 34.99 | 43,614 | 46,960 | 64,116 | 63,378 | -3.15 | -2.73 | 63 | 63 | 2.90 | -0.37 | 88.8 | 88.1 | 0.426 | 0.482 | 66.1 |
| 2024 | 552 | 281 | 2,279 | 1,340 | 45.17 | 32.06 | 45.06 | 31.98 | 64,116 | 63,378 | 93,076 | 83,695 | -11.36 | -6.60 | 121 | 92 | -5.55 | -0.92 | 87.1 | 90.0 | 0.313 | 0.315 | 55.0 |
| 2025 | 418 | 335 | 2,158 | 1,938 | 22.92 | 32.71 | 22.94 | 32.73 | 93,076 | 83,695 | 114,410 | 111,070 | -5.76 | -4.23 | 58 | 52 | -0.36 | 1.27 | 84.7 | 87.5 | 0.572 | 0.455 | 72.7 |

Doi chieu voi bang CAGR-theo-nam va UW-theo-nam da cong bo o `docs/RESULT_BREADTH_GATE_SIM.md` muc 1 (yr/uw_by_year trong `breadth_gate_metrics.json`): return%-nam cua BR/T170 o bang tren KHOP tuyet doi voi cot `yr` (vd BR 2023=47.00784%, T170 2023=34.96167%), va UW(ngay) KHOP tuyet doi voi `uw_by_year` (vd BR 2025=58, T170 2025=52). CAGR% o bang tren la CAGR ANNUALIZED rieng cho tung nam/nam-le (khac voi cot return% thuan tuy va khac voi cot 'CAGR theo nam' trong RESULT_BREADTH_GATE_SIM.md -- cot do thuc chat la return% khong-annualize, xem dinh nghia `r['yr']` trong `c3_rates.py::stats()`).

---

## 3. Toan ky (2021-07-01 .. 2025-12-31) - BR / T170 / BR0 / T100(gate-1.0)

| Tag | n | PnL(USDT) | Equity cuoi | CAGR% | maxDD% | UW(ngay) | WinRate% | ROI/lenh% | %notup | n_eff_total | ICC(ROI,ngay) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BR (`X1_C3_FULL_2021_REGIME_BR`) | 1582 | 6,863 | 114,410 | 30.12 | -11.84 | 180 | 85.3 | 0.417 | 72.3 | 741.83 | 0.083 |
| T170 (`X1_GS_T170_2021`) | 1089 | 5,710 | 111,070 | 29.27 | -11.84 | 92 | 88.2 | 0.440 | 72.3 | 606.26 | 0.052 |
| BR0 (`X1_C3_FULL_2021_REGIME_BR0`) | 1429 | 6,103 | 114,416 | 30.12 | -13.22 | 221 | 86.4 | 0.393 | 72.3 | 641.19 | 0.092 |
| T100/gate-1.0 (`X1_C3_FULL_2021`) | 2559 | 8,119 | 121,770 | 31.94 | -16.13 | 248 | 84.3 | 1.123 | 72.3 | 1103.86 | 0.102 |

Doi chieu: n/CAGR%/maxDD%/UW(ngay)/n_eff_total/ICC o bang tren KHOP tuyet doi voi bang chinh muc 1 cua `docs/RESULT_BREADTH_GATE_SIM.md` va `research/analysis/out/breadth_gate_metrics.json` (vd BR: n=1582 CAGR=30.1229% maxDD=-11.8420% UW=180 n_eff_total=741.8332 ICC=0.0827; T170: n=1089 CAGR=29.2687% maxDD=-11.8443% UW=92 n_eff_total=606.2555 ICC=0.0516).

---

## 4. Ghi chu ky thuat

- **maxDD% va UW(ngay) 'trong ky'** (quy/nam) tinh CUC BO trong pham vi ky do (cummax equity reset tai ngay dau ky), khac voi maxDD%/UW toan cuc (cat lat tu dinh toan cuc) -- vi du maxDD 2022Q4 cua T170/BR = -11.84% (= dung dinh toan cuc 2022-10-17 roi vao quy nay) trong khi maxDD toan ky cung la -11.84%, trung hop vi day chinh la diem sau toan cuc.
- **ROI/lenh% trung binh** mot so ky co gia tri rat lon bat thuong (vd T100 2022Q2 ~9.40%, nam 2022 ~5.36%) do bi keo boi mot vai lenh co `margin` rat nho so voi `profit` (ty le profit/margin bi khuech dai) -- day la dac diem cua PHEP TINH trung binh don gian (khong weighted theo margin), khong phai loi tinh toan; can doc voi luu y nay, KHONG dung lam chi so chinh de so sanh neu khong loai outlier.
- **quy-min% (muc nam)** = min cua 4 (hoac it hon, voi nam le) gia tri return%-quy trong nam do, dung dung dinh nghia 'qmin' trong `c3_rates.py::stats()`.
- **%not_up** doc tu `/home/ubuntu/regime_work/regime_daily_breadth.csv` (cot `regime`), gioi han cua so `[2021-07-01, 2025-12-31]` cho moi ky con -- day la dac diem CUA THI TRUONG (khong phu thuoc tag), nen giong nhau giua BR va T170/T100/BR0 trong cung mot ky; chi anh huong THUC SU den BR (T170/T100/BR0 khong doc gate nay khi sim).
- Toan bo so lieu ky tinh READ-ONLY tu du lieu sim da chay san o TASK B2 Buoc 6 (`docs/RESULT_BREADTH_GATE_SIM.md`), KHONG chay lai sim/engine nao trong buoc nay.

---
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
