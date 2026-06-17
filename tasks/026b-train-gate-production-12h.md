---
id: 026b
status: TODO
depends_on: [025, 026]
touches_live_process: false
writes_242_data: false
resource: kaggle
checkpoint: false
max_retry: 2
report: docs/reports/026b.md
require_review: true
---

# TASK-026b: Train GATE production — horizon 12h + ONNX (tang 1: ML pass)

> 026 = chan doan (chot huong filter mem 12h). 026b = TRAIN RA MODEL DUNG DUOC + xuat ONNX
> de cam backtest. Tin hieu gate = **P_up - P_down** (KHONG hard argmax).

## Input
- `gate_dataset_v1.csv` (190.271 dong x 46 cot, md5 `58d451c6218043fbadf2471e1d701339`).
  - Tren 226: `/home/chuyennd/java/simulator/outputs/gate_dataset_v1.csv`.
  - Tren Kaggle: ĐA co (kernel `chuyendinh/gate-train-026` da doc tu /kaggle/input). Tai dung dataset do.
- Script: `python/tool/train_gate_production.py` (da viet, syntax PASS).

## Viec (CCD — chay Kaggle)
1. Kernel Kaggle: input = dataset chua `gate_dataset_v1.csv` (dataset cu cua 026) + add script production.
   Chay: `python train_gate_production.py <commit_hash_HEAD>`.
2. Doc log, bao lai cac so: CV macro-F1, n_est, **rank-IC OOS + t**, decile spread CV vs OOS,
   DOWN base/prec/rec/lift, RULE precision vs model precision@k (BEAT/KHONG), va dong
   `===== PRE-REGISTERED PASS =====`.
3. Output (de lai Kaggle + tai ve repo `models/gate/` neu PASS): `gate_model_12h.onnx`,
   `gate_model_12h.json`, `gate_features.json`, `gate_manifest.json`.
4. Neu ONNX export FAIL (onnxmltools/NaN) — bao lai, KHONG tu sua; xu o buoc tich hop.

## Pre-registered pass (tang 1 — ML; CHOT voi user, KHONG doi sau khi xem ket qua)
- [ ] rank-IC(P_up-P_down, ret_12h) tren OOS 12 thang cuoi **> 0 va |t| >= 2**.
- [ ] decile spread OOS **giu dau** voi CV.
- [ ] model **BEAT rule baseline** ("breadth thap AND funding cao -> block") o precision lop DOWN.
- 3/3 PASS -> sang tang 2 (backtest). FAIL -> bao user, KHONG tu doi nhan/threshold roi train lai.

## Buoc sau (tang 2 — KHONG thuoc task nay)
- Cam `gate_model_12h.onnx` vao backtest **thay gate cu**, chay **chung funding model ban cu** ->
  do PnL/maxDD/Sharpe + IC thuc vs gate cu tren cung golden range. Đat -> production. Funding moi (037/038/039) sau.

## An toan
- Chi chay Kaggle (KHONG dung 226 process). Doc-thuan v1. SLF4J khong ap dung (Python).

## Job dang chay (ban giao)
- **Kaggle kernel slug:** `chuyendinh/gate-train-026` (version 8, push 2026-06-17 GMT+7).
  - code_file = `train_gate_production.py` (= `python/tool/train_gate_production.py` commit a814887,
    them 1 dong dau inject `sys.argv=['...','a814887']` vi Kaggle khong truyen argv).
  - dataset_sources = `chuyendinh/gate-dataset-v1` (gate_dataset_v1.csv). **enable_internet=true**
    (script pip install onnxmltools de export ONNX — bat buoc, kernel cu de false).
  - Check trang thai: `kaggle kernels status chuyendinh/gate-train-026`.
  - Lay log+output: `kaggle kernels output chuyendinh/gate-train-026 -p ./out`.
- **Buoc con lai:** doc log -> bao so khoi PRE-REGISTERED PASS -> neu output co
  gate_model_12h.{onnx,json}+gate_features.json+gate_manifest.json thi tai ve `models/gate/`.

## (CCD dien) — chay 2026-06-17 GMT+7, kernel v9 COMPLETE
> Luu y: script commit a814887 crash ngay line 53 (`(dt>cutoff).values` — dt la DatetimeIndex,
> so sanh DA la ndarray, khong co `.values`). Da va 1 dong (`np.asarray(dt>cutoff)`) trong
> `python/tool/train_gate_production.py` — bug crash thuan, KHONG dung nhan/threshold/pre-registered.

- **Cac so tu log:**
  - n_feat=37 · md5 dataset khop `58d451...` · OOS cutoff=2025-06-06 · n_train=154662 n_oos=35029
  - dist train (DOWN,FLAT,UP)=[.211,.611,.178] · oos=[.236,.600,.164]
  - **CV macro-F1=0.3321** (std .0414) · n_est(median best)=**56** · CV decile spread=**0.0042**
  - **OOS rank-IC(day)=0.1854  t=8.52** (n_day=365)
  - OOS decile spread=**0.0085** · DOWN base=.2362 prec=.2598 rec=.4170 **lift=1.10**
  - RULE block precision(DOWN)=**0.3943** rec=.0133 lift=1.67
  - **BEAT: model precision@k(=279)=0.1756 vs rule 0.3943 -> KHONG BEAT**
- **PASS/FAIL 3 tieu chi (PRE-REGISTERED):**
  - [PASS] rank-IC OOS>0 & |t|>=2 : IC=0.1854 t=8.52
  - [PASS] decile spread giu dau CV : CV=0.0042 OOS=0.0085 (cung duong)
  - [FAIL] model BEAT rule baseline (precision@k lop DOWN): 0.1756 < 0.3943
  - **=> ML-GATE FAIL (2/3).** Theo pre-registered: FAIL -> bao user, KHONG tu doi nhan/threshold
    roi train lai. CHUA sang tang 2 (backtest). Cho user quyet.
- **Output + duong dan:** ONNX export OK. Tai ve `models/gate/`:
  `gate_model_12h.onnx` (326 KB), `gate_model_12h.json`, `gate_features.json` (37 feat),
  `gate_manifest.json`. Con tren Kaggle output kernel `chuyendinh/gate-train-026` v9.

## DIAGNOSTIC overlap-correct (handoff CCD — chay sau khi user duyet)
> Ly do: t=8.52 cua ban train PHONG DAI vi label ret_12h chong lan 48x (sampling 15m) + cach tinh
> IC theo-ngay khong sach. Beat-rule test lai do kieu CHAN CUNG, trong khi gate la SOFT size-tilt.
> Script do lai cho dung, **KHONG retrain de ep pass**. (User da xac nhan cach do.)
- **Script:** `python/tool/analyze_gate_overlap.py` (refit n_est=56 nhu manifest, do OOS).
- **Chay Kaggle:** add script vao kernel `chuyendinh/gate-train-026` (input dataset
  `chuyendinh/gate-dataset-v1`), `python analyze_gate_overlap.py`. enable_internet KHONG can.
- **Bao lai 4 khoi log:** [1] IC non-overlap (mean/std + %offset p<.05), [2] block-bootstrap CI95
  (khac 0 hay trum 0), [3] Newey-West t (so voi 8.52), [4] bang decile + DOWN% don dieu.
- **Doc:** edge co GIU khi bo chong lan khong (1/2/3) + DOWN% co giam don dieu theo sig khong (4).
  -> quyet dinh gate co dang theo duoi tiep (soft-tilt) hay bo. CHUA sang backtest.
- **Benchmark market model:** chua lam — cho user chi vi tri eval/preds cua market model de do
  cung lang kinh (cung ham IC non-overlap + bootstrap). Ghep sau.
