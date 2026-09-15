# RESULT_DEV2021_READJUDICATE — phan xu lai T170/T130 (GD92 blocked) tren DEV mo rong ve 2021

Pre-reg: `docs/PREREG_DEV2021_READJUDICATE.md` (commit e57fd3d, chot TRUOC khi chay sim).
Nen: DEV mo rong 18 fold (2021Q3..2025Q4), dataset `wfo_ds_x1_2021`, bins `predwf_map_s1a2_x1_2021`,
TICKER_SOURCE=file, jar HEAD 8dd10ae (KHONG rebuild). SIM_END_DATE=20251231, holdout 2026 nguyen ven.
KHONG cham 242, KHONG tune, KHONG push, KHONG doi code.

## 0. Phan quyet (so truoc)
- **T170 (scale 1.70): THANG** (luat cu = >=2 rate CHAT LUONG ngoai CI cung huong TOT + PASS rang buoc cung).
  2 rate ngoai CI DEU TOT: TSloss% -5.62 [-9.62,-1.43], meanP +2.07 [+0.07,+3.98]; PASS rang buoc cung
  CA 5 NAM tuyet doi (baseline FAIL 2024/2025). Danh doi CAGR -2.67pp (KHONG phai tieu chi).
- **T130 (scale 1.30): NULL.** Chi 1 rate ngoai CI (TSloss% -1.88); FAIL rang buoc cung (2024 qmin -5.63,
  2025 maxDD -18.34 / UW 221).
- **GD92 (rolling 0.92/90d): BLOCKED — khong chay.** Co che GateRollingThreshold + SIM_GATE_ROLLING_PCT/DAYS
  bi XOA o commit f1c43a3 (L7); profile -> profiles/archive/. Chay = khoi phuc code + rebuild = ngoai pham vi.
- Multiplicity k = so variant chay = 2. sqrt(2 ln 2)=1.177 < 1.21 (CI block-72h da dung) => khong noi rong them.

## 1. Tich hop fold 2021 — cong PASS het
- S1 2021 rank (x1_s1_rank.py, X1_CUTS="20210701 20211001", seed42 CPU/hist, shuffle tat):
  fold cut20210701 edge5 +8.39% (oos 56015/489 tick), cut20211001 +6.62% (oos 56033/445),
  overall edge5 +7.55% t=22.1 (nguong +6.0; G015 base +4.55) => S1 2021 co edge that.
- Mapped bins 2021 (x1_build_map.py): predict_wf_20210701.bin (rec 999162), predict_wf_20211001.bin
  (rec 1104563); ty le "co score" 0.053 = mat do ledger OOS (khong degenerate).
- Bins dir mo rong = 16 bins cu COPY (sha256 khop 16/16) + 2 bins 2021 = 18 bins.
  ts-range 18 bin ROI NHAU (disjoint) + moi span<=92d < 100d. Bins 2021 lap kin 2021Q3/Q4, khong overlap 20220101.
- Dataset wfo_ds_x1_2021: foldCount=18, leakFreeFrom=2021-07-01, marketRange 2021-01-01..2025-12-31.
  md5_pred KHONG doi (5dd6bb4c); md5_market doi (4ab691.. vs d89ccabb..) NHUNG chi do backfill 2021
  (xac nhan o cong sanity duoi: 2022+ byte-identical).

## 2. Baseline mo rong + CONG SANITY 2022+ (PASS)
- **Control** X1_C3_FULL_2021CTRL (TIME_RUN=20220101 tren wfo_ds_x1_2021) = printDone md5
  **2478e90d** = **X1_C3_FULL_PARITY_R BYTE-IDENTICAL** (n=2266, equity 111428). => 2022+ cua dataset mo rong
  y het dataset cu; md5_market doi chi anh huong VUNG 2021.
- **Baseline mo rong** X1_C3_FULL_2021 (TIME_RUN=20210701): n=**2559** (=293 lenh 2021 + 2266 lenh 2022+),
  equity 121770, CAGR 31.94, n_eff=203 (vs C3_FULL cu ~93 => ~2.2x block, CI hep ~1.48x = power that).
- **CONG SANITY**: tap (symbol, entry_time, exit_reason) cua baseline mo rong phan entry>=2022-01-01
  = **100.00% trung** control/PARITY_R (2266/2266, 0 lech). => fold 2021 KHONG pha 2022+ (chinh xac tuyet doi).

## 3. Bang chinh (equity/CAGR KHONG phai tieu chi)
| tag | scale | n | win% | TSloss% | meanP | mMargin | maxDD% | UW | equity | CAGR% |
|---|---|---|---|---|---|---|---|---|---|---|
| X1_C3_FULL_2021 (baseline) | 1.00 | 2559 | 84.33 | 15.36 | 3.173 | 1983 | -16.13 | 248 | 121770 | 31.94 |
| X1_GS_T170_2021 | 1.70 | 1089 | 88.25 | 9.73 | 5.244 | 1851 | -11.84 | 92 | 111070 | 29.27 |
| X1_GS_T130_2021 | 1.30 | 1580 | 85.57 | 13.48 | 3.755 | 1813 | -18.34 | 221 | 92616 | 24.15 |

## 4. CI khoi-72h x1.21 toan cua so mo rong (variant - baseline)
### T170 (n_A=1089 n_B=2559) — 2 rate CHAT LUONG ngoai CI, DEU TOT
| rate | hieu | lo | hi | ngoaiCI |
|---|---|---|---|---|
| win% | +3.916 | -0.059 | +8.074 | - (bien) |
| TSloss% | -5.624 | -9.622 | -1.429 | **YES (tot)** |
| mP\|SL | +2.197 | -2.181 | +6.715 | - |
| meanP | +2.071 | +0.067 | +3.983 | **YES (tot)** |
=> 2 rate ngoai CI (TSloss% giam, meanP tang) — CUNG HUONG TOT. Ghi chu: o run 48 thang cu
(RESULT_GATESCALE) T170 cung co 2 rate nay ngoai CI => tin hieu BEN voi power moi (khong phai nhieu mau nho).

### T130 (n_A=1580 n_B=2559) — 1 rate ngoai CI
| rate | hieu | lo | hi | ngoaiCI |
|---|---|---|---|---|
| win% | +1.240 | -0.352 | +2.856 | - |
| TSloss% | -1.877 | -3.547 | -0.046 | **YES (tot)** |
| meanP | +0.582 | -0.046 | +1.186 | - (bien) |
=> chi 1 rate ngoai CI. Power moi day T130 tu 0 rate (48 thang cu) -> 1 rate, nhung van < 2.

## 5. Rang buoc cung tung nam (maxDD<=15, UW<=120, nam>=0, quy>=-5) — tuyet doi
| tag | 2021 | 2022 | 2023 | 2024 | 2025 | verdict |
|---|---|---|---|---|---|---|
| baseline | PASS | PASS | PASS | FAIL(UW121) | FAIL(UW227) | FAIL (incumbent tu vi pham) |
| **T170** | PASS | PASS | PASS | PASS | PASS | **PASS ca 5 nam** (maxDD max -11.84, UW max 92, qmin -0.92) |
| T130 | PASS | PASS(DD-13.1) | PASS | FAIL(qmin-5.63) | FAIL(DD-18.34/UW221) | FAIL |

## 6. PHAN QUYET
- **T170: THANG.** >=2 rate CHAT LUONG ngoai CI cung huong TOT (TSloss%, meanP) + PASS rang buoc cung
  CA 5 NAM tuyet doi. Day la WIN ve CHAT LUONG + RUI RO (UW 92 vs 248, maxDD -11.84 vs -16.13), danh doi
  CAGR -2.67pp (KHONG phai tieu chi; cung chieu ~-3.9pp cua run 48 thang cu). Power 2021 XAC NHAN tin hieu
  ben (2 rate ton tai ca hai run) => KHONG phai artefact mau nho.
- **T130: NULL.** 1 rate ngoai CI (<2) + FAIL rang buoc cung.
- **GD92: BLOCKED** (co che rolling da xoa khoi code o f1c43a3; khong khoi phuc/rebuild theo luat cung).

## 7. Ghi chu van hanh + tai lap
- Artifact giu: `predwf_map_s1a2_x1_2021/` (18 bins), `wfo_ds_x1_2021/` (foldCount=18), ledger
  `pred_s1a2x1_y21.parquet`, devrun `X1_C3_FULL_2021{,CTRL}`, `X1_GS_T170_2021`, `X1_GS_T130_2021`.
  Profile build tam: `profiles/x1_c3_2021build.properties`, config `configs/sim_dev_file_2021.properties`
  (chi doi WFO_FUNDING_PRED_DIR / TIME_RUN=20210701 — KHONG tune).
- md5 printDone: baseline `dc16e4da`, control `2478e90d`(=PARITY_R), T170 `efb793e2`, T130 `68510567`.
- Cham: `python3 research/analysis/x1_rates.py X1_C3_FULL_2021 <variant>`.
- KHONG cham 242 / holdout 2026, KHONG deploy, KHONG git push, KHONG doi code/rebuild.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT

> **AUDIT 2026-09-15**: cham lai vong nay bang he so CI dung (`sqrt(2 ln k)`, k=2 da pre-reg = 1.177
> thay vi hang so 1.21) — xem `docs/AUDIT_READJUDICATE_CI_RESCORE.md`. Ket qua: T170 co **3** rate chat
> luong ngoai CI (tang tu 2), phan quyet THANG **dung vung va manh hon**; T130 van NULL. Khong dao nguoc gi.
