# RESULT_REGIME_GATE — gate scale regime-adaptive (BTC 30d) vs T170 / T100

Chay: 2026-09-14. Pre-reg: docs/PREREG_REGIME_GATE.md (commit 98963e9, TRUOC build/chay). Rule CO DINH, KHONG fit.
Dataset wfo_ds_x1_2021, config sim_dev_file_2021.properties, SIM_END_DATE=20251231, harness k_runarm.sh. KHONG 242, KHONG push,
HOLDOUT 2026 nguyen. Code: EntryGate (flag GATE_REGIME_ADAPTIVE default OFF) + RegimeSchedule + DumpBtcDaily; build mvn -o package,
128/128 test PASS.

## 1. CONG PARITY — TAT CA PASS (byte-identical)
Regime tu BTC daily close (symId=1, kaggle_data_hpo, causal C[D-1]/C[D-31]-1; UP>0 else NOT-UP), file regime_daily_x1_2021.csv
(1675 ngay). Scale UP=1.00, NOT-UP=1.70 (= T100/T170, hang so pre-reg).

| cong | tag | flag | scale | md5 printDone (n) | ky vong | ket qua |
|---|---|---|---|---|---|---|
| (a) OFF const | RG_A_T170 | OFF | 1.70 const | `efb793e2...` (1089) | = T170 | **PASS** |
| (a) OFF const | RG_A_T100 | OFF | 1.00 const | `dc16e4da...` (2559) | = T100 | **PASS** |
| (b) cuc NOT-UP | RG_B_NOTUP | ON force=NOTUP | 1.70 const | `efb793e2...` (1089) | = T170 | **PASS** |
| (b) cuc UP | RG_B_UP | ON force=UP | 1.00 const | `dc16e4da...` (2559) | = T100 | **PASS** |

=> flag OFF khong pha code cu (byte-identical ca T170 lan T100); wiring regime dung o 2 cuc (force UP=T100, force NOT-UP=T170).

## 2. REGIME_ADAPTIVE — bang chinh (wfo_ds_x1_2021, 2021-07..2025-12)
md5 RG_ADAPTIVE = `38eef4cd6c0c07c1883b1ef0fe2dbe25` (n=1810, KHAC ca 2 baseline => tron regime that).

| tag | n | win% | TSloss% | meanP | mMargin | maxDD% | UW(ngay) | equity | CAGR% |
|---|---|---|---|---|---|---|---|---|---|
| T100 (RG_A_T100) | 2559 | 84.33 | 15.36 | 3.17 | 1983 | -16.13 | 248 | 121,770 | 31.94 |
| **REGIME** | 1810 | 85.41 | 13.70 | 4.13 | 2050 | **-9.74** | 189 | 116,832 | 30.73 |
| T170 (RG_A_T170) | 1089 | 88.25 | 9.73 | 5.24 | 1851 | -11.84 | 92 | 111,070 | 29.27 |

REGIME nam GIUA: n 1810 (T170 1089 < REGIME < T100 2559); CAGR 30.73 (T170 29.27 < REGIME < T100 31.94); maxDD -9.74 = THAP NHAT
ca 3; UW 189 (T170 92 < REGIME < T100 248).

## 3. CI + rang buoc cung (k=1, 1 config)
**d CAGR (block-bootstrap equity, CHI BAO CAO):**
- vs T170: d = **+1.46pp**, CI95 [-8.12, +11.62], sd_boot 5.01, P(d>0)=0.59 => **CI OM 0**, khong phan biet duoc voi 0.
- vs T100: d = -1.21pp, CI95 [-9.67, +7.50], P(d>0)=0.37 => CI om 0.

**Rate CI khoi-72h x1.21 (T170 - REGIME, toan cua so):** win% +2.83 [0.55,5.60] YES, TSloss% -3.97 [-6.64,-1.49] YES,
meanP +1.12 [0.29,2.05] YES => **T170 TOT hon ro o 3 rate chat luong** (regime nap lai lenh marginal luc UP => pha loang chat luong).
(vs T100: 0 rate ngoai CI => chat luong REGIME ≈ T100.)

**Rang buoc cung tung nam (maxDD<=15, UW<=120, nam>=0, quy>=-5):**
- REGIME: **FAIL** — vi pham UW=189 (>120). (maxDD -9.74 OK, nam>=0 OK, qmin -2.7 OK.)
- T170: **PASS**. T100: FAIL (maxDD -16.13 va UW=248).

## 4. Phan bo regime + return theo quy
- %ngay (≈ %tick, moi ngay ~1440 phut) trong cua so sim: **UP 52.5% / NOT-UP 47.5%**.
- Theo nam UP%: 2021 51.6, 2022 34.2 (bear=>1.70 chu dao), 2023 66.6, 2024 64.2 (bull=>1.00 chu dao), 2025 45.5. Khop macro.
- Return quy (REGIME vs T170) noi bat: 2024Q4 +22.3 vs +11.1; 2023Q1 +6.1 vs -0.4; 2023Q4 +13.2 vs +10.1 (uptrend thu them);
  NHUNG 2025Q2 -2.0 vs +1.6, 2025Q3 -2.7 vs +1.3, 2025Q4 +6.2 vs +12.6 (chop/late 2025 REGIME thua T170).

## 5. VERDICT — KHONG "best of both" => GIU T170
- CAGR REGIME +1.46pp vs T170 nhung **CI om 0** (sd_boot ~5pp): KHONG phan biet duoc — dung ky vong CI_REAUDIT (DEV khong tach duoc
  thay doi CAGR vai pp). Khong dat dieu kien "CAGR CAO hon ro".
- Rui ro so voi T170: maxDD tot hon (-9.74 vs -11.84) NHUNG **UW xau hon nhieu (189 vs 92) va VI PHAM tran cung 120** (T170 qua).
  Chat luong lenh pha loang ro (win/TSloss/meanP deu thua T170, ngoai CI). => KHONG dat "rui ro KHONG xau hon T170".
- So voi T100: REGIME rui ro thap hon ro (maxDD -9.74 vs -16.13; UW 189 vs 248) nhung CAGR thap hon (-1.21pp). La "T100 giam rui ro",
  KHONG vuot T170.
- **Ket luan: khong best-of-both. Uptrend upper-bound trong analysis (giu ~+31.8k) KHONG hien thuc hoa sau khi khoa rule** — gate la
  STATEFUL (noi gate luc UP => nap lai lenh marginal, keo dai UW, pha loang chat luong) chu khong phai loc sach cong pnl uptrend.
  Theo luat pre-reg (best-of-both HOAC NULL) => NULL o tang CAGR + rui ro UW xau hon => **GIU T170** (incumbent).

## 6. CAVEAT HAU KIEM (bang chung YEU)
Rule regime sinh tu hau kiem tren CHINH cua so DEV nay (analysis 8878a96). Tham so DA CO DINH truoc khi chay (nguong 0, scale
1.00/1.70, khong fit) nen DEV la test HOP LE cua rule da khoa, NHUNG viec CHON tin hieu BTC-30d la hau kiem => bang chung YEU
(winner's-curse residual). Ket qua DEV am tinh nay cang cung co: khong tune de "cuu". Xac nhan that (neu muon) = forward/holdout 2026
sau nay — KHONG mo trong bai nay. KHONG doi production, KHONG tune scale/nguong theo ket qua.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
