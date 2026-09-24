# RESULT: B FOLLOW-UP — TIME-STOP ADAPTIVE THEO RANK (adaptive-vs-fixed + sweep WEAK hours)

Thuc thi pre-reg docs/prereg/PREREG_B_FOLLOWUP.md (commit e16415d). Repo branch `module`.
BASELINE = **T170** = X1_GS_T170_2021: profile `profiles/x1_gs_t170.properties` (gate 1.70,
LOSER_TIME_STOP phang 168h), config `configs/sim_dev_file_2021.properties`, env
WFO_DATA_DIR=/home/ubuntu/wfo_ds_x1_2021 WFO_SMART_CACHE=1 SIM_END_DATE=20251231, TIME_RUN=20210701.
printDone md5 efb793e2, n=1089. Harness `/home/ubuntu/x1log2021/bfu/driver.sh`.
Cham: score_wrap.py (x1_rates, CI_INFLATE=1.48 k=3). Variant vs X1_GS_T170_2021.

## 1. PARITY (cong a) — PASS
Current jar (HEAD 42a5f08) + x1_gs_t170.properties (SL_ADAPT_TSTOP OFF) => printDone md5 =
efb793e2468ca3a7318da0f0ad23d4fc = baseline T170 BYTE-IDENTICAL (b:111070). PARITY_GATE=PASS.
=> 3 variant chay CUNG jar voi baseline (so sanh hop le). Jar da co SL_ADAPT_TSTOP (khong rebuild).
Rank split hoat dong: nhanh trailing STRONG~744/WEAK~77 (selRank active).

## 2. BANG CHINH (toan cua so 2021-07 -> 2025-12)
| variant | n | win% | TSloss% | mP\|SM | mP\|SL | meanP | maxDD% | UW | equity | CAGR% | md5 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T170 (baseline) | 1089 | 88.25 | 9.73 | 7.642 | -16.992 | 5.244 | -11.84 | 92 | 111070 | 29.27 | efb793e2 |
| V1 adaptive-96 (WEAK96/STR168) | 1093 | 87.01 | 11.07 | 7.585 | -15.459 | 5.034 | -11.84 | 122 | 105547 | 27.81 | 8e713ac5 |
| V2 adaptive-120 (WEAK120/STR168) | 1093 | 87.74 | 10.25 | 7.599 | -16.454 | 5.134 | -11.85 | 121 | 109436 | 28.84 | 82997fcc |
| V3 fixed-96 (all 96h, khong rank) | 1095 | 86.12 | 11.96 | 7.557 | -14.075 | 4.969 | -11.84 | 151 | 103076 | 27.14 | 56a2ba7b |

Co che dung nhu thiet ke: cat WEAK-loser chua-arm som => mP|SL bot nong (-16.99 -> -15.46 V1 / -14.08 V3)
NHUNG win% giam + TSloss% tang (winner-cho-hoi-phuc bi cat thanh loss). Cat cang som (96<120) / cang deu
(fixed) => hai cang nang.

## 3. CI k=3 (variant - baseline T170, block-72h x1.48) — TOAN CUA SO
Rate chat luong = win%, TSloss%, mP|SM, mP|SL, meanP. Huong TOT: win% cao, TSloss% thap, mP cao.

### V1 adaptive-96
- win%   -1.238 [-2.409, -0.081] YES (XAU)
- TSloss% +1.337 [ 0.130,  2.660] YES (XAU)
- mP|SL +1.533 [-1.465, 4.450], mP|SM -0.056, meanP -0.209 : TRONG CI.
=> 2 rate chat luong ngoai CI, CA HAI XAU. KHONG dat ">=2 cung huong TOT".

### V2 adaptive-120
- 0 rate chat luong ngoai CI (win% -0.506, TSloss% +0.513, meanP -0.110 deu trong CI). NO-OP chat luong.

### V3 fixed-96
- win%   -2.127 [-3.556, -0.771] YES (XAU)
- TSloss% +2.230 [ 0.804,  3.740] YES (XAU)
- mP|SL +2.917 [-0.813, 6.374], meanP -0.275 : TRONG CI.
=> 2 rate chat luong ngoai CI, CA HAI XAU — va TE HON V1 (win% -2.13 vs -1.24, TSloss% +2.23 vs +1.34).

## 4. RANG BUOC CUNG (maxDD<=15, UW<=120, nam>=0, quy>=-5) — baseline T170 PASS CA 5 NAM (UW max 92)
| variant | verdict | vi pham |
|---|---|---|
| T170 (baseline) | **PASS ca 5 nam** | UW max 92, qmin -0.9, maxDD -11.84 |
| V1 adaptive-96 | **FAIL** | UW=122 (>120) |
| V2 adaptive-120 | **FAIL** | UW=121 (>120) |
| V3 fixed-96 | **FAIL** | UW=151 (>120), qmin -4.1 |
Cat loser som keo UW DAI HON baseline (realize loss => equity duoi dinh lau hon): 92 -> 122/121/151.
CA 3 variant PHA hard constraint ma T170 dang giu => vi pham dieu kien "phai GIU pass".

## 5. DOC KET QUA (theo pre-reg muc 3)
1. **V1/V2 vs T170 — adaptive KHONG giup.** V1: 2 rate ngoai CI ca hai XAU + FAIL UW. V2: no-op chat luong
   + van FAIL UW (121). Khong variant nao dat luat WIN.
2. **Adaptivity vs fixed (V1 vs V3).** V3 (fixed 96h cho TAT CA) TE HON V1 (adaptive) tren MOI chieu:
   win% -2.13 vs -1.24, TSloss% +2.23 vs +1.34, UW 151 vs 122, equity 103076 vs 105547, mMargin -83 vs -53.
   => Adaptivity (chia rank, THA STRONG o 168h) chi lam GIAM THIET HAI so voi cat deu, KHONG tao loi.
   Phan "thang" cua adaptive so voi fixed = tranh cat nham STRONG; nhung ban than viec cat (WEAK) da hai
   tren T170. Adaptivity = it hai hon, khong phai co loi.
3. **WEAK hours: 120 it hai nhat > 96 > fixed-96.** Cat cang som cang hai. V2 (WEAK=120) gan baseline nhat
   (no-op chat luong, UW 121, CAGR 28.84 ~ 29.27) nhung van FAIL UW va van khong win.

## 6. VERDICT
- **Tat ca V1/V2/V3: NULL / HAI theo luat.** Khong variant nao co >=2 rate chat luong ngoai CI cung huong TOT;
  moi rate ngoai CI deu XAU; va CA 3 PHA hard constraint UW<=120 ma T170 dang giu.
- **T170 van la incumbent.** KHONG stack adaptive time-stop len T170.
- **Ly do co hoc (khop tin hieu B cu tren C3_FULL):** sweep SL_ADAPTIVE truoc thay B(TSTOP WEAK=72h) co tin hieu
  vi baseline do la C3_FULL gate 1.0 — gate LONG cho vao nhieu vi the collapse-risk ma time-stop don sau.
  T170 (gate 1.70) DA loc san chinh nhung vi the yeu do o CONG VAO => time-stop khong con gi tot de cat, chi
  con realize loss cua winner-cho-hoi-phuc => hai. Gate chat + time-stop som la HAI CO CHE THAY THE, khong bo tro;
  T170 da thu duoc loi ich collapse-risk qua gate.

## 7. LUAT CUNG DA GIU
Chi Oracle. KHONG cham 242, KHONG git push, KHONG tune (dung dung tham so pre-reg muc 4), holdout 2026 nguyen.
Parity PASS nen khong dung giua chung. Baseline devrun X1_GS_T170_2021 KHONG bi ghi de (parity tag rieng BFU_PARITY_T170).
1 box, chay tuan tu (khong song song).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
