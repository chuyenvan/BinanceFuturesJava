# G3_X26_RECOVERY — `predwf_G015x26` TAI LAP DUOC. Ket luan "mat vinh vien" la SAI.

Ngay: 2026-09-06. Chi DOC + tai sinh ra duong dan MOI. KHONG ghi de bins cu, KHONG deploy,
KHONG cham 242, KHONG train lai model nao.

## 0. TRA LOI MOT CAU

**Tai lap DUOC.** 16/16 fold: `spearman = 1.00000000`, `max|delta| = 1.192e-07`
(= **1 ULP cua float32**), so record trung khop tuyet doi voi manifest
`docs/experiment/G015X26_PROVENANCE.md` §2. Vuot xa cong `>= 0.999`.

Ly do lan truoc that bai KHONG phai "mat du lieu" ma la **sai NHAN (label)**:
- ban rebuild `G015_v2` dung `y = (maxFav_4h >= 0.06)`, base rate **0.0457**;
- `G015x26` that su dung `y = (retEnd_4h > 0.015)` (`LABEL_MODE=net`, `NET_THR=0.015`),
  base rate **0.1849**.
Do la hai model khac han, nen `rho` lech 0.0215 va admit-rate lech 3x — dung nhu do duoc,
nhung nguyen nhan bi quy nham cho "mat ban export Tool1 2021".

Script: `research/pipeline/g015x26_train.py`. Bins tai sinh: `/home/ubuntu/g3x26/regen/`
(16 file + `REGEN.sha256`). Bins goc `/home/ubuntu/claudedata/predwf_G015x26/` KHONG bi dung toi.

## 1. LAN REBUILD TRUOC TAC O DAU

`docs/prereg/PREREG_G015REBUILD.md` + `docs/result/G015REBUILD_RESULT.md` (2026-09-04) **khong he co gang tai lap
x26**. Ho dinh nghia lai bai toan: dung recipe trong doc archive, train MOI 10 fold tren CPU, roi
kiem "run1 == run2" (byte-identical voi CHINH NO). Cai do dat — nhung no chung minh
*determinism cua ban moi*, khong phai *tai lap x26*.

Phep so voi x26 that su chi nam o `docs/result/G015CUT_RESULT.md` §2, va no FAIL:

| dai luong | x26 (`p_old`) | ban rebuild (`full45`) |
|---|---:|---:|
| `rho` gop pool | 0.16752 | 0.18900 (lech +0.0215, nguong FAIL > 0.019) |
| `spearman(x26, rebuild)` | — | **0.836** |
| `p_mean` / `p_std` | 0.400 / 0.136 | 0.264 / 0.205 |
| admit-rate `cand_dev3` | 0.200% | 0.613% (3.07x) |

`G015CUT_RESULT` §2.2 dat **gia thuyet** nguyen nhan (tu ghi ro "chua chung minh"):
"bins train tren mot ban export Tool1 2021 KHAC, ban cu **khong con ton tai** tren dia",
lay bang chung tu **mtime**: bins 2026-08-14 15:03, file Tool1 2021 mtime 2026-08-16 08:36.
`docs/experiment/G015X26_PROVENANCE.md` §1 nang gia thuyet do thanh tuyen bo dut khoat
("**KHONG tai lap duoc**", "**KHONG co source de dung lai**"), roi `AGENT_RUNBOOK` §5,
`QUEUE`, `F4_TIMING`, `L1_SHADOW_C3`, `T2_FULLFLOW` deu trich lai nhu su that nen.

**Ca hai chan cua gia thuyet do deu sai** — muc 3 duoi.

## 2. "x26" LA GI

Khong phai 26 feature, khong phai seed, khong phai kernel version. **`x26` = tag cua chien dich
fanout WFO "keo toi 2026"**, dat o tang backtest chu khong phai tang train:

- `_wfotmp/forced/done_all/DONE_G015x26.txt` dong 1: `TAG=G015x26 HIDX=0`, 16 window
  `20220101..20260101`. Cac tag anh em: `G015x26b/c/d/e/q2` (18 window, toi 2026Q2),
  `G015K5v26`, `ARM26K8v26b` — `v26`/`x26` deu la "co 2026".
- `docs/archive/.../wfo_2026_ticker_fix_2026-08-15.md`: "Lan 1: tag G015x26d -> FAIL (bay 3,
  symlink). Lan 2: tag **G015x26e** voi tar v10 data that".
- Bang chung cung nhat: **33 thu muc `predwf_*` dung CHUNG inode**. `predict_wf_20240101.bin`
  co `nlink = 33`; `find -inum` liet ke `predwf_G015x26`, `..._x26b/c/d/e/q2`, `predwf_G015`,
  `predwf_REPRO1`, `predwf_REPRO2`, `predwf_XVAL`, `predwf_G015K5*`, `predwf_ARM*`...
  => chi co **MOT** bo bins vat ly; `predwf_G015x26/` la mot ten hardlink cua no.

`G015` = `net015` = `NET_THR = 0.015` (ho kernel `selector-*-net015-*`, thu muc
`sel_models_net015/`), KHONG phai "gate 0.15".

## 3. MANH MOI THEO TUNG NGUON

### 3.1 Git (repo + Windows `E:\educa\source\github\20260415\BinanceFuturesJava`)
- `git log -S "G015x26" --all`, `--diff-filter=D`, `git branch -a`, `git stash list`: khong co
  ban `gen_funding_wf_predictions_1m.py` nhanh `net` nao tung duoc commit. Khong co stash.
- CO trong git: `docs/archive/_cleanup_20260829/docs/project-memory/code/gen_funding_wf_predictions_CANON.py`
  va `ml/training/gen_funding_wf_predictions.py` — cung dong PIPELINE nhung **ban maxFav**, khong co
  `LABEL_MODE`.
- `ml/funding_selector/train_funding_selector_wfo.py` CO nhan net nhung duoi ten env KHAC
  (`SEL_LABEL_MODE` / `SEL_NET_THR`, mac dinh `tb`), la nhanh EXPLORE 2026-08-26 — khong phai ban 08-14.
- Windows repo = ban sao cung commit, khong co artifact nao them (chi `DONE_G015x26*.txt`).

### 3.2 Tai lieu archive (nguon quyet dinh, truoc do khong ai doc)
`docs/archive/_cleanup_20260829/docs/project-memory/wfo_train_code_provenance_versions_2026-08-16.md`:
> "**Kernel `selector-15mtr-pred15-net015-gpu` exec `_1m`**" ... "**18 fold `predwf_G015x26e`
> (mtime 14/08 15:03-15:05)**" ... "Ban 14/08 (lam 18 fold) la version sel1m-code TRUOC khi toi recreate."

=> chi thang ra kernel, dataset code, va thoi diem. Day la dau moi mo ra toan bo phan con lai.

### 3.3 Bins + dia Oracle — **TIM THAY MODEL GOC**
`/home/ubuntu/claudedata/predwf_G015/` (mot trong 33 hardlink dir) chua **toan bo output kernel 08-14**:

| thu | so luong | mtime |
|---|---:|---|
| `model_f0_4h.json` .. `model_f17_4h.json` | **18 model XGBoost da train** | 2026-08-14 15:02 |
| `predict_wf_*.bin` | 18 bins (16 cai la `predwf_G015x26`) | 2026-08-14 15:03-15:05 |
| `selector-15mtr-pred15-net015-gpu.log` | **log day du cua lan chay** (26,588 B) | 2026-08-14 15:05 |

Doi chieu khoa: log ghi `fold 8 4h: ... pos=0.1864`; `model_f8_4h.json` co
`scale_pos_weight = 4.365823 = (1-0.1864)/0.1864`. Log ghi
`ghi predict_wf_20220101.bin: 1123854 rec = 29220204 bytes` = dung so trong manifest x26.
=> **Model va log CHINH LA cua x26.** Khong mat gi.

### 3.4 Kaggle
- `funding-tool1-15m` con **5 version**. `features_20210101_to_20210401.t1c`:
  `sha256(v1) = sha256(v5) = sha256(ban tren dia)` = `eca5b0244e4e12b8d26df0afd82475525e0f40c17444c202afe1006bbe638c5c`,
  65,478,640 B. v4 chi **bo** 4 file 2021 roi v5 **them lai nguyen ven**.
  => "ban export Tool1 2021 da mat" **SAI**; mtime 08-16 chi la lan tai ve lai.
- `funding-label-15m` (v1, 2026-08-13 14:25) va `funding-oi-percoin` (v2, 2026-08-05) **chua tung
  doi** ke tu truoc lan chay. Log 08-14 ghi `OI=140924110`; ban tren dia hom nay cung `140924110`.
- Kernel `selector-15mtr-pred15-net015-gpu`: **output = 0 file, status ERROR** — lan chay 08-16
  (regen, bi `Killed`/OOM) da GHI DE output 08-14 tren Kaggle. Kaggle chi giu output cua version
  MOI NHAT. API `kernels/pull?version_number=N` tra 400 => **khong lay lai duoc code/version cu**.
- Dataset `sel1m-code` chi con **version 1** (tao lai 2026-08-29) => ban `_1m` nhanh `net` ngay 08-14
  khong con o Kaggle.
- Anh em con nguyen: `selector-15mtr-pred15-net008-gpu` (chay 2026-08-14 07:04) van giu **36 file**
  output (18 model + 18 bins) — cung pipeline, chi khac `NET_THR=0.008`.

### 3.5 Kernel script tren dia
`/home/ubuntu/kB15/net008/selector-15mtr-pred15-net008-gpu.py` (mtime **2026-08-14 14:04**) la
ban stage dung ngay hom do. `kB15/net015/...py` da bi ghi de 2026-08-16 15:06 (ban regen:
`TOOL1_GLOB=features_202[4-6]*`, `XGB_DEVICE=cpu`, `CUTOFFS=20260401`).
`/home/ubuntu/kpull_015/selector-15m-savemodel-net015-gpu.py` ghi ro nhan:
> `LABEL_MODE=net` -> `y = (retEnd_4h - NET_THR > 0)` (kieu NUOI LAI)

### 3.6 Doi chung phan phoi
`predict_wf_20240101.bin`, cot `p0`:

| nguon | mean | std | p10/50/90 |
|---|---:|---:|---|
| `predwf_G015x26` | 0.46416 | 0.12771 | 0.2900 / 0.4753 / 0.6201 |
| `sel_models_net015` (kernel savemodel, cung nhan) | 0.46505 | 0.12990 | 0.2877 / 0.4756 / 0.6239 |
| `sel_models_net03` (`NET_THR=0.03`) | 0.40125 | 0.18040 | 0.1614 / 0.3968 / 0.6461 |
| `predwf_G015_v2` (nhan maxFav) | 0.34095 | 0.22190 | 0.0889 / 0.2918 / 0.6785 |

`scale_pos_weight` fold 0 theo `NET_THR`: 0.008 -> 2.0243 (base 0.331); 0.015 -> 3.5287 (base 0.221);
0.03 -> 9.1386 (base 0.099). Don dieu dung chieu => xac nhan `NET_THR` dieu khien nhan.

## 4. RECIPE DAY DU CUA `predwf_G015x26` (chot tu log + kernel script + model JSON)

| muc | gia tri | nguon |
|---|---|---|
| kernel | `chuyendinh/selector-15mtr-pred15-net015-gpu`, Kaggle **GPU** | metadata + log |
| chay luc | 2026-08-14 07:05-07:57 UTC (= 14:05-14:57 +07) | log |
| pipeline | `PIPELINE_VERSION=wfo-selector-v2-1m-canonical-20260804` | log dong 3 |
| nhan | `LABEL_MODE=net`, `NET_THR=0.015` -> `y = (retEnd_4h > 0.015)` | kernel + log |
| base rate nhan 4h | **0.1849** (48,724,373 dong) | log |
| luoi | `SELECTOR_GRID_MIN=15`, `PRED_GRID_MIN=15` | kernel |
| purge | `PURGE_STEPS=288` buoc x 15m = **72h** | kernel + log |
| WFO | expanding, `OOS_MONTHS=3`, `FIRST_CUTOFF=20220101`, TZ `+7h`, **18 cutoff** 20220101..20260401 | log |
| horizon | `HORIZONS=4h` (slot p1/p2/p3 = NaN) | kernel |
| feature | 45 = `f0..f39` (Tool1 T1C2) + 5 OI, `merge_asof(on=ts, by=symId, backward, tol=2h)` | code |
| ma tran | 49,071,175 dong x 45 cot, memmap per-year | log |
| XGB | `n_estimators=400 max_depth=5 lr=0.05 subsample=0.8 colsample_bytree=0.8 min_child_weight=20 scale_pos_weight=(1-pos)/pos eval_metric=auc random_state=42 tree_method=hist n_jobs=-1` | code + model JSON |
| device | `XGB_DEVICE=cuda` (predict fallback ve CPU DMatrix — co WARNING trong log) | log |
| xgboost | **3.2.0** | model JSON `version:[3,2,0]` |
| bins | 26 B/rec big-endian `>q h 4f` | code `write_bin` |
| input | Tool1 `eca5b024...638c5c` (2021Q1) + 21 quy khac; OI 140,924,110 rec; label 22 file `.pb` | Kaggle + dia |

## 5. BANG GIA THUYET x KET QUA

Chi **1** gia thuyet phai train/predict; 5 cai kia bac bo duoc bang bang chung truc tiep, khong ton
GPU-hour nao. (Ngan sach cho phep 6 lan train — dung 0 lan train, 16 lan predict.)

| # | Gia thuyet | Cach kiem | Ket qua |
|---|---|---|---|
| H1 | Ban export Tool1 2021 da mat (nguyen nhan chinh thuc cu) | tai `features_20210101_to_20210401.t1c` tu Kaggle **v1** va **v5**, sha256 3 ban | **BAC BO.** 3 sha256 giong het nhau |
| H2 | Nhan la `maxFav_4h >= 0.06` (nhu `PREREG_G015REBUILD` §2) | log 08-14 + header kernel + `scale_pos_weight` trong model | **BAC BO.** Nhan la `retEnd_4h > 0.015`, base 0.1849 (khong phai 0.0457) |
| H3 | Lech do GPU-vs-CPU | `spearman(x26, sel_models_net015)` = **0.98325** (2 lan chay GPU, cung nhan) | Co gop phan, nhung khong giai thich noi `spearman = 0.836` cua H2 |
| H4 | x26 la mot lan train rieng, 16 fold | `nlink=33`, `find -inum` | **BAC BO.** 1 bo bins vat ly, 18 fold, x26 = tag fanout lay 16 |
| H5 | Model goc da mat | liet ke 33 hardlink dir | **BAC BO.** 18 model JSON con nguyen o `claudedata/predwf_G015/` |
| **H6** | **Tai sinh bang PREDICT tu model da luu + input ghim** | chay 16 fold, so voi bins goc | **DAT. spearman 1.00000000, max\|d\| = 1.192e-07 (1 ULP float32), 16/16** |

## 6. KET QUA TAI LAP — 16/16 FOLD

`research/pipeline/g015x26_train.py` -> `/home/ubuntu/g3x26/regen/`. So sanh ghep theo khoa
`(ts, symId)` voi `/home/ubuntu/claudedata/predwf_G015x26/`:

| cutoff | n_orig | n_regen | khoa trung | spearman | max\|d\| |
|---|---:|---:|:---:|---:|---:|
| 20220101 | 1,123,854 | 1,123,854 | True | 1.00000000 | 1.192e-07 |
| 20220401 | 1,172,010 | 1,172,010 | True | 1.00000000 | 1.192e-07 |
| 20220701 | 1,188,418 | 1,188,418 | True | 1.00000000 | 1.192e-07 |
| 20221001 | 1,242,626 | 1,242,626 | True | 1.00000000 | 1.192e-07 |
| 20230101 | 1,302,607 | 1,302,607 | True | 1.00000000 | 1.192e-07 |
| 20230401 | 1,524,605 | 1,524,605 | True | 1.00000000 | 1.192e-07 |
| 20230701 | 1,671,614 | 1,671,614 | True | 1.00000000 | 1.192e-07 |
| 20231001 | 1,912,959 | 1,912,959 | True | 1.00000000 | 1.192e-07 |
| 20240101 | 2,140,992 | 2,140,992 | True | 1.00000000 | 1.192e-07 |
| 20240401 | 2,256,504 | 2,256,504 | True | 1.00000000 | 1.192e-07 |
| 20240701 | 2,362,741 | 2,362,741 | True | 1.00000000 | 1.192e-07 |
| 20241001 | 2,719,452 | 2,719,452 | True | 1.00000000 | 1.192e-07 |
| 20250101 | 3,056,303 | 3,056,303 | True | 1.00000000 | 1.192e-07 |
| 20250401 | 3,535,785 | 3,535,785 | True | 1.00000000 | 1.192e-07 |
| 20250701 | 4,078,299 | 4,078,299 | True | 1.00000000 | 1.192e-07 |
| 20251001 | 4,517,610 | 4,517,610 | True | 1.00000000 | 1.192e-07 |

`min_spearman = 1.00000000`, `max(max|d|) = 1.192e-07`, `keys_all_equal = True` (16/16).
So record khop **tuyet doi** manifest `G015X26_PROVENANCE` §2. Percentile trung nhau toi 8 chu so
(fold 20240101: p10/50/90 = 0.28995553 / 0.47525303 / 0.62010239 o CA HAI ban).

### 6.1 Vi sao KHONG byte-identical (va tai sao khong ai lam duoc)
Pipeline goc dung `df.sort_values("ts")` = **quicksort, KHONG on dinh**. Thu tu cac dong CUNG mot
`ts` la tuy y va phu thuoc phien ban numpy/pandas. Do duoc: ca ban goc lan ban tai sinh **deu**
co `within-tick symId ascending = False` (2,132,256 cap ts trung o fold 20240101), chi khac hoan vi.
=> Day la **khiem khuyet determinism cua pipeline goc**, khong phai mat input. Ke ca chay lai dung
kernel do tren Kaggle cung khong dam bao ra dung byte.

Ban than script tai sinh thi **on dinh tuyet doi**: hai duong build khac nhau (`repro.py` nang va
`repro2.py` nhe RAM) cho ra file **byte-identical** (sha256 giong nhau) o fold 20240101.

### 6.2 Tran RAM tren Oracle (ghi de khong ai dam vao lai)
Oracle co 23 GB; Kaggle co 32.9 GB. Duong build "nguyen ban" (dung 45 cot pandas) bi **OOM-kill im
lang** o fold >= 20250101 (nam 2025 co 15,193,408 dong Tool1). Ban trong repo dung duong nhe:
`merge_asof` chi tren `(ts, symId)` + 5 cot OI, con 40 cot Tool1 gather bang `ridx` -> peak ~11 GB.
Da chung minh cho ket qua **byte-identical** voi duong nang.

## 7. CONG ONNX-vs-JSON (fold cuoi cua dai x26)

Fold 15 = cutoff `20251001` (fold cuoi trong 16 fold cua `predwf_G015x26`).

| dai luong | gia tri |
|---|---|
| ONNX | `/home/ubuntu/g3x26/g015x26_f15_cut20251001.onnx`, 806,830 B |
| sha256 | `7921ceaf2405049ddf2c23187264c34d6c95a38125f33c9ef3506f02f4e6dd8b` |
| mau kiem | **300,000 dong feature THAT** cua OOS 2025Q4 (khong phai du lieu gia) |
| `max\|d\|` ONNX vs JSON | **4.619e-07** |
| `mean\|d\|` | 3.471e-08 |
| `spearman` | **1.00000000** |
| input | `FloatTensorType([None, 45])`, thu tu VI TRI = `f0..f39` + `oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy` |

**KHONG cap nhat `deploy_242_l3/`** — co chu dich:
`/home/ubuntu/deploy_242_l3/` dong goi selector **S1** (`s1_c3/s1a2x1_cut20251001.onnx`, 9 feature)
chu khong phai G015. G015x26 di vao he qua **file bins** (`WFO_FUNDING_PRED_DIR`) o tang sim/WFO;
duong live dung `Funding_Classifier_Final.onnx`. Nhet ONNX G015 vao goi deploy = doi hanh vi deploy,
nam ngoai pham vi job nay va vi pham rang buoc "khong deploy / khong sua 242". ONNX o tren la
**artifact nghien cuu + cong kiem chung**, de san khi nao co pre-reg cho viec dung no.

## 8. MANH DUY NHAT CON THIEU (va no khong chan viec gi)

**Source code cua trainer ban 2026-08-14** (`gen_funding_wf_predictions_1m.py` nhanh co
`LABEL_MODE`/`NET_THR`/`SCREEN`/`MAX_TRAIN_ROWS`/luu model). Mat o **hai** noi cung luc:
1. tren dia: bi ghi de 2026-08-16 09:53 (`.bak2`) va 15:36 (ban chinh) khi vá cho nhanh 5m;
2. tren Kaggle: dataset `sel1m-code` bi **tao lai** (chi con version 1, 2026-08-29), va API
   `kernels/pull?version_number=` tra **400** nen khong doc duoc version cu.

Ban gan nhat con giu: `/home/ubuntu/claudedata/gen_funding_wf_predictions_1m.py` (26,561 B,
2026-08-10 23:24) — cung `PIPELINE_VERSION`, cung `build_features_memmap()` (in dung chuoi log
`MEMMAP-PERYEAR` va `quy ... -> merged=... (off=...)` khop log 08-14), cung `write_bin`; **thieu**
dung phan nhan `net` + `SCREEN` + luu model.

**He qua:** khong train lai tu dau ra dung x26 duoc. Nhung **khong can**: 18 model da train con
nguyen, va nhan/`spw` da doc duoc truc tiep tu model JSON + log, nen recipe da duoc phuc dung day du
o muc 4. Neu ve sau muon train lai (vi du doi feature), viet lai phan nhan la 3 dong:
`y = (retEnd_4h > NET_THR)` tren cot `retEnd_4h` da co san trong `label_15m/*.pb`
(`ml/funding_selector/train_funding_selector_wfo.py:115-131` da co ban tham chieu).

## 9. LENH TAI LAP

```bash
# 1 fold (fold 8 = cutoff 20240101). ~2 phut, peak ~11 GB.
CUTOFF=20240101 FOLD_IDX=8 OUT=/home/ubuntu/g3x26/regen/predict_wf_20240101.bin \
  python3 research/pipeline/g015x26_train.py

# FOLD_IDX = vi tri trong 18 cutoff 20220101,20220401,...,20260401 (0..17).
# predwf_G015x26 = fold 0..15. Doi chieu: /home/ubuntu/g3x26/compare_all.py
```
Input ghim: `ds_feat15m/features_*.t1c.gz` (22 quy), `claudedata/oi/oi_percoin_full.bin`
(140,924,110 rec), `claudedata/oi/symbol_map.csv`, model
`claudedata/predwf_G015/model_f{0..17}_4h.json`. Moi truong: python3, xgboost **3.2.0**, CPU.

## 10. DINH CHINH TAI LIEU CU (bat buoc doc kem)

| tai lieu | cau sai | dung la |
|---|---|---|
| `G015X26_PROVENANCE.md` §1 | "train tren ban export Tool1 2021 **da mat**"; "**KHONG co source de dung lai**" | Export 2021 con nguyen (sha256 khop 3 ban). 18 model goc con nguyen. Tai lap duoc, spearman 1.0 |
| `G015CUT_RESULT.md` §2.2 | gia thuyet "ban export 2021 cu khong con ton tai" | Bac bo bang sha256 Kaggle v1/v5/dia |
| `G015CUT_RESULT.md` §8.2 | "code sinh ra bins da deploy khong con ton tai" | Dung mot phan: **trainer** mat, nhung **model + log + input** con, du de tai sinh |
| `PREREG_G015REBUILD.md` §2 | "nhan 1 chieu `y = (maxFav_4h >= 0.06)`... Y het recipe canonical" | Recipe canonical KHAC recipe x26. x26 = `retEnd_4h > 0.015` |
| `G015_PROVENANCE.md` mo dau | `predwf_G015_v2` "thay cho" x26 | v2 la model KHAC NHAN, khong phai ban tai lap cua x26 |
| `AGENT_RUNBOOK.md` §5 | "`predwf_G015x26` KHONG reproduce duoc. Single point of failure." | Da go; xem §3 RUNBOOK |
| `QUEUE.md` (nhieu muc) | "G015x26 KHONG reproduce duoc" | Da go |

**Chua dinh chinh (co y):** moi ket luan ve *gia tri* (rho, maxDD, C3 truot san) giu nguyen. Job nay
chi sua **tinh trang tai lap**, khong dong vao bat ky tuyen bo equity/alpha nao. Rieng
`G015REBUILD_RESULT` §5 "moc 0.1675 coi nhu da mat" nay **sai**: moc 0.1675 la cua model nhan `net`,
tai lap duoc, va no chua bao gio so sanh like-for-like voi 0.18991 (nhan `maxFav`) — hai model khac
nhan thi `rho` khong so truc tiep duoc.

## 11. TOAN VEN + VIEC CHUA LAM

- **Bins goc nguyen ven:** kiem lai 16/16 sha256 cua `/home/ubuntu/claudedata/predwf_G015x26/`
  voi bang `G015X26_PROVENANCE` §2 sau khi job xong: **16/16 KHOP, 0 lech**; mtime van
  2026-08-14 15:03-15:05, `nlink` van 33. Job nay chi DOC.
- **Con mot cau sai chua sua (co y):** header cua
  `/home/ubuntu/claudedata/predwf_G015x26/MANIFEST.sha256` dong 3 van ghi
  *"artifact DONG BANG: train tren export Tool1 2021 da mat, KHONG tai lap duoc"*.
  KHONG sua vi file nam trong thu muc bins da duoc dong bang boi mot job truoc, va sua no khong
  can thiet cho ket luan. Ai doc file do phai doc kem doc nay.
- **Khong chay:** train lai (0 lan), java/sim (0 run), deploy (0), thay doi 242 (0), push (0).
  Bins tai sinh ra duong dan MOI `/home/ubuntu/g3x26/regen/` (2.4 GB, dia con 17 G).
- Process `java BinanceOrderTradingManager` (pid 654317) dang chay tren Oracle la cua **live**,
  co truoc job nay va **khong bi dong toi**.
