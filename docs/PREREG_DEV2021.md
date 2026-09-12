# PREREG_DEV2021 — mo DEV lui ve 2021, train fold 2021 MOI cho x26 (net015) + S1

Viet TRUOC khi chay bat ky fold train 2021 nao. Khong sua sau khi thay ket qua.
Nguon boi canh (da doc): `docs/G3_X26_RECOVERY.md`, `docs/G015X26_PROVENANCE.md`,
`docs/PREREG_G015ABL.md` + `docs/RESULT_G015ABL.md`, `docs/RESULT_S1REFRESH.md`,
`docs/G4_RECIPE_C4.md`.

## 0. Muc tieu
Mo DEV lui ve **2021** (nam data som nhat co san) de tang power cho phan xu, KHONG cham
holdout 2026. Train **fold 2021 MOI** cho:
- **x26 (net015)** = model gate P(win), nhan `y = (retEnd_4h > 0.015)` (LABEL_MODE=net,
  base rate toan cuc 0.1849). Model 2021 la **MODEL MOI**, dat ten `g015x26_2021`
  (KHONG phai tai lap x26; x26 goc 16 fold 20220101..20251001 giu nguyen, KHONG dong).
- **S1** = selector rank (XGBRanker rank:ndcg, 9 feature), fold 2021 MOI dat ten `s1a2x1_cut2021*`.

Muc dich cuoi: co fold 2021 de sau nay phan xu lai cac bien the "chet trong CI"
(T170 / GD92 / GATESCALE) voi nhieu power hon. Viec phan xu do la **pre-reg RIENG**, ngoai
pham vi phien nay.

## 1. Cadence + cutoff fold 2021 (theo dung cach fold hien sinh)
WFO expanding, OOS_MONTHS=3, PURGE=72h, TZ=+7h, luoi 15m — y het `g015_net_train.py`
(x26) va `x1_s1_save_all_folds.py` (S1). Cutoff hien co bat dau 20220101 (quy).
Fold 2021 kha thi (theo thu tu tang dan, expanding):

| cutoff | train (expanding, ts < cutoff-72h) | OOS (3 thang) | x26 | S1 |
|---|---|---|---|---|
| 20210101 | (rong — khong co data truoc 2021) | Q1 2021 | KHONG (vo nghia) | KHONG |
| 20210401 | ~Q1 2021 | Q2 2021 | CO | KHONG* |
| 20210701 | Jan–Jun 2021 | Q3 2021 | CO | CO |
| 20211001 | Jan–Sep 2021 | Q4 2021 | CO | CO |

`*` S1 ledger `cand_dev_x1.parquet` ts_min = 2021-03-31 20:00 UTC, nen cutoff 20210401 co
gan 0 dong train truoc purge -> script tu dong skip (len(tr)<5000). => **S1 2021 = {20210701,
20211001}**; **x26 2021 = {20210401, 20210701, 20211001}** (feature+label 2021 phu tu 2021-01).

Fold 2021 la data SOM NHAT; them fold 2021 KHONG dong den bat ky fold >= 20220101 nao
(expanding, moi cutoff doc lap sau khi da co train-cut cua no) va KHONG cham 2026.

## 2. Cong (gate) — phai qua TRUOC khi tin fold 2021

### 2a. REPRODUCTION GATE (chay TRUOC khi train 2021). FAIL -> DUNG, bao, KHONG va.
Do phat hien khi recon: **train lai x26 KHONG cho spearman 1.0** — day la tinh chat da ghi
nhan (`RESULT_G015ABL.md` muc 0 + `G4_RECIPE_C4.md`): retrain net015 qua chinh
`g015_net_train.py` (GPU, seed 42) chi dat **spearman 0.985997** vs x26 goc (fold 20240101),
NAM TRONG bang nhieu multi-seed (s42 vs s43 = 0.984931). XGBoost co subsample=0.8/
colsample=0.8 (ngau nhien theo thiet ke) + GPU non-determinism -> khong the byte/rank-1.0
qua duong TRAIN. Chi duong **PREDICT** (nap 18 model da luu, `g015x26_train.py`) moi cho
spearman 1.0 (16/16, max|d|=1.19e-7 — `G3_X26_RECOVERY.md` muc 6). Vi vay cong tai lap gom
2 phan bo tro (ca hai phai PASS):

- **(A) Cong PREDICT-faithful (nguong spearman 1.0 / max|d| < 1e-6):** chay
  `g015x26_train.py` cho fold **20220101**, so vs manifest goc
  `claudedata/predwf_G015x26/predict_wf_20220101.bin` (rec 1,123,854, sha
  `199ad42e...acc5a`). Ky vong spearman = 1.00000000, max|d| ~ 1.19e-7, keys_all_equal.
  Cong nay xac nhan **loi feature-build + label-join + OOS-slice + bins** (phan tat dinh
  ma fold 2021 dung chung) trung thuc tuyet doi.
- **(B) Cong TRAIN-environment (bang [0.98, 0.99], theo tien le Stage-0 G015ABL):** so bins
  Stage-0 g015ablv0 (drop-cols="" = dung cong thuc x26, Kaggle GPU seed 42) tai fold
  **20240101** vs x26 goc -> ky vong spearman ~0.986 (trong [0.98,0.99]). Xac nhan **trainer
  + moi truong GPU** hanh xu dung nhu ban da tao ra x26.

**Neu (A) FAIL (spearman < 1.0 hoac max|d| >= 1e-6) -> DUNG, bao, KHONG va.** (A) la cong
cung. (B) la cong nen (train-noise da biet); neu (B) roi ngoai [0.98,0.99] -> canh bao +
DUNG cho phan xu master.

> Sai lech pre-reg co chu y (bao master): pre-reg goc yeu cau "tai lap qua pipeline TRAIN ->
> spearman 1.0". Recon chung minh dieu do bat kha thi cho x26 (GPU, non-determinism). Toi
> tach thanh (A) predict-1.0 + (B) train-band[0.98,0.99]. Khong che gì.

### 2b. Provenance
- sha256 feature 2021 khop G3 doc. `features_20210101_to_20210401.t1c` (giai nen tu
  `.t1c.gz` tren dia) = `eca5b0244e4e12b8d26df0afd82475525e0f40c17444c202afe1006bbe638c5c`,
  65,478,640 B — **da xac minh PASS** khi recon. Dataset Kaggle `funding-tool1-15m` va
  `funding-label-15m` deu con du 4 quy 2021 (da xac minh).

### 2c. Fold 2021 integrity (sau khi train)
- record count OOS hop ly (so voi so tick 2021), pred KHONG NaN/inf.
- base rate nhan train ~ ky vong: net015 `retEnd_4h>0.015` cho pos ~0.25-0.30 o cac fold
  train-tren-2021 (doi chieu g015ablv0 fold 20220101 pos=0.2699, train-tren-ca-2021).
- n_train >= 5000 va co ca 2 lop; ts_max(train) < cutoff (khong leak).

## 3. Cach train (chot)
- **x26 2021**: `research/pipeline/g015_net_train.py` — THEM 3 cutoff 2021 vao `CUT_DATES`
  (thay doi duy nhat; nhan `net`/thr 0.015 va toan bo pipeline giu NGUYEN). Chay tren
  **Kaggle GPU** (device=cuda, seed=42, save-model, full 45 feature = drop-cols rong),
  kernel sao tu template `kg015abl/g015ablv0-stage0-gpu` (dataset: funding-tool1-15m,
  funding-label-15m, funding-oi-percoin, sel1m-code; enable_gpu; internet OFF). Submit ASYNC.
- **S1 2021**: `research/pipeline/x1/x1_s1_save_model.py` (env `X1_CUT`) tren **Oracle CPU**
  (nohup, async), cutoff 20210701 + 20211001. CPU/hist/seed42 = tat dinh (S1REFRESH da chung
  minh byte-identical). Cong doi-chieu-ref cua script se rong o 2021 (ref
  `pred_s1a2x1.parquet` chi phu >=2022Q1) — do la binh thuong cho fold MOI; integrity =
  NaN/inf + train count + save JSON/ONNX.

## 4. Ngoai pham vi (khong lam trong pre-reg nay)
- Phan xu lai T170 / GD92 / GATESCALE tren fold 2021 (pre-reg rieng sau khi co fold 2021).
- Moi thao tac tren box 242 (live tien that), deploy, doi wiring/config.
- Train tren 2026 / cham holdout 2026 duoi bat ky hinh thuc nao.
- Tune sieu tham so / doi feature / doi seed.

## 5. Luat cung
- Reproduction gate (A) PASS moi duoc train 2021. FAIL -> DUNG, KHONG va.
- KHONG tune. KHONG git push. Chi Oracle + Kaggle. KHONG cham 242.
- Holdout 2026 bat kha xam pham.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
