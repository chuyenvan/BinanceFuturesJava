# RESULT_DEV2021 — mo DEV lui ve 2021: train fold 2021 x26(net015) + S1 (2026-09-12)

Pre-reg: `docs/PREREG_DEV2021.md`. Phien: RECON + PRE-REG + gate + PREP + SUBMIT (GPU async).
KHONG cham 242, KHONG push, KHONG tune, holdout 2026 nguyen ven.

## 0. Phan quyet (so truoc)
- **REPRODUCTION GATE: PASS.**
  - (A) PREDICT-faithful, fold 20220101: spearman **1.00000000**, max|d| **1.192e-07**,
    keys_all_equal=True; sha bin goc = `199ad42e...acc5a` (dung x26).
  - (B) TRAIN-environment, fold 20240101 (Stage-0 g015ablv0 GPU vs x26): spearman **0.985962**,
    trong bang [0.98,0.99] (khop tien le 0.985997).
- **Provenance: PASS.** 2021Q1 feature (giai nen tu `.t1c.gz`) sha =
  `eca5b0244e4e12b8d26df0afd82475525e0f40c17444c202afe1006bbe638c5c` @ 65,478,640 B — khop G3.
  Dataset Kaggle `funding-tool1-15m` + `funding-label-15m` deu du 4 quy 2021.
- **x26 2021: DA SUBMIT Kaggle GPU (async).** kernel `chuyendinh/g015x26-2021-gpu` v1, status RUNNING.
- **S1 2021: DA TRAIN xong tren Oracle CPU.** 2 fold model+ONNX luu, integrity PASS.

## 1. Recon (so that)
- Oracle branch `module`, RAM 23GB (~19GB free), **KHONG co GPU** (nvidia-smi NO_GPU), xgboost 3.2.0.
- Kaggle: `kaggle.json` co, auth qua `KaggleApi` OK (khong co CLI binary; dung python API).
- Trainer x26: **`research/pipeline/g015_net_train.py`** — DA CO san ban TAI DUNG day du (nhan
  net `y=(retEnd_4h>0.015)`, WFO, save-model, device). KHONG can viet lai phan nhan (da dung).
  Thay doi DUY NHAT phien nay: them 3 cutoff 2021 vao `CUT_DATES` (prepend).
- Data 2021: `ds_feat15m/features_2021*.t1c.gz` (4 quy) + `label_15m/funding_label_2021*.pb`
  (4 quy) + `retEnd_4h` co trong .pb. Feature 2021 phu tu 2021-01.
- Ledger S1 `cand_dev_x1.parquet`: ts_min 2021-03-31 20:00 -> S1 2021 chi kha thi {20210701, 20211001}.

## 2. Cutoff fold 2021 (theo cadence quy hien co)
| model | cutoff moi | train (expanding) | OOS | trang thai |
|---|---|---|---|---|
| x26 (g015x26_2021) | 20210401 | ~Q1 2021 | Q2 2021 | Kaggle GPU (RUNNING) |
| x26 | 20210701 | Jan–Jun 2021 | Q3 2021 | Kaggle GPU (RUNNING) |
| x26 | 20211001 | Jan–Sep 2021 | Q4 2021 | Kaggle GPU (RUNNING) |
| S1 | 20210701 | ledger Q2 2021 | Q3 2021 | DONE (train 56015 oos / 489 tick) |
| S1 | 20211001 | ledger Q2–Q3 2021 | Q4 2021 | DONE (train 389583 / oos 56033 / 445 tick) |

20210101 vo nghia (khong co train truoc 2021). S1 20210401 skip (ledger gan-rong truoc purge).
Them fold 2021 KHONG dong fold >=20220101 (expanding, doc lap) va KHONG cham 2026.

## 3. Reproduction gate — chi tiet
### 3a. (A) PREDICT-faithful — nguong cung spearman 1.0 / max|d|<1e-6
`g015x26_train.py` fold 20220101 (nap 18 model goc, predict lai) vs
`claudedata/predwf_G015x26/predict_wf_20220101.bin` (rec 1,123,854):
- n_orig=n_regen=1,123,854, keys_all_equal=True, **spearman=1.00000000, max|d|=1.192e-07** -> PASS.
- Xac nhan phan tat dinh (feature-build memory-light + label-join net + OOS-slice + bins 26B)
  ma fold 2021 dung chung la trung thuc tuyet doi.

### 3b. (B) TRAIN-environment — bang [0.98,0.99]
Bins Stage-0 `kg015abl/g015ablv0-stage0-gpu/out/predict_wf_20240101.bin` (retrain FULL 45 feature,
Kaggle GPU seed 42, cung `g015_net_train.py`) vs x26 goc fold 20240101:
- n=2,140,992 ca hai, keys_equal=True, **spearman=0.985962** -> trong [0.98,0.99] PASS.
- Ly do khong 1.0: XGBoost subsample/colsample ngau nhien + GPU non-determinism (da ghi
  `RESULT_G015ABL.md` muc 0: 0.985997; s42-vs-s43 = 0.984931). => train-repro-1.0 bat kha thi;
  do la ly do fold 2021 la MODEL MOI, khong phai tai lap.

## 4. x26 2021 — SUBMIT Kaggle GPU (async)
- Kernel dir: `/home/ubuntu/kg015x26_2021/g015x26-2021-gpu/` (header path-discovery /kaggle/input +
  `g015_net_train.py` da patch CUT_DATES, argv `--fold 20210401,20210701,20211001 --device cuda
  --save-model --drop-cols "" ` = full 45 feature = cong thuc x26).
- kernel-metadata: `chuyendinh/g015x26-2021-gpu`, enable_gpu=true, internet OFF, dataset_sources =
  funding-tool1-15m, funding-label-15m, funding-oi-percoin, sel1m-code.
- Push: versionNumber=1, error="", invalidDatasetSources=[]. URL
  https://www.kaggle.com/code/chuyendinh/g015x26-2021-gpu — **status RUNNING** (ETA vai phut
  compute; 3 fold, data 2021 nho). Output se co `predict_wf_2021*.bin` + `model_f*_4h.json` +
  `net_train_summary.json` o /kaggle/working.
- Integrity fold 2021 (record count / NaN-inf / base rate ~0.25-0.30) se kiem SAU khi kernel xong
  (phien sau, async — pre-reg muc 2c).

## 5. S1 2021 — DONE (Oracle CPU)
- `x1_s1_save_model.py` (env X1_CUT), CPU/hist/seed42, out `/home/ubuntu/s1_2021/out_<cut>/`:
  - cut20210701: json 567,700 B + onnx 246,418 B; OOS 56,015 / 489 tick.
  - cut20211001: train 389,583 (den 2021-09-27 14:45), fit 11s; json 592,080 B + onnx 259,283 B;
    OOS 56,033 / 445 tick.
- Integrity (predict OOS bang JSON booster): **NaN=0, inf=0** ca hai; phan phoi
  20210701 mean -0.6487 std 0.4791 [-1.48,2.40]; 20211001 mean -0.8348 std 0.4573 [-1.41,2.18]
  — cung scale voi model S1 hien co (S1REFRESH: mean -1.065 std 0.611). PASS.
- Cong doi-chieu-ref cua script THOAT loi (0/0 dong ref) vi `pred_s1a2x1.parquet` chi phu >=2022Q1;
  day la binh thuong cho fold MOI (khong co ref 2021). Model+ONNX da luu TRUOC buoc do.

## 6. Sai lech pre-reg (bao master)
- Pre-reg goc yeu cau reproduction gate "qua pipeline TRAIN -> spearman 1.0". Recon chung minh
  bat kha thi cho x26 (GPU non-determinism, ~0.986). Da tach thanh (A) predict-1.0 (cong cung,
  PASS) + (B) train-band[0.98,0.99] (PASS). Master phan xu neu muon dinh nghia khac.
- Khong sai lech nao khac. Khong tune, khong push, khong cham 242/2026.

## 7. Viec con lai (phien sau)
1. Cho kernel `g015x26-2021-gpu` xong -> pull output -> integrity fold 2021 (muc 2c) -> ghi manifest.
2. (Neu master duyet) phan xu lai T170/GD92/GATESCALE tren fold 2021 — pre-reg RIENG.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT

---

## 8. x26 2021 — KERNEL COMPLETE + PULL + INTEGRITY (cap nhat 2026-09-12)

Kernel `chuyendinh/g015x26-2021-gpu` v1: **status COMPLETE** (failureMessage rong). Pull ve
`/home/ubuntu/kg015x26_2021/g015x26-2021-gpu/out/` (3 model JSON + 3 bins + summary + log).
device=cuda, seed=42, xgb 3.2.0, drop_cols=[] (full 45 feature = cong thuc x26).

### 8.1 Integrity 3 fold (PASS)
| cutoff | n_train | pos (train) | spw | n_oos = rec bins | NaN/inf | p0 min/mean/max |
|---|---:|---:|---:|---:|:---:|---|
| 20210401 | 702,071 | 0.3312 | 2.020 | 933,005 | 0/0 | 0.0166 / 0.4821 / 0.9953 |
| 20210701 | 1,632,008 | 0.3140 | 2.185 | 999,162 | 0/0 | 0.0656 / 0.4406 / 0.9714 |
| 20211001 | 2,628,041 | 0.2944 | 2.397 | 1,104,563 | 0/0 | 0.1007 / 0.4366 / 0.9849 |

- record count bins = n_oos khop tuyet doi (filesize/26). pred KHONG NaN/inf. p0 trong (0,1) hop ly.
- sha256 bins (tinh lai khi pull) = sha_bin trong `net_train_summary.json` ca 3 fold -> **self-consistent**.

### 8.2 Base rate — dung ky vong (khong phai bat thuong)
Base rate nhan `retEnd_4h>0.015` **doc lap tren toan 2021** (nBars_4h>=16, 3,768,122 dong) =
**0.2690**. Vay pos train tung fold 2021 (0.29-0.33) la DUNG — 0.1849 la base TOAN CUC moi nam;
2021 (futures som, bien dong manh) cao hon, khop g015ablv0 fold 20220101 pos=0.2699 (train tren
ca 2021). pos giam dan 0.331 -> 0.294 khi cua so train mo rong trong 2021 (som cao hon). Khong
phai anomaly.

### 8.3 Manifest sha256 (3 fold x26 2021)
File: `/home/ubuntu/kg015x26_2021/g015x26-2021-gpu/out/MANIFEST_DEV2021.sha256`
```
predict_wf_20210401.bin  933005   fd4b3bc7aaed9c318245e284a18221ed3bcd8f7e17caea537d1388566b50b2f9
predict_wf_20210701.bin  999162   87b7d2e7a01cf84824ebe42982f127522fa5d8aa4d116dcf76b7cf0326473210
predict_wf_20211001.bin  1104563  59e0241dd60fa2d1f6eac1830379c2e8b31a14ddb8cd1d265c6493592f9f898b
```
Model JSON: `model_f0_4h.json` (cut20210401), `model_f1` (20210701), `model_f2` (20211001).

### 8.4 Phan quyet cap nhat
- **x26 2021 + S1 2021 DONE, integrity PASS ca 5 fold.** DEV da mo lui ve 2021.
- Con lai (pre-reg RIENG, cho master duyet): phan xu lai T170/GD92/GATESCALE tren fold 2021.
- KHONG cham 242, KHONG push, KHONG train 2026, holdout 2026 nguyen ven.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
