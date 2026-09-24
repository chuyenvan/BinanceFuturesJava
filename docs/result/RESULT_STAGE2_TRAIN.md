# RESULT_STAGE2_TRAIN — Stage 2 (train 6 bien the feature) — ket qua

**Ngay:** 2026-09-24 · **Chi nhanh:** `module` · **Trang thai:** DO XONG (train+predict+bins; **KHONG sim**)
**Tien dang ky (chot TRUOC, da commit truoc khi push kernel):** `docs/prereg/PREREG_STAGE2_FEATVAR.md` — commit `dd27c6c`
**Code:** `dd27c6c` (pre-reg + fs_v4..v9) · `32ef0af` (trainer `--add-feats`/`--arms`, build prefeat, kernel, cham diem)
**Kernel:** `chuyendinh/g015p2-stage2-featvar-gpu` (Kaggle GPU, private) · dataset moi `chuyendinh/funding-prefeat-stage2`
**Pham vi:** 16 fold DEV `20220101..20251001` · **KHONG cham 2026/HoldoutSeal** · KHONG cham ONNX/LIVE · KHONG push git · Kaggle ↔ Kaggle (khong tron Oracle)

---

## 0. Tra loi ngan

`k = 6` · he so no rong CI = `c3_rates.inflate(6)` = **1.893018** (khong hardcode) · block 72h · 2000 rep · seed 20260905

| Bien the | Vector | so cot | file version | so fold xong | rank-IC (mean) | lift@8 (mean) | hon V0? | khac V5? | **KET** |
|---|---|---:|---|---:|---:|---:|---|---|---|
| **V0** | 21 keeper (MOC) | 21 | `fs_v4_21.json` | 16/16 | -0.047526 | +0.105444 | - | - | MOC |
| **V1** | 21 + ca 5 | 26 | `fs_v5_26.json` | 16/16 | -0.052018 | +0.109101 | co | khong | NULL |
| **V2** | 21 + {mom7d,mom30d} | 23 | `fs_v6_23.json` | 16/16 | -0.047863 | +0.107205 | khong | khong | NULL |
| **V3** | 21 + {rvol7d} | 22 | `fs_v7_22.json` | 16/16 | -0.052802 | +0.109328 | co | khong | NULL |
| **V4** | 21 + {daysSinceHigh30D,oi_delta7d} | 23 | `fs_v8_23.json` | 16/16 | -0.047826 | +0.104722 | khong | khong | NULL |
| **V5** | 21 + 5 + 5 NHIEU | 31 | `fs_v9_31.json` | 16/16 | -0.051858 | +0.108477 | - | - | DOI CHUNG NHIEU |

**Ket luan theo luat §4 pre-reg:** **NULL** — khong bien the nao dong thoi hon V0 VA khac V5 ngoai CI ⇒ giu nguyen **21 keeper**.

---

## 1. Cong du lieu / tinh dung dan (phai PASS truoc khi doc so)

- **CROSS_ARM `n_train`/`pos`/`spw`/`n_oos`** giua 6 arm x 16 fold: **KHOP TUYET DOI**
- Moc V0 fold 20220101: `n_train=3730472` · `pos=0.26989` · `spw=2.705276` · `n_oos=1123854`
- Tien trinh train (hit cua cot append theo nam): `[[3771001, 3772469], [4722609, 4727216], [6413996, 6414388], [9477503, 9482490], [15163922, 15193408]]`
- `num_feature` tung arm: V0=21, V1=26, V2=23, V3=22, V4=23, V5=31
- **Cong tai lap du lieu (doi chieu ban deploy):** fold `20220101` cho `pos=0.26989` · `spw=2.705276` — khop moc deploy da tai lieu hoa (`0.2699` / `2.70527601`, `docs/plan/PREP_STAGE2_TRAIN.md` §1.3) ⇒ tap dong/nhan/split cua vong nay DUNG la cua net015-45, chi khac vector cot.
- `spw` tang dan theo fold (2.705276 → 4.287861) — khop quy luat expanding (pos 0,2699 → 0,1891).
- `drop_cols` tung arm va `base_trainer_sha256`: xem `net_train_summary.json` cua tung arm.

---

## 2. Bang chinh — rank-IC + lift@8 (OOS, gop 16 fold, CI paired block-72h x `inflate(k)`)

### 2.1 So tuyet doi theo bien the

| Bien the | n_tick | so coin/tick | rank-IC | CI raw | CI x inflate | lift@8 | CI raw | CI x inflate |
|---|---:|---:|---:|---|---|---:|---|---|
| V0 | 140238 | 255.2 | -0.047526 | [-0.050367, -0.044451] | [-0.052904, -0.041705] | +0.105444 | [+0.100095, +0.110813] | [+0.095319, +0.115608] |
| V1 | 140238 | 255.2 | -0.052018 | [-0.055278, -0.048546] | [-0.058189, -0.045446] | +0.109101 | [+0.103938, +0.114268] | [+0.099327, +0.118882] |
| V2 | 140238 | 255.2 | -0.047863 | [-0.051058, -0.044601] | [-0.053912, -0.041688] | +0.107205 | [+0.102015, +0.112399] | [+0.097381, +0.117037] |
| V3 | 140238 | 255.2 | -0.052802 | [-0.056140, -0.049346] | [-0.059121, -0.046260] | +0.109328 | [+0.103901, +0.114612] | [+0.099055, +0.119331] |
| V4 | 140238 | 255.2 | -0.047826 | [-0.050684, -0.044770] | [-0.053237, -0.042041] | +0.104722 | [+0.099286, +0.110200] | [+0.094432, +0.115092] |
| V5 | 140238 | 255.2 | -0.051858 | [-0.055099, -0.048322] | [-0.057994, -0.045165] | +0.108477 | [+0.103215, +0.113627] | [+0.098517, +0.118226] |

### 2.2 Doi dau (paired, theo tung tick) — luat quyet dinh §4

| Bien the | Δrank-IC vs V0 [CI x inflate] | Δrank-IC vs V5 (nhieu) [CI x inflate] | Δlift@8 vs V0 | Δlift@8 vs V5 | hon V0 ngoai CI? | khac V5 ngoai CI? |
|---|---|---|---|---|---|---|
| V1 | -0.004491 [-0.006920, -0.002049] | -0.000160 [-0.000914, +0.000555] | +0.003656 [+0.000593, +0.006542] | +0.000624 [-0.000681, +0.001968] | True | False |
| V2 | -0.000336 [-0.002452, +0.001666] | +0.003995 [+0.002073, +0.005915] | +0.001760 [-0.000967, +0.004533] | -0.001272 [-0.003638, +0.000959] | False | False |
| V3 | -0.005275 [-0.007349, -0.003182] | -0.000944 [-0.002587, +0.000760] | +0.003884 [+0.001488, +0.006306] | +0.000851 [-0.001443, +0.003170] | True | False |
| V4 | -0.000299 [-0.001468, +0.000890] | +0.004032 [+0.001696, +0.006271] | -0.000723 [-0.002890, +0.001312] | -0.003755 [-0.006665, -0.000644] | False | False |
| V5 | -0.004332 [-0.006828, -0.001786] | n/a | +0.003032 [+0.000048, +0.005818] | n/a | True | None |

### 2.3 rank-IC theo TUNG FOLD (16 fold × 6 bien the)

| fold | V0 | V1 | V2 | V3 | V4 | V5 |
|---|---:|---:|---:|---:|---:|---:|
| 20220101 | -0.041660 | -0.048316 | -0.043599 | -0.044674 | -0.039562 | -0.050736 |
| 20220401 | -0.029599 | -0.033952 | -0.030377 | -0.035810 | -0.030944 | -0.033294 |
| 20220701 | -0.045613 | -0.056673 | -0.051026 | -0.056588 | -0.048667 | -0.056607 |
| 20221001 | -0.036712 | -0.046931 | -0.037900 | -0.043587 | -0.036870 | -0.046506 |
| 20230101 | -0.050796 | -0.052995 | -0.051603 | -0.055939 | -0.051485 | -0.052225 |
| 20230401 | -0.066943 | -0.069325 | -0.065119 | -0.071228 | -0.066399 | -0.068154 |
| 20230701 | -0.030565 | -0.033270 | -0.029983 | -0.034830 | -0.030643 | -0.032714 |
| 20231001 | -0.044263 | -0.048235 | -0.046749 | -0.048879 | -0.045454 | -0.049004 |
| 20240101 | -0.056974 | -0.054564 | -0.053577 | -0.057643 | -0.056470 | -0.054006 |
| 20240401 | -0.040494 | -0.041975 | -0.035849 | -0.044151 | -0.040233 | -0.041730 |
| 20240701 | -0.046567 | -0.053067 | -0.047735 | -0.054519 | -0.047777 | -0.053040 |
| 20241001 | -0.058832 | -0.061575 | -0.057091 | -0.064686 | -0.056841 | -0.060830 |
| 20250101 | -0.064603 | -0.068041 | -0.063310 | -0.070032 | -0.064933 | -0.067823 |
| 20250401 | -0.041998 | -0.049179 | -0.044372 | -0.048450 | -0.043127 | -0.049139 |
| 20250701 | -0.047840 | -0.055220 | -0.051314 | -0.053865 | -0.048571 | -0.055164 |
| 20251001 | -0.057253 | -0.059124 | -0.056409 | -0.060134 | -0.057477 | -0.058936 |

| fold | lift@8 V0 | lift@8 V1 | lift@8 V2 | lift@8 V3 | lift@8 V4 | lift@8 V5 |
|---|---:|---:|---:|---:|---:|---:|
| 20220101 | +0.032689 | +0.048184 | +0.048806 | +0.041456 | +0.039315 | +0.043453 |
| 20220401 | +0.042201 | +0.048788 | +0.047371 | +0.046597 | +0.041098 | +0.049361 |
| 20220701 | +0.052547 | +0.060615 | +0.057048 | +0.062610 | +0.048599 | +0.059921 |
| 20221001 | +0.080125 | +0.087074 | +0.085263 | +0.085390 | +0.079375 | +0.088914 |
| 20230101 | +0.074571 | +0.079895 | +0.077986 | +0.080300 | +0.073385 | +0.082311 |
| 20230401 | +0.106771 | +0.110992 | +0.109346 | +0.107229 | +0.106585 | +0.108488 |
| 20230701 | +0.144890 | +0.149448 | +0.147197 | +0.146858 | +0.140502 | +0.148018 |
| 20231001 | +0.131256 | +0.143711 | +0.137455 | +0.139776 | +0.130081 | +0.142593 |
| 20240101 | +0.125840 | +0.127572 | +0.125511 | +0.128659 | +0.127843 | +0.129103 |
| 20240401 | +0.120122 | +0.120852 | +0.117604 | +0.119865 | +0.119292 | +0.119578 |
| 20240701 | +0.098745 | +0.100528 | +0.098971 | +0.102311 | +0.096353 | +0.098249 |
| 20241001 | +0.086571 | +0.086089 | +0.088866 | +0.089631 | +0.081541 | +0.088597 |
| 20250101 | +0.113348 | +0.112002 | +0.104812 | +0.119410 | +0.108458 | +0.109934 |
| 20250401 | +0.119570 | +0.122675 | +0.121144 | +0.121802 | +0.124936 | +0.121373 |
| 20250701 | +0.177694 | +0.179732 | +0.179435 | +0.181119 | +0.182393 | +0.176519 |
| 20251001 | +0.177895 | +0.165342 | +0.166290 | +0.174046 | +0.173664 | +0.167054 |

| fold | n_tick | so coin/tick (V0) |
|---|---:|---:|
| 20220101 | 8640 | 130.1 |
| 20220401 | 8729 | 134.2 |
| 20220701 | 8832 | 134.6 |
| 20221001 | 8832 | 140.7 |
| 20230101 | 8640 | 150.8 |
| 20230401 | 8736 | 174.5 |
| 20230701 | 8831 | 189.3 |
| 20231001 | 8832 | 216.6 |
| 20240101 | 8736 | 245.1 |
| 20240401 | 8736 | 258.3 |
| 20240701 | 8832 | 267.5 |
| 20241001 | 8823 | 308.1 |
| 20250101 | 8640 | 353.7 |
| 20250401 | 8736 | 404.7 |
| 20250701 | 8831 | 461.8 |
| 20251001 | 8832 | 510.4 |

---

## 3. Doi chung NHIEU — V0 vs V5 (bai hoc OFI: 'them cot != them tin hieu')

- `Δrank-IC(V5 − V0)` = **-0.004332**, CI x inflate = **[-0.006828, -0.001786]** ⇒ **CI NGOAI 0 theo CHIEU MANH HON** ⇒ **P1 SAI**: hieu ung 'them cot' KHONG den tu noi dung feature
- `Δlift@8(V5 − V0)` = +0.003032, CI x inflate = [+0.000048, +0.005818]

---

## 4. Doi chieu DU DOAN KHOA TRUOC (pre-reg §5)

| # | Du doan | Ket qua |
|---|---|---|
| P1 | V5 (nhieu) khong hon V0 ngoai CI o rank-IC | **SAI** ⇒ theo pre-reg §5: vong nay **NULL / khong do duoc**, giu 21 keeper + phai dieu tra subset-selection-bias |
| P2 | \|Δ(V1−V5)\| < \|Δ(V1−V0)\| (neu V1 'thang' thi phan lon la do them cot/mask) | DUNG |
| P3 | Ket cuc NULL cho V1..V4 | DUNG |
| P4 | n_train/pos/spw/n_oos khop tuyet doi giua 6 bien the | DUNG |
| P5 | V3 (rvol7d) la ung vien sang nhat nhung van khong vuot §4 | rank-IC Δ vs V0 = -0.005275 ⇒ VUOT V0; Δ vs V5 = -0.000944 ⇒ khong tach duoc khoi V5 |

> **LAM RO SAU KHI XEM SO (KHONG sua pre-reg):** pre-reg §4 viet "CI khong chua 0 VA **cUNG DAU DUONG**".
> Cau do viet theo quy uoc `IC > 0`. Do duoc: **rank-IC cua MOI bien the deu AM** (giong Stage 0 —
> momentum/vol dai han tuong quan AM voi `retEnd_4h`), nen "HON" phai doc la **|IC| LON HON = AM HON**.
> Bang §2.2 o tren dung ban doc theo **chieu tot len** (`huong_tot`). Neu doc **CHU NGHIA** (dau duong)
> thi khong bien the nao 'hon V0' ca — **ket cuc NULL khong doi** (V1/V3/V5 deu AM HON V0, tuc la
> "khong duong" theo chu nghia). Ca hai ban doc deu cho **cung mot ket luan §0**. Khong doi tieu chi/nguong/k.

---

## 5. Model + bins — noi luu (de Stage 3 dung lai)

- **Kernel output (nguon chinh, con nguyen tren Kaggle):** `https://www.kaggle.com/code/chuyendinh/g015p2-stage2-featvar-gpu` (tab Output) và API `GET /api/v1/kernels/output?userName=chuyendinh&kernelSlug=g015p2-stage2-featvar-gpu`
  - `<TAG>/model_f<fidx>_4h.json` = 16 model/bien the (`fidx` = vi tri trong `CUT_DATES`, **KHONG** phai so fold deploy — khop theo CUTOFF)
  - `<TAG>/predict_wf_<cutoff>.bin` = 16 bin/bien the (26 B/rec, `>q h 4f`, `p0` = 4h); `<TAG>/net_train_summary.json`, `stage2_summary.json`, `stage2_metrics.json`, `<TAG>_perfold_ticks.parquet`
- **Backup tai may (ben vung, khong phai /tmp):** `/home/ubuntu/claudedata/stage2_featvar_out/` (173 MB: 6 thu muc model + `*_perfold_ticks.parquet` + 3 JSON summary/score/metrics + log kernel). **KHONG** tai 5,3 GB bins — bins o kernel output (tai lai bang API theo `fileName`).
- Du lieu nguon cot append: `/home/ubuntu/claudedata/prefeat_stage2/prefeat_full.parquet` (39.610.611 dong · 924 MB · sha256 `a601fef5599d12216dddbd9ff25c540109c4af76d2de89efbf188e1789d71d38`) + dataset Kaggle `chuyendinh/funding-prefeat-stage2`.
- **Bang sha256 bins tung fold × tung arm:** trong `stage2_summary.json` (khoa `sha_bin`).

| arm | so fold co bin | sha256 bin fold dau (vi du) |
|---|---:|---|
| V0 | 16 | `86232d9a18fc6402...` (20220101) |
| V1 | 16 | `6b62601cac086180...` (20220101) |
| V2 | 16 | `b1aa517123e1f335...` (20220101) |
| V3 | 16 | `4290a7db68b5c946...` (20220101) |
| V4 | 16 | `4ac79ef6b5a4ab6a...` (20220101) |
| V5 | 16 | `945ca85018c87862...` (20220101) |

- **KHONG** ghi de `/home/ubuntu/claudedata/predwf_G015/model_f*_4h.json` (ban deploy 2026-08-14) va **khong** cham `shadow_c3/*.onnx`.

---

## 6. De xuat Stage 3 (chay tren Kaggle, khong phai o day)

1. `c4_build_map.py s1a2x1` cho tung bien the (`<TAG>/predict_wf_*.bin` -> bins S1-order) — **dung dung 16 bins** `20220101..20251001` (fold 2026 KHONG dua vao).
2. Dataset + sim 48 thang tren **Kaggle** (khong tron Oracle), moi bien the mot arm.
3. Cham bang `research/analysis/x1_rates.py --k 6`: 5 rate (`win%`/`TSloss%`/`mP|SM`/`mP|SL`/`meanP`) + rao cung `RISK_APPETITE.md §7` (`maxDD<=40%`, quy xau nhat `>=-20%`, `UW<=250`, tap trung 1 coin `<=15%`, khong nam am) + `maxDD` do bang **MTM moc phut**. `n` va `mMargin` **khong** phai quality rate.
4. Chi ket luan khi **>= 2 rate ngoai CI**; neu khong ⇒ NULL, giu 21 keeper. Neu 1 bien the GIU o tang rank-IC thi **uu tien** no cho sim (tiet kiem slot).

---

## 7. Ghi chu co che / sai lech

- `oi_delta7d` (idx 49) **gan nhu NaN trong 2021** (do OI 5m offline chi bat dau giua 2021): tren ma tran nam 2021 do duoc **92,3 % NaN**. He qua: o fold 0 (train = 2021) bien the co cot nay (V1/V4) **thuc chat khong duoc them thong tin OI**; V5 (nhieu cung mask) do do cung ‘trong’ tuong ung ⇒ phep so V1/V4 vs V5 o fold 0 gan nhu so 21 vs 21.
- `mom30d`/`daysSinceHigh30D` NaN ~4,5 % (warmup + coin moi list) — nhu Stage 0.
- Tap dong KHONG doi khi them cot (join trai + NaN, va `--drop-cols` chi cat cot): da assert.
- Multiplicity **k = 6** ap cho **ca hai** chieu so (vs V0 va vs V5) — khong noi `k` sau khi xem so.
- **Co che do duoc (quan trong nhat vong nay):** 3 bien the CO cot append (V1 +5 that / V3 +1 that / V5 +5 nhieu) deu dich rank-IC ve cung mot phia voi do lon tuong duong; 2 bien the chi +2 cot that (V2, V4) gan nhu khong dich. ⇒ Phan 'thang' KHONG quy duoc cho noi dung 5 feature.
- `lift@8` cua MOI bien the deu duong lon (~+0,105) va chenh nhau rat it ⇒ thuoc nay khong phan biet duoc arm.
- CI o tang rank-IC dung cung hang so `c3_rates` nhu `x1_rates.py` ⇒ nhat quan giua Stage 2 va Stage 3.

---

## 8. Gioi han / phan CHUA chay

- **16/18 fold**: 2 fold `20260101`/`20260401` **KHONG** chay (HoldoutSeal 2026-01-01).
- **Chua sim**: moi ket luan kinh te (PnL) de Stage 3. rank-IC + lift@8 **khong** du de doi model.
- Nhan do = `retEnd_4h` (ban lien tuc cua nhan train `retEnd_4h > 0,015`), khong dung `maxFav`.
- `lift@8` dung top-8 theo `p0` **trong tung tick** — proxy cua selector, khong phai PnL.

*Sinh boi `research/analysis/stage2_report.py` tu artifact kernel.*
