# RESULT: SWEEP SL TUY BIEN THEO RANK (3 LEVER A/B/C) — DEV MO RONG 2021

Thuc thi pre-reg docs/PREREG_SL_ADAPTIVE_SWEEP.md (commit 17df19d). Repo branch `module`.
Baseline X1_C3_FULL_2021: profile `x1_c3_full.properties`, config `sim_dev_file_2021.properties`,
env WFO_DATA_DIR=/home/ubuntu/wfo_ds_x1_2021 SIM_END_DATE=20251231; printDone md5 dc16e4da, n=2559.
Harness: /home/ubuntu/x1log2021/sladapt/driver.sh. Cham: score_wrap.py (x1_rates, CI_INFLATE=1.48 k=3).

## 1. PARITY (cong a) + mvn test (cong b)
- Jar moi, TAT CA flag OFF (profile x1_c3_full 19 key) => printDone md5 =
  dc16e4da6ff6cb7b8d41c592bc3d9c45 = baseline. PARITY_GATE=PASS. n_PREARM_SL=0.
- mvn -o package (bo clean): 21 class, 133 test, 0 fail, 0 error (PreArmSlTest 7/7). PASS.
=> Ca 3 lever khi OFF byte-identical baseline. Khong lever nao pha parity.

## 2. BANG CHINH (toan cua so 2021-07 -> 2025-12)
| variant | n | win% | TSloss% | mP\|SM | mP\|SL | meanP | maxDD% | UW | equity | CAGR% | md5 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 2559 | 84.33 | 15.36 | 7.230 | -19.189 | 3.173 | -16.13 | 248 | 121770 | 31.94 | dc16e4da |
| B TSTOP | 2577 | 82.62 | 17.97 | 7.241 | -14.982 | 3.248 | -11.50 | 223 | 143464 | 36.84 | da5d3180 |
| A HARDSL | 3144 | 70.52 | 29.07 | 6.906 | -11.153 | 1.656 | -17.53 | 302 | 96024 | 25.15 | a085f224 |
| C ARM | 2559 | 84.33 | 15.36 | 7.230 | -19.189 | 3.173 | -16.13 | 248 | 121770 | 31.94 | dc16e4da |

B: n_PREARM_SL=0 (khong dung nhanh A). A: n_PREARM_SL=723 (hard-cut -8% fired). C: byte-identical.

## 3. CI k=3 (variant - baseline, block-72h x1.48) — TOAN CUA SO
Rate chat luong = win%, TSloss%, mP|SM, mP|SL, meanP (bo n, mMargin). Huong TOT:
win% cao, TSloss% thap, mP|SM cao, mP|SL cao (loss it nong), meanP cao.

### B (SL_ADAPT_TSTOP)
- win%   -1.714 [-3.042, -0.309] YES (XAU)
- TSloss% +2.609 [ 1.418,  3.847] YES (XAU)
- mP|SL  +4.207 [ 1.339,  7.170] YES (TOT)
- mP|SM +0.011, meanP +0.076 : TRONG CI.
=> 3 rate ngoai CI nhung HON HOP HUONG (2 XAU + 1 TOT). KHONG dat ">=2 cung huong TOT".

### A (SL_ADAPT_HARDSL)
- win%   -13.815 [-17.057, -10.174] YES (XAU)
- TSloss% +13.714 [  9.543,  17.781] YES (XAU)
- meanP   -1.517 [ -3.050,  -0.129] YES (XAU)
- mP|SL   +8.035 [  4.414,  11.852] YES (TOT)
- mP|SM: TRONG CI.
=> 4 rate ngoai CI, 3 XAU. Lever HAI ro rang.

### C (SL_ADAPT_ARM)
- 0 rate ngoai CI (byte-identical baseline). NO-OP.

## 4. RANG BUOC CUNG (per nam) — maxDD<=15, UW<=120, nam>=0, quy>=-5
- BASELINE tu no da FAIL: 2024 (UW 121, quy -4.64), 2025 (UW 227). => "PASS hard constraints" KHONG
  thoa man cho bat ky variant (moc so sanh khong pass). maxDD toan cuc baseline -16.13 (>15) cung FAIL.
- B: toan cuc maxDD -11.50 (tot hon -16.13), UW 223 (tot hon 248); nhung per-nam van FAIL 2022 (UW132),
  2024 (UW136, quy -5.38), 2025 (UW223). 2021 cai thien (12.0% vs 9.3%).
- A: xau hon — 2025 maxDD -17.53, 2024 quy -6.58. FAIL nang hon.
- C: = baseline.

## 5. VERDICT tung lever (theo LUAT PRE-REG: >=2 rate cung huong TOT ngoai CI + PASS hard)
- B (TSTOP): **NULL theo luat** (chi 1 rate cung huong TOT ngoai CI: mP|SL; hard khong pass).
  NHUNG bang chung phu MANH & nhat quan huong lever nham (collapse-risk):
  CAGR 36.84 vs 31.94 (+4.90pp), equity +18% (143k vs 121k), maxDD -11.50 vs -16.13,
  UW 223 vs 248, mP|SL -14.98 vs -19.19 (cat loser chua-arm som => loss it nong).
  Cost la win% -1.7 / TSloss% +2.6 — CO HOC: zombie chua arm bi hien thuc hoa thanh loss NHO
  (chuyen "giu lo am tham" -> "loss realized nho" + giai phong budget compound). Trade-off
  risk/return favorable tren dung cac metric ma lever nham.
- A (HARDSL): **NULL / HAI**. Cat -8% coin yeu bien loser-hoi-phuc thanh loss chac -8%:
  win% -14pp, meanP -1.5, CAGR -6.8pp, maxDD xau hon. Bo.
- C (ARM): **NULL cau truc (no-op)**. Cong tai Sim:708 chi la short-circuit "co consult trailing khong";
  arm THAT nam trong updateStatusNew (`rateLoss > rateMin2MoveSl`, rateMin tu RATE_PROFIT_STOP_MARKET
  base). Ha cong NGOAI (0.07->0.03/0.05) khong doi diem arm => byte-identical. Recon da chi sai diem.

## 6. LEVER DANG THEO TIEP
**B (adaptive TIME-STOP theo rank)** — la lever duy nhat co tin hieu that (cai thien CAGR/maxDD/UW/mP|SL).
Follow-up (pre-reg RIENG, khong lam phien nay):
1. Tach adaptive-vs-fixed: chay FIXED (WEAK-hours ap cho MOI rank) vs rank-adaptive, de co lap dong gop
   RIENG cua chia-rank (pre-reg goc da caveat dieu nay).
2. Sweep WEAK hours (96h/120h) — 72h co the cat hoi manh (win% -1.7); tim diem toi uu risk/return.
3. Neu muon test lever C that su: sua nguong arm TRONG updateStatusNew (rateMin2MoveSl) theo rank —
   plumbing sau hon, khong con exit-only.

## 7. LUAT CUNG DA GIU
Chi Oracle. KHONG cham 242, KHONG git push, KHONG tune (dung dung tham so pre-reg muc 2),
holdout 2026 nguyen (khong dong). Parity PASS nen khong dung giua chung.
Baseline devrun X1_C3_FULL_2021 KHONG bi ghi de (parity chay tag rieng X1_SLADAPT_PARITY).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
