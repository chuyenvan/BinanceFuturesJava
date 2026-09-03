# CI_REAUDIT — do lai do tin cay THAT cua cac verdict cu

Ngay: 2026-09-03. Pham vi: **CHI DEV**. Khong cham VALIDATION (2024-07-15..2025-12-31),
khong cham HOLDOUT 2026. Khong chay java, khong backtest, khong train.

Phuong phap: **`docs/PREREG_CI.md`, commit `2493eca`** — chot **TRUOC** khi tinh CI nao.
Script: `research/analysis/ci_group_a.py`, `ci_group_a_extra.py`, `ci_group_b.py`,
`ci_group_b_h3.py`, `ci_group_b_neff.py` (ban chay: `/home/ubuntu/ci/*.py`,
output `/home/ubuntu/ci/*.out`).

Nguon cua van de: `docs/LEAK_L1_REPORT.md` — grid mau 15m + nhan cua so 72h => n hieu dung tren
DEV la **302 khoi 72h**, khong phai 15,442,092 dong; CI that cua spearman G015 rong hon CI naive
**74 lan**. Diem uoc luong khong doi. Bao cao nay ap dung cung logic do cho **tang equity**
(911 ngay DEV khong phai 911 quan sat doc lap) va cho **cac phep so hai model**.

## Tai lap diem uoc luong TRUOC khi lam gi khac (PREREG_CI section 6 buoc 3)

| So cu | Nguon so cu | Tai lap duoc | Khop? |
|---|---|---|---|
| C2b b:60390 / C2_g015 51903 / H1a 60953 / N4 61148 / RND1 60003 / RND2 59846 | AUDIT_APPLIED, RUNS_DEV | 60390 / 51903 / 60953 / 61148 / 60003 / 59846 | **KHOP** |
| map_s1a2_g1 50891 / G1_giveback5 48352 | AUDIT_APPLIED section 3.1-3.2 | 50891 / 48352 | **KHOP** |
| rank-IC S1 **+0.1661** vs G015 **+0.0688** (so MOI sau sua gate) | de bai | +0.1661 / +0.0688 | **KHOP** |
| gate MO top8 **0.0431** / random8 **0.0249** / gate DONG top8 **0.0193** | de bai + `gate_vs_rank3.py` | 0.0431 / 0.0249 / 0.0193 | **KHOP** |
| H3a rho **0.16670** | `ledger/h3/full/h3_metrics.json` | 0.16670 | **KHOP** |
| maxDD C2b -13.12 / C2_g015 -20.82 / map_s1a2_g1 -10.69 / G1_giveback5 -15.61 | AUDIT_APPLIED | -13.12 / -20.82 / -10.69 / -15.61 | **KHOP** |

Hai dinh chinh nho ve doc so (khong phai loi cua ai, la **hai quy uoc khac nhau**):
1. `AUDIT_APPLIED` ghi `H1b b:47460`, `H1c b:37600`; `RUNS_DEV` ghi 47,143 / 37,145.
   Ca hai dung: `AUDIT` doc **`b:` (tien mat)**, `RUNS_DEV`/`qret.py` doc **`b+unP`
   (mark-to-market)**. Hai run nay con lenh mo cuoi ky (`unP` -317 / -455) nen lech.
   Bao cao nay dung **`b+unP`** o moi noi (dung PREREG_CI section 1, dung `qret.py`).
2. `rho(G015, g1lite) = 0.1675` trong `AUDIT_APPLIED:45` do tren pool ledger v3 **day du**
   (15.44M dong, tu 2021-04). Pool OOS cua H3 la **14.32M dong tu 2022-03-31**. Tren
   **dung nhung hang cua H3**, `rho(G015) = 0.17137`. Phep so cu **0.1667 vs 0.1675** la so
   hai pool khac nhau. Phep so dung la **0.16670 vs 0.17137** (xem B10).

---

# BANG KET QUA

`d` = hieu (A - B). CI95 = percentile bootstrap **cua HIEU**, ghep cap (cung index/khoi cho ca hai).
"loai tru 0" = `YYY` nghia la CI khong chua 0 o **ca ba** do dai block da chot; phan loai theo
PREREG_CI section 4 doi **YYY**.

## NHOM A — tang equity/CAGR (block-bootstrap chuoi loi nhuan NGAY, 911 ngay, ghep cap theo ngay)

Block chinh **21 ngay** (n_eff = 44 khoi); kiem tra do ben o **10** (92 khoi) va **42** (22 khoi).
2000 rep, seed 20260903.

| # | So sanh (A vs B) | So cu / verdict cu | d (pp CAGR) | CI95 block 21 | CI95 block 10 | CI95 block 42 | loai tru 0 | n_eff | **PHAN LOAI** | Verdict cu co phai sua? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **C2b vs C2_g015** | 24.48 vs 17.13 => "S1 dong gop **+7.35pp**" | **+7.33** | [-1.72, +15.61] | [-2.88, +16.93] | [-2.33, +16.08] | nnn | 44 | **KHONG PHAN BIET DUOC** | **CO** — con so +7.35pp khong duoc dung nhu bang chung dinh luong nua |
| 2 | **C2b vs H1a_mom006** | 60390 vs 60953 (gap 563 USDT) | -0.46 | [-12.98, +11.96] | [-14.59, +13.19] | [-11.83, +10.18] | nnn | 44 | **KHONG PHAN BIET DUOC** | Khong — verdict cu la "H1a truot maxDD", ly do do **khong** dua vao CAGR |
| 3 | **C2b vs N4_a8s175** | 60390 vs 61148 (N4 cao hon 758 USDT) | -0.62 | [-5.55, +4.32] | [-6.22, +4.68] | [-5.15, +3.55] | nnn | 44 | **KHONG PHAN BIET DUOC** | Khong — **cung co** quyet dinh cu (luat pre-reg cam chon N4): N4 **khong** chung minh duoc la hon |
| 4a | **C2b vs RND1_2dp** | 60390 vs 60003 (chenh 387 USDT) | +0.32 | [-0.08, +0.81] | [-0.10, +0.80] | [-0.10, +0.76] | nnn | 44 | **KHONG PHAN BIET DUOC** | **CO** — xem muc E5 duoi |
| 4b | **C2b vs RND2_rnd** | 60390 vs 59846 (chenh 544 USDT) | +0.45 | [-0.63, +1.46] | [-0.56, +1.51] | [-0.65, +1.60] | nnn | 44 | **KHONG PHAN BIET DUOC** | **CO** — xem muc E5 duoi |
| 4c | RND1_2dp vs RND2_rnd | 60003 vs 59846 | +0.13 | [-0.85, +1.04] | [-0.85, +1.10] | [-0.83, +1.13] | nnn | 44 | **KHONG PHAN BIET DUOC** | Khong |
| 5 | **map_s1a2_g1 vs G1_giveback5** | 16.21 vs 13.85 => "S1 thang that" | +2.36 | [-3.33, +7.71] | [-3.86, +8.55] | [-3.62, +7.63] | nnn | 44 | **KHONG PHAN BIET DUOC** | **CO** — cap 16.21/13.85 khong con la bang chung dinh luong ve edge |
| 6a | C2b vs H1b_rmax30 | 24.43 vs 12.67, "THAM HOA" | +11.75 | [-27.30, +39.52] | [-32.29, +42.23] | [-27.53, +37.22] | nnn | 44 | **KHONG PHAN BIET DUOC** (theo CAGR) | **CO cach dien dat** — dong H1b la dung nhung ly do la **maxDD -44.3% QUAN SAT** (vi pham rang buoc cung C1), KHONG phai vi CAGR thap hon |
| 6b | C2b vs H1c_both | 24.43 vs 2.41, "THAM HOA" | +22.02 | [-29.65, +56.19] | [-31.64, +57.95] | [-27.78, +55.39] | nnn | 44 | **KHONG PHAN BIET DUOC** (theo CAGR) | **CO cach dien dat** — y nhu 6a, maxDD **-51.3%** quan sat |
| 6c | C2b vs RG95 | 60390 vs 56683, "THUA tren nen C2b" | +3.12 | [-2.49, +8.40] | [-1.44, +8.27] | [-3.06, +8.84] | nnn | 44 | **KHONG PHAN BIET DUOC** | **CO** — xem HE QUA (ii) |
| 6d | C2b vs RG97 | 60390 vs 52045, "THUA" | +7.20 | [-0.29, +14.76] | [**+0.38**, +14.64] | [-0.82, +16.17] | nYn | 44 | **KHONG PHAN BIET DUOC** | **CO** — sat nguong, phu thuoc do dai block => dung luat pre-reg: chua phan biet duoc |
| 6e | C2b vs RG95w180 | 60390 vs 59120, "THUA" | +1.06 | [-4.79, +7.34] | [-4.10, +6.51] | [-5.40, +7.39] | nnn | 44 | **KHONG PHAN BIET DUOC** | **CO** — xem HE QUA (ii) |
| 6f | C2b vs BR1_margin | 60390 vs 60272, "breaker khong doi gi" | +0.098 | [-0.034, **+0.264**] | [-0.031, +0.263] | [-0.023, +0.248] | nnn | 44 | **KHONG PHAN BIET DUOC** (**null co thong tin**: CI hep, tac dong toi da 0.26pp) | Khong — verdict "khong cai thien gi" **duoc cung co** |
| 6g | K0_h1a_prof vs BR3_mg006 | 59580 vs 59542, "breaker khong cuu DD" | +0.032 | [-1.28, +1.17] | [-1.35, +1.14] | [-1.27, +1.10] | nnn | 44 | **KHONG PHAN BIET DUOC** | Khong — ket luan cu ve DD dua tren maxDD quan sat (-21.03 vs -20.92), khong dua tren CAGR |
| — | K1_conc25, K2_conc20 vs K0_h1a_prof | "VO HIEU, giong het tung byte" | **d = 0 dinh nghia** | — | — | — | — | — | **VOID — nut tro** | Khong. Da kiem lai: chuoi equity ngay **giong het** => KHONG bootstrap. VOID **khac** THUA |
| — | BR2_both vs BR1_margin | "giong het BR1" | **d = 0 dinh nghia** | — | — | — | — | — | **VOID — nut tro** | Khong. Da kiem: chuoi equity ngay giong het |

**maxDD QUAN SAT (khong co CI — PREREG_CI section 2.5 cam bootstrap maxDD):**

| run | CAGR | maxDD | underwater dai nhat |
|---|---|---|---|
| C2b | +24.43% | **-13.12%** | 93 ngay |
| C2_g015 | +17.10% | -20.82% | **406 ngay** |
| H1a_mom006 | +24.89% | -21.11% | 108 ngay |
| N4_a8s175 | +25.05% | -14.27% | 114 ngay |
| RND1_2dp | +24.11% | -13.14% | 95 ngay |
| RND2_rnd | +23.98% | -13.18% | 95 ngay |
| map_s1a2_g1 | +16.18% | -10.69% | 114 ngay |
| G1_giveback5 | +13.82% | -15.61% | 256 ngay |
| H1b_rmax30 | +12.67% | **-44.28%** | 444 ngay |
| H1c_both | +2.41% | **-51.31%** | 699 ngay |
| RG95 | +21.31% | **-12.88%** | 99 ngay |
| RG97 | +17.23% | **-12.33%** | 147 ngay |
| RG95w180 | +23.37% | -13.12% | 187 ngay |
| BR1_margin | +24.33% | -13.13% | 93 ngay |
| BR3_mg006 | +23.72% | -20.92% | 133 ngay |
| K0_h1a_prof | +23.76% | -21.03% | 133 ngay |

## NHOM B — tang xep hang (block-bootstrap khoi 72h cua tick)

Block chinh **72h**; kiem tra do ben **24h** va **168h**. 2000 rep, seed 20260903.
`n_eff` = so khoi 72h **THAT SU co du lieu** cua phep do do (khong phai so khoi cua ca doan).
Doan `cand_dev` co 303 khoi 72h, trong do 248 khoi co du lieu.

| # | So sanh | So cu | d | CI95 block 72h | CI95 24h | CI95 168h | loai tru 0 | n_eff (khoi 72h) | **PHAN LOAI** | Verdict cu co phai sua? |
|---|---|---|---|---|---|---|---|---|---|---|
| 7 | **rank-IC S1 - rank-IC G015** (gate MO, trong tick, `-score` vs `g1_replay`) | +0.1661 vs +0.0688 (cu: +0.150 / +0.055) | **+0.0973** | **[+0.0711, +0.1152]** | [+0.0673, +0.1293] | [+0.0561, +0.1084] | **YYY** | **39** (325 tick) | **SONG** | Khong — nay da co CI. `P(d>0) = 1.000` |
| 8 | **g1_replay: gate MO top8 - random8** | 0.0431 vs 0.0249 = +0.0182 | **+0.01818** | **[+0.0085, +0.0227]** | [+0.0093, +0.0254] | [+0.0081, +0.0227] | **YYY** | **52** (465 tick, 3030 dong) | **SONG** | Khong. `P(d>0) = 1.000` |
| 9 | **g1_replay: gate MO top8 - gate DONG top8** | 0.0431 vs 0.0193 = +0.0238 | +0.02382 | [-0.0053, +0.0442] | [-0.0043, +0.0428] | [-0.0133, +0.0479] | nnn | 52 vs 248 | **KHONG PHAN BIET DUOC** | **CO** — "gate chon dung tick" chua duoc chung minh |
| 10 | **rho(H3a, g1lite) - rho(G015, g1lite)** tren **cung 14,320,746 hang** | cu so 0.1667 vs 0.1675 (hai pool KHAC nhau) | **-0.00467** (= **-0.34 sd**) | [-0.0315, +0.0229] | [-0.0266, +0.0184] | [-0.0310, +0.0212] | nnn | 274 | **KHONG PHAN BIET DUOC** | **CO** — ghi ro day la "khong phan biet duoc", **KHONG** phai "H3 thua" |

**Kiem chung phuong phap nhom B (#10):** bootstrap dong-bang-hang cho `sd(rho_G015) = 0.01901`
va `CI95 = [0.1338, 0.2086]` o block 72h. `LEAK_L1_REPORT` section 3.3 do bang bootstrap tho
400 rep ra `sd = 0.0187`, `CI = [0.1260, 0.2005]`. **Khop** (lech do pool khac: 14.32M hang tu
2022-03 thay vi 15.44M tu 2021-04, va 2000 rep thay vi 400) => xap xi dong-bang-hang la hop le.

**Vi sao nhom B phat hien duoc ma nhom A khong:** nhom B do tren **3,030 - 36,183 quan sat ket qua
rieng le** (co n_eff = 39-52 khoi), nhom A do tren **MOT duong equity**. Mot duong equity la
mot quan sat duy nhat cua mot the gioi duy nhat; chia no thanh 911 ngay khong tao them thong tin
ve *su khac biet giua hai cau hinh* khi hai cau hinh nam trong cung mot the gioi do.

## PHAN TICH BO SUNG — KHONG PRE-REG (chay SAU khi thay ket qua chinh)

Nghi van hop ly: thong ke chinh (hieu CAGR) la **hieu cua hai ham exp**, nen phuong sai cua no bi
thoi bang **nhan to thi truong chung** (resample nao thi truong tot thi CA HAI CAGR lon len, hieu
cua hai exp cung phong to). Da kiem bang thong ke ghep cap "sach" hon:
`dg = 365 * mean( log(1+r_A,d) - log(1+r_B,d) )` — tru theo **tung ngay** nen nhan to chung triet tieu.

**Ket qua: khong doi ket luan nao.** `dg` cung **chua 0** o ca 14 cap, o ca 3 do dai block:

| # | dg (pp/nam) | CI95 block 21 | # | dg | CI95 block 21 |
|---|---|---|---|---|---|
| 1 (C2b vs C2_g015) | +6.07 | [-1.39, +14.25] | 6a (vs H1b) | +9.92 | [-19.18, +42.49] |
| 2 (vs H1a) | -0.37 | [-9.99, +10.13] | 6b (vs H1c) | +19.47 | [-20.23, +60.98] |
| 3 (vs N4) | -0.50 | [-4.12, +3.73] | 6c (vs RG95) | +2.54 | [-1.98, +6.79] |
| 4a (vs RND1) | +0.26 | [-0.06, +0.66] | 6d (vs RG97) | +5.96 | [-0.20, +12.30] |
| 4b (vs RND2) | +0.36 | [-0.49, +1.19] | 6e (vs RG95w180) | +0.85 | [-3.63, +5.85] |
| 5 (map_s1a2 vs G1) | +2.05 | [-2.62, +7.23] | 6f (vs BR1) | +0.078 | [-0.025, +0.219] |

=> Ket luan "khong phan biet duoc" o nhom A **khong** phai artifact cua phep bien doi exp.
Muc nay **KHONG duoc dung** de doi phan loai (phan loai chi theo PREREG_CI).

---

# HE QUA

## (i) Bang chung "S1 co edge that" con song sau CI that hay khong?

**Tra loi: CON SONG — nhung chi o TANG XEP HANG. O tang equity/CAGR thi KHONG.**
Hai tang phai duoc tach ra, va tu nay khong duoc tron.

**Con song (co CI, loai tru 0 o ca 3 do dai block):**
- **#7**: S1 xep hang trong tick tot hon G015: rank-IC **+0.1661 vs +0.0688**, hieu **+0.0973**,
  CI95 **[+0.0711, +0.1152]**, `P(d>0) = 1.000`, voi n_eff chi **39 khoi 72h**. Song rat manh.
- **#8**: trong tap tick gate MO, top8 theo S1 tot hon 8 coin **ngau nhien**: `g1_replay`
  **0.0431 vs 0.0249**, hieu **+0.0182**, CI95 **[+0.0085, +0.0227]**, `P(d>0) = 1.000`,
  n_eff **52 khoi**. Day la bang chung "xep hang co gia tri" doc lap voi gate.

**KHONG con song (khong phan biet duoc):**
- **#1** — "S1 dong gop **+7.35pp CAGR**" (C2b 24.48 vs C2_g015 17.13). CI cua hieu
  **[-1.72, +15.61]pp**. DEV **khong the loai tru** kha nang G015 tot bang hoac hon o tang equity.
- **#5** — cap goc "16.21 vs 13.85" (`map_s1a2_g1` vs `G1_giveback5`). Hieu +2.36pp,
  CI **[-3.33, +7.71]pp**. Day la cap tung duoc goi la "bang chung S1 thang that" (AUDIT_APPLIED
  Bang 2 #1). No **khong con** dung duoc nhu bang chung dinh luong.

**Phat bieu dung tu nay:** *"S1 xep hang coin trong cung mot tick tot hon G015 — da chung minh voi
CI. Muc do dieu do bien thanh CAGR chua do duoc: diem uoc luong +7.3pp, nhung DEV chi giam duoc
khoang [-2, +16]pp."*

Ba luu y ve **tinh dong quy** (consilience), khong phai ve y nghia thong ke:
1. Ba phep do (#1 +7.33pp, #5 +2.36pp, #7 +0.0973 rank-IC) **cung mot chieu**, cong voi maxDD
   quan sat tot hon (C2b -13.12 vs C2_g015 -20.82; underwater 93 vs **406 ngay**). Do la ly do
   hop ly de **giu** S1. Nhung **KHONG duoc cong lai** thanh "3 bang chung doc lap": #1 va #5
   dung **cung 911 ngay DEV**, cung cac lenh, cung mot duong gia. Chung khong doc lap.
2. Cai #7/#8 chung minh la **xep hang tuong doi trong tick**. Chung **khong** chung minh phan
   **tuyet doi** (hieu chuan P(win)) — va gate cua C2b chay bang phan tuyet doi cua **G015**
   (AUDIT_APPLIED section 3.3 (d)). Nen "S1 co edge" **khong** cuu duoc bat ky nghi van nao ve G015.
3. Doi chung shuffle cua H3 (`h3_metrics.json`) dat `rho = 0.1235` trong khi model that dat
   0.1667 — tuc phan lon do lon cua `rho` **tuyet doi** la cau truc du lieu, khong phai ky nang.
   Con cau `f0..f39` co leak khong thi **van mo** (`LEAK_L1_REPORT` muc "CON LAI CHUA DONG" #1).

## (ii) Nhanh nao tung bi dong vi "thua" ma thuc ra chi NAM TRONG NHIEU, dang mo lai?

Phan loai lai 3 nhom. **Luu y quan trong ve nguyen tac:** "nam trong nhieu" la ly do de noi
*"chua co co so dong no"*, **khong** phai ly do de *mo lai*. Mo lai = them n_trials = them rui ro
L2 selection. Duoi day ghi ro nhanh nao **that su** dang mo lai va nhanh nao khong.

**Nhom 1 — DANG MO LAI: dong bang mot phep so ma du lieu khong the giai, va KHONG vi pham rang buoc cung**

| Nhanh | Ly do dong cu | Su that | Rang buoc cung? |
|---|---|---|---|
| **B4 — rolling-percentile gate** (`RG95` / `RG97` / `RG95w180`) | "ca 3 < C2b 60390 => THUA tren nen C2b"; "EV am tren nen C2b => khong nen" | Ca 3 hieu **nam trong CI**: +3.12 [-2.49,+8.40] · +7.20 [-0.29,+14.76] · +1.06 [-4.79,+7.34]. **Va maxDD cua ca 3 khong te hon C2b**: RG95 **-12.88**, RG97 **-12.33**, RG95w180 -13.12 vs C2b -13.12 | **Khong vi pham** (maxDD <= 15% dat het) |

Day la nhanh **duy nhat** trong danh sach vua nam trong nhieu, vua khong vi pham rang buoc nao,
vua co dau hieu **tot hon** o chieu khac (maxDD). Cau "EV am tren nen C2b" trong `AUDIT_APPLIED:B4`
**khong duoc du lieu ho tro** va nen sua.
Chi phi mo lai la thuc: co che `GateRollingThreshold.java` (97 dong) **da bi xoa** o `5f40a90`
=> phai viet lai code + pre-reg moi. Quyet dinh co bo chi phi do hay khong la **cua chu du an**
(danh doi: 1 nhanh khong the phan biet duoc bang DEV, doi lai ~100 dong code + 1 pre-reg + rui ro
L2). Toi **khong** quyet thay.

**Nhom 2 — VAN DONG, nhung phai SUA LY DO (dong vi rang buoc cung, khong vi phep so CAGR)**

| Nhanh | Ly do dong phai ghi lai |
|---|---|
| **B2 H1b** (`PREDICT_SYMBOL_RATE_MAX` 0.30) | Dong vi **maxDD -44.28% QUAN SAT** (vi pham C1 maxDD<=15%), 444 ngay underwater. **KHONG** vi "CAGR thap hon C2b" — phep so CAGR cho CI [-27.3,+39.5], vo nghia. Cum tu "truc chet, dong vinh vien" van dung nhung phai gan vao maxDD |
| **B3 H1c** | Y nhu tren: **maxDD -51.31%**, 699 ngay underwater |
| **B1 H1a** | Da ghi dung san: "truot C1 maxDD <= 15" (maxDD -21.11%). Phep so equity C2b vs H1a **khong phan biet duoc** (H1a con cao hon 563 USDT) — cang khong duoc dung de bao ve C2b. Giu nguyen quyet dinh, giu nguyen ly do |
| **A10 H3** | Dong vi 4/5 tieu chi FAIL **khac**: hieu chuan `calib_max_gap = 0.215 > 0.05`, va doi chung shuffle dat chat luong admit **+0.0992 > model that +0.0891**. **Phep so rho (#10) phai ghi la "KHONG PHAN BIET DUOC"** (-0.0047 = -0.34 sd), **KHONG** phai "H3 thua". Va phai ghi dung: G015 tren cung pool la **0.17137**, khong phai 0.1675 |

**Nhom 3 — verdict cu DUOC CUNG CO (khong doi gi)**

| Nhanh | Vi sao duoc cung co |
|---|---|
| **D1 BR (circuit breaker)** | `d = +0.098pp`, CI **[-0.034, +0.264]** — **CI hep nhat trong ca bang**. Day la "null co thong tin": khong phai "khong biet", ma la "tac dong toi da khoang 1/4 pp". Verdict "breaker khong cai thien gi" **manh hon** sau CI. Phan biet ro voi #6a/#6b la "khong biet vi CI rong" |
| **C13 K1/K2 `MAX_CONCURRENT`** | **VOID — nut tro**. Da kiem lai: chuoi equity ngay **giong het** K0 => `d = 0` theo dinh nghia. Khong bootstrap. **VOID khac THUA** — dung goi la "khong phan biet duoc" (cach goi do ngu y co bien dong khong do noi; that ra khong co bien dong nao) |
| **BR2 vs BR1** | Y nhu tren: chuoi equity ngay giong het => VOID |
| **C9 N4 / luat cam chon diem tot nhat** | N4 hon C2b 758 USDT nhung `d = -0.62pp`, CI [-5.55,+4.32] => N4 **khong chung minh duoc la hon**. Luat pre-reg "khong chon config tot nhat tu lan can" duoc **cung co bang so**, khong con la nguyen tac tru tuong |

**Nhom 4 — DAO CHIEU ket luan phu: `E5` (hang so HPO 5 chu so)**

Verdict pre-reg cu: **"hang so KHONG load-bearing"** => **VAN DUNG**, va nay co CI:
`d(C2b - RND1) = +0.32pp`, CI [-0.08, +0.81]; `d(C2b - RND2) = +0.45pp`, CI [-0.63, +1.46].
Nhung **loi phe cua AUDIT_APPLIED Bang 2 #3 la SAI va phai rut**: doc nguyen van —
*"Mat that 544 USDT equity = ~-0.5pp CAGR ... Pre-reg viet 'khong mat gi' — cau do khong dung"*.
Voi CI that, **544 USDT nam hoan toan trong nhieu**; cau "mat that" moi la cau khong dung.
=> `E5` **nen apply** (thay `Configs.java:307-309` bang so tron 1.3/0.25/2.0), va cau
"day la quyet dinh CUA UNI, doi 0.5pp CAGR lay su trung thuc" **khong con la mot su danh doi** —
khong co 0.5pp nao de doi. (Quyet dinh bam nut van la cua chu du an; nhung gia cua no la 0.)

**Nhom 5 — muc MOI phai ghi vao ban do quyet dinh: #9 (gate co chon dung tick khong)**

`gate MO top8` vs `gate DONG top8` = +0.0238, CI **[-0.0053, +0.0442]** => **khong phan biet duoc**.
Ket hop voi #8 (**song**): **xep hang trong tick co gia tri da chung minh; con viec GATE chon dung
TICK thi CHUA**. Day khong phai "gate hong" (B5 da rut lai ket luan do va dung rut) — day la
"chua ai chung minh duoc gate them gia tri, va DEV chi co **52 khoi 72h** gate-MO nen kho chung minh".
Con so 0.51% admit rate lam n_eff cua moi cau hoi ve gate nho tham hai.

## (iii) Voi CI that, can bao nhieu du lieu/thoi gian nua moi phan biet duoc mot cai thien 3pp CAGR?

Cong thuc chot truoc o `PREREG_CI` section 5: `sd(CAGR) ~ 1/sqrt(T)`;
`T_can = T_dev * (sd_dev / (0.03/z))^2`, `z = 2.80158` (cong suat 80%), `1.95996` (50%).
`T_dev = 911 ngay = 2.496 nam`.

| Loai cap so sanh | Vi du | sd(d) tren DEV | **Can (cong suat 80%)** | Can (cong suat 50%) |
|---|---|---|---|---|
| Chi doi **tham so exit** (cung selector, cung gate) | C2b vs N4_a8s175 | **2.57pp** | **14.3 nam** | 7.0 nam |
| Chi doi **selector** (cung exit) | C2b vs C2_g015 | **4.45pp** | **43.1 nam** | 21.1 nam |
| Doi **selector** o thang arm5/scale1 | map_s1a2_g1 vs G1_giveback5 | 2.85pp | 17.7 nam | 8.7 nam |
| Noi **gate** | C2b vs H1a_mom006 | **6.34pp** | **87.4 nam** | 42.8 nam |
| Doi **3 hang so gate gan nhu tro** | C2b vs RND2_rnd | 0.53pp | **0.60 nam** | 0.30 nam |

Voi thong ke loga ghep cap (bo sung, khong pre-reg — san duoi **lac quan hon**):
exit-param **9.0 nam**, selector **33.9 nam**, arm5/scale1 **14.2 nam**.

**Cau tra loi mot cau: tu 9 den 45 nam du lieu nua, tuy loai thay doi. Tuc la KHONG THE dat duoc
bang cach cho them du lieu.**

Kiem chung lai bang ca danh muc du lieu du an co: DEV 2.496 + VAL 1.46 + HOLDOUT 2026 (~0.75)
= **~4.7 nam**. `sd` giam theo he so `sqrt(4.7/2.496) = 1.37`. Cap "chi doi tham so exit" van
con `sd = 1.87pp` > nguong can `1.07pp` => van **thieu he so 1.75 ve sd = thieu 3.1 lan ve thoi
gian**. Dung het moi byte du lieu ma du an co (ke ca pha seal HOLDOUT, dieu KHONG duoc lam) thi
van con thieu ~10 nam.

### Bon he qua bat buoc cho ke hoach tiep theo

**1. Ngung dung hieu CAGR tren DEV lam tieu chi phan biet giua hai cau hinh.** Do la mot phep do
co `sd` 2.5-6.3pp. Moi "cai thien" 0.5-3pp tung ghi trong `RUNS_DEV`/`AUDIT_APPLIED`
(N4 +0.6pp, H1a +0.5pp, RND -0.3/-0.5pp, RG95w180 -1.1pp) deu **nho hon nhieu do luong tu 4 den
12 lan**. Chung khong phai tin hieu.

**2. So bang so: ky vong cua GIA TRI LON NHAT trong N phep thu thuan nhieu.**
`E[max] ~ sd * sqrt(2 ln N)`:

| N cau hinh thu | he so `sqrt(2 ln N)` | voi sd 2.57pp (exit-param) | voi sd 4.45pp (selector) |
|---|---|---|---|
| 50 (~so config DEV da thu) | 2.80 | **+7.2pp** | +12.5pp |
| 256 (**GS wave-1 Sobol**) | 3.33 | **+8.6pp** | +14.8pp |
| 1000 | 3.72 | +9.6pp | +16.6pp |

=> Neu GS wave-1 (256 diem) tra ve mot diem hon C2b **+8pp CAGR tren DEV**, do **dung bang** cai
ma nhieu thuan tuy sinh ra. Dieu nay **khong** noi GS la vo ich — no noi luat doc ket qua
(`PREREG_GS` section 4) **khong duoc xep hang finalist bang CAGR DEV**, va nguong "hon baseline
bao nhieu pp" phai duoc dat **cao hon 8.6pp** neu dung DEV-A/DEV-B nhu hien tai.
(Toi **khong sua** `PREREG_GS.md` theo gioi han; day la canh bao gui chu du an.)

**3. Chuyen tieu chi quyet dinh LEN THUONG NGUON — day la cai da hoat dong.** #7 phat hien
`+0.0973` rank-IC va #8 phat hien `+0.0182` g1_replay **voi n_eff chi 39-52 khoi 72h**, trong khi
tang equity khong phat hien duoc gi voi 44 khoi. Ly do: nhom B do **3,030-36,183 ket qua rieng le**,
nhom A do **mot duong equity**. => moi quyet dinh selector/gate nen duoc pre-register o **tang ket
qua tung lenh / tung tick** (voi CI block 72h), va CAGR/maxDD chi lam **kiem tra ha nguon**
(sanity + rang buoc cung maxDD), **khong** lam thu do phan biet.

**4. Muon co suc phan biet o tang equity thi phai tang SO CUOC DOC LAP, khong phai so nam.**
C2b co n = 970 lenh tren 2.5 nam, va cac lenh **dom cum theo thoi gian** (do la ly do n_eff = 44
khoi chu khong phai 970). Ba huong duy nhat co ly:
- (a) **Thong ke ghep cap tung lenh**: cung tick, cung coin, hai cau hinh => tru truc tiep, triet
  tieu nhan to thi truong. Day la phien ban tang-lenh cua cai lam nhom A "hep" duoc (#6f dat
  CI +-0.15pp vi hai run gan nhu trung nhau). **Kha thi ngay voi `printDone.csv` dang co.**
- (b) **Tang so cuoc**: nhieu coin/tick hon, size nho hon moi cuoc — doi lai co the giam CAGR.
  Day la danh doi gia tri, **khong** phai quyet dinh ky thuat => cua chu du an.
- (c) Bo han tham vong "phan biet 3pp": chap nhan chon bang **co che + rang buoc cung**
  (maxDD, chi phi stress, khong nam am) thay vi bang thu tu CAGR. Trong 3 nam DEV, day la cach
  duy nhat dua ra quyet dinh ma khong tu doi lua.

---

## NHUNG GI BAO CAO NAY **KHONG** LAM

- **Khong sua diem uoc luong nao.** CI khong doi diem. C2b van la b:60390 / CAGR 24.43 / maxDD -13.12.
- **Khong mo lai nhanh nao, khong dong nhanh nao.** Chi phan loai lai bang chung va chi ro cau nao
  trong docs khong duoc du lieu ho tro.
- **Khong cham VALIDATION / HOLDOUT.** Moi so trong bao cao tu DEV.
- **Khong tra loi cau leak `f0..f39`** — van la lo hong duy nhat con mo
  (`LEAK_L1_REPORT` muc "CON LAI CHUA DONG" #1).
- **Khong bootstrap maxDD** (`PREREG_CI` section 2.5): moving-block pha thu tu thoi gian nen maxDD
  cua duong gia lap vo nghia. Moi maxDD trong bao cao la **quan sat mot lan, khong co CI** — va
  chinh vi vay no van la rang buoc cung dung duoc (H1b/H1c bi dong bang no).
- **Khong sua `docs/PREREG_GS.md`**, khong cham `/home/ubuntu/gs/`, `research/kaggle/gsearch/*`.
