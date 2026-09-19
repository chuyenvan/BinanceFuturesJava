# KAGGLE_PARITY.md — Do "venh" S1 selector: Kaggle CPU vs Oracle CPU

> Muc dich: dung nang luc chay S1 baseline (18 fold, KEEP-9, seed 42) tren Kaggle CPU,
> roi do do lech so voi ban Oracle CPU CUNG mot code/data/hyperparam. Day la moc rieng
> cho cac vong Kaggle sau (fan-out HPO/bagging/feature-group tren Kaggle) -- KHONG phai
> de trong Oracle-baseline va Kaggle-variant vao chung mot phep so sanh.
> KHONG tune, KHONG GPU, KHONG chay training CPU nang tren Oracle (agent NOISE_CAL dang
> dung CPU Oracle luc lam viec nay) -- moi buoc tren Oracle o day chi la doc file + upload
> (I/O), training that chay tren Kaggle.

## 1. Tap file toi thieu (rut gon tren Oracle, chi doc + to_parquet)

Baseline S1 18-fold (`s1_hpo_bag_featgrp.py` mode `baseline`, dung cho P1/P2/P3) chi can
KEEP-9 feature + `ts,sym,g1lite` cua ledger -- KHONG can G1/G2/G3/noise_0 (chi dung cho P3
feature-group, ngoai pham vi vong nay) va KHONG can `path_labels.parquet` (chi phuc vu
metric phu `g1_replay`, khong anh huong edge5/parity o day).

Sinh tren Oracle bang `research/pipeline/x1/kaggle_parity/make_reduced_dataset.py`
(doc cot chon loc qua `pd.read_parquet(columns=...)`, downcast float64->float32, khong doc
toan bo file 40 cot / 2GB):

| file goc (Oracle)                              | size    | file rut gon                    | size   |
|-------------------------------------------------|---------|----------------------------------|--------|
| `/home/ubuntu/featv2/feat_v2_x1.parquet` (40 cot)| ~2.04GB | `feat_v2_x1_keep9.parquet` (11 cot)| 273MB |
| `/home/ubuntu/ledger/cand_dev_x1.parquet`        | 209MB   | `cand_dev_x1_lite.parquet` (3 cot) | 21MB  |

Tong dataset upload: **~294MB** (thay vi ~2.2GB neu upload nguyen file) -- md5 xem
`research/pipeline/x1/kaggle_parity/dataset-metadata.json` la id dataset, con md5 tung file
nam trong `reduce_meta.json` sinh cung luc (khong commit vao repo, luu tren Oracle
`/home/ubuntu/s1hpo/kaggle_ds/reduce_meta.json`).

⚠️ Dataset Kaggle CU `chuyendinh/s1-ledger-v3` la STALE (2 cot dyn_thr/gate_dyn_ok tinh sai)
-- **KHONG dung**. Dataset MOI cho vong nay: **`chuyendinh/s1-featv2-x1-20260919`** (private,
ready, 4 file: 2 parquet rut gon + `make_reduced.py` + `reduce_meta.json`).

## 2. Kernel Kaggle CPU

`research/pipeline/x1/kaggle_parity/train_baseline18_kaggle.py` -- **self-contained**
(khong import repo, vi kernel Kaggle khong co repo mount). Copy nguyen logic
`run_variant`/`load_D` cua `s1_hpo_bag_featgrp.py` (mode baseline, KHONG doi logic
nhan/purge/hyperparam):

- `pip install xgboost==3.2.0` ngay dau kernel + in version (khop ban Oracle, tranh
  moi truong Kaggle mac dinh khac ban).
- `KEEP9`, `CUTS18`, `H`, `TZ`, `PURGE` giong het `s1_hpo_bag_featgrp.py`.
- Model: `XGBRanker(objective="rank:ndcg", n_estimators=300, max_depth=4,
  learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, min_child_weight=50, n_jobs=4,
  tree_method="hist", random_state=42, lambdarank_pair_method="topk",
  lambdarank_num_pair_per_sample=8)` -- CPU thuan (`tree_method="hist"`, KHONG GPU).
- `score` luu ra la **HANG (rank) trong tick**, dung nhu `run_variant` goc (KHONG phai
  score tho lien tuc) -- day la diem de nham lan da ghi trong `gate_reproduction`
  (`s1_hpo_bag_featgrp.py`), giu nguyen o day de 2 ben so dung don vi.
- Doc data qua `glob.glob("/kaggle/input/**/*.parquet", recursive=True)` (KHONG hardcode
  path/slug, xem KAGGLE_RULES.md Sec 3b/3b-bis).
- `enable_gpu: false`, `enable_internet: true` (can internet de `pip install`).
- Output: `pred_baseline18_kaggle.parquet` (ts,sym,score,fold), `edge5_by_tick_kaggle.csv`,
  `summary_kaggle.json` (env: xgboost/pandas/numpy version, platform, cpu_count, thoi gian
  tung fold + tong, edge5 tong + theo nam).

Dataset+kernel deu **private** (`is_private: true`).

## 3. Ket qua chay (2026-09-19)

- Dataset: `chuyendinh/s1-featv2-x1-20260919` (version 1, private, ready).
- Kernel: `chuyendinh/s1-baseline18-parity-20260919` (version 1, private, CPU, COMPLETE).
- Push luc ~13:15 UTC, COMPLETE luc ~13:37:59 UTC (poll moi 25s, khong giu bridge dong bo).
- Moi truong Kaggle ghi trong `summary_kaggle.json`: Python 3.12.13, xgboost **3.2.0**
  (khop pin), pandas 2.3.3, numpy 2.0.2, `Linux-6.12.90+-x86_64` (Kaggle CPU image),
  **4 CPU** (khop `n_jobs=4` cua model va khop dac ta Sec 3c KAGGLE_RULES.md).

### Thoi gian train 18 fold

| moi truong | thoi gian | ghi chu |
|---|---|---|
| Oracle CPU | **~650s (~10.8 phut)** | `full.log`: fold 0 ket thuc 16:48:30, fold 17 + peak-RSS log 16:58:52 (goi tu `main()` mode `full`, ngay sau REPRODUCTION GATE) |
| Kaggle CPU | **1279.8s (~21.3 phut)** | `summary_kaggle.json.total_train_time_sec`; fold cuoi (20251001, oos 3.5M dong) rieng het 233.9s |

=> **Kaggle CPU cham hon Oracle CPU ~2.0x** tren cung workload (ca hai deu `n_jobs=4`,
Oracle nhieu kha nang co CPU dedicated/nhanh hon vCPU chia se cua Kaggle).

### 4 con so "venh moi truong" (join `pred_baseline18.parquet` Oracle vs
`pred_baseline18_kaggle.parquet` Kaggle theo `(ts,sym)`, n_join = 6,685,957 = 100% ca hai ben)

| # | metric | gia tri | dinh nghia |
|---|---|---|---|
| (a) | **spearman toan cuc** | **0.99278** | `spearmanr(score_oracle, score_kaggle)` tren toan bo 6.69M dong |
| (b) | **rank-in-tick median / min** | **median 0.98872 / min 0.47395** | spearman cua (score_oracle, score_kaggle) tinh RIENG trong tung tick (18,283 tick), roi lay median/min qua cac tick |
| (c) | **rank_exact_match_frac** | **0.05574** | ty le dong co `rank(score, method="first")` trong tick TRUNG TUYET DOI giua Oracle va Kaggle |
| (d) | **chenh edge5 tong (Kaggle - Oracle)** | **+0.197pp** | edge5 Oracle = 15.013%, edge5 Kaggle = 15.209% (cung cong thuc `edge5_series`, cung 18,283 tick) |

Script tai lap: `research/pipeline/x1/kaggle_parity/compare_parity_kaggle.py`
(ket qua tho: `research/pipeline/x1/kaggle_parity/parity_result.json`).

### Doc so lieu

- **rank-in-tick median 0.989** -- cao, dung nhu ky vong ("~0.98+"): 2 model train tren
  CUNG data/hyperparam/seed ra thu tu XEP HANG gan nhu giong het trong da so tick.
- **rank-in-tick min 0.474, rank_exact_match_frac chi 5.6%** -- **KHONG bang 1.0**: dung
  luat da biet tu vong truoc (`KAGGLE_RULES.md` Sec 3e, do tren pipeline Simulator: rho
  0.17040 Oracle vs 0.1723 Kaggle) -- **Kaggle CPU != Oracle CPU** ngay ca cung code/data/
  seed, do khac JVM/OS/float(xgboost build) chu KHONG phai do loi harness. So sanh 2 vong
  gate-reproduction NOI BO Oracle (`gate_result.json`, CUNG mot may) cho rank_exact_match_frac
  = **1.000000** -- tuong phan ro voi 0.056 O DAY (KHAC may) => chenh lech nay THUC SU
  den tu moi truong, khong phai do bug tai lap.
- **edge5 chenh +0.197pp (~1.3% tuong doi tren 15.01%)** -- nho nhung KHONG bang 0. Cung
  huong "so hoc Oracle vs Kaggle chi tin duoc toi ~0.01-0.2%" da ghi trong Sec 3e
  KAGGLE_RULES.md cho pipeline Simulator (o do la 0.008%; o day S1/XGBoost ranker nhay hon
  voi thu tu float nen chenh lon hon mot chut, van cung BAC DO LON: duoi 1 diem pp).

## 4. Luat rut ra -- BAT BUOC cho cac vong Kaggle sau

1. **Kaggle-baseline (`pred_baseline18_kaggle.parquet`, edge5 15.209%) la MOC RIENG** cho
   moi so sanh THANG/NULL/THUA cua cac bien the chay tren Kaggle (HPO/bagging/feature-group
   fan-out). **CAM so Kaggle-variant voi Oracle-baseline** (edge5 15.013%) -- Delta se lan
   0.197pp "venh moi truong" vao tin hieu that, co the doi dau THANG/NULL o muc te.
2. Nguoc lai, **Oracle-variant chi duoc so voi Oracle-baseline**, KHONG so voi
   Kaggle-baseline.
3. Muon so Kaggle voi Oracle (vd audit chinh sach), chi tin duoc **rank-in-tick** (bat bien
   don dieu), KHONG dung spearman toan cuc/score tho, va chi ket luan khi chenh > ~0.2-0.3pp
   edge5 hoac rank-in-tick median tut duoi ~0.98 (nguong do o day).
4. San sang fan-out: **CO** -- dataset + kernel + quy trinh tai lap da xac nhan chay duoc,
   dung xgboost dung ban, dung n_jobs=4, KHONG GPU, thoi gian train du doan ~21 phut/18-fold
   tren Kaggle (gap ~2x Oracle) -- fan-out nhieu bien the can tinh vao ngan sach 5 slot va
   12h kill (KAGGLE_RULES.md Sec 1-2).

## 5. Tai lap

```bash
# 1) Rut gon data tren Oracle (I/O, khong training nang)
python3 research/pipeline/x1/kaggle_parity/make_reduced_dataset.py
# -> /home/ubuntu/s1hpo/kaggle_ds/{feat_v2_x1_keep9,cand_dev_x1_lite}.parquet

# 2) Tao dataset Kaggle (private)
cd /home/ubuntu/s1hpo/kaggle_ds && kaggle datasets create -p .

# 3) Push kernel (CPU, khong GPU)
cd /home/ubuntu/s1hpo/kaggle_kernel && kaggle kernels push -p .
kaggle kernels status chuyendinh/s1-baseline18-parity-20260919   # poll ~25-30s/lan

# 4) Tai output + so sanh
kaggle kernels output chuyendinh/s1-baseline18-parity-20260919 -p ./out
python3 research/pipeline/x1/kaggle_parity/compare_parity_kaggle.py
```

## 6. File lien quan

- `research/pipeline/x1/kaggle_parity/make_reduced_dataset.py` -- sinh dataset rut gon tren Oracle.
- `research/pipeline/x1/kaggle_parity/train_baseline18_kaggle.py` -- kernel Kaggle CPU (self-contained).
- `research/pipeline/x1/kaggle_parity/compare_parity_kaggle.py` -- tinh 4 con so venh.
- `research/pipeline/x1/kaggle_parity/dataset-metadata.json`, `kernel-metadata.json` -- metadata tai lap.
- `research/pipeline/x1/kaggle_parity/summary_kaggle.json` -- log moi truong + timing Kaggle.
- `research/pipeline/x1/kaggle_parity/parity_result.json` -- 4 con so venh (raw).
- Oracle: `/home/ubuntu/s1hpo/pred_baseline18.parquet` (baseline goc), `/home/ubuntu/s1hpo/kaggle_kernel/out/pred_baseline18_kaggle.parquet` (tai ve tu Kaggle).
