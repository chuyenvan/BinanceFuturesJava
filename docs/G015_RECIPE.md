# G015_RECIPE — cong thuc CHINH THUC cua `predwf_G015x26` (= `net015`)

Trang thai: **TAI DUNG DUOC, da qua cong xac minh tren dung device goc (Kaggle GPU).**
Trainer: `research/pipeline/g015_net_train.py` (sha256 `05298cba5578f5c3fde98f1314792acf5aef9ccaafb506d98b718ba1f9f5be6d`).
Boi canh: `docs/G3_X26_RECOVERY.md` (bins tai sinh bang PREDICT tu 18 model da luu).
Doc nay tra no muc 8 cua G3: **source cua TRAINER ban 2026-08-14 da mat** — day la ban dung lai
tu bang chung, khong phai ban khoi phuc file.

## 1. Nguon cua tung con so (khong doan mot cai nao)

| thanh phan | rut tu |
|---|---|
| nhan, base rate, so dong train/fold, `ts_max`, `pos` | log kernel goc `claudedata/predwf_G015/selector-15mtr-pred15-net015-gpu.log` (26,588 B, 2026-08-14) |
| `scale_pos_weight`, `n_estimators`, `num_feature`, `objective`, phien ban xgboost, do sau | 18 model JSON `claudedata/predwf_G015/model_f{0..17}_4h.json` |
| env (`LABEL_MODE`, `NET_THR`, `PURGE_STEPS`, `FIRST_CUTOFF`, `MAX_TRAIN_ROWS`, `XGB_DEVICE`) | kernel stage `kB15/net008/selector-15mtr-pred15-net008-gpu.py` (mtime 2026-08-14 14:04) + `kpull_015/selector-15m-savemodel-net015-gpu.py` |
| than pipeline (`build_features_memmap`, `train_predict_fold`, `write_bin`, `gen_cutoffs`) | `claudedata/gen_funding_wf_predictions_1m.py` (2026-08-10 23:24) — ban con giu gan nhat, cung `PIPELINE_VERSION` |

## 2. Cong thuc

| muc | gia tri |
|---|---|
| pipeline | `PIPELINE_VERSION = wfo-selector-v2-1m-canonical-20260804` |
| luoi | `SELECTOR_GRID_MIN = 15` (= `step_min` cua file label, tu-validate) |
| **nhan** | `LABEL_MODE=net`, `NET_THR=0.015` -> **`y = (retEnd_4h > 0.015)`** |
| loc nhan | `nBars_4h >= 16` va `retEnd_4h` notna |
| base rate 4h | **0.1849** tren **48,724,373** dong (22 file `.pb`, 2021Q1..2026Q2) |
| WFO | expanding, `FIRST_CUTOFF=20220101`, `OOS_MONTHS=3`, **18 cutoff** `20220101..20260401` |
| purge | `PURGE_STEPS=288` buoc x 15m = **72h**; `tr_cut = cutoff − 72h` |
| TZ | cutoff dat theo **GMT+7** (`TZ_OFFSET_MS = 7h`) |
| feature | **45** = `f0..f39` (Tool1 T1C2) + `oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy`; thu tu VI TRI, model khong luu ten cot |
| ghep OI | `merge_asof(on=ts, by=symId, direction=backward, tolerance=2h)`, khong fillna khong drop |
| XGB | `XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, min_child_weight=20, scale_pos_weight=(1−pos)/pos, eval_metric="auc", n_jobs=-1, tree_method="hist", random_state=42, device=<dev>)` |
| device goc | `XGB_DEVICE=cuda` (Kaggle GPU). Predict roi ve DMatrix CPU — WARNING trong log la **dac diem**, khong phai loi |
| xgboost | **3.2.0** (`version:[3,2,0]` trong model JSON) |
| `MAX_TRAIN_ROWS` | 60,000,000 — **khong bao gio cham** (fold lon nhat 43,974,232) |
| bins | 26 B/rec, big-endian `>q h 4f`; slot `p0` = 4h, ba slot con lai NaN |

**Kiem chung nhan doc lap** (khong qua model): dem lai tren 22 file `.pb` cho
`TOTAL_READ = 48,757,302` · `KEEP = 48,724,373` · `base = 0.1849` — **khop tuyet doi** ba con so
cua log 2026-08-14. Day la bang chung truc tiep cho `y = (retEnd_4h > 0.015)`.

## 3. Bang 18 fold — log vs model JSON

`pos` cot 4 doc tu **log**; cot 6 suy nguoc tu `scale_pos_weight` trong **model JSON**
(`pos = 1/(1+spw)`). Hai nguon doc lap, **khop 18/18**.

| fold | cutoff | n_train | pos (log) | `scale_pos_weight` (model) | pos suy tu spw | n_oos (bins) |
|---|---|---:|---:|---:|---:|---:|
| 0 | 20220101 | 3,730,472 | 0.2699 | 2.70527601 | 0.2699 | 1,123,854 |
| 1 | 20220401 | 4,852,846 | 0.2574 | 2.88437128 | 0.2574 | 1,172,010 |
| 2 | 20220701 | 6,020,407 | 0.2513 | 2.97955036 | 0.2513 | 1,188,418 |
| 3 | 20221001 | 7,206,793 | 0.2389 | 3.18566179 | 0.2389 | 1,242,626 |
| 4 | 20230101 | 8,449,371 | 0.2208 | 3.52873826 | 0.2208 | 1,302,607 |
| 5 | 20230401 | 9,745,074 | 0.2153 | 3.64556170 | 0.2153 | 1,524,605 |
| 6 | 20230701 | 11,264,565 | 0.2026 | 3.93555260 | 0.2026 | 1,671,614 |
| 7 | 20231001 | 12,931,274 | 0.1887 | 4.29935074 | 0.1887 | 1,912,959 |
| **8** | **20240101** | **14,834,006** | **0.1864** | **4.36582327** | **0.1864** | **2,140,992** |
| 9 | 20240401 | 16,968,587 | 0.1878 | 4.32422161 | 0.1878 | 2,256,504 |
| 10 | 20240701 | 19,223,554 | 0.1854 | 4.39336014 | 0.1854 | 2,362,741 |
| 11 | 20241001 | 21,577,594 | 0.1842 | 4.43021059 | 0.1842 | 2,719,452 |
| 12 | 20250101 | 24,280,226 | 0.1884 | 4.30772495 | 0.1884 | 3,056,303 |
| 13 | 20250401 | 27,323,970 | 0.1905 | 4.24887848 | 0.1905 | 3,535,785 |
| 14 | 20250701 | 30,843,016 | 0.1911 | 4.23280239 | 0.1911 | 4,078,299 |
| 15 | 20251001 | 34,904,563 | 0.1891 | 4.28786087 | 0.1891 | 4,517,610 |
| 16 | 20260101 | 39,404,186 | 0.1889 | 4.29415512 | 0.1889 | 4,587,093 |
| 17 | 20260401 | 43,974,232 | 0.1868 | 4.35441685 | 0.1868 | 4,891,812 |

`predwf_G015x26` = **fold 0..15** (16 file, `20220101..20251001`). Moi model: `num_trees = 400`,
`num_feature = 45`, `objective = binary:logistic`, `base_score = 0.5`, xgboost `[3,2,0]`.

**`max_depth = 5` do duoc tu cau truc**, khong phai tu tai lieu: so node lon nhat tren mot cay
= **63** = `2^6 − 1` (day du 5 muc chia), nho nhat 47 — **giong het** o ca model goc lan model
tai dung. Cac hyperparam khong duoc serialize trong model JSON (`max_depth`, `learning_rate`,
`subsample`, `colsample_bytree`, `min_child_weight`) lay tu than pipeline muc 1.

## 4. Cong xac minh — train LAI fold 8 tren dung device goc

Train lai cutoff `20240101` bang `g015_net_train.py`, so predict voi bins goc tren **cung
2,140,992 dong OOS** (khoa `(ts,symId)` trung **100.0000%**).

**Khop chinh xac o cac dai luong TAT DINH** (khong phu thuoc RNG):
`n_train = 14,834,006` · `ts_max = 2023-12-28 16:45:00` · `pos = 0.1864` ·
`scale_pos_weight = 4.365823` · `n_oos = 2,140,992 rec = 55,665,792 B` — **giong tung con so**
voi log 2026-08-14 va voi `model_f8_4h.json` goc.

| cap so sanh | spearman gop | max\|d\| | per-tick tb | **top-8/tick trung** |
|---|---:|---:|---:|---:|
| **CONG — GPU seed42 tai dung vs GOC x26 (GPU)** | **0.985997** | 2.304e-01 | 0.967703 | **0.8296** |
| GPU seed43 tai dung vs GOC x26 | 0.984765 | 2.237e-01 | 0.964221 | 0.8271 |
| **NEN NHIEU — GPU s42 vs GPU s43 (cung moi truong)** | **0.984931** | 2.300e-01 | 0.963999 | **0.8246** |
| tham khao: Oracle CPU s42 vs GOC x26 | 0.986678 | 1.908e-01 | 0.962649 | 0.8246 |
| tham khao: CPU s42 vs GPU s42 (deu tai dung) | 0.984283 | 2.554e-01 | 0.959183 | 0.8115 |

`p_mean/p_std`: goc **0.46416 / 0.12771**, GPU tai dung **0.46354 / 0.12778**,
CPU tai dung 0.46172 / 0.12873. `p10/50/90` goc `0.2900/0.4753/0.6201` vs GPU tai dung
`0.2907/0.4730/0.6212`.

### PHAN QUYET: **PASS**
- `spearman >= 0.98`: **DAT** (0.985997).
- `top-8 >= 0.95`: **KHONG DAT** (0.8296) — nhung **nguong nay khong dat duoc bang bat ky
  ban train lai nao**: chi doi SEED tren **cung mot GPU, cung code, cung du lieu** cho
  **0.8246**. Cong tai dung (0.8296) **cao hon nen nhieu between-seed** o **ca hai** do.
- Theo luat da chot `docs/BENCH_DEVICE.md` muc 7.4 — *"hieu ung phai vuot CI multi-seed do
  trong cung moi truong"* — ket luan la **PASS**. Nguong `top-8 >= 0.95` mac dung mot khiem
  khuyet voi cong `spearman >= 0.999` da bi bo o muc 5 cua BENCH_DEVICE: no do "co phai dung
  MOT mo hinh khong", trong khi mo hinh nay von ngau nhien (`subsample=0.8`, `colsample=0.8`).

🔴 **Khong bao gio bit-identical, va do khong phai loi.** `BENCH_DEVICE` muc 3: tren GPU,
`Cover` lech 31/31 node (RNG lay mau khac) + `Split` lech 11/31 (quantile sketch `hist` khac).
Them mot nguyen nhan rieng cua pipeline nay: `df.sort_values("ts")` la **quicksort khong on dinh**
nen thu tu dong trong cung mot `ts` la tuy y => tap con `subsample` khac => cay khac
(`G3_X26_RECOVERY` muc 6.1). **Muon bins byte-identical thi dung `g015x26_train.py` (predict tu
18 model da luu), khong phai trainer nay.**

## 5. Dau vao ghim

| thu | gia tri |
|---|---|
| Tool1 | `/home/ubuntu/ds_feat15m/features_*.t1c.gz` — 22 quy 2021Q1..2026Q2; 2021Q1 sha256 `eca5b0244e4e12b8d26df0afd82475525e0f40c17444c202afe1006bbe638c5c` (Kaggle `funding-tool1-15m` v1 == v5 == dia) |
| Label | `/home/ubuntu/label_15m/funding_label_*.pb` — 22 file dung (loc `< 20260701`), `step_min=15`, `scale=100000` |
| OI | `/home/ubuntu/claudedata/oi/oi_percoin_full.bin` — 140,924,110 rec, sha256 `e3887f63097299655213f8382ca7e473e126ee4d7ddf69a39658942651b305ec` |
| symbol map | `/home/ubuntu/claudedata/oi/symbol_map.csv` — md5 `9a3e40e90b1158a2fe740d261bff690c` |
| decoder | `/home/ubuntu/sel1m_code/{tool1_col.py, funding_label_pb.py}` (Kaggle `chuyendinh/sel1m-code`) |

sha256 bins fold 8: goc `e5a684f4132996ea47cc2341960cf0fd3a5dc0262c65368bac5cf63a4117f131` ·
GPU tai dung `53750a944acdb10594af20a40ae7f64bfe6d4ebdcdcba34cacfb0559ca13931d` ·
CPU tai dung `2e0f2d80962e86abd2bd501be87835e9019568546e045cd6f2057e7f30142b7a`.

## 6. Sinh bins -> `build_map` -> dataset sim

```bash
R=/home/ubuntu/src/BinanceFuturesJava
# (A) TAI SINH bins x26 byte-tuong-duong (spearman 1.0): predict tu 18 model da luu
CUTOFF=20240101 FOLD_IDX=8 OUT=/duong/predict_wf_20240101.bin \
  python3 $R/research/pipeline/g015x26_train.py
# (B) TRAIN LAI tu dau bang recipe nay (KHONG byte-identical — xem muc 4)
python3 $R/research/pipeline/g015_net_train.py --fold 20240101 --device cuda \
  --save-model --out-dir /duong/ra          # Kaggle GPU = dung device goc
python3 $R/research/pipeline/g015_net_train.py --fold all --device cpu --out-dir /duong/ra
# (C) bins GIA TRI -> bins SELECTOR (S1 order ap len phan phoi P(win) cua G015)
X1_CUTS="20220101 ... 20251001" G015_BINS_DIR=/home/ubuntu/claudedata/predwf_G015x26 \
  python3 $R/research/pipeline/x1/c4_build_map.py s1a2x1 /home/ubuntu/predwf_map_c4_parity
# (D) dataset WFO + sim (Oracle, TICKER_SOURCE=file)
bash $R/research/pipeline/x1/run_c4_sim.sh C4_parity $R/profiles/c4_parity.properties \
  /home/ubuntu/predwf_map_c4_parity
```

Cong (C) da do: `c4_build_map.py` + bins `predwf_G015x26` cho ra **byte-identical 16/16**
voi `predwf_map_s1a2_x1` dang deploy o tang sim.

## 7. Canh bao cho ai dung lai

1. **`--device cuda` la device GOC.** Muon so voi bat ky so nao cua x26 thi phai chay GPU.
   CPU cho ket qua **khac** (bang muc 4) — dung, nhung la mot mau khac.
2. **Trainer nay KHONG tai lap `predwf_G015_v2`.** `G015_v2` la nhan `maxFav_4h >= 0.06`
   (base 0.0457), mot model **khac**; dung `--label-mode maxfav --thr 0.06` neu can, va doc
   `docs/G015REBUILD_RESULT.md` truoc.
3. **Fold 16/17 (`20260101`, `20260401`) nam TREN `HoldoutSeal`** (2026-01-01). Recipe co ta
   chung vi chung co trong lan chay goc; **khong duoc dua vao bat ky sim/verdict nao**
   khi chua co `HOLDOUT_UNSEAL` + user duyet truc tiep.
4. Duong build feature trong trainer la **memory-light** (gather bang `ridx`). Duong
   "45-cot-pandas" nguyen ban **OOM-kill im lang** tren Oracle 23 GB o cac fold >= 2025.
