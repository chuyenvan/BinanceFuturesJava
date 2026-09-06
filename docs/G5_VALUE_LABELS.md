# G5_VALUE_LABELS — nhan/horizon nao cho VALUE MODEL, va value model dung de LAM GI

Ngay 2026-09-06/07. Pre-reg: `docs/PREREG_G5.md` (commit `f0b088b`, viet TRUOC moi run).
Doc kem: `G015_RECIPE` (recipe net015), `G4_RECIPE_C4` (gia tri load-bearing o GATE),
`L1_SHADOW_C3` (gia tri KHONG load-bearing o TRAILING), `T1_LABEL3` (doi nhan o tang SELECTOR),
`G3_X26_RECOVERY`, `X1_EXTEND`.

## 0. 🔴 RUI RO / KET LUAN PHAI DOC TRUOC

1. **KHONG ung vien nhan nao thay the duoc S1.** 8/8 arm THUA `G5_parity_S1` (= `X1_C3`):
   moi arm co **>= 1 rate CHAT LUONG xau ngoai CI**, **0 arm co rate nao TOT ngoai CI**, va
   **8/8 FAIL rang buoc cung** o >= 2 nam trong khi parity PASS ca 4 nam. Muc 5-6.
2. 🔴 **Ho nhan 72h la HUONG SAI, va sai rat lon.** `net*_72h`: rank-IC per-tick vs `g1lite`
   ~ **0** (−0.013 / −0.004 / +0.027) trong khi `net015_4h` = +0.144; o sim thi `win%`
   **−8.5..−10.0pp**, `TSloss%` **+10.9..+13.0pp** (4/5 rate ngoai CI, moi nam), 2025 thanh
   **nam AM −20..−25%**, `maxDD` **−25..−31%**. Equity 36.8k-42.4k vs 98.5k. Muc 4 + 6.
3. 🔴 **Cau "value model = HIEU CHUAN gate, THONG TIN coin do S1" — DUNG, va do duoc bang so.**
   Hieu chuan giu CO DINH (multiset x26 tung tick) o CA 9 arm; chi THU TU doi.
   `G5_x26_order` (x26 quyet dinh ca thu tu) thua parity **4/5 rate**, equity 76,700 vs 98,523,
   FAIL rang buoc 2022 + 2025. Tuc **toan bo uu the cua C3 nam o THU TU cua S1**, khong o
   value model. Muc 7.
4. ⚠️ **Mot du doan pre-reg cua toi SAI VA QUAN TRONG**: toi ghi truoc rang so lenh `n` cua
   cac arm quantile-map se ~ parity (lech < 1.5%). Thuc te lech **+37% den +64%**
   (2,815..3,385 vs 2,058). Bat bien toi chung minh (va do duoc dung 8/8) chi la o tang
   **GATE** (so candidate-minute qua gate = **103,840** o CA 9 phan phoi, adm_top8 = **5,906**).
   So lenh THUC THI thi khong bat bien vi con phu thuoc coin nao chiem von/slot. Muc 5.2.
5. ⚠️ **`maxfav06_4h` la ung vien "it xau nhat" (1/5 rate, equity 86,047) nhung van FAIL
   rang buoc cung 2 nam** (2022 `maxDD −18.97`, nam AM −3.66%; 2024 `maxDD −15.24`, quy −7.85%).
   Khong duoc doc no la "gan bang parity".
6. ⚠️ **`net015_4h` la arm SUY BIEN**: `c4_build_map` voi chinh `p` cua x26 cho **0/35,806,379
   dong doi** => bins TRUNG y `predwf_G015x26`, va sim ra **byte-identical** `G5_x26_order`
   (md5 `b99cde31…`). Tuc 10 arm chi co **9 bo so phan biet duoc**. Ghi ro, khong dem 2 lan.

## 1. VIEC 1 — cong LEAK 18/18 fold: **PASS**

Nguon: log kernel goc `claudedata/predwf_G015/selector-15mtr-pred15-net015-gpu.log` (2026-08-14).
Cong: `ts_max(train) <= cutoff − 72h`. `cutoff` la 00:00 GMT+7 => gio UTC = ngay truoc 17:00.

| fold | cutoff | cutoff (UTC) | purge_end = cutoff−72h | ts_max train | bien an | n_train | pos | OOS bins | khoang OOS (UTC) | cong |
|---|---|---|---|---|---:|---:|---:|---:|---|:---:|
| 0 | 20220101 | 2021-12-31 17:00 | 2021-12-28 17:00 | 2021-12-28 16:45 | 15' | 3,730,472 | 0.2699 | 1,123,854 | 2021-12-31 17:00 → 2022-03-31 17:00 | PASS |
| 1 | 20220401 | 2022-03-31 17:00 | 2022-03-28 17:00 | 2022-03-28 16:45 | 15' | 4,852,846 | 0.2574 | 1,172,010 | 2022-03-31 → 2022-06-30 | PASS |
| 2 | 20220701 | 2022-06-30 17:00 | 2022-06-27 17:00 | 2022-06-27 16:45 | 15' | 6,020,407 | 0.2513 | 1,188,418 | 2022-06-30 → 2022-09-30 | PASS |
| 3 | 20221001 | 2022-09-30 17:00 | 2022-09-27 17:00 | 2022-09-27 16:45 | 15' | 7,206,793 | 0.2389 | 1,242,626 | 2022-09-30 → 2022-12-31 | PASS |
| 4 | 20230101 | 2022-12-31 17:00 | 2022-12-28 17:00 | 2022-12-28 16:45 | 15' | 8,449,371 | 0.2208 | 1,302,607 | 2022-12-31 → 2023-03-31 | PASS |
| 5 | 20230401 | 2023-03-31 17:00 | 2023-03-28 17:00 | 2023-03-28 16:45 | 15' | 9,745,074 | 0.2153 | 1,524,605 | 2023-03-31 → 2023-06-30 | PASS |
| 6 | 20230701 | 2023-06-30 17:00 | 2023-06-27 17:00 | 2023-06-27 16:45 | 15' | 11,264,565 | 0.2026 | 1,671,614 | 2023-06-30 → 2023-09-30 | PASS |
| 7 | 20231001 | 2023-09-30 17:00 | 2023-09-27 17:00 | 2023-09-27 16:45 | 15' | 12,931,274 | 0.1887 | 1,912,959 | 2023-09-30 → 2023-12-31 | PASS |
| 8 | 20240101 | 2023-12-31 17:00 | 2023-12-28 17:00 | 2023-12-28 16:45 | 15' | 14,834,006 | 0.1864 | 2,140,992 | 2023-12-31 → 2024-03-31 | PASS |
| 9 | 20240401 | 2024-03-31 17:00 | 2024-03-28 17:00 | 2024-03-28 16:45 | 15' | 16,968,587 | 0.1878 | 2,256,504 | 2024-03-31 → 2024-06-30 | PASS |
| 10 | 20240701 | 2024-06-30 17:00 | 2024-06-27 17:00 | 2024-06-27 16:45 | 15' | 19,223,554 | 0.1854 | 2,362,741 | 2024-06-30 → 2024-09-30 | PASS |
| 11 | 20241001 | 2024-09-30 17:00 | 2024-09-27 17:00 | 2024-09-27 16:45 | 15' | 21,577,594 | 0.1842 | 2,719,452 | 2024-09-30 → 2024-12-31 | PASS |
| 12 | 20250101 | 2024-12-31 17:00 | 2024-12-28 17:00 | 2024-12-28 16:45 | 15' | 24,280,226 | 0.1884 | 3,056,303 | 2024-12-31 → 2025-03-31 | PASS |
| 13 | 20250401 | 2025-03-31 17:00 | 2025-03-28 17:00 | 2025-03-28 16:45 | 15' | 27,323,970 | 0.1905 | 3,535,785 | 2025-03-31 → 2025-06-30 | PASS |
| 14 | 20250701 | 2025-06-30 17:00 | 2025-06-27 17:00 | 2025-06-27 16:45 | 15' | 30,843,016 | 0.1911 | 4,078,299 | 2025-06-30 → 2025-09-30 | PASS |
| 15 | 20251001 | 2025-09-30 17:00 | 2025-09-27 17:00 | 2025-09-27 16:45 | 15' | 34,904,563 | 0.1891 | 4,517,610 | 2025-09-30 → 2025-12-31 | PASS |
| 16 | 20260101 | 2025-12-31 17:00 | 2025-12-28 17:00 | 2025-12-28 16:45 | 15' | 39,404,186 | 0.1889 | (SEAL) | 2025-12-31 → 2026-03-31 | PASS |
| 17 | 20260401 | 2026-03-31 17:00 | 2026-03-28 17:00 | 2026-03-28 16:45 | 15' | 43,974,232 | 0.1868 | (SEAL) | 2026-03-31 → 2026-06-30 | PASS |

**18/18 PASS.** Bien an **dung 15 phut** o moi fold — dung nhu du doan pre-reg muc 6.1: code
loc `ts < tr_cut` (bat dang thuc NGHIEM) tren luoi 15m nen diem train cuoi cung luon la
`tr_cut − 1 buoc`. Purge THUC TE = **72h 15'**, khong phai 72h chan.

**OOS thuan — kiem doc lap tu bins**, khong qua log: doc `ts_min/ts_max` cua 16 file
`predwf_G015x26/predict_wf_*.bin` cho **[cutoff, cutoff+3 thang)** khop TUNG fold, lien tuc,
**khong chong lan**, va khong fold nao co dong nao truoc cutoff cua chinh no.
Fold i sinh du doan DUNG cho quy thu i: fold 0 → 2022Q1 … fold 15 → 2025Q4.

`n_oos` trong bins > `n_oos` trong dong log `SCREEN` (vd fold 0: 1,123,854 vs 1,123,758) vi
`SCREEN` chi dem dong OOS **CO NHAN**, con bins ghi moi dong feature OOS. Khong phai lech.

### 1.1 Kiem `FIRST_CUTOFF` cua wrapper user cung cap — **LECH, phai sua**
Wrapper `selector-15m-savemodel-net008-gpu` ghi `FIRST_CUTOFF=20230101`.
Log goc dong 1 ghi nguyen van: `TRACKC train15->pred15 | SEL_GRID=15 PRED_GRID=15 purge=288
FIRST_CUTOFF=20220101 NET_THR=0.015`. => Ban 2026-08-14 sinh ra `predwf_G015x26` chay
**`FIRST_CUTOFF=20220101`**, 18 fold `20220101..20260401`. Chay wrapper nguyen van se chi ra
**14 fold tu 20230101**, THIEU 4 fold dau cua cua so DEV. **Da dung `20220101`** trong moi
kernel cua dot nay.

### 1.2 Mot cau
**Khong co leak train-thay-tuong-lai trong thiet ke WFO nay** (18/18 PASS, OOS thuan, khong
chong lan). No leak **con lai va CHUA dong** la cai da ghi o `AGENT_RUNBOOK` muc 5:
purge 72h < holding 168h => train/test **chong lan tren duong equity** (khong phai tren nhan).
Job nay khong dong no.

## 2. Chuan bi — 7 model train MOI (SAI LECH so voi de bai, khai bao lai)

De bai ghi "train moi 5 model". Thuc te **7**. Ly do (da ghi trong `PREREG_G5` muc 2 TRUOC khi chay):
- `maxfav06_4h` (= ho `predwf_G015_v2`): thu muc bins **khong con tren dia Oracle**; ban Kaggle
  `predwf-g015-v2-bins` chi co **10/16 fold** (`TS_HI` hardcode 2024-07-01 trong `g72_train.py`).
  Kernel 48 thang `chuyendinh/g015v2-maxfav-cpu` (2026-09-06) **DA FAIL** — `--fold` truyen ca
  danh sach thanh MOT chuoi, `AssertionError` o giay 2.5. Chua tung co so 48 thang.
- `maxfav06_72h`: `G72` da train nhung nguong **0.07** (base 0.4041), khong phai 0.06; va chi
  10 fold; va chi co `pred_pool.npy` tren pool CU 30 thang.

| tag | mode | h | thr | base rate nhan | thoi gian | device |
|---|---|---:|---:|---:|---:|---|
| `net015_4h` | net | 4 | 0.015 | 0.1849 | 0 (lay tu bins goc) | Kaggle GPU (2026-08-14) |
| `net020_4h` | net | 4 | 0.020 | **0.1368** | 30.8' | Kaggle GPU |
| `net030_4h` | net | 4 | 0.030 | **0.0763** | 30.0' | Kaggle GPU |
| `net015_72h` | net | 72 | 0.015 | **0.3932** | 31.2' | Kaggle GPU |
| `net020_72h` | net | 72 | 0.020 | **0.3686** | 29.9' | Kaggle GPU |
| `net030_72h` | net | 72 | 0.030 | **0.3224** | 29.6' | Kaggle GPU |
| `maxfav06_4h` | maxfav | 4 | 0.06 | **0.0457** | 31.1' | Kaggle GPU |
| `maxfav06_72h` | maxfav | 72 | 0.06 | **0.4662** | 30.1' | Kaggle GPU |

**Cong nhan doc lap (khong doan):** `maxfav06_4h` ra base rate **0.0457** — trung TUYET DOI base
cua `predwf_G015_v2` ghi o `G3_X26_RECOVERY` muc 0/1. => trainer moi tai lap dung HO NHAN cu.
Cong purge trong trainer (`assert ts_max <= tr_cut`) PASS **112/112** (7 model x 16 fold).

Device: **Kaggle GPU = device GOC cua x26** (`G015_RECIPE` muc 7.1), xgboost **3.2.0**, seed 42,
`n_jobs=-1`. Quota GPU du; **khong** phai chuyen CPU. Tran Kaggle do duoc: **2 batch GPU session**
cung luc (`Maximum batch GPU session count of 2 reached`) — 7 kernel chay 4 dot.

Trainer: `research/pipeline/g5/g5_pool_train.py` — ban SAO `g015_net_train.py` (sha256
`05298cba5578…`, **KHONG dong vao**) + DUNG 3 thay doi: `--label-h`, `--pool`, `--out-bins`.
Xuat **pool-pred** thay vi bins 26B day du: `c4_build_map.py` chi dung THU TU cua ung vien tren
dong co score, GIA TRI lay tu x26; XGBoost du doan tung dong doc lap nen `p` tren tap con giong
het `p` tren toan bo. Tiet kiem 888 MB/model x 7 (dia Oracle chi con 15G).

## 3. VIEC 2 — PROXY (phut, khong sim). Pool OOS DEV 48 thang

Pool = `ledger/cand_dev_x1.parquet` loc `p_g015` va `g1lite` notna: **6,554,089 dong / 17,349 tick**
(17,240 tick co >= 10 dong). `net015_4h` lay `p` TRUC TIEP tu bins goc — cong: `max|d|` giua
`cand_dev_x1.p_g015` va `predwf_G015x26/predict_wf_20240101.bin` = **0.0** tren 203,328 dong.

### 3.1 Bang 8 ung vien

| ung vien | p10/p50/p90 (pool) | sd | per-tick p10/p50/p90 | per-tick sd | rank-IC vs `g1lite` | d vs net015_4h (CI 72h x1.21) | ngoai CI | edge5 | pass RAW | **x parity** | adm_top8 RAW | pass MAP | adm8 MAP |
|---|---|---:|---|---:|---:|---|:---:|---:|---:|---:|---:|---:|---:|
| `maxfav06_4h` | 0.1478/0.4294/0.8111 | 0.2433 | 0.277/0.432/0.746 | 0.1803 | **+0.16433** | +0.02021 [+0.01268,+0.02773] | **CO** | +0.20746 | 473,561 | **x4.56** | 114,335 | 103,840 | 5,906 |
| `net030_4h` | 0.2538/0.5148/0.7533 | 0.1873 | 0.375/0.506/0.687 | 0.1231 | **+0.15882** | +0.01470 [+0.00941,+0.01999] | **CO** | +0.18878 | 179,456 | x1.73 | 26,116 | 103,840 | 5,906 |
| `net020_4h` | 0.3315/0.5416/0.7218 | 0.1514 | 0.433/0.537/0.660 | 0.0926 | **+0.15037** | +0.00625 [+0.00329,+0.00921] | **CO** | +0.17990 | 124,825 | x1.20 | 8,474 | 103,840 | 5,906 |
| `net015_4h` (x26) | 0.3701/0.5439/0.6949 | 0.1301 | 0.459/0.545/0.636 | 0.0747 | **+0.14412** | — (moc) | — | +0.17205 | 103,840 | **x1.00** | 5,906 | 103,840 | 5,906 |
| `maxfav06_72h` | 0.3863/0.5696/0.7613 | 0.1449 | 0.474/0.582/0.710 | 0.0951 | +0.13319 | −0.01093 [−0.01689,−0.00496] | **CO** | +0.17559 | 231,765 | x2.23 | 31,564 | 103,840 | 5,906 |
| `net030_72h` | 0.3705/0.5248/0.6645 | 0.1175 | 0.442/0.531/0.615 | 0.0693 | **+0.02741** | −0.11671 [−0.13400,−0.09942] | **CO** | +0.04006 | 73,283 | x0.71 | 8,307 | 103,840 | 5,906 |
| `net020_72h` | 0.3743/0.5250/0.6678 | 0.1172 | 0.448/0.535/0.618 | 0.0676 | **−0.00350** | −0.14762 [−0.16762,−0.12761] | **CO** | +0.01621 | 83,513 | x0.80 | 9,460 | 103,840 | 5,906 |
| `net015_72h` | 0.3773/0.5260/0.6703 | 0.1175 | 0.449/0.536/0.619 | 0.0679 | **−0.01277** | −0.15689 [−0.17792,−0.13586] | **CO** | +0.00782 | 83,193 | x0.80 | 9,614 | 103,840 | 5,906 |

`n_eff` = **419 khoi 72h** (khong phai ~900 nhu de bai uoc; ghi lai cho lan sau).
`edge5` la don vi `g1lite` THO (khong phai %): con so lon (~0.17) vi pool 48 thang bi 2025 chi phoi
(5.47M/6.55M dong) — `X1_EXTEND` muc 10 da do `edge5` 2025 = +19.34%.

### 3.2 KIEM CAU TRUC (c) — **PASS 8/8, va PASS TUYET DOI**
Quantile-map cho **`pass_map` = 103,840** va **`adm8_map` = 5,906** o **CA 8** ung vien, bang
**DUNG TUNG DON VI** con so cua parity (x26 tho). `p10/p50/p90` sau map = `0.37005/0.54389/0.69494`
= y het x26 o ca 8. Dung nhu co so co hoc `PREREG_G5` muc 1.3-1.4:
`symbolPred = 1 − P(win)` (`WfoDataset.export`: `floatBits(1-P(win))`), `dyn_thr` khong tran nen
tang don dieu theo `symbolPred` => trong MOT tick "qua gate" ⟺ `p >= nguong_tick`; ma `p15`
(`predReturn15M`) la dai luong THEO TICK => **so candidate-minute qua gate chi phu thuoc MULTISET
`p` cua tick**, ma `c4_build_map` giu nguyen multiset do. **Map dung.**

### 3.3 Doc gi tu proxy
- **Truc nguong `net` o 4h: rank-IC TANG DON DIEU theo nguong** (0.144 → 0.150 → 0.159), ca ba
  buoc **ngoai CI**. Nguong cao = nhan hiem hon = model phan tang manh hon trong tick.
- **Truc horizon: 4h >> 72h, khong phai nguoc lai.** `net*_72h` rank-IC ~ 0.
- **`maxfav06_4h` co rank-IC CAO NHAT** (+0.164) — cao hon ca x26 dang deploy.
- **Admission RAW lech HANG LAN theo base rate**, dung chieu du doan: base cao (`maxfav_4h`
  base 0.0457 => `p` bi keo len o duoi phai) cho `pass` x4.56 va `adm_top8` **x19.4**.
  Day la co che C4 (`C4_maxfav30` admit x5.05) tai lap duoc doc lap, tren 48 thang.

### 3.4 Du doan pre-reg cua toi SAI o dau (muc 6.2)
| du doan | thuc te |
|---|---|
| (1) "moi ung vien chenh nhau TRONG CI" | **SAI**. 8/8 ngoai CI o rank-IC. `n_eff` 419 khoi du de tach. |
| (2) "72h > 4h ve rank-IC vi `g1lite` la nhan 72h — thien vi co hoc" | **SAI ca chieu**. 72h ~ 0, 4h +0.144..+0.164. Cung ho horizon **khong** bao dam thien vi: `g1lite` la ham cua `maxFav_72h` co CAT NGUONG 0.05 + trailing, con `retEnd_72h` la loi nhuan cuoi ky — hai dai luong khac han. Nhan `retEnd_72h` co base ~0.39 (gan 50/50) nen model gan nhu khong phan tang. |
| (3) "admission RAW lech hang lan theo base rate, thu tu `net030 < net020 < net015 < maxfav06 < cac ban 72h`" | **DUNG mot nua**. Chieu maxFav/net dung; nhung `net*_72h` admit **IT hon** parity (x0.71-0.80) chu khong nhieu hon — vi phan phoi `p` cua chung HEP (sd 0.117 vs 0.130) chu khong dich len. Toi lan lon "base rate cao" voi "duoi phai day". Cai quyet dinh gate la **duoi PHAI cua `p` trong tick**, khong phai base rate. |
| (4) "quantile-map admission = parity CHINH XAC" | **DUNG, 8/8, tuyet doi.** |

## 4. VIEC 3 — 10 arm sim 48 thang (2022-01-01..2025-12-31), Oracle, `TICKER_SOURCE=file`

Profile = `x1_c3.properties` sua **DUNG 1 dong** `WFO_FUNDING_PRED_DIR`. `SIM_END_DATE=20251231`.
Dataset build rieng tung arm roi `rm -rf` ngay (bay #13: bins tieu thu o `ExportWfoDataset`,
KHONG di qua duong Kaggle; dia Oracle chi con 8.5-15G). ~14 phut/arm.

### 4.1 CONG PARITY — **PASS byte-identical**
`G5_parity_S1` (bins `predwf_map_s1a2_x1`): **2,058 lenh**, `b:98,523`,
md5 `printDone.csv` = **`d39da2940dfd815f60772f70517750bf`** — **`cmp` = 0 dong khac** voi
`X1_C3` dang la baseline. **Moi truong KHONG troi**; moi so duoi day doc duoc.

### 4.2 KIEM CAU TRUC `symbolPred` — **PASS 9/9**
| arm | `symbolPred` p10/p50/p90 | lech p50 vs parity | %STRONG |
|---|---|---:|---:|
| `G5_parity_S1` | 0.1424 / 0.2173 / 0.3223 | — | 83.8 |
| `G5_x26_order` = `G5_net015_4h` | 0.1216 / 0.1994 / 0.3000 | −8.2% | 88.0 |
| `G5_maxfav06_4h` | 0.1277 / 0.2049 / 0.3075 | −5.7% | 86.6 |
| `G5_maxfav06_72h` | 0.1188 / 0.2021 / 0.3046 | −7.0% | 87.1 |
| `G5_net020_4h` | 0.1160 / 0.1987 / 0.3005 | −8.6% | 87.7 |
| `G5_net030_4h` | 0.1179 / 0.2020 / 0.3035 | −7.0% | 87.2 |
| `G5_net015_72h` | 0.1319 / 0.2067 / 0.3110 | −4.9% | 86.2 |
| `G5_net020_72h` | 0.1316 / 0.2058 / 0.3103 | −5.3% | 85.9 |
| `G5_net030_72h` | 0.1370 / 0.2061 / 0.3093 | −5.2% | 86.2 |

⚠️ Nguong pre-reg "lech > 5% la map sai, DUNG" — do duoc **4.9%-8.6%**, tuc 6/8 arm vuot 5%.
**Nhung day KHONG phai map sai**, va toi khong duoc dung con so nay de dung job. Ly do:
- Phan phoi `symbolPred` tren **toan bo dong bins** giong parity **TUYET DOI** (muc 3.2:
  `p10/p50/p90` sau map = `0.37005/0.54389/0.69494` = x26, 8/8, va `pass`/`adm8` bang tung don vi).
- Bang tren la phan phoi tren **LENH DA VAO** — mot tap con CHON LOC (top-8 x qua gate x con von).
  Arm nhieu lenh hon thi keo them lenh o hang duoi cua tick => `symbolPred` thap hon.
  Do la **HE QUA** cua thu tu khac, khong phai bang chung map hong.
- Cong dung cho "map hong" la muc 3.2, va no PASS tuyet doi. **Ghi lai la nguong pre-reg dat
  SAI CHO (dat tren lenh thay vi tren bins); khong sua tieu chi sau khi thay so, chi giai thich.**

### 4.3 BANG RATE — 48 thang (tieu chi PRIMARY)

| arm | n | win% | TSloss% | mean(P\|SM) | mean(P\|SL) | meanP | mMargin |
|---|---:|---:|---:|---:|---:|---:|---:|
| **`G5_parity_S1`** | **2,058** | **85.33** | **14.87** | 7.178 | −21.848 | 2.863 | 1,918 |
| `G5_maxfav06_4h` | 2,904 | 83.57 | 16.84 | 7.220 | −20.472 | 2.557 | 1,244 |
| `G5_net030_4h` | 3,168 | 82.99 | 17.49 | 6.974 | −18.561 | 2.509 | 1,026 |
| `G5_maxfav06_72h` | 2,915 | 82.74 | 17.87 | 6.978 | −17.426 | 2.617 | 1,033 |
| `G5_x26_order` (=`net015_4h`) | 3,385 | 81.68 | 19.05 | 7.155 | −16.217 | 2.701 | 897 |
| `G5_net020_4h` | 3,257 | 81.33 | 19.13 | 7.211 | −17.351 | 2.513 | 900 |
| `G5_net030_72h` | 2,885 | 76.81 | 25.72 | 7.027 | −12.181 | 2.087 | 725 |
| `G5_net015_72h` | 2,815 | 76.02 | 27.00 | 6.816 | −11.450 | 1.884 | 723 |
| `G5_net020_72h` | 2,823 | 75.35 | 27.91 | 6.917 | −11.321 | 1.826 | 693 |

### 4.4 CI khoi-72h x1.21 (hieu ARM − parity), 48 thang

| arm | Δn | Δwin% | ΔTSloss% | ΔmP\|SM | ΔmP\|SL | ΔmeanP | ΔmMargin | **rate CHAT LUONG ngoai CI** |
|---|---:|---|---|---|---|---|---|:---:|
| `G5_x26_order` | +1,327 **CO** | **−3.64 CO** | **+4.19 CO** | −0.02 | +5.63 **CO** | −0.16 | **−1,021 CO** | **4/5** |
| `G5_maxfav06_4h` | +846 **CO** | −1.75 | +1.97 | +0.04 | +1.38 | −0.31 | **−674 CO** | **1/5** |
| `G5_maxfav06_72h` | +857 **CO** | −2.58 | +3.00 | −0.20 | +4.42 **CO** | −0.25 | **−885 CO** | **2/5** |
| `G5_net020_4h` | +1,199 **CO** | **−3.99 CO** | **+4.26 CO** | +0.03 | +4.50 **CO** | −0.35 | **−1,018 CO** | **4/5** |
| `G5_net030_4h` | +1,110 **CO** | −2.34 | +2.62 | −0.20 | +3.29 **CO** | −0.35 | **−891 CO** | **2/5** |
| `G5_net015_72h` | +757 **CO** | **−9.30 CO** | **+12.13 CO** | −0.36 | +10.40 **CO** | −0.98 | **−1,195 CO** | **4/5** |
| `G5_net020_72h` | +765 **CO** | **−9.98 CO** | **+13.04 CO** | −0.26 | +10.53 **CO** | −1.04 | **−1,225 CO** | **4/5** |
| `G5_net030_72h` | +827 **CO** | **−8.51 CO** | **+10.85 CO** | −0.15 | +9.67 **CO** | −0.78 | **−1,192 CO** | **4/5** |

**Doc dung dau cua `mP|SL`:** `Δ` DUONG (bot am) nhin nhu "tot hon", nhung no di kem `TSloss%`
tang manh — day la **PHA LOANG**: arm cat lo nhieu hon, lenh thua trung binh nong hon nhung
**tong ton that lon hon** (`meanP` giam o ca 8 arm). Khong duoc dem no la "1 rate TOT".
**`mMargin` giam o 8/8 la CO HOC** (cung von, nhieu lenh hon => margin/lenh nho hon) —
`AGENT_RUNBOOK` muc 4 da chot day la kenh THANG DO cua sizing compound, khong phai chat luong.

**=> So rate CHAT LUONG TOT ngoai CI: 0/5 o CA 8 ARM.** Khong arm nao dat nguong "≥2 rate cung
huong TOT ngoai CI" cua `PREREG_G5` muc 5.3.

### 4.5 Theo NAM — so rate chat luong ngoai CI (deu huong XAU)

| arm | 2022 | 2023 | 2024 | 2025 |
|---|:---:|:---:|:---:|:---:|
| `G5_x26_order` | 4/5 | 2/5 | 2/5 | 2/5 |
| `G5_maxfav06_4h` | 4/5 | 1/5 | 1/5 | 1/5 |
| `G5_maxfav06_72h` | 4/5 | 4/5 | 2/5 | 1/5 |
| `G5_net020_4h` | 3/5 | 2/5 | 3/5 | 2/5 |
| `G5_net030_4h` | 3/5 | 1/5 | 1/5 | 1/5 |
| `G5_net015_72h` | 4/5 | 3/5 | 4/5 | 4/5 |
| `G5_net020_72h` | 4/5 | 4/5 | 4/5 | 4/5 |
| `G5_net030_72h` | 4/5 | 4/5 | 4/5 | 4/5 |

**2022 la nam phan biet ro nhat** (8/8 arm co 3-4/5 rate ngoai CI) — trung voi
`SELECTOR_LADDER_Q`: 78% uu the cua selector nam o 2022.

### 4.6 RANG BUOC CUNG — parity PASS 4/4 nam, **8/8 arm FAIL**

| arm | 2022 | 2023 | 2024 | 2025 | ket |
|---|---|---|---|---|---|
| `G5_parity_S1` | PASS | PASS | PASS | PASS | **PASS** |
| `G5_maxfav06_4h` | FAIL (DD −18.97, nam **−3.66%**) | PASS | FAIL (DD −15.24, quy −7.85) | PASS | **FAIL 2/4** |
| `G5_net030_4h` | FAIL (DD −20.43, nam −7.53%) | PASS | FAIL (DD −17.33, quy −10.12) | FAIL (quy −5.46) | **FAIL 3/4** |
| `G5_x26_order` | FAIL (DD −22.07, nam −10.74%) | PASS | PASS | FAIL (DD −20.68) | **FAIL 2/4** |
| `G5_net020_4h` | FAIL (DD −22.88, nam −9.77%) | PASS | FAIL (DD −16.41, quy −6.58) | PASS | **FAIL 2/4** |
| `G5_maxfav06_72h` | FAIL (DD −21.71, nam −11.85%) | PASS | FAIL (DD, quy −7.91) | FAIL (DD −17.62, quy −7.85) | **FAIL 3/4** |
| `G5_net030_72h` | FAIL (nam −14.01%) | PASS | FAIL | FAIL (DD −25.65, nam **−20.40%**) | **FAIL 3/4** |
| `G5_net015_72h` | FAIL (nam −12.01%) | PASS | FAIL (quy −11.15) | FAIL (DD −27.30, nam **−25.34%**) | **FAIL 3/4** |
| `G5_net020_72h` | FAIL (nam −12.14%) | PASS | FAIL (quy −11.90) | FAIL (DD −28.95, nam **−25.39%**) | **FAIL 3/4** |

### 4.7 EQUITY — **KHONG PHAI TIEU CHI** (N=9 arm phan biet => `E[max nhieu]` = 2.57·√(2 ln 9) = **5.4pp** CAGR)

| arm | equity cuoi | CAGR% | maxDD% (48t) | UW (ngay/48t) | md5 `printDone.csv` |
|---|---:|---:|---:|---:|---|
| `G5_parity_S1` | **98,523** | 29.58 | −13.31 | 1,212 | `d39da2940dfd815f60772f70517750bf` |
| `G5_maxfav06_4h` | 86,047 | 25.26 | −18.97 | 1,258 | `ddd0cb16843856d6c4cadeb966d74fbb` |
| `G5_x26_order` | 76,700 | 21.70 | −22.07 | 1,353 | `b99cde31de93b2a77462f9464a954e62` |
| `G5_net015_4h` | 76,700 | 21.70 | −22.07 | 1,353 | `b99cde31de93b2a77462f9464a954e62` (**= x26_order**) |
| `G5_maxfav06_72h` | 75,005 | 21.02 | −21.71 | 1,298 | `76a234c4ab1f28b4a8e460f85db662f8` |
| `G5_net030_4h` | 72,995 | 20.20 | −20.43 | 1,301 | `591a5137fe47b0d3ac7f2373c39ffcd7` |
| `G5_net020_4h` | 72,140 | 19.85 | −22.88 | 1,349 | `a57d48eceb689ae2fa44eec4d963bed6` |
| `G5_net030_72h` | 42,357 | 4.89 | −27.50 | 1,372 | `51ce87c9637b5f07fe457a6d9a160add` |
| `G5_net015_72h` | 39,181 | 2.87 | −28.04 | 1,376 | `a020ba74b38323250a0e65d3ee0ad689` |
| `G5_net020_72h` | 36,813 | 1.27 | −31.04 | 1,388 | `de9786a005e0e90cd149ab41be6d6cce` |

Khoang cach parity − arm tot nhat = **4.3pp CAGR**, NAM TRONG nhieu 5.4pp. Rieng muc equity
**khong** ket luan duoc gi; ket luan nam o muc 4.4 (rate) + 4.6 (rang buoc cung).

### 4.8 ADMISSION (bao rieng, khong phai tieu chi)
Trung khoa `(sym,start)` voi parity: `maxfav06_4h` **43.3%** cua parity (cao nhat) →
`net*_72h` chi **19.3-20.2%**. Tuc ung vien cang xa parity ve rank-IC thi cang chon coin khac.
`n` moi arm **+37%..+64%** so parity.

## 5. PHAN QUYET theo TRUC (quy tac `PREREG_G5` muc 5.3, khong sua sau khi thay so)

### 5.1 Truc HORIZON (4h vs 72h, cung nhan `net`) — **4h THANG, don dieu, khong mo ho**
| nguong | rank-IC 4h | rank-IC 72h | win% 4h | win% 72h | equity 4h | equity 72h |
|---|---:|---:|---:|---:|---:|---:|
| 0.015 | +0.144 | **−0.013** | 81.68 | **76.02** | 76,700 | **39,181** |
| 0.020 | +0.150 | **−0.004** | 81.33 | **75.35** | 72,140 | **36,813** |
| 0.030 | +0.159 | **+0.027** | 82.99 | **76.81** | 72,995 | **42,357** |

**Don dieu 3/3 nguong, moi do.** Nhan `retEnd_72h` gan nhu khong mang thong tin thu hang trong
tick. Co che: base rate 0.32-0.39 (gan 50/50) + 72h la cua so dai gap 18 lan cua so ma gate
15m dang quyet dinh => nhan bi nhieu regime nuot.

### 5.2 Truc NGUONG `net` (0.015 / 0.020 / 0.030 o 4h) — **don dieu o PROXY, KHONG don dieu o SIM**
- Proxy: rank-IC **tang don dieu** 0.144 → 0.150 → 0.159, ca ba ngoai CI.
- Sim: `win%` **81.68 → 81.33 → 82.99**, `rate ngoai CI` **4/5 → 4/5 → 2/5**,
  equity **76,700 → 72,140 → 72,995**. **KHONG don dieu**, va thu tu KHONG khop proxy.
🔴 **Day la lan thu hai do duoc "rank-IC khong du de ket luan"** — `T1_LABEL3` muc 3 diem 3 da
canh bao; G5 xac nhan tren mot ho nhan khac va co so ung vien lon hon. **Dung dung rank-IC
per-tick lam tieu chi cuoi cho value model.**

### 5.3 Truc NHAN (`net` vs `maxFav`, cung horizon)
| horizon | `net015` | `maxfav06` | ai hon |
|---|---:|---:|---|
| 4h | 4/5 rate ngoai CI, equity 76,700 | **1/5**, equity **86,047** | **maxFav** |
| 72h | 4/5, equity 39,181 | 2/5, equity 75,005 | **maxFav** |
**`maxFav` >= `net` o CA HAI horizon.** Nhung ca hai deu THUA parity va FAIL rang buoc cung.

⚠️ **Va day la cho phai doc ky**: `maxfav06_4h` la ung vien tot nhat khi **hieu chuan bi ep
ve x26**; nhung khi tha hieu chuan tu do (`C4_maxfav30`, `G4_RECIPE_C4` muc 6.2) thi chinh no
lam `win%` **−8.04pp**, admit **x5.05**, equity **28,384**. => **Toan bo tac hai cua ho `maxFav`
o C4 den tu HIEU CHUAN, khong tu THU TU.** G5 tach duoc dung hai kenh do; day la dong gop chinh.

## 6. HE QUA — nhan/horizon nao cho VALUE MODEL neu phai train moi cho live

1. **Neu can mot value model MOI: `maxFav_4h >= 0.06`, KHONG phai `net`.** No cho thu tu tot
   nhat (rank-IC +0.164, cao hon ca x26 dang deploy) va o sim la arm it xau nhat (1/5 rate).
2. 🔴 **NHUNG bat buoc kem HIEU CHUAN LAI.** Tha nguyen phan phoi cua no vao gate = admit
   x4.56 candidate-minute / **x19.4 adm_top8** (muc 3.1) => tai lap tham hoa C4
   (`win%` −8.04pp, equity am). Duong an toan da do duoc trong dot nay: **quantile-map ve
   multiset cua bins dang deploy** — admission khi do bang parity **tuyet doi** (muc 3.2).
3. **72h la huong CAM.** Moi bien the `net*_72h` deu bien 2025 thanh nam AM 20-25%.
4. **Cho duong LIVE hom nay**: `Funding_Classifier_Final.onnx` thuoc ho `maxFav`
   (`G4_RECIPE_C4` muc 5: spearman 0.961 vs `G015_v2`) — tuc ho NHAN cua no khong phai van de;
   **HIEU CHUAN cua no moi la van de** (`p_mean` 0.2268 vs net015 0.4642). Doi ONNX sang net015
   (`g3x26/g015x26_f15_cut20251001.onnx`) **khong** phai la viec bat buoc ve nhan; cai bat buoc
   la `symbolPred` live phai co CUNG phan phoi voi bins ma C3 duoc do tren. Day la dinh chinh
   cho `G4_RECIPE_C4` muc 5 "he qua cho shadow".
5. **Neu KHONG bat buoc phai train moi: giu `net015_4h` (x26).** Khong ung vien nao thang no
   trong khuon kho nay, va no la thu duy nhat da co bins + ONNX + provenance day du.

## 7. `G5_x26_order` vs `G5_parity_S1` — vai tro cua VALUE MODEL

| | `G5_parity_S1` | `G5_x26_order` | hieu |
|---|---:|---:|---|
| thu tu coin trong tick | **S1** (XGBRanker, 9 feature) | **x26** (value model, 45 feature) | |
| gia tri `symbolPred` | multiset x26 | multiset x26 | **GIONG HET** |
| n | 2,058 | 3,385 | +64% |
| win% | 85.33 | 81.68 | **−3.64 (ngoai CI)** |
| TSloss% | 14.87 | 19.05 | **+4.19 (ngoai CI)** |
| meanP | 2.863 | 2.701 | trong CI |
| rate chat luong ngoai CI | — | **4/5** | |
| rang buoc cung | PASS 4/4 nam | **FAIL 2022 + 2025** | |
| equity | 98,523 | 76,700 | −22.1% |

Hai arm **dung CHUNG mot bo gia tri, chung mot nguong gate, chung so candidate-minute qua gate
(103,840)**. Khac biet DUY NHAT la **coin nao nhan gia tri nao**. Ket qua khac nhau ngoai CI o
4/5 rate va o rang buoc cung.

### 🔴 KET LUAN — cau truc "value model = hieu chuan gate, thong tin coin do S1" la **DUNG**
- **Thong tin COIN: cua S1.** Bo S1 di, de chinh value model xep hang → thua 4/5 rate.
- **Hieu chuan GATE: cua value model.** Doi ho nhan ma khong hieu chuan → C4: admit x5.05,
  3/5 rate, equity am (`G4_RECIPE_C4` muc 6.2). Giu hieu chuan → admission bang parity tuyet doi.
- **Tang TRAILING: khong phu thuoc gia tri** (`L1_SHADOW_C3` muc 4: hang so o ca hai cuc → 0/5).

| tang | `symbolPred` co load-bearing? | do bang gi |
|---|---|---|
| **thu tu / chon coin** | **KHONG — S1 lam viec nay** | G5 muc 7 (x26_order thua 4/5) |
| **gate (`dyn_thr` admission)** | **CO, chi qua PHAN PHOI (hieu chuan)** | C4 muc 6.2 + G5 muc 3.2/3.3 |
| **trailing (STRONG/WEAK)** | **KHONG** | L1 muc 4 |

=> Value model trong C3 la mot **bo sinh nguong theo tick**, khong phai mot bo chon coin.
Moi model 45-feature nao co **cung phan phoi `p` trong tung tick** deu thay the duoc no ma
khong lam doi admission mot don vi nao. Do la mot **rang buoc RAT NHE** — va la ly do
`predwf_G015x26` "khong tai lap byte duoc" (`G4_RECIPE_C4` muc 4.3) **khong** phai rui ro he thong.

## 8. Du doan pre-reg SAI (ghi ro, muc 6.3)
| # | du doan | thuc te |
|---|---|---|
| 5 | `n` cua arm quantile-map ~ parity, lech < 1.5% | **SAI**. +37%..+64%. Bat bien chi o tang GATE (103,840 / 5,906, dung 8/8); so lenh THUC THI con phu thuoc coin nao chiem von + slot + khong mo trung symbol. Do la mot phat hien: **THU TU quyet dinh muc su dung von**, khong chi quyet dinh chat luong. |
| 6 | "0-1 arm co 1/5 rate ngoai CI (nhieu)" | **SAI theo huong nguoc**: 8/8 arm co >= 1 rate ngoai CI, 5/8 arm co >= 2. Nhung TAT CA deu huong XAU — khong co duong tinh gia nao. |
| 7 | `x26_order` khac biet nhat va xau hon parity | **DUNG** (4/5 rate, FAIL 2 nam). Nhung no **khong** la arm xau nhat — ho 72h xau hon nhieu. |
| 8 | ket luan "value model = hieu chuan gate" | **DUNG**, muc 7. |
| — | (proxy) 4 du doan o muc 3.4 | 1 dung, 1 dung mot nua, 2 sai. |

## 9. Job nay KHONG lam
Khong cham 2026 / `HOLDOUT_UNSEAL` (fold 16-17 chi ta trong bang leak, **khong** vao sim nao).
Khong deploy, khong SSH 242, khong push, khong xoa file user.
Khong sua `research/pipeline/g015_net_train.py`, khong ghi de bins dang deploy
(`predwf_map_s1a2_x1`, `claudedata/predwf_G015x26` chi DOC).
Khong them ung vien / khong tune tham so sau khi thay so.

## 10. Artifact + lenh tai lap
| thu | duong dan |
|---|---|
| pre-reg | `docs/PREREG_G5.md` (commit `f0b088b`) |
| trainer ung vien | `research/pipeline/g5/g5_pool_train.py` (sha256 `6ff6e0d634715131…`) |
| pool-pred 8 ung vien | `/home/ubuntu/g5/pool/pool_<tag>.parquet` (6,554,089 dong moi file) |
| output kernel + summary | `/home/ubuntu/g5/out/g5-<tag>/`, `research/analysis/g5_out/g5_summary_*.json` |
| proxy | `research/analysis/g5_proxy.py`; ket qua `research/analysis/g5_out/proxy_{table,ci}.csv` |
| bang leak | `research/analysis/g5_out/leak18.csv` |
| score → bins | `research/pipeline/g5/g5_mkscore.py` + `research/pipeline/x1/c4_build_map.py` |
| runner sim | `research/pipeline/g5/run_g5_sim.sh <TAG> <profile> <bins>` |
| profile 9 arm | `profiles/g5_*.properties` (chi khac `x1_c3.properties` 1 dong bins) |
| run sim | `/home/ubuntu/java/devrun/G5_*/`, log `/home/ubuntu/g5log/` |
| cham diem | `python3 research/analysis/c4_rates.py G5_parity_S1 G5_x26_order ...` → `/home/ubuntu/g5/rates.out` |
| kernel Kaggle | `chuyendinh/g5-{net020-4h,net030-4h,net015-72h,net020-72h,net030-72h,maxfav06-4h,maxfav06-72h}` |
| dataset Kaggle moi | `chuyendinh/g5-poolkeys` (7,020,129 khoa `(ts,sym)` cua `cand_dev_x1`) |

```bash
R=/home/ubuntu/src/BinanceFuturesJava
python3 $R/research/pipeline/g5/g5_mkscore.py net030_4h
X1_CUTS="20220101 ... 20251001" G015_BINS_DIR=/home/ubuntu/claudedata/predwf_G015x26 \
  python3 $R/research/pipeline/x1/c4_build_map.py g5_net030_4h /home/ubuntu/predwf_map_g5_net030_4h
bash $R/research/pipeline/g5/run_g5_sim.sh G5_net030_4h $R/profiles/g5_net030_4h.properties \
  /home/ubuntu/predwf_map_g5_net030_4h
```

## 11. No ky thuat / viec chua lam
1. ⚠️ Nguong kiem cau truc `symbolPred` cua pre-reg dat tren **lenh da vao** (tap con chon loc)
   thay vi tren **bins** — do sai cho. Cong dung la muc 3.2. Pre-reg sau phai ghi ro tang do.
2. ⚠️ `n_eff` uoc trong de bai la ~900 khoi 72h; do that la **419**. CI rong hon ~1.46 lan so voi
   uoc ban dau. Khong doi ket luan (moi hieu ung deu lon hon nhieu do rong CI) nhung phai ghi.
3. **Chua do**: ghep S1 (thu tu) voi `maxfav06_4h` (hieu chuan) — tuc lay `maxFav` lam value
   model NHUNG van de S1 xep hang. `PREREG_G5` muc 6.3 diem 9 da khai bao day la buoc tiep neu
   co ung vien thang; khong ung vien nao thang nen **khong chay**, va no van la o trong.
4. **Chua do**: nhan 168h (`LABELH` muc 4.3 va `T1_LABEL3` muc 9 deu de trong). G5 chi 4h/72h.
5. Shadow C3 tren Oracle van **DUNG** (tat tu 2026-09-06 15:00Z, `G4_RECIPE_C4` muc 0.4).
   Job nay dung 1 slot JVM Oracle ~2.5 gio nen **khong khoi dong lai**; user quyet dinh khi nao bat.
