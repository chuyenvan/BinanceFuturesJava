# RESULT_NET015_CUT20251231 — refresh model GIA TRI net015 (x26) cutoff 20251231 (2026-09-12)

Pre-reg: `docs/PREREG_NET015_CUT20251231.md`. Phien: pre-reg + gate + train Kaggle GPU (async).
KHONG cham 242, KHONG git push, KHONG tune, KHONG train 2026 (train data dung <= 2025-12-27).

## 0. Phan quyet (so truoc)
- **REPRODUCTION GATE: PASS.**
  - (A) PREDICT-faithful (cut20251001, nap booster goc predwf_G015/model_f15_4h.json, predict lai
    OOS 2025Q4 -> so predwf_G015x26/predict_wf_20251001.bin): rec 4,517,610 = 4,517,610,
    keys_all_equal=True, **spearman 1.00000000, max|d| 1.192e-07**, NaN/inf 0 -> PASS (nguong cung).
  - (B) TRAIN-band (retrain cut20251001 tren Kaggle GPU, cung g015_net_train.py seed42 -> so
    predict_wf_20251001.bin moi vs goc): rec 4,517,610 = 4,517,610, keys_all_equal=True,
    **spearman 0.99135773**, NaN/inf 0. Nam TREN tran [0.98,0.99] (fidelity CAO hon ky vong;
    xa han nguong FAIL <0.98). Reproduction xac nhan. (Sai lech pre-reg nho — xem muc 5.)
- **INTEGRITY model moi (cut20251231): PASS.** NaN/inf 0; rec 4,585,546 = filesize/26 (exact);
  p0 min/mean/max 0.01405 / 0.46629 / 0.91466 (trong (0,1)); pos train 0.1890 ~ net base 0.1849.
- **EXPORT ONNX cut20251231 + parity onnx-vs-json: PASS.** spearman 1.0000000000, max|d| 4.172e-07,
  mean|d| 3.708e-08, top-8/50/200 overlap = 100% (300k mau feature 2025Q4).
- => **UNG VIEN DEPLOY.** DUNG, cho USER quyet dinh deploy (buoc 242). Khong deploy phien nay.

## 1. Thay doi (chi 1)
Them "20251231" vao CUT_DATES trong `research/pipeline/g015_net_train.py` (chen sau "20251001").
CUT_DATES = 22 cutoff: idx(20251001)=18, idx(20251231)=19, idx(20260101)=20. Index 20251001
KHONG doi -> cong tai lap predict-faithful nguyen ven. Khong doi hyperparam/nhan/feature.

## 2. Kaggle GPU kernel
- Kernel `chuyendinh/g015x26-cut20251231-gpu` v1 (gpu=true, internet=false, datasets:
  funding-tool1-15m, funding-label-15m, funding-oi-percoin, sel1m-code). Header path-discovery
  /kaggle/input + `g015_net_train.py` (CUT_DATES da them 20251231), argv `--fold 20251001,20251231
  --device cuda --save-model --drop-cols ""` = cong thuc x26 full 45 feature.
- **status COMPLETE** (failureMessage rong), ~15.5 phut. Pull ve
  `/home/ubuntu/kg015x26_cut20251231/g015x26-cut20251231-gpu/out/`.
- device=cuda seed=42 nest=400 xgb 3.2.0.

| cutoff | fold_idx | n_train | train ts_max | pos | spw | n_oos | p_mean | p_std |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| 20251001 (repro) | 18 | 34,904,563 | 2025-09-27 16:45 | 0.1891 | 4.288 | 4,517,610 | 0.5043 | 0.1316 |
| 20251231 (MOI) | 19 | 39,354,754 | **2025-12-27 16:45** | 0.1890 | 4.291 | 4,585,546 | 0.4663 | 0.1262 |

- Holdout 2026 KHONG train: train ts_max cut20251231 = 2025-12-27 16:45 (<= 2025-12-31). Khop S1
  cut20251231 (train den 2025-12-27 16:30). OOS byproduct predict_wf_20251231.bin phu
  2025-12-30 17:00 -> 2026-03-30 16:45 (2026Q1) — **KHONG danh gia / KHONG dung** cho quyet dinh.

## 3. Artifact + MANIFEST sha256
File: `/home/ubuntu/kg015x26_cut20251231/g015x26-cut20251231-gpu/out/MANIFEST_NET015_CUT20251231.sha256`
```
model_f19_4h.json       1667352    83a5333df0f7b1271f90658e81b0e37f4e2b29e681b8d7a37a0526e2b855657d
predict_wf_20251231.bin 119224196  b40586a63925c602dd191130d7eab76ded4f24e98c9bde23d959c76f204b08eb
g015x26_f15_cut20251231.onnx 807545 41a07109d8f392fee4b1ec59af01ac359d26ef1493fcdefbad5cb867724206ce
```
- ONNX: `/home/ubuntu/g3x26/g015x26_f15_cut20251231.onnx`. sha_bin predict = sha trong
  net_train_summary.json (self-consistent). ONNX [None,45] positional, opset 15 (giong cut20251001).

## 4. Buoc USER can (DEPLOY 242 — KHONG lam phien nay)
1. `cp /home/ubuntu/g3x26/g015x26_f15_cut20251231.onnx /home/ubuntu/deploy_242_l3/models/`
2. Set khoa cfg **`NET015_MODEL_ONNX`** (doc qua `Cfg.get` trong
   `src/main/java/com/binance/chuyennd/tradecore/selector/Net015ValueLive.java`) tro toi
   `.../models/g015x26_f15_cut20251231.onnx` (hien tro g015x26_f15_cut20251001.onnx). Vi du env.sh
   L4: `NET015_MODEL_ONNX=/home/ubuntu/deploy_242_l3/models/g015x26_f15_cut20251231.onnx`.
3. Cap nhat `deploy_242_l3/models/SHA256SUMS` (them dong onnx moi). `feature_order_net015.txt`
   GIU NGUYEN (cung 45 feature positional).
4. Restart tien trinh live (L4 run) de nap ONNX moi.

## 5. Sai lech pre-reg (bao master)
- Gate (B) train-band: pre-reg ky vong [0.98,0.99]; do thuc te = 0.99135773, TREN tran 0.99 mot
  chut. Day la fidelity CAO hon (retrain giong ban goc hon DEV2021 0.9860), KHONG phai break —
  luat FAIL pre-reg la spearman < 0.98 (khong kich hoat). Ket hop voi (A)=1.0 exact => reproduction
  vung chac. Master phan xu neu muon dinh nghia band khac.
- Khong sai lech nao khac. Khong tune, khong push, khong cham 242, holdout 2026 khong train.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
