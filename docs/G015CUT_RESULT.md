# G015CUT_RESULT — bo 5 feature OI khoi G015: ket qua do

Tien dang ky: `docs/PREREG_G015CUT.md`, commit **9db99ef342bbd4ae466c2f355221a94182e12057**
(commit TRUOC moi lan train). Ngay do: 2026-09-03/04. **CHI DEV**, khong cham VALIDATION/HOLDOUT,
khong rebuild file OI, khong chay java/backtest.

Kernel: `chuyendinh/g015-cut-a` (5 bien the) + `chuyendinh/g015-cut-b` (4 bien the), Kaggle GPU
`device="cuda"`, 10 fold WFO DEV, NEST=400. Cham diem + CI tren Oracle
(`/home/ubuntu/g015/analyze.py`, `report2.py`), ket qua tho `/home/ubuntu/g015/g015cut_final.json`.

---

## 1. TRA LOI DUT KHOAT

| Cau | Tra loi |
|---|---|
| **Bo duoc 5 feature OI?** (theo dung hop dong pre-reg §5.3) | **KHONG KET LUAN DUOC.** Hai dieu kien truot: **(E) cong tai lap FAIL** va **(C) chat luong hang admit khong du hep de chung nhan**. |
| Rieng thuoc do `rho`? | **Khong kem di, o le 0.010**: `d = +0.00035`, CI95 `[-0.0053, +0.0058]`, CI noi rong (k=2.0957) `[-0.0056, +0.0063]`, dat o **ca 3** do dai khoi. Diem uoc luong **duong** (bo OI tot hon mot chut). |
| Rieng thuoc do van hanh (admit)? | **Khong ket luan duoc**: `d(chat luong hang admit, ghep so luong) = -0.00104`, CI noi rong `[-0.0066, +0.0045]`. `k*sd = 0.00552 > Delta_adm = 0.0050` => khoang **tu ban chat** qua rong de chung nhan. Day dung la cam bay da ghi truoc o PREREG §6.4. |
| 45 feature co bao nhieu that su dong gop? | **O do phan giai NHOM: khong nhom nao trong 4 nhom da thu la can thiet.** Bo OI (5), bo funding (9), bo basket (5), bo rank cross-sectional (3) — tat ca deu **TUONG DUONG** o le 0.010; 3/4 nhom co diem uoc luong **duong**. Doi chung ve cong suat (`oi_only`, 5 feature) ra **KEM HON RO** (`d = -0.0928`) => thuoc do CO suc phat hien mat mat that. |

**Cau chot:** phep do KHONG chan duoc gia thuyet "bo 5 feature OI de keo DEV ve 2020-01". Nhung no
cung **chua** cho phep ket luan la bo duoc, vi (i) moc so sanh 0.1675 khong tai lap duoc va
(ii) thuoc do van hanh (thu quan trong that voi GATE) khong du phan giai.

---

## 2. CONG TAI LAP — FAIL (PREREG §5.1)

| | gia tri |
|---|---|
| `rho(full45)` tai lap | **0.18900** |
| moc `AUDIT_APPLIED:45` / `LEAK_L1_REPORT` | 0.16752 (da tai lap DUNG tu ledger truoc khi chot pre-reg) |
| lech | **+0.02150** |
| nguong pre-reg | PASS <= 0.010 / MARGINAL <= 0.019 / **FAIL > 0.019** |
| ket luan pre-reg | **FAIL** (truot 0.0025) |

Phep so ghep cap giua ban tai lap va ban da deploy: `d(p_old - full45) = -0.02147`,
`sd = 0.00801`, CI noi rong `[-0.0383, -0.0047]` => **loai tru 0**. Nghia la ban da deploy
**that su kem hon** ban tai lap, khong phai nhieu.

### 2.1 Lech nam o dau — do theo tung fold

`rho` trong TUNG khoi OOS (khong gop):

| fold (cutoff GMT+7) | n | `p_old` (da deploy) | `full45` (tai lap) | `no_oi` | delta (full45 - p_old) |
|---|---:|---:|---:|---:|---:|
| 20220101 | 1,121,346 | 0.0873 | 0.1386 | 0.1498 | **+0.0512** |
| 20220401 | 1,092,771 | 0.1556 | 0.2745 | 0.2615 | **+0.1189** |
| 20220701 | 1,188,130 | 0.1545 | 0.1650 | 0.1630 | +0.0105 |
| 20221001 | 1,241,762 | 0.1844 | 0.1394 | 0.1525 | **-0.0450** |
| 20230101 | 1,302,319 | 0.1503 | 0.1354 | 0.1432 | -0.0149 |
| 20230401 | 1,517,723 | 0.1044 | 0.0726 | 0.0722 | -0.0318 |
| 20230701 | 1,671,614 | 0.0696 | 0.0591 | 0.0563 | -0.0105 |
| 20231001 | 1,912,671 | 0.1823 | 0.1774 | 0.1750 | -0.0049 |
| 20240101 | 2,139,680 | 0.2220 | 0.2313 | 0.2303 | +0.0093 |
| 20240401 | 2,254,076 | 0.1580 | 0.1624 | 0.1611 | +0.0044 |
| **gop toan pool** | 15,442,092 | **0.1675** | **0.1890** | **0.1893** | **+0.0215** |

Doc dung:
1. **Ban tai lap KHONG tot hon deu.** No tot hon manh o **2 fold dau** (2022Q1, 2022Q2 — dung 2 fold
   ma model chi train tren 2021) va **kem hon** o 4 fold giua. Trung binh delta theo fold la
   **+0.0087**, nho hon nhieu delta gop **+0.0215**.
2. `spearman(full45, p_old) = 0.836` tren mau 1/37 => cung ho model, khong phai hai thu khac nhau.
3. Vi delta **gop** lon hon trung binh **theo fold**, phan lon do lech gop la **hieu ung gop lien
   che do** (muc trung binh cua `p` khac nhau giua fold, thang do khac nhau) chu khong phai ky nang.
   Dieu nay dong thoi la mot canh bao ve chinh moc 0.1675: **`rho` gop toan pool trao doi duoc voi
   viec hieu chuan muc `p` giua cac fold**, no khong phai thuoc do xep hang thuan.
4. `0.1890` **nam trong** CI95 that cua moc (`LEAK_L1_REPORT §3.3`: `[0.1260, 0.2005]`;
   `CI_REAUDIT`: `[0.1338, 0.2086]`). Nguong pre-reg 0.019 (= 1 sd) **chat hon** CI95 (+-0.037).
   Phat bieu dung: **khong tai lap duoc diem uoc luong trong 1 sd, nhung gia tri moi khong khac
   moc o muc CI95.**

### 2.2 Nguyen nhan kha di (GIA THUYET, chua chung minh)

Do duoc (khong phai suy dien):
- Bins da deploy `claudedata/predwf_G015x26/predict_wf_*.bin` co mtime **2026-08-14 15:03-15:05**.
- File Tool1 15m cua 4 quy **2021** trong `/home/ubuntu/ds_feat15m/` co mtime **2026-08-16 08:36**
  (SAU khi bins duoc sinh); cac quy 2022+ co mtime 2026-08-13 17:03-17:41.
- `docs/archive/.../wfo_q2_unlock_and_t1c2_rootcause_2026-08-16.md` ghi: dataset Tool1 doi dinh dang
  sang **T1C2** ngay 2026-08-13, va truoc do ban 15m la **row-major float32 170B/record (dinh dang
  CU)**. Hom nay ca 14 file DEV deu la T1C2.
- Hai fold ma ban tai lap tot hon manh la **dung hai fold train HOAN TOAN tren 2021** (fold 20220101
  train 2021; fold 20220401 train 2021 + 1 quy 2022).

=> Gia thuyet manh nhat: **bins da deploy duoc train tren mot ban export Tool1 2021 KHAC (cu hon)
voi ban dang co**, nen 2 fold dau bi lech phan phoi feature giua train va OOS. Chua chung minh
duoc vi ban export 2021 cu **khong con ton tai** tren dia.
Gia thuyet phu (khong loai tru): xgboost 3.2.0 + `device="cuda"` khac phien ban CPU dung hom
2026-08-14 (khong con log nao cua lan chay do tren Oracle de doi chieu).

**Vi cong tai lap FAIL, moi so sanh o muc 4-5 duoi day KHONG duoc dung nhu bang chung ve BAN DA
DEPLOY.** Chung la bang chung noi bo, hop le, ve **ban tai lap** — moi bien the deu train bang cung
mot pipeline, cung data, cung seed, chi khac tap cot.

---

## 3. DOI CHUNG AM — PASS (PREREG §5.2), va phuong phap CI duoc kiem chung

| bien the | `d_rho` | `sd` | CI95 | CI noi rong | chua 0? | `|d| < 0.010`? |
|---|---:|---:|---|---|---|---|
| `noise46_a` (full45 + 1 cot nhieu, seed 101) | **-0.00010** | 0.00067 | [-0.00143, +0.00125] | [-0.00151, +0.00131] | **CO** | CO |
| `noise46_b` (full45 + 1 cot nhieu, seed 202) | **+0.00003** | 0.00066 | [-0.00120, +0.00139] | [-0.00136, +0.00141] | **CO** | CO |

=> **PASS**. Them 1 feature nhieu thuan **khong** co tac dung do duoc.
**San nhieu quy trinh** (max `|d_rho|` cua doi chung) = **0.00010**.

**Kiem chung xap xi frozen-rank (PREREG §4):** bootstrap THO (tinh lai spearman tren dong resample,
60 rep, cung danh sach khoi) cho `sd(d) = 0.002506`; xap xi frozen-rank cho `sd = 0.002847`.
Lech **12.0% < 20%** => xap xi duoc dung. (Kiem tren dung cap `no_oi` vs `full45`.)

**Doi chung ve CONG SUAT (khong pre-reg nhu doi chung, nhung doc duoc nhu vay):** `oi_only`
(chi 5 feature OI) ra `d_rho = -0.0928`, CI noi rong `[-0.1289, -0.0568]` => **KEM HON RO**.
Thuoc do co suc phat hien mat mat that su.

---

## 4. BANG BIEN THE (M = 9 dong bang, k = sqrt(2 ln 9) = 2.0957, khoi 72h chinh)

`n_eff` khoi: **304** (72h) / **907** (24h) / **131** (168h). 2000 rep, seed 20260903, ghep cap.
`d` = hieu so voi `full45`. `q_m` = chat luong hang admit o dang **ghep so luong**.

| bien the | n feat | `rho` | `d_rho` | `sd` | CI95 cua `d` | CI noi rong | `wide_lo` 24h/72h/168h | don dieu 20 bucket | admit rate | `q_m` | `d(q_m)` | CI noi rong `d(q_m)` | phan loai `rho` (Delta=0.010) |
|---|---:|---:|---:|---:|---|---|---|---:|---:|---:|---:|---|---|
| `full45` (moc noi bo) | 45 | 0.18900 | — | — | — | — | — | 0.947 | 0.00613 | 0.12248 | — | — | — |
| **`no_oi`** | **40** | **0.18934** | **+0.00035** | 0.00285 | [-0.0053, +0.0058] | [-0.0056, +0.0063] | -0.0040 / -0.0056 / -0.0065 | **1.000** | 0.00737 | 0.12143 | **-0.00104** | [-0.0066, +0.0045] | **TUONG DUONG** |
| `noise46_a` | 46 | 0.18889 | -0.00010 | 0.00067 | [-0.0014, +0.0012] | [-0.0015, +0.0013] | -0.0013 / -0.0015 / -0.0016 | 0.895 | 0.00604 | 0.12257 | +0.00010 | [-0.0029, +0.0031] | TUONG DUONG |
| `noise46_b` | 46 | 0.18902 | +0.00003 | 0.00066 | [-0.0012, +0.0014] | [-0.0014, +0.0014] | -0.0012 / -0.0014 / -0.0014 | 0.895 | 0.00609 | 0.12182 | -0.00065 | [-0.0036, +0.0023] | TUONG DUONG |
| `no_funding` (bo f17..f25) | 36 | 0.19002 | +0.00102 | 0.00301 | [-0.0051, +0.0070] | [-0.0053, +0.0073] | -0.0039 / -0.0053 / -0.0056 | 0.947 | 0.00633 | 0.12685 | **+0.00438** | [-0.0025, +0.0113] | TUONG DUONG |
| `no_basket` (bo f12..f16) | 40 | 0.18805 | -0.00094 | 0.00083 | [-0.0025, +0.0008] | [-0.0027, +0.0008] | -0.0025 / -0.0027 / -0.0028 | 0.842 | 0.00633 | 0.12290 | +0.00043 | [-0.0022, +0.0031] | TUONG DUONG (ke ca o Delta=0.005) |
| `no_xsec` (bo f32,f33,f34) | 42 | 0.19070 | +0.00171 | 0.00101 | [-0.0002, +0.0037] | [-0.0004, +0.0038] | +0.0001 / -0.0004 / -0.0006 | 0.947 | 0.00620 | 0.12082 | -0.00165 | [-0.0046, +0.0013] | TUONG DUONG |
| **`no_oi_no_xsec`** (tap "san sang 2020") | **37** | **0.19096** | **+0.00196** | 0.00302 | [-0.0040, +0.0077] | [-0.0044, +0.0083] | -0.0028 / -0.0044 / -0.0053 | **1.000** | 0.00743 | 0.11964 | -0.00283 | [-0.0084, +0.0028] | **TUONG DUONG** |
| `oi_only` (chi 5 OI) | 5 | 0.09615 | **-0.09284** | 0.01719 | [-0.1279, -0.0602] | [-0.1289, -0.0568] | -0.1191 / -0.1289 / -0.1318 | 0.947 | 0.00118 | 0.12114 | -0.00132 | [-0.0306, +0.0280] | **KEM HON RO** |
| `p_old` (ban DA DEPLOY) | 45 | 0.16752 | -0.02147 | 0.00801 | [-0.0375, -0.0056] | [-0.0383, -0.0047] | -0.0354 / -0.0383 / -0.0374 | 1.000 | 0.00200 | 0.08016 | -0.04231 | [-0.0664, -0.0182] | loai tru 0 (kem hon), nhung CI khong nam tron duoi -0.010 => o le 0.010: KHONG KET LUAN |

`rho` theo nam cua hai bien the then chot (bucket 2021 chi co **3,612 dong** — khong co y nghia):

| bien the | 2021 (n=3,612) | 2022 | 2023 | 2024 |
|---|---:|---:|---:|---:|
| `full45` | 0.2382 | 0.1939 | 0.1714 | 0.2111 |
| `no_oi` | 0.2401 | 0.1900 | 0.1771 | 0.2135 |
| `p_old` | 0.1807 | 0.1570 | 0.1647 | 0.1985 |

---

## 5. AP DUNG HOP DONG §5.3 CHO `no_oi`

| dieu kien | yeu cau | do duoc | ket qua |
|---|---|---|---|
| **(A)** `rho` | `wide_lo > -0.010` o CA 3 do dai khoi | -0.0040 / -0.0056 / -0.0065 | **DAT** |
| (A) o `Delta = 0.005` (bien do bo sung) | | truot o 72h va 168h (`k*sd = 0.00597 > 0.005`) | khong dat |
| (A) o `Delta = 0.020` | | dat | dat |
| **(B)** don dieu + dau theo nam | `mono20 >= 0.95`, `rho` > 0 ca 4 nam | 1.000; 0.1771..0.2401 | **DAT** |
| **(C)** chat luong hang admit | `wide_lo(d q_m) > -0.0050` | -0.00656 (`k*sd = 0.00552 > 0.0050`) | **KHONG DAT — khoang qua rong => KHONG KET LUAN DUOC** |
| (C) bang admit-rate | native trong `[0.001, 0.004]` | 0.00737 | **khong dat** (xem duoi) |
| **(D)** doi chung am | 2/2 khong phan biet duoc | dat | **DAT** |
| **(E)** cong tai lap | `|rho(full45) - 0.1675| <= 0.010` | 0.02150 | **FAIL** |

=> Theo dung hop dong: **KHONG KET LUAN DUOC**. Khong phai "bo duoc", cung khong phai "khong bo duoc".

**Ve bang admit-rate `[0.001, 0.004]`:** bang do duoc chot **neo vao admit-rate cua ban DA DEPLOY
(0.00200)**. Ban tai lap `full45` tu no da cho **0.00613** (gap 3.07 lan) vi phan bo `p` khac
(`p_mean` 0.264 / `p_std` 0.205 so voi 0.400 / 0.136 cua ban deploy) — model tai lap **tu tin hon**
nen nhieu dong lot qua nguong dong. Vi vay bang tuyet doi do **VO HIEU** cung voi cong tai lap:
so voi chinh `full45`, `no_oi` co admit-rate **1.20 lan** (0.00737 vs 0.00613), nam gon trong bang
0.5x-2x. Ghi ro de khong ai doc bang do nhu mot that bai cua `no_oi`.

**Chi phi doc lap phai bao cao:** **bat ky lan train lai G015 nao cung buoc hieu chuan lai nguong
gate.** Do that: admit-rate o cung cau hinh c2b di tu 0.200% (ban deploy) len 0.613% (ban tai lap)
va 0.737% (`no_oi`). Do la thay doi so lenh gap 3-3.7 lan, khong lien quan gi den cau hoi OI.

---

## 6. DOC KHONG PRE-REG (bat buoc ghi ro: KHONG phai ket luan pre-reg)

Cac so o muc 4 la noi-bo-nhat-quan: 9 bien the cung pipeline, cung 10 fold, cung seed 42, cung
data, chi khac tap cot. Doc theo huong do:

1. **Bo 5 feature OI khong lam kem `rho` o muc do duoc.** `d = +0.00035` — cung dau va cung do lon
   voi doi chung nhieu thuan (`|d| <= 0.00010`) cong voi nhieu train-lai (`sd = 0.00285`).
   Do phan giai that cua phep so ghep cap la **`k*sd = 0.0060`**, tuc **4.5 lan hep hon** con so
   `+-0.027` ma de bai gia dinh. Ly do: ghep cap giua hai model **chia nhau 40/45 feature**
   (`spearman(full45, no_oi) = 0.975`), khac han phep so hai model doc lap cua `CI_REAUDIT` #10.
2. **5 feature OI CO tin hieu khi dung mot minh** (`oi_only`: `rho = 0.096`) nhung **du thua hoan
   toan** khi da co 40 feature Tool1. Do la ket luan "du thua", khong phai "vo dung".
3. **Tap "san sang 2020" (`no_oi_no_xsec`, 37 feature) la bien the co `rho` CAO NHAT trong bang**
   (0.19096, `d = +0.00196`) va don dieu 20/20. Neu chi nhin `rho`, cat ca OI lan rank
   cross-sectional khong mat gi.
4. **Cau phu — 45 feature chua tung cat loc: o do phan giai NHOM, khong nhom nao la can.**
   Bo 5 OI, bo 9 funding, bo 5 basket, bo 3 rank cross-sectional: **tat ca** TUONG DUONG o le 0.010.
   Manh nhat la `no_funding` (bo **9** feature, tuc 1/5 bo feature): `d_rho = +0.00102` va chat
   luong hang admit **tang** `+0.00438` (`wide_lo = -0.0025 > -0.0050`, tuc dat le tuong duong o CA
   thuoc do van hanh). Voi mot model ten la "funding selector" thi do la phat hien dang chu y.
   **Gioi han:** day la cat **tung nhom mot** (tru `no_oi_no_xsec` la cat doi). Khong duoc suy ra
   "bo duoc dong thoi ca 22 feature".
5. **`rho` gop toan pool khong phai thuoc do xep hang thuan** — xem §2.1 diem 3. Neu du an con dung
   `rho` gop lam moc, phai biet no bi anh huong boi hieu chuan muc `p` giua cac fold.

---

## 7. NEU (VE SAU) `no_oi` DUOC CHUNG NHAN — HE QUA SO

Chi la tinh truoc, **khong** phai ket luan cua job nay (dieu kien (C)+(E) chua dat).

### 7.1 `MDE80` voi DEV 4.5 nam

Cong thuc da chot o `docs/DATA_EXTENT_SURVEY.md` §3 (`MDE80(T) = z * sd_dev * sqrt(T_dev/T)`,
`z = 2.80158`, `T_dev = 2.4941` nam), khong tinh lai:

| cap so sanh | MDE80 @ DEV 2.50 nam (nay) | **MDE80 @ DEV 4.50 nam** | giam |
|---|---:|---:|---:|
| chi doi tham so exit (`sd = 2.57pp`) | 7.20 pp | **5.36 pp** | -26% |
| chi doi selector (`sd = 4.45pp`) | 12.46 pp | **9.28 pp** | -26% |
| noi gate (`sd = 6.34pp`) | 17.76 pp | **13.22 pp** | -26% |
| bien the "lac quan" (loga ghep cap, `CI_REAUDIT` ghi la KHONG pre-reg) | 5.70 / 11.06 / 7.16 pp | **4.24 / 8.23 / 5.33 pp** | -26% |

**Van KHONG dat 3pp** o bat ky cap nao. Ket luan cua `DATA_EXTENT_SURVEY` §3 khong doi: keo dai
du lieu la mot cai thien co thuc (-26% do luong) nhung **khong doi dau bai**.

### 7.2 S1 co phai train lai khong — CO, va con hon the

- S1 dung **2** feature OI (`ls_global`, `rk_oi_delta24h` — `feataudit/SELECTOR_FEATURES.md` A.2 #8/#9).
- `feataudit` **da do**: bien the `no_oi` cua S1 (7 feature) la **khong phan biet duoc** so voi du 9
  (rank-IC `g1lite` `d = +0.0008`, CI `[-0.0062, +0.0080]`; `g1_replay` `d = -0.0011`,
  CI `[-0.0072, +0.0054]`; `edge5` `g1lite` `+0.69pp` mixed) => bo 2 feature OI o S1 khong mat gi do duoc.
- Nhung **san pham dang chay** cua S1 la bins `/home/ubuntu/predwf_map_s1a2/` (`java/dev_c2.sh:23`),
  va nguong gate cua C2b chay bang **gia tri tuyet doi** cua score G015. Vi vay muon keo DEV ve 2020-01
  thi phai lam **het** chuoi sau, khong chi train lai G015:
  1. train lai G015 40 feature (hoac 37 = `no_oi_no_xsec`) tren 2020-01..cutoff;
  2. train lai S1 7 feature va **sinh lai** `predwf_map_s1a2/` bins;
  3. **hieu chuan lai** `SIM_MIN_MOMENTUM_15M` / `AI_DYNAMIC_*` — vi admit-rate doi 3-3.7 lan (§5);
  4. do lai moi so DEV/VAL/C2b, `dyn_thr`, va cac ket qua `CI_REAUDIT` #8/#9 tren pool moi;
  5. mo rong Tool1 + label ve 2020-01 (kline/funding co san tu Vision 2020-01; chi phi tai ~4.1 GB
     nen, xem `DATA_EXTENT_SURVEY` §4 — va dia Oracle chi con ~16 G).
- Va **rui ro che do** cua `DATA_EXTENT_SURVEY` §4 van nguyen: universe 2020 chi **80 symbol** (vs
  379 nam 2024); f21/f22 la percentile/z **expanding** nen them 2020-2021 se doi phan phoi tham
  chieu cua chinh 2 feature do cho **toan bo** giai doan sau. Ket qua o muc 4 chi la **dieu kien
  can** (bo OI khong mat gi tren doan CO OI), khong phai dieu kien du.

---

## 8. CHO NAO "SU THAT NEN" DUOC CAP CHO JOB NAY BI SAI

1. **"CI cua `rho` la +-0.027 => phan lon phep so tung-feature se khong do duoc."** **Sai ve pham vi.**
   `+-0.027` la nua do rong CI cua hieu giua **hai model DOC LAP** (`CI_REAUDIT` #10: H3a vs G015).
   Voi phep so **ghep cap** giua cac bien the chia nhau phan lon feature, do phan giai that do duoc o
   job nay la **`k*sd = 0.0014` den `0.0060`** (`no_basket` 0.0017, `no_xsec` 0.0021, `no_oi` 0.0060) —
   **hep hon 4.5 den 20 lan**. Do phan giai chi tut ve ~0.017-0.018 khi hai model **thuc su khac nhau**
   (`oi_only`). => Cat **tung feature** rat co the do duoc; khong can gioi han o do phan giai NHOM.
   (Job nay van lam theo NHOM vi da chot pre-reg nhu vay.)
2. **"Bản `_1m` là bản THẬT đã deploy".** Khong xac minh duoc, va **code sinh ra bins da deploy
   khong con ton tai**: bins co mtime 2026-08-14 15:03; `/home/ubuntu/claudedata/gen_funding_wf_predictions_1m.py`
   co mtime 2026-08-10 23:24 (hop le ve thoi gian) nhung ban trong `/home/ubuntu/sel1m_code/` da bi
   sua 2026-08-16 09:53 va 15:36, va **du lieu Tool1 2021 da bi xuat lai 2026-08-16 08:36**. Job nay
   ap dung dung recipe ma `docs/archive/.../wfo_train_data_recipe_and_golive_gap_2026-08-16.md`
   ghi lai, va van khong tai lap duoc diem uoc luong. **Moc 0.1675 hien khong tai lap duoc.**
3. **"16 fold WFO expanding".** Dung cho **lan sinh** (`predwf_G015x26` co 16 file, tai lieu khac ghi
   18 fold cho `G015x26e`), nhung pool cham diem DEV chi dung **10 fold**
   (`research/pipeline/ledger3.py:26-28` loai `20240701`/`20241001` = VALIDATION). Job nay train dung
   **10 fold** — do la tap sinh ra chinh 15,442,092 dong co `p_g015`.
4. **"rho theo nam 0.1807/0.1570/0.1647/0.1985".** Bucket **2021** chi co **3,612 dong**
   (0.023% pool, = 7 gio dau tien do lech GMT+7 cua cutoff 20220101). Con so 0.1807 khong phai
   "nam 2021" — no la 7 gio. Tai lap dung nhung khong duoc doc nhu mot nam.
5. **"grid 15m".** Dung o muc hang du lieu, nhung header cua chinh file Tool1 khai `stepMin = 1`
   (ts cach nhau 15 buoc 1 phut). Loc `ts % 15m == 0` la no-op tren dataset nay. Khong anh huong ket
   qua, ghi de khong ai doi nham.
6. **`OI_SCOPE_REPORT.md` van con ket luan sai** (nhu de bai canh bao) — job nay dung dung ban SACH:
   `oi_percoin_full.bin` sha256 `e3887f63...b305ec`, 4,227,723,300 B, **kernel da log va so khop hash
   ngay trong lan chay** (`assert`), va **khong rebuild**.

---

## 9. TAI LIEU / TAI LAP

| thu | duong dan |
|---|---|
| tien dang ky | `docs/PREREG_G015CUT.md` @ 9db99ef |
| kernel train | `chuyendinh/g015-cut-a`, `chuyendinh/g015-cut-b` (`research/kaggle/g015cut/run.py`) |
| pool cham diem | dataset Kaggle `chuyendinh/g015cut-pool` (15,442,092 dong, trich tu `ledger/cand_dev3.parquet`, KHONG ghi de) |
| script cham diem + CI | `/home/ubuntu/g015/analyze.py`, `/home/ubuntu/g015/report2.py` |
| ket qua tho | `/home/ubuntu/g015/g015cut_final.json`, `g015cut_table.csv`, `report.out` |
| prediction theo thu tu pool | `/home/ubuntu/g015/out_g015-cut-{a,b}/pred_<bien the>.npy` (float32, 15,442,092 dong) |
| chan doan theo fold | `/home/ubuntu/g015/folddiag.py` -> `bg_fd.log` |

Khong ghi de: `predwf_G015*`, `predwf_map_s1a2/`, `ledger/*`, `featv2/feat_v2.parquet`.
Khong chay java, khong backtest, khong rebuild OI, khong cham `/home/ubuntu/{gs,fs,tick,feataudit}/`.
