# PREREG_NET015_CUT20251231 — refresh model GIA TRI net015 (x26) cutoff 20251231 (2026-09-12)

Pre-reg VIET TRUOC khi train. Phien: pre-reg + gate + train Kaggle GPU (async). Tuan thu:
KHONG cham 242, KHONG git push, KHONG tune, KHONG train 2026 (train data dung <= 2025-12-31).

## 1. Muc tieu
Refresh model GIA TRI net015 (= predwf_G015x26, trainer research/pipeline/g015_net_train.py) tai
cutoff 20251231 cho gate live, DONG BO voi S1 cut20251231 (docs/RESULT_S1REFRESH.md). Van hanh
theo protocol WFO da chot (expanding, OOS_MONTHS=3, PURGE=72h, TZ=+7h, seed 42, n_est 400, full
45 feature). Deliverable: g015x26_f15_cut20251231.onnx cho khoa NET015_MODEL_ONNX. Holdout 2026
KHONG train (train data dung <= 2025-12-31 tru purge 72h = ~2025-12-28).

## 2. Thay doi DUY NHAT
Them "20251231" vao CUT_DATES trong g015_net_train.py, chen sau "20251001" (thanh index 19).
KHONG doi index cua 20251001 (van index 18) -> cong tai lap predict-faithful khong bi anh huong.
KHONG doi hyperparam, khong doi nhan (net y=retEnd_4h>0.015), khong doi feature. = cong thuc x26.

## 3. Cong (gate) — fail thi DUNG + bao
(a) REPRODUCTION tren cutoff DA CO (20251001):
  (A) PREDICT-faithful (nguong CUNG): nap booster goc predwf_G015/model_f15_4h.json, predict lai
      OOS 2025Q4 -> so predwf_G015x26/predict_wf_20251001.bin: spearman ~1.0, max|d|<1e-6.
  (B) TRAIN-band [0.98,0.99]: retrain 20251001 tren Kaggle GPU (cung g015_net_train.py) -> so
      predict_wf_20251001.bin moi vs goc: spearman trong [0.98,0.99] (GPU non-determinism, nhu
      DEV2021 fold 20240101 = 0.985962). Neu spearman < 0.98 -> FAIL, DUNG + bao master.
(b) INTEGRITY model moi (cut20251231): pred khong NaN/inf; base rate hop ly; record count =
    filesize/26; phan phoi p0 trong (0,1).
(c) EXPORT ONNX cut20251231 + verify ONNX-vs-booster JSON: spearman ~1.0, max|d| nho, top-k parity.

## 4. Ngoai pham vi
KHONG train 2026: OOS byproduct 2026Q1 (predict_wf_20251231.bin) la he qua co hoc cua WFO trainer,
KHONG danh gia / KHONG dung cho bat ky quyet dinh nao. KHONG deploy (buoc 242 = user). KHONG tune.
KHONG push.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
